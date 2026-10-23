# modules/rep_gerencial_core.py

import html
import math

import pandas as pd
import streamlit as st

from modules import database as db
from modules.business_rules.business_rules_gerencial import obtener_motor_gerencial
from modules.rep_ccc_core import obtener_matriz_ccc_comercial
from modules.rep_MN_core import obtener_matriz_mn_comercial


# ==========================================================
# MAESTROS
# ==========================================================
def cargar_maestro_ccc(anio, mes):
    try:
        maestro = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
        if not maestro.empty and "Mes" in maestro.columns and "Anio" in maestro.columns:
            maestro = maestro[
                (maestro["Mes"].astype(str) == str(mes))
                & (maestro["Anio"].astype(str) == str(anio))
            ].copy()
        return maestro
    except Exception:
        return pd.DataFrame()


def cargar_maestro_cebe(anio, mes):
    try:
        maestro = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if not maestro.empty and "Mes" in maestro.columns and "Anio" in maestro.columns:
            maestro = maestro[
                (maestro["Mes"].astype(str) == str(mes))
                & (maestro["Anio"].astype(str) == str(anio))
            ].copy()
        return maestro
    except Exception:
        return pd.DataFrame()


# ==========================================================
# FILTROS Y ENRUTAMIENTO DE ESCENARIOS
# ==========================================================
def _filtrar_supervisor(df: pd.DataFrame, supervisor: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    resultado = df.copy()
    if supervisor != "TODOS" and "SUP" in resultado.columns:
        resultado = resultado[
            resultado["SUP"].fillna("").astype(str).str.strip()
            == str(supervisor).strip()
        ].copy()
    return resultado


def _aplicar_escenario_kilos(
    df_kilos: pd.DataFrame,
    modo_proyeccion: str,
) -> pd.DataFrame:
    if df_kilos is None or df_kilos.empty:
        return pd.DataFrame()

    resultado = df_kilos.copy()
    sufijo = "AJUSTADO" if modo_proyeccion == "AJUSTADO" else "TODO"

    mapeo = {
        "Tendencia_Total_Kg": f"Tendencia_Total_Kg_{sufijo}",
        "Cumplimiento_Proyectado_Pct": (f"Cumplimiento_Proyectado_Pct_{sufijo}"),
        "Promedio_Diario": f"Promedio_Diario_{sufijo}",
        "Media_Necesaria_Diaria": f"Media_Necesaria_Diaria_{sufijo}",
        "Días Restantes": (
            "Días Restantes Ajustado" if sufijo == "AJUSTADO" else "Días Restantes Todo"
        ),
    }

    for destino, origen in mapeo.items():
        if origen not in resultado.columns:
            raise ValueError(
                f"Kilos Gerencial no contiene la columna requerida '{origen}' "
                f"para el escenario {modo_proyeccion}."
            )
        resultado[destino] = resultado[origen]

    return resultado


def _aplicar_escenario_gross(
    df_gross: pd.DataFrame,
    modo_proyeccion: str,
) -> pd.DataFrame:
    if df_gross is None or df_gross.empty:
        return pd.DataFrame()

    resultado = df_gross.copy()
    sufijo = "AJUSTADO" if modo_proyeccion == "AJUSTADO" else "TODO"

    mapeo = {
        "Gross_Proyectado_Arg": f"Gross_Proyectado_Arg_{sufijo}",
        "Cumplimiento_Gross_Proy_Pct": (f"Cumplimiento_Gross_Proy_Pct_{sufijo}"),
        "Promedio_Diario": f"Promedio_Diario_{sufijo}",
        "Media_Necesaria_Diaria": f"Media_Necesaria_Diaria_{sufijo}",
        "Futuro_A_Incorporar_Gross": (f"Futuro_A_Incorporar_Gross_{sufijo}"),
        "Días Restantes": (
            "Días Restantes Ajustado" if sufijo == "AJUSTADO" else "Días Restantes Todo"
        ),
    }

    for destino, origen in mapeo.items():
        if origen not in resultado.columns:
            raise ValueError(
                f"Gross Gerencial no contiene la columna requerida '{origen}' "
                f"para el escenario {modo_proyeccion}."
            )
        resultado[destino] = resultado[origen]

    return resultado


# ==========================================================
# VALIDACIÓN Y PRESENTACIÓN
# ==========================================================
def _validar_columnas_requeridas(
    dataframe: pd.DataFrame,
    columnas: list,
    nombre_bloque: str,
) -> bool:
    if dataframe is None or dataframe.empty:
        return False

    faltantes = [col for col in columnas if col not in dataframe.columns]
    if faltantes:
        st.error(
            f"Error contractual en {nombre_bloque}. "
            f"Faltan columnas obligatorias: {', '.join(faltantes)}."
        )
        return False

    return True


def _numero_seguro(valor) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return 0.0
    return numero if math.isfinite(numero) else 0.0


def _render_semaforo(cumplimiento: float) -> tuple[str, str, str]:
    cumplimiento = _numero_seguro(cumplimiento)
    if cumplimiento < 90.0:
        return "🔴", "#dc2626", "Bajo objetivo"
    if cumplimiento < 100.0:
        return "🟡", "#eab308", "En seguimiento"
    return "🟢", "#16a34a", "Objetivo alcanzado"


def _render_tarjeta_segmento(
    titulo: str,
    objetivo: float,
    valor_principal: float,
    cumplimiento: float,
    etiqueta_principal: str,
    tendencia: float | None = None,
    incorporar: float | None = None,
    es_moneda: bool = False,
):
    icono, color, estado = _render_semaforo(cumplimiento)
    titulo_seguro = html.escape(str(titulo))
    etiqueta_segura = html.escape(str(etiqueta_principal))

    if es_moneda:
        formatear = lambda valor: f"${_numero_seguro(valor):,.0f}"
    else:
        formatear = lambda valor: f"{_numero_seguro(valor):,.1f} kg"

    filas_adicionales = ""
    if tendencia is not None:
        filas_adicionales += (
            f'<div style="margin-top:4px;">'
            f'<span style="color:#ffffff;font-size:0.90rem;font-weight:700;">Tendencia</span><br>'
            f'<span style="color:#ffffff;font-size:1.12rem;font-weight:800;">{formatear(tendencia)}</span>'
            f"</div>"
        )
    if incorporar is not None:
        filas_adicionales += (
            f'<div style="margin-top:4px;">'
            f'<span style="color:#ffffff;font-size:0.90rem;font-weight:700;">A incorporar</span><br>'
            f'<span style="color:#ffffff;font-size:1.12rem;font-weight:800;">{formatear(incorporar)}</span>'
            f"</div>"
        )

    tarjeta = f"""
    <div style="
        background-color:#0e1117;
        color:#ffffff;
        border:1px solid #2b313a;
        border-top:5px solid {color};
        border-radius:8px;
        padding:10px 10px 9px 10px;
        margin-bottom:8px;
        box-shadow:0 2px 5px rgba(0,0,0,0.35);
        min-height:200px;
        overflow:hidden;
    ">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px;margin-bottom:8px;">
            <strong style="font-size:1.08rem;line-height:1.14;color:#ffffff;">{titulo_seguro}</strong>
            <span title="{estado}" style="font-size:1.02rem;flex:0 0 auto;">{icono}</span>
        </div>
        <div style="line-height:1.32;">
            <div>
                <span style="color:#ffffff;font-size:0.90rem;font-weight:700;">Objetivo</span><br>
                <span style="color:#ffffff;font-size:1.12rem;font-weight:800;">{formatear(objetivo)}</span>
            </div>
            <div style="margin-top:4px;">
                <span style="color:#ffffff;font-size:0.90rem;font-weight:700;">{etiqueta_segura}</span><br>
                <span style="color:#ffffff;font-size:1.12rem;font-weight:800;">{formatear(valor_principal)}</span>
            </div>
            {filas_adicionales}
            <div style="margin-top:7px;color:{color};font-size:1.14rem;font-weight:900;">
                {_numero_seguro(cumplimiento):,.2f}%
            </div>
            <div style="color:{color};font-size:0.80rem;font-weight:800;">{estado}</div>
        </div>
    </div>
    """
    st.markdown(tarjeta, unsafe_allow_html=True)


def _render_tarjetas_en_filas(registros: list[dict], renderizador):
    for inicio in range(0, len(registros), 4):
        bloque = registros[inicio : inicio + 4]
        columnas = st.columns(len(bloque))
        for indice, registro in enumerate(bloque):
            with columnas[indice]:
                renderizador(registro)


# ==========================================================
# KILOS
# ==========================================================
def construir_bloque_kilos(
    df_kilos: pd.DataFrame,
    modo_proyeccion: str,
    supervisor: str = "TODOS",
) -> pd.DataFrame:
    """Granularidad final: SUP + SEGMENTO."""
    if df_kilos is None or df_kilos.empty:
        return pd.DataFrame()

    trabajo = _filtrar_supervisor(df_kilos, supervisor)
    trabajo = _aplicar_escenario_kilos(trabajo, modo_proyeccion)
    if trabajo.empty:
        return pd.DataFrame()

    columnas_suma = [
        "Objetivo Mes Corriente",
        "Arrastre",
        "Actual",
        "OPERATIVO",
        "Tendencia_Total_Kg",
        "Cumplimiento_Proyectado_Pct",
        "Promedio_Diario",
        "Media_Necesaria_Diaria",
        "Días Pasados",
        "Rutas",
        "Rutas_Ajustadas",
        "Días Restantes",
    ]

    faltantes = [col for col in columnas_suma if col not in trabajo.columns]
    if faltantes:
        raise ValueError(
            "Faltan columnas obligatorias en Kilos Gerencial: " + ", ".join(faltantes)
        )

    resultado = trabajo.groupby(["SUP", "SEGMENTO"], as_index=False)[
        columnas_suma
    ].sum()

    resultado["Cumplimiento_Proyectado_Pct"] = (
        resultado["Tendencia_Total_Kg"]
        .div(resultado["Objetivo Mes Corriente"].replace(0, pd.NA))
        .mul(100)
        .fillna(0.0)
    )
    resultado["Modo_Proyeccion"] = modo_proyeccion
    return resultado


# ==========================================================
# GROSS
# ==========================================================
def construir_bloque_gross(
    df_gross: pd.DataFrame,
    modo_proyeccion: str,
    supervisor: str = "TODOS",
) -> pd.DataFrame:
    """Granularidad final equivalente a Kilos: SUP + SEGMENTO."""
    if df_gross is None or df_gross.empty:
        return pd.DataFrame()

    trabajo = _filtrar_supervisor(df_gross, supervisor)
    trabajo = _aplicar_escenario_gross(trabajo, modo_proyeccion)
    if trabajo.empty:
        return pd.DataFrame()

    columnas_suma = [
        "Objetivo_Importe_Arg",
        "Arrastre",
        "Actual",
        "Importe_Operativo_Arg",
        "Gross_Proyectado_Arg",
        "Cumplimiento_Gross_Proy_Pct",
        "Promedio_Diario",
        "Media_Necesaria_Diaria",
        "Gross_Disponible",
        "Futuro_A_Incorporar_Gross",
        "Días Pasados",
        "Rutas",
        "Rutas_Ajustadas",
        "Días Restantes",
    ]

    faltantes = [col for col in columnas_suma if col not in trabajo.columns]
    if faltantes:
        raise ValueError(
            "Faltan columnas obligatorias en Gross Gerencial: " + ", ".join(faltantes)
        )

    resultado = trabajo.groupby(["SUP", "SEGMENTO"], as_index=False)[
        columnas_suma
    ].sum()

    resultado["Cumplimiento_Gross_Proy_Pct"] = (
        resultado["Gross_Proyectado_Arg"]
        .div(resultado["Objetivo_Importe_Arg"].replace(0, pd.NA))
        .mul(100)
        .fillna(0.0)
    )
    resultado["Modo_Proyeccion"] = modo_proyeccion
    return resultado


# ==========================================================
# CCC Y MI NEGOCIO
# ==========================================================
def construir_bloque_ccc(
    df_ccc: pd.DataFrame,
    maestro_ccc: pd.DataFrame,
) -> pd.DataFrame:
    if df_ccc is None or df_ccc.empty:
        return pd.DataFrame()
    return df_ccc.groupby(["Taxonomia"], as_index=False).agg(
        {
            "Cartera_Neta": "sum",
            "CCC_Gerencia": "sum",
            "Objetivo_CCC": "sum",
        }
    )


def construir_bloque_mn(df_mn: pd.DataFrame) -> pd.DataFrame:
    if df_mn is None or df_mn.empty:
        return pd.DataFrame()
    return df_mn.groupby(["Taxonomia"], as_index=False).agg(
        {"Ventas_Totales": "sum", "Ventas_MiNegocio": "sum"}
    )


# ==========================================================
# MOTOR DEL REPORTE (BASE CACHEADA + DERIVADO LIVIANO)
# ==========================================================
@st.cache_data(show_spinner=False)
def obtener_motor_gerencial_base(
    anio: int,
    mes: int,
    dia_matinal: str,
    dia_venta: str,
    supervisor: str = "TODOS",
) -> dict:
    filtros = {
        "anio": int(anio),
        "mes": int(mes),
        "dia_matinal": dia_matinal,
        "dia_venta": dia_venta,
        "supervisor": supervisor,
    }

    motor_base = obtener_motor_gerencial(int(anio), int(mes), filtros)
    maestro_ccc = cargar_maestro_ccc(anio, mes)

    df_ccc = obtener_matriz_ccc_comercial(int(anio), int(mes), filtros)
    df_mn = obtener_matriz_mn_comercial(int(anio), int(mes), filtros)

    return {
        "kilos_raw": motor_base.get("kilos", pd.DataFrame()),
        "gross_raw": motor_base.get("gross", pd.DataFrame()),
        "ccc": construir_bloque_ccc(df_ccc, maestro_ccc),
        "mn": construir_bloque_mn(df_mn),
    }


def construir_motor_gerencial_escenario(
    base: dict,
    modo_proyeccion: str,
    supervisor: str = "TODOS",
) -> dict:
    modo_proyeccion = str(modo_proyeccion).strip().upper()
    if modo_proyeccion not in {"TODO", "AJUSTADO"}:
        raise ValueError("modo_proyeccion debe ser 'TODO' o 'AJUSTADO'.")

    return {
        "kilos": construir_bloque_kilos(
            base.get("kilos_raw", pd.DataFrame()),
            modo_proyeccion,
            supervisor,
        ),
        "gross": construir_bloque_gross(
            base.get("gross_raw", pd.DataFrame()),
            modo_proyeccion,
            supervisor,
        ),
        "ccc": base.get("ccc", pd.DataFrame()),
        "mn": base.get("mn", pd.DataFrame()),
        "modo_proyeccion": modo_proyeccion,
    }


def obtener_motor_gerencial_core(
    anio: int,
    mes: int,
    dia_matinal: str,
    dia_venta: str,
    supervisor: str = "TODOS",
    modo_proyeccion: str = "AJUSTADO",
) -> dict:
    base = obtener_motor_gerencial_base(
        anio,
        mes,
        dia_matinal,
        dia_venta,
        supervisor,
    )
    return construir_motor_gerencial_escenario(
        base,
        modo_proyeccion,
        supervisor,
    )


# ==========================================================
# RENDERIZADORES DE PESTAÑAS
# ==========================================================
def _seleccion_local(
    df: pd.DataFrame,
    columna: str,
    etiqueta: str,
    key: str,
) -> pd.DataFrame:
    opciones = sorted(
        df[columna]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda serie: serie.ne("")]
        .unique()
        .tolist()
    )

    seleccion = st.multiselect(
        etiqueta,
        options=opciones,
        default=[],
        key=key,
    )

    if not seleccion:
        return df.copy()

    return df[df[columna].astype(str).str.strip().isin(seleccion)].copy()


