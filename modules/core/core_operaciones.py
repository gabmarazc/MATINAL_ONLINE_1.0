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
    obtener_staging_clientes,
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
) -> tuple[dict, dict, dict, dict, dict, float, float]:
    """
    Calcula jornadas equivalentes por vendedor a partir de la carga real de
    clientes programados en RUTAS.

    Regla:
    - Se cuenta la cantidad de clientes unicos por vendedor y fecha.
    - La carga normal del vendedor es la mediana de clientes de sus jornadas
      de lunes a viernes del mes. Si no existen, se usa la mediana de todas
      sus jornadas del mes.
    - Peso de jornada = min(clientes del dia / carga normal, 1.0).
    - Los dias pasados y futuros son la suma de esos pesos.

    De este modo, una jornada reducida de sabado no equivale automaticamente
    a un dia completo. Se conservan las mismas claves publicas para no romper
    consumidores existentes, pero sus valores pasan a ser jornadas
    equivalentes decimales.
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
    rutas_totales_map = {}
    dias_restantes_todo_map = {}
    dias_restantes_ajustado_map = {}
    total_dias_pasados_val = 0.0
    total_dias_restantes_val = 0.0

    if not rutas.empty:
        cols_f_rutas = ["Fecha", "fecha", "Dia", "Date", "FECHA"]
        col_fecha_r = next((c for c in cols_f_rutas if c in rutas.columns), None)
        if not col_fecha_r:
            raise ValueError("No se encontro columna de fecha en la tabla de rutas.")

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
            raise ValueError("No se encontro columna de vendedor en la tabla de rutas.")

        cols_cliente_rutas = [
            "Codigo",
            "Cliente",
            "Cliente_id",
            "Codigo Cliente",
            "CodCliente",
            "NroCliente",
        ]
        col_cliente_r = next(
            (c for c in cols_cliente_rutas if c in rutas.columns), None
        )
        if not col_cliente_r:
            raise ValueError(
                "No se encontro columna de cliente en la tabla de rutas. "
                f"Candidatas={cols_cliente_rutas}; disponibles={list(rutas.columns)}."
            )

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
        rutas["ClienteRuta"] = pd.to_numeric(
            rutas[col_cliente_r], errors="coerce"
        ).astype("Int64")

        rutas_mes = rutas[
            (rutas["Fecha_dt"].dt.year == int(anio))
            & (rutas["Fecha_dt"].dt.month == int(mes))
        ].copy()
        rutas_mes = rutas_mes.dropna(subset=["CodVend", "Fecha_dt", "ClienteRuta"])

        # Una fila logica por cliente, vendedor y fecha antes de medir la carga.
        rutas_mes = rutas_mes.drop_duplicates(
            subset=["CodVend", "Fecha_dt", "ClienteRuta"]
        )

        carga_diaria = rutas_mes.groupby(["CodVend", "Fecha_dt"], as_index=False).agg(
            ClientesRutaDia=("ClienteRuta", "nunique")
        )
        carga_diaria["DiaSemana"] = carga_diaria["Fecha_dt"].dt.dayofweek

        # Referencia normal: mediana lunes-viernes. Fallback: mediana mensual.
        referencia_habil = (
            carga_diaria[carga_diaria["DiaSemana"].le(4)]
            .groupby("CodVend")["ClientesRutaDia"]
            .median()
        )
        referencia_total = carga_diaria.groupby("CodVend")["ClientesRutaDia"].median()
        referencia = referencia_habil.combine_first(referencia_total)
        carga_diaria["ClientesRutaNormal"] = carga_diaria["CodVend"].map(referencia)
        carga_diaria["PesoJornada"] = (
            carga_diaria["ClientesRutaDia"]
            .div(carga_diaria["ClientesRutaNormal"].replace(0, pd.NA))
            .fillna(0.0)
            .clip(lower=0.0, upper=1.0)
        )

        dia_v_dt = parsear_fecha_robusta(pd.Series([dia_venta])).iloc[0]
        corte_date = dia_v_dt.date() if pd.notna(dia_v_dt) else None
        pasadas = (
            carga_diaria[carga_diaria["Fecha_dt"].dt.date <= corte_date]
            if corte_date is not None
            else carga_diaria
        )
        restantes_base = (
            carga_diaria[carga_diaria["Fecha_dt"].dt.date > corte_date]
            if corte_date is not None
            else carga_diaria
        )

        dias_pasados_map = pasadas.groupby("CodVend")["PesoJornada"].sum().to_dict()
        rutas_totales_map = (
            carga_diaria.groupby("CodVend")["PesoJornada"].sum().to_dict()
        )
        dias_restantes_base_map = (
            restantes_base.groupby("CodVend")["PesoJornada"].sum().to_dict()
        )

        codigos_mes = carga_diaria["CodVend"].dropna().unique().tolist()
        for cv in codigos_mes:
            dr_b = float(dias_restantes_base_map.get(cv, 0.0))
            cv_clean_str = str(int(cv)) if pd.notna(cv) else ""
            desc = float(rutas_ajust_map.get(cv_clean_str, 0)) if cv_clean_str else 0.0
            dias_restantes_todo_map[cv] = dr_b
            dias_restantes_ajustado_map[cv] = max(0.0, dr_b - desc)
            dias_restantes_map[cv] = (
                dias_restantes_ajustado_map[cv]
                if modo_ajuste == "AJUSTADO"
                else dias_restantes_todo_map[cv]
            )

        # Totales tecnicos conservados para compatibilidad.
        if dias_pasados_map:
            total_dias_pasados_val = float(
                pd.Series(list(dias_pasados_map.values()), dtype="float64").mean()
            )
        mapa_activo = (
            dias_restantes_ajustado_map
            if modo_ajuste == "AJUSTADO"
            else dias_restantes_todo_map
        )
        if mapa_activo:
            total_dias_restantes_val = float(
                pd.Series(list(mapa_activo.values()), dtype="float64").mean()
            )

    print(
        f"[PERF_CORE] 6) calcular_calendario_y_rutas -> "
        f"{time.perf_counter() - t0:.4f} s"
    )
    return (
        dias_pasados_map,
        dias_restantes_map,
        rutas_totales_map,
        dias_restantes_todo_map,
        dias_restantes_ajustado_map,
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
    y asignaciones operativas procesadas por CORE_OPERACION, manteniendo compatibilidad hacia atrás
    y agregando las vistas 'df_vta_operativa' y 'df_vta_titular' de forma segura.
    """
    t0 = time.perf_counter()
    df_vta = obtener_staging_vta()
    df_rutas = obtener_staging_rutas()
    df_ausencias = obtener_staging_ausencias()
    maestros = obtener_staging_maestros()
    df_clientes = obtener_staging_clientes()

    df_vendedores = (
        maestros.get("maestro_vendedores", pd.DataFrame())
        if isinstance(maestros, dict)
        else pd.DataFrame()
    )

    # REORDENAMIENTO DE PIPELINE DE PERFORMANCE:
    # 1. Ejecutar calcular_ritmo_operativo inmediatamente después de staging
    df_vta_temporal = calcular_ritmo_operativo(df_vta, anio_op, mes_op, dia_matinal)

    # 2. Filtrar y eliminar Fuera de Periodo para reducir volumen de datos procesados
    if not df_vta_temporal.empty and "Periodo" in df_vta_temporal.columns:
        df_vta_temporal = df_vta_temporal[
            df_vta_temporal["Periodo"] != "Fuera de Periodo"
        ].copy()

    # Definición de la vista titular (preserva titularidad inmutable tras filtrado de periodo)
    df_vta_titular = df_vta_temporal.copy()

    # 3. Procesar ausencias y reemplazos sobre el dataframe operativo
    df_vta_procesada = procesar_ausencias_y_reemplazos(df_vta_temporal, df_ausencias)
    df_vta_temporal = df_vta_procesada

    # POC: Enriquecimiento con CodVendedorVigente desde UNIVERSO (staging_clientes)
    if df_clientes is not None and not df_clientes.empty and not df_vta_temporal.empty:
        col_c_vta = next(
            (
                c
                for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
                if c in df_vta_temporal.columns
            ),
            "Cliente",
        )
        col_c_cli = next(
            (
                c
                for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente", "Codigo"]
                if c in df_clientes.columns
            ),
            "Cliente",
        )
        col_v_cli = next(
            (
                c
                for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
                if c in df_clientes.columns
            ),
            "CodVendedor",
        )

        df_vta_temporal["_cli_join"] = pd.to_numeric(
            df_vta_temporal[col_c_vta], errors="coerce"
        ).astype("Int64")
        tmp_cli = df_clientes[[col_c_cli, col_v_cli]].copy()
        tmp_cli["_cli_join"] = pd.to_numeric(
            tmp_cli[col_c_cli], errors="coerce"
        ).astype("Int64")
        tmp_cli["CodVendedorVigente"] = pd.to_numeric(
            tmp_cli[col_v_cli], errors="coerce"
        ).astype("Int64")

        vigente_map = (
            tmp_cli.dropna(subset=["_cli_join"])
            .drop_duplicates("_cli_join")
            .set_index("_cli_join")["CodVendedorVigente"]
        )
        df_vta_temporal["CodVendedorVigente"] = (
            df_vta_temporal["_cli_join"].map(vigente_map).astype("Int64")
        )
        df_vta_temporal = df_vta_temporal.drop(columns=["_cli_join"])
    else:
        if not df_vta_temporal.empty:
            df_vta_temporal["CodVendedorVigente"] = pd.Series(pd.NA, dtype="Int64")

    (
        dias_pasados,
        dias_restantes,
        rutas_totales,
        dias_restantes_todo,
        dias_restantes_ajustado,
        tot_pasados,
        tot_restantes,
    ) = calcular_calendario_y_rutas(
        df_rutas, df_vendedores, anio_op, mes_op, dia_venta, modo_ajuste
    )

    print(f"[PERF_CORE] 7) obtener_core_operacion -> {time.perf_counter() - t0:.4f} s")
    return {
        "df_vta_operativa": df_vta_temporal,
        "df_vta_titular": df_vta_titular,
        "dias_pasados_map": dias_pasados,
        "dias_restantes_map": dias_restantes,
        "rutas_totales_map": rutas_totales,
        "dias_restantes_todo_map": dias_restantes_todo,
        "dias_restantes_ajustado_map": dias_restantes_ajustado,
        "total_dias_pasados": tot_pasados,
        "total_dias_restantes": tot_restantes,
    }
