import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode
from modules.procesamiento import limpiar_vtas_crudas

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
def _procesar_universo_nc_cacheado(bases_vta=None, bases_univ=None, bases_param=None, df_vtas_operativo=None):
    """Función cacheada para aislar y acelerar el procesamiento pesado del panel NC."""
    fechas_param = bases_param["FECHAS"]
    p_dict = {}
    for n, v in zip(fechas_param["PARAMETRO"], fechas_param["VALOR"]):
        if pd.notna(n):
            p_dict[str(n).strip().casefold()] = v
            
    anio_op = int(p_dict.get("añooperativo", p_dict.get("año", 2026)))
    mes_op = int(p_dict.get("mesoperativo", p_dict.get("mes", 1)))
    
    if mes_op == 1:
        mes_ant = 12
        anio_ant = anio_op - 1
    else:
        mes_ant = mes_op - 1
        anio_ant = anio_op
        
    df_vta_limpia_global = limpiar_vtas_crudas(bases_vta)
    
    cols_vg_global = [str(c).strip().lower() for c in df_vta_limpia_global.columns]
    col_prov_vg_g = next((df_vta_limpia_global.columns[i] for i, c in enumerate(cols_vg_global) if c in ["proveedor", "fabricante", "empresa"]), None)
    if col_prov_vg_g:
        df_vta_limpia_global = df_vta_limpia_global[df_vta_limpia_global[col_prov_vg_g].astype(str).str.contains("pepsico", case=False, na=False)].copy()
        
    col_sub_vg_g = next((df_vta_limpia_global.columns[i] for i, c in enumerate(cols_vg_global) if "subramo" in c), None)
    if col_sub_vg_g:
        df_vta_limpia_global = df_vta_limpia_global[df_vta_limpia_global[col_sub_vg_g].fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()

    vta_mes_anterior = df_vta_limpia_global[
        df_vta_limpia_global["FechaCarga"].dt.year.eq(anio_ant) & 
        df_vta_limpia_global["FechaCarga"].dt.month.eq(mes_ant)
    ].copy()
    
    vta_mes_anterior["Cliente"] = pd.to_numeric(vta_mes_anterior["Cliente"], errors="coerce").astype("Int64")
    clientes_mes_anterior_set = set(vta_mes_anterior["Cliente"].dropna().unique())

    # 1. Identificación de compradores válidos
    ventas = df_vtas_operativo.copy() if df_vtas_operativo is not None else pd.DataFrame()
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
    
    col_importe = "ImporteNeto" if "ImporteNeto" in ventas.columns else "ImporteNetoItem"
    if col_importe not in ventas.columns:
        col_importe = next((c for c in ventas.columns if "importe" in str(c).lower()), ventas.columns[0] if not ventas.empty else None)

    ventas_periodo = ventas[ventas["Periodo"].isin(["Arrastre", "Actual"])].copy() if "Periodo" in ventas.columns and not ventas.empty else ventas.copy()
    
    if not ventas_periodo.empty and col_importe:
        clientes_g = ventas_periodo.groupby(["CodVendedor", "Cliente"], as_index=False).agg(
            Total_Cant=("CantBase", "sum"), 
            Total_Importe=(col_importe, "sum")
        )
        clientes_validos_set = set(
            clientes_g[clientes_g["Total_Cant"].ge(3) & clientes_g["Total_Importe"].gt(1)]["Cliente"].dropna().unique()
        )
    else:
        clientes_validos_set = set()

    # 2. Procesamiento del universo
    universo = bases_univ.copy()
    
    cols_c_str = [str(c).strip().lower() for c in universo.columns]
    col_prov_c = next((universo.columns[i] for i, c in enumerate(cols_c_str) if c in ["proveedor", "fabricante", "empresa"]), None)
    if col_prov_c:
        universo = universo[universo[col_prov_c].astype(str).str.contains("pepsico", case=False, na=False)].copy()

    col_r = "Ruta" if "Ruta" in universo.columns else next((c for c in universo.columns if "ruta" in str(c).lower()), None)
    if col_r:
        universo["DiaVisita"] = universo[col_r].apply(parsear_dia_desde_ruta)
    else:
        universo["DiaVisita"] = "SIN RUTA DEFINIDA"
        
    subramo_col = next((c for c in universo.columns if "subramo" in str(c).lower()), None)
    if subramo_col: 
        universo = universo[universo[subramo_col].fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()
        
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

    # 3. Filtrado de No Compradores (NC) y flag de mes anterior
    nc_master = universo[~universo["Cliente"].isin(clientes_validos_set)].copy()
    nc_master["Mes_Anterior"] = nc_master["Cliente"].apply(
        lambda x: "SI" if x in clientes_mes_anterior_set else "NO"
    )

    # 4. Cruce con maestro de vendedores
    vendedores = bases_param["VENDEDORES"].copy()
    vendedores_df = pd.DataFrame()
    vendedores_df["CodVendedor"] = pd.to_numeric(vendedores["CodVend"], errors="coerce").astype("Int64")
    vendedores_df["Preventista"] = vendedores["Nombre"].fillna("").astype(str).str.strip()
    vendedores_df["SUP"] = vendedores["SUP"].fillna("").astype(str).str.strip()
    vendedores_df = vendedores_df.drop_duplicates("CodVendedor")

    nc_enriquecido = nc_master.merge(vendedores_df, on="CodVendedor", how="left")
    
    nc_enriquecido["Preventista"] = nc_enriquecido["Preventista"].fillna("VENDEDOR " + nc_enriquecido["CodVendedor"].astype(str))
    nc_enriquecido["SUP"] = nc_enriquecido["SUP"].fillna("SIN SUP")
    nc_enriquecido["NombreCliente"] = nc_enriquecido["NombreCliente"].fillna("Comercio Activo")
    nc_enriquecido["DireccionCliente"] = nc_enriquecido["DireccionCliente"].fillna("Domicilio Registrado")

    return nc_enriquecido

def dibujar_pestaña_batalla(bases, df_vtas_operativo, supervisores_seleccionados):
    st.subheader("🎯 Panel Operativo: Batalla de Clientes No Compradores (NC)")
    st.markdown("Filtra y rutea la gestión de cobertura crítica por supervisor, preventista y día de la semana.")
    
    # Llamada a la función cacheada interna
    nc_enriquecido = _procesar_universo_nc_cacheado(bases["VTA"], bases["UNIVERSO"], bases["PARAMETROS"], df_vtas_operativo)

    sup_str = [str(s).strip() for s in supervisores_seleccionados]
    nc_enriquecido = nc_enriquecido[nc_enriquecido["SUP"].astype(str).str.strip().isin(sup_str)].copy()

    # 5. Controles e interfaz usuario (filtros reactivos sin st.form)
    v_dispo = sorted(nc_enriquecido["Preventista"].dropna().unique().tolist())
    
    orden_dias_map = {
        "LUNES": 1, "MARTES": 2, "MIÉRCOLES": 3, "JUEVES": 4,
        "VIERNES": 5, "SÁBADO": 6, "DOMINGO": 7, "SIN RUTA DEFINIDA": 8
    }
    d_raw = nc_enriquecido["DiaVisita"].dropna().unique().tolist()
    d_dispo = sorted(d_raw, key=lambda x: orden_dias_map.get(str(x).strip().upper(), 99))

    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        v_selec = crear_filtro_excel("Preventista", v_dispo, "nc_prev")
    with col_f2:
        d_selec = crear_filtro_excel("Día Visita", d_dispo, "nc_dia")
        
    if not v_selec:
        v_selec = v_dispo
    if not d_selec:
        d_selec = d_dispo

    nc_filtrado = nc_enriquecido[
        nc_enriquecido["Preventista"].astype(str).str.strip().isin(v_selec) & 
        nc_enriquecido["DiaVisita"].astype(str).str.strip().isin(d_selec)
    ].copy()
    
    total_nc = len(nc_filtrado)
    conteo_tax = nc_filtrado["Taxonomia"].value_counts()
    
    cant_a = conteo_tax.get("A", 0)
    cant_b = conteo_tax.get("B", 0)
    cant_c = conteo_tax.get("C", 0)
    cant_d = conteo_tax.get("D", 0)
    
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

    col_m1, col_m2, col_m3 = st.columns([1.0, 2.2, 1.4])
    
    with col_m1: 
        st.metric("📕 Comercios NC", f"{total_nc:,}")
        
    with col_m2: 
        st.markdown('<div class="sub-label">Taxonomías (NC)</div>', unsafe_allow_html=True)
        c_a, c_b, c_c, c_d = st.columns(4)
        with c_a:
            st.markdown(f'<div class="tax-box-sm tax-a"><span style="font-size:11px;">A</span><br>{cant_a}</div>', unsafe_allow_html=True)
        with c_b:
            st.markdown(f'<div class="tax-box-sm tax-b"><span style="font-size:11px;">B</span><br>{cant_b}</div>', unsafe_allow_html=True)
        with c_c:
            st.markdown(f'<div class="tax-box-sm tax-c"><span style="font-size:11px;">C</span><br>{cant_c}</div>', unsafe_allow_html=True)
        with c_d:
            st.markdown(f'<div class="tax-box-sm tax-d"><span style="font-size:11px;">D</span><br>{cant_d}</div>', unsafe_allow_html=True)
        
    with col_m3: 
        st.markdown('<div class="sub-label">🔍 Buscar ID / Razón Social:</div>', unsafe_allow_html=True)
        busqueda = st.text_input("", key="nc_busq_f", label_visibility="collapsed")
    
    if busqueda:
        nc_filtrado = nc_filtrado[
            nc_filtrado["Cliente"].astype(str).str.contains(busqueda) | 
            nc_filtrado["NombreCliente"].astype(str).str.contains(busqueda, case=False)
        ]
        
    def formatear_detalle(selec, total_disp):
        if not selec:
            return "NINGUNO"
        if len(selec) == len(total_disp):
            return "TODOS"
        return ", ".join(map(str, selec))

    prev_res = formatear_detalle(v_selec, v_dispo)
    dia_res = formatear_detalle(d_selec, d_dispo)
    
    st.markdown(
        f"""
        <div style="background-color: #1e293b; padding: 12px; border-radius: 6px; font-size: 13px; border: 1px solid #475569; color: #f8fafc; margin-top: 10px; margin-bottom: 10px;">
            <b style="color: #38bdf8;">📋 Resumen de Filtros Aplicados:</b><br>
            • <b>Preventista:</b> <span style="color: #e2e8f0;">{prev_res}</span><br>
            • <b>Día Visita:</b> <span style="color: #e2e8f0;">{dia_res}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
        
    # 6. Tabla y descarga Excel
    columnas_vista_nc = ["SUP", "CodVendedor", "Preventista", "Cliente", "NombreCliente", "DireccionCliente", "Taxonomia", "DiaVisita", "Mes_Anterior"]
    nc_render = nc_filtrado[columnas_vista_nc].sort_values(by=["DiaVisita", "Preventista", "Taxonomia"]).reset_index(drop=True)
    
    if not nc_render.empty:
        gb = GridOptionsBuilder.from_dataframe(nc_render)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=130)
        gb.configure_column("SUP", headerName="SUP", width=80)
        gb.configure_column("CodVendedor", headerName="Cód. Vend", width=100, valueFormatter="x != null ? Number(x).toFixed(0) : ''")
        gb.configure_column("Preventista", headerName="Preventista", minWidth=180)
        gb.configure_column("Cliente", headerName="ID Cliente", width=110, valueFormatter="x != null ? Number(x).toFixed(0) : ''")
        gb.configure_column("NombreCliente", headerName="Razón Social / Comercio", minWidth=220)
        gb.configure_column("DireccionCliente", headerName="Ubicación / Domicilio", minWidth=200)
        gb.configure_column("Taxonomia", headerName="Tax", width=80)
        gb.configure_column("DiaVisita", headerName="Día Visita", width=120)
        
        estilo_celda_js = JsCode("""
        function(params) {
            if (params.value === 'SI') {
                return {'backgroundColor': '#28a745', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'};
            } else if (params.value === 'NO') {
                return {'backgroundColor': '#E63946', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'};
            }
            return null;
        }
        """)
        gb.configure_column("Mes_Anterior", headerName="Mes Anterior", width=130, cellStyle=estilo_celda_js)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        
        grid_options = gb.build()
        AgGrid(
            nc_render,
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
        st.info("No se encontraron comercios NC con los filtros seleccionados.")
    
    buffer_nc = io.BytesIO()
    with pd.ExcelWriter(buffer_nc, engine="openpyxl") as writer:
        nc_render.to_excel(writer, index=False, sheet_name="Ruteo_Clientes_NC")
    buffer_nc.seek(0)
    
    st.download_button(
        label="📥 Descargar Ruteo NC a Excel", 
        data=buffer_nc, 
        file_name="Ruteo_Clientes_No_Compradores.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        key="nc_btn_dl"
    )