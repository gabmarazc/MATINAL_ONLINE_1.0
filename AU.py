from __future__ import annotations

"""AUDITORIA EMPIRICA READ ONLY - deteccion robusta de columnas + filtro supervisor TP/Cobertura."""

import sqlite3
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "matinal.db"
SUPS = (60, 70)


def titulo(texto: str) -> None:
    print("\n" + "=" * 120)
    print(texto)
    print("=" * 120)


def conectar_ro() -> sqlite3.Connection:
    if not DB.exists():
        raise FileNotFoundError(f"No existe {DB}")
    con = sqlite3.connect(DB.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    con.execute("PRAGMA query_only=ON;")
    return con


def normalizar_nombre(valor) -> str:
    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return "".join(c for c in texto if c.isalnum())


def detectar_columna(
    df: pd.DataFrame, candidatos: list[str], contiene: list[str] | None = None
) -> str | None:
    if df is None or df.empty and len(df.columns) == 0:
        return None
    mapa = {normalizar_nombre(c): c for c in df.columns}
    for candidato in candidatos:
        clave = normalizar_nombre(candidato)
        if clave in mapa:
            return mapa[clave]
    if contiene:
        tokens = [normalizar_nombre(x) for x in contiene]
        for c in df.columns:
            nc = normalizar_nombre(c)
            if any(token in nc for token in tokens):
                return c
    return None


def parametros() -> tuple[int, int, pd.Timestamp, pd.Timestamp]:
    con = conectar_ro()
    try:
        quick = con.execute("PRAGMA quick_check;").fetchone()[0]
        filas = con.execute("SELECT PARAMETRO, VALOR FROM parametros").fetchall()
    finally:
        con.close()
    p = {str(k).strip(): v for k, v in filas}
    dm = pd.to_datetime(p.get("Dia Matinal"), dayfirst=True, errors="coerce")
    dv = pd.to_datetime(p.get("Dia Venta"), dayfirst=True, errors="coerce")
    if pd.isna(dm) or pd.isna(dv):
        raise RuntimeError(
            f"Fechas invalidas: Dia Matinal={p.get('Dia Matinal')!r}, Dia Venta={p.get('Dia Venta')!r}"
        )
    anio = int(float(p.get("Año", p.get("Anio", dv.year))))
    mes = int(float(p.get("Mes", dv.month)))
    print(f"SQLite quick_check: {quick}")
    return anio, mes, pd.Timestamp(dm).normalize(), pd.Timestamp(dv).normalize()


def main() -> None:
    titulo("AUDITORIA EMPIRICA READ ONLY - SUPERVISOR GLOBAL - TP Y COBERTURA")
    print(f"Proyecto: {ROOT}")
    print(f"Base: {DB}")
    print("Modo: SQLite mode=ro + PRAGMA query_only=ON")
    print("Escrituras: NINGUNA")

    anio, mes, dm, dv = parametros()
    print(
        f"Escenario: Matinal={dm:%d/%m/%Y} | Venta={dv:%d/%m/%Y} | periodo={mes:02d}/{anio}"
    )

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from modules import database as db
    from modules.business_rules.business_rules_tp import generar_business_rules_tp
    from modules.core.core_cobertura import obtener_base_cobertura

    titulo("1. DETECCION EMPIRICA DE MAESTRO_VENDEDORES")
    mv = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    print(f"Filas maestro_vendedores: {len(mv):,}")
    print("Columnas reales:")
    for i, c in enumerate(mv.columns, 1):
        print(f"  {i:02d}. {c}")

    cod_col = detectar_columna(
        mv,
        [
            "CodVend",
            "CodVendedor",
            "Codigo",
            "CodigoVendedor",
            "IDVEND",
            "IdVendedor",
            "Cod_Vendedor",
        ],
        contiene=["codvend", "codigovend", "idvend"],
    )
    sup_col = detectar_columna(
        mv,
        ["SUP", "Supervisor", "CodSupervisor", "Cod_Supervisor", "SUPERVISOR"],
        contiene=["supervisor", "codsup"],
    )
    print(f"Columna vendedor detectada  : {cod_col!r}")
    print(f"Columna supervisor detectada: {sup_col!r}")

    if cod_col is None or sup_col is None:
        print("\nRESULTADO: NO CONCLUYENTE")
        print(
            "No se pudieron detectar de forma segura las columnas de vendedor/supervisor."
        )
        print(
            "La lista de columnas reales queda impresa arriba para ajustar la AU sin inferencias."
        )
        raise SystemExit(2)

    mv = mv.copy()
    mv["_cod"] = pd.to_numeric(mv[cod_col], errors="coerce").astype("Int64")
    mv["_sup"] = pd.to_numeric(mv[sup_col], errors="coerce").astype("Int64")
    print("\nUniverso detectado por supervisor:")
    for sup in SUPS:
        cods = sorted(
            mv.loc[mv["_sup"].eq(sup), "_cod"].dropna().astype(int).unique().tolist()
        )
        print(f"  SUP {sup}: vendedores={len(cods)} | codigos={cods}")

    titulo("2. TIENDA PERFECTA - PRUEBA REAL")
    tp_all = generar_business_rules_tp()
    detalle_all = tp_all.get("detalle_tp", tp_all.get("df_filtrado", pd.DataFrame()))
    cli_all = (
        detalle_all["Cliente_id"].nunique()
        if "Cliente_id" in detalle_all.columns
        else len(detalle_all)
    )
    print(f"TP TODOS | filas={len(detalle_all):,} | clientes={cli_all:,}")

    for sup in SUPS:
        cods = sorted(
            mv.loc[mv["_sup"].eq(sup), "_cod"].dropna().astype(int).unique().tolist()
        )
        tp_sup = generar_business_rules_tp(vendedores=cods)
        ds = tp_sup.get("detalle_tp", tp_sup.get("df_filtrado", pd.DataFrame()))
        clientes = ds["Cliente_id"].nunique() if "Cliente_id" in ds.columns else len(ds)
        cod_presentes = sorted(
            pd.to_numeric(
                ds.get("CodVendedor", pd.Series(dtype=float)), errors="coerce"
            )
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )
        fuera = sorted(set(cod_presentes) - set(cods))
        print(
            f"TP SUP {sup} | vendedores_esperados={len(cods)} | filas={len(ds):,} | clientes={clientes:,} | vendedores_fuera={fuera}"
        )

    titulo("3. COBERTURA - PRUEBA REAL")
    cob = obtener_base_cobertura(
        anio_op=anio,
        mes_op=mes,
        dia_matinal=dm.strftime("%Y-%m-%d"),
        dia_venta=dv.strftime("%Y-%m-%d"),
    )
    cartera = cob.get("cartera", pd.DataFrame()).copy()
    print(f"Cobertura TODOS | filas cartera={len(cartera):,}")
    print("Columnas reales de cartera relacionadas con vendedor/supervisor:")
    candidatas = [
        c
        for c in cartera.columns
        if any(x in normalizar_nombre(c) for x in ["vend", "sup", "supervisor"])
    ]
    for c in candidatas:
        print(f"  - {c}")

    cob_cod = detectar_columna(
        cartera,
        ["CodVendedor", "CodVend", "CodigoVendedor", "_join_vend", "IDVEND"],
        contiene=["codvend", "idvend", "joinvend"],
    )
    cob_sup = detectar_columna(
        cartera,
        ["SUP", "Supervisor", "SUPERVISOR", "CodSupervisor"],
        contiene=["supervisor", "codsup"],
    )
    print(f"Columna vendedor cobertura  : {cob_cod!r}")
    print(f"Columna supervisor cobertura: {cob_sup!r}")

    if cob_sup is not None:
        serie_sup = pd.to_numeric(cartera[cob_sup], errors="coerce").astype("Int64")
        for sup in SUPS:
            sub = cartera.loc[serie_sup.eq(sup)].copy()
            print(f"Cobertura SUP {sup} por columna {cob_sup} | filas={len(sub):,}")
    elif cob_cod is not None:
        serie_cod = pd.to_numeric(cartera[cob_cod], errors="coerce").astype("Int64")
        for sup in SUPS:
            cods = set(mv.loc[mv["_sup"].eq(sup), "_cod"].dropna().astype(int).tolist())
            sub = cartera.loc[serie_cod.isin(cods)].copy()
            print(f"Cobertura SUP {sup} por vendedores maestro | filas={len(sub):,}")
    else:
        print(
            "Cobertura: no se detecto columna segura para segmentar por supervisor ni vendedor."
        )

    titulo("4. VEREDICTO")
    print(
        "La AU termino correctamente. Use los universos impresos para contrastar TODOS vs SUP 60 vs SUP 70."
    )
    print("READ ONLY - Escrituras realizadas: NINGUNA")


if __name__ == "__main__":
    main()
