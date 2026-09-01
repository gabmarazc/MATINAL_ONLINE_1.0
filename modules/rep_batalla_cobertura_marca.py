import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode

def parsear_dia_desde_ruta(texto):
    """Extrae el día de la semana evaluando el texto de la columna Ruta."""
    if pd.isna(texto):
        return "SIN RUTA DEFINIDA"
        
    t = str(texto).strip().upper()
    
    if "VIERNES" in t:
        return "VIERNES"
    elif "MARTES" in t:
        return "MARTES"
    elif "JUEVES" in t:
        return "JUEVES"
    elif "LUNES" in t:
        return "LUNES"
    elif "MIERCOLES" in t or "MIÉRCOLES" in t:
        return "MIÉRCOLES"
    elif "SABADO" in t or "SÁBADO" in t:
        return "SÁBADO"
    elif "DOMINGO" in t:
        return "DOMINGO"
        
    return "SIN RUTA DEFINIDA"

def crear_filtro_excel(label, opciones, key_prefix):
    """Crea un filtro desplegable tipo Excel con opción de 'TODOS' sincronizada de forma reactiva (sin st.form)."""
    all_key = f"{key_prefix}_todos"
    
    if all_key not in st.session_state:
        st.session_state[all_key] = True

    for op in opciones:
        chk_key = f"{key_prefix}_{op}"
        if chk_key not in st.session_state:
            st.session_state[chk_key] = True

    val_todos_actual = st.session_state.get(all_key, True)
    aux_cambio_key = f"{key_prefix}_aux_prev_todos"
    if aux_cambio_key not in st.session_state:
        st.session_state[aux_cambio_key] = val_todos_actual

    if st.session_state[aux_cambio_key] != val_todos_actual:
        st.session_state[aux_cambio_key] = val_todos_actual
        for op in opciones:
            st.session_state[f"{key_prefix}_{op}"] = val_todos_actual

    with st.popover(f"{label}: ...", use_container_width=True):
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
def _procesar_cobertura_marca_cacheado(bases_univ, df_vtas_operativo_dict_or_df, df_marcas_df, df_vendedores_df):
    """Función cacheada para aislar y acelerar el procesamiento pesado de cobertura por marca."""
    df_marcas = df_marcas_df
    marcas = []
    if not df_marcas.empty and len(df_marcas.columns) > 0:
        col_marca_base = next((c for c in df_marcas.columns if "marca" in str(c).lower()), df_marcas.columns[0])
        for m in df_marcas[col_marca_base].dropna().astype(str).str.strip():
            if m and m not in marcas:
                marcas.append(m)

    if not marcas:
        return pd.DataFrame(), []

    ventas = df_vtas_operativo_dict_or_df.copy() if df_vtas_operativo_dict_or_df is not None else pd.DataFrame()
    if ventas.empty:
        return pd.DataFrame(), marcas

    if "CodVendedorOperativo" in ventas.columns: 
        ventas["CodVendedor"] = ventas["CodVendedorOperativo"]
    elif "CodVend" in ventas.columns:
        ventas = ventas.rename(columns={"CodVend": "CodVendedor"})

    ventas["CodVendedor"] = pd.to_numeric(ventas["CodVendedor"], errors="coerce").astype("Int64")
    ventas["Cliente"] = pd.to_numeric(ventas["Cliente"], errors="coerce").astype("Int64")

    ventas_periodo = ventas[ventas["Periodo"].isin(["Arrastre", "Actual"])].copy() if "Periodo" in ventas.columns else ventas.copy()

    cols_v_str = [str(c).strip().lower() for c in ventas_periodo.columns]
    col_prov_v = next((ventas_periodo.columns[i] for i, c in enumerate(cols_v_str) if c in ["proveedor", "fabricante", "empresa"]), None)
    if col_prov_v:
        ventas_periodo = ventas_periodo[ventas_periodo[col_prov_v].astype(str).str.contains("pepsico", case=False, na=False)].copy()

    col_subramo_v = next((ventas_periodo.columns[i] for i, c in enumerate(cols_v_str) if "subramo" in c), None)
    if col_subramo_v:
        ventas_periodo = ventas_periodo[ventas_periodo[col_subramo_v].fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()

    posibles_cant = ["cantbase", "CantBase", "Cantidad", "CANTIDAD", "cant", "Kilos", "KILOS", "Unidades"]
    enc_cant = next((p for p in posibles_cant if p in [str(c).strip() for c in ventas_periodo.columns]), None)
    if enc_cant:
        ventas_periodo["cantbase"] = pd.to_numeric(ventas_periodo[enc_cant], errors="coerce").fillna(0.0)
    else:
        ventas_periodo["cantbase"] = 0.0

    posibles_marca = ["Marca", "MARCA", "marca"]
    enc_marca = next((p for p in posibles_marca if p in [str(c).strip() for c in ventas_periodo.columns]), None)
    if enc_marca:
        ventas_periodo["Marca"] = ventas_periodo[enc_marca].astype(str).str.strip()
    else:
        ventas_periodo["Marca"] = ""

    vtas_agrupadas = ventas_periodo.groupby(["CodVendedor", "Cliente", "Marca"], as_index=False).agg(
        Total_Cant=("cantbase", "sum")
    )

    universo = bases_univ.copy()
    cols_c_str = [str(c).strip().lower() for c in universo.columns]
    col_prov_c = next((universo.columns[i] for i, c in enumerate(cols_c_str) if c in ["proveedor", "fabricante", "empresa"]), None)
    if col_prov_c:
        universo = universo[universo[col_prov_c].astype(str).str.contains("pepsico", case=False, na=False)].copy()

    subramo_col = next((c for c in universo.columns if "subramo" in str(c).lower()), None)
    if subramo_col: 
        universo = universo[universo[subramo_col].fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()
        
    col_r = "Ruta" if "Ruta" in universo.columns else next((c for c in universo.columns if "ruta" in str(c).lower()), None)
    if col_r:
        universo["DiaVisita"] = universo[col_r].apply(parsear_dia_desde_ruta)
    else:
        universo["DiaVisita"] = "SIN RUTA DEFINIDA"
        
    renombres = {
        "Codigo": "Cliente",
        "codven": "CodVendedor",
        "SegmentoClienteCodigo": "Taxonomia",
    }
    universo = universo.rename(columns=renombres)

    if "NombreCliente" not in universo.columns:
        col_nc = next((c for c in universo.columns if "razon" in str(c).lower() or "nombre" in str(c).lower()), None)
        universo["NombreCliente"] = universo[col_nc].astype(str) if col_nc else universo["Cliente"].astype(str)
    if "DireccionCliente" not in universo.columns:
        col_dir = next((c for c in universo.columns if "direc" in str(c).lower()), None)
        universo["DireccionCliente"] = universo[col_dir].astype(str) if col_dir else "Domicilio Registrado"

    pos_vend_c = next((c for c in universo.columns if str(c).strip().lower() in ["codvendedor", "codvend", "vendedor"]), None)
    if pos_vend_c and pos_vend_c != "CodVendedor":
        universo = universo.rename(columns={pos_vend_c: "CodVendedor"})

    universo["CodVendedor"] = pd.to_numeric(universo["CodVendedor"], errors="coerce").astype("Int64")
    universo["Cliente"] = pd.to_numeric(universo["Cliente"], errors="coerce").astype("Int64")
    
    tax_col = next((c for c in universo.columns if "taxonomia" in str(c).lower() or "segmentoclientecodigo" in str(c).lower()), None)
    if tax_col:
        universo["Taxonomia"] = universo[tax_col].fillna("").astype(str).str.strip().str.upper()
    else:
        universo["Taxonomia"] = ""
    
    universo = universo[
        universo["Taxonomia"].isin(["A", "B", "C", "D"]) & 
        universo["CodVendedor"].notna() & 
        universo["Cliente"].notna()
    ].copy()

    df_marcas_temp = pd.DataFrame({"Marca": marcas})
    universo["_k"] = 1
    df_marcas_temp["_k"] = 1
    universo_marcas = universo.merge(df_marcas_temp, on="_k").drop(columns="_k")

    universo_marcas_ventas = universo_marcas.merge(
        vtas_agrupadas, on=["CodVendedor", "Cliente", "Marca"], how="left"
    )
    universo_marcas_ventas["Total_Cant"] = universo_marcas_ventas["Total_Cant"].fillna(0.0)

    df_incumplidores = universo_marcas_ventas[universo_marcas_ventas["Total_Cant"] < 3].copy()

    vendedores = df_vendedores_df.copy()
    vendedores_df_proc = pd.DataFrame()
    vendedores_df_proc["CodVendedor"] = pd.to_numeric(vendedores["CodVend"], errors="coerce").astype("Int64")
    vendedores_df_proc["Preventista"] = vendedores["Nombre"].fillna("").astype(str).str.strip()
    vendedores_df_proc["SUP"] = vendedores["SUP"].fillna("").astype(str).str.strip()
    vendedores_df_proc = vendedores_df_proc.drop_duplicates("CodVendedor")

    df_enriquecido = df_incumplidores.merge(vendedores_df_proc, on="CodVendedor", how="left")
    
    df_enriquecido["Preventista"] = df_enriquecido["Preventista"].fillna("VENDEDOR " + df_enriquecido["CodVendedor"].astype(str))
    df_enriquecido["SUP"] = df_enriquecido["SUP"].fillna("SIN SUP").astype(str).str.strip()
    df_enriquecido["NombreCliente"] = df_enriquecido["NombreCliente"].fillna("Comercio Activo")
    df_enriquecido["DireccionCliente"] = df_enriquecido["DireccionCliente"].fillna("Domicilio Registrado")

    return df_enriquecido, marcas

def dibujar_pestaña_batalla_cobertura_marca(bases, df_vtas_operativo, supervisores_seleccionados):
    st.subheader("🎯 Oportunidades: Clientes que NO Cumplen Cobertura Por Marca")
    st.markdown("Listado de marcas no alcanzadas (< 3 unidades) por cliente (Taxonomía A, B, C, D) para gestionar acciones comerciales.")
    
    df_marcas = bases.get("PARAMETROS", {}).get("MARCAS", pd.DataFrame())
    df_vendedores = bases.get("PARAMETROS", {}).get("VENDEDORES", pd.DataFrame())
    df_universo = bases.get("UNIVERSO", pd.DataFrame())

    df_enriquecido, marcas = _procesar_cobertura_marca_cacheado(df_universo, df_vtas_operativo, df_marcas, df_vendedores)

    if not marcas:
        st.error("No se encontraron marcas definidas en los parámetros.")
        return

    if df_enriquecido.empty:
        st.warning("No hay datos o ventas operativas disponibles para procesar.")
        return

    sup_str = [str(s).strip() for s in supervisores_seleccionados]
    df_enriquecido = df_enriquecido[df_enriquecido["SUP"].isin(sup_str)].copy()

    if df_enriquecido.empty:
        st.info("No se encontraron registros de clientes incumplidores bajo los supervisores seleccionados.")
        return

    # Filtros reactivos directos (sin st.form ni botón Aplicar)
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        v_dispo = sorted(df_enriquecido["Preventista"].dropna().unique().tolist())
        v_selec = crear_filtro_excel("Preventista", v_dispo, "batallacob_prev")
        
    with col_f2:
        orden_dias_map = {
            "LUNES": 1, "MARTES": 2, "MIÉRCOLES": 3, "JUEVES": 4,
            "VIERNES": 5, "SÁBADO": 6, "DOMINGO": 7, "SIN RUTA DEFINIDA": 8
        }
        d_raw = df_enriquecido["DiaVisita"].dropna().unique().tolist()
        d_dispo = sorted(d_raw, key=lambda x: orden_dias_map.get(str(x).strip().upper(), 99))
        d_selec = crear_filtro_excel("Día Visita", d_dispo, "batallacob_dia")

    with col_f3:
        m_selec = crear_filtro_excel("Marca", marcas, "batallacob_marca")

    with col_f4:
        tax_dispo = sorted(df_enriquecido["Taxonomia"].dropna().unique().tolist())
        tax_selec = crear_filtro_excel("Taxonomía", tax_dispo, "batallacob_tax")

    if not v_selec:
        v_selec = v_dispo
    if not d_selec:
        d_selec = d_dispo
    if not m_selec:
        m_selec = marcas
    if not tax_selec:
        tax_selec = tax_dispo

    df_filtrado = df_enriquecido[
        df_enriquecido["Preventista"].isin(v_selec) & 
        df_enriquecido["DiaVisita"].isin(d_selec) &
        df_enriquecido["Marca"].isin(m_selec) &
        df_enriquecido["Taxonomia"].isin(tax_selec)
    ].copy()

    busqueda = st.text_input("🔍 Buscar por ID de Cliente o Razón Social:", key="batallacob_busq_f")
    if busqueda:
        df_filtrado = df_filtrado[
            df_filtrado["Cliente"].astype(str).str.contains(busqueda) | 
            df_filtrado["NombreCliente"].astype(str).str.contains(busqueda, case=False)
        ]

    col_m1, col_m2 = st.columns([1, 1.8])
    with col_m1:
        st.metric("📊 Total Brechas / Oportunidades", f"{len(df_filtrado):,}")
        
    with col_m2:
        def formatear_detalle(selec, total_disp):
            if not selec:
                return "NINGUNO"
            if len(selec) == len(total_disp):
                return "TODOS"
            return ", ".join(map(str, selec))

        prev_res = formatear_detalle(v_selec, v_dispo)
        dia_res = formatear_detalle(d_selec, d_dispo)
        marca_res = formatear_detalle(m_selec, marcas)
        tax_res = formatear_detalle(tax_selec, tax_dispo)
        
        st.markdown(
            f"""
            <div style="background-color: #1e293b; padding: 12px; border-radius: 6px; font-size: 13px; border: 1px solid #475569; color: #f8fafc;">
                <b style="color: #38bdf8;">📋 Resumen de Filtros Aplicados:</b><br>
                • <b>Preventista:</b> <span style="color: #e2e8f0;">{prev_res}</span><br>
                • <b>Día Visita:</b> <span style="color: #e2e8f0;">{dia_res}</span><br>
                • <b>Marca:</b> <span style="color: #e2e8f0;">{marca_res}</span><br>
                • <b>Taxonomía:</b> <span style="color: #e2e8f0;">{tax_res}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    columnas_vista = ["SUP", "CodVendedor", "Preventista", "Cliente", "NombreCliente", "DireccionCliente", "Taxonomia", "DiaVisita", "Marca", "Total_Cant"]
    columnas_validas_vista = [c for c in columnas_vista if c in df_filtrado.columns]
    
    df_render = df_filtrado[columnas_validas_vista].sort_values(by=["Preventista", "Taxonomia", "Cliente"]).reset_index(drop=True)
    
    if not df_render.empty:
        gb = GridOptionsBuilder.from_dataframe(df_render)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=130)
        gb.configure_column("SUP", headerName="SUP", width=80)
        gb.configure_column("CodVendedor", headerName="Cód. Vend", width=100, valueFormatter="x != null ? Number(x).toFixed(0) : ''")
        gb.configure_column("Preventista", headerName="Preventista", minWidth=180)
        gb.configure_column("Cliente", headerName="ID Cliente", width=110, valueFormatter="x != null ? Number(x).toFixed(0) : ''")
        gb.configure_column("NombreCliente", headerName="Razón Social / Comercio", minWidth=220)
        gb.configure_column("DireccionCliente", headerName="Ubicación / Domicilio", minWidth=200)
        gb.configure_column("Taxonomia", headerName="Tax", width=80)
        gb.configure_column("DiaVisita", headerName="Día Visita", width=120)
        gb.configure_column("Total_Cant", headerName="Cant. Actual", width=110, valueFormatter="x != null ? Number(x).toFixed(1) : '0'")
        
        estilo_marca_js = JsCode("""
        function(params) {
            return {'backgroundColor': '#f4cccc', 'color': '#783f04', 'fontWeight': 'bold', 'textAlign': 'center'};
        }
        """)
        gb.configure_column("Marca", headerName="Marca a Desarrollar", width=150, cellStyle=estilo_marca_js)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        
        grid_options = gb.build()
        AgGrid(
            df_render,
            gridOptions=grid_options,
            height=420,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True
        )
    else:
        st.info("No se encontraron oportunidades pendientes con los filtros seleccionados.")
    
    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
        df_render.to_excel(writer, index=False, sheet_name="Oportunidades_Cobertura_Marca")
    buffer_excel.seek(0)
    
    st.download_button(
        label="📥 Descargar Oportunidades a Excel", 
        data=buffer_excel, 
        file_name="Oportunidades_Cobertura_Por_Marca.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        key="batallacob_btn_dl"
    )