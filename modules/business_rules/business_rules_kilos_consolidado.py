# modules/business_rules/business_rules_kilos_consolidado.py
import time

import pandas as pd
import streamlit as st

# Consumo exclusivo de BUSINESS_RULES_KILOS. No accede a DB, RAW, STAGING ni CORE.
from modules.business_rules.business_rules_kilos import obtener_matriz_kilos_comercial


MAPEO_SEGMENTOS_CONSOLIDADOS = {
    "GOLD SALTY": "PLAT_GOLD",
    "GOLD CRAKERS": "PLAT_GOLD",
    "GOLD CRACKERS": "PLAT_GOLD",
    "PLAT_GOLD SALTY": "PLAT_GOLD",
    "PLAT_GOLD CRAKERS": "PLAT_GOLD",
    "PLAT_GOLD CRACKERS": "PLAT_GOLD",
    "SILVER SALTY": "SILVER_BRZ",
    "SILVER CRAKERS": "SILVER_BRZ",
    "SILVER CRACKERS": "SILVER_BRZ",
    "SILVER CEREALS": "SILVER_BRZ",
    "SILVER_BRZ SALTY": "SILVER_BRZ",
    "SILVER_BRZ CRAKERS": "SILVER_BRZ",
    "SILVER_BRZ CRACKERS": "SILVER_BRZ",
    "SILVER_BRZ CEREALS": "SILVER_BRZ",
}

ORDEN_SEGMENTOS_CONSOLIDADOS = ["PLAT_GOLD", "SILVER_BRZ"]

COLUMNAS_CLAVE = ["CodVendedor", "Nombre", "SUP", "SEGMENTO"]

COLUMNAS_ADITIVAS = [
    "Objetivo Mes Corriente",
    "Arrastre",
    "Actual",
    "Ultima_Vta",
    "Penultima_Vta",
    "OPERATIVO",
    "Ajuste_Reemp_Arrastre",
    "Ajuste_Reemp_Actual",
    "Ajuste_Por_Reemp",
]

COLUMNAS_CALENDARIO = [
    "Días Pasados",
    "Rutas",
    "Ajuste_Entrega",
    "Rutas_Ajustadas",
    "Días Restantes",
    "Días Restantes Todo",
    "Días Restantes Ajustado",
]

COLUMNAS_DERIVADAS = [
    "Tendencia_Total_Kg",
    "Tendencia_Total_Kg_TODO",
    "Tendencia_Total_Kg_AJUSTADO",
    "Cumplimiento_Proyectado_Pct",
    "Cumplimiento_Proyectado_Pct_TODO",
    "Cumplimiento_Proyectado_Pct_AJUSTADO",
    "Promedio_Diario",
    "Promedio_Diario_TODO",
    "Promedio_Diario_AJUSTADO",
    "Media_Necesaria_Diaria",
    "Media_Necesaria_Diaria_TODO",
    "Media_Necesaria_Diaria_AJUSTADO",
]

COLUMNAS_SALIDA = [
    "CodVendedor",
    "Nombre",
    "SUP",
    "SEGMENTO",
    "Objetivo Mes Corriente",
    "Arrastre",
    "Actual",
    "Ultima_Vta",
    "Penultima_Vta",
    "OPERATIVO",
    "Ajuste_Reemp_Arrastre",
    "Ajuste_Reemp_Actual",
    "Ajuste_Por_Reemp",
    "Tendencia_Total_Kg",
    "Tendencia_Total_Kg_TODO",
    "Tendencia_Total_Kg_AJUSTADO",
    "Cumplimiento_Proyectado_Pct",
    "Cumplimiento_Proyectado_Pct_TODO",
    "Cumplimiento_Proyectado_Pct_AJUSTADO",
    "Promedio_Diario",
    "Promedio_Diario_TODO",
    "Promedio_Diario_AJUSTADO",
    "Media_Necesaria_Diaria",
    "Media_Necesaria_Diaria_TODO",
    "Media_Necesaria_Diaria_AJUSTADO",
    "Días Pasados",
    "Rutas",
    "Ajuste_Entrega",
    "Rutas_Ajustadas",
    "Días Restantes",
    "Días Restantes Todo",
    "Días Restantes Ajustado",
]


class BusinessRulesKilosConsolidadoError(RuntimeError):
    """Error de contrato o integridad del consolidado comercial de Kilos."""


def _normalizar_texto_segmento(serie: pd.Series) -> pd.Series:
    return (
        serie.astype("string")
        .fillna("")
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
    )


def _mapear_segmento_consolidado(serie: pd.Series) -> pd.Series:
    normalizado = _normalizar_texto_segmento(serie)
    return normalizado.map(MAPEO_SEGMENTOS_CONSOLIDADOS).astype("string")


def _validar_contrato_entrada(df: pd.DataFrame) -> None:
    requeridas = [
        "CodVendedor",
        "Nombre",
        "SUP",
        "SEGMENTO",
        *COLUMNAS_ADITIVAS,
        *COLUMNAS_CALENDARIO,
    ]
    faltantes = [columna for columna in requeridas if columna not in df.columns]
    if faltantes:
        raise BusinessRulesKilosConsolidadoError(
            "La matriz de business_rules_kilos no cumple el contrato requerido. "
            f"Columnas faltantes: {faltantes}."
        )


