# modules/rep_mn_core.py
import io
import time
import urllib.parse
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode

# REGLA FUNDAMENTAL: Consumo exclusivo de BUSINESS_RULES (Cero acceso a DB, SQLite, RAW, STAGING o CORE)
from modules.business_rules.business_rules_mn import (
    obtener_matriz_mn_comercial,
    calcular_resumen_mn_taxonomia,
)


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
def render_fragmento_interactivo_mn_core(
    matriz_mn: pd.DataFrame, sup_seleccionado: str
):
    """
    Fragmento interactivo de presentación para MiNegocio.
    Aplica filtros visuales locales (Vendedor, Taxonomía, Día de Visita) sin recalcular reglas de negocio.
    Renderiza KPIs, grilla por preventista/taxonomía, detalle caso a caso y botones de exportación.
    """
    if matriz_mn is None or matriz_mn.empty:
        st.info(
            "No hay datos disponibles para procesar el Avance de Adopción MiNegocio."
        )
        return

    df_base = matriz_mn.copy()

    # Filtro visual por Supervisor proveniente de parámetros globales
    if sup_seleccionado != "TODOS" and "SUP" in df_base.columns:
        df_base = df_base[
            df_base["SUP"].astype(str).str.strip() == str(sup_seleccionado).strip()
        ].copy()

    if df_base.empty:
        st.info("No se encontraron registros para los supervisores seleccionados.")
        return

    # Opciones de filtros locales
    v_dispo = sorted(
        df_base["Nombre"].dropna().astype(str).str.strip().unique().tolist()
    )
    tax_dispo = sorted(
        df_base["Taxonomia"].dropna().astype(str).str.strip().unique().tolist()
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
    dias_en_datos = (
        df_base["DiaVisita"].dropna().astype(str).str.strip().unique().tolist()
        if "DiaVisita" in df_base.columns
        else []
    )
    dia_visita_dispo = [d for d in orden_dias if d in dias_en_datos]
    for d in dias_en_datos:
        if d not in dia_visita_dispo:
            dia_visita_dispo.append(d)

    # Controles de filtros visuales locales
    col_fc1, col_fc2, col_fc3 = st.columns(3)
    with col_fc1:
        v_selec = st.multiselect(
            "Vendedor",
            options=v_dispo,
            default=[],
            placeholder="Seleccionar preventistas...",
            key=f"core_mn_vendedor_{sup_seleccionado}",
        )
    with col_fc2:
        tax_selec = st.multiselect(
            "Taxonomía",
            options=tax_dispo,
            default=[],
            placeholder="Seleccionar taxonomías...",
            key=f"core_mn_taxonomia_{sup_seleccionado}",
        )
    with col_fc3:
        dia_visita_selec = st.multiselect(
            "Día de Visita",
            options=dia_visita_dispo,
            default=[],
            placeholder="Seleccionar días de visita...",
            key=f"core_mn_dia_visita_{sup_seleccionado}",
        )

    if not v_selec:
        v_selec = v_dispo
    if not tax_selec:
        tax_selec = tax_dispo
    if not dia_visita_selec:
        dia_visita_selec = dia_visita_dispo

    # Aplicación de filtros locales sobre la vista de detalle
    mask_filtros = (
        df_base["Nombre"].astype(str).str.strip().isin(v_selec)
        & df_base["Taxonomia"].astype(str).str.strip().isin(tax_selec)
        & df_base["DiaVisita"].astype(str).str.strip().isin(dia_visita_selec)
    )
    df_filtrado = df_base[mask_filtros].copy()

    # --------------------------------------------------
    # SECCIÓN 1: KPIs SUPERIORES
    # --------------------------------------------------
    tot_cartera = int(df_filtrado["Cliente"].count()) if not df_filtrado.empty else 0
    tot_ventas = (
        float(df_filtrado["Ventas_Totales"].sum()) if not df_filtrado.empty else 0.0
    )
    tot_mn = (
        float(df_filtrado["Ventas_MiNegocio"].sum()) if not df_filtrado.empty else 0.0
    )
    pct_venta_mn = (tot_mn / tot_ventas * 100.0) if tot_ventas > 0 else 0.0

    cartera_tax = (
        df_filtrado.groupby("Taxonomia")["Cliente"].count()
        if not df_filtrado.empty
        else pd.Series(dtype=int)
    )
    cart_a = cartera_tax.get("A", 0)
    cart_b = cartera_tax.get("B", 0)
    cart_c = cartera_tax.get("C", 0)
    cart_d = cartera_tax.get("D", 0)

    cnt_nodigital = (
        int(df_filtrado["Es_NoDigital"].sum())
        if not df_filtrado.empty and "Es_NoDigital" in df_filtrado.columns
        else 0
    )
    cnt_hibrido = (
        int(df_filtrado["Es_Hibrido"].sum())
        if not df_filtrado.empty and "Es_Hibrido" in df_filtrado.columns
        else 0
    )
    cnt_fully = (
        int(df_filtrado["Es_FullyDigital"].sum())
        if not df_filtrado.empty and "Es_FullyDigital" in df_filtrado.columns
        else 0
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

    cols_r1 = st.columns(3)
    with cols_r1[0]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "VENTAS TOTALES", f"${tot_ventas:,.2f}", "#38bdf8", "2px"
            ),
            unsafe_allow_html=True,
        )
    with cols_r1[1]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "VENTA TOTAL MN+", f"${tot_mn:,.2f}", "#38bdf8", "2px"
            ),
            unsafe_allow_html=True,
        )
    with cols_r1[2]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "% VENTA MN+", f"{pct_venta_mn:,.2f}%", "#38bdf8", "2px"
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    cols_r2 = st.columns(5)
    with cols_r2[0]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "CARTERA TOTAL", f"{tot_cartera:,.0f}", "#3b82f6", "1px"
            ),
            unsafe_allow_html=True,
        )
    with cols_r2[1]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "CARTERA A", f"{cart_a:,.0f}", "#ef4444", "1px"
            ),
            unsafe_allow_html=True,
        )
    with cols_r2[2]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "CARTERA B", f"{cart_b:,.0f}", "#f97316", "1px"
            ),
            unsafe_allow_html=True,
        )
    with cols_r2[3]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "CARTERA C", f"{cart_c:,.0f}", "#eab308", "1px"
            ),
            unsafe_allow_html=True,
        )
    with cols_r2[4]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "CARTERA D", f"{cart_d:,.0f}", "#22c55e", "1px"
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    cols_r3 = st.columns(3)
    with cols_r3[0]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "CLIENTES NO DIGITAL", f"{cnt_nodigital:,.0f}", "#ef4444", "1px"
            ),
            unsafe_allow_html=True,
        )
    with cols_r3[1]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "CLIENTES HÍBRIDOS", f"{cnt_hibrido:,.0f}", "#f97316", "1px"
            ),
            unsafe_allow_html=True,
        )
    with cols_r3[2]:
        st.markdown(
            _tarjeta_metrica_compacta_html(
                "CLIENTES FULLY DIGITAL", f"{cnt_fully:,.0f}", "#22c55e", "1px"
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    # --------------------------------------------------
    # SECCIÓN 3: RESUMEN TAXONOMÍA (calcular_resumen_mn_taxonomia)
    # --------------------------------------------------
    reporte_resumen = calcular_resumen_mn_taxonomia(df_filtrado)

    reporte_render_excel = reporte_resumen.copy()
    reporte_render_display = reporte_resumen.copy()

    cols_pesos_mn = ["Ventas_Totales", "Ventas_MiNegocio"]
    cols_porc_mn = ["% Adopcion", "% No Digital", "% Híbridos", "% FullyDigital"]

    for col in cols_pesos_mn:
        if col in reporte_render_display.columns:
            reporte_render_display[col] = reporte_render_display[col].apply(
                lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
            )
    for col in cols_porc_mn:
        if col in reporte_render_display.columns:
            reporte_render_display[col] = reporte_render_display[col].apply(
                lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%"
            )

    if not reporte_render_display.empty:
        gb = GridOptionsBuilder.from_dataframe(reporte_render_display)
        gb.configure_default_column(
            filterable=True, sortable=True, resizable=True, minWidth=120
        )
        gb.configure_column(
            "CodVendedor",
            headerName="Cód. Vend",
            width=90,
            valueFormatter="x != null ? Number(x).toFixed(0) : ''",
        )
        gb.configure_column("Nombre", headerName="Preventista", minWidth=160)
        gb.configure_column("SUP", headerName="SUP", width=75)
        gb.configure_column("Taxonomia", headerName="Tax", width=70)
        gb.configure_column("Cartera_Total", headerName="Cartera Total", width=100)
        gb.configure_column(
            "Ventas_Totales", headerName="Ventas Totales ($)", width=130
        )
        gb.configure_column("Ventas_MiNegocio", headerName="Ventas App ($)", width=130)
        gb.configure_column("% Adopcion", headerName="% Adopción", width=110)
        gb.configure_column("% No Digital", headerName="% No Digital", width=110)
        gb.configure_column("% Híbridos", headerName="% Híbridos", width=110)
        gb.configure_column("% FullyDigital", headerName="% FullyDigital", width=120)

        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_options = gb.build()

        AgGrid(
            reporte_render_display,
            gridOptions=grid_options,
            height=420,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=False,
        )
    else:
        st.info("No se encontraron registros con los filtros seleccionados.")

    st.divider()

    # --------------------------------------------------
    # SECCIÓN 4: BATALLA MINEGOCIO (EXCLUYE FULLY DIGITAL)
    # --------------------------------------------------
    st.markdown(
        "### ⚔️ Batalla MiNegocio: Detalle Caso a Caso por Cliente (No Digital e Híbridos)"
    )
    st.markdown(
        "Listado de clientes pendientes de conversión digital (excluye FullyDigital), "
        "con montos, porcentaje de adopción y mínimo requerido en $ para alcanzar el 70%."
    )

    if not df_filtrado.empty:
        # Exclusión estricta de FullyDigital consumiendo directamente la bandera de Business Rules
        df_batalla = df_filtrado[df_filtrado["Es_FullyDigital"] == False].copy()

        # Construcción directa de vista visual sin recalcular negocio
        df_batalla_render = pd.DataFrame()
        df_batalla_render["Cód. Vend"] = df_batalla.get(
            "CodVendedor", pd.Series(dtype="Int64")
        )
        df_batalla_render["Preventista"] = df_batalla.get(
            "Nombre", pd.Series(dtype=str)
        )
        df_batalla_render["SUP"] = df_batalla.get("SUP", pd.Series(dtype=str))
        df_batalla_render["Cód. Cliente"] = df_batalla.get(
            "Cliente", pd.Series(dtype="Int64")
        )
        df_batalla_render["Razón Social"] = df_batalla.get(
            "NombreCliente", pd.Series(dtype=str)
        )
        df_batalla_render["Dirección"] = df_batalla.get(
            "DireccionCliente", pd.Series(dtype=str)
        )
        df_batalla_render["Día Visita"] = df_batalla.get(
            "DiaVisita", pd.Series(dtype=str)
        )
        df_batalla_render["Taxonomía"] = df_batalla.get(
            "Taxonomia", pd.Series(dtype=str)
        )
        df_batalla_render["Ventas Totales ($)"] = df_batalla.get(
            "Ventas_Totales", pd.Series(dtype=float)
        )
        df_batalla_render["Ventas App ($)"] = df_batalla.get(
            "Ventas_MiNegocio", pd.Series(dtype=float)
        )
        df_batalla_render["% Adopción"] = df_batalla.get(
            "Pct_MiNegocio", pd.Series(dtype=float)
        )
        df_batalla_render["Faltante Mín. 70% ($)"] = df_batalla.get(
            "Minimo_Facturacion_70", pd.Series(dtype=float)
        )
        df_batalla_render["Categoría App"] = df_batalla.get(
            "Categoria_App", pd.Series(dtype=str)
        )

        df_batalla_render = df_batalla_render.reset_index(drop=True)
    else:
        df_batalla_render = pd.DataFrame(
            columns=[
                "Cód. Vend",
                "Preventista",
                "SUP",
                "Cód. Cliente",
                "Razón Social",
                "Dirección",
                "Día Visita",
                "Taxonomía",
                "Ventas Totales ($)",
                "Ventas App ($)",
                "% Adopción",
                "Faltante Mín. 70% ($)",
                "Categoría App",
            ]
        )

    df_batalla_excel = df_batalla_render.copy()
    df_batalla_display = df_batalla_render.copy()

    for col in ["Ventas Totales ($)", "Ventas App ($)", "Faltante Mín. 70% ($)"]:
        if col in df_batalla_display.columns:
            df_batalla_display[col] = df_batalla_display[col].apply(
                lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
            )
    if "% Adopción" in df_batalla_display.columns:
        df_batalla_display["% Adopción"] = df_batalla_display["% Adopción"].apply(
            lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%"
        )

    if not df_batalla_display.empty:
        gb_b = GridOptionsBuilder.from_dataframe(df_batalla_display)
        gb_b.configure_default_column(
            filterable=True, sortable=True, resizable=True, minWidth=120
        )
        gb_b.configure_column("Cód. Vend", width=90)
        gb_b.configure_column("Preventista", minWidth=150)
        gb_b.configure_column("SUP", width=75)
        gb_b.configure_column("Cód. Cliente", width=100)
        gb_b.configure_column("Razón Social", minWidth=170)
        gb_b.configure_column("Dirección", minWidth=160)
        gb_b.configure_column("Día Visita", width=100)
        gb_b.configure_column("Taxonomía", width=80)
        gb_b.configure_column("Ventas Totales ($)", width=130)
        gb_b.configure_column("Ventas App ($)", width=130)
        gb_b.configure_column("% Adopción", width=110)
        gb_b.configure_column("Faltante Mín. 70% ($)", width=140)
        gb_b.configure_column("Categoría App", width=120)

        gb_b.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_opts_b = gb_b.build()

        AgGrid(
            df_batalla_display,
            gridOptions=grid_opts_b,
            height=400,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=False,
        )
    else:
        st.info(
            "No hay registros de clientes pendientes de conversión digital con los filtros seleccionados."
        )

    st.divider()

    # --------------------------------------------------
    # SECCIÓN 5: EXPORTACIONES (EXCEL Y WHATSAPP)
    # --------------------------------------------------
    col_dl1, col_dl2, col_dl3 = st.columns(3)
    with col_dl1:
        buffer_mn = io.BytesIO()
        with pd.ExcelWriter(buffer_mn, engine="openpyxl") as writer:
            reporte_render_excel.to_excel(
                writer, index=False, sheet_name="Adopcion_MiNegocio_Taxonomia"
            )
        buffer_mn.seek(0)
        st.download_button(
            label="📥 Descargar Resumen a Excel",
            data=buffer_mn,
            file_name="Adopcion_MiNegocio_Resumen.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"core_mn_btn_dl_res_{sup_seleccionado}",
        )

    with col_dl2:
        buffer_bat = io.BytesIO()
        with pd.ExcelWriter(buffer_bat, engine="openpyxl") as writer:
            df_batalla_excel.to_excel(
                writer, index=False, sheet_name="Batalla_MiNegocio_Clientes"
            )
        buffer_bat.seek(0)
        st.download_button(
            label="📥 Descargar Batalla a Excel",
            data=buffer_bat,
            file_name="Batalla_MiNegocio_Clientes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"core_mn_btn_dl_bat_{sup_seleccionado}",
        )

    with col_dl3:
        if not df_batalla_render.empty:
            lista_mn_formateada = []
            for _, row in df_batalla_render.iterrows():
                cli = row.get("Cód. Cliente", "")
                nom = row.get("Razón Social", "")
                dir_c = row.get("Dirección", "")
                dia = row.get("Día Visita", "")
                pct_app = row.get("% Adopción", 0.0)
                faltante = row.get("Faltante Mín. 70% ($)", 0.0)
                cat = row.get("Categoría App", "")

                lista_mn_formateada.append(
                    f"[{cli}] {nom} - {dir_c} - {dia} | App: {pct_app:,.2f}% ({cat}) - Faltante 70%: ${faltante:,.2f}"
                )

            detalle_texto = "\n".join(lista_mn_formateada)
            total_cnt = len(df_batalla_render)

            texto_wa = f"MiNegocio Pendientes (Total: {total_cnt})\n\n{detalle_texto}"

            url_wa = f"https://wa.me/?text={urllib.parse.quote(texto_wa)}"

            st.markdown(
                f"""
                <div style="
                display:flex;
                justify-content:center;
                align-items:center;
                height:100%;
                padding-top:5px;
                ">
                <a href="{url_wa}"
                target="_blank"
                style="
                display:inline-block;
                padding:4px 10px;
                background-color:#25d366;
                color:white;
                text-align:center;
                text-decoration:none;
                font-weight:600;
                font-size:0.75rem;
                border-radius:4px;
                box-shadow:0 1px 2px rgba(0,0,0,0.1);
                ">
                💬 WhatsApp MiNegocio
                </a>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="padding:0.5rem;text-align:center;color:#94a3b8;font-size:0.85rem;">Sin datos para WhatsApp</div>',
                unsafe_allow_html=True,
            )


def render_rep_mn_core(filtros_globales=None):
    """
    Función de renderizado principal para MiNegocio bajo la Arquitectura Objetivo Oficial.
    (CORE -> BUSINESS_RULES -> REPORTES).
    Cero dependencias de SQLite, raw ni staging. Consume exclusivamente business_rules_mn.
    """
    t0 = time.perf_counter()

    st.subheader("📱 Adopción MiNegocio por Taxonomía")
    st.markdown(
        "Analiza la adopción y penetración de la aplicación MiNegocio segmentada por "
        "taxonomía, vendedor y día de visita sobre el universo total de cartera."
    )

    if filtros_globales is None:
        raise ValueError("No se recibieron filtros_globales in render_rep_mn_core().")

    sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()

    # CONSUMO EXCLUSIVO DE BUSINESS_RULES (obtener_matriz_mn_comercial)
    t_br = time.perf_counter()
    matriz_mn = obtener_matriz_mn_comercial(
        int(filtros_globales["anio"]),
        int(filtros_globales["mes"]),
        filtros_globales,
    )
    print(
        f"[PERF_CORE] Construcción y obtención de matriz MN comercial -> {time.perf_counter() - t_br:.4f} s"
    )

    if matriz_mn.empty:
        st.info(
            "No se encontraron registros comerciales de MiNegocio para los parámetros seleccionados."
        )
        return

    # Invocación al fragmento visual
    render_fragmento_interactivo_mn_core(matriz_mn, sup_filtro)

    print(
        f"[PERF_CORE] Tiempo total render_rep_mn_core -> {time.perf_counter() - t0:.4f} s"
    )
