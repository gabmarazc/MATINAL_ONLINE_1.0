# modules/rep_gerencial.py
import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import tarjeta_metrica_html, parsear_fecha_robusta
from modules.rep_kilos import preparar_datos_ventas_segmento
from modules.rep_ccc import generar_reporte_ccc_taxonomia
from modules.rep_MN import generar_reporte_mn_taxonomia
from modules.rep_cob_marca import generar_reporte_cobertura_marca

@st.cache_data(show_spinner=False)
def _calcular_motor_gerencial_global(df_vta, df_universo, df_rutas, df_ausencias, anio_op, mes_op, dia_matinal, dia_venta, huella_global):
    """
    Motor analítico gerencial optimizado con prorrateo estricto por marca/canal, ritmo de rutas y control de período futuro.
    """
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

    try:
        maestro_ccc_param = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
    except Exception:
        maestro_ccc_param = pd.DataFrame(columns=["Taxonomia", "Porcentaje_Cartera"])

    df_marcas_maestro = db.cargar_tabla_sql("SELECT * FROM parametros_marcas")

    if maestro_v.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), [], {}, {}

    col_sup_v = next((c for c in maestro_v.columns if "sup" in str(c).strip().lower()), maestro_v.columns[2] if len(maestro_v.columns) > 2 else maestro_v.columns[0])
    col_cod_v = next((c for c in maestro_v.columns if "cod" in str(c).strip().lower()), maestro_v.columns[0])
    
    maestro_v["Cod_Clean"] = pd.to_numeric(maestro_v[col_cod_v], errors="coerce").astype("Int64").astype(str).str.strip()
    maestro_v["Sup_Clean"] = maestro_v[col_sup_v].fillna("").astype(str).str.strip()
    sup_map = maestro_v.set_index("Cod_Clean")["Sup_Clean"].to_dict()

    # 1. Preparación de ventas base con segmentación
    df_vta_prep_k = preparar_datos_ventas_segmento(df_vta, df_ausencias, anio_op, mes_op, dia_matinal)
    
    kilos_operativos_g = pd.DataFrame(columns=["Supervisor", "SEGMENTO", "Arrastre", "Actual", "Kilos_Operativos_Kg", "Importe_Operativo_Arg", "Kilos_Proyectados_Kg", "Gross_Proyectado_Arg", "Kilos_Futuro_Kg", "Gross_Futuro_Arg"])
    
    if not df_vta_prep_k.empty and "SEGMENTO" in df_vta_prep_k.columns:
        df_vta_seg_bruto = df_vta_prep_k[
            df_vta_prep_k["Periodo"].isin(["Arrastre", "Actual", "Futuro"]) & 
            df_vta_prep_k["SEGMENTO"].notna()
        ].copy()

        df_vta_seg_bruto["CodVen_Clean"] = pd.to_numeric(df_vta_seg_bruto["CodVendedor"], errors="coerce").astype("Int64").astype(str).str.strip()
        df_vta_seg_bruto["Supervisor"] = df_vta_seg_bruto["CodVen_Clean"].map(sup_map).fillna("GENERAL")

        col_imp_neto = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df_vta_seg_bruto.columns), None)
        df_vta_seg_bruto["ImporteNetoItem"] = pd.to_numeric(df_vta_seg_bruto[col_imp_neto], errors="coerce").fillna(0.0) if col_imp_neto else 0.0

        df_arr = df_vta_seg_bruto[df_vta_seg_bruto["Periodo"] == "Arrastre"]
        df_act = df_vta_seg_bruto[df_vta_seg_bruto["Periodo"] == "Actual"]
        df_fut = df_vta_seg_bruto[df_vta_seg_bruto["Periodo"] == "Futuro"]

        arr_agg = df_arr.groupby(["Supervisor", "SEGMENTO"], as_index=False).agg(Arrastre=("PesoKg", "sum"), Arrastre_Imp=("ImporteNetoItem", "sum"))
        act_agg = df_act.groupby(["Supervisor", "SEGMENTO"], as_index=False).agg(Actual=("PesoKg", "sum"), Actual_Imp=("ImporteNetoItem", "sum"))
        fut_agg = df_fut.groupby(["Supervisor", "SEGMENTO"], as_index=False).agg(Kilos_Futuro_Kg=("PesoKg", "sum"), Gross_Futuro_Arg=("ImporteNetoItem", "sum"))

        kilos_operativos_g = arr_agg.merge(act_agg, on=["Supervisor", "SEGMENTO"], how="outer").merge(fut_agg, on=["Supervisor", "SEGMENTO"], how="outer").fillna(0.0)
        
        kilos_operativos_g["Kilos_Operativos_Kg"] = kilos_operativos_g["Arrastre"] + kilos_operativos_g["Actual"]
        kilos_operativos_g["Importe_Operativo_Arg"] = kilos_operativos_g["Arrastre_Imp"] + kilos_operativos_g["Actual_Imp"]

        # Cálculo de días de ruta para proyección por ritmo diario
        rutas = df_rutas.copy() if df_rutas is not None and not df_rutas.empty else pd.DataFrame()
        dias_pasados_tot, dias_totales_mes = 1, 1
        if not rutas.empty:
            col_fecha_r = next((c for c in ["Fecha", "fecha", "Dia", "Date", "FECHA"] if c in rutas.columns), rutas.columns[0])
            rutas["Fecha_dt"] = pd.to_datetime(rutas[col_fecha_r], errors="coerce")
            rutas_mes = rutas[(rutas["Fecha_dt"].dt.year == int(anio_op)) & (rutas["Fecha_dt"].dt.month == int(mes_op))]
            
            dia_v_dt = parsear_fecha_robusta(pd.Series([dia_venta])).iloc[0]
            corte_date = dia_v_dt.date() if pd.notna(dia_v_dt) else None
            
            if corte_date is not None and not rutas_mes.empty:
                pasadas = rutas_mes[rutas_mes["Fecha_dt"].dt.date <= corte_date]
                dias_pasados_tot = max(1, pasadas["Fecha_dt"].nunique())
                dias_totales_mes = max(1, rutas_mes["Fecha_dt"].nunique())

        factor_proyeccion = dias_totales_mes / max(1, dias_pasados_tot)
        
        kilos_operativos_g["Kilos_Proyectados_Kg"] = kilos_operativos_g["Arrastre"] + (kilos_operativos_g["Actual"] * factor_proyeccion)
        
        precio_prom_segmento = (kilos_operativos_g["Importe_Operativo_Arg"] / kilos_operativos_g["Kilos_Operativos_Kg"].replace(0, 1.0))
        kilos_operativos_g["Gross_Proyectado_Arg"] = kilos_operativos_g["Kilos_Proyectados_Kg"] * precio_prom_segmento

    # 2. Prorrateo pormenorizado y cruzado de Objetivos (Kilos y Gross por Marca y Segmento)
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
            
            df_vta_sin_20 = df_vta_prep_k[df_vta_prep_k["CodVendedor"] != 20].copy()
            df_vta_sin_20["CodVen_Clean"] = pd.to_numeric(df_vta_sin_20["CodVendedor"], errors="coerce").astype("Int64").astype(str).str.strip()
            df_vta_sin_20["Supervisor"] = df_vta_sin_20["CodVen_Clean"].map(sup_map).fillna("GENERAL")
            df_vta_sin_20["Marca_Key"] = df_vta_sin_20["Marca"].astype(str).str.strip().str.upper()
            
            tot_marca_vta = df_vta_sin_20.groupby(["Marca_Key", "SEGMENTO"])["PesoKg"].sum().reset_index()
            tot_marca_vta["Total_Marca"] = tot_marca_vta.groupby("Marca_Key")["PesoKg"].transform("sum").replace(0, 1.0)
            tot_marca_vta["Part_Marca_Seg"] = tot_marca_vta["PesoKg"] / tot_marca_vta["Total_Marca"]
            
            tot_marca_vta["Obj_Kilos_Marca"] = tot_marca_vta["Marca_Key"].map(mapa_obj_kg).fillna(0.0)
            tot_marca_vta["Obj_Gross_Marca"] = tot_marca_vta["Marca_Key"].map(mapa_obj_imp).fillna(0.0)
            
            tot_marca_vta["Obj_Seg_Kg"] = tot_marca_vta["Obj_Kilos_Marca"] * tot_marca_vta["Part_Marca_Seg"]
            tot_marca_vta["Obj_Seg_Imp"] = tot_marca_vta["Obj_Gross_Marca"] * tot_marca_vta["Part_Marca_Seg"]

            sup_seg_map = df_vta_sin_20.groupby(["SEGMENTO", "Supervisor"])["PesoKg"].sum().reset_index()
            sup_seg_map = sup_seg_map.sort_values(by="PesoKg", ascending=False).drop_duplicates("SEGMENTO").set_index("SEGMENTO")["Supervisor"].to_dict()
            
            tot_marca_vta["Supervisor"] = tot_marca_vta["SEGMENTO"].map(sup_seg_map).fillna("GENERAL")

            kilos_obj_g = tot_marca_vta.groupby(["Supervisor", "SEGMENTO"], as_index=False).agg(
                Objetivo_Kilos_Kg=("Obj_Seg_Kg", "sum"),
                Objetivo_Importe_Arg=("Obj_Seg_Imp", "sum")
            )

    # 3. Ventas del Vendedor 20 (sin prorrateo)
    df_v20 = df_vta_prep_k[(df_vta_prep_k["CodVendedor"] == 20) & df_vta_prep_k["Periodo"].isin(["Arrastre", "Actual"])].copy()
    if not df_v20.empty and "SEGMENTO" in df_v20.columns:
        col_imp_neto = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df_v20.columns), None)
        df_v20["ImporteNetoItem"] = pd.to_numeric(df_v20[col_imp_neto], errors="coerce").fillna(0.0) if col_imp_neto else 0.0
        
        df_v20_arr = df_v20[df_v20["Periodo"] == "Arrastre"].groupby("SEGMENTO", as_index=False)["PesoKg"].sum().rename(columns={"PesoKg": "Arrastre_V20"})
        df_v20_act = df_v20[df_v20["Periodo"] == "Actual"].groupby("SEGMENTO", as_index=False)["PesoKg"].sum().rename(columns={"PesoKg": "Actual_V20"})
        df_v20_imp = df_v20.groupby("SEGMENTO", as_index=False)["ImporteNetoItem"].sum().rename(columns={"ImporteNetoItem": "Gross_V20"})
        
        v20_agg = df_v20_arr.merge(df_v20_act, on="SEGMENTO", how="outer").merge(df_v20_imp, on="SEGMENTO", how="outer").fillna(0.0)
    else:
        v20_agg = pd.DataFrame(columns=["SEGMENTO", "Arrastre_V20", "Actual_V20", "Gross_V20"])

    filtros_globales_base = {"anio": anio_op, "mes": mes_op, "dia_matinal": dia_matinal, "dia_venta": dia_venta, "supervisor": "TODOS"}
    
    rep_ccc_global = generar_reporte_ccc_taxonomia(df_vta, df_universo, maestro_v, maestro_ccc_param, filtros_globales_base)
    rep_mn_global = generar_reporte_mn_taxonomia(df_vta, df_universo, maestro_v, filtros_globales_base)
    
    generar_reporte_cobertura_marca(df_vta, df_universo, maestro_v, df_marcas_maestro, filtros_globales_base)
    cartera_base_global = st.session_state.get("_cob_cartera_base", pd.DataFrame())
    vtas_agrup_global = st.session_state.get("_cob_vtas_agrupadas", pd.DataFrame())
    marcas_lst = st.session_state.get("_cob_marcas", [])
    mapa_obj = st.session_state.get("_cob_mapa_objetivos", {})

    return kilos_obj_g, kilos_operativos_g, v20_agg, rep_ccc_global, rep_mn_global, cartera_base_global, vtas_agrup_global, marcas_lst, mapa_obj

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

    col_sup_sel, _ = st.columns([2, 3])
    with col_sup_sel:
        sup_seleccionado = st.selectbox("Filtrar Tablero por Supervisor", options=supervisores_disp, index=0, key="gerencial_filtro_sup")

    huella_global = f"{len(df_vta)}_{len(df_universo)}_{anio_op}_{mes_op}_{dia_matinal}"

    kilos_obj_det_global, kilos_oper_detalle_global, v20_agg_global, rep_ccc_global, rep_mn_global, cartera_base_global, vtas_agrup_global, marcas_lst, mapa_obj = _calcular_motor_gerencial_global(
        df_vta, df_universo, df_rutas, df_ausencias, anio_op, mes_op, dia_matinal, dia_venta, huella_global
    )

    if sup_seleccionado != "TODOS":
        if not kilos_oper_detalle_global.empty and "Supervisor" in kilos_oper_detalle_global.columns:
            kilos_operativos_g = kilos_oper_detalle_global[kilos_oper_detalle_global["Supervisor"].astype(str).str.strip() == sup_seleccionado].groupby("SEGMENTO", as_index=False).agg({
                "Arrastre": "sum", "Actual": "sum", "Kilos_Operativos_Kg": "sum", "Importe_Operativo_Arg": "sum", 
                "Kilos_Proyectados_Kg": "sum", "Gross_Proyectado_Arg": "sum", 
                "Kilos_Futuro_Kg": "sum", "Gross_Futuro_Arg": "sum"
            })
        else:
            kilos_operativos_g = pd.DataFrame(columns=["SEGMENTO", "Arrastre", "Actual", "Kilos_Operativos_Kg", "Importe_Operativo_Arg", "Kilos_Proyectados_Kg", "Gross_Proyectado_Arg", "Kilos_Futuro_Kg", "Gross_Futuro_Arg"])
        
        if not kilos_obj_det_global.empty and "Supervisor" in kilos_obj_det_global.columns:
            kilos_obj_g = kilos_obj_det_global[kilos_obj_det_global["Supervisor"].astype(str).str.strip() == sup_seleccionado].groupby("SEGMENTO", as_index=False).agg({"Objetivo_Kilos_Kg": "sum", "Objetivo_Importe_Arg": "sum"})
        else:
            kilos_obj_g = pd.DataFrame(columns=["SEGMENTO", "Objetivo_Kilos_Kg", "Objetivo_Importe_Arg"])

        v20_segmento = pd.DataFrame(columns=["SEGMENTO", "Arrastre_V20", "Actual_V20", "Gross_V20"])

        rep_ccc = rep_ccc_global[rep_ccc_global["SUP"].astype(str).str.strip() == sup_seleccionado].copy() if not rep_ccc_global.empty and "SUP" in rep_ccc_global.columns else pd.DataFrame()
        rep_mn = rep_mn_global[rep_mn_global["SUP"].astype(str).str.strip() == sup_seleccionado].copy() if not rep_mn_global.empty and "SUP" in rep_mn_global.columns else pd.DataFrame()
        cartera_base = cartera_base_global[cartera_base_global["SUP"].astype(str).str.strip() == sup_seleccionado].copy() if not cartera_base_global.empty and "SUP" in cartera_base_global.columns else pd.DataFrame()
    else:
        if not kilos_oper_detalle_global.empty:
            kilos_operativos_g = kilos_oper_detalle_global.groupby("SEGMENTO", as_index=False).agg({
                "Arrastre": "sum", "Actual": "sum", "Kilos_Operativos_Kg": "sum", "Importe_Operativo_Arg": "sum", 
                "Kilos_Proyectados_Kg": "sum", "Gross_Proyectado_Arg": "sum", 
                "Kilos_Futuro_Kg": "sum", "Gross_Futuro_Arg": "sum"
            })
        else:
            kilos_operativos_g = pd.DataFrame(columns=["SEGMENTO", "Arrastre", "Actual", "Kilos_Operativos_Kg", "Importe_Operativo_Arg", "Kilos_Proyectados_Kg", "Gross_Proyectado_Arg", "Kilos_Futuro_Kg", "Gross_Futuro_Arg"])
        
        if not kilos_obj_det_global.empty:
            kilos_obj_g = kilos_obj_det_global.groupby("SEGMENTO", as_index=False).agg({"Objetivo_Kilos_Kg": "sum", "Objetivo_Importe_Arg": "sum"})
        else:
            kilos_obj_g = pd.DataFrame(columns=["SEGMENTO", "Objetivo_Kilos_Kg", "Objetivo_Importe_Arg"])

        v20_segmento = v20_agg_global

        rep_ccc = rep_ccc_global.copy()
        rep_mn = rep_mn_global.copy()
        cartera_base = cartera_base_global.copy()

    # Consolidación final por Segmento incluyendo Vendedor 20
    df_kilos_seg = kilos_obj_g.merge(kilos_operativos_g, on="SEGMENTO", how="outer").fillna(0.0)
    if not v20_segmento.empty:
        df_kilos_seg = df_kilos_seg.merge(v20_segmento, on="SEGMENTO", how="left").fillna(0.0)
        df_kilos_seg["Arrastre"] += df_kilos_seg["Arrastre_V20"]
        df_kilos_seg["Actual"] += df_kilos_seg["Actual_V20"]
        df_kilos_seg["Kilos_Operativos_Kg"] += (df_kilos_seg["Arrastre_V20"] + df_kilos_seg["Actual_V20"])
        df_kilos_seg["Importe_Operativo_Arg"] += df_kilos_seg["Gross_V20"]
        df_kilos_seg["Kilos_Proyectados_Kg"] += (df_kilos_seg["Arrastre_V20"] + df_kilos_seg["Actual_V20"])
        df_kilos_seg["Gross_Proyectado_Arg"] += df_kilos_seg["Gross_V20"]

    # Redondeos y cálculos de porcentajes
    df_kilos_seg["Objetivo_Kilos_Kg"] = df_kilos_seg["Objetivo_Kilos_Kg"].round(2)
    df_kilos_seg["Objetivo_Importe_Arg"] = df_kilos_seg["Objetivo_Importe_Arg"].round(2)
    df_kilos_seg["Arrastre"] = df_kilos_seg["Arrastre"].round(2)
    df_kilos_seg["Actual"] = df_kilos_seg["Actual"].round(2)
    df_kilos_seg["Kilos_Operativos_Kg"] = df_kilos_seg["Kilos_Operativos_Kg"].round(2)
    df_kilos_seg["Importe_Operativo_Arg"] = df_kilos_seg["Importe_Operativo_Arg"].round(2)
    df_kilos_seg["Kilos_Proyectados_Kg"] = df_kilos_seg["Kilos_Proyectados_Kg"].round(2)
    df_kilos_seg["Gross_Proyectado_Arg"] = df_kilos_seg["Gross_Proyectado_Arg"].round(2)
    df_kilos_seg["Kilos_Futuro_Kg"] = df_kilos_seg["Kilos_Futuro_Kg"].round(2)
    df_kilos_seg["Gross_Futuro_Arg"] = df_kilos_seg["Gross_Futuro_Arg"].round(2)
    
    df_kilos_seg["Cumplimiento_Actual_Pct"] = (df_kilos_seg["Kilos_Operativos_Kg"] / df_kilos_seg["Objetivo_Kilos_Kg"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    df_kilos_seg["Cumplimiento_Proyectado_Pct"] = (df_kilos_seg["Kilos_Proyectados_Kg"] / df_kilos_seg["Objetivo_Kilos_Kg"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    df_kilos_seg["Cumplimiento_Gross_Proy_Pct"] = (df_kilos_seg["Gross_Proyectado_Arg"] / df_kilos_seg["Objetivo_Importe_Arg"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)

    # Cálculo de brecha / futuro a incorporar valorizado coherentemente al precio unitario objetivo del segmento
    precio_unit_segmento_obj = (df_kilos_seg["Objetivo_Importe_Arg"] / df_kilos_seg["Objetivo_Kilos_Kg"].replace(0, 1.0))
    
    df_kilos_seg["Futuro_A_Incorporar_Kgs"] = (df_kilos_seg["Objetivo_Kilos_Kg"] - df_kilos_seg["Kilos_Proyectados_Kg"]).clip(lower=0).round(2)
    df_kilos_seg["Futuro_A_Incorporar_Gross"] = (df_kilos_seg["Futuro_A_Incorporar_Kgs"] * precio_unit_segmento_obj).round(2)

    # ORDENAMIENTO OFICIAL DE SEGMENTOS IDÉNTICO A REP_KILOS
    orden_segmentos_maestro = [
        "GOLD Salty",
        "GOLD Crakers",
        "SILVER Salty",
        "SILVER Crakers",
        "SILVER Cereals"
    ]
    mapping_orden = {str(seg).strip(): i for i, seg in enumerate(orden_segmentos_maestro)}
    df_kilos_seg["_orden_idx"] = df_kilos_seg["SEGMENTO"].astype(str).str.strip().map(mapping_orden).fillna(999)
    df_kilos_seg = df_kilos_seg.sort_values(by="_orden_idx").drop(columns=["_orden_idx"]).reset_index(drop=True)

    # Renombrado oficial de columnas para la tabla gerencial
    df_kilos_seg = df_kilos_seg.rename(columns={
        "Objetivo_Kilos_Kg": "Objetivo Kilos Pepsico",
        "Objetivo_Importe_Arg": "Objetivo Gross Pepsico",
        "Arrastre": "Arrastre Kilos",
        "Actual": "Mes Actual Kilos",
        "Kilos_Operativos_Kg": "Operativo Kilos",
        "Importe_Operativo_Arg": "Operativo Gross",
        "Cumplimiento_Actual_Pct": "% Cumpl. Actual",
        "Kilos_Proyectados_Kg": "Proyectado Kilos",
        "Gross_Proyectado_Arg": "Proyectado Gross",
        "Cumplimiento_Proyectado_Pct": "% Cumpl. Proy. Kilos",
        "Cumplimiento_Gross_Proy_Pct": "% Cumpl. Proy. Gross",
        "Kilos_Futuro_Kg": "Futuro Kilos",
        "Gross_Futuro_Arg": "Gross Futuro",
        "Futuro_A_Incorporar_Kgs": "A Incorporar Kilos",
        "Futuro_A_Incorporar_Gross": "A Incorporar Gross"
    })

    cols_mantener = [
        "SEGMENTO", "Objetivo Kilos Pepsico", "Objetivo Gross Pepsico", 
        "Arrastre Kilos", "Mes Actual Kilos", "Operativo Kilos", "Operativo Gross", "% Cumpl. Actual", 
        "Proyectado Kilos", "Proyectado Gross", "% Cumpl. Proy. Kilos", "% Cumpl. Proy. Gross", 
        "Futuro Kilos", "Gross Futuro", "A Incorporar Kilos", "A Incorporar Gross"
    ]
    cols_existentes = [c for c in cols_mantener if c in df_kilos_seg.columns]
    df_kilos_seg = df_kilos_seg[cols_existentes]

    # DataFrame para descarga a Excel (Mantiene los valores numéricos puros)
    df_kilos_seg_excel = df_kilos_seg.copy()

    # DataFrame formateado exclusivamente para visualización en pantalla con $, kg y %
    df_kilos_seg_display = df_kilos_seg.copy()
    cols_pesos = ["Objetivo Gross Pepsico", "Operativo Gross", "Proyectado Gross", "Gross Futuro", "A Incorporar Gross"]
    cols_kilos = ["Objetivo Kilos Pepsico", "Arrastre Kilos", "Mes Actual Kilos", "Operativo Kilos", "Proyectado Kilos", "Futuro Kilos", "A Incorporar Kilos"]
    cols_porc = ["% Cumpl. Actual", "% Cumpl. Proy. Kilos", "% Cumpl. Proy. Gross"]

    for col in cols_pesos:
        if col in df_kilos_seg_display.columns:
            df_kilos_seg_display[col] = df_kilos_seg_display[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
    for col in cols_kilos:
        if col in df_kilos_seg_display.columns:
            df_kilos_seg_display[col] = df_kilos_seg_display[col].apply(lambda x: f"{x:,.2f} kg" if pd.notna(x) else "0.00 kg")
    for col in cols_porc:
        if col in df_kilos_seg_display.columns:
            df_kilos_seg_display[col] = df_kilos_seg_display[col].apply(lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%")

    tot_obj_kilos = float(df_kilos_seg["Objetivo Kilos Pepsico"].sum())
    tot_obj_gross = float(df_kilos_seg["Objetivo Gross Pepsico"].sum())
    tot_arrastre = float(df_kilos_seg["Arrastre Kilos"].sum())
    tot_actual = float(df_kilos_seg["Mes Actual Kilos"].sum())
    tot_operativo_k = float(df_kilos_seg["Operativo Kilos"].sum())
    tot_operativo_g = float(df_kilos_seg["Operativo Gross"].sum())
    tot_proy_k = float(df_kilos_seg["Proyectado Kilos"].sum())
    tot_proy_g = float(df_kilos_seg["Proyectado Gross"].sum())
    tot_futuro_k = float(df_kilos_seg["Futuro Kilos"].sum())
    tot_futuro_g = float(df_kilos_seg["Gross Futuro"].sum())
    tot_incorporar_k = float(df_kilos_seg["A Incorporar Kilos"].sum())
    tot_incorporar_g = float(df_kilos_seg["A Incorporar Gross"].sum())

    cump_actual_val = round((tot_operativo_k / tot_obj_kilos * 100.0) if tot_obj_kilos > 0 else 0.0, 2)
    cump_proy_k_val = round((tot_proy_k / tot_obj_kilos * 100.0) if tot_obj_kilos > 0 else 0.0, 2)
    cump_proy_g_val = round((tot_proy_g / tot_obj_gross * 100.0) if tot_obj_gross > 0 else 0.0, 2)

    # CCC, MiNegocio y Cobertura
    if not rep_ccc.empty:
        df_ccc_tax = rep_ccc.groupby("Taxonomia", as_index=False).agg(
            Cartera_Neta=("Cartera_Neta", "sum"),
            Objetivo_CCC=("Objetivo_CCC", "sum"),
            Cantidad_CCC=("CCC", "sum")
        )
        df_ccc_tax["Cumplimiento_CCC_Pct"] = (df_ccc_tax["Cantidad_CCC"] / df_ccc_tax["Objetivo_CCC"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    else:
        df_ccc_tax = pd.DataFrame(columns=["Taxonomia", "Cartera_Neta", "Objetivo_CCC", "Cantidad_CCC", "Cumplimiento_CCC_Pct"])

    if not rep_mn.empty:
        df_mn_tax = rep_mn.groupby("Taxonomia", as_index=False).agg(
            Clientes_Universo=("Cliente", "count"),
            Clientes_No_Digital=("Es_NoDigital", lambda x: int(x.sum())),
            Clientes_Hibridos=("Es_Hibrido", lambda x: int(x.sum())),
            Clientes_FullyDigital=("Es_FullyDigital", lambda x: int(x.sum()))
        )
        df_mn_tax["Adopcion_App_Pct"] = ((df_mn_tax["Clientes_Hibridos"] + df_mn_tax["Clientes_FullyDigital"]) / df_mn_tax["Clientes_Universo"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    else:
        df_mn_tax = pd.DataFrame(columns=["Taxonomia", "Clientes_Universo", "Clientes_No_Digital", "Clientes_Hibridos", "Clientes_FullyDigital", "Adopcion_App_Pct"])

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

    st.divider()

    # RENDERIZADO EN PESTAÑAS LIMPIAS
    tab_k, tab_c, tab_mn, tab_m = st.tabs(["📦 Kilos e Importes por Segmento", "📈 CCC por Taxonomía", "📱 MiNegocio por Taxonomía", "🎯 Cobertura por Marca"])

    with tab_k:
        st.markdown("### 📦 1. Kilos e Importes: Resumen Ejecutivo y Toma de Decisiones Gerenciales")
        
        # 6 Columnas de Tarjetas de Métricas Directivas
        mk1, mk2, mk3, mk4, mk5, mk6 = st.columns(6)
        with mk1:
            st.markdown(tarjeta_metrica_html("🎯 OBJ. KILOS", f"{tot_obj_kilos:,.2f} kg", "#3b82f6", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mk2:
            st.markdown(tarjeta_metrica_html("📊 OPERATIVO", f"{tot_operativo_k:,.2f} kg", "#3b82f6", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mk3:
            st.markdown(tarjeta_metrica_html("🔮 PROYECTADO", f"{tot_proy_k:,.2f} kg", "#8b5cf6", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mk4:
            st.markdown(tarjeta_metrica_html("📈 CUMP. PROY.", f"{cump_proy_k_val:,.2f}%", "#22c55e" if cump_proy_k_val >= 100 else "#f97316", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mk5:
            st.markdown(tarjeta_metrica_html("🎯 A INCORPORAR", f"{tot_incorporar_k:,.2f} kg", "#ef4444", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mk6:
            st.markdown(tarjeta_metrica_html("⏩ KILOS FUTURO", f"{tot_futuro_k:,.2f} kg", "#f59e0b", "1.1rem", "0.5rem"), unsafe_allow_html=True)

        mi1, mi2, mi3, mi4, mi5, mi6 = st.columns(6)
        with mi1:
            st.markdown(tarjeta_metrica_html("💰 OBJ. GROSS", f"${tot_obj_gross:,.2f}", "#3b82f6", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mi2:
            st.markdown(tarjeta_metrica_html("💵 OPERATIVO GROSS", f"${tot_operativo_g:,.2f}", "#3b82f6", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mi3:
            st.markdown(tarjeta_metrica_html("📊 PROYECTADO GROSS", f"${tot_proy_g:,.2f}", "#8b5cf6", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mi4:
            st.markdown(tarjeta_metrica_html("📊 CUMP. PROY.", f"{cump_proy_g_val:,.2f}%", "#22c55e" if cump_proy_g_val >= 100 else "#f97316", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mi5:
            st.markdown(tarjeta_metrica_html("🎯 A INCORPORAR", f"${tot_incorporar_g:,.2f}", "#ef4444", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mi6:
            st.markdown(tarjeta_metrica_html("⏩ GROSS FUTURO", f"${tot_futuro_g:,.2f}", "#f59e0b", "1.1rem", "0.5rem"), unsafe_allow_html=True)

        st.divider()
        # Se renderiza la versión formateada con $, kg y % para máxima legibilidad visual
        st.dataframe(df_kilos_seg_display, width="stretch", hide_index=True)
        
        # El archivo de Excel se descarga con los valores numéricos puros para permitir operaciones al usuario
        buf1 = io.BytesIO()
        with pd.ExcelWriter(buf1, engine="openpyxl") as w:
            df_kilos_seg_excel.to_excel(w, index=False, sheet_name="Kilos_Importes_Segmento")
        st.download_button("📥 Descargar Kilos e Importes a Excel", data=buf1.getvalue(), file_name="kilos_e_importes_por_segmento.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_kilos_seg")

    with tab_c:
        st.markdown("### 📈 2. CCC: Objetivo, Cantidad de CCC y Cumplimiento por Taxonomía")
        st.dataframe(df_ccc_tax, width="stretch", hide_index=True)

        buf2 = io.BytesIO()
        with pd.ExcelWriter(buf2, engine="openpyxl") as w:
            df_ccc_tax.to_excel(w, index=False, sheet_name="CCC_Taxonomia")
        st.download_button("📥 Descargar CCC por Taxonomía a Excel", data=buf2.getvalue(), file_name="ccc_por_taxonomia.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_ccc_tax")

    with tab_mn:
        st.markdown("### 📱 3. MiNegocio: Clientes del Universo (FullyDigital, Híbridos, No Digital) por Taxonomía")
        st.dataframe(df_mn_tax, width="stretch", hide_index=True)

        buf3 = io.BytesIO()
        with pd.ExcelWriter(buf3, engine="openpyxl") as w:
            df_mn_tax.to_excel(w, index=False, sheet_name="MiNegocio_Taxonomia")
        st.download_button("📥 Descargar MiNegocio por Taxonomía a Excel", data=buf3.getvalue(), file_name="minegocio_por_taxonomia.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_mn_tax")

    with tab_m:
        st.markdown("### 🎯 4. Cobertura por Marca: Objetivo, Cobertura Real Operativa y Cumplimiento")
        st.dataframe(df_marcas_res, width="stretch", hide_index=True)

        buf4 = io.BytesIO()
        with pd.ExcelWriter(buf4, engine="openpyxl") as w:
            df_marcas_res.to_excel(w, index=False, sheet_name="Cobertura_Marca")
        st.download_button("📥 Descargar Cobertura por Marca a Excel", data=buf4.getvalue(), file_name="cobertura_por_marca_resumen.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_marca_res")