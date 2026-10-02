# modules/business_rules/business_rules_ccc.py
import time
import pandas as pd
import numpy as np
import os

from modules import database as db
from modules.core.core_vendedores import obtener_core_vendedores
from modules.core.core_clientes import obtener_core_clientes
from modules.core.core_operaciones import obtener_core_operacion
from modules.utils import parsear_fecha_robusta


def _filtrar_ventas_ccc_comercial(
    df_vta_core: pd.DataFrame, anio_op: int, mes_op: int, dia_matinal: str
) -> pd.DataFrame:
    """
    BUSINESS_RULES CCC: Aplica filtros institucionales de exclusión y período.
    - Exclusión de comodatos y préstamos.
    - Restricción exclusiva al proveedor PepsiCo.
    - Exclusión del vendedor 20 (Depósito).
    - Filtro de fecha matinal.
    - Clasificación en períodos comerciales (Arrastre, Actual).
    """
    if df_vta_core is None or df_vta_core.empty:
        return pd.DataFrame()

    df = df_vta_core.copy()

    # Normalización de cantidades e importes
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

    col_imp = next(
        (
            c
            for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"]
            if c in df.columns
        ),
        None,
    )
    df["ImporteNeto"] = (
        pd.to_numeric(df[col_imp], errors="coerce").fillna(0.0) if col_imp else 0.0
    )

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

    # Fechas
    if "FechaCarga_dt" not in df.columns:
        df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    if "FechaEntrega_dt" not in df.columns:
        df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    # Filtro N2: Matinal
    if dia_matinal and str(dia_matinal).strip():
        dia_matinal_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
        if pd.notna(dia_matinal_dt):
            es_mes_en_curso = (
                dia_matinal_dt.year == anio_op
                and dia_matinal_dt.month in [mes_op, mes_op + 1]
            )
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

    # Operativo / Operador efectivo
    if "CodVendedorOperativo" not in df.columns:
        df["CodVendedorOperativo"] = df["CodVendedor"]
    df["CodVendedorOperativo"] = pd.to_numeric(
        df["CodVendedorOperativo"], errors="coerce"
    ).astype("Int64")

    # Filtrar solo Arrastre y Actual
    if "Periodo" in df.columns:
        df = df[df["Periodo"].isin(["Arrastre", "Actual"])].copy()

    return df


def _procesar_altas_y_reactivaciones_ccc(anio_op: int, mes_op: int) -> tuple[set, set]:
    """
    BUSINESS_RULES CCC: Parsea la tabla altas para identificar altas nuevas y reactivaciones del período.
    """
    try:
        df_altas_all = db.cargar_tabla_sql("SELECT * FROM altas")
    except Exception:
        df_altas_all = pd.DataFrame()

    if df_altas_all.empty:
        ruta_altas = "ALTAS.xlsx" if os.path.exists("ALTAS.xlsx") else "data/ALTAS.xlsx"
        if os.path.exists(ruta_altas):
            try:
                xls_altas = pd.ExcelFile(ruta_altas)
                dfs = []
                for sh in xls_altas.sheet_names:
                    ds = pd.read_excel(ruta_altas, sheet_name=sh)
                    ds["Origen_Hoja"] = sh
                    dfs.append(ds)
                if dfs:
                    df_altas_all = pd.concat(dfs, ignore_index=True)
            except Exception:
                pass

    altas_nuevas_set = set()
    reactivaciones_set = set()

    if not df_altas_all.empty:
        col_f = next(
            (c for c in df_altas_all.columns if "fecha" in str(c).lower()), None
        )
        col_c = next(
            (
                c
                for c in df_altas_all.columns
                if "codigo" in str(c).lower() or "cliente" in str(c).lower()
            ),
            df_altas_all.columns[0],
        )
        col_est = next(
            (c for c in df_altas_all.columns if "estado" in str(c).lower()), None
        )
        col_orig = next(
            (
                c
                for c in df_altas_all.columns
                if "origen_hoja" in str(c).lower() or "origen" in str(c).lower()
            ),
            "Origen_Hoja",
        )

        if col_f:
            df_altas_all["Fecha_dt"] = parsear_fecha_robusta(df_altas_all[col_f])
            f_mes = df_altas_all[
                (df_altas_all["Fecha_dt"].dt.year == int(anio_op))
                & (df_altas_all["Fecha_dt"].dt.month == int(mes_op))
            ].copy()

            if col_est and "Estado" in f_mes.columns:
                f_mes = f_mes[
                    f_mes["Estado"].astype(str).str.strip().str.upper()
                    != "CIERRE DEFINITIVO"
                ]

            if not f_mes.empty and col_orig in f_mes.columns:
                f_mes["_orig_clean"] = (
                    f_mes[col_orig].astype(str).str.strip().str.casefold()
                )

                crea_rows = f_mes[f_mes["_orig_clean"] == "creacion"]
                acti_rows = f_mes[f_mes["_orig_clean"] == "activacion"]
                inac_rows = f_mes[f_mes["_orig_clean"] == "inactivacion"]

                altas_nuevas_set = set(
                    pd.to_numeric(crea_rows[col_c], errors="coerce")
                    .dropna()
                    .astype("Int64")
                    .tolist()
                )
                activacion_bruta_set = set(
                    pd.to_numeric(acti_rows[col_c], errors="coerce")
                    .dropna()
                    .astype("Int64")
                    .tolist()
                )
                inactivaciones_set = set(
                    pd.to_numeric(inac_rows[col_c], errors="coerce")
                    .dropna()
                    .astype("Int64")
                    .tolist()
                )

                reactivaciones_set = (
                    activacion_bruta_set - altas_nuevas_set
                ) - inactivaciones_set
                altas_nuevas_set = altas_nuevas_set - inactivaciones_set

    return altas_nuevas_set, reactivaciones_set


