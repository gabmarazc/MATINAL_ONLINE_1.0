# modules/core/core_operaciones.py
import time
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from modules.staging import (
    obtener_staging_vta,
    obtener_staging_rutas,
    obtener_staging_ausencias,
    obtener_staging_maestros,
)
from modules.utils import parsear_fecha_robusta


@st.cache_data(show_spinner=False)
def procesar_ausencias_y_reemplazos(
    df_vta: pd.DataFrame, df_ausencias: pd.DataFrame
) -> pd.DataFrame:
    """
    Capa CORE: Procesa la tabla de ausencias y asigna la titularidad operativa (CodVendedorOperativo)
    cruzando las fechas de carga y entrega contra las inasistencias registradas.
    Consume directamente las columnas normalizadas provistas por obtener_staging_ausencias().
    """
    t0 = time.perf_counter()
    if df_vta is None or df_vta.empty:
        print(
            f"[PERF_CORE] 4) procesar_ausencias_y_reemplazos (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    df = df_vta.copy()

    if "FechaCarga_dt" not in df.columns:
        df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    if "FechaEntrega_dt" not in df.columns:
        df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    if "CodVendedor" not in df.columns:
        col_vend_tit = next(
            (
                cand
                for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
                if cand in df.columns
            ),
            "CodVendedor",
        )
        df["CodVendedor"] = pd.to_numeric(
            df.get(col_vend_tit, 0), errors="coerce"
        ).astype("Int64")

    # PUNTO 4: Protección explícita ante fechas nulas (NaT) en generación de claves
    mask_carg = df["FechaCarga_dt"].notna()
    mask_ent = df["FechaEntrega_dt"].notna()

    df["ClaveAUS_Carga"] = pd.Series(pd.NA, dtype="string")
    df.loc[mask_carg, "ClaveAUS_Carga"] = (
        df.loc[mask_carg, "CodVendedor"].astype(str)
        + "-"
        + df.loc[mask_carg, "FechaCarga_dt"].dt.strftime("%Y-%m-%d")
    )

    df["ClaveAUS_Entrega"] = pd.Series(pd.NA, dtype="string")
    df.loc[mask_ent, "ClaveAUS_Entrega"] = (
        df.loc[mask_ent, "CodVendedor"].astype(str)
        + "-"
        + df.loc[mask_ent, "FechaEntrega_dt"].dt.strftime("%Y-%m-%d")
    )

    df_aus = (
        df_ausencias.copy()
        if df_ausencias is not None and not df_ausencias.empty
        else pd.DataFrame()
    )
    if not df_aus.empty:
        mask_aus_f = df_aus["Fecha_dt"].notna()
        df_aus["ClaveAUS"] = pd.Series(pd.NA, dtype="string")
        df_aus.loc[mask_aus_f, "ClaveAUS"] = (
            df_aus.loc[mask_aus_f, "CodVend_clean"].astype(str)
            + "-"
            + df_aus.loc[mask_aus_f, "Fecha_dt"].dt.strftime("%Y-%m-%d")
        )

        aus_map = (
            df_aus.dropna(subset=["ClaveAUS", "Reemplazo_clean"])
            .drop_duplicates("ClaveAUS")
            .set_index("ClaveAUS")["Reemplazo_clean"]
        )

        df["Reemplazo"] = (
            df["ClaveAUS_Carga"]
            .map(aus_map)
            .combine_first(df["ClaveAUS_Entrega"].map(aus_map))
        )
        df["CodVendedorOperativo"] = (
            df["Reemplazo"].combine_first(df["CodVendedor"]).astype("Int64")
        )
    else:
        df["Reemplazo"] = pd.NA
        df["CodVendedorOperativo"] = df["CodVendedor"]

    print(
        f"[PERF_CORE] 4) procesar_ausencias_y_reemplazos -> {time.perf_counter() - t0:.4f} s"
    )
    return df


@st.cache_data(show_spinner=False)
def calcular_calendario_y_rutas(
    df_rutas: pd.DataFrame,
    maestro_vendedores: pd.DataFrame,
    anio: int,
    mes: int,
    dia_venta: str,
    modo_ajuste: str = "AJUSTADO",
) -> tuple[dict, dict, int, int]:
    """
    Capa CORE: Calcula los días pasados, rutas totales y días restantes (totales y ajustados) por vendedor
    utilizando el maestro de vendedores y el calendario de rutas.
    """
    t0 = time.perf_counter()
    rutas = (
        df_rutas.copy()
        if df_rutas is not None and not df_rutas.empty
        else pd.DataFrame()
    )
    mv = (
        maestro_vendedores.copy()
        if maestro_vendedores is not None and not maestro_vendedores.empty
        else pd.DataFrame()
    )

    rutas_ajust_map = {}
    if not mv.empty:
        col_cod_v = next(
            (c for c in mv.columns if "cod" in str(c).strip().lower()), mv.columns[0]
        )
        col_rutas_ajust = next(
            (
                c
                for c in mv.columns
                if str(c).strip().lower()
                in ["rutas_ajustadas", "rutasajustadas", "ajustadas"]
            ),
            None,
        )
        if col_rutas_ajust:
            mv["CodClean"] = (
                pd.to_numeric(mv[col_cod_v], errors="coerce")
                .astype("Int64")
                .astype(str)
                .str.strip()
            )
            rutas_ajust_map = (
                mv.set_index("CodClean")[col_rutas_ajust]
                .fillna(0)
                .astype(int)
                .to_dict()
            )

    dias_pasados_map = {}
    dias_restantes_map = {}
    total_dias_pasados_val = 0
    total_dias_restantes_val = 0

    if not rutas.empty:
        # PUNTO 2: Validaciones explícitas de columnas en lugar de accesos posicionales
        cols_f_rutas = ["Fecha", "fecha", "Dia", "Date", "FECHA"]
        col_fecha_r = next((c for c in cols_f_rutas if c in rutas.columns), None)
        if not col_fecha_r:
            raise ValueError("No se encontró columna de fecha en la tabla de rutas.")

        cols_v_rutas = [
            "codven",
            "CodVen",
            "CodVendedor",
            "Vendedor",
            "Cod_Vendedor",
            "CODVEN",
        ]
        col_vend_r = next((c for c in cols_v_rutas if c in rutas.columns), None)
        if not col_vend_r:
            raise ValueError("No se encontró columna de vendedor en la tabla de rutas.")

        s_fechas = (
            rutas[col_fecha_r]
            .astype(str)
            .str.strip()
            .str.replace(" 00:00:00", "", regex=False)
        )
        dt_directo = pd.to_datetime(s_fechas, format="%Y-%m-%d", errors="coerce")
        dt_invertido = pd.to_datetime(s_fechas, format="%Y-%d-%m", errors="coerce")

        if (
            (dt_directo.dt.year == int(anio)) & (dt_directo.dt.month == int(mes))
        ).sum() >= (
            (dt_invertido.dt.year == int(anio)) & (dt_invertido.dt.month == int(mes))
        ).sum():
            rutas["Fecha_dt"] = dt_directo
        else:
            rutas["Fecha_dt"] = dt_invertido

        rutas["CodVend"] = pd.to_numeric(rutas[col_vend_r], errors="coerce").astype(
            "Int64"
        )
        rutas_mes = rutas[
            (
                (rutas["Fecha_dt"].dt.year == int(anio))
                & (rutas["Fecha_dt"].dt.month == int(mes))
            )
        ].copy()

        dia_v_dt = parsear_fecha_robusta(pd.Series([dia_venta])).iloc[0]
        corte_date = dia_v_dt.date() if pd.notna(dia_v_dt) else None

        pasadas = (
            rutas_mes[rutas_mes["Fecha_dt"].dt.date <= corte_date]
            if corte_date is not None
            else rutas_mes
        )
        restantes_base = (
            rutas_mes[rutas_mes["Fecha_dt"].dt.date > corte_date]
            if corte_date is not None
            else rutas_mes
        )

        dias_pasados_map = pasadas.groupby("CodVend")["Fecha_dt"].nunique().to_dict()
        dias_restantes_base_map = (
            restantes_base.groupby("CodVend")["Fecha_dt"].nunique().to_dict()
        )

        for cv, dr_b in dias_restantes_base_map.items():
            cv_clean_str = str(int(cv)) if pd.notna(cv) else ""
            desc = rutas_ajust_map.get(cv_clean_str, 0) if cv_clean_str else 0
            if modo_ajuste == "AJUSTADO":
                dias_restantes_map[cv] = max(0, dr_b - desc)
            else:
                dias_restantes_map[cv] = dr_b

        total_dias_pasados_val = int(pasadas["Fecha_dt"].nunique())
        if dias_restantes_map:
            total_dias_restantes_val = int(
                pd.Series(list(dias_restantes_map.values())).mean()
            )
        else:
            total_dias_restantes_val = int(restantes_base["Fecha_dt"].nunique())

    print(
        f"[PERF_CORE] 6) calcular_calendario_y_rutas -> {time.perf_counter() - t0:.4f} s"
    )
    return (
        dias_pasados_map,
        dias_restantes_map,
        total_dias_pasados_val,
        total_dias_restantes_val,
    )


@st.cache_data(show_spinner=False)
def calcular_ritmo_operativo(
    df_vta: pd.DataFrame, anio_op: int, mes_op: int, dia_matinal: str
) -> pd.DataFrame:
    """
    Capa CORE (Clasificador de Períodos Operativos):
    Aplica el filtro corporativo de fecha matinal y clasifica las transacciones
    en períodos comerciales institucionales (Arrastre, Actual, Futuro).
    No calcula KPIs, proyecciones ni ritmos (responsabilidad de Business Rules / Reportes).
    """
    t0 = time.perf_counter()
    if df_vta is None or df_vta.empty:
        print(
            f"[PERF_CORE] 5) calcular_ritmo_operativo (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    df = df_vta.copy()

    if "FechaCarga_dt" not in df.columns:
        df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    if "FechaEntrega_dt" not in df.columns:
        df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    dia_matinal_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(dia_matinal_dt):
        es_mes_en_curso = dia_matinal_dt.year == anio_op and dia_matinal_dt.month in [
            mes_op,
            mes_op + 1,
        ]
        if es_mes_en_curso:
            df = df[df["FechaCarga_dt"].dt.date < dia_matinal_dt.date()]

    df["MesCarga"] = df["FechaCarga_dt"].dt.month
    df["AñoCarga"] = df["FechaCarga_dt"].dt.year
    df["MesEntrega"] = df["FechaEntrega_dt"].dt.month
    df["AñoEntrega"] = df["FechaEntrega_dt"].dt.year

    mes_ant = 12 if mes_op == 1 else mes_op - 1
    anio_ant = anio_op - 1 if mes_op == 1 else anio_op

    mes_sig = 1 if mes_op == 12 else mes_op + 1
    anio_sig = anio_op + 1 if mes_op == 12 else anio_op

    ac, mc = df["AñoCarga"], df["MesCarga"]
    ae, me = df["AñoEntrega"], df["MesEntrega"]

    cond_arr = (
        (ac == anio_ant) & (mc == mes_ant) & (ae == anio_op) & (me == mes_op)
    ).fillna(False)
    cond_act = (
        (ac == anio_op) & (mc == mes_op) & (ae == anio_op) & (me == mes_op)
    ).fillna(False)
    cond_fut = (
        (ac == anio_op) & (mc == mes_op) & (ae == anio_sig) & (me == mes_sig)
    ).fillna(False)

    df["Periodo"] = np.select(
        [cond_arr, cond_act, cond_fut],
        ["Arrastre", "Actual", "Futuro"],
        default="Fuera de Periodo",
    )

    print(
        f"[PERF_CORE] 5) calcular_ritmo_operativo -> {time.perf_counter() - t0:.4f} s"
    )
    return df


@st.cache_data(show_spinner=False)
def obtener_core_operacion(
    anio_op: int,
    mes_op: int,
    dia_matinal: str,
    dia_venta: str,
    modo_ajuste: str = "AJUSTADO",
) -> dict:
    """
    Capa CORE (Función Orquestadora Pública): Retorna un diccionario consolidado con todas las métricas
    y asignaciones operativas procesadas por CORE_OPERACION.
    """
    t0 = time.perf_counter()
    df_vta = obtener_staging_vta()
    df_rutas = obtener_staging_rutas()
    df_ausencias = obtener_staging_ausencias()
    maestros = obtener_staging_maestros()

    df_vendedores = (
        maestros.get("maestro_vendedores", pd.DataFrame())
        if isinstance(maestros, dict)
        else pd.DataFrame()
    )

    df_vta_procesada = procesar_ausencias_y_reemplazos(df_vta, df_ausencias)
    df_vta_temporal = calcular_ritmo_operativo(
        df_vta_procesada, anio_op, mes_op, dia_matinal
    )
    dias_pasados, dias_restantes, tot_pasados, tot_restantes = (
        calcular_calendario_y_rutas(
            df_rutas, df_vendedores, anio_op, mes_op, dia_venta, modo_ajuste
        )
    )

    print(f"[PERF_CORE] 7) obtener_core_operacion -> {time.perf_counter() - t0:.4f} s")
    return {
        "df_vta_operativa": df_vta_temporal,
        "dias_pasados_map": dias_pasados,
        "dias_restantes_map": dias_restantes,
        "total_dias_pasados": tot_pasados,
        "total_dias_restantes": tot_restantes,
    }
