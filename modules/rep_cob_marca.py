import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode

def generar_reporte_cobertura_marca(df_vtas_operativo, df_cartera, vendedores, df_marcas):
    """
    Genera el reporte de Cobertura por Marca replicando exactamente los filtros de VTA
    del reporte modelo de kilos y evaluando la sumatoria de CantBase por cliente y marca (>= 3).
    """
    df_vend = vendedores.copy() if vendedores is not None and not vendedores.empty else pd.DataFrame(columns=["CodVend", "Nombre", "SUP"])
    if "CodVend" in df_vend.columns:
        df_vend["CodVend"] = pd.to_numeric(df_vend["CodVend"], errors="coerce").astype("Int64")
        df_vend = df_vend[~df_vend["CodVend"].isin([20, 99])].drop_duplicates(subset=["CodVend"])
    
    # Obtener lista oficial de marcas respetando estrictamente el orden original
    marcas = []
    if df_marcas is not None and not df_marcas.empty and len(df_marcas.columns) > 0:
        col_marca_base = next((c for c in df_marcas.columns if "marca" in str(c).lower()), df_marcas.columns[0])
        for m in df_marcas[col_marca_base].dropna().astype(str).str.strip():
            if m and m not in marcas:
                marcas.append(m)
                
    # Detectar columna 'Obj_Cobertura'
    col_obj_encontrada = None
    if df_marcas is not None and not df_marcas.empty:
        cols_base_str = [str(c).strip() for c in df_marcas.columns]
        col_obj_encontrada = next((df_marcas.columns[i] for i, c in enumerate(cols_base_str) if "obj_cobertura" in c.lower() or c.lower() == "obj_cobertura"), None)
        if not col_obj_encontrada:
            col_obj_encontrada = next((df_marcas.columns[i] for i, c in enumerate(cols_base_str) if "cobertura" in c.lower() and "obj" in c.lower()), None)
    
    mapa_objetivos = {}
    if df_marcas is not None and not df_marcas.empty and len(df_marcas.columns) > 0:
        col_m_name = next((c for c in df_marcas.columns if "marca" in str(c).lower()), df_marcas.columns[0])
        for _, row in df_marcas.iterrows():
            m = str(row.get(col_m_name, "")).strip()
            if m:
                val_obj = row.get(col_obj_encontrada, 0) if col_obj_encontrada else 0
                try:
                    f_val = float(val_obj)
                    if f_val <= 1.0 and f_val > 0:
                        f_val = f_val * 100.0
                    mapa_objetivos[m] = f_val
                except:
                    mapa_objetivos[m] = 0.0
    
    vtas = df_vtas_operativo.copy() if df_vtas_operativo is not None else pd.DataFrame()
    if not vtas.empty:
        if "CodVendedorOperativo" in vtas.columns:
            vtas["CodVendedor"] = vtas["CodVendedorOperativo"]
        if "CodVendedor" not in vtas.columns and "CodVend" in vtas.columns:
            vtas = vtas.rename(columns={"CodVend": "CodVendedor"})
        if "CodVendedor" in vtas.columns:
            vtas["CodVendedor"] = pd.to_numeric(vtas["CodVendedor"], errors="coerce").astype("Int64")
        
        # Filtro de períodos idéntico al reporte de kilos
        if "Periodo" in vtas.columns:
            vtass_periodo = vtas[vtas["Periodo"].isin(["Arrastre", "Actual"])].copy()
        else:
            vtass_periodo = vtas.copy()
            
        # Filtro flexible de Proveedor Pepsico en ventas
        cols_v_str = [str(c).strip().lower() for c in vtass_periodo.columns]
        col_prov_v = next((vtass_periodo.columns[i] for i, c in enumerate(cols_v_str) if c in ["proveedor", "fabricante", "empresa"]), None)
        if col_prov_v:
            vtass_periodo = vtass_periodo[vtass_periodo[col_prov_v].astype(str).str.contains("pepsico", case=False, na=False)].copy()
            
        # Filtro de Subramo distinto a Empleados en ventas (igual que en cartera)
        col_subramo_v = next((vtass_periodo.columns[i] for i, c in enumerate(cols_v_str) if "subramo" in c), None)
        if col_subramo_v:
            vtass_periodo = vtass_periodo[vtass_periodo[col_subramo_v].fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()
            
        vtas = vtass_periodo

    # Procesamiento de la Cartera basada en el Universo oficial
    cartera = df_cartera.copy() if df_cartera is not None and not df_cartera.empty else pd.DataFrame()
    total_cartera = pd.DataFrame(columns=["CodVendedor", "Total_Cartera"])
    
    if not cartera.empty:
        cols_c_str = [str(c).strip().lower() for c in cartera.columns]
        
        # Filtro de Proveedor Pepsico en cartera
        col_prov_c = next((cartera.columns[i] for i, c in enumerate(cols_c_str) if c in ["proveedor", "fabricante", "empresa"]), None)
        if col_prov_c:
            cartera = cartera[cartera[col_prov_c].astype(str).str.contains("pepsico", case=False, na=False)].copy()
            
        # Exclusión de empleados en Subramo
        subramo_col = next((c for c in cartera.columns if "subramo" in str(c).lower()), None)
        if subramo_col:
            cartera = cartera[cartera[subramo_col].fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()
            
        # Filtrado de Taxonomías válidas (A, B, C, D)
        tax_col = next((c for c in cartera.columns if "taxonomia" in str(c).lower() or "segmentoclientecodigo" in str(c).lower()), None)
        if tax_col:
            cartera["Taxonomia"] = cartera[tax_col].astype(str).str.strip().str.upper()
            cartera = cartera[cartera["Taxonomia"].isin(["A", "B", "C", "D"])].copy()
            
        posibles_vend = ["codvendedor", "codvend", "vendedor", "vend", "cod_vend", "cod_vendedor", "nrovendedor"]
        enc_vend_c = next((cartera.columns[i] for i, c in enumerate(cols_c_str) if c in posibles_vend), None)
        
        if enc_vend_c:
            cartera["CodVendedor"] = pd.to_numeric(cartera[enc_vend_c], errors="coerce").astype("Int64")
        elif len(cartera.columns) > 0:
            cartera["CodVendedor"] = pd.to_numeric(cartera.iloc[:, 0], errors="coerce").astype("Int64")
            
        if "CodVendedor" in cartera.columns:
            total_cartera = cartera.groupby("CodVendedor").size().reset_index(name="Total_Cartera")
    
    cliente_col_vtas = "Cliente" if not vtas.empty and "Cliente" in vtas.columns else (vtas.columns[1] if not vtas.empty and len(vtas.columns) > 1 else "Cliente")

    if not vtas.empty:
        cols_actuales = [str(c).strip() for c in vtas.columns]
        
        posibles_cant = ["cantbase", "CantBase", "Cantidad", "CANTIDAD", "cant", "Kilos", "KILOS", "Unidades"]
        encontrada_cant = next((p for p in posibles_cant if p in cols_actuales), None)
        if encontrada_cant:
            col_real_cant = vtas.columns[cols_actuales.index(encontrada_cant)]
            vtas["cantbase"] = pd.to_numeric(vtas[col_real_cant], errors="coerce").fillna(0.0)
        else:
            vtas["cantbase"] = 0.0
            
        cols_actuales = [str(c).strip() for c in vtas.columns]
        posibles_marca = ["Marca", "MARCA", "marca"]
        encontrada_marca = next((p for p in posibles_marca if p in cols_actuales), None)
        if encontrada_marca:
            col_real_marca = vtas.columns[cols_actuales.index(encontrada_marca)]
            vtas["Marca"] = vtas[col_real_marca].astype(str).str.strip()
        else:
            vtas["Marca"] = ""
            
        # Agrupar por vendedor, cliente y marca para evaluar la SUMATORIA del periodo (>= 3)
        vtas["Cliente"] = pd.to_numeric(vtas[cliente_col_vtas], errors="coerce").astype("Int64")
        vtas_agrupadas = vtas.groupby(["CodVendedor", "Cliente", "Marca"], as_index=False).agg(
            Total_Cant=("cantbase", "sum")
        )

        vtas_filtradas = vtas_agrupadas[
            vtas_agrupadas["Total_Cant"].ge(3) & 
            vtas_agrupadas["Marca"].isin(marcas)
        ].copy() if marcas else pd.DataFrame()
    else:
        vtas_filtradas = pd.DataFrame()
    
    if not vtas_filtradas.empty and "CodVendedor" in vtas_filtradas.columns and "Marca" in vtas_filtradas.columns and "Cliente" in vtas_filtradas.columns:
        conteo_cubiertos = vtas_filtradas.groupby(["CodVendedor", "Marca"])["Cliente"].nunique().reset_index(name="Clientes_Cubiertos")
        pivot_cubiertos = conteo_cubiertos.pivot_table(index="CodVendedor", columns="Marca", values="Clientes_Cubiertos", fill_value=0).reset_index()
        pivot_cubiertos.columns.name = None
    else:
        pivot_cubiertos = pd.DataFrame(columns=["CodVendedor"])
    
    if not df_vend.empty and "CodVend" in df_vend.columns and "Nombre" in df_vend.columns and "SUP" in df_vend.columns:
        reporte = df_vend[["CodVend", "Nombre", "SUP"]].rename(columns={"CodVend": "CodVendedor"})
    else:
        reporte = pd.DataFrame(columns=["CodVendedor", "Nombre", "SUP"])
        
    if not reporte.empty and not total_cartera.empty and "CodVendedor" in total_cartera.columns:
        reporte = reporte.merge(total_cartera, on="CodVendedor", how="left")
    if "Total_Cartera" in reporte.columns:
        reporte["Total_Cartera"] = reporte["Total_Cartera"].fillna(0)
    else:
        reporte["Total_Cartera"] = 0
    
    if not pivot_cubiertos.empty and "CodVendedor" in pivot_cubiertos.columns:
        reporte = reporte.merge(pivot_cubiertos, on="CodVendedor", how="left")
        
    for marca in marcas:
        if marca not in reporte.columns:
            reporte[marca] = 0.0
        else:
            reporte[marca] = reporte[marca].fillna(0.0)
            
    for marca in marcas:
        if "Total_Cartera" in reporte.columns:
            total_c = reporte["Total_Cartera"].replace(0, pd.NA)
            reporte[marca] = (reporte[marca] / total_c).fillna(0.0) * 100
        else:
            reporte[marca] = 0.0
        
    base_cols = ["CodVendedor", "Nombre", "SUP", "Total_Cartera"]
    columnas_finales = base_cols + [m for m in marcas if m in reporte.columns]
    reporte = reporte[[c for c in columnas_finales if c in reporte.columns]]
        
    return reporte, marcas, mapa_objetivos

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

def dibujar_pestana_cobertura_marca(reporte_cobertura, marcas, mapa_objetivos, supervisores_seleccionados, df_vtas_operativo=None):
    st.subheader("Cobertura Por Marca")
    
    sup_str = [str(s).strip() for s in supervisores_seleccionados]
    if reporte_cobertura is not None and not reporte_cobertura.empty and "SUP" in reporte_cobertura.columns:
        df_filtrado = reporte_cobertura[
            reporte_cobertura["SUP"].astype(str).str.strip().isin(sup_str)
        ].copy()
    else:
        df_filtrado = pd.DataFrame(columns=["CodVendedor", "Nombre", "SUP", "Total_Cartera"])
    
    if marcas and not df_filtrado.empty and df_vtas_operativo is not None and not df_vtas_operativo.empty:
        st.markdown("**Objetivos y Cobertura Global por Marca:**")
        
        suma_cartera_global = df_filtrado["Total_Cartera"].sum()
        vendedores_activos_cods = df_filtrado["CodVendedor"].dropna().tolist()
        
        vtas_g = df_vtas_operativo.copy()
        if "CodVendedorOperativo" in vtas_g.columns:
            vtas_g["CodVendedor"] = vtas_g["CodVendedorOperativo"]
        elif "CodVend" in vtas_g.columns:
            vtas_g = vtas_g.rename(columns={"CodVend": "CodVendedor"})
        if "CodVendedor" in vtas_g.columns:
            vtas_g["CodVendedor"] = pd.to_numeric(vtas_g["CodVendedor"], errors="coerce").astype("Int64")
            
        if "Periodo" in vtas_g.columns:
            vtas_g = vtas_g[vtas_g["Periodo"].isin(["Arrastre", "Actual"])].copy()
            
        cols_vg_str = [str(c).strip().lower() for c in vtas_g.columns]
        col_prov_vg = next((vtas_g.columns[i] for i, c in enumerate(cols_vg_str) if c in ["proveedor", "fabricante", "empresa"]), None)
        if col_prov_vg:
            vtas_g = vtas_g[vtas_g[col_prov_vg].astype(str).str.contains("pepsico", case=False, na=False)].copy()
            
        col_subramo_vg = next((vtas_g.columns[i] for i, c in enumerate(cols_vg_str) if "subramo" in c), None)
        if col_subramo_vg:
            vtas_g = vtas_g[vtas_g[col_subramo_vg].fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()
            
        vtas_g = vtas_g[vtas_g["CodVendedor"].isin(vendedores_activos_cods)].copy()
        
        cols_a = [str(c).strip() for c in vtas_g.columns]
        pos_cant = ["cantbase", "CantBase", "Cantidad", "CANTIDAD", "cant", "Kilos", "KILOS", "Unidades"]
        enc_cant = next((p for p in pos_cant if p in cols_a), None)
        if enc_cant:
            vtas_g["cantbase"] = pd.to_numeric(vtas_g[enc_cant], errors="coerce").fillna(0.0)
        else:
            vtas_g["cantbase"] = 0.0
            
        pos_m = ["Marca", "MARCA", "marca"]
        enc_m = next((p for p in pos_m if p in cols_a), None)
        if enc_m:
            vtas_g["Marca"] = vtas_g[enc_m].astype(str).str.strip()
        else:
            vtas_g["Marca"] = ""
            
        cliente_c = "Cliente" if "Cliente" in vtas_g.columns else (vtas_g.columns[1] if len(vtas_g.columns) > 1 else "Cliente")
        vtas_g["Cliente"] = pd.to_numeric(vtas_g[cliente_c], errors="coerce").astype("Int64")

        # Agrupar globalmente sumando CantBase por cliente y marca
        vtas_g_agrup = vtas_g.groupby(["CodVendedor", "Cliente", "Marca"], as_index=False).agg(
            Total_Cant=("cantbase", "sum")
        )
        vtas_g_filt = vtas_g_agrup[vtas_g_agrup["Total_Cant"].ge(3)].copy()
        
        cols_obj_ui = st.columns(min(len(marcas), 6))
        for idx, marca in enumerate(marcas):
            col_target = cols_obj_ui[idx % len(cols_obj_ui)]
            obj_val = mapa_objetivos.get(marca, 0.0)
            
            if not vtas_g_filt.empty and "Marca" in vtas_g_filt.columns:
                df_m_vta = vtas_g_filt[vtas_g_filt["Marca"] == marca]
                if not df_m_vta.empty and "Cliente" in df_m_vta.columns:
                    clientes_cubiertos_global = df_m_vta["Cliente"].nunique()
                else:
                    clientes_cubiertos_global = 0
            else:
                clientes_cubiertos_global = 0
                
            if suma_cartera_global > 0:
                cobertura_global_pct = (clientes_cubiertos_global / suma_cartera_global) * 100.0
            else:
                cobertura_global_pct = 0.0
                
            cumplida = cobertura_global_pct >= obj_val
            color_estilo = "color: #28a745;" if cumplida else "color: #dc3545;"
            
            with col_target:
                st.markdown(f"""
                <div style="font-size: 14px; font-weight: 600; color: #a0a0a0;">{marca} (Obj: {obj_val:g}%)</div>
                <div style="font-size: 24px; font-weight: bold; {color_estilo}">{cobertura_global_pct:.2f}%</div>
                """, unsafe_allow_html=True)
                
        st.divider()
    elif marcas:
        st.markdown("**Objetivos de Cobertura por Marca:**")
        cols_obj = st.columns(min(len(marcas), 6))
        for idx, marca in enumerate(marcas):
            col_target = cols_obj[idx % len(cols_obj)]
            obj_val = mapa_objetivos.get(marca, 0)
            col_target.metric(label=marca, value=f"{obj_val:g}%")
        st.divider()
    
    # 1. Extracción de opciones disponibles
    v_dispo = sorted(df_filtrado["Nombre"].dropna().astype(str).str.strip().unique().tolist()) if not df_filtrado.empty and "Nombre" in df_filtrado.columns else []

    # 2. Filtros locales interactivos completamente reactivos (Vendedor y Marca)
    col_f1, col_f2, _ = st.columns([2, 2, 1])
    with col_f1:
        v_selec = crear_filtro_excel("Vendedor", v_dispo, "cob_marca_vend")
    with col_f2:
        m_selec = crear_filtro_excel("Marca", marcas, "cob_marca_marca")

    if not v_selec:
        v_selec = v_dispo
    if not m_selec:
        m_selec = marcas

    if not df_filtrado.empty and v_dispo:
        df_filtrado = df_filtrado[
            df_filtrado["Nombre"].astype(str).str.strip().isin(v_selec)
        ].copy()

    def formatear_detalle(selec, total_disp):
        if not selec:
            return "NINGUNO"
        if len(selec) == len(total_disp):
            return "TODOS"
        return ", ".join(map(str, selec))

    vend_res = formatear_detalle(v_selec, v_dispo)
    marca_res = formatear_detalle(m_selec, marcas)

    st.markdown(
        f"""
        <div style="background-color: #1e293b; padding: 12px; border-radius: 6px; font-size: 13px; border: 1px solid #475569; color: #f8fafc; margin-top: 10px; margin-bottom: 10px;">
            <b style="color: #38bdf8;">📋 Resumen de Filtros Aplicados:</b><br>
            • <b>Vendedor:</b> <span style="color: #e2e8f0;">{vend_res}</span><br>
            • <b>Marca:</b> <span style="color: #e2e8f0;">{marca_res}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.divider()
    
    base_cols = ["CodVendedor", "Nombre", "SUP", "Total_Cartera"]
    columnas_finales = base_cols + [m for m in marcas if m in df_filtrado.columns and m in m_selec]
    df_render = df_filtrado[[c for c in columnas_finales if c in df_filtrado.columns]].copy()

    if not df_render.empty:
        gb = GridOptionsBuilder.from_dataframe(df_render)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=140)
        
        js_objetivos = str(mapa_objetivos)
        
        cell_style_conditional = JsCode(f"""
        function(params) {{
            const mapaObj = {js_objetivos};
            const col = params.colDef.field;
            if (mapaObj.hasOwnProperty(col)) {{
                const objetivo = Number(mapaObj[col]) || 0;
                const valorReal = Number(params.value) || 0;
                if (valorReal >= objetivo) {{
                    return {{'backgroundColor': '#d4edda', 'fontWeight': 'bold', 'color': '#155724'}};
                }} else {{
                    return {{'backgroundColor': '#f8d7da', 'fontWeight': 'bold', 'color': '#721c24'}};
                }}
            }}
            return null;
        }}
        """)
        
        for marca in marcas:
            if marca in df_render.columns:
                gb.configure_column(
                    marca,
                    headerName=marca,
                    valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '%' : '0.00%'",
                    cellStyle=cell_style_conditional
                )
                
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_options = gb.build()
        
        AgGrid(
            df_render,
            gridOptions=grid_options,
            height=400,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=False,
            allow_unsafe_jscode=True
        )
    else:
        st.info("No se encontraron registros de Cobertura por Marca con los filtros seleccionados.")
        
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_render.to_excel(writer, index=False, sheet_name="Cobertura_Por_Marca")
    buffer.seek(0)
    
    st.download_button(
        label="📥 Descargar Cobertura por Marca a Excel",
        data=buffer,
        file_name="Cobertura_Por_Marca.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="cob_marca_btn_dl"
    )