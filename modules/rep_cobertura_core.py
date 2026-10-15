# modules/rep_cobertura_core.py

import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode

from modules.core.core_cobertura import (
    obtener_base_cobertura,
    aplicar_regla_elemento_cobertura,
    construir_agregado_cobertura,
    construir_matriz_cobertura,
)
from modules.utils import parsear_fecha_robusta
from modules import database as db


@st.cache_data(show_spinner=False)
def obtener_maestro_marcas_cebe_sql() -> pd.DataFrame:
    try:
        df = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def obtener_maestro_innovaciones_sql() -> pd.DataFrame:
    try:
        df = db.cargar_tabla_sql("SELECT * FROM maestro_innovaciones")
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    return pd.DataFrame()


def _construir_matriz_batalla_completa(
    df_cartera_uniq: pd.DataFrame,
    df_agregado: pd.DataFrame,
    lista_elementos: list,
    clientes_del_dia: set,
) -> pd.DataFrame:
    """
    Construye la Vista Batalla completa para TODOS los clientes de la cartera.
    Reutiliza df_cartera_uniq ya deduplicada y normalizada en render_rep_cobertura_core.
    Cada celda contiene el Total_Cant vendido (0 si no compró).
    Garantiza una fila por cliente y columnas por cada elemento de cobertura.
    """
    cols_fijas = [
        "Vendedor",
        "Cod Cliente",
        "Cliente",
        "Direccion",
        "DiaVisita",
        "DelDia",
    ]
    if df_cartera_uniq is None or df_cartera_uniq.empty or not lista_elementos:
        return pd.DataFrame(columns=cols_fijas + list(lista_elementos))

    df_base = df_cartera_uniq.copy()

    has_razon = "Razon_Social" in df_base.columns
    has_nombre_cli = "NombreCliente" in df_base.columns
    has_dir = "Direccion" in df_base.columns
    has_dia = "DiaVisita" in df_base.columns
    has_vend_nom = "Nombre" in df_base.columns

    # Resolución institucional de Cliente: Razon_Social -> NombreCliente -> Código como fallback
    s_core = df_base["_join_cli"].astype(str)
    if has_razon and has_nombre_cli:
        s_razon = df_base["Razon_Social"].fillna("").astype(str).str.strip()
        s_nombre = df_base["NombreCliente"].fillna("").astype(str).str.strip()
        df_base["Cliente"] = (
            s_razon.replace("", pd.NA)
            .combine_first(s_nombre.replace("", pd.NA))
            .combine_first(s_core)
            .fillna(s_core)
        )
    elif has_razon:
        s_razon = df_base["Razon_Social"].fillna("").astype(str).str.strip()
        df_base["Cliente"] = (
            s_razon.replace("", pd.NA).combine_first(s_core).fillna(s_core)
        )
    elif has_nombre_cli:
        s_nombre = df_base["NombreCliente"].fillna("").astype(str).str.strip()
        df_base["Cliente"] = (
            s_nombre.replace("", pd.NA).combine_first(s_core).fillna(s_core)
        )
    else:
        df_base["Cliente"] = s_core

    df_base["Vendedor"] = (
        df_base["Nombre"].fillna("").astype(str).str.strip()
        if has_vend_nom
        else df_base["_join_vend"].astype(str)
    )
    df_base["Cod Cliente"] = df_base["_join_cli"].astype(int)
    df_base["Direccion"] = (
        df_base["Direccion"].fillna("").astype(str).str.strip() if has_dir else ""
    )
    df_base["DiaVisita"] = (
        df_base["DiaVisita"].fillna("SIN DÍA").astype(str).str.strip()
        if has_dia
        else "SIN DÍA"
    )
    df_base["DiaVisita"] = df_base["DiaVisita"].replace("", "SIN DÍA")
    df_base["DelDia"] = (
        df_base["_join_cli"].isin(clientes_del_dia).map({True: "SI", False: "NO"})
    )

    df_batalla = df_base[["_join_vend", "_join_cli"] + cols_fijas].copy()

    if df_agregado is not None and not df_agregado.empty:
        df_ag = df_agregado[
            df_agregado["ElementoCobertura"].isin(lista_elementos)
        ].copy()
        if not df_ag.empty:
            piv_cant = (
                df_ag.groupby(["CodVendedorCore", "ClienteCore", "ElementoCobertura"])[
                    "Total_Cant"
                ]
                .max()
                .unstack(fill_value=0)
                .reset_index()
            )
            piv_cant.columns.name = None

            df_batalla = df_batalla.merge(
                piv_cant,
                left_on=["_join_vend", "_join_cli"],
                right_on=["CodVendedorCore", "ClienteCore"],
                how="left",
            )
            if "CodVendedorCore" in df_batalla.columns:
                df_batalla.drop(
                    columns=["CodVendedorCore", "ClienteCore"], inplace=True
                )

    for el in lista_elementos:
        if el not in df_batalla.columns:
            df_batalla[el] = 0
        else:
            df_batalla[el] = (
                pd.to_numeric(df_batalla[el], errors="coerce").fillna(0).astype(int)
            )

    df_batalla.drop(columns=["_join_vend", "_join_cli"], inplace=True)
    return df_batalla[cols_fijas + list(lista_elementos)].copy()


