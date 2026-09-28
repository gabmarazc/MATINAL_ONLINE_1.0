# CODIGO CONSOLIDADO MATINAL


### ARCHIVO: app.py

# app.py
import streamlit as st
import pandas as pd
import time
from datetime import date, timedelta
from data_loader import cargar_todas_las_bases
from modules.parametros import (
    render_parametros_view,
    es_entorno_local,
    obtener_tabla_parametros,
)
from modules.rep_kilos import render_rep_kilos
from modules.rep_kilos_core import render_rep_kilos_core
from modules.rep_obj_kilos import render_rep_obj_kilos
from modules.rep_ccc import render_rep_ccc
from modules.rep_MN import render_rep_mn
from modules.rep_cob_marca import (
    generar_reporte_cobertura_marca,
    dibujar_pestana_cobertura_marca,
)
from modules.rep_cob_innovacion import (
    generar_reporte_cobertura_innovacion,
    dibujar_pestana_cobertura_innovacion,
)
from modules.rep_gerencial import render_rep_gerencial
from modules.rep_vespertina import render_rep_vespertina
from modules.rep_tp import render_rep_tp
from modules import database as db

st.set_page_config(
    page_title="Sistema de Gestión de Ventas - MABELHERDI S.A",
    page_icon="📊",
    layout="wide",
)

# Inyección CSS apuntando correctamente a los span de BaseWeb para forzar un tono gris en los tags seleccionados
st.markdown(
    """
    <style>
        span[data-baseweb="tag"] {
            background-color: #475569 !important;
            border: 1px solid #64748b !important;
        }
        span[data-baseweb="tag"] span {
            color: #f8fafc !important;
        }
        span[data-baseweb="tag"] svg {
            fill: #cbd5e1 !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)


def calcular_fechas_operativas_default():
    hoy = date.today()
    if hoy.weekday() == 0:
        dia_vta = hoy - timedelta(days=2)
    elif hoy.weekday() == 6:
        dia_vta = hoy - timedelta(days=1)
    else:
        dia_vta = hoy - timedelta(days=1)

    if dia_vta.weekday() == 0:
        dia_ant = dia_vta - timedelta(days=2)
    else:
        dia_ant = dia_vta - timedelta(days=1)

    return hoy, dia_vta, dia_ant


def verificar_autenticacion():
    """Valida el ingreso por nivel de usuario y contraseña antes de permitir operar."""
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
        st.session_state["nivel_usuario"] = None

    if not st.session_state["autenticado"]:
        st.title("🔒 Sistema de Gestión de Ventas - MABELHERDI S.A")
        st.markdown("### Acceso Restringido")

        with st.form("form_login"):
            nivel_sel = st.selectbox(
                "Seleccione Nivel de Acceso",
                ["Nivel 1: Administrador", "Nivel 2: Gerencia", "Nivel 3: Supervisión"],
            )
            password = st.text_input("Contraseña de Acceso", type="password")
            btn_login = st.form_submit_button("Ingresar al Sistema")

            if btn_login:
                passwords_validos = {
                    "Nivel 1: Administrador": "admin2026",
                    "Nivel 2: Gerencia": "gerencia2026",
                    "Nivel 3: Supervisión": "sup2026",
                }

                if passwords_validos.get(nivel_sel) == password:
                    st.session_state["autenticado"] = True
                    st.session_state["nivel_usuario"] = nivel_sel
                    st.success("¡Acceso concedido! Cargando sistema...")
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta. Verifique sus credenciales.")
        return False
    return True


def main():
    t_rerun_start = time.perf_counter()

    # Telemetría forense: Control de Reruns Globales (Requisitos A y B)
    if "_global_rerun_count" not in st.session_state:
        st.session_state["_global_rerun_count"] = 0
    st.session_state["_global_rerun_count"] += 1
    print(
        f"[PERF_FORENSIC] === INICIO RERUN GLOBAL N° {st.session_state['_global_rerun_count']} === [Timestamp: {t_rerun_start:.4f}]"
    )

    if not verificar_autenticacion():
        return

    st.title("Sistema de Gestión de Ventas - MABELHERDI S.A")

    nivel_actual = st.session_state.get("nivel_usuario", "")
    st.sidebar.info(f"Sesión activa: **{nivel_actual}**")
    if st.sidebar.button("🔒 Cerrar Sesión", width="stretch"):
        st.session_state["autenticado"] = False
        st.session_state["nivel_usuario"] = None
        st.rerun()

    def_matinal, def_vta, def_ant = calcular_fechas_operativas_default()

    if "sel_dia_matinal" not in st.session_state:
        st.session_state["sel_dia_matinal"] = def_matinal
    if "sel_dia_venta" not in st.session_state:
        st.session_state["sel_dia_venta"] = def_vta
    if "sel_dia_anterior" not in st.session_state:
        st.session_state["sel_dia_anterior"] = def_ant

    st.sidebar.header("⚙️ Control de Datos")

    if st.sidebar.button("🧹 Limpiar Caché", width="stretch"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.sidebar.success("¡Caché purgada con éxito!")
        st.rerun()

    if st.sidebar.button("🔄 Recargar Bases", width="stretch"):
        t_inicio = time.time()
        with st.status(
            "Sincronizando motores de datos y SQLite...", expanded=True
        ) as status:
            st.write("Leyendo archivos fuente Excel...")
            prog_bar = st.progress(20, text="Iniciando lectura de bases...")
            time.sleep(0.1)
            prog_bar.progress(50, text="Procesando registros en SQLite...")
            st.session_state["bases"] = cargar_todas_las_bases(forzar=True)
            prog_bar.progress(100, text="¡Sincronización completada!")
            t_fin = time.time()
            duracion = t_fin - t_inicio
            status.update(
                label=f"¡Bases recargadas desde disco en {duracion:.2f} segundos!",
                state="complete",
                expanded=False,
            )
        st.rerun()

    if "bases" not in st.session_state or st.session_state["bases"] is None:
        with st.status(
            "Cargando bases de datos y ausencias...", expanded=True
        ) as status:
            st.write("Conectando con motores de almacenamiento...")
            prog_bar = st.progress(20, text="Iniciando conexión con bases...")
            time.sleep(0.1)
            prog_bar.progress(60, text="Cargando tablas operativas...")
            st.session_state["bases"] = cargar_todas_las_bases()
            prog_bar.progress(100, text="¡Carga completada!")

    datos = st.session_state["bases"]

    print(f"[AUDIT] TP_SESSION = {len(st.session_state['bases']['TP'])}")
    print(f"[AUDIT] TP_SQLITE  = {len(db.cargar_tabla_sql('SELECT * FROM tp'))}")
    print(f"[AUDIT] ID_SESSION_BASES = {id(st.session_state['bases'])}")
    print(f"[AUDIT] ID_DATOS = {id(datos)}")

    df_vta = datos.get("VTA") if datos else pd.DataFrame()
    df_universo = datos.get("UNIVERSO") if datos else pd.DataFrame()
    df_rutas = datos.get("RUTAS") if datos else pd.DataFrame()
    df_ausencias = datos.get("AUSENCIAS") if datos else pd.DataFrame()

    if df_vta is None or df_universo is None or df_vta.empty or df_universo.empty:
        st.warning(
            "⚠️ No se encontraron datos operativos en la base de datos local. Por favor, sube los archivos iniciales para poblar SQLite:"
        )
        col1, col2 = st.columns(2)
        with col1:
            up_vta = st.file_uploader(
                "Subir Archivo VTA (.xlsx)", type=["xlsx", "xls"], key="up_vta"
            )
            up_univ = st.file_uploader(
                "Subir Archivo UNIVERSO (.xlsx)", type=["xlsx", "xls"], key="up_univ"
            )
        with col2:
            up_rutas = st.file_uploader(
                "Subir Archivo RUTAS (.xlsx)", type=["xlsx", "xls"], key="up_rutas"
            )

        if (
            up_vta
            and up_univ
            and up_rutas
            and not st.session_state.get("bd_inicializada", False)
        ):
            with st.status(
                "Procesando y guardando archivos en SQLite...", expanded=True
            ) as status:
                archivos_dict = {"vta": up_vta, "universo": up_univ, "rutas": up_rutas}
                db.inicializar_bd_desde_excel(archivos_dict)
                st.session_state["bd_inicializada"] = True
            st.success(
                "¡Base de datos inicializada con éxito! Recargando aplicación..."
            )
            st.rerun()
        elif not st.session_state.get("bd_inicializada", False):
            st.info(
                "ℹ️ Sube los tres archivos requeridos (VTA, Universo y Rutas) para habilitar el sistema."
            )
            return

    supervisores_disponibles = ["TODOS"]
    col_sup = None
    for cand in ["Supervisor", "SUPERVISOR", "Cod_Supervisor", "Cod_Sup"]:
        if cand in df_vta.columns:
            col_sup = cand
            break

    if col_sup:
        sups_unicos = sorted(
            [str(s) for s in df_vta[col_sup].dropna().unique() if str(s).strip() != ""]
        )
        supervisores_disponibles.extend(sups_unicos)
    else:
        try:
            df_m = db.cargar_tabla_sql(
                "SELECT DISTINCT Supervisor FROM maestro_vendedores"
            )
            if not df_m.empty and "Supervisor" in df_m.columns:
                sups_unicos = sorted(
                    [
                        str(s)
                        for s in df_m["Supervisor"].dropna().unique()
                        if str(s).strip() != ""
                    ]
                )
                supervisores_disponibles.extend(sups_unicos)
        except Exception:
            pass

    st.sidebar.header("🎛️ Filtros Globales")

    with st.sidebar.expander("📅 Fechas de Referencia", expanded=True):
        sel_dia_matinal = st.date_input(
            "Día Matinal",
            min_value=date(2020, 1, 1),
            format="DD/MM/YYYY",
            key="sel_dia_matinal",
        )
        sel_dia_venta = st.date_input(
            "Día Venta",
            min_value=date(2020, 1, 1),
            format="DD/MM/YYYY",
            key="sel_dia_venta",
        )
        sel_dia_anterior = st.date_input(
            "Día Anterior",
            min_value=date(2020, 1, 1),
            format="DD/MM/YYYY",
            key="sel_dia_anterior",
        )

    anio_sugerido = sel_dia_venta.year
    mes_sugerido = sel_dia_venta.month

    opciones_anio = [2023, 2024, 2025, 2026, 2027, 2028]
    idx_anio = (
        opciones_anio.index(anio_sugerido) if anio_sugerido in opciones_anio else 3
    )
    anio_operativo = st.sidebar.selectbox(
        "Año Operativo", opciones_anio, index=idx_anio, key="sel_anio_op"
    )

    opciones_mes = list(range(1, 13))
    mes_operativo = st.sidebar.selectbox(
        "Mes Operativo", opciones_mes, index=mes_sugerido - 1, key="sel_mes_op"
    )

    sel_supervisor = st.sidebar.selectbox(
        "Supervisor", supervisores_disponibles, index=0, key="sel_sup_op"
    )

    filtros_globales = {
        "anio": int(anio_operativo),
        "mes": int(mes_operativo),
        "supervisor": sel_supervisor,
        "dia_matinal": sel_dia_matinal.strftime("%d/%m/%Y"),
        "dia_venta": sel_dia_venta.strftime("%d/%m/%Y"),
        "dia_anterior": sel_dia_anterior.strftime("%d/%m/%Y"),
    }

    sup_sel_efectivo = (
        supervisores_disponibles[1:]
        if filtros_globales["supervisor"] == "TODOS"
        else [filtros_globales["supervisor"]]
    )

    es_local = es_entorno_local()

    if "Nivel 1" in nivel_actual or "Nivel 2" in nivel_actual:
        if es_local and "Nivel 1" in nivel_actual:
            tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab_core = (
                st.tabs(
                    [
                        "📈 Tablero Gerencial",
                        "📊 Avance Kilos",
                        "📈 Avance CCC",
                        "🎯 Cobertura Marca",
                        "🚀 Cobertura Innovación",
                        "📱 Adopción MiNegocio",
                        "🌙 Vespertina",
                        "⭐ Tienda Perfecta",
                        "⚙️ Parámetros",
                        "📦 Composición Obj Kilos",
                        "🧪 Avance Kilos CORE",
                    ]
                )
            )
        else:
            tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab_core = st.tabs(
                [
                    "📈 Tablero Gerencial",
                    "📊 Avance Kilos",
                    "📈 Avance CCC",
                    "🎯 Cobertura Marca",
                    "🚀 Cobertura Innovación",
                    "📱 Adopción MiNegocio",
                    "🌙 Vespertina",
                    "⭐ Tienda Perfecta",
                    "📦 Composición Obj Kilos",
                    "🧪 Avance Kilos CORE",
                ]
            )
    else:
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab_core = st.tabs(
            [
                "📊 Avance Kilos",
                "📈 Avance CCC",
                "🎯 Cobertura Marca",
                "🚀 Cobertura Innovación",
                "📱 Adopción MiNegocio",
                "🌙 Vespertina",
                "⭐ Tienda Perfecta",
                "🧪 Avance Kilos CORE",
            ]
        )

    df_vend_maestro = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    df_marcas_maestro = pd.DataFrame()

    # Telemetría por etapas [PERF_STAGE]
    t0_m = time.perf_counter()
    rep_cob, marcas_lst, mapa_obj = generar_reporte_cobertura_marca(
        df_vta, df_universo, df_vend_maestro, df_marcas_maestro, filtros_globales
    )
    print(
        f"[PERF_STAGE] generar_reporte_cobertura_marca = {time.perf_counter() - t0_m:.2f} s"
    )

    t0_i = time.perf_counter()
    rep_innov, innovaciones_lst, df_innov_master = generar_reporte_cobertura_innovacion(
        df_vta, df_universo, df_vend_maestro, filtros_globales
    )
    print(
        f"[PERF_STAGE] generar_reporte_cobertura_innovacion = {time.perf_counter() - t0_i:.2f} s"
    )

    # Renderizado de pestañas acorde al perfil activo con telemetría de procesamiento
    if "Nivel 1" in nivel_actual:
        with tab1:
            t0_g = time.perf_counter()
            render_rep_gerencial(
                df_vta, df_universo, df_rutas, df_ausencias, filtros_globales
            )
            print(
                f"[PERF_STAGE] render_rep_gerencial = {time.perf_counter() - t0_g:.2f} s"
            )
        with tab2:
            t0_k = time.perf_counter()
            render_rep_kilos(df_vta, df_rutas, df_ausencias, filtros_globales)
            print(f"[PERF] render_rep_kilos: {time.perf_counter() - t0_k:.2f} s")
        with tab3:
            t0_c = time.perf_counter()
            render_rep_ccc(df_vta, df_universo, filtros_globales)
            print(f"[PERF] render_rep_ccc: {time.perf_counter() - t0_c:.2f} s")
        with tab4:
            dibujar_pestana_cobertura_marca(
                rep_cob, marcas_lst, mapa_obj, sup_sel_efectivo, df_vta, df_universo
            )
        with tab5:
            dibujar_pestana_cobertura_innovacion(
                rep_innov, innovaciones_lst, df_innov_master, sup_sel_efectivo
            )
        with tab6:
            t0_mn = time.perf_counter()
            render_rep_mn(df_vta, df_universo, filtros_globales)
            print(f"[PERF_STAGE] render_rep_mn = {time.perf_counter() - t0_mn:.2f} s")
        with tab7:
            t0_v = time.perf_counter()
            render_rep_vespertina(df_vta, df_universo, filtros_globales)
            print(
                f"[PERF_STAGE] render_rep_vespertina = {time.perf_counter() - t0_v:.2f} s"
            )
        with tab8:
            t0_tp = time.perf_counter()
            render_rep_tp(datos)
            print(f"[PERF] render_rep_tp: {time.perf_counter() - t0_tp:.2f} s")
        if es_local:
            with tab9:
                render_parametros_view(filtros_globales)
            with tab10:
                render_rep_obj_kilos(df_vta, filtros_globales)
        else:
            with tab9:
                render_rep_obj_kilos(df_vta, filtros_globales)
        with tab_core:
            t0_kc = time.perf_counter()
            render_rep_kilos_core(df_vta, df_rutas, df_ausencias, filtros_globales)
            print(f"[PERF] render_rep_kilos_core: {time.perf_counter() - t0_kc:.2f} s")
    elif "Nivel 2" in nivel_actual:
        with tab1:
            t0_g = time.perf_counter()
            render_rep_gerencial(
                df_vta, df_universo, df_rutas, df_ausencias, filtros_globales
            )
            print(
                f"[PERF_STAGE] render_rep_gerencial = {time.perf_counter() - t0_g:.2f} s"
            )
        with tab2:
            t0_k = time.perf_counter()
            render_rep_kilos(df_vta, df_rutas, df_ausencias, filtros_globales)
            print(f"[PERF] render_rep_kilos: {time.perf_counter() - t0_k:.2f} s")
        with tab3:
            t0_c = time.perf_counter()
            render_rep_ccc(df_vta, df_universo, filtros_globales)
            print(f"[PERF] render_rep_ccc: {time.perf_counter() - t0_c:.2f} s")
        with tab4:
            dibujar_pestana_cobertura_marca(
                rep_cob, marcas_lst, mapa_obj, sup_sel_efectivo, df_vta, df_universo
            )
        with tab5:
            dibujar_pestana_cobertura_innovacion(
                rep_innov, innovaciones_lst, df_innov_master, sup_sel_efectivo
            )
        with tab6:
            t0_mn = time.perf_counter()
            render_rep_mn(df_vta, df_universo, filtros_globales)
            print(f"[PERF_STAGE] render_rep_mn = {time.perf_counter() - t0_mn:.2f} s")
        with tab7:
            t0_v = time.perf_counter()
            render_rep_vespertina(df_vta, df_universo, filtros_globales)
            print(
                f"[PERF_STAGE] render_rep_vespertina = {time.perf_counter() - t0_v:.2f} s"
            )
        with tab8:
            t0_tp = time.perf_counter()
            render_rep_tp(datos)
            print(f"[PERF] render_rep_tp: {time.perf_counter() - t0_tp:.2f} s")
        with tab9:
            render_rep_obj_kilos(df_vta, filtros_globales)
        with tab_core:
            t0_kc = time.perf_counter()
            render_rep_kilos_core(df_vta, df_rutas, df_ausencias, filtros_globales)
            print(f"[PERF] render_rep_kilos_core: {time.perf_counter() - t0_kc:.2f} s")
    else:
        # Nivel 3: Supervisión
        with tab1:
            t0_k = time.perf_counter()
            render_rep_kilos(df_vta, df_rutas, df_ausencias, filtros_globales)
            print(f"[PERF] render_rep_kilos: {time.perf_counter() - t0_k:.2f} s")
        with tab2:
            t0_c = time.perf_counter()
            render_rep_ccc(df_vta, df_universo, filtros_globales)
            print(f"[PERF] render_rep_ccc: {time.perf_counter() - t0_c:.2f} s")
        with tab3:
            dibujar_pestana_cobertura_marca(
                rep_cob, marcas_lst, mapa_obj, sup_sel_efectivo, df_vta, df_universo
            )
        with tab4:
            dibujar_pestana_cobertura_innovacion(
                rep_innov, innovaciones_lst, df_innov_master, sup_sel_efectivo
            )
        with tab5:
            t0_mn = time.perf_counter()
            render_rep_mn(df_vta, df_universo, filtros_globales)
            print(f"[PERF_STAGE] render_rep_mn = {time.perf_counter() - t0_mn:.2f} s")
        with tab6:
            t0_v = time.perf_counter()
            render_rep_vespertina(df_vta, df_universo, filtros_globales)
            print(
                f"[PERF_STAGE] render_rep_vespertina = {time.perf_counter() - t0_v:.2f} s"
            )
        with tab7:
            t0_tp = time.perf_counter()
            render_rep_tp(datos)
            print(f"[PERF] render_rep_tp: {time.perf_counter() - t0_tp:.2f} s")
        with tab_core:
            t0_kc = time.perf_counter()
            render_rep_kilos_core(df_vta, df_rutas, df_ausencias, filtros_globales)
            print(f"[PERF] render_rep_kilos_core: {time.perf_counter() - t0_kc:.2f} s")

    t_rerun_total = time.perf_counter() - t_rerun_start
    print(
        f"[PERF_FORENSIC] === FIN RERUN GLOBAL N° {st.session_state['_global_rerun_count']} | Duración Total: {t_rerun_total:.2f} s ==="
    )


if __name__ == "__main__":
    main()


====================================================================================================


### ARCHIVO: config.py

# config.py
import os

# Directorio raíz del proyecto y directorio de datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Rutas completas a los archivos dentro de la carpeta /data
ARCHIVO_VTA_EXCEL = os.path.join(DATA_DIR, "VTA.xlsx")
ARCHIVO_VTA_PARQUET = os.path.join(DATA_DIR, "VTA.parquet")
ARCHIVO_UNIVERSO = os.path.join(DATA_DIR, "UNIVERSO.xlsx")
ARCHIVO_PARAMETROS = os.path.join(DATA_DIR, "PARAMETROS.xlsx")
ARCHIVO_RUTAS = os.path.join(DATA_DIR, "RUTAS.xlsx")

# Mantener compatibilidad por variable genérica si algún módulo usa ARCHIVO_VTA
ARCHIVO_VTA = ARCHIVO_VTA_PARQUET if os.path.exists(ARCHIVO_VTA_PARQUET) else ARCHIVO_VTA_EXCEL

# URL Google Sheets Ausencias
URL_AUSENCIAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTt1sbO_3jsIldtNBos3vFN3kKQ68y1lcF1qUy5MfzFzNez0VSli0WGkjC_BG6UaHPYmg1aP9eJPiKk/pub?output=csv"

# Definición de columnas matriciales
COLUMNAS_BASE_EXTVTA = [
    "Cliente", "FechaEntrega", "FechaCarga", "TipoDeVenta", "Codigo",
    "CantBase", "ImporteNetoItem", "ImporteItem", "PrecioCosto",
    "MotivoDevolucion", "CodVendedor", "Articulo", "Reparto", "Subramo",
    "Proveedor", "PesoKg", "Marca", "Rubro", "Tags",
    "SegmentoRentabilidad", "Origen", "Taxonomia",
]

COLUMNAS_FINALES_EXTVTA = [
    "Cliente", "FechaEntrega", "FechaCarga", "TipoDeVenta", "Codigo",
    "CantBase", "ImporteNetoItem", "ImporteItem", "PrecioCosto",
    "MotivoDevolucion", "CodVendedor", "CodVendedorOperativo", "Articulo",
    "Reparto", "Subramo", "Proveedor", "PesoKg", "Marca", "Rubro", "Tags",
    "SegmentoRentabilidad", "SEGMENTO", "Origen", "Taxonomia",
    "MesCarga", "AñoCarga", "MesEntrega", "AñoEntrega", "Periodo",
]

====================================================================================================


### ARCHIVO: data_loader.py

# data_loader.py
import os
import config as cfg
from modules import database as db
import pandas as pd
import streamlit as st
import urllib.request
import io


@st.cache_data(ttl=3600, show_spinner=False)
def cargar_ausencias_remotas(url_ausencias):
    """Carga ausencias desde la web con manejo seguro de timeout para evitar bloqueos"""
    df_vacio = pd.DataFrame(
        columns=[
            "Marca temporal",
            "Dirección de correo electrónico",
            "Fecha",
            "Ausente",
            "Reemplazo",
            "Cliente",
        ]
    )
    if not url_ausencias:
        return df_vacio

    try:
        req = urllib.request.Request(
            url_ausencias, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            contenido = response.read()
            ausencias_crudas = pd.read_csv(
                io.BytesIO(contenido), encoding="utf-8", on_bad_lines="skip"
            )
            if ausencias_crudas.empty or "Fecha" not in ausencias_crudas.columns:
                return df_vacio
            return ausencias_crudas
    except Exception:
        return df_vacio


def sincronizar_archivos_excel_locales(forzar=False):
    """Sincroniza archivos Excel locales a SQLite. Si forzar=True, reconstruye las tablas desde los Excel encontrados."""
    db_path = "data/matinal.db"
    if os.path.exists(db_path) and not forzar:
        return

    posibles_rutas = ["data", "."]
    archivos_encontrados = {}

    mapeo_claves = {
        "vta": ["vta"],
        "universo": ["universo"],
        "rutas": ["ruta"],
        "altas": ["alta"],
        "maestro_vendedores": ["vendedor", "maestro_vendedores"],
        "maestro_segmentos": ["segmento", "maestro_segmentos"],
        "maestro_ccc": ["ccc", "maestro_ccc"],
        "maestro_marcas_cebe": ["cebe", "marcas_cebe", "maestro_marcas_cebe"],
        "parametros_marcas": ["parametros_marcas", "parametros", "parametro_marca"],
        "maestro_innovaciones": ["innovacion", "innovaciones", "maestro_innovaciones"],
        "tp": ["tp", "tienda_perfecta", "tienda perfecta"],
    }

    for d in posibles_rutas:
        if not os.path.exists(d):
            continue
        try:
            for archivo in os.listdir(d):
                if not archivo.lower().endswith((".xlsx", ".xls")):
                    continue
                ruta_completa = os.path.join(d, archivo)
                if os.path.isdir(ruta_completa):
                    continue

                nombre_norm = archivo.lower().replace(" ", "_").replace("-", "_")

                for tabla, keywords in mapeo_claves.items():
                    if tabla not in archivos_encontrados:
                        if any(kw in nombre_norm for kw in keywords):
                            archivos_encontrados[tabla] = ruta_completa
        except Exception:
            pass

    if archivos_encontrados:
        try:
            print("ARCHIVOS_ENCONTRADOS:", archivos_encontrados)

            db.inicializar_bd_desde_excel(archivos_encontrados)

            print("INICIALIZACION SQLITE FINALIZADA")

        except Exception as e:
            import traceback

            print("ERROR EN inicializar_bd_desde_excel")
            print(str(e))

            traceback.print_exc()

            raise


def cargar_todas_las_bases(forzar=False):
    """Carga de bases operativas desde SQLite y ausencias remotas. Si forzar=True, re-sincroniza desde los Excel locales."""
    sincronizar_archivos_excel_locales(forzar=forzar)

    df_vta = db.cargar_tabla_sql("SELECT * FROM vta")
    df_universo = db.cargar_tabla_sql("SELECT * FROM universo")
    df_rutas = db.cargar_tabla_sql("SELECT * FROM rutas")
    df_altas = db.cargar_tabla_sql("SELECT * FROM altas")
    df_tp = db.cargar_tabla_sql("SELECT * FROM tp")

    renombres = {
        "Codigo": "Cliente",
        "codven": "CodVendedor",
        "SegmentoClienteCodigo": "Taxonomia",
    }

    if not df_universo.empty:
        for col in df_universo.columns:
            col_clean = str(col).strip().lower()
            if col_clean in [
                "nombre",
                "razon_social",
                "razonsocial",
                "descripcion",
                "cliente_nombre",
            ]:
                renombres[col] = "NombreCliente"
            if col_clean in ["direccion", "domicilio"]:
                renombres[col] = "DireccionCliente"
        df_universo = df_universo.rename(columns=renombres)

    if not df_rutas.empty:
        if "Codigo" in df_rutas.columns:
            df_rutas["Codigo"] = pd.to_numeric(
                df_rutas["Codigo"], errors="coerce"
            ).astype("Int64")

        col_fecha_rutas = "Fecha"
        for c in df_rutas.columns:
            if str(c).strip().lower() in ["fecha", "fechacarga", "fecha_carga"]:
                col_fecha_rutas = c
                break
        if col_fecha_rutas in df_rutas.columns:
            df_rutas = df_rutas.rename(columns={col_fecha_rutas: "Fecha"})
            df_rutas["Fecha"] = pd.to_datetime(df_rutas["Fecha"], errors="coerce")

    if not df_altas.empty:
        col_fecha_altas = "Fecha"
        for c in df_altas.columns:
            if str(c).strip().lower() in ["fecha", "fechacarga", "fecha_alta"]:
                col_fecha_altas = c
                break
        if col_fecha_altas in df_altas.columns:
            df_altas = df_altas.rename(columns={col_fecha_altas: "Fecha"})
            df_altas["Fecha"] = pd.to_datetime(df_altas["Fecha"], errors="coerce")
        if "Codigo" in df_altas.columns:
            df_altas["Codigo"] = pd.to_numeric(
                df_altas["Codigo"], errors="coerce"
            ).astype("Int64")
        if "Vendedor" in df_altas.columns:
            df_altas["Vendedor"] = pd.to_numeric(
                df_altas["Vendedor"], errors="coerce"
            ).astype("Int64")

    ausencias_crudas = cargar_ausencias_remotas(getattr(cfg, "URL_AUSENCIAS", ""))

    if not ausencias_crudas.empty:
        db.guardar_dataframe_sql(ausencias_crudas, "ausencias", if_exists="replace")

    return {
        "VTA": df_vta,
        "UNIVERSO": df_universo,
        "RUTAS": df_rutas,
        "ALTAS": df_altas,
        "AUSENCIAS": ausencias_crudas,
        "TP": df_tp,
    }


====================================================================================================


### ARCHIVO: generar_objetivos_manuales.py

# generar_objetivos_manuales.py
import io
import streamlit as st
import pandas as pd
from modules import database as db
from modules.rep_obj_kilos import generar_distribucion_objetivos_macro

st.set_page_config(
    page_title="Generador Exclusivo de Objetivos Globales",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Desagregación Global de Objetivos por Vendedor y Segmento")
st.markdown("Esta herramienta procesa la participación histórica y la distribuye sobre los objetivos globales ingresados, generando el archivo Excel final para la calibración.")

OBJETIVOS_GLOBALES_DICT = {
    1: 2500,
    2: 2144,
    3: 2500,
    4: 2800,
    5: 2100,
    6: 3814,
    8: 3100,
    9: 3350,
    10: 3764,
    11: 2296,
    13: 3100,
    14: 3078,
    15: 3020,
    19: 2800,
    22: 2850,
    23: 3580,
    24: 2259,
    25: 2606,
    28: 2300,
    32: 2400,
    37: 2135,
    39: 1950,
    40: 2200
}

col1, col2 = st.columns(2)
with col1:
    anio_op = st.number_input("Año Operativo", value=2026, step=1)
with col2:
    mes_op = st.number_input("Mes Operativo", value=9, min_value=1, max_value=12, step=1)

if st.button("🚀 Calcular y Generar Excel Desagregado", type="primary"):
    with st.spinner("Cargando bases operativas y calculando participaciones..."):
        df_vta = db.cargar_tabla_sql("SELECT * FROM vta")
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        maestro_seg = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos")
        maestro_cebe_act = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        maestro_cebe_ant = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")

        if df_vta.empty or maestro_v.empty:
            st.error("⚠️ No se encontraron las tablas 'vta' o 'maestro_vendedores' en la base SQLite. Verifique que el sistema principal haya sido inicializado.")
        else:
            df_base, seg_orden = generar_distribucion_objetivos_macro(
                df_vta, maestro_v, maestro_cebe_act, maestro_cebe_ant, maestro_seg, int(anio_op), int(mes_op)
            )

            if df_base.empty:
                st.warning("⚠️ El motor no pudo calcular participaciones para el período seleccionado.")
            else:
                # CONSOLIDACIÓN CRÍTICA: Agrupación estricta por Vendedor y Segmento para evitar filas duplicadas por marca
                df_base = df_base.groupby(
                    ["Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "SEGMENTO"],
                    as_index=False
                ).agg({
                    "Kilos_Mes_Anterior": "sum",
                    "Objetivo_Mes_Anterior_Kg": "sum"
                })

                df_base["Logro_Anterior_Pct"] = (
                    df_base["Kilos_Mes_Anterior"] / df_base["Objetivo_Mes_Anterior_Kg"].replace(0, pd.NA)
                ).mul(100).fillna(0.0)

                # Cálculo de la participación porcentual de cada segmento sobre el total histórico consolidado del vendedor
                totales_vendedor = df_base.groupby("CodVendedor")["Kilos_Mes_Anterior"].transform("sum")
                df_base["Participacion_Segmento"] = (df_base["Kilos_Mes_Anterior"] / totales_vendedor.replace(0, pd.NA)).fillna(0.0)

                # Mapeo y aplicación del objetivo global fijo por CodVendedor
                df_base["Objetivo_Global_Vendor"] = df_base["CodVendedor"].map(OBJETIVOS_GLOBALES_DICT).fillna(0.0)
                df_base["Obj_Sugerido_Kg"] = df_base["Objetivo_Global_Vendor"] * df_base["Participacion_Segmento"]

                df_final = df_base[[
                    "Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "SEGMENTO", 
                    "Kilos_Mes_Anterior", "Objetivo_Mes_Anterior_Kg", "Logro_Anterior_Pct", 
                    "Obj_Sugerido_Kg"
                ]].copy()

                df_final = df_final.sort_values(by=["Supervisor", "Nombre", "SEGMENTO"]).reset_index(drop=True)

                st.success("¡Desagregación completada con éxito!")
                st.dataframe(df_final, width="stretch")

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df_final.to_excel(writer, index=False, sheet_name="Objetivos_Desagregados")
                buffer.seek(0)

                st.download_button(
                    label="📥 Descargar Excel de Objetivos Desagregados para Importar",
                    data=buffer,
                    file_name=f"Objetivos_Desagregados_{mes_op}_{anio_op}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

====================================================================================================


### ARCHIVO: requirements.txt

streamlit>=1.32.0
pandas>=2.0.0
streamlit-aggrid>=1.0.5
openpyxl>=3.1.0
xlsxwriter>=3.1.0

====================================================================================================


### ARCHIVO: runtime.txt

python-3.11

====================================================================================================


### ARCHIVO: .gitignore

__pycache__/
.venv/
venv/
data/*.db
data/*.xlsx
data/*.parquet
.DS_Store


====================================================================================================


### ARCHIVO: iniciar_sistema.bat

@echo off
TITLE Lanzador Automatizado - Sistema Matinal 2.0
cd /d "C:\Proyectos\MATINAL ONLINE"

echo [1/2] Levantando servidor local de Streamlit...
start "Streamlit_Matinal" /min cmd /c "streamlit run app.py"

:: Pausa de 5 segundos para garantizar la inicializacion del puerto 8501
timeout /t 5 /nobreak > nul

echo [2/2] Generando tunel cifrado de Cloudflare...
start "Cloudflare_Tunnel" /min cmd /c "cloudflared tunnel --url http://localhost:8501"

exit

====================================================================================================


### ARCHIVO: modules\__init__.py



====================================================================================================


### ARCHIVO: modules\business_rules\business_rules_kilos.py

# modules/business_rules/business_rules_kilos.py
import time
import streamlit as st
import pandas as pd
import numpy as np

# REGLA DE ORO: Consumo exclusivo de la Capa CORE y el Repositorio de Business Rules (Cero acceso a RAW, STAGING o base de datos)
from modules.core.core_vendedores import obtener_core_vendedores
from modules.core.core_operaciones import obtener_core_operacion
from modules.business_rules.business_rules_repository import (
    obtener_objetivos_vendedores,
)


def _asegurar_segmento_comercial(df: pd.DataFrame) -> pd.DataFrame:
    """
    BUSINESS_RULES: Replica exactamente la lógica de segmentación del legacy (rep_kilos.py)
    a partir de SegmentoRentabilidad y Rubro, asegurando la existencia de la columna 'SEGMENTO'.
    """
    if df is None or df.empty:
        return df

    df_trabajo = df.copy()

    if "SEGMENTO" not in df_trabajo.columns or df_trabajo["SEGMENTO"].isna().all():
        col_rent = (
            "SegmentoRentabilidad"
            if "SegmentoRentabilidad" in df_trabajo.columns
            else None
        )
        col_rubro = "Rubro" if "Rubro" in df_trabajo.columns else None

        sr = (
            df_trabajo.get(col_rent, pd.Series("", index=df_trabajo.index))
            .fillna("")
            .astype(str)
            .str.strip()
            .str.title()
            if col_rent
            else pd.Series("", index=df_trabajo.index)
        )
        rubro = (
            df_trabajo.get(col_rubro, pd.Series("", index=df_trabajo.index))
            .fillna("")
            .astype(str)
            .str.strip()
            if col_rubro
            else pd.Series("", index=df_trabajo.index)
        )

        cond_gold = sr.isin(["Platinum", "Gold"]).fillna(False)
        cond_silver = sr.isin(["Silver", "Bronze"]).fillna(False)

        gold_val = "GOLD " + rubro
        silver_val = "SILVER " + rubro
        df_trabajo["SEGMENTO"] = np.select(
            [cond_gold, cond_silver],
            [gold_val.str.strip(), silver_val.str.strip()],
            default=None,
        )

    return df_trabajo


@st.cache_data(show_spinner=False)
def calcular_objetivos_comerciales_kilos(anio: int, mes: int) -> pd.DataFrame:
    """
    BUSINESS_RULES: Recupera y procesa los objetivos comerciales vigentes de volumen (kilos)
    para el período especificado, validando los preventistas contra CORE_VENDEDORES via repositorio.
    """
    t0 = time.perf_counter()
    df_obj_db = obtener_objetivos_vendedores(anio, mes)

    padron_vendedores = obtener_core_vendedores()
    if padron_vendedores.empty:
        raise ValueError(
            "CORE_VENDEDORES no retornó padrón activo para validar los objetivos comerciales."
        )

    codigos_validos = set(
        padron_vendedores["CodVendedor"].dropna().astype("Int64").tolist()
    )

    if df_obj_db is None or df_obj_db.empty:
        print(
            f"[PERF_CORE] 8) calcular_objetivos_comerciales_kilos (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame(
            columns=["CodVendedor", "SEGMENTO", "Objetivo Mes Corriente"]
        )

    df = df_obj_db.copy()
    col_cv = next(
        (c for c in ["CodVendedor", "Codigo_Vendedor", "CodVend"] if c in df.columns),
        None,
    )
    if not col_cv:
        raise ValueError(
            "No se encontró la columna de identificador de vendedor en los objetivos comerciales."
        )

    df["CodVendedor"] = pd.to_numeric(df[col_cv], errors="coerce").astype("Int64")

    col_seg = next((c for c in ["SEGMENTO", "Segmento"] if c in df.columns), None)
    if not col_seg:
        raise ValueError(
            "No se encontró la columna de segmento en los objetivos comerciales."
        )

    df["SEGMENTO"] = df[col_seg].fillna("").astype(str).str.strip()

    col_obj = next(
        (c for c in ["Obj_Sugerido_Kg", "Objetivo", "Obj"] if c in df.columns), None
    )
    if not col_obj:
        raise ValueError(
            "No se encontró la columna de valor objetivo en los objetivos comerciales."
        )

    df["Objetivo Mes Corriente"] = pd.to_numeric(df[col_obj], errors="coerce").fillna(
        0.0
    )

    # Validación defensiva contra CORE_VENDEDORES
    df = df[df["CodVendedor"].isin(codigos_validos)].copy()

    agrupado = df.groupby(["CodVendedor", "SEGMENTO"], as_index=False)[
        "Objetivo Mes Corriente"
    ].sum()
    resultado = agrupado[["CodVendedor", "SEGMENTO", "Objetivo Mes Corriente"]]
    print(
        f"[PERF_CORE] 8) calcular_objetivos_comerciales_kilos -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado


@st.cache_data(show_spinner=False)
def calcular_compensaciones_reemplazos(df_vta_operativa: pd.DataFrame) -> pd.DataFrame:
    """
    BUSINESS_RULES: Detecta operaciones realizadas por reemplazantes mediante la titularidad operativa
    y calcula los ajustes compensatorios de kilos (Arrastre, Actual y Total).
    """
    t0 = time.perf_counter()
    if df_vta_operativa is None or df_vta_operativa.empty:
        print(
            f"[PERF_CORE] 9) calcular_compensaciones_reemplazos (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame(
            columns=[
                "CodVendedor",
                "SEGMENTO",
                "Ajuste_Reemp_Arrastre",
                "Ajuste_Reemp_Actual",
                "Ajuste_Por_Reemp",
            ]
        )

    df = _asegurar_segmento_comercial(df_vta_operativa)

    for col_req in [
        "CodVendedor",
        "CodVendedorOperativo",
        "SEGMENTO",
        "Periodo",
        "PesoKg",
    ]:
        if col_req not in df.columns:
            raise ValueError(
                f"Falta la columna obligatoria '{col_req}' para calcular las compensaciones por reemplazo."
            )

    df["CodVendedor"] = pd.to_numeric(df["CodVendedor"], errors="coerce").astype(
        "Int64"
    )
    df["CodVendedorOperativo"] = pd.to_numeric(
        df["CodVendedorOperativo"], errors="coerce"
    ).astype("Int64")
    df["SEGMENTO"] = df["SEGMENTO"].fillna("").astype(str).str.strip()
    df["PesoKg"] = pd.to_numeric(df["PesoKg"], errors="coerce").fillna(0.0)

    # Identificación de transacciones con divergencia entre titular y operador
    reemplazos = df[
        df["CodVendedorOperativo"].ne(df["CodVendedor"])
        & df["Periodo"].isin(["Arrastre", "Actual"])
    ].copy()

    if reemplazos.empty:
        print(
            f"[PERF_CORE] 9) calcular_compensaciones_reemplazos (sin reemplazos) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame(
            columns=[
                "CodVendedor",
                "SEGMENTO",
                "Ajuste_Reemp_Arrastre",
                "Ajuste_Reemp_Actual",
                "Ajuste_Por_Reemp",
            ]
        )

    # Descuento al titular (salida de kilos)
    mov_titular = reemplazos[["CodVendedor", "SEGMENTO", "Periodo", "PesoKg"]].rename(
        columns={"CodVendedor": "CodVend"}
    )
    mov_titular["Ajuste_Valor"] = -mov_titular.pop("PesoKg")

    # Suma al reemplazante operativo (entrada de kilos)
    mov_reemp = reemplazos[
        ["CodVendedorOperativo", "SEGMENTO", "Periodo", "PesoKg"]
    ].rename(columns={"CodVendedorOperativo": "CodVend"})
    mov_reemp["Ajuste_Valor"] = mov_reemp.pop("PesoKg")

    ajustes_totales = pd.concat([mov_titular, mov_reemp], ignore_index=True)
    ajustes_totales["CodVend"] = pd.to_numeric(
        ajustes_totales["CodVend"], errors="coerce"
    ).astype("Int64")

    aj_arr = (
        ajustes_totales[ajustes_totales["Periodo"] == "Arrastre"]
        .groupby(["CodVend", "SEGMENTO"], as_index=False)["Ajuste_Valor"]
        .sum()
        .rename(
            columns={"Ajuste_Valor": "Ajuste_Reemp_Arrastre", "CodVend": "CodVendedor"}
        )
    )
    aj_act = (
        ajustes_totales[ajustes_totales["Periodo"] == "Actual"]
        .groupby(["CodVend", "SEGMENTO"], as_index=False)["Ajuste_Valor"]
        .sum()
        .rename(
            columns={"Ajuste_Valor": "Ajuste_Reemp_Actual", "CodVend": "CodVendedor"}
        )
    )

    consolidado = aj_arr.merge(
        aj_act, on=["CodVendedor", "SEGMENTO"], how="outer"
    ).fillna(0.0)
    consolidado["Ajuste_Por_Reemp"] = (
        consolidado["Ajuste_Reemp_Arrastre"] + consolidado["Ajuste_Reemp_Actual"]
    )

    resultado = consolidado[
        [
            "CodVendedor",
            "SEGMENTO",
            "Ajuste_Reemp_Arrastre",
            "Ajuste_Reemp_Actual",
            "Ajuste_Por_Reemp",
        ]
    ]
    print(
        f"[PERF_CORE] 9) calcular_compensaciones_reemplazos -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado


@st.cache_data(show_spinner=False)
def obtener_matriz_kilos_comercial(
    anio: int, mes: int, filtros_globales: dict
) -> pd.DataFrame:
    """
    BUSINESS_RULES (Orquestador Comercial): Consume exclusivamente servicios de la Capa CORE y el Repositorio,
    incorpora objetivos comerciales y compensaciones por reemplazo para construir la matriz final.
    """
    t0 = time.perf_counter()
    # 1. Consumo estricto de CORE_VENDEDORES
    padron_vend = obtener_core_vendedores()
    if padron_vend.empty:
        print(
            f"[PERF_CORE] 10) obtener_matriz_kilos_comercial (padrón vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    sup_map = padron_vend.set_index("CodVendedor")["SUP"].to_dict()

    # 2. Consumo estricto de CORE_OPERACIONES
    dia_matinal = (
        filtros_globales.get("dia_matinal", "02/09/2026")
        if filtros_globales
        else "02/09/2026"
    )
    dia_venta = (
        filtros_globales.get("dia_venta", "01/09/2026")
        if filtros_globales
        else "01/09/2026"
    )

    datos_operativos = obtener_core_operacion(
        anio, mes, dia_matinal, dia_venta, modo_ajuste="AJUSTADO"
    )
    df_vta_op = datos_operativos["df_vta_operativa"]
    dias_pasados_map = datos_operativos["dias_pasados_map"]
    dias_restantes_map = datos_operativos["dias_restantes_map"]

    if df_vta_op.empty:
        print(
            f"[PERF_CORE] 10) obtener_matriz_kilos_comercial (vta_op vacía) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    # Asegurar segmentación comercial sobre los datos operativos
    df_vta_op = _asegurar_segmento_comercial(df_vta_op)

    # Filtrado por período comercial operativo (Arrastre y Actual)
    df_periodo = df_vta_op[
        df_vta_op["Periodo"].isin(["Arrastre", "Actual"])
        & df_vta_op["SEGMENTO"].notna()
    ].copy()
    if df_periodo.empty:
        print(
            f"[PERF_CORE] 10) obtener_matriz_kilos_comercial (periodo vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    # Mapeo de titularidad operativa con soporte para comodines especiales (-998)
    codigos_validos = set(padron_vend["CodVendedor"].dropna().tolist())
    cod_op = df_periodo["CodVendedorOperativo"]
    cod_tit = df_periodo["CodVendedor"]
    reemp = df_periodo.get("Reemplazo", pd.Series(pd.NA, index=df_periodo.index))

    is_special = ((reemp == 99) | (cod_op == 99) | (cod_tit == 99)).fillna(False)
    valid_op_mask = cod_op.isin(codigos_validos).fillna(False)
    valid_tit_mask = cod_tit.isin(codigos_validos).fillna(False)

    df_periodo["CodVend_Op"] = np.select(
        [is_special, valid_op_mask, valid_tit_mask],
        [-998, cod_op.fillna(-999).astype(int), cod_tit.fillna(-999).astype(int)],
        default=cod_tit.fillna(-999).astype(int),
    )
    df_periodo["CodVend_Op"] = (
        pd.Series(df_periodo["CodVend_Op"]).replace(-999, pd.NA).astype("Int64")
    )
    df_periodo["SEGMENTO"] = df_periodo["SEGMENTO"].astype(str).str.strip()

    # Agregación volumétrica por operador y segmento
    kilos_agrup = (
        df_periodo.groupby(["CodVend_Op", "SEGMENTO", "Periodo"], dropna=False)[
            "PesoKg"
        ]
        .sum()
        .reset_index()
    )
    kilos_agrup = kilos_agrup.rename(columns={"CodVend_Op": "CodVendedor"})

    kilos_pivot = kilos_agrup.pivot_table(
        index=["CodVendedor", "SEGMENTO"],
        columns="Periodo",
        values="PesoKg",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()
    kilos_pivot.columns.name = None

    for p in ["Arrastre", "Actual"]:
        if p not in kilos_pivot.columns:
            kilos_pivot[p] = 0.0

    # Construcción de matriz base cruzando padrón y segmentos
    orden_segmentos = [
        "GOLD Salty",
        "GOLD Crakers",
        "SILVER Salty",
        "SILVER Crakers",
        "SILVER Cereals",
    ]
    segs_vta = df_periodo["SEGMENTO"].dropna().unique()
    for s in segs_vta:
        if s not in orden_segmentos:
            orden_segmentos.append(s)

    df_comodin = pd.DataFrame(
        {
            "CodVendedor": pd.Series([-998], dtype="Int64"),
            "Nombre": ["REEMPLAZO"],
            "SUP": ["GENERAL"],
        }
    )
    padron_full = pd.concat([padron_vend, df_comodin], ignore_index=True)

    padron_full["_k"] = 1
    segmentos_df = pd.DataFrame({"SEGMENTO": orden_segmentos})
    segmentos_df["_k"] = 1
    matriz_base = padron_full.merge(segmentos_df, on="_k").drop(columns="_k")

    # Integración de transacciones
    matriz_comercial = matriz_base.merge(
        kilos_pivot[["CodVendedor", "SEGMENTO", "Arrastre", "Actual"]],
        on=["CodVendedor", "SEGMENTO"],
        how="left",
    )
    matriz_comercial[["Arrastre", "Actual"]] = matriz_comercial[
        ["Arrastre", "Actual"]
    ].fillna(0.0)

    # Integración de Objetivos Comerciales (via Repositorio de Business Rules)
    df_objetivos = calcular_objetivos_comerciales_kilos(anio, mes)
    if not df_objetivos.empty:
        matriz_comercial = matriz_comercial.merge(
            df_objetivos, on=["CodVendedor", "SEGMENTO"], how="left"
        )
    matriz_comercial["Objetivo Mes Corriente"] = matriz_comercial.get(
        "Objetivo Mes Corriente", 0.0
    ).fillna(0.0)

    # Integración de Compensaciones por Reemplazo
    df_compensaciones = calcular_compensaciones_reemplazos(df_vta_op)
    if not df_compensaciones.empty:
        matriz_comercial = matriz_comercial.merge(
            df_compensaciones, on=["CodVendedor", "SEGMENTO"], how="left"
        )

    # Asignación defensiva segura evitando AttributeError en columnas ausentes
    for col_c in ["Ajuste_Reemp_Arrastre", "Ajuste_Reemp_Actual", "Ajuste_Por_Reemp"]:
        if col_c in matriz_comercial.columns:
            matriz_comercial[col_c] = matriz_comercial[col_c].fillna(0.0)
        else:
            matriz_comercial[col_c] = 0.0

    # Integración de Calendario y Rutas (CORE_OPERACIONES)
    matriz_comercial["Días Pasados"] = (
        matriz_comercial["CodVendedor"].map(dias_pasados_map).fillna(0).astype("Int64")
    )
    matriz_comercial["Rutas"] = (
        matriz_comercial["CodVendedor"]
        .map(dias_restantes_map)
        .fillna(0)
        .astype("Int64")
    )
    matriz_comercial["Días Restantes"] = matriz_comercial["Rutas"]

    # Cálculo del Neto Operativo
    matriz_comercial["OPERATIVO"] = (
        matriz_comercial["Arrastre"]
        + matriz_comercial["Actual"]
        + matriz_comercial["Ajuste_Por_Reemp"]
    )

    # Ordenamiento institucional por supervisor, preventista y segmento
    mapping_orden = {str(seg).strip(): i for i, seg in enumerate(orden_segmentos)}
    matriz_comercial["_orden_idx"] = (
        matriz_comercial["SEGMENTO"]
        .astype(str)
        .str.strip()
        .map(mapping_orden)
        .fillna(999)
    )
    matriz_comercial = (
        matriz_comercial.sort_values(by=["SUP", "Nombre", "_orden_idx"])
        .drop(columns=["_orden_idx"])
        .reset_index(drop=True)
    )

    columnas_salida = [
        "CodVendedor",
        "Nombre",
        "SUP",
        "SEGMENTO",
        "Objetivo Mes Corriente",
        "Arrastre",
        "Actual",
        "OPERATIVO",
        "Ajuste_Reemp_Arrastre",
        "Ajuste_Reemp_Actual",
        "Ajuste_Por_Reemp",
        "Días Pasados",
        "Rutas",
        "Días Restantes",
    ]

    resultado_final = matriz_comercial[
        [c for c in columnas_salida if c in matriz_comercial.columns]
    ]
    print(
        f"[PERF_CORE] 10) obtener_matriz_kilos_comercial -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado_final


====================================================================================================


### ARCHIVO: modules\business_rules\business_rules_repository.py

# modules/business_rules/business_rules_repository.py
import streamlit as st
import pandas as pd
from modules import database as db


@st.cache_data(show_spinner=False)
def obtener_objetivos_vendedores(anio: int, mes: int) -> pd.DataFrame:
    """
    BUSINESS_RULES REPOSITORY: Única entidad autorizada dentro de la capa BUSINESS_RULES
    para consultar la base de datos y extraer la entidad 'objetivos_vendedores' para un período dado.

    Garantiza manejo defensivo ante tablas vacías o inexistentes, retornando un DataFrame tipado.
    """
    try:
        query = f"SELECT CodVendedor, SEGMENTO, Obj_Sugerido_Kg FROM objetivos_vendedores WHERE Anio = {int(anio)} AND Mes = {int(mes)}"
        df = db.cargar_tabla_sql(query)
    except Exception:
        df = pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Obj_Sugerido_Kg"])

    df["CodVendedor"] = pd.to_numeric(
        df.get("CodVendedor", pd.Series(dtype="Int64")), errors="coerce"
    ).astype("Int64")
    df["SEGMENTO"] = (
        df.get("SEGMENTO", pd.Series(dtype="str")).fillna("").astype(str).str.strip()
    )
    df["Obj_Sugerido_Kg"] = pd.to_numeric(
        df.get("Obj_Sugerido_Kg", pd.Series(dtype="float")), errors="coerce"
    ).fillna(0.0)

    return df[["CodVendedor", "SEGMENTO", "Obj_Sugerido_Kg"]]


====================================================================================================


### ARCHIVO: modules\core\core_clientes.py

import streamlit as st
import pandas as pd

from modules.staging import obtener_staging_clientes


@st.cache_data(show_spinner=False)
def obtener_core_clientes():
    """
    CORE_CLIENTES

    Responsabilidades:
    - Consumir STAGING_CLIENTES
    - Excluir empleados
    - Validar taxonomías comerciales
    - Garantizar claves operativas válidas

    No aplica reglas CCC.
    No aplica reglas MN+.
    No aplica reglas TP.
    """

    df = obtener_staging_clientes().copy()

    if df.empty:
        return pd.DataFrame()

    # -------------------------------------------------
    # EXCLUSIÓN EMPLEADOS
    # -------------------------------------------------

    col_subsegmento = next(
        (c for c in df.columns if str(c).strip().lower() == "subsegmento"), None
    )

    if col_subsegmento:
        df = df[
            df[col_subsegmento].fillna("").astype(str).str.strip().str.casefold()
            != "empleados"
        ].copy()

    # -------------------------------------------------
    # TAXONOMÍAS VÁLIDAS
    # -------------------------------------------------

    if "Taxonomia" in df.columns:
        df["Taxonomia"] = df["Taxonomia"].fillna("").astype(str).str.strip().str.upper()

        df = df[df["Taxonomia"].isin(["A", "B", "C", "D"])].copy()

    # -------------------------------------------------
    # CLIENTE VÁLIDO
    # -------------------------------------------------

    if "Cliente" in df.columns:
        df = df[df["Cliente"].notna()].copy()

    # -------------------------------------------------
    # VENDEDOR VÁLIDO
    # -------------------------------------------------

    if "CodVendedor" in df.columns:
        df = df[df["CodVendedor"].notna()].copy()

    return df


====================================================================================================


### ARCHIVO: modules\core\core_operaciones.py

# modules/core/core_operaciones.py
import time
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from modules.staging import (
    obtener_staging_vta,
    obtener_staging_rutas,
    obtener_staging_ausencias,
    obtener_staging_maestros,
)
from modules.utils import parsear_fecha_robusta


@st.cache_data(show_spinner=False)
def procesar_ausencias_y_reemplazos(
    df_vta: pd.DataFrame, df_ausencias: pd.DataFrame
) -> pd.DataFrame:
    """
    Capa CORE: Procesa la tabla de ausencias y asigna la titularidad operativa (CodVendedorOperativo)
    cruzando las fechas de carga y entrega contra las inasistencias registradas.
    """
    t0 = time.perf_counter()
    if df_vta is None or df_vta.empty:
        print(
            f"[PERF_CORE] 4) procesar_ausencias_y_reemplazos (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    df = df_vta.copy()

    if "FechaCarga_dt" not in df.columns:
        df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    if "FechaEntrega_dt" not in df.columns:
        df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    if "CodVendedor" not in df.columns:
        col_vend_tit = next(
            (
                cand
                for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
                if cand in df.columns
            ),
            "CodVendedor",
        )
        df["CodVendedor"] = pd.to_numeric(
            df.get(col_vend_tit, 0), errors="coerce"
        ).astype("Int64")

    # PUNTO 4: Protección explícita ante fechas nulas (NaT) en generación de claves
    mask_carg = df["FechaCarga_dt"].notna()
    mask_ent = df["FechaEntrega_dt"].notna()

    df["ClaveAUS_Carga"] = pd.Series(pd.NA, dtype="string")
    df.loc[mask_carg, "ClaveAUS_Carga"] = (
        df.loc[mask_carg, "CodVendedor"].astype(str)
        + "-"
        + df.loc[mask_carg, "FechaCarga_dt"].dt.strftime("%Y-%m-%d")
    )

    df["ClaveAUS_Entrega"] = pd.Series(pd.NA, dtype="string")
    df.loc[mask_ent, "ClaveAUS_Entrega"] = (
        df.loc[mask_ent, "CodVendedor"].astype(str)
        + "-"
        + df.loc[mask_ent, "FechaEntrega_dt"].dt.strftime("%Y-%m-%d")
    )

    df_aus = (
        df_ausencias.copy()
        if df_ausencias is not None and not df_ausencias.empty
        else pd.DataFrame()
    )
    if not df_aus.empty:
        # PUNTO 2: Eliminación de heurísticas frágiles por índices posicionales
        cols_vend_cand = [
            "Ausente",
            "CodVend",
            "CodVendedor",
            "Vendedor",
            "Cod_Vendedor",
        ]
        col_aus_vend = next((c for c in cols_vend_cand if c in df_aus.columns), None)
        if not col_aus_vend:
            raise ValueError(
                "No se encontró columna de vendedor en la tabla de ausencias."
            )

        cols_f_cand = ["Fecha", "FechaAusencia", "Dia"]
        col_aus_fecha = next((c for c in cols_f_cand if c in df_aus.columns), None)
        if not col_aus_fecha:
            raise ValueError(
                "No se encontró columna de fecha en la tabla de ausencias."
            )

        cols_reemp_cand = [
            "Reemplazo",
            "CodReemplazo",
            "Cod_Reemplazo",
            "PreventistaReemplazo",
        ]
        col_aus_reemp = next((c for c in cols_reemp_cand if c in df_aus.columns), None)
        if not col_aus_reemp:
            raise ValueError(
                "No se encontró columna de reemplazo en la tabla de ausencias."
            )

        df_aus["Fecha_dt"] = parsear_fecha_robusta(df_aus[col_aus_fecha])
        df_aus["CodVend_clean"] = pd.to_numeric(
            df_aus[col_aus_vend], errors="coerce"
        ).astype("Int64")

        mask_aus_f = df_aus["Fecha_dt"].notna()
        df_aus["ClaveAUS"] = pd.Series(pd.NA, dtype="string")
        df_aus.loc[mask_aus_f, "ClaveAUS"] = (
            df_aus.loc[mask_aus_f, "CodVend_clean"].astype(str)
            + "-"
            + df_aus.loc[mask_aus_f, "Fecha_dt"].dt.strftime("%Y-%m-%d")
        )

        df_aus["Reemplazo_clean"] = pd.to_numeric(
            df_aus[col_aus_reemp], errors="coerce"
        ).astype("Int64")

        aus_map = (
            df_aus.dropna(subset=["ClaveAUS", "Reemplazo_clean"])
            .drop_duplicates("ClaveAUS")
            .set_index("ClaveAUS")["Reemplazo_clean"]
        )

        df["Reemplazo"] = (
            df["ClaveAUS_Carga"]
            .map(aus_map)
            .combine_first(df["ClaveAUS_Entrega"].map(aus_map))
        )
        df["CodVendedorOperativo"] = (
            df["Reemplazo"].combine_first(df["CodVendedor"]).astype("Int64")
        )
    else:
        df["Reemplazo"] = pd.NA
        df["CodVendedorOperativo"] = df["CodVendedor"]

    print(
        f"[PERF_CORE] 4) procesar_ausencias_y_reemplazos -> {time.perf_counter() - t0:.4f} s"
    )
    return df


@st.cache_data(show_spinner=False)
def calcular_calendario_y_rutas(
    df_rutas: pd.DataFrame,
    maestro_vendedores: pd.DataFrame,
    anio: int,
    mes: int,
    dia_venta: str,
    modo_ajuste: str = "AJUSTADO",
) -> tuple[dict, dict, int, int]:
    """
    Capa CORE: Calcula los días pasados, rutas totales y días restantes (totales y ajustados) por vendedor
    utilizando el maestro de vendedores y el calendario de rutas.
    """
    t0 = time.perf_counter()
    rutas = (
        df_rutas.copy()
        if df_rutas is not None and not df_rutas.empty
        else pd.DataFrame()
    )
    mv = (
        maestro_vendedores.copy()
        if maestro_vendedores is not None and not maestro_vendedores.empty
        else pd.DataFrame()
    )

    rutas_ajust_map = {}
    if not mv.empty:
        col_cod_v = next(
            (c for c in mv.columns if "cod" in str(c).strip().lower()), mv.columns[0]
        )
        col_rutas_ajust = next(
            (
                c
                for c in mv.columns
                if str(c).strip().lower()
                in ["rutas_ajustadas", "rutasajustadas", "ajustadas"]
            ),
            None,
        )
        if col_rutas_ajust:
            mv["CodClean"] = (
                pd.to_numeric(mv[col_cod_v], errors="coerce")
                .astype("Int64")
                .astype(str)
                .str.strip()
            )
            rutas_ajust_map = (
                mv.set_index("CodClean")[col_rutas_ajust]
                .fillna(0)
                .astype(int)
                .to_dict()
            )

    dias_pasados_map = {}
    dias_restantes_map = {}
    total_dias_pasados_val = 0
    total_dias_restantes_val = 0

    if not rutas.empty:
        # PUNTO 2: Validaciones explícitas de columnas en lugar de accesos posicionales
        cols_f_rutas = ["Fecha", "fecha", "Dia", "Date", "FECHA"]
        col_fecha_r = next((c for c in cols_f_rutas if c in rutas.columns), None)
        if not col_fecha_r:
            raise ValueError("No se encontró columna de fecha en la tabla de rutas.")

        cols_v_rutas = [
            "codven",
            "CodVen",
            "CodVendedor",
            "Vendedor",
            "Cod_Vendedor",
            "CODVEN",
        ]
        col_vend_r = next((c for c in cols_v_rutas if c in rutas.columns), None)
        if not col_vend_r:
            raise ValueError("No se encontró columna de vendedor en la tabla de rutas.")

        s_fechas = (
            rutas[col_fecha_r]
            .astype(str)
            .str.strip()
            .str.replace(" 00:00:00", "", regex=False)
        )
        dt_directo = pd.to_datetime(s_fechas, format="%Y-%m-%d", errors="coerce")
        dt_invertido = pd.to_datetime(s_fechas, format="%Y-%d-%m", errors="coerce")

        if (
            (dt_directo.dt.year == int(anio)) & (dt_directo.dt.month == int(mes))
        ).sum() >= (
            (dt_invertido.dt.year == int(anio)) & (dt_invertido.dt.month == int(mes))
        ).sum():
            rutas["Fecha_dt"] = dt_directo
        else:
            rutas["Fecha_dt"] = dt_invertido

        rutas["CodVend"] = pd.to_numeric(rutas[col_vend_r], errors="coerce").astype(
            "Int64"
        )
        rutas_mes = rutas[
            (
                (rutas["Fecha_dt"].dt.year == int(anio))
                & (rutas["Fecha_dt"].dt.month == int(mes))
            )
        ].copy()

        dia_v_dt = parsear_fecha_robusta(pd.Series([dia_venta])).iloc[0]
        corte_date = dia_v_dt.date() if pd.notna(dia_v_dt) else None

        pasadas = (
            rutas_mes[rutas_mes["Fecha_dt"].dt.date <= corte_date]
            if corte_date is not None
            else rutas_mes
        )
        restantes_base = (
            rutas_mes[rutas_mes["Fecha_dt"].dt.date > corte_date]
            if corte_date is not None
            else rutas_mes
        )

        dias_pasados_map = pasadas.groupby("CodVend")["Fecha_dt"].nunique().to_dict()
        dias_restantes_base_map = (
            restantes_base.groupby("CodVend")["Fecha_dt"].nunique().to_dict()
        )

        for cv, dr_b in dias_restantes_base_map.items():
            cv_clean_str = str(int(cv)) if pd.notna(cv) else ""
            desc = rutas_ajust_map.get(cv_clean_str, 0) if cv_clean_str else 0
            if modo_ajuste == "AJUSTADO":
                dias_restantes_map[cv] = max(0, dr_b - desc)
            else:
                dias_restantes_map[cv] = dr_b

        total_dias_pasados_val = int(pasadas["Fecha_dt"].nunique())
        if dias_restantes_map:
            total_dias_restantes_val = int(
                pd.Series(list(dias_restantes_map.values())).mean()
            )
        else:
            total_dias_restantes_val = int(restantes_base["Fecha_dt"].nunique())

    print(
        f"[PERF_CORE] 6) calcular_calendario_y_rutas -> {time.perf_counter() - t0:.4f} s"
    )
    return (
        dias_pasados_map,
        dias_restantes_map,
        total_dias_pasados_val,
        total_dias_restantes_val,
    )


@st.cache_data(show_spinner=False)
def calcular_ritmo_operativo(
    df_vta: pd.DataFrame, anio_op: int, mes_op: int, dia_matinal: str
) -> pd.DataFrame:
    """
    Capa CORE (Clasificador de Períodos Operativos):
    Aplica el filtro corporativo de fecha matinal y clasifica las transacciones
    en períodos comerciales institucionales (Arrastre, Actual, Futuro).
    No calcula KPIs, proyecciones ni ritmos (responsabilidad de Business Rules / Reportes).
    """
    t0 = time.perf_counter()
    if df_vta is None or df_vta.empty:
        print(
            f"[PERF_CORE] 5) calcular_ritmo_operativo (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    df = df_vta.copy()

    if "FechaCarga_dt" not in df.columns:
        df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    if "FechaEntrega_dt" not in df.columns:
        df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    dia_matinal_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(dia_matinal_dt):
        es_mes_en_curso = dia_matinal_dt.year == anio_op and dia_matinal_dt.month in [
            mes_op,
            mes_op + 1,
        ]
        if es_mes_en_curso:
            df = df[df["FechaCarga_dt"].dt.date < dia_matinal_dt.date()]

    df["MesCarga"] = df["FechaCarga_dt"].dt.month
    df["AñoCarga"] = df["FechaCarga_dt"].dt.year
    df["MesEntrega"] = df["FechaEntrega_dt"].dt.month
    df["AñoEntrega"] = df["FechaEntrega_dt"].dt.year

    mes_ant = 12 if mes_op == 1 else mes_op - 1
    anio_ant = anio_op - 1 if mes_op == 1 else anio_op

    mes_sig = 1 if mes_op == 12 else mes_op + 1
    anio_sig = anio_op + 1 if mes_op == 12 else anio_op

    ac, mc = df["AñoCarga"], df["MesCarga"]
    ae, me = df["AñoEntrega"], df["MesEntrega"]

    cond_arr = (
        (ac == anio_ant) & (mc == mes_ant) & (ae == anio_op) & (me == mes_op)
    ).fillna(False)
    cond_act = (
        (ac == anio_op) & (mc == mes_op) & (ae == anio_op) & (me == mes_op)
    ).fillna(False)
    cond_fut = (
        (ac == anio_op) & (mc == mes_op) & (ae == anio_sig) & (me == mes_sig)
    ).fillna(False)

    df["Periodo"] = np.select(
        [cond_arr, cond_act, cond_fut],
        ["Arrastre", "Actual", "Futuro"],
        default="Fuera de Periodo",
    )

    print(
        f"[PERF_CORE] 5) calcular_ritmo_operativo -> {time.perf_counter() - t0:.4f} s"
    )
    return df


@st.cache_data(show_spinner=False)
def obtener_core_operacion(
    anio_op: int,
    mes_op: int,
    dia_matinal: str,
    dia_venta: str,
    modo_ajuste: str = "AJUSTADO",
) -> dict:
    """
    Capa CORE (Función Orquestadora Pública): Retorna un diccionario consolidado con todas las métricas
    y asignaciones operativas procesadas por CORE_OPERACION.
    """
    t0 = time.perf_counter()
    df_vta = obtener_staging_vta()
    df_rutas = obtener_staging_rutas()
    df_ausencias = obtener_staging_ausencias()
    maestros = obtener_staging_maestros()

    df_vendedores = (
        maestros.get("maestro_vendedores", pd.DataFrame())
        if isinstance(maestros, dict)
        else pd.DataFrame()
    )

    df_vta_procesada = procesar_ausencias_y_reemplazos(df_vta, df_ausencias)
    df_vta_temporal = calcular_ritmo_operativo(
        df_vta_procesada, anio_op, mes_op, dia_matinal
    )
    dias_pasados, dias_restantes, tot_pasados, tot_restantes = (
        calcular_calendario_y_rutas(
            df_rutas, df_vendedores, anio_op, mes_op, dia_venta, modo_ajuste
        )
    )

    print(f"[PERF_CORE] 7) obtener_core_operacion -> {time.perf_counter() - t0:.4f} s")
    return {
        "df_vta_operativa": df_vta_temporal,
        "dias_pasados_map": dias_pasados,
        "dias_restantes_map": dias_restantes,
        "total_dias_pasados": tot_pasados,
        "total_dias_restantes": tot_restantes,
    }


====================================================================================================


### ARCHIVO: modules\core\core_vendedores.py

import streamlit as st
import pandas as pd

from modules import database as db


@st.cache_data(show_spinner=False)
def obtener_core_vendedores():
    """
    CORE_VENDEDORES V1

    Responsabilidades:
    - Cargar maestro_vendedores
    - Normalizar CodVendedor
    - Mantener Nombre
    - Mantener SUP
    - Excluir vendedor 20
    - Eliminar duplicados
    """

    try:
        df = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    col_cod = next(
        (
            c
            for c in ["Codigo_Vendedor", "CodVend", "CodVendedor", "Cod_Vendedor"]
            if c in df.columns
        ),
        None,
    )

    if col_cod is None:
        return pd.DataFrame()

    core = pd.DataFrame()

    core["CodVendedor"] = pd.to_numeric(df[col_cod], errors="coerce").astype("Int64")

    col_nombre = next(
        (c for c in ["Nombre_Vendedor", "Nombre", "Vendedor"] if c in df.columns), None
    )

    if col_nombre:
        core["Nombre"] = df[col_nombre].fillna("").astype(str).str.strip()
    else:
        core["Nombre"] = ""

    col_sup = next((c for c in ["Supervisor", "SUP"] if c in df.columns), None)

    if col_sup:
        core["SUP"] = df[col_sup].fillna("").astype(str).str.strip()
    else:
        core["SUP"] = ""

    core = core[core["CodVendedor"].notna()].copy()

    core = core[core["CodVendedor"] != 20].copy()

    core = core.drop_duplicates(subset=["CodVendedor"])

    core = core.sort_values("CodVendedor").reset_index(drop=True)

    return core


====================================================================================================


### ARCHIVO: modules\core\core_ventas_base.py

# modules/core/core_ventas_base.py

import streamlit as st
import pandas as pd

from modules.staging import obtener_staging_vta
from modules.utils import parsear_fecha_robusta


@st.cache_data(show_spinner=False)
def obtener_core_ventas_base():
    """
    CORE_VENTAS_BASE V1

    Responsabilidades:
    - Consumir STAGING_VTA
    - Tipar identificadores
    - Parsear fechas
    - Normalizar métricas básicas

    No aplica:
    - PepsiCo
    - Comodatos
    - CCC
    - Reemplazos
    - Vendedor 20
    - Empleados
    """

    df = obtener_staging_vta().copy()

    if df.empty:
        return pd.DataFrame()

    # -----------------------------
    # CLIENTE
    # -----------------------------

    col_cliente = next(
        (
            c
            for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
            if c in df.columns
        ),
        None,
    )

    if col_cliente:
        df["Cliente"] = pd.to_numeric(df[col_cliente], errors="coerce").astype("Int64")

    # -----------------------------
    # VENDEDOR
    # -----------------------------

    col_vendedor = next(
        (
            c
            for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
            if c in df.columns
        ),
        None,
    )

    if col_vendedor:
        df["CodVendedor"] = pd.to_numeric(df[col_vendedor], errors="coerce").astype(
            "Int64"
        )

    # -----------------------------
    # CANTBASE
    # -----------------------------

    col_cant = next(
        (
            c
            for c in [
                "CantBase",
                "CANTBASE",
                "Cantidad",
                "CANTIDAD",
                "Unidades",
                "UNIDADES",
            ]
            if c in df.columns
        ),
        None,
    )

    if col_cant:
        df["CantBase"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0)

    # -----------------------------
    # IMPORTE
    # -----------------------------

    col_importe = next(
        (
            c
            for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"]
            if c in df.columns
        ),
        None,
    )

    if col_importe:
        df["ImporteNeto"] = pd.to_numeric(df[col_importe], errors="coerce").fillna(0)

    # -----------------------------
    # PESOKG
    # -----------------------------

    if "PesoKg" in df.columns:
        df["PesoKg"] = pd.to_numeric(df["PesoKg"], errors="coerce").fillna(0)

    # -----------------------------
    # FECHAS
    # -----------------------------

    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))

    df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    if "FechaLiquidacion" in df.columns:
        df["FechaLiquidacion_dt"] = parsear_fecha_robusta(df.get("FechaLiquidacion"))

    return df


====================================================================================================


### ARCHIVO: modules\database.py

# modules/database.py
import sqlite3
import pandas as pd
import os
from modules.logger import get_logger

# Inicialización del logger institucional para la capa de acceso a datos
logger = get_logger("database")

DB_PATH = "data/matinal.db"

def obtener_conexion():
    """Crea una conexión a SQLite con timeout y modo WAL activado para concurrencia segura."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    """Inicializa la estructura básica y asegura índices de rendimiento."""
    conn = obtener_conexion()
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vta_vendedor ON vta(CodVendedor);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vta_cliente ON vta(Cliente);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vta_fechacarga ON vta(FechaCarga);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vta_fechaentrega ON vta(FechaEntrega);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vta_marca ON vta(Marca);")
        conn.commit()
        logger.info("Índices de rendimiento de la tabla vta verificados/creados correctamente en SQLite.")
    except Exception:
        logger.exception("Error crítico al intentar crear los índices de rendimiento para la tabla vta.")
    finally:
        conn.close()

def cargar_tabla_sql(query: str) -> pd.DataFrame:
    """Ejecuta una consulta SQL de forma segura. Si la tabla no existe, retorna un DataFrame vacío."""
    conn = obtener_conexion()
    try:
        q_lower = query.lower()
        if "from" in q_lower:
            partes = q_lower.split("from")[1].strip().split()
            if partes:
                nombre_tabla = partes[0].strip(";")
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name) = ?", (nombre_tabla,))
                if not cursor.fetchone():
                    logger.warning(f"La tabla consultada no existe en el catálogo de SQLite. Retornando DataFrame vacío para: {query}")
                    return pd.DataFrame()
        
        df = pd.read_sql(query, conn)
    except Exception:
        logger.exception(f"Error al ejecutar la consulta SQL: {query}. Retornando DataFrame vacío por seguridad.")
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

def guardar_dataframe_sql(df: pd.DataFrame, nombre_tabla: str, if_exists='replace'):
    """Guarda un DataFrame en la base de datos SQLite."""
    conn = obtener_conexion()
    try:
        df.to_sql(nombre_tabla, conn, if_exists=if_exists, index=False, chunksize=10000)
        logger.info(f"DataFrame persistido con éxito en la tabla '{nombre_tabla}' (modo: {if_exists}).")
    finally:
        conn.close()

def tablas_existen() -> bool:
    """Verifica de forma robusta si las tablas operativas existen y contienen registros."""
    conn = obtener_conexion()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT LOWER(name) FROM sqlite_master WHERE type='table' AND LOWER(name) IN ('vta', 'universo', 'rutas', 'altas');")
        tablas = [row[0] for row in cursor.fetchall()]
        
        if len(set(tablas)) < 3:
            logger.warning("Validación estructural: Faltan tablas operativas esenciales en SQLite.")
            return False
            
        for tabla in ['vta', 'universo', 'rutas']:
            cursor.execute(f"SELECT COUNT(*) FROM {tabla};")
            count = cursor.fetchone()[0]
            if count == 0:
                logger.warning(f"Validación estructural: La tabla operativa '{tabla}' se encuentra vacía.")
                return False
                
        return True
    except Exception:
        logger.exception("Error crítico al verificar la existencia y conteo de registros en las tablas operativas de SQLite.")
        return False
    finally:
        conn.close()

def obtener_df_maestro_corporativo() -> pd.DataFrame:
    """
    DataFrame Maestro de Nivel 1 (Filtro N1: EMPLEADOS).
    - Carga la tabla 'vta' de SQLite.
    - Aplica de forma universal el filtro N1 EMPLEADOS (elimina subramos 'EMPLOYEES' / 'EMPLEADOS').
    - Opera como la Única Fuente de Verdad (SSOT) para la derivación de DataFrames hijos en los reportes.
    """
    df = cargar_tabla_sql("SELECT * FROM vta")
    if df.empty:
        return df

    if "Subramo" in df.columns:
        subramo_clean = df["Subramo"].fillna("").astype(str).str.strip().str.upper()
        df = df[~subramo_clean.isin(["EMPLOYEES", "EMPLEADOS"])]

    col_vend_tit = next((cand for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"] if cand in df.columns), "CodVendedor")
    if col_vend_tit in df.columns:
        df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype("Int64")

    return df

def inicializar_bd_desde_excel(archivos_dict):
    """Lee los archivos Excel interpretando fechas y estructurando tablas con soporte multi-solapa para Altas."""
    conn = obtener_conexion()
    try:
        for nombre_tabla, archivo in archivos_dict.items():
            logger.warning(f"CARGANDO TABLA: {nombre_tabla}")
            if "altas" in nombre_tabla.lower():
                xls_altas = pd.ExcelFile(archivo)
                dfs_all = []
                for sheet in xls_altas.sheet_names:
                    df_sheet = pd.read_excel(archivo, sheet_name=sheet)
                    
                    for col in df_sheet.columns:
                        col_l = str(col).strip().lower()
                        if any(k in col_l for k in ["fecha", "dia", "date"]):
                            s = df_sheet[col].astype(str).str.strip().str.replace(" 00:00:00", "", regex=False)
                            dt = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
                            mask_na = dt.isna()
                            if mask_na.any():
                                dt.loc[mask_na] = pd.to_datetime(s[mask_na], format="%d-%m-%Y", errors="coerce")
                            mask_na = dt.isna()
                            if mask_na.any():
                                dt.loc[mask_na] = pd.to_datetime(s[mask_na], format="%Y-%m-%d", errors="coerce")
                            mask_na = dt.isna()
                            if mask_na.any():
                                dt.loc[mask_na] = pd.to_datetime(s[mask_na], errors="coerce")
                            df_sheet[col] = dt.dt.strftime("%Y-%m-%d")

                    nombre_tabla_sheet = f"altas_{sheet.lower()}"
                    df_sheet.to_sql(nombre_tabla_sheet, conn, if_exists='replace', index=False, chunksize=10000)

                    df_s_copy = df_sheet.copy()
                    df_s_copy["Origen_Hoja"] = sheet
                    dfs_all.append(df_s_copy)
                
                if dfs_all:
                    df_altas_unificado = pd.concat(dfs_all, ignore_index=True)
                    df_altas_unificado.to_sql("altas", conn, if_exists='replace', index=False, chunksize=10000)
            elif nombre_tabla.lower() == "tp":
                logger.warning(f"DETECTADA CARGA ESPECIAL TP: {nombre_tabla}")
                df_raw = pd.read_excel(archivo, header=None)
                header_row = None
                for i, row in df_raw.iterrows():
                    if "Cliente_id" in row.astype(str).values:
                        header_row = i
                        break
                if header_row is None:
                    raise ValueError("No se encontró Cliente_id en TP.xlsx")
                df = pd.read_excel(archivo, header=header_row)
                df.columns = [str(c).strip() for c in df.columns]
            else:
                df = pd.read_excel(archivo)
            
            if any(k in nombre_tabla.lower() for k in ["vendedor", "vendedores", "maestro_vendedores"]):
                col_ajuste_cand = next((c for c in df.columns if any(k in str(c).strip().lower() for k in ["ajuste", "entrega", "lag", "dias_entrega"])), None)
                if col_ajuste_cand:
                    df["Ajuste_Entrega"] = pd.to_numeric(df[col_ajuste_cand], errors="coerce").fillna(1).astype(int)
                else:
                    df["Ajuste_Entrega"] = 1

                col_rutas_ajust = next((c for c in df.columns if any(k in str(c).strip().lower() for k in ["rutas_ajustadas", "rutasajustadas", "ajustadas"])), None)
                if col_rutas_ajust:
                    df["Rutas_Ajustadas"] = pd.to_numeric(df[col_rutas_ajust], errors="coerce").fillna(0).astype(int)
                else:
                    df["Rutas_Ajustadas"] = 0

            if nombre_tabla.lower() in ["maestro_marcas_cebe", "marcas_cebe", "cebes"]:
                for col in df.columns:
                    col_l = str(col).strip().lower()
                    if col_l in ["obj_mes", "objetivo", "obj", "suma de tn", "tn"]:
                        df = df.rename(columns={col: "Obj_Mes"})
                if "Obj_Mes" in df.columns:
                    df["Obj_Mes"] = pd.to_numeric(df["Obj_Mes"], errors="coerce").fillna(0.0)

            if "altas" not in nombre_tabla.lower():
                for col in df.columns:
                    col_l = str(col).strip().lower()
                    if any(k in col_l for k in ["fecha", "dia", "date"]):
                        s = df[col].astype(str).str.strip().str.replace(" 00:00:00", "", regex=False)
                        dt = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
                        mask_na = dt.isna()
                        if mask_na.any():
                            dt.loc[mask_na] = pd.to_datetime(s[mask_na], format="%d-%m-%Y", errors="coerce")
                        mask_na = dt.isna()
                        if mask_na.any():
                            dt.loc[mask_na] = pd.to_datetime(s[mask_na], format="%Y-%m-%d", errors="coerce")
                        mask_na = dt.isna()
                        if mask_na.any():
                            dt.loc[mask_na] = pd.to_datetime(s[mask_na], errors="coerce")
                        df[col] = dt.dt.strftime("%Y-%m-%d")
                        
                df.to_sql(nombre_tabla, conn, if_exists='replace', index=False, chunksize=10000)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_vta_vendedor ON vta(CodVendedor);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vta_cliente ON vta(Cliente);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vta_fechacarga ON vta(FechaCarga);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vta_fechaentrega ON vta(FechaEntrega);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vta_marca ON vta(Marca);")
        conn.commit()
    finally:
        conn.close()

def importar_maestros_multisolapa_atomica(archivo_buffer_or_path, anio_def, mes_def) -> tuple[bool, str]:
    """Importa masivamente todas las solapas del Excel consolidado en una transacción atómica única."""
    try:
        xls_global = pd.ExcelFile(archivo_buffer_or_path)
    except Exception as e:
        return False, f"Error al leer el archivo Excel: {e}"

    sheet_to_table = {
        'Maestro_Vendedores': 'maestro_vendedores',
        'Maestro_Segmentos': 'maestro_segmentos',
        'Maestro_Marcas_CEBE': 'maestro_marcas_cebe',
        'Maestro_CCC_Config': 'maestro_ccc',
        'Maestro_Innovaciones': 'maestro_innovaciones',
        'Objetivos_Calibrados': 'objetivos_vendedores'
    }

    conn = obtener_conexion()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION;")
        
        importados_count = 0
        for sheet_name, table_name in sheet_to_table.items():
            if sheet_name in xls_global.sheet_names:
                df_sheet = pd.read_excel(archivo_buffer_or_path, sheet_name=sheet_name)
                if not df_sheet.empty:
                    if 'Anio' in df_sheet.columns:
                        df_sheet['Anio'] = pd.to_numeric(df_sheet['Anio'], errors='coerce').fillna(int(anio_def)).astype(int)
                    if 'Mes' in df_sheet.columns:
                        df_sheet['Mes'] = pd.to_numeric(df_sheet['Mes'], errors='coerce').fillna(int(mes_def)).astype(int)
                    
                    df_sheet.to_sql(table_name, conn, if_exists='replace', index=False, chunksize=5000)
                    importados_count += 1

        conn.commit()
        return True, f"¡Se han importado y actualizado exitosamente {importados_count} tablas en SQLite de forma atómica e instantánea!"
    except Exception as e:
        conn.rollback()
        return False, f"Error crítico en la transacción SQL: {e}"
    finally:
        conn.close()

def guardar_objetivos_calibrados_desde_excel(file_buffer_or_path, anio, mes):
    """Guarda o reemplaza los objetivos definitivos en 'objetivos_vendedores' para el período (Anio, Mes)."""
    try:
        df_subida = pd.read_excel(file_buffer_or_path)
    except Exception as e:
        return False, f"Error al leer el archivo Excel: {e}"

    columnas_requeridas = ["CodVendedor", "SEGMENTO", "Obj_Sugerido_Kg"]
    faltantes = [c for c in columnas_requeridas if c not in df_subida.columns]
    if faltantes:
        return False, f"El archivo Excel no tiene el formato correcto. Faltan las columnas: {', '.join(faltantes)}"

    df_subida["CodVendedor"] = pd.to_numeric(df_subida["CodVendedor"], errors="coerce").astype("Int64")
    if "Nombre" in df_subida.columns:
        df_subida["Nombre"] = df_subida["Nombre"].fillna("").astype(str).str.strip()
    if "Supervisor" in df_subida.columns:
        df_subida["Supervisor"] = df_subida["Supervisor"].fillna("").astype(str).str.strip()
    df_subida["SEGMENTO"] = df_subida["SEGMENTO"].fillna("").astype(str).str.strip()
    df_subida["Obj_Sugerido_Kg"] = pd.to_numeric(df_subida["Obj_Sugerido_Kg"], errors="coerce").fillna(0.0)

    try:
        anio_int = int(float(str(anio)))
    except Exception:
        anio_int = 2026

    try:
        mes_int = int(float(str(mes)))
    except Exception:
        mes_int = 9

    df_subida["Anio"] = anio_int
    df_subida["Mes"] = mes_int

    conn = obtener_conexion()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS objetivos_vendedores (
                Anio INTEGER,
                Mes INTEGER,
                CodVendedor INTEGER,
                Nombre TEXT,
                Supervisor TEXT,
                SEGMENTO TEXT,
                Kilos_Mes_Anterior REAL,
                Objetivo_Mes_Anterior_Kg REAL,
                Logro_Anterior_Pct REAL,
                Obj_Sugerido_Kg REAL,
                PRIMARY KEY (Anio, Mes, CodVendedor, SEGMENTO)
            )
        """)
        conn.commit()

        cursor.execute("DELETE FROM objetivos_vendedores WHERE Anio = ? AND Mes = ?", (anio_int, mes_int))
        conn.commit()

        df_subida.to_sql("objetivos_vendedores", conn, if_exists="append", index=False, chunksize=10000)
    finally:
        conn.close()

    return True, f"¡Objetivos del período {mes_int:02d}/{anio_int} cargados y versionados con éxito en la base de datos!"

def guardar_innovaciones_desde_excel(file_buffer_or_path, anio, mes):
    """Guarda o reemplaza el maestro de innovaciones en la tabla 'maestro_innovaciones' para el período (Anio, Mes)."""
    try:
        df_subida = pd.read_excel(file_buffer_or_path)
    except Exception as e:
        return False, f"Error al leer el archivo Excel de innovaciones: {e}"

    columnas_requeridas = ["Codigo", "Articulo", "Innovacion", "Condicion_Vta"]
    faltantes = [c for c in columnas_requeridas if c not in df_subida.columns]
    if faltantes:
        return False, f"El archivo Excel no tiene el formato correcto. Faltan las columnas: {', '.join(faltantes)}"

    try:
        anio_int = int(float(str(anio)))
    except Exception:
        anio_int = 2026

    try:
        mes_int = int(float(str(mes)))
    except Exception:
        mes_int = 9

    df_subida["Anio"] = anio_int
    df_subida["Mes"] = mes_int
    df_subida["Codigo"] = pd.to_numeric(df_subida["Codigo"], errors="coerce").astype("Int64")
    df_subida["Articulo"] = df_subida["Articulo"].fillna("").astype(str).str.strip()
    df_subida["Innovacion"] = df_subida["Innovacion"].fillna("").astype(str).str.strip().str.upper()
    df_subida["Condicion_Vta"] = pd.to_numeric(df_subida["Condicion_Vta"], errors="coerce").astype("Int64")

    conn = obtener_conexion()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS objetivos_vendedores (
                Anio INTEGER,
                Mes INTEGER,
                CodVendedor INTEGER,
                Nombre TEXT,
                Supervisor TEXT,
                SEGMENTO TEXT,
                Kilos_Mes_Anterior REAL,
                Objetivo_Mes_Anterior_Kg REAL,
                Logro_Anterior_Pct REAL,
                Obj_Sugerido_Kg REAL,
                PRIMARY KEY (Anio, Mes, CodVendedor, SEGMENTO)
            )
        """)
        conn.commit()

        cursor.execute("DELETE FROM objetivos_vendedores WHERE Anio = ? AND Mes = ?", (anio_int, mes_int))
        conn.commit()

        df_subida.to_sql("objetivos_vendedores", conn, if_exists="append", index=False, chunksize=10000)
    finally:
        conn.close()

    return True, f"¡Objetivos del período {mes_int:02d}/{anio_int} cargados y versionados con éxito en la base de datos!"

====================================================================================================


### ARCHIVO: modules\logger.py

# modules/logger.py
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Directorio de logs centralizado en la raíz del proyecto
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "matinal.log"

# Configuración global base (Nivel INFO por defecto para producción)
DEFAULT_LOG_LEVEL = logging.INFO
MAX_BYTES = 5 * 1024 * 1024  # 5 MB por archivo de log
BACKUP_COUNT = 5             # Conserva hasta 5 respaldos históricos rotados

def setup_root_logger():
    """Configura y retorna el logger raíz de MATINAL con soporte de rotación y consola."""
    root_logger = logging.getLogger("matinal")
    if root_logger.handlers:
        return root_logger

    root_logger.setLevel(DEFAULT_LOG_LEVEL)

    # Formato estructurado estricto: Timestamp | Nivel | Módulo | Mensaje
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Handler para archivo con rotación automática (evita saturación de disco)
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=MAX_BYTES, 
        backupCount=BACKUP_COUNT, 
        encoding="utf-8"
    )
    file_handler.setLevel(DEFAULT_LOG_LEVEL)
    file_handler.setFormatter(formatter)

    # 2. Handler para salida estándar en consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(DEFAULT_LOG_LEVEL)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    root_logger.info("=== SUBSISTEMA DE LOGGING MATINAL INICIALIZADO CORRECTAMENTE ===")
    return root_logger

def get_logger(module_name: str) -> logging.Logger:
    """
    Retorna un logger hijo bajo la jerarquía 'matinal.<module_name>' 
    respetando la convención de nombres por módulo del proyecto.
    Ejemplo:
        logger = get_logger("database")
    """
    setup_root_logger()
    return logging.getLogger(f"matinal.{module_name}")

def set_debug_mode(enabled: bool = True):
    """
    Permite habilitar dinámicamente el nivel DEBUG para diagnósticos temporales.
    Deshabilitado por defecto en producción.
    """
    root_logger = logging.getLogger("matinal")
    new_level = logging.DEBUG if enabled else DEFAULT_LOG_LEVEL
    root_logger.setLevel(new_level)
    for handler in root_logger.handlers:
        handler.setLevel(new_level)
    
    if enabled:
        root_logger.debug("--- MODO DEBUG ACTIVADO TEMPORALMENTE ---")
    else:
        root_logger.info("--- MODO DEBUG DESACTIVADO (Nivel producción restablecido) ---")

====================================================================================================


### ARCHIVO: modules\parametros.py

# modules/parametros.py
import streamlit as st
import pandas as pd
from modules import database as db
from io import BytesIO

def es_entorno_local() -> bool:
    """Valida si la app se ejecuta en entorno local basándose en los secretos."""
    try:
        return st.secrets.get("ENVIRONMENT", "production") == "local"
    except Exception:
        return False

def obtener_tabla_parametros() -> pd.DataFrame:
    """Obtiene los parámetros desde SQLite. Si la tabla no existe, crea valores por defecto."""
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name='parametros'"
    res = db.cargar_tabla_sql(query)
    
    if res is None or res.empty:
        df_default = pd.DataFrame({
            "PARAMETRO": ["Año", "Mes", "Dia Matinal", "Dia Venta", "Dia Anterior"],
            "VALOR": ["2026", "9", "02/09/2026", "01/09/2026", "31/08/2026"]
        })
        db.guardar_dataframe_sql(df_default, "parametros", if_exists='replace')
        return df_default
    
    return db.cargar_tabla_sql("SELECT * FROM parametros")

def obtener_maestro_vendedores_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga el maestro de vendedores desde SQLite asegurando la columna Rutas_Ajustadas."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        if df_all is None or df_all.empty:
            return pd.DataFrame(columns=["Anio", "Mes", "Codigo_Vendedor", "Nombre_Vendedor", "Supervisor", "Rutas_Ajustadas"])
        
        if "Rutas_Ajustadas" not in df_all.columns:
            df_all["Rutas_Ajustadas"] = 0

        if not mes or str(mes).strip() == "":
            return df_all
        
        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = (df_all["Mes"].astype(str) == str(mes))
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]
            
        return df_all
    except Exception:
        return pd.DataFrame(columns=["Anio", "Mes", "Codigo_Vendedor", "Nombre_Vendedor", "Supervisor", "Rutas_Ajustadas"])

def obtener_maestro_segmentos_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga el maestro de segmentos desde SQLite. Si mes está vacío, devuelve la base completa."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos")
        if df_all is None or df_all.empty:
            return pd.DataFrame(columns=["Anio", "Mes", "Segmento"])
        
        if not mes or str(mes).strip() == "":
            return df_all
        
        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = (df_all["Mes"].astype(str) == str(mes))
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]
            
        return df_all
    except Exception:
        return pd.DataFrame(columns=["Anio", "Mes", "Segmento"])

def obtener_maestro_marcas_cebe_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga la relación Marca - CEBE y objetivos desde SQLite. Si mes está vacío, devuelve la base completa."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if df_all is None or df_all.empty:
            return pd.DataFrame(columns=["Anio", "Mes", "Marca", "CEBE", "Obj_TN_Mes", "Obj_Gross_Mes", "Obj_Pepsico_Cobertura", "Obj_Empresa_Cobertura"])
        
        for col_nec in ["Obj_TN_Mes", "Obj_Gross_Mes", "Obj_Pepsico_Cobertura", "Obj_Empresa_Cobertura"]:
            if col_nec not in df_all.columns:
                df_all[col_nec] = 0.0

        if not mes or str(mes).strip() == "":
            return df_all
        
        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = (df_all["Mes"].astype(str) == str(mes))
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]
            
        return df_all
    except Exception:
        return pd.DataFrame(columns=["Anio", "Mes", "Marca", "CEBE", "Obj_TN_Mes", "Obj_Gross_Mes", "Obj_Pepsico_Cobertura", "Obj_Empresa_Cobertura"])

def obtener_maestro_ccc_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga los porcentajes y objetivos de clientes CCC por taxonomía desde SQLite aplicando versionado estricto."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
        if df_all is None or df_all.empty:
            df_default = pd.DataFrame({
                "Anio": [int(anio) if anio else 2026]*4,
                "Mes": [int(mes) if mes else 9]*4,
                "Taxonomia": ["A", "B", "C", "D"],
                "Porcentaje_Cartera": [80.0, 70.0, 60.0, 50.0],
                "Obj_CCC_Pepsico": [0.0, 0.0, 0.0, 0.0]
            })
            db.guardar_dataframe_sql(df_default, "maestro_ccc", if_exists='append')
            return df_default
        
        if "Obj_CCC_Pepsico" not in df_all.columns:
            df_all["Obj_CCC_Pepsico"] = 0.0

        if not mes or str(mes).strip() == "":
            return df_all
        
        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = (df_all["Mes"].astype(str) == str(mes))
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            res = df_all[cond]
            if res.empty:
                return pd.DataFrame({
                    "Anio": [int(anio) if anio else 2026]*4, 
                    "Mes": [int(mes)]*4, 
                    "Taxonomia": ["A", "B", "C", "D"], 
                    "Porcentaje_Cartera": [80.0, 70.0, 60.0, 50.0],
                    "Obj_CCC_Pepsico": [0.0, 0.0, 0.0, 0.0]
                })
            return res
            
        return df_all
    except Exception:
        return pd.DataFrame({
            "Anio": [2026]*4, "Mes": [9]*4, 
            "Taxonomia": ["A", "B", "C", "D"], 
            "Porcentaje_Cartera": [80.0, 70.0, 60.0, 50.0],
            "Obj_CCC_Pepsico": [0.0, 0.0, 0.0, 0.0]
        })

def obtener_objetivos_vendedores_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga los objetivos calibrados desde SQLite. Si mes está vacío, devuelve la base completa."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM objetivos_vendedores")
        if df_all is None or df_all.empty:
            return pd.DataFrame(columns=["Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "SEGMENTO", "Kilos_Mes_Anterior", "Objetivo_Mes_Anterior_Kg", "Logro_Anterior_Pct", "Obj_Sugerido_Kg"])
        
        if not mes or str(mes).strip() == "":
            return df_all
        
        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = (df_all["Mes"].astype(str) == str(mes))
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]
            
        return df_all
    except Exception:
        return pd.DataFrame(columns=["Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "SEGMENTO", "Kilos_Mes_Anterior", "Objetivo_Mes_Anterior_Kg", "Logro_Anterior_Pct", "Obj_Sugerido_Kg"])

def obtener_maestro_innovaciones_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga el maestro de innovaciones desde SQLite. Si mes está vacío, devuelve la base completa."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_innovaciones")
        if df_all is None or df_all.empty:
            return pd.DataFrame(columns=["Anio", "Mes", "Codigo", "Articulo", "Innovacion", "Condicion_Vta"])
        
        if not mes or str(mes).strip() == "":
            return df_all
        
        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = (df_all["Mes"].astype(str) == str(mes))
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]
            
        return df_all
    except Exception:
        return pd.DataFrame(columns=["Anio", "Mes", "Codigo", "Articulo", "Innovacion", "Condicion_Vta"])

def render_parametros_view(filtros_globales: dict = None):
    if not es_entorno_local():
        st.warning("⚠️ Esta sección de configuración y parámetros está restringida al entorno de desarrollo local.")
        return

    st.subheader("⚙️ Configuración de Dimensiones y Maestros")
    st.markdown("Los filtros operativos de Año, Mes, Fechas y Supervisor se gestionan desde la barra lateral izquierda. Esta sección permite cargar y mantener los maestros de Vendedores, Segmentos, Marcas / CEBE, Porcentajes y Objetivos CCC, Innovaciones e importar los objetivos calibrados.")

    anio_def = filtros_globales.get("anio", "2026") if filtros_globales else "2026"
    mes_def = filtros_globales.get("mes", "9") if filtros_globales else "9"

    # =========================================================================
    # 0. IMPORTADOR GLOBAL MULTI-SOLAPA (SOLUCIÓN UNIFICADA)
    # =========================================================================
    st.markdown("### 📂 0. Importador Global Multi-solapa (Actualización Masiva)")
    st.markdown("Sube aquí un único archivo Excel con múltiples solapas (exactamente con la estructura generada por el botón de descarga global) para poblar todas las bases de parámetros, maestros y objetivos de preventistas en un solo paso.")

    archivo_global_multisolapa = st.file_uploader(
        "📂 Subir Archivo Excel Multi-solapa Consolidado",
        type=["xlsx", "xls"],
        key="up_excel_global_multisolapa_principal"
    )

    if archivo_global_multisolapa is not None:
        try:
            xls_global = pd.ExcelFile(archivo_global_multisolapa)
            st.info(f"Solapas detectadas en el archivo: {', '.join(xls_global.sheet_names)}")

            if st.button("🚀 Procesar e Importar Masivamente Todas las Solapas", key="btn_ejecutar_importacion_global_multisolapa"):
                conn = db.obtener_conexion()
                try:
                    sheet_to_table = {
                        'Maestro_Vendedores': 'maestro_vendedores',
                        'Maestro_Segmentos': 'maestro_segmentos',
                        'Maestro_Marcas_CEBE': 'maestro_marcas_cebe',
                        'Maestro_CCC_Config': 'maestro_ccc',
                        'Maestro_Innovaciones': 'maestro_innovaciones',
                        'Objetivos_Calibrados': 'objetivos_vendedores'
                    }

                    importados_count = 0
                    for sheet_name, table_name in sheet_to_table.items():
                        if sheet_name in xls_global.sheet_names:
                            df_sheet = pd.read_excel(archivo_global_multisolapa, sheet_name=sheet_name)
                            if not df_sheet.empty:
                                if 'Anio' in df_sheet.columns:
                                    df_sheet['Anio'] = pd.to_numeric(df_sheet['Anio'], errors='coerce').fillna(int(anio_def)).astype(int)
                                if 'Mes' in df_sheet.columns:
                                    df_sheet['Mes'] = pd.to_numeric(df_sheet['Mes'], errors='coerce').fillna(int(mes_def)).astype(int)
                                
                                df_sheet.to_sql(table_name, conn, if_exists='replace', index=False, chunksize=10000)
                                importados_count += 1

                    st.success(f"¡Se han importado y actualizado exitosamente {importados_count} tablas en SQLite desde el archivo multi-solapa!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al procesar la importación multi-solapa: {e}")
                finally:
                    conn.close()
        except Exception as e:
            st.error(f"Error al leer el archivo Excel: {e}")

    st.divider()

    # =========================================================================
    # 1. SECCIÓN: MAESTRO DE VENDEDORES
    # =========================================================================
    st.markdown("### 👥 1. Maestro de Vendedores y Asignación por Período")
    col1, col2 = st.columns(2)
    with col1:
        sel_anio_v = st.text_input("Año Operativo (Vendedores)", value=anio_def, key="anio_vendedor")
    with col2:
        sel_mes_v = st.text_input("Mes Operativo (Vendedores)", value=mes_def, placeholder="Dejar vacío para ver toda la base", key="mes_vendedor")

    archivo_vendedores = st.file_uploader("📂 Subir Excel de Vendedores (Debe incluir 'Rutas_Ajustadas')", type=["xlsx", "xls"], key="up_excel_vendedores")

    if archivo_vendedores is not None:
        try:
            df_nuevo_master = pd.read_excel(archivo_vendedores)
            columnas_originales = list(df_nuevo_master.columns)
            
            if len(columnas_originales) >= 3:
                nuevos_nombres = {}
                for col in columnas_originales:
                    col_str = str(col).lower()
                    if "codigo" in col_str or "cod" in col_str:
                        nuevos_nombres[col] = "Codigo_Vendedor"
                    elif "nombre" in col_str or "vendedor" in col_str or "razon" in col_str:
                        nuevos_nombres[col] = "Nombre_Vendedor"
                    elif "super" in col_str or "sup" in col_str:
                        nuevos_nombres[col] = "Supervisor"
                    elif "rutas_ajustadas" in col_str or "rutasajustadas" in col_str or "ajustadas" in col_str:
                        nuevos_nombres[col] = "Rutas_Ajustadas"
                
                df_nuevo_master = df_nuevo_master.rename(columns=nuevos_nombres)
                
                if "Codigo_Vendedor" not in df_nuevo_master.columns and len(columnas_originales) > 0:
                    df_nuevo_master = df_nuevo_master.rename(columns={columnas_originales[0]: "Codigo_Vendedor"})
                if "Nombre_Vendedor" not in df_nuevo_master.columns and len(columnas_originales) > 1:
                    df_nuevo_master = df_nuevo_master.rename(columns={columnas_originales[1]: "Nombre_Vendedor"})
                if "Supervisor" not in df_nuevo_master.columns and len(columnas_originales) > 2:
                    df_nuevo_master = df_nuevo_master.rename(columns={columnas_originales[2]: "Supervisor"})
                if "Rutas_Ajustadas" not in df_nuevo_master.columns:
                    df_nuevo_master["Rutas_Ajustadas"] = 0

            st.write("Vista previa del archivo cargado:", df_nuevo_master.head())
            
            if st.button("📥 Registrar y Guardar Vendedores en Base de Datos"):
                if not sel_mes_v or str(sel_mes_v).strip() == "":
                    st.error("⚠️ Debe especificar un Mes Operativo válido para registrar el maestro.")
                else:
                    df_nuevo_master["Anio"] = str(sel_anio_v)
                    df_nuevo_master["Mes"] = str(sel_mes_v)
                    df_nuevo_master["Rutas_Ajustadas"] = pd.to_numeric(df_nuevo_master.get("Rutas_Ajustadas", 0), errors="coerce").fillna(0).astype(int)
                    
                    query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_vendedores'"
                    res_check = db.cargar_tabla_sql(query_check)
                    
                    if res_check is not None and not res_check.empty:
                        df_existente = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
                        df_existente = df_existente[~((df_existente["Anio"].astype(str) == str(sel_anio_v)) & (df_existente["Mes"].astype(str) == str(sel_mes_v)))]
                        df_final_master = pd.concat([df_existente, df_nuevo_master], ignore_index=True)
                    else:
                        df_final_master = df_nuevo_master

                    db.guardar_dataframe_sql(df_final_master, "maestro_vendedores", if_exists='replace')
                    st.success(f"¡Maestro de vendedores guardado exitosamente con Rutas Ajustadas para el período {sel_mes_v}/{sel_anio_v}!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel de vendedores: {e}")

    titulo_tabla_v = f"📋 Vendedores registrados en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_v or str(sel_mes_v).strip() == '' else f'Período {sel_mes_v}/{sel_anio_v}'})"
    st.markdown(f"#### {titulo_tabla_v}")
    
    df_maestro_actual = obtener_maestro_vendedores_sql(sel_anio_v, sel_mes_v)
    st.dataframe(df_maestro_actual, width="stretch")

    st.divider()

    # =========================================================================
    # 2. SECCIÓN: MAESTRO DE SEGMENTOS
    # =========================================================================
    st.markdown("### 🏷️ 2. Maestro de Objetivos por Segmento")
    col3, col4 = st.columns(2)
    with col3:
        sel_anio_s = st.text_input("Año Operativo (Segmentos)", value=anio_def, key="anio_segmento")
    with col4:
        sel_mes_s = st.text_input("Mes Operativo (Segmentos)", value=mes_def, placeholder="Dejar vacío para ver toda la base", key="mes_segmento")

    archivo_segmentos = st.file_uploader("📂 Subir Excel de Segmentos", type=["xlsx", "xls"], key="up_excel_segmentos")

    if archivo_segmentos is not None:
        try:
            df_nuevo_seg = pd.read_excel(archivo_segmentos)
            columnas_seg = list(df_nuevo_seg.columns)
            
            col_encontrada = None
            for c in columnas_seg:
                if "segmento" in str(c).strip().lower():
                    col_encontrada = c
                    break
            
            if col_encontrada:
                df_nuevo_seg = df_nuevo_seg.rename(columns={col_encontrada: "Segmento"})
            elif len(columnas_seg) > 0:
                df_nuevo_seg = df_nuevo_seg.rename(columns={columnas_seg[0]: "Segmento"})
            
            df_nuevo_seg = df_nuevo_seg.dropna(subset=["Segmento"])
            df_nuevo_seg["Segmento"] = df_nuevo_seg["Segmento"].astype(str).str.strip()

            st.write("Vista previa de Segmentos mapeados:", df_nuevo_seg.head())

            if st.button("📥 Registrar y Guardar Segmentos en Base de Datos"):
                if not sel_mes_s or str(sel_mes_s).strip() == "":
                    st.error("⚠️ Debe especificar un Mes Operativo válido para registrar los segmentos.")
                else:
                    df_nuevo_seg["Anio"] = str(sel_anio_s)
                    df_nuevo_seg["Mes"] = str(sel_mes_s)

                    query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_segmentos'"
                    res_check = db.cargar_tabla_sql(query_check)

                    if res_check is not None and not res_check.empty:
                        df_existente_seg = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos")
                        df_existente_seg = df_existente_seg[~((df_existente_seg["Anio"].astype(str) == str(sel_anio_s)) & (df_existente_seg["Mes"].astype(str) == str(sel_mes_s)))]
                        df_final_seg = pd.concat([df_existente_seg, df_nuevo_seg], ignore_index=True)
                    else:
                        df_final_seg = df_nuevo_seg

                    db.guardar_dataframe_sql(df_final_seg, "maestro_segmentos", if_exists='replace')
                    st.success(f"¡Maestro de segmentos guardado exitosamente para el período {sel_mes_s}/{sel_anio_s}!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel de segmentos: {e}")

    titulo_tabla_s = f"📋 Segmentos registrados en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_s or str(sel_mes_s).strip() == '' else f'Período {sel_mes_s}/{sel_anio_s}'})"
    st.markdown(f"#### {titulo_tabla_s}")

    df_segmentos_actual = obtener_maestro_segmentos_sql(sel_anio_s, sel_mes_s)
    st.dataframe(df_segmentos_actual, width="stretch")

    st.divider()

    # =========================================================================
    # 3. SECCIÓN: MAESTRO MARCA - CEBE Y OBJETIVOS (INCL. COBERTURA)
    # =========================================================================
    st.markdown("### 🏷️ 3. Maestro de Marcas, CEBE, Objetivos de TN/Gross y Cobertura (Pepsico / Empresa)")
    col5, col6 = st.columns(2)
    with col5:
        sel_anio_m = st.text_input("Año Operativo (Marcas/CEBE)", value=anio_def, key="anio_marca_cebe")
    with col6:
        sel_mes_m = st.text_input("Mes Operativo (Marcas/CEBE)", value=mes_def, placeholder="Dejar vacío para ver toda la base", key="mes_marca_cebe")

    df_marcas_cebe_actual = obtener_maestro_marcas_cebe_sql(sel_anio_m, sel_mes_m)

    output_plantilla = BytesIO()
    with pd.ExcelWriter(output_plantilla, engine='openpyxl') as writer:
        df_plantilla = df_marcas_cebe_actual.copy()
        if df_plantilla.empty:
            df_plantilla = pd.DataFrame(columns=["Anio", "Mes", "Marca", "CEBE", "Obj_TN_Mes", "Obj_Gross_Mes", "Obj_Pepsico_Cobertura", "Obj_Empresa_Cobertura"])
        df_plantilla.to_excel(writer, index=False, sheet_name='Maestro_Marcas_CEBE')

    st.download_button(
        label="📥 Descargar Plantilla de Marcas y CEBE para Completar",
        data=output_plantilla.getvalue(),
        file_name=f"plantilla_marcas_cebe_{sel_mes_m}_{sel_anio_m}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    archivo_marcas = st.file_uploader("📂 Subir Excel Actualizado de Marcas, CEBE y Objetivos", type=["xlsx", "xls"], key="up_excel_marcas_cebe")

    if archivo_marcas is not None:
        try:
            df_nuevo_cebe = pd.read_excel(archivo_marcas)
            columnas_cebe = list(df_nuevo_cebe.columns)

            nuevos_nombres_cebe = {}
            for col in columnas_cebe:
                col_str = str(col).strip().lower()
                if "marca" in col_str or "marcaupper" in col_str:
                    nuevos_nombres_cebe[col] = "Marca"
                elif "cebe" in col_str or "tipo" in col_str or "categoria" in col_str:
                    nuevos_nombres_cebe[col] = "CEBE"
                elif "obj_tn" in col_str or "tn" in col_str:
                    nuevos_nombres_cebe[col] = "Obj_TN_Mes"
                elif "obj_gross" in col_str or "gross" in col_str:
                    nuevos_nombres_cebe[col] = "Obj_Gross_Mes"
                elif "pepsico" in col_str or "coberturapepsico" in col_str:
                    nuevos_nombres_cebe[col] = "Obj_Pepsico_Cobertura"
                elif "empresa" in col_str or "coberturaempresa" in col_str:
                    nuevos_nombres_cebe[col] = "Obj_Empresa_Cobertura"

            df_nuevo_cebe = df_nuevo_cebe.rename(columns=nuevos_nombres_cebe)

            cols_necesarias_cebe = ["Obj_TN_Mes", "Obj_Gross_Mes", "Obj_Pepsico_Cobertura", "Obj_Empresa_Cobertura"]
            for col_req in cols_necesarias_cebe:
                if col_req not in df_nuevo_cebe.columns:
                    df_nuevo_cebe[col_req] = 0.0
                else:
                    df_nuevo_cebe[col_req] = pd.to_numeric(df_nuevo_cebe[col_req], errors="coerce").fillna(0.0)

            if "Marca" not in df_nuevo_cebe.columns or "CEBE" not in df_nuevo_cebe.columns:
                st.error("⚠️ El archivo Excel debe contener al menos las columnas 'Marca' y 'CEBE'.")
            else:
                cols_requeridas = ["Marca", "CEBE", "Obj_TN_Mes", "Obj_Gross_Mes", "Obj_Pepsico_Cobertura", "Obj_Empresa_Cobertura"]
                df_nuevo_cebe = df_nuevo_cebe[[c for c in cols_requeridas if c in df_nuevo_cebe.columns]].copy()
                df_nuevo_cebe = df_nuevo_cebe.dropna(subset=["Marca", "CEBE"])
                df_nuevo_cebe["Marca"] = df_nuevo_cebe["Marca"].astype(str).str.strip()
                df_nuevo_cebe["CEBE"] = df_nuevo_cebe["CEBE"].astype(str).str.strip()

                st.write("Vista previa de Marcas, CEBE y Objetivos mapeados:", df_nuevo_cebe.head())

                if st.button("📥 Registrar y Guardar Marcas/CEBE y Objetivos en Base de Datos"):
                    if not sel_mes_m or str(sel_mes_m).strip() == "":
                        st.error("⚠️ Debe especificar un Mes Operativo válido para registrar las marcas, CEBE y objetivos.")
                    else:
                        df_nuevo_cebe["Anio"] = str(sel_anio_m)
                        df_nuevo_cebe["Mes"] = str(sel_mes_m)

                        query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_marcas_cebe'"
                        res_check = db.cargar_tabla_sql(query_check)

                        if res_check is not None and not res_check.empty:
                            df_existente_cebe = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
                            df_existente_cebe = df_existente_cebe[~((df_existente_cebe["Anio"].astype(str) == str(sel_anio_m)) & (df_existente_cebe["Mes"].astype(str) == str(sel_mes_m)))]
                            df_final_cebe = pd.concat([df_existente_cebe, df_nuevo_cebe], ignore_index=True)
                        else:
                            df_final_cebe = df_nuevo_cebe

                        db.guardar_dataframe_sql(df_final_cebe, "maestro_marcas_cebe", if_exists='replace')
                        st.success(f"¡Maestro Marca/CEBE y Objetivos guardado exitosamente para el período {sel_mes_m}/{sel_anio_m}!")
                        st.rerun()
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel de Marcas/CEBE: {e}")

    titulo_tabla_m = f"📋 Marcas, CEBE y Objetivos registrados en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_m or str(sel_mes_m).strip() == '' else f'Período {sel_mes_m}/{sel_anio_m}'})"
    st.markdown(f"#### {titulo_tabla_m}")

    df_marcas_cebe_actual = obtener_maestro_marcas_cebe_sql(sel_anio_m, sel_mes_m)
    st.dataframe(df_marcas_cebe_actual, width="stretch")

    st.divider()

    # =========================================================================
    # 3.B SECCIÓN: MAESTRO CCC (INCLUYENDO Obj_CCC_Pepsico) - VERSIONADO HISTÓRICO
    # =========================================================================
    st.markdown("### 📊 3.B Maestro CCC (Porcentaje Cartera y Objetivo Absoluto Obj_CCC_Pepsico)")
    st.markdown("Configure el porcentaje (%) sobre la cartera neta y/o el **Objetivo en cantidad de clientes de Pepsico (`Obj_CCC_Pepsico`)** para cada taxonomía (A, B, C, D) en el período seleccionado.")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        sel_anio_ccc = st.text_input("Año Operativo (CCC)", value=anio_def, key="anio_ccc_param")
    with col_c2:
        sel_mes_ccc = st.text_input("Mes Operativo (CCC)", value=mes_def, key="mes_ccc_param")

    df_ccc_actual = obtener_maestro_ccc_sql(sel_anio_ccc, sel_mes_ccc)

    df_editado_ccc = st.data_editor(
        df_ccc_actual[["Taxonomia", "Porcentaje_Cartera", "Obj_CCC_Pepsico"]],
        num_rows="fixed",
        key="editor_maestro_ccc",
        width='stretch'
    )

    if st.button("📥 Registrar y Guardar Configuración CCC en Base de Datos"):
        if not sel_mes_ccc or str(sel_mes_ccc).strip() == "":
            st.error("⚠️ Debe especificar un Mes Operativo válido para guardar la configuración CCC.")
        else:
            df_nuevo_ccc = df_editado_ccc.copy()
            df_nuevo_ccc["Anio"] = int(float(sel_anio_ccc))
            df_nuevo_ccc["Mes"] = int(float(sel_mes_ccc))
            df_nuevo_ccc["Porcentaje_Cartera"] = pd.to_numeric(df_nuevo_ccc["Porcentaje_Cartera"], errors="coerce").fillna(0.0)
            df_nuevo_ccc["Obj_CCC_Pepsico"] = pd.to_numeric(df_nuevo_ccc["Obj_CCC_Pepsico"], errors="coerce").fillna(0.0)

            query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_ccc'"
            res_check = db.cargar_tabla_sql(query_check)

            if res_check is not None and not res_check.empty:
                df_existente_ccc = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
                df_existente_ccc = df_existente_ccc[~((df_existente_ccc["Anio"].astype(str) == str(sel_anio_ccc)) & (df_existente_ccc["Mes"].astype(str) == str(sel_mes_ccc)))]
                df_final_ccc = pd.concat([df_existente_ccc, df_nuevo_ccc], ignore_index=True)
            else:
                df_final_ccc = df_nuevo_ccc

            db.guardar_dataframe_sql(df_final_ccc, "maestro_ccc", if_exists='replace')
            st.success(f"¡Configuración CCC guardada y versionada exitosamente para el período {sel_mes_ccc}/{sel_anio_ccc}!")
            st.rerun()

    titulo_tabla_ccc_reg = f"📋 Parámetros CCC registrados en Base de Datos (Período {sel_mes_ccc}/{sel_anio_ccc})"
    st.markdown(f"#### {titulo_tabla_ccc_reg}")
    st.dataframe(df_ccc_actual, width="stretch")

    st.divider()

    # =========================================================================
    # 4. SECCIÓN: MAESTRO DE INNOVACIONES
    # =========================================================================
    st.markdown("### 🚀 4. Maestro de Innovaciones")
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        sel_anio_in = st.text_input("Año Operativo (Innovaciones)", value=anio_def, key="anio_innovaciones")
    with col_in2:
        sel_mes_in = st.text_input("Mes Operativo (Innovaciones)", value=mes_def, placeholder="Dejar vacío para ver toda la base", key="mes_innovaciones")

    archivo_innovaciones = st.file_uploader("📂 Subir Excel de Innovaciones", type=["xlsx", "xls"], key="up_excel_innovaciones")

    if archivo_innovaciones is not None:
        try:
            st.write("Vista previa del archivo de innovaciones:", pd.read_excel(archivo_innovaciones).head())

            if st.button("📥 Registrar y Guardar Innovaciones en Base de Datos"):
                if not sel_mes_in or str(sel_mes_in).strip() == "":
                    st.error("⚠️ Debe especificar un Mes Operativo válido para registrar las innovaciones.")
                else:
                    exito, mensaje = db.guardar_innovaciones_desde_excel(archivo_innovaciones, sel_anio_in, sel_mes_in)
                    if exito:
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.error(mensaje)
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel de innovaciones: {e}")

    titulo_tabla_in = f"📋 Innovaciones registradas en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_in or str(sel_mes_in).strip() == '' else f'Período {sel_mes_in}/{sel_anio_in}'})"
    st.markdown(f"#### {titulo_tabla_in}")

    df_innovaciones_actual = obtener_maestro_innovaciones_sql(sel_anio_in, sel_mes_in)
    st.dataframe(df_innovaciones_actual, width="stretch")

    st.divider()

    # =========================================================================
    # 5. SECCIÓN: IMPORTACIÓN DE OBJETIVOS CALIBRADOS (DEFINITIVOS)
    # =========================================================================
    st.markdown("### 📥 5. Importación de Objetivos Calibrados (Definitivos)")
    col7, col8 = st.columns(2)
    with col7:
        sel_anio_obj = st.text_input("Año Operativo (Objetivos Calibrados)", value=anio_def, key="anio_objetivos_calib")
    with col8:
        sel_mes_obj = st.text_input("Mes Operativo (Objetivos Calibrados)", value=mes_def, key="mes_objetivos_calib")

    archivo_objetivos_subido = st.file_uploader(
        "📂 Subir Excel de Objetivos Calibrados (.xlsx)",
        type=["xlsx", "xls"],
        key="up_excel_objetivos_calibrados"
    )

    if archivo_objetivos_subido is not None:
        try:
            st.write("Vista previa del Excel calibrado:", pd.read_excel(archivo_objetivos_subido).head())
            
            if st.button("🚀 Procesar e Ingresar Objetivos Calibrados a la Base de Datos"):
                if not sel_mes_obj or str(sel_mes_obj).strip() == "":
                    st.error("⚠️ Debe especificar un Mes Operativo válido para versionar los objetivos.")
                else:
                    with st.spinner("Guardando y versionando objetivos en SQLite..."):
                        exito, mensaje = db.guardar_objetivos_calibrados_desde_excel(archivo_objetivos_subido, sel_anio_obj, sel_mes_obj)
                        if exito:
                            st.success(mensaje)
                            st.rerun()
                        else:
                            st.error(mensaje)
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel calibrado: {e}")

    titulo_tabla_obj = f"📋 Objetivos Calibrados registrados en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_obj or str(sel_mes_obj).strip() == '' else f'Período {sel_mes_obj}/{sel_anio_obj}'})"
    st.markdown(f"#### {titulo_tabla_obj}")

    df_objetivos_actual = obtener_objetivos_vendedores_sql(sel_anio_obj, sel_mes_obj)
    st.dataframe(df_objetivos_actual, width="stretch")

    st.divider()

    # =========================================================================
    # BOTÓN DE DESCARGA GLOBAL A EXCEL
    # =========================================================================
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_maestro_actual.to_excel(writer, index=False, sheet_name='Maestro_Vendedores')
        df_segmentos_actual.to_excel(writer, index=False, sheet_name='Maestro_Segmentos')
        df_marcas_cebe_actual.to_excel(writer, index=False, sheet_name='Maestro_Marcas_CEBE')
        df_ccc_actual.to_excel(writer, index=False, sheet_name='Maestro_CCC_Config')
        df_innovaciones_actual.to_excel(writer, index=False, sheet_name='Maestro_Innovaciones')
        df_objetivos_actual.to_excel(writer, index=False, sheet_name='Objetivos_Calibrados')
    
    st.download_button(
        label="📥 Descargar Maestros y Objetivos Completos a Excel",
        data=output.getvalue(),
        file_name="maestros_y_objetivos_matinal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

====================================================================================================


### ARCHIVO: modules\rep_ccc.py

# modules/rep_ccc.py
import io
import os
import urllib.parse
import unicodedata
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import parsear_fecha_robusta, extraer_dia_de_ruta, extraer_dia_de_ruta_vectorial

def preparar_ventas_ccc(df_vta, df_ausencias, anio_operativo, mes_operativo, dia_matinal):
    """
    Pipeline de ventas optimizado para CCC derivado del DataFrame Maestro N1 (EMPLEADOS).
    Aplica los filtros N2: PEPSICO, COMODATOS, DEPOSITO, MATINAL y PERIODO.
    """
    # Nivel 1: Obtención del DataFrame corporativo base con filtro EMPLEADOS aplicado
    df_corp = db.obtener_df_maestro_corporativo()
    df = df_corp.copy() if not df_corp.empty else (df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame())
    
    if df.empty:
        return df

    col_cant = next((c for c in ["CantBase", "CANTBASE", "Cantidad", "CANTIDAD", "Unidades", "UNIDADES"] if c in df.columns), df.columns[0])
    df["CantBase"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0.0)

    col_imp = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df.columns), None)
    if col_imp:
        df["ImporteNeto"] = pd.to_numeric(df[col_imp], errors="coerce").fillna(0.0)
    else:
        df["ImporteNeto"] = 0.0

    # Nivel 2: Filtro COMODATOS (Exclusión de comodatos y préstamos)
    if "TipoDeVenta" in df.columns:
        tipos_excluidos = [
            "Comodato Devolución", 
            "Comodato Ficticio", 
            "Comodato Ficticio Devolución", 
            "Comodato Préstamo"
        ]
        df = df[~df["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)]

    # Nivel 2: Filtro PEPSICO (Selección exclusiva de proveedor PepsiCo)
    if "Proveedor" in df.columns:
        df = df[
            df["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    # Nivel 2: Filtro MATINAL (Exclusión de registros cuya fecha de carga sea igual o posterior al Día Matinal)
    dia_matinal_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(dia_matinal_dt):
        es_mes_en_curso = (dia_matinal_dt.year == anio_operativo and dia_matinal_dt.month in [mes_operativo, mes_operativo + 1])
        if es_mes_en_curso:
            df = df[df["FechaCarga_dt"].dt.date < dia_matinal_dt.date()]

    col_vend_tit = next((cand for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"] if cand in df.columns), "CodVendedor")
    df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype("Int64")
    
    # Nivel 2: Filtro DEPOSITO (Exclusión del vendedor 20 para aislar preventistas puros)
    df = df[df["CodVendedor"] != 20]

    df["MesCarga"] = df["FechaCarga_dt"].dt.month
    df["AñoCarga"] = df["FechaCarga_dt"].dt.year
    df["MesEntrega"] = df["FechaEntrega_dt"].dt.month
    df["AñoEntrega"] = df["FechaEntrega_dt"].dt.year

    mes_ant = 12 if mes_operativo == 1 else mes_operativo - 1
    anio_ant = anio_operativo - 1 if mes_operativo == 1 else anio_operativo

    mes_sig = 1 if mes_operativo == 12 else mes_operativo + 1
    anio_sig = anio_operativo + 1 if mes_operativo == 12 else anio_operativo

    conditions = [
        (df["AñoCarga"] == anio_ant) & (df["MesCarga"] == mes_ant) & (df["AñoEntrega"] == anio_operativo) & (df["MesEntrega"] == mes_operativo),
        (df["AñoCarga"] == anio_operativo) & (df["MesCarga"] == mes_operativo) & (df["AñoEntrega"] == anio_operativo) & (df["MesEntrega"] == mes_operativo),
        (df["AñoCarga"] == anio_operativo) & (df["MesCarga"] == mes_operativo) & (df["AñoEntrega"] == anio_sig) & (df["MesEntrega"] == mes_sig)
    ]
    choices = ["Arrastre", "Actual", "Futuro"]
    
    # Nivel 2: Filtro PERIODO (Clasificación de transacciones en Arrastre, Actual o Futuro)
    df["Periodo"] = np.select(conditions, choices, default="Fuera de Periodo")

    df["ClaveAUS_Carga"] = df["CodVendedor"].astype(str) + "-" + df["FechaCarga_dt"].dt.strftime("%Y-%m-%d")
    df["ClaveAUS_Entrega"] = df["CodVendedor"].astype(str) + "-" + df["FechaEntrega_dt"].dt.strftime("%Y-%m-%d")

    df_aus = df_ausencias.copy() if df_ausencias is not None and not df_ausencias.empty else pd.DataFrame()
    if not df_aus.empty:
        col_aus_vend = next((c for c in ["Ausente", "CodVend", "CodVendedor", "Vendedor", "Cod_Vendedor"] if c in df_aus.columns), df_aus.columns[3])
        col_aus_fecha = next((c for c in df_aus.columns if c in ["Fecha", "FechaAusencia", "Dia"]), df_aus.columns[2])
        col_aus_reemp = next((c for c in df_aus.columns if c in ["Reemplazo", "CodReemplazo", "Cod_Reemplazo", "PreventistaReemplazo"]), df_aus.columns[4])

        df_aus["Fecha_dt"] = parsear_fecha_robusta(df_aus[col_aus_fecha])
        df_aus["CodVend_clean"] = pd.to_numeric(df_aus[col_aus_vend], errors="coerce").astype("Int64")
        df_aus["ClaveAUS"] = df_aus["CodVend_clean"].astype(str) + "-" + df_aus["Fecha_dt"].dt.strftime("%Y-%m-%d")
        df_aus["Reemplazo_clean"] = pd.to_numeric(df_aus[col_aus_reemp], errors="coerce").astype("Int64")

        aus_map = df_aus.dropna(subset=["ClaveAUS", "Reemplazo_clean"]).drop_duplicates("ClaveAUS").set_index("ClaveAUS")["Reemplazo_clean"]
        
        df["Reemplazo"] = df["ClaveAUS_Carga"].map(aus_map).combine_first(df["ClaveAUS_Entrega"].map(aus_map))
        df["CodVendedorOperativo"] = df["Reemplazo"].combine_first(df["CodVendedor"]).astype("Int64")
    else:
        df["Reemplazo"] = pd.NA
        df["CodVendedorOperativo"] = df["CodVendedor"]

    return df

def _calcular_base_ccc(df_vta, df_universo, vendedores, hoja_ccc_param, anio_op, mes_op, dia_matinal):
    try:
        df_ccc_db = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
        if df_ccc_db is not None and not df_ccc_db.empty and "Anio" in df_ccc_db.columns and "Mes" in df_ccc_db.columns:
            df_ccc_per = df_ccc_db[(df_ccc_db["Anio"].astype(str) == str(anio_op)) & (df_ccc_db["Mes"].astype(str) == str(mes_op))]
            if not df_ccc_per.empty:
                hoja_ccc = df_ccc_per
            else:
                hoja_ccc = hoja_ccc_param
        else:
            hoja_ccc = hoja_ccc_param
    except Exception:
        hoja_ccc = hoja_ccc_param

    hoja_ccc = hoja_ccc.copy() if hoja_ccc is not None and not hoja_ccc.empty else pd.DataFrame(columns=["Taxonomia", "Porcentaje_Cartera"])
    if not hoja_ccc.empty:
        hoja_ccc.columns = hoja_ccc.columns.astype(str).str.strip()
        rename_metas = {}
        for c in hoja_ccc.columns:
            if str(c).lower() in ["porcentaje_cartera", "porcentaje", "pct", "obj", "objetivo", "obj_ccc"]:
                rename_metas[c] = "Porcentaje_Cartera"
            if str(c).lower() in ["taxonomia", "taxonomía", "categoria", "categoría"]:
                rename_metas[c] = "Taxonomia"
        hoja_ccc = hoja_ccc.rename(columns=rename_metas)
        if "Taxonomia" in hoja_ccc.columns:
            hoja_ccc["Taxonomia"] = hoja_ccc["Taxonomia"].astype(str).str.strip().str.upper()
        if "Porcentaje_Cartera" in hoja_ccc.columns:
            hoja_ccc["Porcentaje_Cartera"] = pd.to_numeric(hoja_ccc["Porcentaje_Cartera"], errors="coerce").fillna(0.0)
            hoja_ccc = hoja_ccc[["Taxonomia", "Porcentaje_Cartera"]].drop_duplicates("Taxonomia")
        else:
            hoja_ccc["Porcentaje_Cartera"] = 80.0
    else:
        hoja_ccc = pd.DataFrame({"Taxonomia": ["A", "B", "C", "D"], "Porcentaje_Cartera": [80.0, 70.0, 60.0, 50.0]})

    try:
        df_ausencias = db.cargar_tabla_sql("SELECT * FROM ausencias")
    except Exception:
        df_ausencias = pd.DataFrame()

    df_altas_all = db.cargar_tabla_sql("SELECT * FROM altas")
    
    if df_altas_all.empty:
        ruta_altas = "ALTAS.xlsx" if os.path.exists("ALTAS.xlsx") else "data/ALTAS.xlsx"
        if os.path.exists(ruta_altas):
            try:
                xls_altas = pd.ExcelFile(ruta_altas)
                dfs = []
                for sh in xls_altas.sheet_names:
                    ds = pd.read_excel(ruta_altas, sheet_name=sh)
                    ds["Origen_Hoja"] = sh
                    dfs.append(ds)
                if dfs:
                    df_altas_all = pd.concat(dfs, ignore_index=True)
            except Exception:
                pass

    altas_nuevas_set = set()
    reactivaciones_set = set()

    if not df_altas_all.empty:
        col_f = next((c for c in df_altas_all.columns if "fecha" in str(c).lower()), None)
        col_c = next((c for c in df_altas_all.columns if "codigo" in str(c).lower() or "cliente" in str(c).lower()), df_altas_all.columns[0])
        col_est = next((c for c in df_altas_all.columns if "estado" in str(c).lower()), None)
        col_orig = next((c for c in df_altas_all.columns if "origen_hoja" in str(c).lower() or "origen" in str(c).lower()), "Origen_Hoja")

        if col_f:
            df_altas_all["Fecha_dt"] = parsear_fecha_robusta(df_altas_all[col_f])
            f_mes = df_altas_all[
                (df_altas_all["Fecha_dt"].dt.year == int(anio_op)) & 
                (df_altas_all["Fecha_dt"].dt.month == int(mes_op))
            ].copy()

            if col_est and "Estado" in f_mes.columns:
                f_mes = f_mes[f_mes["Estado"].astype(str).str.strip().str.upper() != "CIERRE DEFINITIVO"]

            if not f_mes.empty and col_orig in f_mes.columns:
                f_mes["_orig_clean"] = f_mes[col_orig].astype(str).str.strip().str.casefold()
                
                crea_rows = f_mes[f_mes["_orig_clean"] == "creacion"]
                acti_rows = f_mes[f_mes["_orig_clean"] == "activacion"]
                inac_rows = f_mes[f_mes["_orig_clean"] == "inactivacion"]

                altas_nuevas_set = set(pd.to_numeric(crea_rows[col_c], errors="coerce").dropna().astype("Int64").tolist())
                activacion_bruta_set = set(pd.to_numeric(acti_rows[col_c], errors="coerce").dropna().astype("Int64").tolist())
                inactivaciones_set = set(pd.to_numeric(inac_rows[col_c], errors="coerce").dropna().astype("Int64").tolist())

                reactivaciones_set = (activacion_bruta_set - altas_nuevas_set) - inactivaciones_set
                altas_nuevas_set = altas_nuevas_set - inactivaciones_set

    df_vta_prep = preparar_ventas_ccc(df_vta, df_ausencias, anio_op, mes_op, dia_matinal)
    ventas_periodo = df_vta_prep[df_vta_prep["Periodo"].isin(["Arrastre", "Actual"])].copy() if not df_vta_prep.empty and "Periodo" in df_vta_prep.columns else df_vta_prep.copy()

    if not ventas_periodo.empty:
        col_c_orig = next((c for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"] if c in ventas_periodo.columns), "Cliente")
        ventas_periodo["Cliente"] = pd.to_numeric(ventas_periodo[col_c_orig], errors="coerce").astype("Int64")
        
        col_cant = next((c for c in ["CantBase", "CANTBASE", "Cantidad", "CANTIDAD", "Unidades", "UNIDADES"] if c in ventas_periodo.columns), "CantBase")
        ventas_periodo["_cant_calc"] = pd.to_numeric(ventas_periodo[col_cant], errors="coerce").fillna(0.0)
        
        col_imp = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in ventas_periodo.columns), None)
        if col_imp:
            ventas_periodo["_imp_calc"] = pd.to_numeric(ventas_periodo[col_imp], errors="coerce").fillna(0.0)
        else:
            ventas_periodo["_imp_calc"] = 0.0

        clientes_g = ventas_periodo.groupby("Cliente", as_index=False).agg(
            Total_Cant=("_cant_calc", "sum"),
            Total_Imp=("_imp_calc", "sum")
        )
        
        # Nivel 2: Filtro CCC (Restringe el universo a clientes que registren CantBase >= 3 e ImporteNeto >= 1)
        clientes_g["Es_CCC"] = clientes_g["Total_Cant"].ge(3) & clientes_g["Total_Imp"].ge(1)
    else:
        clientes_g = pd.DataFrame(columns=["Cliente", "Es_CCC"])

    universo = df_universo.copy() if df_universo is not None else pd.DataFrame()
    if not universo.empty:
        cols_u = [str(c).strip().lower() for c in universo.columns]
        col_prov_u = next((universo.columns[i] for i, c in enumerate(cols_u) if c in ["proveedor", "fabricante", "empresa"]), None)
        if col_prov_u:
            spu = universo[col_prov_u]
            if isinstance(spu, pd.DataFrame): spu = spu.iloc[:, 0]
            universo = universo[spu.astype(str).str.contains("pepsico", case=False, na=False)].copy()

        col_sub_u = next((c for c in universo.columns if "subramo" in str(c).lower()), None)
        if col_sub_u:
            ssu = universo[col_sub_u]
            if isinstance(ssu, pd.DataFrame): ssu = ssu.iloc[:, 0]
            universo = universo[ssu.fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()

        pos_v_u = next((c for c in ["codven", "CodVendedor", "CodVend", "Vendedor", "cod_vendedor"] if c in universo.columns), None)
        if pos_v_u:
            sv_u = universo[pos_v_u]
            if isinstance(sv_u, pd.DataFrame): sv_u = sv_u.iloc[:, 0]
            universo["CodVendedor"] = pd.to_numeric(sv_u, errors="coerce").astype("Int64")

        tax_col = next((c for c in universo.columns if "taxonomia" in str(c).lower() or "segmentoclientecodigo" in str(c).lower() or "clasificacion" in str(c).lower()), None)
        if tax_col:
            stx = universo[tax_col]
            if isinstance(stx, pd.DataFrame): stx = stx.iloc[:, 0]
            universo["Taxonomia"] = stx.fillna("").astype(str).str.strip().str.upper()
        else:
            universo["Taxonomia"] = "A"

        col_ruta_u = next((c for c in universo.columns if str(c).strip().lower() in ["ruta", "dia_visita", "visita", "dia"]), None)
        if col_ruta_u is not None:
            sr_u = universo[col_ruta_u]
            if isinstance(sr_u, pd.DataFrame):
                sr_u = sr_u.iloc[:, 0]
            universo["DiaVisita"] = extraer_dia_de_ruta_vectorial(sr_u)
        else:
            if "DiaVisita" not in universo.columns:
                universo["DiaVisita"] = "SIN DÍA"

        cli_col_u = next((c for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"] if c in universo.columns), universo.columns[0])
        scli_u = universo[cli_col_u]
        if isinstance(scli_u, pd.DataFrame): scli_u = scli_u.iloc[:, 0]
        universo["Cliente"] = pd.to_numeric(scli_u, errors="coerce").astype("Int64")
        universo = universo[universo["Taxonomia"].isin(["A", "B", "C", "D"])].dropna(subset=["Cliente", "CodVendedor"])

    if not universo.empty and "CodVendedor" in universo.columns:
        universo["CodVendedor"] = pd.to_numeric(universo["CodVendedor"], errors="coerce").astype("Int64")
        universo = universo[universo["CodVendedor"] != 20]

    if not universo.empty:
        universo["Es_Alta_Periodo"] = universo["Cliente"].isin(altas_nuevas_set)
        universo["Es_Reactivacion"] = universo["Cliente"].isin(reactivaciones_set)
    else:
        universo["Es_Alta_Periodo"] = False
        universo["Es_Reactivacion"] = False

    if not universo.empty and not clientes_g.empty:
        universo = universo.merge(clientes_g[["Cliente", "Es_CCC"]], on="Cliente", how="left")
        universo["Es_CCC"] = universo["Es_CCC"].fillna(False)
    else:
        universo["Es_CCC"] = False

    excluidos_set = altas_nuevas_set.union(reactivaciones_set)

    cartera_matriz = universo.groupby(["CodVendedor", "Taxonomia"], as_index=False).agg(
        Cartera_Total=("Cliente", "count"),
        Altas=("Es_Alta_Periodo", lambda x: int(x.sum())),
        Reactivaciones=("Es_Reactivacion", lambda x: int(x.sum())),
        Cartera_Neta=("Cliente", lambda x: int(len(x) - x.isin(excluidos_set).sum())),
        CCC=("Es_CCC", lambda x: int(x.sum()))
    ) if not universo.empty and "CodVendedor" in universo.columns else pd.DataFrame(columns=["CodVendedor", "Taxonomia", "Cartera_Total", "Altas", "Reactivaciones", "Cartera_Neta", "CCC"])

    vendedores_df = pd.DataFrame()
    vendedores_seguro = vendedores.copy() if vendedores is not None and not vendedores.empty else pd.DataFrame(columns=["Codigo_Vendedor", "Nombre_Vendedor", "Supervisor"])
    if vendedores_seguro.empty:
        vendedores_seguro = pd.DataFrame({"Codigo_Vendedor": [0], "Nombre_Vendedor": ["SIN ASIGNAR"], "Supervisor": ["GENERAL"]})

    col_c_v = next((c for c in ["Codigo_Vendedor", "CodVend", "CodVendedor"] if c in vendedores_seguro.columns), vendedores_seguro.columns[0])
    col_n_v = next((c for c in ["Nombre_Vendedor", "Nombre"] if c in vendedores_seguro.columns), vendedores_seguro.columns[1] if len(vendedores_seguro.columns) > 1 else vendedores_seguro.columns[0])
    col_s_v = next((c for c in ["Supervisor", "SUP"] if c in vendedores_seguro.columns), vendedores_seguro.columns[2] if len(vendedores_seguro.columns) > 2 else vendedores_seguro.columns[0])

    sv_c = vendedores_seguro[col_c_v]
    if isinstance(sv_c, pd.DataFrame): sv_c = sv_c.iloc[:, 0]
    vendedores_df["CodVendedor"] = pd.to_numeric(sv_c, errors="coerce").astype("Int64")
    vendedores_df = vendedores_df[vendedores_df["CodVendedor"] != 20]

    sv_n = vendedores_seguro[col_n_v]
    if isinstance(sv_n, pd.DataFrame): sv_n = sv_n.iloc[:, 0]
    vendedores_df["Nombre"] = sv_n.fillna("").astype(str).str.strip()
    sv_s = vendedores_seguro[col_s_v]
    if isinstance(sv_s, pd.DataFrame): sv_s = sv_s.iloc[:, 0]
    vendedores_df["SUP"] = sv_s.fillna("").astype(str).str.strip()
    vendedores_df = vendedores_df.drop_duplicates("CodVendedor")

    df_det_nc = universo.merge(vendedores_df, on="CodVendedor", how="left") if not universo.empty and not vendedores_df.empty else pd.DataFrame()

    taxonomias_df = pd.DataFrame({"Taxonomia": ["A", "B", "C", "D"]})
    vendedores_df["_k"], taxonomias_df["_k"] = 1, 1
    matriz_base = vendedores_df.merge(taxonomias_df, on="_k").drop(columns="_k")

    reporte = matriz_base.merge(cartera_matriz, on=["CodVendedor", "Taxonomia"], how="left")
    reporte[["Cartera_Total", "Altas", "Reactivaciones", "Cartera_Neta", "CCC"]] = reporte[["Cartera_Total", "Altas", "Reactivaciones", "Cartera_Neta", "CCC"]].fillna(0).astype("Int64")
    reporte["NC"] = (reporte["Cartera_Total"] - reporte["CCC"]).clip(lower=0).astype("Int64")
    
    reporte["% Cartera"] = (reporte["CCC"] / reporte["Cartera_Neta"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)

    reporte = reporte.merge(hoja_ccc, on="Taxonomia", how="left")
    reporte["Porcentaje_Cartera"] = reporte["Porcentaje_Cartera"].fillna(80.0)
    reporte["Objetivo_CCC"] = (reporte["Cartera_Neta"] * (reporte["Porcentaje_Cartera"] / 100.0)).round(0).astype("Int64")
    reporte["% Objetivo"] = (reporte["CCC"] / reporte["Objetivo_CCC"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)

    reporte["CodVendedor"] = pd.to_numeric(reporte["CodVendedor"], errors="coerce").astype("Int64")
    reporte = reporte.sort_values(by=["CodVendedor", "Taxonomia"], ascending=[True, True]).reset_index(drop=True)

    columnas_salida = [
        "CodVendedor", "Nombre", "SUP", "Taxonomia", 
        "Cartera_Total", "Altas", "Reactivaciones", "Cartera_Neta", 
        "Objetivo_CCC", "CCC", "NC", "% Cartera", "% Objetivo"
    ]
    return reporte[columnas_salida], df_det_nc

@st.cache_data(show_spinner=False)
def _calcular_base_ccc_cached(df_vta, df_universo, vendedores, hoja_ccc_param, anio_op, mes_op, dia_matinal, huella_datos):
    return _calcular_base_ccc(df_vta, df_universo, vendedores, hoja_ccc_param, anio_op, mes_op, dia_matinal)

def generar_reporte_ccc_taxonomia(df_vta, df_universo, vendedores, hoja_ccc_param, filtros_globales=None):
    anio_op = int(filtros_globales.get("anio", 2026)) if filtros_globales else 2026
    mes_op = int(filtros_globales.get("mes", 9)) if filtros_globales else 9
    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026") if filtros_globales else "02/09/2026"
    sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip() if filtros_globales else "TODOS"

    huella_datos = f"{len(df_vta) if df_vta is not None else 0}_{len(df_universo) if df_universo is not None else 0}_{anio_op}_{mes_op}_{dia_matinal}"

    keys_to_delete = [k for k in st.session_state.keys() if "_ccc_motor_cache_" in k]
    for k in keys_to_delete:
        del st.session_state[k]

    clave_cache_estado = f"_ccc_motor_cache_v68_{anio_op}_{mes_op}_{dia_matinal}_{sup_filtro}"
    if clave_cache_estado not in st.session_state:
        rep, det = _calcular_base_ccc_cached(df_vta, df_universo, vendedores, hoja_ccc_param, anio_op, mes_op, dia_matinal, huella_datos)
        st.session_state[clave_cache_estado] = (rep, det)

    rep_cached, det_cached = st.session_state[clave_cache_estado]
    st.session_state["_ccc_df_clientes_detalle"] = det_cached
    return rep_cached

def _tarjeta_metrica_compacta_html(label, valor, border_color="#475569", border_width="1px"):
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
def render_fragmento_interactivo_ccc(reporte_ccc_base, supervisores_seleccionados):
    if reporte_ccc_base is None or reporte_ccc_base.empty:
        st.info("No hay datos disponibles para procesar el Avance de Clientes con Compra.")
        return

    df_clientes_det = st.session_state.get("_ccc_df_clientes_detalle", pd.DataFrame())
    if df_clientes_det.empty:
        st.info("No se encontró el detalle de clientes para el filtrado dinámico.")
        return

    df_base_cli = df_clientes_det.copy()
    
    if "Es_Reactivacion" not in df_base_cli.columns:
        df_base_cli["Es_Reactivacion"] = False
    if "Es_Alta_Periodo" not in df_base_cli.columns:
        df_base_cli["Es_Alta_Periodo"] = False

    if supervisores_seleccionados and "SUP" in df_base_cli.columns:
        df_base_cli = df_base_cli[df_base_cli["SUP"].astype(str).str.strip().isin([str(s).strip() for s in supervisores_seleccionados])].copy()

    if df_base_cli.empty:
        st.info("No se encontraron registros para los supervisores seleccionados.")
        return

    v_dispo = sorted(df_base_cli["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    tax_dispo = sorted(df_base_cli["Taxonomia"].dropna().astype(str).str.strip().unique().tolist())
    
    orden_dias = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO", "SIN DÍA"]
    dias_en_datos = df_base_cli["DiaVisita"].dropna().astype(str).str.strip().unique().tolist() if "DiaVisita" in df_base_cli.columns else []
    dia_visita_dispo = [d for d in orden_dias if d in dias_en_datos]
    for d in dias_en_datos:
        if d not in dia_visita_dispo:
            dia_visita_dispo.append(d)

    col_fc1, col_fc2, col_fc3 = st.columns(3)
    with col_fc1:
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], placeholder="Seleccionar preventistas...", key="frag_ccc_vendedor")
    with col_fc2:
        tax_selec = st.multiselect("Taxonomía", options=tax_dispo, default=[], placeholder="Seleccionar taxonomías...", key="frag_ccc_taxonomia")
    with col_fc3:
        dia_visita_selec = st.multiselect("Día de Visita", options=dia_visita_dispo, default=[], placeholder="Seleccionar días de visita...", key="frag_ccc_dia_visita")

    if not v_selec:
        v_selec = v_dispo
    if not tax_selec:
        tax_selec = tax_dispo
    if not dia_visita_selec:
        dia_visita_selec = dia_visita_dispo

    mask_cli = (
        df_base_cli["Nombre"].astype(str).str.strip().isin(v_selec) &
        df_base_cli["Taxonomia"].astype(str).str.strip().isin(tax_selec) &
        df_base_cli["DiaVisita"].astype(str).str.strip().isin(dia_visita_selec)
    )

    df_cli_filtrado = df_base_cli[mask_cli].copy()

    if not df_cli_filtrado.empty:
        altas_nuevas_set_f = set(df_cli_filtrado[df_cli_filtrado["Es_Alta_Periodo"] == True]["Cliente"].dropna().tolist())
        reactivaciones_set_f = set(df_cli_filtrado[df_cli_filtrado["Es_Reactivacion"] == True]["Cliente"].dropna().tolist())
        excluidos_set_f = altas_nuevas_set_f.union(reactivaciones_set_f)

        reporte_filtrado = df_cli_filtrado.groupby(["CodVendedor", "Nombre", "SUP", "Taxonomia"], as_index=False).agg(
            Cartera_Total=("Cliente", "count"),
            Altas=("Es_Alta_Periodo", lambda x: int(x.sum())),
            Reactivaciones=("Es_Reactivacion", lambda x: int(x.sum())),
            Cartera_Neta=("Cliente", lambda x: int(len(x) - x.isin(excluidos_set_f).sum())),
            CCC=("Es_CCC", lambda x: int(x.sum()))
        )
        reporte_filtrado[["Cartera_Total", "Altas", "Reactivaciones", "Cartera_Neta", "CCC"]] = reporte_filtrado[["Cartera_Total", "Altas", "Reactivaciones", "Cartera_Neta", "CCC"]].fillna(0).astype("Int64")
        reporte_filtrado["NC"] = (reporte_filtrado["Cartera_Total"] - reporte_filtrado["CCC"]).clip(lower=0).astype("Int64")
        reporte_filtrado["% Cartera"] = (reporte_filtrado["CCC"] / reporte_filtrado["Cartera_Neta"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)

        objs_originales = reporte_ccc_base[["CodVendedor", "Taxonomia", "Objetivo_CCC"]].drop_duplicates(["CodVendedor", "Taxonomia"])
        reporte_filtrado = reporte_filtrado.merge(objs_originales, on=["CodVendedor", "Taxonomia"], how="left")
        reporte_filtrado["Objetivo_CCC"] = reporte_filtrado["Objetivo_CCC"].fillna(0).astype("Int64")
        reporte_filtrado["% Objetivo"] = (reporte_filtrado["CCC"] / reporte_filtrado["Objetivo_CCC"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)
        
        reporte_filtrado["CodVendedor"] = pd.to_numeric(reporte_filtrado["CodVendedor"], errors="coerce").astype("Int64")
        reporte_filtrado = reporte_filtrado.sort_values(by=["CodVendedor", "Taxonomia"], ascending=[True, True]).reset_index(drop=True)
    else:
        reporte_filtrado = pd.DataFrame(columns=["CodVendedor", "Nombre", "SUP", "Taxonomia", "Cartera_Total", "Altas", "Reactivaciones", "Cartera_Neta", "Objetivo_CCC", "CCC", "NC", "% Cartera", "% Objetivo"])

    tot_cartera = int(df_cli_filtrado["Cliente"].count()) if not df_cli_filtrado.empty else 0
    tot_altas = int(df_cli_filtrado["Es_Alta_Periodo"].sum()) if not df_cli_filtrado.empty and "Es_Alta_Periodo" in df_cli_filtrado.columns else 0
    tot_reactivaciones = int(df_cli_filtrado["Es_Reactivacion"].sum()) if not df_cli_filtrado.empty and "Es_Reactivacion" in df_cli_filtrado.columns else 0
    tot_neta = tot_cartera - (tot_altas + tot_reactivaciones)

    altas_react_mask = (df_cli_filtrado["Es_Alta_Periodo"] == True) | (df_cli_filtrado["Es_Reactivacion"] == True) if not df_cli_filtrado.empty else pd.Series(dtype=bool)
    neta_tax_df = df_cli_filtrado[~altas_react_mask].groupby("Taxonomia")["Cliente"].count() if not df_cli_filtrado.empty else pd.Series()
    net_a = int(neta_tax_df.get("A", 0))
    net_b = int(neta_tax_df.get("B", 0))
    net_c = int(neta_tax_df.get("C", 0))
    net_d = int(neta_tax_df.get("D", 0))

    tot_obj_val = int(reporte_filtrado["Objetivo_CCC"].sum()) if not reporte_filtrado.empty and "Objetivo_CCC" in reporte_filtrado.columns else 0
    obj_tax = reporte_filtrado.groupby("Taxonomia")["Objetivo_CCC"].sum() if not reporte_filtrado.empty else pd.Series()
    obj_a = obj_tax.get("A", 0)
    obj_b = obj_tax.get("B", 0)
    obj_c = obj_tax.get("C", 0)
    obj_d = obj_tax.get("D", 0)

    total_ccc_val = int(df_cli_filtrado["Es_CCC"].sum()) if not df_cli_filtrado.empty and "Es_CCC" in df_cli_filtrado.columns else 0
    tot_tax_ccc = df_cli_filtrado[df_cli_filtrado["Es_CCC"] == True].groupby("Taxonomia")["Cliente"].count() if not df_cli_filtrado.empty else pd.Series()
    cant_a = tot_tax_ccc.get("A", 0)
    cant_b = tot_tax_ccc.get("B", 0)
    cant_c = tot_tax_ccc.get("C", 0)
    cant_d = tot_tax_ccc.get("D", 0)

    cob_total = (total_ccc_val / tot_neta * 100) if tot_neta > 0 else 0.0

    cob_a = (cant_a / net_a * 100) if net_a > 0 else 0.0
    cob_b = (cant_b / net_b * 100) if net_b > 0 else 0.0
    cob_c = (cant_c / net_c * 100) if net_c > 0 else 0.0
    cob_d = (cant_d / net_d * 100) if net_d > 0 else 0.0

    st.markdown("""
        <style>
        hr {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            border-color: #334155 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    cols_r1 = st.columns(3)
    with cols_r1[0]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA TOTAL", f"{tot_cartera:,.0f}", "#38bdf8", "2px"), unsafe_allow_html=True)
    with cols_r1[1]:
        st.markdown(_tarjeta_metrica_compacta_html("ALTAS (NUEVOS)", f"{tot_altas:,.0f}", "#38bdf8", "2px"), unsafe_allow_html=True)
    with cols_r1[2]:
        st.markdown(_tarjeta_metrica_compacta_html("REACTIVACIONES", f"{tot_reactivaciones:,.0f}", "#38bdf8", "2px"), unsafe_allow_html=True)

    st.divider()

    cols_r2_net = st.columns(5)
    with cols_r2_net[0]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA NETA", f"{tot_neta:,.0f}", "#ffffff", "1px"), unsafe_allow_html=True)
    with cols_r2_net[1]:
        st.markdown(_tarjeta_metrica_compacta_html("NETA TAX. A", f"{net_a:,.0f}", "#ffffff", "1px"), unsafe_allow_html=True)
    with cols_r2_net[2]:
        st.markdown(_tarjeta_metrica_compacta_html("NETA TAX. B", f"{net_b:,.0f}", "#ffffff", "1px"), unsafe_allow_html=True)
    with cols_r2_net[3]:
        st.markdown(_tarjeta_metrica_compacta_html("NETA TAX. C", f"{net_c:,.0f}", "#ffffff", "1px"), unsafe_allow_html=True)
    with cols_r2_net[4]:
        st.markdown(_tarjeta_metrica_compacta_html("NETA TAX. D", f"{net_d:,.0f}", "#ffffff", "1px"), unsafe_allow_html=True)

    st.divider()

    cols_obj = st.columns(5)
    with cols_obj[0]:
        st.markdown(_tarjeta_metrica_compacta_html("OBJETIVO TOTAL", f"{tot_obj_val:,.0f}", "#3b82f6", "1px"), unsafe_allow_html=True)
    with cols_obj[1]:
        st.markdown(_tarjeta_metrica_compacta_html("OBJETIVO TAX. A", f"{obj_a:,.0f}", "#ef4444", "1px"), unsafe_allow_html=True)
    with cols_obj[2]:
        st.markdown(_tarjeta_metrica_compacta_html("OBJETIVO TAX. B", f"{obj_b:,.0f}", "#f97316", "1px"), unsafe_allow_html=True)
    with cols_obj[3]:
        st.markdown(_tarjeta_metrica_compacta_html("OBJETIVO TAX. C", f"{obj_c:,.0f}", "#eab308", "1px"), unsafe_allow_html=True)
    with cols_obj[4]:
        st.markdown(_tarjeta_metrica_compacta_html("OBJETIVO TAX. D", f"{obj_d:,.0f}", "#22c55e", "1px"), unsafe_allow_html=True)

    cols_r2 = st.columns(5)
    with cols_r2[0]:
        st.markdown(_tarjeta_metrica_compacta_html("TOTAL CCC", f"{total_ccc_val:,.0f}", "#3b82f6", "1px"), unsafe_allow_html=True)
    with cols_r2[1]:
        st.markdown(_tarjeta_metrica_compacta_html("CCC TAX. A", f"{cant_a:,.0f}", "#ef4444", "1px"), unsafe_allow_html=True)
    with cols_r2[2]:
        st.markdown(_tarjeta_metrica_compacta_html("CCC TAX. B", f"{cant_b:,.0f}", "#f97316", "1px"), unsafe_allow_html=True)
    with cols_r2[3]:
        st.markdown(_tarjeta_metrica_compacta_html("CCC TAX. C", f"{cant_c:,.0f}", "#eab308", "1px"), unsafe_allow_html=True)
    with cols_r2[4]:
        st.markdown(_tarjeta_metrica_compacta_html("CCC TAX. D", f"{cant_d:,.0f}", "#22c55e", "1px"), unsafe_allow_html=True)

    cols_r3 = st.columns(5)
    with cols_r3[0]:
        st.markdown(_tarjeta_metrica_compacta_html("% CARTERA TOTAL", f"{cob_total:,.2f}%", "#3b82f6", "1px"), unsafe_allow_html=True)
    with cols_r3[1]:
        st.markdown(_tarjeta_metrica_compacta_html("% CARTERA A", f"{cob_a:,.2f}%", "#ef4444", "1px"), unsafe_allow_html=True)
    with cols_r3[2]:
        st.markdown(_tarjeta_metrica_compacta_html("% CARTERA B", f"{cob_b:,.2f}%", "#f97316", "1px"), unsafe_allow_html=True)
    with cols_r3[3]:
        st.markdown(_tarjeta_metrica_compacta_html("% CARTERA C", f"{cob_c:,.2f}%", "#eab308", "1px"), unsafe_allow_html=True)
    with cols_r3[4]:
        st.markdown(_tarjeta_metrica_compacta_html("% CARTERA D", f"{cob_d:,.2f}%", "#22c55e", "1px"), unsafe_allow_html=True)

    st.divider()

    columnas_visuales_ccc = [
        "CodVendedor", "Nombre", "SUP", "Taxonomia", 
        "Cartera_Total", "Altas", "Reactivaciones", "Cartera_Neta", 
        "Objetivo_CCC", "CCC", "NC", "% Cartera", "% Objetivo"
    ]
    reporte_render = reporte_filtrado[columnas_visuales_ccc].copy().reset_index(drop=True)

    reporte_render_excel = reporte_render.copy()
    reporte_render_display = reporte_render.copy()

    cols_porc_ccc = ["% Cartera", "% Objetivo"]
    for col in cols_porc_ccc:
        if col in reporte_render_display.columns:
            reporte_render_display[col] = reporte_render_display[col].apply(lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%")

    if not reporte_render_display.empty:
        gb = GridOptionsBuilder.from_dataframe(reporte_render_display)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=120)
        
        gb.configure_column("CodVendedor", headerName="Cód. Vend", width=90, valueFormatter="x != null ? Number(x).toFixed(0) : ''")
        gb.configure_column("Nombre", headerName="Preventista", minWidth=160)
        gb.configure_column("SUP", headerName="SUP", width=75)
        gb.configure_column("Taxonomia", headerName="Tax", width=70)
        gb.configure_column("Cartera_Total", headerName="Cartera Total", width=100)
        gb.configure_column("Altas", headerName="Altas", width=70)
        gb.configure_column("Reactivaciones", headerName="Reactiv.", width=90)
        gb.configure_column("Cartera_Neta", headerName="Cartera Neta", width=100)
        gb.configure_column("Objetivo_CCC", headerName="Objetivo CCC", width=105)
        gb.configure_column("CCC", headerName="CCC", width=80)
        gb.configure_column("NC", headerName="NC", width=80)
        
        gb.configure_column("% Cartera", headerName="% Cartera", width=100)
        gb.configure_column("% Objetivo", headerName="% Objetivo", width=110)
        
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
            fit_columns_on_grid_load=False
        )
    else:
        st.info("No se encontraron registros de Clientes con Compra con los filtros seleccionados.")

    st.divider()

    st.markdown("### ⚔️ Batalla NC: Listado de Clientes No Compradores")
    st.markdown("Detalle de clientes sin compra en el período, filtrados por los criterios activos del reporte superior.")

    if not df_cli_filtrado.empty:
        df_nc = df_cli_filtrado[df_cli_filtrado["Es_CCC"] == False].copy()
        
        cols_disponibles = df_nc.columns.tolist()
        map_cols = {}
        for col in cols_disponibles:
            cl = col.lower()
            if cl in ["cliente", "codcliente", "codigo"]: map_cols["Cliente"] = col
            elif cl in ["nombrecliente", "nombre_cliente", "razonsocial"]: map_cols["NombreCliente"] = col
            elif cl in ["direccioncliente", "direccion", "domicilio"]: map_cols["DireccionCliente"] = col
            elif cl in ["diavisita", "dia_visita", "ruta"]: map_cols["DiaVisita"] = col
            elif cl in ["nombre", "preventista", "vendedor"]: map_cols["Vendedor"] = col
            elif cl in ["taxonomia", "taxonomía"]: map_cols["Taxonomia"] = col

        df_nc_escueto = pd.DataFrame()
        df_nc_escueto["Código Cliente"] = df_nc.get(map_cols.get("Cliente", "Cliente"), pd.Series())
        df_nc_escueto["Razón Social"] = df_nc.get(map_cols.get("NombreCliente", "NombreCliente"), pd.Series())
        df_nc_escueto["Dirección"] = df_nc.get(map_cols.get("DireccionCliente", "DireccionCliente"), pd.Series())
        df_nc_escueto["Día Visita"] = df_nc.get(map_cols.get("DiaVisita", "DiaVisita"), pd.Series())
        df_nc_escueto["Taxonomía"] = df_nc.get(map_cols.get("Taxonomia", "Taxonomia"), pd.Series())
        df_nc_escueto["Preventista"] = df_nc.get(map_cols.get("Vendedor", "Nombre"), pd.Series())

        df_nc_render = df_nc_escueto.dropna(how="all").reset_index(drop=True)
    else:
        df_nc_render = pd.DataFrame(columns=["Código Cliente", "Razón Social", "Dirección", "Día Visita", "Taxonomía", "Preventista"])

    if not df_nc_render.empty:
        st.dataframe(df_nc_render, width="stretch", height=350, hide_index=True)
    else:
        st.info("No hay clientes no compradores (NC) para los filtros seleccionados.")

    st.divider()

    col_dl1, col_dl2, col_dl3 = st.columns(3)
    with col_dl1:
        buffer_ccc = io.BytesIO()
        with pd.ExcelWriter(buffer_ccc, engine="openpyxl") as writer:
            reporte_render_excel.to_excel(writer, index=False, sheet_name="Avance_Clientes_Con_Compra")
        buffer_ccc.seek(0)
        st.download_button(
            label="📥 Descargar Avance a Excel",
            data=buffer_ccc,
            file_name="Avance_Clientes_Con_Compra.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="ccc_frag_btn_dl"
        )

    with col_dl2:
        buffer_nc = io.BytesIO()
        with pd.ExcelWriter(buffer_nc, engine="openpyxl") as writer:
            df_nc_render.to_excel(writer, index=False, sheet_name="Clientes_No_Compradores_NC")
        buffer_nc.seek(0)
        st.download_button(
            label="📥 Descargar Clientes NC a Excel",
            data=buffer_nc,
            file_name="Clientes_No_Compradores_NC.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="nc_frag_btn_dl"
        )

    with col_dl3:
        if not df_cli_filtrado.empty:
            df_nc_wa = df_cli_filtrado[df_cli_filtrado["Es_CCC"] == False].copy()
            
            cols_disponibles = df_nc_wa.columns.tolist()
            map_cols = {}
            for col in cols_disponibles:
                cl = col.lower()
                if cl in ["cliente", "codcliente", "codigo"]: map_cols["Cliente"] = col
                elif cl in ["nombrecliente", "nombre_cliente", "razonsocial"]: map_cols["NombreCliente"] = col
                elif cl in ["direccioncliente", "direccion", "domicilio"]: map_cols["DireccionCliente"] = col
                elif cl in ["diavisita", "dia_visita", "ruta"]: map_cols["DiaVisita"] = col

            lista_nc_formateada = []
            for idx, row in df_nc_wa.iterrows():
                cli = row.get(map_cols.get("Cliente", "Cliente"), "")
                nom = row.get(map_cols.get("NombreCliente", "NombreCliente"), "")
                dir_c = row.get(map_cols.get("DireccionCliente", "DireccionCliente"), "")
                dia = row.get(map_cols.get("DiaVisita", "DiaVisita"), "")
                
                lista_nc_formateada.append(f"[{cli}] {nom} - {dir_c} - {dia}")

            detalle_texto = "%0A".join(lista_nc_formateada)
            total_nc_cnt = len(df_nc_wa)
            
            texto_wa = f"NC:{total_nc_cnt}%0A{detalle_texto}"
            url_wa = f"https://wa.me/?text={texto_wa}"
            
            st.markdown(f'''
                <div style="display: flex; justify-content: center; align-items: center; height: 100%; padding-top: 5px;">
                    <a href="{url_wa}" target="_blank" style="
                        display: inline-block;
                        padding: 4px 10px;
                        background-color: #25d366;
                        color: white;
                        text-align: center;
                        text-decoration: none;
                        font-weight: 600;
                        font-size: 0.75rem;
                        border-radius: 4px;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    ">💬 WhatsApp NC</a>
                </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('<div style="padding:0.5rem;text-align:center;color:#94a3b8;font-size:0.85rem;">Sin datos para WhatsApp</div>', unsafe_allow_html=True)

def render_rep_ccc(df_vta, df_universo, filtros_globales=None):
    st.subheader("📊 Avance de Clientes con Compra (CCC) por Taxonomía")
    st.markdown("Analiza la cobertura de Clientes con Compra (CCC) segmentada por taxonomía, vendedor y día de visita sobre el universo de cartera.")

    sup_filtro = "TODOS"
    if filtros_globales and isinstance(filtros_globales, dict):
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    except Exception:
        maestro_v = pd.DataFrame()

    try:
        maestro_ccc_param = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
    except Exception:
        maestro_ccc_param = pd.DataFrame(columns=["Taxonomia", "Porcentaje_Cartera"])

    reporte_base = generar_reporte_ccc_taxonomia(df_vta, df_universo, maestro_v, maestro_ccc_param, filtros_globales)
    sups_sel = [sup_filtro] if sup_filtro != "TODOS" else None

    render_fragmento_interactivo_ccc(reporte_base, sups_sel)

====================================================================================================


### ARCHIVO: modules\rep_cob_innovacion.py

# modules/rep_cob_innovacion.py
import io
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode
from modules import database as db
from modules.utils import parsear_fecha_robusta, extraer_dia_de_ruta_vectorial, tarjeta_metrica_html

def preparar_ventas_cobertura_innovacion(df_vta, anio_operativo, mes_operativo, dia_matinal):
    """
    Pipeline de ventas optimizado para Cobertura por Innovaciones derivado del DataFrame Maestro N1 (EMPLEADOS).
    Aplica los filtros N2: PEPSICO, COMODATOS y PERIODO.
    """
    # Nivel 1: Obtención del DataFrame corporativo base con filtro EMPLEADOS aplicado
    df_corp = db.obtener_df_maestro_corporativo()
    df = df_corp.copy() if not df_corp.empty else (df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame())
    
    if df.empty:
        return df

    col_cant = next((c for c in ["CantBase", "CANTBASE", "Cantidad", "CANTIDAD", "Unidades", "UNIDADES"] if c in df.columns), df.columns[0])
    df["cantbase"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0.0)

    # Nivel 2: Filtro COMODATOS (Exclusión de comodatos y préstamos)
    if "TipoDeVenta" in df.columns:
        tipos_excluidos = [
            "Comodato Devolución", 
            "Comodato Ficticio", 
            "Comodato Ficticio Devolución", 
            "Comodato Préstamo"
        ]
        df = df[~df["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)]

    # Nivel 2: Filtro PEPSICO (Selección exclusiva de proveedor PepsiCo)
    if "Proveedor" in df.columns:
        df = df[
            df["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    col_vend_tit = next((cand for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"] if cand in df.columns), "CodVendedor")
    df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype("Int64")

    col_prod_tit = next((cand for cand in ["Codigo", "CodArticulo", "Cod_Articulo", "Articulo", "CODIGO"] if cand in df.columns), None)
    if col_prod_tit:
        df["Codigo_Prod"] = pd.to_numeric(df[col_prod_tit], errors="coerce").astype("Int64")
    else:
        df["Codigo_Prod"] = pd.Series(dtype="Int64")

    df["MesCarga"] = df["FechaCarga_dt"].dt.month
    df["AñoCarga"] = df["FechaCarga_dt"].dt.year
    df["MesEntrega"] = df["FechaEntrega_dt"].dt.month
    df["AñoEntrega"] = df["FechaEntrega_dt"].dt.year

    mes_ant = 12 if mes_operativo == 1 else mes_operativo - 1
    anio_ant = anio_operativo - 1 if mes_operativo == 1 else anio_operativo

    mes_sig = 1 if mes_operativo == 12 else mes_operativo + 1
    anio_sig = anio_operativo + 1 if mes_operativo == 12 else anio_operativo

    ac, mc = df["AñoCarga"], df["MesCarga"]
    ae, me = df["AñoEntrega"], df["MesEntrega"]
    
    cond_arr = (ac == anio_ant) & (mc == mes_ant) & (ae == anio_operativo) & (me == mes_operativo)
    cond_act = (ac == anio_operativo) & (mc == mes_operativo) & (ae == anio_operativo) & (me == mes_operativo)
    cond_fut = (ac == anio_operativo) & (mc == mes_operativo) & (ae == anio_sig) & (me == mes_sig)

    # Nivel 2: Filtro PERIODO (Clasificación de transacciones en Arrastre, Actual o Futuro)
    df["Periodo"] = np.select(
        [cond_arr, cond_act, cond_fut],
        ["Arrastre", "Actual", "Futuro"],
        default="Fuera de Periodo"
    )
    return df

def _calcular_base_cobertura_innovacion(df_vtas_operativo, df_cartera, vendedores, anio_op, mes_op, dia_matinal):
    """Motor de cálculo base de Cobertura por Innovaciones optimizado."""
    df_vta_prep = preparar_ventas_cobertura_innovacion(df_vtas_operativo, anio_op, mes_op, dia_matinal)

    df_vend = vendedores.copy() if vendedores is not None and not vendedores.empty else pd.DataFrame(columns=["CodVend", "Nombre", "SUP"])
    col_cod_v = next((c for c in ["CodVend", "Codigo_Vendedor", "CodVendedor"] if c in df_vend.columns), df_vend.columns[0])
    col_nom_v = next((c for c in df_vend.columns if "nombre" in str(c).strip().lower()), df_vend.columns[1] if len(df_vend.columns) > 1 else df_vend.columns[0])
    col_sup_v = next((c for c in df_vend.columns if "sup" in str(c).strip().lower() or "supervisor" in str(c).strip().lower()), df_vend.columns[2] if len(df_vend.columns) > 2 else df_vend.columns[0])
    
    df_vend = df_vend.rename(columns={col_cod_v: "CodVendedor", col_nom_v: "Nombre", col_sup_v: "SUP"})
    df_vend["CodVendedor"] = pd.to_numeric(df_vend["CodVendedor"], errors="coerce").astype("Int64")
    df_vend = df_vend[~df_vend["CodVendedor"].isin([20, 99])].drop_duplicates(subset=["CodVendedor"])

    df_innov_master = db.cargar_tabla_sql(f"SELECT * FROM maestro_innovaciones WHERE Anio = {anio_op} AND Mes = {mes_op}")
    if df_innov_master.empty:
        df_innov_master = db.cargar_tabla_sql("SELECT * FROM maestro_innovaciones")

    innovaciones_lista = []
    mapa_codigo_a_innovacion = {}
    if not df_innov_master.empty and "Innovacion" in df_innov_master.columns and "Codigo" in df_innov_master.columns:
        df_innov_master["Innovacion"] = df_innov_master["Innovacion"].astype(str).str.strip().str.upper()
        df_innov_master["Codigo"] = pd.to_numeric(df_innov_master["Codigo"], errors="coerce").astype("Int64")
        
        innovaciones_lista = sorted(df_innov_master["Innovacion"].unique().tolist())
        for _, row in df_innov_master.iterrows():
            cod = row.get("Codigo")
            inv = row.get("Innovacion")
            if pd.notna(cod) and inv:
                mapa_codigo_a_innovacion[int(cod)] = inv

    vtas = df_vta_prep[df_vta_prep["Periodo"].isin(["Arrastre", "Actual"])].copy() if not df_vta_prep.empty and "Periodo" in df_vta_prep.columns else pd.DataFrame()

    cartera = df_cartera.copy() if df_cartera is not None and not df_cartera.empty else pd.DataFrame()
    
    if not cartera.empty:
        cols_c_str = [str(c).strip().lower() for c in cartera.columns]
        
        col_prov_c = next((cartera.columns[i] for i, c in enumerate(cols_c_str) if c in ["proveedor", "fabricante", "empresa"]), None)
        if col_prov_c:
            cartera = cartera[cartera[col_prov_c].astype(str).str.contains("pepsico", case=False, na=False)].copy()
            
        subramo_col = next((c for c in cartera.columns if "subramo" in str(c).lower()), None)
        if subramo_col:
            cartera = cartera[cartera[subramo_col].fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()
            
        tax_col = next((c for c in cartera.columns if "taxonomia" in str(c).lower() or "segmentoclientecodigo" in str(c).lower()), None)
        if tax_col:
            cartera["Taxonomia"] = cartera[tax_col].astype(str).str.strip().str.upper()
            cartera = cartera[cartera["Taxonomia"].isin(["A", "B", "C", "D"])].copy()
            
        posibles_vend = ["codvendedor", "codvend", "vendedor", "vend", "cod_vend", "cod_vendedor", "nrovendedor"]
        enc_vend_c = next((cartera.columns[i] for i, c in enumerate(cols_c_str) if c in posibles_vend), None)
        
        if enc_vend_c:
            cartera["CodVendedor"] = pd.to_numeric(cartera[enc_vend_c], errors="coerce").astype("Int64")
        elif len(cartera.columns) > 0:
            cartera["CodVendedor"] = pd.to_numeric(cartera.iloc[:, 0], errors="coerce").astype("Int64")
            
        col_cod_cliente_c = next((c for c in cartera.columns if "cliente" in c.lower() or "nro" in c.lower() or "codigo" in c.lower()), cartera.columns[0])
        cartera["Cliente_Cod"] = pd.to_numeric(cartera[col_cod_cliente_c], errors="coerce").astype("Int64")
        
        col_desc_cliente = next((c for c in cartera.columns if any(k in c.lower() for k in ["razon", "nombre", "desc", "cliente"]) and c != col_cod_cliente_c), None)
        if col_desc_cliente is None:
            col_desc_cliente = col_cod_cliente_c
        cartera["Cliente_Desc"] = cartera[col_desc_cliente].fillna("").astype(str)

        col_dir_c = next((c for c in cartera.columns if any(k in c.lower() for k in ["dir", "domicilio", "direccion"])), None)
        cartera["Cliente_Dir"] = cartera[col_dir_c].fillna("").astype(str) if col_dir_c else ""

        col_ruta_c = next((c for c in cartera.columns if str(c).strip().lower() in ["ruta", "dia_visita", "visita", "dia"]), None)
        if col_ruta_c is not None:
            cartera["DiaVisita"] = extraer_dia_de_ruta_vectorial(cartera[col_ruta_c])
        else:
            cartera["DiaVisita"] = "SIN DÍA"

        cartera = cartera.dropna(subset=["CodVendedor", "Cliente_Cod"]).drop_duplicates(subset=["CodVendedor", "Cliente_Cod"])
        cartera = cartera.merge(df_vend[["CodVendedor", "Nombre", "SUP"]], on="CodVendedor", how="inner")

    cliente_col_vtas = next((c for c in ["Cliente", "NroCliente", "CodCliente", "CLIENTE"] if not vtas.empty and c in vtas.columns), "Cliente")

    if not vtas.empty and mapa_codigo_a_innovacion:
        vtas["CodVendedor"] = pd.to_numeric(vtas["CodVendedor"], errors="coerce").astype("Int64")
        vtas["Cliente"] = pd.to_numeric(vtas[cliente_col_vtas], errors="coerce").astype("Int64")
        vtas["Codigo_Prod"] = pd.to_numeric(vtas["Codigo_Prod"], errors="coerce").astype("Int64")

        vtas = vtas[vtas["Codigo_Prod"].isin(mapa_codigo_a_innovacion.keys())].copy()
        vtas["Innovacion"] = vtas["Codigo_Prod"].map(mapa_codigo_a_innovacion)

        # Nivel 2: Filtro COBERTURA (Valida unidades compradas cantbase >= 3 agrupadas por innovación)
        vtas_agrupadas = vtas.groupby(["CodVendedor", "Cliente", "Innovacion"], as_index=False).agg(
            Total_Cant=("cantbase", "sum")
        )
    else:
        vtas_agrupadas = pd.DataFrame(columns=["CodVendedor", "Cliente", "Innovacion", "Total_Cant"])

    return cartera, vtas_agrupadas, innovaciones_lista, df_innov_master

@st.cache_data(show_spinner=False)
def _calcular_base_cob_innovacion_cached(df_vtas_operativo, df_cartera, vendedores, anio_op, mes_op, dia_matinal, huella_datos):
    return _calcular_base_cobertura_innovacion(df_vtas_operativo, df_cartera, vendedores, anio_op, mes_op, dia_matinal)

def generar_reporte_cobertura_innovacion(df_vtas_operativo, df_cartera, vendedores, filtros_globales=None):
    if filtros_globales:
        anio_op = int(filtros_globales.get("anio", 2026))
        mes_op = int(filtros_globales.get("mes", 9))
        dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026")
    else:
        df_params = db.cargar_tabla_sql("SELECT * FROM parametros")
        params_map = {}
        if not df_params.empty and "PARAMETRO" in df_params.columns and "VALOR" in df_params.columns:
            params_map = dict(zip(df_params["PARAMETRO"], df_params["VALOR"]))

        anio_op = int(st.session_state.get("sel_anio_op", params_map.get("Año", 2026)))
        mes_op = int(st.session_state.get("sel_mes_op", params_map.get("Mes", 9)))
        
        dia_matinal_default = params_map.get("Dia Matinal", "02/09/2026")
        dia_matinal_obj = st.session_state.get("sel_dia_matinal", dia_matinal_default)
        dia_matinal = dia_matinal_obj.strftime("%d/%m/%Y") if hasattr(dia_matinal_obj, "strftime") else str(dia_matinal_obj)

    huella_datos = f"{len(df_vtas_operativo) if df_vtas_operativo is not None else 0}_{len(df_cartera) if df_cartera is not None else 0}_{anio_op}_{mes_op}_{dia_matinal}"

    cartera, vtas_agrupadas, innovaciones_lista, df_innov_master = _calcular_base_cob_innovacion_cached(
        df_vtas_operativo, df_cartera, vendedores, anio_op, mes_op, dia_matinal, huella_datos
    )

    st.session_state["_cob_innov_cartera_base"] = cartera
    st.session_state["_cob_innov_vtas_agrupadas"] = vtas_agrupadas
    st.session_state["_cob_innov_lista"] = innovaciones_lista
    st.session_state["_cob_innov_master"] = df_innov_master

    return pd.DataFrame(), innovaciones_lista, df_innov_master

@st.fragment
def render_fragmento_interactivo_cobertura_innovacion(reporte_dummy, innovaciones_param, df_innov_master_param, supervisores_seleccionados):
    cartera_base = st.session_state.get("_cob_innov_cartera_base", pd.DataFrame())
    vtas_agrup = st.session_state.get("_cob_innov_vtas_agrupadas", pd.DataFrame())
    innovaciones = st.session_state.get("_cob_innov_lista", innovaciones_param)

    if cartera_base.empty:
        st.info("No hay datos de cartera disponibles para procesar la Cobertura por Innovaciones.")
        return

    if not innovaciones:
        st.warning("⚠️ No se encontraron registros en el 'Maestro de Innovaciones' para el período actual. Por favor, cargue el maestro desde la sección de **Parámetros**.")
        return

    sup_str = [str(s).strip() for s in supervisores_seleccionados]
    cartera_filtrada = cartera_base[cartera_base["SUP"].astype(str).str.strip().isin(sup_str)].copy() if sup_str and "SUP" in cartera_base.columns else cartera_base.copy()

    if cartera_filtrada.empty:
        st.info("No se encontraron registros para los supervisores seleccionados.")
        return

    v_dispo = sorted(cartera_filtrada["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    orden_dias = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO", "SIN DÍA"]
    dias_en_datos = cartera_filtrada["DiaVisita"].dropna().astype(str).str.strip().unique().tolist() if "DiaVisita" in cartera_filtrada.columns else []
    dia_visita_dispo = [d for d in orden_dias if d in dias_en_datos]
    for d in dias_en_datos:
        if d not in dia_visita_dispo:
            dia_visita_dispo.append(d)

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], placeholder="Seleccionar preventistas...", key="frag_innov_vendedor")
    with col_f2:
        i_selec = st.multiselect("Innovación", options=innovaciones, default=[], placeholder="Seleccionar innovaciones...", key="frag_innov_marca")
    with col_f3:
        dia_visita_selec = st.multiselect("Día de Visita", options=dia_visita_dispo, default=[], placeholder="Seleccionar días de visita...", key="frag_innov_dia_visita")

    if not v_selec:
        v_selec = v_dispo
    if not i_selec:
        i_selec = innovaciones
    if not dia_visita_selec:
        dia_visita_selec = dia_visita_dispo

    mask_cartera = (
        cartera_filtrada["Nombre"].astype(str).str.strip().isin(v_selec) &
        cartera_filtrada["DiaVisita"].astype(str).str.strip().isin(dia_visita_selec)
    )
    cartera_activa = cartera_filtrada[mask_cartera].copy()

    if cartera_activa.empty:
        st.info("No se encontraron clientes para los filtros seleccionados.")
        return

    cartera_por_vendedor = cartera_activa.groupby(["CodVendedor", "Nombre", "SUP"], as_index=False).agg(
        Cartera=("Cliente_Cod", "nunique")
    )

    clientes_activos = set(cartera_activa["Cliente_Cod"].unique())
    
    vtas_activas = vtas_agrup[
        vtas_agrup["Cliente"].isin(clientes_activos) &
        vtas_agrup["Innovacion"].isin(i_selec) &
        vtas_agrup["Total_Cant"].ge(3.0)
    ].copy() if not vtas_agrup.empty else pd.DataFrame()

    if not vtas_activas.empty:
        cubiertos_pivot = vtas_activas.groupby(["CodVendedor", "Innovacion"])["Cliente"].nunique().unstack(fill_value=0).reset_index()
        cubiertos_pivot.columns.name = None
    else:
        cubiertos_pivot = pd.DataFrame(columns=["CodVendedor"])

    reporte_matriz = cartera_por_vendedor.merge(cubiertos_pivot, on="CodVendedor", how="left")

    for inv in i_selec:
        if inv not in reporte_matriz.columns:
            reporte_matriz[inv] = 0.0
        else:
            reporte_matriz[inv] = reporte_matriz[inv].fillna(0.0)
            
        total_c = reporte_matriz["Cartera"].replace(0, pd.NA)
        reporte_matriz[inv] = ((reporte_matriz[inv] / total_c).fillna(0.0) * 100.0).round(2)

    reporte_matriz = reporte_matriz.sort_values(by="CodVendedor").reset_index(drop=True)

    suma_cartera_global = reporte_matriz["Cartera"].sum()
    i_selec_ordenadas = [inv for inv in innovaciones if inv in i_selec]

    if i_selec_ordenadas:
        cols_obj_ui = st.columns(min(len(i_selec_ordenadas), 5))
        for idx, inv in enumerate(i_selec_ordenadas):
            col_target = cols_obj_ui[idx % len(cols_obj_ui)]
            obj_val = 80.0
            
            if suma_cartera_global > 0 and inv in reporte_matriz.columns:
                cubiertos_totales = (reporte_matriz[inv] / 100.0 * reporte_matriz["Cartera"]).sum()
                cobertura_global_pct = (cubiertos_totales / suma_cartera_global) * 100.0
            else:
                cobertura_global_pct = 0.0
                
            color_borde = "#64748b"
            alcanzado = cobertura_global_pct >= obj_val
            color_valor = "#22c55e" if alcanzado else "#ef4444"
            
            with col_target:
                titulo_tarjeta = f"<span style='color: #ffffff; font-weight: 700;'>{inv} (OBJ: {obj_val:g}%)</span>"
                st.markdown(tarjeta_metrica_html(titulo_tarjeta, f"{cobertura_global_pct:.2f}%", color_borde, "1.4rem", "0.95rem", color_valor=color_valor), unsafe_allow_html=True)
            
        st.divider()

    columnas_finales = ["CodVendedor", "Nombre", "Cartera", "SUP"] + [inv for inv in i_selec_ordenadas if inv in reporte_matriz.columns]
    df_render = reporte_matriz[columnas_finales].copy()

    df_render_excel = df_render.copy()
    df_render_display = df_render.copy()
    for inv in i_selec_ordenadas:
        if inv in df_render_display.columns:
            df_render_display[inv] = df_render_display[inv].apply(lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%")

    if not df_render_display.empty:
        gb = GridOptionsBuilder.from_dataframe(df_render_display)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, flex=1, minWidth=130, cellStyle={'textAlign': 'center'}, headerClass='centered-header')
        gb.configure_column("CodVendedor", headerName="Cód. Vend", flex=0, width=105, minWidth=105)
        gb.configure_column("Nombre", headerName="Nombre", flex=2, minWidth=220, cellStyle={'textAlign': 'left'}, headerClass='left-header')
        gb.configure_column("Cartera", headerName="Cartera", flex=0, width=100, minWidth=100)
        gb.configure_column("SUP", headerName="SUP", flex=0, width=85, minWidth=85)
        
        cell_style_conditional = JsCode("""
        function(params) {
            const objetivo = 80.0;
            const valorReal = Number(params.value) || 0;
            if (valorReal >= objetivo) {
                return {'backgroundColor': '#d4edda', 'fontWeight': 'bold', 'color': '#155724', 'textAlign': 'center'};
            } else {
                return {'backgroundColor': '#f8d7da', 'fontWeight': 'bold', 'color': '#721c24', 'textAlign': 'center'};
            }
        }
        """)

        for inv in i_selec_ordenadas:
            if inv in df_render_display.columns:
                gb.configure_column(
                    inv,
                    headerName=inv,
                    flex=1,
                    minWidth=150,
                    cellStyle=cell_style_conditional
                )
                
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_options = gb.build()
        
        st.markdown("""
        <style>
        .ag-header-cell-label {
            justify-content: center !important;
            text-align: center !important;
        }
        .left-header .ag-header-cell-label {
            justify-content: flex-start !important;
            text-align: left !important;
        }
        </style>
        """, unsafe_allow_html=True)

        AgGrid(
            df_render_display,
            gridOptions=grid_options,
            height=400,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True
        )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_render_excel.to_excel(writer, index=False, sheet_name="Cob_Innovacion")
    buffer.seek(0)
    
    st.download_button(
        label="📥 Descargar Cobertura por Innovaciones a Excel",
        data=buffer,
        file_name="Cobertura_Por_Innovacion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="cob_innov_btn_dl"
    )

    st.markdown("### ⚔️ Clientes No Cubiertos por Innovación")
    st.markdown("Clientes activos en cartera que no alcanzan el umbral mínimo acumulado de 3 unidades en las innovaciones seleccionadas.")

    ventas_unidades_map = vtas_agrup.set_index(["CodVendedor", "Cliente", "Innovacion"])["Total_Cant"].to_dict() if not vtas_agrup.empty else {}

    registros_nc = []
    for inv in i_selec_ordenadas:
        for row in cartera_activa.itertuples(index=False):
            cv = int(row.CodVendedor)
            cli = int(row.Cliente_Cod)
            und = ventas_unidades_map.get((cv, cli, inv), 0.0)
            if und < 3.0:
                registros_nc.append({
                    "Vendedor": row.Nombre,
                    "Cód. Cliente": cli,
                    "Cliente": row.Cliente_Desc,
                    "Dirección": row.Cliente_Dir,
                    "Día Visita": row.DiaVisita,
                    "Innovación": inv,
                    "Unidades": und,
                    "Estado": "No Cubierto (< 3 u.)"
                })

    df_det_view = pd.DataFrame(registros_nc)
    total_registros_batalla = len(df_det_view)
    st.caption(f"📊 Registros encontrados: **{total_registros_batalla}**")

    if not df_det_view.empty:
        gb_batalla = GridOptionsBuilder.from_dataframe(df_det_view)
        gb_batalla.configure_default_column(filterable=True, sortable=True, resizable=True, flex=1, minWidth=130, cellStyle={'textAlign': 'center'}, headerClass='centered-header')
        gb_batalla.configure_column("Vendedor", headerName="Vendedor", flex=2, minWidth=180, cellStyle={'textAlign': 'left'}, headerClass='left-header')
        gb_batalla.configure_column("Cliente", headerName="Cliente", flex=2, minWidth=190, cellStyle={'textAlign': 'left'}, headerClass='left-header')
        gb_batalla.configure_column("Dirección", headerName="Dirección", flex=2, minWidth=180, cellStyle={'textAlign': 'left'}, headerClass='left-header')
        gb_batalla.configure_column("Cód. Cliente", headerName="Cód. Cliente", flex=0, width=115, minWidth=115)
        gb_batalla.configure_column("Día Visita", headerName="Día Visita", flex=0, width=115, minWidth=115)
        gb_batalla.configure_column("Innovación", headerName="Innovación", flex=1, minWidth=140)
        gb_batalla.configure_column("Unidades", headerName="Unidades", flex=0, width=105, minWidth=105, valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0,00'")
        gb_batalla.configure_column("Estado", headerName="Estado", flex=0, width=150, minWidth=150)
        
        gb_batalla.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_options_batalla = gb_batalla.build()

        AgGrid(
            df_det_view,
            gridOptions=grid_options_batalla,
            height=400,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True
        )

        col_dl1, col_dl2, col_dl3 = st.columns(3)
        with col_dl1:
            buffer_batalla = io.BytesIO()
            with pd.ExcelWriter(buffer_batalla, engine="openpyxl") as writer:
                df_det_view.to_excel(writer, index=False, sheet_name="No_Cubiertos_Innovacion")
            buffer_batalla.seek(0)

            st.download_button(
                label="📥 Descargar Clientes No Cubiertos a Excel",
                data=buffer_batalla,
                file_name="Clientes_No_Cubiertos_Innovacion.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_dl_innov_nc"
            )

        with col_dl2:
            pass

        with col_dl3:
            df_wa_limit = df_det_view.head(30)
            lista_nc_formateada = []
            for idx, row in df_wa_limit.iterrows():
                cli = row.get("Cód. Cliente", "")
                nom = row.get("Cliente", "")
                dir_c = row.get("Dirección", "")
                dia_v = row.get("Día Visita", "")
                inv_c = row.get("Innovación", "")
                und = row.get("Unidades", 0.0)
                lista_nc_formateada.append(f"[{cli}] {nom} - {dir_c} - {dia_v} - Innovación: {inv_c} (U: {und:,.2f})")

            detalle_texto = "%0A".join(lista_nc_formateada)
            aviso_limite = f"%0A(Mostrando 30 de {total_registros_batalla} en WA)" if total_registros_batalla > 30 else ""
            texto_wa = f"NC Innovación:{total_registros_batalla}%0A{detalle_texto}{aviso_limite}"
            url_wa = f"https://wa.me/?text={texto_wa}"
            
            st.markdown(f'''
                <div style="display: flex; justify-content: center; align-items: center; height: 100%; padding-top: 5px;">
                    <a href="{url_wa}" target="_blank" style="
                        display: inline-block;
                        padding: 4px 10px;
                        background-color: #25d366;
                        color: white;
                        text-align: center;
                        text-decoration: none;
                        font-weight: 600;
                        font-size: 0.75rem;
                        border-radius: 4px;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    ">💬 WhatsApp NC</a>
                </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("No se registran clientes sin cobertura para los filtros seleccionados.")

def dibujar_pestana_cobertura_innovacion(reporte_innovacion, innovaciones_lista, df_innov_master, supervisores_seleccionados):
    st.subheader("🚀 Cobertura Por Innovación y Detalle de Clientes")
    sup_sel_efectivo = supervisores_seleccionados if isinstance(supervisores_seleccionados, list) else [supervisores_seleccionados]
    render_fragmento_interactivo_cobertura_innovacion(reporte_innovacion, innovaciones_lista, df_innov_master, sup_sel_efectivo)

====================================================================================================


### ARCHIVO: modules\rep_cob_marca.py

# modules/rep_cob_marca.py
import io
import urllib.parse
import unicodedata
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode
from modules import database as db
from modules.utils import parsear_fecha_robusta, extraer_dia_de_ruta_vectorial, tarjeta_metrica_html

def preparar_ventas_cobertura_marca(df_vta, anio_operativo, mes_operativo, dia_matinal):
    """
    Pipeline de ventas optimizado para Cobertura por Marca derivado del DataFrame Maestro N1 (EMPLEADOS).
    Aplica los filtros N2: PEPSICO, COMODATOS y PERIODO.
    """
    # Nivel 1: Obtención del DataFrame corporativo base con filtro EMPLEADOS aplicado
    df_corp = db.obtener_df_maestro_corporativo()
    df = df_corp.copy() if not df_corp.empty else (df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame())
    
    if df.empty:
        return df

    col_cant = next((c for c in ["CantBase", "CANTBASE", "Cantidad", "CANTIDAD", "Unidades", "UNIDADES"] if c in df.columns), df.columns[0])
    df["cantbase"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0.0)

    # Nivel 2: Filtro COMODATOS (Exclusión de comodatos y préstamos)
    if "TipoDeVenta" in df.columns:
        tipos_excluidos = [
            "Comodato Devolución", 
            "Comodato Ficticio", 
            "Comodato Ficticio Devolución", 
            "Comodato Préstamo"
        ]
        df = df[~df["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)]

    # Nivel 2: Filtro PEPSICO (Selección exclusiva de proveedor PepsiCo)
    if "Proveedor" in df.columns:
        df = df[
            df["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    col_vend_tit = next((cand for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"] if cand in df.columns), "CodVendedor")
    df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype("Int64")

    df["MesCarga"] = df["FechaCarga_dt"].dt.month
    df["AñoCarga"] = df["FechaCarga_dt"].dt.year
    df["MesEntrega"] = df["FechaEntrega_dt"].dt.month
    df["AñoEntrega"] = df["FechaEntrega_dt"].dt.year

    mes_ant = 12 if mes_operativo == 1 else mes_operativo - 1
    anio_ant = anio_operativo - 1 if mes_operativo == 1 else anio_operativo

    mes_sig = 1 if mes_operativo == 12 else mes_operativo + 1
    anio_sig = anio_operativo + 1 if mes_operativo == 12 else anio_operativo

    ac, mc = df["AñoCarga"], df["MesCarga"]
    ae, me = df["AñoEntrega"], df["MesEntrega"]
    
    cond_arr = (ac == anio_ant) & (mc == mes_ant) & (ae == anio_operativo) & (me == mes_operativo)
    cond_act = (ac == anio_operativo) & (mc == mes_operativo) & (ae == anio_operativo) & (me == mes_operativo)
    cond_fut = (ac == anio_operativo) & (mc == mes_operativo) & (ae == anio_sig) & (me == mes_sig)

    # Nivel 2: Filtro PERIODO (Clasificación de transacciones en Arrastre, Actual o Futuro)
    df["Periodo"] = np.select(
        [cond_arr, cond_act, cond_fut],
        ["Arrastre", "Actual", "Futuro"],
        default="Fuera de Periodo"
    )

    col_m = next((c for c in ["Marca", "MARCA", "marca"] if c in df.columns), None)
    df["Marca"] = df[col_m].fillna("").astype(str).str.strip().str.upper() if col_m else "SIN MARCA"

    return df

def _calcular_base_cobertura_marca(df_vtas_operativo, df_cartera, vendedores, df_marcas, anio_op, mes_op, dia_matinal):
    """Motor de cálculo base de Cobertura por Marca optimizado."""
    df_vta_prep = preparar_ventas_cobertura_marca(df_vtas_operativo, anio_op, mes_op, dia_matinal)

    df_vend = vendedores.copy() if vendedores is not None and not vendedores.empty else pd.DataFrame(columns=["CodVend", "Nombre", "SUP"])
    col_cod_v = next((c for c in ["CodVend", "Codigo_Vendedor", "CodVendedor"] if c in df_vend.columns), df_vend.columns[0])
    col_nom_v = next((c for c in df_vend.columns if "nombre" in str(c).strip().lower()), df_vend.columns[1] if len(df_vend.columns) > 1 else df_vend.columns[0])
    col_sup_v = next((c for c in df_vend.columns if "sup" in str(c).strip().lower() or "supervisor" in str(c).strip().lower()), df_vend.columns[2] if len(df_vend.columns) > 2 else df_vend.columns[0])
    
    df_vend = df_vend.rename(columns={col_cod_v: "CodVendedor", col_nom_v: "Nombre", col_sup_v: "SUP"})
    df_vend["CodVendedor"] = pd.to_numeric(df_vend["CodVendedor"], errors="coerce").astype("Int64")
    df_vend = df_vend[~df_vend["CodVendedor"].isin([20, 99])].drop_duplicates(subset=["CodVendedor"])

    df_marcas_oficial = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
    if df_marcas_oficial is None or df_marcas_oficial.empty:
        df_marcas_oficial = df_marcas if df_marcas is not None else pd.DataFrame()

    marcas = []
    mapa_objetivos_empresa = {}
    
    if not df_marcas_oficial.empty:
        col_m = next((c for c in df_marcas_oficial.columns if str(c).strip().lower() in ["marca", "marcaupper", "descripcion_marca"]), None)
        if not col_m:
            col_m = next((c for c in df_marcas_oficial.columns if "marca" in str(c).strip().lower()), df_marcas_oficial.columns[0])
            
        for _, row in df_marcas_oficial.iterrows():
            m = str(row.get(col_m, "")).strip().upper()
            if m and m not in ["", "NAN", "NONE", "-NO DEFINIDO-", "-NO DEFINIDO---NO DEFINIDO-"] and m not in marcas:
                marcas.append(m)
                mapa_objetivos_empresa[m] = float(row.get("Obj_Empresa_Cobertura", 80.0) or 80.0)

    vtas = df_vta_prep[df_vta_prep["Periodo"].isin(["Arrastre", "Actual"])].copy() if not df_vta_prep.empty and "Periodo" in df_vta_prep.columns else pd.DataFrame()

    cartera = df_cartera.copy() if df_cartera is not None and not df_cartera.empty else pd.DataFrame()
    
    if not cartera.empty:
        cols_c_str = [str(c).strip().lower() for c in cartera.columns]
        
        col_prov_c = next((cartera.columns[i] for i, c in enumerate(cols_c_str) if c in ["proveedor", "fabricante", "empresa"]), None)
        if col_prov_c:
            cartera = cartera[cartera[col_prov_c].astype(str).str.contains("pepsico", case=False, na=False)].copy()
            
        subramo_col = next((c for c in cartera.columns if "subramo" in str(c).lower()), None)
        if subramo_col:
            cartera = cartera[cartera[subramo_col].fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()
            
        tax_col = next((c for c in cartera.columns if "taxonomia" in str(c).lower() or "segmentoclientecodigo" in str(c).lower()), None)
        if tax_col:
            cartera["Taxonomia"] = cartera[tax_col].astype(str).str.strip().str.upper()
            cartera = cartera[cartera["Taxonomia"].isin(["A", "B", "C", "D"])].copy()
            
        posibles_vend = ["codvendedor", "codvend", "vendedor", "vend", "cod_vend", "cod_vendedor", "nrovendedor"]
        enc_vend_c = next((cartera.columns[i] for i, c in enumerate(cols_c_str) if c in posibles_vend), None)
        
        if enc_vend_c:
            cartera["CodVendedor"] = pd.to_numeric(cartera[enc_vend_c], errors="coerce").astype("Int64")
        elif len(cartera.columns) > 0:
            cartera["CodVendedor"] = pd.to_numeric(cartera.iloc[:, 0], errors="coerce").astype("Int64")
            
        col_cod_cliente_c = next((c for c in cartera.columns if "cliente" in c.lower() or "nro" in c.lower() or "codigo" in c.lower()), cartera.columns[0])
        cartera["Cliente_Cod"] = pd.to_numeric(cartera[col_cod_cliente_c], errors="coerce").astype("Int64")
        
        col_desc_cliente = next((c for c in cartera.columns if any(k in c.lower() for k in ["razon", "nombre", "desc", "cliente"]) and c != col_cod_cliente_c), None)
        if col_desc_cliente is None:
            col_desc_cliente = col_cod_cliente_c
        cartera["Cliente_Desc"] = cartera[col_desc_cliente].fillna("").astype(str)

        col_dir_c = next((c for c in cartera.columns if any(k in c.lower() for k in ["dir", "domicilio", "direccion"])), None)
        cartera["Cliente_Dir"] = cartera[col_dir_c].fillna("").astype(str) if col_dir_c else ""

        col_ruta_c = next((c for c in cartera.columns if str(c).strip().lower() in ["ruta", "dia_visita", "visita", "dia"]), None)
        if col_ruta_c is not None:
            cartera["DiaVisita"] = extraer_dia_de_ruta_vectorial(cartera[col_ruta_c])
        else:
            cartera["DiaVisita"] = "SIN DÍA"

        cartera = cartera.dropna(subset=["CodVendedor", "Cliente_Cod"]).drop_duplicates(subset=["CodVendedor", "Cliente_Cod"])
        cartera = cartera.merge(df_vend[["CodVendedor", "Nombre", "SUP"]], on="CodVendedor", how="inner")

    cliente_col_vtas = next((c for c in ["Cliente", "NroCliente", "CodCliente", "CLIENTE"] if not vtas.empty and c in vtas.columns), "Cliente")

    if not vtas.empty and marcas:
        vtas["CodVendedor"] = pd.to_numeric(vtas["CodVendedor"], errors="coerce").astype("Int64")
        vtas["Cliente"] = pd.to_numeric(vtas[cliente_col_vtas], errors="coerce").astype("Int64")
        vtas = vtas[vtas["Marca"].isin(marcas)].copy()

        # Nivel 2: Filtro COBERTURA (Valida unidades compradas cantbase >= 3)
        vtas_agrupadas = vtas.groupby(["CodVendedor", "Cliente", "Marca"], as_index=False).agg(
            Total_Cant=("cantbase", "sum")
        )
    else:
        vtas_agrupadas = pd.DataFrame(columns=["CodVendedor", "Cliente", "Marca", "Total_Cant"])

    return cartera, vtas_agrupadas, marcas, mapa_objetivos_empresa

@st.cache_data(show_spinner=False)
def _calcular_base_cob_marca_cached(df_vtas_operativo, df_cartera, vendedores, df_marcas, anio_op, mes_op, dia_matinal, huella_datos):
    return _calcular_base_cobertura_marca(df_vtas_operativo, df_cartera, vendedores, df_marcas, anio_op, mes_op, dia_matinal)

def generar_reporte_cobertura_marca(df_vtas_operativo, df_cartera, vendedores, df_marcas, filtros_globales=None):
    if filtros_globales:
        anio_op = int(filtros_globales.get("anio", 2026))
        mes_op = int(filtros_globales.get("mes", 9))
        dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026")
    else:
        df_params = db.cargar_tabla_sql("SELECT * FROM parametros")
        params_map = {}
        if not df_params.empty and "PARAMETRO" in df_params.columns and "VALOR" in df_params.columns:
            params_map = dict(zip(df_params["PARAMETRO"], df_params["VALOR"]))

        anio_op = int(st.session_state.get("sel_anio_op", params_map.get("Año", 2026)))
        mes_op = int(st.session_state.get("sel_mes_op", params_map.get("Mes", 9)))
        
        dia_matinal_default = params_map.get("Dia Matinal", "02/09/2026")
        dia_matinal_obj = st.session_state.get("sel_dia_matinal", dia_matinal_default)
        dia_matinal = dia_matinal_obj.strftime("%d/%m/%Y") if hasattr(dia_matinal_obj, "strftime") else str(dia_matinal_obj)

    huella_datos = f"{len(df_vtas_operativo) if df_vtas_operativo is not None else 0}_{len(df_cartera) if df_cartera is not None else 0}_{anio_op}_{mes_op}_{dia_matinal}"

    cartera, vtas_agrupadas, marcas, mapa_objetivos = _calcular_base_cob_marca_cached(
        df_vtas_operativo, df_cartera, vendedores, df_marcas, anio_op, mes_op, dia_matinal, huella_datos
    )

    st.session_state["_cob_cartera_base"] = cartera
    st.session_state["_cob_vtas_agrupadas"] = vtas_agrupadas
    st.session_state["_cob_marcas"] = marcas
    st.session_state["_cob_mapa_objetivos"] = mapa_objetivos

    return pd.DataFrame(), marcas, mapa_objetivos

@st.fragment
def render_fragmento_interactivo_cobertura_marca(reporte_cobertura_dummy, marcas_param, mapa_objetivos_param, supervisores_seleccionados):
    cartera_base = st.session_state.get("_cob_cartera_base", pd.DataFrame())
    vtas_agrup = st.session_state.get("_cob_vtas_agrupadas", pd.DataFrame())
    marcas = st.session_state.get("_cob_marcas", marcas_param)
    mapa_objetivos = st.session_state.get("_cob_mapa_objetivos", mapa_objetivos_param)

    if cartera_base.empty:
        st.info("No hay datos de cartera disponibles para procesar la Cobertura por Marca.")
        return

    sup_str = [str(s).strip() for s in supervisores_seleccionados]
    cartera_filtrada = cartera_base[cartera_base["SUP"].astype(str).str.strip().isin(sup_str)].copy() if sup_str and "SUP" in cartera_base.columns else cartera_base.copy()

    if cartera_filtrada.empty:
        st.info("No se encontraron registros para los supervisores seleccionados.")
        return

    v_dispo = sorted(cartera_filtrada["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    orden_dias = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO", "SIN DÍA"]
    dias_en_datos = cartera_filtrada["DiaVisita"].dropna().astype(str).str.strip().unique().tolist() if "DiaVisita" in cartera_filtrada.columns else []
    dia_visita_dispo = [d for d in orden_dias if d in dias_en_datos]
    for d in dias_en_datos:
        if d not in dia_visita_dispo:
            dia_visita_dispo.append(d)

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], placeholder="Seleccionar preventistas...", key="frag_cob_vendedor")
    with col_f2:
        m_selec = st.multiselect("Marca", options=marcas, default=[], placeholder="Seleccionar marcas...", key="frag_cob_marca")
    with col_f3:
        dia_visita_selec = st.multiselect("Día de Visita", options=dia_visita_dispo, default=[], placeholder="Seleccionar días de visita...", key="frag_cob_dia_visita")

    if not v_selec:
        v_selec = v_dispo
    if not m_selec:
        m_selec = marcas
    if not dia_visita_selec:
        dia_visita_selec = dia_visita_dispo

    mask_cartera = (
        cartera_filtrada["Nombre"].astype(str).str.strip().isin(v_selec) &
        cartera_filtrada["DiaVisita"].astype(str).str.strip().isin(dia_visita_selec)
    )
    cartera_activa = cartera_filtrada[mask_cartera].copy()

    if cartera_activa.empty:
        st.info("No se encontraron clientes para los filtros seleccionados.")
        return

    cartera_por_vendedor = cartera_activa.groupby(["CodVendedor", "Nombre", "SUP"], as_index=False).agg(
        Cartera=("Cliente_Cod", "nunique")
    )

    clientes_activos = set(cartera_activa["Cliente_Cod"].unique())
    vtas_activas = vtas_agrup[
        vtas_agrup["Cliente"].isin(clientes_activos) &
        vtas_agrup["Marca"].isin(m_selec) &
        vtas_agrup["Total_Cant"].ge(3)
    ].copy() if not vtas_agrup.empty else pd.DataFrame()

    if not vtas_activas.empty:
        cubiertos_pivot = vtas_activas.groupby(["CodVendedor", "Marca"])["Cliente"].nunique().unstack(fill_value=0).reset_index()
        cubiertos_pivot.columns.name = None
    else:
        cubiertos_pivot = pd.DataFrame(columns=["CodVendedor"])

    reporte_matriz = cartera_por_vendedor.merge(cubiertos_pivot, on="CodVendedor", how="left")

    for m in m_selec:
        if m not in reporte_matriz.columns:
            reporte_matriz[m] = 0.0
        else:
            reporte_matriz[m] = reporte_matriz[m].fillna(0.0)
            
        total_c = reporte_matriz["Cartera"].replace(0, pd.NA)
        reporte_matriz[m] = ((reporte_matriz[m] / total_c).fillna(0.0) * 100.0).round(2)

    reporte_matriz = reporte_matriz.sort_values(by="CodVendedor").reset_index(drop=True)

    suma_cartera_global = reporte_matriz["Cartera"].sum()
    m_selec_ordenadas = [m for m in marcas if m in m_selec]

    if m_selec_ordenadas:
        cols_obj_ui = st.columns(min(len(m_selec_ordenadas), 5))
        for idx, marca in enumerate(m_selec_ordenadas):
            col_target = cols_obj_ui[idx % len(cols_obj_ui)]
            obj_val = float(mapa_objetivos.get(marca, 80.0) or 80.0)
            
            if suma_cartera_global > 0 and marca in reporte_matriz.columns:
                cubiertos_totales = (reporte_matriz[marca] / 100.0 * reporte_matriz["Cartera"]).sum()
                cobertura_global_pct = (cubiertos_totales / suma_cartera_global) * 100.0
            else:
                cobertura_global_pct = 0.0
                
            color_borde = "#64748b"
            alcanzado = cobertura_global_pct >= obj_val
            color_valor = "#22c55e" if alcanzado else "#ef4444"
            
            with col_target:
                titulo_tarjeta = f"<span style='color: #ffffff; font-weight: 700;'>{marca} (OBJ: {obj_val:g}%)</span>"
                st.markdown(tarjeta_metrica_html(titulo_tarjeta, f"{cobertura_global_pct:.2f}%", color_borde, "1.4rem", "0.95rem", color_valor=color_valor), unsafe_allow_html=True)
            
        st.divider()

    columnas_finales = ["CodVendedor", "Nombre", "Cartera", "SUP"] + [m for m in m_selec_ordenadas if m in reporte_matriz.columns]
    df_render = reporte_matriz[columnas_finales].copy()

    df_render_excel = df_render.copy()
    df_render_display = df_render.copy()
    for marca in m_selec_ordenadas:
        if marca in df_render_display.columns:
            df_render_display[marca] = df_render_display[marca].apply(lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%")

    if not df_render_display.empty:
        gb = GridOptionsBuilder.from_dataframe(df_render_display)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, cellStyle={'textAlign': 'center'}, headerClass='centered-header')
        gb.configure_column("CodVendedor", headerName="Cód. Vend", width=100)
        gb.configure_column("Nombre", headerName="Nombre", minWidth=180, cellStyle={'textAlign': 'left'}, headerClass='left-header')
        gb.configure_column("Cartera", headerName="Cartera", width=95)
        gb.configure_column("SUP", headerName="SUP", width=80)
        
        js_objetivos = str(mapa_objetivos)
        cell_style_conditional = JsCode(f"""
        function(params) {{
            const mapaObj = {js_objetivos};
            const col = params.colDef.field;
            if (mapaObj.hasOwnProperty(col)) {{
                const objetivo = Number(mapaObj[col]) || 80.0;
                const valorReal = Number(params.value) || 0;
                if (valorReal >= objetivo) {{
                    return {{'backgroundColor': '#d4edda', 'fontWeight': 'bold', 'color': '#155724', 'textAlign': 'center'}};
                }} else {{
                    return {{'backgroundColor': '#f8d7da', 'fontWeight': 'bold', 'color': '#721c24', 'textAlign': 'center'}};
                }}
            }}
            return {{'textAlign': 'center'}};
        }}
        """)

        for marca in m_selec_ordenadas:
            if marca in df_render_display.columns:
                gb.configure_column(
                    marca,
                    headerName=marca,
                    cellStyle=cell_style_conditional,
                    minWidth=120
                )
                
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_options = gb.build()
        
        st.markdown("""
        <style>
        .ag-header-cell-label {
            justify-content: center !important;
            text-align: center !important;
        }
        .left-header .ag-header-cell-label {
            justify-content: flex-start !important;
            text-align: left !important;
        }
        </style>
        """, unsafe_allow_html=True)

        AgGrid(
            df_render_display,
            gridOptions=grid_options,
            height=400,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True
        )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_render_excel.to_excel(writer, index=False, sheet_name="Cobertura_Por_Marca")
    buffer.seek(0)
    
    st.download_button(
        label="📥 Descargar Cobertura por Marca a Excel",
        data=buffer,
        file_name="Cobertura_Por_Marca.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="cob_marca_btn_dl"
    )

    st.markdown("### ⚔️ Batalla Cobertura por Marca")
    st.markdown("Clientes activos en cartera que no alcanzan el volumen mínimo de compra (< 3 unidades) en las marcas seleccionadas.")

    ventas_unidades_map = vtas_agrup.set_index(["CodVendedor", "Cliente", "Marca"])["Total_Cant"].to_dict() if not vtas_agrup.empty else {}

    registros_nc = []
    for m in m_selec_ordenadas:
        for row in cartera_activa.itertuples(index=False):
            cv = int(row.CodVendedor)
            cli = int(row.Cliente_Cod)
            und = ventas_unidades_map.get((cv, cli, m), 0.0)
            if und < 3.0:
                registros_nc.append({
                    "Vendedor": row.Nombre,
                    "Cód. Cliente": cli,
                    "Cliente": row.Cliente_Desc,
                    "Dirección": row.Cliente_Dir,
                    "Día Visita": row.DiaVisita,
                    "Marca": m,
                    "Unidades": und,
                    "Estado": "No Cubierto (< 3 u.)"
                })

    df_det_view = pd.DataFrame(registros_nc)
    total_registros_batalla = len(df_det_view)
    st.caption(f"📊 Registros encontrados: **{total_registros_batalla}**")

    if not df_det_view.empty:
        gb_batalla = GridOptionsBuilder.from_dataframe(df_det_view)
        gb_batalla.configure_default_column(filterable=True, sortable=True, resizable=True, cellStyle={'textAlign': 'center'}, headerClass='centered-header')
        gb_batalla.configure_column("Vendedor", headerName="Vendedor", minWidth=160, cellStyle={'textAlign': 'left'}, headerClass='left-header')
        gb_batalla.configure_column("Cliente", headerName="Cliente", minWidth=180, cellStyle={'textAlign': 'left'}, headerClass='left-header')
        gb_batalla.configure_column("Dirección", headerName="Dirección", minWidth=160, cellStyle={'textAlign': 'left'}, headerClass='left-header')
        gb_batalla.configure_column("Cód. Cliente", headerName="Cód. Cliente", width=110)
        gb_batalla.configure_column("Día Visita", headerName="Día Visita", width=110)
        gb_batalla.configure_column("Marca", headerName="Marca", width=110)
        gb_batalla.configure_column("Unidades", headerName="Unidades", width=100, valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0,00'")
        gb_batalla.configure_column("Estado", headerName="Estado", width=140)
        
        gb_batalla.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_options_batalla = gb_batalla.build()

        AgGrid(
            df_det_view,
            gridOptions=grid_options_batalla,
            height=400,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True
        )

        col_dl1, col_dl2, col_dl3 = st.columns(3)
        with col_dl1:
            buffer_batalla = io.BytesIO()
            with pd.ExcelWriter(buffer_batalla, engine="openpyxl") as writer:
                df_det_view.to_excel(writer, index=False, sheet_name="Clientes_No_Cubiertos")
            buffer_batalla.seek(0)

            st.download_button(
                label="📥 Descargar Clientes No Cubiertos a Excel",
                data=buffer_batalla,
                file_name="Clientes_No_Cubiertos_Marca.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_dl_batalla_nc"
            )

        with col_dl2:
            pass

        with col_dl3:
            df_wa_limit = df_det_view.head(30)
            lista_nc_formateada = []
            for idx, row in df_wa_limit.iterrows():
                cli = row.get("Cód. Cliente", "")
                nom = row.get("Cliente", "")
                dir_c = row.get("Dirección", "")
                dia_v = row.get("Día Visita", "")
                marca_c = row.get("Marca", "")
                und = row.get("Unidades", 0.0)
                lista_nc_formateada.append(f"[{cli}] {nom} - {dir_c} - {dia_v} - Marca: {marca_c} (U: {und:,.2f})")

            detalle_texto = "%0A".join(lista_nc_formateada)
            aviso_limite = f"%0A(Mostrando 30 de {total_registros_batalla} in WA)" if total_registros_batalla > 30 else ""
            texto_wa = f"NC:{total_registros_batalla}%0A{detalle_texto}{aviso_limite}"
            url_wa = f"https://wa.me/?text={texto_wa}"
            
            st.markdown(f'''
                <div style="display: flex; justify-content: center; align-items: center; height: 100%; padding-top: 5px;">
                    <a href="{url_wa}" target="_blank" style="
                        display: inline-block;
                        padding: 4px 10px;
                        background-color: #25d366;
                        color: white;
                        text-align: center;
                        text-decoration: none;
                        font-weight: 600;
                        font-size: 0.75rem;
                        border-radius: 4px;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    ">💬 WhatsApp NC</a>
                </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("No se registran clientes sin cobertura para los filtros seleccionados.")

def dibujar_pestana_cobertura_marca(reporte_cobertura, marcas, mapa_objetivos, supervisores_seleccionados, df_vtas_operativo=None, df_cartera=None, filtros_globales=None):
    st.subheader("🎯 Cobertura Por Marca y Detalle de Clientes")
    sup_sel_efectivo = supervisores_seleccionados if isinstance(supervisores_seleccionados, list) else [supervisores_seleccionados]
    render_fragmento_interactivo_cobertura_marca(reporte_cobertura, marcas, mapa_objetivos, sup_sel_efectivo)

====================================================================================================


### ARCHIVO: modules\rep_gerencial.py

# modules/rep_gerencial.py
import io
import time
import os
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import tarjeta_metrica_html, parsear_fecha_robusta
from modules.rep_ccc import _calcular_base_ccc


def _preparar_ventas_gerencial_puro(df_vta, anio_operativo, mes_operativo, dia_matinal):
    """
    Pipeline corporativo exclusivo y dedicado para el Tablero Gerencial.
    Aplica N1 (EMPLEADOS) y N2 (PEPSICO, COMODATOS, MATINAL, PERIODO)
    utilizando estrictamente el CodVendedor original inmutable, sin ausencias ni reemplazos.
    """
    t_start = time.perf_counter()
    df_corp = db.obtener_df_maestro_corporativo()
    df = (
        df_corp.copy()
        if not df_corp.empty
        else (
            df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame()
        )
    )

    if df.empty:
        return df

    df["PesoKg"] = pd.to_numeric(df.get("PesoKg", 0), errors="coerce").fillna(0.0)

    col_pesos = next(
        (
            c
            for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"]
            if c in df.columns
        ),
        None,
    )
    df["ImporteNetoItem"] = (
        pd.to_numeric(df[col_pesos], errors="coerce").fillna(0.0) if col_pesos else 0.0
    )

    col_cant = next(
        (
            c
            for c in [
                "CantBase",
                "CANTBASE",
                "Cantidad",
                "CANTIDAD",
                "Unidades",
                "UNIDADES",
            ]
            if c in df.columns
        ),
        df.columns[0],
    )
    df["CantBase"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0.0)

    if "TipoDeVenta" in df.columns:
        tipos_excluidos = [
            "Comodato Devolución",
            "Comodato Ficticio",
            "Comodato Ficticio Devolución",
            "Comodato Préstamo",
        ]
        df = df[~df["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)]

    if "Proveedor" in df.columns:
        df = df[
            df["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    dia_matinal_dt = pd.to_datetime(
        str(dia_matinal), format="%d/%m/%Y", errors="coerce"
    )
    if pd.isna(dia_matinal_dt):
        dia_matinal_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]

    if pd.notna(dia_matinal_dt):
        es_mes_en_curso = (
            dia_matinal_dt.year == anio_operativo
            and dia_matinal_dt.month in [mes_operativo, mes_operativo + 1]
        )
        if es_mes_en_curso:
            df = df[df["FechaCarga_dt"].dt.date < dia_matinal_dt.date()]

    col_vend_tit = next(
        (
            cand
            for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
            if cand in df.columns
        ),
        "CodVendedor",
    )
    if col_vend_tit not in df.columns:
        df[col_vend_tit] = 0

    df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype("Int64")

    col_m = next((c for c in ["Marca", "MARCA", "marca"] if c in df.columns), None)
    df["Marca"] = (
        df[col_m].fillna("").astype(str).str.strip().str.upper()
        if col_m
        else "SIN MARCA"
    )

    col_rent = "SegmentoRentabilidad" if "SegmentoRentabilidad" in df.columns else None
    col_rubro = "Rubro" if "Rubro" in df.columns else None

    sr = (
        df.get(col_rent, pd.Series("", index=df.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .str.title()
        if col_rent
        else pd.Series("", index=df.index)
    )
    rubro = (
        df.get(col_rubro, pd.Series("", index=df.index))
        .fillna("")
        .astype(str)
        .str.strip()
        if col_rubro
        else pd.Series("", index=df.index)
    )

    cond_gold = sr.isin(["Platinum", "Gold"]).fillna(False)
    cond_silver = sr.isin(["Silver", "Bronze"]).fillna(False)

    gold_val = "GOLD " + rubro
    silver_val = "SILVER " + rubro
    df["SEGMENTO"] = np.select(
        [cond_gold, cond_silver],
        [gold_val.str.strip(), silver_val.str.strip()],
        default="SIN SEGMENTO",
    )

    df["MesCarga"] = df["FechaCarga_dt"].dt.month
    df["AñoCarga"] = df["FechaCarga_dt"].dt.year
    df["MesEntrega"] = df["FechaEntrega_dt"].dt.month
    df["AñoEntrega"] = df["FechaEntrega_dt"].dt.year

    mes_ant = 12 if mes_operativo == 1 else mes_operativo - 1
    anio_ant = anio_operativo - 1 if mes_operativo == 1 else anio_operativo

    mes_sig = 1 if mes_operativo == 12 else mes_operativo + 1
    anio_sig = anio_operativo + 1 if mes_operativo == 12 else anio_operativo

    ac, mc = df["AñoCarga"], df["MesCarga"]
    ae, me = df["AñoEntrega"], df["MesEntrega"]

    cond_arr = (
        (ac == anio_ant)
        & (mc == mes_ant)
        & (ae == anio_operativo)
        & (me == mes_operativo)
    ).fillna(False)
    cond_act = (
        (ac == anio_operativo)
        & (mc == mes_operativo)
        & (ae == anio_operativo)
        & (me == mes_operativo)
    ).fillna(False)
    cond_fut = (
        (ac == anio_operativo)
        & (mc == mes_operativo)
        & (ae == anio_sig)
        & (me == mes_sig)
    ).fillna(False)

    df["Periodo"] = np.select(
        [cond_arr, cond_act, cond_fut],
        ["Arrastre", "Actual", "Futuro"],
        default="Fuera de Periodo",
    )

    print(
        f"[PERF_INTERNAL] _preparar_ventas_gerencial_puro = {time.perf_counter() - t_start:.2f} s"
    )
    return df


def _calcular_ccc_taxonomia_gerencial(
    df_vta, df_universo, maestro_v, anio_op, mes_op, dia_matinal, sup_seleccionado
):
    t_start = time.perf_counter()
    try:
        t_s1 = time.perf_counter()
        maestro_ccc = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
        print(
            f"[PERF_INTERNAL] consulta_sqlite_maestro_ccc = {time.perf_counter() - t_s1:.2f} s"
        )
    except Exception:
        maestro_ccc = pd.DataFrame(
            columns=["Taxonomia", "Porcentaje_Cartera", "Obj_CCC_Pepsico"]
        )

    if (
        not maestro_ccc.empty
        and "Mes" in maestro_ccc.columns
        and "Anio" in maestro_ccc.columns
    ):
        mc_per = maestro_ccc[
            (maestro_ccc["Mes"].astype(str) == str(mes_op))
            & (maestro_ccc["Anio"].astype(str) == str(anio_op))
        ]
        if not mc_per.empty:
            maestro_ccc = mc_per

    mapa_obj_pepsico = {}
    if not maestro_ccc.empty and "Taxonomia" in maestro_ccc.columns:
        for _, row in maestro_ccc.iterrows():
            tax = str(row["Taxonomia"]).strip().upper()
            if "Obj_CCC_Pepsico" in maestro_ccc.columns and pd.notna(
                row.get("Obj_CCC_Pepsico")
            ):
                mapa_obj_pepsico[tax] = float(row["Obj_CCC_Pepsico"])

    t_s2 = time.perf_counter()
    reporte_base_ccc, _ = _calcular_base_ccc(
        df_vta, df_universo, maestro_v, maestro_ccc, anio_op, mes_op, dia_matinal
    )
    print(f"[PERF_INTERNAL] _calcular_base_ccc = {time.perf_counter() - t_s2:.2f} s")

    if reporte_base_ccc.empty:
        empty_df = pd.DataFrame(
            columns=[
                "Taxonomia",
                "Cartera_Neta",
                "Obj_Pepsico",
                "Cump_Pepsico_Pct",
                "Obj_Fuerza_Ventas",
                "Cump_Fuerza_Ventas_Pct",
                "Avance_CCC",
            ]
        )
        empty_disp = pd.DataFrame(
            columns=[
                "Taxonomía",
                "Cartera Neta (NC)",
                "Obj de Pepsico",
                "% Cump Obj Pepsico",
                "Objetivo a Fuerza de Ventas",
                "% Cump Obj Fuerza de Ventas",
                "Avance CCC",
            ]
        )
        return empty_df, empty_disp

    if sup_seleccionado != "TODOS" and "SUP" in reporte_base_ccc.columns:
        reporte_base_ccc = reporte_base_ccc[
            reporte_base_ccc["SUP"].astype(str).str.strip()
            == str(sup_seleccionado).strip()
        ].copy()

    t_s3 = time.perf_counter()
    res_tax = reporte_base_ccc.groupby("Taxonomia", as_index=False).agg(
        Cartera_Neta=("Cartera_Neta", "sum"),
        Avance_CCC=("CCC", "sum"),
        Obj_Fuerza_Ventas=("Objetivo_CCC", "sum"),
    )

    res_tax["Obj_Pepsico"] = res_tax["Taxonomia"].map(mapa_obj_pepsico).fillna(0.0)
    res_tax["Obj_Fuerza_Ventas"] = pd.to_numeric(
        res_tax["Obj_Fuerza_Ventas"], errors="coerce"
    ).fillna(0.0)

    res_tax["Cump_Pepsico_Pct"] = (
        (res_tax["Avance_CCC"] / res_tax["Obj_Pepsico"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    res_tax["Cump_Fuerza_Ventas_Pct"] = (
        (res_tax["Avance_CCC"] / res_tax["Obj_Fuerza_Ventas"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    df_res = res_tax[
        [
            "Taxonomia",
            "Cartera_Neta",
            "Obj_Pepsico",
            "Cump_Pepsico_Pct",
            "Obj_Fuerza_Ventas",
            "Cump_Fuerza_Ventas_Pct",
            "Avance_CCC",
        ]
    ].copy()

    df_display = df_res.copy()
    df_display["Cartera_Neta"] = df_display["Cartera_Neta"].apply(
        lambda x: f"{int(x):,}"
    )
    df_display["Obj_Pepsico"] = df_display["Obj_Pepsico"].apply(
        lambda x: f"{int(round(x)):,}"
    )
    df_display["Cump_Pepsico_Pct"] = df_display["Cump_Pepsico_Pct"].apply(
        lambda x: f"{x:,.2f}%"
    )
    df_display["Obj_Fuerza_Ventas"] = df_display["Obj_Fuerza_Ventas"].apply(
        lambda x: f"{int(round(x)):,}"
    )
    df_display["Cump_Fuerza_Ventas_Pct"] = df_display["Cump_Fuerza_Ventas_Pct"].apply(
        lambda x: f"{x:,.2f}%"
    )
    df_display["Avance_CCC"] = df_display["Avance_CCC"].apply(lambda x: f"{int(x):,}")

    df_display = df_display.rename(
        columns={
            "Taxonomia": "Taxonomía",
            "Cartera_Neta": "Cartera Neta (NC)",
            "Obj_Pepsico": "Obj de Pepsico",
            "Cump_Pepsico_Pct": "% Cump Obj Pepsico",
            "Obj_Fuerza_Ventas": "Objetivo a Fuerza de Ventas",
            "Cump_Fuerza_Ventas_Pct": "% Cump Obj Fuerza de Ventas",
            "Avance_CCC": "Avance CCC",
        }
    )
    print(
        f"[PERF_INTERNAL] agrupaciones_ccc_gerencial = {time.perf_counter() - t_s3:.2f} s"
    )
    print(
        f"[PERF_INTERNAL] _calcular_ccc_taxonomia_gerencial = {time.perf_counter() - t_start:.2f} s"
    )

    return df_res, df_display


def _calcular_minegocio_taxonomia_detallado(
    df_vta_prep_gerencial,
    df_universo,
    maestro_v,
    anio_op,
    mes_op,
    dia_matinal,
    sup_seleccionado,
):
    t_start = time.perf_counter()
    try:
        t_s1 = time.perf_counter()
        df_ausencias = db.cargar_tabla_sql("SELECT * FROM ausencias")
        print(
            f"[PERF_INTERNAL] consulta_sqlite_ausencias_mn = {time.perf_counter() - t_s1:.2f} s"
        )
    except Exception:
        df_ausencias = pd.DataFrame()

    from modules.rep_MN import preparar_ventas_mn

    t_s2 = time.perf_counter()
    df_vta_mn = preparar_ventas_mn(
        df_vta_prep_gerencial, df_ausencias, anio_op, mes_op, dia_matinal
    )
    print(
        f"[PERF_INTERNAL] preparar_ventas_mn_gerencial = {time.perf_counter() - t_s2:.2f} s"
    )

    vtas_per = (
        df_vta_mn[df_vta_mn["Periodo"].isin(["Arrastre", "Actual"])].copy()
        if not df_vta_mn.empty and "Periodo" in df_vta_mn.columns
        else df_vta_mn.copy()
    )

    col_pesos = next(
        (
            c
            for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"]
            if c in vtas_per.columns
        ),
        None,
    )
    col_kilos = next(
        (c for c in ["PesoKg", "PESOKG", "Kilos"] if c in vtas_per.columns), None
    )
    col_cant = next(
        (
            c
            for c in ["CantBase", "CANTBASE", "Cantidad", "Unidades"]
            if c in vtas_per.columns
        ),
        None,
    )

    vtas_per["_gross_calc"] = (
        pd.to_numeric(vtas_per[col_pesos], errors="coerce").fillna(0.0)
        if col_pesos
        else 0.0
    )
    vtas_per["_kilos_calc"] = (
        pd.to_numeric(vtas_per[col_kilos], errors="coerce").fillna(0.0)
        if col_kilos
        else 0.0
    )
    vtas_per["_cant_calc"] = (
        pd.to_numeric(vtas_per[col_cant], errors="coerce").fillna(0.0)
        if col_cant
        else 0.0
    )

    col_cli_vta = next(
        (
            c
            for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
            if c in vtas_per.columns
        ),
        "Cliente",
    )
    vtas_per["Cliente"] = pd.to_numeric(vtas_per[col_cli_vta], errors="coerce").astype(
        "Int64"
    )

    vtas_per["_mn_gross_val"] = np.where(
        vtas_per["Es_MiNegocio"], vtas_per["_gross_calc"], 0.0
    )
    vtas_per["_mn_kilos_val"] = np.where(
        vtas_per["Es_MiNegocio"], vtas_per["_kilos_calc"], 0.0
    )

    t_s3 = time.perf_counter()
    cli_agg = vtas_per.groupby("Cliente", as_index=False).agg(
        Gross_Total=("_gross_calc", "sum"),
        Gross_MN=("_mn_gross_val", "sum"),
        Kilos_Total=("_kilos_calc", "sum"),
        Kilos_MN=("_mn_kilos_val", "sum"),
        Total_Cant=("_cant_calc", "sum"),
        Total_Imp=("_gross_calc", "sum"),
    )
    cli_agg["Es_CCC"] = cli_agg["Total_Cant"].ge(3) & cli_agg["Total_Imp"].ge(1)
    cli_agg["Pct_MN_Gross"] = (
        (cli_agg["Gross_MN"] / cli_agg["Gross_Total"].replace(0, pd.NA))
        .mul(100.0)
        .clip(lower=0, upper=100)
        .fillna(0.0)
    )

    cond_nodig = (cli_agg["Pct_MN_Gross"] <= 0.01).fillna(False)
    cond_hibr = (
        (cli_agg["Pct_MN_Gross"] > 0.01) & (cli_agg["Pct_MN_Gross"] < 70.0)
    ).fillna(False)
    cli_agg["Categoria_Digital"] = np.select(
        [cond_nodig, cond_hibr], ["No Digital", "Híbridos"], default="Fully Digital"
    )
    print(f"[PERF_INTERNAL] groupby_clientes_mn = {time.perf_counter() - t_s3:.2f} s")

    univ = df_universo.copy() if df_universo is not None else pd.DataFrame()
    if not univ.empty:
        col_c_u = next(
            (
                c
                for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"]
                if c in univ.columns
            ),
            univ.columns[0],
        )
        univ["Cliente"] = pd.to_numeric(univ[col_c_u], errors="coerce").astype("Int64")

        tax_col = next(
            (
                c
                for c in univ.columns
                if "taxonomia" in str(c).lower()
                or "segmentoclientecodigo" in str(c).lower()
            ),
            None,
        )
        if tax_col:
            univ["Taxonomia"] = (
                univ[tax_col].fillna("").astype(str).str.strip().str.upper()
            )
        else:
            univ["Taxonomia"] = "A"

        pos_v_u = next(
            (
                c
                for c in univ.columns
                if any(k in str(c).lower() for k in ["codven", "vendedor"])
            ),
            None,
        )
        if pos_v_u:
            univ["CodVendedor"] = pd.to_numeric(univ[pos_v_u], errors="coerce").astype(
                "Int64"
            )

        univ = univ[univ["Taxonomia"].isin(["A", "B", "C", "D"])].dropna(
            subset=["Cliente"]
        )

    vend_map = pd.DataFrame()
    if maestro_v is not None and not maestro_v.empty:
        c_cod = next(
            (c for c in maestro_v.columns if "cod" in str(c).lower()),
            maestro_v.columns[0],
        )
        c_sup = next(
            (c for c in maestro_v.columns if "sup" in str(c).lower()),
            maestro_v.columns[2]
            if len(maestro_v.columns) > 2
            else maestro_v.columns[0],
        )
        vend_map["CodVendedor"] = pd.to_numeric(
            maestro_v[c_cod], errors="coerce"
        ).astype("Int64")
        vend_map["SUP"] = maestro_v[c_sup].fillna("").astype(str).str.strip()
        vend_map = vend_map.drop_duplicates("CodVendedor")

    if not univ.empty and not vend_map.empty and "CodVendedor" in univ.columns:
        univ = univ.merge(vend_map, on="CodVendedor", how="left")
    elif not univ.empty:
        univ["SUP"] = "GENERAL"

    if sup_seleccionado != "TODOS" and not univ.empty and "SUP" in univ.columns:
        univ = univ[
            univ["SUP"].astype(str).str.strip() == str(sup_seleccionado).strip()
        ].copy()

    # Alineación estricta basada en el Universo completo (Left Join desde el Universo)
    t_s4 = time.perf_counter()
    if not univ.empty:
        df_merged = univ.merge(cli_agg, on="Cliente", how="left")
    else:
        df_merged = pd.DataFrame(
            columns=[
                "Taxonomia",
                "Cliente",
                "Gross_Total",
                "Gross_MN",
                "Kilos_Total",
                "Kilos_MN",
                "Es_CCC",
                "Categoria_Digital",
            ]
        )

    df_merged["Gross_Total"] = df_merged["Gross_Total"].fillna(0.0)
    df_merged["Gross_MN"] = df_merged["Gross_MN"].fillna(0.0)
    df_merged["Kilos_Total"] = df_merged["Kilos_Total"].fillna(0.0)
    df_merged["Kilos_MN"] = df_merged["Kilos_MN"].fillna(0.0)
    df_merged["Es_CCC"] = df_merged["Es_CCC"].fillna(False)
    df_merged["Categoria_Digital"] = df_merged["Categoria_Digital"].fillna("No Digital")

    tax_base = pd.DataFrame({"Taxonomia": ["A", "B", "C", "D"]})

    gross_g = df_merged.groupby("Taxonomia", as_index=False).agg(
        Gross_Total=("Gross_Total", "sum"), Gross_MN=("Gross_MN", "sum")
    )
    res_gross = tax_base.merge(gross_g, on="Taxonomia", how="left").fillna(0.0)

    try:
        df_v20_total = (
            df_vta_prep_gerencial[
                (df_vta_prep_gerencial["CodVendedor"] == 20)
                & df_vta_prep_gerencial["Periodo"].isin(["Arrastre", "Actual"])
            ].copy()
            if not df_vta_prep_gerencial.empty
            else pd.DataFrame()
        )

        if not df_v20_total.empty:
            val_v20_gross = (
                pd.to_numeric(df_v20_total[col_pesos], errors="coerce").sum()
                if col_pesos
                else 0.0
            )
            suma_gross_actual = res_gross["Gross_Total"].sum()
            if suma_gross_actual > 0:
                for idx, row in res_gross.iterrows():
                    proporcion = row["Gross_Total"] / suma_gross_actual
                    res_gross.loc[idx, "Gross_Total"] += val_v20_gross * proporcion
    except Exception:
        pass

    res_gross["Adopcion_Gross_Pct"] = (
        (res_gross["Gross_MN"] / res_gross["Gross_Total"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    kilos_g = df_merged.groupby("Taxonomia", as_index=False).agg(
        Kilos_Total=("Kilos_Total", "sum"), Kilos_MN=("Kilos_MN", "sum")
    )
    res_kilos = tax_base.merge(kilos_g, on="Taxonomia", how="left").fillna(0.0)
    res_kilos["Adopcion_Kilos_Pct"] = (
        (res_kilos["Kilos_MN"] / res_kilos["Kilos_Total"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    ccc_cartera = df_merged.groupby("Taxonomia", as_index=False).agg(
        Cartera_Total=("Cliente", "count"), CCC_Total=("Es_CCC", lambda x: int(x.sum()))
    )

    ccc_compradores = (
        df_merged[df_merged["Es_CCC"] == True]
        .groupby(["Taxonomia", "Categoria_Digital"], as_index=False)
        .agg(Cantidad=("Cliente", "count"))
    )
    ccc_pivot = ccc_compradores.pivot_table(
        index="Taxonomia", columns="Categoria_Digital", values="Cantidad", fill_value=0
    ).reset_index()
    ccc_pivot.columns.name = None

    for cat in ["No Digital", "Híbridos", "Fully Digital"]:
        if cat not in ccc_pivot.columns:
            ccc_pivot[cat] = 0

    res_ccc = (
        tax_base.merge(ccc_cartera, on="Taxonomia", how="left")
        .merge(ccc_pivot, on="Taxonomia", how="left")
        .fillna(0)
    )
    res_ccc[
        ["Cartera_Total", "CCC_Total", "No Digital", "Híbridos", "Fully Digital"]
    ] = res_ccc[
        ["Cartera_Total", "CCC_Total", "No Digital", "Híbridos", "Fully Digital"]
    ].astype(int)
    print(
        f"[PERF_INTERNAL] merge_y_pivots_mn_detallado = {time.perf_counter() - t_s4:.2f} s"
    )
    print(
        f"[PERF_INTERNAL] _calcular_minegocio_taxonomia_detallado = {time.perf_counter() - t_start:.2f} s"
    )

    return res_gross, res_kilos, res_ccc


@st.cache_data(show_spinner=False)
def _calcular_motor_gerencial_global(
    df_vta,
    df_universo,
    df_rutas,
    df_ausencias,
    anio_op,
    mes_op,
    dia_matinal,
    dia_venta,
    sup_seleccionado,
    modo_ajuste,
    huella_global,
):
    t_start = time.perf_counter()
    try:
        t_s1 = time.perf_counter()
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        print(
            f"[PERF_INTERNAL] consulta_sqlite_maestro_vendedores_ger = {time.perf_counter() - t_s1:.2f} s"
        )
        if not maestro_v.empty and "Mes" in maestro_v.columns:
            mv_per = maestro_v[
                (maestro_v["Mes"].astype(str) == str(mes_op))
                & (maestro_v["Anio"].astype(str) == str(anio_op))
            ]
            if not mv_per.empty:
                maestro_v = mv_per
    except Exception:
        maestro_v = pd.DataFrame()

    try:
        t_s2 = time.perf_counter()
        maestro_s = db.cargar_tabla_sql(
            "SELECT * FROM maestro_segmentos ORDER BY rowid ASC"
        )
        print(
            f"[PERF_INTERNAL] consulta_sqlite_maestro_segmentos = {time.perf_counter() - t_s2:.2f} s"
        )
    except Exception:
        maestro_s = pd.DataFrame()

    try:
        t_s3 = time.perf_counter()
        maestro_cebe = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        print(
            f"[PERF_INTERNAL] consulta_sqlite_maestro_cebe = {time.perf_counter() - t_s3:.2f} s"
        )
        if not maestro_cebe.empty and "Mes" in maestro_cebe.columns:
            mc_per = maestro_cebe[
                (maestro_cebe["Mes"].astype(str) == str(mes_op))
                & (maestro_cebe["Anio"].astype(str) == str(anio_op))
            ]
            if not mc_per.empty:
                maestro_cebe = mc_per
    except Exception:
        maestro_cebe = pd.DataFrame()

    df_marcas_maestro = pd.DataFrame()

    if maestro_v.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            [],
            {},
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            0,
            0,
        )

    col_sup_v = next(
        (c for c in maestro_v.columns if "sup" in str(c).strip().lower()),
        maestro_v.columns[2] if len(maestro_v.columns) > 2 else maestro_v.columns[0],
    )
    col_cod_v = next(
        (c for c in maestro_v.columns if "cod" in str(c).strip().lower()),
        maestro_v.columns[0],
    )

    maestro_v["Cod_Clean"] = (
        pd.to_numeric(maestro_v[col_cod_v], errors="coerce")
        .astype("Int64")
        .astype(str)
        .str.strip()
    )
    maestro_v["Sup_Clean"] = maestro_v[col_sup_v].fillna("").astype(str).str.strip()
    sup_map = maestro_v.set_index("Cod_Clean")["Sup_Clean"].to_dict()

    col_rutas_ajust_m = next(
        (
            c
            for c in maestro_v.columns
            if str(c).strip().lower()
            in ["rutas_ajustadas", "rutasajustadas", "ajustadas"]
        ),
        None,
    )
    rutas_ajust_map_g = (
        maestro_v.set_index("Cod_Clean")[col_rutas_ajust_m]
        .fillna(0)
        .astype(int)
        .to_dict()
        if col_rutas_ajust_m
        else {}
    )

    # Operativo con filtro matinal estricto
    t_s4 = time.perf_counter()
    df_vta_prep_ger = _preparar_ventas_gerencial_puro(
        df_vta, anio_op, mes_op, dia_matinal
    )
    print(
        f"[PERF_INTERNAL] _preparar_ventas_gerencial_puro_operativo = {time.perf_counter() - t_s4:.2f} s"
    )

    # Futuro sin restricción matinal
    t_s5 = time.perf_counter()
    df_corp_raw = db.obtener_df_maestro_corporativo()
    df_vta_prep_ger_full = _preparar_ventas_gerencial_puro(
        df_corp_raw if not df_corp_raw.empty else df_vta, anio_op, mes_op, "01/01/2000"
    )
    print(
        f"[PERF_INTERNAL] _preparar_ventas_gerencial_puro_full = {time.perf_counter() - t_s5:.2f} s"
    )

    rutas = (
        df_rutas.copy()
        if df_rutas is not None and not df_rutas.empty
        else pd.DataFrame()
    )
    dias_pasados_map = {}
    dias_restantes_map = {}
    total_dias_pasados_val = 0
    total_dias_restantes_val = 0

    t_s6 = time.perf_counter()
    if not rutas.empty:
        col_fecha_r = next(
            (
                c
                for c in ["Fecha", "fecha", "Dia", "Date", "FECHA"]
                if c in rutas.columns
            ),
            rutas.columns[0],
        )
        col_vend_r = next(
            (
                c
                for c in [
                    "codven",
                    "CodVen",
                    "CodVendedor",
                    "Vendedor",
                    "Cod_Vendedor",
                    "CODVEN",
                ]
                if c in rutas.columns
            ),
            rutas.columns[1],
        )

        s_fechas = (
            rutas[col_fecha_r]
            .astype(str)
            .str.strip()
            .str.replace(" 00:00:00", "", regex=False)
        )
        dt_directo = pd.to_datetime(s_fechas, format="%Y-%m-%d", errors="coerce")
        dt_invertido = pd.to_datetime(s_fechas, format="%Y-%d-%m", errors="coerce")

        if (
            (dt_directo.dt.year == int(anio_op)) & (dt_directo.dt.month == int(mes_op))
        ).sum() >= (
            (dt_invertido.dt.year == int(anio_op))
            & (dt_invertido.dt.month == int(mes_op))
        ).sum():
            rutas["Fecha_dt"] = dt_directo
        else:
            rutas["Fecha_dt"] = dt_invertido

        rutas["CodVend"] = pd.to_numeric(rutas[col_vend_r], errors="coerce").astype(
            "Int64"
        )
        rutas_mes = rutas[
            (
                (rutas["Fecha_dt"].dt.year == int(anio_op))
                & (rutas["Fecha_dt"].dt.month == int(mes_op))
            )
        ].copy()

        dia_v_dt = parsear_fecha_robusta(pd.Series([dia_venta])).iloc[0]
        corte_date = dia_v_dt.date() if pd.notna(dia_v_dt) else None

        pasadas = (
            rutas_mes[rutas_mes["Fecha_dt"].dt.date <= corte_date]
            if corte_date is not None
            else rutas_mes
        )
        restantes_base = (
            rutas_mes[rutas_mes["Fecha_dt"].dt.date > corte_date]
            if corte_date is not None
            else rutas_mes
        )

        dias_pasados_map = pasadas.groupby("CodVend")["Fecha_dt"].nunique().to_dict()
        dias_restantes_base_map = (
            restantes_base.groupby("CodVend")["Fecha_dt"].nunique().to_dict()
        )

        for cv, dr_b in dias_restantes_base_map.items():
            cv_clean_str = str(int(cv)) if pd.notna(cv) else ""
            desc = rutas_ajust_map_g.get(cv_clean_str, 0) if cv_clean_str else 0
            if modo_ajuste == "AJUSTADO":
                dias_restantes_map[cv] = max(0, dr_b - desc)
            else:
                dias_restantes_map[cv] = dr_b

        total_dias_pasados_val = int(pasadas["Fecha_dt"].nunique())
        if dias_restantes_map:
            total_dias_restantes_val = int(
                pd.Series(list(dias_restantes_map.values())).mean()
            )
        else:
            total_dias_restantes_val = int(restantes_base["Fecha_dt"].nunique())
    print(
        f"[PERF_INTERNAL] procesamiento_rutas_y_dias = {time.perf_counter() - t_s6:.2f} s"
    )

    df_operativo_ger = (
        df_vta_prep_ger[
            df_vta_prep_ger["Periodo"].isin(["Arrastre", "Actual"])
            & df_vta_prep_ger["SEGMENTO"].notna()
            & (df_vta_prep_ger["SEGMENTO"] != "SIN SEGMENTO")
        ].copy()
        if not df_vta_prep_ger.empty
        else pd.DataFrame()
    )

    kilos_oper_todo = pd.DataFrame()

    t_s7 = time.perf_counter()
    if not df_operativo_ger.empty:
        df_operativo_ger["CodVend_Clean"] = pd.to_numeric(
            df_operativo_ger["CodVendedor"], errors="coerce"
        ).astype("Int64")
        df_operativo_ger["Supervisor"] = (
            df_operativo_ger["CodVend_Clean"].astype(str).map(sup_map).fillna("GENERAL")
        )

        df_operativo_ger["Días_Pasados"] = (
            df_operativo_ger["CodVend_Clean"].map(dias_pasados_map).fillna(1.0)
        )
        df_operativo_ger["Días_Restantes"] = (
            df_operativo_ger["CodVend_Clean"].map(dias_restantes_map).fillna(0.0)
        )

        arrastre_g = (
            df_operativo_ger[df_operativo_ger["Periodo"] == "Arrastre"]
            .groupby(["CodVendedor", "Supervisor", "SEGMENTO"], as_index=False)
            .agg(Arrastre=("PesoKg", "sum"), Arrastre_Gross=("ImporteNetoItem", "sum"))
        )
        actual_g = (
            df_operativo_ger[df_operativo_ger["Periodo"] == "Actual"]
            .groupby(["CodVendedor", "Supervisor", "SEGMENTO"], as_index=False)
            .agg(
                Actual=("PesoKg", "sum"),
                Actual_Gross=("ImporteNetoItem", "sum"),
                Dias_Pasados=("Días_Pasados", "first"),
                Dias_Restantes=("Días_Restantes", "first"),
            )
        )

        vend_seg_g = arrastre_g.merge(
            actual_g, on=["CodVendedor", "Supervisor", "SEGMENTO"], how="outer"
        ).fillna(0.0)
        vend_seg_g["Operativo_K"] = vend_seg_g["Arrastre"] + vend_seg_g["Actual"]
        vend_seg_g["Operativo_G"] = (
            vend_seg_g["Arrastre_Gross"] + vend_seg_g["Actual_Gross"]
        )

        dp_v = vend_seg_g["Dias_Pasados"].replace(0, 1.0)
        dr_v = vend_seg_g["Dias_Restantes"]

        p_diario_k = vend_seg_g["Actual"] / dp_v
        p_diario_g = vend_seg_g["Actual_Gross"] / dp_v

        vend_seg_g["Proyectado_Todo_K"] = vend_seg_g["Operativo_K"]
        vend_seg_g["Proyectado_Todo_G"] = vend_seg_g["Operativo_G"]

        mask_p = (dr_v > 0) & (vend_seg_g["CodVendedor"] != 20)
        if mask_p.any():
            vend_seg_g.loc[mask_p, "Proyectado_Todo_K"] = (
                p_diario_k[mask_p] * dr_v[mask_p]
            ) + vend_seg_g.loc[mask_p, "Operativo_K"]
            vend_seg_g.loc[mask_p, "Proyectado_Todo_G"] = (
                p_diario_g[mask_p] * dr_v[mask_p]
            ) + vend_seg_g.loc[mask_p, "Operativo_G"]

        kilos_oper_todo = (
            vend_seg_g.groupby(["Supervisor", "SEGMENTO"], as_index=False)
            .agg(
                {
                    "Arrastre": "sum",
                    "Actual": "sum",
                    "Operativo_K": "sum",
                    "Proyectado_Todo_K": "sum",
                    "Arrastre_Gross": "sum",
                    "Actual_Gross": "sum",
                    "Operativo_G": "sum",
                    "Proyectado_Todo_G": "sum",
                }
            )
            .rename(
                columns={
                    "Operativo_K": "Kilos_Operativos_Kg",
                    "Proyectado_Todo_K": "Kilos_Proyectados_Kg",
                    "Arrastre_Gross": "Gross_Arrastre",
                    "Actual_Gross": "Gross_Actual",
                    "Operativo_G": "Importe_Operativo_Arg",
                    "Proyectado_Todo_G": "Gross_Proyectado_Arg",
                }
            )
        )
    print(
        f"[PERF_INTERNAL] calculo_kilos_operativos_y_proyecciones = {time.perf_counter() - t_s7:.2f} s"
    )

    df_futuro = (
        df_vta_prep_ger_full[
            (df_vta_prep_ger_full["Periodo"] == "Futuro")
            & df_vta_prep_ger_full["SEGMENTO"].notna()
            & (df_vta_prep_ger_full["SEGMENTO"] != "SIN SEGMENTO")
        ].copy()
        if not df_vta_prep_ger_full.empty
        else pd.DataFrame()
    )

    t_s8 = time.perf_counter()
    if not df_futuro.empty:
        df_futuro["CodVen_Clean"] = pd.to_numeric(
            df_futuro["CodVendedor"], errors="coerce"
        ).astype("Int64")
        df_futuro["Supervisor"] = (
            df_futuro["CodVen_Clean"].astype(str).map(sup_map).fillna("GENERAL")
        )

        futuro_seg_agg = df_futuro.groupby(
            ["Supervisor", "SEGMENTO"], as_index=False
        ).agg(
            Kilos_Disponibles=("PesoKg", "sum"),
            Gross_Disponible=("ImporteNetoItem", "sum"),
        )
    else:
        futuro_seg_agg = pd.DataFrame(
            columns=["Supervisor", "SEGMENTO", "Kilos_Disponibles", "Gross_Disponible"]
        )
    print(
        f"[PERF_INTERNAL] agrupacion_ventas_futuras = {time.perf_counter() - t_s8:.2f} s"
    )

    kilos_obj_g = pd.DataFrame(
        columns=["Supervisor", "SEGMENTO", "Objetivo_Kilos_Kg", "Objetivo_Importe_Arg"]
    )
    t_s9 = time.perf_counter()
    if (
        not maestro_cebe.empty
        and not df_vta_prep_ger.empty
        and "Marca" in df_vta_prep_ger.columns
    ):
        col_m_cebe = next(
            (c for c in maestro_cebe.columns if "marca" in str(c).strip().lower()),
            maestro_cebe.columns[0],
        )
        col_obj_tn = next(
            (
                c
                for c in maestro_cebe.columns
                if any(k in str(c).strip().lower() for k in ["obj_tn", "tn", "obj_mes"])
            ),
            None,
        )
        col_obj_gross = next(
            (
                c
                for c in maestro_cebe.columns
                if any(k in str(c).strip().lower() for k in ["obj_gross", "gross"])
            ),
            None,
        )

        if col_obj_tn and col_obj_gross:
            maestro_cebe_clean = maestro_cebe.copy()
            maestro_cebe_clean["Marca_Key"] = (
                maestro_cebe_clean[col_m_cebe]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
            )

            maestro_cebe_clean["Obj_Val_Kg"] = pd.to_numeric(
                maestro_cebe_clean[col_obj_tn], errors="coerce"
            ).fillna(0.0)
            maestro_cebe_clean["Obj_Val_Imp"] = pd.to_numeric(
                maestro_cebe_clean[col_obj_gross], errors="coerce"
            ).fillna(0.0)

            mapa_obj_kg = (
                maestro_cebe_clean.groupby("Marca_Key")["Obj_Val_Kg"].sum().to_dict()
            )
            mapa_obj_imp = (
                maestro_cebe_clean.groupby("Marca_Key")["Obj_Val_Imp"].sum().to_dict()
            )

            df_vta_prep_ger["CodVen_Clean"] = pd.to_numeric(
                df_vta_prep_ger["CodVendedor"], errors="coerce"
            ).astype("Int64")
            df_vta_prep_ger["Supervisor"] = (
                df_vta_prep_ger["CodVen_Clean"]
                .astype(str)
                .map(sup_map)
                .fillna("GENERAL")
            )
            df_vta_prep_ger["Marca_Key"] = (
                df_vta_prep_ger["Marca"].astype(str).str.strip().str.upper()
            )

            tot_marca_vta = (
                df_vta_prep_ger[df_vta_prep_ger["SEGMENTO"] != "SIN SEGMENTO"]
                .groupby(["Supervisor", "Marca_Key", "SEGMENTO"])["PesoKg"]
                .sum()
                .reset_index()
            )
            tot_marca_vta["Total_Marca"] = (
                tot_marca_vta.groupby("Marca_Key")["PesoKg"]
                .transform("sum")
                .replace(0, 1.0)
            )
            tot_marca_vta["Part_Marca_Seg"] = (
                tot_marca_vta["PesoKg"] / tot_marca_vta["Total_Marca"]
            )

            tot_marca_vta["Obj_Kilos_Marca"] = (
                tot_marca_vta["Marca_Key"].map(mapa_obj_kg).fillna(0.0)
            )
            tot_marca_vta["Obj_Gross_Marca"] = (
                tot_marca_vta["Marca_Key"].map(mapa_obj_imp).fillna(0.0)
            )

            tot_marca_vta["Obj_Seg_Kg"] = (
                tot_marca_vta["Obj_Kilos_Marca"] * tot_marca_vta["Part_Marca_Seg"]
            )
            tot_marca_vta["Obj_Seg_Imp"] = (
                tot_marca_vta["Obj_Gross_Marca"] * tot_marca_vta["Part_Marca_Seg"]
            )

            kilos_obj_g = tot_marca_vta.groupby(
                ["Supervisor", "SEGMENTO"], as_index=False
            ).agg(
                Objetivo_Kilos_Kg=("Obj_Seg_Kg", "sum"),
                Objetivo_Importe_Arg=("Obj_Seg_Imp", "sum"),
            )
    print(
        f"[PERF_INTERNAL] calculo_objetivos_maestro_cebe = {time.perf_counter() - t_s9:.2f} s"
    )

    filtros_globales_base = {
        "anio": anio_op,
        "mes": mes_op,
        "dia_matinal": dia_matinal,
        "dia_venta": dia_venta,
        "supervisor": sup_seleccionado,
    }

    t_s10 = time.perf_counter()
    from modules.rep_MN import generar_reporte_mn_taxonomia

    rep_mn_global = generar_reporte_mn_taxonomia(
        df_vta, df_universo, maestro_v, filtros_globales_base
    )
    print(
        f"[PERF_INTERNAL] generar_reporte_mn_taxonomia_ger = {time.perf_counter() - t_s10:.2f} s"
    )

    cartera_base_global = st.session_state.get("_cob_cartera_base", pd.DataFrame())
    vtas_agrup_global = st.session_state.get("_cob_vtas_agrupadas", pd.DataFrame())
    marcas_lst = st.session_state.get("_cob_marcas", [])
    mapa_obj = st.session_state.get("_cob_mapa_objetivos", {})

    t_s11 = time.perf_counter()
    if cartera_base_global.empty or not marcas_lst:
        from modules.rep_cob_marca import generar_reporte_cobertura_marca

        generar_reporte_cobertura_marca(
            df_vta, df_universo, maestro_v, df_marcas_maestro, filtros_globales_base
        )
        cartera_base_global = st.session_state.get("_cob_cartera_base", pd.DataFrame())
        vtas_agrup_global = st.session_state.get("_cob_vtas_agrupadas", pd.DataFrame())
        marcas_lst = st.session_state.get("_cob_marcas", [])
        mapa_obj = st.session_state.get("_cob_mapa_objetivos", {})
    print(
        f"[PERF_INTERNAL] recuperacion_cache_cobertura_marca = {time.perf_counter() - t_s11:.2f} s"
    )

    t_s12 = time.perf_counter()
    res_gross_mn, res_kilos_mn, res_ccc_mn = _calcular_minegocio_taxonomia_detallado(
        df_vta_prep_ger,
        df_universo,
        maestro_v,
        anio_op,
        mes_op,
        dia_matinal,
        sup_seleccionado,
    )
    print(
        f"[PERF_INTERNAL] _calcular_minegocio_taxonomia_detallado = {time.perf_counter() - t_s12:.2f} s"
    )

    print(
        f"[PERF_INTERNAL] _calcular_motor_gerencial_global = {time.perf_counter() - t_start:.2f} s"
    )
    return (
        kilos_obj_g,
        kilos_oper_todo,
        futuro_seg_agg,
        rep_mn_global,
        cartera_base_global,
        vtas_agrup_global,
        marcas_lst,
        mapa_obj,
        res_gross_mn,
        res_kilos_mn,
        res_ccc_mn,
        total_dias_pasados_val,
        total_dias_restantes_val,
    )


def render_rep_gerencial(
    df_vta, df_universo, df_rutas, df_ausencias, filtros_globales=None
):
    t_start = time.perf_counter()
    st.subheader("📈 Tablero Ejecutivo Gerencial - Consolidado Integral")
    st.markdown(
        "Vista directiva completa con el desglose detallado por segmentos, taxonomías, marcas, kilos e importes de la compañía."
    )

    if filtros_globales is None:
        filtros_globales = {
            "anio": 2026,
            "mes": 9,
            "dia_matinal": "02/09/2026",
            "dia_venta": "01/09/2026",
            "supervisor": "TODOS",
        }

    anio_op = int(filtros_globales.get("anio", 2026))
    mes_op = int(filtros_globales.get("mes", 9))
    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026")
    dia_venta = filtros_globales.get("dia_venta", "01/09/2026")

    try:
        t_s1 = time.perf_counter()
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        col_sup_v = next(
            (c for c in maestro_v.columns if "sup" in str(c).strip().lower()),
            maestro_v.columns[2]
            if len(maestro_v.columns) > 2
            else maestro_v.columns[0],
        )
        supervisores_disp = ["TODOS"] + sorted(
            list(
                set(
                    str(s).strip()
                    for s in maestro_v[col_sup_v].dropna().unique()
                    if str(s).strip() != ""
                )
            )
        )
        print(
            f"[PERF_INTERNAL] consulta_sqlite_maestro_vendedores_render = {time.perf_counter() - t_s1:.2f} s"
        )
    except Exception:
        supervisores_disp = ["TODOS"]

    col_sup_sel, col_ajuste_sel, _ = st.columns([2, 2, 3])
    with col_sup_sel:
        sup_seleccionado = st.selectbox(
            "Filtrar Tablero por Supervisor",
            options=supervisores_disp,
            index=0,
            key="gerencial_filtro_sup",
        )
    with col_ajuste_sel:
        modo_ajuste_ger = st.selectbox(
            "Ajuste por Entrega",
            options=["TODO", "AJUSTADO"],
            index=1,
            key="gerencial_filtro_ajuste",
        )

    huella_global = f"{len(df_vta)}_{len(df_universo)}_{anio_op}_{mes_op}_{dia_matinal}_{sup_seleccionado}_{modo_ajuste_ger}"

    t_s2 = time.perf_counter()
    (
        kilos_obj_det_global,
        kilos_oper_todo,
        futuro_agg_global,
        rep_mn_global,
        cartera_base_global,
        vtas_agrup_global,
        marcas_lst,
        mapa_obj,
        res_gross_mn,
        res_kilos_mn,
        res_ccc_mn,
        dias_pasados_tot,
        dias_restantes_tot,
    ) = _calcular_motor_gerencial_global(
        df_vta,
        df_universo,
        df_rutas,
        df_ausencias,
        anio_op,
        mes_op,
        dia_matinal,
        dia_venta,
        sup_seleccionado,
        modo_ajuste_ger,
        huella_global,
    )
    print(
        f"[PERF_INTERNAL] _calcular_motor_gerencial_global_ejecucion = {time.perf_counter() - t_s2:.2f} s"
    )

    # RENDERIZAR ETIQUETAS DE DÍAS PASADOS Y RESTANTES
    col_d1, col_d2, _ = st.columns([1, 1, 3])
    with col_d1:
        st.markdown(
            tarjeta_metrica_html(
                "DÍAS PASADOS", f"{dias_pasados_tot}", "#3b82f6", "1.1rem", "0.6rem"
            ),
            unsafe_allow_html=True,
        )
    with col_d2:
        st.markdown(
            tarjeta_metrica_html(
                f"DÍAS RESTANTES ({modo_ajuste_ger})",
                f"{dias_restantes_tot}",
                "#10b981",
                "1.1rem",
                "0.6rem",
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    t_s3 = time.perf_counter()
    kilos_operativos_g = (
        kilos_oper_todo[
            kilos_oper_todo["Supervisor"].astype(str).str.strip() == sup_seleccionado
        ]
        .groupby("SEGMENTO", as_index=False)
        .agg(
            {
                "Arrastre": "sum",
                "Actual": "sum",
                "Kilos_Operativos_Kg": "sum",
                "Importe_Operativo_Arg": "sum",
                "Kilos_Proyectados_Kg": "sum",
                "Gross_Proyectado_Arg": "sum",
            }
        )
        if sup_seleccionado != "TODOS"
        and not kilos_oper_todo.empty
        and "Supervisor" in kilos_oper_todo.columns
        else (
            kilos_oper_todo.groupby("SEGMENTO", as_index=False).agg(
                {
                    "Arrastre": "sum",
                    "Actual": "sum",
                    "Kilos_Operativos_Kg": "sum",
                    "Importe_Operativo_Arg": "sum",
                    "Kilos_Proyectados_Kg": "sum",
                    "Gross_Proyectado_Arg": "sum",
                }
            )
            if not kilos_oper_todo.empty
            else pd.DataFrame(
                columns=[
                    "SEGMENTO",
                    "Arrastre",
                    "Actual",
                    "Kilos_Operativos_Kg",
                    "Importe_Operativo_Arg",
                    "Kilos_Proyectados_Kg",
                    "Gross_Proyectado_Arg",
                ]
            )
        )
    )

    kilos_obj_g = (
        kilos_obj_det_global[
            kilos_obj_det_global["Supervisor"].astype(str).str.strip()
            == sup_seleccionado
        ]
        .groupby("SEGMENTO", as_index=False)
        .agg({"Objetivo_Kilos_Kg": "sum", "Objetivo_Importe_Arg": "sum"})
        if sup_seleccionado != "TODOS"
        and not kilos_obj_det_global.empty
        and "Supervisor" in kilos_obj_det_global.columns
        else (
            kilos_obj_det_global.groupby("SEGMENTO", as_index=False).agg(
                {"Objetivo_Kilos_Kg": "sum", "Objetivo_Importe_Arg": "sum"}
            )
            if not kilos_obj_det_global.empty
            else pd.DataFrame(
                columns=["SEGMENTO", "Objetivo_Kilos_Kg", "Objetivo_Importe_Arg"]
            )
        )
    )

    futuro_segmento = (
        futuro_agg_global[
            futuro_agg_global["Supervisor"].astype(str).str.strip() == sup_seleccionado
        ]
        .groupby("SEGMENTO", as_index=False)
        .agg({"Kilos_Disponibles": "sum", "Gross_Disponible": "sum"})
        if sup_seleccionado != "TODOS"
        and not futuro_agg_global.empty
        and "Supervisor" in futuro_agg_global.columns
        else (
            futuro_agg_global.groupby("SEGMENTO", as_index=False).agg(
                {"Kilos_Disponibles": "sum", "Gross_Disponible": "sum"}
            )
            if not futuro_agg_global.empty
            else pd.DataFrame(
                columns=["SEGMENTO", "Kilos_Disponibles", "Gross_Disponible"]
            )
        )
    )

    cartera_base = (
        cartera_base_global[
            cartera_base_global["SUP"].astype(str).str.strip() == sup_seleccionado
        ].copy()
        if not cartera_base_global.empty and "SUP" in cartera_base_global.columns
        else cartera_base_global.copy()
    )

    df_seg = kilos_obj_g.merge(kilos_operativos_g, on="SEGMENTO", how="outer").fillna(
        0.0
    )

    if not futuro_segmento.empty:
        df_seg = df_seg.merge(futuro_segmento, on="SEGMENTO", how="left").fillna(0.0)
    else:
        df_seg["Kilos_Disponibles"] = 0.0
        df_seg["Gross_Disponible"] = 0.0

    df_seg["Objetivo_Kilos_Kg"] = df_seg["Objetivo_Kilos_Kg"].round(2)
    df_seg["Objetivo_Importe_Arg"] = df_seg["Objetivo_Importe_Arg"].round(2)
    df_seg["Arrastre"] = df_seg["Arrastre"].round(2)
    df_seg["Actual"] = df_seg["Actual"].round(2)
    df_seg["Kilos_Operativos_Kg"] = df_seg["Kilos_Operativos_Kg"].round(2)
    df_seg["Importe_Operativo_Arg"] = df_seg["Importe_Operativo_Arg"].round(2)
    df_seg["Kilos_Proyectados_Kg"] = df_seg["Kilos_Proyectados_Kg"].round(2)
    df_seg["Gross_Proyectado_Arg"] = df_seg["Gross_Proyectado_Arg"].round(2)

    df_seg["Cumplimiento_Actual_Pct"] = (
        (
            df_seg["Importe_Operativo_Arg"]
            / df_seg["Objetivo_Importe_Arg"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    df_seg["Cumplimiento_Proyectado_Pct"] = (
        (df_seg["Kilos_Proyectados_Kg"] / df_seg["Objetivo_Kilos_Kg"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    df_seg["Cumplimiento_Gross_Proy_Pct"] = (
        (
            df_seg["Gross_Proyectado_Arg"]
            / df_seg["Objetivo_Importe_Arg"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    df_seg["Cumplimiento_Gross_Actual_Pct"] = (
        (
            df_seg["Importe_Operativo_Arg"]
            / df_seg["Objetivo_Importe_Arg"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    df_seg["Raw_Bache_Kgs"] = (
        df_seg["Objetivo_Kilos_Kg"] - df_seg["Kilos_Proyectados_Kg"]
    ).clip(lower=0)
    df_seg["Raw_Bache_Gross"] = (
        df_seg["Objetivo_Importe_Arg"] - df_seg["Gross_Proyectado_Arg"]
    ).clip(lower=0)

    tot_obj_kilos = float(df_seg["Objetivo_Kilos_Kg"].sum())
    tot_proy_k = float(df_seg["Kilos_Proyectados_Kg"].sum())
    global_gap_kilos = max(0.0, tot_obj_kilos - tot_proy_k)

    tot_obj_gross = float(df_seg["Objetivo_Importe_Arg"].sum())
    tot_proy_g = float(df_seg["Gross_Proyectado_Arg"].sum())
    global_gap_gross = max(0.0, tot_obj_gross - tot_proy_g)

    sum_baches_kilos = df_seg["Raw_Bache_Kgs"].sum()
    factor_kilos = (
        (global_gap_kilos / sum_baches_kilos) if sum_baches_kilos > 0 else 0.0
    )

    sum_baches_gross = df_seg["Raw_Bache_Gross"].sum()
    factor_gross = (
        (global_gap_gross / sum_baches_gross) if sum_baches_gross > 0 else 0.0
    )

    df_seg["Futuro_A_Incorporar_Kgs"] = (df_seg["Raw_Bache_Kgs"] * factor_kilos).round(
        2
    )
    df_seg["Futuro_A_Incorporar_Gross"] = (
        df_seg["Raw_Bache_Gross"] * factor_gross
    ).round(2)

    orden_segmentos_maestro = [
        "GOLD Salty",
        "GOLD Crakers",
        "SILVER Salty",
        "SILVER Crakers",
        "SILVER Cereals",
    ]
    mapping_orden = {
        str(seg).strip(): i for i, seg in enumerate(orden_segmentos_maestro)
    }
    df_seg["_orden_idx"] = (
        df_seg["SEGMENTO"].astype(str).str.strip().map(mapping_orden).fillna(999)
    )
    df_seg = (
        df_seg.sort_values(by="_orden_idx")
        .drop(columns=["_orden_idx"])
        .reset_index(drop=True)
    )

    df_gross_seg = (
        df_seg[
            [
                "SEGMENTO",
                "Objetivo_Importe_Arg",
                "Importe_Operativo_Arg",
                "Cumplimiento_Gross_Actual_Pct",
                "Gross_Proyectado_Arg",
                "Cumplimiento_Gross_Proy_Pct",
                "Futuro_A_Incorporar_Gross",
                "Gross_Disponible",
            ]
        ]
        .copy()
        .rename(
            columns={
                "Objetivo_Importe_Arg": "Objetivo Gross Pepsico",
                "Importe_Operativo_Arg": "Operativo Gross",
                "Cumplimiento_Gross_Actual_Pct": "% Cump. Actual Gross",
                "Gross_Proyectado_Arg": "Proyectado Gross",
                "Cumplimiento_Gross_Proy_Pct": "% Cumpl. Proy. Gross",
                "Futuro_A_Incorporar_Gross": "A Incorporar Gross",
                "Gross_Disponible": "Gross Disponible",
            }
        )
    )

    df_gross_display = df_gross_seg.copy()
    for col in [
        "Objetivo Gross Pepsico",
        "Operativo Gross",
        "Proyectado Gross",
        "A Incorporar Gross",
        "Gross Disponible",
    ]:
        df_gross_display[col] = df_gross_display[col].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
        )
    for col in ["% Cump. Actual Gross", "% Cumpl. Proy. Gross"]:
        df_gross_display[col] = df_gross_display[col].apply(
            lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%"
        )

    tot_operativo_g = float(df_seg["Importe_Operativo_Arg"].sum())
    cump_actual_g_val = round(
        (tot_operativo_g / tot_obj_gross * 100.0) if tot_obj_gross > 0 else 0.0, 2
    )
    cump_proy_g_val = round(
        (tot_proy_g / tot_obj_gross * 100.0) if tot_obj_gross > 0 else 0.0, 2
    )
    tot_incorporar_g = float(df_gross_seg["A Incorporar Gross"].sum())

    df_kilos_seg = (
        df_seg[
            [
                "SEGMENTO",
                "Objetivo_Kilos_Kg",
                "Arrastre",
                "Actual",
                "Kilos_Operativos_Kg",
                "Cumplimiento_Actual_Pct",
                "Kilos_Proyectados_Kg",
                "Cumplimiento_Proyectado_Pct",
                "Futuro_A_Incorporar_Kgs",
                "Kilos_Disponibles",
            ]
        ]
        .copy()
        .rename(
            columns={
                "Objetivo_Kilos_Kg": "Objetivo Kilos Pepsico",
                "Arrastre": "Arrastre Kilos",
                "Actual": "Mes Actual Kilos",
                "Kilos_Operativos_Kg": "Operativo Kilos",
                "Cumplimiento_Actual_Pct": "% Cump. Actual Kilos",
                "Kilos_Proyectados_Kg": "Proyectado Kilos",
                "Cumplimiento_Proyectado_Pct": "% Cump. Proy. Kilos",
                "Futuro_A_Incorporar_Kgs": "A Incorporar Kilos",
                "Kilos_Disponibles": "Kilos Disponibles",
            }
        )
    )

    df_kilos_display = df_kilos_seg.copy()
    for col in [
        "Objetivo Kilos Pepsico",
        "Arrastre Kilos",
        "Mes Actual Kilos",
        "Operativo Kilos",
        "Proyectado Kilos",
        "A Incorporar Kilos",
        "Kilos Disponibles",
    ]:
        df_kilos_display[col] = df_kilos_display[col].apply(
            lambda x: f"{x:,.2f} kg" if pd.notna(x) else "0.00 kg"
        )
    for col in ["% Cump. Actual Kilos", "% Cump. Proy. Kilos"]:
        df_kilos_display[col] = df_kilos_display[col].apply(
            lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%"
        )

    tot_operativo_k = float(df_seg["Kilos_Operativos_Kg"].sum())
    cump_actual_k_val = round(
        (tot_operativo_k / tot_obj_kilos * 100.0) if tot_obj_kilos > 0 else 0.0, 2
    )
    cump_proy_k_val = round(
        (tot_proy_k / tot_obj_kilos * 100.0) if tot_obj_kilos > 0 else 0.0, 2
    )
    tot_incorporar_k = float(df_kilos_seg["A Incorporar Kilos"].sum())

    t_s4 = time.perf_counter()
    df_ccc_tax_raw, df_ccc_display = _calcular_ccc_taxonomia_gerencial(
        df_vta, df_universo, maestro_v, anio_op, mes_op, dia_matinal, sup_seleccionado
    )
    print(
        f"[PERF_INTERNAL] _calcular_ccc_taxonomia_gerencial_ejecucion = {time.perf_counter() - t_s4:.2f} s"
    )

    tot_cartera_ger = (
        int(df_ccc_tax_raw["Cartera_Neta"].sum()) if not df_ccc_tax_raw.empty else 0
    )
    tot_obj_pep_ger = (
        float(df_ccc_tax_raw["Obj_Pepsico"].sum()) if not df_ccc_tax_raw.empty else 0.0
    )
    tot_obj_fv_ger = (
        float(df_ccc_tax_raw["Obj_Fuerza_Ventas"].sum())
        if not df_ccc_tax_raw.empty
        else 0.0
    )
    tot_avance_ccc_ger = (
        int(df_ccc_tax_raw["Avance_CCC"].sum()) if not df_ccc_tax_raw.empty else 0
    )

    cump_pep_ger_pct = (
        (tot_avance_ccc_ger / tot_obj_pep_ger * 100.0) if tot_obj_pep_ger > 0 else 0.0
    )
    cump_fv_ger_pct = (
        (tot_avance_ccc_ger / tot_obj_fv_ger * 100.0) if tot_obj_fv_ger > 0 else 0.0
    )

    tot_ventas_mn_ger = (
        float(res_gross_mn["Gross_Total"].sum()) if not res_gross_mn.empty else 0.0
    )
    tot_app_mn_ger = (
        float(res_gross_mn["Gross_MN"].sum()) if not res_gross_mn.empty else 0.0
    )
    pct_venta_mn_ger = (
        (tot_app_mn_ger / tot_ventas_mn_ger * 100.0) if tot_ventas_mn_ger > 0 else 0.0
    )

    tot_cartera_mn_ger = (
        int(res_ccc_mn["Cartera_Total"].sum()) if not res_ccc_mn.empty else 0
    )
    tot_nodig_mn_ger = (
        int(res_ccc_mn["No Digital"].sum()) if not res_ccc_mn.empty else 0
    )
    tot_hibr_mn_ger = int(res_ccc_mn["Híbridos"].sum()) if not res_ccc_mn.empty else 0
    tot_fully_mn_ger = (
        int(res_ccc_mn["Fully Digital"].sum()) if not res_ccc_mn.empty else 0
    )

    df_gross_mn_disp = res_gross_mn.copy()
    df_gross_mn_disp["Gross_Total"] = df_gross_mn_disp["Gross_Total"].apply(
        lambda x: f"${x:,.2f}"
    )
    df_gross_mn_disp["Gross_MN"] = df_gross_mn_disp["Gross_MN"].apply(
        lambda x: f"${x:,.2f}"
    )
    df_gross_mn_disp["Adopcion_Gross_Pct"] = df_gross_mn_disp[
        "Adopcion_Gross_Pct"
    ].apply(lambda x: f"{x:,.2f}%")
    df_gross_mn_disp = df_gross_mn_disp.rename(
        columns={
            "Taxonomia": "Taxonomía",
            "Gross_Total": "Gross Total ($)",
            "Gross_MN": "Gross MiNegocio ($)",
            "Adopcion_Gross_Pct": "% Adopción Gross",
        }
    )

    df_kilos_mn_disp = res_kilos_mn.copy()
    df_kilos_mn_disp["Kilos_Total"] = df_kilos_mn_disp["Kilos_Total"].apply(
        lambda x: f"{x:,.2f} kg"
    )
    df_kilos_mn_disp["Kilos_MN"] = df_kilos_mn_disp["Kilos_MN"].apply(
        lambda x: f"{x:,.2f} kg"
    )
    df_kilos_mn_disp["Adopcion_Kilos_Pct"] = df_kilos_mn_disp[
        "Adopcion_Kilos_Pct"
    ].apply(lambda x: f"{x:,.2f}%")
    df_kilos_mn_disp = df_kilos_mn_disp.rename(
        columns={
            "Taxonomia": "Taxonomía",
            "Kilos_Total": "Kilos Totales (kg)",
            "Kilos_MN": "Kilos MiNegocio (kg)",
            "Adopcion_Kilos_Pct": "% Adopción Kilos",
        }
    )

    df_ccc_mn_disp = res_ccc_mn.copy()
    df_ccc_mn_disp["Cartera_Total"] = df_ccc_mn_disp["Cartera_Total"].apply(
        lambda x: f"{int(x):,}"
    )
    df_ccc_mn_disp["CCC_Total"] = df_ccc_mn_disp["CCC_Total"].apply(
        lambda x: f"{int(x):,}"
    )
    df_ccc_mn_disp["No Digital"] = df_ccc_mn_disp["No Digital"].apply(
        lambda x: f"{int(x):,}"
    )
    df_ccc_mn_disp["Híbridos"] = df_ccc_mn_disp["Híbridos"].apply(
        lambda x: f"{int(x):,}"
    )
    df_ccc_mn_disp["Fully Digital"] = df_ccc_mn_disp["Fully Digital"].apply(
        lambda x: f"{int(x):,}"
    )
    df_ccc_mn_disp = df_ccc_mn_disp.rename(
        columns={
            "Taxonomia": "Taxonomía",
            "Cartera_Total": "Cartera / Clientes",
            "CCC_Total": "Clientes con Compra (CCC)",
            "No Digital": "No Digital (CCC)",
            "Híbridos": "Híbridos (CCC)",
            "Fully Digital": "Fully Digital (CCC)",
        }
    )

    t_s5 = time.perf_counter()
    registros_marca = []
    total_cartera_global = len(cartera_base) if not cartera_base.empty else 0
    if not cartera_base.empty and marcas_lst:
        clientes_unicos_cartera = set(cartera_base["Cliente_Cod"].unique())
        for m in marcas_lst:
            obj_m = mapa_obj.get(m, 80.0)
            if not vtas_agrup_global.empty:
                if (
                    sup_seleccionado != "TODOS"
                    and "CodVendedor" in vtas_agrup_global.columns
                    and "CodVendedor" in cartera_base.columns
                ):
                    vta_m_filt = vtas_agrup_global[
                        vtas_agrup_global["CodVendedor"].isin(
                            cartera_base["CodVendedor"]
                        )
                    ]
                else:
                    vta_m_filt = vtas_agrup_global

                cubiertos_m = vta_m_filt[
                    vta_m_filt["Cliente"].isin(clientes_unicos_cartera)
                    & (vta_m_filt["Marca"] == m)
                    & (vta_m_filt["Total_Cant"] >= 3)
                ]["Cliente"].nunique()
            else:
                cubiertos_m = 0

            cob_real_pct = (
                (cubiertos_m / total_cartera_global * 100.0)
                if total_cartera_global > 0
                else 0.0
            )
            cumpl_marca_pct = (cob_real_pct / obj_m * 100.0) if obj_m > 0 else 0.0

            registros_marca.append(
                {
                    "Marca": m,
                    "Objetivo_Cobertura_Marca_Pct": round(obj_m, 2),
                    "Clientes_Cubiertos": cubiertos_m,
                    "Cartera_Total": total_cartera_global,
                    "Cobertura_Real_Operativa_Pct": round(cob_real_pct, 2),
                    "Cumplimiento_Cobertura_Marca_Pct": round(cumpl_marca_pct, 2),
                }
            )
    df_marcas_res = pd.DataFrame(registros_marca)
    print(
        f"[PERF_INTERNAL] calculo_cobertura_marcas_gerencial = {time.perf_counter() - t_s5:.2f} s"
    )

    tab_k, tab_c, tab_mn, tab_m = st.tabs(
        [
            "📦 Kilos e Importes por Segmento",
            "📈 CCC por Taxonomía",
            "📱 MiNegocio por Taxonomía",
            "🎯 Cobertura por Marca",
        ]
    )

    with tab_k:
        st.markdown("### 💰 1. Desglose Financiero (Gross / Importes)")
        col_proy_g1, col_proy_g2, col_proy_g3 = st.columns([1, 2, 1])
        with col_proy_g2:
            st.markdown(
                tarjeta_metrica_html(
                    "📊 PROYECTADO GROSS",
                    f"${tot_proy_g:,.0f}",
                    "#ef4444",
                    "2.2rem",
                    "1.1rem",
                ),
                unsafe_allow_html=True,
            )

        mi1, mi2, mi3, mi4, mi5 = st.columns(5)
        with mi1:
            st.markdown(
                tarjeta_metrica_html(
                    "💰 OBJ. GROSS",
                    f"${tot_obj_gross:,.0f}",
                    "#3b82f6",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mi2:
            st.markdown(
                tarjeta_metrica_html(
                    "💵 OPERATIVO GROSS",
                    f"${tot_operativo_g:,.0f}",
                    "#10b981",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mi3:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 CUMP. ACTUAL",
                    f"{cump_actual_g_val:,.2f}%",
                    "#8b5cf6",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mi4:
            st.markdown(
                tarjeta_metrica_html(
                    "📊 CUMP. PROY.",
                    f"{cump_proy_g_val:,.2f}%",
                    "#06b6d4",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mi5:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 A INCORPORAR",
                    f"${tot_incorporar_g:,.0f}",
                    "#f59e0b",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )

        st.dataframe(df_gross_display, width="stretch", hide_index=True)

        buf_g = io.BytesIO()
        with pd.ExcelWriter(buf_g, engine="openpyxl") as w:
            df_gross_seg.to_excel(w, index=False, sheet_name="Gross_Segmento")
        st.download_button(
            "📥 Descargar Gross / Importes a Excel",
            data=buf_g.getvalue(),
            file_name="gross_importes_por_segmento.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_gross_seg",
        )

        st.divider()
        st.markdown("### 📦 2. Desglose Operativo (Kilos / Volumen)")
        col_proy_k1, col_proy_k2, col_proy_k3 = st.columns([1, 2, 1])
        with col_proy_k2:
            st.markdown(
                tarjeta_metrica_html(
                    "🔮 PROYECTADO KILOS",
                    f"{tot_proy_k:,.0f} kg",
                    "#ef4444",
                    "2.2rem",
                    "1.1rem",
                ),
                unsafe_allow_html=True,
            )

        mk1, mk2, mk3, mk4, mk5 = st.columns(5)
        with mk1:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 OBJETIVO KILOS",
                    f"{tot_obj_kilos:,.0f} kg",
                    "#3b82f6",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mk2:
            st.markdown(
                tarjeta_metrica_html(
                    "📊 OPERATIVO KILOS",
                    f"{tot_operativo_k:,.0f} kg",
                    "#10b981",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mk3:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 CUMP. ACTUAL",
                    f"{cump_actual_k_val:,.2f}%",
                    "#8b5cf6",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mk4:
            st.markdown(
                tarjeta_metrica_html(
                    "📈 CUMP. PROY.",
                    f"{cump_proy_k_val:,.2f}%",
                    "#06b6d4",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mk5:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 A INCORPORAR",
                    f"${tot_incorporar_k:,.0f} kg",
                    "#f59e0b",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )

        st.dataframe(df_kilos_display, width="stretch", hide_index=True)

        buf_k = io.BytesIO()
        with pd.ExcelWriter(buf_k, engine="openpyxl") as w:
            df_kilos_seg.to_excel(w, index=False, sheet_name="Kilos_Segmento")
        st.download_button(
            "📥 Descargar Kilos / Volumen a Excel",
            data=buf_k.getvalue(),
            file_name="kilos_volumen_por_segmento.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_kilos_seg",
        )

    with tab_c:
        st.markdown(
            "### 📈 CCC por Taxonomía (Obj Pepsico, % Cump, Obj Fuerza de Ventas, % Cump y Avance CCC)"
        )

        cc1, cc2, cc3, cc4, cc5, cc6 = st.columns(6)
        with cc1:
            st.markdown(
                tarjeta_metrica_html(
                    "📋 CARTERA NETA",
                    f"{tot_cartera_ger:,.0f}",
                    "#ffffff",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with cc2:
            st.markdown(
                tarjeta_metrica_html(
                    "📦 CANTIDAD CCC",
                    f"{tot_avance_ccc_ger:,.0f}",
                    "#22c55e",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with cc3:
            st.markdown(
                tarjeta_metrica_html(
                    "🏢 OBJ. PEPSICO",
                    f"{tot_obj_pep_ger:,.0f}",
                    "#3b82f6",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with cc4:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 CUMP. PEPSICO",
                    f"{cump_pep_ger_pct:,.2f}%",
                    "#10b981",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with cc5:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 OBJ. F. VENTAS",
                    f"{tot_obj_fv_ger:,.0f}",
                    "#f59e0b",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with cc6:
            st.markdown(
                tarjeta_metrica_html(
                    "📈 CUMP. F. VENTAS",
                    f"{cump_fv_ger_pct:,.2f}%",
                    "#8b5cf6",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )

        st.divider()
        st.dataframe(df_ccc_display, width="stretch", hide_index=True)

        buf2 = io.BytesIO()
        with pd.ExcelWriter(buf2, engine="openpyxl") as w:
            df_ccc_tax_raw.to_excel(w, index=False, sheet_name="CCC_Taxonomia")
        st.download_button(
            "📥 Descargar CCC por Taxonomía a Excel",
            data=buf2.getvalue(),
            file_name="ccc_por_taxonomia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_ccc_tax",
        )

    with tab_mn:
        st.markdown(
            "### 📱 MiNegocio por Taxonomía (Desglose Híbrido: Gross, Kilos y CCC por App)"
        )

        mn1, mn2, mn3, mn4, mn5, mn6 = st.columns(6)
        with mn1:
            st.markdown(
                tarjeta_metrica_html(
                    "💰 VENTAS TOTALES",
                    f"${tot_ventas_mn_ger:,.2f}",
                    "#38bdf8",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with mn2:
            st.markdown(
                tarjeta_metrica_html(
                    "📱 VENTA APP (MN+)",
                    f"${tot_app_mn_ger:,.2f}",
                    "#38bdf8",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with mn3:
            st.markdown(
                tarjeta_metrica_html(
                    "📈 % VENTA APP",
                    f"{pct_venta_mn_ger:,.2f}%",
                    "#38bdf8",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with mn4:
            st.markdown(
                tarjeta_metrica_html(
                    "🔴 NO DIGITAL",
                    f"{tot_nodig_mn_ger:,.0f}",
                    "#ef4444",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with mn5:
            st.markdown(
                tarjeta_metrica_html(
                    "🟠 HÍBRIDOS",
                    f"{tot_hibr_mn_ger:,.0f}",
                    "#f97316",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with mn6:
            st.markdown(
                tarjeta_metrica_html(
                    "🟢 FULLY DIGITAL",
                    f"{tot_fully_mn_ger:,.0f}",
                    "#22c55e",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("#### 💰 1. Desglose Financiero Gross por Taxonomía")
        st.dataframe(df_gross_mn_disp, width="stretch", hide_index=True)
        buf_mn_g = io.BytesIO()
        with pd.ExcelWriter(buf_mn_g, engine="openpyxl") as w:
            res_gross_mn.to_excel(w, index=False, sheet_name="MiNegocio_Gross")
        st.download_button(
            "📥 Descargar Gross MiNegocio a Excel",
            data=buf_mn_g.getvalue(),
            file_name="minegocio_gross_por_taxonomia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_mn_gross",
        )

        st.divider()
        st.markdown("#### 📦 2. Desglose Operativo Kilos por Taxonomía")
        st.dataframe(df_kilos_mn_disp, width="stretch", hide_index=True)
        buf_mn_k = io.BytesIO()
        with pd.ExcelWriter(buf_mn_k, engine="openpyxl") as w:
            res_kilos_mn.to_excel(w, index=False, sheet_name="MiNegocio_Kilos")
        st.download_button(
            "📥 Descargar Kilos MiNegocio a Excel",
            data=buf_mn_k.getvalue(),
            file_name="minegocio_kilos_por_taxonomia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_mn_kilos",
        )

        st.divider()
        st.markdown(
            "#### 📋 3. Desglose CCC y Compradores por App (No Digital, Híbridos, Fully Digital)"
        )
        st.dataframe(df_ccc_mn_disp, width="stretch", hide_index=True)
        buf_mn_c = io.BytesIO()
        with pd.ExcelWriter(buf_mn_c, engine="openpyxl") as w:
            res_ccc_mn.to_excel(w, index=False, sheet_name="MiNegocio_CCC")
        st.download_button(
            "📥 Descargar CCC MiNegocio a Excel",
            data=buf_mn_c.getvalue(),
            file_name="minegocio_ccc_por_taxonomia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_mn_ccc",
        )

    with tab_m:
        st.markdown("### 🎯 Cobertura por Marca")
        st.dataframe(df_marcas_res, width="stretch", hide_index=True)

        buf4 = io.BytesIO()
        with pd.ExcelWriter(buf4, engine="openpyxl") as w:
            df_marcas_res.to_excel(w, index=False, sheet_name="Cobertura_Marca")
        st.download_button(
            "📥 Descargar Cobertura por Marca a Excel",
            data=buf4.getvalue(),
            file_name="cobertura_por_marca_resumen.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_marca_res",
        )

    print(
        f"[PERF_INTERNAL] render_rep_gerencial = {time.perf_counter() - t_start:.2f} s"
    )


====================================================================================================


### ARCHIVO: modules\rep_kilos.py

# modules/rep_kilos.py
import io
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import parsear_fecha_robusta

def preparar_datos_ventas_segmento(df_vta, df_ausencias, anio_operativo, mes_operativo, dia_matinal):
    """
    Pipeline de ventas optimizado para Kilos derivado del DataFrame Maestro N1 (EMPLEADOS).
    Aplica los filtros N2: PEPSICO, COMODATOS, MATINAL y PERIODO.
    """
    df_corp = db.obtener_df_maestro_corporativo()
    df = df_corp.copy() if not df_corp.empty else (df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame())
    
    if df.empty:
        return df

    df["PesoKg"] = pd.to_numeric(df.get("PesoKg", 0), errors="coerce").fillna(0.0)

    if "TipoDeVenta" in df.columns:
        tipos_excluidos = [
            "Comodato Devolución", 
            "Comodato Ficticio", 
            "Comodato Ficticio Devolución", 
            "Comodato Préstamo"
        ]
        df = df[~df["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)]

    if "Proveedor" in df.columns:
        df = df[
            df["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    dia_matinal_dt = pd.to_datetime(str(dia_matinal), format="%d/%m/%Y", errors="coerce")
    if pd.isna(dia_matinal_dt):
        dia_matinal_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    
    if pd.notna(dia_matinal_dt):
        es_mes_en_curso = (dia_matinal_dt.year == anio_operativo and dia_matinal_dt.month in [mes_operativo, mes_operativo + 1])
        if es_mes_en_curso:
            df = df[df["FechaCarga_dt"].dt.date <= dia_matinal_dt.date()]

    col_vend_tit = next((cand for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"] if cand in df.columns), "CodVendedor")
    if col_vend_tit not in df.columns:
        df[col_vend_tit] = 0

    df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype("Int64")

    col_m = next((c for c in ["Marca", "MARCA", "marca"] if c in df.columns), None)
    df["Marca"] = df[col_m].fillna("").astype(str).str.strip().str.upper() if col_m else "SIN MARCA"

    col_rent = "SegmentoRentabilidad" if "SegmentoRentabilidad" in df.columns else None
    col_rubro = "Rubro" if "Rubro" in df.columns else None
    
    sr = df.get(col_rent, pd.Series("", index=df.index)).fillna("").astype(str).str.strip().str.title() if col_rent else pd.Series("", index=df.index)
    rubro = df.get(col_rubro, pd.Series("", index=df.index)).fillna("").astype(str).str.strip() if col_rubro else pd.Series("", index=df.index)
    
    cond_gold = sr.isin(["Platinum", "Gold"]).fillna(False)
    cond_silver = sr.isin(["Silver", "Bronze"]).fillna(False)
    
    gold_val = "GOLD " + rubro
    silver_val = "SILVER " + rubro
    df["SEGMENTO"] = np.select(
        [cond_gold, cond_silver],
        [gold_val.str.strip(), silver_val.str.strip()],
        default=None
    )

    df["MesCarga"] = df["FechaCarga_dt"].dt.month
    df["AñoCarga"] = df["FechaCarga_dt"].dt.year
    df["MesEntrega"] = df["FechaEntrega_dt"].dt.month
    df["AñoEntrega"] = df["FechaEntrega_dt"].dt.year

    mes_ant = 12 if mes_operativo == 1 else mes_operativo - 1
    anio_ant = anio_operativo - 1 if mes_operativo == 1 else anio_operativo

    mes_sig = 1 if mes_operativo == 12 else mes_operativo + 1
    anio_sig = anio_operativo + 1 if mes_operativo == 12 else anio_operativo

    ac, mc = df["AñoCarga"], df["MesCarga"]
    ae, me = df["AñoEntrega"], df["MesEntrega"]
    
    cond_arr = ((ac == anio_ant) & (mc == mes_ant) & (ae == anio_operativo) & (me == mes_operativo)).fillna(False)
    cond_act = ((ac == anio_operativo) & (mc == mes_operativo) & (ae == anio_operativo) & (me == mes_operativo)).fillna(False)
    cond_fut = ((ac == anio_operativo) & (mc == mes_operativo) & (ae == anio_sig) & (me == mes_sig)).fillna(False)

    df["Periodo"] = np.select(
        [cond_arr, cond_act, cond_fut],
        ["Arrastre", "Actual", "Futuro"],
        default="Fuera de Periodo"
    )

    df["ClaveAUS_Carga"] = df["CodVendedor"].astype(str) + "-" + df["FechaCarga_dt"].dt.strftime("%Y-%m-%d")
    df["ClaveAUS_Entrega"] = df["CodVendedor"].astype(str) + "-" + df["FechaEntrega_dt"].dt.strftime("%Y-%m-%d")

    df_aus = df_ausencias.copy() if df_ausencias is not None and not df_ausencias.empty else pd.DataFrame()
    if not df_aus.empty:
        col_aus_vend = next((c for c in ["Ausente", "CodVend", "CodVendedor", "Vendedor", "Cod_Vendedor"] if c in df_aus.columns), df_aus.columns[3])
        col_aus_fecha = next((c for c in df_aus.columns if c in ["Fecha", "FechaAusencia", "Dia"]), df_aus.columns[2])
        col_aus_reemp = next((c for c in df_aus.columns if c in ["Reemplazo", "CodReemplazo", "Cod_Reemplazo", "PreventistaReemplazo"]), df_aus.columns[4])

        df_aus["Fecha_dt"] = parsear_fecha_robusta(df_aus[col_aus_fecha])
        df_aus["CodVend_clean"] = pd.to_numeric(df_aus[col_aus_vend], errors="coerce").astype("Int64")
        df_aus["ClaveAUS"] = df_aus["CodVend_clean"].astype(str) + "-" + df_aus["Fecha_dt"].dt.strftime("%Y-%m-%d")
        df_aus["Reemplazo_clean"] = pd.to_numeric(df_aus[col_aus_reemp], errors="coerce").astype("Int64")

        aus_map = df_aus.dropna(subset=["ClaveAUS", "Reemplazo_clean"]).drop_duplicates("ClaveAUS").set_index("ClaveAUS")["Reemplazo_clean"]
        
        df["Reemplazo"] = df["ClaveAUS_Carga"].map(aus_map).combine_first(df["ClaveAUS_Entrega"].map(aus_map))
        df["CodVendedorOperativo"] = df["Reemplazo"].combine_first(df["CodVendedor"]).astype("Int64")
    else:
        df["Reemplazo"] = pd.NA
        df["CodVendedorOperativo"] = df["CodVendedor"]

    return df

def generar_reporte_avance_kilos_segmento(df_vta_prep, df_rutas, maestro_vend, maestro_seg, maestro_cebe, dia_venta, anio_operativo, mes_operativo, sup_filtro):
    vendedores_rep = pd.DataFrame()
    col_cod = "Codigo_Vendedor" if "Codigo_Vendedor" in maestro_vend.columns else maestro_vend.columns[0]
    col_nom = "Nombre_Vendedor" if "Nombre_Vendedor" in maestro_vend.columns else maestro_vend.columns[1]
    col_sup = "Supervisor" if "Supervisor" in maestro_vend.columns else maestro_vend.columns[2]
    
    col_ajuste = next((c for c in maestro_vend.columns if str(c).strip().lower() in ["ajuste_entrega", "ajusteentrega", "dias_entrega"]), None)
    col_rutas_ajust = next((c for c in maestro_vend.columns if str(c).strip().lower() in ["rutas_ajustadas", "rutasajustadas", "ajustadas"]), None)

    vendedores_rep["CodVend"] = pd.to_numeric(maestro_vend[col_cod], errors="coerce").astype("Int64")
    vendedores_rep["Nombre"] = maestro_vend[col_nom].fillna("").astype(str).str.strip()
    vendedores_rep["SUP"] = maestro_vend[col_sup].fillna("").astype(str).str.strip()
    vendedores_rep["Ajuste_Entrega"] = pd.to_numeric(maestro_vend[col_ajuste], errors="coerce").fillna(1).astype(int) if col_ajuste else 1
    vendedores_rep["Rutas_Ajustadas"] = pd.to_numeric(maestro_vend[col_rutas_ajust], errors="coerce").fillna(0).astype(int) if col_rutas_ajust else 0
    
    vendedores_rep = vendedores_rep.dropna(subset=["CodVend"]).drop_duplicates(subset=["CodVend"])

    codigos_validos_padron = set(vendedores_rep["CodVend"].dropna().tolist())
    sup_map = vendedores_rep.set_index("CodVend")["SUP"].to_dict()
    ajuste_map = vendedores_rep.set_index("CodVend")["Ajuste_Entrega"].to_dict()
    rutas_ajust_map = vendedores_rep.set_index("CodVend")["Rutas_Ajustadas"].to_dict()

    df_vtas_op_temp = df_vta_prep[df_vta_prep["Periodo"].isin(["Arrastre", "Actual"]) & df_vta_prep["SEGMENTO"].notna()].copy()
    cods_en_ventas = df_vtas_op_temp["CodVendedor"].dropna().unique()
    for cv in cods_en_ventas:
        if cv not in codigos_validos_padron:
            val_int = int(cv)
            nuevo_v = pd.DataFrame({
                "CodVend": pd.Series([val_int], dtype="Int64"),
                "Nombre": [f"VENDEDOR {val_int}"],
                "SUP": ["GENERAL"],
                "Ajuste_Entrega": [1],
                "Rutas_Ajustadas": [0]
            })
            vendedores_rep = pd.concat([vendedores_rep, nuevo_v], ignore_index=True)
            sup_map[val_int] = "GENERAL"
            ajuste_map[val_int] = 1
            rutas_ajust_map[val_int] = 0

    orden_segmentos_maestro = [
        "GOLD Salty",
        "GOLD Crakers",
        "SILVER Salty",
        "SILVER Crakers",
        "SILVER Cereals"
    ]

    segs_vta_unicos = df_vta_prep["SEGMENTO"].dropna().astype(str).str.strip().unique()
    for s_v in segs_vta_unicos:
        if s_v not in orden_segmentos_maestro:
            orden_segmentos_maestro.append(s_v)

    segmentos_rep = pd.DataFrame({"SEGMENTO": orden_segmentos_maestro})

    df_comodines = pd.DataFrame({
        "CodVend": pd.Series([-998], dtype="Int64"),
        "Nombre": ["REEMPLAZO"],
        "SUP": ["GENERAL"],
        "Ajuste_Entrega": [0],
        "Rutas_Ajustadas": [0]
    })
    vendedores_rep_full = pd.concat([vendedores_rep, df_comodines], ignore_index=True)

    vendedores_rep_full["_k"] = 1
    segmentos_rep["_k"] = 1
    matriz = vendedores_rep_full.merge(segmentos_rep, on="_k").drop(columns="_k")

    df_vtas_op = df_vtas_op_temp
    
    cod_op = df_vtas_op["CodVendedorOperativo"]
    cod_tit = df_vtas_op["CodVendedor"]
    reemp = df_vtas_op.get("Reemplazo", pd.Series(pd.NA, index=df_vtas_op.index))
    
    is_special = ((reemp == 99) | (cod_op == 99) | (cod_tit == 99)).fillna(False)
    valid_op_mask = cod_op.isin(codigos_validos_padron).fillna(False)
    valid_tit_mask = cod_tit.isin(codigos_validos_padron).fillna(False)
    
    cod_op_series = cod_op.fillna(-999).astype(int)
    cod_tit_series = cod_tit.fillna(-999).astype(int)
    
    df_vtas_op["CodVend_Op"] = np.select(
        [is_special, valid_op_mask, valid_tit_mask],
        [-998, cod_op_series, cod_tit_series],
        default=cod_tit_series
    )
    df_vtas_op["CodVend_Op"] = pd.Series(df_vtas_op["CodVend_Op"]).replace(-999, pd.NA).astype("Int64")

    cond_op_998 = (df_vtas_op["CodVend_Op"] == -998).fillna(False)
    sup_from_op = df_vtas_op["CodVend_Op"].astype(str).map(sup_map)
    sup_from_tit = df_vtas_op["CodVendedor"].astype(str).map(sup_map)
    
    df_vtas_op["SUP_Transaccion"] = np.select(
        [cond_op_998],
        ["GENERAL"],
        default=sup_from_op.fillna(sup_from_tit).fillna("GENERAL")
    )
    df_vtas_op["SEGMENTO"] = df_vtas_op["SEGMENTO"].astype(str).str.strip()
    
    kilos = df_vtas_op.groupby(["CodVend_Op", "SEGMENTO", "Periodo"], dropna=False)["PesoKg"].sum().reset_index()
    kilos = kilos.rename(columns={"CodVend_Op": "CodVend"})
    
    if not kilos.empty:
        kilos_pivot = kilos.pivot_table(index=["CodVend", "SEGMENTO"], columns="Periodo", values="PesoKg", aggfunc="sum", fill_value=0.0).reset_index()
        kilos_pivot.columns.name = None
    else:
        kilos_pivot = pd.DataFrame(columns=["CodVend", "SEGMENTO", "Arrastre", "Actual"])

    for col_p in ["Arrastre", "Actual"]:
        if col_p not in kilos_pivot.columns:
            kilos_pivot[col_p] = 0.0

    reporte = matriz.merge(kilos_pivot[["CodVend", "SEGMENTO", "Arrastre", "Actual"]], on=["CodVend", "SEGMENTO"], how="left")
    reporte[["Arrastre", "Actual"]] = reporte[["Arrastre", "Actual"]].fillna(0.0)

    rutas = df_rutas.copy() if df_rutas is not None and not df_rutas.empty else pd.DataFrame()
    
    if not rutas.empty:
        col_fecha_r = next((c for c in ["Fecha", "fecha", "Dia", "Date", "FECHA"] if c in rutas.columns), rutas.columns[0])
        col_vend_r = next((c for c in ["codven", "CodVen", "CodVendedor", "Vendedor", "Cod_Vendedor", "CODVEN"] if c in rutas.columns), rutas.columns[1])

        s_fechas = rutas[col_fecha_r].astype(str).str.strip().str.replace(" 00:00:00", "", regex=False)
        dt_directo = pd.to_datetime(s_fechas, format="%Y-%m-%d", errors="coerce")
        dt_invertido = pd.to_datetime(s_fechas, format="%Y-%d-%m", errors="coerce")
        
        coincidencias_directo = ((dt_directo.dt.year == int(anio_operativo)) & (dt_directo.dt.month == int(mes_operativo))).fillna(False)
        coincidencias_invertido = ((dt_invertido.dt.year == int(anio_operativo)) & (dt_invertido.dt.month == int(mes_operativo))).fillna(False)
        
        if coincidencias_directo.sum() >= coincidencias_invertido.sum() and coincidencias_directo.sum() > 0:
            rutas["Fecha_dt"] = dt_directo
        elif coincidencias_invertido.sum() > 0:
            rutas["Fecha_dt"] = dt_invertido
        else:
            rutas["Fecha_dt"] = parsear_fecha_robusta(rutas[col_fecha_r])

        rutas["CodVend"] = pd.to_numeric(rutas[col_vend_r], errors="coerce").astype("Int64")

        rutas_mes = rutas[
            ((rutas["Fecha_dt"].dt.year == int(anio_operativo)) & 
            (rutas["Fecha_dt"].dt.month == int(mes_operativo))).fillna(False)
        ].copy()

        dia_v_dt = parsear_fecha_robusta(pd.Series([dia_venta])).iloc[0]
        corte_date = dia_v_dt.date() if pd.notna(dia_v_dt) else None

        if corte_date is not None:
            pasadas = rutas_mes[rutas_mes["Fecha_dt"].dt.date <= corte_date]
        else:
            pasadas = rutas_mes

        dias_pasados = pasadas.groupby("CodVend")["Fecha_dt"].nunique()
        dias_totales = rutas_mes.groupby("CodVend")["Fecha_dt"].nunique()

        reporte = reporte.merge(dias_pasados.rename("Días Pasados"), left_on="CodVend", right_index=True, how="left")
        reporte = reporte.merge(dias_totales.rename("Rutas"), left_on="CodVend", right_index=True, how="left")
    else:
        reporte["Días Pasados"] = 0
        reporte["Rutas"] = 0

    reporte["Días Pasados"] = reporte["Días Pasados"].fillna(0).astype("Int64")
    reporte["Rutas"] = reporte["Rutas"].fillna(0).astype("Int64")
    
    reporte["Ajuste_Entrega"] = reporte["CodVend"].map(ajuste_map).fillna(1).astype(int)
    reporte["Rutas_Ajustadas"] = reporte["CodVend"].map(rutas_ajust_map).fillna(0).astype(int)

    reporte["Días Restantes Todo"] = (reporte["Rutas"] - reporte["Días Pasados"]).clip(lower=0).astype("Int64")
    
    # APLICACIÓN DE RUTAS AJUSTADAS ESPECÍFICAS POR VENDEDOR
    dias_restantes_base = (reporte["Rutas"] - reporte["Días Pasados"]).clip(lower=0)
    reporte["Días Restantes Ajustado"] = (dias_restantes_base - reporte["Rutas_Ajustadas"]).clip(lower=0).astype("Int64")

    df_obj_db = db.cargar_tabla_sql(
        f"SELECT CodVendedor, SEGMENTO, Obj_Sugerido_Kg FROM objetivos_vendedores WHERE Anio = {int(anio_operativo)} AND Mes = {int(mes_operativo)}"
    )

    if not df_obj_db.empty:
        df_obj_db["CodVend"] = pd.to_numeric(df_obj_db["CodVendedor"], errors="coerce").astype("Int64")
        df_obj_db["SEGMENTO"] = df_obj_db["SEGMENTO"].fillna("").astype(str).str.strip()
        df_obj_db["Obj_Sugerido_Kg"] = pd.to_numeric(df_obj_db["Obj_Sugerido_Kg"], errors="coerce").fillna(0.0)
        
        objs_agrup = df_obj_db.groupby(["CodVend", "SEGMENTO"], as_index=False)["Obj_Sugerido_Kg"].sum()
        objs_agrup = objs_agrup.rename(columns={"Obj_Sugerido_Kg": "Objetivo Mes Corriente"})
        reporte = reporte.merge(objs_agrup, on=["CodVend", "SEGMENTO"], how="left")
    else:
        mes_ant = 12 if mes_operativo == 1 else mes_operativo - 1
        anio_ant = anio_operativo - 1 if mes_operativo == 1 else anio_operativo

        historial = df_vta_prep[
            (df_vta_prep["AñoEntrega"].eq(anio_ant)) & 
            (df_vta_prep["MesEntrega"].eq(mes_ant)) & 
            df_vta_prep["SEGMENTO"].notna()
        ].copy()

        if not historial.empty and maestro_cebe is not None and not maestro_cebe.empty and "Obj_Mes" in maestro_cebe.columns:
            historial["CodVend"] = pd.to_numeric(historial["CodVendedor"], errors="coerce").astype("Int64")
            col_m_cebe = next((c for c in maestro_cebe.columns if str(c).strip().lower() in ["marca", "marcaupper"]), maestro_cebe.columns[0])
            maestro_cebe_clean = maestro_cebe.copy()
            maestro_cebe_clean["Marca_Key"] = maestro_cebe_clean[col_m_cebe].fillna("").astype(str).str.strip().str.upper()
            maestro_cebe_clean["Obj_Mes_Val"] = pd.to_numeric(maestro_cebe_clean["Obj_Mes"], errors="coerce").fillna(0.0)
            
            mapa_obj_marca = maestro_cebe_clean.groupby("Marca_Key")["Obj_Mes_Val"].sum().to_dict()
            
            kilos_hist = historial.groupby(["CodVend", "SEGMENTO", "Marca"])["PesoKg"].sum().reset_index().rename(columns={"PesoKg": "Kilos_Hist"})
            kilos_hist["Total_Kilos_Marca_Seg"] = kilos_hist.groupby(["SEGMENTO", "Marca"])["Kilos_Hist"].transform("sum")
            kilos_hist["Part_Vendedor"] = (kilos_hist["Kilos_Hist"] / kilos_hist["Total_Kilos_Marca_Seg"].replace(0, pd.NA)).fillna(0.0)
            
            kilos_hist["Obj_Marca_Oficial"] = kilos_hist["Marca"].map(mapa_obj_marca).fillna(0.0)
            kilos_hist["Obj_Asignado"] = kilos_hist["Part_Vendedor"] * kilos_hist["Obj_Marca_Oficial"] * 1000.0
            
            objs_oficiales = kilos_hist.groupby(["CodVend", "SEGMENTO"])["Obj_Asignado"].sum().reset_index().rename(columns={"Obj_Asignado": "Objetivo Mes Corriente"})
            reporte = reporte.merge(objs_oficiales, on=["CodVend", "SEGMENTO"], how="left")
        else:
            reporte["Objetivo Mes Corriente"] = 0.0

    reporte["Objetivo Mes Corriente"] = reporte["Objetivo Mes Corriente"].fillna(0.0)

    reemplazos = df_vtas_op[df_vtas_op["CodVend_Op"].ne(df_vtas_op["CodVendedor"])][["CodVendedor", "CodVend_Op", "SEGMENTO", "Periodo", "PesoKg"]].copy()
    
    if not reemplazos.empty:
        mov_titular = reemplazos[["CodVendedor", "SEGMENTO", "Periodo", "PesoKg"]].rename(columns={"CodVendedor": "CodVend"})
        mov_titular["Ajuste_Valor"] = -mov_titular.pop("PesoKg")
        
        mov_reemp = reemplazos[["CodVend_Op", "SEGMENTO", "Periodo", "PesoKg"]].rename(columns={"CodVend_Op": "CodVend"})
        mov_reemp["Ajuste_Valor"] = movimentos_reemp_val = mov_reemp.pop("PesoKg") if "PesoKg" in mov_reemp.columns else 0.0

        ajustes_totales = pd.concat([mov_titular, mov_reemp], ignore_index=True)
        ajustes_totales["CodVend"] = pd.to_numeric(ajustes_totales["CodVend"], errors="coerce").astype("Int64")
        
        aj_arr = ajustes_totales[ajustes_totales["Periodo"] == "Arrastre"].groupby(["CodVend", "SEGMENTO"])["Ajuste_Valor"].sum().reset_index().rename(columns={"Ajuste_Valor": "Ajuste_Reemp_Arrastre"})
        aj_act = ajustes_totales[ajustes_totales["Periodo"] == "Actual"].groupby(["CodVend", "SEGMENTO"])["Ajuste_Valor"].sum().reset_index().rename(columns={"Ajuste_Valor": "Ajuste_Reemp_Actual"})

        reporte = reporte.merge(aj_arr, on=["CodVend", "SEGMENTO"], how="left")
        reporte = reporte.merge(aj_act, on=["CodVend", "SEGMENTO"], how="left")
    else:
        reporte["Ajuste_Reemp_Arrastre"] = 0.0
        reporte["Ajuste_Reemp_Actual"] = 0.0

    reporte["Ajuste_Reemp_Arrastre"] = reporte.get("Ajuste_Reemp_Arrastre", 0.0).fillna(0.0)
    reporte["Ajuste_Reemp_Actual"] = reporte.get("Ajuste_Reemp_Actual", 0.0).fillna(0.0)
    reporte["Ajuste_Por_Reemp"] = reporte["Ajuste_Reemp_Arrastre"] + reporte["Ajuste_Reemp_Actual"]

    if orden_segmentos_maestro:
        mapping_orden = {str(seg).strip(): i for i, seg in enumerate(orden_segmentos_maestro)}
        reporte["SEGMENTO_STR"] = reporte["SEGMENTO"].astype(str).str.strip()
        reporte["_orden_idx"] = reporte["SEGMENTO_STR"].map(mapping_orden).fillna(999)
        reporte = reporte.sort_values(by=["CodVend", "_orden_idx"]).drop(columns=["_orden_idx", "SEGMENTO_STR"]).reset_index(drop=True)
    else:
        reporte = reporte.sort_values(by=["CodVend", "SEGMENTO"]).reset_index(drop=True)

    reporte["SEGMENTO"] = reporte["SEGMENTO"].astype(str)
    
    clave_vtas_op = f"_df_vtas_op_{anio_operativo}_{mes_operativo}_{sup_filtro}"
    st.session_state[clave_vtas_op] = df_vtas_op
    st.session_state[f"_orden_seg_{anio_operativo}_{mes_operativo}"] = orden_segmentos_maestro

    reporte = reporte.rename(columns={"CodVend": "CodVendedor"})
    return reporte

@st.cache_data(show_spinner=False)
def _calcular_avance_kilos_cached(df_vta, df_rutas, maestro_vend, maestro_seg, maestro_cebe, dia_venta, anio_op, mes_op, sup_filtro, huella):
    df_vta_prep = preparar_datos_ventas_segmento(df_vta, None, anio_op, mes_op, dia_venta)
    reporte_avance = generar_reporte_avance_kilos_segmento(df_vta_prep, df_rutas, maestro_vend, maestro_seg, maestro_cebe, dia_venta, anio_op, mes_op, sup_filtro)
    return reporte_avance, df_vta_prep

@st.fragment
def render_fragmento_interactivo_kilos(reporte_vendedores_puro, df_comodines_Rows, s_dispo, v_dispo, anio_op, mes_op, sup_filtro, df_vta_prep, dia_matinal):
    from modules.utils import tarjeta_metrica_html

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], key=f"frag_kilos_v_{anio_op}_{mes_op}_{sup_filtro}")
    with col_f2:
        s_selec = st.multiselect("Segmento", options=s_dispo, default=[], key=f"frag_kilos_s_{anio_op}_{mes_op}_{sup_filtro}")
    with col_f3:
        modo_ajuste = st.selectbox("Ajuste por Entrega", options=["TODO", "AJUSTADO"], index=1, key=f"frag_kilos_ajuste_{anio_op}_{mes_op}_{sup_filtro}")

    if not v_selec:
        v_selec = v_dispo
    if not s_selec:
        s_selec = s_dispo

    rep_filtrado = reporte_vendedores_puro[
        reporte_vendedores_puro["Nombre"].astype(str).str.strip().isin(v_selec) & 
        reporte_vendedores_puro["SEGMENTO"].astype(str).str.strip().isin(s_selec)
    ].copy()

    for col_req in ["Ajuste_Reemp_Arrastre", "Ajuste_Reemp_Actual", "Ajuste_Por_Reemp"]:
        if col_req not in rep_filtrado.columns:
            rep_filtrado[col_req] = 0.0

    col_dias_restantes_activo = "Días Restantes Ajustado" if modo_ajuste == "AJUSTADO" else "Días Restantes Todo"

    rep_detalle = rep_filtrado[
        ["CodVendedor", "Nombre", "SUP", "SEGMENTO", "Objetivo Mes Corriente", "Arrastre", "Actual", "Ajuste_Reemp_Arrastre", "Ajuste_Reemp_Actual", "Ajuste_Por_Reemp", "Días Pasados", "Rutas", "Ajuste_Entrega", "Rutas_Ajustadas", col_dias_restantes_activo]
    ].copy()
    
    rep_detalle = rep_detalle.rename(columns={col_dias_restantes_activo: "Días Restantes"})
    rep_detalle["OPERATIVO"] = rep_detalle["Arrastre"] + rep_detalle["Actual"] + rep_detalle["Ajuste_Por_Reemp"]

    es_todos_vendedores = (len(v_selec) == len(v_dispo)) and (len(v_dispo) > 0)
    total_arrastre_vend = float(rep_detalle["Arrastre"].sum())
    total_actual_vend = float(rep_detalle["Actual"].sum())

    clave_vtas_op = f"_df_vtas_op_{anio_op}_{mes_op}_{sup_filtro}"
    df_global_op = st.session_state.get(clave_vtas_op, pd.DataFrame())

    if es_todos_vendedores:
        if not df_global_op.empty:
            df_reemp_trans = df_global_op[df_global_op["CodVend_Op"] == -998].copy()
            if sup_filtro != "TODOS":
                df_reemp_trans = df_reemp_trans[df_reemp_trans["SUP_Transaccion"].astype(str).str.strip() == sup_filtro]
            if s_dispo:
                df_reemp_trans = df_reemp_trans[df_reemp_trans["SEGMENTO"].astype(str).str.strip().isin(s_selec)]
            
            arrastre_reemp = float(df_reemp_trans[df_reemp_trans["Periodo"] == "Arrastre"]["PesoKg"].sum())
            actual_reemp = float(df_reemp_trans[df_reemp_trans["Periodo"] == "Actual"]["PesoKg"].sum())
        else:
            arrastre_reemp = 0.0
            actual_reemp = 0.0

        total_arrastre = total_arrastre_vend + arrastre_reemp
        total_actual = total_actual_vend + actual_reemp
        total_neto_operativo = total_arrastre + total_actual
    else:
        total_arrastre = total_arrastre_vend
        total_actual = total_actual_vend
        total_neto_operativo = float(rep_detalle["OPERATIVO"].sum())

    total_objetivo_mes = float(rep_detalle["Objetivo Mes Corriente"].sum())
    pct_avance = (total_neto_operativo / total_objetivo_mes * 100.0) if total_objetivo_mes > 0 else 0.0

    fecha_mat_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(fecha_mat_dt):
        f_ult = (fecha_mat_dt - pd.Timedelta(days=7)).date()
        f_penult = (fecha_mat_dt - pd.Timedelta(days=14)).date()
        
        u_vta = df_vta_prep[df_vta_prep["FechaCarga_dt"].dt.date.eq(f_ult)].groupby(["CodVendedor", "SEGMENTO"])["PesoKg"].sum().reset_index().rename(columns={"PesoKg": "Ultima_Vta"})
        p_vta = df_vta_prep[df_vta_prep["FechaCarga_dt"].dt.date.eq(f_penult)].groupby(["CodVendedor", "SEGMENTO"])["PesoKg"].sum().reset_index().rename(columns={"PesoKg": "Penultima_Vta"})
    else:
        u_vta = pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Ultima_Vta"])
        p_vta = pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Penultima_Vta"])

    if not u_vta.empty:
        u_vta["CodVendedor"] = pd.to_numeric(u_vta["CodVendedor"], errors="coerce").astype("Int64")
        rep_detalle = rep_detalle.merge(u_vta, on=["CodVendedor", "SEGMENTO"], how="left")
    else:
        rep_detalle["Ultima_Vta"] = 0.0

    if not p_vta.empty:
        p_vta["CodVendedor"] = pd.to_numeric(p_vta["CodVendedor"], errors="coerce").astype("Int64")
        rep_detalle = rep_detalle.merge(p_vta, on=["CodVendedor", "SEGMENTO"], how="left")
    else:
        rep_detalle["Penultima_Vta"] = 0.0

    rep_detalle[["Ultima_Vta", "Penultima_Vta"]] = rep_detalle[["Ultima_Vta", "Penultima_Vta"]].fillna(0.0)

    dp_s = rep_detalle["Días Pasados"].astype(float).replace(0, 1.0)
    dr_s = rep_detalle["Días Restantes"].astype(float)

    p_diario = (rep_detalle["Actual"] + rep_detalle["Ajuste_Reemp_Actual"]) / dp_s
    rep_detalle["Promedio_Diario"] = p_diario
    
    rep_detalle["Tendencia_Total_Kg"] = rep_detalle["OPERATIVO"]
    mask_activos = dr_s > 0
    if mask_activos.any():
        rep_detalle.loc[mask_activos, "Tendencia_Total_Kg"] = (p_diario[mask_activos] * dr_s[mask_activos]) + rep_detalle.loc[mask_activos, "OPERATIVO"]

    rep_detalle["Cumplimiento_Proyectado_Pct"] = ((rep_detalle["Tendencia_Total_Kg"]) / rep_detalle["Objetivo Mes Corriente"].replace(0, pd.NA)).mul(100).fillna(0.0)
    
    rep_detalle["Media_Necesaria_Diaria"] = 0.0
    if mask_activos.any():
        rep_detalle.loc[mask_activos, "Media_Necesaria_Diaria"] = ((rep_detalle.loc[mask_activos, "Objetivo Mes Corriente"] - rep_detalle.loc[mask_activos, "OPERATIVO"]) / dr_s[mask_activos]).clip(lower=0)

    if rep_detalle["Días Restantes"].sum() == 0:
        total_tendencia = total_neto_operativo
        pct_cumplimiento_obj = pct_avance
    else:
        total_tendencia = float(rep_detalle["Tendencia_Total_Kg"].sum())
        pct_cumplimiento_obj = (total_tendencia / total_objetivo_mes * 100.0) if total_objetivo_mes > 0 else 0.0

    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    with mcol1:
        st.markdown(tarjeta_metrica_html("📦 Arrastre", f"{total_arrastre:,.1f} kg", "#3b82f6", "39px", "21px"), unsafe_allow_html=True)
    with mcol2:
        st.markdown(tarjeta_metrica_html("🚚 Actual", f"{total_actual:,.1f} kg", "#3b82f6", "39px", "21px"), unsafe_allow_html=True)
    with mcol3:
        st.markdown(tarjeta_metrica_html("📊 Neto Operativo", f"{total_neto_operativo:,.1f} kg", "#3b82f6", "39px", "21px"), unsafe_allow_html=True)
    with mcol4:
        st.markdown(tarjeta_metrica_html("📈 % Avance", f"{pct_avance:,.2f}%", "#3b82f6", "39px", "21px"), unsafe_allow_html=True)

    tcol1, tcol2, tcol3 = st.columns(3)
    with tcol1:
        st.markdown(tarjeta_metrica_html("🎯 Objetivo del Mes", f"{total_objetivo_mes:,.1f} kg", "#3b82f6", "39px", "21px"), unsafe_allow_html=True)
    with tcol2:
        st.markdown(tarjeta_metrica_html("📈 Tendencia Kgs", f"{total_tendencia:,.1f} kg", "#ef4444", "39px", "21px"), unsafe_allow_html=True)
    with tcol3:
        st.markdown(tarjeta_metrica_html("🎯 Tendencia %", f"{pct_cumplimiento_obj:,.2f}%", "#3b82f6", "39px", "21px"), unsafe_allow_html=True)
    
    st.divider()

    cols_excepcion = ["CodVendedor", "Nombre", "SUP", "SEGMENTO", "Días Pasados", "Rutas", "Ajuste_Entrega", "Rutas_Ajustadas", "Días Restantes"]
    for col in rep_detalle.columns:
        if col not in cols_excepcion and pd.api.types.is_numeric_dtype(rep_detalle[col]):
            rep_detalle[col] = pd.to_numeric(rep_detalle[col], errors="coerce").round(2)

    columnas_ordenadas = [
        "CodVendedor", "Nombre", "SUP", "SEGMENTO", "Objetivo Mes Corriente", "Arrastre", "Actual", 
        "Ultima_Vta", "Penultima_Vta", "OPERATIVO", "Ajuste_Por_Reemp", "Tendencia_Total_Kg", 
        "Cumplimiento_Proyectado_Pct", "Promedio_Diario", "Media_Necesaria_Diaria", "Días Pasados", "Rutas", "Ajuste_Entrega", "Rutas_Ajustadas", "Días Restantes"
    ]
    rep_detalle = rep_detalle[columnas_ordenadas]

    rep_detalle_excel = rep_detalle.copy()

    rep_detalle_display = rep_detalle.copy()
    cols_kilos = [
        "Objetivo Mes Corriente", "Arrastre", "Actual", "Ultima_Vta", "Penultima_Vta", 
        "OPERATIVO", "Ajuste_Por_Reemp", "Tendencia_Total_Kg", "Promedio_Diario", "Media_Necesaria_Diaria"
    ]
    for col in cols_kilos:
        if col in rep_detalle_display.columns:
            rep_detalle_display[col] = rep_detalle_display[col].apply(lambda x: f"{x:,.2f} kg" if pd.notna(x) else "0.00 kg")
    
    if "Cumplimiento_Proyectado_Pct" in rep_detalle_display.columns:
        rep_detalle_display["Cumplimiento_Proyectado_Pct"] = rep_detalle_display["Cumplimiento_Proyectado_Pct"].apply(lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%")

    if not rep_detalle_display.empty:
        st.dataframe(rep_detalle_display, width="stretch", hide_index=True)
    else:
        st.info("No se encontraron registros de Kilos con los filtros seleccionados.")

    buffer_kilos = io.BytesIO()
    with pd.ExcelWriter(buffer_kilos, engine="openpyxl") as writer:
        rep_detalle_excel.to_excel(writer, index=False, sheet_name="Avance_Kilos_Segmento")
    buffer_kilos.seek(0)

    st.download_button(
        label="📥 Descargar Avance Kilos a Excel", 
        data=buffer_kilos, 
        file_name=f"Avance_Kilos_{sup_filtro}_{mes_op}_{anio_op}.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        key=f"kilos_frag_btn_dl_{sup_filtro}"
    )

def render_rep_kilos(df_vta, df_rutas, df_ausencias, filtros_globales=None):
    st.subheader("📊 Avance de Kilos por Segmento")

    if filtros_globales is None:
        anio_op = 2026
        mes_op = 9
        sup_filtro = "TODOS"
        dia_venta = "01/09/2026"
        dia_matinal = "02/09/2026"
    else:
        anio_op = int(filtros_globales.get("anio", 2026))
        mes_op = int(filtros_globales.get("mes", 9))
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()
        dia_venta = filtros_globales.get("dia_venta", "01/09/2026")
        dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026")

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        if not maestro_v.empty and "Mes" in maestro_v.columns:
            mv_per = maestro_v[(maestro_v["Mes"].astype(str) == str(mes_op)) & (maestro_v["Anio"].astype(str) == str(anio_op))]
            if not mv_per.empty:
                maestro_v = mv_per
    except Exception:
        maestro_v = pd.DataFrame()

    try:
        maestro_s = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos ORDER BY rowid ASC")
        if not maestro_s.empty and "Mes" in maestro_s.columns:
            ms_per = maestro_s[(maestro_s["Mes"].astype(str) == str(mes_op)) & (maestro_s["Anio"].astype(str) == str(anio_op))]
            if not ms_per.empty:
                maestro_s = ms_per
    except Exception:
        maestro_s = pd.DataFrame()

    try:
        maestro_cebe = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if not maestro_cebe.empty and "Mes" in maestro_cebe.columns:
            mc_per = maestro_cebe[(maestro_cebe["Mes"].astype(str) == str(mes_op)) & (maestro_cebe["Anio"].astype(str) == str(anio_op))]
            if not mc_per.empty:
                maestro_cebe = mc_per
    except Exception:
        maestro_cebe = pd.DataFrame()

    if maestro_v.empty:
        st.warning("⚠️ No se encontró el Maestro de Vendedores cargado para este período en SQLite. Verifique en la solapa de Parámetros.")
        return

    huella_kilos = f"{len(df_vta) if df_vta is not None else 0}_{len(df_rutas) if df_rutas is not None else 0}_{anio_op}_{mes_op}_{sup_filtro}_{dia_matinal}_{dia_venta}"
    
    reporte_avance, df_vta_prep = _calcular_avance_kilos_cached(
        df_vta, df_rutas, maestro_v, maestro_s, maestro_cebe, dia_venta, anio_op, mes_op, sup_filtro, huella_kilos
    )

    if "Ajuste_Reemp_Arrastre" not in reporte_avance.columns:
        reporte_avance["Ajuste_Reemp_Arrastre"] = 0.0
    if "Ajuste_Reemp_Actual" not in reporte_avance.columns:
        reporte_avance["Ajuste_Reemp_Actual"] = 0.0
    if "Ajuste_Por_Reemp" not in reporte_avance.columns:
        reporte_avance["Ajuste_Por_Reemp"] = reporte_avance["Ajuste_Reemp_Arrastre"] + reporte_avance["Ajuste_Reemp_Actual"]

    mask_comodines = reporte_avance["CodVendedor"].isin([-999, -998])
    df_comodines_Rows = reporte_avance[mask_comodines].copy()
    reporte_vendedores_puro = reporte_avance[~mask_comodines].copy()

    if sup_filtro != "TODOS":
        reporte_vendedores_puro = reporte_vendedores_puro[reporte_vendedores_puro["SUP"].astype(str).str.strip() == sup_filtro].copy()

    v_dispo = sorted(reporte_vendedores_puro["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    orden_oficial_seg = st.session_state.get(f"_orden_seg_{anio_op}_{mes_op}", [])
    segs_unicos_rep = set(reporte_vendedores_puro["SEGMENTO"].dropna().astype(str).str.strip().unique())
    
    s_dispo = [s for s in orden_oficial_seg if s in segs_unicos_rep]
    for s in segs_unicos_rep:
        if s not in s_dispo:
            s_dispo.append(s)

    render_fragmento_interactivo_kilos(reporte_vendedores_puro, df_comodines_Rows, s_dispo, v_dispo, anio_op, mes_op, sup_filtro, df_vta_prep, dia_matinal)

====================================================================================================


### ARCHIVO: modules\rep_kilos_core.py

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


====================================================================================================


### ARCHIVO: modules\rep_MN.py

# modules/rep_MN.py
import io
import urllib.parse
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import parsear_fecha_robusta, extraer_dia_de_ruta

def preparar_ventas_mn(df_vta, df_ausencias, anio_operativo, mes_operativo, dia_matinal):
    """
    Pipeline de ventas optimizado para MiNegocio derivado del DataFrame Maestro N1 (EMPLEADOS).
    Aplica los filtros N2: PEPSICO, COMODATOS, DEPOSITO, MATINAL y PERIODO.
    """
    # Nivel 1: Obtención del DataFrame corporativo base con filtro EMPLEADOS aplicado
    df_corp = db.obtener_df_maestro_corporativo()
    df = df_corp.copy() if not df_corp.empty else (df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame())
    
    if df.empty:
        return df

    col_imp = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df.columns), None)
    df["ImporteNetoItem"] = pd.to_numeric(df[col_imp], errors="coerce").fillna(0.0) if col_imp else 0.0

    col_orig = next((c for c in df.columns if any(k in str(c).lower() for k in ["origen", "canal"])), None)
    if col_orig:
        df["OrigenDeVta"] = df[col_orig].fillna("").astype(str).str.strip()
        df["Es_MiNegocio"] = df["OrigenDeVta"].str.contains("minegocio|mi negocio", case=False, na=False)
    else:
        df["OrigenDeVta"] = ""
        df["Es_MiNegocio"] = False

    # Nivel 2: Filtro COMODATOS (Exclusión de comodatos y préstamos)
    if "TipoDeVenta" in df.columns:
        tipos_excluidos = [
            "Comodato Devolución", 
            "Comodato Ficticio", 
            "Comodato Ficticio Devolución", 
            "Comodato Préstamo"
        ]
        df = df[~df["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)]

    # Nivel 2: Filtro PEPSICO (Selección exclusiva de proveedor PepsiCo)
    if "Proveedor" in df.columns:
        df = df[
            df["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    # Nivel 2: Filtro MATINAL (Exclusión de registros cuya fecha de carga sea igual o posterior al Día Matinal)
    dia_matinal_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(dia_matinal_dt):
        es_mes_en_curso = (dia_matinal_dt.year == anio_operativo and dia_matinal_dt.month in [mes_operativo, mes_operativo + 1])
        if es_mes_en_curso:
            df = df[df["FechaCarga_dt"].dt.date < dia_matinal_dt.date()]

    col_vend_tit = next((cand for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"] if cand in df.columns), "CodVendedor")
    df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype("Int64")
    
    # Nivel 2: Filtro DEPOSITO (Exclusión del vendedor 20 para aislar preventistas puros)
    df = df[df["CodVendedor"] != 20]

    df["MesCarga"] = df["FechaCarga_dt"].dt.month
    df["AñoCarga"] = df["FechaCarga_dt"].dt.year
    df["MesEntrega"] = df["FechaEntrega_dt"].dt.month
    df["AñoEntrega"] = df["FechaEntrega_dt"].dt.year

    mes_ant = 12 if mes_operativo == 1 else mes_operativo - 1
    anio_ant = anio_operativo - 1 if mes_operativo == 1 else anio_operativo

    mes_sig = 1 if mes_operativo == 12 else mes_operativo + 1
    anio_sig = anio_operativo + 1 if mes_operativo == 12 else anio_operativo

    conditions = [
        (df["AñoCarga"] == anio_ant) & (df["MesCarga"] == mes_ant) & (df["AñoEntrega"] == anio_operativo) & (df["MesEntrega"] == mes_operativo),
        (df["AñoCarga"] == anio_operativo) & (df["MesCarga"] == mes_operativo) & (df["AñoEntrega"] == anio_operativo) & (df["MesEntrega"] == mes_operativo),
        (df["AñoCarga"] == anio_operativo) & (df["MesCarga"] == mes_operativo) & (df["AñoEntrega"] == anio_sig) & (df["MesEntrega"] == mes_sig)
    ]
    choices = ["Arrastre", "Actual", "Futuro"]
    
    # Nivel 2: Filtro PERIODO (Clasificación de transacciones en Arrastre, Actual o Futuro)
    df["Periodo"] = np.select(conditions, choices, default="Fuera de Periodo")

    return df

def _calcular_base_mn(df_vta, df_universo, vendedores, anio_op, mes_op, dia_matinal):
    """Motor de cálculo base de MiNegocio optimizado con operaciones vectorizadas."""
    try:
        df_ausencias = db.cargar_tabla_sql("SELECT * FROM ausencias")
    except Exception:
        df_ausencias = pd.DataFrame()

    df_vta_prep = preparar_ventas_mn(df_vta, df_ausencias, anio_op, mes_op, dia_matinal)
    ventas_periodo = df_vta_prep[df_vta_prep["Periodo"].isin(["Arrastre", "Actual"])].copy() if not df_vta_prep.empty and "Periodo" in df_vta_prep.columns else df_vta_prep.copy()

    if not ventas_periodo.empty:
        col_c_orig = next((c for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"] if c in ventas_periodo.columns), "Cliente")
        ventas_periodo["Cliente"] = pd.to_numeric(ventas_periodo[col_c_orig], errors="coerce").astype("Int64")
        
        ventas_periodo["_mn_val"] = np.where(ventas_periodo["Es_MiNegocio"], ventas_periodo["ImporteNetoItem"], 0.0)
        clientes_g = ventas_periodo.groupby("Cliente", as_index=False).agg(
            Ventas_Totales=("ImporteNetoItem", "sum"),
            Ventas_MiNegocio=("_mn_val", "sum")
        )
        
        clientes_g["Ventas_Totales"] = clientes_g["Ventas_Totales"].round(2)
        clientes_g["Ventas_MiNegocio"] = clientes_g["Ventas_MiNegocio"].round(2)
        
        clientes_g.loc[clientes_g["Ventas_Totales"] < 0, "Ventas_Totales"] = 0.0
        clientes_g.loc[clientes_g["Ventas_MiNegocio"] < 0, "Ventas_MiNegocio"] = 0.0
        clientes_g.loc[clientes_g["Ventas_MiNegocio"] < 0.01, "Ventas_MiNegocio"] = 0.0

        pct_raw = (clientes_g["Ventas_MiNegocio"] / clientes_g["Ventas_Totales"].replace(0, pd.NA)).mul(100.0)
        clientes_g["Pct_MiNegocio"] = pct_raw.clip(lower=0.0, upper=100.0).fillna(0.0).round(2)
    else:
        clientes_g = pd.DataFrame(columns=["Cliente", "Ventas_Totales", "Ventas_MiNegocio", "Pct_MiNegocio"])

    universo = df_universo.copy() if df_universo is not None else pd.DataFrame()
    if not universo.empty:
        cols_u = [str(c).strip().lower() for c in universo.columns]
        col_prov_u = next((universo.columns[i] for i, c in enumerate(cols_u) if c in ["proveedor", "fabricante", "empresa"]), None)
        if col_prov_u:
            spu = universo[col_prov_u]
            if isinstance(spu, pd.DataFrame): spu = spu.iloc[:, 0]
            universo = universo[spu.astype(str).str.contains("pepsico", case=False, na=False)].copy()

        col_sub_u = next((c for c in universo.columns if "subramo" in str(c).lower()), None)
        if col_sub_u:
            ssu = universo[col_sub_u]
            if isinstance(ssu, pd.DataFrame): ssu = ssu.iloc[:, 0]
            universo = universo[ssu.fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()

        pos_v_u = next((c for c in ["codven", "CodVendedor", "CodVend", "Vendedor", "cod_vendedor"] if c in universo.columns), None)
        if pos_v_u:
            sv_u = universo[pos_v_u]
            if isinstance(sv_u, pd.DataFrame): sv_u = sv_u.iloc[:, 0]
            universo["CodVendedor"] = pd.to_numeric(sv_u, errors="coerce").astype("Int64")

        tax_col = next((c for c in universo.columns if "taxonomia" in str(c).lower() or "segmentoclientecodigo" in str(c).lower() or "clasificacion" in str(c).lower()), None)
        if tax_col:
            stx = universo[tax_col]
            if isinstance(stx, pd.DataFrame): stx = stx.iloc[:, 0]
            universo["Taxonomia"] = stx.fillna("").astype(str).str.strip().str.upper()
        else:
            universo["Taxonomia"] = "A"

        col_ruta_u = next((c for c in universo.columns if str(c).strip().lower() in ["ruta", "dia_visita", "visita", "dia"]), None)
        if col_ruta_u is not None:
            sr_u = universo[col_ruta_u]
            if isinstance(sr_u, pd.DataFrame):
                sr_u = sr_u.iloc[:, 0]
            universo["DiaVisita"] = sr_u.apply(extraer_dia_de_ruta)
        else:
            universo["DiaVisita"] = "SIN DÍA"

        cli_col_u = next((c for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"] if c in universo.columns), universo.columns[0])
        scli_u = universo[cli_col_u]
        if isinstance(scli_u, pd.DataFrame): scli_u = scli_u.iloc[:, 0]
        universo["Cliente"] = pd.to_numeric(scli_u, errors="coerce").astype("Int64")

        col_nom_cli = next((c for c in ["NombreCliente", "Nombre_Cliente", "RazonSocial", "ClienteDesc"] if c in universo.columns), cli_col_u)
        universo["NombreCliente"] = universo[col_nom_cli].fillna("").astype(str)

        col_dir_cli = next((c for c in ["DireccionCliente", "Direccion", "Domicilio"] if c in universo.columns), None)
        universo["DireccionCliente"] = universo[col_dir_cli].fillna("").astype(str) if col_dir_cli else ""

        universo = universo[universo["Taxonomia"].isin(["A", "B", "C", "D"])].dropna(subset=["Cliente", "CodVendedor"])

    if not universo.empty and "CodVendedor" in universo.columns:
        universo["CodVendedor"] = pd.to_numeric(universo["CodVendedor"], errors="coerce").astype("Int64")
        universo = universo[universo["CodVendedor"] != 20]

    if not clientes_g.empty:
        clientes_con_ventas = set(clientes_g["Cliente"].dropna().tolist())
        clientes_en_universo = set(universo["Cliente"].dropna().tolist()) if not universo.empty else set()
        clientes_fuera_universo = clientes_con_ventas - clientes_en_universo

        if clientes_fuera_universo and not ventas_periodo.empty:
            df_fuera = ventas_periodo[ventas_periodo["Cliente"].isin(clientes_fuera_universo)].groupby("Cliente", as_index=False).agg({
                "CodVendedor": "first"
            })
            df_fuera["Taxonomia"] = "SIN CLASIFICAR"
            df_fuera["NombreCliente"] = "CLIENTE FUERA DE PADRÓN"
            df_fuera["DireccionCliente"] = ""
            df_fuera["DiaVisita"] = "SIN DÍA"
            
            if universo.empty:
                universo = df_fuera
            else:
                universo = pd.concat([universo, df_fuera], ignore_index=True)

    vendedores_df = pd.DataFrame()
    vendedores_seguro = vendedores.copy() if vendedores is not None and not vendedores.empty else pd.DataFrame(columns=["Codigo_Vendedor", "Nombre_Vendedor", "Supervisor"])
    if vendedores_seguro.empty:
        vendedores_seguro = pd.DataFrame({"Codigo_Vendedor": [0], "Nombre_Vendedor": ["SIN ASIGNAR"], "Supervisor": ["GENERAL"]})

    col_c_v = next((c for c in ["Codigo_Vendedor", "CodVend", "CodVendedor"] if c in vendedores_seguro.columns), vendedores_seguro.columns[0])
    col_n_v = next((c for c in ["Nombre_Vendedor", "Nombre"] if c in vendedores_seguro.columns), vendedores_seguro.columns[1] if len(vendedores_seguro.columns) > 1 else vendedores_seguro.columns[0])
    col_s_v = next((c for c in ["Supervisor", "SUP"] if c in vendedores_seguro.columns), vendedores_seguro.columns[2] if len(vendedores_seguro.columns) > 2 else vendedores_seguro.columns[0])

    sv_c = vendedores_seguro[col_c_v]
    if isinstance(sv_c, pd.DataFrame): sv_c = sv_c.iloc[:, 0]
    vendedores_df["CodVendedor"] = pd.to_numeric(sv_c, errors="coerce").astype("Int64")
    vendedores_df = vendedores_df[vendedores_df["CodVendedor"] != 20]

    sv_n = vendedores_seguro[col_n_v]
    if isinstance(sv_n, pd.DataFrame): sv_n = sv_n.iloc[:, 0]
    vendedores_df["Nombre"] = sv_n.fillna("").astype(str).str.strip()
    sv_s = vendedores_seguro[col_s_v]
    if isinstance(sv_s, pd.DataFrame): sv_s = sv_s.iloc[:, 0]
    vendedores_df["SUP"] = sv_s.fillna("").astype(str).str.strip()
    vendedores_df = vendedores_df.drop_duplicates("CodVendedor")

    if not universo.empty and not clientes_g.empty:
        df_detalle = universo.merge(clientes_g, on="Cliente", how="left")
    else:
        df_detalle = universo.copy()
        df_detalle["Ventas_Totales"] = 0.0
        df_detalle["Ventas_MiNegocio"] = 0.0
        df_detalle["Pct_MiNegocio"] = 0.0

    df_detalle["Ventas_Totales"] = df_detalle["Ventas_Totales"].fillna(0.0)
    df_detalle["Ventas_MiNegocio"] = df_detalle["Ventas_MiNegocio"].fillna(0.0)
    df_detalle["Pct_MiNegocio"] = df_detalle["Pct_MiNegocio"].fillna(0.0)

    df_detalle["Es_NoDigital"] = df_detalle["Pct_MiNegocio"] <= 0.01
    df_detalle["Es_Hibrido"] = (df_detalle["Pct_MiNegocio"] > 0.01) & (df_detalle["Pct_MiNegocio"] < 70.0)
    df_detalle["Es_FullyDigital"] = df_detalle["Pct_MiNegocio"] >= 70.0

    numerador_req = (0.70 * df_detalle["Ventas_Totales"]) - df_detalle["Ventas_MiNegocio"]
    df_detalle["Minimo_Facturacion_70"] = (numerador_req / 0.30).clip(lower=0.0).round(2)

    df_detalle = df_detalle.merge(vendedores_df[["CodVendedor", "Nombre", "SUP"]], on="CodVendedor", how="left", suffixes=("_univ", ""))
    if "Nombre" not in df_detalle.columns and "Nombre_univ" in df_detalle.columns:
        df_detalle["Nombre"] = df_detalle["Nombre_univ"]

    return df_detalle

@st.cache_data(show_spinner=False)
def _calcular_base_mn_cached(df_vta, df_universo, vendedores, anio_op, mes_op, dia_matinal, huella_datos):
    return _calcular_base_mn(df_vta, df_universo, vendedores, anio_op, mes_op, dia_matinal)

def generar_reporte_mn_taxonomia(df_vta, df_universo, vendedores, filtros_globales=None):
    anio_op = int(filtros_globales.get("anio", 2026)) if filtros_globales else 2026
    mes_op = int(filtros_globales.get("mes", 9)) if filtros_globales else 9
    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026") if filtros_globales else "02/09/2026"

    huella_datos = f"{len(df_vta) if df_vta is not None else 0}_{len(df_universo) if df_universo is not None else 0}_{anio_op}_{mes_op}_{dia_matinal}"

    df_det = _calcular_base_mn_cached(df_vta, df_universo, vendedores, anio_op, mes_op, dia_matinal, huella_datos)
    return df_det

def _tarjeta_metrica_compacta_html(label, valor, border_color="#475569", border_width="1px"):
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
def render_fragmento_interactivo_mn(df_det, supervisores_seleccionados):
    if df_det is None or df_det.empty:
        st.info("No hay datos disponibles para procesar el Avance de Adopción MiNegocio.")
        return

    df_base_cli = df_det.copy()
    if supervisores_seleccionados and "SUP" in df_base_cli.columns:
        df_base_cli = df_base_cli[df_base_cli["SUP"].astype(str).str.strip().isin([str(s).strip() for s in supervisores_seleccionados])].copy()

    if df_base_cli.empty:
        st.info("No se encontraron registros para los supervisores seleccionados.")
        return

    v_dispo = sorted(df_base_cli["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    tax_dispo = sorted(df_base_cli["Taxonomia"].dropna().astype(str).str.strip().unique().tolist())
    
    orden_dias = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO", "SIN DÍA"]
    dias_en_datos = df_base_cli["DiaVisita"].dropna().astype(str).str.strip().unique().tolist() if "DiaVisita" in df_base_cli.columns else []
    dia_visita_dispo = [d for d in orden_dias if d in dias_en_datos]
    for d in dias_en_datos:
        if d not in dia_visita_dispo:
            dia_visita_dispo.append(d)

    col_fc1, col_fc2, col_fc3 = st.columns(3)
    with col_fc1:
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], placeholder="Seleccionar preventistas...", key="frag_mn_vendedor")
    with col_fc2:
        tax_selec = st.multiselect("Taxonomía", options=tax_dispo, default=[], placeholder="Seleccionar taxonomías...", key="frag_mn_taxonomia")
    with col_fc3:
        dia_visita_selec = st.multiselect("Día de Visita", options=dia_visita_dispo, default=[], placeholder="Seleccionar días de visita...", key="frag_mn_dia_visita")

    if not v_selec:
        v_selec = v_dispo
    if not tax_selec:
        tax_selec = tax_dispo
    if not dia_visita_selec:
        dia_visita_selec = dia_visita_dispo

    mask_cli = (
        df_base_cli["Nombre"].astype(str).str.strip().isin(v_selec) &
        df_base_cli["Taxonomia"].astype(str).str.strip().isin(tax_selec) &
        df_base_cli["DiaVisita"].astype(str).str.strip().isin(dia_visita_selec)
    )

    df_cli_filtrado = df_base_cli[mask_cli].copy()

    if not df_cli_filtrado.empty:
        reporte_filtrado = df_cli_filtrado.groupby(["CodVendedor", "Nombre", "SUP", "Taxonomia"], as_index=False).agg(
            Cartera_Total=("Cliente", "count"),
            Ventas_Totales=("Ventas_Totales", "sum"),
            Ventas_MiNegocio=("Ventas_MiNegocio", "sum"),
            Count_NoDigital=("Es_NoDigital", lambda x: int(x.sum())),
            Count_Hibrido=("Es_Hibrido", lambda x: int(x.sum())),
            Count_FullyDigital=("Es_FullyDigital", lambda x: int(x.sum()))
        )
        reporte_filtrado[["Cartera_Total", "Ventas_Totales", "Ventas_MiNegocio", "Count_NoDigital", "Count_Hibrido", "Count_FullyDigital"]] = reporte_filtrado[["Cartera_Total", "Ventas_Totales", "Ventas_MiNegocio", "Count_NoDigital", "Count_Hibrido", "Count_FullyDigital"]].fillna(0)
        
        reporte_filtrado["% Adopcion"] = (
            (reporte_filtrado["Count_Hibrido"] + reporte_filtrado["Count_FullyDigital"]) / 
            reporte_filtrado["Cartera_Total"].replace(0, pd.NA)
        ).mul(100.0).fillna(0.0).round(2)

        reporte_filtrado["% No Digital"] = (reporte_filtrado["Count_NoDigital"] / reporte_filtrado["Cartera_Total"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
        reporte_filtrado["% Híbridos"] = (reporte_filtrado["Count_Hibrido"] / reporte_filtrado["Cartera_Total"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
        reporte_filtrado["% FullyDigital"] = (reporte_filtrado["Count_FullyDigital"] / reporte_filtrado["Cartera_Total"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
        
        reporte_filtrado["CodVendedor"] = pd.to_numeric(reporte_filtrado["CodVendedor"], errors="coerce").astype("Int64")
        reporte_filtrado = reporte_filtrado.sort_values(by=["CodVendedor", "Taxonomia"], ascending=[True, True]).reset_index(drop=True)
    else:
        reporte_filtrado = pd.DataFrame(columns=["CodVendedor", "Nombre", "SUP", "Taxonomia", "Cartera_Total", "Ventas_Totales", "Ventas_MiNegocio", "% Adopcion", "% No Digital", "% Híbridos", "% FullyDigital"])

    tot_cartera = int(df_cli_filtrado["Cliente"].count()) if not df_cli_filtrado.empty else 0
    tot_ventas = float(df_cli_filtrado["Ventas_Totales"].sum()) if not df_cli_filtrado.empty else 0.0
    tot_mn = float(df_cli_filtrado["Ventas_MiNegocio"].sum()) if not df_cli_filtrado.empty else 0.0
    pct_venta_mn = (tot_mn / tot_ventas * 100.0) if tot_ventas > 0 else 0.0

    cartera_tax = df_cli_filtrado.groupby("Taxonomia")["Cliente"].count() if not df_cli_filtrado.empty else pd.Series()
    cart_a = cartera_tax.get("A", 0)
    cart_b = cartera_tax.get("B", 0)
    cart_c = cartera_tax.get("C", 0)
    cart_d = cartera_tax.get("D", 0)

    cnt_nodigital = int(df_cli_filtrado["Es_NoDigital"].sum()) if not df_cli_filtrado.empty and "Es_NoDigital" in df_cli_filtrado.columns else 0
    cnt_hibrido = int(df_cli_filtrado["Es_Hibrido"].sum()) if not df_cli_filtrado.empty and "Es_Hibrido" in df_cli_filtrado.columns else 0
    cnt_fully = int(df_cli_filtrado["Es_FullyDigital"].sum()) if not df_cli_filtrado.empty and "Es_FullyDigital" in df_cli_filtrado.columns else 0

    st.markdown("""
        <style>
        hr {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            border-color: #334155 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    cols_r1 = st.columns(3)
    with cols_r1[0]:
        st.markdown(_tarjeta_metrica_compacta_html("VENTAS TOTALES", f"${tot_ventas:,.2f}", "#38bdf8", "2px"), unsafe_allow_html=True)
    with cols_r1[1]:
        st.markdown(_tarjeta_metrica_compacta_html("VENTA TOTAL MN+", f"${tot_mn:,.2f}", "#38bdf8", "2px"), unsafe_allow_html=True)
    with cols_r1[2]:
        st.markdown(_tarjeta_metrica_compacta_html("% VENTA MN+", f"{pct_venta_mn:,.2f}%", "#38bdf8", "2px"), unsafe_allow_html=True)

    st.divider()

    cols_r2 = st.columns(5)
    with cols_r2[0]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA TOTAL", f"{tot_cartera:,.0f}", "#3b82f6", "1px"), unsafe_allow_html=True)
    with cols_r2[1]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA A", f"{cart_a:,.0f}", "#ef4444", "1px"), unsafe_allow_html=True)
    with cols_r2[2]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA B", f"{cart_b:,.0f}", "#f97316", "1px"), unsafe_allow_html=True)
    with cols_r2[3]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA C", f"{cart_c:,.0f}", "#eab308", "1px"), unsafe_allow_html=True)
    with cols_r2[4]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA D", f"{cart_d:,.0f}", "#22c55e", "1px"), unsafe_allow_html=True)

    st.divider()

    cols_r3 = st.columns(3)
    with cols_r3[0]:
        st.markdown(_tarjeta_metrica_compacta_html("CLIENTES NO DIGITAL", f"{cnt_nodigital:,.0f}", "#ef4444", "1px"), unsafe_allow_html=True)
    with cols_r3[1]:
        st.markdown(_tarjeta_metrica_compacta_html("CLIENTES HÍBRIDOS", f"{cnt_hibrido:,.0f}", "#f97316", "1px"), unsafe_allow_html=True)
    with cols_r3[2]:
        st.markdown(_tarjeta_metrica_compacta_html("CLIENTES FULLY DIGITAL", f"{cnt_fully:,.0f}", "#22c55e", "1px"), unsafe_allow_html=True)

    st.divider()

    columnas_visuales_mn = [
        "CodVendedor", "Nombre", "SUP", "Taxonomia", 
        "Cartera_Total", "Ventas_Totales", "Ventas_MiNegocio", 
        "% Adopcion", "% No Digital", "% Híbridos", "% FullyDigital"
    ]
    reporte_render = reporte_filtrado[columnas_visuales_mn].copy().reset_index(drop=True)

    reporte_render_excel = reporte_render.copy()
    reporte_render_display = reporte_render.copy()

    cols_pesos_mn = ["Ventas_Totales", "Ventas_MiNegocio"]
    cols_porc_mn = ["% Adopcion", "% No Digital", "% Híbridos", "% FullyDigital"]

    for col in cols_pesos_mn:
        if col in reporte_render_display.columns:
            reporte_render_display[col] = reporte_render_display[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
    for col in cols_porc_mn:
        if col in reporte_render_display.columns:
            reporte_render_display[col] = reporte_render_display[col].apply(lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%")

    if not reporte_render_display.empty:
        gb = GridOptionsBuilder.from_dataframe(reporte_render_display)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=120)
        
        gb.configure_column("CodVendedor", headerName="Cód. Vend", width=90, valueFormatter="x != null ? Number(x).toFixed(0) : ''")
        gb.configure_column("Nombre", headerName="Preventista", minWidth=160)
        gb.configure_column("SUP", headerName="SUP", width=75)
        gb.configure_column("Taxonomia", headerName="Tax", width=70)
        gb.configure_column("Cartera_Total", headerName="Cartera Total", width=100)
        
        gb.configure_column("Ventas_Totales", headerName="Ventas Totales ($)", width=130)
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
            fit_columns_on_grid_load=False
        )
    else:
        st.info("No se encontraron registros con los filtros seleccionados.")

    st.divider()

    st.markdown("### ⚔️ Batalla MiNegocio: Detalle Caso a Caso por Cliente (No Digital e Híbridos)")
    st.markdown("Listado de clientes pendientes de conversión digital (excluye FullyDigital), con montos, porcentaje de adopción y mínimo requerido en $ para alcanzar el 70%.")

    if not df_cli_filtrado.empty:
        df_batalla = df_cli_filtrado[df_cli_filtrado["Es_FullyDigital"] == False].copy()
        
        def determinar_categoria_txt(row):
            if row["Es_NoDigital"]:
                return "No Digital"
            elif row["Es_Hibrido"]:
                return "Híbridos"
            return "No Digital"

        df_batalla["Categoría App"] = df_batalla.apply(determinar_categoria_txt, axis=1)

        df_batalla_render = pd.DataFrame()
        df_batalla_render["Cód. Vend"] = df_batalla.get("CodVendedor", pd.Series())
        df_batalla_render["Preventista"] = df_batalla.get("Nombre", pd.Series())
        df_batalla_render["SUP"] = df_batalla.get("SUP", pd.Series())
        df_batalla_render["Cód. Cliente"] = df_batalla.get("Cliente", pd.Series())
        df_batalla_render["Razón Social"] = df_batalla.get("NombreCliente", pd.Series())
        df_batalla_render["Dirección"] = df_batalla.get("DireccionCliente", pd.Series())
        df_batalla_render["Día Visita"] = df_batalla.get("DiaVisita", pd.Series())
        df_batalla_render["Taxonomía"] = df_batalla.get("Taxonomia", pd.Series())
        df_batalla_render["Ventas Totales ($)"] = df_batalla.get("Ventas_Totales", pd.Series())
        df_batalla_render["Ventas App ($)"] = df_batalla.get("Ventas_MiNegocio", pd.Series())
        df_batalla_render["% Adopción"] = df_batalla.get("Pct_MiNegocio", pd.Series())
        df_batalla_render["Faltante Mín. 70% ($)"] = df_batalla.get("Minimo_Facturacion_70", pd.Series())
        df_batalla_render["Categoría App"] = df_batalla.get("Categoría App", pd.Series())

        df_batalla_render = df_batalla_render.reset_index(drop=True)
    else:
        df_batalla_render = pd.DataFrame(columns=["Cód. Vend", "Preventista", "SUP", "Cód. Cliente", "Razón Social", "Dirección", "Día Visita", "Taxonomía", "Ventas Totales ($)", "Ventas App ($)", "% Adopción", "Faltante Mín. 70% ($)", "Categoría App"])

    df_batalla_excel = df_batalla_render.copy()
    df_batalla_display = df_batalla_render.copy()

    for col in ["Ventas Totales ($)", "Ventas App ($)", "Faltante Mín. 70% ($)"]:
        if col in df_batalla_display.columns:
            df_batalla_display[col] = df_batalla_display[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
    if "% Adopción" in df_batalla_display.columns:
        df_batalla_display["% Adopción"] = df_batalla_display["% Adopción"].apply(lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%")

    if not df_batalla_display.empty:
        gb_b = GridOptionsBuilder.from_dataframe(df_batalla_display)
        gb_b.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=120)
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
            fit_columns_on_grid_load=False
        )
    else:
        st.info("No hay registros de clientes pendientes de conversión digital con los filtros seleccionados.")

    st.divider()

    col_dl1, col_dl2, col_dl3 = st.columns(3)
    with col_dl1:
        buffer_mn = io.BytesIO()
        with pd.ExcelWriter(buffer_mn, engine="openpyxl") as writer:
            reporte_render_excel.to_excel(writer, index=False, sheet_name="Adopcion_MiNegocio_Taxonomia")
        buffer_mn.seek(0)
        st.download_button(
            label="📥 Descargar Resumen a Excel",
            data=buffer_mn,
            file_name="Adopcion_MiNegocio_Resumen.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="mn_frag_btn_dl_res"
        )

    with col_dl2:
        buffer_bat = io.BytesIO()
        with pd.ExcelWriter(buffer_bat, engine="openpyxl") as writer:
            df_batalla_excel.to_excel(writer, index=False, sheet_name="Batalla_MiNegocio_Clientes")
        buffer_bat.seek(0)
        st.download_button(
            label="📥 Descargar Batalla a Excel",
            data=buffer_bat,
            file_name="Batalla_MiNegocio_Clientes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="mn_frag_btn_dl_bat"
        )

    with col_dl3:
        if not df_batalla_render.empty:
            lista_mn_formateada = []
            for idx, row in df_batalla_render.iterrows():
                cli = row.get("Cód. Cliente", "")
                nom = row.get("Razón Social", "")
                dir_c = row.get("Dirección", "")
                dia = row.get("Día Visita", "")
                pct_app = row.get("% Adopción", 0.0)
                faltante = row.get("Faltante Mín. 70% ($)", 0.0)
                cat = row.get("Categoría App", "")
                
                lista_mn_formateada.append(f"[{cli}] {nom} - {dir_c} - {dia} | App: {pct_app:,.2f}% ({cat}) - Faltante 70%: ${faltante:,.2f}")

            detalle_texto = "%0A".join(lista_mn_formateada)
            total_cnt = len(df_batalla_render)
            
            texto_wa = f"MiNegocio Pendientes (Total: {total_cnt})%0A{detalle_texto}"
            url_wa = f"https://wa.me/?text={texto_wa}"
            
            st.markdown(f'''
                <div style="display: flex; justify-content: center; align-items: center; height: 100%; padding-top: 5px;">
                    <a href="{url_wa}" target="_blank" style="
                        display: inline-block;
                        padding: 4px 10px;
                        background-color: #25d366;
                        color: white;
                        text-align: center;
                        text-decoration: none;
                        font-weight: 600;
                        font-size: 0.75rem;
                        border-radius: 4px;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    ">💬 WhatsApp MiNegocio</a>
                </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('<div style="padding:0.5rem;text-align:center;color:#94a3b8;font-size:0.85rem;">Sin datos para WhatsApp</div>', unsafe_allow_html=True)

def render_rep_mn(df_vta, df_universo, filtros_globales=None):
    st.subheader("📱 Adopción MiNegocio por Taxonomía")
    st.markdown("Analiza la adopción y penetración de la aplicación MiNegocio segmentada por taxonomía, vendedor y día de visita sobre el universo total de cartera.")

    sup_filtro = "TODOS"
    if filtros_globales and isinstance(filtros_globales, dict):
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    except Exception:
        maestro_v = pd.DataFrame()

    df_det = generar_reporte_mn_taxonomia(df_vta, df_universo, maestro_v, filtros_globales)
    
    if sup_filtro != "TODOS" and not df_det.empty and "SUP" in df_det.columns:
        df_det = df_det[df_det["SUP"].astype(str).str.strip() == sup_filtro].copy()

    sups_sel = [sup_filtro] if sup_filtro != "TODOS" else None
    render_fragmento_interactivo_mn(df_det, sups_sel)

====================================================================================================


### ARCHIVO: modules\rep_obj_kilos.py

# modules/rep_obj_kilos.py
import io
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import parsear_fecha_robusta

def generar_distribucion_objetivos_macro(df_vta, maestro_v, maestro_cebe_act, maestro_cebe_ant, maestro_seg, anio_operativo, mes_operativo):
    """
    Calcula la distribución proporcional del objetivo macro de la compañía en Kilos 
    utilizando obligatoriamente el Master DataFrame Corporativo como fuente de verdad con vectorización.
    """
    df_corp = db.obtener_df_maestro_corporativo()
    df_base_vta = df_corp.copy() if not df_corp.empty else (df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame())

    if maestro_v is None or maestro_v.empty:
        return pd.DataFrame(), []

    col_cod_v = "Codigo_Vendedor" if "Codigo_Vendedor" in maestro_v.columns else maestro_v.columns[0]
    col_nom_v = "Nombre_Vendedor" if "Nombre_Vendedor" in maestro_v.columns else maestro_v.columns[1]
    col_sup_v = "Supervisor" if "Supervisor" in maestro_v.columns else (maestro_v.columns[2] if len(maestro_v.columns) > 2 else maestro_v.columns[0])

    df_padron = maestro_v[[col_cod_v, col_nom_v, col_sup_v]].copy()
    df_padron.columns = ["CodVendedor", "Nombre", "Supervisor"]
    
    df_padron["CodVendedor"] = pd.to_numeric(df_padron["CodVendedor"], errors="coerce").astype("Int64")
    df_padron["Nombre"] = df_padron["Nombre"].fillna("").astype(str).str.strip()
    df_padron["Supervisor"] = df_padron["Supervisor"].fillna("SIN SUPERVISOR").astype(str).str.strip()
    df_padron = df_padron.dropna(subset=["CodVendedor"]).drop_duplicates(subset=["CodVendedor"])

    if mes_operativo == 1:
        mes_ant = 12
        anio_ant = anio_operativo - 1
    else:
        mes_ant = mes_operativo - 1
        anio_ant = anio_operativo

    obj_act_map = {}
    cebe_map = {}
    if maestro_cebe_act is not None and not maestro_cebe_act.empty:
        cm_act = next((c for c in maestro_cebe_act.columns if "marca" in str(c).strip().lower()), maestro_cebe_act.columns[0])
        cc_act = next((c for c in maestro_cebe_act.columns if "cebe" in str(c).strip().lower()), maestro_cebe_act.columns[1] if len(maestro_cebe_act.columns) > 1 else maestro_cebe_act.columns[0])
        co_act = next((c for c in maestro_cebe_act.columns if any(k in str(c).strip().lower() for k in ["obj_tn", "tn", "obj_mes", "objetivo", "obj"])), None)
        
        for _, r in maestro_cebe_act.iterrows():
            m = str(r.get(cm_act, "")).strip().upper()
            c = str(r.get(cc_act, "")).strip()
            val_kg = pd.to_numeric(r.get(co_act, 0.0), errors="coerce") if co_act else 0.0
            if m and m != "NAN":
                obj_act_map[m] = val_kg if pd.notna(val_kg) else 0.0
                cebe_map[m] = c if c and c != "NAN" else "GLOBAL"

    obj_ant_map = {}
    if maestro_cebe_ant is not None and not maestro_cebe_ant.empty:
        cm_ant = next((c for c in maestro_cebe_ant.columns if "marca" in str(c).strip().lower()), maestro_cebe_ant.columns[0])
        co_ant = next((c for c in maestro_cebe_ant.columns if any(k in str(c).strip().lower() for k in ["obj_tn", "tn", "obj_mes", "objetivo", "obj"])), None)
        
        for _, r in maestro_cebe_ant.iterrows():
            m = str(r.get(cm_ant, "")).strip().upper()
            val_kg = pd.to_numeric(r.get(co_ant, 0.0), errors="coerce") if co_ant else 0.0
            if m and m != "NAN":
                obj_ant_map[m] = val_kg if pd.notna(val_kg) else 0.0

    segmentos_orden_lista = []
    segmentos_validos = set()
    if maestro_seg is not None and not maestro_seg.empty:
        cs_seg = next((c for c in maestro_seg.columns if "segmento" in str(c).strip().lower()), maestro_seg.columns[0])
        for _, r in maestro_seg.iterrows():
            seg = str(r.get(cs_seg, "")).strip()
            if seg and seg.lower() != "nan":
                segmentos_validos.add(seg)
                if seg not in segmentos_orden_lista:
                    segmentos_orden_lista.append(seg)

    if not segmentos_validos:
        segmentos_validos = {"GOLD Salty", "GOLD Crakers", "SILVER Salty", "SILVER Crakers", "SILVER Cereals"}
        segmentos_orden_lista = ["GOLD Salty", "GOLD Crakers", "SILVER Salty", "SILVER Crakers", "SILVER Cereals"]

    if df_base_vta.empty:
        return pd.DataFrame(), segmentos_orden_lista

    vta = df_base_vta.copy()
    
    if "TipoDeVenta" in vta.columns:
        tipos_excluidos = ["Comodato Devolución", "Comodato Ficticio", "Comodato Ficticio Devolución", "Comodato Préstamo"]
        vta = vta[~vta["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)]

    if "Proveedor" in vta.columns:
        vta = vta[vta["Proveedor"].fillna("").astype(str).str.strip().str.upper().str.contains("PEPSICO", na=False)]

    if "Subramo" in vta.columns:
        subramo_clean = vta["Subramo"].fillna("").astype(str).str.strip().str.upper()
        vta = vta[~subramo_clean.isin(["EMPLOYEES", "EMPLEADOS"])]

    if "FechaEntrega" in vta.columns:
        vta["FechaEntrega_dt"] = parsear_fecha_robusta(vta["FechaEntrega"])
    else:
        vta["FechaEntrega_dt"] = pd.NaT

    vta_mes_ant = vta[
        (vta["FechaEntrega_dt"].dt.year == int(anio_ant)) & 
        (vta["FechaEntrega_dt"].dt.month == int(mes_ant))
    ].copy()

    if vta_mes_ant.empty:
        vta_mes_ant = vta.copy()

    if vta_mes_ant.empty:
        return pd.DataFrame(), segmentos_orden_lista

    col_vend = next((c for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"] if c in vta_mes_ant.columns), None)
    vta_mes_ant["CodVendedor"] = pd.to_numeric(vta_mes_ant[col_vend], errors="coerce").astype("Int64") if col_vend else pd.NA

    col_m = next((c for c in ["Marca", "MARCA", "marca"] if c in vta_mes_ant.columns), None)
    vta_mes_ant["Marca"] = vta_mes_ant[col_m].fillna("").astype(str).str.strip().str.upper() if col_m else "SIN MARCA"

    col_rent = "SegmentoRentabilidad" if "SegmentoRentabilidad" in vta_mes_ant.columns else None
    col_rubro = "Rubro" if "Rubro" in vta_mes_ant.columns else None

    # Vectorización de asignación de segmentos en objetivos
    sr_obj = vta_mes_ant.get(col_rent, pd.Series("", index=vta_mes_ant.index)).fillna("").astype(str).str.strip().str.title() if col_rent else pd.Series("", index=vta_mes_ant.index)
    rubro_obj = vta_mes_ant.get(col_rubro, pd.Series("", index=vta_mes_ant.index)).fillna("").astype(str).str.strip() if col_rubro else pd.Series("", index=vta_mes_ant.index)
    
    cond_gold_obj = sr_obj.isin(["Platinum", "Gold"])
    cond_silver_obj = sr_obj.isin(["Silver", "Bronze"])
    
    gold_val_obj = "GOLD " + rubro_obj
    silver_val_obj = "SILVER " + rubro_obj
    
    default_seg = list(segmentos_validos)[0] if segmentos_validos else "GOLD Salty"
    vta_mes_ant["SEGMENTO"] = np.select(
        [cond_gold_obj, cond_silver_obj],
        [gold_val_obj.str.strip(), silver_val_obj.str.strip()],
        default=default_seg
    )
    
    # Validar que pertenezcan a los segmentos válidos
    vta_mes_ant["SEGMENTO"] = np.where(vta_mes_ant["SEGMENTO"].isin(segmentos_validos), vta_mes_ant["SEGMENTO"], default_seg)

    col_kg = next((c for c in ["PesoKg", "PESOKG", "Kilos", "KILOS"] if c in vta_mes_ant.columns), None)
    vta_mes_ant["Kilos"] = pd.to_numeric(vta_mes_ant[col_kg], errors="coerce").fillna(0.0) if col_kg else 0.0

    vta_mes_ant = vta_mes_ant.dropna(subset=["CodVendedor"]).copy()

    if vta_mes_ant.empty:
        df_padron_k = df_padron.copy()
        df_padron_k["_k"] = 1
        df_seg_k = pd.DataFrame({"SEGMENTO": list(segmentos_validos)})
        df_seg_k["_k"] = 1
        df_reporte = df_padron_k.merge(df_seg_k, on="_k").drop(columns="_k")
        df_reporte["Kilos_Mes_Anterior"] = 0.0
        df_reporte["Objetivo_Mes_Anterior_Kg"] = 0.0
        df_reporte["Logro_Anterior_Pct"] = 0.0
        df_reporte["Obj_Sugerido_Kg"] = 0.0
    else:
        vta_agrup = vta_mes_ant.groupby(
            ["CodVendedor", "Marca", "SEGMENTO"], 
            as_index=False
        )["Kilos"].sum().rename(columns={"Kilos": "Kilos_Mes_Anterior"})

        df_reporte = df_padron.merge(vta_agrup, on="CodVendedor", how="inner")
        df_reporte["CEBE"] = df_reporte["Marca"].map(cebe_map).fillna("GLOBAL")
        df_reporte["Obj_Macro_Marca_Kg"] = df_reporte["Marca"].map(obj_act_map).fillna(0.0)

        df_reporte["Total_Kilos_Marca"] = df_reporte.groupby("Marca")["Kilos_Mes_Anterior"].transform("sum")
        df_reporte["Participacion_Pct"] = (df_reporte["Kilos_Mes_Anterior"] / df_reporte["Total_Kilos_Marca"].replace(0, pd.NA)).fillna(0.0)

        obj_ant_ser = df_reporte["Marca"].map(obj_ant_map).fillna(0.0)
        df_reporte["Objetivo_Mes_Anterior_Kg"] = df_reporte["Participacion_Pct"] * obj_ant_ser

        df_reporte["Logro_Anterior_Pct"] = (df_reporte["Kilos_Mes_Anterior"] / df_reporte["Objetivo_Mes_Anterior_Kg"].replace(0, pd.NA)).mul(100).fillna(0.0)
        df_reporte["Obj_Sugerido_Kg"] = df_reporte["Participacion_Pct"] * df_reporte["Obj_Macro_Marca_Kg"]

        df_reporte = df_reporte.drop(columns=["Total_Kilos_Marca"], errors="ignore")

    if segmentos_orden_lista:
        df_reporte["SEGMENTO"] = pd.Categorical(df_reporte["SEGMENTO"], categories=segmentos_orden_lista, ordered=True)

    sort_cols = [c for c in ["Supervisor", "Nombre", "Marca", "SEGMENTO"] if c in df_reporte.columns]
    df_reporte = df_reporte.sort_values(by=sort_cols).reset_index(drop=True)
    df_reporte["SEGMENTO"] = df_reporte["SEGMENTO"].astype(str)

    df_reporte["Anio"] = int(anio_operativo)
    df_reporte["Mes"] = int(mes_operativo)

    columnas_finales = [
        "Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "SEGMENTO", 
        "Kilos_Mes_Anterior", "Objetivo_Mes_Anterior_Kg", "Logro_Anterior_Pct", 
        "Obj_Sugerido_Kg"
    ]
    
    for col in columnas_finales:
        if col not in df_reporte.columns:
            df_reporte[col] = 0.0

    return df_reporte[columnas_finales], segmentos_orden_lista

def render_rep_obj_kilos(df_vta, filtros_globales=None):
    st.subheader("📦 Generador Tentativo de Objetivos por Vendedor y Segmento")

    if filtros_globales is None:
        anio_op = 2026
        mes_op = 9
        sup_filtro = "TODOS"
    else:
        anio_op = int(filtros_globales.get("anio", 2026))
        mes_op = int(filtros_globales.get("mes", 9))
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()

    mes_ant_eval = 12 if mes_op == 1 else mes_op - 1
    anio_ant_eval = anio_op - 1 if mes_op == 1 else anio_op
    
    st.markdown(f"**Período Operativo:** {mes_op:02d}/{anio_op} | **Referencia Histórica:** {mes_ant_eval:02d}/{anio_ant_eval}")

    coef_opciones = list(range(100, 111))
    coef_sel = st.selectbox(
        "📈 Coeficiente de Ajuste de Objetivo (%)",
        options=coef_opciones,
        format_func=lambda x: f"{x}%",
        index=0,
        key="sel_coef_ajuste_obj"
    )
    factor_multiplicador = coef_sel / 100.0

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        if not maestro_v.empty and "Mes" in maestro_v.columns:
            mv_per = maestro_v[
                (maestro_v["Mes"].astype(str).str.strip() == str(mes_op)) & 
                (maestro_v["Anio"].astype(str).str.strip() == str(anio_op))
            ]
            if not mv_per.empty:
                maestro_v = mv_per
    except Exception:
        maestro_v = pd.DataFrame()

    try:
        maestro_seg = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos ORDER BY rowid ASC")
        if not maestro_seg.empty and "Mes" in maestro_seg.columns:
            ms_per = maestro_seg[
                (maestro_seg["Mes"].astype(str).str.strip() == str(mes_op)) & 
                (maestro_seg["Anio"].astype(str).str.strip() == str(anio_op))
            ]
            if not ms_per.empty:
                maestro_seg = ms_per
    except Exception:
        maestro_seg = pd.DataFrame()

    try:
        maestro_cebe_act = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if not maestro_cebe_act.empty and "Mes" in maestro_cebe_act.columns:
            mc_per = maestro_cebe_act[
                (maestro_cebe_act["Mes"].astype(str).str.strip() == str(mes_op)) & 
                (maestro_cebe_act["Anio"].astype(str).str.strip() == str(anio_op))
            ]
            if not mc_per.empty:
                maestro_cebe_act = mc_per
    except Exception:
        maestro_cebe_act = pd.DataFrame()

    try:
        maestro_cebe_ant = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if not maestro_cebe_ant.empty and "Mes" in maestro_cebe_ant.columns:
            mc_ant = maestro_cebe_ant[
                (maestro_cebe_ant["Mes"].astype(str).str.strip() == str(mes_ant_eval)) & 
                (maestro_cebe_ant["Anio"].astype(str).str.strip() == str(anio_ant_eval))
            ]
            if not mc_ant.empty:
                maestro_cebe_ant = mc_ant
    except Exception:
        maestro_cebe_ant = pd.DataFrame()

    if maestro_v.empty:
        st.warning("⚠️ No se encontró el Maestro de Vendedores cargado para este período en la base de datos.")
        return

    cache_key = f"_cache_rep_obj_distribucion_v15_{anio_op}_{mes_op}_{sup_filtro}"
    if cache_key not in st.session_state:
        with st.spinner("Calculando distribución proporcional de objetivos macro en Kilos..."):
            df_base, seg_orden = generar_distribucion_objetivos_macro(df_vta, maestro_v, maestro_cebe_act, maestro_cebe_ant, maestro_seg, anio_op, mes_op)
            st.session_state[cache_key] = (df_base, seg_orden)
    else:
        df_base, seg_orden = st.session_state[cache_key]

    if df_base is None or df_base.empty:
        st.info("No se encontraron registros coincidentes con los maestros oficiales para el período de referencia.")
        return

    df_filtrado = df_base.copy()
    if sup_filtro != "TODOS" and "Supervisor" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Supervisor"].astype(str).str.strip() == sup_filtro].copy()

    df_filtrado["Obj_Sugerido_Kg"] = df_filtrado["Obj_Sugerido_Kg"] * factor_multiplicador

    df_agrupado = df_filtrado.groupby(
        ["Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "SEGMENTO"],
        as_index=False
    ).agg({
        "Kilos_Mes_Anterior": "sum",
        "Objetivo_Mes_Anterior_Kg": "sum",
        "Obj_Sugerido_Kg": "sum"
    })

    df_agrupado["Logro_Anterior_Pct"] = (
        df_agrupado["Kilos_Mes_Anterior"] / df_agrupado["Objetivo_Mes_Anterior_Kg"].replace(0, pd.NA)
    ).mul(100).fillna(0.0)

    if seg_orden:
        df_agrupado["SEGMENTO"] = pd.Categorical(df_agrupado["SEGMENTO"], categories=seg_orden, ordered=True)

    df_agrupado = df_agrupado.sort_values(by=["Supervisor", "Nombre", "SEGMENTO"]).reset_index(drop=True)
    df_agrupado["SEGMENTO"] = df_agrupado["SEGMENTO"].astype(str)

    columnas_orden_ui = [
        "Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "SEGMENTO", 
        "Kilos_Mes_Anterior", "Objetivo_Mes_Anterior_Kg", "Logro_Anterior_Pct", 
        "Obj_Sugerido_Kg"
    ]
    df_agrupado = df_agrupado[[c for c in columnas_orden_ui if c in df_agrupado.columns]]

    total_kilos_ant = df_agrupado["Kilos_Mes_Anterior"].sum()
    total_obj_sugerido = df_agrupado["Obj_Sugerido_Kg"].sum()
    
    total_macro_compania = 0.0
    if not maestro_cebe_act.empty:
        co_act = next((c for c in maestro_cebe_act.columns if any(k in str(c).strip().lower() for k in ["obj_tn", "tn", "obj_mes", "objetivo", "obj"])), None)
        if co_act:
            total_macro_compania = pd.to_numeric(maestro_cebe_act[co_act], errors="coerce").sum()

    m1, m2, m3 = st.columns(3)
    m1.metric("📦 Total Kilos Históricos", f"{total_kilos_ant:,.1f} kg")
    m2.metric("🏢 Total Macro Compañía", f"{total_macro_compania:,.1f} kg")
    m3.metric("🎯 Total Objetivo Sugerido", f"{total_obj_sugerido:,.1f} kg")

    if not df_agrupado.empty and "SEGMENTO" in df_agrupado.columns:
        tot_por_seg = df_agrupado.groupby("SEGMENTO")["Obj_Sugerido_Kg"].sum()
        if seg_orden:
            tot_por_seg = tot_por_seg.reindex([s for s in seg_orden if s in tot_por_seg.index])
        
        st.markdown("📌 **Objetivo Sugerido por Segmento:**")
        for seg, val in tot_por_seg.items():
            st.markdown(f"- **{seg}**: {val:,.2f} kg")

    st.divider()

    gb = GridOptionsBuilder.from_dataframe(df_agrupado)
    gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=130, cellStyle={'textAlign': 'center'}, headerClass='centered-header')
    
    gb.configure_column("Anio", headerName="Año", width=80)
    gb.configure_column("Mes", headerName="Mes", width=70)
    gb.configure_column("CodVendedor", headerName="Cód. Vend", width=100)
    gb.configure_column("Nombre", headerName="Vendedor", minWidth=180, cellStyle={'textAlign': 'left'}, headerClass='left-header')
    gb.configure_column("Supervisor", headerName="Supervisor", minWidth=140, cellStyle={'textAlign': 'left'}, headerClass='left-header')
    gb.configure_column("SEGMENTO", headerName="Segmento", minWidth=160, cellStyle={'textAlign': 'left'}, headerClass='left-header')
    
    gb.configure_column(
        "Kilos_Mes_Anterior", 
        headerName="Kilos Mes Ant.",
        valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'"
    )
    gb.configure_column(
        "Objetivo_Mes_Anterior_Kg", 
        headerName="Obj. Mes Ant. (Kg)",
        valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'"
    )
    gb.configure_column(
        "Logro_Anterior_Pct", 
        headerName="% Logro Ant.",
        valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '%' : '0.00%'"
    )
    gb.configure_column(
        "Obj_Sugerido_Kg", 
        headerName="Obj. Sugerido (Kg)",
        valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'"
    )

    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    grid_options = gb.build()

    st.markdown("""
    <style>
    .ag-header-cell-label {
        justify-content: center !important;
        text-align: center !important;
    }
    .left-header .ag-header-cell-label {
        justify-content: flex-start !important;
        text-align: left !important;
    }
    </style>
    """, unsafe_allow_html=True)

    AgGrid(
        df_agrupado,
        gridOptions=grid_options,
        height=450,
        width="100%",
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        theme="streamlit",
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True
    )

    st.divider()

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_agrupado.to_excel(writer, index=False, sheet_name="Objetivos_Vendedor_Segmento")
    buffer.seek(0)

    st.download_button(
        label="📥 Descargar Propuesta Tentativa a Excel",
        data=buffer,
        file_name=f"Propuesta_Objetivos_{mes_op}_{anio_op}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"btn_dl_propuesta_obj_{mes_op}_{anio_op}"
    )

====================================================================================================


### ARCHIVO: modules\rep_tp.py

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


====================================================================================================


### ARCHIVO: modules\rep_vespertina.py

# modules/rep_vespertina.py
import io
import time
import sqlite3
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import parsear_fecha_robusta, tarjeta_metrica_html
from modules.rep_ccc import preparar_ventas_ccc


def preparar_vespertina_resumen(df_vta, dia_venta):
    """
    Pipeline de datos exclusivo para el resumen ejecutivo del Día Venta derivado del DataFrame Maestro N1 (EMPLEADOS).
    Aplica los filtros N2: PEPSICO, COMODATOS, DEPOSITO y PERIODO.
    """
    t_start = time.perf_counter()
    # Nivel 1: Obtención del DataFrame corporativo base con filtro EMPLEADOS aplicado
    df_corp = db.obtener_df_maestro_corporativo()
    df = (
        df_corp.copy()
        if not df_corp.empty
        else (
            df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame()
        )
    )

    if df.empty:
        return df

    col_pesos = next(
        (
            c
            for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"]
            if c in df.columns
        ),
        None,
    )
    df["ImporteNeto"] = (
        pd.to_numeric(df[col_pesos], errors="coerce").fillna(0.0) if col_pesos else 0.0
    )

    col_kg = next(
        (c for c in ["PesoKg", "PESOKG", "Kilos", "KILOS"] if c in df.columns), None
    )
    df["PesoKg"] = (
        pd.to_numeric(df[col_kg], errors="coerce").fillna(0.0) if col_kg else 0.0
    )

    col_cant = next(
        (
            c
            for c in [
                "CantBase",
                "CANTBASE",
                "Cantidad",
                "CANTIDAD",
                "Unidades",
                "UNIDADES",
            ]
            if c in df.columns
        ),
        df.columns[0],
    )
    df["CantBase"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0.0)

    col_orig = next(
        (
            c
            for c in df.columns
            if any(k in str(c).lower() for k in ["origen", "canal"])
        ),
        None,
    )
    if col_orig:
        df["OrigenDeVta"] = df[col_orig].fillna("").astype(str).str.strip()
        df["Es_MiNegocio"] = df["OrigenDeVta"].str.contains(
            "minegocio|mi negocio", case=False, na=False
        )
    else:
        df["OrigenDeVta"] = ""
        df["Es_MiNegocio"] = False

    # Nivel 2: Filtro COMODATOS (Exclusión de comodatos y préstamos)
    if "TipoDeVenta" in df.columns:
        tipos_excluidos = [
            "Comodato Devolución",
            "Comodato Ficticio",
            "Comodato Ficticio Devolución",
            "Comodato Préstamo",
        ]
        df = df[~df["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)]

    # Nivel 2: Filtro PEPSICO (Selección exclusiva de proveedor PepsiCo)
    if "Proveedor" in df.columns:
        df = df[
            df["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))

    col_vend_tit = next(
        (
            cand
            for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
            if cand in df.columns
        ),
        "CodVendedor",
    )
    df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype("Int64")

    # Nivel 2: Filtro DEPOSITO (Exclusión del vendedor 20 para aislar preventistas puros)
    df = df[df["CodVendedor"] != 20]

    col_rent = "SegmentoRentabilidad" if "SegmentoRentabilidad" in df.columns else None
    col_rubro = "Rubro" if "Rubro" in df.columns else None

    sr = (
        df.get(col_rent, pd.Series("", index=df.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .str.title()
        if col_rent
        else pd.Series("", index=df.index)
    )
    rubro = (
        df.get(col_rubro, pd.Series("", index=df.index))
        .fillna("")
        .astype(str)
        .str.strip()
        if col_rubro
        else pd.Series("", index=df.index)
    )

    cond_gold = sr.isin(["Platinum", "Gold"]).fillna(False)
    cond_silver = sr.isin(["Silver", "Bronze"]).fillna(False)

    gold_val = "GOLD " + rubro
    silver_val = "SILVER " + rubro
    df["SEGMENTO"] = np.select(
        [cond_gold, cond_silver],
        [gold_val.str.strip(), silver_val.str.strip()],
        default="SIN SEGMENTO",
    )

    df["_mn_val"] = np.where(df["Es_MiNegocio"], df["ImporteNeto"], 0.0)
    print(
        f"[PERF_INTERNAL] preparar_vespertina_resumen = {time.perf_counter() - t_start:.2f} s"
    )
    return df


def clasificar_estado_fd(ratio):
    """Clasifica estrictamente el estado digital según el ratio de MiNegocio."""
    if ratio >= 0.70:
        return "Fully Digital"
    elif ratio > 0.0:
        return "Híbrido"
    else:
        return "No Digital"


def generar_reporte_vespertina_resumen(
    df_vta, df_universo_param, vendedores, filtros_globales=None
):
    """Genera las métricas unificadas del Día Venta evaluando estados, conversiones y activaciones CCC (Arrastre + Actual)."""
    t_start = time.perf_counter()
    dia_venta = (
        filtros_globales.get("dia_venta", "19/09/2026")
        if filtros_globales
        else "19/09/2026"
    )
    anio_op = int(filtros_globales.get("anio", 2026)) if filtros_globales else 2026
    mes_op = int(filtros_globales.get("mes", 9)) if filtros_globales else 9
    dia_matinal = (
        filtros_globales.get("dia_matinal", "21/09/2026")
        if filtros_globales
        else "21/09/2026"
    )

    df_full = preparar_vespertina_resumen(df_vta, dia_venta)
    if df_full.empty:
        return pd.DataFrame()

    dia_vta_dt = parsear_fecha_robusta(pd.Series([dia_venta])).iloc[0]
    target_date = dia_vta_dt.date() if pd.notna(dia_vta_dt) else None

    vendedores_df = pd.DataFrame()
    vendedores_seguro = (
        vendedores.copy()
        if vendedores is not None and not vendedores.empty
        else pd.DataFrame(columns=["Codigo_Vendedor", "Nombre_Vendedor", "Supervisor"])
    )

    col_c_v = next(
        (
            c
            for c in ["Codigo_Vendedor", "CodVend", "CodVendedor"]
            if c in vendedores_seguro.columns
        ),
        vendedores_seguro.columns[0],
    )
    col_n_v = next(
        (c for c in ["Nombre_Vendedor", "Nombre"] if c in vendedores_seguro.columns),
        vendedores_seguro.columns[1]
        if len(vendedores_seguro.columns) > 1
        else vendedores_seguro.columns[0],
    )
    col_s_v = next(
        (c for c in ["Supervisor", "SUP"] if c in vendedores_seguro.columns),
        vendedores_seguro.columns[2]
        if len(vendedores_seguro.columns) > 2
        else vendedores_seguro.columns[0],
    )

    vendedores_df["CodVendedor"] = pd.to_numeric(
        vendedores_seguro[col_c_v], errors="coerce"
    ).astype("Int64")
    vendedores_df["Nombre"] = (
        vendedores_seguro[col_n_v].fillna("").astype(str).str.strip()
    )
    vendedores_df["SUP"] = vendedores_seguro[col_s_v].fillna("").astype(str).str.strip()
    vendedores_df = vendedores_df[vendedores_df["CodVendedor"] != 20].drop_duplicates(
        "CodVendedor"
    )

    if not df_full.empty and not vendedores_df.empty:
        df_full = df_full.merge(
            vendedores_df[["CodVendedor", "SUP"]], on="CodVendedor", how="left"
        )
        df_full["SUP"] = df_full["SUP"].fillna("SIN SUPERVISOR")
    else:
        df_full["SUP"] = "SIN SUPERVISOR"

    t_s1 = time.perf_counter()
    univ_m = pd.DataFrame()
    try:
        univ_m = db.cargar_tabla_sql("SELECT * FROM universo")
    except Exception:
        pass
    print(
        f"[PERF_INTERNAL] consulta_sqlite_universo = {time.perf_counter() - t_s1:.2f} s"
    )

    if univ_m.empty and df_universo_param is not None and not df_universo_param.empty:
        univ_m = df_universo_param.copy()

    df_full["Cliente"] = pd.to_numeric(df_full["Cliente"], errors="coerce").astype(
        "Int64"
    )

    t_s2 = time.perf_counter()
    if not df_full.empty and not univ_m.empty:
        subramo_u = next(
            (c for c in univ_m.columns if "subramo" in str(c).lower()), None
        )
        if subramo_u:
            univ_m = univ_m[
                ~univ_m[subramo_u]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                .isin(["EMPLOYEES", "EMPLEADOS"])
            ].copy()

        col_cu = next(
            (
                c
                for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"]
                if c in univ_m.columns
            ),
            univ_m.columns[0],
        )
        univ_m["Cliente"] = pd.to_numeric(univ_m[col_cu], errors="coerce").astype(
            "Int64"
        )

        col_tax_univ = next(
            (
                c
                for c in univ_m.columns
                if str(c).strip().lower().replace("_", "") == "segmentoclientecodigo"
                or any(
                    k in str(c).lower() for k in ["taxonomia", "clasificacion", "tax"]
                )
            ),
            None,
        )
        if col_tax_univ:
            univ_m["Taxonomia"] = (
                univ_m[col_tax_univ].fillna("").astype(str).str.strip().str.upper()
            )
        else:
            univ_m["Taxonomia"] = "SIN TAXONOMIA"

        univ_m["Taxonomia"] = univ_m["Taxonomia"].replace(
            ["", "NAN", "NONE", "NAT"], "SIN TAXONOMIA"
        )

        col_nom_c = next(
            (
                c
                for c in [
                    "Razon_Social",
                    "RazonSocial",
                    "NombreCliente",
                    "Nombre_Cliente",
                    "ClienteDesc",
                ]
                if c in univ_m.columns
            ),
            col_cu,
        )
        univ_m["NombreCliente"] = (
            univ_m[col_nom_c].fillna("").astype(str)
            if col_nom_c in univ_m.columns
            else ""
        )

        univ_m_subset = (
            univ_m[["Cliente", "Taxonomia", "NombreCliente"]]
            .drop_duplicates(subset=["Cliente"])
            .copy()
        )
        df_full = df_full.merge(univ_m_subset, on="Cliente", how="left")
    else:
        df_full["Taxonomia"] = "SIN TAXONOMIA"
        df_full["NombreCliente"] = "CLIENTE SIN PADS"
    print(
        f"[PERF_INTERNAL] merge_universo_completo = {time.perf_counter() - t_s2:.2f} s"
    )

    if "Taxonomia" not in df_full.columns:
        df_full["Taxonomia"] = "SIN TAXONOMIA"

    mask_sin_tax = (
        df_full["Taxonomia"]
        .astype(str)
        .str.strip()
        .str.upper()
        .isin(["SIN TAXONOMIA", "", "NAN", "NONE"])
    )
    if mask_sin_tax.any():
        clientes_faltantes = (
            df_full.loc[mask_sin_tax, "Cliente"].dropna().unique().tolist()
        )
        if clientes_faltantes:
            try:
                t_s3 = time.perf_counter()
                conn_rescate = sqlite3.connect("data/matinal.db")
                placeholders = ",".join(["?"] * len(clientes_faltantes))
                query_rescate = f"SELECT Codigo AS Cliente, SegmentoClienteCodigo AS Taxonomia, Razon_Social AS NombreCliente FROM universo WHERE Codigo IN ({placeholders})"
                df_rescatados = pd.read_sql(
                    query_rescate, conn_rescate, params=clientes_faltantes
                )
                conn_rescate.close()
                print(
                    f"[PERF_INTERNAL] consulta_sqlite_rescate_clientes = {time.perf_counter() - t_s3:.2f} s"
                )

                if not df_rescatados.empty:
                    df_rescatados["Cliente"] = pd.to_numeric(
                        df_rescatados["Cliente"], errors="coerce"
                    ).astype("Int64")
                    df_rescatados["Taxonomia"] = (
                        df_rescatados["Taxonomia"]
                        .fillna("SIN TAXONOMIA")
                        .astype(str)
                        .str.strip()
                        .str.upper()
                    )
                    mapa_tax_rescate = df_rescatados.set_index("Cliente")[
                        "Taxonomia"
                    ].to_dict()
                    mapa_nom_rescate = df_rescatados.set_index("Cliente")[
                        "NombreCliente"
                    ].to_dict()

                    df_full.loc[mask_sin_tax, "Taxonomia"] = (
                        df_full.loc[mask_sin_tax, "Cliente"]
                        .map(mapa_tax_rescate)
                        .fillna(df_full.loc[mask_sin_tax, "Taxonomia"])
                    )
                    df_full.loc[mask_sin_tax, "NombreCliente"] = (
                        df_full.loc[mask_sin_tax, "Cliente"]
                        .map(mapa_nom_rescate)
                        .fillna(df_full.loc[mask_sin_tax, "NombreCliente"])
                    )
            except Exception:
                pass

    df_full["Taxonomia"] = (
        df_full["Taxonomia"]
        .fillna("SIN TAXONOMIA")
        .replace(["", "NAN", "NONE"], "SIN TAXONOMIA")
    )
    df_full["NombreCliente"] = df_full["NombreCliente"].fillna("CLIENTE SIN NOMBRE")

    df_hoy = (
        df_full[df_full["FechaCarga_dt"].dt.date == target_date].copy()
        if target_date
        else df_full.copy()
    )

    t_s4 = time.perf_counter()
    try:
        df_ausencias = db.cargar_tabla_sql("SELECT * FROM ausencias")
    except Exception:
        df_ausencias = pd.DataFrame()

    df_vta_hist = preparar_ventas_ccc(
        df_vta, df_ausencias, anio_op, mes_op, dia_matinal
    )
    print(
        f"[PERF_INTERNAL] preparar_ventas_ccc_historico = {time.perf_counter() - t_s4:.2f} s"
    )

    t_s5 = time.perf_counter()
    if not df_vta_hist.empty and target_date:
        df_vta_previo = df_vta_hist[
            (df_vta_hist["Periodo"].isin(["Arrastre", "Actual"]))
            & (df_vta_hist["FechaCarga_dt"].dt.date < target_date)
        ].copy()

        col_c_h = next(
            (
                c
                for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
                if c in df_vta_previo.columns
            ),
            "Cliente",
        )
        df_vta_previo["_Cli"] = pd.to_numeric(
            df_vta_previo[col_c_h], errors="coerce"
        ).astype("Int64")

        col_pesos_h = next(
            (
                c
                for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"]
                if c in df_vta_previo.columns
            ),
            "ImporteNeto",
        )
        col_cant_h = next(
            (
                c
                for c in ["CantBase", "CANTBASE", "Cantidad", "Unidades"]
                if c in df_vta_previo.columns
            ),
            "CantBase",
        )
        col_orig_h = next(
            (
                c
                for c in df_vta_previo.columns
                if any(k in str(c).lower() for k in ["origen", "canal"])
            ),
            None,
        )

        df_vta_previo["_ImpH"] = pd.to_numeric(
            df_vta_previo[col_pesos_h], errors="coerce"
        ).fillna(0.0)
        df_vta_previo["_CantH"] = pd.to_numeric(
            df_vta_previo[col_cant_h], errors="coerce"
        ).fillna(0.0)
        df_vta_previo["_IsMNH"] = (
            df_vta_previo[col_orig_h]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.contains("minegocio|mi negocio", case=False, na=False)
            if col_orig_h
            else False
        )
        df_vta_previo["_MNHVal"] = np.where(
            df_vta_previo["_IsMNH"], df_vta_previo["_ImpH"], 0.0
        )

        agg_hist = df_vta_previo.groupby("_Cli", as_index=False).agg(
            CantBase_hist=("_CantH", "sum"),
            ImporteItem_hist=("_ImpH", "sum"),
            VentaTotal_hist=("_ImpH", "sum"),
            VentaMN_hist=("_MNHVal", "sum"),
        )
        agg_hist["Era_NC_hist"] = ~(
            (agg_hist["CantBase_hist"] >= 3) & (agg_hist["ImporteItem_hist"] >= 1)
        )
        agg_hist["Ratio_FD_hist"] = np.where(
            agg_hist["VentaTotal_hist"] != 0,
            agg_hist["VentaMN_hist"] / agg_hist["VentaTotal_hist"],
            0.0,
        )
        agg_hist = agg_hist.rename(columns={"_Cli": "Cliente"})
    else:
        agg_hist = pd.DataFrame(columns=["Cliente", "Era_NC_hist", "Ratio_FD_hist"])

    if not df_vta_hist.empty:
        df_vta_mes_tot = df_vta_hist[
            df_vta_hist["Periodo"].isin(["Arrastre", "Actual"])
        ].copy()
        col_c_tot = next(
            (
                c
                for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
                if c in df_vta_mes_tot.columns
            ),
            "Cliente",
        )
        df_vta_mes_tot["_CliTot"] = pd.to_numeric(
            df_vta_mes_tot[col_c_tot], errors="coerce"
        ).astype("Int64")

        col_pesos_tot = next(
            (
                c
                for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"]
                if c in df_vta_mes_tot.columns
            ),
            "ImporteNeto",
        )
        col_cant_tot = next(
            (
                c
                for c in ["CantBase", "CANTBASE", "Cantidad", "Unidades"]
                if c in df_vta_mes_tot.columns
            ),
            "CantBase",
        )
        col_orig_tot = next(
            (
                c
                for c in df_vta_mes_tot.columns
                if any(k in str(c).lower() for k in ["origen", "canal"])
            ),
            None,
        )

        df_vta_mes_tot["_ImpTot"] = pd.to_numeric(
            df_vta_mes_tot[col_pesos_tot], errors="coerce"
        ).fillna(0.0)
        df_vta_mes_tot["_CantTot"] = pd.to_numeric(
            df_vta_mes_tot[col_cant_tot], errors="coerce"
        ).fillna(0.0)
        df_vta_mes_tot["_IsMNTot"] = (
            df_vta_mes_tot[col_orig_tot]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.contains("minegocio|mi negocio", case=False, na=False)
            if col_orig_tot
            else False
        )
        df_vta_mes_tot["_MNTotVal"] = np.where(
            df_vta_mes_tot["_IsMNTot"], df_vta_mes_tot["_ImpTot"], 0.0
        )

        agg_tot = df_vta_mes_tot.groupby("_CliTot", as_index=False).agg(
            CantBase_tot=("_CantTot", "sum"),
            ImporteItem_tot=("_ImpTot", "sum"),
            VentaTotal_tot=("_ImpTot", "sum"),
            VentaMN_tot=("_MNTotVal", "sum"),
        )
        agg_tot["Cumple_CCC_tot"] = (agg_tot["CantBase_tot"] >= 3) & (
            agg_tot["ImporteItem_tot"] >= 1
        )
        agg_tot["Ratio_FD_tot"] = np.where(
            agg_tot["VentaTotal_tot"] != 0,
            agg_tot["VentaMN_tot"] / agg_tot["VentaTotal_tot"],
            0.0,
        )
        agg_tot = agg_tot.rename(columns={"_CliTot": "Cliente"})
    else:
        agg_tot = pd.DataFrame(columns=["Cliente", "Cumple_CCC_tot", "Ratio_FD_tot"])

    df_neto_hoy = df_hoy.groupby("Cliente", as_index=False).agg(
        ImporteNeto_Dia=("ImporteNeto", "sum"), CantBase_Dia=("CantBase", "sum")
    )
    clientes_compra_real = set(
        df_neto_hoy[
            (df_neto_hoy["ImporteNeto_Dia"] >= 1) & (df_neto_hoy["CantBase_Dia"] >= 3)
        ]["Cliente"]
        .dropna()
        .tolist()
    )

    clientes_hoy = df_hoy[["Cliente"]].drop_duplicates().copy()
    clientes_hoy = clientes_hoy.merge(
        agg_hist[["Cliente", "Era_NC_hist", "Ratio_FD_hist"]], on="Cliente", how="left"
    )
    clientes_hoy = clientes_hoy.merge(
        agg_tot[["Cliente", "Cumple_CCC_tot", "Ratio_FD_tot"]], on="Cliente", how="left"
    )

    clientes_hoy["Era_NC_hist"] = clientes_hoy["Era_NC_hist"].fillna(True)
    clientes_hoy["Cumple_CCC_tot"] = clientes_hoy["Cumple_CCC_tot"].fillna(False)
    clientes_hoy["Ratio_FD_hist"] = clientes_hoy["Ratio_FD_hist"].fillna(0.0)
    clientes_hoy["Ratio_FD_tot"] = clientes_hoy["Ratio_FD_tot"].fillna(0.0)

    clientes_hoy["Estado_Hist"] = clientes_hoy["Ratio_FD_hist"].apply(
        clasificar_estado_fd
    )
    clientes_hoy["Estado_Tot"] = clientes_hoy["Ratio_FD_tot"].apply(
        clasificar_estado_fd
    )

    clientes_hoy["Es_Compra_Real_Dia"] = clientes_hoy["Cliente"].isin(
        clientes_compra_real
    )
    clientes_hoy["Es_Activado_Dia"] = (
        clientes_hoy["Es_Compra_Real_Dia"]
        & clientes_hoy["Era_NC_hist"]
        & clientes_hoy["Cumple_CCC_tot"]
    )

    clientes_hoy["Es_Conversion_FullyDigital"] = (
        clientes_hoy["Es_Compra_Real_Dia"]
        & clientes_hoy["Estado_Hist"].isin(["No Digital", "Híbrido"])
        & (clientes_hoy["Estado_Tot"] == "Fully Digital")
    )

    mapa_ccc = clientes_hoy.set_index("Cliente")["Es_Activado_Dia"].to_dict()
    mapa_fd = clientes_hoy.set_index("Cliente")["Es_Conversion_FullyDigital"].to_dict()
    mapa_compra = clientes_hoy.set_index("Cliente")["Es_Compra_Real_Dia"].to_dict()

    df_hoy["Es_Activado_Dia"] = df_hoy["Cliente"].map(mapa_ccc).fillna(False)
    df_hoy["Es_Conversion_FullyDigital"] = df_hoy["Cliente"].map(mapa_fd).fillna(False)
    df_hoy["Es_Compra_Real_Dia"] = df_hoy["Cliente"].map(mapa_compra).fillna(False)
    print(
        f"[PERF_INTERNAL] groupby_agregaciones_y_mapeos_ccc = {time.perf_counter() - t_s5:.2f} s"
    )

    print(
        f"[PERF_INTERNAL] generar_reporte_vespertina_resumen = {time.perf_counter() - t_start:.2f} s"
    )
    return df_hoy


@st.fragment
def render_fragmento_vespertina_resumen(df_filtrado):
    t_start = time.perf_counter()
    if df_filtrado is None or df_filtrado.empty:
        st.info("No se registraron operaciones para el Día Venta seleccionado.")
        return

    sup_dispo = sorted(
        df_filtrado["SUP"].dropna().astype(str).str.strip().unique().tolist()
    )
    sup_selec = st.multiselect(
        "Supervisor",
        options=sup_dispo,
        default=[],
        placeholder="Seleccionar supervisores...",
        key="frag_vesp_res_supervisor",
    )

    if sup_selec:
        df_filtrado = df_filtrado[
            df_filtrado["SUP"].astype(str).str.strip().isin(sup_selec)
        ].copy()

    if df_filtrado.empty:
        st.info("No se encontraron registros para los supervisores seleccionados.")
        return

    tot_kilos = float(df_filtrado["PesoKg"].sum())
    tot_importe = float(df_filtrado["ImporteNeto"].sum())

    df_compradores_validos = df_filtrado[
        df_filtrado["Es_Compra_Real_Dia"]
    ].drop_duplicates(subset=["Cliente"])
    tot_clientes_compra = int(df_compradores_validos["Cliente"].nunique())

    df_cli_activados_global = (
        df_filtrado[df_filtrado["Es_Activado_Dia"]].drop_duplicates(subset=["Cliente"])
        if "Es_Activado_Dia" in df_filtrado.columns
        else pd.DataFrame()
    )
    tot_ccc_dia = (
        int(df_cli_activados_global["Cliente"].nunique())
        if not df_cli_activados_global.empty
        else 0
    )

    df_conversion_global = df_filtrado[
        df_filtrado["Es_Conversion_FullyDigital"]
    ].drop_duplicates(subset=["Cliente"])
    tot_conversion_fd = int(df_conversion_global["Cliente"].nunique())

    tot_mn = float(df_filtrado[df_filtrado["Es_MiNegocio"]]["ImporteNeto"].sum())
    pct_mn = (tot_mn / tot_importe * 100.0) if tot_importe > 0 else 0.0

    st.markdown(
        """
        <style>
        hr {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            border-color: #334155 !important;
        }
        dataframe, table, [data-testid="stDataFrame"] div[data-testid="stTable"] {
            width: 100% !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("### 📦 1. Kilos e Importe por Segmento")
    cols_m1 = st.columns(2)
    with cols_m1[0]:
        st.markdown(
            tarjeta_metrica_html(
                "KILOS DÍA VENTA",
                f"{tot_kilos:,.2f} kg",
                "#10b981",
                "1.2rem",
                "0.65rem",
            ),
            unsafe_allow_html=True,
        )
    with cols_m1[1]:
        st.markdown(
            tarjeta_metrica_html(
                "IMPORTE NETO DÍA",
                f"${tot_importe:,.2f}",
                "#8b5cf6",
                "1.2rem",
                "0.65rem",
            ),
            unsafe_allow_html=True,
        )

    df_seg_view = df_filtrado.groupby("SEGMENTO", as_index=False).agg(
        Kilos=("PesoKg", "sum"), Importe_Neto=("ImporteNeto", "sum")
    )
    df_seg_disp = df_seg_view.copy()
    df_seg_disp["Kilos"] = df_seg_disp["Kilos"].apply(lambda x: f"{x:,.2f} kg")
    df_seg_disp["Importe_Neto"] = df_seg_disp["Importe_Neto"].apply(
        lambda x: f"${x:,.2f}"
    )
    df_seg_disp = df_seg_disp.rename(
        columns={
            "SEGMENTO": "Segmento",
            "Kilos": "Kilos (kg)",
            "Importe_Neto": "Importe Neto ($)",
        }
    )
    st.dataframe(df_seg_disp, width="stretch", hide_index=True)

    st.divider()

    st.markdown("### 📈 2. CCC (Clientes Compradores y Activados por Taxonomía)")
    cols_m2 = st.columns(2)
    with cols_m2[0]:
        st.markdown(
            tarjeta_metrica_html(
                "CCC DÍA VENTA (ACTIVADOS)",
                f"{tot_ccc_dia:,.0f}",
                "#3b82f6",
                "1.2rem",
                "0.65rem",
            ),
            unsafe_allow_html=True,
        )
    with cols_m2[1]:
        st.markdown(
            tarjeta_metrica_html(
                "CLIENTES CON COMPRA",
                f"{tot_clientes_compra:,.0f}",
                "#06b6d4",
                "1.2rem",
                "0.65rem",
            ),
            unsafe_allow_html=True,
        )

    df_ccc_tax = df_filtrado.groupby("Taxonomia", as_index=False).agg(
        Clientes_Compra=(
            "Cliente",
            lambda x: df_filtrado.loc[x.index][
                df_filtrado.loc[x.index, "Es_Compra_Real_Dia"]
            ]["Cliente"].nunique(),
        ),
        Clientes_Activados=(
            "Cliente",
            lambda x: df_filtrado.loc[x.index][
                df_filtrado.loc[x.index, "Es_Activado_Dia"]
            ]["Cliente"].nunique(),
        )
        if "Es_Activado_Dia" in df_filtrado.columns
        else ("Cliente", lambda x: 0),
    )
    df_ccc_tax = df_ccc_tax.rename(
        columns={
            "Taxonomia": "Taxonomía",
            "Clientes_Compra": "Clientes Compradores",
            "Clientes_Activados": "Clientes Activados (CCC)",
        }
    )
    st.dataframe(df_ccc_tax, width="stretch", hide_index=True)

    st.divider()

    st.markdown("### 📱 3. Adopción MiNegocio y Conversiones Fully Digital")
    cols_m3 = st.columns(3)
    with cols_m3[0]:
        st.markdown(
            tarjeta_metrica_html(
                "VENTAS TOTALES", f"${tot_importe:,.2f}", "#8b5cf6", "1.2rem", "0.65rem"
            ),
            unsafe_allow_html=True,
        )
    with cols_m3[1]:
        st.markdown(
            tarjeta_metrica_html(
                "VENTAS MI NEGOCIO", f"${tot_mn:,.2f}", "#06b6d4", "1.2rem", "0.65rem"
            ),
            unsafe_allow_html=True,
        )
    with cols_m3[2]:
        st.markdown(
            tarjeta_metrica_html(
                "CONVERSIONES FD",
                f"{tot_conversion_fd:,.0f}",
                "#10b981",
                "1.2rem",
                "0.65rem",
            ),
            unsafe_allow_html=True,
        )

    df_mn_tax = df_filtrado.groupby("Taxonomia", as_index=False).agg(
        Ventas_Totales=("ImporteNeto", "sum"), Ventas_MN=("_mn_val", "sum")
    )
    df_mn_tax["% Adopción App"] = (
        (df_mn_tax["Ventas_MN"] / df_mn_tax["Ventas_Totales"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    df_mn_disp = df_mn_tax.copy()
    df_mn_disp["Ventas_Totales"] = df_mn_disp["Ventas_Totales"].apply(
        lambda x: f"${x:,.2f}"
    )
    df_mn_disp["Ventas_MN"] = df_mn_disp["Ventas_MN"].apply(lambda x: f"${x:,.2f}")
    df_mn_disp["% Adopción App"] = df_mn_disp["% Adopción App"].apply(
        lambda x: f"{x:,.2f}%"
    )
    df_mn_disp = df_mn_disp.rename(
        columns={
            "Taxonomia": "Taxonomía",
            "Ventas_Totales": "Ventas Totales ($)",
            "Ventas_MN": "Ventas MiNegocio ($)",
        }
    )
    st.dataframe(df_mn_disp, width="stretch", hide_index=True)

    st.divider()

    st.markdown("### 🔍 Auditoría: Detalle de Clientes Activados en el Día Venta")
    df_activados_audit = (
        df_filtrado[df_filtrado["Es_Activado_Dia"]]
        .groupby("Cliente", as_index=False)
        .agg(
            NombreCliente=("NombreCliente", "first"),
            SUP=("SUP", "first"),
            Taxonomia=("Taxonomia", "first"),
            PesoKg=("PesoKg", "sum"),
            ImporteNeto=("ImporteNeto", "sum"),
        )
        if "Es_Activado_Dia" in df_filtrado.columns
        else pd.DataFrame(
            columns=[
                "Cliente",
                "NombreCliente",
                "SUP",
                "Taxonomia",
                "PesoKg",
                "ImporteNeto",
            ]
        )
    )

    if not df_activados_audit.empty:
        df_act_view = df_activados_audit[
            ["Cliente", "NombreCliente", "SUP", "Taxonomia", "PesoKg", "ImporteNeto"]
        ].copy()

        df_act_view = df_act_view.rename(
            columns={
                "Cliente": "Cód. Cliente",
                "NombreCliente": "Razón Social",
                "SUP": "Supervisor",
                "Taxonomia": "Taxonomía",
                "PesoKg": "Kilos Día (kg)",
                "ImporteNeto": "Importe Día ($)",
            }
        )
        df_act_view["Kilos Día (kg)"] = df_act_view["Kilos Día (kg)"].apply(
            lambda x: f"{x:,.2f} kg"
        )
        df_act_view["Importe Día ($)"] = df_act_view["Importe Día ($)"].apply(
            lambda x: f"${x:,.2f}"
        )

        st.dataframe(df_act_view, width="stretch", hide_index=True)
    else:
        st.info("No se registraron clientes activados para los filtros seleccionados.")

    st.divider()

    st.markdown("### 📱 Auditoría: Clientes Convertidos a FullyDigital en el Día Venta")
    df_conversion_audit = (
        df_filtrado[df_filtrado["Es_Conversion_FullyDigital"]]
        .groupby("Cliente", as_index=False)
        .agg(
            NombreCliente=("NombreCliente", "first"),
            SUP=("SUP", "first"),
            Taxonomia=("Taxonomia", "first"),
            PesoKg=("PesoKg", "sum"),
            ImporteNeto=("ImporteNeto", "sum"),
        )
    )

    if not df_conversion_audit.empty:
        df_conv_view = df_conversion_audit[
            ["Cliente", "NombreCliente", "SUP", "Taxonomia", "PesoKg", "ImporteNeto"]
        ].copy()

        df_conv_view = df_conv_view.rename(
            columns={
                "Cliente": "Cód. Cliente",
                "NombreCliente": "Razón Social",
                "SUP": "Supervisor",
                "Taxonomia": "Taxonomía",
                "PesoKg": "Kilos Día (kg)",
                "ImporteNeto": "Importe Día ($)",
            }
        )
        df_conv_view["Kilos Día (kg)"] = df_conv_view["Kilos Día (kg)"].apply(
            lambda x: f"{x:,.2f} kg"
        )
        df_conv_view["Importe Día ($)"] = df_conv_view["Importe Día ($)"].apply(
            lambda x: f"${x:,.2f}"
        )

        st.dataframe(df_conv_view, width="stretch", hide_index=True)
    else:
        st.info(
            "No se registraron conversiones a FullyDigital para los filtros seleccionados."
        )

    st.divider()

    buffer_vesp = io.BytesIO()
    with pd.ExcelWriter(buffer_vesp, engine="openpyxl") as writer:
        df_seg_view.to_excel(writer, index=False, sheet_name="Kilos_Por_Segmento")
        if not df_ccc_tax.empty:
            df_ccc_tax.to_excel(writer, index=False, sheet_name="CCC_Por_Taxonomia")
        df_mn_tax.to_excel(writer, index=False, sheet_name="Adopcion_MiNegocio")
        if not df_activados_audit.empty:
            df_act_view.to_excel(
                writer, index=False, sheet_name="Clientes_Activados_Auditoria"
            )
        if not df_conversion_audit.empty:
            df_conv_view.to_excel(
                writer, index=False, sheet_name="Conversion_FullyDigital"
            )
    buffer_vesp.seek(0)

    st.download_button(
        label="📥 Descargar Reporte Vespertina a Excel",
        data=buffer_vesp,
        file_name="Reporte_Vespertina_Resumen.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="vesp_resumen_btn_dl",
    )
    print(
        f"[PERF_INTERNAL] render_fragmento_vespertina_resumen = {time.perf_counter() - t_start:.2f} s"
    )


def render_rep_vespertina(df_vta, df_universo, filtros_globales=None):
    """
    Módulo analítico de Reporte Vespertina.
    Instrumentado con telemetría interna [PERF_INTERNAL].
    """
    t_start = time.perf_counter()
    st.subheader("🌙 Reporte Vespertina - Resumen Ejecutivo del Día Venta")
    st.markdown(
        "Consolidado operativo riguroso con motor de estados (No Digital, Híbrido, Fully Digital) y activaciones CCC basados en Arrastre + Actual."
    )

    try:
        t_s1 = time.perf_counter()
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        print(
            f"[PERF_INTERNAL] consulta_sqlite_maestro_vendedores = {time.perf_counter() - t_s1:.2f} s"
        )
    except Exception:
        maestro_v = pd.DataFrame()

    df_filtrado = generar_reporte_vespertina_resumen(
        df_vta, df_universo, maestro_v, filtros_globales
    )
    render_fragmento_vespertina_resumen(df_filtrado)
    print(
        f"[PERF_INTERNAL] render_rep_vespertina = {time.perf_counter() - t_start:.2f} s"
    )


====================================================================================================


### ARCHIVO: modules\staging.py

# modules/staging.py
import time
import streamlit as st
import pandas as pd
import numpy as np
from modules import database as db
from modules.utils import parsear_fecha_robusta


@st.cache_data(show_spinner=False)
def obtener_staging_vta():
    """
    Capa Staging (Técnica Pura Definitiva): Ingesta exclusiva desde la tabla RAW 'vta'.
    Aplica únicamente tipado estricto, parseo de fechas y normalización de marcas.
    Cero reglas de negocio, cero exclusiones y cero filtros de registros.
    """
    t0 = time.perf_counter()
    try:
        df_raw = db.cargar_tabla_sql("SELECT * FROM vta")
    except Exception:
        df_raw = pd.DataFrame()

    if df_raw.empty:
        print(
            f"[PERF_CORE] 1) obtener_staging_vta (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    df = df_raw.copy()

    # Normalización tipográfica estricta
    df["PesoKg"] = pd.to_numeric(df.get("PesoKg", 0), errors="coerce").fillna(0.0)

    col_pesos = next(
        (
            c
            for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"]
            if c in df.columns
        ),
        None,
    )
    df["ImporteNetoItem"] = (
        pd.to_numeric(df[col_pesos], errors="coerce").fillna(0.0) if col_pesos else 0.0
    )

    col_cant = next(
        (
            c
            for c in [
                "CantBase",
                "CANTBASE",
                "Cantidad",
                "CANTIDAD",
                "Unidades",
                "UNIDADES",
            ]
            if c in df.columns
        ),
        df.columns[0],
    )
    df["CantBase"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0.0)

    # Parseo de fechas robusto unificado
    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    # Tipado de identificadores relacionales
    col_vend_tit = next(
        (
            cand
            for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
            if cand in df.columns
        ),
        "CodVendedor",
    )
    df["CodVendedor"] = pd.to_numeric(df.get(col_vend_tit, 0), errors="coerce").astype(
        "Int64"
    )

    col_cli_tit = next(
        (
            cand
            for cand in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
            if cand in df.columns
        ),
        "Cliente",
    )
    df["Cliente"] = pd.to_numeric(df.get(col_cli_tit, 0), errors="coerce").astype(
        "Int64"
    )

    # Normalización sintáctica de marca
    col_m = next((c for c in ["Marca", "MARCA", "marca"] if c in df.columns), None)
    df["Marca"] = (
        df[col_m].fillna("").astype(str).str.strip().str.upper()
        if col_m
        else "SIN MARCA"
    )

    print(f"[PERF_CORE] 1) obtener_staging_vta -> {time.perf_counter() - t0:.4f} s")
    return df


@st.cache_data(show_spinner=False)
def obtener_staging_clientes():
    """
    Capa Staging (Técnica Pura Definitiva): Ingesta exclusiva desde la tabla RAW 'universo'.
    Normaliza taxonomías, claves y razones sociales sin excluir empleados ni asignar supervisores de negocio.
    """
    try:
        univ = db.cargar_tabla_sql("SELECT * FROM universo")
    except Exception:
        univ = pd.DataFrame()

    if univ.empty:
        return pd.DataFrame()

    df = univ.copy()

    col_cu = next(
        (
            c
            for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"]
            if c in df.columns
        ),
        df.columns[0],
    )
    df["Cliente"] = pd.to_numeric(df[col_cu], errors="coerce").astype("Int64")

    col_tax_univ = next(
        (
            c
            for c in df.columns
            if str(c).strip().lower().replace("_", "") == "segmentoclientecodigo"
            or any(k in str(c).lower() for k in ["taxonomia", "clasificacion", "tax"])
        ),
        None,
    )
    if col_tax_univ:
        df["Taxonomia"] = (
            df[col_tax_univ].fillna("").astype(str).str.strip().str.upper()
        )
    else:
        df["Taxonomia"] = "SIN TAXONOMIA"

    df["Taxonomia"] = df["Taxonomia"].replace(
        ["", "NAN", "NONE", "NAT"], "SIN TAXONOMIA"
    )

    col_nom_c = next(
        (
            c
            for c in [
                "Razon_Social",
                "RazonSocial",
                "NombreCliente",
                "Nombre_Cliente",
                "ClienteDesc",
            ]
            if c in df.columns
        ),
        col_cu,
    )
    df["NombreCliente"] = (
        df[col_nom_c].fillna("").astype(str) if col_nom_c in df.columns else ""
    )

    pos_v_u = next(
        (
            c
            for c in df.columns
            if any(k in str(c).lower() for k in ["codven", "vendedor"])
        ),
        None,
    )
    if pos_v_u:
        df["CodVendedor"] = pd.to_numeric(df[pos_v_u], errors="coerce").astype("Int64")

    return df


@st.cache_data(show_spinner=False)
def obtener_staging_rutas():
    """
    Capa Staging (Técnica Pura): Carga la tabla cruda de rutas.
    """
    t0 = time.perf_counter()
    try:
        rutas = db.cargar_tabla_sql("SELECT * FROM rutas")
    except Exception:
        rutas = pd.DataFrame()
    print(f"[PERF_CORE] 2) obtener_staging_rutas -> {time.perf_counter() - t0:.4f} s")
    return rutas


@st.cache_data(show_spinner=False)
def obtener_staging_ausencias():
    """
    Capa Staging (Técnica Pura): Ingesta exclusiva desde la tabla RAW 'ausencias'.
    Aplica tipado estricto, detección robusta de columnas candidatas, parseo de fechas y normalización.
    """
    t0 = time.perf_counter()
    try:
        df_raw = db.cargar_tabla_sql("SELECT * FROM ausencias")
    except Exception:
        df_raw = pd.DataFrame()

    if df_raw.empty:
        print(
            f"[PERF_CORE] obtener_staging_ausencias (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    df = df_raw.copy()

    cols_vend_cand = [
        "Ausente",
        "CodVend",
        "CodVendedor",
        "Vendedor",
        "Cod_Vendedor",
    ]
    col_aus_vend = next((c for c in cols_vend_cand if c in df.columns), None)
    if not col_aus_vend:
        raise ValueError("No se encontró columna de vendedor en la tabla de ausencias.")

    cols_f_cand = ["Fecha", "FechaAusencia", "Dia"]
    col_aus_fecha = next((c for c in cols_f_cand if c in df.columns), None)
    if not col_aus_fecha:
        raise ValueError("No se encontró columna de fecha en la tabla de ausencias.")

    cols_reemp_cand = [
        "Reemplazo",
        "CodReemplazo",
        "Cod_Reemplazo",
        "PreventistaReemplazo",
    ]
    col_aus_reemp = next((c for c in cols_reemp_cand if c in df.columns), None)
    if not col_aus_reemp:
        raise ValueError(
            "No se encontró columna de reemplazo en la tabla de ausencias."
        )

    df["Fecha_dt"] = parsear_fecha_robusta(df[col_aus_fecha])
    df["CodVend_clean"] = pd.to_numeric(df[col_aus_vend], errors="coerce").astype(
        "Int64"
    )
    df["Reemplazo_clean"] = pd.to_numeric(df[col_aus_reemp], errors="coerce").astype(
        "Int64"
    )

    print(f"[PERF_CORE] obtener_staging_ausencias -> {time.perf_counter() - t0:.4f} s")
    return df


@st.cache_data(show_spinner=False)
def obtener_staging_maestros():
    """
    Capa Staging (Técnica Pura): Carga y centraliza los maestros base del sistema.
    """
    t0 = time.perf_counter()
    maestros = {}
    for tabla in [
        "maestro_vendedores",
        "maestro_ccc",
        "maestro_marcas_cebe",
        "ausencias",
        "maestro_segmentos",
    ]:
        try:
            maestros[tabla] = db.cargar_tabla_sql(f"SELECT * FROM {tabla}")
        except Exception:
            maestros[tabla] = pd.DataFrame()
    print(
        f"[PERF_CORE] 3) obtener_staging_maestros -> {time.perf_counter() - t0:.4f} s"
    )
    return maestros


====================================================================================================


### ARCHIVO: modules\utils.py

# modules/utils.py
import pandas as pd
import unicodedata

def parsear_fecha_robusta(serie):
    """Estandariza parseo de fechas considerando formatos ISO y DD/MM/YYYY sin advertencias en consola."""
    if serie is None or (isinstance(serie, pd.Series) and serie.empty):
        return pd.Series(dtype="datetime64[ns]")
    if not isinstance(serie, pd.Series):
        serie = pd.Series([serie])
    s = serie.astype(str).str.strip().str.replace(" 00:00:00", "", regex=False)
    
    dt_iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    dt_lat = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce", dayfirst=True)
    
    return dt_iso.combine_first(dt_lat)

def extraer_dia_de_ruta(val):
    """Extrae y normaliza el día de visita a partir del texto de la ruta."""
    if pd.isna(val):
        return "SIN DÍA"
    nfkd = unicodedata.normalize('NFKD', str(val))
    val_clean = "".join([c for c in nfkd if not unicodedata.combining(c)]).upper()
    
    if "LUN" in val_clean: return "LUNES"
    if "MAR" in val_clean: return "MARTES"
    if "MIE" in val_clean: return "MIERCOLES"
    if "JUE" in val_clean: return "JUEVES"
    if "VIE" in val_clean: return "VIERNES"
    if "SAB" in val_clean: return "SABADO"
    if "DOM" in val_clean: return "DOMINGO"
    return "SIN DÍA"

def extraer_dia_de_ruta_vectorial(serie):
    """Normalización y extracción vectorial rápida de días de visita sin bucles en Python."""
    if serie is None or (isinstance(serie, pd.Series) and serie.empty):
        return pd.Series(dtype="object")
    s_upper = serie.astype(str).str.upper()
    dias_map = pd.Series("SIN DÍA", index=serie.index)
    dias_map[s_upper.str.contains("LUN", na=False)] = "LUNES"
    dias_map[s_upper.str.contains("MAR", na=False)] = "MARTES"
    dias_map[s_upper.str.contains("MIE", na=False)] = "MIERCOLES"
    dias_map[s_upper.str.contains("JUE", na=False)] = "JUEVES"
    dias_map[s_upper.str.contains("VIE", na=False)] = "VIERNES"
    dias_map[s_upper.str.contains("SAB", na=False)] = "SABADO"
    dias_map[s_upper.str.contains("DOM", na=False)] = "DOMINGO"
    return dias_map

def tarjeta_metrica_html(label, valor, border_color="#475569", font_val="1.4rem", font_lbl="0.75rem", color_valor="#f8fafc"):
    """Genera contenedores HTML unificados para tarjetas de métricas con soporte de color dinámico para el valor."""
    return f"""
    <div style="
        background-color: #1e293b;
        border: 2px solid {border_color};
        border-radius: 8px;
        padding: 10px 14px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 8px;
    ">
        <div style="font-size: {font_lbl}; color: #94a3b8; font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">{label}</div>
        <div style="font-size: {font_val}; color: {color_valor}; font-weight: 700;">{valor}</div>
    </div>
    """

====================================================================================================

