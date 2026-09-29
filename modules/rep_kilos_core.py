# modules/reportes/rep_kilos_core.py
import time
import io
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules.utils import tarjeta_metrica_html

# REGLA FUNDAMENTAL: Consumo exclusivo de BUSINESS_RULES (Cero acceso a DB, SQLite, RAW o STAGING)
from modules.business_rules.business_rules_kilos import obtener_matriz_kilos_comercial


def render_rep_kilos_core(df_vta, df_rutas, df_ausencias, filtros_globales=None):
    """
    Reporte de Kilos bajo Arquitectura Objetivo Oficial (CORE -> BUSINESS_RULES -> REPORTES).
    Consumo puramente analítico y de renderizado visual, sin recálculos ni lógica ETL propia.
    """
    t_total = time.perf_counter()

    st.subheader("📊 Avance de Kilos por Segmento")

    if filtros_globales is None:
        anio_op = 2026
        mes_op = 9
        sup_filtro = "TODOS"
        filtros_base = {
            "anio": anio_op,
            "mes": mes_op,
            "supervisor": sup_filtro,
            "dia_matinal": "02/09/2026",
            "dia_venta": "01/09/2026",
        }
    else:
        anio_op = int(filtros_globales.get("anio", 2026))
        mes_op = int(filtros_globales.get("mes", 9))
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()
        filtros_base = filtros_globales

    # CONSUMO EXCLUSIVO DE BUSINESS_RULES (obtener_matriz_kilos_comercial) -> [PERF_CORE] 11
    t11 = time.perf_counter()
    matriz_comercial = obtener_matriz_kilos_comercial(anio_op, mes_op, filtros_base)
    print(
        f"[PERF_CORE] 11) construcción y obtención de matriz comercial -> {time.perf_counter() - t11:.4f} s"
    )

    if matriz_comercial.empty:
        st.info(
            "No se encontraron registros comerciales para los parámetros seleccionados."
        )
        print(
            f"[PERF_CORE] 13) tiempo total render_rep_kilos_core (vacío) -> {time.perf_counter() - t_total:.4f} s"
        )
        return

    # SEPARACIÓN EXPLÍCITA: Matriz Técnica (matriz_comercial) vs Vista Comercial (matriz_comercial_comercial)
    matriz_comercial_comercial = matriz_comercial[
        matriz_comercial["CodVendedor"].ne(-998)
    ].copy()

    # Extracción de dimensiones únicas para filtros de UI (sobre Vista Comercial)
    vendedores_disponibles = sorted(
        matriz_comercial_comercial["Nombre"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    segmentos_disponibles = sorted(
        matriz_comercial_comercial["SEGMENTO"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        v_selec = st.multiselect(
            "Vendedor",
            options=vendedores_disponibles,
            default=[],
            key=f"core_kilos_v_{anio_op}_{mes_op}_{sup_filtro}",
        )
    with col_f2:
        s_selec = st.multiselect(
            "Segmento",
            options=segmentos_disponibles,
            default=[],
            key=f"core_kilos_s_{anio_op}_{mes_op}_{sup_filtro}",
        )
    with col_f3:
        modo_ajuste = st.selectbox(
            "Ajuste por Entrega",
            options=["TODO", "AJUSTADO"],
            index=1,
            key=f"core_kilos_ajuste_{anio_op}_{mes_op}_{sup_filtro}",
        )

    if not v_selec:
        v_selec = vendedores_disponibles
    if not s_selec:
        s_selec = segmentos_disponibles

    # Filtrado interactivo exclusivo sobre la Vista Comercial (-998 excluido de pantalla y KPIs)
    rep_filtrado = matriz_comercial_comercial[
        matriz_comercial_comercial["Nombre"].astype(str).str.strip().isin(v_selec)
        & matriz_comercial_comercial["SEGMENTO"].astype(str).str.strip().isin(s_selec)
    ].copy()

    if sup_filtro != "TODOS" and "SUP" in rep_filtrado.columns:
        rep_filtrado = rep_filtrado[
            rep_filtrado["SUP"].astype(str).str.strip() == sup_filtro
        ].copy()

    if rep_filtrado.empty:
        st.info("No hay registros disponibles para los filtros aplicados.")
        print(
            f"[PERF_CORE] 13) tiempo total render_rep_kilos_core (filtrado vacío) -> {time.perf_counter() - t_total:.4f} s"
        )
        return

    # ENRUTAMIENTO DINÁMICO SEGÚN EL SELECTOR (TODO / AJUSTADO) - SIN RECALCULAR NEGOCIO EN REPORTES
    sufijo_modelo = "_AJUSTADO" if modo_ajuste == "AJUSTADO" else "_TODO"

    rep_filtrado["Tendencia_Total_Kg"] = rep_filtrado.get(
        f"Tendencia_Total_Kg{sufijo_modelo}",
        rep_filtrado.get("Tendencia_Total_Kg", 0.0),
    )
    rep_filtrado["Cumplimiento_Proyectado_Pct"] = rep_filtrado.get(
        f"Cumplimiento_Proyectado_Pct{sufijo_modelo}",
        rep_filtrado.get("Cumplimiento_Proyectado_Pct", 0.0),
    )
    rep_filtrado["Promedio_Diario"] = rep_filtrado.get(
        f"Promedio_Diario{sufijo_modelo}", rep_filtrado.get("Promedio_Diario", 0.0)
    )
    rep_filtrado["Media_Necesaria_Diaria"] = rep_filtrado.get(
        f"Media_Necesaria_Diaria{sufijo_modelo}",
        rep_filtrado.get("Media_Necesaria_Diaria", 0.0),
    )

    if modo_ajuste == "AJUSTADO" and "Días Restantes Ajustado" in rep_filtrado.columns:
        rep_filtrado["Días Restantes"] = rep_filtrado["Días Restantes Ajustado"]
    elif "Días Restantes Todo" in rep_filtrado.columns:
        rep_filtrado["Días Restantes"] = rep_filtrado["Días Restantes Todo"]

    # APLICACIÓN DE ORDENAMIENTO OFICIAL IDÉNTICO A rep_kilos.py (CodVendedor y orden corporativo de segmentos)
    orden_segmentos_maestro = [
        "GOLD Salty",
        "GOLD Crakers",
        "SILVER Salty",
        "SILVER Crakers",
        "SILVER Cereals",
    ]
    segs_actuales = rep_filtrado["SEGMENTO"].dropna().astype(str).str.strip().unique()
    for s_act in segs_actuales:
        if s_act not in orden_segmentos_maestro:
            orden_segmentos_maestro.append(s_act)

    mapping_orden = {
        str(seg).strip(): i for i, seg in enumerate(orden_segmentos_maestro)
    }
    rep_filtrado["SEGMENTO_STR"] = rep_filtrado["SEGMENTO"].astype(str).str.strip()
    rep_filtrado["_orden_idx"] = (
        rep_filtrado["SEGMENTO_STR"].map(mapping_orden).fillna(999)
    )
    rep_filtrado = (
        rep_filtrado.sort_values(by=["CodVendedor", "_orden_idx"])
        .drop(columns=["_orden_idx", "SEGMENTO_STR"])
        .reset_index(drop=True)
    )

    # RENDERIZADO VISUAL Y MÉTRICAS -> [PERF_CORE] 12
    t12 = time.perf_counter()

    # MÉTRICAS OBLIGATORIAS CALCULADAS EXCLUSIVAMENTE DESDE LA VISTA COMERCIAL
    total_arrastre = float(rep_filtrado["Arrastre"].sum())
    total_actual = float(rep_filtrado["Actual"].sum())
    total_neto_operativo = float(rep_filtrado["OPERATIVO"].sum())
    total_objetivo_mes = float(rep_filtrado["Objetivo Mes Corriente"].sum())
    pct_avance = (
        (total_neto_operativo / total_objetivo_mes * 100.0)
        if total_objetivo_mes > 0
        else 0.0
    )

    total_tendencia = (
        float(rep_filtrado["Tendencia_Total_Kg"].sum())
        if "Tendencia_Total_Kg" in rep_filtrado.columns
        else total_neto_operativo
    )
    pct_cumplimiento_obj = (
        (total_tendencia / total_objetivo_mes * 100.0)
        if total_objetivo_mes > 0
        else 0.0
    )

    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    with mcol1:
        st.markdown(
            tarjeta_metrica_html(
                "📦 Arrastre", f"{total_arrastre:,.1f} kg", "#3b82f6", "39px", "21px"
            ),
            unsafe_allow_html=True,
        )
    with mcol2:
        st.markdown(
            tarjeta_metrica_html(
                "🚚 Actual", f"{total_actual:,.1f} kg", "#3b82f6", "39px", "21px"
            ),
            unsafe_allow_html=True,
        )
    with mcol3:
        st.markdown(
            tarjeta_metrica_html(
                "📊 Neto Operativo",
                f"{total_neto_operativo:,.1f} kg",
                "#3b82f6",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )
    with mcol4:
        st.markdown(
            tarjeta_metrica_html(
                "📈 % Avance", f"{pct_avance:,.2f}%", "#3b82f6", "39px", "21px"
            ),
            unsafe_allow_html=True,
        )

    tcol1, tcol2, tcol3 = st.columns(3)
    with tcol1:
        st.markdown(
            tarjeta_metrica_html(
                "🎯 Objetivo del Mes",
                f"{total_objetivo_mes:,.1f} kg",
                "#3b82f6",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )
    with tcol2:
        st.markdown(
            tarjeta_metrica_html(
                "📈 Tendencia Kgs",
                f"{total_tendencia:,.1f} kg",
                "#ef4444",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )
    with tcol3:
        st.markdown(
            tarjeta_metrica_html(
                "🎯 Tendencia %",
                f"{pct_cumplimiento_obj:,.2f}%",
                "#3b82f6",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    columnas_ordenadas = [
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
        "Ajuste_Por_Reemp",
        "Tendencia_Total_Kg",
        "Cumplimiento_Proyectado_Pct",
        "Promedio_Diario",
        "Media_Necesaria_Diaria",
        "Días Pasados",
        "Rutas",
        "Ajuste_Entrega",
        "Rutas_Ajustadas",
        "Días Restantes",
    ]

    for col in columnas_ordenadas:
        if col not in rep_filtrado.columns:
            rep_filtrado[col] = 0.0

    rep_filtrado = rep_filtrado[columnas_ordenadas]

    # Preparación de vista formateada para renderizado visual
    rep_display = rep_filtrado.copy()
    cols_kilos = [
        "Objetivo Mes Corriente",
        "Arrastre",
        "Actual",
        "Ultima_Vta",
        "Penultima_Vta",
        "OPERATIVO",
        "Ajuste_Por_Reemp",
        "Tendencia_Total_Kg",
        "Promedio_Diario",
        "Media_Necesaria_Diaria",
    ]
    for col in cols_kilos:
        if col in rep_display.columns:
            rep_display[col] = rep_display[col].apply(
                lambda x: f"{x:,.2f} kg" if pd.notna(x) else "0.00 kg"
            )

    if "Cumplimiento_Proyectado_Pct" in rep_display.columns:
        rep_display["Cumplimiento_Proyectado_Pct"] = rep_display[
            "Cumplimiento_Proyectado_Pct"
        ].apply(lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%")

    if not rep_display.empty:
        st.dataframe(rep_display, width="stretch", hide_index=True)
    else:
        st.info("No se encontraron registros de Kilos con los filtros seleccionados.")

    # Botón funcional de descarga a Excel integrado al final de la vista (RESPETA MODO_AJUSTE)
    matriz_export = matriz_comercial.copy()
    sufijo_modelo_exp = "_AJUSTADO" if modo_ajuste == "AJUSTADO" else "_TODO"
    matriz_export["Tendencia_Total_Kg"] = matriz_export.get(
        f"Tendencia_Total_Kg{sufijo_modelo_exp}",
        matriz_export.get("Tendencia_Total_Kg", 0.0),
    )
    matriz_export["Cumplimiento_Proyectado_Pct"] = matriz_export.get(
        f"Cumplimiento_Proyectado_Pct{sufijo_modelo_exp}",
        matriz_export.get("Cumplimiento_Proyectado_Pct", 0.0),
    )
    matriz_export["Promedio_Diario"] = matriz_export.get(
        f"Promedio_Diario{sufijo_modelo_exp}",
        matriz_export.get("Promedio_Diario", 0.0),
    )
    matriz_export["Media_Necesaria_Diaria"] = matriz_export.get(
        f"Media_Necesaria_Diaria{sufijo_modelo_exp}",
        matriz_export.get("Media_Necesaria_Diaria", 0.0),
    )
    if modo_ajuste == "AJUSTADO" and "Días Restantes Ajustado" in matriz_export.columns:
        matriz_export["Días Restantes"] = matriz_export["Días Restantes Ajustado"]
    elif "Días Restantes Todo" in matriz_export.columns:
        matriz_export["Días Restantes"] = matriz_export["Días Restantes Todo"]
    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
        matriz_export.to_excel(
            writer,
            index=False,
            sheet_name="Avance_Kilos_Segmento",
        )
    buffer_excel.seek(0)

    st.download_button(
        label="📥 Descargar Avance Kilos a Excel",
        data=buffer_excel,
        file_name=f"Avance_Kilos_{sup_filtro}_{mes_op}_{anio_op}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"btn_dl_kilos_core_{sup_filtro}",
    )

    st.divider()

    # AUDITORÍA TEMPORAL OBLIGATORIA (Sección colapsable de comparación)
    with st.expander("🔍 Auditoría CORE (Comparativa de Ejecución)", expanded=False):
        st.markdown(
            "Métricas globales extraídas de la matriz comercial procesada por la Capa Business Rules:"
        )

        aud_filas = len(rep_filtrado)
        aud_vendedores = rep_filtrado["CodVendedor"].nunique()
        aud_segmentos = rep_filtrado["SEGMENTO"].nunique()
        aud_arrastre = float(rep_filtrado["Arrastre"].sum())
        aud_actual = float(rep_filtrado["Actual"].sum())
        aud_operativo = float(rep_filtrado["OPERATIVO"].sum())
        aud_objetivo = float(rep_filtrado["Objetivo Mes Corriente"].sum())

        acol1, acol2, acol3 = st.columns(3)
        with acol1:
            st.metric("Cantidad de Filas", f"{aud_filas:,}")
            st.metric("Vendedores Únicos", f"{aud_vendedores:,}")
        with acol2:
            st.metric("Segmentos Únicos", f"{aud_segmentos:,}")
            st.metric("Arrastre Total", f"{aud_arrastre:,.2f} kg")
        with acol3:
            st.metric("Actual Total", f"{aud_actual:,.2f} kg")
            st.metric("Operativo Total", f"{aud_operativo:,.2f} kg")
            st.metric("Objetivo Total", f"{aud_objetivo:,.2f} kg")

    print(
        f"[PERF_CORE] 12) renderizado visual y armado de UI -> {time.perf_counter() - t12:.4f} s"
    )
    print(
        f"[PERF_CORE] 13) tiempo total render_rep_kilos_core -> {time.perf_counter() - t_total:.4f} s"
    )
