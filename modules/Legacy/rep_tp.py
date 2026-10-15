# modules/rep_tp.py
import io
import time
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import tarjeta_metrica_html


@st.cache_data(show_spinner=False)
def _preparar_estatico_tp_cached(df_raw_hash, df_raw):
    """
    Capa 1: Preparación estática cacheada de forma inteligente mediante hash de datos crudos.
    Garantiza velocidad de respuesta instantánea y se invalida automáticamente ante cambios en la fuente.
    """
    t_start = time.perf_counter()
    df = df_raw.copy() if df_raw is not None else pd.DataFrame()
    if df.empty:
        return pd.DataFrame(), [], [], [], ["DataFrame vacío"]

    df.columns = [str(c).strip() for c in df.columns]

    col_cliente = "Cliente_id"
    col_vendedor = "Vendedor"
    col_razon = "Razon Social"
    col_subcanal = "SubCanal"
    col_tax = "Taxonomía"
    col_score = "Puntuación"
    col_tp_flag = "Tienda \nPerfecta"

    columnas_faltantes = [
        c
        for c in [
            col_cliente,
            col_vendedor,
            col_razon,
            col_subcanal,
            col_tax,
            col_score,
            col_tp_flag,
        ]
        if c not in df.columns
    ]
    if columnas_faltantes:
        return pd.DataFrame(), [], [], [], columnas_faltantes

    df["_Cliente_id"] = pd.to_numeric(df[col_cliente], errors="coerce")

    # Carga y cruce con maestro_vendedores idéntico al estándar CCC
    try:
        df_m = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    except Exception:
        df_m = pd.DataFrame()

    if not df_m.empty:
        col_c_v = next(
            (
                c
                for c in ["Codigo_Vendedor", "CodVend", "CodVendedor"]
                if c in df_m.columns
            ),
            df_m.columns[0],
        )
        col_n_v = next(
            (c for c in ["Nombre_Vendedor", "Nombre"] if c in df_m.columns),
            df_m.columns[1] if len(df_m.columns) > 1 else df_m.columns[0],
        )
        col_s_v = next(
            (c for c in ["Supervisor", "SUP"] if c in df_m.columns),
            df_m.columns[2] if len(df_m.columns) > 2 else df_m.columns[0],
        )

        df_m_clean = pd.DataFrame()
        df_m_clean["CodVen"] = pd.to_numeric(df_m[col_c_v], errors="coerce").astype(
            "Int64"
        )
        df_m_clean["NombreVen"] = (
            df_m[col_n_v].fillna("SIN NOMBRE").astype(str).str.strip()
        )
        df_m_clean["SupVen"] = df_m[col_s_v].fillna("GENERAL").astype(str).str.strip()
        df_m_clean = df_m_clean.drop_duplicates("CodVen")

        df["_CodVendedor"] = pd.to_numeric(df[col_vendedor], errors="coerce").astype(
            "Int64"
        )
        df = df.merge(df_m_clean, left_on="_CodVendedor", right_on="CodVen", how="left")

        df["_CodVendedor"] = df["CodVen"].fillna(df["_CodVendedor"])
        df["_VendedorNombre"] = (
            df["NombreVen"].fillna(df[col_vendedor].astype(str)).str.strip()
        )
        df["_Supervisor"] = df["SupVen"].fillna("GENERAL").str.strip()
    else:
        df["_CodVendedor"] = pd.to_numeric(df[col_vendedor], errors="coerce").astype(
            "Int64"
        )
        df["_VendedorNombre"] = (
            df[col_vendedor].fillna("SIN VENDEDOR").astype(str).str.strip()
        )
        df["_Supervisor"] = "GENERAL"

    df["_Vendedor"] = df["_VendedorNombre"]
    df["_SubCanal"] = df[col_subcanal].fillna("SIN SUBCANAL").astype(str).str.strip()
    df["_Taxonomia"] = (
        df[col_tax].fillna("SIN TAXONOMIA").astype(str).str.strip().str.upper()
    )
    df["_RazonSocial"] = (
        df[col_razon].fillna("CLIENTE SIN NOMBRE").astype(str).str.strip()
    )

    df["_Es_TP"] = (
        df[col_tp_flag].fillna("").astype(str).str.strip().str.upper() == "SI"
    )
    df["_Score"] = pd.to_numeric(df[col_score], errors="coerce").fillna(0.0)

    vendedores_disp = sorted(df["_Vendedor"].unique().tolist())
    subcanales_disp = sorted(df["_SubCanal"].unique().tolist())
    taxonomias_disp = sorted(df["_Taxonomia"].unique().tolist())

    t_dur = time.perf_counter() - t_start
    print(f"[PERF_TP] _preparar_estatico_tp_cached = {t_dur:.2f} s")

    return df, vendedores_disp, subcanales_disp, taxonomias_disp, []


