from __future__ import annotations

"""AU READ ONLY - trazabilidad fila a fila de PrecioCosto: STAGING -> CORE_OPERACION."""

import sqlite3
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "matinal.db"
TIPO_CANJE = "Devolución por Canje"
TOL = 0.01

# Clave transaccional compuesta exclusivamente por atributos que CORE_OPERACION
# debe preservar. PrecioCosto queda deliberadamente FUERA de la clave para poder
# auditarlo como valor transportado.
CLAVE_BASE = [
    "Cliente",
    "CodVendedor",
    "FechaCarga_dt",
    "Codigo",
    "TipoDeVenta",
    "CantBase",
    "ImporteNetoItem",
    "Proveedor",
]


def titulo(texto: str) -> None:
    print("\n" + "=" * 128)
    print(texto)
    print("=" * 128)


def conectar_ro() -> sqlite3.Connection:
    if not DB.exists():
        raise FileNotFoundError(f"No existe {DB}")
    con = sqlite3.connect(DB.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    con.execute("PRAGMA query_only=ON;")
    return con


def parametros():
    con = conectar_ro()
    try:
        print("SQLite quick_check:", con.execute("PRAGMA quick_check;").fetchone()[0])
        p = dict(con.execute("SELECT PARAMETRO, VALOR FROM parametros").fetchall())
    finally:
        con.close()
    dm = pd.to_datetime(p.get("Dia Matinal"), dayfirst=True, errors="coerce")
    dv = pd.to_datetime(p.get("Dia Venta"), dayfirst=True, errors="coerce")
    if pd.isna(dm) or pd.isna(dv):
        raise RuntimeError("Dia Matinal o Dia Venta inválido.")
    return (
        int(float(p.get("Año", dm.year))),
        int(float(p.get("Mes", dm.month))),
        pd.Timestamp(dm).normalize(),
        pd.Timestamp(dv).normalize(),
    )


def normalizar_para_clave(df: pd.DataFrame, capa: str) -> pd.DataFrame:
    faltantes = [c for c in CLAVE_BASE + ["PrecioCosto"] if c not in df.columns]
    if faltantes:
        raise RuntimeError(f"{capa} no contiene columnas necesarias: {faltantes}")

    x = df.copy()
    for c in ["Cliente", "CodVendedor", "Codigo"]:
        x[c] = pd.to_numeric(x[c], errors="coerce").astype("Int64")
    x["FechaCarga_dt"] = pd.to_datetime(
        x["FechaCarga_dt"], errors="coerce"
    ).dt.normalize()
    for c in ["CantBase", "ImporteNetoItem", "PrecioCosto"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    for c in ["TipoDeVenta", "Proveedor"]:
        x[c] = x[c].fillna("").astype(str).str.strip()

    # Clave textual estable. Los floats se redondean solo para la CLAVE de matching;
    # PrecioCosto se compara después con tolerancia monetaria.
    x["_k_cliente"] = x["Cliente"].astype("string").fillna("<NA>")
    x["_k_vend"] = x["CodVendedor"].astype("string").fillna("<NA>")
    x["_k_fecha"] = x["FechaCarga_dt"].dt.strftime("%Y-%m-%d").fillna("<NA>")
    x["_k_codigo"] = x["Codigo"].astype("string").fillna("<NA>")
    x["_k_tipo"] = x["TipoDeVenta"]
    x["_k_cant"] = x["CantBase"].round(6).astype("string").fillna("<NA>")
    x["_k_importe"] = x["ImporteNetoItem"].round(6).astype("string").fillna("<NA>")
    x["_k_prov"] = x["Proveedor"].str.upper()
    kcols = [
        "_k_cliente",
        "_k_vend",
        "_k_fecha",
        "_k_codigo",
        "_k_tipo",
        "_k_cant",
        "_k_importe",
        "_k_prov",
    ]
    x["ClaveBase"] = x[kcols].agg("|".join, axis=1)

    # Algunas líneas comerciales pueden ser idénticas. El ordinal convierte la
    # clave base en una clave transaccional de multiconjunto sin usar PrecioCosto.
    x = x.sort_values(CLAVE_BASE, kind="stable", na_position="last").copy()
    x["Ordinal"] = x.groupby("ClaveBase", dropna=False).cumcount() + 1
    x["ClaveTransaccional"] = x["ClaveBase"] + "|#" + x["Ordinal"].astype(str)
    return x


def main() -> None:
    titulo("AU READ ONLY - PRECIOCOSTO FILA A FILA CON CLAVE TRANSACCIONAL")
    print(f"Proyecto               : {ROOT}")
    print(f"Base                   : {DB}")
    print("SQLite                 : mode=ro + PRAGMA query_only=ON")
    print("Escrituras productivas : NINGUNA")
    anio, mes, dm, dv = parametros()
    print(
        f"Escenario              : Matinal={dm:%d/%m/%Y} | Venta={dv:%d/%m/%Y} | período={mes:02d}/{anio}"
    )

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from modules.staging import obtener_staging_vta
    from modules.core.core_operaciones import obtener_core_operacion
    from modules.core.core_vendedores import obtener_core_vendedores

    validos = set(
        pd.to_numeric(obtener_core_vendedores()["CodVendedor"], errors="coerce")
        .dropna()
        .astype(int)
        .tolist()
    )

    titulo("1. CAPAS PRODUCTIVAS")
    stg = obtener_staging_vta()
    core = obtener_core_operacion(
        anio,
        mes,
        dm.strftime("%d/%m/%Y"),
        dv.strftime("%d/%m/%Y"),
        modo_ajuste="AJUSTADO",
    )["df_vta_operativa"].copy()
    print(f"STAGING filas           : {len(stg):,}")
    print(f"CORE operativa filas    : {len(core):,}")
    print("PrecioCosto STAGING     :", "PrecioCosto" in stg.columns)
    print("PrecioCosto CORE        :", "PrecioCosto" in core.columns)

    # El universo a auditar se define SOLO desde CORE. No reconstruimos reglas temporales.
    col_vig = (
        "CodVendedorVigente" if "CodVendedorVigente" in core.columns else "CodVendedor"
    )
    vend_vig = pd.to_numeric(core[col_vig], errors="coerce").astype("Int64")
    mask_core = (
        core["Proveedor"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .str.contains("PEPSICO", na=False)
        & core["TipoDeVenta"].fillna("").astype(str).str.strip().eq(TIPO_CANJE)
        & vend_vig.isin(validos)
    )
    if "Periodo" in core.columns:
        mask_core &= core["Periodo"].isin(["Arrastre", "Actual"])
    core_canje = core.loc[mask_core].copy()

    titulo("2. UNIVERSO CORE OBJETIVO")
    print(f"Canjes CORE a trazar    : {len(core_canje):,}")
    print(f"Vendedores vigentes     : {vend_vig.loc[mask_core].nunique():,}")
    print(
        f"PrecioCosto suma        : {pd.to_numeric(core_canje['PrecioCosto'], errors='coerce').sum():,.2f}"
    )
    print(
        f"PrecioCosto suma abs    : {pd.to_numeric(core_canje['PrecioCosto'], errors='coerce').abs().sum():,.2f}"
    )

    # STAGING se limita solo por atributos comerciales amplios. El matching exacto
    # se realiza con las claves de las filas CORE, por lo que no se reimplementa CORE.
    mask_stg = stg["Proveedor"].fillna("").astype(
        str
    ).str.strip().str.upper().str.contains("PEPSICO", na=False) & stg[
        "TipoDeVenta"
    ].fillna("").astype(str).str.strip().eq(TIPO_CANJE)
    stg_canje = stg.loc[mask_stg].copy()

    core_k = normalizar_para_clave(core_canje, "CORE")
    stg_k = normalizar_para_clave(stg_canje, "STAGING")

    titulo("3. MATCH DE CLAVES CORE CONTRA STAGING")
    # Para no distorsionar ordinales por historia completa, primero retenemos en STAGING
    # únicamente claves base exigidas por CORE y luego recalculamos ordinal dentro de ellas.
    claves_core_base = set(core_k["ClaveBase"])
    stg_match_base = stg_k.loc[stg_k["ClaveBase"].isin(claves_core_base)].copy()
    # Recalcular ordinal tras restringir no es necesario: la clave base representa mismas
    # líneas; se compara como multiconjunto por ClaveBase + PrecioCosto ordenado.
    conteo_core = core_k.groupby("ClaveBase").size().rename("Filas_CORE")
    conteo_stg = stg_match_base.groupby("ClaveBase").size().rename("Filas_STG")
    conteos = (
        pd.concat([conteo_core, conteo_stg], axis=1).fillna(0).astype(int).reset_index()
    )
    conteos["DifFilas"] = conteos["Filas_STG"] - conteos["Filas_CORE"]
    claves_insuficientes = conteos.loc[
        conteos["Filas_STG"].lt(conteos["Filas_CORE"])
    ].copy()
    print(f"Claves base CORE        : {len(conteo_core):,}")
    print(f"Claves halladas STAGING : {int(conteos['Filas_STG'].gt(0).sum()):,}")
    print(f"Claves insuficientes    : {len(claves_insuficientes):,}")

    # Comparación de multiconjunto por clave base: ordenar PrecioCosto dentro de cada clave
    # y emparejar por ordinal. Esto evita usar PrecioCosto como parte de la clave auditada.
    def rank_precio(x: pd.DataFrame, suf: str) -> pd.DataFrame:
        y = x[["ClaveBase", "PrecioCosto"]].copy()
        y = y.sort_values(
            ["ClaveBase", "PrecioCosto"], kind="stable", na_position="last"
        )
        y["OrdinalPrecio"] = y.groupby("ClaveBase", dropna=False).cumcount() + 1
        return y.rename(columns={"PrecioCosto": f"PrecioCosto_{suf}"})

    a = rank_precio(core_k, "CORE")
    b = rank_precio(stg_match_base, "STG")
    comp = a.merge(
        b, on=["ClaveBase", "OrdinalPrecio"], how="left", validate="one_to_one"
    )
    comp["DifPrecioCosto"] = comp["PrecioCosto_STG"] - comp["PrecioCosto_CORE"]
    comp["MatchPrecio"] = comp["PrecioCosto_STG"].notna() & comp[
        "DifPrecioCosto"
    ].abs().le(TOL)

    faltantes = comp["PrecioCosto_STG"].isna()
    distintos = comp["PrecioCosto_STG"].notna() & ~comp["MatchPrecio"]
    print(f"Filas CORE trazadas     : {len(comp):,}")
    print(f"Filas sin match STAGING : {int(faltantes.sum()):,}")
    print(f"PrecioCosto diferente   : {int(distintos.sum()):,}")
    print(f"PrecioCosto exacto/tol  : {int(comp['MatchPrecio'].sum()):,}")

    if faltantes.any() or distintos.any():
        titulo("4. DIFERENCIAS - PRIMERAS 30")
        print(
            comp.loc[
                faltantes | distintos,
                [
                    "ClaveBase",
                    "OrdinalPrecio",
                    "PrecioCosto_CORE",
                    "PrecioCosto_STG",
                    "DifPrecioCosto",
                ],
            ]
            .head(30)
            .to_string(index=False)
        )

    titulo("5. CONCILIACION MONETARIA DE FILAS MATCH")
    print(f"CORE PrecioCosto abs    : {comp['PrecioCosto_CORE'].abs().sum():,.2f}")
    print(f"STG PrecioCosto abs     : {comp['PrecioCosto_STG'].abs().sum():,.2f}")
    print(f"Diferencia algebraica   : {comp['DifPrecioCosto'].fillna(0).sum():,.6f}")

    titulo("VEREDICTO")
    if faltantes.any() or distintos.any():
        print("RESULTADO: NO APROBADO")
        print(
            "Existen filas CORE sin trazabilidad o diferencias de PrecioCosto frente a STAGING."
        )
        raise SystemExit(1)
    print("RESULTADO: APROBADO")
    print(
        "Las filas CORE de canje PepsiCo trazan contra STAGING y PrecioCosto se conserva sin diferencias."
    )
    print("La auditoría no reconstruye el corte temporal de CORE_OPERACION.")
    print("READ ONLY - Escrituras realizadas: NINGUNA")


if __name__ == "__main__":
    main()
