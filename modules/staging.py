# modules/staging.py
import time
import streamlit as st
import pandas as pd
import numpy as np
from modules import database as db
from modules.utils import parsear_fecha_robusta


@st.cache_data(show_spinner=False)
def obtener_staging_vta():
    """
    Capa Staging (Técnica Pura Definitiva): Ingesta exclusiva desde la tabla RAW 'vta'.
    Aplica únicamente tipado estricto, parseo de fechas y normalización de marcas.
    Cero reglas de negocio, cero exclusiones y cero filtros de registros.
    """
    t0 = time.perf_counter()
    try:
        df_raw = db.cargar_tabla_sql("SELECT * FROM vta")
    except Exception:
        df_raw = pd.DataFrame()

    if df_raw.empty:
        print(
            f"[PERF_CORE] 1) obtener_staging_vta (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    df = df_raw.copy()

    # Normalización tipográfica estricta
    df["PesoKg"] = pd.to_numeric(df.get("PesoKg", 0), errors="coerce").fillna(0.0)

    col_pesos = next(
        (
            c
            for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"]
            if c in df.columns
        ),
        None,
    )
    df["ImporteNetoItem"] = (
        pd.to_numeric(df[col_pesos], errors="coerce").fillna(0.0) if col_pesos else 0.0
    )

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
        df.columns[0],
    )
    df["CantBase"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0.0)

    # Parseo de fechas robusto unificado
    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    # Tipado de identificadores relacionales
    col_vend_tit = next(
        (
            cand
            for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
            if cand in df.columns
        ),
        "CodVendedor",
    )
    df["CodVendedor"] = pd.to_numeric(df.get(col_vend_tit, 0), errors="coerce").astype(
        "Int64"
    )

    col_cli_tit = next(
        (
            cand
            for cand in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
            if cand in df.columns
        ),
        "Cliente",
    )
    df["Cliente"] = pd.to_numeric(df.get(col_cli_tit, 0), errors="coerce").astype(
        "Int64"
    )

    # Normalización sintáctica de marca
    col_m = next((c for c in ["Marca", "MARCA", "marca"] if c in df.columns), None)
    df["Marca"] = (
        df[col_m].fillna("").astype(str).str.strip().str.upper()
        if col_m
        else "SIN MARCA"
    )

    print(f"[PERF_CORE] 1) obtener_staging_vta -> {time.perf_counter() - t0:.4f} s")
    return df


@st.cache_data(show_spinner=False)
def obtener_staging_clientes():
    """
    Capa Staging (Técnica Pura Definitiva): Ingesta exclusiva desde la tabla RAW 'universo'.
    Normaliza taxonomías, claves y razones sociales sin excluir empleados ni asignar supervisores de negocio.
    """
    try:
        univ = db.cargar_tabla_sql("SELECT * FROM universo")
    except Exception:
        univ = pd.DataFrame()

    if univ.empty:
        return pd.DataFrame()

    df = univ.copy()

    col_cu = next(
        (
            c
            for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"]
            if c in df.columns
        ),
        df.columns[0],
    )
    df["Cliente"] = pd.to_numeric(df[col_cu], errors="coerce").astype("Int64")

    col_tax_univ = next(
        (
            c
            for c in df.columns
            if str(c).strip().lower().replace("_", "") == "segmentoclientecodigo"
            or any(k in str(c).lower() for k in ["taxonomia", "clasificacion", "tax"])
        ),
        None,
    )
    if col_tax_univ:
        df["Taxonomia"] = (
            df[col_tax_univ].fillna("").astype(str).str.strip().str.upper()
        )
    else:
        df["Taxonomia"] = "SIN TAXONOMIA"

    df["Taxonomia"] = df["Taxonomia"].replace(
        ["", "NAN", "NONE", "NAT"], "SIN TAXONOMIA"
    )

    col_nom_c = next(
        (
            c
            for c in [
                "Razon_Social",
                "RazonSocial",
                "NombreCliente",
                "Nombre_Cliente",
                "ClienteDesc",
            ]
            if c in df.columns
        ),
        col_cu,
    )
    df["NombreCliente"] = (
        df[col_nom_c].fillna("").astype(str) if col_nom_c in df.columns else ""
    )

    pos_v_u = next(
        (
            c
            for c in df.columns
            if any(k in str(c).lower() for k in ["codven", "vendedor"])
        ),
        None,
    )
    if pos_v_u:
        df["CodVendedor"] = pd.to_numeric(df[pos_v_u], errors="coerce").astype("Int64")

    col_dir = next(
        (
            c
            for c in df.columns
            if str(c).strip().lower()
            in [
                "direccioncliente",
                "direccion_cliente",
                "direccion",
                "domicilio",
                "calle",
            ]
        ),
        None,
    )
    df["DireccionCliente"] = (
        df[col_dir].fillna("").astype(str).str.strip() if col_dir else ""
    )

    col_ruta = next(
        (
            c
            for c in df.columns
            if str(c).strip().lower()
            in [
                "ruta",
                "codruta",
                "cod_ruta",
                "dia_visita",
                "diavisita",
                "visita",
                "dia",
            ]
        ),
        None,
    )
    df["Ruta"] = (
        df[col_ruta].fillna("").astype(str).str.strip() if col_ruta else "SIN RUTA"
    )

    return df


