import sqlite3
import pandas as pd
import os
import hashlib
import time
from datetime import datetime
from modules.logger import get_logger

# Initialization of the institutional logger for the data access layer
logger = get_logger("database")

DB_PATH = "data/matinal.db"


def obtener_conexion():
    """Crea una conexión a SQLite con timeout y modo WAL activado para concurrencia segura."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def recrear_indices_vta_defensivos(conn):
    """
    Verifica la existencia de la tabla 'vta' y crea de manera defensiva sus índices
    institucionales consultando el esquema real persistido mediante PRAGMA table_info(vta).
    Si una columna no existe, omite la creación del índice y emite una advertencia sin lanzar excepción.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name) = 'vta';"
    )
    if not cursor.fetchone():
        logger.info(
            "Tabla 'vta' no encontrada en SQLite. Creación defensiva de índices omitida."
        )
        return

    cursor.execute("PRAGMA table_info(vta);")
    columnas_reales = [row[1] for row in cursor.fetchall()]

    indices_esperados = [
        ("idx_vta_vendedor", "CodVendedor"),
        ("idx_vta_cliente", "Cliente"),
        ("idx_vta_fechacarga", "FechaCarga"),
        ("idx_vta_fechaentrega", "FechaEntrega"),
        ("idx_vta_marca", "Marca"),
    ]

    for nombre_idx, columna in indices_esperados:
        if columna in columnas_reales:
            conn.execute(
                f'CREATE INDEX IF NOT EXISTS {nombre_idx} ON vta("{columna}");'
            )
            logger.info(
                f"Índice institucional '{nombre_idx}' sobre columna '{columna}' verificado/creado exitosamente."
            )
        else:
            logger.warning(
                f"Índice institucional '{nombre_idx}' omitido: la columna '{columna}' no existe en el esquema persistido de 'vta'."
            )


def init_db():
    """Inicializa la estructura básica y asegura índices de rendimiento defensivos."""
    conn = obtener_conexion()
    try:
        recrear_indices_vta_defensivos(conn)
        conn.commit()
        logger.info("Verificación defensiva de índices de inicio en SQLite finalizada.")
    except Exception:
        logger.exception(
            "Error crítico al intentar crear los índices de rendimiento para la tabla vta en init_db."
        )
    finally:
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
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name) = ?",
                    (nombre_tabla,),
                )
                if not cursor.fetchone():
                    logger.warning(
                        f"La tabla consultada no existe en el catálogo de SQLite. Retornando DataFrame vacío para: {query}"
                    )
                    return pd.DataFrame()

        df = pd.read_sql(query, conn)
    except Exception:
        logger.exception(
            f"Error al ejecutar la consulta SQL: {query}. Retornando DataFrame vacío por seguridad."
        )
        df = pd.DataFrame()
    finally:
        conn.close()
    return df


def guardar_dataframe_sql(df: pd.DataFrame, nombre_tabla: str, if_exists="replace"):
    """Guarda un DataFrame en la base de datos SQLite."""
    conn = obtener_conexion()
    try:
        df.to_sql(nombre_tabla, conn, if_exists=if_exists, index=False, chunksize=10000)
        logger.info(
            f"DataFrame persistido con éxito en la tabla '{nombre_tabla}' (modo: {if_exists})."
        )
    finally:
        conn.close()


def tablas_existen() -> bool:
    """Verifica de forma robusta si las tablas operativas existen y contienen registros."""
    conn = obtener_conexion()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT LOWER(name) FROM sqlite_master WHERE type='table' AND LOWER(name) IN ('vta', 'universo', 'rutas', 'altas');"
        )
        tablas = [row[0] for row in cursor.fetchall()]

        if len(set(tablas)) < 3:
            logger.warning(
                "Validación estructural: Faltan tablas operativas esenciales en SQLite."
            )
            return False

        for tabla in ["vta", "universo", "rutas"]:
            cursor.execute(f"SELECT COUNT(*) FROM {tabla};")
            count = cursor.fetchone()[0]
            if count == 0:
                logger.warning(
                    f"Validación estructural: La tabla operativa '{tabla}' se encuentra vacía."
                )
                return False

        return True
    except Exception:
        logger.exception(
            "Error crítico al verificar la existencia y conteo de registros en las tablas operativas de SQLite."
        )
        return False
    finally:
        conn.close()