def _normalizar_matriz(df: pd.DataFrame) -> pd.DataFrame:
    trabajo = df.copy()
    trabajo["CodVendedor"] = pd.to_numeric(
        trabajo["CodVendedor"], errors="coerce"
    ).astype("Int64")
    trabajo["Nombre"] = trabajo["Nombre"].astype("string").fillna("").str.strip()
    trabajo["SUP"] = trabajo["SUP"].astype("string").fillna("").str.strip()
    trabajo["SEGMENTO_ORIGEN"] = _normalizar_texto_segmento(trabajo["SEGMENTO"])
    trabajo["SEGMENTO"] = _mapear_segmento_consolidado(trabajo["SEGMENTO"])

    for columna in COLUMNAS_ADITIVAS + COLUMNAS_CALENDARIO:
        trabajo[columna] = pd.to_numeric(trabajo[columna], errors="coerce")

    return trabajo


def _validar_segmentos_origen(df: pd.DataFrame) -> None:
    no_mapeados = sorted(
        df.loc[df["SEGMENTO"].isna(), "SEGMENTO_ORIGEN"]
        .dropna()
        .astype(str)
        .loc[lambda serie: serie.ne("")]
        .unique()
        .tolist()
    )
    if no_mapeados:
        raise BusinessRulesKilosConsolidadoError(
            f"Existen segmentos sin mapeo a PLAT_GOLD/SILVER_BRZ: {no_mapeados}."
        )


def _validar_consistencia_calendario(df: pd.DataFrame) -> None:
    """
    Las métricas de calendario pertenecen al vendedor, no al segmento.
    Exige un único valor no nulo por vendedor antes de consolidar.
    """
    errores = []
    for columna in COLUMNAS_CALENDARIO:
        conteos = (
            df.dropna(subset=[columna])
            .groupby("CodVendedor", dropna=False)[columna]
            .nunique(dropna=True)
        )
        vendedores_invalidos = conteos.loc[conteos.gt(1)].index.tolist()
        if vendedores_invalidos:
            errores.append(f"{columna}: vendedores={vendedores_invalidos[:20]}")

    if errores:
        raise BusinessRulesKilosConsolidadoError(
            "Las métricas de calendario no son constantes entre segmentos del "
            "mismo vendedor. " + " | ".join(errores)
        )


def _primer_valor_no_nulo(serie: pd.Series):
    valores = serie.dropna()
    return valores.iloc[0] if not valores.empty else pd.NA


def _consolidar_metricas_base(df: pd.DataFrame) -> pd.DataFrame:
    claves = ["CodVendedor", "Nombre", "SUP", "SEGMENTO"]

    aditivas = df.groupby(claves, dropna=False, as_index=False)[COLUMNAS_ADITIVAS].sum(
        min_count=1
    )

    calendario = df.groupby(claves, dropna=False, as_index=False)[
        COLUMNAS_CALENDARIO
    ].agg(_primer_valor_no_nulo)

    consolidado = aditivas.merge(
        calendario,
        on=claves,
        how="left",
        validate="one_to_one",
    )
    return consolidado


def _recalcular_escenario(
    df: pd.DataFrame,
    sufijo: str,
    columna_dias_restantes: str,
) -> pd.DataFrame:
    resultado = df.copy()

    dias_pasados = pd.to_numeric(resultado["Días Pasados"], errors="coerce").fillna(0.0)
    divisor_dias_pasados = dias_pasados.replace(0, 1.0)

    actual = pd.to_numeric(resultado["Actual"], errors="coerce").fillna(0.0)
    ajuste_actual = pd.to_numeric(
        resultado["Ajuste_Reemp_Actual"], errors="coerce"
    ).fillna(0.0)
    operativo = pd.to_numeric(resultado["OPERATIVO"], errors="coerce").fillna(0.0)
    objetivo = pd.to_numeric(
        resultado["Objetivo Mes Corriente"], errors="coerce"
    ).fillna(0.0)
    dias_restantes = pd.to_numeric(
        resultado[columna_dias_restantes], errors="coerce"
    ).fillna(0.0)

    promedio = (actual + ajuste_actual) / divisor_dias_pasados

    tendencia = operativo.copy()
    mascara_restantes = dias_restantes.gt(0)
    tendencia.loc[mascara_restantes] = (
        promedio.loc[mascara_restantes] * dias_restantes.loc[mascara_restantes]
        + operativo.loc[mascara_restantes]
    )

    cumplimiento = tendencia.div(objetivo.replace(0, pd.NA)).mul(100).fillna(0.0)

    media_necesaria = pd.Series(0.0, index=resultado.index, dtype="float64")
    media_necesaria.loc[mascara_restantes] = (
        (objetivo.loc[mascara_restantes] - operativo.loc[mascara_restantes])
        .div(dias_restantes.loc[mascara_restantes])
        .clip(lower=0)
    )

    resultado[f"Promedio_Diario{sufijo}"] = promedio
    resultado[f"Tendencia_Total_Kg{sufijo}"] = tendencia
    resultado[f"Cumplimiento_Proyectado_Pct{sufijo}"] = cumplimiento
    resultado[f"Media_Necesaria_Diaria{sufijo}"] = media_necesaria
    return resultado


