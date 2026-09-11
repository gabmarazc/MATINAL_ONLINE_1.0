# modules/rep_ccc.py
import io
import urllib.parse
import unicodedata
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import parsear_fecha_robusta, extraer_dia_de_ruta

def preparar_ventas_ccc(df_vta, df_ausencias, anio_operativo, mes_operativo, dia_matinal):
    """Pipeline de ventas independiente y específico para CCC basado en CantBase, ImporteNeto y períodos."""
    df = df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame()
    if df.empty:
        return df

    col_cant = next((c for c in ["CantBase", "CANTBASE", "Cantidad", "CANTIDAD", "Unidades", "UNIDADES"] if c in df.columns), df.columns[0])
    df["CantBase"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0.0)

    col_imp = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df.columns), None)
    if col_imp:
        df["ImporteNeto"] = pd.to_numeric(df[col_imp], errors="coerce").fillna(0.0)
    else:
        df["ImporteNeto"] = 0.0

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

    # Excluir estrictamente al vendedor 20 del pipeline de ventas CCC
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

    df["ClaveAUS_Carga"] = df["CodVendedor"].astype(str) + "-" + df["FechaCarga_dt"].dt.strftime("%Y-%m-%d")
    df["ClaveAUS_Entrega"] = df["CodVendedor"].astype(str) + "-" + df["FechaEntrega_dt"].dt.strftime("%Y-%m-%d")

    df_aus = df_ausencias.copy() if df_ausencias is not None and not df_ausencias.empty else pd.DataFrame()
    if not df_aus.empty:
        col_aus_vend = next((c for c in ["Ausente", "CodVend", "CodVendedor", "Vendedor", "Cod_Vendedor"] if c in df_aus.columns), df_aus.columns[3])
        col_aus_fecha = next((c for c in df_aus.columns if c in ["Fecha", "FechaAusencia", "Dia"]), df_aus.columns[2])
        col_aus_reemp = next((c for c in df_aus.columns if c in ["Reemplazo", "CodReemplazo", "Cod_Reemplazo", "PreventistaReemplazo"]), df_aus.columns[4])

        df_aus["Fecha_dt"] = parsear_fecha_robusta(df_aus[col_aus_fecha])
        df_aus["CodVend_clean"] = pd.to_numeric(df_aus[col_aus_vend], errors="coerce").astype("Int64")
        df_aus["ClaveAUS"] = df_aus["CodVend_clean"].astype(str) + "-" + df_aus["Fecha_dt"].dt.strftime("%Y-%m-%d")
        df_aus["Reemplazo_clean"] = pd.to_numeric(df_aus[col_aus_reemp], errors="coerce").astype("Int64")

        aus_map = df_aus.dropna(subset=["ClaveAUS", "Reemplazo_clean"]).drop_duplicates("ClaveAUS").set_index("ClaveAUS")["Reemplazo_clean"]
        
        df["Reemplazo"] = df["ClaveAUS_Carga"].map(aus_map).combine_first(df["ClaveAUS_Entrega"].map(aus_map))
        df["CodVendedorOperativo"] = df["Reemplazo"].combine_first(df["CodVendedor"]).astype("Int64")
    else:
        df["Reemplazo"] = pd.NA
        df["CodVendedorOperativo"] = df["CodVendedor"]

    return df