def _obtener_hoja_ccc_config(
    anio_op: int, mes_op: int, hoja_ccc_param: pd.DataFrame = None
) -> pd.DataFrame:
    """
    BUSINESS_RULES CCC: Recupera la configuración de objetivos porcentuales de cartera desde maestro_ccc.
    """
    try:
        df_ccc_db = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
        if (
            df_ccc_db is not None
            and not df_ccc_db.empty
            and "Anio" in df_ccc_db.columns
            and "Mes" in df_ccc_db.columns
        ):
            df_ccc_per = df_ccc_db[
                (df_ccc_db["Anio"].astype(str) == str(anio_op))
                & (df_ccc_db["Mes"].astype(str) == str(mes_op))
            ]
            if not df_ccc_per.empty:
                hoja_ccc = df_ccc_per
            else:
                hoja_ccc = (
                    hoja_ccc_param if hoja_ccc_param is not None else pd.DataFrame()
                )
        else:
            hoja_ccc = hoja_ccc_param if hoja_ccc_param is not None else pd.DataFrame()
    except Exception:
        hoja_ccc = hoja_ccc_param if hoja_ccc_param is not None else pd.DataFrame()

    if hoja_ccc is None or hoja_ccc.empty:
        hoja_ccc = pd.DataFrame(
            {
                "Taxonomia": ["A", "B", "C", "D"],
                "Porcentaje_Cartera": [80.0, 70.0, 60.0, 50.0],
            }
        )
    else:
        hoja_ccc = hoja_ccc.copy()
        hoja_ccc.columns = hoja_ccc.columns.astype(str).str.strip()
        rename_metas = {}
        for c in hoja_ccc.columns:
            if str(c).lower() in [
                "porcentaje_cartera",
                "porcentaje",
                "pct",
                "obj",
                "objetivo",
                "obj_ccc",
            ]:
                rename_metas[c] = "Porcentaje_Cartera"
            if str(c).lower() in ["taxonomia", "taxonomía", "categoria", "categoría"]:
                rename_metas[c] = "Taxonomia"
        hoja_ccc = hoja_ccc.rename(columns=rename_metas)
        if "Taxonomia" in hoja_ccc.columns:
            hoja_ccc["Taxonomia"] = (
                hoja_ccc["Taxonomia"].astype(str).str.strip().str.upper()
            )
        if "Porcentaje_Cartera" in hoja_ccc.columns:
            hoja_ccc["Porcentaje_Cartera"] = pd.to_numeric(
                hoja_ccc["Porcentaje_Cartera"], errors="coerce"
            ).fillna(80.0)
            hoja_ccc = hoja_ccc[["Taxonomia", "Porcentaje_Cartera"]].drop_duplicates(
                "Taxonomia"
            )
        else:
            hoja_ccc["Porcentaje_Cartera"] = 80.0

    return hoja_ccc


