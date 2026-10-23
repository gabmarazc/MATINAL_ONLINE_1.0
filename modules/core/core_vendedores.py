# modules/core/core_vendedores.py
import streamlit as st
import pandas as pd
from modules import database as db


def _cargar_y_normalizar_vendedores() -> pd.DataFrame:
    """
    CORE_VENDEDORES - Función Interna Privada

    Responsabilidades:
    - Cargar maestro_vendedores desde SQLite
    - Normalizar CodVendedor
    - Mantener Nombre y SUP
    - Extraer Ajuste_Entrega y Rutas_Ajustadas
    - Eliminar duplicados
    - Ordenar por CodVendedor
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

    col_ajuste = next(
        (
            c
            for c in df.columns
            if str(c).strip().lower()
            in ["ajuste_entrega", "ajusteentrega", "dias_entrega"]
        ),
        None,
    )
    if col_ajuste:
        core["Ajuste_Entrega"] = (
            pd.to_numeric(df[col_ajuste], errors="coerce").fillna(1).astype(int)
        )
    else:
        core["Ajuste_Entrega"] = 1

    col_rutas_ajust = next(
        (
            c
            for c in df.columns
            if str(c).strip().lower()
            in ["rutas_ajustadas", "rutasajustadas", "ajustadas"]
        ),
        None,
    )
    if col_rutas_ajust:
        core["Rutas_Ajustadas"] = (
            pd.to_numeric(df[col_rutas_ajust], errors="coerce").fillna(0).astype(int)
        )
    else:
        core["Rutas_Ajustadas"] = 0

    core = core[core["CodVendedor"].notna()].copy()
    core = core.drop_duplicates(subset=["CodVendedor"])
    core = core.sort_values("CodVendedor").reset_index(drop=True)

    return core


@st.cache_data(show_spinner=False)
def obtener_core_vendedores(incluir_vendedor_20: bool = False) -> pd.DataFrame:
    """
    CORE_VENDEDORES V3 (Punto de Entrada Único)

    Responsabilidades:
    - Cargar maestro_vendedores normalizado mediante función privada.
    - Excluir por defecto al vendedor 20 (comportamiento histórico preservado).
    - Permitir opcionalmente incluir al vendedor 20 mediante el parámetro incluir_vendedor_20=True (uso gerencial).
    - Eliminar duplicados y ordenar de forma ascendente.
    """
    core = _cargar_y_normalizar_vendedores()
    if core.empty:
        return core

    if not incluir_vendedor_20:
        core = core[core["CodVendedor"] != 20].copy()

    return core.reset_index(drop=True)
