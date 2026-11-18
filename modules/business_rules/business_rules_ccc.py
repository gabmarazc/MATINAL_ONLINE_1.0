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


def _obtener_taxonomias_activas_ccc(anio: int, mes: int) -> pd.DataFrame:
    """
    Obtiene la dimension activa de taxonomias para construir las matrices CCC.

    No aplica fallbacks ni define objetivos. Si el periodo no posee un maestro
    valido con taxonomias activas, falla explicitamente.
    """
    maestro = db.obtener_maestro_taxonomias(anio, mes)

    if maestro is None or maestro.empty:
        raise ValueError(
            "BUSINESS_RULES_CCC: no existe maestro_taxonomias para el periodo "
            f"{int(mes):02d}/{int(anio)}."
        )

    requeridas = {"Taxonomia", "Activa"}
    if not requeridas.issubset(set(maestro.columns)):
        raise ValueError(
            "BUSINESS_RULES_CCC: maestro_taxonomias no cumple el contrato "
            "Taxonomia/Activa."
        )

    trabajo = maestro.copy()
    trabajo["Taxonomia"] = trabajo["Taxonomia"].astype("string").str.strip().str.upper()
    trabajo["Activa"] = pd.to_numeric(trabajo["Activa"], errors="coerce")

    if "Orden" in trabajo.columns:
        trabajo["Orden"] = pd.to_numeric(trabajo["Orden"], errors="coerce")
        trabajo = trabajo.sort_values(["Orden", "Taxonomia"], na_position="last")
    else:
        trabajo = trabajo.sort_values("Taxonomia")

    taxonomias_df = (
        trabajo.loc[
            trabajo["Activa"].eq(1)
            & trabajo["Taxonomia"].notna()
            & trabajo["Taxonomia"].ne(""),
            ["Taxonomia"],
        ]
        .drop_duplicates("Taxonomia")
        .reset_index(drop=True)
    )

    if taxonomias_df.empty:
        raise ValueError(
            "BUSINESS_RULES_CCC: maestro_taxonomias no posee taxonomias activas "
            f"para {int(mes):02d}/{int(anio)}."
        )

    return taxonomias_df


