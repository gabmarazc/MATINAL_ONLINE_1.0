# modules/core/core_ventas_base.py

import streamlit as st
import pandas as pd

from modules.staging import obtener_staging_vta
from modules.utils import parsear_fecha_robusta


@st.cache_data(show_spinner=False)
def obtener_core_ventas_base():
    """
    CORE_VENTAS_BASE V1

    Responsabilidades:
    - Consumir STAGING_VTA
    - Tipar identificadores
    - Parsear fechas
    - Normalizar métricas básicas

    No aplica:
    - PepsiCo
    - Comodatos
    - CCC
    - Reemplazos
    - Vendedor 20
    - Empleados
    """

    df = obtener_staging_vta().copy()

    if df.empty:
        return pd.DataFrame()

    # -----------------------------
    # CLIENTE
    # -----------------------------

    col_cliente = next(
        (
            c
            for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
            if c in df.columns
        ),
        None,
    )

    if col_cliente:
        df["Cliente"] = pd.to_numeric(df[col_cliente], errors="coerce").astype("Int64")

    # -----------------------------
    # VENDEDOR
    # -----------------------------

    col_vendedor = next(
        (
            c
            for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
            if c in df.columns
        ),
        None,
    )

    if col_vendedor:
        df["CodVendedor"] = pd.to_numeric(df[col_vendedor], errors="coerce").astype(
            "Int64"
        )

    # -----------------------------
    # CANTBASE
    # -----------------------------

    col_cant = next(
        (
            c
            for c in [
                "CantBase",
                "CANTBASE",
                "Cantidad",
                "CANTIDAD",
                "Unidades",
                "UNIDADES",
            ]
            if c in df.columns
        ),
        None,
    )

    if col_cant:
        df["CantBase"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0)

    # -----------------------------
    # IMPORTE
    # -----------------------------

    col_importe = next(
        (
            c
            for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"]
            if c in df.columns
        ),
        None,
    )

    if col_importe:
        df["ImporteNeto"] = pd.to_numeric(df[col_importe], errors="coerce").fillna(0)

    # -----------------------------
    # PESOKG
    # -----------------------------

    if "PesoKg" in df.columns:
        df["PesoKg"] = pd.to_numeric(df["PesoKg"], errors="coerce").fillna(0)

    # -----------------------------
    # FECHAS
    # -----------------------------

    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))

    df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    if "FechaLiquidacion" in df.columns:
        df["FechaLiquidacion_dt"] = parsear_fecha_robusta(df.get("FechaLiquidacion"))

    return df
