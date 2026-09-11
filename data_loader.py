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

def sincronizar_archivos_excel_locales():
    """Detecta archivos Excel operativos y maestros en data/ o en la raíz y actualiza SQLite si fueron modificados o falta la tabla altas."""
    posibles_rutas = ["data", "."]
    archivos_esperados = {
        "vta": ["VTA.xlsx", "vta.xlsx", "VTA.xls"],
        "universo": ["UNIVERSO.xlsx", "universo.xlsx", "UNIVERSO.xls"],
        "rutas": ["RUTAS.xlsx", "rutas.xlsx", "RUTAS.xls"],
        "maestro_marcas_cebe": ["MAESTRO_MARCAS_CEBE.xlsx", "maestro_marcas_cebe.xlsx", "marcas_cebe.xlsx"],
        "altas": ["ALTAS.xlsx", "altas.xlsx", "ALTAS.xls"]
    }
    
    archivos_encontrados = {}
    for tabla, nombres in archivos_esperados.items():
        for d in posibles_rutas:
            for n in nombres:
                ruta = os.path.join(d, n)
                if os.path.exists(ruta):
                    archivos_encontrados[tabla] = ruta
                    break
            if tabla in archivos_encontrados:
                break

    if "vta" in archivos_encontrados:
        try:
            db_path = "data/matinal.db"
            mtime_vta = os.path.getmtime(archivos_encontrados["vta"])
            mtime_db = os.path.getmtime(db_path) if os.path.exists(db_path) else 0
            
            mtime_cebe = os.path.getmtime(archivos_encontrados["maestro_marcas_cebe"]) if "maestro_marcas_cebe" in archivos_encontrados else 0
            mtime_altas = os.path.getmtime(archivos_encontrados["altas"]) if "altas" in archivos_encontrados else 0

            # Verificar si la tabla 'altas' existe físicamente en SQLite
            conn = db.obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='altas'")
            tabla_altas_existe = cursor.fetchone() is not None
            conn.close()

            # Forzar actualización si algún archivo es más nuevo que la BD, si la BD no existe, o si la tabla altas no fue creada
            if (mtime_vta > mtime_db or 
                mtime_cebe > mtime_db or 
                mtime_altas > mtime_db or 
                mtime_db == 0 or 
                not tabla_altas_existe):
                
                dict_para_cargar = {}
                for t, r in archivos_encontrados.items():
                    dict_para_cargar[t] = open(r, "rb")
                db.inicializar_bd_desde_excel(dict_para_cargar)
                for f in dict_para_cargar.values():
                    f.close()
        except Exception:
            pass

def cargar_todas_las_bases():
    """Carga optimizada de las bases operativas desde SQLite y ausencias remotas."""
    sincronizar_archivos_excel_locales()

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