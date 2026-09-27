# modules/rep_gerencial.py
import io
import time
import os
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import tarjeta_metrica_html, parsear_fecha_robusta
from modules.rep_ccc import _calcular_base_ccc


def _preparar_ventas_gerencial_puro(df_vta, anio_operativo, mes_operativo, dia_matinal):
    """
    Pipeline corporativo exclusivo y dedicado para el Tablero Gerencial.
    Aplica N1 (EMPLEADOS) y N2 (PEPSICO, COMODATOS, MATINAL, PERIODO)
    utilizando estrictamente el CodVendedor original inmutable, sin ausencias ni reemplazos.
    """
    t_start = time.perf_counter()
    df_corp = db.obtener_df_maestro_corporativo()
    df = (
        df_corp.copy()
        if not df_corp.empty
        else (
            df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame()
        )
    )

    if df.empty:
        return df

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

    if "TipoDeVenta" in df.columns:
        tipos_excluidos = [
            "Comodato Devolución",
            "Comodato Ficticio",
            "Comodato Ficticio Devolución",
            "Comodato Préstamo",
        ]
        df = df[~df["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)]

    if "Proveedor" in df.columns:
        df = df[
            df["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    dia_matinal_dt = pd.to_datetime(
        str(dia_matinal), format="%d/%m/%Y", errors="coerce"
    )
    if pd.isna(dia_matinal_dt):
        dia_matinal_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]

    if pd.notna(dia_matinal_dt):
        es_mes_en_curso = (
            dia_matinal_dt.year == anio_operativo
            and dia_matinal_dt.month in [mes_operativo, mes_operativo + 1]
        )
        if es_mes_en_curso:
            df = df[df["FechaCarga_dt"].dt.date < dia_matinal_dt.date()]

    col_vend_tit = next(
        (
            cand
            for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
            if cand in df.columns
        ),
        "CodVendedor",
    )
    if col_vend_tit not in df.columns:
        df[col_vend_tit] = 0

    df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype("Int64")

    col_m = next((c for c in ["Marca", "MARCA", "marca"] if c in df.columns), None)
    df["Marca"] = (
        df[col_m].fillna("").astype(str).str.strip().str.upper()
        if col_m
        else "SIN MARCA"
    )

    col_rent = "SegmentoRentabilidad" if "SegmentoRentabilidad" in df.columns else None
    col_rubro = "Rubro" if "Rubro" in df.columns else None

    sr = (
        df.get(col_rent, pd.Series("", index=df.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .str.title()
        if col_rent
        else pd.Series("", index=df.index)
    )
    rubro = (
        df.get(col_rubro, pd.Series("", index=df.index))
        .fillna("")
        .astype(str)
        .str.strip()
        if col_rubro
        else pd.Series("", index=df.index)
    )

    cond_gold = sr.isin(["Platinum", "Gold"]).fillna(False)
    cond_silver = sr.isin(["Silver", "Bronze"]).fillna(False)

    gold_val = "GOLD " + rubro
    silver_val = "SILVER " + rubro
    df["SEGMENTO"] = np.select(
        [cond_gold, cond_silver],
        [gold_val.str.strip(), silver_val.str.strip()],
        default="SIN SEGMENTO",
    )

    df["MesCarga"] = df["FechaCarga_dt"].dt.month
    df["AñoCarga"] = df["FechaCarga_dt"].dt.year
    df["MesEntrega"] = df["FechaEntrega_dt"].dt.month
    df["AñoEntrega"] = df["FechaEntrega_dt"].dt.year

    mes_ant = 12 if mes_operativo == 1 else mes_operativo - 1
    anio_ant = anio_operativo - 1 if mes_operativo == 1 else anio_operativo

    mes_sig = 1 if mes_operativo == 12 else mes_operativo + 1
    anio_sig = anio_operativo + 1 if mes_operativo == 12 else anio_operativo

    ac, mc = df["AñoCarga"], df["MesCarga"]
    ae, me = df["AñoEntrega"], df["MesEntrega"]

    cond_arr = (
        (ac == anio_ant)
        & (mc == mes_ant)
        & (ae == anio_operativo)
        & (me == mes_operativo)
    ).fillna(False)
    cond_act = (
        (ac == anio_operativo)
        & (mc == mes_operativo)
        & (ae == anio_operativo)
        & (me == mes_operativo)
    ).fillna(False)
    cond_fut = (
        (ac == anio_operativo)
        & (mc == mes_operativo)
        & (ae == anio_sig)
        & (me == mes_sig)
    ).fillna(False)

    df["Periodo"] = np.select(
        [cond_arr, cond_act, cond_fut],
        ["Arrastre", "Actual", "Futuro"],
        default="Fuera de Periodo",
    )

    print(
        f"[PERF_INTERNAL] _preparar_ventas_gerencial_puro = {time.perf_counter() - t_start:.2f} s"
    )
    return df


def _calcular_ccc_taxonomia_gerencial(
    df_vta, df_universo, maestro_v, anio_op, mes_op, dia_matinal, sup_seleccionado
):
    t_start = time.perf_counter()
    try:
        t_s1 = time.perf_counter()
        maestro_ccc = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
        print(
            f"[PERF_INTERNAL] consulta_sqlite_maestro_ccc = {time.perf_counter() - t_s1:.2f} s"
        )
    except Exception:
        maestro_ccc = pd.DataFrame(
            columns=["Taxonomia", "Porcentaje_Cartera", "Obj_CCC_Pepsico"]
        )

    if (
        not maestro_ccc.empty
        and "Mes" in maestro_ccc.columns
        and "Anio" in maestro_ccc.columns
    ):
        mc_per = maestro_ccc[
            (maestro_ccc["Mes"].astype(str) == str(mes_op))
            & (maestro_ccc["Anio"].astype(str) == str(anio_op))
        ]
        if not mc_per.empty:
            maestro_ccc = mc_per

    mapa_obj_pepsico = {}
    if not maestro_ccc.empty and "Taxonomia" in maestro_ccc.columns:
        for _, row in maestro_ccc.iterrows():
            tax = str(row["Taxonomia"]).strip().upper()
            if "Obj_CCC_Pepsico" in maestro_ccc.columns and pd.notna(
                row.get("Obj_CCC_Pepsico")
            ):
                mapa_obj_pepsico[tax] = float(row["Obj_CCC_Pepsico"])

    t_s2 = time.perf_counter()
    reporte_base_ccc, _ = _calcular_base_ccc(
        df_vta, df_universo, maestro_v, maestro_ccc, anio_op, mes_op, dia_matinal
    )
    print(f"[PERF_INTERNAL] _calcular_base_ccc = {time.perf_counter() - t_s2:.2f} s")

    if reporte_base_ccc.empty:
        empty_df = pd.DataFrame(
            columns=[
                "Taxonomia",
                "Cartera_Neta",
                "Obj_Pepsico",
                "Cump_Pepsico_Pct",
                "Obj_Fuerza_Ventas",
                "Cump_Fuerza_Ventas_Pct",
                "Avance_CCC",
            ]
        )
        empty_disp = pd.DataFrame(
            columns=[
                "Taxonomía",
                "Cartera Neta (NC)",
                "Obj de Pepsico",
                "% Cump Obj Pepsico",
                "Objetivo a Fuerza de Ventas",
                "% Cump Obj Fuerza de Ventas",
                "Avance CCC",
            ]
        )
        return empty_df, empty_disp

    if sup_seleccionado != "TODOS" and "SUP" in reporte_base_ccc.columns:
        reporte_base_ccc = reporte_base_ccc[
            reporte_base_ccc["SUP"].astype(str).str.strip()
            == str(sup_seleccionado).strip()
        ].copy()

    t_s3 = time.perf_counter()
    res_tax = reporte_base_ccc.groupby("Taxonomia", as_index=False).agg(
        Cartera_Neta=("Cartera_Neta", "sum"),
        Avance_CCC=("CCC", "sum"),
        Obj_Fuerza_Ventas=("Objetivo_CCC", "sum"),
    )

    res_tax["Obj_Pepsico"] = res_tax["Taxonomia"].map(mapa_obj_pepsico).fillna(0.0)
    res_tax["Obj_Fuerza_Ventas"] = pd.to_numeric(
        res_tax["Obj_Fuerza_Ventas"], errors="coerce"
    ).fillna(0.0)

    res_tax["Cump_Pepsico_Pct"] = (
        (res_tax["Avance_CCC"] / res_tax["Obj_Pepsico"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    res_tax["Cump_Fuerza_Ventas_Pct"] = (
        (res_tax["Avance_CCC"] / res_tax["Obj_Fuerza_Ventas"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    df_res = res_tax[
        [
            "Taxonomia",
            "Cartera_Neta",
            "Obj_Pepsico",
            "Cump_Pepsico_Pct",
            "Obj_Fuerza_Ventas",
            "Cump_Fuerza_Ventas_Pct",
            "Avance_CCC",
        ]
    ].copy()

    df_display = df_res.copy()
    df_display["Cartera_Neta"] = df_display["Cartera_Neta"].apply(
        lambda x: f"{int(x):,}"
    )
    df_display["Obj_Pepsico"] = df_display["Obj_Pepsico"].apply(
        lambda x: f"{int(round(x)):,}"
    )
    df_display["Cump_Pepsico_Pct"] = df_display["Cump_Pepsico_Pct"].apply(
        lambda x: f"{x:,.2f}%"
    )
    df_display["Obj_Fuerza_Ventas"] = df_display["Obj_Fuerza_Ventas"].apply(
        lambda x: f"{int(round(x)):,}"
    )
    df_display["Cump_Fuerza_Ventas_Pct"] = df_display["Cump_Fuerza_Ventas_Pct"].apply(
        lambda x: f"{x:,.2f}%"
    )
    df_display["Avance_CCC"] = df_display["Avance_CCC"].apply(lambda x: f"{int(x):,}")

    df_display = df_display.rename(
        columns={
            "Taxonomia": "Taxonomía",
            "Cartera_Neta": "Cartera Neta (NC)",
            "Obj_Pepsico": "Obj de Pepsico",
            "Cump_Pepsico_Pct": "% Cump Obj Pepsico",
            "Obj_Fuerza_Ventas": "Objetivo a Fuerza de Ventas",
            "Cump_Fuerza_Ventas_Pct": "% Cump Obj Fuerza de Ventas",
            "Avance_CCC": "Avance CCC",
        }
    )
    print(
        f"[PERF_INTERNAL] agrupaciones_ccc_gerencial = {time.perf_counter() - t_s3:.2f} s"
    )
    print(
        f"[PERF_INTERNAL] _calcular_ccc_taxonomia_gerencial = {time.perf_counter() - t_start:.2f} s"
    )

    return df_res, df_display


def _calcular_minegocio_taxonomia_detallado(
    df_vta_prep_gerencial,
    df_universo,
    maestro_v,
    anio_op,
    mes_op,
    dia_matinal,
    sup_seleccionado,
):
    t_start = time.perf_counter()
    try:
        t_s1 = time.perf_counter()
        df_ausencias = db.cargar_tabla_sql("SELECT * FROM ausencias")
        print(
            f"[PERF_INTERNAL] consulta_sqlite_ausencias_mn = {time.perf_counter() - t_s1:.2f} s"
        )
    except Exception:
        df_ausencias = pd.DataFrame()

    from modules.rep_MN import preparar_ventas_mn

    t_s2 = time.perf_counter()
    df_vta_mn = preparar_ventas_mn(
        df_vta_prep_gerencial, df_ausencias, anio_op, mes_op, dia_matinal
    )
    print(
        f"[PERF_INTERNAL] preparar_ventas_mn_gerencial = {time.perf_counter() - t_s2:.2f} s"
    )

    vtas_per = (
        df_vta_mn[df_vta_mn["Periodo"].isin(["Arrastre", "Actual"])].copy()
        if not df_vta_mn.empty and "Periodo" in df_vta_mn.columns
        else df_vta_mn.copy()
    )

    col_pesos = next(
        (
            c
            for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"]
            if c in vtas_per.columns
        ),
        None,
    )
    col_kilos = next(
        (c for c in ["PesoKg", "PESOKG", "Kilos"] if c in vtas_per.columns), None
    )
    col_cant = next(
        (
            c
            for c in ["CantBase", "CANTBASE", "Cantidad", "Unidades"]
            if c in vtas_per.columns
        ),
        None,
    )

    vtas_per["_gross_calc"] = (
        pd.to_numeric(vtas_per[col_pesos], errors="coerce").fillna(0.0)
        if col_pesos
        else 0.0
    )
    vtas_per["_kilos_calc"] = (
        pd.to_numeric(vtas_per[col_kilos], errors="coerce").fillna(0.0)
        if col_kilos
        else 0.0
    )
    vtas_per["_cant_calc"] = (
        pd.to_numeric(vtas_per[col_cant], errors="coerce").fillna(0.0)
        if col_cant
        else 0.0
    )

    col_cli_vta = next(
        (
            c
            for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
            if c in vtas_per.columns
        ),
        "Cliente",
    )
    vtas_per["Cliente"] = pd.to_numeric(vtas_per[col_cli_vta], errors="coerce").astype(
        "Int64"
    )

    vtas_per["_mn_gross_val"] = np.where(
        vtas_per["Es_MiNegocio"], vtas_per["_gross_calc"], 0.0
    )
    vtas_per["_mn_kilos_val"] = np.where(
        vtas_per["Es_MiNegocio"], vtas_per["_kilos_calc"], 0.0
    )

    t_s3 = time.perf_counter()
    cli_agg = vtas_per.groupby("Cliente", as_index=False).agg(
        Gross_Total=("_gross_calc", "sum"),
        Gross_MN=("_mn_gross_val", "sum"),
        Kilos_Total=("_kilos_calc", "sum"),
        Kilos_MN=("_mn_kilos_val", "sum"),
        Total_Cant=("_cant_calc", "sum"),
        Total_Imp=("_gross_calc", "sum"),
    )
    cli_agg["Es_CCC"] = cli_agg["Total_Cant"].ge(3) & cli_agg["Total_Imp"].ge(1)
    cli_agg["Pct_MN_Gross"] = (
        (cli_agg["Gross_MN"] / cli_agg["Gross_Total"].replace(0, pd.NA))
        .mul(100.0)
        .clip(lower=0, upper=100)
        .fillna(0.0)
    )

    cond_nodig = (cli_agg["Pct_MN_Gross"] <= 0.01).fillna(False)
    cond_hibr = (
        (cli_agg["Pct_MN_Gross"] > 0.01) & (cli_agg["Pct_MN_Gross"] < 70.0)
    ).fillna(False)
    cli_agg["Categoria_Digital"] = np.select(
        [cond_nodig, cond_hibr], ["No Digital", "Híbridos"], default="Fully Digital"
    )
    print(f"[PERF_INTERNAL] groupby_clientes_mn = {time.perf_counter() - t_s3:.2f} s")

    univ = df_universo.copy() if df_universo is not None else pd.DataFrame()
    if not univ.empty:
        col_c_u = next(
            (
                c
                for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"]
                if c in univ.columns
            ),
            univ.columns[0],
        )
        univ["Cliente"] = pd.to_numeric(univ[col_c_u], errors="coerce").astype("Int64")

        tax_col = next(
            (
                c
                for c in univ.columns
                if "taxonomia" in str(c).lower()
                or "segmentoclientecodigo" in str(c).lower()
            ),
            None,
        )
        if tax_col:
            univ["Taxonomia"] = (
                univ[tax_col].fillna("").astype(str).str.strip().str.upper()
            )
        else:
            univ["Taxonomia"] = "A"

        pos_v_u = next(
            (
                c
                for c in univ.columns
                if any(k in str(c).lower() for k in ["codven", "vendedor"])
            ),
            None,
        )
        if pos_v_u:
            univ["CodVendedor"] = pd.to_numeric(univ[pos_v_u], errors="coerce").astype(
                "Int64"
            )

        univ = univ[univ["Taxonomia"].isin(["A", "B", "C", "D"])].dropna(
            subset=["Cliente"]
        )

    vend_map = pd.DataFrame()
    if maestro_v is not None and not maestro_v.empty:
        c_cod = next(
            (c for c in maestro_v.columns if "cod" in str(c).lower()),
            maestro_v.columns[0],
        )
        c_sup = next(
            (c for c in maestro_v.columns if "sup" in str(c).lower()),
            maestro_v.columns[2]
            if len(maestro_v.columns) > 2
            else maestro_v.columns[0],
        )
        vend_map["CodVendedor"] = pd.to_numeric(
            maestro_v[c_cod], errors="coerce"
        ).astype("Int64")
        vend_map["SUP"] = maestro_v[c_sup].fillna("").astype(str).str.strip()
        vend_map = vend_map.drop_duplicates("CodVendedor")

    if not univ.empty and not vend_map.empty and "CodVendedor" in univ.columns:
        univ = univ.merge(vend_map, on="CodVendedor", how="left")
    elif not univ.empty:
        univ["SUP"] = "GENERAL"

    if sup_seleccionado != "TODOS" and not univ.empty and "SUP" in univ.columns:
        univ = univ[
            univ["SUP"].astype(str).str.strip() == str(sup_seleccionado).strip()
        ].copy()

    # Alineación estricta basada en el Universo completo (Left Join desde el Universo)
    t_s4 = time.perf_counter()
    if not univ.empty:
        df_merged = univ.merge(cli_agg, on="Cliente", how="left")
    else:
        df_merged = pd.DataFrame(
            columns=[
                "Taxonomia",
                "Cliente",
                "Gross_Total",
                "Gross_MN",
                "Kilos_Total",
                "Kilos_MN",
                "Es_CCC",
                "Categoria_Digital",
            ]
        )

    df_merged["Gross_Total"] = df_merged["Gross_Total"].fillna(0.0)
    df_merged["Gross_MN"] = df_merged["Gross_MN"].fillna(0.0)
    df_merged["Kilos_Total"] = df_merged["Kilos_Total"].fillna(0.0)
    df_merged["Kilos_MN"] = df_merged["Kilos_MN"].fillna(0.0)
    df_merged["Es_CCC"] = df_merged["Es_CCC"].fillna(False)
    df_merged["Categoria_Digital"] = df_merged["Categoria_Digital"].fillna("No Digital")

    tax_base = pd.DataFrame({"Taxonomia": ["A", "B", "C", "D"]})

    gross_g = df_merged.groupby("Taxonomia", as_index=False).agg(
        Gross_Total=("Gross_Total", "sum"), Gross_MN=("Gross_MN", "sum")
    )
    res_gross = tax_base.merge(gross_g, on="Taxonomia", how="left").fillna(0.0)

    try:
        df_v20_total = (
            df_vta_prep_gerencial[
                (df_vta_prep_gerencial["CodVendedor"] == 20)
                & df_vta_prep_gerencial["Periodo"].isin(["Arrastre", "Actual"])
            ].copy()
            if not df_vta_prep_gerencial.empty
            else pd.DataFrame()
        )

        if not df_v20_total.empty:
            val_v20_gross = (
                pd.to_numeric(df_v20_total[col_pesos], errors="coerce").sum()
                if col_pesos
                else 0.0
            )
            suma_gross_actual = res_gross["Gross_Total"].sum()
            if suma_gross_actual > 0:
                for idx, row in res_gross.iterrows():
                    proporcion = row["Gross_Total"] / suma_gross_actual
                    res_gross.loc[idx, "Gross_Total"] += val_v20_gross * proporcion
    except Exception:
        pass

    res_gross["Adopcion_Gross_Pct"] = (
        (res_gross["Gross_MN"] / res_gross["Gross_Total"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    kilos_g = df_merged.groupby("Taxonomia", as_index=False).agg(
        Kilos_Total=("Kilos_Total", "sum"), Kilos_MN=("Kilos_MN", "sum")
    )
    res_kilos = tax_base.merge(kilos_g, on="Taxonomia", how="left").fillna(0.0)
    res_kilos["Adopcion_Kilos_Pct"] = (
        (res_kilos["Kilos_MN"] / res_kilos["Kilos_Total"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    ccc_cartera = df_merged.groupby("Taxonomia", as_index=False).agg(
        Cartera_Total=("Cliente", "count"), CCC_Total=("Es_CCC", lambda x: int(x.sum()))
    )

    ccc_compradores = (
        df_merged[df_merged["Es_CCC"] == True]
        .groupby(["Taxonomia", "Categoria_Digital"], as_index=False)
        .agg(Cantidad=("Cliente", "count"))
    )
    ccc_pivot = ccc_compradores.pivot_table(
        index="Taxonomia", columns="Categoria_Digital", values="Cantidad", fill_value=0
    ).reset_index()
    ccc_pivot.columns.name = None

    for cat in ["No Digital", "Híbridos", "Fully Digital"]:
        if cat not in ccc_pivot.columns:
            ccc_pivot[cat] = 0

    res_ccc = (
        tax_base.merge(ccc_cartera, on="Taxonomia", how="left")
        .merge(ccc_pivot, on="Taxonomia", how="left")
        .fillna(0)
    )
    res_ccc[
        ["Cartera_Total", "CCC_Total", "No Digital", "Híbridos", "Fully Digital"]
    ] = res_ccc[
        ["Cartera_Total", "CCC_Total", "No Digital", "Híbridos", "Fully Digital"]
    ].astype(int)
    print(
        f"[PERF_INTERNAL] merge_y_pivots_mn_detallado = {time.perf_counter() - t_s4:.2f} s"
    )
    print(
        f"[PERF_INTERNAL] _calcular_minegocio_taxonomia_detallado = {time.perf_counter() - t_start:.2f} s"
    )

    return res_gross, res_kilos, res_ccc


@st.cache_data(show_spinner=False)
def _calcular_motor_gerencial_global(
    df_vta,
    df_universo,
    df_rutas,
    df_ausencias,
    anio_op,
    mes_op,
    dia_matinal,
    dia_venta,
    sup_seleccionado,
    modo_ajuste,
    huella_global,
):
    t_start = time.perf_counter()
    try:
        t_s1 = time.perf_counter()
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        print(
            f"[PERF_INTERNAL] consulta_sqlite_maestro_vendedores_ger = {time.perf_counter() - t_s1:.2f} s"
        )
        if not maestro_v.empty and "Mes" in maestro_v.columns:
            mv_per = maestro_v[
                (maestro_v["Mes"].astype(str) == str(mes_op))
                & (maestro_v["Anio"].astype(str) == str(anio_op))
            ]
            if not mv_per.empty:
                maestro_v = mv_per
    except Exception:
        maestro_v = pd.DataFrame()

    try:
        t_s2 = time.perf_counter()
        maestro_s = db.cargar_tabla_sql(
            "SELECT * FROM maestro_segmentos ORDER BY rowid ASC"
        )
        print(
            f"[PERF_INTERNAL] consulta_sqlite_maestro_segmentos = {time.perf_counter() - t_s2:.2f} s"
        )
    except Exception:
        maestro_s = pd.DataFrame()

    try:
        t_s3 = time.perf_counter()
        maestro_cebe = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        print(
            f"[PERF_INTERNAL] consulta_sqlite_maestro_cebe = {time.perf_counter() - t_s3:.2f} s"
        )
        if not maestro_cebe.empty and "Mes" in maestro_cebe.columns:
            mc_per = maestro_cebe[
                (maestro_cebe["Mes"].astype(str) == str(mes_op))
                & (maestro_cebe["Anio"].astype(str) == str(anio_op))
            ]
            if not mc_per.empty:
                maestro_cebe = mc_per
    except Exception:
        maestro_cebe = pd.DataFrame()

    df_marcas_maestro = pd.DataFrame()

    if maestro_v.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            [],
            {},
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            0,
            0,
        )

    col_sup_v = next(
        (c for c in maestro_v.columns if "sup" in str(c).strip().lower()),
        maestro_v.columns[2] if len(maestro_v.columns) > 2 else maestro_v.columns[0],
    )
    col_cod_v = next(
        (c for c in maestro_v.columns if "cod" in str(c).strip().lower()),
        maestro_v.columns[0],
    )

    maestro_v["Cod_Clean"] = (
        pd.to_numeric(maestro_v[col_cod_v], errors="coerce")
        .astype("Int64")
        .astype(str)
        .str.strip()
    )
    maestro_v["Sup_Clean"] = maestro_v[col_sup_v].fillna("").astype(str).str.strip()
    sup_map = maestro_v.set_index("Cod_Clean")["Sup_Clean"].to_dict()

    col_rutas_ajust_m = next(
        (
            c
            for c in maestro_v.columns
            if str(c).strip().lower()
            in ["rutas_ajustadas", "rutasajustadas", "ajustadas"]
        ),
        None,
    )
    rutas_ajust_map_g = (
        maestro_v.set_index("Cod_Clean")[col_rutas_ajust_m]
        .fillna(0)
        .astype(int)
        .to_dict()
        if col_rutas_ajust_m
        else {}
    )

    # Operativo con filtro matinal estricto
    t_s4 = time.perf_counter()
    df_vta_prep_ger = _preparar_ventas_gerencial_puro(
        df_vta, anio_op, mes_op, dia_matinal
    )
    print(
        f"[PERF_INTERNAL] _preparar_ventas_gerencial_puro_operativo = {time.perf_counter() - t_s4:.2f} s"
    )

    # Futuro sin restricción matinal
    t_s5 = time.perf_counter()
    df_corp_raw = db.obtener_df_maestro_corporativo()
    df_vta_prep_ger_full = _preparar_ventas_gerencial_puro(
        df_corp_raw if not df_corp_raw.empty else df_vta, anio_op, mes_op, "01/01/2000"
    )
    print(
        f"[PERF_INTERNAL] _preparar_ventas_gerencial_puro_full = {time.perf_counter() - t_s5:.2f} s"
    )

    rutas = (
        df_rutas.copy()
        if df_rutas is not None and not df_rutas.empty
        else pd.DataFrame()
    )
    dias_pasados_map = {}
    dias_restantes_map = {}
    total_dias_pasados_val = 0
    total_dias_restantes_val = 0

    t_s6 = time.perf_counter()
    if not rutas.empty:
        col_fecha_r = next(
            (
                c
                for c in ["Fecha", "fecha", "Dia", "Date", "FECHA"]
                if c in rutas.columns
            ),
            rutas.columns[0],
        )
        col_vend_r = next(
            (
                c
                for c in [
                    "codven",
                    "CodVen",
                    "CodVendedor",
                    "Vendedor",
                    "Cod_Vendedor",
                    "CODVEN",
                ]
                if c in rutas.columns
            ),
            rutas.columns[1],
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
            (dt_directo.dt.year == int(anio_op)) & (dt_directo.dt.month == int(mes_op))
        ).sum() >= (
            (dt_invertido.dt.year == int(anio_op))
            & (dt_invertido.dt.month == int(mes_op))
        ).sum():
            rutas["Fecha_dt"] = dt_directo
        else:
            rutas["Fecha_dt"] = dt_invertido

        rutas["CodVend"] = pd.to_numeric(rutas[col_vend_r], errors="coerce").astype(
            "Int64"
        )
        rutas_mes = rutas[
            (
                (rutas["Fecha_dt"].dt.year == int(anio_op))
                & (rutas["Fecha_dt"].dt.month == int(mes_op))
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
            desc = rutas_ajust_map_g.get(cv_clean_str, 0) if cv_clean_str else 0
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
        f"[PERF_INTERNAL] procesamiento_rutas_y_dias = {time.perf_counter() - t_s6:.2f} s"
    )

    df_operativo_ger = (
        df_vta_prep_ger[
            df_vta_prep_ger["Periodo"].isin(["Arrastre", "Actual"])
            & df_vta_prep_ger["SEGMENTO"].notna()
            & (df_vta_prep_ger["SEGMENTO"] != "SIN SEGMENTO")
        ].copy()
        if not df_vta_prep_ger.empty
        else pd.DataFrame()
    )

    kilos_oper_todo = pd.DataFrame()

    t_s7 = time.perf_counter()
    if not df_operativo_ger.empty:
        df_operativo_ger["CodVend_Clean"] = pd.to_numeric(
            df_operativo_ger["CodVendedor"], errors="coerce"
        ).astype("Int64")
        df_operativo_ger["Supervisor"] = (
            df_operativo_ger["CodVend_Clean"].astype(str).map(sup_map).fillna("GENERAL")
        )

        df_operativo_ger["Días_Pasados"] = (
            df_operativo_ger["CodVend_Clean"].map(dias_pasados_map).fillna(1.0)
        )
        df_operativo_ger["Días_Restantes"] = (
            df_operativo_ger["CodVend_Clean"].map(dias_restantes_map).fillna(0.0)
        )

        arrastre_g = (
            df_operativo_ger[df_operativo_ger["Periodo"] == "Arrastre"]
            .groupby(["CodVendedor", "Supervisor", "SEGMENTO"], as_index=False)
            .agg(Arrastre=("PesoKg", "sum"), Arrastre_Gross=("ImporteNetoItem", "sum"))
        )
        actual_g = (
            df_operativo_ger[df_operativo_ger["Periodo"] == "Actual"]
            .groupby(["CodVendedor", "Supervisor", "SEGMENTO"], as_index=False)
            .agg(
                Actual=("PesoKg", "sum"),
                Actual_Gross=("ImporteNetoItem", "sum"),
                Dias_Pasados=("Días_Pasados", "first"),
                Dias_Restantes=("Días_Restantes", "first"),
            )
        )

        vend_seg_g = arrastre_g.merge(
            actual_g, on=["CodVendedor", "Supervisor", "SEGMENTO"], how="outer"
        ).fillna(0.0)
        vend_seg_g["Operativo_K"] = vend_seg_g["Arrastre"] + vend_seg_g["Actual"]
        vend_seg_g["Operativo_G"] = (
            vend_seg_g["Arrastre_Gross"] + vend_seg_g["Actual_Gross"]
        )

        dp_v = vend_seg_g["Dias_Pasados"].replace(0, 1.0)
        dr_v = vend_seg_g["Dias_Restantes"]

        p_diario_k = vend_seg_g["Actual"] / dp_v
        p_diario_g = vend_seg_g["Actual_Gross"] / dp_v

        vend_seg_g["Proyectado_Todo_K"] = vend_seg_g["Operativo_K"]
        vend_seg_g["Proyectado_Todo_G"] = vend_seg_g["Operativo_G"]

        mask_p = (dr_v > 0) & (vend_seg_g["CodVendedor"] != 20)
        if mask_p.any():
            vend_seg_g.loc[mask_p, "Proyectado_Todo_K"] = (
                p_diario_k[mask_p] * dr_v[mask_p]
            ) + vend_seg_g.loc[mask_p, "Operativo_K"]
            vend_seg_g.loc[mask_p, "Proyectado_Todo_G"] = (
                p_diario_g[mask_p] * dr_v[mask_p]
            ) + vend_seg_g.loc[mask_p, "Operativo_G"]

        kilos_oper_todo = (
            vend_seg_g.groupby(["Supervisor", "SEGMENTO"], as_index=False)
            .agg(
                {
                    "Arrastre": "sum",
                    "Actual": "sum",
                    "Operativo_K": "sum",
                    "Proyectado_Todo_K": "sum",
                    "Arrastre_Gross": "sum",
                    "Actual_Gross": "sum",
                    "Operativo_G": "sum",
                    "Proyectado_Todo_G": "sum",
                }
            )
            .rename(
                columns={
                    "Operativo_K": "Kilos_Operativos_Kg",
                    "Proyectado_Todo_K": "Kilos_Proyectados_Kg",
                    "Arrastre_Gross": "Gross_Arrastre",
                    "Actual_Gross": "Gross_Actual",
                    "Operativo_G": "Importe_Operativo_Arg",
                    "Proyectado_Todo_G": "Gross_Proyectado_Arg",
                }
            )
        )
    print(
        f"[PERF_INTERNAL] calculo_kilos_operativos_y_proyecciones = {time.perf_counter() - t_s7:.2f} s"
    )

    df_futuro = (
        df_vta_prep_ger_full[
            (df_vta_prep_ger_full["Periodo"] == "Futuro")
            & df_vta_prep_ger_full["SEGMENTO"].notna()
            & (df_vta_prep_ger_full["SEGMENTO"] != "SIN SEGMENTO")
        ].copy()
        if not df_vta_prep_ger_full.empty
        else pd.DataFrame()
    )

    t_s8 = time.perf_counter()
    if not df_futuro.empty:
        df_futuro["CodVen_Clean"] = pd.to_numeric(
            df_futuro["CodVendedor"], errors="coerce"
        ).astype("Int64")
        df_futuro["Supervisor"] = (
            df_futuro["CodVen_Clean"].astype(str).map(sup_map).fillna("GENERAL")
        )

        futuro_seg_agg = df_futuro.groupby(
            ["Supervisor", "SEGMENTO"], as_index=False
        ).agg(
            Kilos_Disponibles=("PesoKg", "sum"),
            Gross_Disponible=("ImporteNetoItem", "sum"),
        )
    else:
        futuro_seg_agg = pd.DataFrame(
            columns=["Supervisor", "SEGMENTO", "Kilos_Disponibles", "Gross_Disponible"]
        )
    print(
        f"[PERF_INTERNAL] agrupacion_ventas_futuras = {time.perf_counter() - t_s8:.2f} s"
    )

    kilos_obj_g = pd.DataFrame(
        columns=["Supervisor", "SEGMENTO", "Objetivo_Kilos_Kg", "Objetivo_Importe_Arg"]
    )
    t_s9 = time.perf_counter()
    if (
        not maestro_cebe.empty
        and not df_vta_prep_ger.empty
        and "Marca" in df_vta_prep_ger.columns
    ):
        col_m_cebe = next(
            (c for c in maestro_cebe.columns if "marca" in str(c).strip().lower()),
            maestro_cebe.columns[0],
        )
        col_obj_tn = next(
            (
                c
                for c in maestro_cebe.columns
                if any(k in str(c).strip().lower() for k in ["obj_tn", "tn", "obj_mes"])
            ),
            None,
        )
        col_obj_gross = next(
            (
                c
                for c in maestro_cebe.columns
                if any(k in str(c).strip().lower() for k in ["obj_gross", "gross"])
            ),
            None,
        )

        if col_obj_tn and col_obj_gross:
            maestro_cebe_clean = maestro_cebe.copy()
            maestro_cebe_clean["Marca_Key"] = (
                maestro_cebe_clean[col_m_cebe]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
            )

            maestro_cebe_clean["Obj_Val_Kg"] = pd.to_numeric(
                maestro_cebe_clean[col_obj_tn], errors="coerce"
            ).fillna(0.0)
            maestro_cebe_clean["Obj_Val_Imp"] = pd.to_numeric(
                maestro_cebe_clean[col_obj_gross], errors="coerce"
            ).fillna(0.0)

            mapa_obj_kg = (
                maestro_cebe_clean.groupby("Marca_Key")["Obj_Val_Kg"].sum().to_dict()
            )
            mapa_obj_imp = (
                maestro_cebe_clean.groupby("Marca_Key")["Obj_Val_Imp"].sum().to_dict()
            )

            df_vta_prep_ger["CodVen_Clean"] = pd.to_numeric(
                df_vta_prep_ger["CodVendedor"], errors="coerce"
            ).astype("Int64")
            df_vta_prep_ger["Supervisor"] = (
                df_vta_prep_ger["CodVen_Clean"]
                .astype(str)
                .map(sup_map)
                .fillna("GENERAL")
            )
            df_vta_prep_ger["Marca_Key"] = (
                df_vta_prep_ger["Marca"].astype(str).str.strip().str.upper()
            )

            tot_marca_vta = (
                df_vta_prep_ger[df_vta_prep_ger["SEGMENTO"] != "SIN SEGMENTO"]
                .groupby(["Supervisor", "Marca_Key", "SEGMENTO"])["PesoKg"]
                .sum()
                .reset_index()
            )
            tot_marca_vta["Total_Marca"] = (
                tot_marca_vta.groupby("Marca_Key")["PesoKg"]
                .transform("sum")
                .replace(0, 1.0)
            )
            tot_marca_vta["Part_Marca_Seg"] = (
                tot_marca_vta["PesoKg"] / tot_marca_vta["Total_Marca"]
            )

            tot_marca_vta["Obj_Kilos_Marca"] = (
                tot_marca_vta["Marca_Key"].map(mapa_obj_kg).fillna(0.0)
            )
            tot_marca_vta["Obj_Gross_Marca"] = (
                tot_marca_vta["Marca_Key"].map(mapa_obj_imp).fillna(0.0)
            )

            tot_marca_vta["Obj_Seg_Kg"] = (
                tot_marca_vta["Obj_Kilos_Marca"] * tot_marca_vta["Part_Marca_Seg"]
            )
            tot_marca_vta["Obj_Seg_Imp"] = (
                tot_marca_vta["Obj_Gross_Marca"] * tot_marca_vta["Part_Marca_Seg"]
            )

            kilos_obj_g = tot_marca_vta.groupby(
                ["Supervisor", "SEGMENTO"], as_index=False
            ).agg(
                Objetivo_Kilos_Kg=("Obj_Seg_Kg", "sum"),
                Objetivo_Importe_Arg=("Obj_Seg_Imp", "sum"),
            )
    print(
        f"[PERF_INTERNAL] calculo_objetivos_maestro_cebe = {time.perf_counter() - t_s9:.2f} s"
    )

    filtros_globales_base = {
        "anio": anio_op,
        "mes": mes_op,
        "dia_matinal": dia_matinal,
        "dia_venta": dia_venta,
        "supervisor": sup_seleccionado,
    }

    t_s10 = time.perf_counter()
    from modules.rep_MN import generar_reporte_mn_taxonomia

    rep_mn_global = generar_reporte_mn_taxonomia(
        df_vta, df_universo, maestro_v, filtros_globales_base
    )
    print(
        f"[PERF_INTERNAL] generar_reporte_mn_taxonomia_ger = {time.perf_counter() - t_s10:.2f} s"
    )

    cartera_base_global = st.session_state.get("_cob_cartera_base", pd.DataFrame())
    vtas_agrup_global = st.session_state.get("_cob_vtas_agrupadas", pd.DataFrame())
    marcas_lst = st.session_state.get("_cob_marcas", [])
    mapa_obj = st.session_state.get("_cob_mapa_objetivos", {})

    t_s11 = time.perf_counter()
    if cartera_base_global.empty or not marcas_lst:
        from modules.rep_cob_marca import generar_reporte_cobertura_marca

        generar_reporte_cobertura_marca(
            df_vta, df_universo, maestro_v, df_marcas_maestro, filtros_globales_base
        )
        cartera_base_global = st.session_state.get("_cob_cartera_base", pd.DataFrame())
        vtas_agrup_global = st.session_state.get("_cob_vtas_agrupadas", pd.DataFrame())
        marcas_lst = st.session_state.get("_cob_marcas", [])
        mapa_obj = st.session_state.get("_cob_mapa_objetivos", {})
    print(
        f"[PERF_INTERNAL] recuperacion_cache_cobertura_marca = {time.perf_counter() - t_s11:.2f} s"
    )

    t_s12 = time.perf_counter()
    res_gross_mn, res_kilos_mn, res_ccc_mn = _calcular_minegocio_taxonomia_detallado(
        df_vta_prep_ger,
        df_universo,
        maestro_v,
        anio_op,
        mes_op,
        dia_matinal,
        sup_seleccionado,
    )
    print(
        f"[PERF_INTERNAL] _calcular_minegocio_taxonomia_detallado = {time.perf_counter() - t_s12:.2f} s"
    )

    print(
        f"[PERF_INTERNAL] _calcular_motor_gerencial_global = {time.perf_counter() - t_start:.2f} s"
    )
    return (
        kilos_obj_g,
        kilos_oper_todo,
        futuro_seg_agg,
        rep_mn_global,
        cartera_base_global,
        vtas_agrup_global,
        marcas_lst,
        mapa_obj,
        res_gross_mn,
        res_kilos_mn,
        res_ccc_mn,
        total_dias_pasados_val,
        total_dias_restantes_val,
    )


def render_rep_gerencial(
    df_vta, df_universo, df_rutas, df_ausencias, filtros_globales=None
):
    t_start = time.perf_counter()
    st.subheader("📈 Tablero Ejecutivo Gerencial - Consolidado Integral")
    st.markdown(
        "Vista directiva completa con el desglose detallado por segmentos, taxonomías, marcas, kilos e importes de la compañía."
    )

    if filtros_globales is None:
        filtros_globales = {
            "anio": 2026,
            "mes": 9,
            "dia_matinal": "02/09/2026",
            "dia_venta": "01/09/2026",
            "supervisor": "TODOS",
        }

    anio_op = int(filtros_globales.get("anio", 2026))
    mes_op = int(filtros_globales.get("mes", 9))
    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026")
    dia_venta = filtros_globales.get("dia_venta", "01/09/2026")

    try:
        t_s1 = time.perf_counter()
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        col_sup_v = next(
            (c for c in maestro_v.columns if "sup" in str(c).strip().lower()),
            maestro_v.columns[2]
            if len(maestro_v.columns) > 2
            else maestro_v.columns[0],
        )
        supervisores_disp = ["TODOS"] + sorted(
            list(
                set(
                    str(s).strip()
                    for s in maestro_v[col_sup_v].dropna().unique()
                    if str(s).strip() != ""
                )
            )
        )
        print(
            f"[PERF_INTERNAL] consulta_sqlite_maestro_vendedores_render = {time.perf_counter() - t_s1:.2f} s"
        )
    except Exception:
        supervisores_disp = ["TODOS"]

    col_sup_sel, col_ajuste_sel, _ = st.columns([2, 2, 3])
    with col_sup_sel:
        sup_seleccionado = st.selectbox(
            "Filtrar Tablero por Supervisor",
            options=supervisores_disp,
            index=0,
            key="gerencial_filtro_sup",
        )
    with col_ajuste_sel:
        modo_ajuste_ger = st.selectbox(
            "Ajuste por Entrega",
            options=["TODO", "AJUSTADO"],
            index=1,
            key="gerencial_filtro_ajuste",
        )

    huella_global = f"{len(df_vta)}_{len(df_universo)}_{anio_op}_{mes_op}_{dia_matinal}_{sup_seleccionado}_{modo_ajuste_ger}"

    t_s2 = time.perf_counter()
    (
        kilos_obj_det_global,
        kilos_oper_todo,
        futuro_agg_global,
        rep_mn_global,
        cartera_base_global,
        vtas_agrup_global,
        marcas_lst,
        mapa_obj,
        res_gross_mn,
        res_kilos_mn,
        res_ccc_mn,
        dias_pasados_tot,
        dias_restantes_tot,
    ) = _calcular_motor_gerencial_global(
        df_vta,
        df_universo,
        df_rutas,
        df_ausencias,
        anio_op,
        mes_op,
        dia_matinal,
        dia_venta,
        sup_seleccionado,
        modo_ajuste_ger,
        huella_global,
    )
    print(
        f"[PERF_INTERNAL] _calcular_motor_gerencial_global_ejecucion = {time.perf_counter() - t_s2:.2f} s"
    )

    # RENDERIZAR ETIQUETAS DE DÍAS PASADOS Y RESTANTES
    col_d1, col_d2, _ = st.columns([1, 1, 3])
    with col_d1:
        st.markdown(
            tarjeta_metrica_html(
                "DÍAS PASADOS", f"{dias_pasados_tot}", "#3b82f6", "1.1rem", "0.6rem"
            ),
            unsafe_allow_html=True,
        )
    with col_d2:
        st.markdown(
            tarjeta_metrica_html(
                f"DÍAS RESTANTES ({modo_ajuste_ger})",
                f"{dias_restantes_tot}",
                "#10b981",
                "1.1rem",
                "0.6rem",
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    t_s3 = time.perf_counter()
    kilos_operativos_g = (
        kilos_oper_todo[
            kilos_oper_todo["Supervisor"].astype(str).str.strip() == sup_seleccionado
        ]
        .groupby("SEGMENTO", as_index=False)
        .agg(
            {
                "Arrastre": "sum",
                "Actual": "sum",
                "Kilos_Operativos_Kg": "sum",
                "Importe_Operativo_Arg": "sum",
                "Kilos_Proyectados_Kg": "sum",
                "Gross_Proyectado_Arg": "sum",
            }
        )
        if sup_seleccionado != "TODOS"
        and not kilos_oper_todo.empty
        and "Supervisor" in kilos_oper_todo.columns
        else (
            kilos_oper_todo.groupby("SEGMENTO", as_index=False).agg(
                {
                    "Arrastre": "sum",
                    "Actual": "sum",
                    "Kilos_Operativos_Kg": "sum",
                    "Importe_Operativo_Arg": "sum",
                    "Kilos_Proyectados_Kg": "sum",
                    "Gross_Proyectado_Arg": "sum",
                }
            )
            if not kilos_oper_todo.empty
            else pd.DataFrame(
                columns=[
                    "SEGMENTO",
                    "Arrastre",
                    "Actual",
                    "Kilos_Operativos_Kg",
                    "Importe_Operativo_Arg",
                    "Kilos_Proyectados_Kg",
                    "Gross_Proyectado_Arg",
                ]
            )
        )
    )

    kilos_obj_g = (
        kilos_obj_det_global[
            kilos_obj_det_global["Supervisor"].astype(str).str.strip()
            == sup_seleccionado
        ]
        .groupby("SEGMENTO", as_index=False)
        .agg({"Objetivo_Kilos_Kg": "sum", "Objetivo_Importe_Arg": "sum"})
        if sup_seleccionado != "TODOS"
        and not kilos_obj_det_global.empty
        and "Supervisor" in kilos_obj_det_global.columns
        else (
            kilos_obj_det_global.groupby("SEGMENTO", as_index=False).agg(
                {"Objetivo_Kilos_Kg": "sum", "Objetivo_Importe_Arg": "sum"}
            )
            if not kilos_obj_det_global.empty
            else pd.DataFrame(
                columns=["SEGMENTO", "Objetivo_Kilos_Kg", "Objetivo_Importe_Arg"]
            )
        )
    )

    futuro_segmento = (
        futuro_agg_global[
            futuro_agg_global["Supervisor"].astype(str).str.strip() == sup_seleccionado
        ]
        .groupby("SEGMENTO", as_index=False)
        .agg({"Kilos_Disponibles": "sum", "Gross_Disponible": "sum"})
        if sup_seleccionado != "TODOS"
        and not futuro_agg_global.empty
        and "Supervisor" in futuro_agg_global.columns
        else (
            futuro_agg_global.groupby("SEGMENTO", as_index=False).agg(
                {"Kilos_Disponibles": "sum", "Gross_Disponible": "sum"}
            )
            if not futuro_agg_global.empty
            else pd.DataFrame(
                columns=["SEGMENTO", "Kilos_Disponibles", "Gross_Disponible"]
            )
        )
    )

    cartera_base = (
        cartera_base_global[
            cartera_base_global["SUP"].astype(str).str.strip() == sup_seleccionado
        ].copy()
        if not cartera_base_global.empty and "SUP" in cartera_base_global.columns
        else cartera_base_global.copy()
    )

    df_seg = kilos_obj_g.merge(kilos_operativos_g, on="SEGMENTO", how="outer").fillna(
        0.0
    )

    if not futuro_segmento.empty:
        df_seg = df_seg.merge(futuro_segmento, on="SEGMENTO", how="left").fillna(0.0)
    else:
        df_seg["Kilos_Disponibles"] = 0.0
        df_seg["Gross_Disponible"] = 0.0

    df_seg["Objetivo_Kilos_Kg"] = df_seg["Objetivo_Kilos_Kg"].round(2)
    df_seg["Objetivo_Importe_Arg"] = df_seg["Objetivo_Importe_Arg"].round(2)
    df_seg["Arrastre"] = df_seg["Arrastre"].round(2)
    df_seg["Actual"] = df_seg["Actual"].round(2)
    df_seg["Kilos_Operativos_Kg"] = df_seg["Kilos_Operativos_Kg"].round(2)
    df_seg["Importe_Operativo_Arg"] = df_seg["Importe_Operativo_Arg"].round(2)
    df_seg["Kilos_Proyectados_Kg"] = df_seg["Kilos_Proyectados_Kg"].round(2)
    df_seg["Gross_Proyectado_Arg"] = df_seg["Gross_Proyectado_Arg"].round(2)

    df_seg["Cumplimiento_Actual_Pct"] = (
        (
            df_seg["Importe_Operativo_Arg"]
            / df_seg["Objetivo_Importe_Arg"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    df_seg["Cumplimiento_Proyectado_Pct"] = (
        (df_seg["Kilos_Proyectados_Kg"] / df_seg["Objetivo_Kilos_Kg"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    df_seg["Cumplimiento_Gross_Proy_Pct"] = (
        (
            df_seg["Gross_Proyectado_Arg"]
            / df_seg["Objetivo_Importe_Arg"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )
    df_seg["Cumplimiento_Gross_Actual_Pct"] = (
        (
            df_seg["Importe_Operativo_Arg"]
            / df_seg["Objetivo_Importe_Arg"].replace(0, pd.NA)
        )
        .mul(100.0)
        .fillna(0.0)
        .round(2)
    )

    df_seg["Raw_Bache_Kgs"] = (
        df_seg["Objetivo_Kilos_Kg"] - df_seg["Kilos_Proyectados_Kg"]
    ).clip(lower=0)
    df_seg["Raw_Bache_Gross"] = (
        df_seg["Objetivo_Importe_Arg"] - df_seg["Gross_Proyectado_Arg"]
    ).clip(lower=0)

    tot_obj_kilos = float(df_seg["Objetivo_Kilos_Kg"].sum())
    tot_proy_k = float(df_seg["Kilos_Proyectados_Kg"].sum())
    global_gap_kilos = max(0.0, tot_obj_kilos - tot_proy_k)

    tot_obj_gross = float(df_seg["Objetivo_Importe_Arg"].sum())
    tot_proy_g = float(df_seg["Gross_Proyectado_Arg"].sum())
    global_gap_gross = max(0.0, tot_obj_gross - tot_proy_g)

    sum_baches_kilos = df_seg["Raw_Bache_Kgs"].sum()
    factor_kilos = (
        (global_gap_kilos / sum_baches_kilos) if sum_baches_kilos > 0 else 0.0
    )

    sum_baches_gross = df_seg["Raw_Bache_Gross"].sum()
    factor_gross = (
        (global_gap_gross / sum_baches_gross) if sum_baches_gross > 0 else 0.0
    )

    df_seg["Futuro_A_Incorporar_Kgs"] = (df_seg["Raw_Bache_Kgs"] * factor_kilos).round(
        2
    )
    df_seg["Futuro_A_Incorporar_Gross"] = (
        df_seg["Raw_Bache_Gross"] * factor_gross
    ).round(2)

    orden_segmentos_maestro = [
        "GOLD Salty",
        "GOLD Crakers",
        "SILVER Salty",
        "SILVER Crakers",
        "SILVER Cereals",
    ]
    mapping_orden = {
        str(seg).strip(): i for i, seg in enumerate(orden_segmentos_maestro)
    }
    df_seg["_orden_idx"] = (
        df_seg["SEGMENTO"].astype(str).str.strip().map(mapping_orden).fillna(999)
    )
    df_seg = (
        df_seg.sort_values(by="_orden_idx")
        .drop(columns=["_orden_idx"])
        .reset_index(drop=True)
    )

    df_gross_seg = (
        df_seg[
            [
                "SEGMENTO",
                "Objetivo_Importe_Arg",
                "Importe_Operativo_Arg",
                "Cumplimiento_Gross_Actual_Pct",
                "Gross_Proyectado_Arg",
                "Cumplimiento_Gross_Proy_Pct",
                "Futuro_A_Incorporar_Gross",
                "Gross_Disponible",
            ]
        ]
        .copy()
        .rename(
            columns={
                "Objetivo_Importe_Arg": "Objetivo Gross Pepsico",
                "Importe_Operativo_Arg": "Operativo Gross",
                "Cumplimiento_Gross_Actual_Pct": "% Cump. Actual Gross",
                "Gross_Proyectado_Arg": "Proyectado Gross",
                "Cumplimiento_Gross_Proy_Pct": "% Cumpl. Proy. Gross",
                "Futuro_A_Incorporar_Gross": "A Incorporar Gross",
                "Gross_Disponible": "Gross Disponible",
            }
        )
    )

    df_gross_display = df_gross_seg.copy()
    for col in [
        "Objetivo Gross Pepsico",
        "Operativo Gross",
        "Proyectado Gross",
        "A Incorporar Gross",
        "Gross Disponible",
    ]:
        df_gross_display[col] = df_gross_display[col].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
        )
    for col in ["% Cump. Actual Gross", "% Cumpl. Proy. Gross"]:
        df_gross_display[col] = df_gross_display[col].apply(
            lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%"
        )

    tot_operativo_g = float(df_seg["Importe_Operativo_Arg"].sum())
    cump_actual_g_val = round(
        (tot_operativo_g / tot_obj_gross * 100.0) if tot_obj_gross > 0 else 0.0, 2
    )
    cump_proy_g_val = round(
        (tot_proy_g / tot_obj_gross * 100.0) if tot_obj_gross > 0 else 0.0, 2
    )
    tot_incorporar_g = float(df_gross_seg["A Incorporar Gross"].sum())

    df_kilos_seg = (
        df_seg[
            [
                "SEGMENTO",
                "Objetivo_Kilos_Kg",
                "Arrastre",
                "Actual",
                "Kilos_Operativos_Kg",
                "Cumplimiento_Actual_Pct",
                "Kilos_Proyectados_Kg",
                "Cumplimiento_Proyectado_Pct",
                "Futuro_A_Incorporar_Kgs",
                "Kilos_Disponibles",
            ]
        ]
        .copy()
        .rename(
            columns={
                "Objetivo_Kilos_Kg": "Objetivo Kilos Pepsico",
                "Arrastre": "Arrastre Kilos",
                "Actual": "Mes Actual Kilos",
                "Kilos_Operativos_Kg": "Operativo Kilos",
                "Cumplimiento_Actual_Pct": "% Cump. Actual Kilos",
                "Kilos_Proyectados_Kg": "Proyectado Kilos",
                "Cumplimiento_Proyectado_Pct": "% Cump. Proy. Kilos",
                "Futuro_A_Incorporar_Kgs": "A Incorporar Kilos",
                "Kilos_Disponibles": "Kilos Disponibles",
            }
        )
    )

    df_kilos_display = df_kilos_seg.copy()
    for col in [
        "Objetivo Kilos Pepsico",
        "Arrastre Kilos",
        "Mes Actual Kilos",
        "Operativo Kilos",
        "Proyectado Kilos",
        "A Incorporar Kilos",
        "Kilos Disponibles",
    ]:
        df_kilos_display[col] = df_kilos_display[col].apply(
            lambda x: f"{x:,.2f} kg" if pd.notna(x) else "0.00 kg"
        )
    for col in ["% Cump. Actual Kilos", "% Cump. Proy. Kilos"]:
        df_kilos_display[col] = df_kilos_display[col].apply(
            lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%"
        )

    tot_operativo_k = float(df_seg["Kilos_Operativos_Kg"].sum())
    cump_actual_k_val = round(
        (tot_operativo_k / tot_obj_kilos * 100.0) if tot_obj_kilos > 0 else 0.0, 2
    )
    cump_proy_k_val = round(
        (tot_proy_k / tot_obj_kilos * 100.0) if tot_obj_kilos > 0 else 0.0, 2
    )
    tot_incorporar_k = float(df_kilos_seg["A Incorporar Kilos"].sum())

    t_s4 = time.perf_counter()
    df_ccc_tax_raw, df_ccc_display = _calcular_ccc_taxonomia_gerencial(
        df_vta, df_universo, maestro_v, anio_op, mes_op, dia_matinal, sup_seleccionado
    )
    print(
        f"[PERF_INTERNAL] _calcular_ccc_taxonomia_gerencial_ejecucion = {time.perf_counter() - t_s4:.2f} s"
    )

    tot_cartera_ger = (
        int(df_ccc_tax_raw["Cartera_Neta"].sum()) if not df_ccc_tax_raw.empty else 0
    )
    tot_obj_pep_ger = (
        float(df_ccc_tax_raw["Obj_Pepsico"].sum()) if not df_ccc_tax_raw.empty else 0.0
    )
    tot_obj_fv_ger = (
        float(df_ccc_tax_raw["Obj_Fuerza_Ventas"].sum())
        if not df_ccc_tax_raw.empty
        else 0.0
    )
    tot_avance_ccc_ger = (
        int(df_ccc_tax_raw["Avance_CCC"].sum()) if not df_ccc_tax_raw.empty else 0
    )

    cump_pep_ger_pct = (
        (tot_avance_ccc_ger / tot_obj_pep_ger * 100.0) if tot_obj_pep_ger > 0 else 0.0
    )
    cump_fv_ger_pct = (
        (tot_avance_ccc_ger / tot_obj_fv_ger * 100.0) if tot_obj_fv_ger > 0 else 0.0
    )

    tot_ventas_mn_ger = (
        float(res_gross_mn["Gross_Total"].sum()) if not res_gross_mn.empty else 0.0
    )
    tot_app_mn_ger = (
        float(res_gross_mn["Gross_MN"].sum()) if not res_gross_mn.empty else 0.0
    )
    pct_venta_mn_ger = (
        (tot_app_mn_ger / tot_ventas_mn_ger * 100.0) if tot_ventas_mn_ger > 0 else 0.0
    )

    tot_cartera_mn_ger = (
        int(res_ccc_mn["Cartera_Total"].sum()) if not res_ccc_mn.empty else 0
    )
    tot_nodig_mn_ger = (
        int(res_ccc_mn["No Digital"].sum()) if not res_ccc_mn.empty else 0
    )
    tot_hibr_mn_ger = int(res_ccc_mn["Híbridos"].sum()) if not res_ccc_mn.empty else 0
    tot_fully_mn_ger = (
        int(res_ccc_mn["Fully Digital"].sum()) if not res_ccc_mn.empty else 0
    )

    df_gross_mn_disp = res_gross_mn.copy()
    df_gross_mn_disp["Gross_Total"] = df_gross_mn_disp["Gross_Total"].apply(
        lambda x: f"${x:,.2f}"
    )
    df_gross_mn_disp["Gross_MN"] = df_gross_mn_disp["Gross_MN"].apply(
        lambda x: f"${x:,.2f}"
    )
    df_gross_mn_disp["Adopcion_Gross_Pct"] = df_gross_mn_disp[
        "Adopcion_Gross_Pct"
    ].apply(lambda x: f"{x:,.2f}%")
    df_gross_mn_disp = df_gross_mn_disp.rename(
        columns={
            "Taxonomia": "Taxonomía",
            "Gross_Total": "Gross Total ($)",
            "Gross_MN": "Gross MiNegocio ($)",
            "Adopcion_Gross_Pct": "% Adopción Gross",
        }
    )

    df_kilos_mn_disp = res_kilos_mn.copy()
    df_kilos_mn_disp["Kilos_Total"] = df_kilos_mn_disp["Kilos_Total"].apply(
        lambda x: f"{x:,.2f} kg"
    )
    df_kilos_mn_disp["Kilos_MN"] = df_kilos_mn_disp["Kilos_MN"].apply(
        lambda x: f"{x:,.2f} kg"
    )
    df_kilos_mn_disp["Adopcion_Kilos_Pct"] = df_kilos_mn_disp[
        "Adopcion_Kilos_Pct"
    ].apply(lambda x: f"{x:,.2f}%")
    df_kilos_mn_disp = df_kilos_mn_disp.rename(
        columns={
            "Taxonomia": "Taxonomía",
            "Kilos_Total": "Kilos Totales (kg)",
            "Kilos_MN": "Kilos MiNegocio (kg)",
            "Adopcion_Kilos_Pct": "% Adopción Kilos",
        }
    )

    df_ccc_mn_disp = res_ccc_mn.copy()
    df_ccc_mn_disp["Cartera_Total"] = df_ccc_mn_disp["Cartera_Total"].apply(
        lambda x: f"{int(x):,}"
    )
    df_ccc_mn_disp["CCC_Total"] = df_ccc_mn_disp["CCC_Total"].apply(
        lambda x: f"{int(x):,}"
    )
    df_ccc_mn_disp["No Digital"] = df_ccc_mn_disp["No Digital"].apply(
        lambda x: f"{int(x):,}"
    )
    df_ccc_mn_disp["Híbridos"] = df_ccc_mn_disp["Híbridos"].apply(
        lambda x: f"{int(x):,}"
    )
    df_ccc_mn_disp["Fully Digital"] = df_ccc_mn_disp["Fully Digital"].apply(
        lambda x: f"{int(x):,}"
    )
    df_ccc_mn_disp = df_ccc_mn_disp.rename(
        columns={
            "Taxonomia": "Taxonomía",
            "Cartera_Total": "Cartera / Clientes",
            "CCC_Total": "Clientes con Compra (CCC)",
            "No Digital": "No Digital (CCC)",
            "Híbridos": "Híbridos (CCC)",
            "Fully Digital": "Fully Digital (CCC)",
        }
    )

    t_s5 = time.perf_counter()
    registros_marca = []
    total_cartera_global = len(cartera_base) if not cartera_base.empty else 0
    if not cartera_base.empty and marcas_lst:
        clientes_unicos_cartera = set(cartera_base["Cliente_Cod"].unique())
        for m in marcas_lst:
            obj_m = mapa_obj.get(m, 80.0)
            if not vtas_agrup_global.empty:
                if (
                    sup_seleccionado != "TODOS"
                    and "CodVendedor" in vtas_agrup_global.columns
                    and "CodVendedor" in cartera_base.columns
                ):
                    vta_m_filt = vtas_agrup_global[
                        vtas_agrup_global["CodVendedor"].isin(
                            cartera_base["CodVendedor"]
                        )
                    ]
                else:
                    vta_m_filt = vtas_agrup_global

                cubiertos_m = vta_m_filt[
                    vta_m_filt["Cliente"].isin(clientes_unicos_cartera)
                    & (vta_m_filt["Marca"] == m)
                    & (vta_m_filt["Total_Cant"] >= 3)
                ]["Cliente"].nunique()
            else:
                cubiertos_m = 0

            cob_real_pct = (
                (cubiertos_m / total_cartera_global * 100.0)
                if total_cartera_global > 0
                else 0.0
            )
            cumpl_marca_pct = (cob_real_pct / obj_m * 100.0) if obj_m > 0 else 0.0

            registros_marca.append(
                {
                    "Marca": m,
                    "Objetivo_Cobertura_Marca_Pct": round(obj_m, 2),
                    "Clientes_Cubiertos": cubiertos_m,
                    "Cartera_Total": total_cartera_global,
                    "Cobertura_Real_Operativa_Pct": round(cob_real_pct, 2),
                    "Cumplimiento_Cobertura_Marca_Pct": round(cumpl_marca_pct, 2),
                }
            )
    df_marcas_res = pd.DataFrame(registros_marca)
    print(
        f"[PERF_INTERNAL] calculo_cobertura_marcas_gerencial = {time.perf_counter() - t_s5:.2f} s"
    )

    tab_k, tab_c, tab_mn, tab_m = st.tabs(
        [
            "📦 Kilos e Importes por Segmento",
            "📈 CCC por Taxonomía",
            "📱 MiNegocio por Taxonomía",
            "🎯 Cobertura por Marca",
        ]
    )

    with tab_k:
        st.markdown("### 💰 1. Desglose Financiero (Gross / Importes)")
        col_proy_g1, col_proy_g2, col_proy_g3 = st.columns([1, 2, 1])
        with col_proy_g2:
            st.markdown(
                tarjeta_metrica_html(
                    "📊 PROYECTADO GROSS",
                    f"${tot_proy_g:,.0f}",
                    "#ef4444",
                    "2.2rem",
                    "1.1rem",
                ),
                unsafe_allow_html=True,
            )

        mi1, mi2, mi3, mi4, mi5 = st.columns(5)
        with mi1:
            st.markdown(
                tarjeta_metrica_html(
                    "💰 OBJ. GROSS",
                    f"${tot_obj_gross:,.0f}",
                    "#3b82f6",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mi2:
            st.markdown(
                tarjeta_metrica_html(
                    "💵 OPERATIVO GROSS",
                    f"${tot_operativo_g:,.0f}",
                    "#10b981",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mi3:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 CUMP. ACTUAL",
                    f"{cump_actual_g_val:,.2f}%",
                    "#8b5cf6",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mi4:
            st.markdown(
                tarjeta_metrica_html(
                    "📊 CUMP. PROY.",
                    f"{cump_proy_g_val:,.2f}%",
                    "#06b6d4",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mi5:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 A INCORPORAR",
                    f"${tot_incorporar_g:,.0f}",
                    "#f59e0b",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )

        st.dataframe(df_gross_display, width="stretch", hide_index=True)

        buf_g = io.BytesIO()
        with pd.ExcelWriter(buf_g, engine="openpyxl") as w:
            df_gross_seg.to_excel(w, index=False, sheet_name="Gross_Segmento")
        st.download_button(
            "📥 Descargar Gross / Importes a Excel",
            data=buf_g.getvalue(),
            file_name="gross_importes_por_segmento.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_gross_seg",
        )

        st.divider()
        st.markdown("### 📦 2. Desglose Operativo (Kilos / Volumen)")
        col_proy_k1, col_proy_k2, col_proy_k3 = st.columns([1, 2, 1])
        with col_proy_k2:
            st.markdown(
                tarjeta_metrica_html(
                    "🔮 PROYECTADO KILOS",
                    f"{tot_proy_k:,.0f} kg",
                    "#ef4444",
                    "2.2rem",
                    "1.1rem",
                ),
                unsafe_allow_html=True,
            )

        mk1, mk2, mk3, mk4, mk5 = st.columns(5)
        with mk1:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 OBJETIVO KILOS",
                    f"{tot_obj_kilos:,.0f} kg",
                    "#3b82f6",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mk2:
            st.markdown(
                tarjeta_metrica_html(
                    "📊 OPERATIVO KILOS",
                    f"{tot_operativo_k:,.0f} kg",
                    "#10b981",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mk3:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 CUMP. ACTUAL",
                    f"{cump_actual_k_val:,.2f}%",
                    "#8b5cf6",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mk4:
            st.markdown(
                tarjeta_metrica_html(
                    "📈 CUMP. PROY.",
                    f"{cump_proy_k_val:,.2f}%",
                    "#06b6d4",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )
        with mk5:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 A INCORPORAR",
                    f"${tot_incorporar_k:,.0f} kg",
                    "#f59e0b",
                    "1.0rem",
                    "0.45rem",
                ),
                unsafe_allow_html=True,
            )

        st.dataframe(df_kilos_display, width="stretch", hide_index=True)

        buf_k = io.BytesIO()
        with pd.ExcelWriter(buf_k, engine="openpyxl") as w:
            df_kilos_seg.to_excel(w, index=False, sheet_name="Kilos_Segmento")
        st.download_button(
            "📥 Descargar Kilos / Volumen a Excel",
            data=buf_k.getvalue(),
            file_name="kilos_volumen_por_segmento.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_kilos_seg",
        )

    with tab_c:
        st.markdown(
            "### 📈 CCC por Taxonomía (Obj Pepsico, % Cump, Obj Fuerza de Ventas, % Cump y Avance CCC)"
        )

        cc1, cc2, cc3, cc4, cc5, cc6 = st.columns(6)
        with cc1:
            st.markdown(
                tarjeta_metrica_html(
                    "📋 CARTERA NETA",
                    f"{tot_cartera_ger:,.0f}",
                    "#ffffff",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with cc2:
            st.markdown(
                tarjeta_metrica_html(
                    "📦 CANTIDAD CCC",
                    f"{tot_avance_ccc_ger:,.0f}",
                    "#22c55e",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with cc3:
            st.markdown(
                tarjeta_metrica_html(
                    "🏢 OBJ. PEPSICO",
                    f"{tot_obj_pep_ger:,.0f}",
                    "#3b82f6",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with cc4:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 CUMP. PEPSICO",
                    f"{cump_pep_ger_pct:,.2f}%",
                    "#10b981",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with cc5:
            st.markdown(
                tarjeta_metrica_html(
                    "🎯 OBJ. F. VENTAS",
                    f"{tot_obj_fv_ger:,.0f}",
                    "#f59e0b",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with cc6:
            st.markdown(
                tarjeta_metrica_html(
                    "📈 CUMP. F. VENTAS",
                    f"{cump_fv_ger_pct:,.2f}%",
                    "#8b5cf6",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )

        st.divider()
        st.dataframe(df_ccc_display, width="stretch", hide_index=True)

        buf2 = io.BytesIO()
        with pd.ExcelWriter(buf2, engine="openpyxl") as w:
            df_ccc_tax_raw.to_excel(w, index=False, sheet_name="CCC_Taxonomia")
        st.download_button(
            "📥 Descargar CCC por Taxonomía a Excel",
            data=buf2.getvalue(),
            file_name="ccc_por_taxonomia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_ccc_tax",
        )

    with tab_mn:
        st.markdown(
            "### 📱 MiNegocio por Taxonomía (Desglose Híbrido: Gross, Kilos y CCC por App)"
        )

        mn1, mn2, mn3, mn4, mn5, mn6 = st.columns(6)
        with mn1:
            st.markdown(
                tarjeta_metrica_html(
                    "💰 VENTAS TOTALES",
                    f"${tot_ventas_mn_ger:,.2f}",
                    "#38bdf8",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with mn2:
            st.markdown(
                tarjeta_metrica_html(
                    "📱 VENTA APP (MN+)",
                    f"${tot_app_mn_ger:,.2f}",
                    "#38bdf8",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with mn3:
            st.markdown(
                tarjeta_metrica_html(
                    "📈 % VENTA APP",
                    f"{pct_venta_mn_ger:,.2f}%",
                    "#38bdf8",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with mn4:
            st.markdown(
                tarjeta_metrica_html(
                    "🔴 NO DIGITAL",
                    f"{tot_nodig_mn_ger:,.0f}",
                    "#ef4444",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with mn5:
            st.markdown(
                tarjeta_metrica_html(
                    "🟠 HÍBRIDOS",
                    f"{tot_hibr_mn_ger:,.0f}",
                    "#f97316",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )
        with mn6:
            st.markdown(
                tarjeta_metrica_html(
                    "🟢 FULLY DIGITAL",
                    f"{tot_fully_mn_ger:,.0f}",
                    "#22c55e",
                    "1.1rem",
                    "0.6rem",
                ),
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("#### 💰 1. Desglose Financiero Gross por Taxonomía")
        st.dataframe(df_gross_mn_disp, width="stretch", hide_index=True)
        buf_mn_g = io.BytesIO()
        with pd.ExcelWriter(buf_mn_g, engine="openpyxl") as w:
            res_gross_mn.to_excel(w, index=False, sheet_name="MiNegocio_Gross")
        st.download_button(
            "📥 Descargar Gross MiNegocio a Excel",
            data=buf_mn_g.getvalue(),
            file_name="minegocio_gross_por_taxonomia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_mn_gross",
        )

        st.divider()
        st.markdown("#### 📦 2. Desglose Operativo Kilos por Taxonomía")
        st.dataframe(df_kilos_mn_disp, width="stretch", hide_index=True)
        buf_mn_k = io.BytesIO()
        with pd.ExcelWriter(buf_mn_k, engine="openpyxl") as w:
            res_kilos_mn.to_excel(w, index=False, sheet_name="MiNegocio_Kilos")
        st.download_button(
            "📥 Descargar Kilos MiNegocio a Excel",
            data=buf_mn_k.getvalue(),
            file_name="minegocio_kilos_por_taxonomia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_mn_kilos",
        )

        st.divider()
        st.markdown(
            "#### 📋 3. Desglose CCC y Compradores por App (No Digital, Híbridos, Fully Digital)"
        )
        st.dataframe(df_ccc_mn_disp, width="stretch", hide_index=True)
        buf_mn_c = io.BytesIO()
        with pd.ExcelWriter(buf_mn_c, engine="openpyxl") as w:
            res_ccc_mn.to_excel(w, index=False, sheet_name="MiNegocio_CCC")
        st.download_button(
            "📥 Descargar CCC MiNegocio a Excel",
            data=buf_mn_c.getvalue(),
            file_name="minegocio_ccc_por_taxonomia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_mn_ccc",
        )

    with tab_m:
        st.markdown("### 🎯 Cobertura por Marca")
        st.dataframe(df_marcas_res, width="stretch", hide_index=True)

        buf4 = io.BytesIO()
        with pd.ExcelWriter(buf4, engine="openpyxl") as w:
            df_marcas_res.to_excel(w, index=False, sheet_name="Cobertura_Marca")
        st.download_button(
            "📥 Descargar Cobertura por Marca a Excel",
            data=buf4.getvalue(),
            file_name="cobertura_por_marca_resumen.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_marca_res",
        )

    print(
        f"[PERF_INTERNAL] render_rep_gerencial = {time.perf_counter() - t_start:.2f} s"
    )
