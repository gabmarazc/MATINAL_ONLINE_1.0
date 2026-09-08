# modules/rep_ccc.py
import io
import urllib.parse
import unicodedata
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.rep_kilos import preparar_datos_ventas_segmento, parsear_fecha_robusta

def _extraer_dia_de_ruta(val):
    if pd.isna(val):
        return None
    nfkd = unicodedata.normalize('NFKD', str(val))
    val_clean = "".join([c for c in nfkd if not unicodedata.combining(c)]).upper()
    
    if "LUN" in val_clean: return "LUNES"
    if "MAR" in val_clean: return "MARTES"
    if "MIE" in val_clean: return "MIERCOLES"
    if "JUE" in val_clean: return "JUEVES"
    if "VIE" in val_clean: return "VIERNES"
    if "SAB" in val_clean: return "SABADO"
    if "DOM" in val_clean: return "DOMINGO"
    return "SIN DÍA"

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

    dia_mat_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(dia_mat_dt) and not ventas_periodo.empty and "FechaEntrega_dt" in ventas_periodo.columns:
        ventas_periodo = ventas_periodo[ventas_periodo["FechaEntrega_dt"].dt.date < dia_mat_dt.date()]

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

        col_ruta_u = next((c for c in universo.columns if str(c).strip().lower() in ["ruta", "dia_visita", "visita", "dia"]), None)
        if col_ruta_u is not None:
            sr_u = universo[col_ruta_u]
            if isinstance(sr_u, pd.DataFrame):
                sr_u = sr_u.iloc[:, 0]
            universo["DiaVisita"] = sr_u.apply(_extraer_dia_de_ruta)
        else:
            universo["DiaVisita"] = "SIN DÍA"

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

    reporte = reporte.sort_values(by=["CodVendedor", "Taxonomia"], ascending=[True, True]).reset_index(drop=True)

    return reporte[["CodVendedor", "Nombre", "SUP", "Taxonomia", "Cartera_Total", "Objetivo_CCC", "CCC", "NC", "Cobertura_Pct", "% Cumplimiento Objetivo"]], df_det_nc

def generar_reporte_ccc_taxonomia(df_vta, df_universo, vendedores, hoja_ccc_param, filtros_globales=None):
    anio_op = int(filtros_globales.get("anio", 2026)) if filtros_globales else 2026
    mes_op = int(filtros_globales.get("mes", 9)) if filtros_globales else 9
    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026") if filtros_globales else "02/09/2026"
    sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip() if filtros_globales else "TODOS"

    keys_to_delete = [k for k in st.session_state.keys() if "_ccc_motor_cache_" in k]
    for k in keys_to_delete:
        del st.session_state[k]

    clave_cache_estado = f"_ccc_motor_cache_v15_{anio_op}_{mes_op}_{dia_matinal}_{sup_filtro}"
    if clave_cache_estado not in st.session_state:
        rep, det = _calcular_base_ccc(df_vta, df_universo, vendedores, hoja_ccc_param, anio_op, mes_op, dia_matinal)
        st.session_state[clave_cache_estado] = (rep, det)

    rep_cached, det_cached = st.session_state[clave_cache_estado]
    st.session_state["_ccc_df_clientes_detalle"] = det_cached
    return rep_cached

def _tarjeta_metrica_html(label, valor, border_color="#475569"):
    return f"""
    <div style="
        background-color: #1e293b;
        border: 2px solid {border_color};
        border-radius: 8px;
        padding: 10px 14px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 8px;
    ">
        <div style="font-size: 0.75rem; color: #94a3b8; font-weight: 600; margin-bottom: 4px; text-transform: uppercase;">{label}</div>
        <div style="font-size: 1.4rem; color: #f8fafc; font-weight: 700;">{valor}</div>
    </div>
    """

