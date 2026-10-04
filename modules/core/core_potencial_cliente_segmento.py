import time
import pandas as pd
import numpy as np
from modules.staging import obtener_staging_vta
from modules.business_rules.business_rules_kilos import _asegurar_segmento_comercial


def generar_core_potencial_cliente_segmento(
    anio_operativo: int, mes_operativo: int
) -> pd.DataFrame:
    """
    CORE: Calcula el potencial de Cliente + Marca + SEGMENTO utilizando una ventana móvil de
    los últimos 3 meses completos anteriores al período operativo, conservando la
    multi-segmentación comercial sin aplicar filtros de segmento dominante.

    Arquitectura: CORE (Sistema Matinal 2.0)
    """
    t0 = time.perf_counter()

    columnas_salida = [
        "Cliente",
        "Marca",
        "SEGMENTO",
        "Kg_Mes_1",
        "Kg_Mes_2",
        "Kg_Mes_3",
        "PotencialKg",
        "Mes_Referencia_1",
        "Mes_Referencia_2",
        "Mes_Referencia_3",
    ]

    # 1. Obtener datos desde Staging VTA
    df_vta = obtener_staging_vta()
    if df_vta is None or df_vta.empty:
        return pd.DataFrame(columns=columnas_salida)

    # 2. Validaciones defensivas de columnas obligatorias en el contrato de entrada
    columnas_requeridas = ["Cliente", "Marca", "PesoKg"]
    for col_req in columnas_requeridas:
        if col_req not in df_vta.columns:
            return pd.DataFrame(columns=columnas_salida)

    df_trabajo = df_vta.copy()

    # 3. Asegurar la existencia de SEGMENTO utilizando la función institucional oficial[cite: 1]
    df_trabajo = _asegurar_segmento_comercial(df_trabajo)
    if "SEGMENTO" not in df_trabajo.columns:
        return pd.DataFrame(columns=columnas_salida)

    # 4. Aplicación de filtros institucionales
    # - Restricción exclusiva a Portafolio PEPSICO
    if "Proveedor" in df_trabajo.columns:
        df_trabajo = df_trabajo[
            df_trabajo["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    # - Exclusión de empleados (Subramo EMPLEADOS / EMPLOYEES)
    if "Subramo" in df_trabajo.columns:
        subramo_clean = (
            df_trabajo["Subramo"].fillna("").astype(str).str.strip().str.upper()
        )
        df_trabajo = df_trabajo[~subramo_clean.isin(["EMPLOYEES", "EMPLEADOS"])]

    # - Exclusión de comodatos, préstamos y devoluciones ficticias
    if "TipoDeVenta" in df_trabajo.columns:
        tipos_excluidos = [
            "Comodato Devolución",
            "Comodato Ficticio",
            "Comodato Ficticio Devolución",
            "Comodato Préstamo",
        ]
        df_trabajo = df_trabajo[
            ~df_trabajo["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)
        ]

    if df_trabajo.empty:
        return pd.DataFrame(columns=columnas_salida)

    # 5. Determinación de la ventana móvil de los 3 meses anteriores completos
    try:
        fecha_base = pd.Timestamp(
            year=int(anio_operativo), month=int(mes_operativo), day=1
        )
    except Exception:
        fecha_base = pd.Timestamp.now().normalize().replace(day=1)

    # Los 3 meses completos anteriores
    m3 = fecha_base - pd.DateOffset(months=1)
    m2 = fecha_base - pd.DateOffset(months=2)
    m1 = fecha_base - pd.DateOffset(months=3)

    meses_objetivo = [m1, m2, m3]
    meses_strs = [m.strftime("%Y-%m") for m in meses_objetivo]

    # Filtrar por FechaEntrega_dt (asegurando parseo robusto)
    if "FechaEntrega_dt" not in df_trabajo.columns:
        if "FechaEntrega" in df_trabajo.columns:
            df_trabajo["FechaEntrega_dt"] = pd.to_datetime(
                df_trabajo["FechaEntrega"], errors="coerce"
            )
        else:
            return pd.DataFrame(columns=columnas_salida)

    df_trabajo["AnioMes"] = (
        df_trabajo["FechaEntrega_dt"].dt.to_period("M").dt.to_timestamp()
    )

    # Filtrar transacciones dentro del rango de los 3 meses objetivo
    df_ventana = df_trabajo[df_trabajo["AnioMes"].isin(meses_objetivo)].copy()
    if df_ventana.empty:
        return pd.DataFrame(columns=columnas_salida)

    df_ventana["Cliente_Str"] = df_ventana["Cliente"].astype(str).str.strip()
    df_ventana["Marca_Str"] = (
        df_ventana["Marca"].fillna("").astype(str).str.strip().str.upper()
    )
    df_ventana["SEGMENTO_Str"] = (
        df_ventana["SEGMENTO"].fillna("SIN SEGMENTO").astype(str).str.strip()
    )
    df_ventana["PesoKg"] = pd.to_numeric(df_ventana["PesoKg"], errors="coerce").fillna(
        0.0
    )
    df_ventana["Periodo_Str"] = df_ventana["AnioMes"].dt.strftime("%Y-%m")

    # 6. Agrupar por Cliente, Marca, SEGMENTO y Mes de referencia sumando PesoKg
    agrupado = df_ventana.groupby(
        ["Cliente_Str", "Marca_Str", "SEGMENTO_Str", "Periodo_Str"], as_index=False
    )["PesoKg"].sum()

    # 7. Pivotear los 3 meses para obtener columnas de meses
    pivoteado = agrupado.pivot_table(
        index=["Cliente_Str", "Marca_Str", "SEGMENTO_Str"],
        columns="Periodo_Str",
        values="PesoKg",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()
    pivoteado.columns.name = None

    # Asegurar que existan las 3 columnas de meses en el pivote
    for i, m_str in enumerate(meses_strs, start=1):
        col_name = f"Kg_Mes_{i}"
        if m_str in pivoteado.columns:
            pivoteado[col_name] = pd.to_numeric(
                pivoteado[m_str], errors="coerce"
            ).fillna(0.0)
        else:
            pivoteado[col_name] = 0.0

    # 8. Cálculo del Potencial Kg (promedio simple de los 3 meses)
    pivoteado["PotencialKg"] = (
        pivoteado["Kg_Mes_1"] + pivoteado["Kg_Mes_2"] + pivoteado["Kg_Mes_3"]
    ) / 3.0

    # Asignación de etiquetas de referencia de meses
    pivoteado["Mes_Referencia_1"] = meses_strs[0]
    pivoteado["Mes_Referencia_2"] = meses_strs[1]
    pivoteado["Mes_Referencia_3"] = meses_strs[2]

    pivoteado = pivoteado.rename(
        columns={
            "Cliente_Str": "Cliente",
            "Marca_Str": "Marca",
            "SEGMENTO_Str": "SEGMENTO",
        }
    )

    resultado = pivoteado[columnas_salida].copy()

    print(
        f"[PERF_CORE] generar_core_potencial_cliente_segmento -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado
