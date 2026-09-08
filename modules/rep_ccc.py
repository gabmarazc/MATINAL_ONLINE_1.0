# modules/rep_ccc.py
import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.rep_kilos import preparar_datos_ventas_segmento

def _calcular_base_ccc(df_vta, df_universo, vendedores, hoja_ccc_param, anio_op, mes_op, dia_matinal):
    hoja_ccc = hoja_ccc_param.copy() if hoja_ccc_param is not None and not hoja_ccc_param.empty else pd.DataFrame(columns=["Taxonomia", "OBJ_CCC"])
    if not hoja_ccc.empty:
        hoja_ccc.columns = hoja_ccc.columns.astype(str).str.strip()
        rename_metas = {}
        for c in hoja_ccc.columns:
            if str(c).lower() in ["obj", "objetivo", "obj_ccc", "obj_pepsico", "kilos", "cantidad"]:
                rename_metas[c] = "OBJ_CCC"
            if str(c).lower() in ["taxonomia", "taxonomía", "categoria", "categoría"]:
                rename_metas[c] = "Taxonomia"
        hoja_ccc = hoja_ccc.rename(columns=rename_metas)
        if "Taxonomia" in hoja_ccc.columns:
            hoja_ccc["Taxonomia"] = hoja_ccc["Taxonomia"].astype(str).str.strip().str.upper()
        if "OBJ_CCC" in hoja_ccc.columns:
            hoja_ccc["OBJ_CCC"] = pd.to_numeric(hoja_ccc["OBJ_CCC"], errors="coerce").fillna(0.0)
            hoja_ccc = hoja_ccc[["Taxonomia", "OBJ_CCC"]].drop_duplicates("Taxonomia")
        else:
            hoja_ccc["OBJ_CCC"] = 0.0
    else:
        hoja_ccc = pd.DataFrame({"Taxonomia": ["A", "B", "C", "D"], "OBJ_CCC": [0.0, 0.0, 0.0, 0.0]})

    try:
        df_ausencias = db.cargar_tabla_sql("SELECT * FROM ausencias")
    except Exception:
        df_ausencias = pd.DataFrame()

    df_vta_prep = preparar_datos_ventas_segmento(df_vta, df_ausencias, anio_op, mes_op, dia_matinal)
    ventas_periodo = df_vta_prep[df_vta_prep["Periodo"].isin(["Arrastre", "Actual"])].copy() if not df_vta_prep.empty and "Periodo" in df_vta_prep.columns else df_vta_prep.copy()

    if not ventas_periodo.empty:
        col_c_orig = next((c for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"] if c in ventas_periodo.columns), "Cliente")
        ventas_periodo["Cliente"] = pd.to_numeric(ventas_periodo[col_c_orig], errors="coerce").astype("Int64")
        col_kg = next((c for c in ["PesoKg", "CantBase", "Cantidad", "Kilos"] if c in ventas_periodo.columns), "PesoKg")
        ventas_periodo["_peso_calc"] = pd.to_numeric(ventas_periodo[col_kg], errors="coerce").fillna(0.0)

        clientes_g = ventas_periodo.groupby("Cliente", as_index=False).agg(Total_Peso=("_peso_calc", "sum"))
        clientes_g["Es_CCC"] = clientes_g["Total_Peso"].gt(0)
    else:
        clientes_g = pd.DataFrame(columns=["Cliente", "Es_CCC"])

    universo = df_universo.copy() if df_universo is not None else pd.DataFrame()
    if not universo.empty:
        cols_u = [str(c).strip().lower() for c in universo.columns]
        col_prov_u = next((universo.columns[i] for i, c in enumerate(cols_u) if c in ["proveedor", "fabricante", "empresa"]), None)
        if col_prov_u:
            spu = universo[col_prov_u]
            if isinstance(spu, pd.DataFrame): spu = spu.iloc[:, 0]
            universo = universo[spu.astype(str).str.contains("pepsico", case=False, na=False)].copy()

        col_sub_u = next((c for c in universo.columns if "subramo" in str(c).lower()), None)
        if col_sub_u:
            ssu = universo[col_sub_u]
            if isinstance(ssu, pd.DataFrame): ssu = ssu.iloc[:, 0]
            universo = universo[ssu.fillna("").astype(str).str.strip().str.casefold().ne("empleados")].copy()

        pos_v_u = next((c for c in ["codven", "CodVendedor", "CodVend", "Vendedor", "cod_vendedor"] if c in universo.columns), None)
        if pos_v_u:
            sv_u = universo[pos_v_u]
            if isinstance(sv_u, pd.DataFrame): sv_u = sv_u.iloc[:, 0]
            universo["CodVendedor"] = pd.to_numeric(sv_u, errors="coerce").astype("Int64")

        tax_col = next((c for c in universo.columns if "taxonomia" in str(c).lower() or "segmentoclientecodigo" in str(c).lower() or "clasificacion" in str(c).lower()), None)
        if tax_col:
            stx = universo[tax_col]
            if isinstance(stx, pd.DataFrame): stx = stx.iloc[:, 0]
            universo["Taxonomia"] = stx.fillna("").astype(str).str.strip().str.upper()
        else:
            universo["Taxonomia"] = "A"

        cli_col_u = next((c for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"] if c in universo.columns), universo.columns[0])
        scli_u = universo[cli_col_u]
        if isinstance(scli_u, pd.DataFrame): scli_u = scli_u.iloc[:, 0]
        universo["Cliente"] = pd.to_numeric(scli_u, errors="coerce").astype("Int64")
        universo = universo[universo["Taxonomia"].isin(["A", "B", "C", "D"])].dropna(subset=["Cliente", "CodVendedor"])

    if not universo.empty and "CodVendedor" in universo.columns:
        universo["CodVendedor"] = pd.to_numeric(universo["CodVendedor"], errors="coerce").astype("Int64")

    if not universo.empty and not clientes_g.empty:
        universo = universo.merge(clientes_g[["Cliente", "Es_CCC"]], on="Cliente", how="left")
        universo["Es_CCC"] = universo["Es_CCC"].fillna(False)
    else:
        universo["Es_CCC"] = False

    cartera_matriz = universo.groupby(["CodVendedor", "Taxonomia"], as_index=False).agg(
        Cartera_Total=("Cliente", "count"),
        CCC=("Es_CCC", lambda x: int(x.sum()))
    ) if not universo.empty and "CodVendedor" in universo.columns else pd.DataFrame(columns=["CodVendedor", "Taxonomia", "Cartera_Total", "CCC"])

    vendedores_df = pd.DataFrame()
    col_c_v = next((c for c in ["Codigo_Vendedor", "CodVend", "CodVendedor"] if c in vendedores.columns), vendedores.columns[0])
    col_n_v = next((c for c in ["Nombre_Vendedor", "Nombre"] if c in vendedores.columns), vendedores.columns[1])
    col_s_v = next((c for c in ["Supervisor", "SUP"] if c in vendedores.columns), vendedores.columns[2] if len(vendedores.columns) > 2 else vendedores.columns[1])

    sv_c = vendedores[col_c_v]
    if isinstance(sv_c, pd.DataFrame): sv_c = sv_c.iloc[:, 0]
    vendedores_df["CodVendedor"] = pd.to_numeric(sv_c, errors="coerce").astype("Int64")
    sv_n = vendedores[col_n_v]
    if isinstance(sv_n, pd.DataFrame): sv_n = sv_n.iloc[:, 0]
    vendedores_df["Nombre"] = sv_n.fillna("").astype(str).str.strip()
    sv_s = vendedores[col_s_v]
    if isinstance(sv_s, pd.DataFrame): sv_s = sv_s.iloc[:, 0]
    vendedores_df["SUP"] = sv_s.fillna("").astype(str).str.strip()
    vendedores_df = vendedores_df.drop_duplicates("CodVendedor")

    df_det_nc = universo.merge(vendedores_df, on="CodVendedor", how="left") if not universo.empty and not vendedores_df.empty else pd.DataFrame()

    taxonomias_df = pd.DataFrame({"Taxonomia": ["A", "B", "C", "D"]})
    vendedores_df["_k"], taxonomias_df["_k"] = 1, 1
    matriz_base = vendedores_df.merge(taxonomias_df, on="_k").drop(columns="_k")

    reporte = matriz_base.merge(cartera_matriz, on=["CodVendedor", "Taxonomia"], how="left")
    reporte[["Cartera_Total", "CCC"]] = reporte[["Cartera_Total", "CCC"]].fillna(0).astype("Int64")
    reporte["NC"] = (reporte["Cartera_Total"] - reporte["CCC"]).clip(lower=0).astype("Int64")
    reporte["Cobertura_Pct"] = (reporte["CCC"] / reporte["Cartera_Total"].replace(0, pd.NA)).mul(100).fillna(0.0)
    reporte["Total_Cartera_Cia"] = reporte.groupby("Taxonomia")["Cartera_Total"].transform("sum")
    reporte["Participacion_Cartera"] = (reporte["Cartera_Total"] / reporte["Total_Cartera_Cia"].replace(0, pd.NA)).fillna(0.0)

    reporte = reporte.merge(hoja_ccc, on="Taxonomia", how="left")
    reporte["OBJ_CCC"] = reporte["OBJ_CCC"].fillna(0.0)
    reporte["Objetivo_CCC"] = (reporte["Participacion_Cartera"] * reporte["OBJ_CCC"]).fillna(0.0).round(0).astype("Int64")
    reporte["% Cumplimiento Objetivo"] = (reporte["CCC"] / reporte["Objetivo_CCC"].replace(0, pd.NA)).mul(100).fillna(0.0)

    return reporte[["CodVendedor", "Nombre", "SUP", "Taxonomia", "Cartera_Total", "Objetivo_CCC", "CCC", "NC", "Cobertura_Pct", "% Cumplimiento Objetivo"]], df_det_nc

def generar_reporte_ccc_taxonomia(df_vta, df_universo, vendedores, hoja_ccc_param, filtros_globales=None):
    anio_op = int(filtros_globales.get("anio", 2026)) if filtros_globales else 2026
    mes_op = int(filtros_globales.get("mes", 9)) if filtros_globales else 9
    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026") if filtros_globales else "02/09/2026"
    sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip() if filtros_globales else "TODOS"

    clave_cache_estado = f"_ccc_motor_cache_{anio_op}_{mes_op}_{dia_matinal}_{sup_filtro}"
    if clave_cache_estado not in st.session_state:
        rep, det = _calcular_base_ccc(df_vta, df_universo, vendedores, hoja_ccc_param, anio_op, mes_op, dia_matinal)
        st.session_state[clave_cache_estado] = (rep, det)

    rep_cached, det_cached = st.session_state[clave_cache_estado]
    st.session_state["_ccc_df_clientes_detalle"] = det_cached
    return rep_cached

@st.fragment
def render_fragmento_interactivo_ccc(reporte_ccc_base, supervisores_seleccionados):
    """Fragmento aislado de alta velocidad. Multiselects limpios por defecto (vacíos implican el universo total)."""
    if reporte_ccc_base is None or reporte_ccc_base.empty:
        st.info("No hay datos disponibles para procesar el Avance CCC.")
        return

    df_base = reporte_ccc_base
    if supervisores_seleccionados and "SUP" in df_base.columns:
        df_base = df_base[df_base["SUP"].astype(str).str.strip().isin([str(s).strip() for s in supervisores_seleccionados])].copy()

    if df_base.empty:
        st.info("No se encontraron registros para los supervisores seleccionados.")
        return

    v_dispo = sorted(df_base["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    tax_dispo = sorted(df_base["Taxonomia"].dropna().astype(str).str.strip().unique().tolist())

    col_fc1, col_fc2 = st.columns(2)
    with col_fc1:
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], placeholder="Seleccionar preventistas (Todos por defecto)...", key="frag_ccc_vendedor")
    with col_fc2:
        tax_selec = st.multiselect("Taxonomía", options=tax_dispo, default=[], placeholder="Seleccionar taxonomías (Todas por defecto)...", key="frag_ccc_taxonomia")

    if not v_selec:
        v_selec = v_dispo
    if not tax_selec:
        tax_selec = tax_dispo

    reporte_filtrado = df_base[
        df_base["Nombre"].astype(str).str.strip().isin(v_selec) &
        df_base["Taxonomia"].astype(str).str.strip().isin(tax_selec)
    ].copy()

    total_ccc_val = reporte_filtrado["CCC"].sum()
    tot_tax = reporte_filtrado.groupby("Taxonomia")["CCC"].sum()
    cant_a = tot_tax.get("A", 0)
    cant_b = tot_tax.get("B", 0)
    cant_c = tot_tax.get("C", 0)
    cant_d = tot_tax.get("D", 0)

    col_mc1, col_mc2, col_mc3, col_mc4, col_mc5, col_mc6 = st.columns(6)
    col_mc1.metric("📊 Total CCC", f"{total_ccc_val:,.0f}")
    col_mc2.metric("🔴 Taxonomía A", f"{cant_a:,.0f}")
    col_mc3.metric("🟠 Taxonomía B", f"{cant_b:,.0f}")
    col_mc4.metric("🟡 Taxonomía C", f"{cant_c:,.0f}")
    col_mc5.metric("🟢 Taxonomía D", f"{cant_d:,.0f}")
    col_mc6.metric("📋 Registros", f"{len(reporte_filtrado):,}")

    st.divider()

    columnas_visuales_ccc = ["CodVendedor", "Nombre", "SUP", "Taxonomia", "Cartera_Total", "Objetivo_CCC", "CCC", "NC", "Cobertura_Pct", "% Cumplimiento Objetivo"]
    reporte_render = reporte_filtrado[columnas_visuales_ccc].copy()

    if not reporte_render.empty:
        gb = GridOptionsBuilder.from_dataframe(reporte_render)
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
            reporte_render,
            gridOptions=grid_options,
            height=420,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=False
        )
    else:
        st.info("No se encontraron registros de CCC con los filtros seleccionados.")

    st.divider()

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        buffer_ccc = io.BytesIO()
        with pd.ExcelWriter(buffer_ccc, engine="openpyxl") as writer:
            reporte_render.to_excel(writer, index=False, sheet_name="Avance_CCC_Taxonomia")
        buffer_ccc.seek(0)
        st.download_button(
            label="📥 Descargar Avance CCC a Excel",
            data=buffer_ccc,
            file_name="Avance_CCC_Taxonomia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="ccc_frag_btn_dl"
        )

    with col_dl2:
        df_clientes_det = st.session_state.get("_ccc_df_clientes_detalle", pd.DataFrame())
        if not df_clientes_det.empty:
            df_nc = df_clientes_det[df_clientes_det["Es_CCC"] == False].copy()
            if supervisores_seleccionados and "SUP" in df_nc.columns:
                df_nc = df_nc[df_nc["SUP"].astype(str).str.strip().isin([str(s).strip() for s in supervisores_seleccionados])]
            if v_selec and "Nombre" in df_nc.columns:
                df_nc = df_nc[df_nc["Nombre"].astype(str).str.strip().isin(v_selec)]
            if tax_selec and "Taxonomia" in df_nc.columns:
                df_nc = df_nc[df_nc["Taxonomia"].astype(str).str.strip().isin(tax_selec)]
            
            cols_excluir = ["_k", "Es_CCC"]
            cols_nc_final = [c for c in df_nc.columns if c not in cols_excluir]
            df_nc_render = df_nc[cols_nc_final].copy()
        else:
            df_nc_render = pd.DataFrame()

        buffer_nc = io.BytesIO()
        with pd.ExcelWriter(buffer_nc, engine="openpyxl") as writer:
            df_nc_render.to_excel(writer, index=False, sheet_name="Clientes_No_Compradores_NC")
        buffer_nc.seek(0)
        st.download_button(
            label="📥 Descargar Clientes NC a Excel",
            data=buffer_nc,
            file_name="Clientes_No_Compradores_NC.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="nc_frag_btn_dl"
        )

def render_rep_ccc(df_vta, df_universo, filtros_globales=None):
    st.subheader("📊 Avance de Condiciones de Crédito Comercial (CCC) por Taxonomía")
    st.markdown("Analiza la cobertura de Clientes Con Compra (CCC) segmentada por taxonomía y vendedor sobre el universo de cartera.")

    sup_filtro = "TODOS"
    if filtros_globales and isinstance(filtros_globales, dict):
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    except Exception:
        maestro_v = pd.DataFrame()

    if maestro_v.empty:
        col_v_cand = next((c for c in ["CodVendedor", "Cod_Vendedor", "CodVend", "Vendedor", "codven"] if c in df_vta.columns), None)
        v_uniq = df_vta[col_v_cand].dropna().unique() if col_v_cand else [1]
        maestro_v = pd.DataFrame({"Codigo_Vendedor": v_uniq, "Nombre_Vendedor": "VENDEDOR GENERAL", "Supervisor": "GENERAL"})

    try:
        maestro_ccc_param = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
    except Exception:
        maestro_ccc_param = pd.DataFrame(columns=["Taxonomia", "OBJ_CCC"])

    reporte_base = generar_reporte_ccc_taxonomia(df_vta, df_universo, maestro_v, maestro_ccc_param, filtros_globales)
    sups_sel = [sup_filtro] if sup_filtro != "TODOS" else None

    render_fragmento_interactivo_ccc(reporte_base, sups_sel)