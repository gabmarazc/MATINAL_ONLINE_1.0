# app.py
import io
import streamlit as st
import pandas as pd

# Importaciones modulares internas (desde el paquete /modules)
from data_loader import cargar_todas_las_bases
from modules.procesamiento import limpiar_vtas_crudas, procesar_ext_vta, procesar_rutas_operativas
from modules.rep_kilos import generar_reporte_avance_kilos_segmento, dibujar_pestaña_kilos
from modules.rep_ccc import generar_reporte_ccc_taxonomia, dibujar_pestaña_ccc
from modules.rep_batalla_ccc import dibujar_pestaña_batalla
from modules.rep_cob_marca import generar_reporte_cobertura_marca, dibujar_pestana_cobertura_marca
from modules.rep_batalla_cobertura_marca import dibujar_pestaña_batalla_cobertura_marca, crear_filtro_excel
from modules.parametros import render_parametros

# Configuración de página
st.set_page_config(page_title="Sistema Matinal 2.0", layout="wide", page_icon="🚀")
st.title("🚀 Sistema Modular de Capas - Matinal 2.0")

# ==========================================
# FUNCIÓN COMPONENTE REUTILIZABLE NATIVA
# ==========================================
def renderizar_aggrid(df: pd.DataFrame, altura: int = 400):
    if df.empty:
        st.warning("No hay datos disponibles para mostrar.")
        return

    st.dataframe(
        df,
        height=altura,
        width="stretch"
    )

# ==========================================
# FUNCIÓN DE PROCESAMIENTO DINÁMICO (SIN CACHÉ PARA REFRESCO INMEDIATO)
# ==========================================
def procesar_datos_completos(bases, df_parametros_dinamico=None):
    if df_parametros_dinamico is not None and not df_parametros_dinamico.empty:
        fechas_param = df_parametros_dinamico
    else:
        fechas_param = bases["PARAMETROS"].get("FECHAS", pd.DataFrame({"PARAMETRO": ["Año", "Mes", "Dia Venta"], "VALOR": [2026, 8, "29/08/2026"]}))
        
    parametros_por_nombre = {}
    for n, v in zip(fechas_param["PARAMETRO"], fechas_param["VALOR"]):
        if pd.notna(n):
            parametros_por_nombre[str(n).strip().casefold()] = v
            
    anio_operativo = int(parametros_por_nombre.get("añooperativo", parametros_por_nombre.get("año", 2026)))
    
    # --- CORRECCIÓN DEL MES OPERATIVO ---
    val_mes = parametros_por_nombre.get("mesoperativo", parametros_por_nombre.get("mes", 1))
    val_mes_str = str(val_mes).strip()
    if "-" in val_mes_str:
        mes_operativo = int(val_mes_str.split("-")[1])
    else:
        mes_operativo = int(float(val_mes_str))
    # ------------------------------------

    dia_venta = pd.to_datetime(parametros_por_nombre.get("dia venta", parametros_por_nombre.get("día venta", "29/08/2026")), dayfirst=True, errors="coerce")
    
    # Inyectar los parámetros dinámicos actualizados en una copia de las bases para que el procesamiento los tome
    bases_trabajo = bases.copy()
    param_copia = bases_trabajo.get("PARAMETROS", {}).copy()
    param_copia["FECHAS"] = fechas_param
    bases_trabajo["PARAMETROS"] = param_copia

    df_vtas_limpias = limpiar_vtas_crudas(bases_trabajo["VTA"])
    df_vtas_limpias = df_vtas_limpias[df_vtas_limpias["FechaCarga"] <= dia_venta].copy()
    df_vtas_operativo = procesar_ext_vta(df_vtas_limpias, bases_trabajo["AUSENCIAS"], bases_trabajo["PARAMETROS"])
    df_rutas_operativas = procesar_rutas_operativas(bases_trabajo["RUTAS"], anio_operativo, mes_operativo)
    
    reporte_avance = generar_reporte_avance_kilos_segmento(
        df_vtas_operativo, df_vtas_limpias, bases_trabajo["PARAMETROS"]["VENDEDORES"], 
        bases_trabajo["PARAMETROS"]["SEGMENTOS"], df_rutas_operativas, dia_venta, anio_operativo, mes_operativo
    )
    reporte_ccc = generar_reporte_ccc_taxonomia(
        df_vtas_operativo.copy(), bases_trabajo["UNIVERSO"].copy(), 
        bases_trabajo["PARAMETROS"]["VENDEDORES"].copy(), bases_trabajo["PARAMETROS"]["CCC"].copy()
    )
    
    cartera_df = bases_trabajo.get("UNIVERSO", pd.DataFrame())
    
    reporte_cob_marca, marcas_lista, mapa_objetivos_marca = generar_reporte_cobertura_marca(
        df_vtas_operativo=df_vtas_operativo,
        df_cartera=cartera_df,
        vendedores=bases_trabajo["PARAMETROS"]["VENDEDORES"],
        df_marcas=bases_trabajo["PARAMETROS"]["MARCAS"]
    )
    
    return df_vtas_limpias, df_vtas_operativo, reporte_avance, reporte_ccc, reporte_cob_marca, marcas_lista, mapa_objetivos_marca, parametros_por_nombre, dia_venta

