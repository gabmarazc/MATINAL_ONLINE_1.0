from __future__ import annotations

"""
modules/reportes/rep_compromisos_core.py

Reporte visual de COMPROMISOS.
Consume exclusivamente BUSINESS_RULES_COMPROMISOS y no redefine reglas analiticas.
"""

import io
import time

import pandas as pd
import streamlit as st

from modules.business_rules.business_rules_compromisos import (
    obtener_business_rules_compromisos,
)
from modules import database as db

SUPERVISORES_VALIDOS = (60, 70)
ORDEN_INDICADORES = [
    "PLAT_GOLD",
    "SILVER_BRZ",
    "VARIOS ($)",
    "CCC (Efect)",
    "NC",
    "PORC SELLOUT MN",
    "ADOPCIÓN MN",
    "TIENDAS PERFECTAS",
]

COLUMNAS_TABLERO = [
    "INDICADOR",
    "SUGERIDO_MESA",
    "COMP_VENDEDORES",
    "COMP_SUPERVISOR",
    "% VEND / SUP",
]


def _normalizar_supervisor_filtro(valor) -> int | None:
    if valor is None:
        return None
    texto = str(valor).strip().upper()
    if not texto or texto == "TODOS":
        return None
    numero = pd.to_numeric(pd.Series([valor]), errors="coerce").iloc[0]
    if pd.isna(numero):
        return None
    numero = int(numero)
    return numero if numero in SUPERVISORES_VALIDOS else None


def _formatear_valor(indicador: str, valor) -> str:
    if pd.isna(valor):
        return "—"
    numero = float(valor)
    if indicador == "VARIOS ($)":
        return f"$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if indicador in {"PLAT_GOLD", "SILVER_BRZ"}:
        return f"{numero:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if indicador == "PORC SELLOUT MN":
        return f"{numero:.0f}%"
    return f"{numero:,.0f}".replace(",", ".")


def _preparar_tablero_visual(tablero: pd.DataFrame) -> pd.DataFrame:
    if tablero is None or tablero.empty:
        return pd.DataFrame(columns=COLUMNAS_TABLERO)
    df = tablero.copy()
    for columna in ["INDICADOR", "SUGERIDO_MESA", "COMP_VENDEDORES", "COMP_SUPERVISOR"]:
        if columna not in df.columns:
            df[columna] = pd.NA
    vend = pd.to_numeric(df["COMP_VENDEDORES"], errors="coerce")
    sup = pd.to_numeric(df["COMP_SUPERVISOR"], errors="coerce")
    df["% VEND / SUP"] = vend.div(sup.replace(0, pd.NA)).mul(100.0)
    orden = {indicador: i for i, indicador in enumerate(ORDEN_INDICADORES)}
    df["_orden"] = df["INDICADOR"].map(orden).fillna(999)
    df = df.sort_values("_orden", kind="stable").drop(columns="_orden")
    visual = df[COLUMNAS_TABLERO].copy()
    for columna in ["SUGERIDO_MESA", "COMP_VENDEDORES", "COMP_SUPERVISOR"]:
        visual[columna] = [
            _formatear_valor(indicador, valor)
            for indicador, valor in zip(visual["INDICADOR"], visual[columna])
        ]
    return visual.reset_index(drop=True)


def _estilo_cumplimiento(valor):
    if pd.isna(valor):
        return "color: #94a3b8; font-weight: 700;"
    color = "#22c55e" if float(valor) >= 100.0 else "#ef4444"
    return f"color: {color}; font-weight: 800;"


def _formato_cumplimiento(valor) -> str:
    if pd.isna(valor):
        return "—"
    return f"{float(valor):.1f}%"


def _conciliar_supervisores(resultados: dict[int, dict]) -> pd.DataFrame:
    """Consolida 60 + 70 sin sumar porcentajes."""
    filas = []
    for indicador in ORDEN_INDICADORES:
        fila = {"INDICADOR": indicador}
        for columna in ["SUGERIDO_MESA", "COMP_VENDEDORES", "COMP_SUPERVISOR"]:
            valores = []
            for supervisor in SUPERVISORES_VALIDOS:
                resultado = resultados.get(supervisor)
                if not resultado:
                    continue
                tablero = resultado.get("tablero", pd.DataFrame())
                serie = pd.to_numeric(
                    tablero.loc[tablero["INDICADOR"].eq(indicador), columna],
                    errors="coerce",
                ).dropna()
                if not serie.empty:
                    valores.append(float(serie.iloc[0]))

            if not valores:
                fila[columna] = pd.NA
            elif indicador == "PORC SELLOUT MN":
                fila[columna] = float(sum(valores) / len(valores))
            else:
                fila[columna] = float(sum(valores))
        filas.append(fila)
    return pd.DataFrame(filas)