def _recalcular_metricas_derivadas(df: pd.DataFrame) -> pd.DataFrame:
    resultado = _recalcular_escenario(
        df,
        sufijo="_TODO",
        columna_dias_restantes="Días Restantes Todo",
    )
    resultado = _recalcular_escenario(
        resultado,
        sufijo="_AJUSTADO",
        columna_dias_restantes="Días Restantes Ajustado",
    )

    # Mantiene el mismo contrato principal del reporte actual: AJUSTADO por defecto.
    resultado["Promedio_Diario"] = resultado["Promedio_Diario_AJUSTADO"]
    resultado["Tendencia_Total_Kg"] = resultado["Tendencia_Total_Kg_AJUSTADO"]
    resultado["Cumplimiento_Proyectado_Pct"] = resultado[
        "Cumplimiento_Proyectado_Pct_AJUSTADO"
    ]
    resultado["Media_Necesaria_Diaria"] = resultado["Media_Necesaria_Diaria_AJUSTADO"]
    resultado["Días Restantes"] = resultado["Días Restantes Ajustado"]
    return resultado


def _ordenar_resultado(df: pd.DataFrame) -> pd.DataFrame:
    resultado = df.copy()
    orden = {
        segmento: indice for indice, segmento in enumerate(ORDEN_SEGMENTOS_CONSOLIDADOS)
    }
    resultado["_orden_segmento"] = resultado["SEGMENTO"].map(orden).fillna(999)
    resultado = (
        resultado.sort_values(
            ["SUP", "Nombre", "CodVendedor", "_orden_segmento"],
            kind="stable",
        )
        .drop(columns=["_orden_segmento"])
        .reset_index(drop=True)
    )
    return resultado


def consolidar_matriz_kilos(
    matriz_comercial: pd.DataFrame,
) -> pd.DataFrame:
    """
    Consolida una matriz comercial ya calculada de cinco segmentos a dos.

    PLAT_GOLD = GOLD/PLAT_GOLD Salty + GOLD/PLAT_GOLD Crakers.
    SILVER_BRZ = SILVER/SILVER_BRZ Salty + Crakers + Cereals.

    Las métricas aditivas se suman. Las métricas derivadas se recalculan
    desde sus componentes consolidados. Las métricas de calendario se
    validan y se conservan una vez por vendedor.
    """
    if matriz_comercial is None or matriz_comercial.empty:
        return pd.DataFrame(columns=COLUMNAS_SALIDA)

    _validar_contrato_entrada(matriz_comercial)
    trabajo = _normalizar_matriz(matriz_comercial)
    _validar_segmentos_origen(trabajo)

    trabajo = trabajo.loc[trabajo["SEGMENTO"].notna()].copy()
    _validar_consistencia_calendario(trabajo)

    consolidado = _consolidar_metricas_base(trabajo)
    consolidado = _recalcular_metricas_derivadas(consolidado)
    consolidado = _ordenar_resultado(consolidado)

    for columna in COLUMNAS_SALIDA:
        if columna not in consolidado.columns:
            consolidado[columna] = 0.0

    resultado = consolidado[COLUMNAS_SALIDA].copy()

    duplicados = resultado.duplicated(
        subset=["CodVendedor", "SEGMENTO"],
        keep=False,
    )
    if duplicados.any():
        muestra = (
            resultado.loc[
                duplicados,
                ["CodVendedor", "SEGMENTO"],
            ]
            .head(20)
            .to_dict("records")
        )
        raise BusinessRulesKilosConsolidadoError(
            f"La matriz consolidada produjo claves duplicadas. Muestra={muestra}."
        )

    return resultado


@st.cache_data(show_spinner=False)
def obtener_matriz_kilos_consolidada(
    anio: int,
    mes: int,
    filtros_globales: dict,
) -> pd.DataFrame:
    """
    Punto de entrada oficial de BUSINESS_RULES_KILOS_CONSOLIDADO.

    Reutiliza íntegramente business_rules_kilos y transforma únicamente la
    segmentación comercial de cinco categorías a PLAT_GOLD y SILVER_BRZ.
    """
    t0 = time.perf_counter()

    matriz_detallada = obtener_matriz_kilos_comercial(
        int(anio),
        int(mes),
        filtros_globales,
    )
    resultado = consolidar_matriz_kilos(matriz_detallada)

    print(
        "[PERF_CORE] obtener_matriz_kilos_consolidada -> "
        f"{time.perf_counter() - t0:.4f} s | "
        f"filas_origen={len(matriz_detallada)} | "
        f"filas_consolidadas={len(resultado)}"
    )
    return resultado
