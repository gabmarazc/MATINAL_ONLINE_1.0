# modules/rep_obj_kilos.py
import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import parsear_fecha_robusta

def generar_distribucion_objetivos_macro(df_vta, maestro_v, maestro_cebe_act, maestro_cebe_ant, maestro_seg, anio_operativo, mes_operativo):
    """
    Calcula la distribución proporcional del objetivo macro de la compañía en Kilos 
    tomando los valores directamente en Kilos (sin multiplicar por 1000) y basándose en la participación histórica global por Marca.
    """
    if maestro_v is None or maestro_v.empty:
        return pd.DataFrame(), []

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

    obj_act_map = {}
    cebe_map = {}
    if maestro_cebe_act is not None and not maestro_cebe_act.empty:
        cm_act = next((c for c in maestro_cebe_act.columns if "marca" in str(c).strip().lower()), maestro_cebe_act.columns[0])
        cc_act = next((c for c in maestro_cebe_act.columns if "cebe" in str(c).strip().lower()), maestro_cebe_act.columns[1] if len(maestro_cebe_act.columns) > 1 else maestro_cebe_act.columns[0])
        co_act = next((c for c in maestro_cebe_act.columns if any(k in str(c).strip().lower() for k in ["obj_tn", "tn", "obj_mes", "objetivo", "obj"])), None)
        
        for _, r in maestro_cebe_act.iterrows():
            m = str(r.get(cm_act, "")).strip().upper()
            c = str(r.get(cc_act, "")).strip()
            val_kg = pd.to_numeric(r.get(co_act, 0.0), errors="coerce") if co_act else 0.0
            if m and m != "NAN":
                # Lectura directa en Kilos (sin factores adicionales de 1000)
                obj_act_map[m] = val_kg if pd.notna(val_kg) else 0.0
                cebe_map[m] = c if c and c != "NAN" else "GLOBAL"

    obj_ant_map = {}
    if maestro_cebe_ant is not None and not maestro_cebe_ant.empty:
        cm_ant = next((c for c in maestro_cebe_ant.columns if "marca" in str(c).strip().lower()), maestro_cebe_ant.columns[0])
        co_ant = next((c for c in maestro_cebe_ant.columns if any(k in str(c).strip().lower() for k in ["obj_tn", "tn", "obj_mes", "objetivo", "obj"])), None)
        
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
        segmentos_validos = {"GOLD Salty", "GOLD Crakers", "SILVER Salty", "SILVER Crakers", "SILVER Cereals"}
        segmentos_orden_lista = ["GOLD Salty", "GOLD Crakers", "SILVER Salty", "SILVER Crakers", "SILVER Cereals"]

    if df_vta is None or df_vta.empty:
        return pd.DataFrame(), segmentos_orden_lista

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
        vta_mes_ant = vta.copy()

    if vta_mes_ant.empty:
        return pd.DataFrame(), segmentos_orden_lista

    col_vend = next((c for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"] if c in vta_mes_ant.columns), None)
    vta_mes_ant["CodVendedor"] = pd.to_numeric(vta_mes_ant[col_vend], errors="coerce").astype("Int64") if col_vend else pd.NA

    col_m = next((c for c in ["Marca", "MARCA", "marca"] if c in vta_mes_ant.columns), None)
    vta_mes_ant["Marca"] = vta_mes_ant[col_m].fillna("").astype(str).str.strip().str.upper() if col_m else "SIN MARCA"

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
            seg = sr if sr else (list(segmentos_validos)[0] if segmentos_validos else "GOLD Salty")
        return seg if seg in segmentos_validos else (list(segmentos_validos)[0] if segmentos_validos else seg)

    vta_mes_ant["SEGMENTO"] = vta_mes_ant.apply(resolver_segmento, axis=1)

    col_kg = next((c for c in ["PesoKg", "PESOKG", "Kilos", "KILOS"] if c in vta_mes_ant.columns), None)
    vta_mes_ant["Kilos"] = pd.to_numeric(vta_mes_ant[col_kg], errors="coerce").fillna(0.0) if col_kg else 0.0

    vta_mes_ant = vta_mes_ant.dropna(subset=["CodVendedor"]).copy()

    if vta_mes_ant.empty:
        df_padron_k = df_padron.copy()
        df_padron_k["_k"] = 1
        df_seg_k = pd.DataFrame({"SEGMENTO": list(segmentos_validos)})
        df_seg_k["_k"] = 1
        df_reporte = df_padron_k.merge(df_seg_k, on="_k").drop(columns="_k")
        df_reporte["Kilos_Mes_Anterior"] = 0.0
        df_reporte["Objetivo_Mes_Anterior_Kg"] = 0.0
        df_reporte["Logro_Anterior_Pct"] = 0.0
        df_reporte["Obj_Sugerido_Kg"] = 0.0
    else:
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

    if segmentos_orden_lista:
        df_reporte["SEGMENTO"] = pd.Categorical(df_reporte["SEGMENTO"], categories=segmentos_orden_lista, ordered=True)

    sort_cols = [c for c in ["Supervisor", "Nombre", "Marca", "SEGMENTO"] if c in df_reporte.columns]
    df_reporte = df_reporte.sort_values(by=sort_cols).reset_index(drop=True)
    df_reporte["SEGMENTO"] = df_reporte["SEGMENTO"].astype(str)

    df_reporte["Anio"] = int(anio_operativo)
    df_reporte["Mes"] = int(mes_operativo)

    columnas_finales = [
        "Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "SEGMENTO", 
        "Kilos_Mes_Anterior", "Objetivo_Mes_Anterior_Kg", "Logro_Anterior_Pct", 
        "Obj_Sugerido_Kg"
    ]
    
    for col in columnas_finales:
        if col not in df_reporte.columns:
            df_reporte[col] = 0.0

    return df_reporte[columnas_finales], segmentos_orden_lista

def render_rep_obj_kilos(df_vta, filtros_globales=None):
    st.subheader("📦 Generador Tentativo de Objetivos por Vendedor y Segmento")

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
            mv_per = maestro_v[
                (maestro_v["Mes"].astype(str).str.strip() == str(mes_op)) & 
                (maestro_v["Anio"].astype(str).str.strip() == str(anio_op))
            ]
            if not mv_per.empty:
                maestro_v = mv_per
    except Exception:
        maestro_v = pd.DataFrame()

    try:
        maestro_seg = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos ORDER BY rowid ASC")
        if not maestro_seg.empty and "Mes" in maestro_seg.columns:
            ms_per = maestro_seg[
                (maestro_seg["Mes"].astype(str).str.strip() == str(mes_op)) & 
                (maestro_seg["Anio"].astype(str).str.strip() == str(anio_op))
            ]
            if not ms_per.empty:
                maestro_seg = ms_per
    except Exception:
        maestro_seg = pd.DataFrame()

    try:
        maestro_cebe_act = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if not maestro_cebe_act.empty and "Mes" in maestro_cebe_act.columns:
            mc_per = maestro_cebe_act[
                (maestro_cebe_act["Mes"].astype(str).str.strip() == str(mes_op)) & 
                (maestro_cebe_act["Anio"].astype(str).str.strip() == str(anio_op))
            ]
            if not mc_per.empty:
                maestro_cebe_act = mc_per
    except Exception:
        maestro_cebe_act = pd.DataFrame()

    try:
        maestro_cebe_ant = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if not maestro_cebe_ant.empty and "Mes" in maestro_cebe_ant.columns:
            mc_ant = maestro_cebe_ant[
                (maestro_cebe_ant["Mes"].astype(str).str.strip() == str(mes_ant_eval)) & 
                (maestro_cebe_ant["Anio"].astype(str).str.strip() == str(anio_ant_eval))
            ]
            if not mc_ant.empty:
                maestro_cebe_ant = mc_ant
    except Exception:
        maestro_cebe_ant = pd.DataFrame()

    if maestro_v.empty:
        st.warning("⚠️ No se encontró el Maestro de Vendedores cargado para este período en la base de datos.")
        return

    cache_key = f"_cache_rep_obj_distribucion_v15_{anio_op}_{mes_op}_{sup_filtro}"
    if cache_key not in st.session_state:
        with st.spinner("Calculando distribución proporcional de objetivos macro en Kilos..."):
            df_base, seg_orden = generar_distribucion_objetivos_macro(df_vta, maestro_v, maestro_cebe_act, maestro_cebe_ant, maestro_seg, anio_op, mes_op)
            st.session_state[cache_key] = (df_base, seg_orden)
    else:
        df_base, seg_orden = st.session_state[cache_key]

    if df_base is None or df_base.empty:
        st.info("No se encontraron registros coincidentes con los maestros oficiales para el período de referencia.")
        return

    df_filtrado = df_base.copy()
    if sup_filtro != "TODOS" and "Supervisor" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Supervisor"].astype(str).str.strip() == sup_filtro].copy()

    df_filtrado["Obj_Sugerido_Kg"] = df_filtrado["Obj_Sugerido_Kg"] * factor_multiplicador

    df_agrupado = df_filtrado.groupby(
        ["Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "SEGMENTO"],
        as_index=False
    ).agg({
        "Kilos_Mes_Anterior": "sum",
        "Objetivo_Mes_Anterior_Kg": "sum",
        "Obj_Sugerido_Kg": "sum"
    })

    df_agrupado["Logro_Anterior_Pct"] = (
        df_agrupado["Kilos_Mes_Anterior"] / df_agrupado["Objetivo_Mes_Anterior_Kg"].replace(0, pd.NA)
    ).mul(100).fillna(0.0)

    if seg_orden:
        df_agrupado["SEGMENTO"] = pd.Categorical(df_agrupado["SEGMENTO"], categories=seg_orden, ordered=True)

    df_agrupado = df_agrupado.sort_values(by=["Supervisor", "Nombre", "SEGMENTO"]).reset_index(drop=True)
    df_agrupado["SEGMENTO"] = df_agrupado["SEGMENTO"].astype(str)

    total_kilos_ant = df_agrupado["Kilos_Mes_Anterior"].sum()
    total_obj_sugerido = df_agrupado["Obj_Sugerido_Kg"].sum()
    
    total_macro_compania = 0.0
    if not maestro_cebe_act.empty:
        co_act = next((c for c in maestro_cebe_act.columns if any(k in str(c).strip().lower() for k in ["obj_tn", "tn", "obj_mes", "objetivo", "obj"])), None)
        if co_act:
            # Lectura directa en Kilos sin factor 1000
            total_macro_compania = pd.to_numeric(maestro_cebe_act[co_act], errors="coerce").sum()

    m1, m2, m3 = st.columns(3)
    m1.metric("📦 Total Kilos Históricos", f"{total_kilos_ant:,.1f} kg")
    m2.metric("🏢 Total Macro Compañía", f"{total_macro_compania:,.1f} kg")
    m3.metric("🎯 Total Objetivo Sugerido", f"{total_obj_sugerido:,.1f} kg")

    if not df_agrupado.empty and "SEGMENTO" in df_agrupado.columns:
        tot_por_seg = df_agrupado.groupby("SEGMENTO")["Obj_Sugerido_Kg"].sum()
        if seg_orden:
            tot_por_seg = tot_por_seg.reindex([s for s in seg_orden if s in tot_por_seg.index])
        
        st.markdown("📌 **Objetivo Sugerido por Segmento:**")
        for seg, val in tot_por_seg.items():
            st.markdown(f"- **{seg}**: {val:,.2f} kg")

    st.divider()

    gb = GridOptionsBuilder.from_dataframe(df_agrupado)
    gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=130, cellStyle={'textAlign': 'center'}, headerClass='centered-header')
    
    gb.configure_column("Anio", headerName="Año", width=80)
    gb.configure_column("Mes", headerName="Mes", width=70)
    gb.configure_column("CodVendedor", headerName="Cód. Vend", width=100)
    gb.configure_column("Nombre", headerName="Vendedor", minWidth=180, cellStyle={'textAlign': 'left'}, headerClass='left-header')
    gb.configure_column("Supervisor", headerName="Supervisor", minWidth=140, cellStyle={'textAlign': 'left'}, headerClass='left-header')
    gb.configure_column("SEGMENTO", headerName="Segmento", minWidth=160, cellStyle={'textAlign': 'left'}, headerClass='left-header')
    
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
        "Obj_Sugerido_Kg", 
        headerName="Obj. Sugerido (Kg)",
        valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'"
    )

    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    grid_options = gb.build()

    st.markdown("""
    <style>
    .ag-header-cell-label {
        justify-content: center !important;
        text-align: center !important;
    }
    .left-header .ag-header-cell-label {
        justify-content: flex-start !important;
        text-align: left !important;
    }
    </style>
    """, unsafe_allow_html=True)

    AgGrid(
        df_agrupado,
        gridOptions=grid_options,
        height=450,
        width="100%",
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        theme="streamlit",
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True
    )

    st.divider()

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_agrupado.to_excel(writer, index=False, sheet_name="Objetivos_Vendedor_Segmento")
    buffer.seek(0)

    st.download_button(
        label="📥 Descargar Propuesta Tentativa a Excel",
        data=buffer,
        file_name=f"Propuesta_Objetivos_{mes_op}_{anio_op}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"btn_dl_propuesta_obj_{mes_op}_{anio_op}"
    )