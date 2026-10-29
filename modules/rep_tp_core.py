# modules/reportes/rep_tp_core.py

import io
import time
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from modules.business_rules.business_rules_tp import generar_business_rules_tp
from modules.utils import tarjeta_metrica_html


@st.cache_data(show_spinner=False)
def _generar_excel_tp_core(r_vend, r_sub, r_tax, r_op):
    """
    Función cacheada para diferir la serialización a Excel estrictamente bajo demanda.
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        r_vend.to_excel(writer, index=False, sheet_name="Ranking_Vendedor")
        r_sub.to_excel(writer, index=False, sheet_name="Ranking_SubCanal")
        r_tax.to_excel(writer, index=False, sheet_name="Ranking_Taxonomia")
        r_op.to_excel(writer, index=False, sheet_name="Tabla_Oportunidades")
    return buffer.getvalue()


@st.fragment
def render_fragmento_interactivo_tp(br_data):
    """
    Fragmento interactivo de presentación para Tienda Perfecta (TP).
    Aplica filtros visuales locales sobre el dataset maestro (detalle_tp) en memoria
    sin volver a ejecutar la lógica de negocio ni consultar el Core.
    """
    detalle_tp = br_data.get(
        "detalle_tp",
        br_data.get("df_filtrado", pd.DataFrame()),
    )
    ranking_vendedor_taxonomia_snapshot = br_data.get(
        "ranking_vendedor_taxonomia", pd.DataFrame()
    )
    if ranking_vendedor_taxonomia_snapshot is None:
        ranking_vendedor_taxonomia_snapshot = pd.DataFrame()

    vendedores_disp = (
        sorted(detalle_tp["Vendedor"].dropna().unique().tolist())
        if not detalle_tp.empty and "Vendedor" in detalle_tp.columns
        else []
    )
    subcanales_disp = (
        sorted(detalle_tp["SubCanal"].dropna().unique().tolist())
        if not detalle_tp.empty and "SubCanal" in detalle_tp.columns
        else []
    )
    taxonomias_disp = (
        sorted(detalle_tp["Taxonomia"].dropna().unique().tolist())
        if not detalle_tp.empty and "Taxonomia" in detalle_tp.columns
        else []
    )

    # Filtros locales interactivos
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        v_sel = st.multiselect(
            "Filtrar por Vendedor",
            options=vendedores_disp,
            default=[],
            placeholder="Todos los vendedores...",
            key="tp_core_filtro_vend",
        )
    with col_f2:
        sc_sel = st.multiselect(
            "Filtrar por SubCanal",
            options=subcanales_disp,
            default=[],
            placeholder="Todos los subcanales...",
            key="tp_core_filtro_subcanal",
        )
    with col_f3:
        tx_sel = st.multiselect(
            "Filtrar por Taxonomía",
            options=taxonomias_disp,
            default=[],
            placeholder="Todas las taxonomías...",
            key="tp_core_filtro_tax",
        )
    with col_f4:
        estado_tp_sel = st.selectbox(
            "Estado Tienda Perfecta",
            options=["Todos", "SI", "NO", "Menos de 70%", "Entre 70% y 80%"],
            key="tp_core_filtro_estado_tp",
        )

    # Aplicación estricta de filtros sobre detalle_tp en memoria
    df = detalle_tp.copy()
    if not df.empty:
        if v_sel and "Vendedor" in df.columns:
            df = df[df["Vendedor"].isin(v_sel)]
        if sc_sel and "SubCanal" in df.columns:
            df = df[df["SubCanal"].isin(sc_sel)]
        if tx_sel and "Taxonomia" in df.columns:
            df = df[df["Taxonomia"].isin(tx_sel)]
        if estado_tp_sel == "SI":
            df = df[df["Es_TP"] == True]
        elif estado_tp_sel == "NO":
            df = df[df["Es_TP"] == False]
        elif estado_tp_sel == "Menos de 70%":
            df = df[df["Score"] < 70]
        elif estado_tp_sel == "Entre 70% y 80%":
            df = df[(df["Score"] >= 70) & (df["Score"] < 80)]

    # Objetivo congelado: solo Vendedor y Taxonomía acotan el objetivo.
    # SubCanal, Estado TP y bandas de Score solo filtran el realizado.
    objetivos_scope = ranking_vendedor_taxonomia_snapshot.copy()
    if not objetivos_scope.empty:
        if v_sel and "Vendedor" in objetivos_scope.columns:
            objetivos_scope = objetivos_scope[objetivos_scope["Vendedor"].isin(v_sel)]
        if tx_sel and "Taxonomia" in objetivos_scope.columns:
            objetivos_scope = objetivos_scope[objetivos_scope["Taxonomia"].isin(tx_sel)]
    objetivo_total = (
        int(
            pd.to_numeric(
                objetivos_scope.get("Objetivo_TP", pd.Series(dtype=float)),
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )
        if not objetivos_scope.empty
        else 0
    )

    # Recálculo local en memoria de KPIs realizados
    total_censados = int(
        df["Cliente_id"].nunique()
        if not df.empty
        and "Cliente_id" in df.columns
        and df["Cliente_id"].notna().any()
        else len(df)
    )
    total_tp = int(
        df[df["Es_TP"]]["Cliente_id"].nunique()
        if not df.empty
        and "Cliente_id" in df.columns
        and df["Cliente_id"].notna().any()
        else (df["Es_TP"].sum() if not df.empty and "Es_TP" in df.columns else 0)
    )
    pct_tp_global = round(
        (total_tp / total_censados * 100.0) if total_censados > 0 else 0.0, 2
    )
    promedio_score = round(
        float(df["Score"].mean()) if not df.empty and "Score" in df.columns else 0.0, 2
    )

    cumplimiento_objetivo = round(
        (total_tp / objetivo_total * 100.0) if objetivo_total > 0 else 0.0, 2
    )
    gap_tp = max(objetivo_total - total_tp, 0)
    excedente_tp = max(total_tp - objetivo_total, 0)
    kpis = {
        "Clientes_Censados": total_censados,
        "Clientes_TP": total_tp,
        "Porcentaje_Cumplimiento_TP": pct_tp_global,
        "Porcentaje_TP_Sobre_Censados": pct_tp_global,
        "Puntuacion_Promedio": promedio_score,
        "Objetivo_TP": objetivo_total,
        "Cumplimiento_Objetivo_TP_Pct": cumplimiento_objetivo,
        "Gap_TP": gap_tp,
        "Excedente_TP": excedente_tp,
    }

    # Recálculo local en memoria de Rankings y Tabla de Oportunidades
    ranking_vendedor = pd.DataFrame()
    if not df.empty and "Vendedor" in df.columns:
        rv = df.groupby("Vendedor", as_index=False).agg(
            Censados=("Cliente_id", "nunique"),
            Clientes_TP=("Es_TP", lambda x: int(x.sum())),
            Puntuacion_Promedio=("Score", "mean"),
        )
        rv["Porcentaje_Cumplimiento_TP"] = (
            (rv["Clientes_TP"] / rv["Censados"].replace(0, pd.NA))
            .mul(100.0)
            .fillna(0.0)
            .round(2)
        )
        rv["Puntuacion_Promedio"] = rv["Puntuacion_Promedio"].round(2)
        ranking_vendedor = (
            rv[
                [
                    "Vendedor",
                    "Censados",
                    "Clientes_TP",
                    "Porcentaje_Cumplimiento_TP",
                    "Puntuacion_Promedio",
                ]
            ]
            .sort_values(
                by=["Porcentaje_Cumplimiento_TP", "Censados"], ascending=[False, False]
            )
            .reset_index(drop=True)
        )

    if not ranking_vendedor.empty and not objetivos_scope.empty:
        obj_vendedor = objetivos_scope.groupby("Vendedor", as_index=False)[
            "Objetivo_TP"
        ].sum()
        ranking_vendedor = ranking_vendedor.merge(
            obj_vendedor, on="Vendedor", how="left"
        )
        ranking_vendedor["Objetivo_TP"] = (
            pd.to_numeric(ranking_vendedor["Objetivo_TP"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
        ranking_vendedor["Cumplimiento_Objetivo_TP_Pct"] = (
            ranking_vendedor["Clientes_TP"]
            .div(ranking_vendedor["Objetivo_TP"].replace(0, pd.NA))
            .mul(100)
            .fillna(0)
            .round(2)
        )
        ranking_vendedor["Gap_TP"] = (
            (ranking_vendedor["Objetivo_TP"] - ranking_vendedor["Clientes_TP"])
            .clip(lower=0)
            .astype(int)
        )
        ranking_vendedor["Excedente_TP"] = (
            (ranking_vendedor["Clientes_TP"] - ranking_vendedor["Objetivo_TP"])
            .clip(lower=0)
            .astype(int)
        )

    ranking_subcanal = pd.DataFrame()
    if not df.empty and "SubCanal" in df.columns:
        rsc = df.groupby("SubCanal", as_index=False).agg(
            Censados=("Cliente_id", "nunique"),
            Clientes_TP=("Es_TP", lambda x: int(x.sum())),
            Puntuacion_Promedio=("Score", "mean"),
        )
        rsc["Porcentaje_Cumplimiento_TP"] = (
            (rsc["Clientes_TP"] / rsc["Censados"].replace(0, pd.NA))
            .mul(100.0)
            .fillna(0.0)
            .round(2)
        )
        rsc["Puntuacion_Promedio"] = rsc["Puntuacion_Promedio"].round(2)
        ranking_subcanal = (
            rsc[
                [
                    "SubCanal",
                    "Censados",
                    "Clientes_TP",
                    "Porcentaje_Cumplimiento_TP",
                    "Puntuacion_Promedio",
                ]
            ]
            .sort_values(by="Porcentaje_Cumplimiento_TP", ascending=False)
            .reset_index(drop=True)
        )

    ranking_taxonomia = pd.DataFrame()
    if not df.empty and "Taxonomia" in df.columns:
        rtx = df.groupby("Taxonomia", as_index=False).agg(
            Censados=("Cliente_id", "nunique"),
            Clientes_TP=("Es_TP", lambda x: int(x.sum())),
            Puntuacion_Promedio=("Score", "mean"),
        )
        rtx["Porcentaje_Cumplimiento_TP"] = (
            (rtx["Clientes_TP"] / rtx["Censados"].replace(0, pd.NA))
            .mul(100.0)
            .fillna(0.0)
            .round(2)
        )
        rtx["Puntuacion_Promedio"] = rtx["Puntuacion_Promedio"].round(2)
        ranking_taxonomia = (
            rtx[
                [
                    "Taxonomia",
                    "Censados",
                    "Clientes_TP",
                    "Porcentaje_Cumplimiento_TP",
                    "Puntuacion_Promedio",
                ]
            ]
            .sort_values(by="Porcentaje_Cumplimiento_TP", ascending=False)
            .reset_index(drop=True)
        )

    if not ranking_taxonomia.empty and not objetivos_scope.empty:
        obj_taxonomia = objetivos_scope.groupby("Taxonomia", as_index=False)[
            "Objetivo_TP"
        ].sum()
        ranking_taxonomia = ranking_taxonomia.merge(
            obj_taxonomia, on="Taxonomia", how="left"
        )
        ranking_taxonomia["Objetivo_TP"] = (
            pd.to_numeric(ranking_taxonomia["Objetivo_TP"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
        ranking_taxonomia["Cumplimiento_Objetivo_TP_Pct"] = (
            ranking_taxonomia["Clientes_TP"]
            .div(ranking_taxonomia["Objetivo_TP"].replace(0, pd.NA))
            .mul(100)
            .fillna(0)
            .round(2)
        )
        ranking_taxonomia["Gap_TP"] = (
            (ranking_taxonomia["Objetivo_TP"] - ranking_taxonomia["Clientes_TP"])
            .clip(lower=0)
            .astype(int)
        )
        ranking_taxonomia["Excedente_TP"] = (
            (ranking_taxonomia["Clientes_TP"] - ranking_taxonomia["Objetivo_TP"])
            .clip(lower=0)
            .astype(int)
        )

    tabla_oportunidades = pd.DataFrame()
    if not df.empty:
        cols_op = [
            c
            for c in [
                "Vendedor",
                "Cliente_id",
                "RazonSocial",
                "SubCanal",
                "Taxonomia",
                "Score",
                "Es_TP",
            ]
            if c in df.columns
        ]
        if cols_op:
            tabla_oportunidades = df[cols_op].copy()
            tabla_oportunidades["Score"] = pd.to_numeric(
                tabla_oportunidades["Score"], errors="coerce"
            ).fillna(0.0)
            tabla_oportunidades = tabla_oportunidades.sort_values(
                by="Score", ascending=True
            ).reset_index(drop=True)

    # Renderizado visual de KPIs
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.markdown(
            tarjeta_metrica_html(
                "CLIENTES CENSADOS",
                f"{kpis['Clientes_Censados']:,.0f}",
                "#3b82f6",
                "1.3rem",
                "0.7rem",
            ),
            unsafe_allow_html=True,
        )
    with sc2:
        st.markdown(
            tarjeta_metrica_html(
                "CLIENTES TIENDA PERFECTA",
                f"{kpis['Clientes_TP']:,.0f}",
                "#22c55e",
                "1.3rem",
                "0.7rem",
            ),
            unsafe_allow_html=True,
        )
    with sc3:
        st.markdown(
            tarjeta_metrica_html(
                "% TP SOBRE CENSADOS",
                f"{kpis['Porcentaje_Cumplimiento_TP']:,.2f}%",
                "#8b5cf6",
                "1.3rem",
                "0.7rem",
            ),
            unsafe_allow_html=True,
        )
    with sc4:
        st.markdown(
            tarjeta_metrica_html(
                "PUNTUACIÓN PROMEDIO",
                f"{kpis['Puntuacion_Promedio']:,.2f}",
                "#f59e0b",
                "1.3rem",
                "0.7rem",
            ),
            unsafe_allow_html=True,
        )

    sc5, sc6, sc7, sc8 = st.columns(4)
    with sc5:
        st.markdown(
            tarjeta_metrica_html(
                "OBJETIVO TP FIJADO",
                f"{kpis['Objetivo_TP']:,.0f}",
                "#f59e0b",
                "1.3rem",
                "0.7rem",
            ),
            unsafe_allow_html=True,
        )
    with sc6:
        st.markdown(
            tarjeta_metrica_html(
                "% CUMPLIMIENTO OBJETIVO",
                f"{kpis['Cumplimiento_Objetivo_TP_Pct']:.2f}%",
                "#10b981",
                "1.3rem",
                "0.7rem",
            ),
            unsafe_allow_html=True,
        )
    with sc7:
        st.markdown(
            tarjeta_metrica_html(
                "GAP TP", f"{kpis['Gap_TP']:,.0f}", "#ef4444", "1.3rem", "0.7rem"
            ),
            unsafe_allow_html=True,
        )
    with sc8:
        st.markdown(
            tarjeta_metrica_html(
                "EXCEDENTE TP",
                f"{kpis['Excedente_TP']:,.0f}",
                "#14b8a6",
                "1.3rem",
                "0.7rem",
            ),
            unsafe_allow_html=True,
        )
    if sc_sel or estado_tp_sel != "Todos":
        st.caption(
            "El objetivo permanece como referencia del snapshot congelado por vendedor y taxonomía; SubCanal y Estado TP solo filtran el realizado."
        )

    st.divider()

    st.markdown("#### 📊 Rankings Institucionales de Tienda Perfecta")

    dimension_sel = st.radio(
        "Seleccione Dimensión de Análisis",
        options=["Vendedor", "SubCanal", "Taxonomía"],
        horizontal=True,
        key="tp_core_dimension_analisis",
    )

    if dimension_sel == "Vendedor":
        st.markdown("##### Cumplimiento y Puntuación por Vendedor (Padrón Completo)")
        if not ranking_vendedor.empty:
            gb_v = GridOptionsBuilder.from_dataframe(ranking_vendedor)
            gb_v.configure_default_column(
                filterable=True, sortable=True, resizable=True
            )
            gb_v.configure_column("Vendedor", minWidth=180)
            gb_v.configure_column("Censados", width=100)
            gb_v.configure_column("Clientes_TP", headerName="Clientes TP", width=120)
            gb_v.configure_column(
                "Porcentaje_Cumplimiento_TP",
                headerName="% TP sobre Censados",
                width=140,
                valueFormatter="x != null ? Number(x).toFixed(2) + '%' : '0.00%'",
            )
            if "Objetivo_TP" in ranking_vendedor.columns:
                gb_v.configure_column(
                    "Objetivo_TP", headerName="Objetivo TP", width=115
                )
                gb_v.configure_column(
                    "Cumplimiento_Objetivo_TP_Pct",
                    headerName="% Cumplimiento Objetivo",
                    width=175,
                    valueFormatter="x != null ? Number(x).toFixed(2) + '%' : '0.00%'",
                )
                gb_v.configure_column("Gap_TP", headerName="Gap TP", width=95)
                gb_v.configure_column(
                    "Excedente_TP", headerName="Excedente TP", width=115
                )
            gb_v.configure_column(
                "Puntuacion_Promedio",
                headerName="Puntuación Promedio",
                width=150,
                valueFormatter="x != null ? Number(x).toFixed(2) : '0.00'",
            )
            gb_v.configure_pagination(
                paginationAutoPageSize=False, paginationPageSize=15
            )
            AgGrid(
                ranking_vendedor,
                gridOptions=gb_v.build(),
                height=380,
                width="100%",
                theme="streamlit",
            )
        else:
            st.info("Sin datos para mostrar en el ranking de vendedores.")

    elif dimension_sel == "SubCanal":
        st.markdown("##### Cumplimiento y Puntuación por SubCanal")
        if not ranking_subcanal.empty:
            gb_sc = GridOptionsBuilder.from_dataframe(ranking_subcanal)
            gb_sc.configure_default_column(
                filterable=True, sortable=True, resizable=True
            )
            gb_sc.configure_column("SubCanal", minWidth=180)
            gb_sc.configure_column(
                "Porcentaje_Cumplimiento_TP",
                headerName="% TP sobre Censados",
                width=140,
                valueFormatter="x != null ? Number(x).toFixed(2) + '%' : '0.00%'",
            )
            gb_sc.configure_column(
                "Puntuacion_Promedio",
                headerName="Puntuación Promedio",
                width=150,
                valueFormatter="x != null ? Number(x).toFixed(2) : '0.00'",
            )
            gb_sc.configure_pagination(
                paginationAutoPageSize=False, paginationPageSize=15
            )
            AgGrid(
                ranking_subcanal,
                gridOptions=gb_sc.build(),
                height=380,
                width="100%",
                theme="streamlit",
            )
        else:
            st.info("Sin datos para mostrar en el ranking de subcanales.")

    elif dimension_sel == "Taxonomía":
        st.markdown("##### Cumplimiento y Puntuación por Taxonomía")
        if not ranking_taxonomia.empty:
            gb_tx = GridOptionsBuilder.from_dataframe(ranking_taxonomia)
            gb_tx.configure_default_column(
                filterable=True, sortable=True, resizable=True
            )
            gb_tx.configure_column("Taxonomia", headerName="Taxonomía", width=120)
            gb_tx.configure_column(
                "Porcentaje_Cumplimiento_TP",
                headerName="% TP sobre Censados",
                width=140,
                valueFormatter="x != null ? Number(x).toFixed(2) + '%' : '0.00%'",
            )
            if "Objetivo_TP" in ranking_taxonomia.columns:
                gb_tx.configure_column(
                    "Objetivo_TP", headerName="Objetivo TP", width=115
                )
                gb_tx.configure_column(
                    "Cumplimiento_Objetivo_TP_Pct",
                    headerName="% Cumplimiento Objetivo",
                    width=175,
                    valueFormatter="x != null ? Number(x).toFixed(2) + '%' : '0.00%'",
                )
                gb_tx.configure_column("Gap_TP", headerName="Gap TP", width=95)
                gb_tx.configure_column(
                    "Excedente_TP", headerName="Excedente TP", width=115
                )
            gb_tx.configure_column(
                "Puntuacion_Promedio",
                headerName="Puntuación Promedio",
                width=150,
                valueFormatter="x != null ? Number(x).toFixed(2) : '0.00'",
            )
            gb_tx.configure_pagination(
                paginationAutoPageSize=False, paginationPageSize=15
            )
            AgGrid(
                ranking_taxonomia,
                gridOptions=gb_tx.build(),
                height=380,
                width="100%",
                theme="streamlit",
            )
        else:
            st.info("Sin datos para mostrar en el ranking de taxonomías.")

    st.divider()

    st.markdown("### ⚔️ Tabla de Oportunidades (Clientes con Menor Puntuación)")
    st.markdown(
        "Listado de puntos de venta ordenados de menor a mayor puntuación en Tienda Perfecta para focalizar la gestión correctiva."
    )

    filtros_activos = bool(v_sel or sc_sel or tx_sel or estado_tp_sel != "Todos")

    if not filtros_activos:
        st.info(
            "ℹ️ Seleccione al menos un filtro (Vendedor, SubCanal, Taxonomía o Estado TP) para consultar oportunidades."
        )
    else:
        if not tabla_oportunidades.empty:
            tabla_op_display = tabla_oportunidades.copy()
            tabla_op_display.columns = [
                "Vendedor",
                "Cliente_id",
                "Razón Social",
                "SubCanal",
                "Taxonomía",
                "Puntuación TP",
                "Tienda Perfecta",
            ]
            tabla_op_display["Puntuación TP"] = pd.to_numeric(
                tabla_op_display["Puntuación TP"], errors="coerce"
            ).fillna(0.0)

            gb_op = GridOptionsBuilder.from_dataframe(tabla_op_display)
            gb_op.configure_default_column(
                filterable=True, sortable=True, resizable=True
            )
            gb_op.configure_column("Vendedor", minWidth=160)
            gb_op.configure_column("Cliente_id", width=110)
            gb_op.configure_column("Razón Social", minWidth=180)
            gb_op.configure_column("SubCanal", minWidth=140)
            gb_op.configure_column("Taxonomía", width=100)
            gb_op.configure_column(
                "Puntuación TP",
                width=130,
                valueFormatter="x != null ? Number(x).toFixed(2) : '0.00'",
            )
            gb_op.configure_column("Tienda Perfecta", width=130)
            gb_op.configure_pagination(
                paginationAutoPageSize=False, paginationPageSize=15
            )

            AgGrid(
                tabla_op_display,
                gridOptions=gb_op.build(),
                height=400,
                width="100%",
                theme="streamlit",
            )

            if "tp_core_generar_excel" not in st.session_state:
                st.session_state["tp_core_generar_excel"] = False

            col_btn1, col_btn2 = st.columns([2, 2])
            with col_btn1:
                if st.button(
                    "📥 Generar Archivo Excel para Descarga",
                    key="btn_trigger_excel_tp_core",
                ):
                    st.session_state["tp_core_generar_excel"] = True

            if st.session_state.get("tp_core_generar_excel", False):
                excel_bytes = _generar_excel_tp_core(
                    ranking_vendedor,
                    ranking_subcanal,
                    ranking_taxonomia,
                    tabla_oportunidades,
                )
                st.download_button(
                    label="💾 Descargar Reporte Tienda Perfecta (.xlsx)",
                    data=excel_bytes,
                    file_name="Reporte_Tienda_Perfecta.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_dl_tp_core_excel",
                )
        else:
            st.info(
                "No hay registros para la tabla de oportunidades con los filtros seleccionados."
            )


def render_rep_tp_core(bases=None, filtros_globales=None):
    """
    Módulo analítico desacoplado de Tienda Perfecta (TP) basado en la capa Business Rules.
    Ejecuta Business Rules una sola vez, aislando la interacción visual mediante @st.fragment.
    """
    t_rep_start = time.perf_counter()

    st.subheader("⭐ Auditoría de Ejecución - Tienda Perfecta (TP)")
    st.markdown(
        "Análisis de cumplimiento de surtido ideal, planogramas, racks y estándares de ejecución en punto de venta."
    )

    # Ejecución única de Business Rules
    br_data = generar_business_rules_tp()

    if not br_data or not isinstance(br_data, dict):
        st.warning(
            "⚠️ No se pudieron cargar los datos de Tienda Perfecta desde Business Rules."
        )
        return

    # Renderizado del fragmento interactivo con respuesta instantánea
    render_fragmento_interactivo_tp(br_data)

    t_dur = time.perf_counter() - t_rep_start
    print(f"[PERF_TP] render_rep_tp_core = {t_dur:.2f} s")
