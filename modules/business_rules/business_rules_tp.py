# modules/business_rules/business_rules_tp.py

from __future__ import annotations

import time
from typing import Iterable

import pandas as pd
import streamlit as st

from modules import database as db
from modules.core.core_tp import obtener_core_tp


COLUMNAS_RANKING = [
    "Censados",
    "Clientes_TP",
    "Porcentaje_Cumplimiento_TP",
    "Porcentaje_TP_Sobre_Censados",
    "Puntuacion_Promedio",
]

COLUMNAS_OBJETIVO = [
    "Objetivo_TP",
    "Gap_TP",
    "Excedente_TP",
    "Cumplimiento_Objetivo_TP_Pct",
]


def _lista_normalizada(valores: Iterable | None) -> list[str]:
    if valores is None:
        return []
    if isinstance(valores, str):
        valores = [valores]
    return [str(valor).strip() for valor in valores if str(valor).strip()]


def _periodo_operativo() -> tuple[int | None, int | None]:
    """Lee Año y Mes desde SQLite.parametros sin inventar valores por defecto."""
    try:
        parametros = db.cargar_tabla_sql(
            "SELECT PARAMETRO, VALOR FROM parametros "
            "WHERE PARAMETRO IN ('Año', 'Anio', 'Mes')"
        )
    except Exception:
        return None, None

    if parametros is None or parametros.empty:
        return None, None

    mapa = {
        str(fila["PARAMETRO"]).strip().lower(): fila["VALOR"]
        for _, fila in parametros.iterrows()
    }
    valor_anio = mapa.get("año", mapa.get("anio"))
    valor_mes = mapa.get("mes")
    try:
        return int(float(valor_anio)), int(float(valor_mes))
    except (TypeError, ValueError):
        return None, None


