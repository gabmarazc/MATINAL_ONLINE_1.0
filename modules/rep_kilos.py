# modules/rep_kilos.py
import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import parsear_fecha_robusta

def preparar_datos_ventas_segmento(df_vta, df_ausencias, anio_operativo, mes_operativo, dia_matinal):
    df = df_vta.copy()
    df["PesoKg"] = pd.to_numeric(df.get("PesoKg", 0), errors="coerce").fillna(0.0)

    if "TipoDeVenta" in df.columns:
        tipos_excluidos = [
            "Comodato Devolución", 
            "Comodato Ficticio", 
            "Comodato Ficticio Devolución", 
            "Comodato Préstamo"
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

    if "Subramo" in df.columns:
        subramo_clean = df["Subramo"].fillna("").astype(str).str.strip().str.upper()
        df = df[~subramo_clean.isin(["EMPLOYEES", "EMPLEADOS"])]

    df["FechaCarga_dt"] = parsear_fecha_robusta(df["FechaCarga"])
    df["FechaEntrega_dt"] = parsear_fecha_robusta(df["FechaEntrega"])

    dia_matinal_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    
    if pd.notna(dia_matinal_dt):
        es_mes_en_curso = (dia_matinal_dt.year == anio_operativo and dia_matinal_dt.month in [mes_operativo, mes_operativo + 1])
        if es_mes_en_curso:
            df = df[df["FechaCarga_dt"].dt.date < dia_matinal_dt.date()]

    col_vend_tit = None
    for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]:
        if cand in df.columns:
            col_vend_tit = cand
            break
    if not col_vend_tit:
        col_vend_tit = "CodVendedor"
        df[col_vend_tit] = 0

    df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype("Int64")

    col_m = next((c for c in ["Marca", "MARCA", "marca"] if c in df.columns), None)
    df["Marca"] = df[col_m].fillna("").astype(str).str.strip().str.upper() if col_m else "SIN MARCA"

    col_rent = "SegmentoRentabilidad" if "SegmentoRentabilidad" in df.columns else None
    col_rubro = "Rubro" if "Rubro" in df.columns else None
    
    def asignar_segmento(row):
        sr = str(row.get(col_rent, "")).strip().title() if col_rent else ""
        rubro = str(row.get(col_rubro, "")).strip() if col_rubro else ""
        if sr in ["Platinum", "Gold"]:
            return f"GOLD {rubro}".strip()
        elif sr in ["Silver", "Bronze"]:
            return f"SILVER {rubro}".strip()
        return None

    df["SEGMENTO"] = df.apply(asignar_segmento, axis=1)

    df["MesCarga"] = df["FechaCarga_dt"].dt.month
    df["AñoCarga"] = df["FechaCarga_dt"].dt.year
    df["MesEntrega"] = df["FechaEntrega_dt"].dt.month
    df["AñoEntrega"] = df["FechaEntrega_dt"].dt.year

    mes_ant = 12 if mes_operativo == 1 else mes_operativo - 1
    anio_ant = anio_operativo - 1 if mes_operativo == 1 else anio_operativo

    mes_sig = 1 if mes_operativo == 12 else mes_operativo + 1
    anio_sig = anio_operativo + 1 if mes_operativo == 12 else anio_operativo

    def asignar_periodo(row):
        ac, mc = row["AñoCarga"], row["MesCarga"]
        ae, me = row["AñoEntrega"], row["MesEntrega"]
        
        if ac == anio_ant and mc == mes_ant and ae == anio_operativo and me == mes_operativo:
            return "Arrastre"
        elif ac == anio_operativo and mc == mes_operativo and ae == anio_operativo and me == mes_operativo:
            return "Actual"
        elif ac == anio_operativo and mc == mes_operativo and ae == anio_sig and me == mes_sig:
            return "Futuro"
        return "Fuera de Periodo"

    df["Periodo"] = df.apply(asignar_periodo, axis=1)

    df["ClaveAUS_Carga"] = df["CodVendedor"].astype(str) + "-" + df["FechaCarga_dt"].dt.strftime("%Y-%m-%d")
    df["ClaveAUS_Entrega"] = df["CodVendedor"].astype(str) + "-" + df["FechaEntrega_dt"].dt.strftime("%Y-%m-%d")

    df_aus = df_ausencias.copy() if df_ausencias is not None and not df_ausencias.empty else pd.DataFrame()
    if not df_aus.empty:
        col_aus_vend = None
        for c in ["Ausente", "CodVend", "CodVendedor", "Vendedor", "Cod_Vendedor"]:
            if c in df_aus.columns:
                col_aus_vend = c
                break
        if not col_aus_vend:
            col_aus_vend = df_aus.columns[3]

        col_aus_fecha = None
        for c in ["Fecha", "FechaAusencia", "Dia"]:
            if c in df_aus.columns:
                col_aus_fecha = c
                break
        if not col_aus_fecha:
            col_aus_fecha = df_aus.columns[2]

        col_aus_reemp = None
        for c in ["Reemplazo", "CodReemplazo", "Cod_Reemplazo", "PreventistaReemplazo"]:
            if c in df_aus.columns:
                col_aus_reemp = c
                break
        if not col_aus_reemp:
            col_aus_reemp = df_aus.columns[4]

        df_aus["Fecha_dt"] = parsear_fecha_robusta(df_aus[col_aus_fecha])
        df_aus["CodVend_clean"] = pd.to_numeric(df_aus[col_aus_vend], errors="coerce").astype("Int64")
        df_aus["ClaveAUS"] = df_aus["CodVend_clean"].astype(str) + "-" + df_aus["Fecha_dt"].dt.strftime("%Y-%m-%d")
        df_aus["Reemplazo_clean"] = pd.to_numeric(df_aus[col_aus_reemp], errors="coerce").astype("Int64")

        aus_map = df_aus.dropna(subset=["ClaveAUS", "Reemplazo_clean"]).drop_duplicates("ClaveAUS").set_index("ClaveAUS")["Reemplazo_clean"]
        
        df["Reemplazo"] = df["ClaveAUS_Carga"].map(aus_map).combine_first(df["ClaveAUS_Entrega"].map(aus_map))
        df["CodVendedorOperativo"] = df["Reemplazo"].combine_first(df["CodVendedor"]).astype("Int64")
    else:
        df["Reemplazo"] = pd.NA
        df["CodVendedorOperativo"] = df["CodVendedor"]

    return df

