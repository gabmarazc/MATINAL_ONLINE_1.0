# modules/database.py
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


def calcular_hash_fila_vta(row) -> str:
    """Calcula el HASH_VTA institucional para una fila de ventas utilizando las 6 columnas clave."""
    partes = [
        str(row.get("NroComprobante", "")).strip(),
        str(row.get("Codigo", "")).strip(),
        str(row.get("CantBase", "")).strip(),
        str(row.get("ImporteNetoItem", "")).strip(),
        str(row.get("ComprobanteReferencia", "")).strip(),
        str(row.get("ComboCodigo", "")).strip(),
    ]
    raw_str = "|".join(partes)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def asegurar_tabla_vta(conn, df_muestra: pd.DataFrame):
    """
    Detecta si la tabla 'vta' existe. Si no existe, utiliza df.head(0).to_sql
    únicamente para el bootstrap inicial preservando los tipos de datos originales.
    Garantiza la presencia de la columna HASH_VTA.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name) = 'vta';"
    )
    tabla_existe = cursor.fetchone() is not None

    if not tabla_existe:
        df_muestra.head(0).to_sql("vta", conn, if_exists="append", index=False)
        logger.info(
            "Estructura VTA creada mediante bootstrap inicial con preservación de tipos."
        )

    cursor.execute("PRAGMA table_info(vta);")
    columnas_vta = [row[1] for row in cursor.fetchall()]
    if "HASH_VTA" not in columnas_vta:
        cursor.execute("ALTER TABLE vta ADD COLUMN HASH_VTA TEXT;")
        logger.info("Columna HASH_VTA añadida a la tabla vta existente.")


def migrar_hash_vta_si_corresponde(conn):
    """
    Verifica mediante la tabla de control persistente 'schema_version' si la migración histórica
    de HASH_VTA ya se ejecutó. Si no se ha ejecutado, procesa el relleno histórico paginado una única vez
    y registra el estado de completitud. Participa completamente de la transacción abierta por la función contenedora
    sin emitir commits ni rollbacks propios.
    """
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            MigrationKey TEXT PRIMARY KEY,
            CompletedAt TEXT
        );
    """)

    cursor.execute(
        "SELECT 1 FROM schema_version WHERE MigrationKey = 'MIGRACION_HASH_VTA_COMPLETADA';"
    )
    if cursor.fetchone() is not None:
        return

    batch_size = 50000
    while True:
        cursor.execute(
            "SELECT rowid, NroComprobante, Codigo, CantBase, ImporteNetoItem, ComprobanteReferencia, ComboCodigo "
            "FROM vta WHERE HASH_VTA IS NULL OR HASH_VTA = '' LIMIT ?;",
            (batch_size,),
        )
        registros_antiguos = cursor.fetchall()
        if not registros_antiguos:
            break

        updates = []
        for reg in registros_antiguos:
            row_dict = {
                "NroComprobante": reg[1],
                "Codigo": reg[2],
                "CantBase": reg[3],
                "ImporteNetoItem": reg[4],
                "ComprobanteReferencia": reg[5],
                "ComboCodigo": reg[6],
            }
            h = calcular_hash_fila_vta(row_dict)
            updates.append((h, reg[0]))

        cursor.executemany("UPDATE vta SET HASH_VTA = ? WHERE rowid = ?;", updates)
        logger.info(
            f"Relleno histórico paginado HASH_VTA: Procesados {len(updates)} registros."
        )

    cursor.execute(
        "INSERT OR IGNORE INTO schema_version (MigrationKey, CompletedAt) VALUES ('MIGRACION_HASH_VTA_COMPLETADA', ?);",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),),
    )
    logger.info(
        "Migración histórica HASH_VTA marcada como completada permanentemente en schema_version."
    )


