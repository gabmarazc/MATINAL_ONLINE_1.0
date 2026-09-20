# modules/rep_vespertina.py
import io
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import parsear_fecha_robusta, tarjeta_metrica_html

def preparar_ventas_vespertina_resumen(df_vta, dia_venta):
    """Pipeline de datos exclusivo para el resumen ejecutivo del Día Venta."""
    df_corp = db.obtener_df_maestro_corporativo()
    df = df_corp.copy() if not df_corp.empty else (df_vta.copy() if df_vta is not None and not df_vta.empty else pd.DataFrame())
    
    if df.empty:
        return df

    col_pesos = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df.columns), None)
    df["ImporteNeto"] = pd.to_numeric(df[col_pesos], errors="coerce").fillna(0.0) if col_pesos else 0.0

    col_kg = next((c for c in ["PesoKg", "PESOKG", "Kilos", "KILOS"] if c in df.columns), None)
    df["PesoKg"] = pd.to_numeric(df[col_kg], errors="coerce").fillna(0.0) if col_kg else 0.0

    col_cant = next((c for c in ["CantBase", "CANTBASE", "Cantidad", "CANTIDAD", "Unidades", "UNIDADES"] if c in df.columns), df.columns[0])
    df["CantBase"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0.0)

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

    # Filtrado estricto al Día Venta
    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    dia_vta_dt = parsear_fecha_robusta(pd.Series([dia_venta])).iloc[0]
    if pd.notna(dia_vta_dt):
        df = df[df["FechaCarga_dt"].dt.date == dia_vta_dt.date()].copy()

    col_vend_tit = next((cand for cand in ["CodVendedor", "Cod_Vendedor", "CodVen", "Vendedor"] if cand in df.columns), "CodVendedor")
    df["CodVendedor"] = pd.to_numeric(df[col_vend_tit], errors="coerce").astype("Int64")
    df = df[df["CodVendedor"] != 20]

    col_rent = "SegmentoRentabilidad" if "SegmentoRentabilidad" in df.columns else None
    col_rubro = "Rubro" if "Rubro" in df.columns else None
    
    sr = df.get(col_rent, pd.Series("", index=df.index)).fillna("").astype(str).str.strip().str.title() if col_rent else pd.Series("", index=df.index)
    rubro = df.get(col_rubro, pd.Series("", index=df.index)).fillna("").astype(str).str.strip() if col_rubro else pd.Series("", index=df.index)
    
    cond_gold = sr.isin(["Platinum", "Gold"]).fillna(False)
    cond_silver = sr.isin(["Silver", "Bronze"]).fillna(False)
    
    gold_val = "GOLD " + rubro
    silver_val = "SILVER " + rubro
    df["SEGMENTO"] = np.select(
        [cond_gold, cond_silver],
        [gold_val.str.strip(), silver_val.str.strip()],
        default="SIN SEGMENTO"
    )

    return df