@st.cache_data(show_spinner=False)
def obtener_staging_rutas():
    """
    Capa Staging (Técnica Pura): Carga la tabla cruda de rutas.
    """
    t0 = time.perf_counter()
    try:
        rutas = db.cargar_tabla_sql("SELECT * FROM rutas")
    except Exception:
        rutas = pd.DataFrame()
    print(f"[PERF_CORE] 2) obtener_staging_rutas -> {time.perf_counter() - t0:.4f} s")
    return rutas


@st.cache_data(show_spinner=False)
def obtener_staging_ausencias():
    """
    Capa Staging (Técnica Pura): Ingesta exclusiva desde la tabla RAW 'ausencias'.
    Aplica tipado estricto, detección robusta de columnas candidatas, parseo de fechas y normalización.
    """
    t0 = time.perf_counter()
    try:
        df_raw = db.cargar_tabla_sql("SELECT * FROM ausencias")
    except Exception:
        df_raw = pd.DataFrame()

    if df_raw.empty:
        print(
            f"[PERF_CORE] obtener_staging_ausencias (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    df = df_raw.copy()

    cols_vend_cand = [
        "Ausente",
        "CodVend",
        "CodVendedor",
        "Vendedor",
        "Cod_Vendedor",
    ]
    col_aus_vend = next((c for c in cols_vend_cand if c in df.columns), None)
    if not col_aus_vend:
        raise ValueError("No se encontró columna de vendedor en la tabla de ausencias.")

    cols_f_cand = ["Fecha", "FechaAusencia", "Dia"]
    col_aus_fecha = next((c for c in cols_f_cand if c in df.columns), None)
    if not col_aus_fecha:
        raise ValueError("No se encontró columna de fecha en la tabla de ausencias.")

    cols_reemp_cand = [
        "Reemplazo",
        "CodReemplazo",
        "Cod_Reemplazo",
        "PreventistaReemplazo",
    ]
    col_aus_reemp = next((c for c in cols_reemp_cand if c in df.columns), None)
    if not col_aus_reemp:
        raise ValueError(
            "No se encontró columna de reemplazo en la tabla de ausencias."
        )

    df["Fecha_dt"] = parsear_fecha_robusta(df[col_aus_fecha])
    df["CodVend_clean"] = pd.to_numeric(df[col_aus_vend], errors="coerce").astype(
        "Int64"
    )
    df["Reemplazo_clean"] = pd.to_numeric(df[col_aus_reemp], errors="coerce").astype(
        "Int64"
    )

    print(f"[PERF_CORE] obtener_staging_ausencias -> {time.perf_counter() - t0:.4f} s")
    return df


@st.cache_data(show_spinner=False)
def obtener_staging_maestros():
    """
    Capa Staging (Técnica Pura): Carga y centraliza los maestros base del sistema.
    """
    t0 = time.perf_counter()
    maestros = {}
    for tabla in [
        "maestro_vendedores",
        "maestro_ccc",
        "maestro_marcas_cebe",
        "ausencias",
        "maestro_segmentos",
    ]:
        try:
            maestros[tabla] = db.cargar_tabla_sql(f"SELECT * FROM {tabla}")
        except Exception:
            maestros[tabla] = pd.DataFrame()
    print(
        f"[PERF_CORE] 3) obtener_staging_maestros -> {time.perf_counter() - t0:.4f} s"
    )
    return maestros
