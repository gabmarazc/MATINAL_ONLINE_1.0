# modules/rep_cob_marca.py
import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode
from modules import database as db
from modules.rep_kilos import preparar_datos_ventas_segmento

def generar_reporte_cobertura_marca(df_vtas_operativo, df_cartera, vendedores, df_marcas):
    """
    Genera la matriz analítica de Cobertura por Marca utilizando el código de vendedor original de ventas,
    calculando la cartera propia por preventista y evaluando la sumatoria de unidades por cliente (>= 3).
    """
    # 1. Obtención de parámetros operativos vigentes
    df_params = db.cargar_tabla_sql("SELECT * FROM parametros")
    params_map = {}
    if not df_params.empty and "PARAMETRO" in df_params.columns and "VALOR" in df_params.columns:
        params_map = dict(zip(df_params["PARAMETRO"], df_params["VALOR"]))

    anio_op = int(st.session_state.get("sel_anio_op", params_map.get("Año", 2026)))
    mes_op = int(st.session_state.get("sel_mes_op", params_map.get("Mes", 9)))
    
    dia_matinal_default = params_map.get("Dia Matinal", "02/09/2026")
    dia_matinal_obj = st.session_state.get("sel_dia_matinal", dia_matinal_default)
    dia_matinal = dia_matinal_obj.strftime("%d/%m/%Y") if hasattr(dia_matinal_obj, "strftime") else str(dia_matinal_obj)

    # 2. Preparación de ventas estándar con el pipeline oficial
    try:
        df_ausencias = db.cargar_tabla_sql("SELECT * FROM ausencias")
    except Exception:
        df_ausencias = pd.DataFrame()

    df_vta_prep = preparar_datos_ventas_segmento(df_vtas_operativo, df_ausencias, anio_op, mes_op, dia_matinal)

    # 3. Procesamiento del maestro de vendedores oficial
    df_vend = vendedores.copy() if vendedores is not None and not vendedores.empty else pd.DataFrame(columns=["CodVend", "Nombre", "SUP"])
    col_cod_v = next((c for c in ["CodVend", "Codigo_Vendedor", "CodVendedor"] if c in df_vend.columns), df_vend.columns[0])
    col_nom_v = next((c for c in df_vend.columns if "nombre" in str(c).strip().lower()), df_vend.columns[1] if len(df_vend.columns) > 1 else df_vend.columns[0])
    col_sup_v = next((c for c in df_vend.columns if "sup" in str(c).strip().lower() or "supervisor" in str(c).strip().lower()), df_vend.columns[2] if len(df_vend.columns) > 2 else df_vend.columns[0])
    
    df_vend = df_vend.rename(columns={col_cod_v: "CodVendedor", col_nom_v: "Nombre", col_sup_v: "SUP"})
    df_vend["CodVendedor"] = pd.to_numeric(df_vend["CodVendedor"], errors="coerce").astype("Int64")
    df_vend = df_vend[~df_vend["CodVendedor"].isin([20, 99])].drop_duplicates(subset=["CodVendedor"])

    # 4. Extracción estricta del padrón oficial de marcas (maestro_marcas_cebe)
    df_marcas_oficial = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
    if df_marcas_oficial is None or df_marcas_oficial.empty:
        df_marcas_oficial = df_marcas if df_marcas is not None else pd.DataFrame()

    marcas = []
    mapa_objetivos = {}
    if not df_marcas_oficial.empty:
        col_m = next((c for c in df_marcas_oficial.columns if str(c).strip().lower() in ["marca", "marcaupper", "descripcion_marca"]), None)
        if not col_m:
            col_m = next((c for c in df_marcas_oficial.columns if "marca" in str(c).strip().lower()), df_marcas_oficial.columns[0])
            
        for _, row in df_marcas_oficial.iterrows():
            m = str(row.get(col_m, "")).strip().upper()
            if m and m not in ["", "NAN", "NONE", "-NO DEFINIDO-", "-NO DEFINIDO---NO DEFINIDO-"] and m not in marcas:
                marcas.append(m)
                mapa_objetivos[m] = 80.0

    marcas = sorted(marcas)

    # 5. Filtrado de ventas por períodos operativos (Arrastre / Actual)
    vtas = df_vta_prep[df_vta_prep["Periodo"].isin(["Arrastre", "Actual"])].copy() if not df_vta_prep.empty and "Periodo" in df_vta_prep.columns else pd.DataFrame()

    # 6. Procesamiento de Cartera (Universo) para obtener la cartera propia por vendedor
    cartera = df_cartera.copy() if df_cartera is not None and not df_cartera.empty else pd.DataFrame()
    total_cartera = pd.DataFrame(columns=["CodVendedor", "Total_Cartera"])
    
    if not cartera.empty:
        cols_c_str = [str(c).strip().lower() for c in cartera.columns]
        
        col_prov_c = next((cartera.columns[i] for i, c in enumerate(cols_c_str) if c in ["proveedor", "fabricante", "empresa"]), None)
        if col_prov_c:
            cartera = cartera[cartera[col_prov_c].astype(str).str.contains("pepsico", case=False, na=False)].copy()
            
        subramo_col = next((c for c in cartera.columns if "subramo" in str(c).lower()), None)
        if subramo_col:
            cartera = cartera[cartera[subramo_col].fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()
            
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
    
    cliente_col_vtas = next((c for c in ["Cliente", "NroCliente", "CodCliente", "CLIENTE"] if not vtas.empty and c in vtas.columns), "Cliente")

    # 7. Evaluación estricta de Cobertura (Sumatoria por Cliente y Marca >= 3 unidades)
    if not vtas.empty and marcas:
        col_cv = next((c for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor", "CodVend"] if c in vtas.columns), "CodVendedor")
        vtas["CodVendedor"] = pd.to_numeric(vtas[col_cv], errors="coerce").astype("Int64")
        
        col_cant = next((c for c in ["CantBase", "CANTBASE", "Cantidad", "CANTIDAD", "Unidades", "UNIDADES", "PesoKg"] if c in vtas.columns), vtas.columns[0])
        vtas["cantbase"] = pd.to_numeric(vtas[col_cant], errors="coerce").fillna(0.0)
        vtas["Marca"] = vtas["Marca"].astype(str).str.strip().str.upper()
        
        vtas["Cliente"] = pd.to_numeric(vtas[cliente_col_vtas], errors="coerce").astype("Int64")
        vtas = vtas[vtas["Marca"].isin(marcas)].copy()

        vtas_agrupadas = vtas.groupby(["CodVendedor", "Cliente", "Marca"], as_index=False).agg(
            Total_Cant=("cantbase", "sum")
        )

        vtas_filtradas = vtas_agrupadas[
            vtas_agrupadas["Total_Cant"].ge(3)
        ].copy() if not vtas_agrupadas.empty else pd.DataFrame()
    else:
        vtas_filtradas = pd.DataFrame()
    
    # 8. Construcción de la matriz pivote de cobertura por vendedor
    if not vtas_filtradas.empty and "CodVendedor" in vtas_filtradas.columns and "Marca" in vtas_filtradas.columns and "Cliente" in vtas_filtradas.columns:
        conteo_cubiertos = vtas_filtradas.groupby(["CodVendedor", "Marca"])["Cliente"].nunique().reset_index(name="Clientes_Cubiertos")
        pivot_cubiertos = conteo_cubiertos.pivot_table(index="CodVendedor", columns="Marca", values="Clientes_Cubiertos", fill_value=0).reset_index()
        pivot_cubiertos.columns.name = None
    else:
        pivot_cubiertos = pd.DataFrame(columns=["CodVendedor"])
    
    reporte = df_vend[["CodVendedor", "Nombre", "SUP"]].copy()
        
    if not reporte.empty and not total_cartera.empty and "CodVendedor" in total_cartera.columns:
        reporte = reporte.merge(total_cartera, on="CodVendedor", how="left")
    
    reporte["Total_Cartera"] = reporte["Total_Cartera"].fillna(0) if "Total_Cartera" in reporte.columns else 0
    
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
            # Cálculo porcentual exacto escala 0 a 100 frente a la cartera propia del vendedor
            reporte[marca] = (reporte[marca] / total_c).fillna(0.0) * 100.0
        else:
            reporte[marca] = 0.0
        
    base_cols = ["CodVendedor", "Nombre", "SUP", "Total_Cartera"]
    columnas_finales = base_cols + [m for m in marcas if m in reporte.columns]
    reporte = reporte[[c for c in columnas_finales if c in reporte.columns]].rename(columns={"Total_Cartera": "Cartera"})

    # 9. Guardado en caché de sesión para el detalle interactivo de clientes
    if not cartera.empty and not vtas.empty:
        c_cartera = cartera.copy()
        col_cod_cliente_c = next((c for c in c_cartera.columns if "cliente" in c.lower() or "nro" in c.lower() or "codigo" in c.lower()), c_cartera.columns[0])
        c_cartera["Cliente_Cod"] = pd.to_numeric(c_cartera[col_cod_cliente_c], errors="coerce").astype("Int64")
        
        col_desc_cliente = next((c for c in c_cartera.columns if any(k in c.lower() for k in ["razon", "nombre", "desc", "cliente"]) and c != col_cod_cliente_c), col_cod_cliente_c)
        c_cartera["Cliente_Desc"] = c_cartera[col_desc_cliente].fillna("").astype(str)

        enc_vend_c = next((c for c in ["codvendedor", "codvend", "vendedor", "vend"] if c in c_cartera.columns.str.lower()), None)
        if enc_vend_c:
            real_col_v = [c for c in c_cartera.columns if c.lower() == enc_vend_c][0]
            c_cartera["CodVendedor"] = pd.to_numeric(c_cartera[real_col_v], errors="coerce").astype("Int64")

        if "CodVendedor" in c_cartera.columns:
            lista_clientes_cartera = c_cartera[["CodVendedor", "Cliente_Cod", "Cliente_Desc"]].drop_duplicates().copy()
            lista_clientes_cartera = lista_clientes_cartera.merge(df_vend[["CodVendedor", "Nombre"]], on="CodVendedor", how="inner")

            df_expansion = []
            for marca in marcas:
                tmp = lista_clientes_cartera.copy()
                tmp["Marca"] = marca
                df_expansion.append(tmp)
            
            if df_expansion:
                df_matriz_potencial = pd.concat(df_expansion, ignore_index=True)
                vtas_agrup_det = vtas.groupby(["CodVendedor", "Cliente", "Marca"], as_index=False).agg(Unidades_Ultimo_Mes=("cantbase", "sum"))
                
                df_det_merged = df_matriz_potencial.merge(
                    vtas_agrup_det,
                    left_on=["CodVendedor", "Cliente_Cod", "Marca"],
                    right_on=["CodVendedor", "Cliente", "Marca"],
                    how="left"
                )
                df_det_merged["Unidades_Ultimo_Mes"] = df_det_merged["Unidades_Ultimo_Mes"].fillna(0.0)
                df_det_cumplen = df_det_merged[df_det_merged["Unidades_Ultimo_Mes"] >= 3.0].copy()
                df_det_cumplen["Estado"] = "Cumple Objetivo (>= 3 u.)"

                df_det_final = df_det_cumplen[[
                    "Nombre", "Cliente_Cod", "Cliente_Desc", "Marca", "Unidades_Ultimo_Mes", "Estado"
                ]].rename(columns={
                    "Nombre": "Vendedor",
                    "Cliente_Cod": "Cód. Cliente",
                    "Cliente_Desc": "Cliente",
                    "Unidades_Ultimo_Mes": "Unidades"
                }).reset_index(drop=True)
                
                st.session_state["_cache_detalle_clientes_cob"] = df_det_final
    
    return reporte, marcas, mapa_objetivos

@st.fragment
def render_fragmento_interactivo_cobertura_marca(reporte_cobertura, marcas, mapa_objetivos, supervisores_seleccionados):
    """
    Fragmento interactivo de velocidad instantánea. Realiza filtrado vectorial en memoria
    sobre el DataFrame precalculado, eliminando cualquier latencia al operar los multiselects.
    """
    sup_str = [str(s).strip() for s in supervisores_seleccionados]
    if reporte_cobertura is not None and not reporte_cobertura.empty and "SUP" in reporte_cobertura.columns:
        df_filtrado = reporte_cobertura[
            reporte_cobertura["SUP"].astype(str).str.strip().isin(sup_str)
        ].copy()
    else:
        df_filtrado = pd.DataFrame(columns=["CodVendedor", "Nombre", "Cartera", "SUP"])

    v_dispo = sorted(df_filtrado["Nombre"].dropna().astype(str).str.strip().unique().tolist()) if not df_filtrado.empty and "Nombre" in df_filtrado.columns else []

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], placeholder="Seleccionar preventistas...", key="frag_cob_vendedor")
    with col_f2:
        m_selec = st.multiselect("Marca", options=marcas, default=[], placeholder="Seleccionar marcas...", key="frag_cob_marca")

    if not v_selec:
        v_selec = v_dispo
    if not m_selec:
        m_selec = marcas

    if not df_filtrado.empty and v_dispo:
        df_filtrado = df_filtrado[
            df_filtrado["Nombre"].astype(str).str.strip().isin(v_selec)
        ].copy()

    # Métricas y objetivos globales calculados de forma instantánea sobre el DataFrame filtrado
    if marcas and not df_filtrado.empty:
        suma_cartera_global = df_filtrado["Cartera"].sum()
        
        cols_obj_ui = st.columns(min(len(m_selec), 6)) if m_selec else st.columns(1)
        for idx, marca in enumerate(m_selec):
            col_target = cols_obj_ui[idx % len(cols_obj_ui)]
            obj_val = mapa_objetivos.get(marca, 80.0)
            
            if suma_cartera_global > 0 and marca in df_filtrado.columns:
                clientes_cubiertos_ponderados = (df_filtrado[marca] / 100.0 * df_filtrado["Cartera"]).sum()
                cobertura_global_pct = (clientes_cubiertos_ponderados / suma_cartera_global) * 100.0
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

    base_cols = ["CodVendedor", "Nombre", "Cartera", "SUP"]
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
                const objetivo = Number(mapaObj[col]) || 80.0;
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
                    valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '%' : '0,00%'",
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

    # Detalle de clientes instantáneo vía sesión
    st.markdown("### ✅ Detalle de Clientes que Alcanzan el Objetivo de Cobertura")
    st.markdown("Clientes activos en cartera que sí alcanzan el volumen mínimo de compra ($\ge 3$ unidades) en las marcas seleccionadas.")

    df_detalle_clientes = st.session_state.get("_cache_detalle_clientes_cob", pd.DataFrame())
    if not df_detalle_clientes.empty:
        df_det_view = df_detalle_clientes[
            df_detalle_clientes["Vendedor"].isin(v_selec) & 
            df_detalle_clientes["Marca"].isin(m_selec)
        ].copy()

        if not df_det_view.empty:
            st.dataframe(df_det_view, use_container_width=True, hide_index=True)

            buffer_batalla = io.BytesIO()
            with pd.ExcelWriter(buffer_batalla, engine="openpyxl") as writer:
                df_det_view.to_excel(writer, index=False, sheet_name="Clientes_Cumplen_Objetivo")
            buffer_batalla.seek(0)

            st.download_button(
                label="📥 Descargar Clientes Cubiertos a Excel",
                data=buffer_batalla,
                file_name="Clientes_Cumplen_Objetivo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_dl_batalla"
            )
        else:
            st.info("No se registran clientes que cumplan con el mínimo de 3 unidades para los filtros seleccionados.")
    else:
        st.info("No hay datos de clientes suficientes para calcular el detalle.")

def dibujar_pestana_cobertura_marca(reporte_cobertura, marcas, mapa_objetivos, supervisores_seleccionados, df_vtas_operativo=None, df_cartera=None):
    st.subheader("🎯 Cobertura Por Marca y Detalle de Clientes")
    sup_sel_efectivo = supervisores_seleccionados if isinstance(supervisores_seleccionados, list) else [supervisores_seleccionados]
    render_fragmento_interactivo_cobertura_marca(reporte_cobertura, marcas, mapa_objetivos, sup_sel_efectivo)