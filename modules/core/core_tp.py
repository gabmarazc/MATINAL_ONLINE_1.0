# modules/core/core_tp.py

import time
import pandas as pd
import streamlit as st
from modules import database as db


@st.cache_data(show_spinner=False)
def obtener_core_tp() -> pd.DataFrame:
    """
    CORE TP
    Normaliza la fuente de Tienda Perfecta,
    resuelve vendedor y supervisor mediante maestro_vendedores,
    tipa columnas,
    limpia textos
    y expone un contrato estable para capas superiores.
    No aplica reglas comerciales.
    No genera rankings.
    No genera métricas.
    No genera reportes.
    """
    t_start = time.perf_counter()

    try:
        df_raw = db.cargar_tabla_sql("SELECT * FROM tp")
    except Exception:
        df_raw = pd.DataFrame()

    if df_raw is None or df_raw.empty:
        return pd.DataFrame(
            columns=[
                "Cliente_id",
                "CodVendedor",
                "Vendedor",
                "Supervisor",
                "RazonSocial",
                "SubCanal",
                "Taxonomia",
                "Score",
                "Es_TP",
            ]
        )

    df = df_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    col_cliente = "Cliente_id"
    col_vendedor = "Vendedor"
    col_razon = "Razon Social"
    col_subcanal = "SubCanal"
    col_tax = "Taxonomía"
    col_score = "Puntuación"
    col_tp_flag = "Tienda \nPerfecta"

    columnas_faltantes = [
        c
        for c in [
            col_cliente,
            col_vendedor,
            col_razon,
            col_subcanal,
            col_tax,
            col_score,
            col_tp_flag,
        ]
        if c not in df.columns
    ]
    if columnas_faltantes:
        return pd.DataFrame(
            columns=[
                "Cliente_id",
                "CodVendedor",
                "Vendedor",
                "Supervisor",
                "RazonSocial",
                "SubCanal",
                "Taxonomia",
                "Score",
                "Es_TP",
            ]
        )

    df["Cliente_id"] = pd.to_numeric(df[col_cliente], errors="coerce").astype("Int64")

    # Resolución de vendedor y supervisor desde maestro_vendedores
    try:
        df_m = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    except Exception:
        df_m = pd.DataFrame()

    if not df_m.empty:
        col_c_v = next(
            (
                c
                for c in ["Codigo_Vendedor", "CodVend", "CodVendedor"]
                if c in df_m.columns
            ),
            df_m.columns[0],
        )
        col_n_v = next(
            (c for c in ["Nombre_Vendedor", "Nombre"] if c in df_m.columns),
            df_m.columns[1] if len(df_m.columns) > 1 else df_m.columns[0],
        )
        col_s_v = next(
            (c for c in ["Supervisor", "SUP"] if c in df_m.columns),
            df_m.columns[2] if len(df_m.columns) > 2 else df_m.columns[0],
        )

        df_m_clean = pd.DataFrame()
        df_m_clean["CodVen"] = pd.to_numeric(df_m[col_c_v], errors="coerce").astype(
            "Int64"
        )
        df_m_clean["NombreVen"] = (
            df_m[col_n_v].fillna("SIN NOMBRE").astype(str).str.strip()
        )
        df_m_clean["SupVen"] = df_m[col_s_v].fillna("GENERAL").astype(str).str.strip()
        df_m_clean = df_m_clean.drop_duplicates("CodVen")

        df["_CodVendedor"] = pd.to_numeric(df[col_vendedor], errors="coerce").astype(
            "Int64"
        )
        df = df.merge(df_m_clean, left_on="_CodVendedor", right_on="CodVen", how="left")

        df["CodVendedor"] = df["CodVen"].fillna(df["_CodVendedor"]).astype("Int64")
        df["Vendedor"] = (
            df["NombreVen"].fillna(df[col_vendedor].astype(str)).str.strip()
        )
        df["Supervisor"] = df["SupVen"].fillna("GENERAL").str.strip()
    else:
        df["CodVendedor"] = pd.to_numeric(df[col_vendedor], errors="coerce").astype(
            "Int64"
        )
        df["Vendedor"] = df[col_vendedor].fillna("SIN VENDEDOR").astype(str).str.strip()
        df["Supervisor"] = "GENERAL"

    df["SubCanal"] = df[col_subcanal].fillna("SIN SUBCANAL").astype(str).str.strip()
    df["Taxonomia"] = (
        df[col_tax].fillna("SIN TAXONOMIA").astype(str).str.strip().str.upper()
    )
    df["RazonSocial"] = (
        df[col_razon].fillna("CLIENTE SIN NOMBRE").astype(str).str.strip()
    )

    df["Es_TP"] = df[col_tp_flag].fillna("").astype(str).str.strip().str.upper() == "SI"
    df["Score"] = pd.to_numeric(df[col_score], errors="coerce").fillna(0.0)

    columnas_salida = [
        "Cliente_id",
        "CodVendedor",
        "Vendedor",
        "Supervisor",
        "RazonSocial",
        "SubCanal",
        "Taxonomia",
        "Score",
        "Es_TP",
    ]

    resultado = df[columnas_salida].copy()

    t_dur = time.perf_counter() - t_start
    print(f"[PERF_TP] obtener_core_tp = {t_dur:.2f} s")

    return resultado
