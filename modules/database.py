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


def asegurar_tabla_maestro_tp():
    """
    Crea la tabla maestro_tp si todavía no existe.

    Contrato:
        Anio             INTEGER
        Mes              INTEGER
        Taxonomia        TEXT
        Obj_TP_Pepsico   INTEGER

    Clave única lógica y física:
        Anio + Mes + Taxonomia
    """
    conn = obtener_conexion()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS maestro_tp (
                Anio INTEGER NOT NULL,
                Mes INTEGER NOT NULL CHECK (Mes BETWEEN 1 AND 12),
                Taxonomia TEXT NOT NULL CHECK (Taxonomia IN ('A', 'B', 'C', 'D')),
                Obj_TP_Pepsico INTEGER NOT NULL DEFAULT 0
                    CHECK (Obj_TP_Pepsico >= 0),
                PRIMARY KEY (Anio, Mes, Taxonomia)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def guardar_maestro_tp(df: pd.DataFrame, anio, mes):
    """
    Valida y reemplaza de forma transaccional únicamente el período indicado
    dentro de maestro_tp, preservando el resto del histórico.

    Devuelve:
        (True, mensaje) si la operación se confirma.
        (False, mensaje) ante un error de contrato o persistencia.
    """
    columnas = ["Taxonomia", "Obj_TP_Pepsico"]
    faltantes = [col for col in columnas if col not in df.columns]
    if faltantes:
        return False, (
            "Faltan columnas obligatorias para maestro_tp: " + ", ".join(faltantes)
        )

    try:
        anio_int = int(float(anio))
        mes_int = int(float(mes))
    except (TypeError, ValueError):
        return False, "Anio y Mes deben ser valores numéricos válidos."

    if mes_int < 1 or mes_int > 12:
        return False, "Mes debe estar comprendido entre 1 y 12."

    trabajo = df[columnas].copy()
    trabajo["Taxonomia"] = trabajo["Taxonomia"].astype("string").str.strip().str.upper()
    trabajo["Obj_TP_Pepsico"] = pd.to_numeric(
        trabajo["Obj_TP_Pepsico"], errors="coerce"
    )

    if trabajo["Taxonomia"].isna().any():
        return False, "Taxonomia contiene valores nulos."
    if not trabajo["Taxonomia"].isin(["A", "B", "C", "D"]).all():
        invalidas = sorted(
            trabajo.loc[
                ~trabajo["Taxonomia"].isin(["A", "B", "C", "D"]),
                "Taxonomia",
            ]
            .astype(str)
            .unique()
            .tolist()
        )
        return False, f"Taxonomías no válidas: {invalidas}."
    if trabajo["Taxonomia"].duplicated().any():
        duplicadas = sorted(
            trabajo.loc[trabajo["Taxonomia"].duplicated(False), "Taxonomia"]
            .astype(str)
            .unique()
            .tolist()
        )
        return False, f"Taxonomías duplicadas: {duplicadas}."
    if set(trabajo["Taxonomia"].tolist()) != {"A", "B", "C", "D"}:
        return False, "El período debe contener exactamente las taxonomías A, B, C y D."
    if trabajo["Obj_TP_Pepsico"].isna().any():
        return False, "Obj_TP_Pepsico contiene valores vacíos o no numéricos."
    if (trabajo["Obj_TP_Pepsico"] < 0).any():
        return False, "Obj_TP_Pepsico no puede contener valores negativos."
    if not (trabajo["Obj_TP_Pepsico"] % 1 == 0).all():
        return False, "Obj_TP_Pepsico debe expresarse como cantidad entera de clientes."

    trabajo["Obj_TP_Pepsico"] = trabajo["Obj_TP_Pepsico"].astype(int)
    trabajo["Anio"] = anio_int
    trabajo["Mes"] = mes_int
    trabajo = trabajo[["Anio", "Mes", "Taxonomia", "Obj_TP_Pepsico"]]
    trabajo = trabajo.sort_values("Taxonomia").reset_index(drop=True)

    conn = obtener_conexion()
    try:
        conn.execute("BEGIN")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS maestro_tp (
                Anio INTEGER NOT NULL,
                Mes INTEGER NOT NULL CHECK (Mes BETWEEN 1 AND 12),
                Taxonomia TEXT NOT NULL CHECK (Taxonomia IN ('A', 'B', 'C', 'D')),
                Obj_TP_Pepsico INTEGER NOT NULL DEFAULT 0
                    CHECK (Obj_TP_Pepsico >= 0),
                PRIMARY KEY (Anio, Mes, Taxonomia)
            )
            """
        )
        conn.execute(
            "DELETE FROM maestro_tp WHERE Anio = ? AND Mes = ?",
            (anio_int, mes_int),
        )
        conn.executemany(
            """
            INSERT INTO maestro_tp
                (Anio, Mes, Taxonomia, Obj_TP_Pepsico)
            VALUES (?, ?, ?, ?)
            """,
            list(trabajo.itertuples(index=False, name=None)),
        )
        conn.commit()
        return (
            True,
            f"Maestro TP guardado para {mes_int:02d}/{anio_int}: "
            f"{len(trabajo)} taxonomías.",
        )
    except Exception as exc:
        conn.rollback()
        return False, f"Error al guardar maestro_tp: {exc}"
    finally:
        conn.close()


def asegurar_tablas_objetivos_tp():
    """Crea las tablas congeladas de objetivos TP sin alterar maestro_tp."""
    conn = obtener_conexion()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS objetivos_tp_periodo (
                Anio INTEGER NOT NULL,
                Mes INTEGER NOT NULL CHECK (Mes BETWEEN 1 AND 12),
                Taxonomia TEXT NOT NULL CHECK (Taxonomia IN ('A','B','C','D')),
                Obj_TP_Pepsico INTEGER NOT NULL CHECK (Obj_TP_Pepsico >= 0),
                Factor_Ajuste REAL NOT NULL,
                Objetivo_Base_Ajustado INTEGER NOT NULL CHECK (Objetivo_Base_Ajustado >= 0),
                Adicional_Global INTEGER NOT NULL DEFAULT 0 CHECK (Adicional_Global >= 0),
                Objetivo_Final_Taxonomia INTEGER NOT NULL CHECK (Objetivo_Final_Taxonomia >= 0),
                Potencial_Taxonomia INTEGER NOT NULL CHECK (Potencial_Taxonomia >= 0),
                EstadoSnapshot TEXT NOT NULL,
                FechaGeneracion TEXT NOT NULL,
                FechaModificacion TEXT,
                PRIMARY KEY (Anio, Mes, Taxonomia)
            );

            CREATE TABLE IF NOT EXISTS objetivos_tp_vendedor (
                Anio INTEGER NOT NULL,
                Mes INTEGER NOT NULL CHECK (Mes BETWEEN 1 AND 12),
                CodVendedor INTEGER NOT NULL,
                Vendedor_Snapshot TEXT,
                Supervisor_Snapshot TEXT,
                Taxonomia TEXT NOT NULL CHECK (Taxonomia IN ('A','B','C','D')),
                Clientes_Potenciales_Snapshot INTEGER NOT NULL
                    CHECK (Clientes_Potenciales_Snapshot >= 0),
                Objetivo_Taxonomia_Final INTEGER NOT NULL
                    CHECK (Objetivo_Taxonomia_Final >= 0),
                Obj_TP_Asignado INTEGER NOT NULL CHECK (Obj_TP_Asignado >= 0),
                Obj_TP_Manual INTEGER CHECK (Obj_TP_Manual IS NULL OR Obj_TP_Manual >= 0),
                Motivo_Modificacion TEXT,
                FechaGeneracion TEXT NOT NULL,
                FechaModificacion TEXT,
                PRIMARY KEY (Anio, Mes, CodVendedor, Taxonomia)
            );

            CREATE INDEX IF NOT EXISTS idx_obj_tp_vendedor_periodo
                ON objetivos_tp_vendedor (Anio, Mes);
            CREATE INDEX IF NOT EXISTS idx_obj_tp_vendedor_taxonomia
                ON objetivos_tp_vendedor (Anio, Mes, Taxonomia);
            """
        )
        conn.commit()
    finally:
        conn.close()


