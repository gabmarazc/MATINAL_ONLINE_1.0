import sqlite3
import pandas as pd

conn = sqlite3.connect("data/matinal.db")

query = """
SELECT
    substr(FechaCarga,1,7) mes,
    COUNT(DISTINCT CLAVE_NEGOCIO) claves
FROM vta
GROUP BY mes
ORDER BY mes DESC
"""

df = pd.read_sql(query, conn)

conn.close()

print(df.to_string(index=False))