def obtener_df_maestro_corporativo() -> pd.DataFrame:
    """
    DataFrame Maestro de Nivel 1 (Filtro N1: EMPLEADOS).
    - Carga la tabla 'vta' de SQLite.
    - Aplica de forma universal el filtro N1 EMPLEADOS (elimina subramos 'EMPLOYEES' / 'EMPLEADOS').
    - Opera como la Única Fuente de Verdad (SSOT) para la derivación de DataFrames hijos en los reportes.
    """
    df = cargar_tabla_sql("SELECT * FROM vta")
    if df.empty:
        return df

    if "Subramo" in df.columns:
        subramo_clean = df["Subramo"].fillna("").astype(str).str.strip().str.upper()
        df = df[~subramo_clean.isin(["EMPLOYEES", "EMPLEADOS"])]

    col_vend_tit = next(
        (
            cand
            for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
            if cand in df.columns
        ),
        "CodVendedor",
    )
    if col_vend_tit in df.columns:
        df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype(
            "Int64"
        )

    return df


def obtener_hash_dataframe(df: pd.DataFrame) -> str:
    """Calcula un hash SHA-256 estable del contenido del DataFrame, normalizando nulos/espacios y orden superficial."""
    if df is None or df.empty:
        return hashlib.sha256(b"empty").hexdigest()

    df_clean = df.copy()
    for col in df_clean.columns:
        df_clean[col] = df_clean[col].fillna("").astype(str).str.strip()

    df_clean = df_clean.reindex(sorted(df_clean.columns), axis=1)
    try:
        df_clean = df_clean.sort_values(by=list(df_clean.columns)).reset_index(
            drop=True
        )
    except Exception:
        df_clean = df_clean.reset_index(drop=True)

    csv_bytes = df_clean.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def guardar_snapshot_universo_si_cambio(conn, df_universo: pd.DataFrame):
    """Compara el hash del universo actual con el último snapshot histórico, guarda en universo_hist y cataloga en universo_versiones si cambió."""
    if df_universo is None or df_universo.empty:
        return

    hash_actual = obtener_hash_dataframe(df_universo)

    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS universo_versiones (
            VersionID INTEGER PRIMARY KEY AUTOINCREMENT,
            FechaSnapshot TEXT,
            FechaCargaSistema TEXT,
            HashSnapshot TEXT UNIQUE,
            CantClientes INTEGER
        );
    """)
    conn.commit()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name) = 'universo_hist';"
    )
    tabla_existe = cursor.fetchone() is not None

    ultimo_hash = None
    if tabla_existe:
        try:
            res = pd.read_sql(
                "SELECT HashSnapshot FROM universo_hist ORDER BY FechaCargaSistema DESC LIMIT 1;",
                conn,
            )
            if not res.empty and "HashSnapshot" in res.columns:
                ultimo_hash = res.iloc[0]["HashSnapshot"]
        except Exception:
            ultimo_hash = None

    if hash_actual != ultimo_hash:
        df_hist = df_universo.copy()
        now = datetime.now()
        fecha_snapshot = now.strftime("%Y-%m-%d")
        fecha_carga_sistema = now.strftime("%Y-%m-%d %H:%M:%S")
        df_hist["FechaSnapshot"] = fecha_snapshot
        df_hist["FechaCargaSistema"] = fecha_carga_sistema
        df_hist["HashSnapshot"] = hash_actual

        try:
            df_hist.to_sql(
                "universo_hist", conn, if_exists="append", index=False, chunksize=10000
            )
        except Exception:
            # Detección de incompatibilidad de esquema (schema drift): recrear universo_hist con el nuevo esquema
            logger.warning(
                "Incompatibilidad de esquema detectada en 'universo_hist'. Recreando tabla histórica."
            )
            conn.execute("DROP TABLE IF EXISTS universo_hist;")
            conn.commit()
            df_hist.to_sql(
                "universo_hist", conn, if_exists="replace", index=False, chunksize=10000
            )

        logger.info(
            "Nuevo snapshot histórico del universo guardado en 'universo_hist' (detectados cambios en el contenido)."
        )

        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO universo_versiones (FechaSnapshot, FechaCargaSistema, HashSnapshot, CantClientes)
                VALUES (?, ?, ?, ?)
                """,
                (fecha_snapshot, fecha_carga_sistema, hash_actual, len(df_universo)),
            )
            if cursor.rowcount > 0:
                logger.info("UNIVERSO_VERSIONES: versión registrada correctamente")
            else:
                logger.info("UNIVERSO_VERSIONES: hash ya existente, versión omitida")
            conn.commit()
        except Exception:
            logger.exception("Error al registrar versión en universo_versiones.")
    else:
        logger.info(
            "El contenido de la tabla 'universo' no ha cambiado. No se genera nuevo snapshot en 'universo_hist'."
        )


