# modules/business_rules/business_rules_mn.py
import time
import streamlit as st
import pandas as pd
import numpy as np

# REGLA DE ORO: Consumo exclusivo de la Capa CORE (Cero acceso a RAW, STAGING, SQLite o base de datos)
from modules.core.core_operaciones import obtener_core_operacion
from modules.core.core_clientes import obtener_core_clientes
from modules.core.core_vendedores import obtener_core_vendedores
from modules.utils import parsear_fecha_robusta


def _filtrar_ventas_mn_comercial(
    df_vta_core: pd.DataFrame, anio_op: int, mes_op: int, dia_matinal: str
) -> pd.DataFrame:
    """
    BUSINESS_RULES: Aplica las reglas institucionales de exclusión, clasificación temporal y
    asignación de titularidad operativa (reemplazos) para MiNegocio.
    - Exclusión de comodatos y préstamos logísticos.
    - Restricción exclusiva al portafolio PEPSICO.
    - Exclusión del preventista 20 (Depósito).
    - Filtro de fecha matinal (excluye cargas >= dia_matinal en el mes en curso).
    - Clasificación en períodos comerciales (Arrastre, Actual, Futuro).
    - Detección de canal digital MiNegocio y resolución del operador efectivo.
    """
    if df_vta_core is None or df_vta_core.empty:
        return pd.DataFrame()

    df = df_vta_core.copy()

    # Normalización del importe neto (tolerancia de nombres entre core_operaciones y staging)
    col_imp = next(
        (
            c
            for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"]
            if c in df.columns
        ),
        None,
    )
    df["ImporteNetoItem"] = (
        pd.to_numeric(df[col_imp], errors="coerce").fillna(0.0) if col_imp else 0.0
    )

    # Detección de canal digital MiNegocio
    col_orig = next(
        (
            c
            for c in df.columns
            if any(k in str(c).lower() for k in ["origen", "canal"])
        ),
        None,
    )
    if col_orig:
        df["OrigenDeVta"] = df[col_orig].fillna("").astype(str).str.strip()
        df["Es_MiNegocio"] = df["OrigenDeVta"].str.contains(
            "minegocio|mi negocio", case=False, na=False
        )
    else:
        df["OrigenDeVta"] = ""
        df["Es_MiNegocio"] = False

    # Filtro N2: Exclusión de comodatos y préstamos
    if "TipoDeVenta" in df.columns:
        tipos_excluidos = [
            "Comodato Devolución",
            "Comodato Ficticio",
            "Comodato Ficticio Devolución",
            "Comodato Préstamo",
        ]
        df = df[~df["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)]

    # Filtro N2: Restricción a Proveedor PepsiCo
    if "Proveedor" in df.columns:
        df = df[
            df["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    # Parseo robusto defensivo de fechas
    if "FechaCarga_dt" not in df.columns:
        df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    if "FechaEntrega_dt" not in df.columns:
        df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    # Filtro N2: Matinal
    dia_matinal_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(dia_matinal_dt):
        es_mes_en_curso = dia_matinal_dt.year == anio_op and dia_matinal_dt.month in [
            mes_op,
            mes_op + 1,
        ]
        if es_mes_en_curso:
            df = df[df["FechaCarga_dt"].dt.date < dia_matinal_dt.date()]

    # Filtro N2: Depósito (Exclusión del vendedor 20)
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
    df = df[df["CodVendedor"] != 20]

    # Resolución de titularidad operativa y reemplazos (Filosofía idéntica a Kilos CORE)
    padron_vend = obtener_core_vendedores()
    codigos_validos = (
        set(padron_vend["CodVendedor"].dropna().tolist())
        if not padron_vend.empty
        else set()
    )

    if "CodVendedorOperativo" not in df.columns:
        df["CodVendedorOperativo"] = df["CodVendedor"]

    cod_op = df["CodVendedorOperativo"]
    cod_tit = df["CodVendedor"]
    reemp = df.get("Reemplazo", pd.Series(pd.NA, index=df.index))

    is_special = ((reemp == 99) | (cod_op == 99) | (cod_tit == 99)).fillna(False)
    valid_op_mask = cod_op.isin(codigos_validos).fillna(False)
    valid_tit_mask = cod_tit.isin(codigos_validos).fillna(False)

    df["CodVendedor_Efectivo"] = np.select(
        [is_special, valid_op_mask, valid_tit_mask],
        [99, cod_op.fillna(-999).astype(int), cod_tit.fillna(-999).astype(int)],
        default=cod_tit.fillna(-999).astype(int),
    )
    df["CodVendedor_Efectivo"] = (
        pd.Series(df["CodVendedor_Efectivo"]).replace(-999, pd.NA).astype("Int64")
    )

    # Se preserva estrictamente el CodVendedor titular del Universo; CodVendedor_Efectivo se reserva para operaciones
    df["CodVendedor"] = cod_tit

    return df


def _consolidar_ventas_cliente_mn(df_vta_mn: pd.DataFrame) -> pd.DataFrame:
    """
    BUSINESS_RULES: Agrupa las transacciones de Arrastre y Actual por cliente y preventista efectivo,
    totalizando ventas brutas y digitales, aplicando las reglas de saneamiento comercial.
    """
    ventas_periodo = (
        df_vta_mn[df_vta_mn["Periodo"].isin(["Arrastre", "Actual"])].copy()
        if not df_vta_mn.empty and "Periodo" in df_vta_mn.columns
        else df_vta_mn.copy()
    )

    if ventas_periodo.empty:
        return pd.DataFrame(
            columns=[
                "Cliente",
                "CodVendedor",
                "Ventas_Totales",
                "Ventas_MiNegocio",
                "Pct_MiNegocio",
            ]
        )

    col_cli = next(
        (
            c
            for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
            if c in ventas_periodo.columns
        ),
        "Cliente",
    )
    ventas_periodo["Cliente"] = pd.to_numeric(
        ventas_periodo[col_cli], errors="coerce"
    ).astype("Int64")
    ventas_periodo["CodVendedor"] = pd.to_numeric(
        ventas_periodo["CodVendedor"], errors="coerce"
    ).astype("Int64")

    ventas_periodo["_mn_val"] = np.where(
        ventas_periodo["Es_MiNegocio"], ventas_periodo["ImporteNetoItem"], 0.0
    )

    clientes_g = ventas_periodo.groupby(["Cliente", "CodVendedor"], as_index=False).agg(
        Ventas_Totales=("ImporteNetoItem", "sum"),
        Ventas_MiNegocio=("_mn_val", "sum"),
    )

    clientes_g["Ventas_Totales"] = clientes_g["Ventas_Totales"].round(2)
    clientes_g["Ventas_MiNegocio"] = clientes_g["Ventas_MiNegocio"].round(2)

    # Reglas institucionales de truncamiento comercial
    clientes_g.loc[clientes_g["Ventas_Totales"] < 0, "Ventas_Totales"] = 0.0
    clientes_g.loc[clientes_g["Ventas_MiNegocio"] < 0, "Ventas_MiNegocio"] = 0.0
    clientes_g.loc[clientes_g["Ventas_MiNegocio"] < 0.01, "Ventas_MiNegocio"] = 0.0

    pct_raw = (
        clientes_g["Ventas_MiNegocio"] / clientes_g["Ventas_Totales"].replace(0, pd.NA)
    ).mul(100.0)
    clientes_g["Pct_MiNegocio"] = (
        pct_raw.clip(lower=0.0, upper=100.0).fillna(0.0).round(2)
    )

    return clientes_g


def _integrar_universo_y_fuera_de_padron(
    df_clientes_core: pd.DataFrame,
    df_ventas_cliente: pd.DataFrame,
    df_vta_mn: pd.DataFrame,
) -> pd.DataFrame:
    """
    BUSINESS_RULES: Fusiona la cartera oficial de clientes con las ventas del período,
    manteniendo el Universo como tabla maestra inalterable y agregando las ventas por cliente mediante sum().
    """
    universo = (
        df_clientes_core.copy() if df_clientes_core is not None else pd.DataFrame()
    )

    # Filtro defensivo de vendedor 20 sobre la cartera
    if not universo.empty and "CodVendedor" in universo.columns:
        universo["CodVendedor"] = pd.to_numeric(
            universo["CodVendedor"], errors="coerce"
        ).astype("Int64")
        universo = universo[universo["CodVendedor"] != 20]

    # Detección e incorporación de clientes fuera de padrón con ventas operativas
    ventas_periodo = (
        df_vta_mn[df_vta_mn["Periodo"].isin(["Arrastre", "Actual"])].copy()
        if not df_vta_mn.empty and "Periodo" in df_vta_mn.columns
        else df_vta_mn.copy()
    )

    if not df_ventas_cliente.empty:
        clientes_con_ventas = set(df_ventas_cliente["Cliente"].dropna().tolist())
        clientes_en_universo = (
            set(universo["Cliente"].dropna().tolist()) if not universo.empty else set()
        )
        clientes_fuera_universo = clientes_con_ventas - clientes_en_universo

        if clientes_fuera_universo and not ventas_periodo.empty:
            df_fuera = (
                ventas_periodo[ventas_periodo["Cliente"].isin(clientes_fuera_universo)]
                .groupby("Cliente", as_index=False)
                .agg({"CodVendedor": "first"})
            )
            df_fuera["Taxonomia"] = "SIN CLASIFICAR"
            df_fuera["NombreCliente"] = "CLIENTE FUERA DE PADRÓN"
            df_fuera["DireccionCliente"] = ""
            df_fuera["DiaVisita"] = "SIN DÍA"
            df_fuera["Ruta"] = "SIN RUTA"

            if universo.empty:
                universo = df_fuera
            else:
                universo = pd.concat([universo, df_fuera], ignore_index=True)

    if not universo.empty and not df_ventas_cliente.empty:
        df_ventas_cliente_agg = df_ventas_cliente.groupby("Cliente", as_index=False)[
            ["Ventas_Totales", "Ventas_MiNegocio"]
        ].sum()
        df_detalle = universo.merge(
            df_ventas_cliente_agg,
            on="Cliente",
            how="left",
        )
    else:
        df_detalle = universo.copy()
        df_detalle["Ventas_Totales"] = 0.0
        df_detalle["Ventas_MiNegocio"] = 0.0

    df_detalle["Ventas_Totales"] = df_detalle["Ventas_Totales"].fillna(0.0)
    df_detalle["Ventas_MiNegocio"] = df_detalle["Ventas_MiNegocio"].fillna(0.0)
    pct_raw = (
        df_detalle["Ventas_MiNegocio"] / df_detalle["Ventas_Totales"].replace(0, pd.NA)
    ).mul(100.0)
    df_detalle["Pct_MiNegocio"] = (
        pct_raw.clip(lower=0.0, upper=100.0).fillna(0.0).round(2)
    )

    return df_detalle


def _clasificar_taxonomia_digital_cliente(df_detalle: pd.DataFrame) -> pd.DataFrame:
    """
    BUSINESS_RULES: Aplica los umbrales corporativos de adopción digital y calcula
    el faltante mínimo en facturación ($) para alcanzar el 70% de penetración digital.
    """
    df = df_detalle.copy()
    if df.empty:
        for c in [
            "Es_NoDigital",
            "Es_Hibrido",
            "Es_FullyDigital",
            "Minimo_Facturacion_70",
            "Categoria_App",
        ]:
            df[c] = pd.Series(dtype="object")
        return df

    pct = df["Pct_MiNegocio"]
    df["Es_NoDigital"] = pct <= 0.01
    df["Es_Hibrido"] = (pct > 0.01) & (pct < 70.0)
    df["Es_FullyDigital"] = pct >= 70.0

    # Categorización textual para reportes y WhatsApp
    cond_nodig = df["Es_NoDigital"]
    cond_hibr = df["Es_Hibrido"]
    df["Categoria_App"] = np.select(
        [cond_nodig, cond_hibr], ["No Digital", "Híbridos"], default="Fully Digital"
    )

    # Ecuación de equilibrio comercial al 70%: ((0.70 * Ventas_Totales) - Ventas_MiNegocio) / 0.30
    numerador_req = (0.70 * df["Ventas_Totales"]) - df["Ventas_MiNegocio"]
    df["Minimo_Facturacion_70"] = (numerador_req / 0.30).clip(lower=0.0).round(2)

    return df


def _incorporar_estructura_comercial_mn(
    df_detalle: pd.DataFrame, padron_vendedores: pd.DataFrame
) -> pd.DataFrame:
    """
    BUSINESS_RULES: Realiza el cruce con el maestro de preventistas para incorporar
    las columnas institucionales 'Nombre' y 'SUP'.
    """
    df = df_detalle.copy()
    if df.empty:
        df["Nombre"] = ""
        df["SUP"] = ""
        return df

    vendedores_df = (
        padron_vendedores.copy()
        if padron_vendedores is not None and not padron_vendedores.empty
        else pd.DataFrame(columns=["CodVendedor", "Nombre", "SUP"])
    )

    if vendedores_df.empty:
        vendedores_df = pd.DataFrame(
            {
                "CodVendedor": pd.Series([0], dtype="Int64"),
                "Nombre": ["SIN ASIGNAR"],
                "SUP": ["GENERAL"],
            }
        )

    vendedores_df["CodVendedor"] = pd.to_numeric(
        vendedores_df["CodVendedor"], errors="coerce"
    ).astype("Int64")
    vendedores_df = vendedores_df[vendedores_df["CodVendedor"] != 20]
    vendedores_df["Nombre"] = vendedores_df["Nombre"].fillna("").astype(str).str.strip()
    vendedores_df["SUP"] = vendedores_df["SUP"].fillna("").astype(str).str.strip()
    vendedores_df = vendedores_df.drop_duplicates("CodVendedor")

    df = df.merge(
        vendedores_df[["CodVendedor", "Nombre", "SUP"]],
        on="CodVendedor",
        how="left",
        suffixes=("_univ", ""),
    )

    if "Nombre" not in df.columns and "Nombre_univ" in df.columns:
        df["Nombre"] = df["Nombre_univ"]

    df["Nombre"] = df["Nombre"].fillna("SIN ASIGNAR").astype(str).str.strip()
    df["SUP"] = df["SUP"].fillna("GENERAL").astype(str).str.strip()

    return df


@st.cache_data(show_spinner=False)
def obtener_matriz_mn_comercial(
    anio: int, mes: int, filtros_globales: dict
) -> pd.DataFrame:
    """
    BUSINESS_RULES (Función Orquestadora Pública de MiNegocio):
    Consume exclusivamente la Capa CORE (ventas operativas con ausencias/reemplazos, clientes y vendedores),
    calcula la adopción digital por cliente, clasifica la taxonomía digital,
    determina el gap de facturación al 70% e incorpora los datos estructurales.
    Retorna la matriz comercial granular a nivel cliente reflejando la titularidad operativa.
    """
    t0 = time.perf_counter()

    # Validación defensiva estricta de parámetros institucionales obligatorios
    if not filtros_globales or not isinstance(filtros_globales, dict):
        raise ValueError(
            "No se recibieron filtros_globales in obtener_matriz_mn_comercial()."
        )

    dia_matinal = filtros_globales.get("dia_matinal")
    if not dia_matinal or not str(dia_matinal).strip():
        raise ValueError("No se encontró 'dia_matinal' dentro de filtros_globales.")

    dia_matinal = str(dia_matinal).strip()
    dia_venta = filtros_globales.get("dia_venta", "01/09/2026")

    # 1. Consumo estricto de CORE (operaciones con soporte de reemplazos)
    datos_operativos = obtener_core_operacion(
        anio, mes, dia_matinal, dia_venta, modo_ajuste="AJUSTADO"
    )
    df_vta_core = datos_operativos["df_vta_operativa"]
    df_clientes_core = obtener_core_clientes()
    padron_vendedores = obtener_core_vendedores()

    # 2. Pipeline analítico modular
    df_vta_mn = _filtrar_ventas_mn_comercial(df_vta_core, anio, mes, dia_matinal)
    df_ventas_cliente = _consolidar_ventas_cliente_mn(df_vta_mn)
    df_detalle = _integrar_universo_y_fuera_de_padron(
        df_clientes_core, df_ventas_cliente, df_vta_mn
    )
    df_detalle = _clasificar_taxonomia_digital_cliente(df_detalle)
    df_detalle = _incorporar_estructura_comercial_mn(df_detalle, padron_vendedores)

    # 3. Contrato de Salida Garantizado a nivel cliente
    columnas_salida = [
        "CodVendedor",
        "Nombre",
        "SUP",
        "Cliente",
        "NombreCliente",
        "DireccionCliente",
        "Ruta",
        "DiaVisita",
        "Taxonomia",
        "Ventas_Totales",
        "Ventas_MiNegocio",
        "Pct_MiNegocio",
        "Es_NoDigital",
        "Es_Hibrido",
        "Es_FullyDigital",
        "Minimo_Facturacion_70",
        "Categoria_App",
    ]

    for col in columnas_salida:
        if col not in df_detalle.columns:
            if col in [
                "Ventas_Totales",
                "Ventas_MiNegocio",
                "Pct_MiNegocio",
                "Minimo_Facturacion_70",
            ]:
                df_detalle[col] = 0.0
            elif col in ["Es_NoDigital", "Es_Hibrido", "Es_FullyDigital"]:
                df_detalle[col] = False
            else:
                df_detalle[col] = ""

    resultado_final = (
        df_detalle[columnas_salida]
        .sort_values(by=["SUP", "Nombre", "Cliente"])
        .reset_index(drop=True)
    )

    print(
        f"[PERF_CORE] obtener_matriz_mn_comercial -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado_final


@st.cache_data(show_spinner=False)
def calcular_resumen_mn_taxonomia(matriz_mn: pd.DataFrame) -> pd.DataFrame:
    """
    BUSINESS_RULES (Función Pública de Resumen por Preventista y Taxonomía):
    Calcula las agregaciones oficiales de cartera, importes, conteos digitales y
    porcentajes de adopción agrupados por CodVendedor, Nombre, SUP y Taxonomia.
    Listo para renderizado en tabla y exportación a Excel.
    """
    if matriz_mn is None or matriz_mn.empty:
        return pd.DataFrame(
            columns=[
                "CodVendedor",
                "Nombre",
                "SUP",
                "Taxonomia",
                "Cartera_Total",
                "Ventas_Totales",
                "Ventas_MiNegocio",
                "Count_NoDigital",
                "Count_Hibrido",
                "Count_FullyDigital",
                "% Adopcion",
                "% No Digital",
                "% Híbridos",
                "% FullyDigital",
            ]
        )

    df = matriz_mn.copy()

    resumen = df.groupby(
        ["CodVendedor", "Nombre", "SUP", "Taxonomia"], as_index=False
    ).agg(
        Cartera_Total=("Cliente", "count"),
        Ventas_Totales=("Ventas_Totales", "sum"),
        Ventas_MiNegocio=("Ventas_MiNegocio", "sum"),
        Count_NoDigital=("Es_NoDigital", lambda x: int(x.sum())),
        Count_Hibrido=("Es_Hibrido", lambda x: int(x.sum())),
        Count_FullyDigital=("Es_FullyDigital", lambda x: int(x.sum())),
    )

    resumen[
        [
            "Cartera_Total",
            "Ventas_Totales",
            "Ventas_MiNegocio",
            "Count_NoDigital",
            "Count_Hibrido",
            "Count_FullyDigital",
        ]
    ] = resumen[
        [
            "Cartera_Total",
            "Ventas_Totales",
            "Ventas_MiNegocio",
            "Count_NoDigital",
            "Count_Hibrido",
            "Count_FullyDigital",
        ]
    ].fillna(0)

    resumen["% Adopcion"] = (
        (
            (resumen["Count_Hibrido"] + resumen["Count_FullyDigital"])
            / resumen["Cartera_Total"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    resumen["% No Digital"] = (
        (resumen["Count_NoDigital"] / resumen["Cartera_Total"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    resumen["% Híbridos"] = (
        (resumen["Count_Hibrido"] / resumen["Cartera_Total"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    resumen["% FullyDigital"] = (
        (resumen["Count_FullyDigital"] / resumen["Cartera_Total"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    resumen["CodVendedor"] = pd.to_numeric(
        resumen["CodVendedor"], errors="coerce"
    ).astype("Int64")
    resumen = resumen.sort_values(
        by=["CodVendedor", "Taxonomia"], ascending=[True, True]
    ).reset_index(drop=True)

    return resumen
