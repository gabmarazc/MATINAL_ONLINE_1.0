import streamlit as st
import pandas as pd

from modules import database as db


@st.cache_data(show_spinner=False)
def obtener_core_vendedores():
    """
    CORE_VENDEDORES V1

    Responsabilidades:
    - Cargar maestro_vendedores
    - Normalizar CodVendedor
    - Mantener Nombre
    - Mantener SUP
    - Excluir vendedor 20
    - Eliminar duplicados
    """

    try:
        df = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    col_cod = next(
        (
            c
            for c in ["Codigo_Vendedor", "CodVend", "CodVendedor", "Cod_Vendedor"]
            if c in df.columns
        ),
        None,
    )

    if col_cod is None:
        return pd.DataFrame()

    core = pd.DataFrame()

    core["CodVendedor"] = pd.to_numeric(df[col_cod], errors="coerce").astype("Int64")

    col_nombre = next(
        (c for c in ["Nombre_Vendedor", "Nombre", "Vendedor"] if c in df.columns), None
    )

    if col_nombre:
        core["Nombre"] = df[col_nombre].fillna("").astype(str).str.strip()
    else:
        core["Nombre"] = ""

    col_sup = next((c for c in ["Supervisor", "SUP"] if c in df.columns), None)

    if col_sup:
        core["SUP"] = df[col_sup].fillna("").astype(str).str.strip()
    else:
        core["SUP"] = ""

    core = core[core["CodVendedor"].notna()].copy()

    core = core[core["CodVendedor"] != 20].copy()

    core = core.drop_duplicates(subset=["CodVendedor"])

    core = core.sort_values("CodVendedor").reset_index(drop=True)

    return core