def _construir_modelo_atribucion_ccc(
    df_vta_filtrada: pd.DataFrame, df_universo: pd.DataFrame
) -> pd.DataFrame:
    """
    BUSINESS_RULES CCC: Ejecuta el motor matemático de atribución de suma cero.
    - Titularidad surge exclusivamente del Universo (columna normalizada 'Cliente' y 'CodVendedor').
    - CCC Gerencia sobre total cliente del mes (CantBase >= 3 e ImporteNeto >= 1).
    - Evaluación por Cliente + Operador.
    - Reglas de atribución oficiales:
      * Caso A: Ningún operador cumple -> Propietario_CCC = NULL, Es_CCC_Sin_Responsable = TRUE, Origen_CCC = "SIN_RESPONSABLE"
      * Caso B: Único operador cumple -> Propietario_CCC = operador, Origen_CCC = "TITULAR" | "REEMPLAZO" | "DUMMY99"
      * Caso C: Múltiples operadores cumplen y titular está entre ellos -> Propietario_CCC = titular, Origen_CCC = "TITULAR"
      * Caso D: Múltiples operadores cumplen y titular NO está -> Origen_CCC = "MULTIPLE_CONFLICTO", Es_CCC_Sin_Responsable = TRUE
    """
    if df_universo is None or df_universo.empty:
        return pd.DataFrame()

    universo = df_universo.copy()

    # Normalización segura de la columna Cliente
    col_cli_u = next(
        (
            c
            for c in ["Cliente", "Codigo", "NroCliente", "CodCliente"]
            if c in universo.columns
        ),
        universo.columns[0],
    )
    universo["Cliente"] = pd.to_numeric(universo[col_cli_u], errors="coerce").astype(
        "Int64"
    )

    # Normalización segura de la columna CodVendedor titular
    col_vend_u = next(
        (
            c
            for c in ["CodVendedor", "CodVen", "codven", "cod_vendedor"]
            if c in universo.columns
        ),
        "CodVendedor",
    )
    universo["CodVendedor_Titular"] = pd.to_numeric(
        universo[col_vend_u], errors="coerce"
    ).astype("Int64")

    # Exclusión del vendedor 20 en universo
    universo = (
        universo[universo["CodVendedor_Titular"] != 20]
        .dropna(subset=["Cliente", "CodVendedor_Titular"])
        .copy()
    )

    if df_vta_filtrada is None or df_vta_filtrada.empty:
        res = (
            universo[["Cliente", "CodVendedor_Titular"]]
            .drop_duplicates("Cliente")
            .copy()
        )
        res["CantBase_Total"] = 0.0
        res["ImporteNeto_Total"] = 0.0
        res["Es_CCC_Gerencia"] = False
        res["Propietario_CCC"] = pd.NA
        res["Es_CCC_Sin_Responsable"] = False
        res["Origen_CCC"] = "NO_CCC"
        return res

    vta = df_vta_filtrada.copy()
    col_c_vta = next(
        (
            c
            for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
            if c in vta.columns
        ),
        "Cliente",
    )
    vta["Cliente"] = pd.to_numeric(vta[col_c_vta], errors="coerce").astype("Int64")
    vta["CodVendedorOperativo"] = pd.to_numeric(
        vta["CodVendedorOperativo"], errors="coerce"
    ).astype("Int64")

    # 1. Acumulado Gerencial por Cliente
    gerencial_g = vta.groupby("Cliente", as_index=False).agg(
        CantBase_Total=("CantBase", "sum"), ImporteNeto_Total=("ImporteNeto", "sum")
    )
    gerencial_g["Es_CCC_Gerencia"] = gerencial_g["CantBase_Total"].ge(3) & gerencial_g[
        "ImporteNeto_Total"
    ].ge(1)

    # 2. Acumulado por Cliente + Operador
    operador_g = vta.groupby(["Cliente", "CodVendedorOperativo"], as_index=False).agg(
        CantBase_Operador=("CantBase", "sum"),
        ImporteNeto_Operador=("ImporteNeto", "sum"),
    )
    operador_g["Es_CCC_Operador"] = operador_g["CantBase_Operador"].ge(3) & operador_g[
        "ImporteNeto_Operador"
    ].ge(1)

    operadores_cumplen = operador_g[operador_g["Es_CCC_Operador"] == True].copy()

    base_cli = (
        universo[["Cliente", "CodVendedor_Titular"]]
        .drop_duplicates("Cliente")
        .merge(gerencial_g, on="Cliente", how="left")
    )
    base_cli["CantBase_Total"] = base_cli["CantBase_Total"].fillna(0.0)
    base_cli["ImporteNeto_Total"] = base_cli["ImporteNeto_Total"].fillna(0.0)
    base_cli["Es_CCC_Gerencia"] = base_cli["Es_CCC_Gerencia"].fillna(False)

    propietarios = []
    sin_responsable = []
    origenes = []

    for _, row in base_cli.iterrows():
        cli = row["Cliente"]
        titular = row["CodVendedor_Titular"]
        es_gerencia = row["Es_CCC_Gerencia"]

        if not es_gerencia:
            propietarios.append(pd.NA)
            sin_responsable.append(False)
            origenes.append("NO_CCC")
            continue

        ops_candidatos = operadores_cumplen[operadores_cumplen["Cliente"] == cli][
            "CodVendedorOperativo"
        ].tolist()

        if len(ops_candidatos) == 0:
            propietarios.append(pd.NA)
            sin_responsable.append(True)
            origenes.append("SIN_RESPONSABLE")
        elif len(ops_candidatos) == 1:
            op_unico = ops_candidatos[0]
            propietarios.append(op_unico)
            sin_responsable.append(False)
            if pd.notna(titular) and op_unico == titular:
                origenes.append("TITULAR")
            elif op_unico == 99 or op_unico == -99 or op_unico == 999:
                origenes.append("DUMMY99")
            else:
                origenes.append("REEMPLAZO")
        else:
            # Múltiples operadores cumplen
            if pd.notna(titular) and titular in ops_candidatos:
                propietarios.append(titular)
                sin_responsable.append(False)
                origenes.append("TITULAR")
            else:
                # Caso D: Múltiples operadores cumplen y el titular NO está entre ellos.
                propietarios.append(pd.NA)
                sin_responsable.append(True)
                origenes.append("MULTIPLE_CONFLICTO")

    base_cli["Propietario_CCC"] = pd.Series(propietarios, dtype="Int64")
    base_cli["Es_CCC_Sin_Responsable"] = pd.Series(sin_responsable, dtype="bool")
    base_cli["Origen_CCC"] = pd.Series(origenes, dtype="string")

    return base_cli


