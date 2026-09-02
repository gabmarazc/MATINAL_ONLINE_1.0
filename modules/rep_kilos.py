import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode

def crear_filtro_excel(label, opciones, key_prefix):
    """Crea un filtro desplegable tipo Excel con opción de 'TODOS' sincronizada de forma reactiva (sin st.form)."""
    all_key = f"{key_prefix}_todos"
    
    if all_key not in st.session_state:
        st.session_state[all_key] = False

    for op in opciones:
        chk_key = f"{key_prefix}_{op}"
        if chk_key not in st.session_state:
            st.session_state[chk_key] = False

    val_todos_actual = st.session_state.get(all_key, False)
    aux_cambio_key = f"{key_prefix}_aux_prev_todos"
    if aux_cambio_key not in st.session_state:
        st.session_state[aux_cambio_key] = val_todos_actual

    if st.session_state[aux_cambio_key] != val_todos_actual:
        st.session_state[aux_cambio_key] = val_todos_actual
        for op in opciones:
            st.session_state[f"{key_prefix}_{op}"] = val_todos_actual

    with st.popover(f"{label}: ...", width="stretch"):
        st.checkbox("TODOS", key=all_key)
        st.divider()
        
        for op in opciones:
            st.checkbox(str(op), key=f"{key_prefix}_{op}")

    todos_estan_marcados = all(st.session_state.get(f"{key_prefix}_{op}", False) for op in opciones)
    if todos_estan_marcados and opciones and not st.session_state.get(all_key, False):
        st.session_state[all_key] = True
        st.session_state[aux_cambio_key] = True

    seleccionados = [op for op in opciones if st.session_state.get(f"{key_prefix}_{op}", False)]
    return seleccionados