def obtener_auditoria_taxonomias_ccc(
    anio: int, mes: int, filtros_globales: dict = None
) -> pd.DataFrame:
    """
    Audita la calidad de Taxonomia directamente contra SQLite.universo para el
    periodo operativo indicado. No corrige, no imputa y no persiste datos.

    Estados:
    - SIN_TAXONOMIA: valor nulo, vacio o equivalente.
    - TAXONOMIA_NO_REGISTRADA: valor informado no activo en maestro_taxonomias.
    """
    columnas_salida = [
        "Cliente",
        "NombreCliente",
        "CodVendedor",
        "Ruta",
        "Taxonomia_Original",
        "Taxonomia_Normalizada",
        "Estado_Auditoria",
    ]

    maestro = db.obtener_maestro_taxonomias(anio, mes)
    if maestro is None or maestro.empty:
        raise ValueError(
            "BUSINESS_RULES_CCC: no existe maestro_taxonomias para el periodo "
            f"{int(mes):02d}/{int(anio)}."
        )
    requeridas_maestro = {"Taxonomia", "Activa"}
    if not requeridas_maestro.issubset(set(maestro.columns)):
        raise ValueError(
            "BUSINESS_RULES_CCC: maestro_taxonomias no cumple el contrato "
            "Taxonomia/Activa."
        )

    maestro = maestro.copy()
    maestro["Taxonomia"] = maestro["Taxonomia"].astype("string").str.strip().str.upper()
    maestro["Activa"] = pd.to_numeric(maestro["Activa"], errors="coerce")
    activas = set(
        maestro.loc[maestro["Activa"].eq(1), "Taxonomia"].dropna().astype(str).tolist()
    )
    if not activas:
        raise ValueError(
            "BUSINESS_RULES_CCC: maestro_taxonomias no posee taxonomias activas "
            f"para {int(mes):02d}/{int(anio)}."
        )

    try:
        universo = db.cargar_tabla_sql("SELECT * FROM universo")
    except Exception as exc:
        raise ValueError(
            f"BUSINESS_RULES_CCC: no se pudo leer SQLite.universo: {exc}"
        ) from exc
    if universo is None or universo.empty:
        return pd.DataFrame(columns=columnas_salida)

    columnas_universo = list(universo.columns)
    col_cliente = next(
        (
            c
            for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"]
            if c in columnas_universo
        ),
        None,
    )
    if col_cliente is None:
        raise ValueError(
            "BUSINESS_RULES_CCC: no se encontro columna de cliente en universo."
        )

    col_taxonomia = next(
        (
            c
            for c in columnas_universo
            if str(c).strip().lower().replace("_", "") == "segmentoclientecodigo"
            or any(
                clave in str(c).lower()
                for clave in ["taxonomia", "clasificacion", "tax"]
            )
        ),
        None,
    )
    if col_taxonomia is None:
        raise ValueError(
            "BUSINESS_RULES_CCC: no se encontro columna de taxonomia en universo."
        )

    col_vendedor = next(
        (
            c
            for c in columnas_universo
            if any(clave in str(c).lower() for clave in ["codven", "vendedor"])
        ),
        None,
    )
    col_nombre = next(
        (
            c
            for c in [
                "Razon_Social",
                "RazonSocial",
                "NombreCliente",
                "Nombre_Cliente",
                "ClienteDesc",
            ]
            if c in columnas_universo
        ),
        None,
    )
    col_ruta = next(
        (
            c
            for c in [
                "Ruta",
                "CodRuta",
                "Cod_Ruta",
                "Dia_Visita",
                "DiaVisita",
                "Visita",
                "Dia",
            ]
            if c in columnas_universo
        ),
        None,
    )
    col_subsegmento = next(
        (c for c in columnas_universo if str(c).strip().lower() == "subsegmento"),
        None,
    )
    col_subramo = next(
        (c for c in columnas_universo if str(c).strip().lower() == "subramo"),
        None,
    )

    trabajo = pd.DataFrame(index=universo.index)
    trabajo["Cliente"] = pd.to_numeric(universo[col_cliente], errors="coerce").astype(
        "Int64"
    )
    trabajo["CodVendedor"] = (
        pd.to_numeric(universo[col_vendedor], errors="coerce").astype("Int64")
        if col_vendedor
        else pd.Series(pd.NA, index=universo.index, dtype="Int64")
    )
    trabajo["NombreCliente"] = (
        universo[col_nombre].fillna("").astype(str).str.strip() if col_nombre else ""
    )
    trabajo["Ruta"] = (
        universo[col_ruta].fillna("").astype(str).str.strip() if col_ruta else ""
    )
    trabajo["Taxonomia_Original"] = universo[col_taxonomia].fillna("")

    if col_subsegmento:
        trabajo["_subsegmento"] = (
            universo[col_subsegmento].fillna("").astype(str).str.strip().str.casefold()
        )
    if col_subramo:
        trabajo["_subramo"] = (
            universo[col_subramo].fillna("").astype(str).str.strip().str.casefold()
        )

    if "_subsegmento" in trabajo.columns:
        trabajo = trabajo[trabajo["_subsegmento"] != "empleados"].copy()
    if "_subramo" in trabajo.columns:
        trabajo = trabajo[trabajo["_subramo"] != "empleados"].copy()

    trabajo = trabajo[
        trabajo["Cliente"].notna() & trabajo["CodVendedor"].notna()
    ].copy()
    trabajo["Taxonomia_Normalizada"] = (
        trabajo["Taxonomia_Original"].astype(str).str.strip().str.upper()
    )

    valores_sin_taxonomia = {
        "",
        "NAN",
        "NONE",
        "NAT",
        "<NA>",
        "NULL",
        "SIN TAXONOMIA",
        "SIN TAXONOMÍA",
    }
    sin_taxonomia = trabajo["Taxonomia_Normalizada"].isin(valores_sin_taxonomia)
    no_registrada = ~sin_taxonomia & ~trabajo["Taxonomia_Normalizada"].isin(activas)

    auditoria = trabajo[sin_taxonomia | no_registrada].copy()
    if auditoria.empty:
        return pd.DataFrame(columns=columnas_salida)

    auditoria["Estado_Auditoria"] = "TAXONOMIA_NO_REGISTRADA"
    mascara_sin = auditoria["Taxonomia_Normalizada"].isin(valores_sin_taxonomia)
    auditoria.loc[mascara_sin, "Estado_Auditoria"] = "SIN_TAXONOMIA"

    return (
        auditoria[columnas_salida]
        .drop_duplicates(["Cliente", "Estado_Auditoria"])
        .sort_values(["Estado_Auditoria", "CodVendedor", "Cliente"])
        .reset_index(drop=True)
    )