@st.fragment
def render_fragmento_interactivo_cobertura(
    estructuras_cobertura: dict,
    vendedores_disponibles: list,
    dias_visita_disp: list,
):
    """
    Fragmento interactivo de Cobertura.
    Opera EXCLUSIVAMENTE sobre estructuras y matrices ya precalculadas y pivotadas.
    Cualquier interacción de filtros solo realiza slicing y filtrado de DataFrames en memoria.
    No ejecuta ninguna función de core_cobertura ni pivot_table.
    """
    # Contenedor en cuerpo principal de pestaña (Sin intrusión en st.sidebar)
    with st.container():
        st.markdown("#### 🎛️ Filtros de Cobertura")
        col_c1, col_c2, col_c3, col_c4 = st.columns([1.2, 2.0, 1.5, 1.3])

        with col_c1:
            tipo_cobertura = st.selectbox(
                "Tipo Cobertura", options=["MARCA", "INNOVACION"], key="cob_tipo_filtro"
            )

        paquete = estructuras_cobertura.get(tipo_cobertura, {})
        lista_elementos_total = paquete.get("lista_elementos", [])
        mapa_objetivos_empresa = paquete.get("mapa_objetivos", {})
        df_matriz_base = paquete.get("df_matriz", pd.DataFrame())
        df_batalla_base = paquete.get("df_batalla", pd.DataFrame())

        with col_c2:
            placeholder_txt = (
                "Todas las marcas (o seleccione opciones)"
                if tipo_cobertura == "MARCA"
                else "Todas las innovaciones (o seleccione opciones)"
            )
            key_selector = (
                "cob_marcas_filtro" if tipo_cobertura == "MARCA" else "cob_innov_filtro"
            )
            sel_cobertura = st.multiselect(
                f"Cobertura ({tipo_cobertura.capitalize()})",
                options=lista_elementos_total,
                default=[],
                placeholder=placeholder_txt,
                key=key_selector,
            )

        with col_c3:
            sel_vendedor = st.multiselect(
                "Vendedor",
                options=vendedores_disponibles,
                default=[],
                key="cob_vendedor_filtro",
            )

        with col_c4:
            sel_dia_visita = st.multiselect(
                "DiaVisita",
                options=dias_visita_disp,
                default=[],
                key="cob_dia_visita_filtro",
            )

    # 1. Elementos activos seleccionados o todos por defecto
    elementos_activos = sel_cobertura if sel_cobertura else lista_elementos_total

    # 2. Filtrado de Matriz Precalculada Superior (Permanecer exactamente igual)
    df_matriz_render = (
        df_matriz_base.copy() if not df_matriz_base.empty else pd.DataFrame()
    )

    if not df_matriz_render.empty:
        # Filtrado por vendedor
        if sel_vendedor and "Nombre" in df_matriz_render.columns:
            df_matriz_render = df_matriz_render[
                df_matriz_render["Nombre"].isin(sel_vendedor)
            ].copy()

        # Proyección de columnas visibles de cobertura
        cols_fijas = [
            c
            for c in ["CodVendedor", "Nombre", "Cartera", "SUP"]
            if c in df_matriz_render.columns
        ]
        cols_elementos = [
            el for el in elementos_activos if el in df_matriz_render.columns
        ]
        cols_finales = cols_fijas + cols_elementos
        df_matriz_render = df_matriz_render[cols_finales].copy()

    # 3. Filtrado de Vista Batalla PRE-PIVOTADA COMPLETA (TODOS LOS CLIENTES)
    df_batalla_render = (
        df_batalla_base.copy() if not df_batalla_base.empty else pd.DataFrame()
    )

    cols_dinamicas_batalla = []
    if not df_batalla_render.empty:
        # Filtrado de filas por Vendedor
        if sel_vendedor and "Vendedor" in df_batalla_render.columns:
            df_batalla_render = df_batalla_render[
                df_batalla_render["Vendedor"].isin(sel_vendedor)
            ].copy()

        # Filtrado de filas por Día de Visita
        if sel_dia_visita and "DiaVisita" in df_batalla_render.columns:
            df_batalla_render = df_batalla_render[
                df_batalla_render["DiaVisita"].isin(sel_dia_visita)
            ].copy()

        # Proyección de columnas de cobertura sobre matriz ya pivotada (sin eliminar filas de clientes)
        cols_idx = [
            "Vendedor",
            "Cod Cliente",
            "Cliente",
            "Direccion",
            "DiaVisita",
            "DelDia",
        ]
        cols_idx_presentes = [c for c in cols_idx if c in df_batalla_render.columns]
        cols_dinamicas_batalla = [
            c for c in elementos_activos if c in df_batalla_render.columns
        ]

        df_batalla_render = df_batalla_render[
            cols_idx_presentes + cols_dinamicas_batalla
        ].copy()

    if df_matriz_render.empty and df_batalla_render.empty:
        st.warning("No hay datos que coincidan con los filtros seleccionados.")
        return

    # 4. Renderizado de Matriz AgGrid (Superior - Intacta)
    st.subheader("📋 Matriz de Cobertura por Vendedor")

    if not df_matriz_render.empty:
        gb_matriz = GridOptionsBuilder.from_dataframe(df_matriz_render)
        gb_matriz.configure_default_column(
            filterable=True,
            sortable=True,
            resizable=True,
            cellStyle={"textAlign": "center"},
            headerClass="centered-header",
        )
        if "CodVendedor" in df_matriz_render.columns:
            gb_matriz.configure_column("CodVendedor", headerName="Cód. Vend", width=100)
        if "Nombre" in df_matriz_render.columns:
            gb_matriz.configure_column(
                "Nombre",
                headerName="Nombre",
                minWidth=180,
                cellStyle={"textAlign": "left"},
                headerClass="left-header",
            )
        if "Cartera" in df_matriz_render.columns:
            gb_matriz.configure_column("Cartera", headerName="Cartera", width=95)
        if "SUP" in df_matriz_render.columns:
            gb_matriz.configure_column("SUP", headerName="SUP", width=80)

        if tipo_cobertura == "INNOVACION":
            mapa_obj_js = {el: 80.0 for el in elementos_activos}
        else:
            mapa_obj_js = {
                el: float(mapa_objetivos_empresa.get(el, 80.0))
                for el in elementos_activos
            }

        js_objetivos = str(mapa_obj_js)
        cell_style_conditional = JsCode(f"""
        function(params) {{
            const mapaObj = {js_objetivos};
            const col = params.colDef.field;
            const objetivo = Number(mapaObj[col]) || 80.0;
            const valorReal = Number(params.value) || 0;
            if (valorReal >= objetivo) {{
                return {{'backgroundColor': '#d4edda', 'fontWeight': 'bold', 'color': '#155724', 'textAlign': 'center'}};
            }} else {{
                return {{'backgroundColor': '#f8d7da', 'fontWeight': 'bold', 'color': '#721c24', 'textAlign': 'center'}};
            }}
        }}
        """)

        for el in elementos_activos:
            if el in df_matriz_render.columns:
                gb_matriz.configure_column(
                    el,
                    headerName=el,
                    cellStyle=cell_style_conditional,
                    minWidth=120,
                    valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '%' : '0,00%'",
                )

        gb_matriz.configure_pagination(
            paginationAutoPageSize=False, paginationPageSize=15
        )
        grid_options_matriz = gb_matriz.build()

        st.markdown(
            """
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
        """,
            unsafe_allow_html=True,
        )

        AgGrid(
            df_matriz_render,
            gridOptions=grid_options_matriz,
            height=400,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True,
        )

    buffer_matriz = io.BytesIO()
    with pd.ExcelWriter(buffer_matriz, engine="openpyxl") as writer:
        df_matriz_render.to_excel(writer, index=False, sheet_name="Matriz Cobertura")
    buffer_matriz.seek(0)
    excel_matriz = buffer_matriz

    st.download_button(
        label="📥 Descargar Excel Matriz",
        data=excel_matriz,
        file_name=f"matriz_cobertura_{tipo_cobertura.lower()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # 5. Renderizado de Vista Batalla Matricial
    st.subheader("⚔️ Vista Batalla (Clientes de Cartera)")
    st.caption(f"📊 Clientes encontrados: **{len(df_batalla_render)}**")

    if not df_batalla_render.empty:
        gb_batalla = GridOptionsBuilder.from_dataframe(df_batalla_render)
        gb_batalla.configure_default_column(
            filterable=True,
            sortable=True,
            resizable=True,
            cellStyle={"textAlign": "center"},
            headerClass="centered-header",
        )
        if "Vendedor" in df_batalla_render.columns:
            gb_batalla.configure_column(
                "Vendedor",
                headerName="Vendedor",
                minWidth=160,
                cellStyle={"textAlign": "left"},
                headerClass="left-header",
            )
        if "Cod Cliente" in df_batalla_render.columns:
            gb_batalla.configure_column(
                "Cod Cliente", headerName="Cód. Cliente", width=110
            )
        if "Cliente" in df_batalla_render.columns:
            gb_batalla.configure_column(
                "Cliente",
                headerName="Cliente",
                minWidth=180,
                cellStyle={"textAlign": "left"},
                headerClass="left-header",
            )
        if "Direccion" in df_batalla_render.columns:
            gb_batalla.configure_column(
                "Direccion",
                headerName="Dirección",
                minWidth=160,
                cellStyle={"textAlign": "left"},
                headerClass="left-header",
            )
        if "DiaVisita" in df_batalla_render.columns:
            gb_batalla.configure_column("DiaVisita", headerName="Día Visita", width=110)
        if "DelDia" in df_batalla_render.columns:
            gb_batalla.configure_column("DelDia", headerName="Del Día", width=90)

        # Semáforo Oficial:
        # valor <= 0 -> Rojo (#f8d7da)
        # 0 < valor < 3 -> Amarillo (#fff3cd)
        # valor >= 3 -> Verde (#d4edda)
        js_semaforo_batalla = JsCode("""
        function(params) {
            let val = 0;
            if (params.value !== null && params.value !== undefined && params.value !== '') {
                val = Number(params.value);
            }
            if (val <= 0) {
                return {
                    'backgroundColor': '#f8d7da',
                    'color': '#721c24',
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'fontSize': '16px'
                };
            } else if (val > 0 && val < 3) {
                return {
                    'backgroundColor': '#fff3cd',
                    'color': '#856404',
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'fontSize': '16px'
                };
            } else if (val >= 3) {
                return {
                    'backgroundColor': '#d4edda',
                    'color': '#155724',
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'fontSize': '16px'
                };
            }
            return {'textAlign': 'center', 'fontSize': '16px', 'fontWeight': 'bold'};
        }
        """)

        js_formatter_entero = JsCode("""
        function(params) {
            if (params.value === null || params.value === undefined) {
                return '0';
            }
            return String(Math.round(Number(params.value)));
        }
        """)

        # Configuración homogénea de columnas de cobertura: ancho 100, entero sin decimales
        for col_cob in cols_dinamicas_batalla:
            gb_batalla.configure_column(
                col_cob,
                headerName=col_cob,
                cellStyle=js_semaforo_batalla,
                width=100,
                minWidth=90,
                valueFormatter=js_formatter_entero,
            )

        gb_batalla.configure_pagination(
            paginationAutoPageSize=False, paginationPageSize=15
        )
        grid_options_batalla = gb_batalla.build()

        AgGrid(
            df_batalla_render,
            gridOptions=grid_options_batalla,
            height=450,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True,
        )
    else:
        st.info("No se registran clientes para los filtros seleccionados.")

    buffer_batalla = io.BytesIO()
    with pd.ExcelWriter(buffer_batalla, engine="openpyxl") as writer:
        df_batalla_render.to_excel(writer, index=False, sheet_name="Batalla Cobertura")
    buffer_batalla.seek(0)
    excel_batalla = buffer_batalla

    st.download_button(
        label="📥 Descargar Excel Batalla",
        data=excel_batalla,
        file_name=f"batalla_cobertura_{tipo_cobertura.lower()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def render_rep_cobertura_core():
    """
    Punto de entrada institucional invocado por app.py.
    Ejecuta UNA ÚNICA VEZ la lectura de bases, catálogos y el pipeline de cálculo completo.
    Precalcula y pre-pivotea las estructuras matriciales de Matriz y Batalla para TODOS los clientes.
    Delega la interactividad visual al fragmento aislado.
    """
    st.title("📊 Reporte de Cobertura Unificada")
    st.markdown(
        "Análisis institucional de cobertura por **Marca** o **Innovación** basado en preventa y catálogos oficiales."
    )

    df_params = db.cargar_tabla_sql("SELECT * FROM parametros")
    params_map = {}
    if (
        not df_params.empty
        and "PARAMETRO" in df_params.columns
        and "VALOR" in df_params.columns
    ):
        params_map = dict(zip(df_params["PARAMETRO"], df_params["VALOR"]))

    anio_op = int(st.session_state.get("sel_anio_op", params_map.get("Año", 2026)))
    mes_op = int(st.session_state.get("sel_mes_op", params_map.get("Mes", 10)))

    dia_matinal_default = params_map.get("Dia Matinal", "2026-10-06")
    dia_matinal_obj = st.session_state.get("sel_dia_matinal", dia_matinal_default)
    dia_matinal = (
        dia_matinal_obj.strftime("%Y-%m-%d")
        if hasattr(dia_matinal_obj, "strftime")
        else str(dia_matinal_obj)
    )

    dia_venta_raw = params_map.get(
        "Dia Venta", params_map.get("Fecha Venta", dia_matinal)
    )
    dia_venta_obj = st.session_state.get("sel_dia_venta", dia_venta_raw)
    dia_venta = (
        dia_venta_obj.strftime("%Y-%m-%d")
        if hasattr(dia_venta_obj, "strftime")
        else str(dia_venta_obj)
    )

    dia_vta_dt = parsear_fecha_robusta(pd.Series([dia_venta])).iloc[0]
    dias_semana_esp = [
        "LUNES",
        "MARTES",
        "MIERCOLES",
        "JUEVES",
        "VIERNES",
        "SABADO",
        "DOMINGO",
    ]
    dia_venta_nombre = (
        dias_semana_esp[dia_vta_dt.weekday()] if pd.notna(dia_vta_dt) else ""
    )

    with st.spinner("Procesando base de cobertura unificada..."):
        data_cob = obtener_base_cobertura(
            anio_op=int(anio_op),
            mes_op=int(mes_op),
            dia_matinal=dia_matinal,
            dia_venta=dia_venta,
        )

    df_vtas = data_cob.get("ventas", pd.DataFrame())
    df_cartera = data_cob.get("cartera", pd.DataFrame())
    clientes_del_dia = data_cob.get("clientes_del_dia", set())

    if df_vtas.empty or df_cartera.empty:
        st.warning(
            "No se encontraron registros de ventas o cartera para los parámetros seleccionados."
        )
        return

    df_marcas = obtener_maestro_marcas_cebe_sql()
    df_innov = obtener_maestro_innovaciones_sql()

    # 1. Catálogo oficial de Marcas
    lista_marcas = []
    mapa_objetivos_empresa = {}
    if not df_marcas.empty:
        col_m = next(
            (
                c
                for c in df_marcas.columns
                if str(c).strip().lower()
                in ["marca", "marcaupper", "descripcion_marca", "brand"]
            ),
            df_marcas.columns[0],
        )
        for _, row in df_marcas.iterrows():
            m = str(row.get(col_m, "")).strip().upper()
            if (
                m
                and m not in ["", "NAN", "NONE", "-NO DEFINIDO-"]
                and m not in lista_marcas
            ):
                lista_marcas.append(m)
                mapa_objetivos_empresa[m] = float(
                    row.get("Obj_Empresa_Cobertura", 80.0) or 80.0
                )
    elif "Marca" in df_vtas.columns:
        lista_marcas = sorted(
            df_vtas["Marca"].dropna().astype(str).str.strip().unique().tolist()
        )

    # 2. Catálogo oficial de Innovaciones
    lista_innovaciones = []
    mapa_codigo_a_innovacion = {}
    if not df_innov.empty:
        col_i = next(
            (
                c
                for c in ["Innovacion", "INNOVACION", "Descripcion", "Nombre"]
                if c in df_innov.columns
            ),
            df_innov.columns[0],
        )
        lista_innovaciones = sorted(
            df_innov[col_i].dropna().astype(str).str.strip().unique().tolist()
        )
        col_cod = next(
            (
                c
                for c in [
                    "Codigo",
                    "Codigo_Prod",
                    "CodArticulo",
                    "Articulo",
                    "ARTICULO",
                ]
                if c in df_innov.columns
            ),
            None,
        )
        if col_cod:
            for _, row in df_innov.iterrows():
                cod = pd.to_numeric(row.get(col_cod), errors="coerce")
                inv = str(row.get(col_i, "")).strip().upper()
                if pd.notna(cod) and inv:
                    mapa_codigo_a_innovacion[int(cod)] = inv

    # 3. Listados de selección global para el fragmento
    vendedores_disponibles = []
    if "Nombre" in df_cartera.columns:
        vendedores_disponibles = sorted(
            df_cartera["Nombre"].dropna().astype(str).str.strip().unique().tolist()
        )

    dias_visita_disp = []
    if "DiaVisita" in df_cartera.columns:
        dias_visita_disp = sorted(
            df_cartera["DiaVisita"].dropna().astype(str).str.strip().unique().tolist()
        )

    # 4. Deduplicación de cartera única para Vista Batalla
    df_cartera_uniq = df_cartera.copy()
    if (
        "_join_vend" not in df_cartera_uniq.columns
        or "_join_cli" not in df_cartera_uniq.columns
    ):
        col_c_cli = next(
            (
                c
                for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente", "Codigo"]
                if c in df_cartera_uniq.columns
            ),
            "Cliente",
        )
        col_v_cli = next(
            (
                c
                for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"]
                if c in df_cartera_uniq.columns
            ),
            "CodVendedor",
        )
        df_cartera_uniq["_join_cli"] = pd.to_numeric(
            df_cartera_uniq[col_c_cli], errors="coerce"
        ).astype("Int64")
        df_cartera_uniq["_join_vend"] = pd.to_numeric(
            df_cartera_uniq[col_v_cli], errors="coerce"
        ).astype("Int64")

    df_cartera_uniq = df_cartera_uniq.drop_duplicates(
        subset=["_join_vend", "_join_cli"]
    ).copy()

    # 5. PRE-CÁLCULO INSTITUCIONAL (Ejecutado una única vez fuera del fragmento)
    with st.spinner("Precalculando matrices y Vista Batalla de cobertura..."):
        # Rama MARCA completa
        df_trabajo_marca = aplicar_regla_elemento_cobertura(
            df_vtas=df_vtas,
            df_cartera=df_cartera,
            tipo_cobertura="MARCA",
            df_marcas=df_marcas,
            df_innov=df_innov,
            mapa_codigo_a_innovacion=mapa_codigo_a_innovacion,
        )
        df_agregado_marca = construir_agregado_cobertura(df_trabajo_marca)
        df_matriz_marca = construir_matriz_cobertura(
            df_cartera_m=df_cartera,
            df_agregado=df_agregado_marca,
            elementos_activos=lista_marcas,
            tipo_cobertura="MARCA",
            mapa_objetivos_empresa=mapa_objetivos_empresa,
        )
        # Vista Batalla completa MARCA (reutiliza df_cartera_uniq ya deduplicada)
        df_batalla_marca_piv = _construir_matriz_batalla_completa(
            df_cartera_uniq=df_cartera_uniq,
            df_agregado=df_agregado_marca,
            lista_elementos=lista_marcas,
            clientes_del_dia=clientes_del_dia,
        )

        # Rama INNOVACION completa
        df_trabajo_innov = aplicar_regla_elemento_cobertura(
            df_vtas=df_vtas,
            df_cartera=df_cartera,
            tipo_cobertura="INNOVACION",
            df_marcas=df_marcas,
            df_innov=df_innov,
            mapa_codigo_a_innovacion=mapa_codigo_a_innovacion,
        )
        df_agregado_innov = construir_agregado_cobertura(df_trabajo_innov)
        df_matriz_innov = construir_matriz_cobertura(
            df_cartera_m=df_cartera,
            df_agregado=df_agregado_innov,
            elementos_activos=lista_innovaciones,
            tipo_cobertura="INNOVACION",
            mapa_objetivos_empresa=mapa_objetivos_empresa,
        )
        # Vista Batalla completa INNOVACION (reutiliza df_cartera_uniq ya deduplicada)
        df_batalla_innov_piv = _construir_matriz_batalla_completa(
            df_cartera_uniq=df_cartera_uniq,
            df_agregado=df_agregado_innov,
            lista_elementos=lista_innovaciones,
            clientes_del_dia=clientes_del_dia,
        )

    # 6. Empaquetado de estructuras terminadas (Ambas matrices YA PIVOTADAS con TODOS los clientes)
    estructuras_cobertura = {
        "MARCA": {
            "lista_elementos": lista_marcas,
            "mapa_objetivos": mapa_objetivos_empresa,
            "df_matriz": df_matriz_marca,
            "df_batalla": df_batalla_marca_piv,
        },
        "INNOVACION": {
            "lista_elementos": lista_innovaciones,
            "mapa_objetivos": mapa_objetivos_empresa,
            "df_matriz": df_matriz_innov,
            "df_batalla": df_batalla_innov_piv,
        },
    }

    # 7. Invocación del fragmento interactivo aislado
    render_fragmento_interactivo_cobertura(
        estructuras_cobertura=estructuras_cobertura,
        vendedores_disponibles=vendedores_disponibles,
        dias_visita_disp=dias_visita_disp,
    )
