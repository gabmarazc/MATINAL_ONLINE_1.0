# modules/rep_gerencial.py
import io
import os
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import tarjeta_metrica_html, parsear_fecha_robusta
from modules.rep_kilos import preparar_datos_ventas_segmento, generar_reporte_avance_kilos_segmento
from modules.rep_MN import preparar_ventas_mn, generar_reporte_mn_taxonomia
from modules.rep_cob_marca import preparar_ventas_cobertura_marca
from modules.rep_ccc import _calcular_base_ccc

def _calcular_ccc_taxonomia_gerencial(df_vta, df_universo, maestro_v, anio_op, mes_op, dia_matinal, sup_seleccionado):
    try:
        maestro_ccc = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
    except Exception:
        maestro_ccc = pd.DataFrame(columns=["Taxonomia", "Porcentaje_Cartera", "Obj_CCC_Pepsico"])

    if not maestro_ccc.empty and "Mes" in maestro_ccc.columns and "Anio" in maestro_ccc.columns:
        mc_per = maestro_ccc[(maestro_ccc["Mes"].astype(str) == str(mes_op)) & (maestro_ccc["Anio"].astype(str) == str(anio_op))]
        if not mc_per.empty:
            maestro_ccc = mc_per

    mapa_obj_pepsico = {}
    if not maestro_ccc.empty and "Taxonomia" in maestro_ccc.columns:
        for _, row in maestro_ccc.iterrows():
            tax = str(row["Taxonomia"]).strip().upper()
            if "Obj_CCC_Pepsico" in maestro_ccc.columns and pd.notna(row.get("Obj_CCC_Pepsico")):
                mapa_obj_pepsico[tax] = float(row["Obj_CCC_Pepsico"])

    reporte_base_ccc, _ = _calcular_base_ccc(df_vta, df_universo, maestro_v, maestro_ccc, anio_op, mes_op, dia_matinal)

    if reporte_base_ccc.empty:
        empty_df = pd.DataFrame(columns=["Taxonomia", "Cartera_Neta", "Obj_Pepsico", "Cump_Pepsico_Pct", "Obj_Fuerza_Ventas", "Cump_Fuerza_Ventas_Pct", "Avance_CCC"])
        empty_disp = pd.DataFrame(columns=["Taxonomía", "Cartera Neta (NC)", "Obj de Pepsico", "% Cump Obj Pepsico", "Objetivo a Fuerza de Ventas", "% Cump Obj Fuerza de Ventas", "Avance CCC"])
        return empty_df, empty_disp

    if sup_seleccionado != "TODOS" and "SUP" in reporte_base_ccc.columns:
        reporte_base_ccc = reporte_base_ccc[reporte_base_ccc["SUP"].astype(str).str.strip() == str(sup_seleccionado).strip()].copy()

    res_tax = reporte_base_ccc.groupby("Taxonomia", as_index=False).agg(
        Cartera_Neta=("Cartera_Neta", "sum"),
        Avance_CCC=("CCC", "sum"),
        Obj_Fuerza_Ventas=("Objetivo_CCC", "sum")
    )

    res_tax["Obj_Pepsico"] = res_tax["Taxonomia"].map(mapa_obj_pepsico).fillna(0.0)
    res_tax["Obj_Fuerza_Ventas"] = pd.to_numeric(res_tax["Obj_Fuerza_Ventas"], errors="coerce").fillna(0.0)

    res_tax["Cump_Pepsico_Pct"] = (res_tax["Avance_CCC"] / res_tax["Obj_Pepsico"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    res_tax["Cump_Fuerza_Ventas_Pct"] = (res_tax["Avance_CCC"] / res_tax["Obj_Fuerza_Ventas"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)

    df_res = res_tax[[
        "Taxonomia", "Cartera_Neta", "Obj_Pepsico", "Cump_Pepsico_Pct",
        "Obj_Fuerza_Ventas", "Cump_Fuerza_Ventas_Pct", "Avance_CCC"
    ]].copy()

    df_display = df_res.copy()
    df_display["Cartera_Neta"] = df_display["Cartera_Neta"].apply(lambda x: f"{int(x):,}")
    df_display["Obj_Pepsico"] = df_display["Obj_Pepsico"].apply(lambda x: f"{int(round(x)):,}")
    df_display["Cump_Pepsico_Pct"] = df_display["Cump_Pepsico_Pct"].apply(lambda x: f"{x:,.2f}%")
    df_display["Obj_Fuerza_Ventas"] = df_display["Obj_Fuerza_Ventas"].apply(lambda x: f"{int(round(x)):,}")
    df_display["Cump_Fuerza_Ventas_Pct"] = df_display["Cump_Fuerza_Ventas_Pct"].apply(lambda x: f"{x:,.2f}%")
    df_display["Avance_CCC"] = df_display["Avance_CCC"].apply(lambda x: f"{int(x):,}")

    df_display = df_display.rename(columns={
        "Taxonomia": "Taxonomía",
        "Cartera_Neta": "Cartera Neta (NC)",
        "Obj_Pepsico": "Obj de Pepsico",
        "Cump_Pepsico_Pct": "% Cump Obj Pepsico",
        "Obj_Fuerza_Ventas": "Objetivo a Fuerza de Ventas",
        "Cump_Fuerza_Ventas_Pct": "% Cump Obj Fuerza de Ventas",
        "Avance_CCC": "Avance CCC"
    })

    return df_res, df_display


def _calcular_minegocio_taxonomia_detallado(df_vta_prep_k, df_universo, maestro_v, anio_op, mes_op, dia_matinal, sup_seleccionado):
    try:
        df_ausencias = db.cargar_tabla_sql("SELECT * FROM ausencias")
    except Exception:
        df_ausencias = pd.DataFrame()

    # UNIFICACIÓN ABSOLUTA: Usamos estrictamente el DataFrame preparado corporativo (df_vta_prep_k)
    df_vta_mn = preparar_ventas_mn(df_vta_prep_k, df_ausencias, anio_op, mes_op, dia_matinal)
    vtas_per = df_vta_mn[df_vta_mn["Periodo"].isin(["Arrastre", "Actual"])].copy() if not df_vta_mn.empty and "Periodo" in df_vta_mn.columns else df_vta_mn.copy()

    col_pesos = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in vtas_per.columns), None)
    col_kilos = next((c for c in ["PesoKg", "PESOKG", "Kilos"] if c in vtas_per.columns), None)
    col_cant = next((c for c in ["CantBase", "CANTBASE", "Cantidad", "Unidades"] if c in vtas_per.columns), None)

    vtas_per["_gross_calc"] = pd.to_numeric(vtas_per[col_pesos], errors="coerce").fillna(0.0) if col_pesos else 0.0
    vtas_per["_kilos_calc"] = pd.to_numeric(vtas_per[col_kilos], errors="coerce").fillna(0.0) if col_kilos else 0.0
    vtas_per["_cant_calc"] = pd.to_numeric(vtas_per[col_cant], errors="coerce").fillna(0.0) if col_cant else 0.0

    col_cli_vta = next((c for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"] if c in vtas_per.columns), "Cliente")
    vtas_per["Cliente"] = pd.to_numeric(vtas_per[col_cli_vta], errors="coerce").astype("Int64")

    vtas_per["_mn_gross_val"] = np.where(vtas_per["Es_MiNegocio"], vtas_per["_gross_calc"], 0.0)
    vtas_per["_mn_kilos_val"] = np.where(vtas_per["Es_MiNegocio"], vtas_per["_kilos_calc"], 0.0)

    cli_agg = vtas_per.groupby("Cliente", as_index=False).agg(
        Gross_Total=("_gross_calc", "sum"),
        Gross_MN=("_mn_gross_val", "sum"),
        Kilos_Total=("_kilos_calc", "sum"),
        Kilos_MN=("_mn_kilos_val", "sum"),
        Total_Cant=("_cant_calc", "sum"),
        Total_Imp=("_gross_calc", "sum")
    )
    cli_agg["Es_CCC"] = cli_agg["Total_Cant"].ge(3) & cli_agg["Total_Imp"].ge(1)
    cli_agg["Pct_MN_Gross"] = (cli_agg["Gross_MN"] / cli_agg["Gross_Total"].replace(0, pd.NA)).mul(100.0).clip(lower=0, upper=100).fillna(0.0)

    cond_nodig = (cli_agg["Pct_MN_Gross"] <= 0.01).fillna(False)
    cond_hibr = ((cli_agg["Pct_MN_Gross"] > 0.01) & (cli_agg["Pct_MN_Gross"] < 70.0)).fillna(False)
    cli_agg["Categoria_Digital"] = np.select(
        [cond_nodig, cond_hibr],
        ["No Digital", "Híbridos"],
        default="Fully Digital"
    )

    univ = df_universo.copy() if df_universo is not None and not df_universo.empty else pd.DataFrame()
    if not univ.empty:
        col_c_u = next((c for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"] if c in univ.columns), univ.columns[0])
        univ["Cliente"] = pd.to_numeric(univ[col_c_u], errors="coerce").astype("Int64")

        tax_col = next((c for c in univ.columns if "taxonomia" in str(c).lower() or "segmentoclientecodigo" in str(c).lower()), None)
        if tax_col:
            univ["Taxonomia"] = univ[tax_col].fillna("").astype(str).str.strip().str.upper()
        else:
            univ["Taxonomia"] = "A"

        pos_v_u = next((c for c in univ.columns if any(k in str(c).lower() for k in ["codven", "vendedor"])), None)
        if pos_v_u:
            univ["CodVendedor"] = pd.to_numeric(univ[pos_v_u], errors="coerce").astype("Int64")

        univ = univ[univ["Taxonomia"].isin(["A", "B", "C", "D"])].dropna(subset=["Cliente"])

    vend_map = pd.DataFrame()
    if maestro_v is not None and not maestro_v.empty:
        c_cod = next((c for c in maestro_v.columns if "cod" in str(c).lower()), maestro_v.columns[0])
        c_sup = next((c for c in maestro_v.columns if "sup" in str(c).lower()), maestro_v.columns[2] if len(maestro_v.columns) > 2 else maestro_v.columns[0])
        vend_map["CodVendedor"] = pd.to_numeric(maestro_v[c_cod], errors="coerce").astype("Int64")
        vend_map["SUP"] = maestro_v[c_sup].fillna("").astype(str).str.strip()
        vend_map = vend_map.drop_duplicates("CodVendedor")

    if not univ.empty and not vend_map.empty and "CodVendedor" in univ.columns:
        univ = univ.merge(vend_map, on="CodVendedor", how="left")
    elif not univ.empty:
        univ["SUP"] = "GENERAL"

    if sup_seleccionado != "TODOS" and not univ.empty and "SUP" in univ.columns:
        univ = univ[univ["SUP"].astype(str).str.strip() == str(sup_seleccionado).strip()].copy()

    if not univ.empty and not cli_agg.empty:
        df_merged = univ.merge(cli_agg, on="Cliente", how="left")
    else:
        df_merged = univ.copy()
        df_merged["Gross_Total"] = 0.0
        df_merged["Gross_MN"] = 0.0
        df_merged["Kilos_Total"] = 0.0
        df_merged["Kilos_MN"] = 0.0
        df_merged["Es_CCC"] = False
        df_merged["Categoria_Digital"] = "No Digital"

    df_merged["Gross_Total"] = df_merged["Gross_Total"].fillna(0.0)
    df_merged["Gross_MN"] = df_merged["Gross_MN"].fillna(0.0)
    df_merged["Kilos_Total"] = df_merged["Kilos_Total"].fillna(0.0)
    df_merged["Kilos_MN"] = df_merged["Kilos_MN"].fillna(0.0)
    df_merged["Es_CCC"] = df_merged["Es_CCC"].fillna(False)
    df_merged["Categoria_Digital"] = df_merged["Categoria_Digital"].fillna("No Digital")

    tax_base = pd.DataFrame({"Taxonomia": ["A", "B", "C", "D"]})

    gross_g = df_merged.groupby("Taxonomia", as_index=False).agg(
        Gross_Total=("Gross_Total", "sum"),
        Gross_MN=("Gross_MN", "sum")
    )
    res_gross = tax_base.merge(gross_g, on="Taxonomia", how="left").fillna(0.0)
    
    try:
        df_v20_total = df_vta_prep_k[
            (df_vta_prep_k["CodVendedor"] == 20) & 
            df_vta_prep_k["Periodo"].isin(["Arrastre", "Actual"])
        ].copy() if not df_vta_prep_k.empty else pd.DataFrame()
        
        if not df_v20_total.empty:
            val_v20_gross = pd.to_numeric(df_v20_total[col_pesos], errors="coerce").sum() if col_pesos else 0.0
            suma_gross_actual = res_gross["Gross_Total"].sum()
            if suma_gross_actual > 0:
                for idx, row in res_gross.iterrows():
                    proporcion = row["Gross_Total"] / suma_gross_actual
                    res_gross.loc[idx, "Gross_Total"] += (val_v20_gross * proporcion)
    except Exception:
        pass

    res_gross["Adopcion_Gross_Pct"] = (res_gross["Gross_MN"] / res_gross["Gross_Total"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)

    kilos_g = df_merged.groupby("Taxonomia", as_index=False).agg(
        Kilos_Total=("Kilos_Total", "sum"),
        Kilos_MN=("Kilos_MN", "sum")
    )
    res_kilos = tax_base.merge(kilos_g, on="Taxonomia", how="left").fillna(0.0)
    res_kilos["Adopcion_Kilos_Pct"] = (res_kilos["Kilos_MN"] / res_kilos["Kilos_Total"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)

    ccc_cartera = df_merged.groupby("Taxonomia", as_index=False).agg(
        Cartera_Total=("Cliente", "count"),
        CCC_Total=("Es_CCC", lambda x: int(x.sum()))
    )
    
    ccc_compradores = df_merged[df_merged["Es_CCC"] == True].groupby(["Taxonomia", "Categoria_Digital"], as_index=False).agg(
        Cantidad=("Cliente", "count")
    )
    ccc_pivot = ccc_compradores.pivot_table(index="Taxonomia", columns="Categoria_Digital", values="Cantidad", fill_value=0).reset_index()
    ccc_pivot.columns.name = None

    for cat in ["No Digital", "Híbridos", "Fully Digital"]:
        if cat not in ccc_pivot.columns:
            ccc_pivot[cat] = 0

    res_ccc = tax_base.merge(ccc_cartera, on="Taxonomia", how="left").merge(ccc_pivot, on="Taxonomia", how="left").fillna(0)
    res_ccc[["Cartera_Total", "CCC_Total", "No Digital", "Híbridos", "Fully Digital"]] = res_ccc[["Cartera_Total", "CCC_Total", "No Digital", "Híbridos", "Fully Digital"]].astype(int)

    return res_gross, res_kilos, res_ccc


@st.cache_data(show_spinner=False)
def _calcular_motor_gerencial_global(df_vta, df_universo, df_rutas, df_ausencias, anio_op, mes_op, dia_matinal, dia_venta, sup_seleccionado, huella_global):
    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        if not maestro_v.empty and "Mes" in maestro_v.columns:
            mv_per = maestro_v[(maestro_v["Mes"].astype(str) == str(mes_op)) & (maestro_v["Anio"].astype(str) == str(anio_op))]
            if not mv_per.empty:
                maestro_v = mv_per
    except Exception:
        maestro_v = pd.DataFrame()

    try:
        maestro_s = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos ORDER BY rowid ASC")
    except Exception:
        maestro_s = pd.DataFrame()

    try:
        maestro_cebe = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if not maestro_cebe.empty and "Mes" in maestro_cebe.columns:
            mc_per = maestro_cebe[(maestro_cebe["Mes"].astype(str) == str(mes_op)) & (maestro_cebe["Anio"].astype(str) == str(anio_op))]
            if not mc_per.empty:
                maestro_cebe = mc_per
    except Exception:
        maestro_cebe = pd.DataFrame()

    df_marcas_maestro = db.cargar_tabla_sql("SELECT * FROM parametros_marcas")

    if maestro_v.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), [], {}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    col_sup_v = next((c for c in maestro_v.columns if "sup" in str(c).strip().lower()), maestro_v.columns[2] if len(maestro_v.columns) > 2 else maestro_v.columns[0])
    col_cod_v = next((c for c in maestro_v.columns if "cod" in str(c).strip().lower()), maestro_v.columns[0])
    
    maestro_v["Cod_Clean"] = pd.to_numeric(maestro_v[col_cod_v], errors="coerce").astype("Int64").astype(str).str.strip()
    maestro_v["Sup_Clean"] = maestro_v[col_sup_v].fillna("").astype(str).str.strip()
    sup_map = maestro_v.set_index("Cod_Clean")["Sup_Clean"].to_dict()

    df_vta_prep_k = preparar_datos_ventas_segmento(df_vta, df_ausencias, anio_op, mes_op, dia_matinal)
    
    reporte_kilos_base = generar_reporte_avance_kilos_segmento(df_vta_prep_k, df_rutas, maestro_v, maestro_s, maestro_cebe, dia_venta, anio_op, mes_op, "TODOS")

    kilos_oper_todo = pd.DataFrame()
    kilos_oper_ajustado = pd.DataFrame()

    if not reporte_kilos_base.empty:
        rep_k = reporte_kilos_base.copy()
        rep_k["CodVend_Clean"] = pd.to_numeric(rep_k["CodVendedor"], errors="coerce").astype("Int64").astype(str).str.strip()
        rep_k["Supervisor"] = rep_k["CodVend_Clean"].map(sup_map).fillna("GENERAL")

        dp_todo = rep_k["Días Pasados"].astype(float).replace(0, 1.0)
        dr_todo = rep_k["Días Restantes Todo"].astype(float)
        p_diario = (rep_k["Actual"] + rep_k.get("Ajuste_Reemp_Actual", 0.0)) / dp_todo
        
        rep_k["Operativo"] = rep_k["Arrastre"] + rep_k["Actual"] + rep_k.get("Ajuste_Por_Reemp", 0.0)
        rep_k["Proyectado_Todo"] = rep_k["Operativo"]
        mask_t = dr_todo > 0
        if mask_t.any():
            rep_k.loc[mask_t, "Proyectado_Todo"] = (p_diario[mask_t] * dr_todo[mask_t]) + rep_k.loc[mask_t, "Operativo"]

        dr_ajustado = rep_k["Días Restantes Ajustado"].astype(float)
        rep_k["Proyectado_Ajustado"] = rep_k["Operativo"]
        if mask_t.any():
            rep_k.loc[mask_t, "Proyectado_Ajustado"] = (p_diario[mask_t] * dr_ajustado[mask_t]) + rep_k.loc[mask_t, "Operativo"]

        col_imp_neto = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df_vta_prep_k.columns), None)
        
        if not df_vta_prep_k.empty and col_imp_neto:
            df_vta_prep_k["_Imp_Real"] = pd.to_numeric(df_vta_prep_k[col_imp_neto], errors="coerce").fillna(0.0)
            
            codigos_validos_padron = set(maestro_v[col_cod_v].dropna().astype("Int64").tolist()) if not maestro_v.empty else set()
            
            cod_op_g = df_vta_prep_k.get("CodVendedorOperativo", pd.Series(pd.NA, index=df_vta_prep_k.index))
            cod_tit_g = df_vta_prep_k["CodVendedor"]
            reemp_g = df_vta_prep_k.get("Reemplazo", pd.Series(pd.NA, index=df_vta_prep_k.index))
            
            is_special_g = ((reemp_g == 99) | (cod_op_g == 99) | (cod_tit_g == 99)).fillna(False)
            valid_op_g = cod_op_g.isin(codigos_validos_padron).fillna(False)
            valid_tit_g = cod_tit_g.isin(codigos_validos_padron).fillna(False)
            
            df_vta_prep_k["CodVend_Op_Gross"] = np.select(
                [is_special_g, valid_op_g, valid_tit_g],
                [-998, cod_op_g.fillna(-999).astype(int), cod_tit_g.fillna(-999).astype(int)],
                default=-999
            )
            df_vta_prep_k["CodVend_Op_Gross"] = pd.Series(df_vta_prep_k["CodVend_Op_Gross"]).replace(-999, pd.NA).astype("Int64")
            
            cond_gross_999 = (df_vta_prep_k["CodVend_Op_Gross"] == -999).fillna(False)
            cond_gross_998 = (df_vta_prep_k["CodVend_Op_Gross"] == -998).fillna(False)
            
            sup_op_g = df_vta_prep_k["CodVend_Op_Gross"].astype(str).map(sup_map)
            sup_tit_g = df_vta_prep_k["CodVendedor"].astype(str).map(sup_map)
            
            df_vta_prep_k["Supervisor_Gross"] = np.select(
                [cond_gross_999, cond_gross_998],
                ["GENERAL", sup_tit_g.fillna("GENERAL")],
                default=sup_op_g.fillna(sup_tit_g).fillna("GENERAL")
            )

            df_operativo_real = df_vta_prep_k[
                (df_vta_prep_k["Periodo"].isin(["Arrastre", "Actual"])) & 
                (df_vta_prep_k["SEGMENTO"].notna())
            ].copy()

            gross_operativo_agg = df_operativo_real.groupby(["Supervisor_Gross", "SEGMENTO"], as_index=False)["_Imp_Real"].sum().rename(
                columns={"_Imp_Real": "Importe_Operativo_Arg", "Supervisor_Gross": "Supervisor"}
            )
        else:
            gross_operativo_agg = pd.DataFrame(columns=["Supervisor", "SEGMENTO", "Importe_Operativo_Arg"])

        kilos_oper_todo = rep_k.groupby(["Supervisor", "SEGMENTO"], as_index=False).agg({
            "Arrastre": "sum", "Actual": "sum", "Operativo": "sum",
            "Proyectado_Todo": "sum"
        }).rename(columns={"Operativo": "Kilos_Operativos_Kg", "Proyectado_Todo": "Kilos_Proyectados_Kg"})

        if not gross_operativo_agg.empty:
            kilos_oper_todo = kilos_oper_todo.merge(gross_operativo_agg, on=["Supervisor", "SEGMENTO"], how="left").fillna(0.0)
        else:
            kilos_oper_todo["Importe_Operativo_Arg"] = 0.0

        kilos_oper_todo["Precio_Implicito"] = kilos_oper_todo["Importe_Operativo_Arg"] / kilos_oper_todo["Kilos_Operativos_Kg"].replace(0, pd.NA)
        kilos_oper_todo["Precio_Implicito"] = kilos_oper_todo["Precio_Implicito"].fillna(0.0)
        
        precio_global_prom = kilos_oper_todo["Importe_Operativo_Arg"].sum() / max(1.0, kilos_oper_todo["Kilos_Operativos_Kg"].sum())
        kilos_oper_todo["Precio_Implicito"] = np.where(kilos_oper_todo["Precio_Implicito"] > 0, kilos_oper_todo["Precio_Implicito"], precio_global_prom)

        kilos_oper_todo["Gross_Proyectado_Arg"] = kilos_oper_todo["Kilos_Proyectados_Kg"] * kilos_oper_todo["Precio_Implicito"]

        kilos_oper_ajustado = kilos_oper_todo.copy()
        rep_k["Gross_Proyectado_Ajustado"] = rep_k["Proyectado_Ajustado"] * kilos_oper_todo.set_index(["Supervisor", "SEGMENTO"])["Precio_Implicito"].reindex(
            pd.MultiIndex.from_arrays([rep_k["Supervisor"], rep_k["SEGMENTO"]]), fill_value=precio_global_prom
        ).values

        kilos_oper_ajustado = rep_k.groupby(["Supervisor", "SEGMENTO"], as_index=False).agg({
            "Arrastre": "sum", "Actual": "sum", "Operativo": "sum",
            "Proyectado_Ajustado": "sum", "Gross_Proyectado_Ajustado": "sum"
        }).rename(columns={"Operativo": "Kilos_Operativos_Kg", "Proyectado_Ajustado": "Kilos_Proyectados_Kg", "Gross_Proyectado_Ajustado": "Gross_Proyectado_Arg"})
        
        if not gross_operativo_agg.empty:
            kilos_oper_ajustado = kilos_oper_ajustado.merge(gross_operativo_agg, on=["Supervisor", "SEGMENTO"], how="left").fillna(0.0)
        else:
            kilos_oper_ajustado["Importe_Operativo_Arg"] = 0.0

    df_futuro = df_vta_prep_k[df_vta_prep_k["Periodo"] == "Futuro"].copy() if not df_vta_prep_k.empty and "Periodo" in df_vta_prep_k.columns else pd.DataFrame()
    if not df_futuro.empty and "SEGMENTO" in df_futuro.columns:
        col_imp_neto_fut = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df_futuro.columns), None)
        df_futuro["Imp_Fut"] = pd.to_numeric(df_futuro[col_imp_neto_fut], errors="coerce").fillna(0.0) if col_imp_neto_fut else 0.0
        
        df_futuro["CodVen_Clean"] = pd.to_numeric(df_futuro["CodVendedor"], errors="coerce").astype("Int64").astype(str).str.strip()
        df_futuro["Supervisor"] = df_futuro["CodVen_Clean"].map(sup_map).fillna("GENERAL")

        futuro_seg_agg = df_futuro.groupby(["Supervisor", "SEGMENTO"], as_index=False).agg(
            Kilos_Disponibles=("PesoKg", "sum"),
            Gross_Disponible=("Imp_Fut", "sum")
        )
    else:
        futuro_seg_agg = pd.DataFrame(columns=["Supervisor", "SEGMENTO", "Kilos_Disponibles", "Gross_Disponible"])

    kilos_obj_g = pd.DataFrame(columns=["Supervisor", "SEGMENTO", "Objetivo_Kilos_Kg", "Objetivo_Importe_Arg"])
    if not maestro_cebe.empty and not df_vta_prep_k.empty and "Marca" in df_vta_prep_k.columns:
        col_m_cebe = next((c for c in maestro_cebe.columns if "marca" in str(c).strip().lower()), maestro_cebe.columns[0])
        col_obj_tn = next((c for c in maestro_cebe.columns if any(k in str(c).strip().lower() for k in ["obj_tn", "tn", "obj_mes"])), None)
        col_obj_gross = next((c for c in maestro_cebe.columns if any(k in str(c).strip().lower() for k in ["obj_gross", "gross"])), None)
        
        if col_obj_tn and col_obj_gross:
            maestro_cebe_clean = maestro_cebe.copy()
            maestro_cebe_clean["Marca_Key"] = maestro_cebe_clean[col_m_cebe].fillna("").astype(str).str.strip().str.upper()
            
            maestro_cebe_clean["Obj_Val_Kg"] = pd.to_numeric(maestro_cebe_clean[col_obj_tn], errors="coerce").fillna(0.0)
            maestro_cebe_clean["Obj_Val_Imp"] = pd.to_numeric(maestro_cebe_clean[col_obj_gross], errors="coerce").fillna(0.0)
            
            mapa_obj_kg = maestro_cebe_clean.groupby("Marca_Key")["Obj_Val_Kg"].sum().to_dict()
            mapa_obj_imp = maestro_cebe_clean.groupby("Marca_Key")["Obj_Val_Imp"].sum().to_dict()
            
            cod_vend_serie_obj = pd.to_numeric(df_vta_prep_k["CodVendedor"], errors="coerce").astype("Int64")
            df_vta_sin_20 = df_vta_prep_k[cod_vend_serie_obj != 20].copy()
            df_vta_sin_20["CodVen_Clean"] = cod_vend_serie_obj[cod_vend_serie_obj != 20].astype(str).str.strip()
            df_vta_sin_20["Supervisor"] = df_vta_sin_20["CodVen_Clean"].map(sup_map).fillna("GENERAL")
            df_vta_sin_20["Marca_Key"] = df_vta_sin_20["Marca"].astype(str).str.strip().str.upper()
            
            tot_marca_vta = df_vta_sin_20.groupby(["Supervisor", "Marca_Key", "SEGMENTO"])["PesoKg"].sum().reset_index()
            tot_marca_vta["Total_Marca"] = tot_marca_vta.groupby("Marca_Key")["PesoKg"].transform("sum").replace(0, 1.0)
            tot_marca_vta["Part_Marca_Seg"] = tot_marca_vta["PesoKg"] / tot_marca_vta["Total_Marca"]
            
            tot_marca_vta["Obj_Kilos_Marca"] = tot_marca_vta["Marca_Key"].map(mapa_obj_kg).fillna(0.0)
            tot_marca_vta["Obj_Gross_Marca"] = tot_marca_vta["Marca_Key"].map(mapa_obj_imp).fillna(0.0)
            
            tot_marca_vta["Obj_Seg_Kg"] = tot_marca_vta["Obj_Kilos_Marca"] * tot_marca_vta["Part_Marca_Seg"]
            tot_marca_vta["Obj_Seg_Imp"] = tot_marca_vta["Obj_Gross_Marca"] * tot_marca_vta["Part_Marca_Seg"]

            kilos_obj_g = tot_marca_vta.groupby(["Supervisor", "SEGMENTO"], as_index=False).agg(
                Objetivo_Kilos_Kg=("Obj_Seg_Kg", "sum"),
                Objetivo_Importe_Arg=("Obj_Seg_Imp", "sum")
            )

    cod_vend_serie_v20 = pd.to_numeric(df_vta_prep_k["CodVendedor"], errors="coerce").astype("Int64")
    df_v20 = df_vta_prep_k[(cod_vend_serie_v20 == 20) & df_vta_prep_k["Periodo"].isin(["Arrastre", "Actual"])].copy()
    
    if not df_v20.empty and "SEGMENTO" in df_v20.columns:
        col_imp_neto_v20 = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df_v20.columns), None)
        df_v20["ImporteNetoItem"] = pd.to_numeric(df_v20[col_imp_neto_v20], errors="coerce").fillna(0.0) if col_imp_neto_v20 else 0.0
        
        df_v20_arr = df_v20[df_v20["Periodo"] == "Arrastre"].groupby("SEGMENTO", as_index=False).agg(Arrastre_V20=("PesoKg", "sum"), Arrastre_Imp_V20=("ImporteNetoItem", "sum"))
        df_v20_act = df_v20[df_v20["Periodo"] == "Actual"].groupby("SEGMENTO", as_index=False).agg(Actual_V20=("PesoKg", "sum"), Actual_Imp_V20=("ImporteNetoItem", "sum"))
        df_v20_imp = df_v20.groupby("SEGMENTO", as_index=False)["ImporteNetoItem"].sum().rename(columns={"ImporteNetoItem": "Gross_V20"})
        
        v20_agg = df_v20_arr.merge(df_v20_act, on="SEGMENTO", how="outer").merge(df_v20_imp, on="SEGMENTO", how="outer").fillna(0.0)
    else:
        v20_agg = pd.DataFrame(columns=["SEGMENTO", "Arrastre_V20", "Actual_V20", "Arrastre_Imp_V20", "Actual_Imp_V20", "Gross_V20"])

    filtros_globales_base = {"anio": anio_op, "mes": mes_op, "dia_matinal": dia_matinal, "dia_venta": dia_venta, "supervisor": sup_seleccionado}
    
    rep_mn_global = generar_reporte_mn_taxonomia(df_vta, df_universo, maestro_v, filtros_globales_base)
    
    cartera_base_global = st.session_state.get("_cob_cartera_base", pd.DataFrame())
    vtas_agrup_global = st.session_state.get("_cob_vtas_agrupadas", pd.DataFrame())
    marcas_lst = st.session_state.get("_cob_marcas", [])
    mapa_obj = st.session_state.get("_cob_mapa_objetivos", {})
    
    if cartera_base_global.empty or not marcas_lst:
        from modules.rep_cob_marca import generar_reporte_cobertura_marca
        generar_reporte_cobertura_marca(df_vta, df_universo, maestro_v, df_marcas_maestro, filtros_globales_base)
        cartera_base_global = st.session_state.get("_cob_cartera_base", pd.DataFrame())
        vtas_agrup_global = st.session_state.get("_cob_vtas_agrupadas", pd.DataFrame())
        marcas_lst = st.session_state.get("_cob_marcas", [])
        mapa_obj = st.session_state.get("_cob_mapa_objetivos", {})

    res_gross_mn, res_kilos_mn, res_ccc_mn = _calcular_minegocio_taxonomia_detallado(df_vta_prep_k, df_universo, maestro_v, anio_op, mes_op, dia_matinal, sup_seleccionado)

    return kilos_obj_g, kilos_oper_todo, kilos_oper_ajustado, v20_agg, futuro_seg_agg, rep_mn_global, cartera_base_global, vtas_agrup_global, marcas_lst, mapa_obj, res_gross_mn, res_kilos_mn, res_ccc_mn

