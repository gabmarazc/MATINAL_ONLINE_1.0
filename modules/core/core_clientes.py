import streamlit as st
import pandas as pd

from modules.staging import obtener_staging_clientes
from modules.utils import extraer_dia_de_ruta


@st.cache_data(show_spinner=False)
def obtener_core_clientes():
    """
    CORE_CLIENTES

    Responsabilidades:
    - Consumir STAGING_CLIENTES
    - Excluir empleados
    - Validar taxonomías comerciales
    - Garantizar claves operativas válidas

    No aplica reglas CCC.
    No aplica reglas MN+.
    No aplica reglas TP.
    """

    df = obtener_staging_clientes().copy()

    if df.empty:
        return pd.DataFrame()

    # -------------------------------------------------
    # EXCLUSIÓN EMPLEADOS
    # -------------------------------------------------

    col_subsegmento = next(
        (c for c in df.columns if str(c).strip().lower() == "subsegmento"), None
    )

    if col_subsegmento:
        df = df[
            df[col_subsegmento].fillna("").astype(str).str.strip().str.casefold()
            != "empleados"
        ].copy()

    col_subramo = next(
        (c for c in df.columns if str(c).strip().lower() == "subramo"), None
    )

    if col_subramo:
        df = df[
            df[col_subramo].fillna("").astype(str).str.strip().str.casefold()
            != "empleados"
        ].copy()

    # -------------------------------------------------
    # TAXONOMÍAS VÁLIDAS
    # -------------------------------------------------

    if "Taxonomia" in df.columns:
        df["Taxonomia"] = df["Taxonomia"].fillna("").astype(str).str.strip().str.upper()

        df = df[df["Taxonomia"].isin(["A", "B", "C", "D"])].copy()

    # -------------------------------------------------
    # CLIENTE VÁLIDO
    # -------------------------------------------------

    if "Cliente" in df.columns:
        df = df[df["Cliente"].notna()].copy()

    # -------------------------------------------------
    # VENDEDOR VÁLIDO
    # -------------------------------------------------

    if "CodVendedor" in df.columns:
        df = df[df["CodVendedor"].notna()].copy()

    if "Ruta" in df.columns:
        df["DiaVisita"] = df["Ruta"].apply(extraer_dia_de_ruta)
    else:
        df["DiaVisita"] = "SIN DÍA"

    return df