# Carga de datos en sesión
if "bases" not in st.session_state:
    st.session_state["bases"] = None

if st.session_state["bases"] is None:
    with st.spinner("Cargando y procesando bases matriciales..."):
        st.session_state["bases"] = cargar_todas_las_bases()

if st.session_state["bases"] is not None:
    try:
        bases = st.session_state["bases"]
        
        # Recuperar parámetros interactivos si existen en la sesión
        df_p_input = st.session_state.get("df_parametros", None)
        
        df_vtas_limpias, df_vtas_operativo, reporte_avance, reporte_ccc, reporte_cob_marca, marcas_lista, mapa_objetivos_marca, parametros_por_nombre, dia_venta = procesar_datos_completos(bases, df_p_input)
        
        # Sidebar y Botón de Recarga Manual
        st.sidebar.header("Acciones")
        if st.sidebar.button("🔄 Recargar Bases / Limpiar Caché"):
            st.cache_data.clear()
            st.session_state["bases"] = None
            if "df_parametros" in st.session_state:
                del st.session_state["df_parametros"]
            if "supervisores_activos" in st.session_state:
                del st.session_state["supervisores_activos"]
            st.rerun()
            
        supervisores_disponibles = sorted(
            [str(s).strip() for s in reporte_avance["SUP"].dropna().unique() if str(s).strip() not in ["0", "0.0", ""]]
        )
        
        supervisores_seleccionados = crear_filtro_excel("Supervisor", supervisores_disponibles, "filtro_global_sup")
        
        if not supervisores_seleccionados:
            supervisores_seleccionados = supervisores_disponibles
            
        # GUARDAR EN EL ESTADO GLOBAL DE LA SESIÓN PARA ACCESO TRANSVERSAL EN MÓDULOS
        st.session_state["supervisores_activos"] = supervisores_seleccionados
            
        # Visualización centrada, en negrita, tamaño doble (52px) y color rojo en el sidebar
        st.sidebar.markdown("---")
        st.sidebar.markdown("<div style='text-align: center;'><b>SUPERVISOR</b></div>", unsafe_allow_html=True)
        sup_codigos_texto = ", ".join(map(str, supervisores_seleccionados)) if supervisores_seleccionados else "NINGUNO"
        st.sidebar.markdown(f"<div style='text-align: center; color: #ef4444; font-size: 52px; font-weight: bold;'>{sup_codigos_texto}</div>", unsafe_allow_html=True)
        
        reporte_ccc_filtrado = reporte_ccc[
            reporte_ccc["SUP"].astype(str).str.strip().isin([str(s).strip() for s in supervisores_seleccionados])
        ].copy()
        
        # Pestañas principales con Parámetros Fechas al principio
        tab_params, tab_reporte, tab_ccc, tab_batalla, tab_cob_marca, tab_batalla_cob = st.tabs([
            "⚙️ Parámetros Fechas", "📈 Avance Kilos", "📊 Avance CCC Taxonomía", "🎯 Batalla NC", "🏷️ Cobertura por Marca", "🎯 Batalla Cob. Marca"
        ])
        
        # --- PESTAÑA 1: PARÁMETROS FECHAS ---
        with tab_params:
            render_parametros()

        # --- PESTAÑA 2: AVANCE KILOS ---
        with tab_reporte:
            dibujar_pestaña_kilos(reporte_avance, supervisores_seleccionados, df_vtas_limpias, parametros_por_nombre)
            
        # --- PESTAÑA 3: AVANCE CCC TAXONOMÍA ---
        with tab_ccc:
            dibujar_pestaña_ccc(reporte_ccc_filtrado)
            
        # --- PESTAÑA 4: BATALLA NC ---
        with tab_batalla:
            dibujar_pestaña_batalla(bases, df_vtas_operativo, supervisores_seleccionados)
            
        # --- PESTAÑA 5: COBERTURA POR MARCA ---
        with tab_cob_marca:
            dibujar_pestana_cobertura_marca(
                reporte_cobertura=reporte_cob_marca,
                marcas=marcas_lista,
                mapa_objetivos=mapa_objetivos_marca,
                supervisores_seleccionados=supervisores_seleccionados,
                df_vtas_operativo=df_vtas_operativo
            )

        # --- PESTAÑA 6: BATALLA COBERTURA POR MARCA ---
        with tab_batalla_cob:
            dibujar_pestaña_batalla_cobertura_marca(
                bases=bases,
                df_vtas_operativo=df_vtas_operativo,
                supervisores_seleccionados=supervisores_seleccionados
            )

    except Exception as e:
        import traceback
        st.error("❌ Ocurrió un error en la ejecución del sistema:")
        st.code(traceback.format_exc(), language="python")