def cargar_vta_desde_directorio(ruta_directorio: str) -> pd.DataFrame:
    """
    Carga y consolida verticalmente las transacciones particionadas de ventas desde el directorio Gescom.

    Flujo técnico:
    1. Evalúa si 'VTA_CONSOLIDADO.parquet' existe en el directorio y si está vigente
       respecto al mtime más reciente de los archivos CSV fuente.
    2. Si está vigente, lee directamente desde Parquet con manejo defensivo contra archivos corruptos.
    3. Si no existe o se detectaron CSVs más recientes, lee los CSV con pd.read_csv(sep=';', encoding='latin1', engine='c', dtype=str),
       los concatena y genera 'VTA_CONSOLIDADO.parquet' con compresión 'snappy'.
    4. Mantiene fallback defensivo para directorios históricos con archivos *.xlsx.
    """
    t_inicio_directorio = time.perf_counter()

    if not os.path.exists(ruta_directorio) or not os.path.isdir(ruta_directorio):
        logger.warning(
            f"El directorio especificado para VTA particionado no existe o no es válido: {ruta_directorio}"
        )
        return pd.DataFrame()

    ruta_parquet = os.path.join(ruta_directorio, "VTA_CONSOLIDADO.parquet")

    # Identificar archivos fuente CSV (excluyendo archivos temporales)
    archivos_csv = [
        f
        for f in os.listdir(ruta_directorio)
        if f.lower().endswith(".csv")
        and not f.startswith("~$")
        and os.path.isfile(os.path.join(ruta_directorio, f))
    ]
    archivos_csv.sort()

    # Si hay archivos CSV, procesamos bajo la regla institucional Parquet / CSV Gescom
    if archivos_csv:
        rutas_csv = [os.path.join(ruta_directorio, f) for f in archivos_csv]
        mtime_fuentes_max = max(os.path.getmtime(r) for r in rutas_csv)

        # 1. Leer parquet si está vigente
        if os.path.exists(ruta_parquet):
            try:
                mtime_parquet = os.path.getmtime(ruta_parquet)
                if mtime_parquet >= mtime_fuentes_max:
                    t_inicio_parquet = time.perf_counter()
                    df_consolidado = pd.read_parquet(ruta_parquet)
                    t_duracion_parquet = time.perf_counter() - t_inicio_parquet

                    msg_perf_parquet = (
                        f"[PERF_VTA] CACHE PARQUET VIGENTE -> {t_duracion_parquet:.2f} s | "
                        f"filas={len(df_consolidado)}"
                    )
                    print(msg_perf_parquet)
                    logger.info(msg_perf_parquet)
                    return df_consolidado
            except Exception:
                logger.warning(
                    f"[PERF_VTA] Caché Parquet '{ruta_parquet}' corrupto o ilegible. Reconstruyendo desde CSVs de origen."
                )
                try:
                    os.remove(ruta_parquet)
                except OSError:
                    pass

        # 2. Leer CSV Gescom con configuración obligatoria
        dfs = []
        for arch in archivos_csv:
            ruta_archivo = os.path.join(ruta_directorio, arch)
            t_inicio_archivo = time.perf_counter()
            try:
                # Verificación defensiva contra archivos CSV vacíos (0 bytes)
                if os.path.getsize(ruta_archivo) == 0:
                    logger.warning(
                        f"[PERF_VTA] Archivo CSV vacío (0 bytes) ignorado: {arch}"
                    )
                    continue

                df_item = pd.read_csv(
                    ruta_archivo,
                    sep=";",
                    encoding="latin1",
                    engine="c",
                    dtype=str,
                )
                t_duracion_archivo = time.perf_counter() - t_inicio_archivo

                cant_filas = len(df_item)
                msg_perf_archivo = f"[PERF_VTA] {arch} (CSV Gescom) -> {t_duracion_archivo:.2f} s | filas={cant_filas}"
                print(msg_perf_archivo)
                logger.info(msg_perf_archivo)
                dfs.append(df_item)
            except pd.errors.EmptyDataError:
                logger.warning(f"[PERF_VTA] Archivo CSV sin datos ignorado: {arch}")
            except Exception:
                logger.exception(f"[PERF_VTA] Error al procesar archivo CSV: {arch}")
                raise

        if not dfs:
            logger.warning(
                f"No se pudieron cargar datos válidos desde los CSVs en: {ruta_directorio}"
            )
            return pd.DataFrame()

        t_inicio_concat = time.perf_counter()
        df_consolidado = pd.concat(dfs, ignore_index=True)
        t_duracion_concat = time.perf_counter() - t_inicio_concat

        msg_perf_concat = f"[PERF_VTA] CONCAT CSV -> {t_duracion_concat:.2f} s"
        print(msg_perf_concat)
        logger.info(msg_perf_concat)

        # 3. Generar VTA_CONSOLIDADO.parquet con compresión snappy
        try:
            df_consolidado.to_parquet(ruta_parquet, index=False, compression="snappy")
            logger.info(
                f"[PERF_VTA] Archivo '{ruta_parquet}' generado y actualizado exitosamente (compresión: snappy)."
            )
        except Exception:
            logger.exception(
                f"[PERF_VTA] Error al intentar generar '{ruta_parquet}'. Se continuará con el DataFrame en memoria."
            )

        t_duracion_directorio = time.perf_counter() - t_inicio_directorio
        msg_perf_total_dir = (
            f"[PERF_VTA] TOTAL LECTURA DIRECTORIO -> {t_duracion_directorio:.2f} s"
        )
        print(msg_perf_total_dir)
        logger.info(msg_perf_total_dir)

        return df_consolidado

    # Fallback defensivo para directorios históricos con archivos *.xlsx
    archivos_xlsx = [
        f
        for f in os.listdir(ruta_directorio)
        if f.lower().endswith(".xlsx")
        and not f.startswith("~$")
        and os.path.isfile(os.path.join(ruta_directorio, f))
    ]
    archivos_xlsx.sort()

    if not archivos_xlsx:
        logger.warning(
            f"No se encontraron archivos *.csv ni *.xlsx en el directorio de ventas: {ruta_directorio}"
        )
        return pd.DataFrame()

    dfs = []
    for arch in archivos_xlsx:
        ruta_archivo = os.path.join(ruta_directorio, arch)
        t_inicio_archivo = time.perf_counter()
        try:
            df_mes = pd.read_excel(ruta_archivo)
            t_duracion_archivo = time.perf_counter() - t_inicio_archivo

            cant_filas = len(df_mes)
            msg_perf_archivo = f"[PERF_VTA] {arch} (Excel) -> {t_duracion_archivo:.2f} s | filas={cant_filas}"
            print(msg_perf_archivo)
            logger.info(msg_perf_archivo)
            dfs.append(df_mes)
        except Exception:
            logger.exception(f"[PERF_VTA] Error al leer archivo Excel: {arch}")

    if not dfs:
        return pd.DataFrame()

    t_inicio_concat = time.perf_counter()
    df_consolidado = pd.concat(dfs, ignore_index=True)
    t_duracion_concat = time.perf_counter() - t_inicio_concat

    msg_perf_concat = f"[PERF_VTA] CONCAT EXCEL -> {t_duracion_concat:.2f} s"
    print(msg_perf_concat)
    logger.info(msg_perf_concat)

    # Generar parquet consolidado si aplica
    try:
        df_consolidado.to_parquet(ruta_parquet, index=False, compression="snappy")
    except Exception:
        logger.exception("Error al generar parquet desde archivos Excel.")

    t_duracion_directorio = time.perf_counter() - t_inicio_directorio
    msg_perf_total_dir = (
        f"[PERF_VTA] TOTAL DIRECTORIO EXCEL -> {t_duracion_directorio:.2f} s"
    )
    print(msg_perf_total_dir)
    logger.info(msg_perf_total_dir)

    return df_consolidado


