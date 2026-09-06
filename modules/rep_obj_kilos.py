# modules/rep_obj_kilos.py
import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db

def parsear_fecha_robusta(serie):
    """Estandariza parseo de fechas considerando formatos ISO, DD/MM/YYYY y genérico sin advertencias."""
    if serie is None or (isinstance(serie, pd.Series) and serie.empty):
        return pd.Series(dtype="datetime64[ns]")
    if not isinstance(serie, pd.Series):
        serie = pd.Series([serie])
    s = serie.astype(str).str.strip().str.replace(" 00:00:00", "", regex=False)
    
    dt_iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    dt_lat = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    dt_gen = pd.to_datetime(s, errors="coerce")
    
    return dt_iso.combine_first(dt_lat).combine_first(dt_gen)

def generar_distribucion_objetivos_macro(df_vta, maestro_v, maestro_cebe_act, maestro_cebe_ant, maestro_seg, anio_operativo, mes_operativo):
    """
    Calcula la distribución proporcional del objetivo macro de la compañía en Kilos 
    tomando los valores directamente en Kilos y basándose en la participación histórica global por Marca.
    """
    if maestro_v is None or maestro_v.empty:
        return pd.DataFrame()

    col_cod_v = "Codigo_Vendedor" if "Codigo_Vendedor" in maestro_v.columns else maestro_v.columns[0]
    col_nom_v = "Nombre_Vendedor" if "Nombre_Vendedor" in maestro_v.columns else maestro_v.columns[1]
    col_sup_v = "Supervisor" if "Supervisor" in maestro_v.columns else (maestro_v.columns[2] if len(maestro_v.columns) > 2 else maestro_v.columns[0])

    df_padron = maestro_v[[col_cod_v, col_nom_v, col_sup_v]].copy()
    df_padron.columns = ["CodVendedor", "Nombre", "Supervisor"]
    
    df_padron["CodVendedor"] = pd.to_numeric(df_padron["CodVendedor"], errors="coerce").astype("Int64")
    df_padron["Nombre"] = df_padron["Nombre"].fillna("").astype(str).str.strip()
    df_padron["Supervisor"] = df_padron["Supervisor"].fillna("SIN SUPERVISOR").astype(str).str.strip()
    df_padron = df_padron.dropna(subset=["CodVendedor"]).drop_duplicates(subset=["CodVendedor"])

    if mes_operativo == 1:
        mes_ant = 12
        anio_ant = anio_operativo - 1
    else:
        mes_ant = mes_operativo - 1
        anio_ant = anio_operativo

    # 1. Extraer objetivos macro del mes actual (maestro_cebe_act) directamente en Kilos
    obj_act_map = {}
    cebe_map = {}
    if maestro_cebe_act is not None and not maestro_cebe_act.empty:
        cm_act = next((c for c in maestro_cebe_act.columns if "marca" in str(c).strip().lower()), maestro_cebe_act.columns[0])
        cc_act = next((c for c in maestro_cebe_act.columns if "cebe" in str(c).strip().lower()), maestro_cebe_act.columns[1])
        co_act = next((c for c in maestro_cebe_act.columns if "obj_tn" in str(c).strip().lower() or "tn" in str(c).strip().lower() or "obj" in str(c).strip().lower()), None)
        
        for _, r in maestro_cebe_act.iterrows():
            m = str(r.get(cm_act, "")).strip().upper()
            c = str(r.get(cc_act, "")).strip()
            val_kg = pd.to_numeric(r.get(co_act, 0.0), errors="coerce") if co_act else 0.0
            if m and m != "NAN":
                obj_act_map[m] = val_kg if pd.notna(val_kg) else 0.0
                cebe_map[m] = c if c and c != "NAN" else "GLOBAL"

    # 2. Extraer objetivos macro del mes anterior (maestro_cebe_ant) directamente en Kilos
    obj_ant_map = {}
    if maestro_cebe_ant is not None and not maestro_cebe_ant.empty:
        cm_ant = next((c for c in maestro_cebe_ant.columns if "marca" in str(c).strip().lower()), maestro_cebe_ant.columns[0])
        co_ant = next((c for c in maestro_cebe_ant.columns if "obj_tn" in str(c).strip().lower() or "tn" in str(c).strip().lower() or "obj" in str(c).strip().lower()), None)
        
        for _, r in maestro_cebe_ant.iterrows():
            m = str(r.get(cm_ant, "")).strip().upper()
            val_kg = pd.to_numeric(r.get(co_ant, 0.0), errors="coerce") if co_ant else 0.0
            if m and m != "NAN":
                obj_ant_map[m] = val_kg if pd.notna(val_kg) else 0.0

    segmentos_orden_lista = []
    segmentos_validos = set()
    if maestro_seg is not None and not maestro_seg.empty:
        cs_seg = next((c for c in maestro_seg.columns if "segmento" in str(c).strip().lower()), maestro_seg.columns[0])
        for _, r in maestro_seg.iterrows():
            seg = str(r.get(cs_seg, "")).strip()
            if seg and seg.lower() != "nan":
                segmentos_validos.add(seg)
                if seg not in segmentos_orden_lista:
                    segmentos_orden_lista.append(seg)

    if not segmentos_validos:
        segmentos_validos = {"GOLD", "SILVER"}
        segmentos_orden_lista = ["GOLD", "SILVER"]

    if df_vta is None or df_vta.empty:
        return pd.DataFrame()

    vta = df_vta.copy()
    
    if "TipoDeVenta" in vta.columns:
        tipos_excluidos = ["Comodato Devolución", "Comodato Ficticio", "Comodato Ficticio Devolución", "Comodato Préstamo"]
        vta = vta[~vta["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)]

    if "Proveedor" in vta.columns:
        vta = vta[vta["Proveedor"].fillna("").astype(str).str.strip().str.upper().str.contains("PEPSICO", na=False)]

    if "Subramo" in vta.columns:
        subramo_clean = vta["Subramo"].fillna("").astype(str).str.strip().str.upper()
        vta = vta[~subramo_clean.isin(["EMPLOYEES", "EMPLEADOS"])]

    if "FechaEntrega" in vta.columns:
        vta["FechaEntrega_dt"] = parsear_fecha_robusta(vta["FechaEntrega"])
    else:
        vta["FechaEntrega_dt"] = pd.NaT

    vta_mes_ant = vta[
        (vta["FechaEntrega_dt"].dt.year == int(anio_ant)) & 
        (vta["FechaEntrega_dt"].dt.month == int(mes_ant))
    ].copy()

    if vta_mes_ant.empty:
        return pd.DataFrame()

    col_vend = next((c for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"] if c in vta_mes_ant.columns), None)
    vta_mes_ant["CodVendedor"] = pd.to_numeric(vta_mes_ant[col_vend], errors="coerce").astype("Int64") if col_vend else pd.NA

    col_m = next((c for c in ["Marca", "MARCA", "marca"] if c in vta_mes_ant.columns), None)
    vta_mes_ant["Marca"] = vta_mes_ant[col_m].fillna("").astype(str).str.strip().str.upper() if col_m else ""

    col_rent = "SegmentoRentabilidad" if "SegmentoRentabilidad" in vta_mes_ant.columns else None
    col_rubro = "Rubro" if "Rubro" in vta_mes_ant.columns else None

    def resolver_segmento(row):
        sr = str(row.get(col_rent, "")).strip().title() if col_rent else ""
        rubro = str(row.get(col_rubro, "")).strip() if col_rubro else ""
        if sr in ["Platinum", "Gold"]:
            seg = f"GOLD {rubro}".strip()
        elif sr in ["Silver", "Bronze"]:
            seg = f"SILVER {rubro}".strip()
        else:
            seg = sr
        return seg if seg in segmentos_validos else None

    vta_mes_ant["SEGMENTO"] = vta_mes_ant.apply(resolver_segmento, axis=1)

    col_kg = next((c for c in ["PesoKg", "PESOKG", "Kilos", "KILOS"] if c in vta_mes_ant.columns), None)
    vta_mes_ant["Kilos"] = pd.to_numeric(vta_mes_ant[col_kg], errors="coerce").fillna(0.0) if col_kg else 0.0

    marcas_validas = set(obj_act_map.keys()) | set(obj_ant_map.keys())

    vta_mes_ant = vta_mes_ant[
        vta_mes_ant["Marca"].isin(marcas_validas) & 
        vta_mes_ant["SEGMENTO"].isin(segmentos_validos) &
        vta_mes_ant["CodVendedor"].notna()
    ].copy()

    if vta_mes_ant.empty:
        return pd.DataFrame()

    vta_agrup = vta_mes_ant.groupby(
        ["CodVendedor", "Marca", "SEGMENTO"], 
        as_index=False
    )["Kilos"].sum().rename(columns={"Kilos": "Kilos_Mes_Anterior"})

    df_reporte = df_padron.merge(vta_agrup, on="CodVendedor", how="inner")
    df_reporte["CEBE"] = df_reporte["Marca"].map(cebe_map).fillna("GLOBAL")
    df_reporte["Obj_Macro_Marca_Kg"] = df_reporte["Marca"].map(obj_act_map).fillna(0.0)

    df_reporte["Total_Kilos_Marca"] = df_reporte.groupby("Marca")["Kilos_Mes_Anterior"].transform("sum")
    df_reporte["Participacion_Pct"] = (df_reporte["Kilos_Mes_Anterior"] / df_reporte["Total_Kilos_Marca"].replace(0, pd.NA)).fillna(0.0)

    obj_ant_ser = df_reporte["Marca"].map(obj_ant_map).fillna(0.0)
    df_reporte["Objetivo_Mes_Anterior_Kg"] = df_reporte["Participacion_Pct"] * obj_ant_ser

    df_reporte["Logro_Anterior_Pct"] = (df_reporte["Kilos_Mes_Anterior"] / df_reporte["Objetivo_Mes_Anterior_Kg"].replace(0, pd.NA)).mul(100).fillna(0.0)
    df_reporte["Obj_Sugerido_Kg"] = df_reporte["Participacion_Pct"] * df_reporte["Obj_Macro_Marca_Kg"]

    df_reporte = df_reporte.drop(columns=["Total_Kilos_Marca"], errors="ignore")
    
    # Ordenar estrictamente según el orden definido en el padrón de segmentos (`maestro_segmentos`)
    if segmentos_orden_lista:
        df_reporte["SEGMENTO"] = pd.Categorical(df_reporte["SEGMENTO"], categories=segmentos_orden_lista, ordered=True)

    df_reporte = df_reporte.sort_values(by=["Supervisor", "Nombre", "Marca", "SEGMENTO"]).reset_index(drop=True)
    df_reporte["SEGMENTO"] = df_reporte["SEGMENTO"].astype(str)

    columnas_finales = [
        "CodVendedor", "Nombre", "Supervisor", "Marca", "CEBE", "SEGMENTO", 
        "Kilos_Mes_Anterior", "Objetivo_Mes_Anterior_Kg", "Logro_Anterior_Pct", 
        "Obj_Macro_Marca_Kg", "Obj_Sugerido_Kg"
    ]
    return df_reporte[columnas_finales], segmentos_orden_lista

def render_rep_obj_kilos(df_vta, filtros_globales=None):
    st.subheader("📦 Generador Tentativo de Objetivos")

    if filtros_globales is None:
        anio_op = 2026
        mes_op = 9
        sup_filtro = "TODOS"
    else:
        anio_op = int(filtros_globales.get("anio", 2026))
        mes_op = int(filtros_globales.get("mes", 9))
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()

    mes_ant_eval = 12 if mes_op == 1 else mes_op - 1
    anio_ant_eval = anio_op - 1 if mes_op == 1 else anio_op
    
    st.markdown(f"**Período Operativo:** {mes_op:02d}/{anio_op} | **Referencia Histórica:** {mes_ant_eval:02d}/{anio_ant_eval}")

    coef_opciones = list(range(100, 111))
    coef_sel = st.selectbox(
        "📈 Coeficiente de Ajuste de Objetivo (%)",
        options=coef_opciones,
        format_func=lambda x: f"{x}%",
        index=0,
        key="sel_coef_ajuste_obj"
    )
    factor_multiplicador = coef_sel / 100.0

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        if not maestro_v.empty and "Mes" in maestro_v.columns:
            mv_per = maestro_v[(maestro_v["Mes"].astype(str) == str(mes_op)) & (maestro_v["Anio"].astype(str) == str(anio_op))]
            if not mv_per.empty:
                maestro_v = mv_per
    except Exception:
        maestro_v = pd.DataFrame()

    try:
        maestro_seg = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos")
        if not maestro_seg.empty and "Mes" in maestro_seg.columns:
            ms_per = maestro_seg[(maestro_seg["Mes"].astype(str) == str(mes_op)) & (maestro_seg["Anio"].astype(str) == str(anio_op))]
            if not ms_per.empty:
                maestro_seg = ms_per
    except Exception:
        maestro_seg = pd.DataFrame()

    try:
        maestro_cebe_act = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if not maestro_cebe_act.empty and "Mes" in maestro_cebe_act.columns:
            mc_per = maestro_cebe_act[(maestro_cebe_act["Mes"].astype(str) == str(mes_op)) & (maestro_cebe_act["Anio"].astype(str) == str(anio_op))]
            if not mc_per.empty:
                maestro_cebe_act = mc_per
    except Exception:
        maestro_cebe_act = pd.DataFrame()

    try:
        maestro_cebe_ant = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if not maestro_cebe_ant.empty and "Mes" in maestro_cebe_ant.columns:
            mc_ant = maestro_cebe_ant[(maestro_cebe_ant["Mes"].astype(str) == str(mes_ant_eval)) & (maestro_cebe_ant["Anio"].astype(str) == str(anio_ant_eval))]
            if not mc_ant.empty:
                maestro_cebe_ant = mc_ant
    except Exception:
        maestro_cebe_ant = pd.DataFrame()

    if maestro_v.empty:
        st.warning("⚠️ No se encontró el Maestro de Vendedores cargado para este período en la base de datos.")
        return

    cache_key = f"_cache_rep_obj_distribucion_v10_{anio_op}_{mes_op}_{sup_filtro}"
    if cache_key not in st.session_state:
        with st.spinner("Calculando distribución proporcional de objetivos macro en Kilos..."):
            df_base, seg_orden = generar_distribucion_objetivos_macro(df_vta, maestro_v, maestro_cebe_act, maestro_cebe_ant, maestro_seg, anio_op, mes_op)
            st.session_state[cache_key] = (df_base, seg_orden)
    else:
        df_base, seg_orden = st.session_state[cache_key]

    if df_base is None or df_base.empty:
        st.info("No se encontraron registros coincidentes con los maestros oficiales para el período de referencia.")
        return

    if "Obj_Macro_Marca_Kg" not in df_base.columns:
        df_base, seg_orden = generar_distribucion_objetivos_macro(df_vta, maestro_v, maestro_cebe_act, maestro_cebe_ant, maestro_seg, anio_op, mes_op)
        st.session_state[cache_key] = (df_base, seg_orden)

    df_filtrado = df_base.copy()
    if sup_filtro != "TODOS" and "Supervisor" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Supervisor"].astype(str).str.strip() == sup_filtro].copy()

    df_filtrado["Obj_Sugerido_Kg"] = df_filtrado["Obj_Sugerido_Kg"] * factor_multiplicador

    total_kilos_ant = df_filtrado["Kilos_Mes_Anterior"].sum() if "Kilos_Mes_Anterior" in df_filtrado.columns else 0.0
    total_obj_sugerido = df_filtrado["Obj_Sugerido_Kg"].sum() if "Obj_Sugerido_Kg" in df_filtrado.columns else 0.0
    total_macro_compania = df_filtrado[["Marca", "Obj_Macro_Marca_Kg"]].drop_duplicates()["Obj_Macro_Marca_Kg"].sum() if "Obj_Macro_Marca_Kg" in df_filtrado.columns and "Marca" in df_filtrado.columns else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric("📦 Total Kilos Históricos", f"{total_kilos_ant:,.1f} kg")
    m2.metric("🏢 Total Macro Compañía", f"{total_macro_compania:,.1f} kg")
    m3.metric("🎯 Total Objetivo Sugerido", f"{total_obj_sugerido:,.1f} kg")

    if not df_filtrado.empty and "SEGMENTO" in df_filtrado.columns:
        tot_por_seg = df_filtrado.groupby("SEGMENTO")["Obj_Sugerido_Kg"].sum()
        if seg_orden:
            tot_por_seg = tot_por_seg.reindex([s for s in seg_orden if s in tot_por_seg.index])
        
        st.markdown("📌 **Objetivo Sugerido por Segmento:**")
        for seg, val in tot_por_seg.items():
            st.markdown(f"- **{seg}**: {val:,.2f} kg")

    st.divider()

    gb = GridOptionsBuilder.from_dataframe(df_filtrado)
    gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=130)
    
    gb.configure_column("CodVendedor", headerName="Cód. Vend", width=100)
    gb.configure_column("Nombre", headerName="Vendedor", width=180)
    gb.configure_column("Supervisor", headerName="Supervisor", width=140)
    gb.configure_column("Marca", headerName="Marca", width=150)
    gb.configure_column("CEBE", headerName="CEBE", width=140)
    gb.configure_column("SEGMENTO", headerName="Segmento", width=160, rowGroup=True)
    gb.configure_column(
        "Kilos_Mes_Anterior", 
        headerName="Kilos Mes Ant.",
        valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'"
    )
    gb.configure_column(
        "Objetivo_Mes_Anterior_Kg", 
        headerName="Obj. Mes Ant. (Kg)",
        valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'"
    )
    gb.configure_column(
        "Logro_Anterior_Pct", 
        headerName="% Logro Ant.",
        valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '%' : '0.00%'"
    )
    gb.configure_column(
        "Obj_Macro_Marca_Kg", 
        headerName="Obj. Macro Marca (Kg)",
        valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'"
    )
    gb.configure_column(
        "Obj_Sugerido_Kg", 
        headerName="Obj. Sugerido (Kg)",
        valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'"
    )

    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    grid_options = gb.build()

    AgGrid(
        df_filtrado,
        gridOptions=grid_options,
        height=450,
        width="100%",
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        theme="streamlit",
        fit_columns_on_grid_load=False
    )

    st.divider()

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_filtrado.to_excel(writer, index=False, sheet_name="Propuesta_Objetivos")
    buffer.seek(0)

    st.download_button(
        label="📥 Descargar Propuesta Tentativa a Excel",
        data=buffer,
        file_name=f"Propuesta_Objetivos_{mes_op}_{anio_op}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"btn_dl_propuesta_obj_{anio_op}_{mes_op}"
    )