def _render_tarjetas_una_linea(registros: list[dict], renderizador):
    if not registros:
        return
    columnas = st.columns(len(registros), gap="small")
    for indice, registro in enumerate(registros):
        with columnas[indice]:
            renderizador(registro)


def _render_pestana_kilos(df_kilos: pd.DataFrame):
    if df_kilos is None or df_kilos.empty:
        st.info("No hay datos gerenciales de Kilos para los filtros seleccionados.")
        return

    requeridas = [
        "Objetivo Mes Corriente",
        "OPERATIVO",
        "Tendencia_Total_Kg",
        "SEGMENTO",
    ]
    if not _validar_columnas_requeridas(df_kilos, requeridas, "Kilos Visual"):
        return

    df_filtrado = _seleccion_local(
        df_kilos,
        "SEGMENTO",
        "Segmentos de Kilos",
        "gerencial_filtro_segmentos_kilos_v2",
    )
    if df_filtrado.empty:
        st.warning("Seleccioná al menos un segmento de Kilos.")
        return

    objetivo = _numero_seguro(df_filtrado["Objetivo Mes Corriente"].sum())
    operativo = _numero_seguro(df_filtrado["OPERATIVO"].sum())
    tendencia = _numero_seguro(df_filtrado["Tendencia_Total_Kg"].sum())
    cumplimiento = tendencia / objetivo * 100.0 if objetivo > 0 else 0.0

    st.markdown("### KPIs ejecutivos - Kilos")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Objetivo Total", f"{objetivo:,.1f} kg")
    col2.metric("Operativo Total", f"{operativo:,.1f} kg")
    col3.metric("Tendencia Total", f"{tendencia:,.1f} kg")
    col4.metric(
        "Cumplimiento Proyectado",
        f"{cumplimiento:,.2f}%",
        delta=f"{cumplimiento - 100.0:,.2f} pp vs objetivo",
        delta_color="normal",
    )

    st.divider()
    st.markdown("### Resumen por segmento")
    segmentos = df_filtrado.groupby("SEGMENTO", as_index=False).agg(
        {
            "Objetivo Mes Corriente": "sum",
            "OPERATIVO": "sum",
            "Tendencia_Total_Kg": "sum",
        }
    )
    segmentos["Cumplimiento"] = (
        segmentos["Tendencia_Total_Kg"]
        .div(segmentos["Objetivo Mes Corriente"].replace(0, pd.NA))
        .mul(100)
        .fillna(0.0)
    )
    registros = segmentos.to_dict(orient="records")

    def renderizar(registro):
        _render_tarjeta_segmento(
            titulo=registro["SEGMENTO"],
            objetivo=registro["Objetivo Mes Corriente"],
            valor_principal=registro["OPERATIVO"],
            cumplimiento=registro["Cumplimiento"],
            etiqueta_principal="Operativo",
            tendencia=registro["Tendencia_Total_Kg"],
            es_moneda=False,
        )

    _render_tarjetas_una_linea(registros, renderizar)

    with st.expander("Ver detalle completo de Kilos", expanded=False):
        st.dataframe(df_filtrado, width="stretch", hide_index=True)