def generar_reporte_avance_kilos_segmento(df_vtas_operativo, df_vtas_limpias, vendedores, segmentos, df_rutas_operativas, dia_venta, anio_operativo, mes_operativo):
    vendedores_reporte = pd.DataFrame()
    vendedores_reporte["CodVend"] = pd.to_numeric(vendedores["CodVend"], errors="coerce").astype("Int64")
    vendedores_reporte["Nombre"] = vendedores["Nombre"].fillna("").astype(str).str.strip()
    vendedores_reporte["SUP"] = vendedores["SUP"].fillna("").astype(str).str.strip()
    
    rutas_maestro = pd.DataFrame()
    rutas_maestro["CodVend"] = pd.to_numeric(vendedores["CodVend"], errors="coerce").astype("Int64")
    rutas_maestro["Rutas"] = pd.to_numeric(vendedores["Rutas"], errors="coerce").fillna(0).astype("Int64")
    
    vendedores_reporte = vendedores_reporte.merge(rutas_maestro, on="CodVend", how="left")
    
    segmentos_reporte = pd.DataFrame()
    segmentos_reporte["SEGMENTO"] = segmentos["SEGMENTO"].fillna("").astype(str).str.strip()
    segmentos_reporte = segmentos_reporte[segmentos_reporte["SEGMENTO"].ne("") & segmentos_reporte["SEGMENTO"].ne("nan")].drop_duplicates()
    
    vendedores_reporte["_k"], segmentos_reporte["_k"] = 1, 1
    matriz = vendedores_reporte.merge(segmentos_reporte, on="_k").drop(columns="_k")
    
    kilos = df_vtas_operativo.groupby(["CodVendedorOperativo", "SEGMENTO", "Periodo"], dropna=False)["PesoKg"].sum().reset_index().rename(columns={"CodVendedorOperativo": "CodVend"})
    kilos["CodVend"] = pd.to_numeric(kilos["CodVend"], errors="coerce").astype("Int64")
    kilos["SEGMENTO"] = kilos["SEGMENTO"].fillna("").astype(str).str.strip()
    
    kilos_pivot = kilos.pivot_table(index=["CodVend", "SEGMENTO"], columns="Periodo", values="PesoKg", aggfunc="sum", fill_value=0).reset_index()
    kilos_pivot.columns.name = None
    
    for periodo in ["Arrastre", "Actual"]:
        if periodo not in kilos_pivot.columns: kilos_pivot[periodo] = 0.0
        
    reporte = matriz.merge(kilos_pivot[["CodVend", "SEGMENTO", "Arrastre", "Actual"]], on=["CodVend", "SEGMENTO"], how="left")
    reporte[["Arrastre", "Actual"]] = reporte[["Arrastre", "Actual"]].fillna(0.0)
    
    rutas = df_rutas_operativas.copy()
    rutas["Fecha"] = pd.to_datetime(rutas["Fecha"], errors="coerce")
    rutas["codven"] = pd.to_numeric(rutas["codven"], errors="coerce").astype("Int64")
    
    dias_pasados = rutas[rutas["Fecha"].le(pd.Timestamp(dia_venta))].groupby("codven")["Fecha"].nunique()
    dias_totales = rutas.groupby("codven")["Fecha"].nunique()
    
    reporte = reporte.merge(dias_pasados.rename("Días Pasados"), left_on="CodVend", right_index=True, how="left").merge(dias_totales.rename("Días Totales"), left_on="CodVend", right_index=True, how="left")
    reporte["Días Pasados"] = reporte["Días Pasados"].fillna(0).astype("Int64")
    reporte["Días Totales"] = reporte["Días Totales"].fillna(0).astype("Int64")
    reporte["Rutas"] = reporte["Rutas"].fillna(0).astype("Int64")
    reporte["Días Restantes"] = (reporte["Días Totales"] - reporte["Días Pasados"] - reporte["Rutas"]).clip(lower=0).astype("Int64")
    
    historial = df_vtas_limpias[df_vtas_limpias["FechaCarga"].dt.year.eq(anio_operativo) & df_vtas_limpias["FechaCarga"].dt.month.eq(mes_operativo - 1) & df_vtas_limpias["SEGMENTO"].notna()].copy()
    kilos_historial = historial.groupby(["CodVendedor", "SEGMENTO"])["PesoKg"].sum().reset_index().rename(columns={"PesoKg": "Kilos Historial"})
    kilos_historial["Kilos Totales Segmento"] = kilos_historial.groupby("SEGMENTO")["Kilos Historial"].transform("sum")
    kilos_historial["Participación"] = (kilos_historial["Kilos Historial"] / kilos_historial["Kilos Totales Segmento"].replace(0, pd.NA)).fillna(0.0)
    
    objetivos = pd.DataFrame()
    objetivos["SEGMENTO"] = segmentos["SEGMENTO"].fillna("").astype(str).str.strip()
    objetivos["OBJ"] = pd.to_numeric(segmentos["OBJ"], errors="coerce").fillna(0.0)
    objetivos["Porc_Requerido"] = pd.to_numeric(segmentos["Porc_Requerido"], errors="coerce").fillna(0.0)
    objetivos = objetivos.drop_duplicates("SEGMENTO")
    
    kilos_historial = kilos_historial.merge(objetivos, on="SEGMENTO", how="left")
    kilos_historial["Objetivo Mes Corriente"] = kilos_historial["Participación"] * kilos_historial["OBJ"] * kilos_historial["Porc_Requerido"]
    
    reporte = reporte.merge(kilos_historial[["CodVendedor", "SEGMENTO", "Objetivo Mes Corriente"]], left_on=["CodVend", "SEGMENTO"], right_on=["CodVendedor", "SEGMENTO"], how="left").drop(columns="CodVendedor")
    reporte["Objetivo Mes Corriente"] = reporte["Objetivo Mes Corriente"].fillna(0.0)
    
    reemplazos = df_vtas_operativo[df_vtas_operativo["CodVendedorOperativo"].ne(df_vtas_operativo["CodVendedor"])][["CodVendedor", "CodVendedorOperativo", "SEGMENTO", "PesoKg"]].copy()
    
    movimientos_titular = reemplazos[["CodVendedor", "SEGMENTO", "PesoKg"]].rename(columns={"CodVendedor": "CodVend"})
    movimientos_titular["Ajuste_Por_Reemp"] = -movimientos_titular.pop("PesoKg")
    
    movimientos_reemplazo = reemplazos[["CodVendedorOperativo", "SEGMENTO", "PesoKg"]].rename(columns={"CodVendedorOperativo": "CodVend"})
    movimientos_reemplazo["Ajuste_Por_Reemp"] = movimientos_reemplazo.pop("PesoKg")
    
    ajustes = pd.concat([movimientos_titular, movimientos_reemplazo], ignore_index=True).groupby(["CodVend", "SEGMENTO"])["Ajuste_Por_Reemp"].sum().reset_index()
    reporte = reporte.merge(ajustes, on=["CodVend", "SEGMENTO"], how="left").rename(columns={"CodVend": "CodVendedor"})
    reporte["Ajuste_Por_Reemp"] = reporte["Ajuste_Por_Reemp"].fillna(0.0)
    
    return reporte