def _filtrar_tp(df, v_tuple, sc_tuple, tx_tuple, estado_tp="Todos"):
    """
    Capa 2: Filtrado dinámico interactivo en base a tuplas inmutables y el filtro de Estado TP.
    """
    t_start = time.perf_counter()
    df_filtered = df.copy()
    if v_tuple:
        df_filtered = df_filtered[df_filtered["_Vendedor"].isin(v_tuple)]
    if sc_tuple:
        df_filtered = df_filtered[df_filtered["_SubCanal"].isin(sc_tuple)]
    if tx_tuple:
        df_filtered = df_filtered[df_filtered["_Taxonomia"].isin(tx_tuple)]

    if estado_tp == "SI":
        df_filtered = df_filtered[df_filtered["_Es_TP"] == True]
    elif estado_tp == "NO":
        df_filtered = df_filtered[df_filtered["_Es_TP"] == False]
    elif estado_tp == "Menos de 70%":
        col_cumpl = "% De cumplimiento de surtido ideal"
        if col_cumpl not in df_filtered.columns:
            col_cumpl = next(
                (
                    c
                    for c in df_filtered.columns
                    if "cumplimiento" in c.lower() and "surtido" in c.lower()
                ),
                "_Score",
            )
        s_vals = pd.to_numeric(
            df_filtered.get(col_cumpl, df_filtered["_Score"]), errors="coerce"
        ).fillna(0.0)
        df_filtered = df_filtered[(s_vals >= 0) & (s_vals < 70)]
    elif estado_tp == "Entre 70% y 80%":
        col_cumpl = "% De cumplimiento de surtido ideal"
        if col_cumpl not in df_filtered.columns:
            col_cumpl = next(
                (
                    c
                    for c in df_filtered.columns
                    if "cumplimiento" in c.lower() and "surtido" in c.lower()
                ),
                "_Score",
            )
        s_vals = pd.to_numeric(
            df_filtered.get(col_cumpl, df_filtered["_Score"]), errors="coerce"
        ).fillna(0.0)
        df_filtered = df_filtered[(s_vals >= 70) & (s_vals < 80)]

    t_dur = time.perf_counter() - t_start
    print(f"[PERF_TP] _filtrar_tp = {t_dur:.2f} s")
    return df_filtered


