# modules/business_rules/business_rules_kilos.py
import time
import streamlit as st
import pandas as pd
import numpy as np

# REGLA DE ORO: Consumo exclusivo de la Capa CORE y el Repositorio de Business Rules (Cero acceso a RAW, STAGING o base de datos)
from modules.core.core_vendedores import obtener_core_vendedores
from modules.core.core_operaciones import obtener_core_operacion
from modules.business_rules.business_rules_repository import (
    obtener_objetivos_vendedores,
)


def _filtrar_universo_comercial_kilos(df: pd.DataFrame) -> pd.DataFrame:
    """
    BUSINESS_RULES: Aplica las reglas institucionales de exclusión sobre el universo bruto operativo.
    - Filtra transacciones restringiendo al proveedor PEPSICO.
    - Excluye tipologías de venta atípicas (Comodatos, Préstamos y Devoluciones Ficticias).
    """
    if df is None or df.empty:
        return df

    df_filtrado = df.copy()

    # Regla 1: Restricción exclusiva a Portafolio PEPSICO
    if "Proveedor" in df_filtrado.columns:
        df_filtrado = df_filtrado[
            df_filtrado["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    # Regla 2: Exclusión de Comodatos y Préstamos Logísticos
    if "TipoDeVenta" in df_filtrado.columns:
        tipos_excluidos = [
            "Comodato Devolución",
            "Comodato Ficticio",
            "Comodato Ficticio Devolución",
            "Comodato Préstamo",
        ]
        df_filtrado = df_filtrado[
            ~df_filtrado["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)
        ]

    return df_filtrado


def _asegurar_segmento_comercial(df: pd.DataFrame) -> pd.DataFrame:
    """
    BUSINESS_RULES: Replica exactamente la lógica de segmentación del legacy (rep_kilos.py)
    a partir de SegmentoRentabilidad y Rubro, asegurando la existencia de la columna 'SEGMENTO'.
    """
    if df is None or df.empty:
        return df

    df_trabajo = df.copy()

    if "SEGMENTO" not in df_trabajo.columns or df_trabajo["SEGMENTO"].isna().all():
        col_rent = (
            "SegmentoRentabilidad"
            if "SegmentoRentabilidad" in df_trabajo.columns
            else None
        )
        col_rubro = "Rubro" if "Rubro" in df_trabajo.columns else None

        sr = (
            df_trabajo.get(col_rent, pd.Series("", index=df_trabajo.index))
            .fillna("")
            .astype(str)
            .str.strip()
            .str.title()
            if col_rent
            else pd.Series("", index=df_trabajo.index)
        )
        rubro = (
            df_trabajo.get(col_rubro, pd.Series("", index=df_trabajo.index))
            .fillna("")
            .astype(str)
            .str.strip()
            if col_rubro
            else pd.Series("", index=df_trabajo.index)
        )

        cond_gold = sr.isin(["Platinum", "Gold"]).fillna(False)
        cond_silver = sr.isin(["Silver", "Bronze"]).fillna(False)

        gold_val = "GOLD " + rubro
        silver_val = "SILVER " + rubro
        df_trabajo["SEGMENTO"] = np.select(
            [cond_gold, cond_silver],
            [gold_val.str.strip(), silver_val.str.strip()],
            default=None,
        )

    return df_trabajo


@st.cache_data(show_spinner=False)
def calcular_objetivos_comerciales_kilos(anio: int, mes: int) -> pd.DataFrame:
    """
    BUSINESS_RULES: Recupera y procesa los objetivos comerciales vigentes de volumen (kilos)
    para el período especificado, validando los preventistas contra CORE_VENDEDORES via repositorio.
    """
    t0 = time.perf_counter()
    df_obj_db = obtener_objetivos_vendedores(anio, mes)

    padron_vendedores = obtener_core_vendedores()
    if padron_vendedores.empty:
        raise ValueError(
            "CORE_VENDEDORES no retornó padrón activo para validar los objetivos comerciales."
        )

    codigos_validos = set(
        padron_vendedores["CodVendedor"].dropna().astype("Int64").tolist()
    )

    if df_obj_db is None or df_obj_db.empty:
        print(
            f"[PERF_CORE] 8) calcular_objetivos_comerciales_kilos (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame(
            columns=["CodVendedor", "SEGMENTO", "Objetivo Mes Corriente"]
        )

    df = df_obj_db.copy()
    col_cv = next(
        (c for c in ["CodVendedor", "Codigo_Vendedor", "CodVend"] if c in df.columns),
        None,
    )
    if not col_cv:
        raise ValueError(
            "No se encontró la columna de identificador de vendedor en los objetivos comerciales."
        )

    df["CodVendedor"] = pd.to_numeric(df[col_cv], errors="coerce").astype("Int64")

    col_seg = next((c for c in ["SEGMENTO", "Segmento"] if c in df.columns), None)
    if not col_seg:
        raise ValueError(
            "No se encontró la columna de segmento en los objetivos comerciales."
        )

    df["SEGMENTO"] = df[col_seg].fillna("").astype(str).str.strip()

    col_obj = next(
        (c for c in ["Obj_Sugerido_Kg", "Objetivo", "Obj"] if c in df.columns), None
    )
    if not col_obj:
        raise ValueError(
            "No se encontró la columna de valor objetivo en los objetivos comerciales."
        )

    df["Objetivo Mes Corriente"] = pd.to_numeric(df[col_obj], errors="coerce").fillna(
        0.0
    )

    # Validación defensiva contra CORE_VENDEDORES
    df = df[df["CodVendedor"].isin(codigos_validos)].copy()

    agrupado = df.groupby(["CodVendedor", "SEGMENTO"], as_index=False)[
        "Objetivo Mes Corriente"
    ].sum()
    resultado = agrupado[["CodVendedor", "SEGMENTO", "Objetivo Mes Corriente"]]
    print(
        f"[PERF_CORE] 8) calcular_objetivos_comerciales_kilos -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado


@st.cache_data(show_spinner=False)
def calcular_compensaciones_reemplazos(df_vta_operativa: pd.DataFrame) -> pd.DataFrame:
    """
    BUSINESS_RULES: Detecta operaciones realizadas por reemplazantes mediante la titularidad operativa
    y calcula los ajustes compensatorios de kilos (Arrastre, Actual y Total).
    """
    t0 = time.perf_counter()
    if df_vta_operativa is None or df_vta_operativa.empty:
        print(
            f"[PERF_CORE] 9) calcular_compensaciones_reemplazos (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame(
            columns=[
                "CodVendedor",
                "SEGMENTO",
                "Ajuste_Reemp_Arrastre",
                "Ajuste_Reemp_Actual",
                "Ajuste_Por_Reemp",
            ]
        )

    df = _asegurar_segmento_comercial(df_vta_operativa)

    for col_req in [
        "CodVendedor",
        "CodVendedorOperativo",
        "SEGMENTO",
        "Periodo",
        "PesoKg",
    ]:
        if col_req not in df.columns:
            raise ValueError(
                f"Falta la columna obligatoria '{col_req}' para calcular las compensaciones por reemplazo."
            )

    df["CodVendedor"] = pd.to_numeric(df["CodVendedor"], errors="coerce").astype(
        "Int64"
    )
    df["CodVendedorOperativo"] = pd.to_numeric(
        df["CodVendedorOperativo"], errors="coerce"
    ).astype("Int64")
    df["SEGMENTO"] = df["SEGMENTO"].fillna("").astype(str).str.strip()
    df["PesoKg"] = pd.to_numeric(df["PesoKg"], errors="coerce").fillna(0.0)

    # Identificación de transacciones con divergencia entre titular y operador
    reemplazos = df[
        df["CodVendedorOperativo"].ne(df["CodVendedor"])
        & df["Periodo"].isin(["Arrastre", "Actual"])
    ].copy()

    if reemplazos.empty:
        print(
            f"[PERF_CORE] 9) calcular_compensaciones_reemplazos (sin reemplazos) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame(
            columns=[
                "CodVendedor",
                "SEGMENTO",
                "Ajuste_Reemp_Arrastre",
                "Ajuste_Reemp_Actual",
                "Ajuste_Por_Reemp",
            ]
        )

    # Descuento al titular (salida de kilos)
    mov_titular = reemplazos[["CodVendedor", "SEGMENTO", "Periodo", "PesoKg"]].rename(
        columns={"CodVendedor": "CodVend"}
    )
    mov_titular["Ajuste_Valor"] = -mov_titular.pop("PesoKg")

    # Suma al reemplazante operativo (entrada de kilos)
    mov_reemp = reemplazos[
        ["CodVendedorOperativo", "SEGMENTO", "Periodo", "PesoKg"]
    ].rename(columns={"CodVendedorOperativo": "CodVend"})
    mov_reemp["Ajuste_Valor"] = mov_reemp.pop("PesoKg")

    ajustes_totales = pd.concat([mov_titular, mov_reemp], ignore_index=True)
    ajustes_totales["CodVend"] = pd.to_numeric(
        ajustes_totales["CodVend"], errors="coerce"
    ).astype("Int64")

    aj_arr = (
        ajustes_totales[ajustes_totales["Periodo"] == "Arrastre"]
        .groupby(["CodVend", "SEGMENTO"], as_index=False)["Ajuste_Valor"]
        .sum()
        .rename(
            columns={"Ajuste_Valor": "Ajuste_Reemp_Arrastre", "CodVend": "CodVendedor"}
        )
    )
    aj_act = (
        ajustes_totales[ajustes_totales["Periodo"] == "Actual"]
        .groupby(["CodVend", "SEGMENTO"], as_index=False)["Ajuste_Valor"]
        .sum()
        .rename(
            columns={"Ajuste_Valor": "Ajuste_Reemp_Actual", "CodVend": "CodVendedor"}
        )
    )

    consolidado = aj_arr.merge(
        aj_act, on=["CodVendedor", "SEGMENTO"], how="outer"
    ).fillna(0.0)
    consolidado["Ajuste_Por_Reemp"] = (
        consolidado["Ajuste_Reemp_Arrastre"] + consolidado["Ajuste_Reemp_Actual"]
    )

    resultado = consolidado[
        [
            "CodVendedor",
            "SEGMENTO",
            "Ajuste_Reemp_Arrastre",
            "Ajuste_Reemp_Actual",
            "Ajuste_Por_Reemp",
        ]
    ]
    print(
        f"[PERF_CORE] 9) calcular_compensaciones_reemplazos -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado


def _calcular_calendario_ajustado_comercial(
    matriz_comercial: pd.DataFrame,
    padron_vendedores: pd.DataFrame,
    dias_pasados_map: dict,
    rutas_totales_map: dict,
    dias_restantes_todo_map: dict,
    dias_restantes_ajustado_map: dict,
) -> pd.DataFrame:
    """
    BUSINESS_RULES: Incorpora los parámetros logísticos utilizando los mapas seguros y explícitos
    provistos por CORE, garantizando que Rutas sea el total del mes y que TODO y AJUSTADO diverjan correctamente.
    """
    df = matriz_comercial.copy()
    if df.empty or padron_vendedores.empty:
        df["Ajuste_Entrega"] = 1
        df["Rutas_Ajustadas"] = 0
        df["Días Pasados"] = 0
        df["Rutas"] = 0
        df["Días Restantes Todo"] = 0
        df["Días Restantes Ajustado"] = 0
        df["Días Restantes"] = 0
        return df

    mv = padron_vendedores.copy()

    map_ajuste = (
        mv.set_index("CodVendedor")["Ajuste_Entrega"].to_dict()
        if "Ajuste_Entrega" in mv.columns
        else {}
    )
    map_rutas_ajust = (
        mv.set_index("CodVendedor")["Rutas_Ajustadas"].to_dict()
        if "Rutas_Ajustadas" in mv.columns
        else {}
    )

    df["Ajuste_Entrega"] = df["CodVendedor"].map(map_ajuste).fillna(1).astype(int)
    df["Rutas_Ajustadas"] = df["CodVendedor"].map(map_rutas_ajust).fillna(0).astype(int)

    df["Días Pasados"] = (
        df["CodVendedor"].map(dias_pasados_map).fillna(0).astype("Int64")
    )
    df["Rutas"] = df["CodVendedor"].map(rutas_totales_map).fillna(0).astype("Int64")
    df["Días Restantes Todo"] = (
        df["CodVendedor"].map(dias_restantes_todo_map).fillna(0).astype("Int64")
    )
    df["Días Restantes Ajustado"] = (
        df["CodVendedor"].map(dias_restantes_ajustado_map).fillna(0).astype("Int64")
    )
    df["Días Restantes"] = df["Días Restantes Ajustado"]

    return df


def _calcular_proyecciones_y_tendencias(matriz_comercial: pd.DataFrame) -> pd.DataFrame:
    """
    BUSINESS_RULES: Calcula de manera centralizada el Promedio Diario, la Tendencia Total en Kg,
    el Cumplimiento Proyectado en Porcentaje y la Media Necesaria Diaria para ambos escenarios (TODO y AJUSTADO).
    """
    df = matriz_comercial.copy()
    if df.empty:
        for suf in ["_TODO", "_AJUSTADO", ""]:
            df[f"Promedio_Diario{suf}"] = 0.0
            df[f"Tendencia_Total_Kg{suf}"] = 0.0
            df[f"Cumplimiento_Proyectado_Pct{suf}"] = 0.0
            df[f"Media_Necesaria_Diaria{suf}"] = 0.0
        return df

    dp_s = (
        df.get("Días Pasados", pd.Series(0, index=df.index))
        .astype(float)
        .replace(0, 1.0)
    )

    actual_val = df.get("Actual", 0.0)
    ajuste_act_val = df.get("Ajuste_Reemp_Actual", 0.0)
    operativo_val = df.get("OPERATIVO", 0.0)
    objetivo_val = df.get("Objetivo Mes Corriente", 0.0)

    p_diario = (actual_val + ajuste_act_val) / dp_s

    # Escenario TODO (Usa Días Restantes Todo)
    dr_todo = df.get("Días Restantes Todo", pd.Series(0, index=df.index)).astype(float)
    tend_todo = operativo_val.copy()
    mask_todo = dr_todo > 0
    if mask_todo.any():
        tend_todo.loc[mask_todo] = (
            p_diario[mask_todo] * dr_todo[mask_todo]
        ) + operativo_val.loc[mask_todo]

    media_nec_todo = pd.Series(0.0, index=df.index)
    if mask_todo.any():
        media_nec_todo.loc[mask_todo] = (
            (objetivo_val.loc[mask_todo] - operativo_val.loc[mask_todo])
            / dr_todo[mask_todo]
        ).clip(lower=0)

    df["Promedio_Diario_TODO"] = p_diario
    df["Tendencia_Total_Kg_TODO"] = tend_todo
    df["Cumplimiento_Proyectado_Pct_TODO"] = (
        (tend_todo / objetivo_val.replace(0, pd.NA)).mul(100).fillna(0.0)
    )
    df["Media_Necesaria_Diaria_TODO"] = media_nec_todo

    # Escenario AJUSTADO (Usa Días Restantes Ajustado)
    dr_ajust = df.get("Días Restantes Ajustado", dr_todo).astype(float)
    tend_ajust = operativo_val.copy()
    mask_ajust = dr_ajust > 0
    if mask_ajust.any():
        tend_ajust.loc[mask_ajust] = (
            p_diario[mask_ajust] * dr_ajust[mask_ajust]
        ) + operativo_val.loc[mask_ajust]

    media_nec_ajust = pd.Series(0.0, index=df.index)
    if mask_ajust.any():
        media_nec_ajust.loc[mask_ajust] = (
            (objetivo_val.loc[mask_ajust] - operativo_val.loc[mask_ajust])
            / dr_ajust[mask_ajust]
        ).clip(lower=0)

    df["Promedio_Diario_AJUSTADO"] = p_diario
    df["Tendencia_Total_Kg_AJUSTADO"] = tend_ajust
    df["Cumplimiento_Proyectado_Pct_AJUSTADO"] = (
        (tend_ajust / objetivo_val.replace(0, pd.NA)).mul(100).fillna(0.0)
    )
    df["Media_Necesaria_Diaria_AJUSTADO"] = media_nec_ajust

    # Columnas por defecto (AJUSTADO como principal)
    df["Promedio_Diario"] = df["Promedio_Diario_AJUSTADO"]
    df["Tendencia_Total_Kg"] = df["Tendencia_Total_Kg_AJUSTADO"]
    df["Cumplimiento_Proyectado_Pct"] = df["Cumplimiento_Proyectado_Pct_AJUSTADO"]
    df["Media_Necesaria_Diaria"] = df["Media_Necesaria_Diaria_AJUSTADO"]

    return df


def _incorporar_ventas_temporales_soporte(
    matriz_comercial: pd.DataFrame, df_vta_operativa: pd.DataFrame, dia_matinal: str
) -> pd.DataFrame:
    """
    BUSINESS_RULES: Extrae y adjunta los volúmenes de la última y penúltima semana a partir
    del histórico operativo bruto para trazabilidad analítica de soporte.
    """
    df = matriz_comercial.copy()
    if df.empty or df_vta_operativa is None or df_vta_operativa.empty:
        df["Ultima_Vta"] = 0.0
        df["Penultima_Vta"] = 0.0
        return df

    from modules.utils import parsear_fecha_robusta

    fecha_mat_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(fecha_mat_dt):
        f_ult = (fecha_mat_dt - pd.Timedelta(days=7)).date()
        f_penult = (fecha_mat_dt - pd.Timedelta(days=14)).date()

        u_vta = (
            df_vta_operativa[df_vta_operativa["FechaCarga_dt"].dt.date.eq(f_ult)]
            .groupby(["CodVendedor", "SEGMENTO"])["PesoKg"]
            .sum()
            .reset_index()
            .rename(columns={"PesoKg": "Ultima_Vta"})
        )
        p_vta = (
            df_vta_operativa[df_vta_operativa["FechaCarga_dt"].dt.date.eq(f_penult)]
            .groupby(["CodVendedor", "SEGMENTO"])["PesoKg"]
            .sum()
            .reset_index()
            .rename(columns={"PesoKg": "Penultima_Vta"})
        )
    else:
        u_vta = pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Ultima_Vta"])
        p_vta = pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Penultima_Vta"])

    if not u_vta.empty:
        u_vta["CodVendedor"] = pd.to_numeric(
            u_vta["CodVendedor"], errors="coerce"
        ).astype("Int64")
        df = df.merge(u_vta, on=["CodVendedor", "SEGMENTO"], how="left")
    else:
        df["Ultima_Vta"] = 0.0

    if not p_vta.empty:
        p_vta["CodVendedor"] = pd.to_numeric(
            p_vta["CodVendedor"], errors="coerce"
        ).astype("Int64")
        df = df.merge(p_vta, on=["CodVendedor", "SEGMENTO"], how="left")
    else:
        df["Penultima_Vta"] = 0.0

    df["Ultima_Vta"] = df.get("Ultima_Vta", 0.0).fillna(0.0)
    df["Penultima_Vta"] = df.get("Penultima_Vta", 0.0).fillna(0.0)

    return df


@st.cache_data(show_spinner=False)
def obtener_matriz_kilos_comercial(
    anio: int, mes: int, filtros_globales: dict
) -> pd.DataFrame:
    """
    BUSINESS_RULES (Orquestador Comercial): Consume servicios de la Capa CORE y el Repositorio,
    manteniendo compatibilidad con las claves legacy (dias_restantes_map) y consumiendo los nuevos mapas de rutas y días.
    """
    t0 = time.perf_counter()
    # 1. Consumo estricto de CORE_VENDEDORES (incluye padrón y parámetros logísticos de padrón)
    padron_vend = obtener_core_vendedores()
    if padron_vend.empty:
        print(
            f"[PERF_CORE] 10) obtener_matriz_kilos_comercial (padrón vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    sup_map = padron_vend.set_index("CodVendedor")["SUP"].to_dict()

    # 2. Consumo estricto de CORE_OPERACIONES
    dia_matinal = (
        filtros_globales.get("dia_matinal", "02/09/2026")
        if filtros_globales
        else "02/09/2026"
    )
    dia_venta = (
        filtros_globales.get("dia_venta", "01/09/2026")
        if filtros_globales
        else "01/09/2026"
    )

    datos_operativos = obtener_core_operacion(
        anio, mes, dia_matinal, dia_venta, modo_ajuste="AJUSTADO"
    )
    df_vta_op_bruto = datos_operativos["df_vta_operativa"]
    dias_pasados_map = datos_operativos["dias_pasados_map"]
    dias_restantes_map = datos_operativos["dias_restantes_map"]

    # Consumo seguro de las nuevas claves adicionales sin romper compatibilidad
    rutas_totales_map = datos_operativos.get("rutas_totales_map", dias_restantes_map)
    dias_restantes_todo_map = datos_operativos.get(
        "dias_restantes_todo_map", dias_restantes_map
    )
    dias_restantes_ajustado_map = datos_operativos.get(
        "dias_restantes_ajustado_map", dias_restantes_map
    )

    if df_vta_op_bruto.empty:
        print(
            f"[PERF_CORE] 10) obtener_matriz_kilos_comercial (vta_op vacía) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    # APLICACIÓN DE LA REGLA INSTITUCIONAL DE PORTAFOLIO (PEPSICO Y SIN COMODATOS)
    df_vta_op = _filtrar_universo_comercial_kilos(df_vta_op_bruto)

    if df_vta_op.empty:
        print(
            f"[PERF_CORE] 10) obtener_matriz_kilos_comercial (vta_op vacía tras filtrado de portafolio) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    # Asegurar segmentación comercial sobre los datos operativos
    df_vta_op = _asegurar_segmento_comercial(df_vta_op)

    # Filtrado por período comercial operativo (Arrastre y Actual)
    df_periodo = df_vta_op[
        df_vta_op["Periodo"].isin(["Arrastre", "Actual"])
        & df_vta_op["SEGMENTO"].notna()
    ].copy()
    if df_periodo.empty:
        print(
            f"[PERF_CORE] 10) obtener_matriz_kilos_comercial (periodo vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    # Mapeo de titularidad operativa con soporte para comodines especiales (-998)
    codigos_validos = set(padron_vend["CodVendedor"].dropna().tolist())
    cod_op = df_periodo["CodVendedorOperativo"]
    cod_tit = df_periodo["CodVendedor"]
    reemp = df_periodo.get("Reemplazo", pd.Series(pd.NA, index=df_periodo.index))

    is_special = ((reemp == 99) | (cod_op == 99) | (cod_tit == 99)).fillna(False)
    valid_op_mask = cod_op.isin(codigos_validos).fillna(False)
    valid_tit_mask = cod_tit.isin(codigos_validos).fillna(False)

    df_periodo["CodVend_Op"] = np.select(
        [is_special, valid_op_mask, valid_tit_mask],
        [-998, cod_op.fillna(-999).astype(int), cod_tit.fillna(-999).astype(int)],
        default=cod_tit.fillna(-999).astype(int),
    )
    df_periodo["CodVend_Op"] = (
        pd.Series(df_periodo["CodVend_Op"]).replace(-999, pd.NA).astype("Int64")
    )
    df_periodo["SEGMENTO"] = df_periodo["SEGMENTO"].astype(str).str.strip()

    # Agregación volumétrica por operador y segmento
    kilos_agrup = (
        df_periodo.groupby(["CodVend_Op", "SEGMENTO", "Periodo"], dropna=False)[
            "PesoKg"
        ]
        .sum()
        .reset_index()
    )
    kilos_agrup = kilos_agrup.rename(columns={"CodVend_Op": "CodVendedor"})

    kilos_pivot = kilos_agrup.pivot_table(
        index=["CodVendedor", "SEGMENTO"],
        columns="Periodo",
        values="PesoKg",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()
    kilos_pivot.columns.name = None

    for p in ["Arrastre", "Actual"]:
        if p not in kilos_pivot.columns:
            kilos_pivot[p] = 0.0

    # Construcción de matriz base cruzando padrón y segmentos
    orden_segmentos = [
        "GOLD Salty",
        "GOLD Crakers",
        "SILVER Salty",
        "SILVER Crakers",
        "SILVER Cereals",
    ]
    segs_vta = df_periodo["SEGMENTO"].dropna().unique()
    for s in segs_vta:
        if s not in orden_segmentos:
            orden_segmentos.append(s)

    df_comodin = pd.DataFrame(
        {
            "CodVendedor": pd.Series([-998], dtype="Int64"),
            "Nombre": ["REEMPLAZO"],
            "SUP": ["GENERAL"],
        }
    )
    padron_full = pd.concat([padron_vend, df_comodin], ignore_index=True)

    padron_full["_k"] = 1
    segmentos_df = pd.DataFrame({"SEGMENTO": orden_segmentos})
    segmentos_df["_k"] = 1
    matriz_base = padron_full.merge(segmentos_df, on="_k").drop(columns="_k")

    # Integración de transacciones
    matriz_comercial = matriz_base.merge(
        kilos_pivot[["CodVendedor", "SEGMENTO", "Arrastre", "Actual"]],
        on=["CodVendedor", "SEGMENTO"],
        how="left",
    )
    matriz_comercial[["Arrastre", "Actual"]] = matriz_comercial[
        ["Arrastre", "Actual"]
    ].fillna(0.0)

    # Integración de Objetivos Comerciales (via Repositorio de Business Rules)
    df_objetivos = calcular_objetivos_comerciales_kilos(anio, mes)
    if not df_objetivos.empty:
        matriz_comercial = matriz_comercial.merge(
            df_objetivos, on=["CodVendedor", "SEGMENTO"], how="left"
        )
    matriz_comercial["Objetivo Mes Corriente"] = matriz_comercial.get(
        "Objetivo Mes Corriente", 0.0
    ).fillna(0.0)

    # Integración de Compensaciones por Reemplazo
    df_compensaciones = calcular_compensaciones_reemplazos(df_vta_op)
    if not df_compensaciones.empty:
        matriz_comercial = matriz_comercial.merge(
            df_compensaciones, on=["CodVendedor", "SEGMENTO"], how="left"
        )

    # Asignación defensiva segura evitando AttributeError en columnas ausentes
    for col_c in ["Ajuste_Reemp_Arrastre", "Ajuste_Reemp_Actual", "Ajuste_Por_Reemp"]:
        if col_c in matriz_comercial.columns:
            matriz_comercial[col_c] = matriz_comercial[col_c].fillna(0.0)
        else:
            matriz_comercial[col_c] = 0.0

    # Cálculo del Neto Operativo
    matriz_comercial["OPERATIVO"] = (
        matriz_comercial["Arrastre"]
        + matriz_comercial["Actual"]
        + matriz_comercial["Ajuste_Por_Reemp"]
    )

    # Incorporación de Parámetros Logísticos y Calendario (utilizando mapas explícitos)
    matriz_comercial = _calcular_calendario_ajustado_comercial(
        matriz_comercial,
        padron_vend,
        dias_pasados_map,
        rutas_totales_map,
        dias_restantes_todo_map,
        dias_restantes_ajustado_map,
    )

    # Incorporación de Métricas Analíticas de Proyección y Tendencia (Incluyendo variantes TODO y AJUSTADO)
    matriz_comercial = _calcular_proyecciones_y_tendencias(matriz_comercial)

    # Incorporación de Ventas Temporales de Soporte (Última y Penúltima semana)
    matriz_comercial = _incorporar_ventas_temporales_soporte(
        matriz_comercial, df_vta_op, dia_matinal
    )

    # Ordenamiento institucional por supervisor, preventista y segmento
    mapping_orden = {str(seg).strip(): i for i, seg in enumerate(orden_segmentos)}
    matriz_comercial["_orden_idx"] = (
        matriz_comercial["SEGMENTO"]
        .astype(str)
        .str.strip()
        .map(mapping_orden)
        .fillna(999)
    )
    matriz_comercial = (
        matriz_comercial.sort_values(by=["SUP", "Nombre", "_orden_idx"])
        .drop(columns=["_orden_idx"])
        .reset_index(drop=True)
    )

    columnas_salida = [
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

    resultado_final = matriz_comercial[
        [c for c in columnas_salida if c in matriz_comercial.columns]
    ]
    print(
        f"[PERF_CORE] 10) obtener_matriz_kilos_comercial -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado_final
