# modules/database.py
import sqlite3
import pandas as pd
import os

DB_PATH = "data/matinal.db"

def obtener_conexion():
    """Crea una conexión a SQLite con timeout y modo WAL activado para concurrencia segura."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    """Inicializa la estructura básica si es necesario."""
    conn = obtener_conexion()
    conn.close()

def cargar_tabla_sql(query: str) -> pd.DataFrame:
    """Ejecuta una consulta SQL de forma segura. Si la tabla no existe, retorna un DataFrame vacío."""
    conn = obtener_conexion()
    try:
        q_lower = query.lower()
        if "from" in q_lower:
            partes = q_lower.split("from")[1].strip().split()
            if partes:
                nombre_tabla = partes[0].strip(";")
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name) = ?", (nombre_tabla,))
                if not cursor.fetchone():
                    return pd.DataFrame()
        
        df = pd.read_sql(query, conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

def guardar_dataframe_sql(df: pd.DataFrame, nombre_tabla: str, if_exists='replace'):
    """Guarda un DataFrame en la base de datos SQLite."""
    conn = obtener_conexion()
    try:
        df.to_sql(nombre_tabla, conn, if_exists=if_exists, index=False, chunksize=10000)
    finally:
        conn.close()

def tablas_existen() -> bool:
    """Verifica de forma robusta si las tablas operativas existen y contienen registros."""
    conn = obtener_conexion()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT LOWER(name) FROM sqlite_master WHERE type='table' AND LOWER(name) IN ('vta', 'universo', 'rutas', 'altas');")
        tablas = [row[0] for row in cursor.fetchall()]
        
        if len(set(tablas)) < 3:
            return False
            
        for tabla in ['vta', 'universo', 'rutas']:
            cursor.execute(f"SELECT COUNT(*) FROM {tabla};")
            count = cursor.fetchone()[0]
            if count == 0:
                return False
                
        return True
    except Exception:
        return False
    finally:
        conn.close()

def inicializar_bd_desde_excel(archivos_dict):
    """Lee los archivos Excel interpretando fechas y estructurando tablas con soporte para Obj_Mes, Altas y Ajuste_Entrega."""
    conn = obtener_conexion()
    try:
        for nombre_tabla, archivo in archivos_dict.items():
            if nombre_tabla.lower() == "altas":
                df = pd.read_excel(archivo, sheet_name="Creacion")
            else:
                df = pd.read_excel(archivo)
            
            # Normalización para maestro de vendedores (Ajuste_Entrega)
            if any(k in nombre_tabla.lower() for k in ["vendedor", "vendedores", "maestro_vendedores"]):
                col_ajuste_cand = next((c for c in df.columns if any(k in str(c).strip().lower() for k in ["ajuste", "entrega", "lag", "dias_entrega"])), None)
                if col_ajuste_cand:
                    df["Ajuste_Entrega"] = pd.to_numeric(df[col_ajuste_cand], errors="coerce").fillna(1).astype(int)
                else:
                    df["Ajuste_Entrega"] = 1

            if nombre_tabla.lower() in ["maestro_marcas_cebe", "marcas_cebe", "cebes"]:
                for col in df.columns:
                    col_l = str(col).strip().lower()
                    if col_l in ["obj_mes", "objetivo", "obj", "suma de tn", "tn"]:
                        df = df.rename(columns={col: "Obj_Mes"})
                if "Obj_Mes" in df.columns:
                    df["Obj_Mes"] = pd.to_numeric(df["Obj_Mes"], errors="coerce").fillna(0.0)

            for col in df.columns:
                col_l = str(col).strip().lower()
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
    finally:
        conn.close()

def guardar_objetivos_calibrados_desde_excel(file_buffer_or_path, anio, mes):
    """Guarda o reemplaza los objetivos definitivos en 'objetivos_vendedores' para el período (Anio, Mes)."""
    try:
        df_subida = pd.read_excel(file_buffer_or_path)
    except Exception as e:
        return False, f"Error al leer el archivo Excel: {e}"

    columnas_requeridas = ["CodVendedor", "SEGMENTO", "Obj_Sugerido_Kg"]
    faltantes = [c for c in columnas_requeridas if c not in df_subida.columns]
    if faltantes:
        return False, f"El archivo Excel no tiene el formato correcto. Faltan las columnas: {', '.join(faltantes)}"

    df_subida["CodVendedor"] = pd.to_numeric(df_subida["CodVendedor"], errors="coerce").astype("Int64")
    if "Nombre" in df_subida.columns:
        df_subida["Nombre"] = df_subida["Nombre"].fillna("").astype(str).str.strip()
    if "Supervisor" in df_subida.columns:
        df_subida["Supervisor"] = df_subida["Supervisor"].fillna("").astype(str).str.strip()
    df_subida["SEGMENTO"] = df_subida["SEGMENTO"].fillna("").astype(str).str.strip()
    df_subida["Obj_Sugerido_Kg"] = pd.to_numeric(df_subida["Obj_Sugerido_Kg"], errors="coerce").fillna(0.0)

    try:
        anio_int = int(float(str(anio)))
    except Exception:
        anio_int = 2026

    try:
        mes_int = int(float(str(mes)))
    except Exception:
        mes_int = 9

    df_subida["Anio"] = anio_int
    df_subida["Mes"] = mes_int

    conn = obtener_conexion()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS objetivos_vendedores (
                Anio INTEGER,
                Mes INTEGER,
                CodVendedor INTEGER,
                Nombre TEXT,
                Supervisor TEXT,
                SEGMENTO TEXT,
                Kilos_Mes_Anterior REAL,
                Objetivo_Mes_Anterior_Kg REAL,
                Logro_Anterior_Pct REAL,
                Obj_Sugerido_Kg REAL,
                PRIMARY KEY (Anio, Mes, CodVendedor, SEGMENTO)
            )
        """)
        conn.commit()

        cursor.execute("DELETE FROM objetivos_vendedores WHERE Anio = ? AND Mes = ?", (anio_int, mes_int))
        conn.commit()

        df_subida.to_sql("objetivos_vendedores", conn, if_exists="append", index=False, chunksize=10000)
    finally:
        conn.close()

    return True, f"¡Objetivos del período {mes_int:02d}/{anio_int} cargados y versionados con éxito en la base de datos!"