def _filtrar_ventas_ccc_comercial(
    df_vta_core: pd.DataFrame,
    anio_op: int,
    mes_op: int,
    dia_matinal: str,
    aplicar_periodo: bool = True,
) -> pd.DataFrame:
    """
    BUSINESS_RULES CCC: Aplica filtros institucionales de exclusión y período.
    - Exclusión de comodatos y préstamos.
    - Restricción exclusiva al proveedor PepsiCo.
    - Exclusión del vendedor 20 (Depósito).
    - Filtro de fecha matinal.
    - Clasificación en períodos comerciales (Arrastre, Actual) según parámetro.
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

    # Filtrar solo Arrastre y Actual condicionalmente
    if aplicar_periodo and "Periodo" in df.columns:
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
    Recupera exclusivamente los objetivos CCC configurados para el periodo.

    Este contrato no define que taxonomias existen. Esa responsabilidad
    pertenece a maestro_taxonomias. No fabrica catalogos ni porcentajes por
    defecto. Una taxonomia activa puede existir sin objetivo CCC.
    """
    try:
        hoja_ccc = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
    except Exception as exc:
        raise ValueError(
            f"BUSINESS_RULES_CCC: no se pudo leer maestro_ccc: {exc}"
        ) from exc

    if hoja_ccc is None or hoja_ccc.empty:
        return pd.DataFrame(columns=["Taxonomia", "Porcentaje_Cartera"])

    hoja_ccc = hoja_ccc.copy()
    hoja_ccc.columns = hoja_ccc.columns.astype(str).str.strip()

    if "Anio" not in hoja_ccc.columns or "Mes" not in hoja_ccc.columns:
        raise ValueError(
            "BUSINESS_RULES_CCC: maestro_ccc no cumple el contrato Anio/Mes."
        )

    hoja_ccc = hoja_ccc[
        (pd.to_numeric(hoja_ccc["Anio"], errors="coerce") == int(anio_op))
        & (pd.to_numeric(hoja_ccc["Mes"], errors="coerce") == int(mes_op))
    ].copy()

    if hoja_ccc.empty:
        return pd.DataFrame(columns=["Taxonomia", "Porcentaje_Cartera"])

    rename_metas = {}
    for columna in hoja_ccc.columns:
        nombre = str(columna).strip().lower()
        if nombre in [
            "porcentaje_cartera",
            "porcentaje",
            "pct",
            "obj",
            "objetivo",
            "obj_ccc",
        ]:
            rename_metas[columna] = "Porcentaje_Cartera"
        if nombre in ["taxonomia", "taxonomía", "categoria", "categoría"]:
            rename_metas[columna] = "Taxonomia"
    hoja_ccc = hoja_ccc.rename(columns=rename_metas)

    requeridas = {"Taxonomia", "Porcentaje_Cartera"}
    if not requeridas.issubset(set(hoja_ccc.columns)):
        raise ValueError(
            "BUSINESS_RULES_CCC: maestro_ccc no cumple el contrato "
            "Taxonomia/Porcentaje_Cartera."
        )

    hoja_ccc["Taxonomia"] = (
        hoja_ccc["Taxonomia"].astype("string").str.strip().str.upper()
    )
    hoja_ccc["Porcentaje_Cartera"] = pd.to_numeric(
        hoja_ccc["Porcentaje_Cartera"], errors="coerce"
    )

    invalidas = (
        hoja_ccc["Taxonomia"].isna()
        | hoja_ccc["Taxonomia"].eq("")
        | hoja_ccc["Porcentaje_Cartera"].isna()
    )
    if invalidas.any():
        raise ValueError(
            "BUSINESS_RULES_CCC: maestro_ccc contiene taxonomias u objetivos "
            "nulos/invalidos para el periodo solicitado."
        )

    if hoja_ccc["Taxonomia"].duplicated().any():
        duplicadas = sorted(
            hoja_ccc.loc[hoja_ccc["Taxonomia"].duplicated(keep=False), "Taxonomia"]
            .unique()
            .tolist()
        )
        raise ValueError(
            "BUSINESS_RULES_CCC: maestro_ccc contiene taxonomias duplicadas "
            f"para {int(mes_op):02d}/{int(anio_op)}: {duplicadas}."
        )

    fuera_rango = ~hoja_ccc["Porcentaje_Cartera"].between(0, 100, inclusive="both")
    if fuera_rango.any():
        raise ValueError(
            "BUSINESS_RULES_CCC: maestro_ccc contiene porcentajes fuera del "
            "rango 0-100."
        )

    return hoja_ccc[["Taxonomia", "Porcentaje_Cartera"]].reset_index(drop=True)


