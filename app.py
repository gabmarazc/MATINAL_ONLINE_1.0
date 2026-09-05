# app.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from data_loader import cargar_todas_las_bases
from modules.parametros import render_parametros_view, es_entorno_local, obtener_tabla_parametros
from modules.rep_kilos import render_rep_kilos
from modules.rep_obj_kilos import render_rep_obj_kilos
from modules.rep_ccc import render_rep_ccc
from modules.rep_batalla_ccc import render_rep_batalla_nc
from modules.rep_batalla_cobertura_marca import render_rep_batalla_cobertura
from modules import database as db

st.set_page_config(
    page_title="Sistema Matinal 2.0",
    page_icon="📊",
    layout="wide"
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

def main():
    st.title("🚀 Sistema Matinal 2.0 - Panel de Control Comercial")

    # ==========================================
    # BARRA LATERAL: CONTROL DE DATOS Y CACHÉ
    # ==========================================
    st.sidebar.header("⚙️ Control de Datos")
    if st.sidebar.button("🔄 Recargar Bases y Limpiar Caché", width="stretch"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.session_state.clear()
        st.sidebar.success("¡Caché borrada y bases actualizadas!")
        st.rerun()

    if "bases" not in st.session_state or st.session_state["bases"] is None:
        with st.spinner("Cargando bases de datos y ausencias..."):
            st.session_state["bases"] = cargar_todas_las_bases()

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

        if up_vta and up_univ and up_rutas:
            with st.spinner("Procesando y guardando archivos en SQLite..."):
                archivos_dict = {"vta": up_vta, "universo": up_univ, "rutas": up_rutas}
                db.inicializar_bd_desde_excel(archivos_dict)
            st.success("¡Base de datos inicializada con éxito! Recargando aplicación...")
            st.rerun()
        else:
            st.info("ℹ️ Sube los tres archivos requeridos (VTA, Universo y Rutas) para habilitar el sistema.")
            return

    def_matinal, def_vta, def_ant = calcular_fechas_operativas_default()

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
        sel_dia_matinal = st.date_input("Día Matinal", value=def_matinal, min_value=date(2020, 1, 1), format="DD/MM/YYYY")
        sel_dia_venta = st.date_input("Día Venta", value=def_vta, min_value=date(2020, 1, 1), format="DD/MM/YYYY")
        sel_dia_anterior = st.date_input("Día Anterior", value=def_ant, min_value=date(2020, 1, 1), format="DD/MM/YYYY")

    anio_sugerido = sel_dia_venta.year
    mes_sugerido = sel_dia_venta.month

    opciones_anio = [2023, 2024, 2025, 2026, 2027, 2028]
    idx_anio = opciones_anio.index(anio_sugerido) if anio_sugerido in opciones_anio else 3
    anio_operativo = st.sidebar.selectbox("Año Operativo", opciones_anio, index=idx_anio)

    opciones_mes = list(range(1, 13))
    mes_operativo = st.sidebar.selectbox("Mes Operativo", opciones_mes, index=mes_sugerido - 1)

    sel_supervisor = st.sidebar.selectbox("Supervisor", supervisores_disponibles, index=0)

    filtros_globales = {
        "anio": int(anio_operativo),
        "mes": int(mes_operativo),
        "supervisor": sel_supervisor,
        "dia_matinal": sel_dia_matinal.strftime("%d/%m/%Y"),
        "dia_venta": sel_dia_venta.strftime("%d/%m/%Y"),
        "dia_anterior": sel_dia_anterior.strftime("%d/%m/%Y")
    }

    es_local = es_entorno_local()
    
    if es_local:
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Avance Kilos", 
            "📦 Composición Obj Kilos",
            "📈 Avance CCC", 
            "⚔️ Batalla NC", 
            "🎯 Cobertura Marca", 
            "⚙️ Parámetros"
        ])
    else:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Avance Kilos", 
            "📦 Composición Obj Kilos",
            "📈 Avance CCC", 
            "⚔️ Batalla NC", 
            "🎯 Cobertura Marca"
        ])
    
    with tab1:
        render_rep_kilos(df_vta, df_rutas, df_ausencias, filtros_globales)

    with tab2:
        render_rep_obj_kilos(df_vta, filtros_globales)
        
    with tab3:
        render_rep_ccc(df_vta, df_universo)
        
    with tab4:
        render_rep_batalla_nc(df_vta, df_universo)
        
    with tab5:
        render_rep_batalla_cobertura()
        
    if es_local:
        with tab6:
            render_parametros_view(filtros_globales)

if __name__ == "__main__":
    main()