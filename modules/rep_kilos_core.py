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

    st.subheader("📊 Avance de Kilos por Segmento [ARQUITECTURA CORE]")
    st.markdown(
        "Vista analítica de desempeño volumétrico conectada directamente al motor institucional de reglas de negocio."
    )

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

    # Extracción de dimensiones únicas para filtros de UI
    vendedores_disponibles = sorted(
        matriz_comercial["Nombre"].dropna().astype(str).str.strip().unique().tolist()
    )
    segmentos_disponibles = sorted(
        matriz_comercial["SEGMENTO"].dropna().astype(str).str.strip().unique().tolist()
    )

    col_f1, col_f2 = st.columns(2)
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

    if not v_selec:
        v_selec = vendedores_disponibles
    if not s_selec:
        s_selec = segmentos_disponibles

    # Filtrado interactivo exclusivo sobre la matriz recibida
    rep_filtrado = matriz_comercial[
        matriz_comercial["Nombre"].astype(str).str.strip().isin(v_selec)
        & matriz_comercial["SEGMENTO"].astype(str).str.strip().isin(s_selec)
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

    # RENDERIZADO VISUAL Y MÉTRICAS -> [PERF_CORE] 12
    t12 = time.perf_counter()

    # MÉTRICAS OBLIGATORIAS CALCULADAS EXCLUSIVAMENTE DESDE EL DATAFRAME RECIBIDO
    total_arrastre = float(rep_filtrado["Arrastre"].sum())
    total_actual = float(rep_filtrado["Actual"].sum())
    total_operativo = float(rep_filtrado["OPERATIVO"].sum())
    total_objetivo = float(rep_filtrado["Objetivo Mes Corriente"].sum())
    pct_cumplimiento = (
        (total_operativo / total_objetivo * 100.0) if total_objetivo > 0 else 0.0
    )

    mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
    with mcol1:
        st.markdown(
            tarjeta_metrica_html(
                "📦 Arrastre Total",
                f"{total_arrastre:,.1f} kg",
                "#3b82f6",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )
    with mcol2:
        st.markdown(
            tarjeta_metrica_html(
                "🚚 Actual Total", f"{total_actual:,.1f} kg", "#3b82f6", "39px", "21px"
            ),
            unsafe_allow_html=True,
        )
    with mcol3:
        st.markdown(
            tarjeta_metrica_html(
                "📊 Operativo Total",
                f"{total_operativo:,.1f} kg",
                "#3b82f6",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )
    with mcol4:
        st.markdown(
            tarjeta_metrica_html(
                "🎯 Objetivo Total",
                f"{total_objetivo:,.1f} kg",
                "#3b82f6",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )
    with mcol5:
        st.markdown(
            tarjeta_metrica_html(
                "📈 % Cumplimiento",
                f"{pct_cumplimiento:,.2f}%",
                "#10b981",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    # Preparación de vista formateada para renderizado
    rep_display = rep_filtrado.copy()
    cols_numericas = [
        "Objetivo Mes Corriente",
        "Arrastre",
        "Actual",
        "OPERATIVO",
        "Ajuste_Reemp_Arrastre",
        "Ajuste_Reemp_Actual",
        "Ajuste_Por_Reemp",
    ]
    for col in cols_numericas:
        if col in rep_display.columns:
            rep_display[col] = rep_display[col].apply(
                lambda x: f"{x:,.2f} kg" if pd.notna(x) else "0.00 kg"
            )

    st.dataframe(rep_display, width="stretch", hide_index=True)

    # Botón funcional de descarga a Excel integrado al final de la vista
    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
        rep_filtrado.to_excel(writer, index=False, sheet_name="Avance_Kilos_CORE")
    buffer_excel.seek(0)

    st.download_button(
        label="📥 Descargar Avance Kilos [CORE] a Excel",
        data=buffer_excel,
        file_name=f"Avance_Kilos_CORE_{sup_filtro}_{mes_op}_{anio_op}.xlsx",
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