def render_rep_gerencial(df_vta, df_universo, df_rutas, df_ausencias, filtros_globales=None):
    st.subheader("📈 Tablero Ejecutivo Gerencial - Consolidado Integral")
    st.markdown("Vista directiva completa con el desglose detallado por segmentos, taxonomías, marcas, kilos e importes de la compañía.")

    if filtros_globales is None:
        filtros_globales = {"anio": 2026, "mes": 9, "dia_matinal": "02/09/2026", "dia_venta": "01/09/2026", "supervisor": "TODOS"}

    anio_op = int(filtros_globales.get("anio", 2026))
    mes_op = int(filtros_globales.get("mes", 9))
    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026")
    dia_venta = filtros_globales.get("dia_venta", "01/09/2026")

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        col_sup_v = next((c for c in maestro_v.columns if "sup" in str(c).strip().lower()), maestro_v.columns[2] if len(maestro_v.columns) > 2 else maestro_v.columns[0])
        supervisores_disp = ["TODOS"] + sorted(list(set(str(s).strip() for s in maestro_v[col_sup_v].dropna().unique() if str(s).strip() != "")))
    except Exception:
        supervisores_disp = ["TODOS"]

    col_sup_sel, col_ajuste_sel, _ = st.columns([2, 2, 3])
    with col_sup_sel:
        sup_seleccionado = st.selectbox("Filtrar Tablero por Supervisor", options=supervisores_disp, index=0, key="gerencial_filtro_sup")
    with col_ajuste_sel:
        modo_ajuste_ger = st.selectbox("Ajuste por Entrega", options=["TODO", "AJUSTADO"], index=1, key="gerencial_filtro_ajuste")

    huella_global = f"{len(df_vta)}_{len(df_universo)}_{anio_op}_{mes_op}_{dia_matinal}_{sup_seleccionado}"

    kilos_obj_det_global, kilos_oper_todo, kilos_oper_ajustado, v20_agg_global, futuro_agg_global, rep_mn_global, cartera_base_global, vtas_agrup_global, marcas_lst, mapa_obj, res_gross_mn, res_kilos_mn, res_ccc_mn = _calcular_motor_gerencial_global(
        df_vta, df_universo, df_rutas, df_ausencias, anio_op, mes_op, dia_matinal, dia_venta, sup_seleccionado, huella_global
    )

    kilos_oper_detalle_global = kilos_oper_ajustado if modo_ajuste_ger == "AJUSTADO" else kilos_oper_todo

    if sup_seleccionado != "TODOS":
        if not kilos_oper_detalle_global.empty and "Supervisor" in kilos_oper_detalle_global.columns:
            kilos_operativos_g = kilos_oper_detalle_global[kilos_oper_detalle_global["Supervisor"].astype(str).str.strip() == sup_seleccionado].groupby("SEGMENTO", as_index=False).agg({
                "Arrastre": "sum", "Actual": "sum", 
                "Kilos_Operativos_Kg": "sum", "Importe_Operativo_Arg": "sum", 
                "Kilos_Proyectados_Kg": "sum", "Gross_Proyectado_Arg": "sum"
            })
        else:
            kilos_operativos_g = pd.DataFrame(columns=["SEGMENTO", "Arrastre", "Actual", "Kilos_Operativos_Kg", "Importe_Operativo_Arg", "Kilos_Proyectados_Kg", "Gross_Proyectado_Arg"])
        
        if not kilos_obj_det_global.empty and "Supervisor" in kilos_obj_det_global.columns:
            kilos_obj_g = kilos_obj_det_global[kilos_obj_det_global["Supervisor"].astype(str).str.strip() == sup_seleccionado].groupby("SEGMENTO", as_index=False).agg({"Objetivo_Kilos_Kg": "sum", "Objetivo_Importe_Arg": "sum"})
        else:
            kilos_obj_g = pd.DataFrame(columns=["SEGMENTO", "Objetivo_Kilos_Kg", "Objetivo_Importe_Arg"])

        if not futuro_agg_global.empty and "Supervisor" in futuro_agg_global.columns:
            futuro_segmento = futuro_agg_global[futuro_agg_global["Supervisor"].astype(str).str.strip() == sup_seleccionado].groupby("SEGMENTO", as_index=False).agg({"Kilos_Disponibles": "sum", "Gross_Disponible": "sum"})
        else:
            futuro_segmento = pd.DataFrame(columns=["SEGMENTO", "Kilos_Disponibles", "Gross_Disponible"])

        v20_segmento = pd.DataFrame(columns=["SEGMENTO", "Arrastre_V20", "Actual_V20", "Arrastre_Imp_V20", "Actual_Imp_V20", "Gross_V20"])

        cartera_base = cartera_base_global[cartera_base_global["SUP"].astype(str).str.strip() == sup_seleccionado].copy() if not cartera_base_global.empty and "SUP" in cartera_base_global.columns else pd.DataFrame()
    else:
        if not kilos_oper_detalle_global.empty:
            kilos_operativos_g = kilos_oper_detalle_global.groupby("SEGMENTO", as_index=False).agg({
                "Arrastre": "sum", "Actual": "sum", 
                "Kilos_Operativos_Kg": "sum", "Importe_Operativo_Arg": "sum", 
                "Kilos_Proyectados_Kg": "sum", "Gross_Proyectado_Arg": "sum"
            })
        else:
            kilos_operativos_g = pd.DataFrame(columns=["SEGMENTO", "Arrastre", "Actual", "Kilos_Operativos_Kg", "Importe_Operativo_Arg", "Kilos_Proyectados_Kg", "Gross_Proyectado_Arg"])
        
        if not kilos_obj_det_global.empty:
            kilos_obj_g = kilos_obj_det_global.groupby("SEGMENTO", as_index=False).agg({
                "Objetivo_Kilos_Kg": "sum", 
                "Objetivo_Importe_Arg": "sum"
            })
        else:
            kilos_obj_g = pd.DataFrame(columns=["SEGMENTO", "Objetivo_Kilos_Kg", "Objetivo_Importe_Arg"])

        if not futuro_agg_global.empty:
            futuro_segmento = futuro_agg_global.groupby("SEGMENTO", as_index=False).agg({"Kilos_Disponibles": "sum", "Gross_Disponible": "sum"})
        else:
            futuro_segmento = pd.DataFrame(columns=["SEGMENTO", "Kilos_Disponibles", "Gross_Disponible"])

        v20_segmento = v20_agg_global
        cartera_base = cartera_base_global.copy()

    df_seg = kilos_obj_g.merge(kilos_operativos_g, on="SEGMENTO", how="outer").fillna(0.0)
    
    total_proyectado_preventistas_puro = float(kilos_operativos_g["Kilos_Proyectados_Kg"].sum()) if not kilos_operativos_g.empty else 0.0

    if not v20_segmento.empty:
        df_seg = df_seg.merge(v20_segmento, on="SEGMENTO", how="left").fillna(0.0)
        df_seg["Arrastre"] += df_seg["Arrastre_V20"]
        df_seg["Actual"] += df_seg["Actual_V20"]
        df_seg["Kilos_Operativos_Kg"] += (df_seg["Arrastre_V20"] + df_seg["Actual_V20"])
        df_seg["Importe_Operativo_Arg"] += df_seg["Gross_V20"]
        df_seg["Kilos_Proyectados_Kg"] += (df_seg["Arrastre_V20"] + df_seg["Actual_V20"])
        df_seg["Gross_Proyectado_Arg"] += df_seg["Gross_V20"]

    if not futuro_segmento.empty:
        df_seg = df_seg.merge(futuro_segmento, on="SEGMENTO", how="left").fillna(0.0)
    else:
        df_seg["Kilos_Disponibles"] = 0.0
        df_seg["Gross_Disponible"] = 0.0

    total_v20_kilos = float((v20_segmento["Arrastre_V20"] + v20_segmento["Actual_V20"]).sum()) if not v20_segmento.empty else 0.0

    df_seg["Objetivo_Kilos_Kg"] = df_seg["Objetivo_Kilos_Kg"].round(2)
    df_seg["Objetivo_Importe_Arg"] = df_seg["Objetivo_Importe_Arg"].round(2)
    df_seg["Arrastre"] = df_seg["Arrastre"].round(2)
    df_seg["Actual"] = df_seg["Actual"].round(2)
    df_seg["Kilos_Operativos_Kg"] = df_seg["Kilos_Operativos_Kg"].round(2)
    df_seg["Importe_Operativo_Arg"] = df_seg["Importe_Operativo_Arg"].round(2)
    df_seg["Kilos_Proyectados_Kg"] = df_seg["Kilos_Proyectados_Kg"].round(2)
    df_seg["Gross_Proyectado_Arg"] = df_seg["Gross_Proyectado_Arg"].round(2)
    
    df_seg["Cumplimiento_Actual_Pct"] = (df_seg["Importe_Operativo_Arg"] / df_seg["Objetivo_Importe_Arg"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    df_seg["Cumplimiento_Proyectado_Pct"] = (df_seg["Kilos_Proyectados_Kg"] / df_seg["Objetivo_Kilos_Kg"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    df_seg["Cumplimiento_Gross_Proy_Pct"] = (df_seg["Gross_Proyectado_Arg"] / df_seg["Objetivo_Importe_Arg"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    df_seg["Cumplimiento_Gross_Actual_Pct"] = (df_seg["Importe_Operativo_Arg"] / df_seg["Objetivo_Importe_Arg"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)

    df_seg["Raw_Bache_Kgs"] = (df_seg["Objetivo_Kilos_Kg"] - df_seg["Kilos_Proyectados_Kg"]).clip(lower=0)
    df_seg["Raw_Bache_Gross"] = (df_seg["Objetivo_Importe_Arg"] - df_seg["Gross_Proyectado_Arg"]).clip(lower=0)

    tot_obj_kilos = float(df_seg["Objetivo_Kilos_Kg"].sum())
    tot_proy_k = float(df_seg["Kilos_Proyectados_Kg"].sum())
    global_gap_kilos = max(0.0, tot_obj_kilos - tot_proy_k)

    tot_obj_gross = float(df_seg["Objetivo_Importe_Arg"].sum())
    tot_proy_g = float(df_seg["Gross_Proyectado_Arg"].sum())
    global_gap_gross = max(0.0, tot_obj_gross - tot_proy_g)

    sum_baches_kilos = df_seg["Raw_Bache_Kgs"].sum()
    factor_kilos = (global_gap_kilos / sum_baches_kilos) if sum_baches_kilos > 0 else 0.0

    sum_baches_gross = df_seg["Raw_Bache_Gross"].sum()
    factor_gross = (global_gap_gross / sum_baches_gross) if sum_baches_gross > 0 else 0.0

    df_seg["Futuro_A_Incorporar_Kgs"] = (df_seg["Raw_Bache_Kgs"] * factor_kilos).round(2)
    df_seg["Futuro_A_Incorporar_Gross"] = (df_seg["Raw_Bache_Gross"] * factor_gross).round(2)

    orden_segmentos_maestro = [
        "GOLD Salty",
        "GOLD Crakers",
        "SILVER Salty",
        "SILVER Crakers",
        "SILVER Cereals"
    ]
    mapping_orden = {str(seg).strip(): i for i, seg in enumerate(orden_segmentos_maestro)}
    df_seg["_orden_idx"] = df_seg["SEGMENTO"].astype(str).str.strip().map(mapping_orden).fillna(999)
    df_seg = df_seg.sort_values(by="_orden_idx").drop(columns=["_orden_idx"]).reset_index(drop=True)

    df_gross_seg = df_seg[[
        "SEGMENTO", "Objetivo_Importe_Arg", "Importe_Operativo_Arg", "Cumplimiento_Gross_Actual_Pct",
        "Gross_Proyectado_Arg", "Cumplimiento_Gross_Proy_Pct", "Futuro_A_Incorporar_Gross", "Gross_Disponible"
    ]].copy().rename(columns={
        "Objetivo_Importe_Arg": "Objetivo Gross Pepsico", "Importe_Operativo_Arg": "Operativo Gross",
        "Cumplimiento_Gross_Actual_Pct": "% Cump. Actual Gross", "Gross_Proyectado_Arg": "Proyectado Gross",
        "Cumplimiento_Gross_Proy_Pct": "% Cumpl. Proy. Gross", "Futuro_A_Incorporar_Gross": "A Incorporar Gross",
        "Gross_Disponible": "Gross Disponible"
    })

    df_gross_display = df_gross_seg.copy()
    for col in ["Objetivo Gross Pepsico", "Operativo Gross", "Proyectado Gross", "A Incorporar Gross", "Gross Disponible"]:
        df_gross_display[col] = df_gross_display[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
    for col in ["% Cump. Actual Gross", "% Cumpl. Proy. Gross"]:
        df_gross_display[col] = df_gross_display[col].apply(lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%")

    tot_operativo_g = float(df_seg["Importe_Operativo_Arg"].sum())
    cump_actual_g_val = round((tot_operativo_g / tot_obj_gross * 100.0) if tot_obj_gross > 0 else 0.0, 2)
    cump_proy_g_val = round((tot_proy_g / tot_obj_gross * 100.0) if tot_obj_gross > 0 else 0.0, 2)
    tot_incorporar_g = float(df_gross_seg["A Incorporar Gross"].sum())

    df_kilos_seg = df_seg[[
        "SEGMENTO", "Objetivo_Kilos_Kg", "Arrastre", "Actual", 
        "Kilos_Operativos_Kg", "Cumplimiento_Actual_Pct", "Kilos_Proyectados_Kg", 
        "Cumplimiento_Proyectado_Pct", "Futuro_A_Incorporar_Kgs", "Kilos_Disponibles"
    ]].copy().rename(columns={
        "Objetivo_Kilos_Kg": "Objetivo Kilos Pepsico", "Arrastre": "Arrastre Kilos", "Actual": "Mes Actual Kilos",
        "Kilos_Operativos_Kg": "Operativo Kilos", "Cumplimiento_Actual_Pct": "% Cump. Actual Kilos",
        "Kilos_Proyectados_Kg": "Proyectado Kilos", "Cumplimiento_Proyectado_Pct": "% Cump. Proy. Kilos",
        "Futuro_A_Incorporar_Kgs": "A Incorporar Kilos", "Kilos_Disponibles": "Kilos Disponibles"
    })

    df_kilos_display = df_kilos_seg.copy()
    for col in ["Objetivo Kilos Pepsico", "Arrastre Kilos", "Mes Actual Kilos", "Operativo Kilos", "Proyectado Kilos", "A Incorporar Kilos", "Kilos Disponibles"]:
        df_kilos_display[col] = df_kilos_display[col].apply(lambda x: f"{x:,.2f} kg" if pd.notna(x) else "0.00 kg")
    for col in ["% Cump. Actual Kilos", "% Cump. Proy. Kilos"]:
        df_kilos_display[col] = df_kilos_display[col].apply(lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%")

    tot_operativo_k = float(df_seg["Kilos_Operativos_Kg"].sum())
    cump_actual_k_val = round((tot_operativo_k / tot_obj_kilos * 100.0) if tot_obj_kilos > 0 else 0.0, 2)
    cump_proy_k_val = round((tot_proy_k / tot_obj_kilos * 100.0) if tot_obj_kilos > 0 else 0.0, 2)
    tot_incorporar_k = float(df_kilos_seg["A Incorporar Kilos"].sum())

    df_ccc_tax_raw, df_ccc_display = _calcular_ccc_taxonomia_gerencial(df_vta, df_universo, maestro_v, anio_op, mes_op, dia_matinal, sup_seleccionado)

    tot_cartera_ger = int(df_ccc_tax_raw["Cartera_Neta"].sum()) if not df_ccc_tax_raw.empty else 0
    tot_obj_pep_ger = float(df_ccc_tax_raw["Obj_Pepsico"].sum()) if not df_ccc_tax_raw.empty else 0.0
    tot_obj_fv_ger = float(df_ccc_tax_raw["Obj_Fuerza_Ventas"].sum()) if not df_ccc_tax_raw.empty else 0.0
    tot_avance_ccc_ger = int(df_ccc_tax_raw["Avance_CCC"].sum()) if not df_ccc_tax_raw.empty else 0

    cump_pep_ger_pct = (tot_avance_ccc_ger / tot_obj_pep_ger * 100.0) if tot_obj_pep_ger > 0 else 0.0
    cump_fv_ger_pct = (tot_avance_ccc_ger / tot_obj_fv_ger * 100.0) if tot_obj_fv_ger > 0 else 0.0

    tot_ventas_mn_ger = float(res_gross_mn["Gross_Total"].sum()) if not res_gross_mn.empty else 0.0
    tot_app_mn_ger = float(res_gross_mn["Gross_MN"].sum()) if not res_gross_mn.empty else 0.0
    pct_venta_mn_ger = (tot_app_mn_ger / tot_ventas_mn_ger * 100.0) if tot_ventas_mn_ger > 0 else 0.0

    tot_cartera_mn_ger = int(res_ccc_mn["Cartera_Total"].sum()) if not res_ccc_mn.empty else 0
    tot_nodig_mn_ger = int(res_ccc_mn["No Digital"].sum()) if not res_ccc_mn.empty else 0
    tot_hibr_mn_ger = int(res_ccc_mn["Híbridos"].sum()) if not res_ccc_mn.empty else 0
    tot_fully_mn_ger = int(res_ccc_mn["Fully Digital"].sum()) if not res_ccc_mn.empty else 0

    df_gross_mn_disp = res_gross_mn.copy()
    df_gross_mn_disp["Gross_Total"] = df_gross_mn_disp["Gross_Total"].apply(lambda x: f"${x:,.2f}")
    df_gross_mn_disp["Gross_MN"] = df_gross_mn_disp["Gross_MN"].apply(lambda x: f"${x:,.2f}")
    df_gross_mn_disp["Adopcion_Gross_Pct"] = df_gross_mn_disp["Adopcion_Gross_Pct"].apply(lambda x: f"{x:,.2f}%")
    df_gross_mn_disp = df_gross_mn_disp.rename(columns={"Taxonomia": "Taxonomía", "Gross_Total": "Gross Total ($)", "Gross_MN": "Gross MiNegocio ($)", "Adopcion_Gross_Pct": "% Adopción Gross"})

    df_kilos_mn_disp = res_kilos_mn.copy()
    df_kilos_mn_disp["Kilos_Total"] = df_kilos_mn_disp["Kilos_Total"].apply(lambda x: f"{x:,.2f} kg")
    df_kilos_mn_disp["Kilos_MN"] = df_kilos_mn_disp["Kilos_MN"].apply(lambda x: f"{x:,.2f} kg")
    df_kilos_mn_disp["Adopcion_Kilos_Pct"] = df_kilos_mn_disp["Adopcion_Kilos_Pct"].apply(lambda x: f"{x:,.2f}%")
    df_kilos_mn_disp = df_kilos_mn_disp.rename(columns={"Taxonomia": "Taxonomía", "Kilos_Total": "Kilos Totales (kg)", "Kilos_MN": "Kilos MiNegocio (kg)", "Adopcion_Kilos_Pct": "% Adopción Kilos"})

    df_ccc_mn_disp = res_ccc_mn.copy()
    df_ccc_mn_disp["Cartera_Total"] = df_ccc_mn_disp["Cartera_Total"].apply(lambda x: f"{int(x):,}")
    df_ccc_mn_disp["CCC_Total"] = df_ccc_mn_disp["CCC_Total"].apply(lambda x: f"{int(x):,}")
    df_ccc_mn_disp["No Digital"] = df_ccc_mn_disp["No Digital"].apply(lambda x: f"{int(x):,}")
    df_ccc_mn_disp["Híbridos"] = df_ccc_mn_disp["Híbridos"].apply(lambda x: f"{int(x):,}")
    df_ccc_mn_disp["Fully Digital"] = df_ccc_mn_disp["Fully Digital"].apply(lambda x: f"{int(x):,}")
    df_ccc_mn_disp = df_ccc_mn_disp.rename(columns={"Taxonomia": "Taxonomía", "Cartera_Total": "Cartera / Clientes", "CCC_Total": "Clientes con Compra (CCC)", "No Digital": "No Digital (CCC)", "Híbridos": "Híbridos (CCC)", "Fully Digital": "Fully Digital (CCC)"})

    registros_marca = []
    total_cartera_global = len(cartera_base) if not cartera_base.empty else 0
    if not cartera_base.empty and marcas_lst:
        clientes_unicos_cartera = set(cartera_base["Cliente_Cod"].unique())
        for m in marcas_lst:
            obj_m = mapa_obj.get(m, 80.0)
            if not vtas_agrup_global.empty:
                if sup_seleccionado != "TODOS" and "CodVendedor" in vtas_agrup_global.columns and "CodVendedor" in cartera_base.columns:
                    vta_m_filt = vtas_agrup_global[vtas_agrup_global["CodVendedor"].isin(cartera_base["CodVendedor"])]
                else:
                    vta_m_filt = vtas_agrup_global
                
                cubiertos_m = vta_m_filt[
                    vta_m_filt["Cliente"].isin(clientes_unicos_cartera) &
                    (vta_m_filt["Marca"] == m) &
                    (vta_m_filt["Total_Cant"] >= 3)
                ]["Cliente"].nunique()
            else:
                cubiertos_m = 0
            
            cob_real_pct = (cubiertos_m / total_cartera_global * 100.0) if total_cartera_global > 0 else 0.0
            cumpl_marca_pct = (cob_real_pct / obj_m * 100.0) if obj_m > 0 else 0.0
            
            registros_marca.append({
                "Marca": m,
                "Objetivo_Cobertura_Marca_Pct": round(obj_m, 2),
                "Clientes_Cubiertos": cubiertos_m,
                "Cartera_Total": total_cartera_global,
                "Cobertura_Real_Operativa_Pct": round(cob_real_pct, 2),
                "Cumplimiento_Cobertura_Marca_Pct": round(cumpl_marca_pct, 2)
            })
    df_marcas_res = pd.DataFrame(registros_marca)

    with st.expander("🔍 Auditoría de Conciliación: Preventistas vs. Consolidado Gerencial", expanded=False):
        st.markdown("This panel breaks down the exact origin of the numerical gap between preventer trends and the consolidated managerial dashboard.")
        aud_col1, aud_col2, aud_col3, aud_col4 = st.columns(4)
        with aud_col1:
            st.metric("1. Preventistas Puros", f"{total_proyectado_preventistas_puro:,.2f} kg")
        with aud_col2:
            st.metric("2. Vendedor 20 (Depósito)", f"{total_v20_kilos:,.2f} kg")
        with aud_col3:
            st.metric("3. Total Consolidado Gerencial", f"{tot_proy_k:,.2f} kg")
        with aud_col4:
            diferencia_neta = tot_proy_k - total_proyectado_preventistas_puro
            st.metric("Brecha Neta (V20 + Reemplazos)", f"{diferencia_neta:,.2f} kg", delta=f"{diferencia_neta:,.2f} kg")

    st.divider()

    tab_k, tab_c, tab_mn, tab_m = st.tabs(["📦 Kilos e Importes por Segmento", "📈 CCC por Taxonomía", "📱 MiNegocio por Taxonomía", "🎯 Cobertura por Marca"])

    with tab_k:
        st.markdown("### 💰 1. Desglose Financiero (Gross / Importes)")
        col_proy_g1, col_proy_g2, col_proy_g3 = st.columns([1, 2, 1])
        with col_proy_g2:
            st.markdown(tarjeta_metrica_html("📊 PROYECTADO GROSS", f"${tot_proy_g:,.0f}", "#ef4444", "2.2rem", "1.1rem"), unsafe_allow_html=True)

        mi1, mi2, mi3, mi4, mi5 = st.columns(5)
        with mi1:
            st.markdown(tarjeta_metrica_html("💰 OBJ. GROSS", f"${tot_obj_gross:,.0f}", "#3b82f6", "1.0rem", "0.45rem"), unsafe_allow_html=True)
        with mi2:
            st.markdown(tarjeta_metrica_html("💵 OPERATIVO GROSS", f"${tot_operativo_g:,.0f}", "#10b981", "1.0rem", "0.45rem"), unsafe_allow_html=True)
        with mi3:
            st.markdown(tarjeta_metrica_html("🎯 CUMP. ACTUAL", f"{cump_actual_g_val:,.2f}%", "#8b5cf6", "1.0rem", "0.45rem"), unsafe_allow_html=True)
        with mi4:
            st.markdown(tarjeta_metrica_html("📊 CUMP. PROY.", f"{cump_proy_g_val:,.2f}%", "#06b6d4", "1.0rem", "0.45rem"), unsafe_allow_html=True)
        with mi5:
            st.markdown(tarjeta_metrica_html("🎯 A INCORPORAR", f"${tot_incorporar_g:,.0f}", "#f59e0b", "1.0rem", "0.45rem"), unsafe_allow_html=True)

        st.dataframe(df_gross_display, width="stretch", hide_index=True)
        
        buf_g = io.BytesIO()
        with pd.ExcelWriter(buf_g, engine="openpyxl") as w:
            df_gross_seg.to_excel(w, index=False, sheet_name="Gross_Segmento")
        st.download_button("📥 Descargar Gross / Importes a Excel", data=buf_g.getvalue(), file_name="gross_importes_por_segmento.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_gross_seg")

        st.divider()
        st.markdown("### 📦 2. Desglose Operativo (Kilos / Volumen)")
        col_proy_k1, col_proy_k2, col_proy_k3 = st.columns([1, 2, 1])
        with col_proy_k2:
            st.markdown(tarjeta_metrica_html("🔮 PROYECTADO KILOS", f"{tot_proy_k:,.0f} kg", "#ef4444", "2.2rem", "1.1rem"), unsafe_allow_html=True)

        mk1, mk2, mk3, mk4, mk5 = st.columns(5)
        with mk1:
            st.markdown(tarjeta_metrica_html("🎯 OBJETIVO KILOS", f"{tot_obj_kilos:,.0f} kg", "#3b82f6", "1.0rem", "0.45rem"), unsafe_allow_html=True)
        with mk2:
            st.markdown(tarjeta_metrica_html("📊 OPERATIVO KILOS", f"{tot_operativo_k:,.0f} kg", "#10b981", "1.0rem", "0.45rem"), unsafe_allow_html=True)
        with mk3:
            st.markdown(tarjeta_metrica_html("🎯 CUMP. ACTUAL", f"{cump_actual_k_val:,.2f}%", "#8b5cf6", "1.0rem", "0.45rem"), unsafe_allow_html=True)
        with mk4:
            st.markdown(tarjeta_metrica_html("📈 CUMP. PROY.", f"{cump_proy_k_val:,.2f}%", "#06b6d4", "1.0rem", "0.45rem"), unsafe_allow_html=True)
        with mk5:
            st.markdown(tarjeta_metrica_html("🎯 A INCORPORAR", f"${tot_incorporar_k:,.0f} kg", "#f59e0b", "1.0rem", "0.45rem"), unsafe_allow_html=True)

        st.dataframe(df_kilos_display, width="stretch", hide_index=True)
        
        buf_k = io.BytesIO()
        with pd.ExcelWriter(buf_k, engine="openpyxl") as w:
            df_kilos_seg.to_excel(w, index=False, sheet_name="Kilos_Segmento")
        st.download_button("📥 Descargar Kilos / Volumen a Excel", data=buf_k.getvalue(), file_name="kilos_volumen_por_segmento.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_kilos_seg")

    with tab_c:
        st.markdown("### 📈 CCC por Taxonomía (Obj Pepsico, % Cump, Obj Fuerza de Ventas, % Cump y Avance CCC)")

        cc1, cc2, cc3, cc4, cc5, cc6 = st.columns(6)
        with cc1:
            st.markdown(tarjeta_metrica_html("📋 CARTERA NETA", f"{tot_cartera_ger:,.0f}", "#ffffff", "1.1rem", "0.6rem"), unsafe_allow_html=True)
        with cc2:
            st.markdown(tarjeta_metrica_html("📦 CANTIDAD CCC", f"{tot_avance_ccc_ger:,.0f}", "#22c55e", "1.1rem", "0.6rem"), unsafe_allow_html=True)
        with cc3:
            st.markdown(tarjeta_metrica_html("🏢 OBJ. PEPSICO", f"{tot_obj_pep_ger:,.0f}", "#3b82f6", "1.1rem", "0.6rem"), unsafe_allow_html=True)
        with cc4:
            st.markdown(tarjeta_metrica_html("🎯 CUMP. PEPSICO", f"{cump_pep_ger_pct:,.2f}%", "#10b981", "1.1rem", "0.6rem"), unsafe_allow_html=True)
        with cc5:
            st.markdown(tarjeta_metrica_html("🎯 OBJ. F. VENTAS", f"{tot_obj_fv_ger:,.0f}", "#f59e0b", "1.1rem", "0.6rem"), unsafe_allow_html=True)
        with cc6:
            st.markdown(tarjeta_metrica_html("📈 CUMP. F. VENTAS", f"{cump_fv_ger_pct:,.2f}%", "#8b5cf6", "1.1rem", "0.6rem"), unsafe_allow_html=True)

        st.divider()
        st.dataframe(df_ccc_display, width="stretch", hide_index=True)

        buf2 = io.BytesIO()
        with pd.ExcelWriter(buf2, engine="openpyxl") as w:
            df_ccc_tax_raw.to_excel(w, index=False, sheet_name="CCC_Taxonomia")
        st.download_button("📥 Descargar CCC por Taxonomía a Excel", data=buf2.getvalue(), file_name="ccc_por_taxonomia.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_ccc_tax")

    with tab_mn:
        st.markdown("### 📱 MiNegocio por Taxonomía (Desglose Híbrido: Gross, Kilos y CCC por App)")

        mn1, mn2, mn3, mn4, mn5, mn6 = st.columns(6)
        with mn1:
            st.markdown(tarjeta_metrica_html("💰 VENTAS TOTALES", f"${tot_ventas_mn_ger:,.2f}", "#38bdf8", "1.1rem", "0.6rem"), unsafe_allow_html=True)
        with mn2:
            st.markdown(tarjeta_metrica_html("📱 VENTA APP (MN+)", f"${tot_app_mn_ger:,.2f}", "#38bdf8", "1.1rem", "0.6rem"), unsafe_allow_html=True)
        with mn3:
            st.markdown(tarjeta_metrica_html("📈 % VENTA APP", f"{pct_venta_mn_ger:,.2f}%", "#38bdf8", "1.1rem", "0.6rem"), unsafe_allow_html=True)
        with mn4:
            st.markdown(tarjeta_metrica_html("🔴 NO DIGITAL", f"{tot_nodig_mn_ger:,.0f}", "#ef4444", "1.1rem", "0.6rem"), unsafe_allow_html=True)
        with mn5:
            st.markdown(tarjeta_metrica_html("🟠 HÍBRIDOS", f"{tot_hibr_mn_ger:,.0f}", "#f97316", "1.1rem", "0.6rem"), unsafe_allow_html=True)
        with mn6:
            st.markdown(tarjeta_metrica_html("🟢 FULLY DIGITAL", f"{tot_fully_mn_ger:,.0f}", "#22c55e", "1.1rem", "0.6rem"), unsafe_allow_html=True)

        st.divider()
        st.markdown("#### 💰 1. Desglose Financiero Gross por Taxonomía")
        st.dataframe(df_gross_mn_disp, width="stretch", hide_index=True)
        buf_mn_g = io.BytesIO()
        with pd.ExcelWriter(buf_mn_g, engine="openpyxl") as w:
            res_gross_mn.to_excel(w, index=False, sheet_name="MiNegocio_Gross")
        st.download_button("📥 Descargar Gross MiNegocio a Excel", data=buf_mn_g.getvalue(), file_name="minegocio_gross_por_taxonomia.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_mn_gross")

        st.divider()
        st.markdown("#### 📦 2. Desglose Operativo Kilos por Taxonomía")
        st.dataframe(df_kilos_mn_disp, width="stretch", hide_index=True)
        buf_mn_k = io.BytesIO()
        with pd.ExcelWriter(buf_mn_k, engine="openpyxl") as w:
            res_kilos_mn.to_excel(w, index=False, sheet_name="MiNegocio_Kilos")
        st.download_button("📥 Descargar Kilos MiNegocio a Excel", data=buf_mn_k.getvalue(), file_name="minegocio_kilos_por_taxonomia.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_mn_kilos")

        st.divider()
        st.markdown("#### 📋 3. Desglose CCC y Compradores por App (No Digital, Híbridos, Fully Digital)")
        st.dataframe(df_ccc_mn_disp, width="stretch", hide_index=True)
        buf_mn_c = io.BytesIO()
        with pd.ExcelWriter(buf_mn_c, engine="openpyxl") as w:
            res_ccc_mn.to_excel(w, index=False, sheet_name="MiNegocio_CCC")
        st.download_button("📥 Descargar CCC MiNegocio a Excel", data=buf_mn_c.getvalue(), file_name="minegocio_ccc_por_taxonomia.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_mn_ccc")

    with tab_m:
        st.markdown("### 🎯 Cobertura por Marca")
        st.dataframe(df_marcas_res, width="stretch", hide_index=True)

        buf4 = io.BytesIO()
        with pd.ExcelWriter(buf4, engine="openpyxl") as w:
            df_marcas_res.to_excel(w, index=False, sheet_name="Cobertura_Marca")
        st.download_button("📥 Descargar Cobertura por Marca a Excel", data=buf4.getvalue(), file_name="cobertura_por_marca_resumen.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_marca_res")