def inicializar_bd_desde_excel(archivos_dict):
    """Lee los archivos interpretando fechas y estructurando tablas con soporte multi-solapa para Altas."""
    conn = obtener_conexion()
    try:
        for nombre_tabla, archivo in archivos_dict.items():
            logger.warning(f"CARGANDO TABLA: {nombre_tabla}")
            if "altas" in nombre_tabla.lower():
                xls_altas = pd.ExcelFile(archivo)
                dfs_all = []
                for sheet in xls_altas.sheet_names:
                    df_sheet = pd.read_excel(archivo, sheet_name=sheet)

                    for col in df_sheet.columns:
                        col_l = str(col).strip().lower()
                        if any(k in col_l for k in ["fecha", "dia", "date"]):
                            s = (
                                df_sheet[col]
                                .astype(str)
                                .str.strip()
                                .str.replace(" 00:00:00", "", regex=False)
                            )
                            dt = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
                            mask_na = dt.isna()
                            if mask_na.any():
                                dt.loc[mask_na] = pd.to_datetime(
                                    s[mask_na], format="%d-%m-%Y", errors="coerce"
                                )
                            mask_na = dt.isna()
                            if mask_na.any():
                                dt.loc[mask_na] = pd.to_datetime(
                                    s[mask_na], format="%Y-%m-%d", errors="coerce"
                                )
                            mask_na = dt.isna()
                            if mask_na.any():
                                dt.loc[mask_na] = pd.to_datetime(
                                    s[mask_na], errors="coerce"
                                )
                            df_sheet[col] = dt.dt.strftime("%Y-%m-%d")

                    nombre_tabla_sheet = f"altas_{sheet.lower()}"
                    df_sheet.to_sql(
                        nombre_tabla_sheet,
                        conn,
                        if_exists="replace",
                        index=False,
                        chunksize=10000,
                    )

                    df_s_copy = df_sheet.copy()
                    df_s_copy["Origen_Hoja"] = sheet
                    dfs_all.append(df_s_copy)

                if dfs_all:
                    df_altas_unificado = pd.concat(dfs_all, ignore_index=True)
                    df_altas_unificado.to_sql(
                        "altas", conn, if_exists="replace", index=False, chunksize=10000
                    )
            elif nombre_tabla.lower() == "tp":
                logger.warning(f"DETECTADA CARGA ESPECIAL TP: {nombre_tabla}")
                df_raw = pd.read_excel(archivo, header=None)
                header_row = None
                for i, row in df_raw.iterrows():
                    if "Cliente_id" in row.astype(str).values:
                        header_row = i
                        break
                if header_row is None:
                    raise ValueError("No se encontró Cliente_id en TP.xlsx")
                df = pd.read_excel(archivo, header=header_row)
                df.columns = [str(c).strip() for c in df.columns]
            elif nombre_tabla.lower() == "vta":
                # RAMA VTA: Lectura optimizada (Directorio CSV/Parquet o Archivo único)
                t_inicio_lectura_vta = time.perf_counter()
                if os.path.isdir(archivo):
                    df = cargar_vta_desde_directorio(archivo)
                elif str(archivo).lower().endswith(".parquet"):
                    df = pd.read_parquet(archivo)
                elif str(archivo).lower().endswith(".csv"):
                    df = pd.read_csv(
                        archivo,
                        sep=";",
                        encoding="latin1",
                        engine="c",
                        dtype=str,
                    )
                else:
                    df = pd.read_excel(archivo)
                t_duracion_lectura_vta = time.perf_counter() - t_inicio_lectura_vta
                msg_perf_lectura = f"[PERF_VTA] LECTURA VTA -> {t_duracion_lectura_vta:.2f} s | filas={len(df)}"
                print(msg_perf_lectura)
                logger.info(msg_perf_lectura)
            else:
                df = pd.read_excel(archivo)

            if any(
                k in nombre_tabla.lower()
                for k in ["vendedor", "vendedores", "maestro_vendedores"]
            ):
                col_ajuste_cand = next(
                    (
                        c
                        for c in df.columns
                        if any(
                            k in str(c).strip().lower()
                            for k in ["ajuste", "entrega", "lag", "dias_entrega"]
                        )
                    ),
                    None,
                )
                if col_ajuste_cand:
                    df["Ajuste_Entrega"] = (
                        pd.to_numeric(df[col_ajuste_cand], errors="coerce")
                        .fillna(1)
                        .astype(int)
                    )
                else:
                    df["Ajuste_Entrega"] = 1

                col_rutas_ajust = next(
                    (
                        c
                        for c in df.columns
                        if any(
                            k in str(c).strip().lower()
                            for k in ["rutas_ajustadas", "rutasajustadas", "ajustadas"]
                        )
                    ),
                    None,
                )
                if col_rutas_ajust:
                    df["Rutas_Ajustadas"] = (
                        pd.to_numeric(df[col_rutas_ajust], errors="coerce")
                        .fillna(0)
                        .astype(int)
                    )
                else:
                    df["Rutas_Ajustadas"] = 0

            if nombre_tabla.lower() in ["maestro_marcas_cebe", "marcas_cebe", "cebes"]:
                for col in df.columns:
                    col_l = str(col).strip().lower()
                    if col_l in ["obj_mes", "objetivo", "obj", "suma de tn", "tn"]:
                        df = df.rename(columns={col: "Obj_Mes"})
                if "Obj_Mes" in df.columns:
                    df["Obj_Mes"] = pd.to_numeric(
                        df["Obj_Mes"], errors="coerce"
                    ).fillna(0.0)

            if "altas" not in nombre_tabla.lower():
                for col in df.columns:
                    col_l = str(col).strip().lower()
                    if any(k in col_l for k in ["fecha", "dia", "date"]):
                        s = (
                            df[col]
                            .astype(str)
                            .str.strip()
                            .str.replace(" 00:00:00", "", regex=False)
                        )
                        dt = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
                        mask_na = dt.isna()
                        if mask_na.any():
                            dt.loc[mask_na] = pd.to_datetime(
                                s[mask_na], format="%d-%m-%Y", errors="coerce"
                            )
                        mask_na = dt.isna()
                        if mask_na.any():
                            dt.loc[mask_na] = pd.to_datetime(
                                s[mask_na], format="%Y-%m-%d", errors="coerce"
                            )
                        mask_na = dt.isna()
                        if mask_na.any():
                            dt.loc[mask_na] = pd.to_datetime(
                                s[mask_na], errors="coerce"
                            )
                        df[col] = dt.dt.strftime("%Y-%m-%d")

                if nombre_tabla.lower() == "vta":
                    # Mantiene exactamente el mismo replace actual de SQLite
                    t_inicio_replace_vta = time.perf_counter()
                    df.to_sql(
                        "vta",
                        conn,
                        if_exists="replace",
                        index=False,
                        chunksize=10000,
                    )
                    t_duracion_replace_vta = time.perf_counter() - t_inicio_replace_vta
                    msg_perf_replace = (
                        f"[PERF_VTA] SQLITE REPLACE -> {t_duracion_replace_vta:.2f} s"
                    )
                    print(msg_perf_replace)
                    logger.info(msg_perf_replace)
                    logger.info(
                        f"Tabla 'vta' reconstruida completamente por reemplazo directo ({len(df)} registros)."
                    )
                elif nombre_tabla.lower() == "universo":
                    guardar_snapshot_universo_si_cambio(conn, df)
                    df.to_sql(
                        "universo",
                        conn,
                        if_exists="replace",
                        index=False,
                        chunksize=10000,
                    )
                else:
                    df.to_sql(
                        nombre_tabla,
                        conn,
                        if_exists="replace",
                        index=False,
                        chunksize=10000,
                    )

        # Recreación defensiva institucional de índices sobre vta validada contra esquema real
        recrear_indices_vta_defensivos(conn)
        conn.commit()
        logger.info(
            "Sincronización finalizada: verificación e indexación defensiva completada en SQLite."
        )
    finally:
        conn.close()


