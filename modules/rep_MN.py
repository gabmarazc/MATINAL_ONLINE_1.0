# modules/rep_MN.py
import io
import urllib.parse
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import parsear_fecha_robusta, extraer_dia_de_ruta

def preparar_ventas_mn(df_vta, df_ausencias, anio_operativo, mes_operativo, dia_matinal):
    """Pipeline de ventas independiente y específico para MiNegocio homologado con CCC."""
    df = df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame()
    if df.empty:
        return df

    col_imp = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df.columns), None)
    df["ImporteNetoItem"] = pd.to_numeric(df[col_imp], errors="coerce").fillna(0.0) if col_imp else 0.0

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

    # Exclusión estricta del vendedor 20
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
        
        # Limpieza rigurosa de ruido de punto flotante en sumas monetarias
        clientes_g["Ventas_Totales"] = clientes_g["Ventas_Totales"].round(2)
        clientes_g["Ventas_MiNegocio"] = clientes_g["Ventas_MiNegocio"].round(2)
        
        clientes_g.loc[clientes_g["Ventas_Totales"] < 0, "Ventas_Totales"] = 0.0
        clientes_g.loc[clientes_g["Ventas_MiNegocio"] < 0, "Ventas_MiNegocio"] = 0.0

        pct_raw = (clientes_g["Ventas_MiNegocio"] / clientes_g["Ventas_Totales"].replace(0, pd.NA)).mul(100.0)
        clientes_g["Pct_MiNegocio"] = pct_raw.clip(lower=0.0, upper=100.0).fillna(0.0).round(2)
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

    # Clasificación de categorías analíticas por cliente basada en el porcentaje limpio y acotado
    df_detalle["Es_NoDigital"] = df_detalle["Pct_MiNegocio"] == 0.0
    df_detalle["Es_Hibrido"] = (df_detalle["Pct_MiNegocio"] > 0.0) & (df_detalle["Pct_MiNegocio"] < 70.0)
    df_detalle["Es_FullyDigital"] = df_detalle["Pct_MiNegocio"] >= 70.0

    # Cálculo del monto mínimo faltante para alcanzar el 70% (Fully Digital) manteniendo ventas totales constantes
    df_detalle["Minimo_Facturacion_70"] = (0.70 * df_detalle["Ventas_Totales"] - df_detalle["Ventas_MiNegocio"]).clip(lower=0.0).round(2)

    df_detalle = df_detalle.merge(vendedores_df[["CodVendedor", "Nombre", "SUP"]], on="CodVendedor", how="left", suffixes=("_univ", ""))
    if "Nombre" not in df_detalle.columns and "Nombre_univ" in df_detalle.columns:
        df_detalle["Nombre"] = df_detalle["Nombre_univ"]

    return df_detalle

