import sqlite3
import pandas as pd

con = sqlite3.connect("data/matinal.db")

sql = """
SELECT
    COUNT(*) filas,
    SUM(PesoKg) kg
FROM vta_limpia
WHERE FechaCarga='2026-09-30'
  AND FechaEntrega >= '2026-10-01'
"""

print(pd.read_sql(sql, con))
