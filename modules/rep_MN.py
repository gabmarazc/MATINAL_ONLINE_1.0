# modules/rep_MN.py
import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import parsear_fecha_robusta, extraer_dia_de_ruta

def preparar_ventas_mn(df_vta, df_ausencias, anio_operativo, mes_operativo, dia_matinal):
    """Pipeline de ventas específico para MiNegocio basado en ImporteNetoItem y columna Origen de Vta."""
    df = df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame()
    if df.empty:
        return df

    col_imp = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df.columns), None)
    df["ImporteNetoItem"] = pd.to_numeric(df[col_imp], errors="coerce").fillna(0.0) if col_imp else 0.0

    # Detección robusta de la columna de origen de venta
    col_orig = next((c for c in df.columns if any(k in str(c).lower() for k in ["origen", "canal"])), None)
    if col_orig:
        df["OrigenDeVta"] = df[col_orig].fillna("").astype(str).str.strip()
        df["Es_MiNegocio"] = df["OrigenDeVta"].str.contains("minegocio|mi negocio", case=False, na=False)
    else:
        df["OrigenDeVta"] = ""
        df["Es_MiNegocio"] = False

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

    df = df[df["CodVendedor"] != 20]

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

    return df

def _calcular_base_mn(df_vta, df_universo, vendedores, anio_op, mes_op, dia_matinal):
    try:
        df_ausencias = db.cargar_tabla_sql("SELECT * FROM ausencias")
    except Exception:
        df_ausencias = pd.DataFrame()

    df_vta_prep = preparar_ventas_mn(df_vta, df_ausencias, anio_op, mes_op, dia_matinal)
    ventas_periodo = df_vta_prep[df_vta_prep["Periodo"].isin(["Arrastre", "Actual"])].copy() if not df_vta_prep.empty and "Periodo" in df_vta_prep.columns else df_vta_prep.copy()

    dia_mat_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(dia_mat_dt) and not ventas_periodo.empty and "FechaEntrega_dt" in ventas_periodo.columns:
        ventas_periodo = ventas_periodo[ventas_periodo["FechaEntrega_dt"].dt.date < dia_mat_dt.date()]

    if not ventas_periodo.empty:
        col_c_orig = next((c for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"] if c in ventas_periodo.columns), "Cliente")
        ventas_periodo["Cliente"] = pd.to_numeric(ventas_periodo[col_c_orig], errors="coerce").astype("Int64")
        
        clientes_g = ventas_periodo.groupby("Cliente", as_index=False).agg(
            Ventas_Totales=("ImporteNetoItem", "sum"),
            Ventas_MiNegocio=("ImporteNetoItem", lambda x: x[ventas_periodo.loc[x.index, "Es_MiNegocio"]].sum())
        )
        clientes_g["Pct_MiNegocio"] = (clientes_g["Ventas_MiNegocio"] / clientes_g["Ventas_Totales"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    else:
        clientes_g = pd.DataFrame(columns=["Cliente", "Ventas_Totales", "Ventas_MiNegocio", "Pct_MiNegocio"])

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
            universo["DiaVisita"] = sr_u.apply(extraer_dia_de_ruta)
        else:
            universo["DiaVisita"] = "SIN DÍA"

        cli_col_u = next((c for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"] if c in universo.columns), universo.columns[0])
        scli_u = universo[cli_col_u]
        if isinstance(scli_u, pd.DataFrame): scli_u = scli_u.iloc[:, 0]
        universo["Cliente"] = pd.to_numeric(scli_u, errors="coerce").astype("Int64")

        col_nom_cli = next((c for c in ["NombreCliente", "Nombre_Cliente", "RazonSocial", "ClienteDesc"] if c in universo.columns), cli_col_u)
        universo["NombreCliente"] = universo[col_nom_cli].fillna("").astype(str)

        col_dir_cli = next((c for c in ["DireccionCliente", "Direccion", "Domicilio"] if c in universo.columns), None)
        universo["DireccionCliente"] = universo[col_dir_cli].fillna("").astype(str) if col_dir_cli else ""

        universo = universo[universo["Taxonomia"].isin(["A", "B", "C", "D"])].dropna(subset=["Cliente", "CodVendedor"])

    if not universo.empty and "CodVendedor" in universo.columns:
        universo["CodVendedor"] = pd.to_numeric(universo["CodVendedor"], errors="coerce").astype("Int64")
        universo = universo[universo["CodVendedor"] != 20]

    vendedores_df = pd.DataFrame()
    col_c_v = next((c for c in ["Codigo_Vendedor", "CodVend", "CodVendedor"] if c in vendedores.columns), vendedores.columns[0])
    col_n_v = next((c for c in ["Nombre_Vendedor", "Nombre"] if c in vendedores.columns), vendedores.columns[1])
    col_s_v = next((c for c in ["Supervisor", "SUP"] if c in vendedores.columns), vendedores.columns[2] if len(vendedores.columns) > 2 else vendedores.columns[1])

    sv_c = vendedores[col_c_v]
    if isinstance(sv_c, pd.DataFrame): sv_c = sv_c.iloc[:, 0]
    vendedores_df["CodVendedor"] = pd.to_numeric(sv_c, errors="coerce").astype("Int64")
    vendedores_df = vendedores_df[vendedores_df["CodVendedor"] != 20]

    sv_n = vendedores[col_n_v]
    if isinstance(sv_n, pd.DataFrame): sv_n = sv_n.iloc[:, 0]
    vendedores_df["Nombre"] = sv_n.fillna("").astype(str).str.strip()
    sv_s = vendedores[col_s_v]
    if isinstance(sv_s, pd.DataFrame): sv_s = sv_s.iloc[:, 0]
    vendedores_df["SUP"] = sv_s.fillna("").astype(str).str.strip()
    vendedores_df = vendedores_df.drop_duplicates("CodVendedor")

    if not universo.empty and not clientes_g.empty:
        df_detalle = universo.merge(clientes_g, on="Cliente", how="left")
    else:
        df_detalle = universo.copy()
        df_detalle["Ventas_Totales"] = 0.0
        df_detalle["Ventas_MiNegocio"] = 0.0
        df_detalle["Pct_MiNegocio"] = 0.0

    df_detalle["Ventas_Totales"] = df_detalle["Ventas_Totales"].fillna(0.0)
    df_detalle["Ventas_MiNegocio"] = df_detalle["Ventas_MiNegocio"].fillna(0.0)
    df_detalle["Pct_MiNegocio"] = df_detalle["Pct_MiNegocio"].fillna(0.0)

    df_detalle = df_detalle.merge(vendedores_df[["CodVendedor", "Nombre", "SUP"]], on="CodVendedor", how="left", suffixes=("_univ", ""))
    if "Nombre" not in df_detalle.columns and "Nombre_univ" in df_detalle.columns:
        df_detalle["Nombre"] = df_detalle["Nombre_univ"]

    return df_detalle

@st.fragment
def render_fragmento_interactivo_mn(df_det):
    v_dispo = sorted(df_det["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    tax_dispo = sorted(df_det["Taxonomia"].dropna().astype(str).str.strip().unique().tolist())

    col_fc1, col_fc2 = st.columns(2)
    with col_fc1:
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], placeholder="Seleccionar preventistas...", key="frag_mn_vendedor")
    with col_fc2:
        tax_selec = st.multiselect("Taxonomía", options=tax_dispo, default=[], placeholder="Seleccionar taxonomías...", key="frag_mn_taxonomia")

    if not v_selec:
        v_selec = v_dispo
    if not tax_selec:
        tax_selec = tax_dispo

    mask = (
        df_det["Nombre"].astype(str).str.strip().isin(v_selec) &
        df_det["Taxonomia"].astype(str).str.strip().isin(tax_selec)
    )
    df_filtrado = df_det[mask].copy()

    tot_ventas_global = float(df_filtrado["Ventas_Totales"].sum())
    tot_mn_global = float(df_filtrado["Ventas_MiNegocio"].sum())
    pct_global = (tot_mn_global / tot_ventas_global * 100.0) if tot_ventas_global > 0 else 0.0

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("💰 Ventas Totales Período", f"${tot_ventas_global:,.2f}")
    with m2:
        st.metric("📱 Ventas MiNegocio", f"${tot_mn_global:,.2f}")
    with m3:
        st.metric("📊 % Adopción Global", f"{pct_global:,.2f}%")

    st.divider()

    st.markdown("### ⚔️ Detalle Caso a Caso por Cliente (Batalla MiNegocio)")
    st.markdown("Listado completo de clientes con sus importes totales, ventas por MiNegocio y porcentaje de utilización de la app.")

    if not df_filtrado.empty:
        df_render = pd.DataFrame()
        df_render["Cód. Vend"] = df_filtrado.get("CodVendedor", pd.Series())
        df_render["Preventista"] = df_filtrado.get("Nombre", pd.Series())
        df_render["SUP"] = df_filtrado.get("SUP", pd.Series())
        df_render["Cód. Cliente"] = df_filtrado.get("Cliente", pd.Series())
        df_render["Razón Social"] = df_filtrado.get("NombreCliente", pd.Series())
        df_render["Dirección"] = df_filtrado.get("DireccionCliente", pd.Series())
        df_render["Taxonomía"] = df_filtrado.get("Taxonomia", pd.Series())
        df_render["Ventas Totales ($)"] = df_filtrado.get("Ventas_Totales", pd.Series())
        df_render["Ventas MiNegocio ($)"] = df_filtrado.get("Ventas_MiNegocio", pd.Series())
        df_render["% MiNegocio"] = df_filtrado.get("Pct_MiNegocio", pd.Series())

        df_render = df_render.reset_index(drop=True)

        gb = GridOptionsBuilder.from_dataframe(df_render)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=130)
        
        gb.configure_column("Cód. Vend", width=95)
        gb.configure_column("Preventista", minWidth=160)
        gb.configure_column("SUP", width=80)
        gb.configure_column("Cód. Cliente", width=100)
        gb.configure_column("Razón Social", minWidth=180)
        gb.configure_column("Taxonomía", width=80)

        val_fmt_pesos = "x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0,00'"
        gb.configure_column("Ventas Totales ($)", width=130, valueFormatter=val_fmt_pesos)
        gb.configure_column("Ventas MiNegocio ($)", width=140, valueFormatter=val_fmt_pesos)
        gb.configure_column("% MiNegocio", width=110, valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '%' : '0,00%'")

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
            fit_columns_on_grid_load=False
        )

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_render.to_excel(writer, index=False, sheet_name="Adopcion_MiNegocio_Clientes")
        buffer.seek(0)

        st.download_button(
            label="📥 Descargar Detalle MiNegocio a Excel",
            data=buffer,
            file_name="Adopcion_MiNegocio_Clientes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_dl_mn_excel"
        )
    else:
        st.info("No hay registros para mostrar con los filtros seleccionados.")

def render_rep_mn(df_vta, df_universo, filtros_globales=None):
    st.subheader("📱 Adopción MiNegocio")
    st.markdown("Analiza el porcentaje de ventas operadas a través de la aplicación MiNegocio sobre el total facturado por cliente en el período.")

    anio_op = int(filtros_globales.get("anio", 2026)) if filtros_globales else 2026
    mes_op = int(filtros_globales.get("mes", 9)) if filtros_globales else 9
    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026") if filtros_globales else "02/09/2026"
    sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip() if filtros_globales else "TODOS"

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    except Exception:
        maestro_v = pd.DataFrame()

    cache_key = f"_mn_base_cache_{anio_op}_{mes_op}_{dia_matinal}_{sup_filtro}"
    if cache_key not in st.session_state:
        df_det = _calcular_base_mn(df_vta, df_universo, maestro_v, anio_op, mes_op, dia_matinal)
        st.session_state[cache_key] = df_det
    else:
        df_det = st.session_state[cache_key]

    if df_det.empty:
        st.info("No hay datos disponibles para procesar el reporte de MiNegocio.")
        return

    if sup_filtro != "TODOS" and "SUP" in df_det.columns:
        df_det = df_det[df_det["SUP"].astype(str).str.strip() == sup_filtro].copy()

    if df_det.empty:
        st.info("No se encontraron registros para el supervisor seleccionado.")
        return

    render_fragmento_interactivo_mn(df_det)