def generar_reporte_mn_taxonomia(df_vta, df_universo, vendedores, filtros_globales=None):
    anio_op = int(filtros_globales.get("anio", 2026)) if filtros_globales else 2026
    mes_op = int(filtros_globales.get("mes", 9)) if filtros_globales else 9
    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026") if filtros_globales else "02/09/2026"
    sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip() if filtros_globales else "TODOS"

    keys_to_del = [k for k in st.session_state.keys() if "_mn_motor_cache_" in k]
    for k in keys_to_del:
        del st.session_state[k]

    clave_cache_estado = f"_mn_motor_cache_v6_{anio_op}_{mes_op}_{dia_matinal}_{sup_filtro}"
    if clave_cache_estado not in st.session_state:
        df_det = _calcular_base_mn(df_vta, df_universo, vendedores, anio_op, mes_op, dia_matinal)
        
        taxonomias_df = pd.DataFrame({"Taxonomia": ["A", "B", "C", "D"]})
        vendedores_df = df_det[["CodVendedor", "Nombre", "SUP"]].drop_duplicates("CodVendedor") if not df_det.empty else pd.DataFrame(columns=["CodVendedor", "Nombre", "SUP"])
        
        if not vendedores_df.empty:
            vendedores_df["_k"], taxonomias_df["_k"] = 1, 1
            matriz_base = vendedores_df.merge(taxonomias_df, on="_k").drop(columns="_k")
            
            cartera_matriz = df_det.groupby(["CodVendedor", "Taxonomia"], as_index=False).agg(
                Cartera_Total=("Cliente", "count"),
                Ventas_Totales=("Ventas_Totales", "sum"),
                Ventas_MiNegocio=("Ventas_MiNegocio", "sum"),
                Count_NoDigital=("Es_NoDigital", lambda x: int(x.sum())),
                Count_Hibrido=("Es_Hibrido", lambda x: int(x.sum())),
                Count_FullyDigital=("Es_FullyDigital", lambda x: int(x.sum()))
            )
            
            reporte = matriz_base.merge(cartera_matriz, on=["CodVendedor", "Taxonomia"], how="left")
            reporte[["Cartera_Total", "Ventas_Totales", "Ventas_MiNegocio", "Count_NoDigital", "Count_Hibrido", "Count_FullyDigital"]] = reporte[["Cartera_Total", "Ventas_Totales", "Ventas_MiNegocio", "Count_NoDigital", "Count_Hibrido", "Count_FullyDigital"]].fillna(0)
            
            reporte["% Adopcion"] = (reporte["Ventas_MiNegocio"] / reporte["Ventas_Totales"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)
            reporte["% No Digital"] = (reporte["Count_NoDigital"] / reporte["Cartera_Total"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)
            reporte["% Híbridos"] = (reporte["Count_Hibrido"] / reporte["Cartera_Total"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)
            reporte["% FullyDigital"] = (reporte["Count_FullyDigital"] / reporte["Cartera_Total"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)
            
            reporte["CodVendedor"] = pd.to_numeric(reporte["CodVendedor"], errors="coerce").astype("Int64")
            reporte = reporte.sort_values(by=["CodVendedor", "Taxonomia"], ascending=[True, True]).reset_index(drop=True)
        else:
            reporte = pd.DataFrame(columns=["CodVendedor", "Nombre", "SUP", "Taxonomia", "Cartera_Total", "Ventas_Totales", "Ventas_MiNegocio", "% Adopcion", "% No Digital", "% Híbridos", "% FullyDigital"])
            
        st.session_state[clave_cache_estado] = (reporte, df_det)

    rep_cached, det_cached = st.session_state[clave_cache_estado]
    st.session_state["_mn_df_clientes_detalle"] = det_cached
    return rep_cached

def _tarjeta_metrica_compacta_html(label, valor, border_color="#475569", border_width="1px"):
    return f"""
    <div style="
        background-color: #1e293b;
        border: {border_width} solid {border_color};
        border-radius: 6px;
        padding: 4px 6px;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        margin-bottom: 3px;
    ">
        <div style="font-size: 0.6rem; color: #94a3b8; font-weight: 600; margin-bottom: 2px; text-transform: uppercase;">{label}</div>
        <div style="font-size: 1.0rem; color: #f8fafc; font-weight: 700;">{valor}</div>
    </div>
    """

@st.fragment
def render_fragmento_interactivo_mn(reporte_mn_base, supervisores_seleccionados):
    if reporte_mn_base is None or reporte_mn_base.empty:
        st.info("No hay datos disponibles para procesar el Avance de Adopción MiNegocio.")
        return

    df_clientes_det = st.session_state.get("_mn_df_clientes_detalle", pd.DataFrame())
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
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], placeholder="Seleccionar preventistas...", key="frag_mn_vendedor")
    with col_fc2:
        tax_selec = st.multiselect("Taxonomía", options=tax_dispo, default=[], placeholder="Seleccionar taxonomías...", key="frag_mn_taxonomia")
    with col_fc3:
        dia_visita_selec = st.multiselect("Día de Visita", options=dia_visita_dispo, default=[], placeholder="Seleccionar días de visita...", key="frag_mn_dia_visita")

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
            Ventas_Totales=("Ventas_Totales", "sum"),
            Ventas_MiNegocio=("Ventas_MiNegocio", "sum"),
            Count_NoDigital=("Es_NoDigital", lambda x: int(x.sum())),
            Count_Hibrido=("Es_Hibrido", lambda x: int(x.sum())),
            Count_FullyDigital=("Es_FullyDigital", lambda x: int(x.sum()))
        )
        reporte_filtrado[["Cartera_Total", "Ventas_Totales", "Ventas_MiNegocio", "Count_NoDigital", "Count_Hibrido", "Count_FullyDigital"]] = reporte_filtrado[["Cartera_Total", "Ventas_Totales", "Ventas_MiNegocio", "Count_NoDigital", "Count_Hibrido", "Count_FullyDigital"]].fillna(0)
        
        reporte_filtrado["% Adopcion"] = (reporte_filtrado["Ventas_MiNegocio"] / reporte_filtrado["Ventas_Totales"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)
        reporte_filtrado["% No Digital"] = (reporte_filtrado["Count_NoDigital"] / reporte_filtrado["Cartera_Total"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)
        reporte_filtrado["% Híbridos"] = (reporte_filtrado["Count_Hibrido"] / reporte_filtrado["Cartera_Total"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)
        reporte_filtrado["% FullyDigital"] = (reporte_filtrado["Count_FullyDigital"] / reporte_filtrado["Cartera_Total"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)
        
        reporte_filtrado["CodVendedor"] = pd.to_numeric(reporte_filtrado["CodVendedor"], errors="coerce").astype("Int64")
        reporte_filtrado = reporte_filtrado.sort_values(by=["CodVendedor", "Taxonomia"], ascending=[True, True]).reset_index(drop=True)
    else:
        reporte_filtrado = pd.DataFrame(columns=["CodVendedor", "Nombre", "SUP", "Taxonomia", "Cartera_Total", "Ventas_Totales", "Ventas_MiNegocio", "% Adopcion", "% No Digital", "% Híbridos", "% FullyDigital"])

    tot_cartera = int(df_cli_filtrado["Cliente"].count()) if not df_cli_filtrado.empty else 0
    tot_ventas = float(df_cli_filtrado["Ventas_Totales"].sum()) if not df_cli_filtrado.empty else 0.0
    tot_mn = float(df_cli_filtrado["Ventas_MiNegocio"].sum()) if not df_cli_filtrado.empty else 0.0
    pct_venta_mn = (tot_mn / tot_ventas * 100.0) if tot_ventas > 0 else 0.0

    cartera_tax = df_cli_filtrado.groupby("Taxonomia")["Cliente"].count() if not df_cli_filtrado.empty else pd.Series()
    cart_a = cartera_tax.get("A", 0)
    cart_b = cartera_tax.get("B", 0)
    cart_c = cartera_tax.get("C", 0)
    cart_d = cartera_tax.get("D", 0)

    cnt_nodigital = int(df_cli_filtrado["Es_NoDigital"].sum()) if not df_cli_filtrado.empty and "Es_NoDigital" in df_cli_filtrado.columns else 0
    cnt_hibrido = int(df_cli_filtrado["Es_Hibrido"].sum()) if not df_cli_filtrado.empty and "Es_Hibrido" in df_cli_filtrado.columns else 0
    cnt_fully = int(df_cli_filtrado["Es_FullyDigital"].sum()) if not df_cli_filtrado.empty and "Es_FullyDigital" in df_cli_filtrado.columns else 0

    # Tarjetas de resumen métricas superiores organizadas en 3 líneas exactas
    st.markdown("""
        <style>
        hr {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            border-color: #334155 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # LÍNEA 1: Ventas Totales, Venta Total MN+, % Venta MN+
    cols_r1 = st.columns(3)
    with cols_r1[0]:
        st.markdown(_tarjeta_metrica_compacta_html("VENTAS TOTALES", f"${tot_ventas:,.2f}", "#38bdf8", "2px"), unsafe_allow_html=True)
    with cols_r1[1]:
        st.markdown(_tarjeta_metrica_compacta_html("VENTA TOTAL MN+", f"${tot_mn:,.2f}", "#38bdf8", "2px"), unsafe_allow_html=True)
    with cols_r1[2]:
        st.markdown(_tarjeta_metrica_compacta_html("% VENTA MN+", f"{pct_venta_mn:,.2f}%", "#38bdf8", "2px"), unsafe_allow_html=True)

    st.divider()

    # LÍNEA 2: Cartera Total + Colores por Taxonomía (A, B, C, D) con estilos idénticos a rep_ccc.py
    cols_r2 = st.columns(5)
    with cols_r2[0]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA TOTAL", f"{tot_cartera:,.0f}", "#3b82f6", "1px"), unsafe_allow_html=True)
    with cols_r2[1]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA A", f"{cart_a:,.0f}", "#ef4444", "1px"), unsafe_allow_html=True)
    with cols_r2[2]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA B", f"{cart_b:,.0f}", "#f97316", "1px"), unsafe_allow_html=True)
    with cols_r2[3]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA C", f"{cart_c:,.0f}", "#eab308", "1px"), unsafe_allow_html=True)
    with cols_r2[4]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA D", f"{cart_d:,.0f}", "#22c55e", "1px"), unsafe_allow_html=True)

    st.divider()

    # LÍNEA 3: Conteo de clientes por categoría analítica (No Digital, Híbridos, FullyDigital)
    cols_r3 = st.columns(3)
    with cols_r3[0]:
        st.markdown(_tarjeta_metrica_compacta_html("CLIENTES NO DIGITAL", f"{cnt_nodigital:,.0f}", "#ef4444", "1px"), unsafe_allow_html=True)
    with cols_r3[1]:
        st.markdown(_tarjeta_metrica_compacta_html("CLIENTES HÍBRIDOS", f"{cnt_hibrido:,.0f}", "#f97316", "1px"), unsafe_allow_html=True)
    with cols_r3[2]:
        st.markdown(_tarjeta_metrica_compacta_html("CLIENTES FULLY DIGITAL", f"{cnt_fully:,.0f}", "#22c55e", "1px"), unsafe_allow_html=True)

    st.divider()

    columnas_visuales_mn = [
        "CodVendedor", "Nombre", "SUP", "Taxonomia", 
        "Cartera_Total", "Ventas_Totales", "Ventas_MiNegocio", 
        "% Adopcion", "% No Digital", "% Híbridos", "% FullyDigital"
    ]
    reporte_render = reporte_filtrado[columnas_visuales_mn].copy().reset_index(drop=True)

    if not reporte_render.empty:
        gb = GridOptionsBuilder.from_dataframe(reporte_render)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=120)
        
        gb.configure_column("CodVendedor", headerName="Cód. Vend", width=90, valueFormatter="x != null ? Number(x).toFixed(0) : ''")
        gb.configure_column("Nombre", headerName="Preventista", minWidth=160)
        gb.configure_column("SUP", headerName="SUP", width=75)
        gb.configure_column("Taxonomia", headerName="Tax", width=70)
        gb.configure_column("Cartera_Total", headerName="Cartera Total", width=100)
        
        val_fmt_pesos = "x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0,00'"
        val_fmt_pct = "x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '%' : '0,00%'"
        
        gb.configure_column("Ventas_Totales", headerName="Ventas Totales ($)", width=130, valueFormatter=val_fmt_pesos)
        gb.configure_column("Ventas_MiNegocio", headerName="Ventas App ($)", width=130, valueFormatter=val_fmt_pesos)
        gb.configure_column("% Adopcion", headerName="% Adopción", width=110, valueFormatter=val_fmt_pct)
        gb.configure_column("% No Digital", headerName="% No Digital", width=110, valueFormatter=val_fmt_pct)
        gb.configure_column("% Híbridos", headerName="% Híbridos", width=110, valueFormatter=val_fmt_pct)
        gb.configure_column("% FullyDigital", headerName="% FullyDigital", width=120, valueFormatter=val_fmt_pct)
        
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
        st.info("No se encontraron registros con los filtros seleccionados.")

    st.divider()

    st.markdown("### ⚔️ Batalla MiNegocio: Detalle Caso a Caso por Cliente (No Digital e Híbridos)")
    st.markdown("Listado de clientes pendientes de conversión digital (excluye FullyDigital), con montos, porcentaje de adopción y mínimo requerido en $ para alcanzar el 70%.")

    if not df_cli_filtrado.empty:
        # Excluir estrictamente a los FullyDigital de la batalla inferior
        df_batalla = df_cli_filtrado[df_cli_filtrado["Es_FullyDigital"] == False].copy()
        
        def determinar_categoria_txt(row):
            if row["Es_NoDigital"]:
                return "No Digital"
            elif row["Es_Hibrido"]:
                return "Híbridos"
            return "No Digital"

        df_batalla["Categoría App"] = df_batalla.apply(determinar_categoria_txt, axis=1)

        df_batalla_render = pd.DataFrame()
        df_batalla_render["Cód. Vend"] = df_batalla.get("CodVendedor", pd.Series())
        df_batalla_render["Preventista"] = df_batalla.get("Nombre", pd.Series())
        df_batalla_render["SUP"] = df_batalla.get("SUP", pd.Series())
        df_batalla_render["Cód. Cliente"] = df_batalla.get("Cliente", pd.Series())
        df_batalla_render["Razón Social"] = df_batalla.get("NombreCliente", pd.Series())
        df_batalla_render["Dirección"] = df_batalla.get("DireccionCliente", pd.Series())
        df_batalla_render["Día Visita"] = df_batalla.get("DiaVisita", pd.Series())
        df_batalla_render["Taxonomía"] = df_batalla.get("Taxonomia", pd.Series())
        df_batalla_render["Ventas Totales ($)"] = df_batalla.get("Ventas_Totales", pd.Series())
        df_batalla_render["Ventas App ($)"] = df_batalla.get("Ventas_MiNegocio", pd.Series())
        df_batalla_render["% Adopción"] = df_batalla.get("Pct_MiNegocio", pd.Series())
        df_batalla_render["Faltante Mín. 70% ($)"] = df_batalla.get("Minimo_Facturacion_70", pd.Series())
        df_batalla_render["Categoría App"] = df_batalla.get("Categoría App", pd.Series())

        df_batalla_render = df_batalla_render.reset_index(drop=True)
    else:
        df_batalla_render = pd.DataFrame(columns=["Cód. Vend", "Preventista", "SUP", "Cód. Cliente", "Razón Social", "Dirección", "Día Visita", "Taxonomía", "Ventas Totales ($)", "Ventas App ($)", "% Adopción", "Faltante Mín. 70% ($)", "Categoría App"])

    if not df_batalla_render.empty:
        gb_b = GridOptionsBuilder.from_dataframe(df_batalla_render)
        gb_b.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=120)
        gb_b.configure_column("Cód. Vend", width=90)
        gb_b.configure_column("Preventista", minWidth=150)
        gb_b.configure_column("SUP", width=75)
        gb_b.configure_column("Cód. Cliente", width=100)
        gb_b.configure_column("Razón Social", minWidth=170)
        gb_b.configure_column("Dirección", minWidth=160)
        gb_b.configure_column("Día Visita", width=100)
        gb_b.configure_column("Taxonomía", width=80)
        gb_b.configure_column("Ventas Totales ($)", width=130, valueFormatter=val_fmt_pesos)
        gb_b.configure_column("Ventas App ($)", width=130, valueFormatter=val_fmt_pesos)
        gb_b.configure_column("% Adopción", width=110, valueFormatter=val_fmt_pct)
        gb_b.configure_column("Faltante Mín. 70% ($)", width=140, valueFormatter=val_fmt_pesos)
        gb_b.configure_column("Categoría App", width=120)

        gb_b.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_opts_b = gb_b.build()

        AgGrid(
            df_batalla_render,
            gridOptions=grid_opts_b,
            height=400,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=False
        )
    else:
        st.info("No hay registros de clientes pendientes de conversión digital con los filtros seleccionados.")

    st.divider()

    col_dl1, col_dl2, col_dl3 = st.columns(3)
    with col_dl1:
        buffer_mn = io.BytesIO()
        with pd.ExcelWriter(buffer_mn, engine="openpyxl") as writer:
            reporte_render.to_excel(writer, index=False, sheet_name="Adopcion_MiNegocio_Taxonomia")
        buffer_mn.seek(0)
        st.download_button(
            label="📥 Descargar Resumen a Excel",
            data=buffer_mn,
            file_name="Adopcion_MiNegocio_Resumen.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="mn_frag_btn_dl_res"
        )

    with col_dl2:
        buffer_bat = io.BytesIO()
        with pd.ExcelWriter(buffer_bat, engine="openpyxl") as writer:
            df_batalla_render.to_excel(writer, index=False, sheet_name="Batalla_MiNegocio_Clientes")
        buffer_bat.seek(0)
        st.download_button(
            label="📥 Descargar Batalla a Excel",
            data=buffer_bat,
            file_name="Batalla_MiNegocio_Clientes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="mn_frag_btn_dl_bat"
        )

    with col_dl3:
        if not df_batalla_render.empty:
            lista_mn_formateada = []
            for idx, row in df_batalla_render.iterrows():
                cli = row.get("Cód. Cliente", "")
                nom = row.get("Razón Social", "")
                dir_c = row.get("Dirección", "")
                dia = row.get("Día Visita", "")
                pct_app = row.get("% Adopción", 0.0)
                faltante = row.get("Faltante Mín. 70% ($)", 0.0)
                cat = row.get("Categoría App", "")
                
                lista_mn_formateada.append(f"[{cli}] {nom} - {dir_c} - {dia} | App: {pct_app:,.2f}% ({cat}) - Faltante 70%: ${faltante:,.2f}")

            detalle_texto = "%0A".join(lista_mn_formateada)
            total_cnt = len(df_batalla_render)
            
            texto_wa = f"MiNegocio Pendientes (Total: {total_cnt})%0A{detalle_texto}"
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
                    ">💬 WhatsApp MiNegocio</a>
                </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('<div style="padding:0.5rem;text-align:center;color:#94a3b8;font-size:0.85rem;">Sin datos para WhatsApp</div>', unsafe_allow_html=True)

def render_rep_mn(df_vta, df_universo, filtros_globales=None):
    st.subheader("📱 Adopción MiNegocio por Taxonomía")
    st.markdown("Analiza la adopción y penetración de la aplicación MiNegocio segmentada por taxonomía, vendedor y día de visita sobre el universo total de cartera.")

    sup_filtro = "TODOS"
    if filtros_globales and isinstance(filtros_globales, dict):
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    except Exception:
        maestro_v = pd.DataFrame()

    reporte_base = generar_reporte_mn_taxonomia(df_vta, df_universo, maestro_v, filtros_globales)
    sups_sel = [sup_filtro] if sup_filtro != "TODOS" else None

    render_fragmento_interactivo_mn(reporte_base, sups_sel)