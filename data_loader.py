# data_loader.py
import os
import config as cfg
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

def sincronizar_archivos_excel_locales():
    """Detecta archivos Excel en la raíz o en data/ y actualiza SQLite si fueron pisados o modificados."""
    posibles_rutas = [".", "data"]
    archivos_esperados = {
        "vta": ["VTA.xlsx", "vta.xlsx", "VTA.xls"],
        "universo": ["UNIVERSO.xlsx", "universo.xlsx", "UNIVERSO.xls"],
        "rutas": ["RUTAS.xlsx", "rutas.xlsx", "RUTAS.xls"]
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

    # Si encontramos VTA.xlsx en el disco, verificamos si es más nuevo que la base o forzamos actualización
    if "vta" in archivos_encontrados:
        try:
            db_path = "data/matinal.db"
            mtime_vta = os.path.getmtime(archivos_encontrados["vta"])
            mtime_db = os.path.getmtime(db_path) if os.path.exists(db_path) else 0
            
            # Si el archivo Excel fue modificado después de la base de datos (o la base no existe)
            if mtime_vta > mtime_db or mtime_db == 0:
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
    # Sincroniza automáticamente cualquier Excel que se haya pisado en local
    sincronizar_archivos_excel_locales()

    df_vta = db.cargar_tabla_sql("SELECT * FROM vta")
    df_universo = db.cargar_tabla_sql("SELECT * FROM universo")
    df_rutas = db.cargar_tabla_sql("SELECT * FROM rutas")

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

    ausencias_crudas = cargar_ausencias_remotas(getattr(cfg, "URL_AUSENCIAS", ""))

    return {
        "VTA": df_vta,
        "UNIVERSO": df_universo,
        "RUTAS": df_rutas,
        "AUSENCIAS": ausencias_crudas,
    }