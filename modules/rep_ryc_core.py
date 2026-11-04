from __future__ import annotations

"""
modules/rep_ryc_core.py

Reporte Streamlit de RyC (Rechazos y Cambios).
Consume exclusivamente BUSINESS_RULES_RYC para métricas comerciales.
"""

import html
import io
import time

import pandas as pd
import streamlit as st
from modules.utils import tarjeta_metrica_html

from modules.business_rules.business_rules_ryc import obtener_business_rules_ryc


COLUMNAS_REPORTE = [
    "CodVendedor",
    "Nombre",
    "SUP",
    "Rechazos",
    "Pct_Rechazos",
    "Cambios",
    "Presupuesto_Cambios",
    "Pct_Presupuesto_Cambios",
    "Saldo_Presupuesto_Cambios",
    "Excede_Presupuesto_Cambios",
    "Pct_Cambios",
]


def _normalizar_supervisor(valor):
    if valor is None:
        return None
    texto = str(valor).strip().upper()
    if texto in {"", "TODOS"}:
        return None
    numero = pd.to_numeric(pd.Series([valor]), errors="coerce").iloc[0]
    if pd.isna(numero):
        raise ValueError(f"Supervisor global inválido para RyC: {valor!r}")
    return int(numero)


def _aplicar_supervisor(matriz: pd.DataFrame, supervisor) -> pd.DataFrame:
    sup = _normalizar_supervisor(supervisor)
    if sup is None:
        return matriz.copy().reset_index(drop=True)
    if "SUP" not in matriz.columns:
        raise RuntimeError("La matriz RyC no contiene la columna SUP.")
    serie_sup = pd.to_numeric(matriz["SUP"], errors="coerce")
    return matriz.loc[serie_sup.eq(sup)].copy().reset_index(drop=True)


def _resumen_desde_matriz(matriz: pd.DataFrame) -> dict:
    venta = float(pd.to_numeric(matriz["Venta_Total"], errors="coerce").fillna(0).sum())
    rechazos = float(pd.to_numeric(matriz["Rechazos"], errors="coerce").fillna(0).sum())
    cambios = float(pd.to_numeric(matriz["Cambios"], errors="coerce").fillna(0).sum())
    presupuesto = float(
        pd.to_numeric(matriz["Presupuesto_Cambios"], errors="coerce").fillna(0).sum()
    )
    saldo = presupuesto - cambios
    excedidos = int(
        matriz["Excede_Presupuesto_Cambios"].fillna(False).astype(bool).sum()
    )
    return {
        "Venta_Total": venta,
        "Rechazos": rechazos,
        "Pct_Rechazos": rechazos / venta * 100.0 if venta else 0.0,
        "Cambios": cambios,
        "Pct_Cambios": cambios / venta * 100.0 if venta else 0.0,
        "Presupuesto_Cambios": presupuesto,
        "Pct_Presupuesto_Cambios": cambios / presupuesto * 100.0
        if presupuesto
        else 0.0,
        "Saldo_Presupuesto_Cambios": saldo,
        "Vendedores_Excedidos_Cambios": excedidos,
    }


def _formatear_porcentaje(valor) -> str:
    return f"{float(valor or 0.0):.2f}%".replace(".", ",")


