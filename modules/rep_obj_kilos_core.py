import io
import time
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules.utils import tarjeta_metrica_html
from modules.business_rules.business_rules_objetivo_segmentos import (
    generar_business_rules_objetivo_segmentos,
)


def generar_rep_obj_kilos_core(anio_operativo: int, mes_operativo: int) -> pd.DataFrame:
    """Capa CORE de reporte para Kilos, consumiendo exclusivamente

    la salida de la capa Business Rules de segmentos.

    Arquitectura: REPORTES (Sistema Matinal 2.0)
    """
    columnas_salida = ["codven", "Vendedor", "Ruta", "SEGMENTO", "ObjetivoKg"]

    # 1. Consumo exclusivo de Business Rules
    df_segmentos = generar_business_rules_objetivo_segmentos(
        anio_operativo, mes_operativo
    )

    if df_segmentos is None or df_segmentos.empty:
        return pd.DataFrame(columns=columnas_salida)

    # 1.0.1 Filtrar filas con SEGMENTO = "SIN SEGMENTO" inmediatamente después de obtener los datos
    df_segmentos = df_segmentos[
        df_segmentos["SEGMENTO"].fillna("").astype(str).str.strip().str.upper()
        != "SIN SEGMENTO"
    ].copy()

    if df_segmentos.empty:
        return pd.DataFrame(columns=columnas_salida)

    # 1.1 Validación de Contrato
    faltantes = [c for c in columnas_salida if c not in df_segmentos.columns]
    if faltantes:
        raise ValueError(
            f"Faltan columnas obligatorias en business_rules_objetivo_segmentos: {faltantes}"
        )

    # 2. Validación de Integridad (Suma previa)
    suma_entrada = (
        pd.to_numeric(df_segmentos["ObjetivoKg"], errors="coerce").fillna(0.0).sum()
    )

    # 3. Selección estricta del contrato de salida sin columnas adicionales
    resultado = df_segmentos[columnas_salida].copy()

    # 3.1 Validación de Integridad (Suma posterior)
    suma_salida = (
        pd.to_numeric(resultado["ObjetivoKg"], errors="coerce").fillna(0.0).sum()
    )
    assert abs(suma_entrada - suma_salida) < 1e-6

    return resultado


