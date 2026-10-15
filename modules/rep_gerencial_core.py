# modules/rep_gerencial_core.py
import pandas as pd
import streamlit as st
from modules import database as db
from modules.core.core_operaciones import obtener_core_operacion
from modules.rep_kilos_core import obtener_matriz_kilos_comercial
from modules.rep_ccc_core import obtener_matriz_ccc_comercial
from modules.rep_MN_core import obtener_matriz_mn_comercial


# ==========================================================
# CARGA BASE
# ==========================================================
def obtener_datasets_base_gerencial(
    anio, mes, dia_matinal, dia_venta, supervisor="TODOS"
):
    """
    Dataset inicial del Gerencial Core.
    Fuente única:
        - CORE OPERACIÓN (df_vta_operativa)
        - KILOS CORE
        - CCC CORE
        - MN CORE
    """
    filtros = {
        "anio": anio,
        "mes": mes,
        "dia_matinal": dia_matinal,
        "dia_venta": dia_venta,
        "supervisor": supervisor,
    }
    core_operacion = obtener_core_operacion(anio, mes, dia_matinal, dia_venta)
    df_core = core_operacion.get("df_vta_operativa", pd.DataFrame())
    df_kilos = obtener_matriz_kilos_comercial(anio, mes, filtros)
    df_ccc = obtener_matriz_ccc_comercial(anio, mes, filtros)
    df_mn = obtener_matriz_mn_comercial(anio, mes, filtros)
    return {
        "core": df_core,
        "kilos": df_kilos,
        "ccc": df_ccc,
        "mn": df_mn,
    }


# ==========================================================
# MAESTROS
# ==========================================================
def cargar_maestro_ccc(anio, mes):
    try:
        maestro = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
        if not maestro.empty and "Mes" in maestro.columns and "Anio" in maestro.columns:
            maestro = maestro[
                (maestro["Mes"].astype(str) == str(mes))
                & (maestro["Anio"].astype(str) == str(anio))
            ].copy()
        return maestro
    except Exception:
        return pd.DataFrame()


def cargar_maestro_cebe(anio, mes):
    try:
        maestro = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if not maestro.empty and "Mes" in maestro.columns and "Anio" in maestro.columns:
            maestro = maestro[
                (maestro["Mes"].astype(str) == str(mes))
                & (maestro["Anio"].astype(str) == str(anio))
            ].copy()
        return maestro
    except Exception:
        return pd.DataFrame()


# ==========================================================
# KILOS
# ==========================================================
def construir_bloque_kilos(df_kilos):
    """
    Granularidad final:
        SUP + SEGMENTO
    """
    if df_kilos.empty:
        return pd.DataFrame()
    res = df_kilos.groupby(["SUP", "SEGMENTO"], as_index=False).agg(
        {
            "Objetivo Mes Corriente": "sum",
            "Arrastre": "sum",
            "Actual": "sum",
            "OPERATIVO": "sum",
            "Tendencia_Total_Kg": "sum",
            "Ajuste_Por_Reemp": "sum",
        }
    )
    return res


# ==========================================================
# GROSS
# ==========================================================
def construir_bloque_gross(df_core, maestro_cebe):
    """
    IMPLEMENTACION PENDIENTE
    Debe sustituir:
        Objetivo Gross
        Operativo Gross
        Proyectado Gross
    del gerencial legacy.
    """
    return pd.DataFrame()


# ==========================================================
# CCC
# ==========================================================
def construir_bloque_ccc(df_ccc, maestro_ccc):
    if df_ccc.empty:
        return pd.DataFrame()
    res = df_ccc.groupby(["Taxonomia"], as_index=False).agg(
        {"Cartera_Neta": "sum", "CCC_Gerencia": "sum", "Objetivo_CCC": "sum"}
    )
    return res


# ==========================================================
# MN
# ==========================================================
def construir_bloque_mn(df_mn):
    if df_mn.empty:
        return pd.DataFrame()
    res = df_mn.groupby(["Taxonomia"], as_index=False).agg(
        {"Ventas_Totales": "sum", "Ventas_MiNegocio": "sum"}
    )
    return res


# ==========================================================
# FUTURO DISPONIBLE
# ==========================================================
def calcular_futuro_disponible(anio, mes):
    """
    FASE 2
    Portar desde:
        rep_gerencial.py
    usando Periodo = Futuro
    """
    return pd.DataFrame()


# ==========================================================
# GAP
# ==========================================================
def calcular_gap_incorporacion(df_kilos, df_gross):
    """
    FASE 2
    Portar:
        Futuro_A_Incorporar_Kgs
        Futuro_A_Incorporar_Gross
    """
    return {"gap_kilos": 0.0, "gap_gross": 0.0}


# ==========================================================
# MOTOR
# ==========================================================
def obtener_motor_gerencial_core(anio, mes, dia_matinal, dia_venta, supervisor="TODOS"):
    datasets = obtener_datasets_base_gerencial(
        anio, mes, dia_matinal, dia_venta, supervisor
    )
    maestro_ccc = cargar_maestro_ccc(anio, mes)
    maestro_cebe = cargar_maestro_cebe(anio, mes)
    kilos = construir_bloque_kilos(datasets["kilos"])
    gross = construir_bloque_gross(datasets["core"], maestro_cebe)
    ccc = construir_bloque_ccc(datasets["ccc"], maestro_ccc)
    mn = construir_bloque_mn(datasets["mn"])
    return {
        "kilos": kilos,
        "gross": gross,
        "ccc": ccc,
        "mn": mn,
    }


# ==========================================================
# RENDER
# ==========================================================
def render_rep_gerencial_core(filtros_globales):
    st.subheader("📈 Tablero Ejecutivo Gerencial Core")
    motor = obtener_motor_gerencial_core(
        filtros_globales["anio"],
        filtros_globales["mes"],
        filtros_globales["dia_matinal"],
        filtros_globales["dia_venta"],
        filtros_globales.get("supervisor", "TODOS"),
    )
    tab_k, tab_g, tab_c, tab_m = st.tabs(
        ["📦 KILOS", "💰 GROSS", "📈 CCC", "📱 MI NEGOCIO"]
    )
    with tab_k:
        st.dataframe(motor["kilos"], width="stretch")
    with tab_g:
        st.dataframe(motor["gross"], width="stretch")
    with tab_c:
        st.dataframe(motor["ccc"], width="stretch")
    with tab_m:
        st.dataframe(motor["mn"], width="stretch")