def importar_maestros_multisolapa_atomica(
    archivo_buffer_or_path, anio_def, mes_def
) -> tuple[bool, str]:
    """Importa masivamente todas las solapas del Excel consolidado en una transacción atómica única."""
    try:
        xls_global = pd.ExcelFile(archivo_buffer_or_path)
    except Exception as e:
        return False, f"Error al leer el archivo Excel: {e}"

    sheet_to_table = {
        "Maestro_Vendedores": "maestro_vendedores",
        "Maestro_Segmentos": "maestro_segmentos",
        "Maestro_Marcas_CEBE": "maestro_marcas_cebe",
        "Maestro_CCC_Config": "maestro_ccc",
        "Maestro_Innovaciones": "maestro_innovaciones",
        "Objetivos_Calibrados": "objetivos_vendedores",
    }

    conn = obtener_conexion()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION;")

        importados_count = 0
        for sheet_name, table_name in sheet_to_table.items():
            if sheet_name in xls_global.sheet_names:
                df_sheet = pd.read_excel(archivo_buffer_or_path, sheet_name=sheet_name)
                if not df_sheet.empty:
                    if "Anio" in df_sheet.columns:
                        df_sheet["Anio"] = (
                            pd.to_numeric(df_sheet["Anio"], errors="coerce")
                            .fillna(int(anio_def))
                            .astype(int)
                        )
                    if "Mes" in df_sheet.columns:
                        df_sheet["Mes"] = (
                            pd.to_numeric(df_sheet["Mes"], errors="coerce")
                            .fillna(int(mes_def))
                            .astype(int)
                        )

                    df_sheet.to_sql(
                        table_name,
                        conn,
                        if_exists="replace",
                        index=False,
                        chunksize=5000,
                    )
                    importados_count += 1

        conn.commit()
        return (
            True,
            f"¡Se han importado y actualizado exitosamente {importados_count} tablas en SQLite de forma atómica e instantánea!",
        )
    except Exception as e:
        conn.rollback()
        return False, f"Error crítico en la transacción SQL: {e}"
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
        return (
            False,
            f"El archivo Excel no tiene el formato correcto. Faltan las columnas: {', '.join(faltantes)}",
        )

    df_subida["CodVendedor"] = pd.to_numeric(
        df_subida["CodVendedor"], errors="coerce"
    ).astype("Int64")
    if "Nombre" in df_subida.columns:
        df_subida["Nombre"] = df_subida["Nombre"].fillna("").astype(str).str.strip()
    if "Supervisor" in df_subida.columns:
        df_subida["Supervisor"] = (
            df_subida["Supervisor"].fillna("").astype(str).str.strip()
        )
    df_subida["SEGMENTO"] = df_subida["SEGMENTO"].fillna("").astype(str).str.strip()
    df_subida["Obj_Sugerido_Kg"] = pd.to_numeric(
        df_subida["Obj_Sugerido_Kg"], errors="coerce"
    ).fillna(0.0)

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

        cursor.execute(
            "DELETE FROM objetivos_vendedores WHERE Anio = ? AND Mes = ?",
            (anio_int, mes_int),
        )
        conn.commit()

        df_subida.to_sql(
            "objetivos_vendedores",
            conn,
            if_exists="append",
            index=False,
            chunksize=10000,
        )
    finally:
        conn.close()

    return (
        True,
        f"¡Objetivos del período {mes_int:02d}/{anio_int} cargados y versionados con éxito en la base de datos!",
    )