@st.fragment
def render_fragmento_interactivo_obj_kilos_core(
    df_base: pd.DataFrame,
    anio_op: int,
    mes_op: int,
):
    """
    Fragmento interactivo de presentación para Objetivos de Kilos.
    Aplica únicamente simulación por Coeficiente de Ajuste (90% a 110%) sin recalcular la capa Business Rules base.
    Renderiza tarjetas de métricas, grilla interactiva AgGrid y botón de exportación a Excel.
    """
    if df_base.empty:
        st.info("No hay registros disponibles.")
        return

    # Único filtro permitido: Coeficiente de Ajuste de Objetivo (90% a 110%, por defecto 100%)
    col_f = st.columns(1)
    with col_f[0]:
        coeficiente = st.slider(
            "Coeficiente de Ajuste de Objetivo",
            min_value=90,
            max_value=110,
            value=100,
            step=1,
            format="%d%%",
            key=f"core_obj_kilos_coef_{anio_op}_{mes_op}",
        )

    # Simulación visual en memoria del coeficiente (Rendimiento instantáneo sin reejecutar Business Rules)
    df_view = df_base.copy()
    factor = coeficiente / 100.0
    df_view["ObjetivoKg_Ajustado"] = df_view["ObjetivoKg"] * factor

    # Consolidación a nivel codven, Vendedor, SEGMENTO sumando los objetivos
    df_view = df_view.groupby(["codven", "Vendedor", "SEGMENTO"], as_index=False)[
        ["ObjetivoKg", "ObjetivoKg_Ajustado"]
    ].sum()

    # Métricas institucionales solicitadas
    total_objetivo_base = float(df_view["ObjetivoKg"].sum())
    total_objetivo_ajustado = float(df_view["ObjetivoKg_Ajustado"].sum())

    mcol1, mcol2, mcol3 = st.columns(3)
    with mcol1:
        st.markdown(
            tarjeta_metrica_html(
                "🎯 Objetivo Base",
                f"{total_objetivo_base:,.2f} kg",
                "#3b82f6",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )
    with mcol2:
        st.markdown(
            tarjeta_metrica_html(
                f"📈 Objetivo Ajustado",
                f"{total_objetivo_ajustado:,.2f} kg",
                "#3b82f6",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )
    with mcol3:
        st.markdown(
            tarjeta_metrica_html(
                "⚙️ Coeficiente Aplicado",
                f"{coeficiente}%",
                "#3b82f6",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    # Preparación de vista para presentación visual en AgGrid consolidado sin Ruta
    df_display = df_view.copy()

    if not df_display.empty:
        gb = GridOptionsBuilder.from_dataframe(df_display)
        gb.configure_default_column(
            filterable=True, sortable=True, resizable=True, minWidth=120
        )
        gb.configure_column(
            "codven",
            headerName="Cód. Vend",
            width=100,
            valueFormatter="x != null ? Number(x).toFixed(0) : ''",
        )
        gb.configure_column("Vendedor", headerName="Vendedor", minWidth=160)
        gb.configure_column("SEGMENTO", headerName="Segmento", width=140)
        gb.configure_column(
            "ObjetivoKg",
            headerName="Objetivo Base (kg)",
            width=140,
            valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' kg' : '0.00 kg'",
        )
        gb.configure_column(
            "ObjetivoKg_Ajustado",
            headerName="Objetivo Ajustado (kg)",
            width=150,
            valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' kg' : '0.00 kg'",
        )

        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_options = gb.build()

        AgGrid(
            df_display,
            gridOptions=grid_options,
            height=420,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=False,
        )
    else:
        st.info("No se encontraron registros disponibles.")

    st.divider()

    # Funcionalidad de descarga a Excel exportando el dataset consolidado con el ObjetivoKg ya ajustado
    df_export = df_view.copy()
    df_export["ObjetivoKg"] = df_export["ObjetivoKg_Ajustado"]
    df_export = df_export[["codven", "Vendedor", "SEGMENTO", "ObjetivoKg"]]

    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
        df_export.to_excel(
            writer,
            index=False,
            sheet_name="Objetivos_Kilos_Segmentos",
        )
    buffer_excel.seek(0)

    st.download_button(
        label="📥 Descargar Reporte a Excel",
        data=buffer_excel,
        file_name=f"Objetivos_Kilos_{coeficiente}pct_{mes_op}_{anio_op}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"btn_dl_obj_kilos_core_final",
    )


def render_rep_obj_kilos_core(filtros_globales=None):
    """
    Reporte de Objetivos de Kilos bajo Arquitectura Objetivo Oficial (CORE -> BUSINESS_RULES -> REPORTES).
    Ejecuta una única vez la capa de negocio y delega la simulación visual interactiva al fragmento.
    """
    t_total = time.perf_counter()

    st.subheader("🎯 Objetivos de Kilos por Segmento y Cartera")
    st.markdown(
        "Visualiza y simula los objetivos de volumen en kilogramos asignados a la cartera comercial "
        "y segmentados por categoría oficial, aplicando un coeficiente de ajuste general en tiempo real."
    )

    if filtros_globales is None:
        anio_op = 2026
        mes_op = 9
    else:
        anio_op = int(filtros_globales.get("anio", 2026))
        mes_op = int(filtros_globales.get("mes", 9))

    # Caché y ejecución única institucional de la capa Business Rules (Cero recálculos al mover el slider)
    @st.cache_data(show_spinner=False)
    def _obtener_base_cached(anio: int, mes: int):
        return generar_rep_obj_kilos_core(anio, mes)

    df_base = _obtener_base_cached(anio_op, mes_op)

    if df_base.empty:
        st.info(
            "No se encontraron registros de objetivos para los parámetros seleccionados."
        )
        return

    # Invocación del fragmento interactivo sin filtros adicionales
    render_fragmento_interactivo_obj_kilos_core(df_base, anio_op, mes_op)

    print(
        f"[PERF_CORE] Tiempo total render_rep_obj_kilos_core -> {time.perf_counter() - t_total:.4f} s"
    )