def _resolver_columna_tp(columnas, candidatos, etiqueta):
    mapa = {str(c).strip().lower(): c for c in columnas}
    for candidato in candidatos:
        encontrado = mapa.get(str(candidato).strip().lower())
        if encontrado is not None:
            return encontrado
    raise ValueError(
        f"No se encontró la columna {etiqueta}. Candidatos={candidatos}; "
        f"columnas disponibles={list(columnas)}."
    )


def _asignar_entero_con_topes_tp(df, columna_capacidad, objetivo_total):
    """Reparte enteros proporcionalmente, sin exceder capacidad y conciliando el total."""
    resultado = df.copy().reset_index(drop=True)
    resultado[columna_capacidad] = (
        pd.to_numeric(resultado[columna_capacidad], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    objetivo_total = int(objetivo_total)
    capacidad_total = int(resultado[columna_capacidad].sum())
    if capacidad_total < objetivo_total:
        raise ValueError(
            f"Objetivo no factible: objetivo={objetivo_total}, capacidad={capacidad_total}."
        )
    if objetivo_total == 0:
        resultado["Obj_TP_Asignado"] = 0
        return resultado

    peso = resultado[columna_capacidad] / capacidad_total
    teorico = peso * objetivo_total
    asignado = teorico.astype(int)
    asignado = asignado.clip(upper=resultado[columna_capacidad])
    faltan = objetivo_total - int(asignado.sum())

    while faltan > 0:
        capacidad_libre = resultado[columna_capacidad] - asignado
        elegibles = capacidad_libre > 0
        if not elegibles.any():
            raise ValueError(
                f"No existe capacidad suficiente para distribuir {faltan} unidades TP."
            )
        residuos = (teorico - asignado).where(elegibles, -1.0)
        orden = sorted(
            resultado.index[elegibles].tolist(),
            key=lambda i: (
                -float(residuos.loc[i]),
                -int(capacidad_libre.loc[i]),
                int(resultado.loc[i, "CodVendedor"]),
            ),
        )
        progreso = 0
        for i in orden:
            if faltan <= 0:
                break
            if asignado.loc[i] < resultado.loc[i, columna_capacidad]:
                asignado.loc[i] += 1
                faltan -= 1
                progreso += 1
        if progreso == 0:
            raise ValueError("El reparto TP quedó bloqueado sin capacidad marginal.")

    resultado["Obj_TP_Asignado"] = asignado.astype(int)
    return resultado


def _objetivos_base_tp(maestro):
    factores = {"A": 1.20, "B": 1.20, "C": 1.05, "D": 1.05}
    prioridad_empate = {"B": 0, "A": 1, "C": 2, "D": 3}
    trabajo = maestro.copy().sort_values("Taxonomia").reset_index(drop=True)
    trabajo["Factor_Ajuste"] = trabajo["Taxonomia"].map(factores)
    trabajo["Base_Decimal"] = trabajo["Obj_TP_Pepsico"] * trabajo["Factor_Ajuste"]
    trabajo["Objetivo_Base_Ajustado"] = trabajo["Base_Decimal"].astype(int)
    objetivo_entero = int(round(float(trabajo["Base_Decimal"].sum())))
    faltan = objetivo_entero - int(trabajo["Objetivo_Base_Ajustado"].sum())
    trabajo["Resto"] = trabajo["Base_Decimal"] - trabajo["Objetivo_Base_Ajustado"]
    orden = sorted(
        trabajo.index.tolist(),
        key=lambda i: (
            -float(trabajo.loc[i, "Resto"]),
            prioridad_empate[str(trabajo.loc[i, "Taxonomia"])],
        ),
    )
    for i in orden[:faltan]:
        trabajo.loc[i, "Objetivo_Base_Ajustado"] += 1
    return trabajo


def generar_snapshot_objetivos_tp(anio, mes):
    """
    Genera una única vez los objetivos TP congelados.
    A/B reciben +20%; C/D +5%. El adicional para alcanzar +20% global
    se distribuye solo entre C/D según la capacidad libre observada en ese momento.
    """
    anio_int, mes_int = int(float(anio)), int(float(mes))
    asegurar_tablas_objetivos_tp()
    conn = obtener_conexion()
    try:
        existente = conn.execute(
            "SELECT COUNT(*) FROM objetivos_tp_vendedor WHERE Anio=? AND Mes=?",
            (anio_int, mes_int),
        ).fetchone()[0]
        if existente:
            return False, (
                f"El snapshot TP {mes_int:02d}/{anio_int} ya existe. "
                "No se recalculó ni se modificó."
            )

        maestro = pd.read_sql_query(
            """
            SELECT Anio, Mes, Taxonomia, Obj_TP_Pepsico
            FROM maestro_tp
            WHERE Anio=? AND Mes=?
            ORDER BY Taxonomia
            """,
            conn,
            params=(anio_int, mes_int),
        )
        if set(maestro.get("Taxonomia", pd.Series(dtype=str)).astype(str)) != {
            "A",
            "B",
            "C",
            "D",
        }:
            return (
                False,
                "maestro_tp debe contener exactamente A, B, C y D para el período.",
            )
        maestro["Obj_TP_Pepsico"] = pd.to_numeric(
            maestro["Obj_TP_Pepsico"], errors="coerce"
        )
        if maestro["Obj_TP_Pepsico"].isna().any():
            return False, "maestro_tp contiene objetivos no numéricos."
        maestro["Obj_TP_Pepsico"] = maestro["Obj_TP_Pepsico"].astype(int)

        universo = pd.read_sql_query("SELECT * FROM universo", conn)
        if universo.empty:
            return False, "La tabla universo está vacía."
        col_cliente = _resolver_columna_tp(
            universo.columns,
            ["Codigo", "Cliente", "Cliente_id", "Codigo Cliente"],
            "cliente",
        )
        col_vendedor = _resolver_columna_tp(
            universo.columns,
            ["codven", "CodVendedor", "Codigo_Vendedor", "Vendedor"],
            "vendedor",
        )
        col_taxonomia = _resolver_columna_tp(
            universo.columns,
            ["SegmentoClienteCodigo", "Taxonomia", "Taxonomía", "Segmento"],
            "taxonomía",
        )
        col_subramo = next(
            (c for c in universo.columns if str(c).strip().lower() == "subramo"),
            None,
        )
        u = universo[
            [col_cliente, col_vendedor, col_taxonomia]
            + ([col_subramo] if col_subramo else [])
        ].copy()
        if col_subramo:
            sub = u[col_subramo].fillna("").astype(str).str.strip().str.upper()
            u = u[~sub.isin(["EMPLEADOS", "EMPLOYEES"])].copy()
        u["CodVendedor"] = pd.to_numeric(u[col_vendedor], errors="coerce").astype(
            "Int64"
        )
        u["Cliente"] = pd.to_numeric(u[col_cliente], errors="coerce").astype("Int64")
        u["Taxonomia"] = u[col_taxonomia].fillna("").astype(str).str.strip().str.upper()
        u = u.dropna(subset=["CodVendedor", "Cliente"])
        u = u[u["Taxonomia"].isin(["A", "B", "C", "D"])].copy()
        u = u.drop_duplicates(["CodVendedor", "Cliente", "Taxonomia"])
        potencial = u.groupby(["CodVendedor", "Taxonomia"], as_index=False).agg(
            Clientes_Potenciales_Snapshot=("Cliente", "nunique")
        )
        if potencial.empty:
            return False, "No se encontraron clientes potenciales A/B/C/D por vendedor."

        vendedores = pd.read_sql_query("SELECT * FROM maestro_vendedores", conn)
        if not vendedores.empty:
            if "Anio" in vendedores.columns and "Mes" in vendedores.columns:
                vendedores = vendedores[
                    (vendedores["Anio"].astype(str) == str(anio_int))
                    & (vendedores["Mes"].astype(str) == str(mes_int))
                ].copy()
            cv = _resolver_columna_tp(
                vendedores.columns,
                ["Codigo_Vendedor", "CodVendedor", "CodVend"],
                "código vendedor maestro",
            )
            nv = next(
                (c for c in ["Nombre_Vendedor", "Nombre"] if c in vendedores.columns),
                None,
            )
            sv = next(
                (c for c in ["Supervisor", "SUP"] if c in vendedores.columns), None
            )
            vm = pd.DataFrame(
                {
                    "CodVendedor": pd.to_numeric(
                        vendedores[cv], errors="coerce"
                    ).astype("Int64")
                }
            )
            vm["Vendedor_Snapshot"] = (
                vendedores[nv].astype(str).str.strip() if nv else ""
            )
            vm["Supervisor_Snapshot"] = (
                vendedores[sv].astype(str).str.strip() if sv else ""
            )
            vm = vm.dropna(subset=["CodVendedor"]).drop_duplicates("CodVendedor")
            potencial = potencial.merge(vm, on="CodVendedor", how="left")
        else:
            potencial["Vendedor_Snapshot"] = ""
            potencial["Supervisor_Snapshot"] = ""
        potencial[["Vendedor_Snapshot", "Supervisor_Snapshot"]] = potencial[
            ["Vendedor_Snapshot", "Supervisor_Snapshot"]
        ].fillna("")

        base = _objetivos_base_tp(maestro)
        pot_tax = potencial.groupby("Taxonomia", as_index=False)[
            "Clientes_Potenciales_Snapshot"
        ].sum()
        base = base.merge(pot_tax, on="Taxonomia", how="left")
        base["Clientes_Potenciales_Snapshot"] = (
            base["Clientes_Potenciales_Snapshot"].fillna(0).astype(int)
        )
        minimo_global = int(round(float(maestro["Obj_TP_Pepsico"].sum()) * 1.20))
        adicional_total = minimo_global - int(base["Objetivo_Base_Ajustado"].sum())
        if adicional_total < 0:
            adicional_total = 0
        base["Adicional_Global"] = 0
        libres = {}
        for tax in ["C", "D"]:
            fila = base.loc[base["Taxonomia"] == tax].iloc[0]
            libres[tax] = max(
                int(fila["Clientes_Potenciales_Snapshot"])
                - int(fila["Objetivo_Base_Ajustado"]),
                0,
            )
        if sum(libres.values()) < adicional_total:
            return False, (
                f"Objetivo global no factible: adicional requerido={adicional_total}, "
                f"capacidad libre C+D={sum(libres.values())}."
            )
        if adicional_total:
            teoricos = {
                tax: adicional_total * libres[tax] / sum(libres.values())
                for tax in ["C", "D"]
            }
            adicionales = {
                tax: min(int(teoricos[tax]), libres[tax]) for tax in ["C", "D"]
            }
            faltan = adicional_total - sum(adicionales.values())
            while faltan > 0:
                orden = sorted(
                    ["C", "D"],
                    key=lambda tax: (
                        -(teoricos[tax] - adicionales[tax]),
                        -(libres[tax] - adicionales[tax]),
                        tax,
                    ),
                )
                progreso = False
                for tax in orden:
                    if faltan and adicionales[tax] < libres[tax]:
                        adicionales[tax] += 1
                        faltan -= 1
                        progreso = True
                if not progreso:
                    return (
                        False,
                        "No se pudo conciliar el adicional global entre C y D.",
                    )
            for tax, valor in adicionales.items():
                base.loc[base["Taxonomia"] == tax, "Adicional_Global"] = int(valor)

        base["Objetivo_Final_Taxonomia"] = (
            base["Objetivo_Base_Ajustado"] + base["Adicional_Global"]
        ).astype(int)
        if (
            base["Objetivo_Final_Taxonomia"] > base["Clientes_Potenciales_Snapshot"]
        ).any():
            detalle = base.loc[
                base["Objetivo_Final_Taxonomia"]
                > base["Clientes_Potenciales_Snapshot"],
                [
                    "Taxonomia",
                    "Objetivo_Final_Taxonomia",
                    "Clientes_Potenciales_Snapshot",
                ],
            ].to_dict("records")
            return False, f"Objetivos por taxonomía no factibles: {detalle}."

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filas_vendedor = []
        for _, taxrow in base.iterrows():
            tax = str(taxrow["Taxonomia"])
            grupo = potencial[potencial["Taxonomia"] == tax].copy()
            grupo = _asignar_entero_con_topes_tp(
                grupo,
                "Clientes_Potenciales_Snapshot",
                int(taxrow["Objetivo_Final_Taxonomia"]),
            )
            grupo["Anio"] = anio_int
            grupo["Mes"] = mes_int
            grupo["Objetivo_Taxonomia_Final"] = int(taxrow["Objetivo_Final_Taxonomia"])
            grupo["Obj_TP_Manual"] = pd.NA
            grupo["Motivo_Modificacion"] = pd.NA
            grupo["FechaGeneracion"] = fecha
            grupo["FechaModificacion"] = pd.NA
            filas_vendedor.append(grupo)
        detalle = pd.concat(filas_vendedor, ignore_index=True)
        cols_det = [
            "Anio",
            "Mes",
            "CodVendedor",
            "Vendedor_Snapshot",
            "Supervisor_Snapshot",
            "Taxonomia",
            "Clientes_Potenciales_Snapshot",
            "Objetivo_Taxonomia_Final",
            "Obj_TP_Asignado",
            "Obj_TP_Manual",
            "Motivo_Modificacion",
            "FechaGeneracion",
            "FechaModificacion",
        ]
        detalle = detalle[cols_det]
        if (
            detalle["Obj_TP_Asignado"] > detalle["Clientes_Potenciales_Snapshot"]
        ).any():
            return (
                False,
                "Control fallido: un objetivo vendedor supera su potencial snapshot.",
            )
        conciliacion = detalle.groupby("Taxonomia")["Obj_TP_Asignado"].sum()
        esperados = base.set_index("Taxonomia")["Objetivo_Final_Taxonomia"]
        if not conciliacion.equals(esperados.astype(int)):
            return (
                False,
                f"Conciliación por taxonomía fallida: asignado={conciliacion.to_dict()}, esperado={esperados.to_dict()}.",
            )
        if int(detalle["Obj_TP_Asignado"].sum()) < minimo_global:
            return False, "Control global +20% no cumplido."

        periodo = base[
            [
                "Taxonomia",
                "Obj_TP_Pepsico",
                "Factor_Ajuste",
                "Objetivo_Base_Ajustado",
                "Adicional_Global",
                "Objetivo_Final_Taxonomia",
                "Clientes_Potenciales_Snapshot",
            ]
        ].rename(columns={"Clientes_Potenciales_Snapshot": "Potencial_Taxonomia"})
        periodo["Anio"] = anio_int
        periodo["Mes"] = mes_int
        periodo["EstadoSnapshot"] = "CONCILIADO"
        periodo["FechaGeneracion"] = fecha
        periodo["FechaModificacion"] = pd.NA
        periodo = periodo[
            [
                "Anio",
                "Mes",
                "Taxonomia",
                "Obj_TP_Pepsico",
                "Factor_Ajuste",
                "Objetivo_Base_Ajustado",
                "Adicional_Global",
                "Objetivo_Final_Taxonomia",
                "Potencial_Taxonomia",
                "EstadoSnapshot",
                "FechaGeneracion",
                "FechaModificacion",
            ]
        ]

        try:
            conn.execute("BEGIN IMMEDIATE")
            periodo.to_sql(
                "objetivos_tp_periodo", conn, if_exists="append", index=False
            )
            detalle.to_sql(
                "objetivos_tp_vendedor", conn, if_exists="append", index=False
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return True, (
            f"Snapshot TP {mes_int:02d}/{anio_int} generado y congelado: "
            f"objetivo total={int(detalle['Obj_TP_Asignado'].sum())}, "
            f"filas vendedor-taxonomía={len(detalle)}."
        )
    except Exception as exc:
        return False, f"Error al generar snapshot TP: {exc}"
    finally:
        conn.close()


def obtener_snapshot_objetivos_tp(anio, mes):
    asegurar_tablas_objetivos_tp()
    conn = obtener_conexion()
    try:
        return pd.read_sql_query(
            """
            SELECT *, COALESCE(Obj_TP_Manual, Obj_TP_Asignado) AS Obj_TP_Final
            FROM objetivos_tp_vendedor
            WHERE Anio=? AND Mes=?
            ORDER BY Supervisor_Snapshot, Vendedor_Snapshot, Taxonomia
            """,
            conn,
            params=(int(float(anio)), int(float(mes))),
        )
    finally:
        conn.close()


def obtener_control_objetivos_tp(anio, mes):
    asegurar_tablas_objetivos_tp()
    conn = obtener_conexion()
    try:
        periodo = pd.read_sql_query(
            "SELECT * FROM objetivos_tp_periodo WHERE Anio=? AND Mes=? ORDER BY Taxonomia",
            conn,
            params=(int(float(anio)), int(float(mes))),
        )
        detalle = pd.read_sql_query(
            """
            SELECT Taxonomia,
                   SUM(Obj_TP_Asignado) AS Objetivo_Asignado_Original,
                   SUM(COALESCE(Obj_TP_Manual, Obj_TP_Asignado)) AS Objetivo_Final,
                   SUM(Clientes_Potenciales_Snapshot) AS Potencial_Snapshot
            FROM objetivos_tp_vendedor
            WHERE Anio=? AND Mes=?
            GROUP BY Taxonomia
            ORDER BY Taxonomia
            """,
            conn,
            params=(int(float(anio)), int(float(mes))),
        )
        return periodo, detalle
    finally:
        conn.close()


def guardar_modificaciones_objetivos_tp(df_editado, anio, mes):
    """Actualiza solo las filas recibidas y conserva intacto el resto del snapshot."""
    requeridas = ["CodVendedor", "Taxonomia", "Obj_TP_Manual", "Motivo_Modificacion"]
    faltantes = [c for c in requeridas if c not in df_editado.columns]
    if faltantes:
        return False, "Faltan columnas: " + ", ".join(faltantes)
    anio_int, mes_int = int(float(anio)), int(float(mes))
    actual = obtener_snapshot_objetivos_tp(anio_int, mes_int)
    if actual.empty:
        return False, "No existe snapshot TP para el período seleccionado."

    cambios = df_editado[requeridas].copy()
    cambios["CodVendedor"] = pd.to_numeric(
        cambios["CodVendedor"], errors="coerce"
    ).astype("Int64")
    cambios["Taxonomia"] = cambios["Taxonomia"].astype(str).str.strip().str.upper()
    cambios["Obj_TP_Manual"] = pd.to_numeric(cambios["Obj_TP_Manual"], errors="coerce")
    if cambios.duplicated(["CodVendedor", "Taxonomia"]).any():
        return False, "La edición contiene claves vendedor-taxonomía duplicadas."

    claves = ["CodVendedor", "Taxonomia"]
    referencia = actual[claves + ["Clientes_Potenciales_Snapshot", "Obj_TP_Asignado"]]
    cambios = cambios.merge(referencia, on=claves, how="left")
    if cambios["Clientes_Potenciales_Snapshot"].isna().any():
        return False, "Hay filas editadas que no pertenecen al snapshot persistido."
    final_cambio = cambios["Obj_TP_Manual"].fillna(cambios["Obj_TP_Asignado"])
    if (final_cambio < 0).any() or not (final_cambio % 1 == 0).all():
        return False, "Los objetivos finales deben ser enteros no negativos."
    if (final_cambio > cambios["Clientes_Potenciales_Snapshot"]).any():
        malos = cambios.loc[
            final_cambio > cambios["Clientes_Potenciales_Snapshot"],
            [
                "CodVendedor",
                "Taxonomia",
                "Clientes_Potenciales_Snapshot",
                "Obj_TP_Manual",
            ],
        ].to_dict("records")
        return False, f"Objetivos manuales superiores al potencial snapshot: {malos}."
    modificadas = cambios["Obj_TP_Manual"].notna()
    motivo = cambios["Motivo_Modificacion"].fillna("").astype(str).str.strip()
    if (modificadas & motivo.eq("")).any():
        return False, "Toda modificación manual requiere Motivo_Modificacion."

    # Simulación completa antes de escribir: solo reemplaza las claves editadas.
    simulado = actual.copy().set_index(claves)
    for _, fila in cambios.iterrows():
        clave = (int(fila["CodVendedor"]), fila["Taxonomia"])
        manual = pd.NA if pd.isna(fila["Obj_TP_Manual"]) else int(fila["Obj_TP_Manual"])
        simulado.loc[clave, "Obj_TP_Manual"] = manual
        simulado.loc[clave, "Motivo_Modificacion"] = (
            pd.NA if pd.isna(manual) else str(fila["Motivo_Modificacion"]).strip()
        )
    simulado = simulado.reset_index()
    simulado["Obj_TP_Final"] = (
        pd.to_numeric(simulado["Obj_TP_Manual"], errors="coerce")
        .fillna(simulado["Obj_TP_Asignado"])
        .astype(int)
    )

    conn = obtener_conexion()
    try:
        maestro_total = (
            conn.execute(
                "SELECT SUM(Obj_TP_Pepsico) FROM maestro_tp WHERE Anio=? AND Mes=?",
                (anio_int, mes_int),
            ).fetchone()[0]
            or 0
        )
        minimo = int(round(float(maestro_total) * 1.20))
        suma_final = int(simulado["Obj_TP_Final"].sum())
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        estado = "CONCILIADO" if suma_final >= minimo else "OBSERVADO"
        try:
            conn.execute("BEGIN IMMEDIATE")
            for _, fila in cambios.iterrows():
                manual = (
                    None
                    if pd.isna(fila["Obj_TP_Manual"])
                    else int(fila["Obj_TP_Manual"])
                )
                mot = (
                    None if manual is None else str(fila["Motivo_Modificacion"]).strip()
                )
                fecha_mod = None if manual is None else ahora
                conn.execute(
                    """
                    UPDATE objetivos_tp_vendedor
                    SET Obj_TP_Manual=?, Motivo_Modificacion=?, FechaModificacion=?
                    WHERE Anio=? AND Mes=? AND CodVendedor=? AND Taxonomia=?
                    """,
                    (
                        manual,
                        mot,
                        fecha_mod,
                        anio_int,
                        mes_int,
                        int(fila["CodVendedor"]),
                        fila["Taxonomia"],
                    ),
                )
            conn.execute(
                "UPDATE objetivos_tp_periodo SET EstadoSnapshot=?, FechaModificacion=? WHERE Anio=? AND Mes=?",
                (estado, ahora, anio_int, mes_int),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return True, (
            f"Modificaciones TP guardadas. Estado={estado}; total final={suma_final}; "
            f"mínimo global={minimo}."
        )
    except Exception as exc:
        return False, f"Error al guardar modificaciones TP: {exc}"
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
        "Maestro_TP_Config": "maestro_tp",
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