def obtener_detalle_clientes_ccc(
    anio: int, mes: int, filtros_globales: dict = None
) -> pd.DataFrame:
    """
    BUSINESS_RULES (Función Pública de Detalle de Clientes CCC):
    Retorna la estructura detallada por cliente con titular, propietario CCC, gerencia, origen y banderas de atribución.
    """
    t0 = time.perf_counter()

    if filtros_globales is None:
        filtros_globales = {}

    dia_matinal = filtros_globales.get("dia_matinal", None)
    dia_venta = filtros_globales.get("dia_venta", None)

    datos_operativos = obtener_core_operacion(
        anio, mes, dia_matinal, dia_venta, modo_ajuste="AJUSTADO"
    )
    df_vta_core = datos_operativos["df_vta_operativa"]
    df_clientes_core = obtener_core_clientes()

    df_vta_filtrada = _filtrar_ventas_ccc_comercial(df_vta_core, anio, mes, dia_matinal)
    df_atribucion = _procesar_atribucion_clientes_completo(
        df_vta_filtrada, df_clientes_core, anio, mes
    )

    print(
        f"[PERF_CORE] obtener_detalle_clientes_ccc -> {time.perf_counter() - t0:.4f} s"
    )
    return df_atribucion


def _procesar_atribucion_clientes_completo(
    df_vta_filtrada: pd.DataFrame,
    df_clientes_core: pd.DataFrame,
    anio_op: int,
    mes_op: int,
) -> pd.DataFrame:
    """
    Ensambla el detalle completo de clientes cruzando universo, atribución CCC, altas, reactivaciones y datos comerciales.
    Garantiza la normalización segura de columnas de cliente y vendedor a partir de contratos reales.
    """
    universo = (
        df_clientes_core.copy()
        if df_clientes_core is not None and not df_clientes_core.empty
        else pd.DataFrame()
    )
    if universo.empty:
        return pd.DataFrame()

    altas_nuevas_set, reactivaciones_set = _procesar_altas_y_reactivaciones_ccc(
        anio_op, mes_op
    )

    col_cli_u = next(
        (
            c
            for c in ["Cliente", "Codigo", "NroCliente", "CodCliente"]
            if c in universo.columns
        ),
        universo.columns[0],
    )
    universo["Cliente"] = pd.to_numeric(universo[col_cli_u], errors="coerce").astype(
        "Int64"
    )

    universo["Es_Alta_Periodo"] = universo["Cliente"].isin(altas_nuevas_set)
    universo["Es_Reactivacion"] = universo["Cliente"].isin(reactivaciones_set)

    df_atrib = _construir_modelo_atribucion_ccc(df_vta_filtrada, universo)

    cols_mantener = [
        c
        for c in [
            "Cliente",
            "NombreCliente",
            "DireccionCliente",
            "DiaVisita",
            "Taxonomia",
            "Ruta",
            "Es_Alta_Periodo",
            "Es_Reactivacion",
        ]
        if c in universo.columns
    ]
    det_merged = df_atrib.merge(
        universo[cols_mantener].drop_duplicates("Cliente"), on="Cliente", how="left"
    )

    vendedores_df = obtener_core_vendedores()
    if not vendedores_df.empty:
        vendedores_df = vendedores_df.rename(
            columns={"CodVendedor": "CodVendedor_Titular"}
        )
        det_merged = det_merged.merge(
            vendedores_df[["CodVendedor_Titular", "Nombre", "SUP"]],
            on="CodVendedor_Titular",
            how="left",
        )

    if "Nombre" not in det_merged.columns:
        det_merged["Nombre"] = "SIN ASIGNAR"
    if "SUP" not in det_merged.columns:
        det_merged["SUP"] = "GENERAL"

    det_merged["Nombre"] = (
        det_merged["Nombre"].fillna("SIN ASIGNAR").astype(str).str.strip()
    )
    det_merged["SUP"] = det_merged["SUP"].fillna("GENERAL").astype(str).str.strip()
    if "Taxonomia" in det_merged.columns:
        det_merged["Taxonomia"] = (
            det_merged["Taxonomia"].fillna("A").astype(str).str.strip().str.upper()
        )
    else:
        det_merged["Taxonomia"] = "A"

    det_merged["Es_CCC_Vendedor"] = (
        det_merged["Propietario_CCC"] == det_merged["CodVendedor_Titular"]
    ).fillna(False)

    return det_merged


