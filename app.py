# app.py
import streamlit as st
import pandas as pd
import time
from datetime import date, timedelta
from data_loader import cargar_todas_las_bases
from modules.parametros import render_parametros_view, es_entorno_local, obtener_tabla_parametros
from modules.rep_kilos import render_rep_kilos
from modules.rep_obj_kilos import render_rep_obj_kilos
from modules.rep_ccc import render_rep_ccc
from modules.rep_MN import render_rep_mn
from modules.rep_cob_marca import generar_reporte_cobertura_marca, dibujar_pestana_cobertura_marca
from modules.rep_cob_innovacion import generar_reporte_cobertura_innovacion, dibujar_pestana_cobertura_innovacion
from modules.rep_gerencial import render_rep_gerencial
from modules.rep_vespertina import render_rep_vespertina
from modules import database as db

st.set_page_config(
    page_title="Sistema de Gestión de Ventas - MABELHERDI S.A",
    page_icon="📊",
    layout="wide"
)

# Inyección CSS apuntando correctamente a los span de BaseWeb para forzar un tono gris en los tags seleccionados
st.markdown("""
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
""", unsafe_allow_html=True)

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
                ["Nivel 1: Administrador", "Nivel 2: Gerencia", "Nivel 3: Supervisión"]
            )
            password = st.text_input("Contraseña de Acceso", type="password")
            btn_login = st.form_submit_button("Ingresar al Sistema")

            if btn_login:
                passwords_validos = {
                    "Nivel 1: Administrador": "admin2026",
                    "Nivel 2: Gerencia": "gerencia2026",
                    "Nivel 3: Supervisión": "sup2026"
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
    if not verificar_autenticacion():
        return

    st.title("Sistema de Gestión de Ventas - MABELHERDI S.A")

    nivel_actual = st.session_state.get("nivel_usuario", "")
    st.sidebar.info(f"Sesión activa: **{nivel_actual}**")
    if st.sidebar.button("🔒 Cerrar Sesión", width='stretch'):
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
    
    # Botones separados para Limpiar Caché y Recargar Bases con forzado de Excel
    if st.sidebar.button("🧹 Limpiar Caché", width='stretch'):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.sidebar.success("¡Caché purgada con éxito!")
        st.rerun()

    if st.sidebar.button("🔄 Recargar Bases", width='stretch'):
        t_inicio = time.time()
        with st.status("Sincronizando motores de datos y SQLite...", expanded=False) as status:
            st.write("Leyendo archivos fuente Excel...")
            st.session_state["bases"] = cargar_todas_las_bases(forzar=True)
            t_fin = time.time()
            duracion = t_fin - t_inicio
            status.update(label=f"¡Bases recargadas desde disco en {duracion:.2f} segundos!", state="complete", expanded=False)
        st.rerun()

    if "bases" not in st.session_state or st.session_state["bases"] is None:
        t_inicio = time.time()
        with st.status("Cargando bases de datos y ausencias...", expanded=False) as status:
            st.write("Conectando con motores de almacenamiento...")
            st.session_state["bases"] = cargar_todas_las_bases()
            t_fin = time.time()
            duracion = t_fin - t_inicio
            status.update(label=f"¡Bases cargadas exitosamente en {duracion:.2f} segundos!", state="complete", expanded=False)

    datos = st.session_state["bases"]

    df_vta = datos.get("VTA") if datos else pd.DataFrame()
    df_universo = datos.get("UNIVERSO") if datos else pd.DataFrame()
    df_rutas = datos.get("RUTAS") if datos else pd.DataFrame()
    df_ausencias = datos.get("AUSENCIAS") if datos else pd.DataFrame()

    if df_vta is None or df_universo is None or df_vta.empty or df_universo.empty:
        st.warning("⚠️ No se encontraron datos operativos en la base de datos local. Por favor, sube los archivos iniciales para poblar SQLite:")
        col1, col2 = st.columns(2)
        with col1:
            up_vta = st.file_uploader("Subir Archivo VTA (.xlsx)", type=["xlsx", "xls"], key="up_vta")
            up_univ = st.file_uploader("Subir Archivo UNIVERSO (.xlsx)", type=["xlsx", "xls"], key="up_univ")
        with col2:
            up_rutas = st.file_uploader("Subir Archivo RUTAS (.xlsx)", type=["xlsx", "xls"], key="up_rutas")

        if up_vta and up_univ and up_rutas and not st.session_state.get("bd_inicializada", False):
            t_inicio = time.time()
            with st.status("Procesando y guardando archivos en SQLite...", expanded=False) as status:
                archivos_dict = {"vta": up_vta, "universo": up_univ, "rutas": up_rutas}
                db.inicializar_bd_desde_excel(archivos_dict)
                st.session_state["bd_inicializada"] = True
                t_fin = time.time()
                duracion = t_fin - t_inicio
                status.update(label=f"¡Base de datos inicializada en {duracion:.2f} segundos!", state="complete", expanded=False)
            
            st.success("¡Base de datos inicializada con éxito! Recargando aplicación...")
            st.rerun()
        elif not st.session_state.get("bd_inicializada", False):
            st.info("ℹ️ Sube los tres archivos requeridos (VTA, Universo y Rutas) para habilitar el sistema.")
            return

    supervisores_disponibles = ["TODOS"]
    col_sup = None
    for cand in ["Supervisor", "SUPERVISOR", "Cod_Supervisor", "Cod_Sup"]:
        if cand in df_vta.columns:
            col_sup = cand
            break
    
    if col_sup:
        sups_unicos = sorted([str(s) for s in df_vta[col_sup].dropna().unique() if str(s).strip() != ""])
        supervisores_disponibles.extend(sups_unicos)
    else:
        try:
            df_m = db.cargar_tabla_sql("SELECT DISTINCT Supervisor FROM maestro_vendedores")
            if not df_m.empty and "Supervisor" in df_m.columns:
                sups_unicos = sorted([str(s) for s in df_m["Supervisor"].dropna().unique() if str(s).strip() != ""])
                supervisores_disponibles.extend(sups_unicos)
        except Exception:
            pass

    st.sidebar.header("🎛️ Filtros Globales")

    with st.sidebar.expander("📅 Fechas de Referencia", expanded=True):
        sel_dia_matinal = st.date_input("Día Matinal", min_value=date(2020, 1, 1), format="DD/MM/YYYY", key="sel_dia_matinal")
        sel_dia_venta = st.date_input("Día Venta", min_value=date(2020, 1, 1), format="DD/MM/YYYY", key="sel_dia_venta")
        sel_dia_anterior = st.date_input("Día Anterior", min_value=date(2020, 1, 1), format="DD/MM/YYYY", key="sel_dia_anterior")

    anio_sugerido = sel_dia_venta.year
    mes_sugerido = sel_dia_venta.month

    opciones_anio = [2023, 2024, 2025, 2026, 2027, 2028]
    idx_anio = opciones_anio.index(anio_sugerido) if anio_sugerido in opciones_anio else 3
    anio_operativo = st.sidebar.selectbox("Año Operativo", opciones_anio, index=idx_anio, key="sel_anio_op")

    opciones_mes = list(range(1, 13))
    mes_operativo = st.sidebar.selectbox("Mes Operativo", opciones_mes, index=mes_sugerido - 1, key="sel_mes_op")

    sel_supervisor = st.sidebar.selectbox("Supervisor", supervisores_disponibles, index=0, key="sel_sup_op")

    filtros_globales = {
        "anio": int(anio_operativo),
        "mes": int(mes_operativo),
        "supervisor": sel_supervisor,
        "dia_matinal": sel_dia_matinal.strftime("%d/%m/%Y"),
        "dia_venta": sel_dia_venta.strftime("%d/%m/%Y"),
        "dia_anterior": sel_dia_anterior.strftime("%d/%m/%Y")
    }

    es_local = es_entorno_local()
    
    # Definición de solapas incluyendo Vespertina
    if "Nivel 1" in nivel_actual or "Nivel 2" in nivel_actual:
        if es_local and "Nivel 1" in nivel_actual:
            tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
                "📈 Tablero Gerencial",
                "📊 Avance Kilos", 
                "📈 Avance CCC", 
                "🎯 Cobertura Marca", 
                "🚀 Cobertura Innovación",
                "📱 Adopción MiNegocio",
                "🌙 Vespertina",
                "⚙️ Parámetros",
                "📦 Composición Obj Kilos"
            ])
        else:
            tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
                "📈 Tablero Gerencial",
                "📊 Avance Kilos", 
                "📈 Avance CCC", 
                "🎯 Cobertura Marca", 
                "🚀 Cobertura Innovación",
                "📱 Adopción MiNegocio",
                "🌙 Vespertina",
                "📦 Composición Obj Kilos"
            ])
    else:
        # Nivel 3: Supervisión (Sin acceso al tablero gerencial)
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Avance Kilos", 
            "📈 Avance CCC", 
            "🎯 Cobertura Marca",
            "🚀 Cobertura Innovación",
            "📱 Adopción MiNegocio",
            "🌙 Vespertina"
        ])
    
    df_vend_maestro = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    df_marcas_maestro = db.cargar_tabla_sql("SELECT * FROM parametros_marcas")
    
    sup_sel_efectivo = supervisores_disponibles[1:] if filtros_globales["supervisor"] == "TODOS" else [filtros_globales["supervisor"]]
    
    # Medición del tiempo de procesamiento analítico previo al renderizado de pestañas
    t_proc_inicio = time.time()
    rep_cob, marcas_lst, mapa_obj = generar_reporte_cobertura_marca(df_vta, df_universo, df_vend_maestro, df_marcas_maestro, filtros_globales)
    rep_innov, innovaciones_lst, df_innov_master = generar_reporte_cobertura_innovacion(df_vta, df_universo, df_vend_maestro, filtros_globales)
    t_proc_fin = time.time()
    duracion_procesamiento = t_proc_fin - t_proc_inicio

    # Renderizado de pestañas acorde al perfil activo con telemetría de procesamiento
    if "Nivel 1" in nivel_actual:
        with tab1:
            render_rep_gerencial(df_vta, df_universo, df_rutas, df_ausencias, filtros_globales)
        with tab2:
            render_rep_kilos(df_vta, df_rutas, df_ausencias, filtros_globales)
        with tab3:
            render_rep_ccc(df_vta, df_universo, filtros_globales)
        with tab4:
            dibujar_pestana_cobertura_marca(rep_cob, marcas_lst, mapa_obj, sup_sel_efectivo, df_vta, df_universo)
        with tab5:
            dibujar_pestana_cobertura_innovacion(rep_innov, innovaciones_lst, df_innov_master, sup_sel_efectivo)
        with tab6:
            render_rep_mn(df_vta, df_universo, filtros_globales)
        with tab7:
            render_rep_vespertina(df_vta, filtros_globales)
        if es_local:
            with tab8:
                render_parametros_view(filtros_globales)
            with tab9:
                render_rep_obj_kilos(df_vta, filtros_globales)
        else:
            with tab8:
                render_rep_obj_kilos(df_vta, filtros_globales)
    elif "Nivel 2" in nivel_actual:
        with tab1:
            render_rep_gerencial(df_vta, df_universo, df_rutas, df_ausencias, filtros_globales)
        with tab2:
            render_rep_kilos(df_vta, df_rutas, df_ausencias, filtros_globales)
        with tab3:
            render_rep_ccc(df_vta, df_universo, filtros_globales)
        with tab4:
            dibujar_pestana_cobertura_marca(rep_cob, marcas_lst, mapa_obj, sup_sel_efectivo, df_vta, df_universo)
        with tab5:
            dibujar_pestana_cobertura_innovacion(rep_innov, innovaciones_lst, df_innov_master, sup_sel_efectivo)
        with tab6:
            render_rep_mn(df_vta, df_universo, filtros_globales)
        with tab7:
            render_rep_vespertina(df_vta, filtros_globales)
        with tab8:
            render_rep_obj_kilos(df_vta, filtros_globales)
    else:
        # Nivel 3: Supervisión
        with tab1:
            render_rep_kilos(df_vta, df_rutas, df_ausencias, filtros_globales)
        with tab2:
            render_rep_ccc(df_vta, df_universo, filtros_globales)
        with tab3:
            dibujar_pestana_cobertura_marca(rep_cob, marcas_lst, mapa_obj, sup_sel_efectivo, df_vta, df_universo)
        with tab4:
            dibujar_pestana_cobertura_innovacion(rep_innov, innovaciones_lst, df_innov_master, sup_sel_efectivo)
        with tab5:
            render_rep_mn(df_vta, df_universo, filtros_globales)
        with tab6:
            render_rep_vespertina(df_vta, filtros_globales)

    # Toast informativo discreto con el tiempo de procesamiento global de los motores analíticos
    st.toast(f"⚡ Procesamiento analítico completado en {duracion_procesamiento:.2f} segundos", icon="⏱️")

if __name__ == "__main__":
    main()