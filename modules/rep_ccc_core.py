# modules/reportes/rep_ccc_core.py
import time
import io
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode

from modules.business_rules.business_rules_ccc import (
    obtener_matriz_ccc_comercial,
    obtener_detalle_clientes_ccc,
)
from modules import database as db


def _tarjeta_metrica_compacta_html(
    label: str, valor: str, border_color: str = "#475569", border_width: str = "1px"
) -> str:
    """Helper visual institucional para tarjetas compactas de métricas."""
    return f"""
    <div style="
        background-color: #1e293b;
        border: {border_width} solid {border_color};
        border-radius: 6px;
        padding: 4px 6px;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        margin-bottom: 3px;
    ">
        <div style="font-size: 0.6rem; color: #94a3b8; font-weight: 600; margin-bottom: 2px; text-transform: uppercase;">{label}</div>
        <div style="font-size: 1.0rem; color: #f8fafc; font-weight: 700;">{valor}</div>
    </div>
    """


@st.fragment
def render_fragmento_interactivo_ccc_core(
    matriz_ccc: pd.DataFrame,
    detalle_ccc: pd.DataFrame,
    sup_seleccionado: str,
    dia_matinal: str,
):
    """
    Fragmento interactivo de presentación para CCC.
    Aplica filtros locales (Vendedor, Taxonomía, Día de Visita) sin recalcular reglas de negocio.
    Renderiza KPIs, Grilla 1 (Resumen CCC), Grilla 2 (Batalla CCC) y botones de exportación a Excel.
    """
    if matriz_ccc is None or matriz_ccc.empty:
        st.info("No hay datos disponibles para procesar el reporte CCC.")
        return

    df_resumen_base = matriz_ccc.copy()
    df_detalle_base = detalle_ccc.copy() if detalle_ccc is not None else pd.DataFrame()

    # Fallbacks seguros para columnas obligatorias del resumen
    if "Nombre" not in df_resumen_base.columns:
        df_resumen_base["Nombre"] = "SIN ASIGNAR"
    if "Taxonomia" not in df_resumen_base.columns:
        df_resumen_base["Taxonomia"] = "A"
    if "SUP" not in df_resumen_base.columns:
        df_resumen_base["SUP"] = "GENERAL"

    # Filtro por supervisor proveniente de filtros globales
    if sup_seleccionado != "TODOS" and "SUP" in df_resumen_base.columns:
        df_resumen_base = df_resumen_base[
            df_resumen_base["SUP"].astype(str).str.strip()
            == str(sup_seleccionado).strip()
        ].copy()
        if not df_detalle_base.empty and "SUP" in df_detalle_base.columns:
            df_detalle_base = df_detalle_base[
                df_detalle_base["SUP"].astype(str).str.strip()
                == str(sup_seleccionado).strip()
            ].copy()

    if df_resumen_base.empty:
        st.info("No se encontraron registros para el supervisor seleccionado.")
        return

    # Opciones de filtros locales
    v_dispo = sorted(
        df_resumen_base["Nombre"].dropna().astype(str).str.strip().unique().tolist()
    )
    tax_dispo = sorted(
        df_resumen_base["Taxonomia"].dropna().astype(str).str.strip().unique().tolist()
    )

    orden_dias = [
        "LUNES",
        "MARTES",
        "MIERCOLES",
        "JUEVES",
        "VIERNES",
        "SABADO",
        "DOMINGO",
        "SIN DÍA",
    ]

    if not df_detalle_base.empty:
        if "DiaVisita" not in df_detalle_base.columns:
            df_detalle_base["DiaVisita"] = "SIN DÍA"
        dias_en_datos = (
            df_detalle_base["DiaVisita"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )
    else:
        dias_en_datos = []

    dia_visita_dispo = [d for d in orden_dias if d in dias_en_datos]
    for d in dias_en_datos:
        if d not in dia_visita_dispo:
            dia_visita_dispo.append(d)

    # Controles de filtros locales
    col_fc1, col_fc2, col_fc3 = st.columns(3)
    with col_fc1:
        v_selec = st.multiselect(
            "Vendedor",
            options=v_dispo,
            default=[],
            placeholder="Seleccionar preventistas...",
            key=f"core_ccc_vendedor_{sup_seleccionado}",
        )
    with col_fc2:
        tax_selec = st.multiselect(
            "Taxonomía",
            options=tax_dispo,
            default=[],
            placeholder="Seleccionar taxonomías...",
            key=f"core_ccc_taxonomia_{sup_seleccionado}",
        )
    with col_fc3:
        dia_visita_selec = st.multiselect(
            "Día de Visita",
            options=dia_visita_dispo,
            default=[],
            placeholder="Seleccionar días de visita...",
            key=f"core_ccc_dia_visita_{sup_seleccionado}",
        )

    if not v_selec:
        v_selec = v_dispo
    if not tax_selec:
        tax_selec = tax_dispo
    if not dia_visita_selec:
        dia_visita_selec = dia_visita_dispo

    # Filtrar Resumen
    mask_res = df_resumen_base["Nombre"].astype(str).str.strip().isin(
        v_selec
    ) & df_resumen_base["Taxonomia"].astype(str).str.strip().isin(tax_selec)
    df_resumen_filtrado = df_resumen_base[mask_res].copy()

    # Filtrar Detalle si aplica
    if not df_detalle_base.empty:
        if "Nombre" not in df_detalle_base.columns:
            df_detalle_base["Nombre"] = "SIN ASIGNAR"
        if "Taxonomia" not in df_detalle_base.columns:
            df_detalle_base["Taxonomia"] = "A"

        mask_det = df_detalle_base["Nombre"].astype(str).str.strip().isin(
            v_selec
        ) & df_detalle_base["Taxonomia"].astype(str).str.strip().isin(tax_selec)
        if dia_visita_selec and "DiaVisita" in df_detalle_base.columns:
            mask_det = mask_det & df_detalle_base["DiaVisita"].astype(
                str
            ).str.strip().isin(dia_visita_selec)
        df_detalle_filtrado = df_detalle_base[mask_det].copy()
    else:
        df_detalle_filtrado = pd.DataFrame()

    # Lógica ES_DEL_DIA basada estrictamente en la tabla rutas (Fecha, Codigo)
    clientes_del_dia_set = set()
    if dia_matinal and str(dia_matinal).strip():
        try:
            df_rutas_db = db.cargar_tabla_sql("SELECT * FROM rutas")
            if df_rutas_db is not None and not df_rutas_db.empty:
                df_rutas = df_rutas_db.copy()
                df_rutas["Fecha_dt"] = pd.to_datetime(
                    df_rutas["Fecha"], errors="coerce"
                )
                dia_matinal_dt = pd.to_datetime(
                    dia_matinal, format="%d/%m/%Y", errors="coerce"
                )
                if pd.notna(dia_matinal_dt):
                    rutas_dia = df_rutas[
                        df_rutas["Fecha_dt"].dt.date == dia_matinal_dt.date()
                    ]
                    if "Codigo" in rutas_dia.columns:
                        s_cod = (
                            pd.to_numeric(rutas_dia["Codigo"], errors="coerce")
                            .dropna()
                            .astype("Int64")
                        )
                        clientes_del_dia_set = set(s_cod.dropna().astype(int).tolist())
        except Exception:
            pass

    if not df_detalle_filtrado.empty:
        s_cli = pd.to_numeric(df_detalle_filtrado["Cliente"], errors="coerce")
        df_detalle_filtrado["ES_DEL_DIA"] = np.where(
            s_cli.isin(clientes_del_dia_set), "✅ SI", "❌ NO"
        )
    else:
        if "ES_DEL_DIA" not in df_detalle_filtrado.columns:
            df_detalle_filtrado["ES_DEL_DIA"] = "❌ NO"

    # KPIs solicitados (Sin CCC_Gerencia)
    tot_cartera = (
        int(df_resumen_filtrado["Cartera_Total"].sum())
        if not df_resumen_filtrado.empty
        else 0
    )
    tot_altas = (
        int(df_resumen_filtrado["Altas"].sum()) if not df_resumen_filtrado.empty else 0
    )
    tot_reactivaciones = (
        int(df_resumen_filtrado["Reactivaciones"].sum())
        if not df_resumen_filtrado.empty
        else 0
    )
    tot_cartera_neta = (
        int(df_resumen_filtrado["Cartera_Neta"].sum())
        if not df_resumen_filtrado.empty
        else 0
    )
    tot_ccc_vendedor = (
        int(df_resumen_filtrado["CCC_Vendedor"].sum())
        if not df_resumen_filtrado.empty
        else 0
    )
    tot_nc = (
        int(df_resumen_filtrado["NC"].sum()) if not df_resumen_filtrado.empty else 0
    )
    tot_objetivo_ccc = (
        int(df_resumen_filtrado["Objetivo_CCC"].sum())
        if not df_resumen_filtrado.empty
        else 0
    )

    pct_cartera_global = (
        (tot_ccc_vendedor / tot_cartera_neta * 100.0) if tot_cartera_neta > 0 else 0.0
    )
    pct_objetivo_global = (
        (tot_ccc_vendedor / tot_objetivo_ccc * 100.0) if tot_objetivo_ccc > 0 else 0.0
    )

    st.markdown(
        """
        <style>
        hr {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            border-color: #334155 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    cols_kpi1 = st.columns(4)
    with cols_kpi1[0]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "CARTERA TOTAL", f"{tot_cartera:,.0f}", "#38bdf8", "2px"
            ),
            unsafe_allow_html=True,
        )
    with cols_kpi1[1]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "ALTAS", f"{tot_altas:,.0f}", "#38bdf8", "2px"
            ),
            unsafe_allow_html=True,
        )
    with cols_kpi1[2]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "REACTIVACIONES", f"{tot_reactivaciones:,.0f}", "#38bdf8", "2px"
            ),
            unsafe_allow_html=True,
        )
    with cols_kpi1[3]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "CARTERA NETA", f"{tot_cartera_neta:,.0f}", "#ffffff", "2px"
            ),
            unsafe_allow_html=True,
        )

    cols_kpi2 = st.columns(5)
    with cols_kpi2[0]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "CCC VENDEDOR", f"{tot_ccc_vendedor:,.0f}", "#3b82f6", "2px"
            ),
            unsafe_allow_html=True,
        )
    with cols_kpi2[1]:
        st.markdown(
            _tarjeta_metrica_compacta_html("NC", f"{tot_nc:,.0f}", "#ef4444", "1px"),
            unsafe_allow_html=True,
        )
    with cols_kpi2[2]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "OBJETIVO CCC", f"{tot_objetivo_ccc:,.0f}", "#3b82f6", "1px"
            ),
            unsafe_allow_html=True,
        )
    with cols_kpi2[3]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "% CARTERA", f"{pct_cartera_global:,.2f}%", "#22c55e", "1px"
            ),
            unsafe_allow_html=True,
        )
    with cols_kpi2[4]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "% OBJETIVO", f"{pct_objetivo_global:,.2f}%", "#22c55e", "1px"
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    # --------------------------------------------------
    # GRILLA 1: Resumen CCC (Sin CCC_Gerencia)
    # --------------------------------------------------
    st.subheader("📋 Resumen CCC por Taxonomía y Vendedor")
    if not df_resumen_filtrado.empty:
        display_resumen = df_resumen_filtrado.copy()
        if "CCC_Gerencia" in display_resumen.columns:
            display_resumen = display_resumen.drop(columns=["CCC_Gerencia"])

        for col_p in ["Pct_Cartera", "Pct_Objetivo"]:
            if col_p in display_resumen.columns:
                display_resumen[col_p] = display_resumen[col_p].apply(
                    lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%"
                )

        gb1 = GridOptionsBuilder.from_dataframe(display_resumen)
        gb1.configure_default_column(
            filterable=True, sortable=True, resizable=True, minWidth=110
        )
        gb1.configure_column("CodVendedor", headerName="Cód. Vend", width=90)
        gb1.configure_column("Nombre", headerName="Preventista", minWidth=150)
        gb1.configure_column("SUP", headerName="SUP", width=75)
        gb1.configure_column("Taxonomia", headerName="Tax", width=70)
        gb1.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_opts1 = gb1.build()

        AgGrid(
            display_resumen,
            gridOptions=grid_opts1,
            height=380,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=False,
        )
    else:
        st.info("No hay datos en el resumen CCC para los filtros seleccionados.")

    st.divider()

    # --------------------------------------------------
    # GRILLA 2: BATALLA CCC (Reconciliado exacto contra NC y con ES_DEL_DIA)
    # --------------------------------------------------
    st.subheader("⚔️ BATALLA CCC")
    if not df_detalle_filtrado.empty:
        df_batalla = df_detalle_filtrado.copy()
        if "Es_CCC_Vendedor" in df_batalla.columns:
            df_batalla = df_batalla[df_batalla["Es_CCC_Vendedor"] == False].copy()
        if "Es_Alta_Periodo" in df_batalla.columns:
            df_batalla = df_batalla[df_batalla["Es_Alta_Periodo"] == False].copy()
        if "Es_Reactivacion" in df_batalla.columns:
            df_batalla = df_batalla[df_batalla["Es_Reactivacion"] == False].copy()

        cols_batalla_requeridas = [
            "Cliente",
            "NombreCliente",
            "CodVendedor_Titular",
            "Nombre",
            "SUP",
            "Taxonomia",
            "DiaVisita",
            "Origen_CCC",
            "ES_DEL_DIA",
        ]
        df_batalla_view = pd.DataFrame()
        for c in cols_batalla_requeridas:
            if c in df_batalla.columns:
                df_batalla_view[c] = df_batalla[c]
            else:
                df_batalla_view[c] = pd.Series(dtype=object)

        gb2 = GridOptionsBuilder.from_dataframe(df_batalla_view)
        gb2.configure_default_column(
            filterable=True, sortable=True, resizable=True, minWidth=110
        )
        gb2.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_opts2 = gb2.build()

        AgGrid(
            df_batalla_view,
            gridOptions=grid_opts2,
            height=400,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=False,
        )
    else:
        st.info("No hay datos de Batalla CCC para los filtros seleccionados.")

    st.divider()

    # --------------------------------------------------
    # EXPORTACIÓN
    # --------------------------------------------------
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        buf_res = io.BytesIO()
        with pd.ExcelWriter(buf_res, engine="openpyxl") as writer:
            df_resumen_export = df_resumen_filtrado.copy()
            if "CCC_Gerencia" in df_resumen_export.columns:
                df_resumen_export = df_resumen_export.drop(columns=["CCC_Gerencia"])
            df_resumen_export.to_excel(writer, index=False, sheet_name="Resumen_CCC")
        buf_res.seek(0)
        st.download_button(
            label="📥 Exportar Resumen CCC",
            data=buf_res,
            file_name="Resumen_CCC.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_dl_resumen_ccc",
        )

    with col_dl2:
        buf_det = io.BytesIO()
        with pd.ExcelWriter(buf_det, engine="openpyxl") as writer:
            df_batalla_export = df_detalle_filtrado.copy()
            if "Es_CCC_Vendedor" in df_batalla_export.columns:
                df_batalla_export = df_batalla_export[
                    df_batalla_export["Es_CCC_Vendedor"] == False
                ].copy()
            if "Es_Alta_Periodo" in df_batalla_export.columns:
                df_batalla_export = df_batalla_export[
                    df_batalla_export["Es_Alta_Periodo"] == False
                ].copy()
            if "Es_Reactivacion" in df_batalla_export.columns:
                df_batalla_export = df_batalla_export[
                    df_batalla_export["Es_Reactivacion"] == False
                ].copy()
            df_batalla_export.to_excel(writer, index=False, sheet_name="Batalla_CCC")
        buf_det.seek(0)
        st.download_button(
            label="📥 Exportar Batalla CCC",
            data=buf_det,
            file_name="Batalla_CCC.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_dl_batalla_ccc",
        )


def render_rep_ccc_core(filtros_globales=None):
    """
    Reporte de CCC bajo Arquitectura Objetivo Oficial (CORE -> BUSINESS_RULES -> REPORTES).
    Consumo puramente analítico y de renderizado visual, sin recálculos propios.
    Valida explícitamente los parámetros obligatorios de año y mes.
    """
    t0 = time.perf_counter()

    if filtros_globales is None:
        raise ValueError("No se recibieron filtros_globales en render_rep_ccc_core().")
    if "anio" not in filtros_globales:
        raise ValueError(
            "Falta el parámetro obligatorio 'anio' dentro de filtros_globales."
        )
    if "mes" not in filtros_globales:
        raise ValueError(
            "Falta el parámetro obligatorio 'mes' dentro de filtros_globales."
        )

    anio_op = int(filtros_globales["anio"])
    mes_op = int(filtros_globales["mes"])
    sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()
    dia_matinal = filtros_globales.get("dia_matinal", None)

    st.subheader("📊 Avance de Clientes con Compra (CCC)")
    st.markdown(
        "Analiza la cobertura de Clientes con Compra (CCC) y la atribución de mérito comercial "
        "por taxonomía, vendedor y detalle de cuenta sobre el universo de cartera."
    )

    # CONSUMO EXCLUSIVO DE BUSINESS_RULES (obtener_matriz_ccc_comercial y obtener_detalle_clientes_ccc)
    matriz_ccc = obtener_matriz_ccc_comercial(anio_op, mes_op, filtros_globales)
    detalle_ccc = obtener_detalle_clientes_ccc(anio_op, mes_op, filtros_globales)

    if matriz_ccc.empty:
        st.info(
            "No se encontraron registros comerciales de CCC para los parámetros seleccionados."
        )
        return

    # Renderizado del fragmento interactivo
    render_fragmento_interactivo_ccc_core(
        matriz_ccc, detalle_ccc, sup_filtro, dia_matinal
    )

    print(
        f"[PERF_CORE] Tiempo total render_rep_ccc_core -> {time.perf_counter() - t0:.4f} s"
    )