def obtener_matriz_ccc_comercial(
    anio: int, mes: int, filtros_globales: dict = None
) -> pd.DataFrame:
    """
    BUSINESS_RULES (Función Orquestadora Pública de CCC):
    Construye la matriz comercial consolidada a nivel de CodVendedor titular y Taxonomía.
    Retorna las columnas obligatorias:
    CodVendedor, Nombre, SUP, Taxonomia, Cartera_Total, Altas, Reactivaciones, Cartera_Neta,
    CCC_Vendedor, CCC_Gerencia, NC, Objetivo_CCC, Pct_Cartera, Pct_Objetivo.
    """
    t0 = time.perf_counter()

    if filtros_globales is None:
        filtros_globales = {}

    dia_matinal = filtros_globales.get("dia_matinal", None)
    dia_venta = filtros_globales.get("dia_venta", None)

    datos_operativos = obtener_core_operacion(
        anio, mes, dia_matinal, dia_venta, modo_ajuste="AJUSTADO"
    )
    df_vta_core = datos_operativos["df_vta_operativa"]
    df_clientes_core = obtener_core_clientes()
    vendedores_df = obtener_core_vendedores()

    df_vta_filtrada = _filtrar_ventas_ccc_comercial(df_vta_core, anio, mes, dia_matinal)
    df_detalle = _procesar_atribucion_clientes_completo(
        df_vta_filtrada, df_clientes_core, anio, mes
    )

    if df_detalle.empty:
        return pd.DataFrame(
            columns=[
                "CodVendedor",
                "Nombre",
                "SUP",
                "Taxonomia",
                "Cartera_Total",
                "Altas",
                "Reactivaciones",
                "Cartera_Neta",
                "CCC_Vendedor",
                "CCC_Gerencia",
                "NC",
                "Objetivo_CCC",
                "Pct_Cartera",
                "Pct_Objetivo",
            ]
        )

    excluidos_set = set(
        df_detalle[df_detalle["Es_Alta_Periodo"] | df_detalle["Es_Reactivacion"]][
            "Cliente"
        ]
        .dropna()
        .tolist()
    )

    cartera_matriz = df_detalle.groupby(
        ["CodVendedor_Titular", "Taxonomia"], as_index=False
    ).agg(
        Cartera_Total=("Cliente", "count"),
        Altas=("Es_Alta_Periodo", lambda x: int(x.sum())),
        Reactivaciones=("Es_Reactivacion", lambda x: int(x.sum())),
        Cartera_Neta=("Cliente", lambda x: int(len(x) - x.isin(excluidos_set).sum())),
        CCC_Vendedor=("Es_CCC_Vendedor", lambda x: int(x.sum())),
        CCC_Gerencia=("Es_CCC_Gerencia", lambda x: int(x.sum())),
    )

    if vendedores_df.empty:
        vendedores_df = pd.DataFrame(
            {"CodVendedor": [0], "Nombre": ["SIN ASIGNAR"], "SUP": ["GENERAL"]}
        )
    else:
        vendedores_df = vendedores_df.rename(
            columns={"CodVendedor": "CodVendedor_Titular"}
        )

    vendedores_df = vendedores_df[
        vendedores_df["CodVendedor_Titular"] != 20
    ].drop_duplicates("CodVendedor_Titular")

    taxonomias_df = pd.DataFrame({"Taxonomia": ["A", "B", "C", "D"]})
    vendedores_df["_k"], taxonomias_df["_k"] = 1, 1
    matriz_base = vendedores_df.merge(taxonomias_df, on="_k").drop(columns="_k")

    reporte = matriz_base.merge(
        cartera_matriz, on=["CodVendedor_Titular", "Taxonomia"], how="left"
    )

    for col_num in [
        "Cartera_Total",
        "Altas",
        "Reactivaciones",
        "Cartera_Neta",
        "CCC_Vendedor",
        "CCC_Gerencia",
    ]:
        reporte[col_num] = reporte[col_num].fillna(0).astype("Int64")

    reporte["NC"] = (
        (reporte["Cartera_Neta"] - reporte["CCC_Vendedor"])
        .clip(lower=0)
        .astype("Int64")
    )

    hoja_ccc = _obtener_hoja_ccc_config(anio, mes)
    reporte = reporte.merge(hoja_ccc, on="Taxonomia", how="left")
    reporte["Porcentaje_Cartera"] = reporte["Porcentaje_Cartera"].fillna(80.0)
    reporte["Objetivo_CCC"] = (
        (reporte["Cartera_Neta"] * (reporte["Porcentaje_Cartera"] / 100.0))
        .round(0)
        .astype("Int64")
    )

    reporte["Pct_Cartera"] = (
        (reporte["CCC_Vendedor"] / reporte["Cartera_Neta"].replace(0, pd.NA))
        .mul(100)
        .fillna(0.0)
        .round(2)
    )
    reporte["Pct_Objetivo"] = (
        (reporte["CCC_Vendedor"] / reporte["Objetivo_CCC"].replace(0, pd.NA))
        .mul(100)
        .fillna(0.0)
        .round(2)
    )

    reporte = reporte.rename(columns={"CodVendedor_Titular": "CodVendedor"})
    reporte["CodVendedor"] = pd.to_numeric(
        reporte["CodVendedor"], errors="coerce"
    ).astype("Int64")
    reporte = reporte.sort_values(
        by=["CodVendedor", "Taxonomia"], ascending=[True, True]
    ).reset_index(drop=True)

    columnas_salida = [
        "CodVendedor",
        "Nombre",
        "SUP",
        "Taxonomia",
        "Cartera_Total",
        "Altas",
        "Reactivaciones",
        "Cartera_Neta",
        "CCC_Vendedor",
        "CCC_Gerencia",
        "NC",
        "Objetivo_CCC",
        "Pct_Cartera",
        "Pct_Objetivo",
    ]

    resultado_final = reporte[[c for c in columnas_salida if c in reporte.columns]]
    print(
        f"[PERF_CORE] obtener_matriz_ccc_comercial -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado_final
