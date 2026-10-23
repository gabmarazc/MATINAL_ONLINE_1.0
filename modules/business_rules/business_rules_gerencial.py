# modules/business_rules/business_rules_gerencial.py

import time

import numpy as np
import pandas as pd
import streamlit as st

from modules.core.core_operaciones import obtener_core_operacion
from modules.core.core_vendedores import obtener_core_vendedores
from modules.staging import obtener_staging_maestros


SEGMENTOS_ORDEN = [
    "GOLD Salty",
    "GOLD Crakers",
    "SILVER Salty",
    "SILVER Crakers",
    "SILVER Cereals",
]

TIPOS_VENTA_EXCLUIDOS = [
    "Comodato Devolución",
    "Comodato Ficticio",
    "Comodato Ficticio Devolución",
    "Comodato Préstamo",
]


def _filtrar_universo_gerencial(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica el universo institucional PEPSICO sin alterar la titularidad original."""
    if df is None or df.empty:
        return pd.DataFrame()

    resultado = df.copy()

    if "Proveedor" in resultado.columns:
        resultado = resultado[
            resultado["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ].copy()

    if "TipoDeVenta" in resultado.columns:
        resultado = resultado[
            ~resultado["TipoDeVenta"]
            .fillna("")
            .astype(str)
            .str.strip()
            .isin(TIPOS_VENTA_EXCLUIDOS)
        ].copy()

    return resultado


def _asegurar_segmento_gerencial(df: pd.DataFrame) -> pd.DataFrame:
    """Construye SEGMENTO desde SegmentoRentabilidad y Rubro cuando sea necesario."""
    if df is None or df.empty:
        return pd.DataFrame()

    resultado = df.copy()

    if "SEGMENTO" not in resultado.columns or resultado["SEGMENTO"].isna().all():
        segmento_rentabilidad = (
            resultado["SegmentoRentabilidad"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.title()
            if "SegmentoRentabilidad" in resultado.columns
            else pd.Series("", index=resultado.index, dtype="string")
        )
        rubro = (
            resultado["Rubro"].fillna("").astype(str).str.strip()
            if "Rubro" in resultado.columns
            else pd.Series("", index=resultado.index, dtype="string")
        )

        condicion_gold = segmento_rentabilidad.isin(["Platinum", "Gold"])
        condicion_silver = segmento_rentabilidad.isin(["Silver", "Bronze"])

        resultado["SEGMENTO"] = np.select(
            [condicion_gold, condicion_silver],
            [("GOLD " + rubro).str.strip(), ("SILVER " + rubro).str.strip()],
            default=None,
        )

    resultado["SEGMENTO"] = resultado["SEGMENTO"].fillna("").astype(str).str.strip()
    return resultado


def _obtener_contexto_gerencial(
    anio: int,
    mes: int,
    filtros_globales: dict,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Obtiene padrón gerencial, ventas por titular y mapas de calendario."""
    padron = obtener_core_vendedores(incluir_vendedor_20=True)
    if padron is None or padron.empty:
        return pd.DataFrame(), pd.DataFrame(), {}

    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026")
    dia_venta = filtros_globales.get("dia_venta", "01/09/2026")

    datos_core = obtener_core_operacion(
        anio,
        mes,
        dia_matinal,
        dia_venta,
        modo_ajuste="AJUSTADO",
    )

    ventas_titular = datos_core.get("df_vta_titular", pd.DataFrame()).copy()
    if ventas_titular.empty:
        return padron, pd.DataFrame(), datos_core

    ventas_titular = _filtrar_universo_gerencial(ventas_titular)
    ventas_titular = _asegurar_segmento_gerencial(ventas_titular)

    ventas_titular["CodVendedor"] = pd.to_numeric(
        ventas_titular.get("CodVendedor"), errors="coerce"
    ).astype("Int64")

    codigos_validos = set(padron["CodVendedor"].dropna().astype("Int64").tolist())
    ventas_titular = ventas_titular[
        ventas_titular["CodVendedor"].isin(codigos_validos)
    ].copy()

    return padron, ventas_titular, datos_core


def _construir_matriz_base(
    padron: pd.DataFrame,
    ventas: pd.DataFrame,
) -> pd.DataFrame:
    """Construye el producto cartesiano padrón gerencial por segmentos."""
    segmentos = list(SEGMENTOS_ORDEN)
    if not ventas.empty and "SEGMENTO" in ventas.columns:
        for segmento in ventas["SEGMENTO"].dropna().astype(str).str.strip().unique():
            if segmento and segmento not in segmentos:
                segmentos.append(segmento)

    padron_base = padron[
        ["CodVendedor", "Nombre", "SUP", "Ajuste_Entrega", "Rutas_Ajustadas"]
    ].copy()
    padron_base["_k"] = 1
    segmentos_df = pd.DataFrame({"SEGMENTO": segmentos, "_k": 1})
    return padron_base.merge(segmentos_df, on="_k", how="inner").drop(columns="_k")


def _incorporar_calendario(
    matriz: pd.DataFrame,
    datos_core: dict,
) -> pd.DataFrame:
    """Incorpora rutas y días de los escenarios TODO y AJUSTADO."""
    df = matriz.copy()

    mapas = {
        "Días Pasados": datos_core.get("dias_pasados_map", {}),
        "Rutas": datos_core.get("rutas_totales_map", {}),
        "Días Restantes Todo": datos_core.get("dias_restantes_todo_map", {}),
        "Días Restantes Ajustado": datos_core.get("dias_restantes_ajustado_map", {}),
    }

    for columna, mapa in mapas.items():
        df[columna] = df["CodVendedor"].map(mapa).fillna(0).astype("Int64")

    df["Días Restantes"] = df["Días Restantes Ajustado"]
    return df


def _calcular_escenarios(
    matriz: pd.DataFrame,
    columna_objetivo: str,
    columna_operativo: str,
    prefijo_tendencia: str,
    prefijo_cumplimiento: str,
) -> pd.DataFrame:
    """Calcula TODO y AJUSTADO desde venta titular, sin compensaciones por reemplazo."""
    df = matriz.copy()
    if df.empty:
        return df

    dias_pasados = (
        pd.to_numeric(df["Días Pasados"], errors="coerce").fillna(0).astype(float)
    )
    divisor = dias_pasados.replace(0, 1.0)
    actual = pd.to_numeric(df["Actual"], errors="coerce").fillna(0.0)
    operativo = pd.to_numeric(df[columna_operativo], errors="coerce").fillna(0.0)
    objetivo = pd.to_numeric(df[columna_objetivo], errors="coerce").fillna(0.0)
    promedio_diario = actual / divisor

    for sufijo, columna_dias in [
        ("TODO", "Días Restantes Todo"),
        ("AJUSTADO", "Días Restantes Ajustado"),
    ]:
        dias_restantes = (
            pd.to_numeric(df[columna_dias], errors="coerce").fillna(0).astype(float)
        )

        tendencia = operativo.copy()
        mascara = dias_restantes > 0
        tendencia.loc[mascara] = (
            operativo.loc[mascara]
            + promedio_diario.loc[mascara] * dias_restantes.loc[mascara]
        )

        media_necesaria = pd.Series(0.0, index=df.index)
        media_necesaria.loc[mascara] = (
            (objetivo.loc[mascara] - operativo.loc[mascara])
            / dias_restantes.loc[mascara]
        ).clip(lower=0)

        df[f"Promedio_Diario_{sufijo}"] = promedio_diario
        df[f"{prefijo_tendencia}_{sufijo}"] = tendencia
        df[f"{prefijo_cumplimiento}_{sufijo}"] = (
            tendencia.div(objetivo.replace(0, pd.NA)).mul(100).fillna(0.0)
        )
        df[f"Media_Necesaria_Diaria_{sufijo}"] = media_necesaria

    df["Promedio_Diario"] = df["Promedio_Diario_AJUSTADO"]
    df[prefijo_tendencia] = df[f"{prefijo_tendencia}_AJUSTADO"]
    df[prefijo_cumplimiento] = df[f"{prefijo_cumplimiento}_AJUSTADO"]
    df["Media_Necesaria_Diaria"] = df["Media_Necesaria_Diaria_AJUSTADO"]
    return df


def _calcular_objetivos_kilos_gerencial(
    anio: int,
    mes: int,
    ventas: pd.DataFrame,
    padron: pd.DataFrame,
) -> pd.DataFrame:
    """Distribuye en Gerencial el objetivo corporativo de Kilos cargado en CEBE.

    La fuente es maestro_marcas_cebe[Obj_TN_Mes]. El objetivo de cada marca se
    distribuye entre vendedor y segmento según la participación observada de
    PesoKg en las ventas titulares de Arrastre y Actual.
    """
    columnas_salida = ["CodVendedor", "SEGMENTO", "Objetivo Mes Corriente"]

    maestros = obtener_staging_maestros()
    maestro_cebe = (
        maestros.get("maestro_marcas_cebe", pd.DataFrame())
        if isinstance(maestros, dict)
        else pd.DataFrame()
    )
    if maestro_cebe.empty or ventas is None or ventas.empty or padron.empty:
        return pd.DataFrame(columns=columnas_salida)

    if "Anio" in maestro_cebe.columns and "Mes" in maestro_cebe.columns:
        maestro_cebe = maestro_cebe[
            (maestro_cebe["Anio"].astype(str) == str(anio))
            & (maestro_cebe["Mes"].astype(str) == str(mes))
        ].copy()

    col_marca_maestro = next(
        (c for c in maestro_cebe.columns if str(c).strip().lower() == "marca"),
        None,
    )
    col_objetivo = next(
        (
            c
            for c in maestro_cebe.columns
            if str(c).strip().lower() in ["obj_tn_mes", "obj_tn", "objetivo_tn_mes"]
        ),
        None,
    )
    col_marca_ventas = next(
        (c for c in ["Marca", "MARCA"] if c in ventas.columns),
        None,
    )

    if col_marca_maestro is None or col_objetivo is None or col_marca_ventas is None:
        raise ValueError(
            "No se pudo construir el objetivo corporativo de Kilos Gerencial: "
            "faltan Marca y/o Obj_TN_Mes en maestro_marcas_cebe, o Marca en ventas."
        )

    mc = maestro_cebe.copy()
    mc["Marca_Key"] = (
        mc[col_marca_maestro].fillna("").astype(str).str.strip().str.upper()
    )
    mc["Objetivo_Marca_Kg"] = pd.to_numeric(mc[col_objetivo], errors="coerce").fillna(
        0.0
    )
    objetivos_marca = (
        mc[mc["Marca_Key"].ne("")]
        .groupby("Marca_Key", as_index=False)["Objetivo_Marca_Kg"]
        .sum()
    )
    mapa_objetivos = objetivos_marca.set_index("Marca_Key")[
        "Objetivo_Marca_Kg"
    ].to_dict()

    df = ventas.copy()
    columnas_ventas_requeridas = ["CodVendedor", "SEGMENTO", "Periodo"]
    faltantes_ventas = [
        columna for columna in columnas_ventas_requeridas if columna not in df.columns
    ]
    if faltantes_ventas:
        raise ValueError(
            "No se pudo distribuir el objetivo corporativo de Kilos Gerencial. "
            "Faltan columnas en ventas: " + ", ".join(faltantes_ventas)
        )

    df["Marca_Key"] = (
        df[col_marca_ventas].fillna("").astype(str).str.strip().str.upper()
    )
    df["PesoKg"] = pd.to_numeric(df.get("PesoKg", 0.0), errors="coerce").fillna(0.0)
    df["CodVendedor"] = pd.to_numeric(df["CodVendedor"], errors="coerce").astype(
        "Int64"
    )
    df["SEGMENTO"] = df["SEGMENTO"].fillna("").astype(str).str.strip()

    codigos_validos = set(padron["CodVendedor"].dropna().astype("Int64").tolist())
    df = df[
        df["CodVendedor"].isin(codigos_validos)
        & df["Marca_Key"].ne("")
        & df["SEGMENTO"].ne("")
        & df["Periodo"].isin(["Arrastre", "Actual"])
    ].copy()

    if df.empty:
        return pd.DataFrame(columns=columnas_salida)

    participacion = df.groupby(
        ["CodVendedor", "Marca_Key", "SEGMENTO"],
        as_index=False,
    )["PesoKg"].sum()
    participacion["Total_Marca_Kg"] = (
        participacion.groupby("Marca_Key")["PesoKg"].transform("sum").replace(0, pd.NA)
    )
    participacion["Participacion_Marca"] = (
        participacion["PesoKg"].div(participacion["Total_Marca_Kg"]).fillna(0.0)
    )
    participacion["Objetivo Mes Corriente"] = (
        participacion["Marca_Key"].map(mapa_objetivos).fillna(0.0)
        * participacion["Participacion_Marca"]
    )

    resultado = participacion.groupby(
        ["CodVendedor", "SEGMENTO"],
        as_index=False,
    )["Objetivo Mes Corriente"].sum()

    marcas_con_actividad = set(participacion["Marca_Key"].unique().tolist())
    objetivo_distribuible = float(
        objetivos_marca[objetivos_marca["Marca_Key"].isin(marcas_con_actividad)][
            "Objetivo_Marca_Kg"
        ].sum()
    )
    objetivo_asignado = float(resultado["Objetivo Mes Corriente"].sum())
    if abs(objetivo_distribuible - objetivo_asignado) >= 1e-6:
        raise AssertionError(
            "Error de integridad en objetivo corporativo de Kilos Gerencial: "
            f"objetivo CEBE distribuible={objetivo_distribuible} y "
            f"objetivo asignado={objetivo_asignado}."
        )

    return resultado[columnas_salida]


def _calcular_objetivos_gross_gerencial(
    anio: int,
    mes: int,
    ventas: pd.DataFrame,
    padron: pd.DataFrame,
) -> pd.DataFrame:
    """Distribuye el objetivo Gross por marca, vendedor titular y segmento."""
    maestros = obtener_staging_maestros()
    maestro_cebe = (
        maestros.get("maestro_marcas_cebe", pd.DataFrame())
        if isinstance(maestros, dict)
        else pd.DataFrame()
    )
    if maestro_cebe.empty or ventas.empty:
        return pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Objetivo_Importe_Arg"])

    if "Anio" in maestro_cebe.columns and "Mes" in maestro_cebe.columns:
        maestro_cebe = maestro_cebe[
            (maestro_cebe["Anio"].astype(str) == str(anio))
            & (maestro_cebe["Mes"].astype(str) == str(mes))
        ].copy()

    col_marca_maestro = next(
        (c for c in maestro_cebe.columns if "marca" in str(c).strip().lower()),
        None,
    )
    col_objetivo = next(
        (
            c
            for c in maestro_cebe.columns
            if str(c).strip().lower() in ["obj_gross_mes", "obj_gross", "gross"]
        ),
        None,
    )
    col_marca_ventas = next(
        (c for c in ["Marca", "MARCA"] if c in ventas.columns), None
    )

    if col_marca_maestro is None or col_objetivo is None or col_marca_ventas is None:
        raise ValueError(
            "No se pudo construir el objetivo Gross gerencial por falta de columnas."
        )

    mc = maestro_cebe.copy()
    mc["Marca_Key"] = (
        mc[col_marca_maestro].fillna("").astype(str).str.strip().str.upper()
    )
    mc["Objetivo_Marca"] = pd.to_numeric(mc[col_objetivo], errors="coerce").fillna(0.0)
    mapa_objetivos = mc.groupby("Marca_Key")["Objetivo_Marca"].sum().to_dict()

    df = ventas.copy()
    df["Marca_Key"] = (
        df[col_marca_ventas].fillna("").astype(str).str.strip().str.upper()
    )
    df["PesoKg"] = pd.to_numeric(df.get("PesoKg", 0.0), errors="coerce").fillna(0.0)
    codigos = set(padron["CodVendedor"].dropna().astype("Int64").tolist())
    df = df[
        df["CodVendedor"].isin(codigos)
        & df["SEGMENTO"].ne("")
        & df["Periodo"].isin(["Arrastre", "Actual"])
    ].copy()

    participacion = df.groupby(
        ["CodVendedor", "Marca_Key", "SEGMENTO"], as_index=False
    )["PesoKg"].sum()
    participacion["Total_Marca"] = (
        participacion.groupby("Marca_Key")["PesoKg"].transform("sum").replace(0, pd.NA)
    )
    participacion["Participacion"] = (
        participacion["PesoKg"].div(participacion["Total_Marca"]).fillna(0.0)
    )
    participacion["Objetivo_Importe_Arg"] = (
        participacion["Marca_Key"].map(mapa_objetivos).fillna(0.0)
        * participacion["Participacion"]
    )

    return participacion.groupby(["CodVendedor", "SEGMENTO"], as_index=False)[
        "Objetivo_Importe_Arg"
    ].sum()


def _ordenar_matriz(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    orden = {segmento: indice for indice, segmento in enumerate(SEGMENTOS_ORDEN)}
    resultado = df.copy()
    resultado["_orden_segmento"] = resultado["SEGMENTO"].map(orden).fillna(999)
    return (
        resultado.sort_values(["SUP", "Nombre", "CodVendedor", "_orden_segmento"])
        .drop(columns="_orden_segmento")
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner=False)
def obtener_matriz_gerencial_kilos(
    anio: int,
    mes: int,
    filtros_globales: dict,
) -> pd.DataFrame:
    """Construye Kilos Gerencial por titular, sin ausencias ni reemplazos e incluyendo vendedor 20."""
    t0 = time.perf_counter()
    padron, ventas, datos_core = _obtener_contexto_gerencial(
        anio, mes, filtros_globales
    )
    if padron.empty or ventas.empty:
        return pd.DataFrame()

    periodo = ventas[
        ventas["Periodo"].isin(["Arrastre", "Actual"]) & ventas["SEGMENTO"].ne("")
    ].copy()
    periodo["PesoKg"] = pd.to_numeric(
        periodo.get("PesoKg", 0.0), errors="coerce"
    ).fillna(0.0)

    agrupado = periodo.groupby(["CodVendedor", "SEGMENTO", "Periodo"], as_index=False)[
        "PesoKg"
    ].sum()
    pivot = agrupado.pivot_table(
        index=["CodVendedor", "SEGMENTO"],
        columns="Periodo",
        values="PesoKg",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()
    pivot.columns.name = None
    for columna in ["Arrastre", "Actual"]:
        if columna not in pivot.columns:
            pivot[columna] = 0.0

    matriz = _construir_matriz_base(padron, ventas)
    matriz = matriz.merge(
        pivot[["CodVendedor", "SEGMENTO", "Arrastre", "Actual"]],
        on=["CodVendedor", "SEGMENTO"],
        how="left",
    )
    matriz[["Arrastre", "Actual"]] = matriz[["Arrastre", "Actual"]].fillna(0.0)

    objetivos = _calcular_objetivos_kilos_gerencial(anio, mes, ventas, padron)
    matriz = matriz.merge(objetivos, on=["CodVendedor", "SEGMENTO"], how="left")
    matriz["Objetivo Mes Corriente"] = matriz["Objetivo Mes Corriente"].fillna(0.0)

    matriz["Ajuste_Reemp_Arrastre"] = 0.0
    matriz["Ajuste_Reemp_Actual"] = 0.0
    matriz["Ajuste_Por_Reemp"] = 0.0
    matriz["OPERATIVO"] = matriz["Arrastre"] + matriz["Actual"]

    matriz = _incorporar_calendario(matriz, datos_core)
    matriz = _calcular_escenarios(
        matriz,
        "Objetivo Mes Corriente",
        "OPERATIVO",
        "Tendencia_Total_Kg",
        "Cumplimiento_Proyectado_Pct",
    )

    columnas = [
        "CodVendedor",
        "Nombre",
        "SUP",
        "SEGMENTO",
        "Objetivo Mes Corriente",
        "Arrastre",
        "Actual",
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
    resultado = _ordenar_matriz(matriz[[c for c in columnas if c in matriz.columns]])
    print(
        f"[PERF_CORE] obtener_matriz_gerencial_kilos -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado


@st.cache_data(show_spinner=False)
def obtener_matriz_gerencial_gross(
    anio: int,
    mes: int,
    filtros_globales: dict,
) -> pd.DataFrame:
    """Construye Gross Gerencial valorizando los kilos proyectados por segmento."""
    t0 = time.perf_counter()
    padron, ventas, datos_core = _obtener_contexto_gerencial(
        anio, mes, filtros_globales
    )
    if padron.empty or ventas.empty:
        return pd.DataFrame()

    periodo = ventas[
        ventas["Periodo"].isin(["Arrastre", "Actual"]) & ventas["SEGMENTO"].ne("")
    ].copy()
    periodo["ImporteNetoItem"] = pd.to_numeric(
        periodo.get("ImporteNetoItem", 0.0), errors="coerce"
    ).fillna(0.0)

    agrupado = periodo.groupby(["CodVendedor", "SEGMENTO", "Periodo"], as_index=False)[
        "ImporteNetoItem"
    ].sum()
    pivot = agrupado.pivot_table(
        index=["CodVendedor", "SEGMENTO"],
        columns="Periodo",
        values="ImporteNetoItem",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()
    pivot.columns.name = None
    for columna in ["Arrastre", "Actual"]:
        if columna not in pivot.columns:
            pivot[columna] = 0.0

    matriz = _construir_matriz_base(padron, ventas)
    matriz = matriz.merge(
        pivot[["CodVendedor", "SEGMENTO", "Arrastre", "Actual"]],
        on=["CodVendedor", "SEGMENTO"],
        how="left",
    )
    matriz[["Arrastre", "Actual"]] = matriz[["Arrastre", "Actual"]].fillna(0.0)

    objetivos = _calcular_objetivos_gross_gerencial(anio, mes, ventas, padron)
    matriz = matriz.merge(objetivos, on=["CodVendedor", "SEGMENTO"], how="left")
    matriz["Objetivo_Importe_Arg"] = matriz["Objetivo_Importe_Arg"].fillna(0.0)

    matriz["Ajuste_Reemp_Arrastre"] = 0.0
    matriz["Ajuste_Reemp_Actual"] = 0.0
    matriz["Ajuste_Por_Reemp"] = 0.0
    matriz["OPERATIVO"] = matriz["Arrastre"] + matriz["Actual"]
    matriz["Importe_Operativo_Arg"] = matriz["OPERATIVO"]
    matriz = _incorporar_calendario(matriz, datos_core)

    # La proyección monetaria se deriva de la matriz de Kilos Gerencial.
    kilos = obtener_matriz_gerencial_kilos(anio, mes, filtros_globales)
    columnas_kilos_requeridas = [
        "CodVendedor",
        "SEGMENTO",
        "OPERATIVO",
        "Tendencia_Total_Kg_TODO",
        "Tendencia_Total_Kg_AJUSTADO",
        "Promedio_Diario_TODO",
        "Promedio_Diario_AJUSTADO",
    ]
    faltantes_kilos = [
        columna for columna in columnas_kilos_requeridas if columna not in kilos.columns
    ]
    if faltantes_kilos:
        raise ValueError(
            "La matriz de Kilos Gerencial no contiene las columnas requeridas "
            "para proyectar Gross: " + ", ".join(faltantes_kilos)
        )

    kilos_ref = (
        kilos[columnas_kilos_requeridas]
        .copy()
        .rename(
            columns={
                "OPERATIVO": "Kilos_Operativos",
                "Tendencia_Total_Kg_TODO": "Kilos_Proyectados_TODO",
                "Tendencia_Total_Kg_AJUSTADO": "Kilos_Proyectados_AJUSTADO",
                "Promedio_Diario_TODO": "Kilos_Promedio_Diario_TODO",
                "Promedio_Diario_AJUSTADO": "Kilos_Promedio_Diario_AJUSTADO",
            }
        )
    )
    matriz = matriz.merge(
        kilos_ref,
        on=["CodVendedor", "SEGMENTO"],
        how="left",
    )

    columnas_numericas_kilos = [
        "Kilos_Operativos",
        "Kilos_Proyectados_TODO",
        "Kilos_Proyectados_AJUSTADO",
        "Kilos_Promedio_Diario_TODO",
        "Kilos_Promedio_Diario_AJUSTADO",
    ]
    for columna in columnas_numericas_kilos:
        matriz[columna] = pd.to_numeric(matriz[columna], errors="coerce").fillna(0.0)

    # Valor medio ponderado por kilo: suma de Gross operativo / suma de Kg operativo.
    valor_segmento = matriz.groupby("SEGMENTO", as_index=False).agg(
        Gross_Operativo_Segmento=("Importe_Operativo_Arg", "sum"),
        Kilos_Operativos_Segmento=("Kilos_Operativos", "sum"),
    )
    valor_segmento["Valor_Promedio_Kg_Segmento"] = valor_segmento[
        "Gross_Operativo_Segmento"
    ].div(valor_segmento["Kilos_Operativos_Segmento"].replace(0, pd.NA))

    gross_operativo_global = float(matriz["Importe_Operativo_Arg"].sum())
    kilos_operativos_global = float(matriz["Kilos_Operativos"].sum())
    valor_kg_global = (
        gross_operativo_global / kilos_operativos_global
        if kilos_operativos_global > 0
        else pd.NA
    )

    valor_segmento["Valor_Promedio_Kg_Arg"] = valor_segmento[
        "Valor_Promedio_Kg_Segmento"
    ].fillna(valor_kg_global)
    valor_segmento["Fuente_Valor_Kg"] = np.select(
        [
            valor_segmento["Kilos_Operativos_Segmento"] > 0,
            valor_segmento["Valor_Promedio_Kg_Arg"].notna(),
        ],
        ["SEGMENTO", "GLOBAL"],
        default="NO_CALCULABLE",
    )

    matriz = matriz.merge(
        valor_segmento[["SEGMENTO", "Valor_Promedio_Kg_Arg", "Fuente_Valor_Kg"]],
        on="SEGMENTO",
        how="left",
    )

    valor_kg = pd.to_numeric(matriz["Valor_Promedio_Kg_Arg"], errors="coerce")
    objetivo = pd.to_numeric(matriz["Objetivo_Importe_Arg"], errors="coerce").fillna(
        0.0
    )
    operativo = pd.to_numeric(matriz["Importe_Operativo_Arg"], errors="coerce").fillna(
        0.0
    )

    for sufijo, columna_dias in [
        ("TODO", "Días Restantes Todo"),
        ("AJUSTADO", "Días Restantes Ajustado"),
    ]:
        matriz[f"Gross_Proyectado_Arg_{sufijo}"] = (
            matriz[f"Kilos_Proyectados_{sufijo}"] * valor_kg
        )
        matriz[f"Cumplimiento_Gross_Proy_Pct_{sufijo}"] = (
            matriz[f"Gross_Proyectado_Arg_{sufijo}"]
            .div(objetivo.replace(0, pd.NA))
            .mul(100)
            .fillna(0.0)
        )
        matriz[f"Promedio_Diario_{sufijo}"] = (
            matriz[f"Kilos_Promedio_Diario_{sufijo}"] * valor_kg
        )

        dias_restantes = pd.to_numeric(matriz[columna_dias], errors="coerce").fillna(
            0.0
        )
        media_necesaria = pd.Series(0.0, index=matriz.index)
        mascara_dias = dias_restantes > 0
        media_necesaria.loc[mascara_dias] = (
            (objetivo.loc[mascara_dias] - operativo.loc[mascara_dias])
            / dias_restantes.loc[mascara_dias]
        ).clip(lower=0.0)
        matriz[f"Media_Necesaria_Diaria_{sufijo}"] = media_necesaria

    matriz["Gross_Proyectado_Arg"] = matriz["Gross_Proyectado_Arg_AJUSTADO"]
    matriz["Cumplimiento_Gross_Proy_Pct"] = matriz[
        "Cumplimiento_Gross_Proy_Pct_AJUSTADO"
    ]
    matriz["Promedio_Diario"] = matriz["Promedio_Diario_AJUSTADO"]
    matriz["Media_Necesaria_Diaria"] = matriz["Media_Necesaria_Diaria_AJUSTADO"]

    futuros = ventas[ventas["Periodo"].eq("Futuro") & ventas["SEGMENTO"].ne("")].copy()
    if not futuros.empty:
        futuros["ImporteNetoItem"] = pd.to_numeric(
            futuros.get("ImporteNetoItem", 0.0), errors="coerce"
        ).fillna(0.0)
        gross_disponible = (
            futuros.groupby(["CodVendedor", "SEGMENTO"], as_index=False)[
                "ImporteNetoItem"
            ]
            .sum()
            .rename(columns={"ImporteNetoItem": "Gross_Disponible"})
        )
        matriz = matriz.merge(
            gross_disponible,
            on=["CodVendedor", "SEGMENTO"],
            how="left",
        )
    matriz["Gross_Disponible"] = matriz.get(
        "Gross_Disponible", pd.Series(0.0, index=matriz.index)
    ).fillna(0.0)

    for sufijo in ["TODO", "AJUSTADO"]:
        proyeccion = pd.to_numeric(
            matriz[f"Gross_Proyectado_Arg_{sufijo}"], errors="coerce"
        ).fillna(0.0)
        bache = (matriz["Objetivo_Importe_Arg"] - proyeccion).clip(lower=0.0)
        gap_global = max(
            0.0,
            float(matriz["Objetivo_Importe_Arg"].sum()) - float(proyeccion.sum()),
        )
        suma_bache = float(bache.sum())
        factor = gap_global / suma_bache if suma_bache > 0 else 0.0
        matriz[f"Futuro_A_Incorporar_Gross_{sufijo}"] = (bache * factor).round(2)

    matriz["Futuro_A_Incorporar_Gross"] = matriz["Futuro_A_Incorporar_Gross_AJUSTADO"]

    columnas = [
        "CodVendedor",
        "Nombre",
        "SUP",
        "SEGMENTO",
        "Objetivo_Importe_Arg",
        "Arrastre",
        "Actual",
        "Importe_Operativo_Arg",
        "Kilos_Operativos",
        "Kilos_Proyectados_TODO",
        "Kilos_Proyectados_AJUSTADO",
        "Valor_Promedio_Kg_Arg",
        "Fuente_Valor_Kg",
        "Ajuste_Reemp_Arrastre",
        "Ajuste_Reemp_Actual",
        "Ajuste_Por_Reemp",
        "Gross_Proyectado_Arg",
        "Gross_Proyectado_Arg_TODO",
        "Gross_Proyectado_Arg_AJUSTADO",
        "Cumplimiento_Gross_Proy_Pct",
        "Cumplimiento_Gross_Proy_Pct_TODO",
        "Cumplimiento_Gross_Proy_Pct_AJUSTADO",
        "Promedio_Diario",
        "Promedio_Diario_TODO",
        "Promedio_Diario_AJUSTADO",
        "Media_Necesaria_Diaria",
        "Media_Necesaria_Diaria_TODO",
        "Media_Necesaria_Diaria_AJUSTADO",
        "Gross_Disponible",
        "Futuro_A_Incorporar_Gross",
        "Futuro_A_Incorporar_Gross_TODO",
        "Futuro_A_Incorporar_Gross_AJUSTADO",
        "Días Pasados",
        "Rutas",
        "Ajuste_Entrega",
        "Rutas_Ajustadas",
        "Días Restantes",
        "Días Restantes Todo",
        "Días Restantes Ajustado",
    ]
    resultado = _ordenar_matriz(
        matriz[[columna for columna in columnas if columna in matriz.columns]]
    )
    print(
        f"[PERF_CORE] obtener_matriz_gerencial_gross -> "
        f"{time.perf_counter() - t0:.4f} s"
    )
    return resultado


@st.cache_data(show_spinner=False)
def obtener_motor_gerencial(
    anio: int,
    mes: int,
    filtros_globales: dict,
) -> dict:
    """Retorna las matrices base gerenciales de Kilos y Gross con ambos escenarios."""
    return {
        "kilos": obtener_matriz_gerencial_kilos(anio, mes, filtros_globales),
        "gross": obtener_matriz_gerencial_gross(anio, mes, filtros_globales),
    }
