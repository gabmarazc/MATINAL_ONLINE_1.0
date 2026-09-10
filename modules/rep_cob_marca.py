# modules/rep_cob_marca.py
import io
import urllib.parse
import unicodedata
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode
from modules import database as db
from modules.utils import parsear_fecha_robusta, extraer_dia_de_ruta_vectorial, tarjeta_metrica_html

def preparar_ventas_cobertura_marca(df_vta, anio_operativo, mes_operativo, dia_matinal):
    """
    Pipeline de ventas nativo para Cobertura por Marca:
    Aplica exclusivamente los filtros de cabecera válidos sin agrupar ni descartar filas por segmentos de kilos.
    """
    df = df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame()
    if df.empty:
        return df

    col_cant = next((c for c in ["CantBase", "CANTBASE", "Cantidad", "CANTIDAD", "Unidades", "UNIDADES"] if c in df.columns), df.columns[0])
    df["cantbase"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0.0)

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

    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    df["FechaEntrega_dt"] = parsear_fecha_robusta(df.get("FechaEntrega"))

    dia_matinal_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(dia_matinal_dt):
        es_mes_en_curso = (dia_matinal_dt.year == anio_operativo and dia_matinal_dt.month in [mes_operativo, mes_operativo + 1])
        if es_mes_en_curso:
            df = df[df["FechaCarga_dt"].dt.date < dia_matinal_dt.date()]

    col_vend_tit = next((cand for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"] if cand in df.columns), "CodVendedor")
    df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype("Int64")

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

    col_m = next((c for c in ["Marca", "MARCA", "marca"] if c in df.columns), None)
    df["Marca"] = df[col_m].fillna("").astype(str).str.strip().str.upper() if col_m else "SIN MARCA"

    return df

def generar_reporte_cobertura_marca(df_vtas_operativo, df_cartera, vendedores, df_marcas, filtros_globales=None):
    """
    Genera la matriz analítica de Cobertura por Marca estructurando la base analítica en memoria
    para posibilitar recalculo instantáneo de cobertura ante cambios de Vendedor, Marca o Día de Visita.
    """
    if filtros_globales:
        anio_op = int(filtros_globales.get("anio", 2026))
        mes_op = int(filtros_globales.get("mes", 9))
        dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026")
    else:
        df_params = db.cargar_tabla_sql("SELECT * FROM parametros")
        params_map = {}
        if not df_params.empty and "PARAMETRO" in df_params.columns and "VALOR" in df_params.columns:
            params_map = dict(zip(df_params["PARAMETRO"], df_params["VALOR"]))

        anio_op = int(st.session_state.get("sel_anio_op", params_map.get("Año", 2026)))
        mes_op = int(st.session_state.get("sel_mes_op", params_map.get("Mes", 9)))
        
        dia_matinal_default = params_map.get("Dia Matinal", "02/09/2026")
        dia_matinal_obj = st.session_state.get("sel_dia_matinal", dia_matinal_default)
        dia_matinal = dia_matinal_obj.strftime("%d/%m/%Y") if hasattr(dia_matinal_obj, "strftime") else str(dia_matinal_obj)

    df_vta_prep = preparar_ventas_cobertura_marca(df_vtas_operativo, anio_op, mes_op, dia_matinal)

    df_vend = vendedores.copy() if vendedores is not None and not vendedores.empty else pd.DataFrame(columns=["CodVend", "Nombre", "SUP"])
    col_cod_v = next((c for c in ["CodVend", "Codigo_Vendedor", "CodVendedor"] if c in df_vend.columns), df_vend.columns[0])
    col_nom_v = next((c for c in df_vend.columns if "nombre" in str(c).strip().lower()), df_vend.columns[1] if len(df_vend.columns) > 1 else df_vend.columns[0])
    col_sup_v = next((c for c in df_vend.columns if "sup" in str(c).strip().lower() or "supervisor" in str(c).strip().lower()), df_vend.columns[2] if len(df_vend.columns) > 2 else df_vend.columns[0])
    
    df_vend = df_vend.rename(columns={col_cod_v: "CodVendedor", col_nom_v: "Nombre", col_sup_v: "SUP"})
    df_vend["CodVendedor"] = pd.to_numeric(df_vend["CodVendedor"], errors="coerce").astype("Int64")
    df_vend = df_vend[~df_vend["CodVendedor"].isin([20, 99])].drop_duplicates(subset=["CodVendedor"])

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

    vtas = df_vta_prep[df_vta_prep["Periodo"].isin(["Arrastre", "Actual"])].copy() if not df_vta_prep.empty and "Periodo" in df_vta_prep.columns else pd.DataFrame()

    cartera = df_cartera.copy() if df_cartera is not None and not df_cartera.empty else pd.DataFrame()
    
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
            
        col_cod_cliente_c = next((c for c in cartera.columns if "cliente" in c.lower() or "nro" in c.lower() or "codigo" in c.lower()), cartera.columns[0])
        cartera["Cliente_Cod"] = pd.to_numeric(cartera[col_cod_cliente_c], errors="coerce").astype("Int64")
        
        col_desc_cliente = next((c for c in cartera.columns if any(k in c.lower() for k in ["razon", "nombre", "desc", "cliente"]) and c != col_cod_cliente_c), None)
        if col_desc_cliente is None:
            col_desc_cliente = col_cod_cliente_c
        cartera["Cliente_Desc"] = cartera[col_desc_cliente].fillna("").astype(str)

        col_dir_c = next((c for c in cartera.columns if any(k in c.lower() for k in ["dir", "domicilio", "direccion"])), None)
        cartera["Cliente_Dir"] = cartera[col_dir_c].fillna("").astype(str) if col_dir_c else ""

        col_ruta_c = next((c for c in cartera.columns if str(c).strip().lower() in ["ruta", "dia_visita", "visita", "dia"]), None)
        if col_ruta_c is not None:
            cartera["DiaVisita"] = extraer_dia_de_ruta_vectorial(cartera[col_ruta_c])
        else:
            cartera["DiaVisita"] = "SIN DÍA"

        cartera = cartera.dropna(subset=["CodVendedor", "Cliente_Cod"]).drop_duplicates(subset=["CodVendedor", "Cliente_Cod"])
        cartera = cartera.merge(df_vend[["CodVendedor", "Nombre", "SUP"]], on="CodVendedor", how="inner")

    cliente_col_vtas = next((c for c in ["Cliente", "NroCliente", "CodCliente", "CLIENTE"] if not vtas.empty and c in vtas.columns), "Cliente")

    if not vtas.empty and marcas:
        vtas["CodVendedor"] = pd.to_numeric(vtas["CodVendedor"], errors="coerce").astype("Int64")
        vtas["Cliente"] = pd.to_numeric(vtas[cliente_col_vtas], errors="coerce").astype("Int64")
        vtas = vtas[vtas["Marca"].isin(marcas)].copy()

        vtas_agrupadas = vtas.groupby(["CodVendedor", "Cliente", "Marca"], as_index=False).agg(
            Total_Cant=("cantbase", "sum")
        )
    else:
        vtas_agrupadas = pd.DataFrame(columns=["CodVendedor", "Cliente", "Marca", "Total_Cant"])

    st.session_state["_cob_cartera_base"] = cartera
    st.session_state["_cob_vtas_agrupadas"] = vtas_agrupadas
    st.session_state["_cob_marcas"] = marcas
    st.session_state["_cob_mapa_objetivos"] = mapa_objetivos
    st.session_state["_cob_vendedores_df"] = df_vend

    return pd.DataFrame(), marcas, mapa_objetivos

@st.fragment
def render_fragmento_interactivo_cobertura_marca(reporte_cobertura_dummy, marcas_param, mapa_objetivos_param, supervisores_seleccionados):
    cartera_base = st.session_state.get("_cob_cartera_base", pd.DataFrame())
    vtas_agrup = st.session_state.get("_cob_vtas_agrupadas", pd.DataFrame())
    marcas = st.session_state.get("_cob_marcas", marcas_param)
    mapa_objetivos = st.session_state.get("_cob_mapa_objetivos", mapa_objetivos_param)

    if cartera_base.empty:
        st.info("No hay datos de cartera disponibles para procesar la Cobertura por Marca.")
        return

    sup_str = [str(s).strip() for s in supervisores_seleccionados]
    cartera_filtrada = cartera_base[cartera_base["SUP"].astype(str).str.strip().isin(sup_str)].copy() if sup_str and "SUP" in cartera_base.columns else cartera_base.copy()

    if cartera_filtrada.empty:
        st.info("No se encontraron registros para los supervisores seleccionados.")
        return

    v_dispo = sorted(cartera_filtrada["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    orden_dias = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO", "SIN DÍA"]
    dias_en_datos = cartera_filtrada["DiaVisita"].dropna().astype(str).str.strip().unique().tolist() if "DiaVisita" in cartera_filtrada.columns else []
    dia_visita_dispo = [d for d in orden_dias if d in dias_en_datos]
    for d in dias_en_datos:
        if d not in dia_visita_dispo:
            dia_visita_dispo.append(d)

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], placeholder="Seleccionar preventistas...", key="frag_cob_vendedor")
    with col_f2:
        m_selec = st.multiselect("Marca", options=marcas, default=[], placeholder="Seleccionar marcas...", key="frag_cob_marca")
    with col_f3:
        dia_visita_selec = st.multiselect("Día de Visita", options=dia_visita_dispo, default=[], placeholder="Seleccionar días de visita...", key="frag_cob_dia_visita")

    if not v_selec:
        v_selec = v_dispo
    if not m_selec:
        m_selec = marcas
    if not dia_visita_selec:
        dia_visita_selec = dia_visita_dispo

    mask_cartera = (
        cartera_filtrada["Nombre"].astype(str).str.strip().isin(v_selec) &
        cartera_filtrada["DiaVisita"].astype(str).str.strip().isin(dia_visita_selec)
    )
    cartera_activa = cartera_filtrada[mask_cartera].copy()

    if cartera_activa.empty:
        st.info("No se encontraron clientes para los filtros seleccionados.")
        return

    cartera_por_vendedor = cartera_activa.groupby(["CodVendedor", "Nombre", "SUP"], as_index=False).agg(
        Cartera=("Cliente_Cod", "nunique")
    )

    clientes_activos = set(cartera_activa["Cliente_Cod"].unique())
    vtas_activas = vtas_agrup[
        vtas_agrup["Cliente"].isin(clientes_activos) &
        vtas_agrup["Marca"].isin(m_selec) &
        vtas_agrup["Total_Cant"].ge(3)
    ].copy() if not vtas_agrup.empty else pd.DataFrame()

    if not vtas_activas.empty:
        cubiertos_pivot = vtas_activas.groupby(["CodVendedor", "Marca"])["Cliente"].nunique().unstack(fill_value=0).reset_index()
        cubiertos_pivot.columns.name = None
    else:
        cubiertos_pivot = pd.DataFrame(columns=["CodVendedor"])

    reporte_matriz = cartera_por_vendedor.merge(cubiertos_pivot, on="CodVendedor", how="left")

    for m in m_selec:
        if m not in reporte_matriz.columns:
            reporte_matriz[m] = 0.0
        else:
            reporte_matriz[m] = reporte_matriz[m].fillna(0.0)
            
        total_c = reporte_matriz["Cartera"].replace(0, pd.NA)
        reporte_matriz[m] = ((reporte_matriz[m] / total_c).fillna(0.0) * 100.0).round(2)

    reporte_matriz = reporte_matriz.sort_values(by="CodVendedor").reset_index(drop=True)

    colores_tarjetas = [
        "#3b82f6", "#ef4444", "#f97316", "#eab308", "#22c55e", "#a855f7", 
        "#ec4899", "#14b8a6", "#6366f1", "#84cc16", "#06b6d4", "#f43f5e"
    ]
    
    suma_cartera_global = reporte_matriz["Cartera"].sum()
    m_selec_ordenadas = [m for m in marcas if m in m_selec]

    if m_selec_ordenadas:
        cols_obj_ui = st.columns(min(len(m_selec_ordenadas), 5))
        for idx, marca in enumerate(m_selec_ordenadas):
            col_target = cols_obj_ui[idx % len(cols_obj_ui)]
            obj_val = mapa_objetivos.get(marca, 80.0)
            
            if suma_cartera_global > 0 and marca in reporte_matriz.columns:
                cubiertos_totales = (reporte_matriz[marca] / 100.0 * reporte_matriz["Cartera"]).sum()
                cobertura_global_pct = (cubiertos_totales / suma_cartera_global) * 100.0
            else:
                cobertura_global_pct = 0.0
                
            color_borde = colores_tarjetas[idx % len(colores_tarjetas)]
            with col_target:
                st.markdown(tarjeta_metrica_html(f"{marca} (Obj: {obj_val:g}%)", f"{cobertura_global_pct:.2f}%", color_borde, "1.4rem", "0.95rem"), unsafe_allow_html=True)
            
        st.divider()

    columnas_finales = ["CodVendedor", "Nombre", "Cartera", "SUP"] + [m for m in m_selec_ordenadas if m in reporte_matriz.columns]
    df_render = reporte_matriz[columnas_finales].copy()

    if not df_render.empty:
        gb = GridOptionsBuilder.from_dataframe(df_render)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=140, cellStyle={'textAlign': 'center'}, headerClass='centered-header')
        gb.configure_column("CodVendedor", headerName="Cód. Vend", width=100)
        gb.configure_column("Nombre", headerName="Nombre", minWidth=200, cellStyle={'textAlign': 'left'}, headerClass='left-header')
        gb.configure_column("Cartera", headerName="Cartera", width=110)
        gb.configure_column("SUP", headerName="SUP", width=90)
        
        js_objetivos = str(mapa_objetivos)
        cell_style_conditional = JsCode(f"""
        function(params) {{
            const mapaObj = {js_objetivos};
            const col = params.colDef.field;
            if (mapaObj.hasOwnProperty(col)) {{
                const objetivo = Number(mapaObj[col]) || 80.0;
                const valorReal = Number(params.value) || 0;
                if (valorReal >= objetivo) {{
                    return {{'backgroundColor': '#d4edda', 'fontWeight': 'bold', 'color': '#155724', 'textAlign': 'center'}};
                }} else {{
                    return {{'backgroundColor': '#f8d7da', 'fontWeight': 'bold', 'color': '#721c24', 'textAlign': 'center'}};
                }}
            }}
            return {{'textAlign': 'center'}};
        }}
        """)
        
        val_fmt_2dec = JsCode("""
        function(params) {
            if (params.value == null || isNaN(params.value)) {
                return '0,00%';
            }
            return Number(params.value).toLocaleString('es-AR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }) + '%';
        }
        """)

        for marca in m_selec_ordenadas:
            if marca in df_render.columns:
                gb.configure_column(
                    marca,
                    headerName=marca,
                    valueFormatter=val_fmt_2dec,
                    cellStyle=cell_style_conditional
                )
                
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
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

    st.markdown("### ⚔️ Batalla Cobertura por Marca")
    st.markdown("Clientes activos en cartera que no alcanzan el volumen mínimo de compra (< 3 unidades) en las marcas seleccionadas.")

    ventas_unidades_map = vtas_agrup.set_index(["CodVendedor", "Cliente", "Marca"])["Total_Cant"].to_dict() if not vtas_agrup.empty else {}

    registros_nc = []
    for m in m_selec_ordenadas:
        for row in cartera_activa.itertuples(index=False):
            cv = int(row.CodVendedor)
            cli = int(row.Cliente_Cod)
            und = ventas_unidades_map.get((cv, cli, m), 0.0)
            if und < 3.0:
                registros_nc.append({
                    "Vendedor": row.Nombre,
                    "Cód. Cliente": cli,
                    "Cliente": row.Cliente_Desc,
                    "Dirección": row.Cliente_Dir,
                    "Día Visita": row.DiaVisita,
                    "Marca": m,
                    "Unidades": und,
                    "Estado": "No Cubierto (< 3 u.)"
                })

    df_det_view = pd.DataFrame(registros_nc)
    total_registros_batalla = len(df_det_view)
    st.caption(f"📊 Registros encontrados: **{total_registros_batalla}**")

    if not df_det_view.empty:
        gb_batalla = GridOptionsBuilder.from_dataframe(df_det_view)
        gb_batalla.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=130, cellStyle={'textAlign': 'center'}, headerClass='centered-header')
        gb_batalla.configure_column("Vendedor", headerName="Vendedor", minWidth=180, cellStyle={'textAlign': 'left'}, headerClass='left-header')
        gb_batalla.configure_column("Cliente", headerName="Cliente", minWidth=180, cellStyle={'textAlign': 'left'}, headerClass='left-header')
        gb_batalla.configure_column("Dirección", headerName="Dirección", minWidth=180, cellStyle={'textAlign': 'left'}, headerClass='left-header')
        gb_batalla.configure_column("Cód. Cliente", headerName="Cód. Cliente", width=110)
        gb_batalla.configure_column("Día Visita", headerName="Día Visita", width=110)
        gb_batalla.configure_column("Marca", headerName="Marca", width=120)
        
        val_fmt_unidades = JsCode("""
        function(params) {
            if (params.value == null || isNaN(params.value)) {
                return '0,00';
            }
            return Number(params.value).toLocaleString('es-AR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
        """)
        gb_batalla.configure_column("Unidades", headerName="Unidades", width=100, valueFormatter=val_fmt_unidades)
        gb_batalla.configure_column("Estado", headerName="Estado", width=160)
        
        gb_batalla.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_options_batalla = gb_batalla.build()

        AgGrid(
            df_det_view,
            gridOptions=grid_options_batalla,
            height=400,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=False,
            allow_unsafe_jscode=True
        )

        col_dl1, col_dl2, col_dl3 = st.columns(3)
        with col_dl1:
            buffer_batalla = io.BytesIO()
            with pd.ExcelWriter(buffer_batalla, engine="openpyxl") as writer:
                df_det_view.to_excel(writer, index=False, sheet_name="Clientes_No_Cubiertos")
            buffer_batalla.seek(0)

            st.download_button(
                label="📥 Descargar Clientes No Cubiertos a Excel",
                data=buffer_batalla,
                file_name="Clientes_No_Cubiertos_Marca.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_dl_batalla_nc"
            )

        with col_dl2:
            pass

        with col_dl3:
            df_wa_limit = df_det_view.head(30)
            lista_nc_formateada = []
            for idx, row in df_wa_limit.iterrows():
                cli = row.get("Cód. Cliente", "")
                nom = row.get("Cliente", "")
                dir_c = row.get("Dirección", "")
                dia_v = row.get("Día Visita", "")
                marca_c = row.get("Marca", "")
                und = row.get("Unidades", 0.0)
                lista_nc_formateada.append(f"[{cli}] {nom} - {dir_c} - {dia_v} - Marca: {marca_c} (U: {und:,.2f})")

            detalle_texto = "%0A".join(lista_nc_formateada)
            aviso_limite = f"%0A(Mostrando 30 de {total_registros_batalla} en WA)" if total_registros_batalla > 30 else ""
            texto_wa = f"NC:{total_registros_batalla}%0A{detalle_texto}{aviso_limite}"
            url_wa = f"https://wa.me/?text={texto_wa}"
            
            st.markdown(f'''
                <div style="display: flex; justify-content: center; align-items: center; height: 100%; padding-top: 5px;">
                    <a href="{url_wa}" target="_blank" style="
                        display: inline-block;
                        padding: 4px 10px;
                        background-color: #25d366;
                        color: white;
                        text-align: center;
                        text-decoration: none;
                        font-weight: 600;
                        font-size: 0.75rem;
                        border-radius: 4px;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    ">💬 WhatsApp NC</a>
                </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("No se registran clientes sin cobertura para los filtros seleccionados.")

def dibujar_pestana_cobertura_marca(reporte_cobertura, marcas, mapa_objetivos, supervisores_seleccionados, df_vtas_operativo=None, df_cartera=None, filtros_globales=None):
    st.subheader("🎯 Cobertura Por Marca y Detalle de Clientes")
    sup_sel_efectivo = supervisores_seleccionados if isinstance(supervisores_seleccionados, list) else [supervisores_seleccionados]
    render_fragmento_interactivo_cobertura_marca(reporte_cobertura, marcas, mapa_objetivos, sup_sel_efectivo)