def _snapshot_objetivos(anio: int | None, mes: int | None) -> pd.DataFrame:
    columnas = [
        "Anio",
        "Mes",
        "CodVendedor",
        "Vendedor_Snapshot",
        "Supervisor_Snapshot",
        "Taxonomia",
        "Clientes_Potenciales_Snapshot",
        "Obj_TP_Asignado",
        "Obj_TP_Final",
    ]
    if anio is None or mes is None:
        return pd.DataFrame(columns=columnas)

    try:
        snapshot = db.obtener_snapshot_objetivos_tp(anio, mes)
    except Exception:
        return pd.DataFrame(columns=columnas)

    if snapshot is None or snapshot.empty:
        return pd.DataFrame(columns=columnas)

    resultado = snapshot.copy()
    for columna in columnas:
        if columna not in resultado.columns:
            resultado[columna] = pd.NA

    resultado["CodVendedor"] = pd.to_numeric(
        resultado["CodVendedor"], errors="coerce"
    ).astype("Int64")
    resultado["Taxonomia"] = (
        resultado["Taxonomia"].fillna("").astype(str).str.strip().str.upper()
    )
    resultado["Obj_TP_Final"] = (
        pd.to_numeric(resultado["Obj_TP_Final"], errors="coerce").fillna(0).astype(int)
    )
    resultado["Clientes_Potenciales_Snapshot"] = (
        pd.to_numeric(resultado["Clientes_Potenciales_Snapshot"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    return resultado[columnas].copy()


def _agregar_metricas(df: pd.DataFrame, grupos: list[str]) -> pd.DataFrame:
    columnas = grupos + COLUMNAS_RANKING
    if df is None or df.empty:
        return pd.DataFrame(columns=columnas)

    base = df.copy()
    base["Es_TP"] = base["Es_TP"].fillna(False).astype(bool)
    base["Score"] = pd.to_numeric(base["Score"], errors="coerce").fillna(0.0)

    censados = (
        base.groupby(grupos, dropna=False)["Cliente_id"].nunique().rename("Censados")
    )
    clientes_tp = (
        base.loc[base["Es_TP"]]
        .groupby(grupos, dropna=False)["Cliente_id"]
        .nunique()
        .rename("Clientes_TP")
    )
    puntuacion = (
        base.groupby(grupos, dropna=False)["Score"].mean().rename("Puntuacion_Promedio")
    )

    resultado = pd.concat([censados, clientes_tp, puntuacion], axis=1).reset_index()
    resultado["Clientes_TP"] = resultado["Clientes_TP"].fillna(0).astype(int)
    resultado["Censados"] = resultado["Censados"].fillna(0).astype(int)
    porcentaje = (
        resultado["Clientes_TP"]
        .div(resultado["Censados"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    # Alias histórico preservado para no romper rep_tp_core.py.
    resultado["Porcentaje_Cumplimiento_TP"] = porcentaje
    resultado["Porcentaje_TP_Sobre_Censados"] = porcentaje
    resultado["Puntuacion_Promedio"] = (
        resultado["Puntuacion_Promedio"].fillna(0.0).round(2)
    )
    return resultado[columnas]


def _agregar_objetivos(
    ranking: pd.DataFrame,
    objetivos: pd.DataFrame,
    claves: list[str],
) -> pd.DataFrame:
    if ranking is None or ranking.empty:
        return pd.DataFrame(columns=claves + COLUMNAS_RANKING + COLUMNAS_OBJETIVO)

    resultado = ranking.copy()
    if objetivos is None or objetivos.empty:
        resultado["Objetivo_TP"] = 0
    else:
        agregado = (
            objetivos.groupby(claves, dropna=False, as_index=False)["Obj_TP_Final"]
            .sum()
            .rename(columns={"Obj_TP_Final": "Objetivo_TP"})
        )
        resultado = resultado.merge(agregado, on=claves, how="left")
        resultado["Objetivo_TP"] = (
            pd.to_numeric(resultado["Objetivo_TP"], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    resultado["Gap_TP"] = (
        (resultado["Objetivo_TP"] - resultado["Clientes_TP"]).clip(lower=0).astype(int)
    )
    resultado["Excedente_TP"] = (
        (resultado["Clientes_TP"] - resultado["Objetivo_TP"]).clip(lower=0).astype(int)
    )
    resultado["Cumplimiento_Objetivo_TP_Pct"] = (
        resultado["Clientes_TP"]
        .div(resultado["Objetivo_TP"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    return resultado


def _resultado_vacio(anio: int | None, mes: int | None) -> dict:
    return {
        "df_filtrado": pd.DataFrame(),
        "periodo_objetivos": {"Anio": anio, "Mes": mes},
        "snapshot_disponible": False,
        "alcance_objetivo": "SIN_SNAPSHOT",
        "kpis": {
            "Clientes_Censados": 0,
            "Clientes_TP": 0,
            "Porcentaje_Cumplimiento_TP": 0.0,
            "Porcentaje_TP_Sobre_Censados": 0.0,
            "Puntuacion_Promedio": 0.0,
            "Objetivo_TP": 0,
            "Gap_TP": 0,
            "Excedente_TP": 0,
            "Cumplimiento_Objetivo_TP_Pct": 0.0,
        },
        "ranking_vendedor": pd.DataFrame(
            columns=["CodVendedor", "Vendedor"] + COLUMNAS_RANKING + COLUMNAS_OBJETIVO
        ),
        "ranking_subcanal": pd.DataFrame(columns=["SubCanal"] + COLUMNAS_RANKING),
        "ranking_taxonomia": pd.DataFrame(
            columns=["Taxonomia"] + COLUMNAS_RANKING + COLUMNAS_OBJETIVO
        ),
        "ranking_vendedor_taxonomia": pd.DataFrame(
            columns=["CodVendedor", "Vendedor", "Taxonomia"]
            + COLUMNAS_RANKING
            + ["Clientes_Potenciales_Snapshot"]
            + COLUMNAS_OBJETIVO
        ),
        "tabla_oportunidades": pd.DataFrame(
            columns=[
                "CodVendedor",
                "Vendedor",
                "Cliente_id",
                "RazonSocial",
                "SubCanal",
                "Taxonomia",
                "Score",
                "Es_TP",
            ]
        ),
    }


@st.cache_data(show_spinner=False)
def generar_business_rules_tp(
    vendedores=None,
    subcanales=None,
    taxonomias=None,
    estado_tp="Todos",
) -> dict:
    """
    Consume CORE TP y el snapshot congelado de objetivos del período operativo.

    Reglas:
    - El realizado se calcula con clientes únicos.
    - El objetivo se lee de objetivos_tp_vendedor; nunca se recalcula desde universo.
    - Los filtros de vendedor y taxonomía acotan también el objetivo.
    - Subcanal y estado TP acotan el realizado, pero no alteran el objetivo congelado.
    - Se preservan nombres históricos para mantener compatibilidad con rep_tp_core.py.
    """
    t_start = time.perf_counter()
    anio, mes = _periodo_operativo()

    try:
        core = obtener_core_tp()
    except Exception:
        core = pd.DataFrame()

    if core is None or core.empty:
        resultado = _resultado_vacio(anio, mes)
        print(
            f"[PERF_TP] generar_business_rules_tp = "
            f"{time.perf_counter() - t_start:.2f} s"
        )
        return resultado

    df = core.copy()
    df["CodVendedor"] = pd.to_numeric(df["CodVendedor"], errors="coerce").astype(
        "Int64"
    )
    df["Vendedor"] = df["Vendedor"].fillna("").astype(str).str.strip()
    df["SubCanal"] = df["SubCanal"].fillna("").astype(str).str.strip()
    df["Taxonomia"] = df["Taxonomia"].fillna("").astype(str).str.strip().str.upper()
    df["Es_TP"] = df["Es_TP"].fillna(False).astype(bool)
    df["Score"] = pd.to_numeric(df["Score"], errors="coerce").fillna(0.0)

    lista_vendedores = _lista_normalizada(vendedores)
    lista_subcanales = _lista_normalizada(subcanales)
    lista_taxonomias = [valor.upper() for valor in _lista_normalizada(taxonomias)]

    if lista_vendedores:
        codigos_vendedor = pd.to_numeric(
            pd.Series(lista_vendedores), errors="coerce"
        ).dropna()
        if not codigos_vendedor.empty:
            df = df[df["CodVendedor"].isin(codigos_vendedor.astype(int).tolist())]
        else:
            df = df[df["Vendedor"].isin(lista_vendedores)]
    if lista_subcanales:
        df = df[df["SubCanal"].isin(lista_subcanales)]
    if lista_taxonomias:
        df = df[df["Taxonomia"].isin(lista_taxonomias)]

    estado = str(estado_tp or "Todos").strip().lower()
    if estado in {"tienda perfecta", "tp", "si", "sí", "true", "1"}:
        df = df[df["Es_TP"]]
    elif estado in {"no tienda perfecta", "no tp", "no", "false", "0"}:
        df = df[~df["Es_TP"]]

    snapshot = _snapshot_objetivos(anio, mes)
    objetivos_scope = snapshot.copy()
    if lista_vendedores and not objetivos_scope.empty:
        codigos_vendedor = pd.to_numeric(
            pd.Series(lista_vendedores), errors="coerce"
        ).dropna()
        if not codigos_vendedor.empty:
            objetivos_scope = objetivos_scope[
                objetivos_scope["CodVendedor"].isin(
                    codigos_vendedor.astype(int).tolist()
                )
            ]
        else:
            objetivos_scope = objetivos_scope[
                objetivos_scope["Vendedor_Snapshot"].isin(lista_vendedores)
            ]
    if lista_taxonomias and not objetivos_scope.empty:
        objetivos_scope = objetivos_scope[
            objetivos_scope["Taxonomia"].isin(lista_taxonomias)
        ]

    clientes_censados = int(df["Cliente_id"].nunique()) if not df.empty else 0
    clientes_tp = (
        int(df.loc[df["Es_TP"], "Cliente_id"].nunique()) if not df.empty else 0
    )
    pct_sobre_censados = (
        round(clientes_tp / clientes_censados * 100.0, 2) if clientes_censados else 0.0
    )
    puntuacion_promedio = round(float(df["Score"].mean()), 2) if not df.empty else 0.0
    objetivo_total = (
        int(objetivos_scope["Obj_TP_Final"].sum()) if not objetivos_scope.empty else 0
    )
    gap_total = max(objetivo_total - clientes_tp, 0)
    excedente_total = max(clientes_tp - objetivo_total, 0)
    cumplimiento_objetivo = (
        round(clientes_tp / objetivo_total * 100.0, 2) if objetivo_total else 0.0
    )

    kpis = {
        "Clientes_Censados": clientes_censados,
        "Clientes_TP": clientes_tp,
        # Alias histórico. Semánticamente es TP sobre censados, no objetivo PepsiCo.
        "Porcentaje_Cumplimiento_TP": pct_sobre_censados,
        "Porcentaje_TP_Sobre_Censados": pct_sobre_censados,
        "Puntuacion_Promedio": puntuacion_promedio,
        "Objetivo_TP": objetivo_total,
        "Gap_TP": gap_total,
        "Excedente_TP": excedente_total,
        "Cumplimiento_Objetivo_TP_Pct": cumplimiento_objetivo,
    }

    ranking_vendedor = _agregar_metricas(df, ["CodVendedor", "Vendedor"])
    ranking_vendedor = _agregar_objetivos(
        ranking_vendedor,
        objetivos_scope,
        ["CodVendedor"],
    )
    if not ranking_vendedor.empty:
        ranking_vendedor = ranking_vendedor.sort_values(
            ["Cumplimiento_Objetivo_TP_Pct", "Clientes_TP", "Censados"],
            ascending=[False, False, False],
        ).reset_index(drop=True)

    ranking_subcanal = _agregar_metricas(df, ["SubCanal"])
    if not ranking_subcanal.empty:
        ranking_subcanal = ranking_subcanal.sort_values(
            ["Porcentaje_TP_Sobre_Censados", "Censados"],
            ascending=[False, False],
        ).reset_index(drop=True)

    ranking_taxonomia = _agregar_metricas(df, ["Taxonomia"])
    ranking_taxonomia = _agregar_objetivos(
        ranking_taxonomia,
        objetivos_scope,
        ["Taxonomia"],
    )
    if not ranking_taxonomia.empty:
        ranking_taxonomia = ranking_taxonomia.sort_values("Taxonomia").reset_index(
            drop=True
        )

    ranking_vendedor_taxonomia = _agregar_metricas(
        df, ["CodVendedor", "Vendedor", "Taxonomia"]
    )
    ranking_vendedor_taxonomia = _agregar_objetivos(
        ranking_vendedor_taxonomia,
        objetivos_scope,
        ["CodVendedor", "Taxonomia"],
    )
    if not ranking_vendedor_taxonomia.empty:
        potencial = objetivos_scope[
            ["CodVendedor", "Taxonomia", "Clientes_Potenciales_Snapshot"]
        ].drop_duplicates(["CodVendedor", "Taxonomia"])
        ranking_vendedor_taxonomia = ranking_vendedor_taxonomia.merge(
            potencial,
            on=["CodVendedor", "Taxonomia"],
            how="left",
        )
        ranking_vendedor_taxonomia["Clientes_Potenciales_Snapshot"] = (
            pd.to_numeric(
                ranking_vendedor_taxonomia["Clientes_Potenciales_Snapshot"],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )
        ranking_vendedor_taxonomia = ranking_vendedor_taxonomia.sort_values(
            ["Vendedor", "Taxonomia"]
        ).reset_index(drop=True)

    columnas_oportunidad = [
        "CodVendedor",
        "Vendedor",
        "Cliente_id",
        "RazonSocial",
        "SubCanal",
        "Taxonomia",
        "Score",
        "Es_TP",
    ]
    tabla_oportunidades = df[
        [col for col in columnas_oportunidad if col in df.columns]
    ].copy()
    if not tabla_oportunidades.empty:
        tabla_oportunidades = tabla_oportunidades.sort_values(
            ["Es_TP", "Score", "Vendedor", "Cliente_id"],
            ascending=[True, True, True, True],
        ).reset_index(drop=True)

    filtros_no_asignables = bool(lista_subcanales) or estado != "todos"
    alcance_objetivo = (
        "REFERENCIA_SNAPSHOT_VENDEDOR_TAXONOMIA"
        if filtros_no_asignables
        else "SNAPSHOT_VENDEDOR_TAXONOMIA"
    )

    resultado = {
        "df_filtrado": df,
        "periodo_objetivos": {"Anio": anio, "Mes": mes},
        "snapshot_disponible": not snapshot.empty,
        "alcance_objetivo": alcance_objetivo,
        "kpis": kpis,
        "ranking_vendedor": ranking_vendedor,
        "ranking_subcanal": ranking_subcanal,
        "ranking_taxonomia": ranking_taxonomia,
        "ranking_vendedor_taxonomia": ranking_vendedor_taxonomia,
        "tabla_oportunidades": tabla_oportunidades,
    }

    print(
        f"[PERF_TP] generar_business_rules_tp = {time.perf_counter() - t_start:.2f} s"
    )
    return resultado
