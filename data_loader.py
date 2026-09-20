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
            url_ausencias, 
            headers={'User-Agent': 'Mozilla/5.0'}
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
        "maestro_innovaciones": ["innovacion", "innovaciones", "maestro_innovaciones"]
    }

    for d in posibles_rutas:
        if not os.path.exists(d):
            continue
        try:
            for archivo in os.listdir(d):
                if not archivo.lower().endswith(('.xlsx', '.xls')):
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
            db.inicializar_bd_desde_excel(archivos_encontrados)
        except Exception:
            pass

def cargar_todas_las_bases(forzar=False):
    """Carga de bases operativas desde SQLite y ausencias remotas. Si forzar=True, re-sincroniza desde los Excel locales."""
    sincronizar_archivos_excel_locales(forzar=forzar)

    df_vta = db.cargar_tabla_sql("SELECT * FROM vta")
    df_universo = db.cargar_tabla_sql("SELECT * FROM universo")
    df_rutas = db.cargar_tabla_sql("SELECT * FROM rutas")
    df_altas = db.cargar_tabla_sql("SELECT * FROM altas")

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
            df_altas["Codigo"] = pd.to_numeric(df_altas["Codigo"], errors="coerce").astype("Int64")
        if "Vendedor" in df_altas.columns:
            df_altas["Vendedor"] = pd.to_numeric(df_altas["Vendedor"], errors="coerce").astype("Int64")

    ausencias_crudas = cargar_ausencias_remotas(getattr(cfg, "URL_AUSENCIAS", ""))

    return {
        "VTA": df_vta,
        "UNIVERSO": df_universo,
        "RUTAS": df_rutas,
        "ALTAS": df_altas,
        "AUSENCIAS": ausencias_crudas,
    }