def _render_pestana_gross(df_gross: pd.DataFrame):
    if df_gross is None or df_gross.empty:
        st.info("No hay datos gerenciales de Gross para los filtros seleccionados.")
        return

    requeridas = [
        "Objetivo_Importe_Arg",
        "Importe_Operativo_Arg",
        "Gross_Proyectado_Arg",
        "Futuro_A_Incorporar_Gross",
        "SEGMENTO",
    ]
    if not _validar_columnas_requeridas(df_gross, requeridas, "Gross Visual"):
        return

    df_filtrado = _seleccion_local(
        df_gross,
        "SEGMENTO",
        "Segmentos de Gross",
        "gerencial_filtro_segmentos_gross_v2",
    )
    if df_filtrado.empty:
        st.warning("Seleccioná al menos un segmento de Gross.")
        return

    objetivo = _numero_seguro(df_filtrado["Objetivo_Importe_Arg"].sum())
    operativo = _numero_seguro(df_filtrado["Importe_Operativo_Arg"].sum())
    proyectado = _numero_seguro(df_filtrado["Gross_Proyectado_Arg"].sum())
    cumplimiento = proyectado / objetivo * 100.0 if objetivo > 0 else 0.0

    st.markdown("### KPIs ejecutivos - Gross")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Objetivo Gross", f"${objetivo:,.0f}")
    col2.metric("Gross Operativo", f"${operativo:,.0f}")
    col3.metric("Gross Proyectado", f"${proyectado:,.0f}")
    col4.metric(
        "Cumplimiento Proyectado",
        f"{cumplimiento:,.2f}%",
        delta=f"{cumplimiento - 100.0:,.2f} pp vs objetivo",
        delta_color="normal",
    )

    st.divider()
    st.markdown("### Resumen por segmento - Gross")
    segmentos = df_filtrado.groupby("SEGMENTO", as_index=False).agg(
        {
            "Objetivo_Importe_Arg": "sum",
            "Gross_Proyectado_Arg": "sum",
            "Futuro_A_Incorporar_Gross": "sum",
        }
    )
    segmentos["Cumplimiento"] = (
        segmentos["Gross_Proyectado_Arg"]
        .div(segmentos["Objetivo_Importe_Arg"].replace(0, pd.NA))
        .mul(100)
        .fillna(0.0)
    )
    registros = segmentos.to_dict(orient="records")

    def renderizar(registro):
        _render_tarjeta_segmento(
            titulo=registro["SEGMENTO"],
            objetivo=registro["Objetivo_Importe_Arg"],
            valor_principal=registro["Gross_Proyectado_Arg"],
            cumplimiento=registro["Cumplimiento"],
            etiqueta_principal="Proyección",
            incorporar=registro["Futuro_A_Incorporar_Gross"],
            es_moneda=True,
        )

    _render_tarjetas_una_linea(registros, renderizar)

    with st.expander("Ver detalle completo de Gross", expanded=False):
        st.dataframe(df_filtrado, width="stretch", hide_index=True)