def _construir_modelo_atribucion_ccc(
    df_vta_filtrada: pd.DataFrame, df_universo: pd.DataFrame
) -> pd.DataFrame:
    """
    BUSINESS_RULES CCC: Ejecuta el motor matemático de atribución de suma cero.
    - Titularidad surge exclusivamente del Universo (columna normalizada 'Cliente' y 'CodVendedor').
    - CCC Gerencia sobre total cliente del mes (CantBase >= 3 e ImporteNeto >= 1).
    - Evaluación por Cliente + Operador.
    - Reglas de atribución oficiales:
      * Propietario_CCC se asigna directamente al CodVendedor_Titular del Universo.
      * Es_CCC_Vendedor se determina validando si el CodVendedor_Titular cumple con la condición de compra CCC (CantBase >= 3 e ImporteNeto >= 1) en las ventas filtradas del período.
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
        res["Propietario_CCC"] = res["CodVendedor_Titular"]
        res["Es_CCC_Sin_Responsable"] = False
        res["Origen_CCC"] = "TITULAR"
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

    if "CodVendedorVigente" in vta.columns:
        vta["CodVendedor_Vta"] = pd.to_numeric(
            vta["CodVendedorVigente"], errors="coerce"
        ).astype("Int64")
    elif "CodVendedorHistorico" in vta.columns:
        vta["CodVendedor_Vta"] = pd.to_numeric(
            vta["CodVendedorHistorico"], errors="coerce"
        ).astype("Int64")
    else:
        col_v_vta = next(
            (
                c
                for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
                if c in vta.columns
            ),
            "CodVendedor",
        )
        vta["CodVendedor_Vta"] = pd.to_numeric(vta[col_v_vta], errors="coerce").astype(
            "Int64"
        )

    if "CodVendedorOperativo" in vta.columns:
        vta["CodVendedor_Op"] = pd.to_numeric(
            vta["CodVendedorOperativo"], errors="coerce"
        ).astype("Int64")
    else:
        vta["CodVendedor_Op"] = vta["CodVendedor_Vta"]

    # 1. Acumulado Gerencial por Cliente
    gerencial_g = vta.groupby("Cliente", as_index=False).agg(
        CantBase_Total=("CantBase", "sum"), ImporteNeto_Total=("ImporteNeto", "sum")
    )
    gerencial_g["Es_CCC_Gerencia"] = gerencial_g["CantBase_Total"].ge(3) & gerencial_g[
        "ImporteNeto_Total"
    ].ge(1)

    # 2. Acumulado por Cliente + Operador
    operador_g = vta.groupby(["Cliente", "CodVendedor_Op"], as_index=False).agg(
        CantBase_Operador=("CantBase", "sum"),
        ImporteNeto_Operador=("ImporteNeto", "sum"),
    )
    operador_g["Es_CCC_Operador"] = operador_g["CantBase_Operador"].ge(3) & operador_g[
        "ImporteNeto_Operador"
    ].ge(1)

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

        ops_candidatos = operador_g[
            (operador_g["Cliente"] == cli) & (operador_g["Es_CCC_Operador"] == True)
        ]["CodVendedor_Op"].tolist()

        if len(ops_candidatos) == 0:
            propietarios.append(titular if pd.notna(titular) else pd.NA)
            sin_responsable.append(False)
            origenes.append("TITULAR")
        elif len(ops_candidatos) == 1:
            op_unico = ops_candidatos[0]
            if op_unico == 99 or op_unico == -99 or op_unico == 999:
                if pd.notna(titular):
                    vta_cli_tit = vta[
                        (vta["Cliente"] == cli) & (vta["CodVendedor_Vta"] == titular)
                    ]
                    sum_cb_tit = vta_cli_tit["CantBase"].sum()
                    sum_in_tit = vta_cli_tit["ImporteNeto"].sum()
                    if sum_cb_tit >= 3 and sum_in_tit >= 1:
                        propietarios.append(titular)
                        sin_responsable.append(False)
                        origenes.append("TITULAR_RECUPERADO_99")
                    else:
                        propietarios.append(99)
                        sin_responsable.append(False)
                        origenes.append("DUMMY99")
                else:
                    propietarios.append(99)
                    sin_responsable.append(False)
                    origenes.append("DUMMY99")
            else:
                propietarios.append(titular if pd.notna(titular) else op_unico)
                sin_responsable.append(False)
                origenes.append("TITULAR")
        else:
            if 99 in ops_candidatos or -99 in ops_candidatos or 999 in ops_candidatos:
                if pd.notna(titular):
                    vta_cli_tit = vta[
                        (vta["Cliente"] == cli) & (vta["CodVendedor_Vta"] == titular)
                    ]
                    sum_cb_tit = vta_cli_tit["CantBase"].sum()
                    sum_in_tit = vta_cli_tit["ImporteNeto"].sum()
                    if sum_cb_tit >= 3 and sum_in_tit >= 1:
                        propietarios.append(titular)
                        sin_responsable.append(False)
                        origenes.append("TITULAR_RECUPERADO_99")
                    else:
                        propietarios.append(titular if pd.notna(titular) else pd.NA)
                        sin_responsable.append(False)
                        origenes.append("TITULAR")
                else:
                    propietarios.append(titular if pd.notna(titular) else pd.NA)
                    sin_responsable.append(False)
                    origenes.append("TITULAR")
            else:
                propietarios.append(titular if pd.notna(titular) else pd.NA)
                sin_responsable.append(False)
                origenes.append("TITULAR")

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

    df_vta_filtrada = _filtrar_ventas_ccc_comercial(
        df_vta_core, anio, mes, dia_matinal, aplicar_periodo=True
    )
    df_atribucion = _procesar_atribucion_clientes_completo(
        df_vta_filtrada, df_clientes_core, anio, mes
    )

    print(
        f"[PERF_CORE] obtener_detalle_clientes_ccc -> {time.perf_counter() - t0:.4f} s"
    )
    return df_atribucion


def obtener_detalle_clientes_ccc_v2(
    anio: int, mes: int, filtros_globales: dict = None
) -> pd.DataFrame:
    """
    BUSINESS_RULES (Función Pública V2 de Detalle de Clientes CCC):
    Utiliza _filtrar_ventas_ccc_comercial con aplicar_periodo=False.
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

    df_vta_filtrada = _filtrar_ventas_ccc_comercial(
        df_vta_core, anio, mes, dia_matinal, aplicar_periodo=False
    )
    df_atribucion = _procesar_atribucion_clientes_completo(
        df_vta_filtrada, df_clientes_core, anio, mes
    )

    print(
        f"[PERF_CORE] obtener_detalle_clientes_ccc_v2 -> {time.perf_counter() - t0:.4f} s"
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
        taxonomia_normalizada = (
            det_merged["Taxonomia"].astype("string").str.strip().str.upper()
        )
        valores_sin_taxonomia = {
            "",
            "NAN",
            "NONE",
            "NAT",
            "<NA>",
            "NULL",
            "SIN TAXONOMÍA",
        }
        det_merged["Taxonomia"] = taxonomia_normalizada.mask(
            taxonomia_normalizada.isna()
            | taxonomia_normalizada.isin(valores_sin_taxonomia),
            "SIN TAXONOMIA",
        )
    else:
        det_merged["Taxonomia"] = "SIN TAXONOMIA"

    if df_vta_filtrada is not None and not df_vta_filtrada.empty:
        vta_chk = df_vta_filtrada.copy()
        col_c_vta = next(
            (
                c
                for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
                if c in vta_chk.columns
            ),
            "Cliente",
        )
        vta_chk["Cliente"] = pd.to_numeric(vta_chk[col_c_vta], errors="coerce").astype(
            "Int64"
        )

        if "CodVendedorVigente" in vta_chk.columns:
            vta_chk["CodVendedor_Vta"] = pd.to_numeric(
                vta_chk["CodVendedorVigente"], errors="coerce"
            ).astype("Int64")
        elif "CodVendedorHistorico" in vta_chk.columns:
            vta_chk["CodVendedor_Vta"] = pd.to_numeric(
                vta_chk["CodVendedorHistorico"], errors="coerce"
            ).astype("Int64")
        else:
            col_v_vta = next(
                (
                    c
                    for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
                    if c in vta_chk.columns
                ),
                "CodVendedor",
            )
            vta_chk["CodVendedor_Vta"] = pd.to_numeric(
                vta_chk[col_v_vta], errors="coerce"
            ).astype("Int64")

        cli_vend_cumple = vta_chk[
            vta_chk["CantBase"].ge(3) & vta_chk["ImporteNeto"].ge(1)
        ][["Cliente", "CodVendedor_Vta"]].drop_duplicates()

        det_merged = det_merged.merge(
            cli_vend_cumple.rename(columns={"CodVendedor_Vta": "CodVendedor_Cumple"}),
            on="Cliente",
            how="left",
        )
        det_merged["Es_CCC_Vendedor"] = (
            det_merged["Propietario_CCC"] == det_merged["CodVendedor_Titular"]
        ).fillna(False)
        if "CodVendedor_Cumple" in det_merged.columns:
            det_merged = det_merged.drop(columns=["CodVendedor_Cumple"])
    else:
        det_merged["Es_CCC_Vendedor"] = False

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

    df_vta_filtrada = _filtrar_ventas_ccc_comercial(
        df_vta_core, anio, mes, dia_matinal, aplicar_periodo=True
    )
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
                "Tiene_Objetivo_CCC",
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

    taxonomias_df = _obtener_taxonomias_activas_ccc(anio, mes)
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
    reporte["Tiene_Objetivo_CCC"] = reporte["Porcentaje_Cartera"].notna()
    reporte["Objetivo_CCC"] = (
        reporte["Cartera_Neta"]
        .mul(reporte["Porcentaje_Cartera"].div(100.0))
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
        reporte["CCC_Vendedor"]
        .div(reporte["Objetivo_CCC"].replace(0, pd.NA))
        .mul(100)
        .round(2)
    )
    reporte.loc[~reporte["Tiene_Objetivo_CCC"], "Pct_Objetivo"] = pd.NA

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
        "Tiene_Objetivo_CCC",
        "Pct_Cartera",
        "Pct_Objetivo",
    ]

    resultado_final = reporte[[c for c in columnas_salida if c in reporte.columns]]
    print(
        f"[PERF_CORE] obtener_matriz_ccc_comercial -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado_final


def obtener_matriz_ccc_comercial_v2(
    anio: int, mes: int, filtros_globales: dict = None
) -> pd.DataFrame:
    """
    BUSINESS_RULES (Función Orquestadora Pública V2 de CCC):
    Construye la matriz comercial consolidada utilizando aplicar_periodo=False.
    Preserva intactas las reglas de negocio, matriz y objetivos.
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

    df_vta_filtrada = _filtrar_ventas_ccc_comercial(
        df_vta_core, anio, mes, dia_matinal, aplicar_periodo=False
    )
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
                "Tiene_Objetivo_CCC",
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

    taxonomias_df = _obtener_taxonomias_activas_ccc(anio, mes)
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
    reporte["Tiene_Objetivo_CCC"] = reporte["Porcentaje_Cartera"].notna()
    reporte["Objetivo_CCC"] = (
        reporte["Cartera_Neta"]
        .mul(reporte["Porcentaje_Cartera"].div(100.0))
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
        reporte["CCC_Vendedor"]
        .div(reporte["Objetivo_CCC"].replace(0, pd.NA))
        .mul(100)
        .round(2)
    )
    reporte.loc[~reporte["Tiene_Objetivo_CCC"], "Pct_Objetivo"] = pd.NA

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
        "Tiene_Objetivo_CCC",
        "Pct_Cartera",
        "Pct_Objetivo",
    ]

    resultado_final = reporte[[c for c in columnas_salida if c in reporte.columns]]
    print(
        f"[PERF_CORE] obtener_matriz_ccc_comercial_v2 -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado_final
