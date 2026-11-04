from __future__ import annotations

"""AU empirica READ ONLY - Batalla RyC vs CORE_RUTAS."""

import sqlite3
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "matinal.db"
TOL = 0.01
TIPO_RECHAZO = "DEVOLUCION POR RECHAZO"
TIPO_CANJE = "DEVOLUCION POR CANJE"


def titulo(t):
    print("\n" + "=" * 126)
    print(t)
    print("=" * 126)


def parametros():
    con = sqlite3.connect(DB.resolve().as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    try:
        print(
            "SQLite quick_check     :", con.execute("PRAGMA quick_check").fetchone()[0]
        )
        p = dict(con.execute("SELECT PARAMETRO, VALOR FROM parametros").fetchall())
    finally:
        con.close()
    dm = pd.to_datetime(p["Dia Matinal"], dayfirst=True, errors="coerce")
    dv = pd.to_datetime(p["Dia Venta"], dayfirst=True, errors="coerce")
    return (
        int(float(p["Año"])),
        int(float(p["Mes"])),
        pd.Timestamp(dm),
        pd.Timestamp(dv),
    )


def main():
    titulo("AU READ ONLY - BATALLA RYC vs CORE_RUTAS")
    print("Proyecto               :", ROOT)
    print("Base                   :", DB)
    print("Escrituras productivas : NINGUNA")
    anio, mes, dm, dv = parametros()
    print(
        f"Escenario              : Matinal={dm:%d/%m/%Y} | Venta={dv:%d/%m/%Y} | periodo={mes:02d}/{anio}"
    )

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from modules.business_rules.business_rules_ryc import obtener_business_rules_ryc
    from modules.core.core_rutas import obtener_core_rutas

    titulo("1. EJECUCION PRODUCTIVA")
    r = obtener_business_rules_ryc(
        anio,
        mes,
        dm.strftime("%d/%m/%Y"),
        dv.strftime("%d/%m/%Y"),
        modo_ajuste="AJUSTADO",
    )
    b = r["batalla"].copy()
    d = r["detalle"].copy()
    meta = r["metadata"]
    rutas = obtener_core_rutas().copy()
    print("Filas Batalla          :", len(b))
    print("Filas CORE_RUTAS       :", len(rutas))
    print("Contrato rutas metadata:", meta.get("core_rutas_batalla"))
    print("Clave día metadata     :", meta.get("clave_cliente_dia_visita"))

    errores = []
    if meta.get("core_rutas_batalla") != "CORE_RUTAS.obtener_core_rutas":
        errores.append("metadata CORE_RUTAS incorrecta")
    if meta.get("clave_cliente_dia_visita") != "Cliente + CodVendedor + Dia Matinal":
        errores.append("metadata clave cliente día incorrecta")

    titulo("2. RECONSTRUCCION INDEPENDIENTE Cliente_Dia_Visita")
    rutas["Cliente_E"] = pd.to_numeric(rutas["Cliente"], errors="coerce").astype(
        "Int64"
    )
    rutas["Vendedor_E"] = pd.to_numeric(rutas["CodVendedor"], errors="coerce").astype(
        "Int64"
    )
    rutas["Fecha_E"] = pd.to_datetime(
        rutas["FechaRuta"], errors="coerce"
    ).dt.normalize()
    claves_dia = set(
        rutas.loc[rutas["Fecha_E"].eq(dm.normalize()), ["Cliente_E", "Vendedor_E"]]
        .dropna()
        .itertuples(index=False, name=None)
    )
    cliente_b = pd.to_numeric(b["Cliente"], errors="coerce").astype("Int64")
    vendedor_b = pd.to_numeric(b["CodVendedor"], errors="coerce").astype("Int64")
    esperado_flag = pd.Series(
        [
            (c, v) in claves_dia if pd.notna(c) and pd.notna(v) else False
            for c, v in zip(cliente_b, vendedor_b)
        ],
        index=b.index,
        dtype=bool,
    )
    real_flag = b["Cliente_Dia_Visita"].fillna(False).astype(bool)
    diferencias_flag = int(real_flag.ne(esperado_flag).sum())
    print("Claves CORE_RUTAS día  :", len(claves_dia))
    print("True Batalla           :", int(real_flag.sum()))
    print("True esperado          :", int(esperado_flag.sum()))
    print("Diferencias flag       :", diferencias_flag)
    if diferencias_flag:
        errores.append(
            "Cliente_Dia_Visita no concilia con Cliente+Vendedor+Día Matinal"
        )

    titulo("3. INTEGRIDAD BATALLA")
    rech = d["TipoDeVentaNorm"].eq(TIPO_RECHAZO)
    camb = d["TipoDeVentaNorm"].eq(TIPO_CANJE) & ~d["Excluir_Cambio_Innovacion"].fillna(
        False
    )
    esperado = d.loc[rech | camb].copy()
    esperado["Importe_E"] = (
        pd.to_numeric(esperado["ImporteNetoItem"], errors="coerce").fillna(0).abs()
    )
    idx_camb = esperado["TipoDeVentaNorm"].eq(TIPO_CANJE)
    esperado.loc[idx_camb, "Importe_E"] = pd.to_numeric(
        esperado.loc[idx_camb, "ValorCambioComputable"], errors="coerce"
    ).fillna(0)
    imp_b = float(pd.to_numeric(b["Importe"], errors="coerce").fillna(0).sum())
    imp_e = float(esperado["Importe_E"].sum())
    print("Filas Batalla          :", len(b))
    print("Filas esperadas        :", len(esperado))
    print("Importe Batalla total  :", f"{imp_b:,.2f}")
    print("Importe esperado total :", f"{imp_e:,.2f}")
    print("Código nulo            :", int(b["Codigo"].isna().sum()))
    print("Cliente nulo           :", int(b["Cliente"].isna().sum()))
    print("Vendedor 20            :", int(vendedor_b.eq(20).sum()))
    if len(b) != len(esperado):
        errores.append("filas Batalla no concilian")
    if abs(imp_b - imp_e) > TOL:
        errores.append("importe Batalla no concilia")
    if b["Codigo"].isna().any():
        errores.append("Código nulo en Batalla")
    if b["Cliente"].isna().any():
        errores.append("Cliente nulo en Batalla")
    if vendedor_b.eq(20).any():
        errores.append("Vendedor 20 presente")

    titulo("4. MUESTRA CLIENTES DEL DIA")
    muestra = b.loc[
        real_flag,
        [
            "Cliente",
            "Razon_Social",
            "Fecha",
            "Codigo",
            "CodVendedor",
            "Nombre",
            "DiaVisita",
            "Cliente_Dia_Visita",
        ],
    ].head(30)
    print(
        muestra.to_string(index=False)
        if not muestra.empty
        else "Sin operaciones RyC de clientes programados para el Día Matinal."
    )

    titulo("VEREDICTO")
    if errores:
        print("RESULTADO: NO APROBADO")
        for e in errores:
            print("-", e)
        raise SystemExit(1)
    print("RESULTADO: APROBADO")
    print(
        "BATALLA RYC concilia contra CORE_RUTAS usando Cliente + CodVendedor + Día Matinal."
    )
    print("READ ONLY - Escrituras realizadas: NINGUNA")


if __name__ == "__main__":
    main()
