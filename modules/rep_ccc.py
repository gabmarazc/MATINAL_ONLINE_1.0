#[cite: 5]
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

@st.cache_data
def generar_reporte_ccc_taxonomia(df_vtas_limpias, df_universo, vendedores, hoja_ccc_param):
    """Función cacheada para procesar y calcular el avance de CCC por taxonomía."""
    hoja_ccc = hoja_ccc_param.copy()
    hoja_ccc.columns = hoja_ccc.columns.astype(str).str.strip()
    rename_metas = {}
    for c in hoja_ccc.columns:
        if str(c).lower() in ["obj", "objetivo", "obj_ccc", "obj_pepsico", "kilos", "cantidad"]:
            rename_metas[c] = "OBJ_CCC"
        if str(c).lower() in ["taxonomia", "taxonomía", "categoria", "categoría"]:
            rename_metas[c] = "Taxonomia"
    hoja_ccc = hoja_ccc.rename(columns=rename_metas)
    hoja_ccc["Taxonomia"] = hoja_ccc["Taxonomia"].astype(str).str.strip().str.upper()
    hoja_ccc["OBJ_CCC"] = pd.to_numeric(hoja_ccc["OBJ_CCC"], errors="coerce").fillna(0.0)
    hoja_ccc = hoja_ccc[["Taxonomia", "OBJ_CCC"]].drop_duplicates("Taxonomia")
    
    ventas = df_vtas_limpias.copy() if df_vtas_limpias is not None else pd.DataFrame()
    if not ventas.empty:
        if "CodVendedorOperativo" in ventas.columns: 
            ventas["CodVendedor"] = ventas["CodVendedorOperativo"]
        elif "CodVend" in ventas.columns:
            ventas = ventas.rename(columns={"CodVend": "CodVendedor"})
            
        ventas["CodVendedor"] = pd.to_numeric(ventas["CodVendedor"], errors="coerce").astype("Int64")
        ventas["Cliente"] = pd.to_numeric(ventas["Cliente"], errors="coerce").astype("Int64")
        
        cols_v_str = [str(c).strip().lower() for c in ventas.columns]
        col_prov_v = next((ventas.columns[i] for i, c in enumerate(cols_v_str) if c in ["proveedor", "fabricante", "empresa"]), None)
        if col_prov_v:
            ventas = ventas[ventas[col_prov_v].astype(str).str.contains("pepsico", case=False, na=False)].copy()
            
        col_subramo_v = next((ventas.columns[i] for i, c in enumerate(cols_v_str) if "subramo" in c), None)
        if col_subramo_v:
            ventas = ventas[ventas[col_subramo_v].fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()
    
    ventas_periodo = ventas[ventas["Periodo"].isin(["Arrastre", "Actual"])].copy() if "Periodo" in ventas.columns and not ventas.empty else ventas.copy()
    
    if not ventas_periodo.empty:
        clientes_g = ventas_periodo.groupby(["CodVendedor", "Cliente"], as_index=False).agg(
            Total_Cant=("CantBase", "sum"), 
            Total_Importe=("ImporteNetoItem", "sum") if "ImporteNetoItem" in ventas_periodo.columns else ("ImporteNeto", "sum")
        )
        clientes_g["Es_CCC"] = clientes_g["Total_Cant"].ge(3) & clientes_g["Total_Importe"].gt(1)
    else:
        clientes_g = pd.DataFrame(columns=["CodVendedor", "Cliente", "Es_CCC"])
    
    universo = df_universo.copy() if df_universo is not None else pd.DataFrame()
    if not universo.empty:
        cols_c_str = [str(c).strip().lower() for c in universo.columns]
        col_prov_c = next((universo.columns[i] for i, c in enumerate(cols_c_str) if c in ["proveedor", "fabricante", "empresa"]), None)
        if col_prov_c:
            universo = universo[universo[col_prov_c].astype(str).str.contains("pepsico", case=False, na=False)].copy()
            
        subramo_col = next((c for c in universo.columns if "subramo" in str(c).lower()), None)
        if subramo_col: 
            universo = universo[universo[subramo_col].fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()
            
        pos_vend_c = next((c for c in universo.columns if str(c).strip().lower() in ["codvendedor", "codvend", "vendedor"]), None)
        if pos_vend_c and pos_vend_c != "CodVendedor":
            universo = universo.rename(columns={pos_vend_c: "CodVendedor"})
            
        tax_col = next((c for c in universo.columns if "taxonomia" in str(c).lower() or "segmentoclientecodigo" in str(c).lower()), None)
        if tax_col:
            universo["Taxonomia"] = universo[tax_col].fillna("").astype(str).str.strip().str.upper()
            
        universo["CodVendedor"] = pd.to_numeric(universo["CodVendedor"], errors="coerce").astype("Int64")
        universo["Cliente"] = pd.to_numeric(universo["Cliente"], errors="coerce").astype("Int64")
        universo = universo[universo["Taxonomia"].isin(["A", "B", "C", "D"])].dropna(subset=["CodVendedor", "Cliente"])
    
    universo_clean = universo[["Cliente", "Taxonomia"]].drop_duplicates("Cliente") if not universo.empty else pd.DataFrame(columns=["Cliente", "Taxonomia"])
    
    if not clientes_g.empty and not universo_clean.empty:
        clientes_g = clientes_g.merge(universo_clean, on="Cliente", how="left")
        clientes_g["Taxonomia"] = clientes_g["Taxonomia"].astype(str).str.strip().str.upper()
        clientes_g = clientes_g[clientes_g["Taxonomia"].isin(["A", "B", "C", "D"])]
    
    ccc_matriz = clientes_g[clientes_g["Es_CCC"]].groupby(["CodVendedor", "Taxonomia"]).size().rename("CCC").reset_index() if not clientes_g.empty else pd.DataFrame(columns=["CodVendedor", "Taxonomia", "CCC"])
    cartera_matriz = universo.groupby(["CodVendedor", "Taxonomia"]).size().rename("Cartera_Total").reset_index() if not universo.empty else pd.DataFrame(columns=["CodVendedor", "Taxonomia", "Cartera_Total"])
    
    vendedores_df = pd.DataFrame()
    vendedores_df["CodVendedor"] = pd.to_numeric(vendedores["CodVend"], errors="coerce").astype("Int64")
    vendedores_df["Nombre"] = vendedores["Nombre"].fillna("").astype(str).str.strip()
    vendedores_df["SUP"] = vendedores["SUP"].fillna("").astype(str).str.strip()
    vendedores_df = vendedores_df.drop_duplicates("CodVendedor")
    
    taxonomias_df = pd.DataFrame({"Taxonomia": ["A", "B", "C", "D"]})
    vendedores_df["_k"], taxonomias_df["_k"] = 1, 1
    matriz_base = vendedores_df.merge(taxonomias_df, on="_k").drop(columns="_k")
    
    reporte = matriz_base.merge(cartera_matriz, on=["CodVendedor", "Taxonomia"], how="left").merge(ccc_matriz, on=["CodVendedor", "Taxonomia"], how="left")
    reporte[["Cartera_Total", "CCC"]] = reporte[["Cartera_Total", "CCC"]].fillna(0).astype("Int64")
    reporte["NC"] = (reporte["Cartera_Total"] - reporte["CCC"]).clip(lower=0).astype("Int64")
    reporte["Cobertura_Pct"] = (reporte["CCC"] / reporte["Cartera_Total"].replace(0, pd.NA)).mul(100).fillna(0.0)
    reporte["Total_Cartera_Cia"] = reporte.groupby("Taxonomia")["Cartera_Total"].transform("sum")
    reporte["Participacion_Cartera"] = (reporte["Cartera_Total"] / reporte["Total_Cartera_Cia"].replace(0, pd.NA)).fillna(0.0)
    
    reporte = reporte.merge(hoja_ccc, on="Taxonomia", how="left")
    reporte["OBJ_CCC"] = reporte["OBJ_CCC"].fillna(0.0)
    reporte["Objetivo_CCC"] = (reporte["Participacion_Cartera"] * reporte["OBJ_CCC"]).fillna(0.0).round(0).astype("Int64")
    reporte["% Cumplimiento Objetivo"] = (reporte["CCC"] / reporte["Objetivo_CCC"].replace(0, pd.NA)).mul(100).fillna(0.0)
    
    return reporte[["CodVendedor", "Nombre", "SUP", "Taxonomia", "Cartera_Total", "Objetivo_CCC", "CCC", "NC", "Cobertura_Pct", "% Cumplimiento Objetivo"]]

def dibujar_pestaña_ccc(reporte_ccc_base, supervisores_seleccionados=None):
    st.subheader("📊 Avance de CCC por Taxonomía")
    st.markdown("Analiza la cobertura de Clientes Con Compra (CCC) segmentada por taxonomía y vendedor.")
    
    df_base = reporte_ccc_base.copy()
    if supervisores_seleccionados and "SUP" in df_base.columns:
        sup_str = [str(s).strip() for s in supervisores_seleccionados]
        df_base = df_base[df_base["SUP"].astype(str).str.strip().isin(sup_str)].copy()
        
    if df_base.empty:
        st.info("No hay registros para los supervisores seleccionados.")
        return

    v_dispo_ccc = sorted(df_base["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    tax_dispo_ccc = sorted(df_base["Taxonomia"].dropna().astype(str).str.strip().unique().tolist())

    col_fc1, col_fc2 = st.columns([2, 2])
    with col_fc1:
        v_selec_ccc = crear_filtro_excel("Vendedor", v_dispo_ccc, "ccc_vend")
    with col_fc2:
        tax_selec_ccc = crear_filtro_excel("Taxonomía", tax_dispo_ccc, "ccc_tax")
        
    if not v_selec_ccc:
        v_selec_ccc = v_dispo_ccc
    if not tax_selec_ccc:
        tax_selec_ccc = tax_dispo_ccc

    reporte_ccc_filtrado = df_base[
        df_base["Nombre"].astype(str).str.strip().isin(v_selec_ccc) &
        df_base["Taxonomia"].astype(str).str.strip().isin(tax_selec_ccc)
    ].copy()
    
    total_ccc_val = reporte_ccc_filtrado["CCC"].sum()
    tot_tax = reporte_ccc_filtrado.groupby("Taxonomia")["CCC"].sum()
    cant_a = tot_tax.get("A", 0)
    cant_b = tot_tax.get("B", 0)
    cant_c = tot_tax.get("C", 0)
    cant_d = tot_tax.get("D", 0)
    
    st.markdown("""
    <style>
    .tax-box-sm {
        padding: 4px 6px;
        border-radius: 6px;
        color: white;
        font-weight: bold;
        text-align: center;
        font-size: 13px;
        line-height: 1.2;
    }
    .tax-a { background-color: #E63946; }
    .tax-b { background-color: #F4A261; }
    .tax-c { background-color: #E7C169; color: #111; }
    .tax-d { background-color: #2A9D8F; }
    .sub-label {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 6px;
        color: #E0E0E0;
    }
    </style>
    """, unsafe_allow_html=True)

    col_mc1, col_mc2 = st.columns([1.0, 2.0])
    with col_mc1:
        st.metric("📊 Total CCC", f"{total_ccc_val:,.0f}")
    with col_mc2:
        def formatear_detalle(selec, total_disp):
            if not selec:
                return "NINGUNO"
            if len(selec) == len(total_disp):
                return "TODOS"
            return ", ".join(map(str, selec))

        vend_res = formatear_detalle(v_selec_ccc, v_dispo_ccc)
        tax_res = formatear_detalle(tax_selec_ccc, tax_dispo_ccc)
        
        st.markdown(
            f"""
            <div style="background-color: #1e293b; padding: 10px; border-radius: 6px; font-size: 13px; border: 1px solid #475569; color: #f8fafc;">
                <b style="color: #38bdf8;">📋 Resumen de Filtros Aplicados:</b><br>
                • <b>Vendedor:</b> <span style="color: #e2e8f0;">{vend_res}</span><br>
                • <b>Taxonomía:</b> <span style="color: #e2e8f0;">{tax_res}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    c_a, c_b, c_c, c_d = st.columns(4)
    with c_a:
        st.markdown(f'<div class="tax-box-sm tax-a"><span style="font-size:11px;">A</span><br>{cant_a:,.0f}</div>', unsafe_allow_html=True)
    with c_b:
        st.markdown(f'<div class="tax-box-sm tax-b"><span style="font-size:11px;">B</span><br>{cant_b:,.0f}</div>', unsafe_allow_html=True)
    with c_c:
        st.markdown(f'<div class="tax-box-sm tax-c"><span style="font-size:11px;">C</span><br>{cant_c:,.0f}</div>', unsafe_allow_html=True)
    with c_d:
        st.markdown(f'<div class="tax-box-sm tax-d"><span style="font-size:11px;">D</span><br>{cant_d:,.0f}</div>', unsafe_allow_html=True)
            
    st.divider()

    columnas_visuales_ccc = ["CodVendedor", "Nombre", "SUP", "Taxonomia", "Cartera_Total", "Objetivo_CCC", "CCC", "NC", "Cobertura_Pct", "% Cumplimiento Objetivo"]
    reporte_ccc_render = reporte_ccc_filtrado[columnas_visuales_ccc].copy()
    
    if not reporte_ccc_render.empty:
        gb = GridOptionsBuilder.from_dataframe(reporte_ccc_render)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=130)
        gb.configure_column("CodVendedor", headerName="Cód. Vend", width=100, valueFormatter="x != null ? Number(x).toFixed(0) : ''")
        gb.configure_column("Nombre", headerName="Preventista", minWidth=180)
        gb.configure_column("SUP", headerName="SUP", width=80)
        gb.configure_column("Taxonomia", headerName="Tax", width=80)
        gb.configure_column("Cartera_Total", headerName="Cartera Total", width=110)
        gb.configure_column("Objetivo_CCC", headerName="Objetivo CCC", width=110)
        gb.configure_column("CCC", headerName="CCC", width=90)
        gb.configure_column("NC", headerName="NC", width=90)
        gb.configure_column("Cobertura_Pct", headerName="Cob %", width=100, valueFormatter="x != null ? Number(x).toFixed(2) + '%' : '0.00%'")
        gb.configure_column("% Cumplimiento Objetivo", headerName="% Cumplimiento", width=130, valueFormatter="x != null ? Number(x).toFixed(2) + '%' : '0.00%'")
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        
        grid_options = gb.build()
        AgGrid(
            reporte_ccc_render,
            gridOptions=grid_options,
            height=420,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=True
        )
    else:
        st.info("No se encontraron registros de CCC con los filtros seleccionados.")
        
    buffer_ccc = io.BytesIO()
    with pd.ExcelWriter(buffer_ccc, engine="openpyxl") as writer:
        reporte_ccc_render.to_excel(writer, index=False, sheet_name="Avance_CCC_Taxonomia")
    buffer_ccc.seek(0)
    
    st.download_button(
        label="📥 Descargar Avance CCC a Excel", 
        data=buffer_ccc, 
        file_name="Avance_CCC_Taxonomia.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        key="ccc_btn_dl"
    )