@st.fragment
def render_fragmento_interactivo_ccc(reporte_ccc_base, supervisores_seleccionados):
    if reporte_ccc_base is None or reporte_ccc_base.empty:
        st.info("No hay datos disponibles para procesar el Avance de Clientes con Compra.")
        return

    df_clientes_det = st.session_state.get("_ccc_df_clientes_detalle", pd.DataFrame())
    if df_clientes_det.empty:
        st.info("No se encontró el detalle de clientes para el filtrado dinámico.")
        return

    df_base_cli = df_clientes_det.copy()
    if supervisores_seleccionados and "SUP" in df_base_cli.columns:
        df_base_cli = df_base_cli[df_base_cli["SUP"].astype(str).str.strip().isin([str(s).strip() for s in supervisores_seleccionados])].copy()

    if df_base_cli.empty:
        st.info("No se encontraron registros para los supervisores seleccionados.")
        return

    v_dispo = sorted(df_base_cli["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    tax_dispo = sorted(df_base_cli["Taxonomia"].dropna().astype(str).str.strip().unique().tolist())
    
    orden_dias = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO", "SIN DÍA"]
    dias_en_datos = df_base_cli["DiaVisita"].dropna().astype(str).str.strip().unique().tolist() if "DiaVisita" in df_base_cli.columns else []
    dia_visita_dispo = [d for d in orden_dias if d in dias_en_datos]
    for d in dias_en_datos:
        if d not in dia_visita_dispo:
            dia_visita_dispo.append(d)

    col_fc1, col_fc2, col_fc3 = st.columns(3)
    with col_fc1:
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], placeholder="Seleccionar preventistas...", key="frag_ccc_vendedor")
    with col_fc2:
        tax_selec = st.multiselect("Taxonomía", options=tax_dispo, default=[], placeholder="Seleccionar taxonomías...", key="frag_ccc_taxonomia")
    with col_fc3:
        dia_visita_selec = st.multiselect("Día de Visita", options=dia_visita_dispo, default=[], placeholder="Seleccionar días de visita...", key="frag_ccc_dia_visita")

    if not v_selec:
        v_selec = v_dispo
    if not tax_selec:
        tax_selec = tax_dispo
    if not dia_visita_selec:
        dia_visita_selec = dia_visita_dispo

    mask_cli = (
        df_base_cli["Nombre"].astype(str).str.strip().isin(v_selec) &
        df_base_cli["Taxonomia"].astype(str).str.strip().isin(tax_selec) &
        df_base_cli["DiaVisita"].astype(str).str.strip().isin(dia_visita_selec)
    )

    df_cli_filtrado = df_base_cli[mask_cli].copy()

    if not df_cli_filtrado.empty:
        reporte_filtrado = df_cli_filtrado.groupby(["CodVendedor", "Nombre", "SUP", "Taxonomia"], as_index=False).agg(
            Cartera_Total=("Cliente", "count"),
            CCC=("Es_CCC", lambda x: int(x.sum()))
        )
        reporte_filtrado[["Cartera_Total", "CCC"]] = reporte_filtrado[["Cartera_Total", "CCC"]].fillna(0).astype("Int64")
        reporte_filtrado["NC"] = (reporte_filtrado["Cartera_Total"] - reporte_filtrado["CCC"]).clip(lower=0).astype("Int64")
        reporte_filtrado["Cobertura_Pct"] = (reporte_filtrado["CCC"] / reporte_filtrado["Cartera_Total"].replace(0, pd.NA)).mul(100).fillna(0.0)

        objs_originales = reporte_ccc_base[["CodVendedor", "Taxonomia", "Objetivo_CCC"]].drop_duplicates(["CodVendedor", "Taxonomia"])
        reporte_filtrado = reporte_filtrado.merge(objs_originales, on=["CodVendedor", "Taxonomia"], how="left")
        reporte_filtrado["Objetivo_CCC"] = reporte_filtrado["Objetivo_CCC"].fillna(0).astype("Int64")
        reporte_filtrado["% Cumplimiento Objetivo"] = (reporte_filtrado["CCC"] / reporte_filtrado["Objetivo_CCC"].replace(0, pd.NA)).mul(100).fillna(0.0)
        
        reporte_filtrado = reporte_filtrado.sort_values(by=["CodVendedor", "Taxonomia"], ascending=[True, True]).reset_index(drop=True)
    else:
        reporte_filtrado = pd.DataFrame(columns=["CodVendedor", "Nombre", "SUP", "Taxonomia", "Cartera_Total", "Objetivo_CCC", "CCC", "NC", "Cobertura_Pct", "% Cumplimiento Objetivo"])

    tot_cartera = int(df_cli_filtrado["Cliente"].count()) if not df_cli_filtrado.empty else 0
    cartera_tax = df_cli_filtrado.groupby("Taxonomia")["Cliente"].count() if not df_cli_filtrado.empty else pd.Series()
    cart_a = cartera_tax.get("A", 0)
    cart_b = cartera_tax.get("B", 0)
    cart_c = cartera_tax.get("C", 0)
    cart_d = cartera_tax.get("D", 0)

    total_ccc_val = int(df_cli_filtrado["Es_CCC"].sum()) if not df_cli_filtrado.empty and "Es_CCC" in df_cli_filtrado.columns else 0
    tot_tax_ccc = df_cli_filtrado[df_cli_filtrado["Es_CCC"] == True].groupby("Taxonomia")["Cliente"].count() if not df_cli_filtrado.empty else pd.Series()
    cant_a = tot_tax_ccc.get("A", 0)
    cant_b = tot_tax_ccc.get("B", 0)
    cant_c = tot_tax_ccc.get("C", 0)
    cant_d = tot_tax_ccc.get("D", 0)

    cob_total = (total_ccc_val / tot_cartera * 100) if tot_cartera > 0 else 0.0
    cob_a = (cant_a / cart_a * 100) if cart_a > 0 else 0.0
    cob_b = (cant_b / cart_b * 100) if cart_b > 0 else 0.0
    cob_c = (cant_c / cart_c * 100) if cart_c > 0 else 0.0
    cob_d = (cant_d / cart_d * 100) if cart_d > 0 else 0.0

    cols_r1 = st.columns(5)
    with cols_r1[0]:
        st.markdown(_tarjeta_metrica_html("Cartera Total", f"{tot_cartera:,.0f}", "#3b82f6"), unsafe_allow_html=True)
    with cols_r1[1]:
        st.markdown(_tarjeta_metrica_html("Cartera A", f"{cart_a:,.0f}", "#ef4444"), unsafe_allow_html=True)
    with cols_r1[2]:
        st.markdown(_tarjeta_metrica_html("Cartera B", f"{cart_b:,.0f}", "#f97316"), unsafe_allow_html=True)
    with cols_r1[3]:
        st.markdown(_tarjeta_metrica_html("Cartera C", f"{cart_c:,.0f}", "#eab308"), unsafe_allow_html=True)
    with cols_r1[4]:
        st.markdown(_tarjeta_metrica_html("Cartera D", f"{cart_d:,.0f}", "#22c55e"), unsafe_allow_html=True)

    cols_r2 = st.columns(5)
    with cols_r2[0]:
        st.markdown(_tarjeta_metrica_html("Total CCC", f"{total_ccc_val:,.0f}", "#3b82f6"), unsafe_allow_html=True)
    with cols_r2[1]:
        st.markdown(_tarjeta_metrica_html("CCC Tax. A", f"{cant_a:,.0f}", "#ef4444"), unsafe_allow_html=True)
    with cols_r2[2]:
        st.markdown(_tarjeta_metrica_html("CCC Tax. B", f"{cant_b:,.0f}", "#f97316"), unsafe_allow_html=True)
    with cols_r2[3]:
        st.markdown(_tarjeta_metrica_html("CCC Tax. C", f"{cant_c:,.0f}", "#eab308"), unsafe_allow_html=True)
    with cols_r2[4]:
        st.markdown(_tarjeta_metrica_html("CCC Tax. D", f"{cant_d:,.0f}", "#22c55e"), unsafe_allow_html=True)

    cols_r3 = st.columns(5)
    with cols_r3[0]:
        st.markdown(_tarjeta_metrica_html("Cob. Total %", f"{cob_total:,.2f}%", "#3b82f6"), unsafe_allow_html=True)
    with cols_r3[1]:
        st.markdown(_tarjeta_metrica_html("Cob. Tax. A %", f"{cob_a:,.2f}%", "#ef4444"), unsafe_allow_html=True)
    with cols_r3[2]:
        st.markdown(_tarjeta_metrica_html("Cob. Tax. B %", f"{cob_b:,.2f}%", "#f97316"), unsafe_allow_html=True)
    with cols_r3[3]:
        st.markdown(_tarjeta_metrica_html("Cob. Tax. C %", f"{cob_c:,.2f}%", "#eab308"), unsafe_allow_html=True)
    with cols_r3[4]:
        st.markdown(_tarjeta_metrica_html("Cob. Tax. D %", f"{cob_d:,.2f}%", "#22c55e"), unsafe_allow_html=True)

    st.divider()

    columnas_visuales_ccc = ["CodVendedor", "Nombre", "SUP", "Taxonomia", "Cartera_Total", "Objetivo_CCC", "CCC", "NC", "Cobertura_Pct", "% Cumplimiento Objetivo"]
    reporte_render = reporte_filtrado[columnas_visuales_ccc].copy().reset_index(drop=True)

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
        st.info("No se encontraron registros de Clientes con Compra con los filtros seleccionados.")

    st.divider()

    col_dl1, col_dl2, col_dl3 = st.columns(3)
    with col_dl1:
        buffer_ccc = io.BytesIO()
        with pd.ExcelWriter(buffer_ccc, engine="openpyxl") as writer:
            reporte_render.to_excel(writer, index=False, sheet_name="Avance_Clientes_Con_Compra")
        buffer_ccc.seek(0)
        st.download_button(
            label="📥 Descargar Avance a Excel",
            data=buffer_ccc,
            file_name="Avance_Clientes_Con_Compra.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="ccc_frag_btn_dl"
        )

    with col_dl2:
        if not df_cli_filtrado.empty:
            df_nc = df_cli_filtrado[df_cli_filtrado["Es_CCC"] == False].copy()
            cols_excluir = ["_k", "Es_CCC"]
            cols_nc_final = [c for c in df_nc.columns if c not in cols_excluir]
            df_nc_render = df_nc[cols_nc_final].copy().reset_index(drop=True)
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

    with col_dl3:
        if not df_cli_filtrado.empty:
            df_nc_wa = df_cli_filtrado[df_cli_filtrado["Es_CCC"] == False].copy()
            
            cols_disponibles = df_nc_wa.columns.tolist()
            map_cols = {}
            for col in cols_disponibles:
                cl = col.lower()
                if cl in ["cliente", "codcliente", "codigo"]: map_cols["Cliente"] = col
                elif cl in ["nombrecliente", "nombre_cliente", "razonsocial"]: map_cols["NombreCliente"] = col
                elif cl in ["direccioncliente", "direccion", "domicilio"]: map_cols["DireccionCliente"] = col
                elif cl in ["diavisita", "dia_visita", "ruta"]: map_cols["DiaVisita"] = col

            lista_nc_formateada = []
            for idx, row in df_nc_wa.iterrows():
                cli = row.get(map_cols.get("Cliente", "Cliente"), "")
                nom = row.get(map_cols.get("NombreCliente", "NombreCliente"), "")
                dir_c = row.get(map_cols.get("DireccionCliente", "DireccionCliente"), "")
                dia = row.get(map_cols.get("DiaVisita", "DiaVisita"), "")
                
                lista_nc_formateada.append(f"[{cli}] {nom} - {dir_c} - {dia}")

            detalle_texto = "%0A".join(lista_nc_formateada)
            total_nc_cnt = len(df_nc_wa)
            
            texto_wa = f"NC:{total_nc_cnt}%0A{detalle_texto}"
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
            st.markdown('<div style="padding:0.5rem;text-align:center;color:#94a3b8;font-size:0.85rem;">Sin datos para WhatsApp</div>', unsafe_allow_html=True)

def render_rep_ccc(df_vta, df_universo, filtros_globales=None):
    st.subheader("📊 Avance de Clientes con Compra (CCC) por Taxonomía")
    st.markdown("Analiza la cobertura de Clientes con Compra (CCC) segmentada por taxonomía, vendedor y día de visita sobre el universo de cartera.")

    sup_filtro = "TODOS"
    if filtros_globales and isinstance(filtros_globales, dict):
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    except Exception:
        maestro_v = pd.DataFrame()

    try:
        maestro_ccc_param = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
    except Exception:
        maestro_ccc_param = pd.DataFrame(columns=["Taxonomia", "OBJ_CCC"])

    reporte_base = generar_reporte_ccc_taxonomia(df_vta, df_universo, maestro_v, maestro_ccc_param, filtros_globales)
    sups_sel = [sup_filtro] if sup_filtro != "TODOS" else None

    render_fragmento_interactivo_ccc(reporte_base, sups_sel)