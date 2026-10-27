import sqlite3
import pandas as pd
import os
import re
import hashlib
import time
from datetime import datetime
from modules.logger import get_logger

# Initialization of the institutional logger for the data access layer
logger = get_logger("database")

DB_PATH = "data/matinal.db"

# VTA se sincroniza automáticamente por versión de archivo.
# Cada AAAA-MM.csv representa la foto completa vigente de ese período físico.
# Si el archivo es nuevo o cambió, el período correspondiente se reemplaza
# íntegramente dentro de una transacción SQLite y se valida antes del COMMIT.


def obtener_conexion():
    """Crea una conexión a SQLite con timeout y modo WAL activado para concurrencia segura."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def sincronizar_parametros_desde_filtros(filtros_globales: dict) -> dict:
    """
    Sincroniza en SQLite.parametros las fechas seleccionadas en los filtros
    globales de Streamlit.

    Fuente de verdad temporal:
    - Dia Matinal: filtros_globales["dia_matinal"]
    - Dia Venta: filtros_globales["dia_venta"]
    - Dia Anterior: filtros_globales["dia_anterior"]
    - Año y Mes: se derivan exclusivamente de Dia Venta.

    La funcion actualiza solo las cinco claves anteriores. Compara primero los
    valores vigentes y no escribe si no existen cambios. La persistencia se
    ejecuta dentro de una unica transaccion SQLite.
    """
    if not isinstance(filtros_globales, dict):
        raise TypeError("filtros_globales debe ser un diccionario.")

    claves_requeridas = ["dia_matinal", "dia_venta", "dia_anterior"]
    faltantes = [
        clave
        for clave in claves_requeridas
        if clave not in filtros_globales
        or filtros_globales[clave] is None
        or str(filtros_globales[clave]).strip() == ""
    ]
    if faltantes:
        raise ValueError(
            "No se pueden sincronizar PARAMETROS. Faltan filtros globales: "
            + ", ".join(faltantes)
        )

    def normalizar_fecha(valor, nombre_campo: str):
        if isinstance(valor, datetime):
            fecha = valor
        else:
            fecha = pd.to_datetime(valor, dayfirst=True, errors="coerce")
        if pd.isna(fecha):
            raise ValueError(
                f"Fecha invalida para {nombre_campo}: {valor!r}. "
                "Se esperaba una fecha o un texto DD/MM/AAAA."
            )
        return fecha

    fecha_matinal = normalizar_fecha(filtros_globales["dia_matinal"], "dia_matinal")
    fecha_venta = normalizar_fecha(filtros_globales["dia_venta"], "dia_venta")
    fecha_anterior = normalizar_fecha(filtros_globales["dia_anterior"], "dia_anterior")

    valores_objetivo = {
        "Año": str(int(fecha_venta.year)),
        "Mes": str(int(fecha_venta.month)),
        "Dia Matinal": fecha_matinal.strftime("%d/%m/%Y"),
        "Dia Venta": fecha_venta.strftime("%d/%m/%Y"),
        "Dia Anterior": fecha_anterior.strftime("%d/%m/%Y"),
    }

    conn = obtener_conexion()
    try:
        cursor = conn.cursor()
        tabla_existe = cursor.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type='table' AND LOWER(name)='parametros'
            LIMIT 1;
            """
        ).fetchone()

        if tabla_existe is None:
            cursor.execute(
                """
                CREATE TABLE parametros (
                    PARAMETRO TEXT PRIMARY KEY,
                    VALOR TEXT
                );
                """
            )
        else:
            columnas = [
                str(fila[1]).strip().upper()
                for fila in cursor.execute("PRAGMA table_info(parametros);").fetchall()
            ]
            requeridas = {"PARAMETRO", "VALOR"}
            if not requeridas.issubset(set(columnas)):
                raise ValueError(
                    "La tabla parametros no cumple el contrato requerido. "
                    f"Columnas encontradas: {columnas}."
                )

        filas_actuales = cursor.execute(
            "SELECT PARAMETRO, VALOR FROM parametros;"
        ).fetchall()
        valores_actuales = {
            str(parametro).strip(): "" if valor is None else str(valor).strip()
            for parametro, valor in filas_actuales
        }

        cambios = {
            parametro: {
                "anterior": valores_actuales.get(parametro),
                "nuevo": valor,
            }
            for parametro, valor in valores_objetivo.items()
            if valores_actuales.get(parametro) != valor
        }

        if not cambios:
            logger.info(
                "PARAMETROS: los filtros globales coinciden con SQLite. "
                "No se realizaron escrituras."
            )
            return {
                "actualizado": False,
                "cambios": {},
                "valores": valores_objetivo,
            }

        try:
            cursor.execute("BEGIN IMMEDIATE;")
            for parametro, valor in valores_objetivo.items():
                cursor.execute(
                    "UPDATE parametros SET VALOR=? WHERE PARAMETRO=?;",
                    (valor, parametro),
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        "INSERT INTO parametros (PARAMETRO, VALOR) VALUES (?, ?);",
                        (parametro, valor),
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        logger.info(
            "PARAMETROS sincronizados desde filtros globales: "
            + ", ".join(
                f"{parametro}={detalle['nuevo']}"
                for parametro, detalle in cambios.items()
            )
        )
        return {
            "actualizado": True,
            "cambios": cambios,
            "valores": valores_objetivo,
        }
    except Exception:
        logger.exception(
            "Error al sincronizar la tabla parametros desde filtros globales."
        )
        raise
    finally:
        conn.close()


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
        ("idx_vta_periodo_archivo", "PeriodoArchivo"),
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


def _normalizar_fechas_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza columnas de fecha con el mismo contrato usado por SQLite."""
    resultado = df.copy()
    for col in resultado.columns:
        col_l = str(col).strip().lower()
        if any(k in col_l for k in ["fecha", "dia", "date"]):
            s = (
                resultado[col]
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
                dt.loc[mask_na] = pd.to_datetime(s[mask_na], errors="coerce")
            resultado[col] = dt.dt.strftime("%Y-%m-%d")
    return resultado


def _periodo_desde_nombre_csv(nombre_archivo: str) -> str:
    """Extrae AAAA-MM de un archivo mensual llamado AAAA-MM.csv."""
    nombre = os.path.basename(str(nombre_archivo)).strip()
    coincidencia = re.fullmatch(
        r"(\d{4}-(?:0[1-9]|1[0-2]))\.csv", nombre, re.IGNORECASE
    )
    if coincidencia is None:
        raise ValueError(
            "Archivo VTA mensual inválido. Se esperaba AAAA-MM.csv y se recibió: "
            f"{nombre}."
        )
    return coincidencia.group(1)


def _listar_csv_vta(ruta_directorio: str) -> dict:
    """Devuelve {periodo: ruta} y rechaza nombres o períodos duplicados."""
    archivos = {}
    for nombre in sorted(os.listdir(ruta_directorio)):
        ruta = os.path.join(ruta_directorio, nombre)
        if (
            not nombre.lower().endswith(".csv")
            or nombre.startswith("~$")
            or not os.path.isfile(ruta)
        ):
            continue
        periodo = _periodo_desde_nombre_csv(nombre)
        if periodo in archivos:
            raise ValueError(f"Existe más de un CSV de VTA para el período {periodo}.")
        archivos[periodo] = ruta
    return archivos


def _leer_csv_vta_mensual(ruta_archivo: str, periodo: str) -> pd.DataFrame:
    """Lee un CSV mensual Gescom y agrega su período físico de procedencia."""
    if os.path.getsize(ruta_archivo) == 0:
        raise ValueError(f"El archivo VTA está vacío: {ruta_archivo}")
    df = pd.read_csv(
        ruta_archivo,
        sep=";",
        encoding="latin1",
        engine="c",
        dtype=str,
    )
    df.columns = [str(col).strip() for col in df.columns]
    if "PeriodoArchivo" in df.columns:
        df = df.drop(columns=["PeriodoArchivo"])
    df["PeriodoArchivo"] = periodo
    return _normalizar_fechas_dataframe(df)


def _tabla_vta_tiene_periodo_archivo(conn) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name)='vta';"
    )
    if cursor.fetchone() is None:
        return False
    cursor.execute("PRAGMA table_info(vta);")
    return "PeriodoArchivo" in [fila[1] for fila in cursor.fetchall()]


def _validar_esquema_vta_incremental(conn, df: pd.DataFrame):
    """Exige igualdad exacta entre CSV mensual y tabla vta persistida."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(vta);")
    columnas_sql = [fila[1] for fila in cursor.fetchall()]
    columnas_df = list(df.columns)
    faltantes = [col for col in columnas_sql if col not in columnas_df]
    extras = [col for col in columnas_df if col not in columnas_sql]
    if faltantes or extras:
        raise ValueError(
            "El esquema del CSV mensual no coincide con SQLite.vta. "
            f"Faltantes en CSV: {faltantes}. Extras en CSV: {extras}."
        )
    return columnas_sql