def generar_reporte_vespertina_resumen(df_vta, df_universo, vendedores, filtros_globales=None):
    """Genera las métricas unificadas del Día Venta para el reporte Vespertina."""
    dia_venta = filtros_globales.get("dia_venta", "01/09/2026") if filtros_globales else "01/09/2026"
    anio_op = int(filtros_globales.get("anio", 2026)) if filtros_globales else 2026
    mes_op = int(filtros_globales.get("mes", 9)) if filtros_globales else 9
    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026") if filtros_globales else "02/09/2026"

    df_prep = preparar_ventas_vespertina_resumen(df_vta, dia_venta)

    vendedores_df = pd.DataFrame()
    vendedores_seguro = vendedores.copy() if vendedores is not None and not vendedores.empty else pd.DataFrame(columns=["Codigo_Vendedor", "Nombre_Vendedor", "Supervisor"])
    
    col_c_v = next((c for c in ["Codigo_Vendedor", "CodVend", "CodVendedor"] if c in vendedores_seguro.columns), vendedores_seguro.columns[0])
    col_n_v = next((c for c in ["Nombre_Vendedor", "Nombre"] if c in vendedores_seguro.columns), vendedores_seguro.columns[1] if len(vendedores_seguro.columns) > 1 else vendedores_seguro.columns[0])
    col_s_v = next((c for c in ["Supervisor", "SUP"] if c in vendedores_seguro.columns), vendedores_seguro.columns[2] if len(vendedores_seguro.columns) > 2 else vendedores_seguro.columns[0])

    vendedores_df["CodVendedor"] = pd.to_numeric(vendedores_seguro[col_c_v], errors="coerce").astype("Int64")
    vendedores_df["Nombre"] = vendedores_seguro[col_n_v].fillna("").astype(str).str.strip()
    vendedores_df["SUP"] = vendedores_seguro[col_s_v].fillna("").astype(str).str.strip()
    vendedores_df = vendedores_df[vendedores_df["CodVendedor"] != 20].drop_duplicates("CodVendedor")

    # 1. Kilos por Segmento en el Día Venta
    if not df_prep.empty:
        df_prep["Cliente"] = pd.to_numeric(df_prep.get("Cliente", df_prep.columns[0]), errors="coerce").astype("Int64")
        kilos_seg = df_prep.groupby(["CodVendedor", "SEGMENTO"], as_index=False).agg(
            Kilos=("PesoKg", "sum"),
            Importe_Neto=("ImporteNeto", "sum"),
            Clientes_Compra=("Cliente", "nunique")
        )
    else:
        kilos_seg = pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Kilos", "Importe_Neto", "Clientes_Compra"])

    # 2. Clientes con Compra y CCC del Día Venta (pasaron de NC a CC en el día)
    from modules.rep_ccc import _calcular_base_ccc
    try:
        maestro_ccc = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
    except Exception:
        maestro_ccc = pd.DataFrame(columns=["Taxonomia", "Porcentaje_Cartera"])

    # Calculamos base CCC utilizando las ventas acumuladas hasta el día anterior vs día venta para detectar activación
    _, df_det_clientes_ccc = _calcular_base_ccc(df_vta, df_universo, vendedores_seguro, maestro_ccc, anio_op, mes_op, dia_matinal)
    
    if not df_prep.empty and not df_det_clientes_ccc.empty:
        clientes_dia_venta = set(df_prep["Cliente"].dropna().unique())
        # Identificar clientes que compraron en el día venta y cuya condición cambió (activos en el día)
        df_det_clientes_ccc["Compro_Dia_Venta"] = df_det_clientes_ccc["Cliente"].isin(clientes_dia_venta)
        
        ccc_dia = df_det_clientes_ccc.groupby("CodVendedor", as_index=False).agg(
            CCC_Dia_Venta=("Compro_Dia_Venta", lambda x: int(x.sum()))
        )
    else:
        ccc_dia = pd.DataFrame(columns=["CodVendedor", "CCC_Dia_Venta"])

    # 3. Ventas Totales y Adopción MiNegocio por Taxonomía en el Día Venta
    if not df_prep.empty and df_universo is not None and not df_universo.empty:
        univ_m = df_universo.copy()
        col_cu = next((c for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"] if c in univ_m.columns), univ_m.columns[0])
        univ_m["Cliente"] = pd.to_numeric(univ_m[col_cu], errors="coerce").astype("Int64")
        tax_col = next((c for c in univ_m.columns if "taxonomia" in str(c).lower() or "segmentoclientecodigo" in str(c).lower()), None)
        univ_m["Taxonomia"] = univ_m[tax_col].fillna("").astype(str).str.strip().str.upper() if tax_col else "A"
        
        df_prep_tax = df_prep.merge(univ_m[["Cliente", "Taxonomia"]], on="Cliente", how="left")
        df_prep_tax["Taxonomia"] = df_prep_tax["Taxonomia"].fillna("SIN TAXONOMIA")
        
        df_prep_tax["_mn_val"] = np.where(df_prep_tax["Es_MiNegocio"], df_prep_tax["ImporteNeto"], 0.0)
        
        tax_agg = df_prep_tax.groupby(["CodVendedor", "Taxonomia"], as_index=False).agg(
            Ventas_Totales_Tax=("ImporteNeto", "sum"),
            Ventas_MN_Tax=("_mn_val", "sum")
        )
    else:
        tax_agg = pd.DataFrame(columns=["CodVendedor", "Taxonomia", "Ventas_Totales_Tax", "Ventas_MN_Tax"])

    # Consolidación final por Vendedor
    resumen_vendedor = vendedores_df.merge(kilos_seg, on="CodVendedor", how="left").merge(ccc_dia, on="CodVendedor", how="left")
    resumen_vendedor[["Kilos", "Importe_Neto", "Clientes_Compra", "CCC_Dia_Venta"]] = resumen_vendedor[["Kilos", "Importe_Neto", "Clientes_Compra", "CCC_Dia_Venta"]].fillna(0.0)

    return resumen_vendedor, tax_agg, df_prep

@st.fragment
def render_fragmento_vespertina_resumen(resumen_vendedor, tax_agg, df_prep, supervisores_seleccionados):
    if resumen_vendedor is None or resumen_vendedor.empty:
        st.info("No se registraron operaciones para el Día Venta seleccionado.")
        return

    df_base = resumen_vendedor.copy()
    sup_str = [str(s).strip() for s in supervisores_seleccionados] if supervisores_seleccionados else []
    
    if sup_str and "SUP" in df_base.columns:
        df_base = df_base[df_base["SUP"].astype(str).str.strip().isin(sup_str)].copy()

    if df_base.empty:
        st.info("No se encontraron registros para los supervisores seleccionados.")
        return

    v_dispo = sorted(df_base["Nombre"].dropna().astype(str).str.strip().unique().tolist())
    s_dispo = sorted(df_base["SEGMENTO"].dropna().astype(str).str.strip().unique().tolist())

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        v_selec = st.multiselect("Vendedor", options=v_dispo, default=[], placeholder="Seleccionar preventistas...", key="frag_vesp_res_vendedor")
    with col_f2:
        s_selec = st.multiselect("Segmento", options=s_dispo, default=[], placeholder="Seleccionar segmentos...", key="frag_vesp_res_segmento")

    if not v_selec:
        v_selec = v_dispo
    if not s_selec:
        s_selec = s_dispo

    mask = (
        df_base["Nombre"].astype(str).str.strip().isin(v_selec) &
        df_base["SEGMENTO"].astype(str).str.strip().isin(s_selec)
    )
    df_filtrado = df_base[mask].copy()

    tot_kilos = float(df_filtrado["Kilos"].sum()) if not df_filtrado.empty else 0.0
    tot_importe = float(df_filtrado["Importe_Neto"].sum()) if not df_filtrado.empty else 0.0
    tot_ccc_dia = int(df_filtrado["CCC_Dia_Venta"].sum()) if not df_filtrado.empty else 0
    tot_clientes_compra = int(df_filtrado["Clientes_Compra"].sum()) if not df_filtrado.empty else 0

    st.markdown("""
        <style>
        hr {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            border-color: #334155 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    cols_m = st.columns(4)
    with cols_m[0]:
        st.markdown(tarjeta_metrica_html("KILOS DÍA VENTA", f"{tot_kilos:,.2f} kg", "#10b981", "1.2rem", "0.65rem"), unsafe_allow_html=True)
    with cols_m[1]:
        st.markdown(tarjeta_metrica_html("IMPORTE NETO DÍA", f"${tot_importe:,.2f}", "#8b5cf6", "1.2rem", "0.65rem"), unsafe_allow_html=True)
    with cols_m[2]:
        st.markdown(tarjeta_metrica_html("CCC DÍA VENTA (ACTIVADOS)", f"{tot_ccc_dia:,.0f}", "#3b82f6", "1.2rem", "0.65rem"), unsafe_allow_html=True)
    with cols_m[3]:
        st.markdown(tarjeta_metrica_html("CLIENTES CON COMPRA", f"{tot_clientes_compra:,.0f}", "#06b6d4", "1.2rem", "0.65rem"), unsafe_allow_html=True)

    st.divider()

    st.markdown("### 📊 Detalle Operativo por Preventista y Segmento")
    df_render_display = df_filtrado.copy()
    df_render_excel = df_filtrado.copy()

    df_render_display["Kilos"] = df_render_display["Kilos"].apply(lambda x: f"{x:,.2f} kg" if pd.notna(x) else "0.00 kg")
    df_render_display["Importe_Neto"] = df_render_display["Importe_Neto"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")

    if not df_render_display.empty:
        gb = GridOptionsBuilder.from_dataframe(df_render_display)
        gb.configure_default_column(filterable=True, sortable=True, resizable=True, minWidth=120)
        
        gb.configure_column("CodVendedor", headerName="Cód. Vend", width=95)
        gb.configure_column("Nombre", headerName="Preventista", minWidth=170)
        gb.configure_column("SUP", headerName="SUP", width=85)
        gb.configure_column("SEGMENTO", headerName="Segmento", minWidth=140)
        gb.configure_column("Clientes_Compra", headerName="Clientes Compra", width=120)
        gb.configure_column("CCC_Dia_Venta", headerName="CCC Día Venta", width=120)
        gb.configure_column("Kilos", headerName="Kilos (kg)", width=120)
        gb.configure_column("Importe_Neto", headerName="Importe Neto ($)", width=130)
        
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        grid_options = gb.build()
        
        AgGrid(
            df_render_display,
            gridOptions=grid_options,
            height=380,
            width="100%",
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            theme="streamlit",
            fit_columns_on_grid_load=True
        )

    st.divider()
    st.markdown("### 📱 Adopción MiNegocio y Ventas Totales por Taxonomía (Día Venta)")

    if not tax_agg.empty:
        tax_grouped = tax_agg.groupby("Taxonomia", as_index=False).agg(
            Ventas_Totales=("Ventas_Totales_Tax", "sum"),
            Ventas_MN=("Ventas_MN_Tax", "sum")
        )
        tax_grouped["% Adopción App"] = (tax_grouped["Ventas_MN"] / tax_grouped["Ventas_Totales"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
        
        tax_disp = tax_grouped.copy()
        tax_disp["Ventas_Totales"] = tax_disp["Ventas_Totales"].apply(lambda x: f"${x:,.2f}")
        tax_disp["Ventas_MN"] = tax_disp["Ventas_MN"].apply(lambda x: f"${x:,.2f}")
        tax_disp["% Adopción App"] = tax_disp["% Adopción App"].apply(lambda x: f"{x:,.2f}%")
        tax_disp = tax_disp.rename(columns={"Taxonomia": "Taxonomía", "Ventas_Totales": "Ventas Totales ($)", "Ventas_MN": "Ventas MiNegocio ($)"})

        st.dataframe(tax_disp, width="stretch", hide_index=True)
    else:
        st.info("No hay datos de taxonomía disponibles para el Día Venta.")

    st.divider()

    buffer_vesp = io.BytesIO()
    with pd.ExcelWriter(buffer_vesp, engine="openpyxl") as writer:
        df_render_excel.to_excel(writer, index=False, sheet_name="Resumen_Vespertina")
        if not tax_agg.empty:
            tax_grouped.to_excel(writer, index=False, sheet_name="Adopcion_Taxonomia_Día")
    buffer_vesp.seek(0)

    st.download_button(
        label="📥 Descargar Resumen Vespertina a Excel",
        data=buffer_vesp,
        file_name="Resumen_Vespertina_Dia_Venta.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="vesp_resumen_btn_dl"
    )

def render_rep_vespertina(df_vta, df_universo, filtros_globales=None):
    st.subheader("🌙 Reporte Vespertina - Resumen Ejecutivo del Día Venta")
    st.markdown("Consolidado operativo exclusivo del **Día Venta** que integra volumen en kilos, activación de CCC del día y participación de ventas por la app MiNegocio desglosada por taxonomía.")

    sup_filtro = "TODOS"
    if filtros_globales and isinstance(filtros_globales, dict):
        sup_filtro = str(filtros_globales.get("supervisor", "TODOS")).strip()

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    except Exception:
        maestro_v = pd.DataFrame()

    resumen_vendedor, tax_agg, df_prep = generar_reporte_vespertina_resumen(df_vta, df_universo, maestro_v, filtros_globales)
    sups_sel = [sup_filtro] if sup_filtro != "TODOS" else None

    render_fragmento_vespertina_resumen(resumen_vendedor, tax_agg, df_prep, sups_sel)