def _calcular_base_ccc(df_vta, df_universo, vendedores, hoja_ccc_param, anio_op, mes_op, dia_matinal):
    try:
        df_ccc_db = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
        if df_ccc_db is not None and not df_ccc_db.empty and "Anio" in df_ccc_db.columns and "Mes" in df_ccc_db.columns:
            df_ccc_per = df_ccc_db[(df_ccc_db["Anio"].astype(str) == str(anio_op)) & (df_ccc_db["Mes"].astype(str) == str(mes_op))]
            if not df_ccc_per.empty:
                hoja_ccc = df_ccc_per
            else:
                hoja_ccc = hoja_ccc_param
        else:
            hoja_ccc = hoja_ccc_param
    except Exception:
        hoja_ccc = hoja_ccc_param

    hoja_ccc = hoja_ccc.copy() if hoja_ccc is not None and not hoja_ccc.empty else pd.DataFrame(columns=["Taxonomia", "Porcentaje_Cartera"])
    if not hoja_ccc.empty:
        hoja_ccc.columns = hoja_ccc.columns.astype(str).str.strip()
        rename_metas = {}
        for c in hoja_ccc.columns:
            if str(c).lower() in ["porcentaje_cartera", "porcentaje", "pct", "obj", "objetivo", "obj_ccc"]:
                rename_metas[c] = "Porcentaje_Cartera"
            if str(c).lower() in ["taxonomia", "taxonomía", "categoria", "categoría"]:
                rename_metas[c] = "Taxonomia"
        hoja_ccc = hoja_ccc.rename(columns=rename_metas)
        if "Taxonomia" in hoja_ccc.columns:
            hoja_ccc["Taxonomia"] = hoja_ccc["Taxonomia"].astype(str).str.strip().str.upper()
        if "Porcentaje_Cartera" in hoja_ccc.columns:
            hoja_ccc["Porcentaje_Cartera"] = pd.to_numeric(hoja_ccc["Porcentaje_Cartera"], errors="coerce").fillna(0.0)
            hoja_ccc = hoja_ccc[["Taxonomia", "Porcentaje_Cartera"]].drop_duplicates("Taxonomia")
        else:
            hoja_ccc["Porcentaje_Cartera"] = 80.0
    else:
        hoja_ccc = pd.DataFrame({"Taxonomia": ["A", "B", "C", "D"], "Porcentaje_Cartera": [80.0, 70.0, 60.0, 50.0]})

    try:
        df_ausencias = db.cargar_tabla_sql("SELECT * FROM ausencias")
    except Exception:
        df_ausencias = pd.DataFrame()

    try:
        df_altas_db = db.cargar_tabla_sql("SELECT * FROM altas")
    except Exception:
        df_altas_db = pd.DataFrame()

    altas_periodo_set = set()
    if not df_altas_db.empty:
        col_f_altas = next((c for c in df_altas_db.columns if "fecha" in str(c).lower()), None)
        col_cod_altas = next((c for c in df_altas_db.columns if "codigo" in str(c).lower() or "cliente" in str(c).lower()), df_altas_db.columns[0])
        if col_f_altas:
            df_altas_db["Fecha_dt"] = parsear_fecha_robusta(df_altas_db[col_f_altas])
            altas_mes = df_altas_db[
                (df_altas_db["Fecha_dt"].dt.year == int(anio_op)) & 
                (df_altas_db["Fecha_dt"].dt.month == int(mes_op))
            ].copy()
            if not altas_mes.empty:
                altas_periodo_set = set(pd.to_numeric(altas_mes[col_cod_altas], errors="coerce").dropna().astype("Int64").tolist())

    df_vta_prep = preparar_ventas_ccc(df_vta, df_ausencias, anio_op, mes_op, dia_matinal)
    ventas_periodo = df_vta_prep[df_vta_prep["Periodo"].isin(["Arrastre", "Actual"])].copy() if not df_vta_prep.empty and "Periodo" in df_vta_prep.columns else df_vta_prep.copy()

    dia_mat_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(dia_mat_dt) and not ventas_periodo.empty and "FechaEntrega_dt" in ventas_periodo.columns:
        ventas_periodo = ventas_periodo[ventas_periodo["FechaEntrega_dt"].dt.date < dia_mat_dt.date()]

    if not ventas_periodo.empty:
        col_c_orig = next((c for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"] if c in ventas_periodo.columns), "Cliente")
        ventas_periodo["Cliente"] = pd.to_numeric(ventas_periodo[col_c_orig], errors="coerce").astype("Int64")
        
        col_cant = next((c for c in ["CantBase", "CANTBASE", "Cantidad", "CANTIDAD", "Unidades", "UNIDADES"] if c in ventas_periodo.columns), "CantBase")
        ventas_periodo["_cant_calc"] = pd.to_numeric(ventas_periodo[col_cant], errors="coerce").fillna(0.0)
        
        col_imp = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in ventas_periodo.columns), None)
        if col_imp:
            ventas_periodo["_imp_calc"] = pd.to_numeric(ventas_periodo[col_imp], errors="coerce").fillna(0.0)
        else:
            ventas_periodo["_imp_calc"] = 0.0

        clientes_g = ventas_periodo.groupby("Cliente", as_index=False).agg(
            Total_Cant=("_cant_calc", "sum"),
            Total_Imp=("_imp_calc", "sum")
        )
        
        clientes_g["Es_CCC"] = clientes_g["Total_Cant"].ge(3) & clientes_g["Total_Imp"].ge(1)
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
            universo["DiaVisita"] = sr_u.apply(extraer_dia_de_ruta)
        else:
            universo["DiaVisita"] = "SIN DÍA"

        cli_col_u = next((c for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"] if c in universo.columns), universo.columns[0])
        scli_u = universo[cli_col_u]
        if isinstance(scli_u, pd.DataFrame): scli_u = scli_u.iloc[:, 0]
        universo["Cliente"] = pd.to_numeric(scli_u, errors="coerce").astype("Int64")
        universo = universo[universo["Taxonomia"].isin(["A", "B", "C", "D"])].dropna(subset=["Cliente", "CodVendedor"])

    if not universo.empty and "CodVendedor" in universo.columns:
        universo["CodVendedor"] = pd.to_numeric(universo["CodVendedor"], errors="coerce").astype("Int64")
        # Excluir estrictamente al Vendedor 20
        universo = universo[universo["CodVendedor"] != 20]

    if not universo.empty:
        universo["Es_Alta_Periodo"] = universo["Cliente"].isin(altas_periodo_set)
    else:
        universo["Es_Alta_Periodo"] = False

    if not universo.empty and not clientes_g.empty:
        universo = universo.merge(clientes_g[["Cliente", "Es_CCC"]], on="Cliente", how="left")
        universo["Es_CCC"] = universo["Es_CCC"].fillna(False)
    else:
        universo["Es_CCC"] = False

    # Agrupación por Vendedor y Taxonomía incluyendo Cartera Total, Altas y Cartera Neta
    cartera_matriz = universo.groupby(["CodVendedor", "Taxonomia"], as_index=False).agg(
        Cartera_Total=("Cliente", "count"),
        Altas=("Es_Alta_Periodo", lambda x: int(x.sum())),
        Cartera_Neta=("Es_Alta_Periodo", lambda x: int((~x).sum())),
        CCC=("Es_CCC", lambda x: int(x.sum()))
    ) if not universo.empty and "CodVendedor" in universo.columns else pd.DataFrame(columns=["CodVendedor", "Taxonomia", "Cartera_Total", "Altas", "Cartera_Neta", "CCC"])

    vendedores_df = pd.DataFrame()
    col_c_v = next((c for c in ["Codigo_Vendedor", "CodVend", "CodVendedor"] if c in vendedores.columns), vendedores.columns[0])
    col_n_v = next((c for c in ["Nombre_Vendedor", "Nombre"] if c in vendedores.columns), vendedores.columns[1])
    col_s_v = next((c for c in ["Supervisor", "SUP"] if c in vendedores.columns), vendedores.columns[2] if len(vendedores.columns) > 2 else vendedores.columns[1])

    sv_c = vendedores[col_c_v]
    if isinstance(sv_c, pd.DataFrame): sv_c = sv_c.iloc[:, 0]
    vendedores_df["CodVendedor"] = pd.to_numeric(sv_c, errors="coerce").astype("Int64")
    # Excluir estrictamente al Vendedor 20 del maestro
    vendedores_df = vendedores_df[vendedores_df["CodVendedor"] != 20]

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
    reporte[["Cartera_Total", "Altas", "Cartera_Neta", "CCC"]] = reporte[["Cartera_Total", "Altas", "Cartera_Neta", "CCC"]].fillna(0).astype("Int64")
    reporte["NC"] = (reporte["Cartera_Total"] - reporte["CCC"]).clip(lower=0).astype("Int64")
    
    # % Cartera calculado sobre Cartera Neta para absoluta claridad analítica
    reporte["% Cartera"] = (reporte["CCC"] / reporte["Cartera_Neta"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)

    reporte = reporte.merge(hoja_ccc, on="Taxonomia", how="left")
    reporte["Porcentaje_Cartera"] = reporte["Porcentaje_Cartera"].fillna(80.0)
    reporte["Objetivo_CCC"] = (reporte["Cartera_Neta"] * (reporte["Porcentaje_Cartera"] / 100.0)).round(0).astype("Int64")
    reporte["% Objetivo"] = (reporte["CCC"] / reporte["Objetivo_CCC"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)

    reporte["CodVendedor"] = pd.to_numeric(reporte["CodVendedor"], errors="coerce").astype("Int64")
    reporte = reporte.sort_values(by=["CodVendedor", "Taxonomia"], ascending=[True, True]).reset_index(drop=True)

    columnas_salida = [
        "CodVendedor", "Nombre", "SUP", "Taxonomia", 
        "Cartera_Total", "Altas", "Cartera_Neta", 
        "Objetivo_CCC", "CCC", "NC", "% Cartera", "% Objetivo"
    ]
    return reporte[columnas_salida], df_det_nc

def generar_reporte_ccc_taxonomia(df_vta, df_universo, vendedores, hoja_ccc_param, filtros_globales=None):
    anio_op = int(filtros_globales.get("anio", 2026)) if filtros_globales else 2026
    mes_op = int(filtros_globales.get("mes", 9)) if filtros_globales else 9
    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026") if filtros_globales else "02/09/2026"
    sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip() if filtros_globales else "TODOS"

    keys_to_delete = [k for k in st.session_state.keys() if "_ccc_motor_cache_" in k]
    for k in keys_to_delete:
        del st.session_state[k]

    clave_cache_estado = f"_ccc_motor_cache_v54_{anio_op}_{mes_op}_{dia_matinal}_{sup_filtro}"
    if clave_cache_estado not in st.session_state:
        rep, det = _calcular_base_ccc(df_vta, df_universo, vendedores, hoja_ccc_param, anio_op, mes_op, dia_matinal)
        st.session_state[clave_cache_estado] = (rep, det)

    rep_cached, det_cached = st.session_state[clave_cache_estado]
    st.session_state["_ccc_df_clientes_detalle"] = det_cached
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
            Altas=("Es_Alta_Periodo", lambda x: int(x.sum())),
            Cartera_Neta=("Es_Alta_Periodo", lambda x: int((~x).sum())),
            CCC=("Es_CCC", lambda x: int(x.sum()))
        )
        reporte_filtrado[["Cartera_Total", "Altas", "Cartera_Neta", "CCC"]] = reporte_filtrado[["Cartera_Total", "Altas", "Cartera_Neta", "CCC"]].fillna(0).astype("Int64")
        reporte_filtrado["NC"] = (reporte_filtrado["Cartera_Total"] - reporte_filtrado["CCC"]).clip(lower=0).astype("Int64")
        reporte_filtrado["% Cartera"] = (reporte_filtrado["CCC"] / reporte_filtrado["Cartera_Neta"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)

        objs_originales = reporte_ccc_base[["CodVendedor", "Taxonomia", "Objetivo_CCC"]].drop_duplicates(["CodVendedor", "Taxonomia"])
        reporte_filtrado = reporte_filtrado.merge(objs_originales, on=["CodVendedor", "Taxonomia"], how="left")
        reporte_filtrado["Objetivo_CCC"] = reporte_filtrado["Objetivo_CCC"].fillna(0).astype("Int64")
        reporte_filtrado["% Objetivo"] = (reporte_filtrado["CCC"] / reporte_filtrado["Objetivo_CCC"].replace(0, pd.NA)).mul(100).fillna(0.0).round(2)
        
        reporte_filtrado["CodVendedor"] = pd.to_numeric(reporte_filtrado["CodVendedor"], errors="coerce").astype("Int64")
        reporte_filtrado = reporte_filtrado.sort_values(by=["CodVendedor", "Taxonomia"], ascending=[True, True]).reset_index(drop=True)
    else:
        reporte_filtrado = pd.DataFrame(columns=["CodVendedor", "Nombre", "SUP", "Taxonomia", "Cartera_Total", "Altas", "Cartera_Neta", "Objetivo_CCC", "CCC", "NC", "% Cartera", "% Objetivo"])

    tot_cartera = int(df_cli_filtrado["Cliente"].count()) if not df_cli_filtrado.empty else 0
    tot_altas = int(df_cli_filtrado["Es_Alta_Periodo"].sum()) if not df_cli_filtrado.empty and "Es_Alta_Periodo" in df_cli_filtrado.columns else 0
    tot_neta = tot_cartera - tot_altas

    cartera_tax = df_cli_filtrado.groupby("Taxonomia")["Cliente"].count() if not df_cli_filtrado.empty else pd.Series()
    cart_a = cartera_tax.get("A", 0)
    cart_b = cartera_tax.get("B", 0)
    cart_c = cartera_tax.get("C", 0)
    cart_d = cartera_tax.get("D", 0)

    tot_obj_val = int(reporte_filtrado["Objetivo_CCC"].sum()) if not reporte_filtrado.empty and "Objetivo_CCC" in reporte_filtrado.columns else 0
    obj_tax = reporte_filtrado.groupby("Taxonomia")["Objetivo_CCC"].sum() if not reporte_filtrado.empty else pd.Series()
    obj_a = obj_tax.get("A", 0)
    obj_b = obj_tax.get("B", 0)
    obj_c = obj_tax.get("C", 0)
    obj_d = obj_tax.get("D", 0)

    total_ccc_val = int(df_cli_filtrado["Es_CCC"].sum()) if not df_cli_filtrado.empty and "Es_CCC" in df_cli_filtrado.columns else 0
    tot_tax_ccc = df_cli_filtrado[df_cli_filtrado["Es_CCC"] == True].groupby("Taxonomia")["Cliente"].count() if not df_cli_filtrado.empty else pd.Series()
    cant_a = tot_tax_ccc.get("A", 0)
    cant_b = tot_tax_ccc.get("B", 0)
    cant_c = tot_tax_ccc.get("C", 0)
    cant_d = tot_tax_ccc.get("D", 0)

    # % Cartera total calculado sobre la neta filtrada
    cob_total = (total_ccc_val / tot_neta * 100) if tot_neta > 0 else 0.0
    
    # Taxonomías netas para porcentajes individuales
    neta_tax = df_cli_filtrado[df_cli_filtrado["Es_Alta_Periodo"] == False].groupby("Taxonomia")["Cliente"].count() if not df_cli_filtrado.empty else pd.Series()
    neta_a = neta_tax.get("A", 0)
    neta_b = neta_tax.get("B", 0)
    neta_c = neta_tax.get("C", 0)
    neta_d = neta_tax.get("D", 0)

    cob_a = (cant_a / neta_a * 100) if neta_a > 0 else 0.0
    cob_b = (cant_b / neta_b * 100) if neta_b > 0 else 0.0
    cob_c = (cant_c / neta_c * 100) if neta_c > 0 else 0.0
    cob_d = (cant_d / neta_d * 100) if neta_d > 0 else 0.0

    # Inyección CSS para reducir al mínimo absoluto el espacio vertical del separador <hr>
    st.markdown("""
        <style>
        hr {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            border-color: #334155 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 1. FILA 1: CARTERA TOTAL y ALTAS (2 columnas, borde celeste y más grueso)
    cols_r1 = st.columns(2)
    with cols_r1[0]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA TOTAL", f"{tot_cartera:,.0f}", "#38bdf8", "2px"), unsafe_allow_html=True)
    with cols_r1[1]:
        st.markdown(_tarjeta_metrica_compacta_html("ALTAS", f"{tot_altas:,.0f}", "#38bdf8", "2px"), unsafe_allow_html=True)

    # Línea divisoria exactamente ENTRE la Fila 1 y la Fila 2
    st.divider()

    # 2. FILA 2: CARTERA NETA y COMPOSICIÓN POR TAXONOMÍA (5 columnas, borde blanco y grosor 1px)
    cols_r2_net = st.columns(5)
    with cols_r2_net[0]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA NETA", f"{tot_neta:,.0f}", "#ffffff", "1px"), unsafe_allow_html=True)
    with cols_r2_net[1]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA A", f"{cart_a:,.0f}", "#ffffff", "1px"), unsafe_allow_html=True)
    with cols_r2_net[2]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA B", f"{cart_b:,.0f}", "#ffffff", "1px"), unsafe_allow_html=True)
    with cols_r2_net[3]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA C", f"{cart_c:,.0f}", "#ffffff", "1px"), unsafe_allow_html=True)
    with cols_r2_net[4]:
        st.markdown(_tarjeta_metrica_compacta_html("CARTERA D", f"{cart_d:,.0f}", "#ffffff", "1px"), unsafe_allow_html=True)

    # Línea divisoria entre la Fila 2 y la Fila 3
    st.divider()

    # 3. OBJETIVOS EN CANTIDAD (Fila 3)
    cols_obj = st.columns(5)
    with cols_obj[0]:
        st.markdown(_tarjeta_metrica_compacta_html("OBJETIVO TOTAL", f"{tot_obj_val:,.0f}", "#3b82f6", "1px"), unsafe_allow_html=True)
    with cols_obj[1]:
        st.markdown(_tarjeta_metrica_compacta_html("OBJETIVO TAX. A", f"{obj_a:,.0f}", "#ef4444", "1px"), unsafe_allow_html=True)
    with cols_obj[2]:
        st.markdown(_tarjeta_metrica_compacta_html("OBJETIVO TAX. B", f"{obj_b:,.0f}", "#f97316", "1px"), unsafe_allow_html=True)
    with cols_obj[3]:
        st.markdown(_tarjeta_metrica_compacta_html("OBJETIVO TAX. C", f"{obj_c:,.0f}", "#eab308", "1px"), unsafe_allow_html=True)
    with cols_obj[4]:
        st.markdown(_tarjeta_metrica_compacta_html("OBJETIVO TAX. D", f"{obj_d:,.0f}", "#22c55e", "1px"), unsafe_allow_html=True)

    # 4. TOTAL CCC (Fila 4)
    cols_r2 = st.columns(5)
    with cols_r2[0]:
        st.markdown(_tarjeta_metrica_compacta_html("TOTAL CCC", f"{total_ccc_val:,.0f}", "#3b82f6", "1px"), unsafe_allow_html=True)
    with cols_r2[1]:
        st.markdown(_tarjeta_metrica_compacta_html("CCC TAX. A", f"{cant_a:,.0f}", "#ef4444", "1px"), unsafe_allow_html=True)
    with cols_r2[2]:
        st.markdown(_tarjeta_metrica_compacta_html("CCC TAX. B", f"{cant_b:,.0f}", "#f97316", "1px"), unsafe_allow_html=True)
    with cols_r2[3]:
        st.markdown(_tarjeta_metrica_compacta_html("CCC TAX. C", f"{cant_c:,.0f}", "#eab308", "1px"), unsafe_allow_html=True)
    with cols_r2[4]:
        st.markdown(_tarjeta_metrica_compacta_html("CCC TAX. D", f"{cant_d:,.0f}", "#22c55e", "1px"), unsafe_allow_html=True)

    # 5. % CARTERA (Fila 5)
    cols_r3 = st.columns(5)
    with cols_r3[0]:
        st.markdown(_tarjeta_metrica_compacta_html("% CARTERA TOTAL", f"{cob_total:,.2f}%", "#3b82f6", "1px"), unsafe_allow_html=True)
    with cols_r3[1]:
        st.markdown(_tarjeta_metrica_compacta_html("% CARTERA A", f"{cob_a:,.2f}%", "#ef4444", "1px"), unsafe_allow_html=True)
    with cols_r3[2]:
        st.markdown(_tarjeta_metrica_compacta_html("% CARTERA B", f"{cob_b:,.2f}%", "#f97316", "1px"), unsafe_allow_html=True)
    with cols_r3[3]:
        st.markdown(_tarjeta_metrica_compacta_html("% CARTERA C", f"{cob_c:,.2f}%", "#eab308", "1px"), unsafe_allow_html=True)
    with cols_r3[4]:
        st.markdown(_tarjeta_metrica_compacta_html("% CARTERA D", f"{cob_d:,.2f}%", "#22c55e", "1px"), unsafe_allow_html=True)

    st.divider()

    columnas_visuales_ccc = [
        "CodVendedor", "Nombre", "SUP", "Taxonomia", 
        "Cartera_Total", "Altas", "Cartera_Neta", 
        "Objetivo_CCC", "CCC", "NC", "% Cartera", "% Objetivo"
    ]
    reporte_render = reporte_filtrado[columnas_visuales_ccc].copy().reset_index(drop=True)

    if not reporte_render.empty:
        gb = GridOptionsBuilder.from_dataframe(reporte_render)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=130)
        
        gb.configure_column("CodVendedor", headerName="Cód. Vend", width=90, valueFormatter="x != null ? Number(x).toFixed(0) : ''")
        gb.configure_column("Nombre", headerName="Preventista", minWidth=160)
        gb.configure_column("SUP", headerName="SUP", width=75)
        gb.configure_column("Taxonomia", headerName="Tax", width=70)
        gb.configure_column("Cartera_Total", headerName="Cartera Total", width=100)
        gb.configure_column("Altas", headerName="Altas", width=80)
        gb.configure_column("Cartera_Neta", headerName="Cartera Neta", width=100)
        gb.configure_column("Objetivo_CCC", headerName="Objetivo CCC", width=105)
        gb.configure_column("CCC", headerName="CCC", width=80)
        gb.configure_column("NC", headerName="NC", width=80)
        
        val_fmt = "x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0,00'"
        
        gb.configure_column("% Cartera", headerName="% Cartera", width=100, valueFormatter=val_fmt)
        gb.configure_column("% Objetivo", headerName="% Objetivo", width=110, valueFormatter=val_fmt)
        
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

    st.markdown("### ⚔️ Batalla NC: Listado de Clientes No Compradores")
    st.markdown("Detalle de clientes sin compra en el período, filtrados por los criterios activos del reporte superior.")

    if not df_cli_filtrado.empty:
        df_nc = df_cli_filtrado[df_cli_filtrado["Es_CCC"] == False].copy()
        
        cols_disponibles = df_nc.columns.tolist()
        map_cols = {}
        for col in cols_disponibles:
            cl = col.lower()
            if cl in ["cliente", "codcliente", "codigo"]: map_cols["Cliente"] = col
            elif cl in ["nombrecliente", "nombre_cliente", "razonsocial"]: map_cols["NombreCliente"] = col
            elif cl in ["direccioncliente", "direccion", "domicilio"]: map_cols["DireccionCliente"] = col
            elif cl in ["diavisita", "dia_visita", "ruta"]: map_cols["DiaVisita"] = col
            elif cl in ["nombre", "preventista", "vendedor"]: map_cols["Vendedor"] = col
            elif cl in ["taxonomia", "taxonomía"]: map_cols["Taxonomia"] = col

        df_nc_escueto = pd.DataFrame()
        df_nc_escueto["Código Cliente"] = df_nc.get(map_cols.get("Cliente", "Cliente"), pd.Series())
        df_nc_escueto["Razón Social"] = df_nc.get(map_cols.get("NombreCliente", "NombreCliente"), pd.Series())
        df_nc_escueto["Dirección"] = df_nc.get(map_cols.get("DireccionCliente", "DireccionCliente"), pd.Series())
        df_nc_escueto["Día Visita"] = df_nc.get(map_cols.get("DiaVisita", "DiaVisita"), pd.Series())
        df_nc_escueto["Taxonomía"] = df_nc.get(map_cols.get("Taxonomia", "Taxonomia"), pd.Series())
        df_nc_escueto["Preventista"] = df_nc.get(map_cols.get("Vendedor", "Nombre"), pd.Series())

        df_nc_render = df_nc_escueto.dropna(how="all").reset_index(drop=True)
    else:
        df_nc_render = pd.DataFrame(columns=["Código Cliente", "Razón Social", "Dirección", "Día Visita", "Taxonomía", "Preventista"])

    if not df_nc_render.empty:
        st.dataframe(df_nc_render, width="stretch", height=350, hide_index=True)
    else:
        st.info("No hay clientes no compradores (NC) para los filtros seleccionados.")

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
        maestro_ccc_param = pd.DataFrame(columns=["Taxonomia", "Porcentaje_Cartera"])

    reporte_base = generar_reporte_ccc_taxonomia(df_vta, df_universo, maestro_v, maestro_ccc_param, filtros_globales)
    sups_sel = [sup_filtro] if sup_filtro != "TODOS" else None

    render_fragmento_interactivo_ccc(reporte_base, sups_sel)