@st.cache_data(show_spinner=False)
def _calcular_rankings_tp(df_filtered, vendedores_tuple):
    """
    Capa 3: Cálculo cacheado de agrupaciones, cruces y rankings institucionales.
    """
    t_tot_start = time.perf_counter()

    t_s1 = time.perf_counter()
    padron_vendedores = pd.DataFrame({"Vendedor": list(vendedores_tuple)})

    agrup_vend = (
        df_filtered.groupby("_Vendedor", as_index=False)
        .agg(
            Censados=("_Cliente_id", "nunique"),
            Clientes_TP=("_Es_TP", lambda x: int(x.sum())),
            Puntuacion_Promedio=("_Score", "mean"),
        )
        .rename(columns={"_Vendedor": "Vendedor"})
    )

    ranking_vendedor = padron_vendedores.merge(
        agrup_vend, on="Vendedor", how="left"
    ).fillna({"Censados": 0, "Clientes_TP": 0, "Puntuacion_Promedio": 0.0})

    ranking_vendedor["Censados"] = ranking_vendedor["Censados"].astype(int)
    ranking_vendedor["Clientes_TP"] = ranking_vendedor["Clientes_TP"].astype(int)
    ranking_vendedor["% Cumplimiento TP"] = (
        (
            ranking_vendedor["Clientes_TP"]
            / ranking_vendedor["Censados"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    ranking_vendedor["Puntuación Promedio"] = ranking_vendedor[
        "Puntuacion_Promedio"
    ].round(2)

    ranking_vendedor = ranking_vendedor[
        [
            "Vendedor",
            "Censados",
            "Clientes_TP",
            "% Cumplimiento TP",
            "Puntuación Promedio",
        ]
    ]
    ranking_vendedor = ranking_vendedor.sort_values(
        by=["% Cumplimiento TP", "Censados"], ascending=[False, False]
    ).reset_index(drop=True)
    t_d1 = time.perf_counter() - t_s1
    print(f"[PERF_TP] Generación ranking_vendedor = {t_d1:.2f} s")

    t_s2 = time.perf_counter()
    ranking_subcanal = (
        df_filtered.groupby("_SubCanal", as_index=False)
        .agg(
            Censados=("_Cliente_id", "nunique"),
            Clientes_TP=("_Es_TP", lambda x: int(x.sum())),
            Puntuacion_Promedio=("_Score", "mean"),
        )
        .rename(columns={"_SubCanal": "SubCanal"})
    )

    ranking_subcanal["% Cumplimiento TP"] = (
        (
            ranking_subcanal["Clientes_TP"]
            / ranking_subcanal["Censados"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    ranking_subcanal["Puntuación Promedio"] = ranking_subcanal[
        "Puntuacion_Promedio"
    ].round(2)
    ranking_subcanal = ranking_subcanal[
        [
            "SubCanal",
            "Censados",
            "Clientes_TP",
            "% Cumplimiento TP",
            "Puntuación Promedio",
        ]
    ]
    ranking_subcanal = ranking_subcanal.sort_values(
        by="% Cumplimiento TP", ascending=False
    ).reset_index(drop=True)
    t_d2 = time.perf_counter() - t_s2
    print(f"[PERF_TP] Generación ranking_subcanal = {t_d2:.2f} s")

    t_s3 = time.perf_counter()
    ranking_taxonomia = (
        df_filtered.groupby("_Taxonomia", as_index=False)
        .agg(
            Censados=("_Cliente_id", "nunique"),
            Clientes_TP=("_Es_TP", lambda x: int(x.sum())),
            Puntuacion_Promedio=("_Score", "mean"),
        )
        .rename(columns={"_Taxonomia": "Taxonomía"})
    )

    ranking_taxonomia["% Cumplimiento TP"] = (
        (
            ranking_taxonomia["Clientes_TP"]
            / ranking_taxonomia["Censados"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    ranking_taxonomia["Puntuación Promedio"] = ranking_taxonomia[
        "Puntuacion_Promedio"
    ].round(2)
    ranking_taxonomia = ranking_taxonomia[
        [
            "Taxonomía",
            "Censados",
            "Clientes_TP",
            "% Cumplimiento TP",
            "Puntuación Promedio",
        ]
    ]
    ranking_taxonomia = ranking_taxonomia.sort_values(
        by="% Cumplimiento TP", ascending=False
    ).reset_index(drop=True)
    t_d3 = time.perf_counter() - t_s3
    print(f"[PERF_TP] Generación ranking_taxonomia = {t_d3:.2f} s")

    print(
        f"[PERF_TP] _calcular_rankings_tp = {time.perf_counter() - t_tot_start:.2f} s"
    )
    return ranking_vendedor, ranking_subcanal, ranking_taxonomia


@st.cache_data(show_spinner=False)
def _generar_excel_tp(r_vend, r_sub, r_tax, r_op):
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


def render_fragmento_interactivo_tp(vendedores_disp, subcanales_disp, taxonomias_disp):
    """
    Capa Interactiva directa optimizada para máxima fluidez en los filtros locales.
    """
    t_frag_start = time.perf_counter()

    # Telemetría forense: Conteo y lectura de st.session_state (Requisitos E, F y G)
    tp_keys = [k for k in st.session_state.keys() if "_tp_" in k]
    print(
        f"[PERF_FORENSIC] Cantidad total de claves TP activas en session_state: {len(tp_keys)} | Claves: {tp_keys}"
    )
    for k in tp_keys:
        _ = st.session_state[k]
        print(f"[PERF_FORENSIC] Lectura session_state interceptada para clave: '{k}'")

    if "_tp_fragment_invocations" not in st.session_state:
        st.session_state["_tp_fragment_invocations"] = 0
    st.session_state["_tp_fragment_invocations"] += 1
    print(
        f"[PERF_FORENSIC] Cantidad de invocaciones de render_fragmento_interactivo_tp en este ciclo: {st.session_state['_tp_fragment_invocations']}"
    )

    df_prep = st.session_state.get("_tp_df_prep", pd.DataFrame())
    if df_prep.empty:
        st.info("No hay datos disponibles en la sesión.")
        return

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        v_sel = st.multiselect(
            "Filtrar por Vendedor",
            options=vendedores_disp,
            default=[],
            placeholder="Todos los vendedores...",
            key="tp_filtro_vend",
        )
    with col_f2:
        sc_sel = st.multiselect(
            "Filtrar por SubCanal",
            options=subcanales_disp,
            default=[],
            placeholder="Todos los subcanales...",
            key="tp_filtro_subcanal",
        )
    with col_f3:
        tx_sel = st.multiselect(
            "Filtrar por Taxonomía",
            options=taxonomias_disp,
            default=[],
            placeholder="Todas las taxonomías...",
            key="tp_filtro_tax",
        )
    with col_f4:
        estado_tp_sel = st.selectbox(
            "Estado Tienda Perfecta",
            options=["Todos", "SI", "NO", "Menos de 70%", "Entre 70% y 80%"],
            key="tp_filtro_estado_tp",
        )

    # Invocación del filtrado dinámico
    df_filtered = _filtrar_tp(
        df_prep, tuple(v_sel), tuple(sc_sel), tuple(tx_sel), estado_tp_sel
    )

    if df_filtered.empty:
        st.info("No hay registros disponibles para los filtros seleccionados.")
        return

    col_cliente = "Cliente_id"
    col_vendedor = "_Vendedor"
    col_razon = "Razon Social"
    col_subcanal = "_SubCanal"
    col_tax = "_Taxonomia"
    col_score = "_Score"
    col_tp_flag = "Tienda \nPerfecta"

    total_censados = int(
        df_filtered["_Cliente_id"].nunique()
        if df_filtered["_Cliente_id"].notna().any()
        else len(df_filtered)
    )
    total_tp = int(
        df_filtered[df_filtered["_Es_TP"]]["_Cliente_id"].nunique()
        if df_filtered["_Cliente_id"].notna().any()
        else df_filtered["_Es_TP"].sum()
    )
    pct_tp_global = (total_tp / total_censados * 100.0) if total_censados > 0 else 0.0
    promedio_score = (
        float(df_filtered["_Score"].mean()) if not df_filtered.empty else 0.0
    )

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.markdown(
            tarjeta_metrica_html(
                "CLIENTES CENSADOS",
                f"{total_censados:,.0f}",
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
                f"{total_tp:,.0f}",
                "#22c55e",
                "1.3rem",
                "0.7rem",
            ),
            unsafe_allow_html=True,
        )
    with sc3:
        st.markdown(
            tarjeta_metrica_html(
                "% CUMPLIMIENTO TP",
                f"{pct_tp_global:,.2f}%",
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
                f"{promedio_score:,.2f}",
                "#f59e0b",
                "1.3rem",
                "0.7rem",
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    ranking_vendedor, ranking_subcanal, ranking_taxonomia = _calcular_rankings_tp(
        df_filtered, tuple(vendedores_disp)
    )

    st.markdown("#### 📊 Rankings Institucionales de Tienda Perfecta")

    dimension_sel = st.radio(
        "Seleccione Dimensión de Análisis",
        options=["Vendedor", "SubCanal", "Taxonomía"],
        horizontal=True,
        key="tp_dimension_analisis",
    )

    t_ag_start = time.perf_counter()
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
                "% Cumplimiento TP",
                width=140,
                valueFormatter="x != null ? Number(x).toFixed(2) + '%' : '0.00%'",
            )
            gb_v.configure_column(
                "Puntuación Promedio",
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
                "% Cumplimiento TP",
                width=140,
                valueFormatter="x != null ? Number(x).toFixed(2) + '%' : '0.00%'",
            )
            gb_sc.configure_column(
                "Puntuación Promedio",
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
            gb_tx.configure_column("Taxonomía", width=120)
            gb_tx.configure_column(
                "% Cumplimiento TP",
                width=140,
                valueFormatter="x != null ? Number(x).toFixed(2) + '%' : '0.00%'",
            )
            gb_tx.configure_column(
                "Puntuación Promedio",
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
    print(f"[PERF_TP] Renderizado AgGrid = {time.perf_counter() - t_ag_start:.2f} s")

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
        tabla_oportunidades = df_filtered[
            [
                col_vendedor,
                col_cliente,
                "Razon Social",
                col_subcanal,
                col_tax,
                col_score,
                col_tp_flag,
            ]
        ].copy()

        if not tabla_oportunidades.empty:
            tabla_oportunidades.columns = [
                "Vendedor",
                "Cliente_id",
                "Razón Social",
                "SubCanal",
                "Taxonomía",
                "Puntuación TP",
                "Tienda Perfecta",
            ]
            tabla_oportunidades["Puntuación TP"] = pd.to_numeric(
                tabla_oportunidades["Puntuación TP"], errors="coerce"
            ).fillna(0.0)
            tabla_oportunidades = tabla_oportunidades.sort_values(
                by="Puntuación TP", ascending=True
            ).reset_index(drop=True)

            gb_op = GridOptionsBuilder.from_dataframe(tabla_oportunidades)
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
                tabla_oportunidades,
                gridOptions=gb_op.build(),
                height=400,
                width="100%",
                theme="streamlit",
            )

            if "tp_generar_excel" not in st.session_state:
                st.session_state["tp_generar_excel"] = False

            col_btn1, col_btn2 = st.columns([2, 2])
            with col_btn1:
                if st.button(
                    "📥 Generar Archivo Excel para Descarga", key="btn_trigger_excel_tp"
                ):
                    st.session_state["tp_generar_excel"] = True

            if st.session_state.get("tp_generar_excel", False):
                excel_bytes = _generar_excel_tp(
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
                    key="btn_dl_tp_excel",
                )
        else:
            st.info("No hay registros para la tabla de oportunidades.")

    print(
        f"[PERF_TP] render_fragmento_interactivo_tp = {time.perf_counter() - t_frag_start:.2f} s"
    )


def render_rep_tp(bases, filtros_globales=None):
    """
    Módulo analítico de Tienda Perfecta (TP).
    Instrumentado con telemetría forense para diagnóstico avanzado de latencia interactiva.
    """
    t_rep_start = time.perf_counter()

    # Telemetría forense: Medición de delta temporal desde el inicio del rerun (Requisito D)
    t_desde_inicio_rerun = t_rep_start - st.session_state.get(
        "_t_rerun_global_start", t_rep_start
    )
    print(
        f"[PERF_FORENSIC] Momento exacto de entrada a render_rep_tp: {t_rep_start:.4f} s | Delta desde inicio de rerun: {t_desde_inicio_rerun:.4f} s"
    )

    # Telemetría forense: Conteo de invocaciones de render_rep_tp (Requisito H)
    if "_tp_render_invocations" not in st.session_state:
        st.session_state["_tp_render_invocations"] = 0
    st.session_state["_tp_render_invocations"] += 1
    print(
        f"[PERF_FORENSIC] Cantidad de invocaciones de render_rep_tp en este ciclo: {st.session_state['_tp_render_invocations']}"
    )

    st.subheader("⭐ Auditoría de Ejecución - Tienda Perfecta (TP)")
    st.markdown(
        "Análisis de cumplimiento de surtido ideal, planogramas, racks y estándares de ejecución en punto de venta."
    )

    df_tp = bases.get("TP") if bases is not None else pd.DataFrame()

    if df_tp is None or df_tp.empty:
        st.warning(
            "⚠️ No se encontró la tabla 'TP' cargada en el sistema. Verifique que el archivo TP.xlsx se encuentre en la carpeta /data/."
        )
        return

    sup_filtro = "TODOS"
    if filtros_globales and isinstance(filtros_globales, dict):
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()
    else:
        sup_filtro = str(st.session_state.get("sel_sup_op", "TODOS")).strip()

    df_hash = f"{len(df_tp)}_{int(df_tp['Cliente_id'].dropna().astype(float).sum()) if 'Cliente_id' in df_tp.columns and not df_tp.empty else 0}"

    df_prep, vendedores_disp, subcanales_disp, taxonomias_disp, columnas_faltantes = (
        _preparar_estatico_tp_cached(df_hash, df_tp)
    )
    if columnas_faltantes:
        st.error(
            f"⚠️ La fuente TP no contiene las columnas obligatorias: {', '.join(columnas_faltantes)}"
        )
        return

    if sup_filtro != "TODOS" and "_Supervisor" in df_prep.columns:
        df_prep = df_prep[
            df_prep["_Supervisor"].astype(str).str.strip().str.casefold()
            == sup_filtro.casefold()
        ].copy()
        vendedores_disp = sorted(df_prep["_Vendedor"].unique().tolist())
        subcanales_disp = sorted(df_prep["_SubCanal"].unique().tolist())
        taxonomias_disp = sorted(df_prep["_Taxonomia"].unique().tolist())

    st.session_state["_tp_df_prep"] = df_prep

    render_fragmento_interactivo_tp(vendedores_disp, subcanales_disp, taxonomias_disp)
    print(f"[PERF_TP] render_rep_tp = {time.perf_counter() - t_rep_start:.2f} s")
