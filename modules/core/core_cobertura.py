# modules/core/core_cobertura.py

import streamlit as st
import pandas as pd

from modules.staging import obtener_staging_rutas
from modules.core.core_operaciones import obtener_core_operacion
from modules.core.core_clientes import obtener_core_clientes
from modules.core.core_vendedores import obtener_core_vendedores

from modules.business_rules.business_rules_cobertura import (
    aplicar_reglas_base_cobertura,
    es_cliente_batalla,
    es_cliente_cubierto,
    obtener_estado_cobertura,
)
from modules.utils import parsear_fecha_robusta


def _normalizar_cartera_cobertura(df_cartera: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza de forma defensiva las claves técnicas de la cartera sin alterar
    las columnas originales ni romper compatibilidad con contratos de STAGING/CORE.
    Garantiza la disponibilidad de _join_cli y _join_vend como Int64.
    """
    if df_cartera is None or df_cartera.empty:
        return pd.DataFrame()

    df_norm = df_cartera.copy()

    if "_join_cli" not in df_norm.columns:
        col_c = next(
            (
                c
                for c in [
                    "Codigo",
                    "Cliente",
                    "CLIENTE",
                    "CodCliente",
                    "Cliente_Cod",
                    "NroCliente",
                ]
                if c in df_norm.columns
            ),
            None,
        )
        if col_c is None:
            raise KeyError("No existe columna válida para cliente")
        df_norm["_join_cli"] = pd.to_numeric(df_norm[col_c], errors="coerce").astype(
            "Int64"
        )
    else:
        df_norm["_join_cli"] = pd.to_numeric(
            df_norm["_join_cli"], errors="coerce"
        ).astype("Int64")

    if "_join_vend" not in df_norm.columns:
        col_v = next(
            (
                c
                for c in [
                    "CodVendedor",
                    "Cod_Vendedor",
                    "CodVen",
                    "Vendedor",
                    "CodVend",
                ]
                if c in df_norm.columns
            ),
            None,
        )
        if col_v is None:
            raise KeyError("No existe columna válida para vendedor")
        df_norm["_join_vend"] = pd.to_numeric(df_norm[col_v], errors="coerce").astype(
            "Int64"
        )
    else:
        df_norm["_join_vend"] = pd.to_numeric(
            df_norm["_join_vend"], errors="coerce"
        ).astype("Int64")

    return df_norm


def resolver_clientes_ruta_dia(df_rutas: pd.DataFrame, dia_matinal: str) -> set:
    """
    Extrae el conjunto de clientes en ruta para la fecha operativa institucional dia_matinal.
    Lógica idéntica a la utilizada en construir_matriz_batalla.
    """
    clientes_visita_hoy = set()
    if df_rutas is not None and not df_rutas.empty:
        col_fecha_r = next(
            (
                c
                for c in ["Fecha", "fecha", "FECHA", "Date", "Dia"]
                if c in df_rutas.columns
            ),
            None,
        )
        col_cod_r = next(
            (
                c
                for c in [
                    "Codigo",
                    "CodCliente",
                    "Cliente",
                    "codigo",
                    "NroCliente",
                    "Cliente_Cod",
                ]
                if c in df_rutas.columns
            ),
            None,
        )

        if col_fecha_r and col_cod_r:
            s_fechas_r = (
                df_rutas[col_fecha_r]
                .astype(str)
                .str.strip()
                .str.replace(" 00:00:00", "", regex=False)
            )
            s_dia_mat = str(dia_matinal).strip().replace(" 00:00:00", "")

            dt_rutas = parsear_fecha_robusta(df_rutas[col_fecha_r])
            dt_mat = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]

            if pd.notna(dt_mat):
                mask_fecha = dt_rutas.dt.date == dt_mat.date()
            else:
                mask_fecha = s_fechas_r == s_dia_mat

            cods_rutas = (
                pd.to_numeric(df_rutas.loc[mask_fecha, col_cod_r], errors="coerce")
                .dropna()
                .astype("Int64")
            )
            clientes_visita_hoy = set(cods_rutas.unique())
    return clientes_visita_hoy


@st.cache_data(show_spinner=False)
def obtener_base_cobertura(
    anio_op: int,
    mes_op: int,
    dia_matinal: str,
    dia_venta: str,
):
    """
    CORE_COBERTURA

    Responsabilidades:
    - Reutilizar CORE_OPERACION
    - Reutilizar CORE_CLIENTES
    - Reutilizar CORE_VENDEDORES
    - Tipar columnas necesarias
    - Construir cartera enriquecida
    - Transformaciones analíticas de cobertura (ElementoCobertura, Agregados, Matriz)
    """

    core_op = obtener_core_operacion(
        anio_op,
        mes_op,
        dia_matinal,
        dia_venta,
    )

    df_vtas = core_op["df_vta_operativa"].copy()
    df_clientes = obtener_core_clientes()
    df_vendedores = obtener_core_vendedores()

    try:
        df_rutas = obtener_staging_rutas()
    except Exception:
        df_rutas = pd.DataFrame()

    clientes_del_dia = resolver_clientes_ruta_dia(df_rutas, dia_matinal)

    if df_vtas.empty:
        df_cartera = pd.DataFrame()
        if (
            not df_clientes.empty
            and not df_vendedores.empty
            and "CodVendedor" in df_clientes.columns
            and "CodVendedor" in df_vendedores.columns
        ):
            df_cartera = df_clientes.merge(
                df_vendedores,
                on="CodVendedor",
                how="inner",
            )

        return {
            "ventas": pd.DataFrame(),
            "clientes": df_clientes,
            "vendedores": df_vendedores,
            "cartera": df_cartera,
            "clientes_del_dia": clientes_del_dia,
        }

    if "CantBase" in df_vtas.columns:
        df_vtas["CantBase"] = pd.to_numeric(
            df_vtas["CantBase"],
            errors="coerce",
        ).fillna(0)

    if "Cliente" in df_vtas.columns:
        df_vtas["Cliente"] = pd.to_numeric(
            df_vtas["Cliente"],
            errors="coerce",
        ).astype("Int64")

    if "CodVendedor" in df_vtas.columns:
        df_vtas["CodVendedor"] = pd.to_numeric(
            df_vtas["CodVendedor"],
            errors="coerce",
        ).astype("Int64")

    df_vtas = aplicar_reglas_base_cobertura(df_vtas)

    df_cartera = pd.DataFrame()
    if (
        not df_clientes.empty
        and not df_vendedores.empty
        and "CodVendedor" in df_clientes.columns
        and "CodVendedor" in df_vendedores.columns
    ):
        df_cartera = df_clientes.merge(
            df_vendedores,
            on="CodVendedor",
            how="inner",
        )

    return {
        "ventas": df_vtas,
        "clientes": df_clientes,
        "vendedores": df_vendedores,
        "cartera": df_cartera,
        "clientes_del_dia": clientes_del_dia,
    }


def aplicar_regla_elemento_cobertura(
    df_vtas: pd.DataFrame,
    df_cartera: pd.DataFrame,
    tipo_cobertura: str,
    df_marcas: pd.DataFrame,
    df_innov: pd.DataFrame,
    mapa_codigo_a_innovacion: dict,
) -> pd.DataFrame:
    if df_vtas is None or df_vtas.empty or df_cartera is None or df_cartera.empty:
        return pd.DataFrame()

    col_c_vta = next(
        (
            c
            for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
            if c in df_vtas.columns
        ),
        "Cliente",
    )
    col_c_cli = next(
        (
            c
            for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente", "Codigo"]
            if c in df_cartera.columns
        ),
        "Cliente",
    )
    col_v_vta = next(
        (
            c
            for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
            if c in df_vtas.columns
        ),
        "CodVendedor",
    )
    col_v_cli = next(
        (
            c
            for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
            if c in df_cartera.columns
        ),
        "CodVendedor",
    )

    df_v = df_vtas.copy()
    df_c = df_cartera.copy()
    df_v["_join_cli"] = pd.to_numeric(df_v[col_c_vta], errors="coerce").astype("Int64")
    df_v["_join_vend"] = pd.to_numeric(df_v[col_v_vta], errors="coerce").astype("Int64")
    df_c["_join_cli"] = pd.to_numeric(df_c[col_c_cli], errors="coerce").astype("Int64")
    df_c["_join_vend"] = pd.to_numeric(df_c[col_v_cli], errors="coerce").astype("Int64")

    df_trabajo = df_v.merge(
        df_c, on=["_join_cli", "_join_vend"], how="inner", suffixes=("", "_cli")
    )

    if df_trabajo.empty:
        return pd.DataFrame()

    if tipo_cobertura == "MARCA":
        if df_marcas is not None and not df_marcas.empty:
            col_m_orig = next(
                (c for c in ["Marca", "MARCA"] if c in df_marcas.columns),
                df_marcas.columns[0],
            )

            marcas_validas = set(
                df_marcas[col_m_orig].astype(str).str.strip().str.upper()
            )

            df_trabajo = df_trabajo[
                df_trabajo["Marca"]
                .astype(str)
                .str.strip()
                .str.upper()
                .isin(marcas_validas)
            ].copy()

            df_trabajo["ElementoCobertura"] = (
                df_trabajo["Marca"].astype(str).str.strip()
            )
        else:
            df_trabajo["ElementoCobertura"] = (
                df_trabajo["Marca"].astype(str).str.strip()
            )

    elif tipo_cobertura == "INNOVACION":
        col_art_vta = next(
            (
                c
                for c in ["Codigo", "CodArticulo", "Cod_Articulo", "Articulo"]
                if c in df_trabajo.columns
            ),
            None,
        )
        if col_art_vta and mapa_codigo_a_innovacion:
            df_trabajo["_cod_art_num"] = pd.to_numeric(
                df_trabajo[col_art_vta], errors="coerce"
            ).astype("Int64")
            df_trabajo["ElementoCobertura"] = (
                df_trabajo["_cod_art_num"]
                .map(mapa_codigo_a_innovacion)
                .fillna("SIN INNOVACION")
            )
            # DEBUG_AUDITORIA_INNOVACIONES
            print("[AUDIT] Columna utilizada:", col_art_vta)
            print("[AUDIT] Total filas df_trabajo:", len(df_trabajo))
            print(
                "[AUDIT] Filas SIN INNOVACION:",
                (df_trabajo["ElementoCobertura"] == "SIN INNOVACION").sum(),
            )
            print("[AUDIT] Top 20 ElementoCobertura:")
            print(df_trabajo["ElementoCobertura"].value_counts(dropna=False).head(20))
        else:
            df_trabajo["ElementoCobertura"] = "SIN INNOVACION"

    else:
        df_trabajo["ElementoCobertura"] = "GENERAL"

    return df_trabajo


def construir_agregado_cobertura(df_trabajo: pd.DataFrame) -> pd.DataFrame:
    if df_trabajo is None or df_trabajo.empty:
        return pd.DataFrame()

    agg_dict = {"CantBase": "sum"}
    if "Direccion" in df_trabajo.columns:
        agg_dict["Direccion"] = "first"
    if "DiaVisita" in df_trabajo.columns:
        agg_dict["DiaVisita"] = "first"

    df_agregado = (
        df_trabajo.groupby(
            [
                "_join_vend",
                "Nombre" if "Nombre" in df_trabajo.columns else "_join_vend",
                "SUP" if "SUP" in df_trabajo.columns else "_join_vend",
                "_join_cli",
                "ElementoCobertura",
            ],
            as_index=False,
        )
        .agg(agg_dict)
        .rename(
            columns={
                "_join_vend": "CodVendedorCore",
                "_join_cli": "ClienteCore",
                "CantBase": "Total_Cant",
            }
        )
    )

    df_agregado["EsCubierto"] = df_agregado["Total_Cant"].apply(
        lambda x: es_cliente_cubierto(x)
    )
    df_agregado["Cobertura_Txt"] = df_agregado["Total_Cant"].apply(
        lambda x: obtener_estado_cobertura(x)
    )

    return df_agregado


def construir_matriz_cobertura(
    df_cartera_m: pd.DataFrame,
    df_agregado: pd.DataFrame,
    elementos_activos: list,
    tipo_cobertura: str,
    mapa_objetivos_empresa: dict,
) -> pd.DataFrame:
    if df_cartera_m is None or df_cartera_m.empty:
        return pd.DataFrame()

    df_cartera_norm = _normalizar_cartera_cobertura(df_cartera_m)

    df_cartera_uniq = df_cartera_norm.drop_duplicates(
        subset=["_join_vend", "_join_cli"]
    ).copy()
    df_cartera_uniq["CodVendedorCore"] = df_cartera_uniq["_join_vend"]
    df_cartera_uniq["ClienteCore"] = df_cartera_uniq["_join_cli"]

    cartera_por_vend = (
        df_cartera_uniq.groupby(["CodVendedorCore", "Nombre", "SUP"])["ClienteCore"]
        .nunique()
        .reset_index(name="Cartera")
        .rename(columns={"CodVendedorCore": "CodVendedor"})
    )

    clientes_activos_set = set(df_cartera_uniq["ClienteCore"].unique())
    vtas_cubiertas = (
        df_agregado[
            df_agregado["ClienteCore"].isin(clientes_activos_set)
            & df_agregado["EsCubierto"]
        ].copy()
        if df_agregado is not None and not df_agregado.empty
        else pd.DataFrame()
    )

    if not vtas_cubiertas.empty:
        pivote_cubiertos = (
            vtas_cubiertas.groupby(["CodVendedorCore", "ElementoCobertura"])[
                "ClienteCore"
            ]
            .nunique()
            .unstack(fill_value=0)
            .reset_index()
            .rename(columns={"CodVendedorCore": "CodVendedor"})
        )
        pivote_cubiertos.columns.name = None
    else:
        pivote_cubiertos = pd.DataFrame(columns=["CodVendedor"])

    df_matriz = cartera_por_vend.merge(
        pivote_cubiertos, on="CodVendedor", how="left"
    ).fillna(0)

    for el in elementos_activos:
        if el not in df_matriz.columns:
            df_matriz[el] = 0.0
        else:
            df_matriz[el] = df_matriz[el].fillna(0.0)
            total_c = df_matriz["Cartera"].replace(0, pd.NA)
            df_matriz[el] = ((df_matriz[el] / total_c).fillna(0.0) * 100.0).round(2)

    df_matriz = df_matriz.sort_values(by="CodVendedor").reset_index(drop=True)

    columnas_matriz = ["CodVendedor", "Nombre", "Cartera", "SUP"] + [
        e for e in elementos_activos if e in df_matriz.columns
    ]
    return df_matriz[columnas_matriz].copy()


def construir_matriz_batalla(
    df_cartera_m: pd.DataFrame,
    df_agregado: pd.DataFrame,
    df_rutas: pd.DataFrame,
    elementos_activos: list,
    dia_matinal: str,
) -> pd.DataFrame:
    columnas_base = [
        "CodVendedor",
        "Nombre",
        "SUP",
        "ClienteCore",
        "Cliente",
        "Direccion",
        "DiaVisita",
        "VisitaHoy",
    ]
    elementos_cols = list(elementos_activos) if elementos_activos else []
    columnas_finales = columnas_base + elementos_cols + ["Faltantes"]

    if df_cartera_m is None or df_cartera_m.empty:
        return pd.DataFrame(columns=columnas_finales)

    df_cartera_norm = _normalizar_cartera_cobertura(df_cartera_m)

    base_clientes = df_cartera_norm.drop_duplicates(
        subset=["_join_vend", "_join_cli"]
    ).copy()

    matriz = pd.DataFrame()
    matriz["CodVendedor"] = base_clientes["_join_vend"]
    matriz["Nombre"] = (
        base_clientes["Nombre"].fillna("").astype(str).str.strip()
        if "Nombre" in base_clientes.columns
        else ""
    )
    matriz["SUP"] = (
        base_clientes["SUP"].fillna("").astype(str).str.strip()
        if "SUP" in base_clientes.columns
        else ""
    )
    matriz["ClienteCore"] = base_clientes["_join_cli"]

    col_razon = "Razon_Social" if "Razon_Social" in base_clientes.columns else None
    col_nombre_cli = (
        "NombreCliente" if "NombreCliente" in base_clientes.columns else None
    )

    s_razon = (
        base_clientes[col_razon].fillna("").astype(str).str.strip()
        if col_razon
        else pd.Series("", index=base_clientes.index)
    )
    s_nombre_cli = (
        base_clientes[col_nombre_cli].fillna("").astype(str).str.strip()
        if col_nombre_cli
        else pd.Series("", index=base_clientes.index)
    )
    s_core = matriz["ClienteCore"].astype(str).str.strip()

    matriz["Cliente"] = (
        s_razon.replace("", pd.NA)
        .combine_first(s_nombre_cli.replace("", pd.NA))
        .combine_first(s_core.replace("", pd.NA))
        .fillna(s_core)
    )

    matriz["Direccion"] = (
        base_clientes["Direccion"].fillna("").astype(str).str.strip()
        if "Direccion" in base_clientes.columns
        else ""
    )
    matriz["DiaVisita"] = (
        base_clientes["DiaVisita"].fillna("SIN DÍA").astype(str).str.strip()
        if "DiaVisita" in base_clientes.columns
        else "SIN DÍA"
    )

    clientes_visita_hoy = resolver_clientes_ruta_dia(df_rutas, dia_matinal)

    matriz["VisitaHoy"] = (
        matriz["ClienteCore"].isin(clientes_visita_hoy).map({True: "SI", False: "NO"})
    )

    if (
        df_agregado is not None
        and not df_agregado.empty
        and "CodVendedorCore" in df_agregado.columns
        and "ClienteCore" in df_agregado.columns
        and "ElementoCobertura" in df_agregado.columns
        and "Total_Cant" in df_agregado.columns
    ):
        pivote_cant = (
            df_agregado.groupby(
                ["CodVendedorCore", "ClienteCore", "ElementoCobertura"]
            )["Total_Cant"]
            .sum()
            .unstack(fill_value=0.0)
            .reset_index()
        )
        pivote_cant.columns.name = None
    else:
        pivote_cant = pd.DataFrame(columns=["CodVendedorCore", "ClienteCore"])

    matriz = matriz.merge(
        pivote_cant,
        left_on=["CodVendedor", "ClienteCore"],
        right_on=["CodVendedorCore", "ClienteCore"],
        how="left",
    )

    if "CodVendedorCore" in matriz.columns:
        matriz = matriz.drop(columns=["CodVendedorCore"])

    for el in elementos_activos:
        if el not in matriz.columns:
            matriz[el] = 0.0
        else:
            matriz[el] = pd.to_numeric(matriz[el], errors="coerce").fillna(0.0)

    elementos_validos = [e for e in elementos_activos if e in matriz.columns]

    if elementos_validos:
        matriz["Faltantes"] = (matriz[elementos_validos] < 3.0).sum(axis=1)
    else:
        matriz["Faltantes"] = 0

    return matriz[columnas_finales].copy()


def construir_dataframe_batalla(
    df_cartera_uniq: pd.DataFrame,
    df_cartera_m: pd.DataFrame,
    df_agregado: pd.DataFrame,
    elementos_batalla: list,
    dia_venta: str,
    clientes_del_dia: set = None,
) -> pd.DataFrame:
    """
    Construye la vista de batalla detallada para clientes no cubiertos.
    Versión optimizada Gold Standard:
    - Indexación O(1) de cartera sin creación masiva de diccionarios intermedios.
    - Iteraciones vectorizadas mediante itertuples(index=False).
    - Cero conversiones de tipos y cero evaluaciones de reglas dentro del doble loop.
    - Preserva firma, columnas y contratos institucionales exactos.
    """
    columnas_esperadas = [
        "Vendedor",
        "Cod Cliente",
        "Cliente",
        "Direccion",
        "DiaVisita",
        "DelDia",
        "Cobertura",
        "Unidades",
        "Estado",
    ]

    if (
        df_agregado is None
        or df_agregado.empty
        or df_cartera_uniq is None
        or df_cartera_uniq.empty
        or not elementos_batalla
    ):
        return pd.DataFrame(columns=columnas_esperadas)

    df_cartera_m_norm = _normalizar_cartera_cobertura(df_cartera_m)

    ventas_unidades_map = df_agregado.set_index(
        ["CodVendedorCore", "ClienteCore", "ElementoCobertura"]
    )["Total_Cant"].to_dict()

    cartera_map = {}
    if not df_cartera_m_norm.empty:
        cols_presentes = set(df_cartera_m_norm.columns)
        has_razon = "Razon_Social" in cols_presentes
        has_nombre_cli = "NombreCliente" in cols_presentes
        has_direccion = "Direccion" in cols_presentes
        has_dia_visita = "DiaVisita" in cols_presentes
        has_nombre_vend = "Nombre" in cols_presentes

        set_rutas = clientes_del_dia if clientes_del_dia is not None else set()

        for row in df_cartera_m_norm.itertuples(index=False):
            v_val = getattr(row, "_join_vend", None)
            c_val = getattr(row, "_join_cli", None)

            if pd.notna(v_val) and pd.notna(c_val):
                key = (int(v_val), int(c_val))
                if key not in cartera_map:
                    razon = getattr(row, "Razon_Social", None) if has_razon else None
                    nombre_cli = (
                        getattr(row, "NombreCliente", None) if has_nombre_cli else None
                    )

                    if pd.notna(razon) and str(razon).strip() != "":
                        c_desc = str(razon).strip()
                    elif pd.notna(nombre_cli) and str(nombre_cli).strip() != "":
                        c_desc = str(nombre_cli).strip()
                    else:
                        c_desc = str(int(c_val))

                    dir_val = getattr(row, "Direccion", None) if has_direccion else None
                    direccion = str(dir_val).strip() if pd.notna(dir_val) else ""

                    dia_vis_val = (
                        getattr(row, "DiaVisita", None) if has_dia_visita else None
                    )
                    dia_visita_cli = (
                        str(dia_vis_val).strip()
                        if pd.notna(dia_vis_val) and str(dia_vis_val).strip() != ""
                        else "SIN DÍA"
                    )

                    nom_vend = getattr(row, "Nombre", None) if has_nombre_vend else None
                    vendedor_nombre = (
                        str(nom_vend).strip()
                        if pd.notna(nom_vend) and str(nom_vend).strip() != ""
                        else str(int(v_val))
                    )

                    del_dia = "SI" if int(c_val) in set_rutas else "NO"

                    cartera_map[key] = {
                        "cliente_desc": c_desc,
                        "direccion": direccion,
                        "dia_visita_cli": dia_visita_cli,
                        "vendedor_nombre": vendedor_nombre,
                        "del_dia": del_dia,
                    }

    col_vend_uniq = (
        "CodVendedorCore"
        if "CodVendedorCore" in df_cartera_uniq.columns
        else (
            "_join_vend" if "_join_vend" in df_cartera_uniq.columns else "CodVendedor"
        )
    )
    col_cli_uniq = (
        "ClienteCore"
        if "ClienteCore" in df_cartera_uniq.columns
        else ("_join_cli" if "_join_cli" in df_cartera_uniq.columns else "Cliente")
    )

    df_claves = (
        df_cartera_uniq[[col_vend_uniq, col_cli_uniq]]
        .dropna()
        .astype(int)
        .drop_duplicates()
    )
    cartera_claves = list(df_claves.itertuples(index=False, name=None))

    registros_nc = []
    set_rutas = clientes_del_dia if clientes_del_dia is not None else set()

    for el in elementos_batalla:
        for cv, cli in cartera_claves:
            und = ventas_unidades_map.get((cv, cli, el), 0.0)

            if es_cliente_batalla(und):
                info_cli = cartera_map.get((cv, cli))
                if info_cli is not None:
                    registros_nc.append(
                        {
                            "Vendedor": info_cli["vendedor_nombre"],
                            "Cod Cliente": cli,
                            "Cliente": info_cli["cliente_desc"],
                            "Direccion": info_cli["direccion"],
                            "DiaVisita": info_cli["dia_visita_cli"],
                            "DelDia": info_cli["del_dia"],
                            "Cobertura": el,
                            "Unidades": und,
                            "Estado": "NO CUBIERTO (< 3 u.)",
                        }
                    )
                else:
                    registros_nc.append(
                        {
                            "Vendedor": str(cv),
                            "Cod Cliente": cli,
                            "Cliente": str(cli),
                            "Direccion": "",
                            "DiaVisita": "SIN DÍA",
                            "DelDia": "SI" if cli in set_rutas else "NO",
                            "Cobertura": el,
                            "Unidades": und,
                            "Estado": "NO CUBIERTO (< 3 u.)",
                        }
                    )

    if not registros_nc:
        return pd.DataFrame(columns=columnas_esperadas)

    return pd.DataFrame(registros_nc)