def _render_control_carga(control: pd.DataFrame, supervisor: int) -> None:
    if control is None or control.empty:
        return

    completa = int(control["EstadoCarga"].eq("COMPLETA").sum())
    parcial = int(control["EstadoCarga"].eq("PARCIAL").sum())
    sin_carga = int(control["EstadoCarga"].eq("SIN CARGA").sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Carga completa", completa)
    c2.metric("Carga parcial", parcial)
    c3.metric("Sin carga", sin_carga)

    with st.expander(
        f"Detalle de carga de vendedores - Supervisor {supervisor}", expanded=False
    ):
        columnas = [
            c
            for c in [
                "CodVend",
                "Nombre",
                "EstadoCarga",
                "IndicadoresCargados",
                "IndicadoresFaltantes",
                "Faltantes",
                "UltimaMarcaTemporal",
            ]
            if c in control.columns
        ]
        st.dataframe(control[columnas], width="stretch", hide_index=True)


def _render_tablero(tablero: pd.DataFrame, titulo: str) -> None:
    st.markdown(f"### {titulo}")
    display = _preparar_tablero_visual(tablero)
    if display.empty:
        st.info("No hay datos de compromisos para mostrar.")
        return
    styler = display.style.map(_estilo_cumplimiento, subset=["% VEND / SUP"]).format(
        {"% VEND / SUP": _formato_cumplimiento}
    )
    st.dataframe(styler, width="stretch", hide_index=True)


def _exportar_excel(
    resultados: dict[int, dict], tablero_general: pd.DataFrame | None
) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        if tablero_general is not None and not tablero_general.empty:
            tablero_general.to_excel(
                writer, index=False, sheet_name="Compromisos_General"
            )
        for supervisor, resultado in resultados.items():
            resultado["tablero"].to_excel(
                writer, index=False, sheet_name=f"Compromisos_{supervisor}"
            )
            control = resultado.get("control_carga", pd.DataFrame())
            if control is not None and not control.empty:
                control.to_excel(writer, index=False, sheet_name=f"Carga_{supervisor}")
    buffer.seek(0)
    return buffer.getvalue()


@st.fragment
def render_rep_compromisos_core(filtros_globales=None):
    """
    Render oficial de COMPROMISOS.

    - Supervisor seleccionado: presenta exclusivamente esa mesa.
    - Supervisor TODOS: presenta consolidado 60 + 70 y permite revisar ambas mesas.
    - Toda la logica proviene de BUSINESS_RULES_COMPROMISOS.
    """
    t0 = time.perf_counter()

    if not isinstance(filtros_globales, dict):
        raise ValueError(
            "No se recibieron filtros_globales en render_rep_compromisos_core()."
        )

    dia_matinal = filtros_globales.get("dia_matinal")
    if not dia_matinal or not str(dia_matinal).strip():
        raise ValueError("Falta dia_matinal en filtros_globales.")

    st.subheader("🤝 COMPROMISOS")
    st.caption(
        "Compara Sugerido Mesa, compromiso agregado de vendedores y compromiso del supervisor."
    )
    col_recarga, col_estado = st.columns([1, 3])
    with col_recarga:
        recargar_compromisos = st.button(
            "🔄 Recargar compromisos",
            key="btn_recargar_compromisos_core",
            width="stretch",
            help="Actualiza exclusivamente SQLite.compromisos desde el formulario.",
        )
    with col_estado:
        estado_recarga = st.empty()
    if recargar_compromisos:
        try:
            with st.spinner("Actualizando exclusivamente COMPROMISOS..."):
                resultado_recarga = db.actualizar_compromisos_desde_google_sheet()
            estado_recarga.success(
                "COMPROMISOS actualizado: "
                f"{resultado_recarga.get('filas_sqlite', 0)} respuestas vigentes."
            )
            st.rerun(scope="fragment")
        except Exception as exc:
            estado_recarga.error(f"No se pudo actualizar COMPROMISOS: {exc}")

    supervisor_local = st.selectbox(
        "Supervisor",
        options=list(SUPERVISORES_VALIDOS),
        format_func=lambda valor: f"Supervisor {valor}",
        key="compromisos_supervisor_local",
    )

    resultados: dict[int, dict] = {}
    errores = []
    try:
        resultados[supervisor_local] = obtener_business_rules_compromisos(
            supervisor=supervisor_local,
            dia_matinal=dia_matinal,
            filtros_globales=filtros_globales,
        )
    except Exception as exc:
        errores.append(f"Supervisor {supervisor_local}: {exc}")

    if errores:
        for error in errores:
            st.error(error)
    if not resultados:
        st.info(
            "No hay información disponible de COMPROMISOS para los filtros seleccionados."
        )
        return

    resultado = resultados[supervisor_local]
    _render_tablero(resultado["tablero"], f"Mesa Supervisor {supervisor_local}")
    _render_control_carga(
        resultado.get("control_carga", pd.DataFrame()), supervisor_local
    )

    st.divider()
    archivo = _exportar_excel(resultados, None)
    st.download_button(
        "📥 Exportar COMPROMISOS",
        data=archivo,
        file_name="COMPROMISOS.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_exportar_compromisos_core",
    )

    print(
        f"[PERF_CORE] render_rep_compromisos_core -> {time.perf_counter() - t0:.4f} s"
    )