def guardar_innovaciones_desde_excel(file_buffer_or_path, anio, mes):
    """Guarda o reemplaza el maestro de innovaciones en la tabla 'maestro_innovaciones' para el período (Anio, Mes)."""
    try:
        df_subida = pd.read_excel(file_buffer_or_path)
    except Exception as e:
        return False, f"Error al leer el archivo Excel de innovaciones: {e}"

    columnas_requeridas = ["Codigo", "Articulo", "Innovacion", "Condicion_Vta"]
    faltantes = [c for c in columnas_requeridas if c not in df_subida.columns]
    if faltantes:
        return (
            False,
            f"El archivo Excel no tiene el formato correcto. Faltan las columnas: {', '.join(faltantes)}",
        )

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
    df_subida["Codigo"] = pd.to_numeric(df_subida["Codigo"], errors="coerce").astype(
        "Int64"
    )
    df_subida["Articulo"] = df_subida["Articulo"].fillna("").astype(str).str.strip()
    df_subida["Innovacion"] = (
        df_subida["Innovacion"].fillna("").astype(str).str.strip().str.upper()
    )
    df_subida["Condicion_Vta"] = pd.to_numeric(
        df_subida["Condicion_Vta"], errors="coerce"
    ).astype("Int64")

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
                Condicion_Vta INTEGER,
                PRIMARY KEY (Anio, Mes, Codigo)
            )
        """)
        conn.commit()

        cursor.execute(
            "DELETE FROM maestro_innovaciones WHERE Anio = ? AND Mes = ?",
            (anio_int, mes_int),
        )
        conn.commit()

        df_subida.to_sql(
            "maestro_innovaciones",
            conn,
            if_exists="append",
            index=False,
            chunksize=10000,
        )
    finally:
        conn.close()

    return (
        True,
        f"¡Innovaciones del período {mes_int:02d}/{anio_int} cargadas y versionados con éxito en la base de datos!",
    )
