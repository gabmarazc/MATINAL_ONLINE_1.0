# modules/business_rules/business_rules_tp.py

import time
import pandas as pd
import streamlit as st
from modules.core.core_tp import obtener_core_tp


@st.cache_data(show_spinner=False)
def generar_business_rules_tp(
    vendedores=None,
    subcanales=None,
    taxonomias=None,
    estado_tp="Todos",
) -> dict:
    """
    BUSINESS RULES TP
    Consume obtener_core_tp(), aplica filtros dinámicos y genera datasets reutilizables:
    kpis, ranking_vendedor, ranking_subcanal, ranking_taxonomia, tabla_oportunidades.
    No aplica lógica visual ni componentes de UI.
    """
    t_start = time.perf_counter()
    df = obtener_core_tp()

    if df is None or df.empty:
        empty_kpis = {
            "Clientes_Censados": 0,
            "Clientes_TP": 0,
            "Porcentaje_Cumplimiento_TP": 0.0,
            "Puntuacion_Promedio": 0.0,
        }
        empty_rv = pd.DataFrame(
            columns=[
                "Vendedor",
                "Censados",
                "Clientes_TP",
                "Porcentaje_Cumplimiento_TP",
                "Puntuacion_Promedio",
            ]
        )
        empty_rs = pd.DataFrame(
            columns=[
                "SubCanal",
                "Censados",
                "Clientes_TP",
                "Porcentaje_Cumplimiento_TP",
                "Puntuacion_Promedio",
            ]
        )
        empty_rt = pd.DataFrame(
            columns=[
                "Taxonomia",
                "Censados",
                "Clientes_TP",
                "Porcentaje_Cumplimiento_TP",
                "Puntuacion_Promedio",
            ]
        )
        empty_op = pd.DataFrame(
            columns=[
                "Vendedor",
                "Cliente_id",
                "RazonSocial",
                "SubCanal",
                "Taxonomia",
                "Score",
                "Es_TP",
            ]
        )

        print(
            f"[PERF_TP] generar_business_rules_tp = "
            f"{time.perf_counter() - t_start:.2f} s"
        )
        return {
            "kpis": empty_kpis,
            "ranking_vendedor": empty_rv,
            "ranking_subcanal": empty_rs,
            "ranking_taxonomia": empty_rt,
            "tabla_oportunidades": empty_op,
        }

    # Aplicación de filtros dinámicos exactamente sobre el DataFrame completo
    if vendedores:
        df = df[df["Vendedor"].isin(vendedores)]
    if subcanales:
        df = df[df["SubCanal"].isin(subcanales)]
    if taxonomias:
        df = df[df["Taxonomia"].isin(taxonomias)]

    if estado_tp == "SI":
        df = df[df["Es_TP"] == True]
    elif estado_tp == "NO":
        df = df[df["Es_TP"] == False]
    elif estado_tp == "Menos de 70%":
        df = df[df["Score"] < 70]
    elif estado_tp == "Entre 70% y 80%":
        df = df[(df["Score"] >= 70) & (df["Score"] < 80)]

    if df.empty:
        empty_kpis = {
            "Clientes_Censados": 0,
            "Clientes_TP": 0,
            "Porcentaje_Cumplimiento_TP": 0.0,
            "Puntuacion_Promedio": 0.0,
        }
        empty_rv = pd.DataFrame(
            columns=[
                "Vendedor",
                "Censados",
                "Clientes_TP",
                "Porcentaje_Cumplimiento_TP",
                "Puntuacion_Promedio",
            ]
        )
        empty_rs = pd.DataFrame(
            columns=[
                "SubCanal",
                "Censados",
                "Clientes_TP",
                "Porcentaje_Cumplimiento_TP",
                "Puntuacion_Promedio",
            ]
        )
        empty_rt = pd.DataFrame(
            columns=[
                "Taxonomia",
                "Censados",
                "Clientes_TP",
                "Porcentaje_Cumplimiento_TP",
                "Puntuacion_Promedio",
            ]
        )
        empty_op = pd.DataFrame(
            columns=[
                "Vendedor",
                "Cliente_id",
                "RazonSocial",
                "SubCanal",
                "Taxonomia",
                "Score",
                "Es_TP",
            ]
        )

        print(
            f"[PERF_TP] generar_business_rules_tp = "
            f"{time.perf_counter() - t_start:.2f} s"
        )
        return {
            "kpis": empty_kpis,
            "ranking_vendedor": empty_rv,
            "ranking_subcanal": empty_rs,
            "ranking_taxonomia": empty_rt,
            "tabla_oportunidades": empty_op,
        }

    # 1. KPIs generales
    total_censados = int(
        df["Cliente_id"].nunique() if df["Cliente_id"].notna().any() else len(df)
    )
    total_tp = int(
        df[df["Es_TP"]]["Cliente_id"].nunique()
        if df["Cliente_id"].notna().any()
        else df["Es_TP"].sum()
    )
    pct_tp_global = round(
        (total_tp / total_censados * 100.0) if total_censados > 0 else 0.0, 2
    )
    promedio_score = round(float(df["Score"].mean()) if not df.empty else 0.0, 2)

    kpis = {
        "Clientes_Censados": total_censados,
        "Clientes_TP": total_tp,
        "Porcentaje_Cumplimiento_TP": pct_tp_global,
        "Puntuacion_Promedio": promedio_score,
    }

    # 2. Ranking por Vendedor
    ranking_vendedor = df.groupby("Vendedor", as_index=False).agg(
        Censados=("Cliente_id", "nunique"),
        Clientes_TP=("Es_TP", lambda x: int(x.sum())),
        Puntuacion_Promedio=("Score", "mean"),
    )
    ranking_vendedor["Porcentaje_Cumplimiento_TP"] = (
        (
            ranking_vendedor["Clientes_TP"]
            / ranking_vendedor["Censados"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    ranking_vendedor["Puntuacion_Promedio"] = ranking_vendedor[
        "Puntuacion_Promedio"
    ].round(2)
    ranking_vendedor = (
        ranking_vendedor[
            [
                "Vendedor",
                "Censados",
                "Clientes_TP",
                "Porcentaje_Cumplimiento_TP",
                "Puntuacion_Promedio",
            ]
        ]
        .sort_values(
            by=["Porcentaje_Cumplimiento_TP", "Censados"], ascending=[False, False]
        )
        .reset_index(drop=True)
    )

    # 3. Ranking por SubCanal
    ranking_subcanal = df.groupby("SubCanal", as_index=False).agg(
        Censados=("Cliente_id", "nunique"),
        Clientes_TP=("Es_TP", lambda x: int(x.sum())),
        Puntuacion_Promedio=("Score", "mean"),
    )
    ranking_subcanal["Porcentaje_Cumplimiento_TP"] = (
        (
            ranking_subcanal["Clientes_TP"]
            / ranking_subcanal["Censados"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    ranking_subcanal["Puntuacion_Promedio"] = ranking_subcanal[
        "Puntuacion_Promedio"
    ].round(2)
    ranking_subcanal = (
        ranking_subcanal[
            [
                "SubCanal",
                "Censados",
                "Clientes_TP",
                "Porcentaje_Cumplimiento_TP",
                "Puntuacion_Promedio",
            ]
        ]
        .sort_values(by="Porcentaje_Cumplimiento_TP", ascending=False)
        .reset_index(drop=True)
    )

    # 4. Ranking por Taxonomia
    ranking_taxonomia = df.groupby("Taxonomia", as_index=False).agg(
        Censados=("Cliente_id", "nunique"),
        Clientes_TP=("Es_TP", lambda x: int(x.sum())),
        Puntuacion_Promedio=("Score", "mean"),
    )
    ranking_taxonomia["Porcentaje_Cumplimiento_TP"] = (
        (
            ranking_taxonomia["Clientes_TP"]
            / ranking_taxonomia["Censados"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    ranking_taxonomia["Puntuacion_Promedio"] = ranking_taxonomia[
        "Puntuacion_Promedio"
    ].round(2)
    ranking_taxonomia = (
        ranking_taxonomia[
            [
                "Taxonomia",
                "Censados",
                "Clientes_TP",
                "Porcentaje_Cumplimiento_TP",
                "Puntuacion_Promedio",
            ]
        ]
        .sort_values(by="Porcentaje_Cumplimiento_TP", ascending=False)
        .reset_index(drop=True)
    )

    # 5. Tabla de oportunidades
    tabla_oportunidades = df[
        [
            "Vendedor",
            "Cliente_id",
            "RazonSocial",
            "SubCanal",
            "Taxonomia",
            "Score",
            "Es_TP",
        ]
    ].copy()
    tabla_oportunidades["Score"] = pd.to_numeric(
        tabla_oportunidades["Score"], errors="coerce"
    ).fillna(0.0)
    tabla_oportunidades = tabla_oportunidades.sort_values(
        by="Score", ascending=True
    ).reset_index(drop=True)

    resultado = {
        "detalle_tp": df.copy(),
        "kpis": kpis,
        "ranking_vendedor": ranking_vendedor,
        "ranking_subcanal": ranking_subcanal,
        "ranking_taxonomia": ranking_taxonomia,
        "tabla_oportunidades": tabla_oportunidades,
    }

    print(
        f"[PERF_TP] generar_business_rules_tp = {time.perf_counter() - t_start:.2f} s"
    )
    return resultado
