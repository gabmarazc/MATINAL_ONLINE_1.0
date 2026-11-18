import io
import time

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode

from modules import database as db
from modules.business_rules.business_rules_objetivo_segmentos import (
    generar_business_rules_objetivo_segmentos,
)
from modules.core.core_potencial_cliente_segmento import (
    generar_core_potencial_cliente_segmento,
)
from modules.utils import tarjeta_metrica_html


CACHE_VERSION_POTENCIAL_CARTERA = "v2"


def _normalizar_cliente(serie: pd.Series) -> pd.Series:
    """Normaliza Codigo/Cliente para ejecutar el cruce sin diferencias de tipo."""
    return pd.to_numeric(serie, errors="coerce").astype("Int64").astype("string")


def _normalizar_texto_clave(serie: pd.Series) -> pd.Series:
    return serie.fillna("").astype(str).str.strip().str.upper()


def _generar_potencial_cartera(
    anio_operativo: int,
    mes_operativo: int,
) -> pd.DataFrame:
    """Genera PotencialCarteraKg como dato exclusivamente visual.

    Regla:
        1. Consume PotencialKg ya calculado por
           core_potencial_cliente_segmento para los tres meses anteriores.
        2. Cruza Cliente con universo[Codigo] para obtener la cartera vigente.
        3. Suma PotencialKg por codven + Ruta + SEGMENTO.

    No utiliza ObjetivoKg ni participa en su cálculo.
    """
    columnas_salida = [
        "codven",
        "Ruta",
        "SEGMENTO",
        "PotencialCarteraKg",
    ]

    df_potencial = generar_core_potencial_cliente_segmento(
        anio_operativo,
        mes_operativo,
    )
    if df_potencial is None or df_potencial.empty:
        return pd.DataFrame(columns=columnas_salida)

    columnas_potencial = ["Cliente", "SEGMENTO", "PotencialKg"]
    faltantes = [c for c in columnas_potencial if c not in df_potencial.columns]
    if faltantes:
        raise ValueError(
            "Faltan columnas obligatorias en "
            f"core_potencial_cliente_segmento: {faltantes}"
        )

    df_universo = db.cargar_tabla_sql("SELECT Codigo, codven, Ruta FROM universo")
    if df_universo is None or df_universo.empty:
        return pd.DataFrame(columns=columnas_salida)

    columnas_universo = ["Codigo", "codven", "Ruta"]
    faltantes = [c for c in columnas_universo if c not in df_universo.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias en universo: {faltantes}")

    potencial = df_potencial[columnas_potencial].copy()
    universo = df_universo[columnas_universo].copy()

    potencial["Cliente_Join"] = _normalizar_cliente(potencial["Cliente"])
    universo["Cliente_Join"] = _normalizar_cliente(universo["Codigo"])

    universo["codven"] = pd.to_numeric(universo["codven"], errors="coerce").astype(
        "Int64"
    )
    universo["Ruta"] = universo["Ruta"].fillna("").astype(str).str.strip()

    # Mismo criterio vigente utilizado por el pipeline de cartera:
    # una única asignación del cliente en universo.
    universo = universo.dropna(subset=["Cliente_Join", "codven"]).drop_duplicates(
        subset=["Cliente_Join"], keep="first"
    )

    potencial["SEGMENTO"] = _normalizar_texto_clave(potencial["SEGMENTO"])
    potencial["PotencialKg"] = pd.to_numeric(
        potencial["PotencialKg"], errors="coerce"
    ).fillna(0.0)

    potencial = potencial[
        (potencial["Cliente_Join"].notna())
        & (potencial["SEGMENTO"] != "")
        & (potencial["SEGMENTO"] != "SIN SEGMENTO")
    ].copy()

    detalle = potencial.merge(
        universo[["Cliente_Join", "codven", "Ruta"]],
        on="Cliente_Join",
        how="inner",
        validate="many_to_one",
    )
    if detalle.empty:
        return pd.DataFrame(columns=columnas_salida)

    resultado = (
        detalle.groupby(
            ["codven", "Ruta", "SEGMENTO"],
            as_index=False,
            dropna=False,
        )["PotencialKg"]
        .sum()
        .rename(columns={"PotencialKg": "PotencialCarteraKg"})
    )

    resultado["PotencialCarteraKg"] = pd.to_numeric(
        resultado["PotencialCarteraKg"], errors="coerce"
    ).fillna(0.0)

    return resultado[columnas_salida].copy()


def generar_rep_obj_kilos_core(
    anio_operativo: int,
    mes_operativo: int,
) -> pd.DataFrame:
    """Capa CORE del reporte de Objetivos de Kilos.

    ObjetivoKg conserva exclusivamente la salida de Business Rules.
    PotencialCarteraKg se anexa como referencia visual independiente.
    """
    columnas_objetivo = [
        "codven",
        "Vendedor",
        "Ruta",
        "SEGMENTO",
        "ObjetivoKg",
    ]
    columnas_salida = columnas_objetivo + ["PotencialCarteraKg"]

    df_segmentos = generar_business_rules_objetivo_segmentos(
        anio_operativo,
        mes_operativo,
    )
    if df_segmentos is None or df_segmentos.empty:
        return pd.DataFrame(columns=columnas_salida)

    faltantes = [c for c in columnas_objetivo if c not in df_segmentos.columns]
    if faltantes:
        raise ValueError(
            "Faltan columnas obligatorias en "
            f"business_rules_objetivo_segmentos: {faltantes}"
        )

    df_segmentos = df_segmentos[columnas_objetivo].copy()
    df_segmentos["SEGMENTO"] = _normalizar_texto_clave(df_segmentos["SEGMENTO"])
    df_segmentos = df_segmentos[
        (df_segmentos["SEGMENTO"] != "") & (df_segmentos["SEGMENTO"] != "SIN SEGMENTO")
    ].copy()

    if df_segmentos.empty:
        return pd.DataFrame(columns=columnas_salida)

    df_segmentos["codven"] = pd.to_numeric(
        df_segmentos["codven"], errors="coerce"
    ).astype("Int64")
    df_segmentos["Ruta"] = df_segmentos["Ruta"].fillna("").astype(str).str.strip()
    df_segmentos["ObjetivoKg"] = pd.to_numeric(
        df_segmentos["ObjetivoKg"], errors="coerce"
    ).fillna(0.0)

    suma_entrada = float(df_segmentos["ObjetivoKg"].sum())

    df_potencial = _generar_potencial_cartera(
        anio_operativo,
        mes_operativo,
    )

    resultado = df_segmentos.merge(
        df_potencial,
        on=["codven", "Ruta", "SEGMENTO"],
        how="left",
        validate="one_to_one",
    )
    resultado["PotencialCarteraKg"] = pd.to_numeric(
        resultado["PotencialCarteraKg"], errors="coerce"
    ).fillna(0.0)

    suma_salida = float(resultado["ObjetivoKg"].sum())
    assert abs(suma_entrada - suma_salida) < 1e-6

    return resultado[columnas_salida].copy()


@st.fragment
def render_fragmento_interactivo_obj_kilos_core(
    df_base: pd.DataFrame,
    anio_op: int,
    mes_op: int,
):
    """Presentación interactiva para Objetivos de Kilos."""
    if df_base.empty:
        st.info("No hay registros disponibles.")
        return

    columnas_requeridas = [
        "codven",
        "Vendedor",
        "SEGMENTO",
        "PotencialCarteraKg",
        "ObjetivoKg",
    ]
    faltantes = [c for c in columnas_requeridas if c not in df_base.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en el contrato del reporte: {faltantes}")

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

    df_view = df_base.copy()
    factor = coeficiente / 100.0
    df_view["ObjetivoKg_Ajustado"] = df_view["ObjetivoKg"] * factor

    # Mismo nivel visual original: vendedor + segmento, sin Ruta.
    df_view = df_view.groupby(
        ["codven", "Vendedor", "SEGMENTO"],
        as_index=False,
        dropna=False,
    )[["PotencialCarteraKg", "ObjetivoKg", "ObjetivoKg_Ajustado"]].sum()

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
                "📈 Objetivo Ajustado",
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

    df_display = df_view.copy()
    if not df_display.empty:
        gb = GridOptionsBuilder.from_dataframe(df_display)
        gb.configure_default_column(
            filterable=True,
            sortable=True,
            resizable=True,
            minWidth=120,
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
            "PotencialCarteraKg",
            headerName="Potencial Cartera (kg)",
            width=170,
            valueFormatter=(
                "x != null ? Number(x).toLocaleString('es-AR', "
                "{minimumFractionDigits: 2, maximumFractionDigits: 2}) "
                "+ ' kg' : '0.00 kg'"
            ),
        )
        gb.configure_column(
            "ObjetivoKg",
            headerName="Objetivo Base (kg)",
            width=140,
            valueFormatter=(
                "x != null ? Number(x).toLocaleString('es-AR', "
                "{minimumFractionDigits: 2, maximumFractionDigits: 2}) "
                "+ ' kg' : '0.00 kg'"
            ),
        )
        gb.configure_column(
            "ObjetivoKg_Ajustado",
            headerName="Objetivo Ajustado (kg)",
            width=150,
            valueFormatter=(
                "x != null ? Number(x).toLocaleString('es-AR', "
                "{minimumFractionDigits: 2, maximumFractionDigits: 2}) "
                "+ ' kg' : '0.00 kg'"
            ),
        )
        gb.configure_pagination(
            paginationAutoPageSize=False,
            paginationPageSize=15,
        )
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

    df_export = df_view.copy()
    df_export["Anio"] = int(anio_op)
    df_export["Mes"] = int(mes_op)
    df_export["Supervisor"] = None
    df_export = df_export.rename(
        columns={
            "codven": "CodVendedor",
            "Vendedor": "Nombre",
            "PotencialCarteraKg": "Potencial_Cartera_Kg",
            "ObjetivoKg_Ajustado": "Obj_Sugerido_Kg",
        }
    )
    df_export = df_export[
        [
            "Anio",
            "Mes",
            "CodVendedor",
            "Nombre",
            "Supervisor",
            "SEGMENTO",
            "Potencial_Cartera_Kg",
            "Obj_Sugerido_Kg",
        ]
    ]

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
        file_name=(f"Objetivos_Kilos_{coeficiente}pct_{mes_op}_{anio_op}.xlsx"),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_dl_obj_kilos_core_final",
    )


def render_rep_obj_kilos_core(filtros_globales=None):
    """Reporte de Objetivos de Kilos bajo la arquitectura vigente."""
    t_total = time.perf_counter()

    st.subheader("🎯 Objetivos de Kilos por Segmento y Cartera")
    st.markdown(
        "Visualiza y simula los objetivos de volumen en kilogramos asignados "
        "a la cartera comercial y segmentados por categoría oficial, aplicando "
        "un coeficiente de ajuste general en tiempo real."
    )

    if filtros_globales is None:
        anio_op = 2026
        mes_op = 9
    else:
        anio_op = int(filtros_globales.get("anio", 2026))
        mes_op = int(filtros_globales.get("mes", 9))

    # El argumento de versión invalida cualquier caché generado con el contrato
    # anterior, que todavía no contenía PotencialCarteraKg.
    @st.cache_data(show_spinner=False)
    def _obtener_base_cached(
        anio: int,
        mes: int,
        version_contrato: str,
    ) -> pd.DataFrame:
        _ = version_contrato
        return generar_rep_obj_kilos_core(anio, mes)

    df_base = _obtener_base_cached(
        anio_op,
        mes_op,
        CACHE_VERSION_POTENCIAL_CARTERA,
    )

    if df_base.empty:
        st.info(
            "No se encontraron registros de objetivos para los parámetros "
            "seleccionados."
        )
        return

    render_fragmento_interactivo_obj_kilos_core(
        df_base,
        anio_op,
        mes_op,
    )

    print(
        "[PERF_CORE] Tiempo total render_rep_obj_kilos_core -> "
        f"{time.perf_counter() - t_total:.4f} s"
    )