def _render_pestana_ccc(df_ccc: pd.DataFrame):
    if df_ccc is None or df_ccc.empty:
        st.info("No hay datos de CCC para los filtros seleccionados.")
        return

    requeridas = ["Taxonomia", "Cartera_Neta", "CCC_Gerencia", "Objetivo_CCC"]
    if not _validar_columnas_requeridas(df_ccc, requeridas, "CCC Visual"):
        return

    df_filtrado = _seleccion_local(
        df_ccc,
        "Taxonomia",
        "Taxonomías de CCC",
        "gerencial_filtro_taxonomias_ccc_v2",
    )
    if df_filtrado.empty:
        st.warning("Seleccioná al menos una taxonomía de CCC.")
        return

    cartera = _numero_seguro(df_filtrado["Cartera_Neta"].sum())
    actual = _numero_seguro(df_filtrado["CCC_Gerencia"].sum())
    objetivo = _numero_seguro(df_filtrado["Objetivo_CCC"].sum())

    st.markdown("### KPIs ejecutivos - CCC")
    col1, col2, col3 = st.columns(3)
    col1.metric("Cartera Neta Total", f"{cartera:,.0f}")
    col2.metric("CCC Actual", f"{actual:,.0f}")
    col3.metric("Objetivo CCC", f"{objetivo:,.0f}")

    with st.expander("Ver detalle completo de CCC", expanded=False):
        st.dataframe(df_filtrado, width="stretch", hide_index=True)


