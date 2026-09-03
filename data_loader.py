import io
import os
import config as cfg
from modules.procesamiento import leer_parametros_con_encabezado
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import streamlit as st


@st.cache_data(show_spinner=False)
def cargar_vta_optimizado(ruta_o_archivo):
  """Carga VTA en Parquet aceptando ruta local o un buffer subido por Streamlit."""
  if hasattr(ruta_o_archivo, "read"):
    # Es un archivo subido por st.file_uploader
    df_vta = pd.read_excel(ruta_o_archivo, dtype=str)
    df_vta = df_vta.fillna("")
    return df_vta

  ruta_excel = ruta_o_archivo
  ruta_parquet = ruta_excel.replace(".xlsx", ".parquet").replace(
      ".XLSX", ".parquet"
  )

  if os.path.exists(ruta_parquet):
    if not os.path.exists(ruta_excel) or os.path.getmtime(
        ruta_parquet
    ) >= os.path.getmtime(ruta_excel):
      try:
        return pd.read_parquet(ruta_parquet)
      except Exception:
        if os.path.exists(ruta_parquet):
          os.remove(ruta_parquet)

  if not os.path.exists(ruta_excel):
    return None

  df_vta = pd.read_excel(ruta_excel, dtype=str)
  df_vta = df_vta.fillna("")
  table = pa.Table.from_pandas(df_vta, preserve_index=False)
  pq.write_table(table, ruta_parquet)

  return df_vta


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
  """Capa 1: Carga optimizada de bases, validando archivos locales o solicitándolos por UI."""
  
  # Verificamos si los archivos locales existen. Si no, abrimos unexpander / uploader en la barra lateral o pantalla principal.
  falta_vta = not os.path.exists(cfg.ARCHIVO_VTA_EXCEL)
  falta_universo = not os.path.exists(cfg.ARCHIVO_UNIVERSO)
  falta_rutas = not os.path.exists(cfg.ARCHIVO_RUTAS)
  falta_params = not os.path.exists(cfg.ARCHIVO_PARAMETROS)

  if falta_vta or falta_universo or falta_rutas or falta_params:
    st.warning("⚠️ No se encontraron las bases de datos locales en el servidor. Por favor, sube los archivos correspondientes para iniciar el sistema:")
    
    col1, col2 = st.columns(2)
    with col1:
      up_vta = st.file_uploader("Subir Archivo VTA (.xlsx)", type=["xlsx", "xls"], key="up_vta")
      up_univ = st.file_uploader("Subir Archivo UNIVERSO (.xlsx)", type=["xlsx", "xls"], key="up_univ")
    with col2:
      up_rutas = st.file_uploader("Subir Archivo RUTAS (.xlsx)", type=["xlsx", "xls"], key="up_rutas")
      up_params = st.file_uploader("Subir Archivo PARÁMETROS (.xlsx)", type=["xlsx", "xls"], key="up_params")

    if not up_vta or not up_univ or not up_rutas or not up_params:
      st.info("ℹ️ Sube todos los archivos requeridos arriba para continuar.")
      st.stop()
    
    # Si fueron subidos, los usamos directamente
    df_vta = cargar_vta_optimizado(up_vta)
    df_universo = pd.read_excel(up_univ)
    df_rutas = pd.read_excel(up_rutas)
    try:
      parametros = leer_parametros_con_encabezado(up_params)
    except Exception:
      parametros = {}
  else:
    df_vta = cargar_vta_optimizado(cfg.ARCHIVO_VTA_EXCEL)
    df_universo = pd.read_excel(cfg.ARCHIVO_UNIVERSO)
    df_rutas = pd.read_excel(cfg.ARCHIVO_RUTAS)
    try:
      parametros = leer_parametros_con_encabezado(cfg.ARCHIVO_PARAMETROS)
    except Exception:
      parametros = {}

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

  df_rutas["Codigo"] = (
      pd.to_numeric(df_rutas["Codigo"], errors="coerce").astype("Int64")
  )
  col_fecha_rutas = "Fecha"
  for c in df_rutas.columns:
    if str(c).strip().lower() in ["fecha", "fechacarga", "fecha_carga"]:
      col_fecha_rutas = c
      break
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