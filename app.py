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
from modules.rep_obj_kilos_core import render_rep_obj_kilos_core
from modules.rep_ccc import render_rep_ccc
from modules.rep_ccc_core import render_rep_ccc_core
from modules.rep_MN import render_rep_mn
from modules.rep_MN_core import render_rep_mn_core
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
from modules.rep_tp_core import render_rep_tp_core
from modules import database as db
from modules.core.core_validacion_periodo import validar_integridad_periodo_operativo
from modules.feature_flags import ff  # FEATURE_FLAG

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

    if "_cache_limpiado_inicio" not in st.session_state:
        st.cache_data.clear()
        st.cache_resource.clear()
        st.session_state["_cache_limpiado_inicio"] = True

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
            st.cache_data.clear()
            st.cache_resource.clear()
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
                "ℹ Sube los tres archivos requeridos (VTA, Universo y Rutas) para habilitar el sistema."
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

    # Integración de la validación de integridad del período operativo
    estado_periodo = validar_integridad_periodo_operativo(
        filtros_globales["anio"], filtros_globales["mes"]
    )

    # Renderizado del semáforo visual en el sidebar usando st.sidebar.success o st.sidebar.error
    st.sidebar.markdown("---")
    if estado_periodo["completo"]:
        st.sidebar.success(
            f"✅ Período {estado_periodo['mes']}/{estado_periodo['anio']} completo"
        )
    else:
        st.sidebar.error(
            f"⚠️ Período {estado_periodo['mes']}/{estado_periodo['anio']} incompleto\n\n"
            f"{estado_periodo['bases_ok']} / {estado_periodo['bases_total']} bases cargadas"
        )

    # Renderizado del banner superior global cuando existan faltantes
    if not estado_periodo["completo"]:
        faltantes_str = "\n".join([f"• {b}" for b in estado_periodo["faltantes"]])
        st.warning(
            f"⚠️ **PERÍODO OPERATIVO INCOMPLETO**\n\n"
            f"**Período:** {estado_periodo['mes']}/{estado_periodo['anio']}\n\n"
            f"**Faltan cargar:**\n{faltantes_str}\n\n"
            f"Diríjase a Parámetros para completar la carga."
        )

    sup_sel_efectivo = (
        supervisores_disponibles[1:]
        if filtros_globales["supervisor"] == "TODOS"
        else [filtros_globales["supervisor"]]
    )

    es_local = es_entorno_local()

    # FEATURE_FLAG: Construcción dinámica de nombres de pestañas y mapeo de descriptores activos (Incluyendo Legacy)
    titulos_tabs_maestro = []
    claves_tabs_maestro = []

    if ff("GERENCIAL_UI"):
        titulos_tabs_maestro.append("📈 Tablero Gerencial")
        claves_tabs_maestro.append("GERENCIAL")

    if ff("KILOS_LEGACY_UI"):  # FEATURE_FLAG
        titulos_tabs_maestro.append("📊 Avance Kilos")
        claves_tabs_maestro.append("KILOS")

    if ff("CCC_LEGACY_UI"):  # FEATURE_FLAG
        titulos_tabs_maestro.append("📈 Avance CCC")
        claves_tabs_maestro.append("CCC")

    if ff("COB_MARCA_UI"):
        titulos_tabs_maestro.append("🎯 Cobertura Marca")
        claves_tabs_maestro.append("COB_MARCA")

    if ff("COB_INNOV_UI"):
        titulos_tabs_maestro.append("🚀 Cobertura Innovación")
        claves_tabs_maestro.append("COB_INNOV")

    if ff("MN_LEGACY_UI"):  # FEATURE_FLAG
        titulos_tabs_maestro.append("📱 Adopción MiNegocio")
        claves_tabs_maestro.append("MN")

    if ff("VESPERTINA_UI"):
        titulos_tabs_maestro.append("🌙 Vespertina")
        claves_tabs_maestro.append("VESPERTINA")

    if ff("TP_LEGACY_UI"):  # FEATURE_FLAG
        titulos_tabs_maestro.append("⭐ Tienda Perfecta")
        claves_tabs_maestro.append("TP")

    if "Nivel 1" in nivel_actual and es_local:
        titulos_tabs_maestro.append("⚙️ Parámetros")
        claves_tabs_maestro.append("PARAMETROS")

    if ff("OBJ_KILOS_LEGACY_UI"):  # FEATURE_FLAG
        titulos_tabs_maestro.append("📦 Composición Obj Kilos")
        claves_tabs_maestro.append("OBJ_KILOS")

    titulos_tabs_maestro.extend(
        [
            "🧪 Avance Kilos CORE",
            "🎯 Obj Kilos CORE",
            "📈 Avance CCC CORE",
            "📱 Adopción MiNegocio CORE",
            "⭐ Tienda Perfecta CORE",
        ]
    )
    claves_tabs_maestro.extend(
        ["KILOS_CORE", "OBJ_KILOS_CORE", "CCC_CORE", "MN_CORE", "TP_CORE"]
    )

    # Desempaquetado dinámico exacto de st.tabs según FEATURE_FLAGS vigentes
    objetos_tabs = st.tabs(titulos_tabs_maestro)
    mapping_tabs = dict(zip(claves_tabs_maestro, objetos_tabs))

    df_vend_maestro = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    df_marcas_maestro = pd.DataFrame()

    # Telemetría por etapas [PERF_STAGE] y control de ejecución condicional de motores
    if ff("COB_MARCA_ENGINE"):  # FEATURE_FLAG
        t0_m = time.perf_counter()
        rep_cob, marcas_lst, mapa_obj = generar_reporte_cobertura_marca(
            df_vta, df_universo, df_vend_maestro, df_marcas_maestro, filtros_globales
        )
        print(
            f"[PERF_STAGE] generar_reporte_cobertura_marca = {time.perf_counter() - t0_m:.2f} s"
        )
    else:
        rep_cob, marcas_lst, mapa_obj = (
            None,
            [],
            {},
        )  # FEATURE_FLAG: Valores dummy seguros
        print(
            "[PERF_STAGE] generar_reporte_cobertura_marca = OMITIDO (Engine Off)"
        )  # FEATURE_FLAG

    if ff("COB_INNOV_ENGINE"):  # FEATURE_FLAG
        t0_i = time.perf_counter()
        rep_innov, innovaciones_lst, df_innov_master = (
            generar_reporte_cobertura_innovacion(
                df_vta, df_universo, df_vend_maestro, filtros_globales
            )
        )
        print(
            f"[PERF_STAGE] generar_reporte_cobertura_innovacion = {time.perf_counter() - t0_i:.2f} s"
        )
    else:
        rep_innov, innovaciones_lst, df_innov_master = (
            None,
            [],
            pd.DataFrame(),
        )  # FEATURE_FLAG: Valores dummy seguros
        print(
            "[PERF_STAGE] generar_reporte_cobertura_innovacion = OMITIDO (Engine Off)"
        )  # FEATURE_FLAG

    # Renderizado de pestañas acorde al perfil activo protegido por Feature Flags (Incluyendo validación de ENGINE Legacy)
    if "Nivel 1" in nivel_actual:
        if "GERENCIAL" in mapping_tabs:
            with mapping_tabs["GERENCIAL"]:
                if ff("GERENCIAL_ENGINE"):  # FEATURE_FLAG
                    t0_g = time.perf_counter()
                    render_rep_gerencial(
                        df_vta, df_universo, df_rutas, df_ausencias, filtros_globales
                    )
                    print(
                        f"[PERF_STAGE] render_rep_gerencial = {time.perf_counter() - t0_g:.2f} s"
                    )
                else:
                    st.info(
                        "Módulo temporalmente deshabilitado."
                    )  # FEATURE_FLAG: Mensaje robusto UI sin engine
        if "KILOS" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["KILOS"]:
                if ff("KILOS_LEGACY_ENGINE"):  # FEATURE_FLAG
                    t0_k = time.perf_counter()
                    render_rep_kilos(df_vta, df_rutas, df_ausencias, filtros_globales)
                    print(
                        f"[PERF] render_rep_kilos: {time.perf_counter() - t0_k:.2f} s"
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "CCC" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["CCC"]:
                if ff("CCC_LEGACY_ENGINE"):  # FEATURE_FLAG
                    t0_c = time.perf_counter()
                    render_rep_ccc(df_vta, df_universo, filtros_globales)
                    print(f"[PERF] render_rep_ccc: {time.perf_counter() - t0_c:.2f} s")
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "COB_MARCA" in mapping_tabs:
            with mapping_tabs["COB_MARCA"]:
                if ff("COB_MARCA_ENGINE"):  # FEATURE_FLAG
                    dibujar_pestana_cobertura_marca(
                        rep_cob,
                        marcas_lst,
                        mapa_obj,
                        sup_sel_efectivo,
                        df_vta,
                        df_universo,
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "COB_INNOV" in mapping_tabs:
            with mapping_tabs["COB_INNOV"]:
                if ff("COB_INNOV_ENGINE"):  # FEATURE_FLAG
                    dibujar_pestana_cobertura_innovacion(
                        rep_innov, innovaciones_lst, df_innov_master, sup_sel_efectivo
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "MN" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["MN"]:
                if ff("MN_LEGACY_ENGINE"):  # FEATURE_FLAG
                    t0_mn = time.perf_counter()
                    render_rep_mn(df_vta, df_universo, filtros_globales)
                    print(
                        f"[PERF_STAGE] render_rep_mn = {time.perf_counter() - t0_mn:.2f} s"
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "VESPERTINA" in mapping_tabs:
            with mapping_tabs["VESPERTINA"]:
                if ff("VESPERTINA_ENGINE"):  # FEATURE_FLAG
                    t0_v = time.perf_counter()
                    render_rep_vespertina(df_vta, df_universo, filtros_globales)
                    print(
                        f"[PERF_STAGE] render_rep_vespertina = {time.perf_counter() - t0_v:.2f} s"
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "TP" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["TP"]:
                if ff("TP_LEGACY_ENGINE"):  # FEATURE_FLAG
                    t0_tp = time.perf_counter()
                    render_rep_tp(datos)
                    print(f"[PERF] render_rep_tp: {time.perf_counter() - t0_tp:.2f} s")
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "PARAMETROS" in mapping_tabs:
            with mapping_tabs["PARAMETROS"]:
                render_parametros_view(filtros_globales)
        if "OBJ_KILOS" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["OBJ_KILOS"]:
                if ff("OBJ_KILOS_LEGACY_ENGINE"):  # FEATURE_FLAG
                    render_rep_obj_kilos(df_vta, filtros_globales)
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        with mapping_tabs["KILOS_CORE"]:
            t0_kc = time.perf_counter()
            render_rep_kilos_core(df_vta, df_rutas, df_ausencias, filtros_globales)
            print(f"[PERF] render_rep_kilos_core: {time.perf_counter() - t0_kc:.2f} s")
        with mapping_tabs["OBJ_KILOS_CORE"]:
            t0_okc = time.perf_counter()
            render_rep_obj_kilos_core(filtros_globales)
            print(
                f"[PERF] render_rep_obj_kilos_core: {time.perf_counter() - t0_okc:.2f} s"
            )
        with mapping_tabs["CCC_CORE"]:
            t0_cccc = time.perf_counter()
            render_rep_ccc_core(filtros_globales)
            print(f"[PERF] render_rep_ccc_core: {time.perf_counter() - t0_cccc:.2f} s")
        with mapping_tabs["MN_CORE"]:
            t0_mnc = time.perf_counter()
            render_rep_mn_core(filtros_globales)
            print(f"[PERF] render_rep_mn_core: {time.perf_counter() - t0_mnc:.2f} s")
        with mapping_tabs["TP_CORE"]:
            t0_tpc = time.perf_counter()
            render_rep_tp_core(filtros_globales=filtros_globales)
            print(f"[PERF] render_rep_tp_core: {time.perf_counter() - t0_tpc:.2f} s")
    elif "Nivel 2" in nivel_actual:
        if "GERENCIAL" in mapping_tabs:
            with mapping_tabs["GERENCIAL"]:
                if ff("GERENCIAL_ENGINE"):  # FEATURE_FLAG
                    t0_g = time.perf_counter()
                    render_rep_gerencial(
                        df_vta, df_universo, df_rutas, df_ausencias, filtros_globales
                    )
                    print(
                        f"[PERF_STAGE] render_rep_gerencial = {time.perf_counter() - t0_g:.2f} s"
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "KILOS" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["KILOS"]:
                if ff("KILOS_LEGACY_ENGINE"):  # FEATURE_FLAG
                    t0_k = time.perf_counter()
                    render_rep_kilos(df_vta, df_rutas, df_ausencias, filtros_globales)
                    print(
                        f"[PERF] render_rep_kilos: {time.perf_counter() - t0_k:.2f} s"
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "CCC" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["CCC"]:
                if ff("CCC_LEGACY_ENGINE"):  # FEATURE_FLAG
                    t0_c = time.perf_counter()
                    render_rep_ccc(df_vta, df_universo, filtros_globales)
                    print(f"[PERF] render_rep_ccc: {time.perf_counter() - t0_c:.2f} s")
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "COB_MARCA" in mapping_tabs:
            with mapping_tabs["COB_MARCA"]:
                if ff("COB_MARCA_ENGINE"):  # FEATURE_FLAG
                    dibujar_pestana_cobertura_marca(
                        rep_cob,
                        marcas_lst,
                        mapa_obj,
                        sup_sel_efectivo,
                        df_vta,
                        df_universo,
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "COB_INNOV" in mapping_tabs:
            with mapping_tabs["COB_INNOV"]:
                if ff("COB_INNOV_ENGINE"):  # FEATURE_FLAG
                    dibujar_pestana_cobertura_innovacion(
                        rep_innov, innovaciones_lst, df_innov_master, sup_sel_efectivo
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "MN" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["MN"]:
                if ff("MN_LEGACY_ENGINE"):  # FEATURE_FLAG
                    t0_mn = time.perf_counter()
                    render_rep_mn(df_vta, df_universo, filtros_globales)
                    print(
                        f"[PERF_STAGE] render_rep_mn = {time.perf_counter() - t0_mn:.2f} s"
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "VESPERTINA" in mapping_tabs:
            with mapping_tabs["VESPERTINA"]:
                if ff("VESPERTINA_ENGINE"):  # FEATURE_FLAG
                    t0_v = time.perf_counter()
                    render_rep_vespertina(df_vta, df_universo, filtros_globales)
                    print(
                        f"[PERF_STAGE] render_rep_vespertina = {time.perf_counter() - t0_v:.2f} s"
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "TP" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["TP"]:
                if ff("TP_LEGACY_ENGINE"):  # FEATURE_FLAG
                    t0_tp = time.perf_counter()
                    render_rep_tp(datos)
                    print(f"[PERF] render_rep_tp: {time.perf_counter() - t0_tp:.2f} s")
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "OBJ_KILOS" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["OBJ_KILOS"]:
                if ff("OBJ_KILOS_LEGACY_ENGINE"):  # FEATURE_FLAG
                    render_rep_obj_kilos(df_vta, filtros_globales)
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        with mapping_tabs["KILOS_CORE"]:
            t0_kc = time.perf_counter()
            render_rep_kilos_core(df_vta, df_rutas, df_ausencias, filtros_globales)
            print(f"[PERF] render_rep_kilos_core: {time.perf_counter() - t0_kc:.2f} s")
        with mapping_tabs["OBJ_KILOS_CORE"]:
            t0_okc = time.perf_counter()
            render_rep_obj_kilos_core(filtros_globales)
            print(
                f"[PERF] render_rep_obj_kilos_core: {time.perf_counter() - t0_okc:.2f} s"
            )
        with mapping_tabs["CCC_CORE"]:
            t0_cccc = time.perf_counter()
            render_rep_ccc_core(filtros_globales)
            print(f"[PERF] render_rep_ccc_core: {time.perf_counter() - t0_cccc:.2f} s")
        with mapping_tabs["MN_CORE"]:
            t0_mnc = time.perf_counter()
            render_rep_mn_core(filtros_globales)
            print(f"[PERF] render_rep_mn_core: {time.perf_counter() - t0_mnc:.2f} s")
        with mapping_tabs["TP_CORE"]:
            t0_tpc = time.perf_counter()
            render_rep_tp_core(filtros_globales=filtros_globales)
            print(f"[PERF] render_rep_tp_core: {time.perf_counter() - t0_tpc:.2f} s")
    else:
        # Nivel 3: Supervisión
        if "KILOS" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["KILOS"]:
                if ff("KILOS_LEGACY_ENGINE"):  # FEATURE_FLAG
                    t0_k = time.perf_counter()
                    render_rep_kilos(df_vta, df_rutas, df_ausencias, filtros_globales)
                    print(
                        f"[PERF] render_rep_kilos: {time.perf_counter() - t0_k:.2f} s"
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "CCC" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["CCC"]:
                if ff("CCC_LEGACY_ENGINE"):  # FEATURE_FLAG
                    t0_c = time.perf_counter()
                    render_rep_ccc(df_vta, df_universo, filtros_globales)
                    print(f"[PERF] render_rep_ccc: {time.perf_counter() - t0_c:.2f} s")
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "COB_MARCA" in mapping_tabs:
            with mapping_tabs["COB_MARCA"]:
                if ff("COB_MARCA_ENGINE"):  # FEATURE_FLAG
                    dibujar_pestana_cobertura_marca(
                        rep_cob,
                        marcas_lst,
                        mapa_obj,
                        sup_sel_efectivo,
                        df_vta,
                        df_universo,
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "COB_INNOV" in mapping_tabs:
            with mapping_tabs["COB_INNOV"]:
                if ff("COB_INNOV_ENGINE"):  # FEATURE_FLAG
                    dibujar_pestana_cobertura_innovacion(
                        rep_innov, innovaciones_lst, df_innov_master, sup_sel_efectivo
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "MN" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["MN"]:
                if ff("MN_LEGACY_ENGINE"):  # FEATURE_FLAG
                    t0_mn = time.perf_counter()
                    render_rep_mn(df_vta, df_universo, filtros_globales)
                    print(
                        f"[PERF_STAGE] render_rep_mn = {time.perf_counter() - t0_mn:.2f} s"
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "VESPERTINA" in mapping_tabs:
            with mapping_tabs["VESPERTINA"]:
                if ff("VESPERTINA_ENGINE"):  # FEATURE_FLAG
                    t0_v = time.perf_counter()
                    render_rep_vespertina(df_vta, df_universo, filtros_globales)
                    print(
                        f"[PERF_STAGE] render_rep_vespertina = {time.perf_counter() - t0_v:.2f} s"
                    )
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        if "TP" in mapping_tabs:  # FEATURE_FLAG
            with mapping_tabs["TP"]:
                if ff("TP_LEGACY_ENGINE"):  # FEATURE_FLAG
                    t0_tp = time.perf_counter()
                    render_rep_tp(datos)
                    print(f"[PERF] render_rep_tp: {time.perf_counter() - t0_tp:.2f} s")
                else:
                    st.info("Módulo temporalmente deshabilitado.")  # FEATURE_FLAG
        with mapping_tabs["KILOS_CORE"]:
            t0_kc = time.perf_counter()
            render_rep_kilos_core(df_vta, df_rutas, df_ausencias, filtros_globales)
            print(f"[PERF] render_rep_kilos_core: {time.perf_counter() - t0_kc:.2f} s")
        with mapping_tabs["OBJ_KILOS_CORE"]:
            t0_okc = time.perf_counter()
            render_rep_obj_kilos_core(filtros_globales)
            print(
                f"[PERF] render_rep_obj_kilos_core: {time.perf_counter() - t0_okc:.2f} s"
            )
        with mapping_tabs["CCC_CORE"]:
            t0_cccc = time.perf_counter()
            render_rep_ccc_core(filtros_globales)
            print(f"[PERF] render_rep_ccc_core: {time.perf_counter() - t0_cccc:.2f} s")
        with mapping_tabs["MN_CORE"]:
            t0_mnc = time.perf_counter()
            render_rep_mn_core(filtros_globales)
            print(f"[PERF] render_rep_mn_core: {time.perf_counter() - t0_mnc:.2f} s")
        with mapping_tabs["TP_CORE"]:
            t0_tpc = time.perf_counter()
            render_rep_tp_core(filtros_globales=filtros_globales)
            print(f"[PERF] render_rep_tp_core: {time.perf_counter() - t0_tpc:.2f} s")

    t_rerun_total = time.perf_counter() - t_rerun_start
    print(
        f"[PERF_FORENSIC] === FIN RERUN GLOBAL N° {st.session_state['_global_rerun_count']} | Duración Total: {t_rerun_total:.2f} s ==="
    )


if __name__ == "__main__":
    main()
