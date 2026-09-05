# modules/database.py
import sqlite3
import pandas as pd
import os

DB_PATH = "data/matinal.db"

def init_db():
    """Inicializa la carpeta y la estructura básica si es necesario."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.close()

def cargar_tabla_sql(query: str) -> pd.DataFrame:
    """Ejecuta una consulta SQL y retorna un DataFrame."""
    init_db()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    try:
        df = pd.read_sql(query, conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def guardar_dataframe_sql(df: pd.DataFrame, nombre_tabla: str, if_exists='replace'):
    """Guarda un DataFrame en la base de datos SQLite."""
    init_db()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    df.to_sql(nombre_tabla, conn, if_exists=if_exists, index=False, chunksize=10000)
    conn.close()

def tablas_existen() -> bool:
    """Verifica de forma robusta si las tablas operativas existen y contienen registros."""
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("SELECT LOWER(name) FROM sqlite_master WHERE type='table' AND LOWER(name) IN ('vta', 'universo', 'rutas');")
        tablas = [row[0] for row in cursor.fetchall()]
        
        if len(set(tablas)) < 3:
            conn.close()
            return False
            
        for tabla in ['vta', 'universo', 'rutas']:
            cursor.execute(f"SELECT COUNT(*) FROM {tabla};")
            count = cursor.fetchone()[0]
            if count == 0:
                conn.close()
                return False
                
        conn.close()
        return True
    except Exception:
        return False

def inicializar_bd_desde_excel(archivos_dict):
    """Lee los archivos Excel forzando la interpretación latina DD/MM/YYYY."""
    init_db()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    for nombre_tabla, archivo in archivos_dict.items():
        df = pd.read_excel(archivo)
        
        for col in df.columns:
            col_l = str(col).lower().strip()
            if any(k in col_l for k in ["fecha", "dia", "date"]):
                s = df[col].astype(str).str.strip().str.replace(" 00:00:00", "", regex=False)
                
                dt = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
                
                mask_na = dt.isna()
                if mask_na.any():
                    dt.loc[mask_na] = pd.to_datetime(s[mask_na], format="%d-%m-%Y", errors="coerce")
                
                mask_na = dt.isna()
                if mask_na.any():
                    dt.loc[mask_na] = pd.to_datetime(s[mask_na], format="%Y-%m-%d", errors="coerce")
                
                mask_na = dt.isna()
                if mask_na.any():
                    dt.loc[mask_na] = pd.to_datetime(s[mask_na], errors="coerce")
                
                df[col] = dt.dt.strftime("%Y-%m-%d")
                
        df.to_sql(nombre_tabla, conn, if_exists='replace', index=False, chunksize=10000)
    conn.close()