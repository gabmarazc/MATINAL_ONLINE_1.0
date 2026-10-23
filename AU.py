# au.py
# Auditoría de tablas SQLite en modo exclusivamente lectura.

import sqlite3
from pathlib import Path


DB_PATH = Path("data") / "matinal.db"


def main():
    print("=" * 80)
    print("AUDITORÍA DEL CATÁLOGO SQLITE")
    print("=" * 80)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"No se encontró la base SQLite: {DB_PATH.resolve()}")

    print(f"\nBase auditada: {DB_PATH.resolve()}")
    print("Modo: SOLO LECTURA")

    conexion = sqlite3.connect(
        f"file:{DB_PATH.resolve().as_posix()}?mode=ro",
        uri=True,
    )

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        )

        tablas = [fila[0] for fila in cursor.fetchall()]

        print(f"\nCantidad de tablas: {len(tablas)}")

        print("\n" + "=" * 80)
        print("TABLAS EXISTENTES")
        print("=" * 80)

        for tabla in tablas:
            print(tabla)

        posibles_respaldos = [
            tabla
            for tabla in tablas
            if (
                "vendedor" in tabla.lower()
                or "maestro" in tabla.lower()
                or "backup" in tabla.lower()
                or "old" in tabla.lower()
                or "bak" in tabla.lower()
                or "abm" in tabla.lower()
            )
        ]

        print("\n" + "=" * 80)
        print("POSIBLES TABLAS DE RECUPERACIÓN")
        print("=" * 80)

        if posibles_respaldos:
            for tabla in posibles_respaldos:
                print(tabla)
        else:
            print("No se detectaron posibles respaldos por nombre.")

        print("\n" + "=" * 80)
        print("ESTRUCTURA DE TABLAS CANDIDATAS")
        print("=" * 80)

        for tabla in posibles_respaldos:
            nombre_seguro = tabla.replace('"', '""')

            cursor.execute(f'PRAGMA table_info("{nombre_seguro}")')

            columnas = cursor.fetchall()

            print(f"\nTABLA: {tabla}")
            print("-" * 80)

            if not columnas:
                print("Sin columnas detectadas.")
                continue

            for columna in columnas:
                cid = columna[0]
                nombre = columna[1]
                tipo = columna[2]

                print(f"{cid:>3} | {nombre:<45} | {tipo}")

            cursor.execute(f'SELECT COUNT(*) FROM "{nombre_seguro}"')

            cantidad = cursor.fetchone()[0]

            print(f"\nRegistros: {cantidad:,}")

        print("\n" + "=" * 80)
        print("AUDITORÍA FINALIZADA")
        print("=" * 80)

    finally:
        conexion.close()


if __name__ == "__main__":
    main()
