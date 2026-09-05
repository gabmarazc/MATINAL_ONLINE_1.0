# modules/rep_obj_kilos.py
import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db

def parsear_fecha_robusta(serie):
    """Estandariza parseo de fechas considerando formatos ISO, DD/MM/YYYY y genérico sin advertencias."""
    if serie is None or (isinstance(serie, pd.Series) and serie.empty):
        return pd.Series(dtype="datetime64[ns]")
    if not isinstance(serie, pd.Series):
        serie = pd.Series([serie])
    s = serie.astype(str).str.strip().str.replace(" 00:00:00", "", regex=False)
    
    dt_iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    dt_lat = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    dt_gen = pd.to_datetime(s, errors="coerce")
    
    return dt_iso.combine_first(dt_lat).combine_first(dt_gen)

def crear_filtro_excel(label, opciones, key_prefix):
    """Crea un menú desplegable con checkboxes y opción 'TODOS' sincronizada."""
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

    with st.popover(f"{label}: ...", width="stretch"):
        st.checkbox("TODOS", key=all_key)
        st.divider()
        for op in opciones:
            st.checkbox(str(op), key=f"{key_prefix}_{op}")

    todos_estan_marcados = all(st.session_state.get(f"{key_prefix}_{op}", False) for op in opciones) if opciones else False
    if todos_estan_marcados and opciones and not st.session_state.get(all_key, False):
        st.session_state[all_key] = True
        st.session_state[aux_cambio_key] = True

    seleccionados = [op for op in opciones if st.session_state.get(f"{key_prefix}_{op}", False)]
    return seleccionados