def generar_reporte_avance_kilos_segmento(df_vta_prep, df_rutas, maestro_vend, maestro_seg, maestro_cebe, dia_venta, anio_operativo, mes_operativo, sup_filtro):
    vendedores_rep = pd.DataFrame()
    col_cod = "Codigo_Vendedor" if "Codigo_Vendedor" in maestro_vend.columns else maestro_vend.columns[0]
    col_nom = "Nombre_Vendedor" if "Nombre_Vendedor" in maestro_vend.columns else maestro_vend.columns[1]
    col_sup = "Supervisor" if "Supervisor" in maestro_vend.columns else maestro_vend.columns[2]

    vendedores_rep["CodVend"] = pd.to_numeric(maestro_vend[col_cod], errors="coerce").astype("Int64")
    vendedores_rep["Nombre"] = maestro_vend[col_nom].fillna("").astype(str).str.strip()
    vendedores_rep["SUP"] = maestro_vend[col_sup].fillna("").astype(str).str.strip()
    vendedores_rep = vendedores_rep.dropna(subset=["CodVend"]).drop_duplicates(subset=["CodVend"])

    codigos_validos_padron = set(vendedores_rep["CodVend"].dropna().tolist())
    sup_map = vendedores_rep.set_index("CodVend")["SUP"].to_dict()

    orden_segmentos_maestro = [
        "GOLD Salty",
        "GOLD Crakers",
        "SILVER Salty",
        "SILVER Crakers",
        "SILVER Cereals"
    ]

    segs_vta_unicos = df_vta_prep["SEGMENTO"].dropna().astype(str).str.strip().unique()
    for s_v in segs_vta_unicos:
        if s_v not in orden_segmentos_maestro:
            orden_segmentos_maestro.append(s_v)

    segmentos_rep = pd.DataFrame({"SEGMENTO": orden_segmentos_maestro})

    df_comodines = pd.DataFrame({
        "CodVend": [-999, -998],
        "Nombre": ["DEPOSITO", "REEMPLAZO"],
        "SUP": ["GENERAL", "GENERAL"]
    })
    vendedores_rep_full = pd.concat([vendedores_rep, df_comodines], ignore_index=True)

    vendedores_rep_full["_k"] = 1
    segmentos_rep["_k"] = 1
    matriz = vendedores_rep_full.merge(segmentos_rep, on="_k").drop(columns="_k")

    df_vtas_op = df_vta_prep[df_vta_prep["Periodo"].isin(["Arrastre", "Actual"]) & df_vta_prep["SEGMENTO"].notna()].copy()
    
    def rutear_vendedor_operativo(row):
        cod_op = row["CodVendedorOperativo"]
        cod_tit = row["CodVendedor"]
        reemp = row.get("Reemplazo", pd.NA)
        
        if (pd.notna(reemp) and int(reemp) == 99) or (pd.notna(cod_op) and int(cod_op) == 99) or (pd.notna(cod_tit) and int(cod_tit) == 99):
            return -998
        elif pd.notna(cod_op) and int(cod_op) in codigos_validos_padron:
            return int(cod_op)
        elif pd.notna(cod_tit) and int(cod_tit) in codigos_validos_padron:
            return int(cod_tit)
        else:
            return -999

    df_vtas_op["CodVend_Op"] = df_vtas_op.apply(rutear_vendedor_operativo, axis=1).astype("Int64")
    
    def asignar_sup_transaccion(row):
        c_op = row["CodVend_Op"]
        c_tit = row["CodVendedor"]
        if c_op == -999:
            return "GENERAL"
        elif c_op == -998:
            return sup_map.get(c_tit, "GENERAL")
        else:
            return sup_map.get(c_op, sup_map.get(c_tit, "GENERAL"))

    df_vtas_op["SUP_Transaccion"] = df_vtas_op.apply(asignar_sup_transaccion, axis=1).astype(str).str.strip()
    df_vtas_op["SEGMENTO"] = df_vtas_op["SEGMENTO"].astype(str).str.strip()
    
    kilos = df_vtas_op.groupby(["CodVend_Op", "SEGMENTO", "Periodo"], dropna=False)["PesoKg"].sum().reset_index()
    kilos = kilos.rename(columns={"CodVend_Op": "CodVend"})
    
    if not kilos.empty:
        kilos_pivot = kilos.pivot_table(index=["CodVend", "SEGMENTO"], columns="Periodo", values="PesoKg", aggfunc="sum", fill_value=0.0).reset_index()
        kilos_pivot.columns.name = None
    else:
        kilos_pivot = pd.DataFrame(columns=["CodVend", "SEGMENTO", "Arrastre", "Actual"])

    for col_p in ["Arrastre", "Actual"]:
        if col_p not in kilos_pivot.columns:
            kilos_pivot[col_p] = 0.0

    reporte = matriz.merge(kilos_pivot[["CodVend", "SEGMENTO", "Arrastre", "Actual"]], on=["CodVend", "SEGMENTO"], how="left")
    reporte[["Arrastre", "Actual"]] = reporte[["Arrastre", "Actual"]].fillna(0.0)

    rutas = df_rutas.copy() if df_rutas is not None and not df_rutas.empty else pd.DataFrame()
    
    if not rutas.empty:
        col_fecha_r = next((c for c in ["Fecha", "fecha", "Dia", "Date", "FECHA"] if c in rutas.columns), rutas.columns[0])
        col_vend_r = next((c for c in ["codven", "CodVen", "CodVendedor", "Vendedor", "Cod_Vendedor", "CODVEN"] if c in rutas.columns), rutas.columns[1])

        s_fechas = rutas[col_fecha_r].astype(str).str.strip().str.replace(" 00:00:00", "", regex=False)
        dt_directo = pd.to_datetime(s_fechas, format="%Y-%m-%d", errors="coerce")
        dt_invertido = pd.to_datetime(s_fechas, format="%Y-%d-%m", errors="coerce")
        
        coincidencias_directo = (dt_directo.dt.year == int(anio_operativo)) & (dt_directo.dt.month == int(mes_operativo))
        coincidencias_invertido = (dt_invertido.dt.year == int(anio_operativo)) & (dt_invertido.dt.month == int(mes_operativo))
        
        if coincidencias_directo.sum() >= coincidencias_invertido.sum() and coincidencias_directo.sum() > 0:
            rutas["Fecha_dt"] = dt_directo
        elif coincidencias_invertido.sum() > 0:
            rutas["Fecha_dt"] = dt_invertido
        else:
            rutas["Fecha_dt"] = parsear_fecha_robusta(rutas[col_fecha_r])

        rutas["CodVend"] = pd.to_numeric(rutas[col_vend_r], errors="coerce").astype("Int64")

        rutas_mes = rutas[
            (rutas["Fecha_dt"].dt.year == int(anio_operativo)) & 
            (rutas["Fecha_dt"].dt.month == int(mes_operativo))
        ].copy()

        dia_v_dt = parsear_fecha_robusta(pd.Series([dia_venta])).iloc[0]
        corte_date = dia_v_dt.date() if pd.notna(dia_v_dt) else None

        if corte_date is not None:
            pasadas = rutas_mes[rutas_mes["Fecha_dt"].dt.date <= corte_date]
        else:
            pasadas = rutas_mes

        dias_pasados = pasadas.groupby("CodVend")["Fecha_dt"].nunique()
        dias_totales = rutas_mes.groupby("CodVend")["Fecha_dt"].nunique()

        reporte = reporte.merge(dias_pasados.rename("Días Pasados"), left_on="CodVend", right_index=True, how="left")
        reporte = reporte.merge(dias_totales.rename("Rutas"), left_on="CodVend", right_index=True, how="left")
    else:
        reporte["Días Pasados"] = 0
        reporte["Rutas"] = 0

    reporte["Días Pasados"] = reporte["Días Pasados"].fillna(0).astype("Int64")
    reporte["Rutas"] = reporte["Rutas"].fillna(0).astype("Int64")
    reporte["Días Restantes"] = (reporte["Rutas"] - reporte["Días Pasados"]).clip(lower=0).astype("Int64")

    df_obj_db = db.cargar_tabla_sql(
        f"SELECT CodVendedor, SEGMENTO, Obj_Sugerido_Kg FROM objetivos_vendedores WHERE Anio = {int(anio_operativo)} AND Mes = {int(mes_operativo)}"
    )

    if not df_obj_db.empty:
        df_obj_db["CodVend"] = pd.to_numeric(df_obj_db["CodVendedor"], errors="coerce").astype("Int64")
        df_obj_db["SEGMENTO"] = df_obj_db["SEGMENTO"].fillna("").astype(str).str.strip()
        df_obj_db["Obj_Sugerido_Kg"] = pd.to_numeric(df_obj_db["Obj_Sugerido_Kg"], errors="coerce").fillna(0.0)
        
        objs_agrup = df_obj_db.groupby(["CodVend", "SEGMENTO"], as_index=False)["Obj_Sugerido_Kg"].sum()
        objs_agrup = objs_agrup.rename(columns={"Obj_Sugerido_Kg": "Objetivo Mes Corriente"})
        reporte = reporte.merge(objs_agrup, on=["CodVend", "SEGMENTO"], how="left")
    else:
        mes_ant = 12 if mes_operativo == 1 else mes_operativo - 1
        anio_ant = anio_operativo - 1 if mes_operativo == 1 else anio_operativo

        historial = df_vta_prep[
            (df_vta_prep["AñoEntrega"].eq(anio_ant)) & 
            (df_vta_prep["MesEntrega"].eq(mes_ant)) & 
            df_vta_prep["SEGMENTO"].notna()
        ].copy()

        if not historial.empty and maestro_cebe is not None and not maestro_cebe.empty and "Obj_Mes" in maestro_cebe.columns:
            historial["CodVend"] = pd.to_numeric(historial["CodVendedor"], errors="coerce").astype("Int64")
            col_m_cebe = next((c for c in maestro_cebe.columns if str(c).strip().lower() in ["marca", "marcaupper"]), maestro_cebe.columns[0])
            maestro_cebe_clean = maestro_cebe.copy()
            maestro_cebe_clean["Marca_Key"] = maestro_cebe_clean[col_m_cebe].fillna("").astype(str).str.strip().str.upper()
            maestro_cebe_clean["Obj_Mes_Val"] = pd.to_numeric(maestro_cebe_clean["Obj_Mes"], errors="coerce").fillna(0.0)
            
            mapa_obj_marca = maestro_cebe_clean.groupby("Marca_Key")["Obj_Mes_Val"].sum().to_dict()
            
            kilos_hist = historial.groupby(["CodVend", "SEGMENTO", "Marca"])["PesoKg"].sum().reset_index().rename(columns={"PesoKg": "Kilos_Hist"})
            kilos_hist["Total_Kilos_Marca_Seg"] = kilos_hist.groupby(["SEGMENTO", "Marca"])["Kilos_Hist"].transform("sum")
            kilos_hist["Part_Vendedor"] = (kilos_hist["Kilos_Hist"] / kilos_hist["Total_Kilos_Marca_Seg"].replace(0, pd.NA)).fillna(0.0)
            
            kilos_hist["Obj_Marca_Oficial"] = kilos_hist["Marca"].map(mapa_obj_marca).fillna(0.0)
            kilos_hist["Obj_Asignado"] = kilos_hist["Part_Vendedor"] * kilos_hist["Obj_Marca_Oficial"] * 1000.0
            
            objs_oficiales = kilos_hist.groupby(["CodVend", "SEGMENTO"])["Obj_Asignado"].sum().reset_index().rename(columns={"Obj_Asignado": "Objetivo Mes Corriente"})
            reporte = reporte.merge(objs_oficiales, on=["CodVend", "SEGMENTO"], how="left")
        else:
            reporte["Objetivo Mes Corriente"] = 0.0

    reporte["Objetivo Mes Corriente"] = reporte["Objetivo Mes Corriente"].fillna(0.0)

    reemplazos = df_vtas_op[df_vtas_op["CodVend_Op"].ne(df_vtas_op["CodVendedor"])][["CodVendedor", "CodVend_Op", "SEGMENTO", "Periodo", "PesoKg"]].copy()
    
    if not reemplazos.empty:
        mov_titular = reemplazos[["CodVendedor", "SEGMENTO", "Periodo", "PesoKg"]].rename(columns={"CodVendedor": "CodVend"})
        mov_titular["Ajuste_Valor"] = -mov_titular.pop("PesoKg")
        
        mov_reemp = reemplazos[["CodVend_Op", "SEGMENTO", "Periodo", "PesoKg"]].rename(columns={"CodVend_Op": "CodVend"})
        mov_reemp["Ajuste_Valor"] = mov_reemp.pop("PesoKg") if "PesoKg" in mov_reemp.columns else 0.0

        ajustes_totales = pd.concat([mov_titular, mov_reemp], ignore_index=True)
        ajustes_totales["CodVend"] = pd.to_numeric(ajustes_totales["CodVend"], errors="coerce").astype("Int64")
        
        aj_arr = ajustes_totales[ajustes_totales["Periodo"] == "Arrastre"].groupby(["CodVend", "SEGMENTO"])["Ajuste_Valor"].sum().reset_index().rename(columns={"Ajuste_Valor": "Ajuste_Reemp_Arrastre"})
        aj_act = ajustes_totales[ajustes_totales["Periodo"] == "Actual"].groupby(["CodVend", "SEGMENTO"])["Ajuste_Valor"].sum().reset_index().rename(columns={"Ajuste_Valor": "Ajuste_Reemp_Actual"})

        reporte = reporte.merge(aj_arr, on=["CodVend", "SEGMENTO"], how="left")
        reporte = reporte.merge(aj_act, on=["CodVend", "SEGMENTO"], how="left")
    else:
        reporte["Ajuste_Reemp_Arrastre"] = 0.0
        reporte["Ajuste_Reemp_Actual"] = 0.0

    reporte["Ajuste_Reemp_Arrastre"] = reporte.get("Ajuste_Reemp_Arrastre", 0.0).fillna(0.0)
    reporte["Ajuste_Reemp_Actual"] = reporte.get("Ajuste_Reemp_Actual", 0.0).fillna(0.0)
    reporte["Ajuste_Por_Reemp"] = reporte["Ajuste_Reemp_Arrastre"] + reporte["Ajuste_Reemp_Actual"]

    if orden_segmentos_maestro:
        mapping_orden = {str(seg).strip(): i for i, seg in enumerate(orden_segmentos_maestro)}
        reporte["SEGMENTO_STR"] = reporte["SEGMENTO"].astype(str).str.strip()
        reporte["_orden_idx"] = reporte["SEGMENTO_STR"].map(mapping_orden).fillna(999)
        reporte = reporte.sort_values(by=["CodVend", "_orden_idx"]).drop(columns=["_orden_idx", "SEGMENTO_STR"]).reset_index(drop=True)
    else:
        reporte = reporte.sort_values(by=["CodVend", "SEGMENTO"]).reset_index(drop=True)

    reporte["SEGMENTO"] = reporte["SEGMENTO"].astype(str)
    
    clave_vtas_op = f"_df_vtas_op_{anio_operativo}_{mes_operativo}_{sup_filtro}"
    st.session_state[clave_vtas_op] = df_vtas_op
    st.session_state[f"_orden_seg_{anio_operativo}_{mes_operativo}"] = orden_segmentos_maestro

    reporte = reporte.rename(columns={"CodVend": "CodVendedor"})
    return reporte