def _render_etiqueta_porcentaje(
    titulo: str,
    porcentaje: float,
    color_fondo: str,
    color_borde: str,
) -> None:
    titulo_seguro = html.escape(str(titulo))
    valor_seguro = html.escape(_formatear_porcentaje(porcentaje))
    st.markdown(
        f"""
        <div style="
            background:{color_fondo};
            border:1px solid {color_borde};
            border-left:8px solid {color_borde};
            border-radius:14px;
            padding:18px 22px;
            min-height:116px;
            display:flex;
            flex-direction:column;
            justify-content:center;
            box-shadow:0 2px 8px rgba(0,0,0,0.08);
        ">
            <div style="font-size:0.90rem;font-weight:700;letter-spacing:0.03em;color:#334155;">
                {titulo_seguro}
            </div>
            <div style="font-size:2.25rem;font-weight:800;line-height:1.15;color:#0f172a;margin-top:8px;">
                {valor_seguro}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _preparar_visual(matriz: pd.DataFrame) -> pd.DataFrame:
    faltantes = [c for c in COLUMNAS_REPORTE if c not in matriz.columns]
    if faltantes:
        raise RuntimeError(
            f"La matriz RyC no contiene columnas requeridas: {faltantes}"
        )

    df = matriz[COLUMNAS_REPORTE].copy()
    df = df.drop(columns=["SUP"], errors="ignore")
    df["Estado_Presupuesto"] = (
        df["Excede_Presupuesto_Cambios"].fillna(False).map({True: "✕", False: "✓"})
    )
    df = df.drop(columns=["Excede_Presupuesto_Cambios"])
    return df.rename(
        columns={
            "CodVendedor": "Código",
            "Nombre": "Vendedor",
            "Rechazos": "Total Rechazos",
            "Pct_Rechazos": "% Rechazos",
            "Cambios": "Cambios Ejecutados",
            "Presupuesto_Cambios": "Presupuesto Cambios",
            "Pct_Presupuesto_Cambios": "% Presupuesto Consumido",
            "Saldo_Presupuesto_Cambios": "Saldo Presupuesto",
            "Pct_Cambios": "% Cambios",
            "Estado_Presupuesto": "Estado Presupuesto",
        }
    )


def _estilo_presupuesto(df: pd.DataFrame):
    def color_consumo(valor):
        numero = pd.to_numeric(pd.Series([valor]), errors="coerce").iloc[0]
        if pd.isna(numero):
            return ""
        if numero >= 100:
            return "color:#dc2626;font-weight:800;"
        if numero >= 80:
            return "color:#d97706;font-weight:800;"
        return "color:#16a34a;font-weight:800;"

    def color_estado(valor):
        if str(valor).strip() == "✕":
            return "color:#dc2626;font-weight:900;font-size:1.15rem;text-align:center;"
        return "color:#16a34a;font-weight:900;font-size:1.15rem;text-align:center;"

    return df.style.map(color_consumo, subset=["% Presupuesto Consumido"]).map(
        color_estado, subset=["Estado Presupuesto"]
    )


def _filtrar_batalla(
    batalla: pd.DataFrame,
    vendedor: str,
    dia_visita: str,
    tipo: str,
) -> pd.DataFrame:
    df = batalla.copy()
    if vendedor != "TODOS":
        df = df.loc[df["Nombre"].astype(str).eq(vendedor)].copy()
    if dia_visita != "TODOS":
        df = df.loc[df["DiaVisita"].astype(str).eq(dia_visita)].copy()
    if tipo != "TODOS":
        df = df.loc[df["Tipo"].astype(str).eq(tipo)].copy()
    return df.reset_index(drop=True)


def _preparar_batalla_visual(batalla: pd.DataFrame) -> pd.DataFrame:
    columnas = [
        "Cliente",
        "Razon_Social",
        "Fecha",
        "Codigo",
        "Articulo",
        "Tipo",
        "Cantidad",
        "Importe",
        "CodVendedor",
        "DiaVisita",
        "Cliente_Dia_Visita",
    ]
    faltantes = [c for c in columnas if c not in batalla.columns]
    if faltantes:
        raise RuntimeError(f"Batalla RyC no contiene columnas requeridas: {faltantes}")
    df = batalla[columnas].copy()
    df["Cliente_Dia_Visita"] = (
        df["Cliente_Dia_Visita"].fillna(False).map({True: "✓", False: "✕"})
    )
    return df.rename(
        columns={
            "Razon_Social": "Razón Social",
            "Codigo": "Código Artículo",
            "Articulo": "Artículo",
            "CodVendedor": "Cod Vendedor",
            "DiaVisita": "Día de Visita",
            "Cliente_Dia_Visita": "Cliente del Día",
        }
    )


def _exportar_excel(matriz: pd.DataFrame, resumen: dict, metadata: dict) -> bytes:
    buffer = io.BytesIO()
    tabla_exportacion = _preparar_visual(matriz)
    resumen_df = pd.DataFrame([resumen])
    metadata_df = pd.DataFrame([metadata])
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        tabla_exportacion.to_excel(writer, index=False, sheet_name="RyC_Vendedores")
        resumen_df.to_excel(writer, index=False, sheet_name="RyC_Resumen")
        metadata_df.to_excel(writer, index=False, sheet_name="RyC_Metadata")
    buffer.seek(0)
    return buffer.getvalue()


@st.fragment
def render_fragmento_interactivo_ryc_core(
    matriz, batalla, metadata, supervisor, anio_op, mes_op
):
    """Filtros locales del reporte completo, sin recalcular Business Rules."""
    matriz_base = _aplicar_supervisor(matriz, supervisor)
    sup_norm = _normalizar_supervisor(supervisor)
    if matriz_base.empty:
        st.info("No hay vendedores RyC para los filtros seleccionados.")
        return

    if sup_norm is not None and not batalla.empty:
        cod_sup = set(
            pd.to_numeric(matriz_base["CodVendedor"], errors="coerce")
            .dropna()
            .astype(int)
        )
        batalla = batalla.loc[
            pd.to_numeric(batalla["CodVendedor"], errors="coerce").isin(cod_sup)
        ].copy()

    dias_map = {
        "MONDAY": "LUNES",
        "TUESDAY": "MARTES",
        "WEDNESDAY": "MIÉRCOLES",
        "THURSDAY": "JUEVES",
        "FRIDAY": "VIERNES",
        "SATURDAY": "SÁBADO",
        "SUNDAY": "DOMINGO",
    }
    if not batalla.empty:
        d = batalla["DiaVisita"].fillna("SIN DÍA").astype(str).str.strip().str.upper()
        batalla["DiaVisita"] = d.map(dias_map).fillna(d)

    vendedores = sorted(
        [
            x
            for x in matriz_base["Nombre"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
            if x
        ]
    )
    orden_dias = [
        "LUNES",
        "MARTES",
        "MIÉRCOLES",
        "JUEVES",
        "VIERNES",
        "SÁBADO",
        "DOMINGO",
        "SIN DÍA",
    ]
    presentes = (
        set(batalla["DiaVisita"].dropna().astype(str).str.strip())
        if not batalla.empty
        else set()
    )
    dias = [x for x in orden_dias if x in presentes] + sorted(
        presentes - set(orden_dias)
    )

    # Los filtros están arriba y gobiernan TODO el reporte.
    f1, f2, f3 = st.columns(3)
    with f1:
        vsel = st.multiselect(
            "Vendedor",
            vendedores,
            default=[],
            key=f"ryc_v_{anio_op}_{mes_op}_{supervisor}",
        )
    with f2:
        dsel = st.multiselect(
            "Día de Visita",
            dias,
            default=[],
            key=f"ryc_d_{anio_op}_{mes_op}_{supervisor}",
        )
    with f3:
        tsel = st.selectbox(
            "Tipo",
            ["TODOS", "CAMBIOS", "RECHAZOS"],
            index=0,
            key=f"ryc_t_{anio_op}_{mes_op}_{supervisor}",
        )
    if not vsel:
        vsel = vendedores
    if not dsel:
        dsel = dias

    batalla_filtrada = (
        batalla.loc[
            batalla["Nombre"].astype(str).str.strip().isin(vsel)
            & batalla["DiaVisita"].astype(str).str.strip().isin(dsel)
        ].copy()
        if not batalla.empty
        else batalla.copy()
    )
    if tsel != "TODOS" and not batalla_filtrada.empty:
        batalla_filtrada = batalla_filtrada.loc[
            batalla_filtrada["Tipo"].astype(str).eq(tsel)
        ].copy()

    # Tabla superior y KPIs quedan restringidos por los mismos filtros.
    codigos = set(
        pd.to_numeric(batalla_filtrada["CodVendedor"], errors="coerce")
        .dropna()
        .astype(int)
    )
    matriz_visible = matriz_base.loc[
        matriz_base["Nombre"].astype(str).str.strip().isin(vsel)
        & pd.to_numeric(matriz_base["CodVendedor"], errors="coerce").isin(codigos)
    ].copy()
    if matriz_visible.empty:
        st.info("No hay vendedores con operaciones para los filtros aplicados.")
        return

    resumen = _resumen_desde_matriz(matriz_visible)
    k1, k2 = st.columns(2)
    with k1:
        st.markdown(
            tarjeta_metrica_html(
                "% Total de Rechazos",
                f"{resumen['Pct_Rechazos']:,.2f}%",
                "#ef4444",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            tarjeta_metrica_html(
                "% Total de Cambios",
                f"{resumen['Pct_Cambios']:,.2f}%",
                "#f97316",
                "39px",
                "21px",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("### Detalle por vendedor")
    st.dataframe(
        _estilo_presupuesto(_preparar_visual(matriz_visible)),
        width="stretch",
        hide_index=True,
        column_config={
            "Código": st.column_config.NumberColumn("Código", format="%d"),
            "Total Rechazos": st.column_config.NumberColumn(
                "Total Rechazos", format="$ %.2f"
            ),
            "% Rechazos": st.column_config.NumberColumn("% Rechazos", format="%.2f%%"),
            "Cambios Ejecutados": st.column_config.NumberColumn(
                "Cambios Ejecutados", format="$ %.2f"
            ),
            "Presupuesto Cambios": st.column_config.NumberColumn(
                "Presupuesto Cambios", format="$ %.2f"
            ),
            "% Presupuesto Consumido": st.column_config.NumberColumn(
                "% Presupuesto Consumido", format="%.2f%%"
            ),
            "Saldo Presupuesto": st.column_config.NumberColumn(
                "Saldo Presupuesto", format="$ %.2f"
            ),
            "% Cambios": st.column_config.NumberColumn("% Cambios", format="%.2f%%"),
        },
    )

    st.markdown("### ⚔️ Batalla RyC")
    if batalla_filtrada.empty:
        st.info("No hay operaciones para los filtros aplicados.")
    else:
        st.caption(
            f"Operaciones mostradas: {len(batalla_filtrada):,}".replace(",", ".")
        )
        bv = _preparar_batalla_visual(batalla_filtrada)

        def color_dia(v):
            return f"color:{'#16a34a' if str(v).strip() == '✓' else '#dc2626'};font-weight:900;text-align:center;"

        st.dataframe(
            bv.style.map(color_dia, subset=["Cliente del Día"]),
            width="stretch",
            hide_index=True,
            column_config={
                "Cliente": st.column_config.NumberColumn("Cliente", format="%d"),
                "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "Código Artículo": st.column_config.NumberColumn(
                    "Código Artículo", format="%d"
                ),
                "Cantidad": st.column_config.NumberColumn("Cantidad", format="%.2f"),
                "Importe": st.column_config.NumberColumn("Importe", format="$ %.2f"),
                "Cod Vendedor": st.column_config.NumberColumn(
                    "Cod Vendedor", format="%d"
                ),
            },
        )

    sup_txt = "TODOS" if sup_norm is None else str(sup_norm)
    excel = _exportar_excel(matriz_visible, resumen, metadata)
    st.download_button(
        "📥 Exportar RyC",
        data=excel,
        file_name=f"RyC_SUP_{sup_txt}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"btn_exportar_ryc_{anio_op}_{mes_op}_{sup_txt}",
    )


def render_rep_ryc_core(filtros_globales=None):
    """Calcula Business Rules una vez; las interacciones quedan dentro del fragmento."""
    t0 = time.perf_counter()
    if not isinstance(filtros_globales, dict):
        raise TypeError("render_rep_ryc_core requiere filtros_globales como dict.")
    requeridos = ["anio", "mes", "dia_matinal", "dia_venta"]
    faltantes = [c for c in requeridos if filtros_globales.get(c) in (None, "")]
    if faltantes:
        raise ValueError(f"Faltan filtros globales requeridos para RyC: {faltantes}")
    anio = int(filtros_globales["anio"])
    mes = int(filtros_globales["mes"])
    supervisor = str(filtros_globales.get("supervisor", "TODOS")).strip()
    st.subheader("🔁 RyC · Rechazos y Cambios")
    resultado = obtener_business_rules_ryc(
        anio=anio,
        mes=mes,
        dia_matinal=filtros_globales["dia_matinal"],
        dia_venta=filtros_globales["dia_venta"],
        modo_ajuste="AJUSTADO",
    )
    render_fragmento_interactivo_ryc_core(
        resultado["matriz"].copy(),
        resultado.get("batalla", pd.DataFrame()).copy(),
        resultado["metadata"],
        supervisor,
        anio,
        mes,
    )
    print(f"[PERF_CORE] render_rep_ryc_core -> {time.perf_counter() - t0:.4f} s")
