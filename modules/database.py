import sqlite3
import os
import pandas as pd

DB_PATH = os.path.join("data", "matinal.db")

def obtener_conexion():
    """Crea y retorna una conexión a la base de datos SQLite, asegurando que la carpeta data exista."""
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def inicializar_bd_desde_excel(archivos_dict):
    """Carga los DataFrames o rutas de Excel iniciales y los persiste en tablas SQLite."""
    conn = obtener_conexion()
    
    if "vta" in archivos_dict and archivos_dict["vta"] is not None:
        df_vta = pd.read_excel(archivos_dict["vta"], dtype=str)
        df_vta.to_sql("vta", conn, if_exists="replace", index=False)
        
    if "universo" in archivos_dict and archivos_dict["universo"] is not None:
        df_univ = pd.read_excel(archivos_dict["universo"])
        df_univ.to_sql("universo", conn, if_exists="replace", index=False)
        
    if "rutas" in archivos_dict and archivos_dict["rutas"] is not None:
        df_rutas = pd.read_excel(archivos_dict["rutas"])
        df_rutas.to_sql("rutas", conn, if_exists="replace", index=False)
        
    conn.close()

def tablas_existen():
    """Verifica si las tablas principales ya están creadas en la base de datos."""
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablas = [row[0] for row in cursor.fetchall()]
        conn.close()
        return all(t in tablas for t in ["vta", "universo", "rutas"])
    except Exception:
        return False

def cargar_tabla_sql(nombre_tabla: str) -> pd.DataFrame:
    """Extrae una tabla completa desde SQLite a un DataFrame de Pandas."""
    conn = obtener_conexion()
    try:
        df = pd.read_sql(f"SELECT * FROM {nombre_tabla}", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df