@st.fragment
def render_fragmento_interactivo_kilos(reporte_vendedores_puro, df_comodines_Rows, s_dispo, v_dispo, anio_op, mes_op, sup_filtro, df_vta_prep, dia_matinal):
    from modules.utils import tarjeta_metrica_html

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], key=f"frag_kilos_v_{anio_op}_{mes_op}_{sup_filtro}")
    with col_f2:
        s_selec = st.multiselect("Segmento", options=s_dispo, default=[], key=f"frag_kilos_s_{anio_op}_{mes_op}_{sup_filtro}")

    if not v_selec:
        v_selec = v_dispo
    if not s_selec:
        s_selec = s_dispo

    rep_filtrado = reporte_vendedores_puro[
        reporte_vendedores_puro["Nombre"].astype(str).str.strip().isin(v_selec) & 
        reporte_vendedores_puro["SEGMENTO"].astype(str).str.strip().isin(s_selec)
    ].copy()

    for col_req in ["Ajuste_Reemp_Arrastre", "Ajuste_Reemp_Actual", "Ajuste_Por_Reemp"]:
        if col_req not in rep_filtrado.columns:
            rep_filtrado[col_req] = 0.0

    rep_detalle = rep_filtrado[
        ["CodVendedor", "Nombre", "SUP", "SEGMENTO", "Objetivo Mes Corriente", "Arrastre", "Actual", "Ajuste_Reemp_Arrastre", "Ajuste_Reemp_Actual", "Ajuste_Por_Reemp", "Días Pasados", "Rutas", "Días Restantes"]
    ].copy()

    rep_detalle["OPERATIVO"] = rep_detalle["Arrastre"] + rep_detalle["Actual"] + rep_detalle["Ajuste_Por_Reemp"]

    es_todos_vendedores = (len(v_selec) == len(v_dispo)) and (len(v_dispo) > 0)
    total_arrastre_vend = float(rep_detalle["Arrastre"].sum())
    total_actual_vend = float(rep_detalle["Actual"].sum())

    clave_vtas_op = f"_df_vtas_op_{anio_op}_{mes_op}_{sup_filtro}"
    df_global_op = st.session_state.get(clave_vtas_op, pd.DataFrame())

    if es_todos_vendedores:
        if not df_global_op.empty:
            df_reemp_trans = df_global_op[df_global_op["CodVend_Op"] == -998].copy()
            if sup_filtro != "TODOS":
                df_reemp_trans = df_reemp_trans[df_reemp_trans["SUP_Transaccion"].astype(str).str.strip() == sup_filtro]
            if s_dispo:
                df_reemp_trans = df_reemp_trans[df_reemp_trans["SEGMENTO"].astype(str).str.strip().isin(s_selec)]
            
            arrastre_reemp = float(df_reemp_trans[df_reemp_trans["Periodo"] == "Arrastre"]["PesoKg"].sum())
            actual_reemp = float(df_reemp_trans[df_reemp_trans["Periodo"] == "Actual"]["PesoKg"].sum())
        else:
            arrastre_reemp = 0.0
            actual_reemp = 0.0

        total_arrastre = total_arrastre_vend + arrastre_reemp
        total_actual = total_actual_vend + actual_reemp
        total_neto_operativo = total_arrastre + total_actual
    else:
        total_arrastre = total_arrastre_vend
        total_actual = total_actual_vend
        total_neto_operativo = float(rep_detalle["OPERATIVO"].sum())

    total_objetivo_mes = float(rep_detalle["Objetivo Mes Corriente"].sum())
    pct_avance = (total_neto_operativo / total_objetivo_mes * 100.0) if total_objetivo_mes > 0 else 0.0

    fecha_mat_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(fecha_mat_dt):
        f_ult = (fecha_mat_dt - pd.Timedelta(days=7)).date()
        f_penult = (fecha_mat_dt - pd.Timedelta(days=14)).date()
        
        u_vta = df_vta_prep[df_vta_prep["FechaCarga_dt"].dt.date.eq(f_ult)].groupby(["CodVendedor", "SEGMENTO"])["PesoKg"].sum().reset_index().rename(columns={"PesoKg": "Ultima_Vta"})
        p_vta = df_vta_prep[df_vta_prep["FechaCarga_dt"].dt.date.eq(f_penult)].groupby(["CodVendedor", "SEGMENTO"])["PesoKg"].sum().reset_index().rename(columns={"PesoKg": "Penultima_Vta"})
    else:
        u_vta = pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Ultima_Vta"])
        p_vta = pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Penultima_Vta"])

    if not u_vta.empty:
        u_vta["CodVendedor"] = pd.to_numeric(u_vta["CodVendedor"], errors="coerce").astype("Int64")
        rep_detalle = rep_detalle.merge(u_vta, on=["CodVendedor", "SEGMENTO"], how="left")
    else:
        rep_detalle["Ultima_Vta"] = 0.0

    if not p_vta.empty:
        p_vta["CodVendedor"] = pd.to_numeric(p_vta["CodVendedor"], errors="coerce").astype("Int64")
        rep_detalle = rep_detalle.merge(p_vta, on=["CodVendedor", "SEGMENTO"], how="left")
    else:
        rep_detalle["Penultima_Vta"] = 0.0

    rep_detalle[["Ultima_Vta", "Penultima_Vta"]] = rep_detalle[["Ultima_Vta", "Penultima_Vta"]].fillna(0.0)

    dp_s = rep_detalle["Días Pasados"].astype(float).replace(0, 1.0)
    dr_s = rep_detalle["Días Restantes"].astype(float)

    p_diario = (rep_detalle["Actual"] + rep_detalle["Ajuste_Reemp_Actual"]) / dp_s
    rep_detalle["Promedio_Diario"] = p_diario
    
    rep_detalle["Tendencia_Total_Kg"] = rep_detalle["OPERATIVO"]
    mask_activos = dr_s > 0
    if mask_activos.any():
        rep_detalle.loc[mask_activos, "Tendencia_Total_Kg"] = (p_diario[mask_activos] * dr_s[mask_activos]) + rep_detalle.loc[mask_activos, "OPERATIVO"]

    rep_detalle["Cumplimiento_Proyectado_Pct"] = ((rep_detalle["Tendencia_Total_Kg"]) / rep_detalle["Objetivo Mes Corriente"].replace(0, pd.NA)).mul(100).fillna(0.0)
    
    rep_detalle["Media_Necesaria_Diaria"] = 0.0
    if mask_activos.any():
        rep_detalle.loc[mask_activos, "Media_Necesaria_Diaria"] = ((rep_detalle.loc[mask_activos, "Objetivo Mes Corriente"] - rep_detalle.loc[mask_activos, "OPERATIVO"]) / dr_s[mask_activos]).clip(lower=0)

    if rep_detalle["Días Restantes"].sum() == 0:
        total_tendencia = total_neto_operativo
        pct_cumplimiento_obj = pct_avance
    else:
        total_tendencia = float(rep_detalle["Tendencia_Total_Kg"].sum())
        pct_cumplimiento_obj = (total_tendencia / total_objetivo_mes * 100.0) if total_objetivo_mes > 0 else 0.0

    # RENDERIZADO DE MÉTRICAS UTILIZANDO LA UTILIDAD COMPARTIDA
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    with mcol1:
        st.markdown(tarjeta_metrica_html("📦 Arrastre", f"{total_arrastre:,.1f} kg", "#3b82f6", "39px", "21px"), unsafe_allow_html=True)
    with mcol2:
        st.markdown(tarjeta_metrica_html("🚚 Actual", f"{total_actual:,.1f} kg", "#3b82f6", "39px", "21px"), unsafe_allow_html=True)
    with mcol3:
        st.markdown(tarjeta_metrica_html("📊 Neto Operativo", f"{total_neto_operativo:,.1f} kg", "#3b82f6", "39px", "21px"), unsafe_allow_html=True)
    with mcol4:
        st.markdown(tarjeta_metrica_html("📈 % Avance", f"{pct_avance:,.2f}%", "#3b82f6", "39px", "21px"), unsafe_allow_html=True)

    tcol1, tcol2, tcol3 = st.columns(3)
    with tcol1:
        st.markdown(tarjeta_metrica_html("🎯 Objetivo del Mes", f"{total_objetivo_mes:,.1f} kg", "#3b82f6", "39px", "21px"), unsafe_allow_html=True)
    with tcol2:
        st.markdown(tarjeta_metrica_html("📈 Tendencia Kgs", f"{total_tendencia:,.1f} kg", "#ef4444", "39px", "21px"), unsafe_allow_html=True)
    with tcol3:
        st.markdown(tarjeta_metrica_html("🎯 Tendencia %", f"{pct_cumplimiento_obj:,.2f}%", "#3b82f6", "39px", "21px"), unsafe_allow_html=True)
    
    st.divider()

    cols_excepcion = ["CodVendedor", "Nombre", "SUP", "SEGMENTO", "Días Pasados", "Rutas", "Días Restantes"]
    for col in rep_detalle.columns:
        if col not in cols_excepcion and pd.api.types.is_numeric_dtype(rep_detalle[col]):
            rep_detalle[col] = pd.to_numeric(rep_detalle[col], errors="coerce").round(2)

    columnas_ordenadas = [
        "CodVendedor", "Nombre", "SUP", "SEGMENTO", "Objetivo Mes Corriente", "Arrastre", "Actual", 
        "Ultima_Vta", "Penultima_Vta", "OPERATIVO", "Ajuste_Por_Reemp", "Tendencia_Total_Kg", 
        "Cumplimiento_Proyectado_Pct", "Promedio_Diario", "Media_Necesaria_Diaria", "Días Pasados", "Rutas", "Días Restantes"
    ]
    rep_detalle = rep_detalle[columnas_ordenadas]

    if not rep_detalle.empty:
        gb = GridOptionsBuilder.from_dataframe(rep_detalle)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=130)

        cols_numericas = [
            "Objetivo Mes Corriente", "Arrastre", "Actual", "Ultima_Vta", "Penultima_Vta", 
            "OPERATIVO", "Ajuste_Por_Reemp", "Tendencia_Total_Kg", "Promedio_Diario", "Media_Necesaria_Diaria"
        ]
        for col in cols_numericas:
            gb.configure_column(
                col, 
                valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : ''"
            )

        gb.configure_column(
            "Cumplimiento_Proyectado_Pct", 
            headerName="% Cumpl. Proyectado",
            valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '%' : '0.00%'"
        )

        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_options = gb.build()

        AgGrid(
            rep_detalle,
            gridOptions=grid_options,
            height=450,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=False
        )
    else:
        st.info("No se encontraron registros de Kilos con los filtros seleccionados.")

    buffer_kilos = io.BytesIO()
    with pd.ExcelWriter(buffer_kilos, engine="openpyxl") as writer:
        rep_detalle.to_excel(writer, index=False, sheet_name="Avance_Kilos_Segmento")
    buffer_kilos.seek(0)

    st.download_button(
        label="📥 Descargar Avance Kilos a Excel", 
        data=buffer_kilos, 
        file_name=f"Avance_Kilos_{sup_filtro}_{mes_op}_{anio_op}.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        key=f"kilos_frag_btn_dl_{sup_filtro}"
    )