def dibujar_pestaña_kilos(reporte_avance, supervisores_seleccionados, df_vtas_limpias, parametros_por_nombre):
    st.subheader("Avance de Kilos por Segmento")
    st.markdown("Seguimiento y proyección del avance de kilos por preventista y segmento.")
    
    sup_str = [str(s).strip() for s in supervisores_seleccionados]
    reporte_avance_filtrado = reporte_avance[
        reporte_avance["SUP"].astype(str).str.strip().isin(sup_str)
    ].copy()
    
    v_dispo_kilos = sorted(reporte_avance_filtrado["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    segmentos_disponibles = sorted(reporte_avance_filtrado["SEGMENTO"].dropna().astype(str).str.strip().unique().tolist())

    for v in v_dispo_kilos:
        k = f"kilos_vend_{v}"
        if k in st.session_state and not st.session_state[k]:
            pass
    for seg in segmentos_disponibles:
        k = f"kilos_seg_{seg}"
        if k in st.session_state and not st.session_state[k]:
            pass

    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        v_selec_kilos = crear_filtro_excel("Vendedor", v_dispo_kilos, "kilos_vend")
    with col_f2:
        segmentos_seleccionados = crear_filtro_excel("Segmento", segmentos_disponibles, "kilos_seg")

    if not v_selec_kilos:
        v_selec_kilos = v_dispo_kilos
    if not segmentos_seleccionados:
        segmentos_seleccionados = segmentos_disponibles
    
    reporte_avance_filtrado = reporte_avance_filtrado[
        reporte_avance_filtrado["Nombre"].astype(str).str.strip().isin(v_selec_kilos) &
        reporte_avance_filtrado["SEGMENTO"].isin(segmentos_seleccionados)
    ].copy()
    
    total_kilos_operativos = float(reporte_avance_filtrado["Actual"].sum() + reporte_avance_filtrado["Arrastre"].sum())
    
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        st.metric(label="📊 Total Kilos Operativos", value=f"{total_kilos_operativos:,.1f} kg")
    with col_m2:
        def formatear_detalle(selec, total_disp):
            if not selec:
                return "NINGUNO"
            if len(selec) == len(total_disp):
                return "TODOS"
            return ", ".join(map(str, selec))

        vend_res = formatear_detalle(v_selec_kilos, v_dispo_kilos)
        seg_res = formatear_detalle(segmentos_seleccionados, segmentos_disponibles)
        
        st.markdown(
            f"""
            <div style="background-color: #1e293b; padding: 10px; border-radius: 6px; font-size: 13px; border: 1px solid #475569; color: #f8fafc;">
                <b style="color: #38bdf8;">📋 Resumen de Filtros Aplicados:</b><br>
                • <b>Vendedor:</b> <span style="color: #e2e8f0;">{vend_res}</span><br>
                • <b>Segmento:</b> <span style="color: #e2e8f0;">{seg_res}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()
    
    reporte_detalle = reporte_avance_filtrado[
        ["CodVendedor", "Nombre", "SUP", "SEGMENTO", "Objetivo Mes Corriente", "Arrastre", "Actual", "Ajuste_Por_Reemp", "Días Pasados", "Rutas", "Días Restantes"]
    ].copy()
    
    fecha_matinal = pd.to_datetime(parametros_por_nombre["dia matinal"], dayfirst=True, errors="coerce")
    
    ultima_vta = df_vtas_limpias[
        df_vtas_limpias["FechaCarga"].eq(fecha_matinal - pd.Timedelta(days=7))
    ].groupby(["CodVendedor", "SEGMENTO"])["PesoKg"].sum().reset_index().rename(columns={"PesoKg": "Ultima_Vta"})
    
    penultima_vta = df_vtas_limpias[
        df_vtas_limpias["FechaCarga"].eq(fecha_matinal - pd.Timedelta(days=14))
    ].groupby(["CodVendedor", "SEGMENTO"])["PesoKg"].sum().reset_index().rename(columns={"PesoKg": "Penultima_Vta"})
    
    reporte_detalle = reporte_detalle.merge(ultima_vta, on=["CodVendedor", "SEGMENTO"], how="left").merge(penultima_vta, on=["CodVendedor", "SEGMENTO"], how="left")
    reporte_detalle[["Ultima_Vta", "Penultima_Vta"]] = reporte_detalle[["Ultima_Vta", "Penultima_Vta"]].fillna(0.0)
    reporte_detalle["OPERATIVO"] = reporte_detalle["Arrastre"] + reporte_detalle["Actual"]
    
    dp_s = reporte_detalle["Días Pasados"].astype(float).replace(0, 1.0)
    dr_s = reporte_detalle["Días Restantes"].astype(float).replace(0, 1.0)
    
    p_diario = (reporte_detalle["OPERATIVO"] - reporte_detalle["Ajuste_Por_Reemp"]) / dp_s
    reporte_detalle["Tendencia_Total_Kg"] = (p_diario * dr_s) + reporte_detalle["OPERATIVO"]
    reporte_detalle["Cumplimiento_Proyectado_Pct"] = ((reporte_detalle["Tendencia_Total_Kg"] - reporte_detalle["Ajuste_Por_Reemp"]) / reporte_detalle["Objetivo Mes Corriente"].replace(0, pd.NA)).mul(100).fillna(0.0)
    reporte_detalle["Promedio_Diario"] = p_diario
    reporte_detalle["Media_Necesaria_Diaria"] = ((reporte_detalle["Objetivo Mes Corriente"] - reporte_detalle["OPERATIVO"] + reporte_detalle["Ajuste_Por_Reemp"]) / dr_s).clip(lower=0)
    
    columnas_finales = [
        "CodVendedor", "Nombre", "SUP", "SEGMENTO", "Objetivo Mes Corriente", "Arrastre", "Actual", 
        "Ultima_Vta", "Penultima_Vta", "OPERATIVO", "Ajuste_Por_Reemp", "Días Pasados", "Rutas", 
        "Días Restantes", "Tendencia_Total_Kg", "Cumplimiento_Proyectado_Pct", "Promedio_Diario", "Media_Necesaria_Diaria"
    ]
    
    df_render = reporte_detalle[[c for c in columnas_finales if c in reporte_detalle.columns]].copy()
    
    if not df_render.empty:
        gb = GridOptionsBuilder.from_dataframe(df_render)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=130)
        gb.configure_column("CodVendedor", headerName="Cód. Vend", width=100, valueFormatter="x != null ? Number(x).toFixed(0) : ''")
        gb.configure_column("Nombre", headerName="Preventista", minWidth=180)
        gb.configure_column("SUP", headerName="SUP", width=80)
        gb.configure_column("SEGMENTO", headerName="Segmento", minWidth=160)
        gb.configure_column("Objetivo Mes Corriente", headerName="Objetivo", width=110, valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 1, maximumFractionDigits: 1}) : '0.0'")
        gb.configure_column("Arrastre", headerName="Arrastre", width=100, valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 1, maximumFractionDigits: 1}) : '0.0'")
        gb.configure_column("Actual", headerName="Actual", width=100, valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 1, maximumFractionDigits: 1}) : '0.0'")
        gb.configure_column("OPERATIVO", headerName="Operativo", width=110, valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 1, maximumFractionDigits: 1}) : '0.0'")
        gb.configure_column("Tendencia_Total_Kg", headerName="Tendencia Kg", width=120, valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 1, maximumFractionDigits: 1}) : '0.0'")
        gb.configure_column("Cumplimiento_Proyectado_Pct", headerName="% Proyectado", width=130, valueFormatter="x != null ? Number(x).toFixed(2) + '%' : '0.00%'")
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        
        grid_options = gb.build()
        AgGrid(
            df_render,
            gridOptions=grid_options,
            height=420,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=True
        )
    else:
        st.info("No se encontraron registros con los filtros seleccionados.")
        
    buffer_kilos = io.BytesIO()
    with pd.ExcelWriter(buffer_kilos, engine="openpyxl") as writer:
        df_render.to_excel(writer, index=False, sheet_name="Avance_Kilos_Segmento")
    buffer_kilos.seek(0)
    
    st.download_button(
        label="📥 Descargar Avance de Kilos a Excel", 
        data=buffer_kilos, 
        file_name="Avance_Kilos_Segmento.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        key="kilos_btn_dl"
    )