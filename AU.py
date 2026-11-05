from __future__ import annotations

"""AU MN 3 READ ONLY - origen exacto de Gross Total en Reporte Gerencial."""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "matinal.db"


def titulo(texto: str) -> None:
    print("\n" + "=" * 126)
    print(texto)
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
    if pd.isna(dm) or pd.isna(dv):
        raise RuntimeError("Dia Matinal o Dia Venta inválido")
    return (
        int(float(p["Año"])),
        int(float(p["Mes"])),
        pd.Timestamp(dm),
        pd.Timestamp(dv),
    )


def suma(df: pd.DataFrame, columna: str) -> float:
    if df is None or df.empty or columna not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[columna], errors="coerce").fillna(0).sum())


def main() -> None:
    titulo("AU MN 3 READ ONLY - ORIGEN DEL GROSS TOTAL EN GERENCIAL")
    print("Proyecto               :", ROOT)
    print("Base                   :", DB)
    print("Escrituras productivas : NINGUNA")
    anio, mes, dm, dv = parametros()
    print(
        f"Escenario              : Matinal={dm:%d/%m/%Y} | Venta={dv:%d/%m/%Y} | periodo={mes:02d}/{anio}"
    )

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from modules.business_rules.business_rules_gerencial import obtener_motor_gerencial
    from modules.business_rules.business_rules_mn import obtener_matriz_mn_comercial
    from modules.rep_gerencial_core import (
        construir_bloque_gross,
        construir_bloque_mn,
        obtener_motor_gerencial_base,
        construir_motor_gerencial_escenario,
    )

    filtros = {
        "anio": anio,
        "mes": mes,
        "dia_matinal": dm.strftime("%d/%m/%Y"),
        "dia_venta": dv.strftime("%d/%m/%Y"),
        "supervisor": "TODOS",
    }

    titulo("1. FUENTES PRODUCTIVAS INDEPENDIENTES")
    motor_br = obtener_motor_gerencial(anio, mes, filtros)
    gross_raw = motor_br["gross"].copy()
    mn_comercial = obtener_matriz_mn_comercial(anio, mes, filtros).copy()

    print("Gross BR filas         :", len(gross_raw))
    print("MN comercial filas     :", len(mn_comercial))
    print(
        "Gross operativo BR     :", f"${suma(gross_raw, 'Importe_Operativo_Arg'):,.2f}"
    )
    print("Ventas Totales MN      :", f"${suma(mn_comercial, 'Ventas_Totales'):,.2f}")
    print("Ventas MiNegocio MN    :", f"${suma(mn_comercial, 'Ventas_MiNegocio'):,.2f}")

    titulo("2. MOTOR BASE DE rep_gerencial_core")
    base = obtener_motor_gerencial_base(
        anio, mes, filtros["dia_matinal"], filtros["dia_venta"], "TODOS"
    )
    gross_base = base.get("gross_raw", pd.DataFrame()).copy()
    mn_base = base.get("mn", pd.DataFrame()).copy()

    print("Claves motor base      :", sorted(base.keys()))
    print("Gross raw base filas   :", len(gross_base))
    print("MN base filas          :", len(mn_base))
    print(
        "Gross operativo base   :", f"${suma(gross_base, 'Importe_Operativo_Arg'):,.2f}"
    )
    print("MN Ventas Totales base :", f"${suma(mn_base, 'Ventas_Totales'):,.2f}")
    print("MN Ventas App base     :", f"${suma(mn_base, 'Ventas_MiNegocio'):,.2f}")

    titulo("3. ESCENARIO QUE RECIBE EL RENDER")
    escenario = construir_motor_gerencial_escenario(base, "AJUSTADO", "TODOS")
    gross_render = escenario.get("gross", pd.DataFrame()).copy()
    mn_render = escenario.get("mn", pd.DataFrame()).copy()

    gross_operativo = suma(gross_render, "Importe_Operativo_Arg")
    mn_total = suma(mn_render, "Ventas_Totales")
    mn_app = suma(mn_render, "Ventas_MiNegocio")

    print("Gross render filas     :", len(gross_render))
    print("MN render filas        :", len(mn_render))
    print("Pestaña GROSS usa      : SUM(Importe_Operativo_Arg)")
    print("Gross Operativo render :", f"${gross_operativo:,.2f}")
    print("Pestaña MI NEGOCIO usa : SUM(Ventas_Totales)")
    print("Ventas Totales MN      :", f"${mn_total:,.2f}")
    print("Ventas MiNegocio       :", f"${mn_app:,.2f}")
    print(
        "Participación          :",
        f"{(mn_app / mn_total * 100 if mn_total else 0):,.4f}%",
    )

    titulo("4. TRAZABILIDAD DE TRANSFORMACIONES DEL REPORTE")
    gross_reconstruido = construir_bloque_gross(gross_raw, "AJUSTADO", "TODOS")
    mn_reconstruido = construir_bloque_mn(mn_comercial)
    print(
        "Gross antes bloque     :", f"${suma(gross_raw, 'Importe_Operativo_Arg'):,.2f}"
    )
    print(
        "Gross después bloque   :",
        f"${suma(gross_reconstruido, 'Importe_Operativo_Arg'):,.2f}",
    )
    print(
        "Delta bloque Gross     :",
        f"${suma(gross_reconstruido, 'Importe_Operativo_Arg') - suma(gross_raw, 'Importe_Operativo_Arg'):+,.2f}",
    )
    print("MN total antes bloque  :", f"${suma(mn_comercial, 'Ventas_Totales'):,.2f}")
    print(
        "MN total después bloque:", f"${suma(mn_reconstruido, 'Ventas_Totales'):,.2f}"
    )
    print(
        "Delta bloque MN        :",
        f"${suma(mn_reconstruido, 'Ventas_Totales') - suma(mn_comercial, 'Ventas_Totales'):+,.2f}",
    )

    titulo("5. DIFERENCIA ENTRE LOS DOS 'GROSS TOTAL'")
    diferencia = gross_operativo - mn_total
    print("Gross Operativo pestaña GROSS      :", f"${gross_operativo:,.2f}")
    print("Ventas Totales pestaña MI NEGOCIO  :", f"${mn_total:,.2f}")
    print("Diferencia                          :", f"${diferencia:+,.2f}")
    print("Gross MN digital                    :", f"${mn_app:,.2f}")

    titulo("6. CONTRATO DE COLUMNAS")
    print("Columnas Gross render:")
    print(list(gross_render.columns))
    print("\nColumnas MN render:")
    print(list(mn_render.columns))

    titulo("VEREDICTO AU MN 3")
    if abs(mn_total - suma(mn_comercial, "Ventas_Totales")) <= 0.01:
        print("RESULTADO: ORIGEN CONFIRMADO")
        print(
            "El Gross Total mostrado en la pestaña MI NEGOCIO proviene de business_rules_mn.Ventas_Totales."
        )
        print("No proviene del Gross Gerencial ni de Importe_Operativo_Arg.")
    else:
        print("RESULTADO: EXISTE UNA TRANSFORMACIÓN ADICIONAL EN EL REPORTE")
    print("READ ONLY - Escrituras productivas realizadas: NINGUNA")


if __name__ == "__main__":
    main()