def _render_pestana_mn(df_mn: pd.DataFrame):
    if df_mn is None or df_mn.empty:
        st.info("No hay datos de MiNegocio para los filtros seleccionados.")
        return

    requeridas = ["Taxonomia", "Ventas_Totales", "Ventas_MiNegocio"]
    if not _validar_columnas_requeridas(df_mn, requeridas, "MiNegocio Visual"):
        return

    df_filtrado = _seleccion_local(
        df_mn,
        "Taxonomia",
        "Taxonomías de MiNegocio",
        "gerencial_filtro_taxonomias_mn_v2",
    )
    if df_filtrado.empty:
        st.warning("Seleccioná al menos una taxonomía de MiNegocio.")
        return

    ventas = _numero_seguro(df_filtrado["Ventas_Totales"].sum())
    ventas_mn = _numero_seguro(df_filtrado["Ventas_MiNegocio"].sum())
    participacion = ventas_mn / ventas * 100.0 if ventas > 0 else 0.0

    st.markdown("### KPIs ejecutivos - MiNegocio")
    col1, col2, col3 = st.columns(3)
    col1.metric("Ventas Totales", f"${ventas:,.0f}")
    col2.metric("Ventas MiNegocio", f"${ventas_mn:,.0f}")
    col3.metric("Participación", f"{participacion:,.2f}%")

    with st.expander("Ver detalle completo de MiNegocio", expanded=False):
        st.dataframe(df_filtrado, width="stretch", hide_index=True)


