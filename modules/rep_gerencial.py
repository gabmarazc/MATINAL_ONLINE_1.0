# modules/rep_gerencial.py
import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import tarjeta_metrica_html, parsear_fecha_robusta
from modules.rep_kilos import preparar_datos_ventas_segmento, generar_reporte_avance_kilos_segmento
from modules.rep_ccc import generar_reporte_ccc_taxonomia
from modules.rep_MN import generar_reporte_mn_taxonomia
from modules.rep_cob_marca import generar_reporte_cobertura_marca

@st.cache_data(show_spinner=False)
def _calcular_motor_gerencial_global(df_vta, df_universo, df_rutas, df_ausencias, anio_op, mes_op, dia_matinal, dia_venta, sup_seleccionado, huella_global):
    """
    Motor analítico gerencial optimizado con caché por supervisor, prorrateo estricto por marca/canal,
    soporte dual para Ajuste de Entrega (TODO / AJUSTADO) y ritmo de rutas unificado con rep_kilos.
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
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), [], {}, {}

    col_sup_v = next((c for c in maestro_v.columns if "sup" in str(c).strip().lower()), maestro_v.columns[2] if len(maestro_v.columns) > 2 else maestro_v.columns[0])
    col_cod_v = next((c for c in maestro_v.columns if "cod" in str(c).strip().lower()), maestro_v.columns[0])
    
    maestro_v["Cod_Clean"] = pd.to_numeric(maestro_v[col_cod_v], errors="coerce").astype("Int64").astype(str).str.strip()
    maestro_v["Sup_Clean"] = maestro_v[col_sup_v].fillna("").astype(str).str.strip()
    sup_map = maestro_v.set_index("Cod_Clean")["Sup_Clean"].to_dict()

    # 1. Preparación de ventas base con segmentación
    df_vta_prep_k = preparar_datos_ventas_segmento(df_vta, df_ausencias, anio_op, mes_op, dia_matinal)
    
    # Generamos el reporte unificado de kilos a nivel vendedor para extraer las proyecciones exactas TODO y AJUSTADO
    reporte_kilos_base = generar_reporte_avance_kilos_segmento(df_vta_prep_k, df_rutas, maestro_v, maestro_s, maestro_cebe, dia_venta, anio_op, mes_op, "TODOS")

    kilos_operativos_g_todo = pd.DataFrame()
    kilos_operativos_g_ajustado = pd.DataFrame()

    if not reporte_kilos_base.empty:
        rep_k = reporte_kilos_base.copy()
        rep_k["CodVend_Clean"] = pd.to_numeric(rep_k["CodVendedor"], errors="coerce").astype("Int64").astype(str).str.strip()
        rep_k["Supervisor"] = rep_k["CodVend_Clean"].map(sup_map).fillna("GENERAL")

        col_imp_neto = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df_vta_prep_k.columns), None)
        
        # Procesamos escenario TODO
        dp_todo = rep_k["Días Pasados"].astype(float).replace(0, 1.0)
        dr_todo = rep_k["Días Restantes Todo"].astype(float)
        p_diario = (rep_k["Actual"] + rep_k.get("Ajuste_Reemp_Actual", 0.0)) / dp_todo
        
        rep_k["Operativo"] = rep_k["Arrastre"] + rep_k["Actual"] + rep_k.get("Ajuste_Por_Reemp", 0.0)
        rep_k["Proyectado_Todo"] = rep_k["Operativo"]
        mask_t = dr_todo > 0
        if mask_t.any():
            rep_k.loc[mask_t, "Proyectado_Todo"] = (p_diario[mask_t] * dr_todo[mask_t]) + rep_k.loc[mask_t, "Operativo"]

        # Procesamos escenario AJUSTADO
        dr_ajustado = rep_k["Días Restantes Ajustado"].astype(float)
        rep_k["Proyectado_Ajustado"] = rep_k["Operativo"]
        if mask_t.any():
            rep_k.loc[mask_t, "Proyectado_Ajustado"] = (p_diario[mask_t] * dr_ajustado[mask_t]) + rep_k.loc[mask_t, "Operativo"]

        # Estimación de importes (Gross) proporcionales al volumen operativo y proyectado
        if not df_vta_prep_k.empty:
            df_vta_precio = df_vta_prep_k[df_vta_prep_k["Periodo"].isin(["Arrastre", "Actual"]) & df_vta_prep_k["SEGMENTO"].notna()].copy()
            if col_imp_neto:
                df_vta_precio["Imp"] = pd.to_numeric(df_vta_precio[col_imp_neto], errors="coerce").fillna(0.0)
                precio_seg = df_vta_precio.groupby("SEGMENTO").apply(lambda x: x["Imp"].sum() / x["PesoKg"].sum() if x["PesoKg"].sum() > 0 else 0.0).to_dict()
            else:
                precio_seg = {}
        else:
            precio_seg = {}

        rep_k["Precio_Unit"] = rep_k["SEGMENTO"].map(precio_seg).fillna(0.0)
        rep_k["Gross_Operativo"] = rep_k["Operativo"] * rep_k["Precio_Unit"]
        rep_k["Gross_Proyectado_Todo"] = rep_k["Proyectado_Todo"] * rep_k["Precio_Unit"]
        rep_k["Gross_Proyectado_Ajustado"] = rep_k["Proyectado_Ajustado"] * rep_k["Precio_Unit"]

        # Agrupado TODO
        kilos_operativos_g_todo = rep_k.groupby(["Supervisor", "SEGMENTO"], as_index=False).agg({
            "Arrastre": "sum", "Actual": "sum", "Operativo": "sum", "Gross_Operativo": "sum",
            "Proyectado_Todo": "sum", "Gross_Proyectado_Todo": "sum"
        }).rename(columns={"Operativo": "Kilos_Operativos_Kg", "Gross_Operativo": "Importe_Operativo_Arg", "Proyectado_Todo": "Kilos_Proyectados_Kg", "Gross_Proyectado_Todo": "Gross_Proyectado_Arg"})

        # Agrupado AJUSTADO
        kilos_operativos_g_ajustado = rep_k.groupby(["Supervisor", "SEGMENTO"], as_index=False).agg({
            "Arrastre": "sum", "Actual": "sum", "Operativo": "sum", "Gross_Operativo": "sum",
            "Proyectado_Ajustado": "sum", "Gross_Proyectado_Ajustado": "sum"
        }).rename(columns={"Operativo": "Kilos_Operativos_Kg", "Gross_Operativo": "Importe_Operativo_Arg", "Proyectado_Ajustado": "Kilos_Proyectados_Kg", "Gross_Proyectado_Ajustado": "Gross_Proyectado_Arg"})

    # 2. Prorrateo pormenorizado y cruzado de Objetivos por Marca, Segmento y Supervisor
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

    # 3. Ventas del Vendedor 20 (sin prorrateo)
    df_v20 = df_vta_prep_k[(df_vta_prep_k["CodVendedor"] == 20) & df_vta_prep_k["Periodo"].isin(["Arrastre", "Actual"])].copy()
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
    
    rep_ccc_global = generar_reporte_ccc_taxonomia(df_vta, df_universo, maestro_v, maestro_ccc_param, filtros_globales_base)
    rep_mn_global = generar_reporte_mn_taxonomia(df_vta, df_universo, maestro_v, filtros_globales_base)
    
    generar_reporte_cobertura_marca(df_vta, df_universo, maestro_v, df_marcas_maestro, filtros_globales_base)
    cartera_base_global = st.session_state.get("_cob_cartera_base", pd.DataFrame())
    vtas_agrup_global = st.session_state.get("_cob_vtas_agrupadas", pd.DataFrame())
    marcas_lst = st.session_state.get("_cob_marcas", [])
    mapa_obj = st.session_state.get("_cob_mapa_objetivos", {})

    return kilos_obj_g, kilos_operativos_g_todo, kilos_operativos_g_ajustado, v20_agg, rep_ccc_global, rep_mn_global, cartera_base_global, vtas_agrup_global, marcas_lst, mapa_obj

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

    kilos_obj_det_global, kilos_oper_todo, kilos_oper_ajustado, v20_agg_global, rep_ccc_global, rep_mn_global, cartera_base_global, vtas_agrup_global, marcas_lst, mapa_obj = _calcular_motor_gerencial_global(
        df_vta, df_universo, df_rutas, df_ausencias, anio_op, mes_op, dia_matinal, dia_venta, sup_seleccionado, huella_global
    )

    # Seleccionamos dinámicamente el DataFrame operativo según el modo elegido (TODO / AJUSTADO)
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

        v20_segmento = pd.DataFrame(columns=["SEGMENTO", "Arrastre_V20", "Actual_V20", "Arrastre_Imp_V20", "Actual_Imp_V20", "Gross_V20"])

        rep_ccc = rep_ccc_global[rep_ccc_global["SUP"].astype(str).str.strip() == sup_seleccionado].copy() if not rep_ccc_global.empty and "SUP" in rep_ccc_global.columns else pd.DataFrame()
        rep_mn = rep_mn_global[rep_mn_global["SUP"].astype(str).str.strip() == sup_seleccionado].copy() if not rep_mn_global.empty and "SUP" in rep_mn_global.columns else pd.DataFrame()
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

        v20_segmento = v20_agg_global
        rep_ccc = rep_ccc_global.copy()
        rep_mn = rep_mn_global.copy()
        cartera_base = cartera_base_global.copy()

    # Consolidación final por Segmento incluyendo Vendedor 20
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

    total_v20_kilos = float((v20_segmento["Arrastre_V20"] + v20_segmento["Actual_V20"]).sum()) if not v20_segmento.empty else 0.0

    # Redondeos y cálculos de porcentajes
    df_seg["Objetivo_Kilos_Kg"] = df_seg["Objetivo_Kilos_Kg"].round(2)
    df_seg["Objetivo_Importe_Arg"] = df_seg["Objetivo_Importe_Arg"].round(2)
    df_seg["Arrastre"] = df_seg["Arrastre"].round(2)
    df_seg["Actual"] = df_seg["Actual"].round(2)
    df_seg["Kilos_Operativos_Kg"] = df_seg["Kilos_Operativos_Kg"].round(2)
    df_seg["Importe_Operativo_Arg"] = df_seg["Importe_Operativo_Arg"].round(2)
    df_seg["Kilos_Proyectados_Kg"] = df_seg["Kilos_Proyectados_Kg"].round(2)
    df_seg["Gross_Proyectado_Arg"] = df_seg["Gross_Proyectado_Arg"].round(2)
    
    df_seg["Cumplimiento_Actual_Pct"] = (df_seg["Kilos_Operativos_Kg"] / df_seg["Objetivo_Kilos_Kg"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    df_seg["Cumplimiento_Proyectado_Pct"] = (df_seg["Kilos_Proyectados_Kg"] / df_seg["Objetivo_Kilos_Kg"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    df_seg["Cumplimiento_Gross_Proy_Pct"] = (df_seg["Gross_Proyectado_Arg"] / df_seg["Objetivo_Importe_Arg"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)

    precio_unit_segmento_obj = (df_seg["Objetivo_Importe_Arg"] / df_seg["Objetivo_Kilos_Kg"].replace(0, 1.0))
    
    df_seg["Futuro_A_Incorporar_Kgs"] = (df_seg["Objetivo_Kilos_Kg"] - df_seg["Kilos_Proyectados_Kg"]).clip(lower=0).round(2)
    df_seg["Futuro_A_Incorporar_Gross"] = (df_seg["Futuro_A_Incorporar_Kgs"] * precio_unit_segmento_obj).round(2)

    # Ordenamiento oficial de segmentos idéntico a rep_kilos
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

    # ----------------------------------------------------
    # TABLA 1: GROSS / IMPORTES
    # ----------------------------------------------------
    df_gross_seg = df_seg[[
        "SEGMENTO", "Objetivo_Importe_Arg", "Importe_Operativo_Arg", 
        "Gross_Proyectado_Arg", "Cumplimiento_Gross_Proy_Pct", "Futuro_A_Incorporar_Gross"
    ]].copy()

    df_gross_seg = df_gross_seg.rename(columns={
        "Objetivo_Importe_Arg": "Objetivo Gross Pepsico",
        "Importe_Operativo_Arg": "Operativo Gross",
        "Gross_Proyectado_Arg": "Proyectado Gross",
        "Cumplimiento_Gross_Proy_Pct": "% Cumpl. Proy. Gross",
        "Futuro_A_Incorporar_Gross": "A Incorporar Gross"
    })

    df_gross_excel = df_gross_seg.copy()
    df_gross_display = df_gross_seg.copy()
    for col in ["Objetivo Gross Pepsico", "Operativo Gross", "Proyectado Gross", "A Incorporar Gross"]:
        if col in df_gross_display.columns:
            df_gross_display[col] = df_gross_display[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
    if "% Cumpl. Proy. Gross" in df_gross_display.columns:
        df_gross_display["% Cumpl. Proy. Gross"] = df_gross_display["% Cumpl. Proy. Gross"].apply(lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%")

    tot_obj_gross = float(df_gross_seg["Objetivo Gross Pepsico"].sum())
    tot_operativo_g = float(df_gross_seg["Operativo Gross"].sum())
    tot_proy_g = float(df_gross_seg["Proyectado Gross"].sum())
    cump_proy_g_val = round((tot_proy_g / tot_obj_gross * 100.0) if tot_obj_gross > 0 else 0.0, 2)
    tot_incorporar_g = float(df_gross_seg["A Incorporar Gross"].sum())

    # ----------------------------------------------------
    # TABLA 2: KILOS / VOLUMEN
    # ----------------------------------------------------
    df_kilos_seg = df_seg[[
        "SEGMENTO", "Objetivo_Kilos_Kg", "Arrastre", "Actual", 
        "Kilos_Operativos_Kg", "Cumplimiento_Actual_Pct", "Kilos_Proyectados_Kg", 
        "Cumplimiento_Proyectado_Pct", "Futuro_A_Incorporar_Kgs"
    ]].copy()

    df_kilos_seg = df_kilos_seg.rename(columns={
        "Objetivo_Kilos_Kg": "Objetivo Kilos Pepsico",
        "Arrastre": "Arrastre Kilos",
        "Actual": "Mes Actual Kilos",
        "Kilos_Operativos_Kg": "Operativo Kilos",
        "Cumplimiento_Actual_Pct": "% Cumpl. Actual",
        "Kilos_Proyectados_Kg": "Proyectado Kilos",
        "Cumplimiento_Proyectado_Pct": "% Cumpl. Proy. Kilos",
        "Futuro_A_Incorporar_Kgs": "A Incorporar Kilos"
    })

    df_kilos_excel = df_kilos_seg.copy()
    df_kilos_display = df_kilos_seg.copy()
    for col in ["Objetivo Kilos Pepsico", "Arrastre Kilos", "Mes Actual Kilos", "Operativo Kilos", "Proyectado Kilos", "A Incorporar Kilos"]:
        if col in df_kilos_display.columns:
            df_kilos_display[col] = df_kilos_display[col].apply(lambda x: f"{x:,.2f} kg" if pd.notna(x) else "0.00 kg")
    for col in ["% Cumpl. Actual", "% Cumpl. Proy. Kilos"]:
        if col in df_kilos_display.columns:
            df_kilos_display[col] = df_kilos_display[col].apply(lambda x: f"{x:,.2f}%" if pd.notna(x) else "0.00%")

    tot_obj_kilos = float(df_kilos_seg["Objetivo Kilos Pepsico"].sum())
    tot_operativo_k = float(df_kilos_seg["Operativo Kilos"].sum())
    tot_proy_k = float(df_kilos_seg["Proyectado Kilos"].sum())
    cump_proy_k_val = round((tot_proy_k / tot_obj_kilos * 100.0) if tot_obj_kilos > 0 else 0.0, 2)
    tot_incorporar_k = float(df_kilos_seg["A Incorporar Kilos"].sum())

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

    # ----------------------------------------------------
    # PANEL DE AUDITORÍA Y CONCILIACIÓN (V20 y Reemplazos)
    # ----------------------------------------------------
    with st.expander("🔍 Auditoría de Conciliación: Preventistas vs. Consolidado Gerencial", expanded=False):
        st.markdown("Este panel desglosa el origen exacto de la brecha numérica entre la tendencia de preventistas (`rep_kilos`) y el consolidado del tablero gerencial.")
        
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
            
        st.info("💡 **Conclusión de Auditoría:** La diferencia entre ambos reportes se debe exclusivamente a que el Tablero Gerencial incorpora el volumen y tendencia del **Vendedor 20** y las reasignaciones de red por **reemplazos/comodines**, los cuales operan fuera de la grilla estándar de preventistas.")

    st.divider()

    # RENDERIZADO EN PESTAÑAS LIMPIAS
    tab_k, tab_c, tab_mn, tab_m = st.tabs(["📦 Kilos e Importes por Segmento", "📈 CCC por Taxonomía", "📱 MiNegocio por Taxonomía", "🎯 Cobertura por Marca"])

    with tab_k:
        st.markdown("### 💰 1. Desglose Financiero (Gross / Importes)")
        
        # Fila 1 (Nivel Superior Exclusivo): Proyectado Gross en ROJO vibrante y 50% más grande
        col_proy_g1, col_proy_g2, col_proy_g3 = st.columns([1, 2, 1])
        with col_proy_g2:
            st.markdown(tarjeta_metrica_html("📊 PROYECTADO GROSS", f"${tot_proy_g:,.0f}", "#ef4444", "2.2rem", "1.1rem"), unsafe_allow_html=True)

        # Fila 2: Resto de indicadores financieros con colores distintos
        mi1, mi2, mi3, mi4 = st.columns(4)
        with mi1:
            st.markdown(tarjeta_metrica_html("💰 OBJ. GROSS", f"${tot_obj_gross:,.0f}", "#3b82f6", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mi2:
            st.markdown(tarjeta_metrica_html("💵 OPERATIVO GROSS", f"${tot_operativo_g:,.0f}", "#10b981", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mi3:
            st.markdown(tarjeta_metrica_html("📊 CUMP. PROY.", f"{cump_proy_g_val:,.2f}%", "#06b6d4", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mi4:
            st.markdown(tarjeta_metrica_html("🎯 A INCORPORAR", f"${tot_incorporar_g:,.0f}", "#f59e0b", "1.1rem", "0.5rem"), unsafe_allow_html=True)

        st.dataframe(df_gross_display, width="stretch", hide_index=True)
        
        buf_g = io.BytesIO()
        with pd.ExcelWriter(buf_g, engine="openpyxl") as w:
            df_gross_excel.to_excel(w, index=False, sheet_name="Gross_Importes_Segmento")
        st.download_button("📥 Descargar Gross / Importes a Excel", data=buf_g.getvalue(), file_name="gross_importes_por_segmento.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_gross_seg")

        st.divider()
        st.markdown("### 📦 2. Desglose Operativo (Kilos / Volumen)")
        
        # Fila 1 (Nivel Superior Exclusivo): Proyectado Kilos en ROJO vibrante y 50% más grande
        col_proy_k1, col_proy_k2, col_proy_k3 = st.columns([1, 2, 1])
        with col_proy_k2:
            st.markdown(tarjeta_metrica_html("🔮 PROYECTADO KILOS", f"{tot_proy_k:,.0f} kg", "#ef4444", "2.2rem", "1.1rem"), unsafe_allow_html=True)

        # Fila 2: Resto de indicadores operativos con colores distintos
        mk1, mk2, mk3, mk4 = st.columns(4)
        with mk1:
            st.markdown(tarjeta_metrica_html("🎯 OBJETIVO KILOS", f"{tot_obj_kilos:,.0f} kg", "#3b82f6", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mk2:
            st.markdown(tarjeta_metrica_html("📊 OPERATIVO KILOS", f"{tot_operativo_k:,.0f} kg", "#10b981", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mk3:
            st.markdown(tarjeta_metrica_html("📈 CUMP. PROY.", f"{cump_proy_g_val:,.2f}%", "#06b6d4", "1.1rem", "0.5rem"), unsafe_allow_html=True)
        with mk4:
            st.markdown(tarjeta_metrica_html("🎯 A INCORPORAR", f"{tot_incorporar_k:,.0f} kg", "#f59e0b", "1.1rem", "0.5rem"), unsafe_allow_html=True)

        st.dataframe(df_kilos_display, width="stretch", hide_index=True)
        
        buf_k = io.BytesIO()
        with pd.ExcelWriter(buf_k, engine="openpyxl") as w:
            df_kilos_excel.to_excel(w, index=False, sheet_name="Kilos_Volumen_Segmento")
        st.download_button("📥 Descargar Kilos / Volumen a Excel", data=buf_k.getvalue(), file_name="kilos_volumen_por_segmento.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_kilos_seg")

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