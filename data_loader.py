import io
import os
import config as cfg
from modules.procesamiento import leer_parametros_con_encabezado
from modules import database as db
import pandas as pd
import streamlit as st


@st.cache_data(ttl=3600, show_spinner=False)
def cargar_ausencias_remotas(url_ausencias):
  """Carga ausencias desde la web con caché de 1 hora"""
  try:
    ausencias_crudas = pd.read_csv(
        url_ausencias, encoding="utf-8", engine="python", on_bad_lines="skip"
    )
    if ausencias_crudas.empty or "Fecha" not in ausencias_crudas.columns:
      raise ValueError("Estructura remota inválida")
    return ausencias_crudas
  except Exception:
    return pd.DataFrame(
        columns=[
            "Marca temporal",
            "Dirección de correo electrónico",
            "Fecha",
            "Ausente",
            "Reemplazo",
            "Cliente",
        ]
    )


def cargar_todas_las_bases():
  """Capa 1: Carga optimizada desde SQLite, solicitando archivos por UI solo si la base de datos no existe."""
  
  if not db.tablas_existen():
    st.warning("⚠️ No se encontró la base de datos local en el servidor. Por favor, sube los archivos iniciales para poblar SQLite:")
    
    col1, col2 = st.columns(2)
    with col1:
      up_vta = st.file_uploader("Subir Archivo VTA (.xlsx)", type=["xlsx", "xls"], key="up_vta")
      up_univ = st.file_uploader("Subir Archivo UNIVERSO (.xlsx)", type=["xlsx", "xls"], key="up_univ")
    with col2:
      up_rutas = st.file_uploader("Subir Archivo RUTAS (.xlsx)", type=["xlsx", "xls"], key="up_rutas")
      up_params = st.file_uploader("Subir Archivo PARÁMETROS (.xlsx)", type=["xlsx", "xls"], key="up_params")

    if not up_vta or not up_univ or not up_rutas or not up_params:
      st.info("ℹ️ Sube todos los archivos requeridos arriba para inicializar el sistema.")
      st.stop()
    
    archivos_dict = {
        "vta": up_vta,
        "universo": up_univ,
        "rutas": up_rutas
    }
    db.inicializar_bd_desde_excel(archivos_dict)
    
    try:
      parametros = leer_parametros_con_encabezado(up_params)
    except Exception:
      parametros = {}
  else:
    parametros = {}

  # Carga eficiente de tablas completas directamente desde SQLite
  df_vta = db.cargar_tabla_sql("vta")
  df_universo = db.cargar_tabla_sql("universo")
  df_rutas = db.cargar_tabla_sql("rutas")

  renombres = {
      "Codigo": "Cliente",
      "codven": "CodVendedor",
      "SegmentoClienteCodigo": "Taxonomia",
  }
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

  if "Codigo" in df_rutas.columns:
    df_rutas["Codigo"] = (
        pd.to_numeric(df_rutas["Codigo"], errors="coerce").astype("Int64")
    )
  
  col_fecha_rutas = "Fecha"
  for c in df_rutas.columns:
    if str(c).strip().lower() in ["fecha", "fechacarga", "fecha_carga"]:
      col_fecha_rutas = c
      break
  if col_fecha_rutas in df_rutas.columns:
    df_rutas = df_rutas.rename(columns={col_fecha_rutas: "Fecha"})
    df_rutas["Fecha"] = pd.to_datetime(df_rutas["Fecha"], errors="coerce")

  ausencias_crudas = cargar_ausencias_remotas(cfg.URL_AUSENCIAS)

  # GESTIÓN DINÁMICA DE FECHAS:
  if "df_parametros" not in st.session_state:
    st.session_state["df_parametros"] = pd.DataFrame({
        "PARAMETRO": [
            "Año",
            "Mes",
            "Dia Matinal",
            "Dia Venta",
            "Dia Anterior",
        ],
        "VALOR": ["2026", "9", "02/09/2026", "01/09/2026", "31/08/2026"],
    })

  parametros["FECHAS"] = st.session_state["df_parametros"]

  return {
      "VTA": df_vta,
      "UNIVERSO": df_universo,
      "RUTAS": df_rutas,
      "PARAMETROS": parametros,
      "AUSENCIAS": ausencias_crudas,
  }