def _hash_archivo_sha256(ruta_archivo: str, bloque: int = 1024 * 1024) -> str:
    """Calcula SHA-256 del archivo físico sin cargarlo completo en memoria."""
    digest = hashlib.sha256()
    with open(ruta_archivo, "rb") as archivo:
        while True:
            contenido = archivo.read(bloque)
            if not contenido:
                break
            digest.update(contenido)
    return digest.hexdigest()


def _crear_control_versiones_vta(conn):
    """Crea el catálogo técnico de versiones físicas de los CSV mensuales."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vta_periodos_control (
            PeriodoArchivo TEXT PRIMARY KEY,
            NombreArchivo TEXT NOT NULL,
            RutaArchivo TEXT NOT NULL,
            FechaModificacionNs INTEGER NOT NULL,
            TamanoBytes INTEGER NOT NULL,
            HashArchivo TEXT NOT NULL,
            CantidadFilas INTEGER NOT NULL,
            PesoKgTotal REAL NOT NULL,
            FechaCargaSistema TEXT NOT NULL
        );
        """
    )


def _version_archivo_vta(ruta_archivo: str) -> dict:
    """Obtiene metadatos baratos de un CSV mensual."""
    stat = os.stat(ruta_archivo)
    return {
        "nombre": os.path.basename(ruta_archivo),
        "ruta": os.path.abspath(ruta_archivo),
        "mtime_ns": int(stat.st_mtime_ns),
        "tamano": int(stat.st_size),
    }