# ==========================================================
# FRAGMENTO PRINCIPAL
# ==========================================================
@st.fragment
def render_fragmento_gerencial_core(
    filtros_globales: dict,
):
    modo_proyeccion = st.selectbox(
        "Modo de proyección para Kilos y Gross",
        options=["TODO", "AJUSTADO"],
        index=1,
        key=(
            f"gerencial_modo_proyeccion_"
            f"{filtros_globales['anio']}_{filtros_globales['mes']}"
        ),
    )

    st.caption(
        "TODO utiliza todas las rutas restantes. "
        "AJUSTADO descuenta las rutas configuradas en Rutas_Ajustadas. "
        "La atribución gerencial conserva al vendedor titular e incluye al vendedor 20."
    )

    motor = obtener_motor_gerencial_core(
        filtros_globales["anio"],
        filtros_globales["mes"],
        filtros_globales["dia_matinal"],
        filtros_globales["dia_venta"],
        filtros_globales.get("supervisor", "TODOS"),
        modo_proyeccion,
    )

    tab_k, tab_g, tab_c, tab_m = st.tabs(
        ["📦 KILOS", "💰 GROSS", "📈 CCC", "📱 MI NEGOCIO"]
    )

    with tab_k:
        _render_pestana_kilos(motor.get("kilos", pd.DataFrame()))

    with tab_g:
        _render_pestana_gross(motor.get("gross", pd.DataFrame()))

    with tab_c:
        _render_pestana_ccc(motor.get("ccc", pd.DataFrame()))

    with tab_m:
        _render_pestana_mn(motor.get("mn", pd.DataFrame()))


# ==========================================================
# RENDER PRINCIPAL
# ==========================================================
def render_rep_gerencial_core(filtros_globales: dict):
    st.subheader("📈 Tablero Ejecutivo Gerencial Core")
    render_fragmento_gerencial_core(filtros_globales)