def render_rep_kilos(df_vta, df_rutas, df_ausencias, filtros_globales=None):
    st.subheader("📊 Avance de Kilos por Segmento")

    if filtros_globales is None:
        anio_op = 2026
        mes_op = 9
        sup_filtro = "TODOS"
        dia_venta = "01/09/2026"
        dia_matinal = "02/09/2026"
    else:
        anio_op = int(filtros_globales.get("anio", 2026))
        mes_op = int(filtros_globales.get("mes", 9))
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()
        dia_venta = filtros_globales.get("dia_venta", "01/09/2026")
        dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026")

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
        if not maestro_s.empty and "Mes" in maestro_s.columns:
            ms_per = maestro_s[(ms_per["Mes"].astype(str) == str(mes_op)) & (ms_per["Anio"].astype(str) == str(anio_op))]
            if not ms_per.empty:
                maestro_s = ms_per
    except Exception:
        maestro_s = pd.DataFrame()

    try:
        maestro_cebe = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if not maestro_cebe.empty and "Mes" in maestro_cebe.columns:
            mc_per = maestro_cebe[(mc_per["Mes"].astype(str) == str(mes_op)) & (mc_per["Anio"].astype(str) == str(anio_op))]
            if not mc_per.empty:
                maestro_cebe = mc_per
    except Exception:
        maestro_cebe = pd.DataFrame()

    if maestro_v.empty:
        st.warning("⚠️ No se encontró el Maestro de Vendedores cargado para este período en SQLite. Verifique en la solapa de Parámetros.")
        return

    cache_key_rep = f"_cache_kilos_v47_{sup_filtro}_{anio_op}_{mes_op}_{dia_matinal.replace('/', '')}_{dia_venta.replace('/', '')}"
    if cache_key_rep not in st.session_state:
        df_vta_prep = preparar_datos_ventas_segmento(df_vta, df_ausencias, anio_op, mes_op, dia_matinal)
        reporte_avance = generar_reporte_avance_kilos_segmento(df_vta_prep, df_rutas, maestro_v, maestro_s, maestro_cebe, dia_venta, anio_op, mes_op, sup_filtro)
        st.session_state[cache_key_rep] = (reporte_avance, df_vta_prep)
    else:
        reporte_avance, df_vta_prep = st.session_state[cache_key_rep]

    if "Ajuste_Reemp_Arrastre" not in reporte_avance.columns:
        reporte_avance["Ajuste_Reemp_Arrastre"] = 0.0
    if "Ajuste_Reemp_Actual" not in reporte_avance.columns:
        reporte_avance["Ajuste_Reemp_Actual"] = 0.0
    if "Ajuste_Por_Reemp" not in reporte_avance.columns:
        reporte_avance["Ajuste_Por_Reemp"] = reporte_avance["Ajuste_Reemp_Arrastre"] + reporte_avance["Ajuste_Reemp_Actual"]

    mask_comodines = reporte_avance["CodVendedor"].isin([-999, -998])
    df_comodines_Rows = reporte_avance[mask_comodines].copy()
    reporte_vendedores_puro = reporte_avance[~mask_comodines].copy()

    if sup_filtro != "TODOS":
        reporte_vendedores_puro = reporte_vendedores_puro[reporte_vendedores_puro["SUP"].astype(str).str.strip() == sup_filtro].copy()

    v_dispo = sorted(reporte_vendedores_puro["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    orden_oficial_seg = st.session_state.get(f"_orden_seg_{anio_op}_{mes_op}", [])
    segs_unicos_rep = set(reporte_vendedores_puro["SEGMENTO"].dropna().astype(str).str.strip().unique())
    
    s_dispo = [s for s in orden_oficial_seg if s in segs_unicos_rep]
    for s in segs_unicos_rep:
        if s not in s_dispo:
            s_dispo.append(s)

    render_fragmento_interactivo_kilos(reporte_vendedores_puro, df_comodines_Rows, s_dispo, v_dispo, anio_op, mes_op, sup_filtro, df_vta_prep, dia_matinal)