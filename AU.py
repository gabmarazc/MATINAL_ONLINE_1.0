# au.py

import sqlite3
from pathlib import Path
import pandas as pd


def encontrar_db():

    candidatos = list(Path(".").rglob("*.db"))

    if not candidatos:
        raise FileNotFoundError("No se encontró ninguna base SQLite.")

    return sorted(candidatos, key=lambda x: x.stat().st_size, reverse=True)[0]


db_path = encontrar_db()

conn = sqlite3.connect(db_path)

try:
    df = pd.read_sql_query(
        """
        SELECT DISTINCT
            FechaEntrega
        FROM vta
        ORDER BY FechaEntrega
        LIMIT 100
        """,
        conn,
    )

    print(df.to_string(index=False))

finally:
    conn.close()
