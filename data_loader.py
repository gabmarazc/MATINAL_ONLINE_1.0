import os
import io
import requests
import pandas as pd
import streamlit as st
import pyarrow as pa
import pyarrow.parquet as pq
from modules.procesamiento import leer_parametros_con_encabezado
import config as cfg

@st.cache_data(show_spinner=False)
def cargar_vta_optimizado(ruta_excel):
    """
    Carga VTA en Parquet. Si no existe o se actualiza VTA.xlsx, 
    convierte todas las columnas object/string a texto puro usando PyArrow nativo.
    """
    ruta_parquet = ruta_excel.replace(".xlsx", ".parquet").replace(".XLSX", ".parquet")
    
    if os.path.exists(ruta_parquet):
        if not os.path.exists(ruta_excel) or os.path.getmtime(ruta_parquet) >= os.path.getmtime(ruta_excel):
            try:
                return pd.read_parquet(ruta_parquet)
            except Exception:
                if os.path.exists(ruta_parquet):
                    os.remove(ruta_parquet)
    
    df_vta = pd.read_excel(ruta_excel, dtype=str)
    df_vta = df_vta.fillna("")
    table = pa.Table.from_pandas(df_vta, preserve_index=False)
    pq.write_table(table, ruta_parquet)
    
    return df_vta

@st.cache_data(ttl=3600, show_spinner=False)
def cargar_ausencias_remotas(url_ausencias):
    """Carga ausencias desde la web con caché de 1 hora"""
    try:
        ausencias_crudas = pd.read_csv(url_ausencias, encoding="utf-8", engine="python", on_bad_lines="skip")
        if ausencias_crudas.empty or "Fecha" not in ausencias_crudas.columns:
            raise ValueError("Estructura remota inválida")
        return ausencias_crudas
    except Exception:
        return pd.DataFrame(columns=["Marca temporal", "Dirección de correo electrónico", "Fecha", "Ausente", "Reemplazo", "Cliente"])

def cargar_todas_las_bases():
    """Capa 1: Carga optimizada de bases con Parquet y Caché de Streamlit"""
    df_vta = cargar_vta_optimizado(cfg.ARCHIVO_VTA_EXCEL)
    df_universo = pd.read_excel(cfg.ARCHIVO_UNIVERSO)
    
    renombres = {"Codigo": "Cliente", "codven": "CodVendedor", "SegmentoClienteCodigo": "Taxonomia"}
    for col in df_universo.columns:
        col_clean = str(col).strip().lower()
        if col_clean in ["nombre", "razon_social", "razonsocial", "descripcion", "cliente_nombre"]:
            renombres[col] = "NombreCliente"
        if col_clean in ["direccion", "domicilio"]:
            renombres[col] = "DireccionCliente"
    df_universo = df_universo.rename(columns=renombres)
    
    df_rutas = pd.read_excel(cfg.ARCHIVO_RUTAS)
    df_rutas["Codigo"] = pd.to_numeric(df_rutas["Codigo"], errors="coerce").astype("Int64")
    col_fecha_rutas = "Fecha"
    for c in df_rutas.columns:
        if str(c).strip().lower() in ["fecha", "fechacarga", "fecha_carga"]:
            col_fecha_rutas = c
            break
    df_rutas = df_rutas.rename(columns={col_fecha_rutas: "Fecha"})
    df_rutas["Fecha"] = pd.to_datetime(df_rutas["Fecha"], errors="coerce")
    
    ausencias_crudas = cargar_ausencias_remotas(cfg.URL_AUSENCIAS)
    
    # Carga segura de parámetros manejando la ausencia opcional de la hoja FECHAS
    try:
        parametros = leer_parametros_con_encabezado(cfg.ARCHIVO_PARAMETROS)
    except Exception:
        parametros = {}

    # Si el usuario ya modificó los parámetros en la UI, sincronizar con el diccionario base
    if "df_parametros" in st.session_state:
        df_p = st.session_state["df_parametros"]
        parametros["FECHAS"] = df_p

    return {
        "VTA": df_vta, 
        "UNIVERSO": df_universo, 
        "RUTAS": df_rutas, 
        "PARAMETROS": parametros, 
        "AUSENCIAS": ausencias_crudas
    }