def guardar_innovaciones_desde_excel(file_buffer_or_path, anio, mes):
    """Guarda o reemplaza el maestro de innovaciones en la tabla 'maestro_innovaciones' para el período (Anio, Mes)."""
    try:
        df_subida = pd.read_excel(file_buffer_or_path)
    except Exception as e:
        return False, f"Error al leer el archivo Excel de innovaciones: {e}"

    columnas_requeridas = ["Codigo", "Articulo", "Innovacion", "Condicion_Vta"]
    faltantes = [c for c in columnas_requeridas if c not in df_subida.columns]
    if faltantes:
        return False, f"El archivo Excel no tiene el formato correcto. Faltan las columnas: {', '.join(faltantes)}"

    try:
        anio_int = int(float(str(anio)))
    except Exception:
        anio_int = 2026

    try:
        mes_int = int(float(str(mes)))
    except Exception:
        mes_int = 9

    df_subida["Anio"] = anio_int
    df_subida["Mes"] = mes_int
    df_subida["Codigo"] = pd.to_numeric(df_subida["Codigo"], errors="coerce").astype("Int64")
    df_subida["Articulo"] = df_subida["Articulo"].fillna("").astype(str).str.strip()
    df_subida["Innovacion"] = df_subida["Innovacion"].fillna("").astype(str).str.strip().str.upper()
    df_subida["Condicion_Vta"] = pd.to_numeric(df_subida["Condicion_Vta"], errors="coerce").fillna(1.0)

    conn = obtener_conexion()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS maestro_innovaciones (
                Anio INTEGER,
                Mes INTEGER,
                Codigo INTEGER,
                Articulo TEXT,
                Innovacion TEXT,
                Condicion_Vta REAL,
                PRIMARY KEY (Anio, Mes, Codigo, Innovacion)
            )
        """)
        conn.commit()

        cursor.execute("DELETE FROM maestro_innovaciones WHERE Anio = ? AND Mes = ?", (anio_int, mes_int))
        conn.commit()

        df_subida.to_sql("maestro_innovaciones", conn, if_exists="append", index=False, chunksize=10000)
    finally:
        conn.close()

    return True, f"¡Maestro de innovaciones del período {mes_int:02d}/{anio_int} guardado con éxito en la base de datos!"