def guardar_vta_incremental_sql(conn, df_vta: pd.DataFrame):
    """
    Persiste la tabla VTA en modelo histórico acumulativo permanente de forma escalable.
    Sincroniza columnas, ejecuta migración histórica, staging temporal e inserción basada en clave de negocio única en transacción única.
    """
    if df_vta is None or df_vta.empty:
        return

    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN TRANSACTION;")

        # 1. Asegurar la existencia de la tabla vta y la columna HASH_VTA
        asegurar_tabla_vta(conn, df_vta)

        # 2. Ejecutar migración histórica persistente de registros antiguos una sola vez
        migrar_hash_vta_si_corresponde(conn)

        # Asegurar columna CLAVE_NEGOCIO en vta
        cursor.execute("PRAGMA table_info(vta);")
        columnas_vta = [row[1] for row in cursor.fetchall()]
        if "CLAVE_NEGOCIO" not in columnas_vta:
            cursor.execute("ALTER TABLE vta ADD COLUMN CLAVE_NEGOCIO TEXT;")
            logger.info("Columna CLAVE_NEGOCIO añadida a la tabla vta existente.")

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_vta_clave_negocio
            ON vta(CLAVE_NEGOCIO);
        """)

        # Función local interna de normalización canónica simétrica
        def normalizar_valor(val):
            if val is None:
                return ""
            s = str(val).strip()
            if s in ["nan", "None", "<NA>", ""]:
                return ""
            if s.endswith(".0"):
                s = s[:-2]
            return s

        cols_clave = [
            "NroComprobante",
            "Codigo",
            "CantBase",
            "ImporteNetoItem",
            "ComprobanteReferencia",
            "ComboCodigo",
        ]

        def construir_clave_row(row):
            partes = []
            for col in cols_clave:
                val = row.get(col, "")
                partes.append(normalizar_valor(val))
            return "|".join(partes)

        # 3. Backfill / actualización de CLAVE_NEGOCIO para registros históricos en vta que no la tengan
        cursor.execute(
            "SELECT rowid, NroComprobante, Codigo, CantBase, ImporteNetoItem, ComprobanteReferencia, ComboCodigo "
            "FROM vta WHERE CLAVE_NEGOCIO IS NULL OR CLAVE_NEGOCIO = '';"
        )
        historicos = cursor.fetchall()
        if historicos:
            updates_hist = []
            for reg in historicos:
                row_dict = {
                    "NroComprobante": reg[1],
                    "Codigo": reg[2],
                    "CantBase": reg[3],
                    "ImporteNetoItem": reg[4],
                    "ComprobanteReferencia": reg[5],
                    "ComboCodigo": reg[6],
                }
                clave = construir_clave_row(row_dict)
                updates_hist.append((clave, reg[0]))
            cursor.executemany(
                "UPDATE vta SET CLAVE_NEGOCIO = ? WHERE rowid = ?;", updates_hist
            )
            logger.info(
                f"Backfill CLAVE_NEGOCIO histórico: Procesados {len(updates_hist)} registros."
            )

        # 4. Preparar el DataFrame entrante: construir CLAVE_NEGOCIO, calcular HASH_VTA y eliminar duplicados internos por CLAVE_NEGOCIO
        df = df_vta.copy()

        df["CLAVE_NEGOCIO"] = df.apply(construir_clave_row, axis=1)

        if "HASH_VTA" not in df.columns:
            df["HASH_VTA"] = df.apply(calcular_hash_fila_vta, axis=1)

        df = df.drop_duplicates(subset=["CLAVE_NEGOCIO"]).copy()

        # 5. Sincronización de esquema: Agregar columnas faltantes en vta si existen en el DataFrame entrante
        cursor.execute("PRAGMA table_info(vta);")
        columnas_tabla_vta = [row[1] for row in cursor.fetchall()]

        for col in df.columns:
            if col not in columnas_tabla_vta:
                cursor.execute(f'ALTER TABLE vta ADD COLUMN "{col}" TEXT;')
                logger.info(
                    f"Sincronización de esquema VTA: Columna faltante '{col}' añadida mediante ALTER TABLE."
                )

        # Recargar esquema sincronizado
        cursor.execute("PRAGMA table_info(vta);")
        columnas_tabla_vta = [row[1] for row in cursor.fetchall()]

        for col in columnas_tabla_vta:
            if col not in df.columns:
                df[col] = None

        df = df[columnas_tabla_vta]

        # 6. Crear tabla temporal SQLite (staging_vta) con la estructura sincronizada
        cursor.execute("DROP TABLE IF EXISTS staging_vta;")
        cursor.execute(
            "CREATE TEMPORARY TABLE staging_vta AS SELECT * FROM vta WHERE 1=0;"
        )

        # 7. Volcar el DataFrame normalizado a staging_vta por lotes (chunks)
        chunk_size = 10000
        total_registros = len(df)
        cols = list(df.columns)

        for start_idx in range(0, total_registros, chunk_size):
            chunk_df = df.iloc[start_idx : start_idx + chunk_size]
            chunk_df.to_sql(
                "staging_vta", conn, if_exists="append", index=False, chunksize=10000
            )

        # 8. Inserción basada exclusivamente en CLAVE_NEGOCIO
        cols_str = ", ".join(cols)
        sql_insert_set_based = f"""
            INSERT INTO vta ({cols_str})
            SELECT {cols_str} FROM staging_vta
            WHERE NOT EXISTS (
                SELECT 1 FROM vta
                WHERE vta.CLAVE_NEGOCIO = staging_vta.CLAVE_NEGOCIO
            )
        """
        cursor.execute(sql_insert_set_based)
        filas_insertadas = cursor.rowcount

        # 9. Limpiar tabla temporal y confirmar la transacción atómica única
        cursor.execute("DROP TABLE IF EXISTS staging_vta;")
        conn.commit()

        logger.info(
            f"VTA INCREMENTAL SET-BASED: Se procesaron {total_registros} registros entrantes (nuevos insertados: {filas_insertadas})."
        )

    except Exception as e:
        conn.rollback()
        logger.exception(
            "Error crítico durante la transacción de VTA incremental. Rollback ejecutado."
        )
        raise e


def cargar_vta_desde_directorio(ruta_directorio: str) -> pd.DataFrame:
    """
    Carga y concatena verticalmente todos los archivos Excel (*.xlsx) contenidos en el directorio
    especificado, ordenados alfabéticamente de forma estable. Incorpora telemetría forense de tiempos.
    No agrega columnas auxiliares.
    """
    t_inicio_directorio = time.perf_counter()

    if not os.path.exists(ruta_directorio) or not os.path.isdir(ruta_directorio):
        logger.warning(
            f"El directorio especificado para VTA particionado no existe o no es válido: {ruta_directorio}"
        )
        return pd.DataFrame()

    archivos = [
        f
        for f in os.listdir(ruta_directorio)
        if f.lower().endswith(".xlsx")
        and not f.startswith("~$")
        and os.path.isfile(os.path.join(ruta_directorio, f))
    ]

    archivos.sort()

    if not archivos:
        logger.warning(
            f"No se encontraron archivos *.xlsx en el directorio de ventas: {ruta_directorio}"
        )
        return pd.DataFrame()

    dfs = []
    for arch in archivos:
        ruta_archivo = os.path.join(ruta_directorio, arch)
        t_inicio_archivo = time.perf_counter()
        df_mes = pd.read_excel(ruta_archivo)
        t_duracion_archivo = time.perf_counter() - t_inicio_archivo

        cant_filas = len(df_mes)
        msg_perf_archivo = (
            f"[PERF_VTA] {arch} -> {t_duracion_archivo:.2f} s | filas={cant_filas}"
        )
        print(msg_perf_archivo)
        logger.info(msg_perf_archivo)

        dfs.append(df_mes)

    t_inicio_concat = time.perf_counter()
    df_consolidado = pd.concat(dfs, ignore_index=True)
    t_duracion_concat = time.perf_counter() - t_inicio_concat

    msg_perf_concat = f"[PERF_VTA] CONCAT -> {t_duracion_concat:.2f} s"
    print(msg_perf_concat)
    logger.info(msg_perf_concat)

    t_duracion_directorio = time.perf_counter() - t_inicio_directorio
    msg_perf_total_dir = f"[PERF_VTA] TOTAL DIRECTORIO -> {t_duracion_directorio:.2f} s"
    print(msg_perf_total_dir)
    logger.info(msg_perf_total_dir)

    return df_consolidado


def inicializar_bd_desde_excel(archivos_dict):
    """Lee los archivos Excel interpretando fechas y estructurando tablas con soporte multi-solapa para Altas."""
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
                t_inicio_lectura_vta = time.perf_counter()
                if os.path.isdir(archivo):
                    df = cargar_vta_desde_directorio(archivo)
                else:
                    df = pd.read_excel(archivo)
                t_duracion_lectura_vta = time.perf_counter() - t_inicio_lectura_vta
                msg_perf_lectura = (
                    f"[PERF_VTA] LECTURA EXCELS -> {t_duracion_lectura_vta:.2f} s"
                )
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
