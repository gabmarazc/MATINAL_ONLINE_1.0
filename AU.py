# AU_CHKIN_STAGING.py
# Auditoria independiente y de solo lectura de SQLite.chkin vs STAGING_CHKIN.
# No modifica matinal.db ni codigo productivo.

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "matinal.db"
KEY_COLS = ["Codigo Cliente", "Fecha Check-in"]
EXPECTED_COLS = [
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


def titulo(texto: str) -> None:
    print("\n" + "=" * 88)
    print(texto)
    print("=" * 88)


def ok(etiqueta: str, condicion: bool, detalle: str = "") -> bool:
    estado = "OK" if condicion else "ERROR"
    sufijo = f" | {detalle}" if detalle else ""
    print(f"[{estado}] {etiqueta}{sufijo}")
    return condicion


def normalizar_key_cliente(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce").astype("Int64").astype("string")


def normalizar_key_fecha(serie: pd.Series) -> pd.Series:
    fechas = pd.to_datetime(serie, errors="coerce")
    return fechas.dt.strftime("%Y-%m-%d %H:%M:%S.%f").astype("string")


def main() -> int:
    inicio = time.perf_counter()
    errores = 0

    titulo("AU_CHKIN_STAGING - AUDITORIA FORENSE")
    print(f"Proyecto : {ROOT}")
    print(f"SQLite   : {DB_PATH}")
    print("Modo     : SOLO LECTURA")

    if not DB_PATH.is_file():
        print(f"\n[ERROR] No existe la base: {DB_PATH}")
        return 1

    # 1. Auditoria directa de SQLite, abriendo explicitamente en modo read-only.
    titulo("1. SQLITE.chkin")
    uri = DB_PATH.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        existe = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chkin'"
        ).fetchone()
        if not ok("Existe tabla chkin", bool(existe)):
            return 1

        info = conn.execute('PRAGMA table_info("chkin")').fetchall()
        sql_cols = [fila[1] for fila in info]
        errores += not ok(
            "Contrato de 13 columnas",
            sql_cols == EXPECTED_COLS,
            f"encontradas={len(sql_cols)}",
        )
        if sql_cols != EXPECTED_COLS:
            print("Esperadas :", EXPECTED_COLS)
            print("Encontradas:", sql_cols)

        sql_rows = int(conn.execute('SELECT COUNT(*) FROM "chkin"').fetchone()[0])
        sql_distinct_key = int(
            conn.execute(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT "Codigo Cliente", "Fecha Check-in"
                    FROM chkin
                    GROUP BY "Codigo Cliente", "Fecha Check-in"
                )
                """
            ).fetchone()[0]
        )
        sql_null_key = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM chkin
                WHERE "Codigo Cliente" IS NULL
                   OR TRIM("Codigo Cliente") = ''
                   OR "Fecha Check-in" IS NULL
                   OR TRIM("Fecha Check-in") = ''
                """
            ).fetchone()[0]
        )
        rango = conn.execute(
            'SELECT MIN("Fecha Check-in"), MAX("Fecha Check-in") FROM chkin'
        ).fetchone()

        print(f"Filas SQLite         : {sql_rows}")
        print(f"KEY distintas        : {sql_distinct_key}")
        print(f"KEY nulas/vacias     : {sql_null_key}")
        print(f"Fecha Check-in MIN   : {rango[0]}")
        print(f"Fecha Check-in MAX   : {rango[1]}")
        errores += not ok("KEY SQLite unica", sql_rows == sql_distinct_key)
        errores += not ok("KEY SQLite completa", sql_null_key == 0)

        # Carga solo las columnas necesarias para conciliacion detallada.
        sql_key_df = pd.read_sql_query(
            'SELECT "Codigo Cliente", "Fecha Check-in" FROM chkin', conn
        )
    finally:
        conn.close()

    # 2. Ejecutar exactamente el STAGING productivo.
    titulo("2. EJECUCION obtener_staging_chkin()")
    try:
        from modules.staging import obtener_staging_chkin
    except Exception as exc:
        print(
            f"[ERROR] No se pudo importar modules.staging: {type(exc).__name__}: {exc}"
        )
        return 1

    try:
        # Evita que una version cacheada de Streamlit oculte el estado actual.
        if hasattr(obtener_staging_chkin, "clear"):
            obtener_staging_chkin.clear()
        df = obtener_staging_chkin()
    except Exception as exc:
        print(f"[ERROR] obtener_staging_chkin fallo: {type(exc).__name__}: {exc}")
        return 1

    if not isinstance(df, pd.DataFrame):
        print(f"[ERROR] STAGING devolvio {type(df).__name__}, no DataFrame.")
        return 1

    print(f"Filas STAGING        : {len(df)}")
    print(f"Columnas STAGING     : {len(df.columns)}")
    errores += not ok("STAGING no vacio", not df.empty)
    errores += not ok(
        "Contrato de columnas STAGING",
        list(df.columns) == EXPECTED_COLS,
        f"encontradas={len(df.columns)}",
    )

    faltantes = [c for c in EXPECTED_COLS if c not in df.columns]
    if faltantes:
        print("Columnas faltantes:", faltantes)
        return 1

    # 3. Conciliacion de granularidad y KEY.
    titulo("3. CONCILIACION SQLITE vs STAGING")
    errores += not ok(
        "Misma cantidad de filas",
        len(df) == sql_rows,
        f"SQLite={sql_rows} | STAGING={len(df)}",
    )

    stg_dup = int(df.duplicated(subset=KEY_COLS, keep=False).sum())
    stg_key_null = int(df[KEY_COLS].isna().any(axis=1).sum())
    print(f"Filas en KEY duplicadas: {stg_dup}")
    print(f"Filas con KEY nula     : {stg_key_null}")
    errores += not ok("KEY STAGING unica", stg_dup == 0)
    errores += not ok("KEY STAGING completa", stg_key_null == 0)

    sql_key = pd.DataFrame(
        {
            "Codigo Cliente": normalizar_key_cliente(sql_key_df["Codigo Cliente"]),
            "Fecha Check-in": normalizar_key_fecha(sql_key_df["Fecha Check-in"]),
        }
    )
    stg_key = pd.DataFrame(
        {
            "Codigo Cliente": normalizar_key_cliente(df["Codigo Cliente"]),
            "Fecha Check-in": normalizar_key_fecha(df["Fecha Check-in"]),
        }
    )
    sql_set = set(map(tuple, sql_key.itertuples(index=False, name=None)))
    stg_set = set(map(tuple, stg_key.itertuples(index=False, name=None)))
    faltan_staging = sql_set - stg_set
    sobran_staging = stg_set - sql_set
    print(f"KEY SQLite ausentes en STAGING : {len(faltan_staging)}")
    print(f"KEY STAGING ausentes en SQLite : {len(sobran_staging)}")
    errores += not ok(
        "Conservacion exacta de KEY",
        not faltan_staging and not sobran_staging,
    )
    if faltan_staging:
        print("Muestra faltantes STAGING:", list(faltan_staging)[:5])
    if sobran_staging:
        print("Muestra sobrantes STAGING:", list(sobran_staging)[:5])

    # 4. Tipos tecnicos.
    titulo("4. TIPOS TECNICOS STAGING")
    checks_tipo = {
        "Codigo Cliente -> Int64": str(df["Codigo Cliente"].dtype) == "Int64",
        "Codigo Empleado -> string": pd.api.types.is_string_dtype(
            df["Codigo Empleado"].dtype
        ),
        "Fecha Check-in -> datetime": pd.api.types.is_datetime64_any_dtype(
            df["Fecha Check-in"]
        ),
        "Fecha Check-out -> datetime": pd.api.types.is_datetime64_any_dtype(
            df["Fecha Check-out"]
        ),
        "Tiempo en PDV -> timedelta": pd.api.types.is_timedelta64_dtype(
            df["Tiempo en PDV"]
        ),
    }
    for etiqueta, condicion in checks_tipo.items():
        errores += not ok(etiqueta, condicion)

    print("\nDtypes relevantes:")
    print(
        df[
            [
                "Codigo Cliente",
                "Codigo Empleado",
                "Supervisor",
                "Fecha Check-in",
                "Fecha Check-out",
                "Tiempo en PDV",
            ]
        ].dtypes.to_string()
    )

    # 5. Calidad tecnica, sin aplicar reglas CORE.
    titulo("5. CALIDAD TECNICA")
    for col in EXPECTED_COLS:
        print(f"{col:<32} nulos={int(df[col].isna().sum()):>7}")

    empleados = df["Codigo Empleado"].dropna().astype("string")
    empleados_alfanum = empleados[~empleados.str.fullmatch(r"\d+")]
    print(f"\nCodigos Empleado distintos          : {empleados.nunique()}")
    print(f"Codigos Empleado alfanumericos      : {empleados_alfanum.nunique()}")
    if not empleados_alfanum.empty:
        print(
            "Muestra alfanumericos                :",
            empleados_alfanum.drop_duplicates().head(15).tolist(),
        )

    fechas_ci_nulas = int(df["Fecha Check-in"].isna().sum())
    fechas_co_nulas = int(df["Fecha Check-out"].isna().sum())
    tiempos_nulos = int(df["Tiempo en PDV"].isna().sum())
    errores += not ok(
        "Fecha Check-in parseada", fechas_ci_nulas == 0, f"NaT={fechas_ci_nulas}"
    )
    errores += not ok(
        "Fecha Check-out parseada", fechas_co_nulas == 0, f"NaT={fechas_co_nulas}"
    )
    errores += not ok(
        "Tiempo en PDV parseado", tiempos_nulos == 0, f"NaT={tiempos_nulos}"
    )

    if not df["Fecha Check-in"].dropna().empty:
        print(
            f"Rango STAGING Check-in : {df['Fecha Check-in'].min()} -> {df['Fecha Check-in'].max()}"
        )
    if not df["Tiempo en PDV"].dropna().empty:
        print(f"Tiempo PDV minimo      : {df['Tiempo en PDV'].min()}")
        print(f"Tiempo PDV maximo      : {df['Tiempo en PDV'].max()}")

    print("\nValores Motivo Invalidez Check-in:")
    print(df["Motivo Invalidez Check-in"].value_counts(dropna=False).to_string())
    print("\nValores Motivo Invalidez Check-out:")
    print(df["Motivo Invalidez Check-out"].value_counts(dropna=False).to_string())
    print("\nValores Valido:")
    print(df["Valido"].value_counts(dropna=False).to_string())
    print("\nValores Existe Carga:")
    print(df["Existe Carga"].value_counts(dropna=False).to_string())

    # 6. Control informativo de la regla que luego pertenecera a CORE.
    # No altera STAGING ni usa esta regla para filtrar registros.
    titulo("6. CONTROL FUNCIONAL INFORMATIVO PARA FUTURO CORE")
    ci_correcto = df["Motivo Invalidez Check-in"].isna()
    co_correcto = df["Motivo Invalidez Check-out"].isna()
    valido_calculado = ci_correcto & co_correcto
    valido_origen = df["Valido"].astype("string").str.upper().eq("SI")
    diferencias = int((valido_calculado != valido_origen).sum())
    print(f"Check-in sin motivo de invalidez : {int(ci_correcto.sum())}")
    print(f"Check-out sin motivo de invalidez: {int(co_correcto.sum())}")
    print(f"Valido calculado por ambos       : {int(valido_calculado.sum())}")
    print(f"Valido='SI' en origen            : {int(valido_origen.sum())}")
    print(f"Diferencias regla vs origen      : {diferencias}")
    if diferencias:
        muestra_cols = [
            "Codigo Cliente",
            "Codigo Empleado",
            "Fecha Check-in",
            "Motivo Invalidez Check-in",
            "Motivo Invalidez Check-out",
            "Valido",
        ]
        print("\nMuestra de diferencias:")
        print(
            df.loc[valido_calculado != valido_origen, muestra_cols]
            .head(10)
            .to_string(index=False)
        )

    titulo("7. VEREDICTO")
    duracion = time.perf_counter() - inicio
    if errores == 0:
        print("STAGING_CHKIN APROBADO")
        print(
            "No se detectaron perdidas de granularidad, duplicacion de KEY ni errores de tipado tecnico."
        )
        print(
            "El control funcional del punto 6 es informativo y debe interpretarse antes de crear CORE_CHKIN."
        )
        print(f"Duracion total: {duracion:.2f} s")
        return 0

    print("STAGING_CHKIN NO APROBADO")
    print(f"Controles tecnicos fallidos: {errores}")
    print(f"Duracion total: {duracion:.2f} s")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nAuditoria interrumpida por el usuario.")
        raise SystemExit(130)
    except Exception as exc:
        print("\n" + "=" * 88)
        print("ERROR NO CONTROLADO EN AU_CHKIN_STAGING")
        print("=" * 88)
        print(f"{type(exc).__name__}: {exc}")
        raise
