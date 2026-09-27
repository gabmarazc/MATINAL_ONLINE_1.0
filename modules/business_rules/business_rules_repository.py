# modules/business_rules/business_rules_repository.py
import streamlit as st
import pandas as pd
from modules import database as db


@st.cache_data(show_spinner=False)
def obtener_objetivos_vendedores(anio: int, mes: int) -> pd.DataFrame:
    """
    BUSINESS_RULES REPOSITORY: Única entidad autorizada dentro de la capa BUSINESS_RULES
    para consultar la base de datos y extraer la entidad 'objetivos_vendedores' para un período dado.

    Garantiza manejo defensivo ante tablas vacías o inexistentes, retornando un DataFrame tipado.
    """
    try:
        query = f"SELECT CodVendedor, SEGMENTO, Obj_Sugerido_Kg FROM objetivos_vendedores WHERE Anio = {int(anio)} AND Mes = {int(mes)}"
        df = db.cargar_tabla_sql(query)
    except Exception:
        df = pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Obj_Sugerido_Kg"])

    df["CodVendedor"] = pd.to_numeric(
        df.get("CodVendedor", pd.Series(dtype="Int64")), errors="coerce"
    ).astype("Int64")
    df["SEGMENTO"] = (
        df.get("SEGMENTO", pd.Series(dtype="str")).fillna("").astype(str).str.strip()
    )
    df["Obj_Sugerido_Kg"] = pd.to_numeric(
        df.get("Obj_Sugerido_Kg", pd.Series(dtype="float")), errors="coerce"
    ).fillna(0.0)

    return df[["CodVendedor", "SEGMENTO", "Obj_Sugerido_Kg"]]