def _peso_total_vta(df: pd.DataFrame) -> float:
    """Normaliza PesoKg solo para conciliación técnica de la carga mensual."""
    if df is None or df.empty or "PesoKg" not in df.columns:
        return 0.0
    serie = (
        df["PesoKg"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.replace(" ", "", regex=False)
    )
    ambos = serie.str.contains(",", regex=False) & serie.str.contains(".", regex=False)
    serie = serie.where(
        ~ambos,
        serie.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    solo_coma = serie.str.contains(",", regex=False) & ~serie.str.contains(
        ".", regex=False
    )
    serie = serie.where(~solo_coma, serie.str.replace(",", ".", regex=False))
    return float(pd.to_numeric(serie, errors="coerce").fillna(0.0).sum())


def _detectar_periodos_vta_modificados(conn, archivos_por_periodo: dict) -> list:
    """
    Detecta archivos nuevos o modificados.

    Primero compara mtime en nanosegundos y tamaño. Solo calcula SHA-256 si esos
    metadatos cambiaron o si el período todavía no posee control persistido.
    """
    _crear_control_versiones_vta(conn)
    controles = {
        fila[0]: {
            "mtime_ns": int(fila[1]),
            "tamano": int(fila[2]),
            "hash": str(fila[3]),
        }
        for fila in conn.execute(
            """
            SELECT PeriodoArchivo, FechaModificacionNs, TamanoBytes, HashArchivo
            FROM vta_periodos_control;
            """
        ).fetchall()
    }
    modificados = []
    for periodo, ruta in archivos_por_periodo.items():
        version = _version_archivo_vta(ruta)
        control = controles.get(periodo)
        if control is None:
            version["hash"] = _hash_archivo_sha256(ruta)
            modificados.append((periodo, ruta, version, "SIN_CONTROL"))
            continue
        mismos_metadatos = (
            control["mtime_ns"] == version["mtime_ns"]
            and control["tamano"] == version["tamano"]
        )
        if mismos_metadatos:
            continue
        version["hash"] = _hash_archivo_sha256(ruta)
        if version["hash"] != control["hash"]:
            modificados.append((periodo, ruta, version, "CONTENIDO_MODIFICADO"))
        else:
            # El contenido es idéntico. Se actualizan únicamente mtime/ruta/tamaño.
            conn.execute(
                """
                UPDATE vta_periodos_control
                SET NombreArchivo=?, RutaArchivo=?, FechaModificacionNs=?, TamanoBytes=?
                WHERE PeriodoArchivo=?;
                """,
                (
                    version["nombre"],
                    version["ruta"],
                    version["mtime_ns"],
                    version["tamano"],
                    periodo,
                ),
            )
            logger.info(
                f"[VTA_INCREMENTAL] {periodo}: cambió el metadato físico, "
                "pero el hash es idéntico. No se recarga."
            )
    conn.commit()
    return modificados


def sincronizar_vta_incremental(
    conn,
    ruta_directorio: str,
    periodos_actualizar=None,
) -> dict:
    """
    Sincroniza automáticamente VTA por versión física de cada AAAA-MM.csv.

    Reglas:
    - Cada CSV mensual es la foto completa vigente de su PeriodoArchivo.
    - Los archivos sin cambios no se leen ni se escriben nuevamente.
    - Un archivo nuevo o modificado reemplaza íntegramente su período.
    - La sustitución se valida por filas y PesoKg antes del COMMIT.
    - periodos_actualizar se conserva solo por compatibilidad y se ignora.
    """
    if not os.path.isdir(ruta_directorio):
        raise ValueError(
            f"El directorio de VTA no existe o no es válido: {ruta_directorio}"
        )
    archivos_por_periodo = _listar_csv_vta(ruta_directorio)
    if not archivos_por_periodo:
        raise ValueError(
            f"No se encontraron CSV mensuales de VTA en: {ruta_directorio}"
        )
    if periodos_actualizar:
        logger.warning(
            "[VTA_INCREMENTAL] El parámetro periodos_actualizar está obsoleto y "
            "se ignora. La detección de versiones es automática."
        )

    carga_inicial = not _tabla_vta_tiene_periodo_archivo(conn)
    if carga_inicial:
        t0 = time.perf_counter()
        logger.warning(
            "[VTA_INCREMENTAL] Inicialización completa requerida. "
            "Se cargarán todos los CSV y se incorporará PeriodoArchivo."
        )
        bloques = []
        versiones = {}
        for periodo, ruta in archivos_por_periodo.items():
            df_mes = _leer_csv_vta_mensual(ruta, periodo)
            bloques.append(df_mes)
            version = _version_archivo_vta(ruta)
            version["hash"] = _hash_archivo_sha256(ruta)
            version["filas"] = int(len(df_mes))
            version["peso"] = _peso_total_vta(df_mes)
            versiones[periodo] = version
            logger.info(
                f"[VTA_INCREMENTAL] Inicialización {periodo}: "
                f"{len(df_mes)} filas leídas."
            )
        df_total = pd.concat(bloques, ignore_index=True)
        df_total.to_sql("vta", conn, if_exists="replace", index=False, chunksize=10000)
        _crear_control_versiones_vta(conn)
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for periodo, version in versiones.items():
            conn.execute(
                """
                INSERT OR REPLACE INTO vta_periodos_control (
                    PeriodoArchivo, NombreArchivo, RutaArchivo,
                    FechaModificacionNs, TamanoBytes, HashArchivo,
                    CantidadFilas, PesoKgTotal, FechaCargaSistema
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    periodo,
                    version["nombre"],
                    version["ruta"],
                    version["mtime_ns"],
                    version["tamano"],
                    version["hash"],
                    version["filas"],
                    version["peso"],
                    ahora,
                ),
            )
        recrear_indices_vta_defensivos(conn)
        conn.commit()
        total = int(len(df_total))
        logger.info(
            f"[VTA_INCREMENTAL] Inicialización completa finalizada: "
            f"{total} filas, {len(archivos_por_periodo)} períodos, "
            f"{time.perf_counter() - t0:.2f} s."
        )
        return {
            "modo": "INICIAL_COMPLETA",
            "periodos": list(archivos_por_periodo),
            "filas_insertadas": total,
            "filas_eliminadas": 0,
            "total_final": total,
        }

    modificados = _detectar_periodos_vta_modificados(conn, archivos_por_periodo)
    if not modificados:
        total = int(conn.execute("SELECT COUNT(*) FROM vta;").fetchone()[0])
        logger.info(
            "[VTA_INCREMENTAL] Ningún CSV mensual cambió. SQLite.vta no fue "
            f"modificada. Total vigente: {total} filas."
        )
        return {
            "modo": "SIN_CAMBIOS",
            "periodos": [],
            "filas_insertadas": 0,
            "filas_eliminadas": 0,
            "total_final": total,
        }

    datos_periodos = {}
    versiones = {}
    columnas_sql = None
    for periodo, ruta, version, motivo in modificados:
        df_mes = _leer_csv_vta_mensual(ruta, periodo)
        columnas_actuales = _validar_esquema_vta_incremental(conn, df_mes)
        if columnas_sql is None:
            columnas_sql = columnas_actuales
        datos_periodos[periodo] = df_mes[columnas_sql].copy()
        version["filas"] = int(len(df_mes))
        version["peso"] = _peso_total_vta(df_mes)
        versiones[periodo] = version
        logger.info(
            f"[VTA_INCREMENTAL] Detectado {periodo}: {motivo} | "
            f"filas={version['filas']} | PesoKg={version['peso']:.6f}."
        )

    tabla_temporal = "vta_actualizacion_tmp"
    conn.execute(f'DROP TABLE IF EXISTS "{tabla_temporal}";')
    df_actualizacion = pd.concat(
        [datos_periodos[periodo] for periodo in datos_periodos],
        ignore_index=True,
    )
    df_actualizacion.to_sql(
        tabla_temporal, conn, if_exists="replace", index=False, chunksize=10000
    )
    periodos = list(datos_periodos)
    placeholders = ", ".join("?" for _ in periodos)
    columnas_sql_quoted = ", ".join(
        f'"{col.replace(chr(34), chr(34) * 2)}"' for col in columnas_sql
    )
    filas_antes = {
        periodo: int(
            conn.execute(
                "SELECT COUNT(*) FROM vta WHERE PeriodoArchivo = ?;", (periodo,)
            ).fetchone()[0]
        )
        for periodo in periodos
    }
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute(
            f"DELETE FROM vta WHERE PeriodoArchivo IN ({placeholders});",
            tuple(periodos),
        )
        conn.execute(
            f"INSERT INTO vta ({columnas_sql_quoted}) "
            f'SELECT {columnas_sql_quoted} FROM "{tabla_temporal}";'
        )

        for periodo in periodos:
            filas_sql = int(
                conn.execute(
                    "SELECT COUNT(*) FROM vta WHERE PeriodoArchivo=?;", (periodo,)
                ).fetchone()[0]
            )
            df_validacion = pd.read_sql_query(
                "SELECT PesoKg FROM vta WHERE PeriodoArchivo=?;",
                conn,
                params=(periodo,),
            )
            peso_sql = _peso_total_vta(df_validacion)
            filas_origen = versiones[periodo]["filas"]
            peso_origen = versiones[periodo]["peso"]
            if filas_sql != filas_origen or abs(peso_sql - peso_origen) >= 1e-6:
                raise AssertionError(
                    f"Conciliación VTA fallida para {periodo}: "
                    f"origen filas={filas_origen}, SQL filas={filas_sql}; "
                    f"origen PesoKg={peso_origen:.6f}, SQL PesoKg={peso_sql:.6f}."
                )
            version = versiones[periodo]
            conn.execute(
                """
                INSERT INTO vta_periodos_control (
                    PeriodoArchivo, NombreArchivo, RutaArchivo,
                    FechaModificacionNs, TamanoBytes, HashArchivo,
                    CantidadFilas, PesoKgTotal, FechaCargaSistema
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(PeriodoArchivo) DO UPDATE SET
                    NombreArchivo=excluded.NombreArchivo,
                    RutaArchivo=excluded.RutaArchivo,
                    FechaModificacionNs=excluded.FechaModificacionNs,
                    TamanoBytes=excluded.TamanoBytes,
                    HashArchivo=excluded.HashArchivo,
                    CantidadFilas=excluded.CantidadFilas,
                    PesoKgTotal=excluded.PesoKgTotal,
                    FechaCargaSistema=excluded.FechaCargaSistema;
                """,
                (
                    periodo,
                    version["nombre"],
                    version["ruta"],
                    version["mtime_ns"],
                    version["tamano"],
                    version["hash"],
                    version["filas"],
                    version["peso"],
                    ahora,
                ),
            )
            logger.info(
                f"[VTA_INCREMENTAL] Conciliación aprobada {periodo}: "
                f"filas={filas_sql} | PesoKg={peso_sql:.6f}."
            )
        conn.execute(f'DROP TABLE "{tabla_temporal}";')
        conn.commit()
    except Exception:
        conn.rollback()
        conn.execute(f'DROP TABLE IF EXISTS "{tabla_temporal}";')
        conn.commit()
        raise

    filas_eliminadas = int(sum(filas_antes.values()))
    filas_insertadas = int(len(df_actualizacion))
    total_final = int(conn.execute("SELECT COUNT(*) FROM vta;").fetchone()[0])
    logger.info(
        f"[VTA_INCREMENTAL] Períodos reemplazados automáticamente: "
        f"{', '.join(periodos)} | eliminadas={filas_eliminadas} | "
        f"insertadas={filas_insertadas} | total_final={total_final}."
    )
    return {
        "modo": "ACTUALIZACION_AUTOMATICA",
        "periodos": periodos,
        "filas_insertadas": filas_insertadas,
        "filas_eliminadas": filas_eliminadas,
        "total_final": total_final,
    }


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


def _tabla_sql_existe(conn, nombre_tabla: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;",
            (nombre_tabla,),
        ).fetchone()
        is not None
    )


def _columnas_tabla_sql(conn, nombre_tabla: str) -> list:
    nombre_seguro = str(nombre_tabla).replace('"', '""')
    return [
        fila[1]
        for fila in conn.execute(f'PRAGMA table_info("{nombre_seguro}");').fetchall()
    ]


def _columnas_sql_quoted(columnas: list) -> str:
    return ", ".join(
        f'"{columna.replace(chr(34), chr(34) * 2)}"' for columna in columnas
    )


def _crear_control_tp(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tp_periodo_control (
            ControlID INTEGER PRIMARY KEY CHECK (ControlID = 1),
            PeriodoTP TEXT NOT NULL,
            FechaUltimaCarga TEXT NOT NULL,
            HashUltimaCarga TEXT NOT NULL,
            CantidadRegistros INTEGER NOT NULL,
            CantidadTP INTEGER NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tp_versiones_mensuales (
            PeriodoTP TEXT PRIMARY KEY,
            FechaSnapshot TEXT NOT NULL,
            FechaCierreSistema TEXT NOT NULL,
            HashSnapshot TEXT NOT NULL,
            CantidadRegistros INTEGER NOT NULL,
            CantidadTP INTEGER NOT NULL
        );
        """
    )
    conn.commit()


def _validar_foto_tp(df_tp: pd.DataFrame):
    if df_tp is None or df_tp.empty:
        raise ValueError("No se puede procesar una foto TP vacia.")
    requeridas = ["Cliente_id", "CumpleTiendaPerfecta"]
    faltantes = [col for col in requeridas if col not in df_tp.columns]
    if faltantes:
        raise ValueError(
            "TP no cumple el contrato para versionado. Faltan: " + ", ".join(faltantes)
        )
    if df_tp["Cliente_id"].isna().any():
        raise ValueError("TP contiene Cliente_id nulos.")
    if df_tp["Cliente_id"].duplicated().any():
        duplicados = int(df_tp["Cliente_id"].duplicated().sum())
        raise ValueError(f"TP contiene {duplicados} Cliente_id duplicados.")


def _metricas_foto_tp(df_tp: pd.DataFrame) -> tuple:
    _validar_foto_tp(df_tp)
    hash_tp = obtener_hash_dataframe(df_tp)
    registros = int(len(df_tp))
    cantidad_tp = int(
        pd.to_numeric(df_tp["CumpleTiendaPerfecta"], errors="coerce")
        .fillna(0)
        .eq(1)
        .sum()
    )
    return hash_tp, registros, cantidad_tp


def _guardar_snapshot_diario_tp(conn, df_tp: pd.DataFrame, fecha_carga) -> dict:
    """Guarda o reemplaza una unica foto completa por dia del mes vigente."""
    hash_tp, registros, cantidad_tp = _metricas_foto_tp(df_tp)
    periodo = fecha_carga.strftime("%Y-%m")
    fecha_snapshot = fecha_carga.strftime("%Y-%m-%d")
    fecha_sistema = fecha_carga.strftime("%Y-%m-%d %H:%M:%S")

    foto = df_tp.copy()
    foto["PeriodoTP"] = periodo
    foto["FechaSnapshot"] = fecha_snapshot
    foto["FechaCargaSistema"] = fecha_sistema
    foto["HashSnapshot"] = hash_tp

    tabla_tmp = "tp_snapshot_periodo_tmp"
    foto.to_sql(tabla_tmp, conn, if_exists="replace", index=False, chunksize=10000)

    if not _tabla_sql_existe(conn, "tp_snapshot_periodo"):
        foto.head(0).to_sql(
            "tp_snapshot_periodo",
            conn,
            if_exists="replace",
            index=False,
        )

    columnas_destino = _columnas_tabla_sql(conn, "tp_snapshot_periodo")
    columnas_tmp = _columnas_tabla_sql(conn, tabla_tmp)
    if columnas_destino != columnas_tmp:
        conn.execute(f'DROP TABLE IF EXISTS "{tabla_tmp}";')
        conn.commit()
        raise ValueError(
            "Cambio de esquema TP detectado en snapshots diarios. "
            f"Destino={columnas_destino}; carga={columnas_tmp}."
        )

    columnas_sql = _columnas_sql_quoted(columnas_destino)
    try:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute(
            "DELETE FROM tp_snapshot_periodo WHERE FechaSnapshot = ?;",
            (fecha_snapshot,),
        )
        conn.execute(
            f"INSERT INTO tp_snapshot_periodo ({columnas_sql}) "
            f'SELECT {columnas_sql} FROM "{tabla_tmp}";'
        )
        conn.execute(f'DROP TABLE "{tabla_tmp}";')
        conn.commit()
    except Exception:
        conn.rollback()
        conn.execute(f'DROP TABLE IF EXISTS "{tabla_tmp}";')
        conn.commit()
        raise

    guardadas = int(
        conn.execute(
            "SELECT COUNT(*) FROM tp_snapshot_periodo WHERE FechaSnapshot=?;",
            (fecha_snapshot,),
        ).fetchone()[0]
    )
    if guardadas != registros:
        raise AssertionError(
            f"Conciliacion snapshot diario TP fallida para {fecha_snapshot}: "
            f"origen={registros}, guardadas={guardadas}."
        )

    logger.info(
        f"TP_DIARIO: fecha={fecha_snapshot} | periodo={periodo} | "
        f"registros={registros} | TP={cantidad_tp}."
    )
    return {
        "periodo": periodo,
        "fecha_snapshot": fecha_snapshot,
        "registros": registros,
        "tp": cantidad_tp,
        "hash": hash_tp,
    }


def _cerrar_periodo_tp_si_corresponde(conn, periodo_nuevo: str, fecha_carga) -> dict:
    """
    Al comenzar un mes nuevo conserva solo la ultima foto del mes cerrado y
    elimina del area diaria todas las fotos de ese mes.
    """
    _crear_control_tp(conn)
    control = conn.execute(
        """
        SELECT PeriodoTP, FechaUltimaCarga, HashUltimaCarga,
               CantidadRegistros, CantidadTP
        FROM tp_periodo_control
        WHERE ControlID=1;
        """
    ).fetchone()

    if control is None:
        return {"accion": "PRIMER_PERIODO", "periodo_nuevo": periodo_nuevo}

    periodo_anterior = str(control[0])
    if periodo_anterior == periodo_nuevo:
        return {"accion": "MISMO_PERIODO", "periodo": periodo_nuevo}
    if periodo_nuevo < periodo_anterior:
        raise ValueError(
            "No se permite retroceder el periodo TP. "
            f"Control={periodo_anterior}; carga={periodo_nuevo}."
        )
    if not _tabla_sql_existe(conn, "tp_snapshot_periodo"):
        raise ValueError(
            f"No existen snapshots diarios para cerrar {periodo_anterior}."
        )

    ultima_fecha = conn.execute(
        """
        SELECT MAX(FechaSnapshot)
        FROM tp_snapshot_periodo
        WHERE PeriodoTP=?;
        """,
        (periodo_anterior,),
    ).fetchone()[0]
    if not ultima_fecha:
        raise ValueError(
            f"No se encontro una foto diaria para cerrar {periodo_anterior}."
        )

    df_cierre = pd.read_sql(
        """
        SELECT *
        FROM tp_snapshot_periodo
        WHERE PeriodoTP=? AND FechaSnapshot=?;
        """,
        conn,
        params=(periodo_anterior, ultima_fecha),
    )
    if df_cierre.empty:
        raise ValueError(f"La ultima foto de {periodo_anterior} esta vacia.")

    hash_cierre = str(df_cierre["HashSnapshot"].iloc[0])
    registros = int(len(df_cierre))
    cantidad_tp = int(
        pd.to_numeric(df_cierre["CumpleTiendaPerfecta"], errors="coerce")
        .fillna(0)
        .eq(1)
        .sum()
    )
    df_cierre["FechaCierreSistema"] = fecha_carga.strftime("%Y-%m-%d %H:%M:%S")

    tabla_tmp = "tp_snapshot_mensual_tmp"
    df_cierre.to_sql(tabla_tmp, conn, if_exists="replace", index=False, chunksize=10000)
    if not _tabla_sql_existe(conn, "tp_snapshot_mensual"):
        df_cierre.head(0).to_sql(
            "tp_snapshot_mensual",
            conn,
            if_exists="replace",
            index=False,
        )

    columnas_destino = _columnas_tabla_sql(conn, "tp_snapshot_mensual")
    columnas_tmp = _columnas_tabla_sql(conn, tabla_tmp)
    if columnas_destino != columnas_tmp:
        conn.execute(f'DROP TABLE IF EXISTS "{tabla_tmp}";')
        conn.commit()
        raise ValueError(
            "Cambio de esquema TP detectado en cierres mensuales. "
            f"Destino={columnas_destino}; cierre={columnas_tmp}."
        )

    columnas_sql = _columnas_sql_quoted(columnas_destino)
    try:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute(
            "DELETE FROM tp_snapshot_mensual WHERE PeriodoTP=?;",
            (periodo_anterior,),
        )
        conn.execute(
            f"INSERT INTO tp_snapshot_mensual ({columnas_sql}) "
            f'SELECT {columnas_sql} FROM "{tabla_tmp}";'
        )
        conn.execute(
            "DELETE FROM tp_snapshot_periodo WHERE PeriodoTP=?;",
            (periodo_anterior,),
        )
        conn.execute(
            """
            INSERT INTO tp_versiones_mensuales (
                PeriodoTP, FechaSnapshot, FechaCierreSistema,
                HashSnapshot, CantidadRegistros, CantidadTP
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(PeriodoTP) DO UPDATE SET
                FechaSnapshot=excluded.FechaSnapshot,
                FechaCierreSistema=excluded.FechaCierreSistema,
                HashSnapshot=excluded.HashSnapshot,
                CantidadRegistros=excluded.CantidadRegistros,
                CantidadTP=excluded.CantidadTP;
            """,
            (
                periodo_anterior,
                ultima_fecha,
                fecha_carga.strftime("%Y-%m-%d %H:%M:%S"),
                hash_cierre,
                registros,
                cantidad_tp,
            ),
        )
        conn.execute(f'DROP TABLE "{tabla_tmp}";')
        conn.commit()
    except Exception:
        conn.rollback()
        conn.execute(f'DROP TABLE IF EXISTS "{tabla_tmp}";')
        conn.commit()
        raise

    archivadas = int(
        conn.execute(
            "SELECT COUNT(*) FROM tp_snapshot_mensual WHERE PeriodoTP=?;",
            (periodo_anterior,),
        ).fetchone()[0]
    )
    diarias_restantes = int(
        conn.execute(
            "SELECT COUNT(*) FROM tp_snapshot_periodo WHERE PeriodoTP=?;",
            (periodo_anterior,),
        ).fetchone()[0]
    )
    if archivadas != registros or diarias_restantes != 0:
        raise AssertionError(
            f"Cierre TP {periodo_anterior} inconsistente: "
            f"archivadas={archivadas}, esperadas={registros}, "
            f"diarias_restantes={diarias_restantes}."
        )

    logger.info(
        f"TP_CIERRE: periodo={periodo_anterior} | ultima_foto={ultima_fecha} | "
        f"registros={registros} | TP={cantidad_tp} | fotos_diarias_eliminadas."
    )
    return {
        "accion": "PERIODO_CERRADO",
        "periodo_cerrado": periodo_anterior,
        "ultima_foto": ultima_fecha,
        "registros": registros,
        "tp": cantidad_tp,
        "periodo_nuevo": periodo_nuevo,
    }


def _registrar_control_tp(conn, snapshot: dict, fecha_carga):
    _crear_control_tp(conn)
    conn.execute(
        """
        INSERT INTO tp_periodo_control (
            ControlID, PeriodoTP, FechaUltimaCarga, HashUltimaCarga,
            CantidadRegistros, CantidadTP
        )
        VALUES (1, ?, ?, ?, ?, ?)
        ON CONFLICT(ControlID) DO UPDATE SET
            PeriodoTP=excluded.PeriodoTP,
            FechaUltimaCarga=excluded.FechaUltimaCarga,
            HashUltimaCarga=excluded.HashUltimaCarga,
            CantidadRegistros=excluded.CantidadRegistros,
            CantidadTP=excluded.CantidadTP;
        """,
        (
            snapshot["periodo"],
            fecha_carga.strftime("%Y-%m-%d %H:%M:%S"),
            snapshot["hash"],
            snapshot["registros"],
            snapshot["tp"],
        ),
    )
    conn.commit()


def persistir_tp_con_ciclo_snapshots(
    conn, df_tp: pd.DataFrame, fecha_carga=None
) -> dict:
    """
    Flujo TP completo:
    1. Cierra el mes anterior si cambio el periodo.
    2. Reemplaza la foto operativa tp.
    3. Guarda/reemplaza la foto diaria del mes vigente.
    4. Actualiza el control del periodo.
    """
    _validar_foto_tp(df_tp)
    ahora = fecha_carga or datetime.now()
    periodo_nuevo = ahora.strftime("%Y-%m")
    cierre = _cerrar_periodo_tp_si_corresponde(conn, periodo_nuevo, ahora)

    df_tp.to_sql(
        "tp",
        conn,
        if_exists="replace",
        index=False,
        chunksize=10000,
    )
    snapshot = _guardar_snapshot_diario_tp(conn, df_tp, ahora)
    _registrar_control_tp(conn, snapshot, ahora)

    logger.info(
        f"TP_CICLO: periodo={periodo_nuevo} | fecha={snapshot['fecha_snapshot']} | "
        f"cierre={cierre['accion']} | registros={snapshot['registros']} | "
        f"TP={snapshot['tp']}."
    )
    return {"cierre": cierre, "snapshot": snapshot}


def _cargar_tp_desde_excel(archivo) -> pd.DataFrame:
    """Carga exclusivamente TP_DIA_VENTA y adapta el contrato para core_tp."""
    xls = pd.ExcelFile(archivo)
    hoja_detectada = None
    fila_encabezado = None

    for hoja in xls.sheet_names:
        muestra = pd.read_excel(
            archivo,
            sheet_name=hoja,
            header=None,
            nrows=50,
        )
        for indice, fila in muestra.iterrows():
            encabezados = {
                str(valor).strip() for valor in fila.tolist() if pd.notna(valor)
            }
            if {"Cliente", "CumpleTiendaPerfecta"}.issubset(encabezados):
                hoja_detectada = hoja
                fila_encabezado = indice
                break
        if hoja_detectada is not None:
            break

    if hoja_detectada is None:
        raise ValueError(
            "No se reconoció el contrato de TP_DIA_VENTA. "
            "El archivo debe contener Cliente y CumpleTiendaPerfecta."
        )

    df_origen = pd.read_excel(
        archivo,
        sheet_name=hoja_detectada,
        header=fila_encabezado,
    )
    df_origen.columns = [str(columna).strip() for columna in df_origen.columns]

    columnas_requeridas = [
        "Cliente",
        "Razon_Social",
        "Direccion",
        "Vendedor_ID",
        "Tipologia",
        "SubCanal",
        "Segmento",
        "porcentajePortafolio",
        "CumplimientoEstandar",
        "rackadecuado",
        "rackposicion",
        "planograma",
        "preciosvisibles",
        "rotacionpreventiva",
        "Puntuacion",
        "TiendaPerfecta",
        "SupOk",
        "ultimafechacenso",
        "frecuencia",
        "SubCanalTiendaPerfecta",
        "FechaUltimaValidacionSupervisorJDRPromotor",
        "Usuario",
        "EstandarSOD",
        "PuntajeSOD",
        "CumpleTiendaPerfecta",
    ]
    faltantes = [
        columna for columna in columnas_requeridas if columna not in df_origen.columns
    ]
    if faltantes:
        raise ValueError(
            "TP_DIA_VENTA no cumple el contrato requerido. "
            "Faltan columnas: " + ", ".join(faltantes)
        )

    cumple_tp = (
        pd.to_numeric(df_origen["CumpleTiendaPerfecta"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    valores_invalidos = sorted(set(cumple_tp.unique().tolist()) - {0, 1})
    if valores_invalidos:
        raise ValueError(
            "CumpleTiendaPerfecta solo admite 0 o 1. "
            f"Valores inválidos: {valores_invalidos}."
        )

    df = pd.DataFrame(
        {
            "Cliente_id": df_origen["Cliente"],
            "Vendedor": df_origen["Vendedor_ID"],
            "Razon Social": df_origen["Razon_Social"],
            "Direccion": df_origen["Direccion"],
            "Tipología": df_origen["Tipologia"],
            "SubCanal": df_origen["SubCanal"],
            "Taxonomía": df_origen["Segmento"],
            "% De cumplimiento de surtido ideal": df_origen["porcentajePortafolio"],
            "Cumplimiento    \nEstandar": df_origen["CumplimientoEstandar"],
            "Rack Adecuado": df_origen["rackadecuado"],
            "Rack en Posicion Correcta": df_origen["rackposicion"],
            "Planograma": df_origen["planograma"],
            "Precios visibles y correctos": df_origen["preciosvisibles"],
            "Rotación\nPreventiva": df_origen["rotacionpreventiva"],
            "Puntuación": df_origen["Puntuacion"],
            "Tienda \nPerfecta": cumple_tp.map({1: "SI", 0: "NO"}),
            "Sup\nok": df_origen["SupOk"],
            "Ult Fecha Censo": df_origen["ultimafechacenso"],
            "Frecuencia": df_origen["frecuencia"],
            "Subcanal Tienda Perfecta": df_origen["SubCanalTiendaPerfecta"],
            "Fecha Ultima Validacion Supervisor/JDR/Promotor": df_origen[
                "FechaUltimaValidacionSupervisorJDRPromotor"
            ],
            "Usuario": df_origen["Usuario"],
            "Estandar \nSOD": df_origen["EstandarSOD"],
            "Puntaje \nSOD": df_origen["PuntajeSOD"],
            "TiendaPerfecta_Tecnica": df_origen["TiendaPerfecta"],
            "CumpleTiendaPerfecta": cumple_tp,
        }
    )

    df["Cliente_id"] = pd.to_numeric(df["Cliente_id"], errors="coerce").astype("Int64")
    df["Vendedor"] = pd.to_numeric(df["Vendedor"], errors="coerce").astype("Int64")
    df["Puntuación"] = pd.to_numeric(df["Puntuación"], errors="coerce").fillna(0.0)

    if df["Cliente_id"].isna().any():
        cantidad_invalidos = int(df["Cliente_id"].isna().sum())
        raise ValueError(
            "TP_DIA_VENTA contiene clientes sin identificador numérico válido: "
            f"{cantidad_invalidos} filas."
        )
    if df["Cliente_id"].duplicated().any():
        cantidad_duplicados = int(df["Cliente_id"].duplicated().sum())
        raise ValueError(
            "TP_DIA_VENTA contiene Cliente_id duplicados: "
            f"{cantidad_duplicados} filas duplicadas."
        )

    logger.info(
        f"TP_DIA_VENTA cargada desde hoja '{hoja_detectada}' "
        f"({len(df)} registros; TP validadas={int(cumple_tp.sum())})."
    )
    return df


CHKIN_COLUMNAS = [
    "Codigo Cliente",
    "Cliente",
    "Codigo Empleado",
    "Supervisor",
    "Coordenadas Check-in",
    "Coordenadas Check-out",
    "Fecha Check-in",
    "Fecha Check-out",
    "Motivo Invalidez Check-in",
    "Motivo Invalidez Check-out",
    "Existe Carga",
    "Tiempo en PDV",
    "Valido",
]


def _normalizar_timestamp_chkin(serie: pd.Series, nombre_columna: str) -> pd.Series:
    """Normaliza un timestamp CHKIN conservando microsegundos para la clave natural."""
    fechas = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    invalidas = fechas.isna()
    if invalidas.any():
        ejemplos = serie.loc[invalidas].head(5).tolist()
        raise ValueError(
            f"CHKIN contiene {int(invalidas.sum())} valores invalidos en "
            f"'{nombre_columna}'. Ejemplos: {ejemplos}."
        )
    return fechas.dt.strftime("%Y-%m-%d %H:%M:%S.%f")


def _leer_chkin_desde_excel(archivo) -> pd.DataFrame:
    """Lee la hoja Data de CHKIN y valida el contrato RAW antes de persistir."""
    xls = pd.ExcelFile(archivo)
    if "Data" not in xls.sheet_names:
        raise ValueError(
            "CHKIN.xlsx no contiene la hoja requerida 'Data'. "
            f"Hojas encontradas: {xls.sheet_names}."
        )
    df = pd.read_excel(archivo, sheet_name="Data", dtype=object)
    df.columns = [str(columna).strip() for columna in df.columns]
    faltantes = [columna for columna in CHKIN_COLUMNAS if columna not in df.columns]
    extras = [columna for columna in df.columns if columna not in CHKIN_COLUMNAS]
    if faltantes or extras:
        raise ValueError(
            "CHKIN.xlsx no cumple el contrato de columnas. "
            f"Faltantes: {faltantes}. Extras: {extras}."
        )
    df = df[CHKIN_COLUMNAS].copy()
    if df.empty:
        raise ValueError("CHKIN.xlsx no contiene registros para persistir.")
    for columna in CHKIN_COLUMNAS:
        if columna not in ("Fecha Check-in", "Fecha Check-out"):
            df[columna] = df[columna].apply(
                lambda valor: (
                    None
                    if pd.isna(valor) or str(valor).strip() == ""
                    else str(valor).strip()
                )
            )
    df["Fecha Check-in"] = _normalizar_timestamp_chkin(
        df["Fecha Check-in"], "Fecha Check-in"
    )
    df["Fecha Check-out"] = _normalizar_timestamp_chkin(
        df["Fecha Check-out"], "Fecha Check-out"
    )
    claves_nulas = df["Codigo Cliente"].isna() | df["Fecha Check-in"].isna()
    if claves_nulas.any():
        raise ValueError(
            "CHKIN contiene filas sin Codigo Cliente o Fecha Check-in: "
            f"{int(claves_nulas.sum())}."
        )
    clave = ["Codigo Cliente", "Fecha Check-in"]
    duplicadas = df.duplicated(subset=clave, keep=False)
    if duplicadas.any():
        muestra = df.loc[duplicadas, clave].head(10).to_dict("records")
        raise ValueError(
            "CHKIN contiene claves duplicadas para Codigo Cliente + Fecha Check-in. "
            f"Filas involucradas: {int(duplicadas.sum())}. Muestra: {muestra}."
        )
    return df


def _crear_tabla_chkin(conn):
    """Crea la tabla historica CHKIN y su clave natural institucional."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chkin (
            "Codigo Cliente" TEXT NOT NULL,
            "Cliente" TEXT,
            "Codigo Empleado" TEXT,
            "Supervisor" TEXT,
            "Coordenadas Check-in" TEXT,
            "Coordenadas Check-out" TEXT,
            "Fecha Check-in" TEXT NOT NULL,
            "Fecha Check-out" TEXT,
            "Motivo Invalidez Check-in" TEXT,
            "Motivo Invalidez Check-out" TEXT,
            "Existe Carga" TEXT,
            "Tiempo en PDV" TEXT,
            "Valido" TEXT,
            PRIMARY KEY ("Codigo Cliente", "Fecha Check-in")
        );
        """
    )
    columnas_sql = _columnas_tabla_sql(conn, "chkin")
    if columnas_sql != CHKIN_COLUMNAS:
        raise ValueError(
            "La tabla SQLite.chkin no cumple el contrato institucional. "
            f"Esperadas={CHKIN_COLUMNAS}; encontradas={columnas_sql}."
        )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_chkin_fecha_checkin ON chkin("Fecha Check-in");'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_chkin_empleado ON chkin("Codigo Empleado");'
    )


def sincronizar_chkin_incremental(conn, archivo) -> dict:
    """
    Incorpora solamente visitas CHKIN ausentes en SQLite.

    La clave natural es Codigo Cliente + Fecha Check-in completa. Las filas ya
    persistidas no se actualizan ni se eliminan, aunque desaparezcan del Excel.
    El periodo de la visita no condiciona la carga.
    """
    if not os.path.isfile(archivo):
        raise ValueError(f"El archivo CHKIN no existe o no es valido: {archivo}")
    t0 = time.perf_counter()
    df = _leer_chkin_desde_excel(archivo)
    _crear_tabla_chkin(conn)
    columnas_sql = _columnas_sql_quoted(CHKIN_COLUMNAS)
    placeholders = ", ".join("?" for _ in CHKIN_COLUMNAS)
    sentencia = f"INSERT OR IGNORE INTO chkin ({columnas_sql}) VALUES ({placeholders});"
    filas = [
        tuple(None if pd.isna(valor) else valor for valor in fila)
        for fila in df.itertuples(index=False, name=None)
    ]
    total_antes = int(conn.execute("SELECT COUNT(*) FROM chkin;").fetchone()[0])
    try:
        conn.execute("BEGIN IMMEDIATE;")
        conn.executemany(sentencia, filas)
        total_despues = int(conn.execute("SELECT COUNT(*) FROM chkin;").fetchone()[0])
        insertadas = total_despues - total_antes
        if insertadas < 0 or insertadas > len(df):
            raise AssertionError(
                "Conciliacion CHKIN invalida: "
                f"antes={total_antes}, despues={total_despues}, origen={len(df)}."
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    resultado = {
        "filas_origen": int(len(df)),
        "filas_insertadas": int(insertadas),
        "filas_ya_existentes": int(len(df) - insertadas),
        "total_final": int(total_despues),
    }
    logger.info(
        "[CHKIN_INCREMENTAL] "
        f"origen={resultado['filas_origen']} | "
        f"insertadas={resultado['filas_insertadas']} | "
        f"ya_existentes={resultado['filas_ya_existentes']} | "
        f"total_final={resultado['total_final']} | "
        f"duracion={time.perf_counter() - t0:.2f} s."
    )
    return resultado


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
            elif nombre_tabla.lower() == "chkin":
                resultado_chkin = sincronizar_chkin_incremental(conn, archivo)
                logger.info(
                    f"[CHKIN_INCREMENTAL] Resultado de sincronizacion: {resultado_chkin}"
                )
                continue
            elif nombre_tabla.lower() == "tp":
                logger.warning(f"DETECTADA CARGA ESPECIAL TP: {nombre_tabla}")
                df = _cargar_tp_desde_excel(archivo)
            elif nombre_tabla.lower() == "vta" and os.path.isdir(archivo):
                resultado_vta = sincronizar_vta_incremental(
                    conn,
                    archivo,
                )
                logger.info(
                    f"[VTA_INCREMENTAL] Resultado de sincronización: {resultado_vta}"
                )
                continue
            elif nombre_tabla.lower() == "vta":
                # Compatibilidad defensiva para una fuente VTA no particionada.
                t_inicio_lectura_vta = time.perf_counter()
                if str(archivo).lower().endswith(".parquet"):
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
                elif nombre_tabla.lower() == "tp":
                    resultado_tp = persistir_tp_con_ciclo_snapshots(
                        conn,
                        df,
                        datetime.now(),
                    )
                    logger.info(f"TP_CICLO: resultado {resultado_tp}")
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