def generar_datos_composicion_mes_anterior(df_vta, maestro_v, maestro_cebe, anio_operativo, mes_operativo):
    """
    Filtra las ventas por FechaEntrega del mes anterior completo y compone:
    Vendedor -> Marca -> CEBE -> SEGMENTO -> Kilos
    Garantiza la presencia de todos los vendedores del padrón.
    """
    col_cod_v = "Codigo_Vendedor" if "Codigo_Vendedor" in maestro_v.columns else maestro_v.columns[0]
    col_nom_v = "Nombre_Vendedor" if "Nombre_Vendedor" in maestro_v.columns else maestro_v.columns[1]
    col_sup_v = "Supervisor" if "Supervisor" in maestro_v.columns else maestro_v.columns[2]

    df_padron = maestro_v[[col_cod_v, col_nom_v, col_sup_v]].copy()
    df_padron = df_padron.rename(columns={
        col_cod_v: "CodVendedor",
        col_nom_v: "Nombre",
        col_sup_v: "Supervisor"
    })
    df_padron["CodVendedor"] = pd.to_numeric(df_padron["CodVendedor"], errors="coerce").astype("Int64")
    df_padron["Nombre"] = df_padron["Nombre"].fillna("").astype(str).str.strip()
    df_padron["Supervisor"] = df_padron["Supervisor"].fillna("").astype(str).str.strip()
    df_padron = df_padron.dropna(subset=["CodVendedor"]).drop_duplicates(subset=["CodVendedor"])

    if mes_operativo == 1:
        mes_ant = 12
        anio_ant = anio_operativo - 1
    else:
        mes_ant = mes_operativo - 1
        anio_ant = anio_operativo

    if df_vta is None or df_vta.empty:
        df_padron["Marca"] = "-"
        df_padron["CEBE"] = "-"
        df_padron["SEGMENTO"] = "-"
        df_padron["Kilos"] = 0.0
        return df_padron[["CodVendedor", "Nombre", "Supervisor", "Marca", "CEBE", "SEGMENTO", "Kilos"]]

    vta = df_vta.copy()
    
    if "TipoDeVenta" in vta.columns:
        tipos_excluidos = [
            "Comodato Devolución", 
            "Comodato Ficticio", 
            "Comodato Ficticio Devolución", 
            "Comodato Préstamo"
        ]
        vta = vta[~vta["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)]

    if "Proveedor" in vta.columns:
        vta = vta[
            vta["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .contains("PEPSICO", na=False)
        ]

    if "Subramo" in vta.columns:
        vta = vta[
            ~vta["Subramo"].fillna("").astype(str).str.strip().str.upper().isin(["EMPLOYEES", "EMPLEADOS"])
        ]

    if "FechaEntrega" in vta.columns:
        vta["FechaEntrega_dt"] = parsear_fecha_robusta(vta["FechaEntrega"])
    else:
        vta["FechaEntrega_dt"] = pd.NaT

    vta_mes_ant = vta[
        (vta["FechaEntrega_dt"].dt.year == int(anio_ant)) & 
        (vta["FechaEntrega_dt"].dt.month == int(mes_ant))
    ].copy()

    if vta_mes_ant.empty:
        df_padron["Marca"] = "-"
        df_padron["CEBE"] = "-"
        df_padron["SEGMENTO"] = "-"
        df_padron["Kilos"] = 0.0
        return df_padron[["CodVendedor", "Nombre", "Supervisor", "Marca", "CEBE", "SEGMENTO", "Kilos"]]

    col_vend = next((c for c in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"] if c in vta_mes_ant.columns), None)
    if col_vend:
        vta_mes_ant["CodVendedor"] = pd.to_numeric(vta_mes_ant[col_vend], errors="coerce").astype("Int64")
    else:
        vta_mes_ant["CodVendedor"] = pd.NA

    col_m = next((c for c in ["Marca", "MARCA", "marca"] if c in vta_mes_ant.columns), None)
    vta_mes_ant["Marca"] = vta_mes_ant[col_m].fillna("").astype(str).str.strip().str.upper() if col_m else "SIN MARCA"

    mapa_cebe = {}
    if maestro_cebe is not None and not maestro_cebe.empty:
        col_m_cebe = "Marca" if "Marca" in maestro_cebe.columns else maestro_cebe.columns[0]
        col_c_cebe = "CEBE" if "CEBE" in maestro_cebe.columns else maestro_cebe.columns[1]
        for _, r in maestro_cebe.iterrows():
            m_key = str(r.get(col_m_cebe, "")).strip().upper()
            c_val = str(r.get(col_c_cebe, "")).strip()
            if m_key:
                mapa_cebe[m_key] = c_val

    vta_mes_ant["CEBE"] = vta_mes_ant["Marca"].map(mapa_cebe).fillna("SIN CEBE")

    col_rent = "SegmentoRentabilidad" if "SegmentoRentabilidad" in vta_mes_ant.columns else None
    col_rubro = "Rubro" if "Rubro" in vta_mes_ant.columns else None

    def resolver_segmento(row):
        sr = str(row.get(col_rent, "")).strip().title() if col_rent else ""
        rubro = str(row.get(col_rubro, "")).strip() if col_rubro else ""
        if sr in ["Platinum", "Gold"]:
            return f"GOLD {rubro}".strip()
        elif sr in ["Silver", "Bronze"]:
            return f"SILVER {rubro}".strip()
        return "SIN SEGMENTO"

    vta_mes_ant["SEGMENTO"] = vta_mes_ant.apply(resolver_segmento, axis=1)

    col_kg = next((c for c in ["PesoKg", "PESOKG", "Kilos", "KILOS"] if c in vta_mes_ant.columns), None)
    vta_mes_ant["Kilos"] = pd.to_numeric(vta_mes_ant[col_kg], errors="coerce").fillna(0.0) if col_kg else 0.0

    vta_agrup = vta_mes_ant.groupby(
        ["CodVendedor", "Marca", "CEBE", "SEGMENTO"], 
        as_index=False
    )["Kilos"].sum()

    df_reporte = df_padron.merge(vta_agrup, on="CodVendedor", how="left")

    df_reporte["Marca"] = df_reporte["Marca"].fillna("-")
    df_reporte["CEBE"] = df_reporte["CEBE"].fillna("-")
    df_reporte["SEGMENTO"] = df_reporte["SEGMENTO"].fillna("-")
    df_reporte["Kilos"] = df_reporte["Kilos"].fillna(0.0)

    df_reporte = df_reporte.sort_values(by=["Supervisor", "Nombre", "Marca", "CEBE", "SEGMENTO"]).reset_index(drop=True)

    columnas_finales = ["CodVendedor", "Nombre", "Supervisor", "Marca", "CEBE", "SEGMENTO", "Kilos"]
    return df_reporte[columnas_finales]

def render_rep_obj_kilos(df_vta, filtros_globales=None):
    st.subheader("📦 Base de Objetivos Kilos: Composición Mes Anterior")

    if filtros_globales is None:
        anio_op = 2026
        mes_op = 9
        sup_filtro = "TODOS"
    else:
        anio_op = int(filtros_globales.get("anio", 2026))
        mes_op = int(filtros_globales.get("mes", 9))
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()

    mes_ant_eval = 12 if mes_op == 1 else mes_op - 1
    anio_ant_eval = anio_op - 1 if mes_op == 1 else anio_op
    
    st.caption(f"🗓️ Analizando todas las entregas correspondientes al período cerrado: **{mes_ant_eval:02d}/{anio_ant_eval}**")

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        if not maestro_v.empty and "Mes" in maestro_v.columns:
            mv_per = maestro_v[(maestro_v["Mes"].astype(str) == str(mes_op)) & (maestro_v["Anio"].astype(str) == str(anio_op))]
            if not mv_per.empty:
                maestro_v = mv_per
    except Exception:
        maestro_v = pd.DataFrame()

    try:
        maestro_cebe = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if not maestro_cebe.empty and "Mes" in maestro_cebe.columns:
            mc_per = maestro_cebe[(maestro_cebe["Mes"].astype(str) == str(mes_op)) & (maestro_cebe["Anio"].astype(str) == str(anio_op))]
            if not mc_per.empty:
                maestro_cebe = mc_per
    except Exception:
        maestro_cebe = pd.DataFrame()

    if maestro_v.empty:
        st.warning("⚠️ No se encontró el Maestro de Vendedores cargado para este período en la base de datos.")
        return

    cache_key = f"_cache_rep_obj_kilos_{anio_op}_{mes_op}_{sup_filtro}"
    if cache_key not in st.session_state:
        with st.spinner("Procesando histórico de ventas por Marca, CEBE y Segmento..."):
            df_base = generar_datos_composicion_mes_anterior(df_vta, maestro_v, maestro_cebe, anio_op, mes_op)
            st.session_state[cache_key] = df_base
    else:
        df_base = st.session_state[cache_key]

    df_filtrado = df_base.copy()

    if sup_filtro != "TODOS":
        df_filtrado = df_filtrado[df_filtrado["Supervisor"].astype(str).str.strip() == sup_filtro].copy()

    v_dispo = sorted([v for v in df_filtrado["Nombre"].dropna().unique() if v != ""])
    m_dispo = sorted([m for m in df_filtrado["Marca"].dropna().unique() if m not in ["", "-"]])
    c_dispo = sorted([c for c in df_filtrado["CEBE"].dropna().unique() if c not in ["", "-"]])
    s_dispo = sorted([s for s in df_filtrado["SEGMENTO"].dropna().unique() if s not in ["", "-"]])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        v_sel = crear_filtro_excel("Vendedor", v_dispo, f"rok_v_{anio_op}_{mes_op}")
    with c2:
        m_sel = crear_filtro_excel("Marca", m_dispo, f"rok_m_{anio_op}_{mes_op}")
    with c3:
        c_sel = crear_filtro_excel("CEBE", c_dispo, f"rok_c_{anio_op}_{mes_op}")
    with c4:
        s_sel = crear_filtro_excel("Segmento", s_dispo, f"rok_s_{anio_op}_{mes_op}")

    if v_dispo and v_sel:
        df_filtrado = df_filtrado[df_filtrado["Nombre"].isin(v_sel)]
    if m_dispo and m_sel:
        df_filtrado = df_filtrado[df_filtrado["Marca"].isin(m_sel) | df_filtrado["Marca"].eq("-")]
    if c_dispo and c_sel:
        df_filtrado = df_filtrado[df_filtrado["CEBE"].isin(c_sel) | df_filtrado["CEBE"].eq("-")]
    if s_dispo and s_sel:
        df_filtrado = df_filtrado[df_filtrado["SEGMENTO"].isin(s_sel) | df_filtrado["SEGMENTO"].eq("-")]

    total_kilos_mes = df_filtrado["Kilos"].sum()
    vendedores_activos = df_filtrado[df_filtrado["Kilos"] > 0]["CodVendedor"].nunique()
    cebes_activos = df_filtrado[df_filtrado["Kilos"] > 0]["CEBE"].nunique()
    marcas_activas = df_filtrado[df_filtrado["Kilos"] > 0]["Marca"].nunique()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 Total Kilos Mes Anterior", f"{total_kilos_mes:,.1f} kg")
    m2.metric("👥 Vendedores c/ Venta", str(vendedores_activos))
    m3.metric("🏷️ CEBEs Activos", str(cebes_activos))
    m4.metric("🎯 Marcas Activas", str(marcas_activas))

    st.divider()

    if not df_filtrado.empty:
        gb = GridOptionsBuilder.from_dataframe(df_filtrado)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=130)
        
        gb.configure_column("CodVendedor", headerName="Cód. Vend", width=100)
        gb.configure_column("Nombre", headerName="Vendedor", width=180)
        gb.configure_column("Supervisor", headerName="Supervisor", width=140)
        gb.configure_column("Marca", headerName="Marca", width=150)
        gb.configure_column("CEBE", headerName="CEBE", width=140)
        gb.configure_column("SEGMENTO", headerName="Segmento", width=160)
        gb.configure_column(
            "Kilos", 
            headerName="Kilos",
            valueFormatter="x != null ? Number(x).toLocaleString('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'"
        )

        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        grid_options = gb.build()

        AgGrid(
            df_filtrado,
            gridOptions=grid_options,
            height=480,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=False
        )
    else:
        st.info("No se encontraron registros con las combinaciones seleccionadas.")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_filtrado.to_excel(writer, index=False, sheet_name="Composicion_Kilos_Mes_Ant")
    buffer.seek(0)

    st.download_button(
        label="📥 Descargar Reporte Composición a Excel",
        data=buffer,
        file_name=f"Composicion_Kilos_{mes_ant_eval}_{anio_ant_eval}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"btn_dl_rep_obj_kilos_{anio_op}_{mes_op}"
    )