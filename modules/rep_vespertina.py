# modules/rep_vespertina.py
import io
import sqlite3
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode
from modules import database as db
from modules.utils import parsear_fecha_robusta, tarjeta_metrica_html
from modules.rep_ccc import preparar_ventas_ccc

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

    df["FechaCarga_dt"] = parsear_fecha_robusta(df.get("FechaCarga"))
    
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

    df["_mn_val"] = np.where(df["Es_MiNegocio"], df["ImporteNeto"], 0.0)
    return df

def clasificar_estado_fd(ratio):
    """Clasifica estrictamente el estado digital según el ratio de MiNegocio."""
    if ratio >= 0.70:
        return "Fully Digital"
    elif ratio > 0.0:
        return "Híbrido"
    else:
        return "No Digital"

def generar_reporte_vespertina_resumen(df_vta, df_universo_param, vendedores, filtros_globales=None):
    """Genera las métricas unificadas del Día Venta evaluando estados, conversiones y activaciones CCC (Arrastre + Actual)."""
    dia_venta = filtros_globales.get("dia_venta", "19/09/2026") if filtros_globales else "19/09/2026"
    anio_op = int(filtros_globales.get("anio", 2026)) if filtros_globales else 2026
    mes_op = int(filtros_globales.get("mes", 9)) if filtros_globales else 9
    dia_matinal = filtros_globales.get("dia_matinal", "21/09/2026") if filtros_globales else "21/09/2026"

    df_full = preparar_ventas_vespertina_resumen(df_vta, dia_venta)
    if df_full.empty:
        return pd.DataFrame()

    dia_vta_dt = parsear_fecha_robusta(pd.Series([dia_venta])).iloc[0]
    target_date = dia_vta_dt.date() if pd.notna(dia_vta_dt) else None

    # Merge riguroso con maestro de vendedores para asegurar supervisores
    vendedores_df = pd.DataFrame()
    vendedores_seguro = vendedores.copy() if vendedores is not None and not vendedores.empty else pd.DataFrame(columns=["Codigo_Vendedor", "Nombre_Vendedor", "Supervisor"])
    
    col_c_v = next((c for c in ["Codigo_Vendedor", "CodVend", "CodVendedor"] if c in vendedores_seguro.columns), vendedores_seguro.columns[0])
    col_n_v = next((c for c in ["Nombre_Vendedor", "Nombre"] if c in vendedores_seguro.columns), vendedores_seguro.columns[1] if len(vendedores_seguro.columns) > 1 else vendedores_seguro.columns[0])
    col_s_v = next((c for c in ["Supervisor", "SUP"] if c in vendedores_seguro.columns), vendedores_seguro.columns[2] if len(vendedores_seguro.columns) > 2 else vendedores_seguro.columns[0])

    vendedores_df["CodVendedor"] = pd.to_numeric(vendedores_seguro[col_c_v], errors="coerce").astype("Int64")
    vendedores_df["Nombre"] = vendedores_seguro[col_n_v].fillna("").astype(str).str.strip()
    vendedores_df["SUP"] = vendedores_seguro[col_s_v].fillna("").astype(str).str.strip()
    vendedores_df = vendedores_df[vendedores_df["CodVendedor"] != 20].drop_duplicates("CodVendedor")

    if not df_full.empty and not vendedores_df.empty:
        df_full = df_full.merge(vendedores_df[["CodVendedor", "SUP"]], on="CodVendedor", how="left")
        df_full["SUP"] = df_full["SUP"].fillna("SIN SUPERVISOR")
    else:
        df_full["SUP"] = "SIN SUPERVISOR"

    # Carga robusta de la tabla universo para evitar taxonomías nulas
    univ_m = pd.DataFrame()
    try:
        univ_m = db.cargar_tabla_sql("SELECT * FROM universo")
    except Exception:
        pass

    if univ_m.empty and df_universo_param is not None and not df_universo_param.empty:
        univ_m = df_universo_param.copy()

    df_full["Cliente"] = pd.to_numeric(df_full["Cliente"], errors="coerce").astype("Int64")

    if not df_full.empty and not univ_m.empty:
        subramo_u = next((c for c in univ_m.columns if "subramo" in str(c).lower()), None)
        if subramo_u:
            univ_m = univ_m[~univ_m[subramo_u].fillna("").astype(str).str.strip().str.upper().isin(["EMPLOYEES", "EMPLEADOS"])].copy()

        col_cu = next((c for c in ["Codigo", "Cliente", "NroCliente", "CodCliente"] if c in univ_m.columns), univ_m.columns[0])
        univ_m["Cliente"] = pd.to_numeric(univ_m[col_cu], errors="coerce").astype("Int64")
        
        col_tax_univ = next((c for c in univ_m.columns if str(c).strip().lower().replace("_", "") == "segmentoclientecodigo" or any(k in str(c).lower() for k in ["taxonomia", "clasificacion", "tax"])), None)
        if col_tax_univ:
            univ_m["Taxonomia"] = univ_m[col_tax_univ].fillna("").astype(str).str.strip().str.upper()
        else:
            univ_m["Taxonomia"] = "SIN TAXONOMIA"
        
        univ_m["Taxonomia"] = univ_m["Taxonomia"].replace(["", "NAN", "NONE", "NAT"], "SIN TAXONOMIA")
        
        col_nom_c = next((c for c in ["Razon_Social", "RazonSocial", "NombreCliente", "Nombre_Cliente", "ClienteDesc"] if c in univ_m.columns), col_cu)
        univ_m["NombreCliente"] = univ_m[col_nom_c].fillna("").astype(str) if col_nom_c in univ_m.columns else ""

        univ_m_subset = univ_m[["Cliente", "Taxonomia", "NombreCliente"]].drop_duplicates(subset=["Cliente"]).copy()
        df_full = df_full.merge(univ_m_subset, on="Cliente", how="left")
    else:
        df_full["Taxonomia"] = "SIN TAXONOMIA"
        df_full["NombreCliente"] = "CLIENTE SIN PADS"

    if "Taxonomia" not in df_full.columns:
        df_full["Taxonomia"] = "SIN TAXONOMIA"
    
    mask_sin_tax = df_full["Taxonomia"].astype(str).str.strip().str.upper().isin(["SIN TAXONOMIA", "", "NAN", "NONE"])
    if mask_sin_tax.any():
        clientes_faltantes = df_full.loc[mask_sin_tax, "Cliente"].dropna().unique().tolist()
        if clientes_faltantes:
            try:
                conn_rescate = sqlite3.connect("data/matinal.db")
                placeholders = ",".join(["?"] * len(clientes_faltantes))
                query_rescate = f"SELECT Codigo AS Cliente, SegmentoClienteCodigo AS Taxonomia, Razon_Social AS NombreCliente FROM universo WHERE Codigo IN ({placeholders})"
                df_rescatados = pd.read_sql(query_rescate, conn_rescate, params=clientes_faltantes)
                conn_rescate.close()
                
                if not df_rescatados.empty:
                    df_rescatados["Cliente"] = pd.to_numeric(df_rescatados["Cliente"], errors="coerce").astype("Int64")
                    df_rescatados["Taxonomia"] = df_rescatados["Taxonomia"].fillna("SIN TAXONOMIA").astype(str).str.strip().str.upper()
                    mapa_tax_rescate = df_rescatados.set_index("Cliente")["Taxonomia"].to_dict()
                    mapa_nom_rescate = df_rescatados.set_index("Cliente")["NombreCliente"].to_dict()
                    
                    df_full.loc[mask_sin_tax, "Taxonomia"] = df_full.loc[mask_sin_tax, "Cliente"].map(mapa_tax_rescate).fillna(df_full.loc[mask_sin_tax, "Taxonomia"])
                    df_full.loc[mask_sin_tax, "NombreCliente"] = df_full.loc[mask_sin_tax, "Cliente"].map(mapa_nom_rescate).fillna(df_full.loc[mask_sin_tax, "NombreCliente"])
            except Exception:
                pass

    df_full["Taxonomia"] = df_full["Taxonomia"].fillna("SIN TAXONOMIA").replace(["", "NAN", "NONE"], "SIN TAXONOMIA")
    df_full["NombreCliente"] = df_full["NombreCliente"].fillna("CLIENTE SIN NOMBRE")

    # Separar estrictamente la foto operativa del Día Venta (`df_hoy`)
    df_hoy = df_full[df_full["FechaCarga_dt"].dt.date == target_date].copy() if target_date else df_full.copy()

    # MOTOR HISTÓRICO ACUMULADO MENSUAL (Arrastre + Actual hasta el día anterior al Día Venta)
    try:
        df_ausencias = db.cargar_tabla_sql("SELECT * FROM ausencias")
    except Exception:
        df_ausencias = pd.DataFrame()

    df_vta_hist = preparar_ventas_ccc(df_vta, df_ausencias, anio_op, mes_op, dia_matinal)
    
    if not df_vta_hist.empty and target_date:
        df_vta_previo = df_vta_hist[
            (df_vta_hist["Periodo"].isin(["Arrastre", "Actual"])) & 
            (df_vta_hist["FechaCarga_dt"].dt.date < target_date)
        ].copy()
        
        col_c_h = next((c for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"] if c in df_vta_previo.columns), "Cliente")
        df_vta_previo["_Cli"] = pd.to_numeric(df_vta_previo[col_c_h], errors="coerce").astype("Int64")
        
        col_pesos_h = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df_vta_previo.columns), "ImporteNeto")
        col_cant_h = next((c for c in ["CantBase", "CANTBASE", "Cantidad", "Unidades"] if c in df_vta_previo.columns), "CantBase")
        col_orig_h = next((c for c in df_vta_previo.columns if any(k in str(c).lower() for k in ["origen", "canal"])), None)
        
        df_vta_previo["_ImpH"] = pd.to_numeric(df_vta_previo[col_pesos_h], errors="coerce").fillna(0.0)
        df_vta_previo["_CantH"] = pd.to_numeric(df_vta_previo[col_cant_h], errors="coerce").fillna(0.0)
        df_vta_previo["_IsMNH"] = df_vta_previo[col_orig_h].fillna("").astype(str).str.strip().str.contains("minegocio|mi negocio", case=False, na=False) if col_orig_h else False
        df_vta_previo["_MNHVal"] = np.where(df_vta_previo["_IsMNH"], df_vta_previo["_ImpH"], 0.0)

        agg_hist = df_vta_previo.groupby("_Cli", as_index=False).agg(
            CantBase_hist=("_CantH", "sum"),
            ImporteItem_hist=("_ImpH", "sum"),
            VentaTotal_hist=("_ImpH", "sum"),
            VentaMN_hist=("_MNHVal", "sum")
        )
        agg_hist["Era_NC_hist"] = ~((agg_hist["CantBase_hist"] >= 3) & (agg_hist["ImporteItem_hist"] >= 1))
        agg_hist["Ratio_FD_hist"] = np.where(agg_hist["VentaTotal_hist"] != 0, agg_hist["VentaMN_hist"] / agg_hist["VentaTotal_hist"], 0.0)
        agg_hist = agg_hist.rename(columns={"_Cli": "Cliente"})
    else:
        agg_hist = pd.DataFrame(columns=["Cliente", "Era_NC_hist", "Ratio_FD_hist"])

    # ACUMULADO TOTAL DEL MES (Arrastre + Actual completo, incluyendo el Día Venta)
    if not df_vta_hist.empty:
        df_vta_mes_tot = df_vta_hist[df_vta_hist["Periodo"].isin(["Arrastre", "Actual"])].copy()
        col_c_tot = next((c for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"] if c in df_vta_mes_tot.columns), "Cliente")
        df_vta_mes_tot["_CliTot"] = pd.to_numeric(df_vta_mes_tot[col_c_tot], errors="coerce").astype("Int64")
        
        col_pesos_tot = next((c for c in ["ImporteNetoItem", "ImporteNeto", "IMIMPORTENETO", "Neto"] if c in df_vta_mes_tot.columns), "ImporteNeto")
        col_cant_tot = next((c for c in ["CantBase", "CANTBASE", "Cantidad", "Unidades"] if c in df_vta_mes_tot.columns), "CantBase")
        col_orig_tot = next((c for c in df_vta_mes_tot.columns if any(k in str(c).lower() for k in ["origen", "canal"])), None)
        
        df_vta_mes_tot["_ImpTot"] = pd.to_numeric(df_vta_mes_tot[col_pesos_tot], errors="coerce").fillna(0.0)
        df_vta_mes_tot["_CantTot"] = pd.to_numeric(df_vta_mes_tot[col_cant_tot], errors="coerce").fillna(0.0)
        df_vta_mes_tot["_IsMNTot"] = df_vta_mes_tot[col_orig_tot].fillna("").astype(str).str.strip().str.contains("minegocio|mi negocio", case=False, na=False) if col_orig_tot else False
        df_vta_mes_tot["_MNTotVal"] = np.where(df_vta_mes_tot["_IsMNTot"], df_vta_mes_tot["_ImpTot"], 0.0)

        agg_tot = df_vta_mes_tot.groupby("_CliTot", as_index=False).agg(
            CantBase_tot=("_CantTot", "sum"),
            ImporteItem_tot=("_ImpTot", "sum"),
            VentaTotal_tot=("_ImpTot", "sum"),
            VentaMN_tot=("_MNTotVal", "sum")
        )
        agg_tot["Cumple_CCC_tot"] = (agg_tot["CantBase_tot"] >= 3) & (agg_tot["ImporteItem_tot"] >= 1)
        agg_tot["Ratio_FD_tot"] = np.where(agg_tot["VentaTotal_tot"] != 0, agg_tot["VentaMN_tot"] / agg_tot["VentaTotal_tot"], 0.0)
        agg_tot = agg_tot.rename(columns={"_CliTot": "Cliente"})
    else:
        agg_tot = pd.DataFrame(columns=["Cliente", "Cumple_CCC_tot", "Ratio_FD_tot"])

    # Verificación de compra real en el Día Venta (admite montos netos positivos y negativos)
    df_neto_hoy = df_hoy.groupby("Cliente", as_index=False).agg(
        ImporteNeto_Dia=("ImporteNeto", "sum"),
        CantBase_Dia=("CantBase", "sum")
    )
    clientes_compra_real = set(df_neto_hoy[(df_neto_hoy["ImporteNeto_Dia"] != 0) | (df_neto_hoy["CantBase_Dia"] != 0)]["Cliente"].dropna().tolist())

    # Consolidado y asignación de estados, activaciones CCC y triggers de conversión
    clientes_hoy = df_hoy[["Cliente"]].drop_duplicates().copy()
    clientes_hoy = clientes_hoy.merge(agg_hist[["Cliente", "Era_NC_hist", "Ratio_FD_hist"]], on="Cliente", how="left")
    clientes_hoy = clientes_hoy.merge(agg_tot[["Cliente", "Cumple_CCC_tot", "Ratio_FD_tot"]], on="Cliente", how="left")

    clientes_hoy["Era_NC_hist"] = clientes_hoy["Era_NC_hist"].fillna(True)
    clientes_hoy["Cumple_CCC_tot"] = clientes_hoy["Cumple_CCC_tot"].fillna(False)
    clientes_hoy["Ratio_FD_hist"] = clientes_hoy["Ratio_FD_hist"].fillna(0.0)
    clientes_hoy["Ratio_FD_tot"] = clientes_hoy["Ratio_FD_tot"].fillna(0.0)

    clientes_hoy["Estado_Hist"] = clientes_hoy["Ratio_FD_hist"].apply(clasificar_estado_fd)
    clientes_hoy["Estado_Tot"] = clientes_hoy["Ratio_FD_tot"].apply(clasificar_estado_fd)

    clientes_hoy["Es_Compra_Real_Dia"] = clientes_hoy["Cliente"].isin(clientes_compra_real)
    
    # Trigger CCC: Era NC hasta el día anterior y con la venta de hoy alcanza los umbrales CCC
    clientes_hoy["Es_Activado_Dia"] = clientes_hoy["Es_Compra_Real_Dia"] & clientes_hoy["Era_NC_hist"] & clientes_hoy["Cumple_CCC_tot"]
    
    # Trigger de Conversión Fully Digital: Estado previo No Digital u Híbrido que evoluciona a Fully Digital con compra real en el dia
    clientes_hoy["Es_Conversion_FullyDigital"] = (
        clientes_hoy["Es_Compra_Real_Dia"] &
        clientes_hoy["Estado_Hist"].isin(["No Digital", "Híbrido"]) &
        (clientes_hoy["Estado_Tot"] == "Fully Digital")
    )

    mapa_ccc = clientes_hoy.set_index("Cliente")["Es_Activado_Dia"].to_dict()
    mapa_fd = clientes_hoy.set_index("Cliente")["Es_Conversion_FullyDigital"].to_dict()
    mapa_compra = clientes_hoy.set_index("Cliente")["Es_Compra_Real_Dia"].to_dict()

    df_hoy["Es_Activado_Dia"] = df_hoy["Cliente"].map(mapa_ccc).fillna(False)
    df_hoy["Es_Conversion_FullyDigital"] = df_hoy["Cliente"].map(mapa_fd).fillna(False)
    df_hoy["Es_Compra_Real_Dia"] = df_hoy["Cliente"].map(mapa_compra).fillna(False)

    return df_hoy

@st.fragment
def render_fragmento_vespertina_resumen(df_filtrado):
    if df_filtrado is None or df_filtrado.empty:
        st.info("No se registraron operaciones para el Día Venta seleccionado.")
        return

    sup_dispo = sorted(df_filtrado["SUP"].dropna().astype(str).str.strip().unique().tolist())
    sup_selec = st.multiselect("Supervisor", options=sup_dispo, default=[], placeholder="Seleccionar supervisores...", key="frag_vesp_res_supervisor")

    if sup_selec:
        df_filtrado = df_filtrado[df_filtrado["SUP"].astype(str).str.strip().isin(sup_selec)].copy()

    if df_filtrado.empty:
        st.info("No se encontraron registros para los supervisores seleccionados.")
        return

    tot_kilos = float(df_filtrado["PesoKg"].sum())
    tot_importe = float(df_filtrado["ImporteNeto"].sum())
    
    df_compradores_validos = df_filtrado[df_filtrado["Es_Compra_Real_Dia"]].drop_duplicates(subset=["Cliente"])
    tot_clientes_compra = int(df_compradores_validos["Cliente"].nunique())
    
    df_cli_activados_global = df_filtrado[df_filtrado["Es_Activado_Dia"]].drop_duplicates(subset=["Cliente"]) if "Es_Activado_Dia" in df_filtrado.columns else pd.DataFrame()
    tot_ccc_dia = int(df_cli_activados_global["Cliente"].nunique()) if not df_cli_activados_global.empty else 0

    df_conversion_global = df_filtrado[df_filtrado["Es_Conversion_FullyDigital"]].drop_duplicates(subset=["Cliente"])
    tot_conversion_fd = int(df_conversion_global["Cliente"].nunique())

    tot_mn = float(df_filtrado[df_filtrado["Es_MiNegocio"]]["ImporteNeto"].sum())
    pct_mn = (tot_mn / tot_importe * 100.0) if tot_importe > 0 else 0.0

    st.markdown("""
        <style>
        hr {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            border-color: #334155 !important;
        }
        /* Estilo para asegurar que las tablas ajusten automáticamente el ancho de sus columnas */
        dataframe, table, [data-testid="stDataFrame"] div[data-testid="stTable"] {
            width: 100% !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # ==========================================
    # BLOQUE 1: KILOS POR SEGMENTO
    # ==========================================
    st.markdown("### 📦 1. Kilos e Importe por Segmento")
    cols_m1 = st.columns(2)
    with cols_m1[0]:
        st.markdown(tarjeta_metrica_html("KILOS DÍA VENTA", f"{tot_kilos:,.2f} kg", "#10b981", "1.2rem", "0.65rem"), unsafe_allow_html=True)
    with cols_m1[1]:
        st.markdown(tarjeta_metrica_html("IMPORTE NETO DÍA", f"${tot_importe:,.2f}", "#8b5cf6", "1.2rem", "0.65rem"), unsafe_allow_html=True)

    df_seg_view = df_filtrado.groupby("SEGMENTO", as_index=False).agg(
        Kilos=("PesoKg", "sum"),
        Importe_Neto=("ImporteNeto", "sum")
    )
    df_seg_disp = df_seg_view.copy()
    df_seg_disp["Kilos"] = df_seg_disp["Kilos"].apply(lambda x: f"{x:,.2f} kg")
    df_seg_disp["Importe_Neto"] = df_seg_disp["Importe_Neto"].apply(lambda x: f"${x:,.2f}")
    df_seg_disp = df_seg_disp.rename(columns={"SEGMENTO": "Segmento", "Kilos": "Kilos (kg)", "Importe_Neto": "Importe Neto ($)"})
    st.dataframe(df_seg_disp, use_container_width=True, hide_index=True)

    st.divider()

    # ==========================================
    # BLOQUE 2: CCC (CLIENTES Y ACTIVADOS POR TAXONOMÍA)
    # ==========================================
    st.markdown("### 📈 2. CCC (Clientes Compradores y Activados por Taxonomía)")
    cols_m2 = st.columns(2)
    with cols_m2[0]:
        st.markdown(tarjeta_metrica_html("CCC DÍA VENTA (ACTIVADOS)", f"{tot_ccc_dia:,.0f}", "#3b82f6", "1.2rem", "0.65rem"), unsafe_allow_html=True)
    with cols_m2[1]:
        st.markdown(tarjeta_metrica_html("CLIENTES CON COMPRA", f"{tot_clientes_compra:,.0f}", "#06b6d4", "1.2rem", "0.65rem"), unsafe_allow_html=True)

    df_ccc_tax = df_filtrado.groupby("Taxonomia", as_index=False).agg(
        Clientes_Compra=("Cliente", lambda x: df_filtrado.loc[x.index][df_filtrado.loc[x.index, "Es_Compra_Real_Dia"]]["Cliente"].nunique()),
        Clientes_Activados=("Cliente", lambda x: df_filtrado.loc[x.index][df_filtrado.loc[x.index, "Es_Activado_Dia"]]["Cliente"].nunique()) if "Es_Activado_Dia" in df_filtrado.columns else ("Cliente", lambda x: 0)
    )
    df_ccc_tax = df_ccc_tax.rename(columns={"Taxonomia": "Taxonomía", "Clientes_Compra": "Clientes Compradores", "Clientes_Activados": "Clientes Activados (CCC)"})
    st.dataframe(df_ccc_tax, use_container_width=True, hide_index=True)

    st.divider()

    # ==========================================
    # BLOQUE 3: MI NEGOCIO Y CONVERSIÓN
    # ==========================================
    st.markdown("### 📱 3. Adopción MiNegocio y Conversiones Fully Digital")
    cols_m3 = st.columns(3)
    with cols_m3[0]:
        st.markdown(tarjeta_metrica_html("VENTAS TOTALES", f"${tot_importe:,.2f}", "#8b5cf6", "1.2rem", "0.65rem"), unsafe_allow_html=True)
    with cols_m3[1]:
        st.markdown(tarjeta_metrica_html("VENTAS MI NEGOCIO", f"${tot_mn:,.2f}", "#06b6d4", "1.2rem", "0.65rem"), unsafe_allow_html=True)
    with cols_m3[2]:
        st.markdown(tarjeta_metrica_html("CONVERSIONES FD", f"{tot_conversion_fd:,.0f}", "#10b981", "1.2rem", "0.65rem"), unsafe_allow_html=True)

    df_mn_tax = df_filtrado.groupby("Taxonomia", as_index=False).agg(
        Ventas_Totales=("ImporteNeto", "sum"),
        Ventas_MN=("_mn_val", "sum")
    )
    df_mn_tax["% Adopción App"] = (df_mn_tax["Ventas_MN"] / df_mn_tax["Ventas_Totales"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    
    df_mn_disp = df_mn_tax.copy()
    df_mn_disp["Ventas_Totales"] = df_mn_disp["Ventas_Totales"].apply(lambda x: f"${x:,.2f}")
    df_mn_disp["Ventas_MN"] = df_mn_disp["Ventas_MN"].apply(lambda x: f"${x:,.2f}")
    df_mn_disp["% Adopción App"] = df_mn_disp["% Adopción App"].apply(lambda x: f"{x:,.2f}%")
    df_mn_disp = df_mn_disp.rename(columns={"Taxonomia": "Taxonomía", "Ventas_Totales": "Ventas Totales ($)", "Ventas_MN": "Ventas MiNegocio ($)"})
    st.dataframe(df_mn_disp, use_container_width=True, hide_index=True)

    st.divider()

    # ==========================================
    # BLOQUE 4: AUDITORÍA DE CLIENTES ACTIVADOS (CCC)
    # ==========================================
    st.markdown("### 🔍 Auditoría: Detalle de Clientes Activados en el Día Venta")
    st.markdown("Listado completo y consolidado de cada cliente único considerado **Activado** en la jornada:")

    df_activados_audit = df_filtrado[df_filtrado["Es_Activado_Dia"]].groupby("Cliente", as_index=False).agg(
        NombreCliente=("NombreCliente", "first"),
        SUP=("SUP", "first"),
        Taxonomia=("Taxonomia", "first"),
        PesoKg=("PesoKg", "sum"),
        ImporteNeto=("ImporteNeto", "sum")
    ) if "Es_Activado_Dia" in df_filtrado.columns else pd.DataFrame(columns=["Cliente", "NombreCliente", "SUP", "Taxonomia", "PesoKg", "ImporteNeto"])

    if not df_activados_audit.empty:
        df_act_view = df_activados_audit[
            ["Cliente", "NombreCliente", "SUP", "Taxonomia", "PesoKg", "ImporteNeto"]
        ].copy()
        
        df_act_view = df_act_view.rename(columns={
            "Cliente": "Cód. Cliente",
            "NombreCliente": "Razón Social",
            "SUP": "Supervisor",
            "Taxonomia": "Taxonomía",
            "PesoKg": "Kilos Día (kg)",
            "ImporteNeto": "Importe Día ($)"
        })
        df_act_view["Kilos Día (kg)"] = df_act_view["Kilos Día (kg)"].apply(lambda x: f"{x:,.2f} kg")
        df_act_view["Importe Día ($)"] = df_act_view["Importe Día ($)"].apply(lambda x: f"${x:,.2f}")

        st.dataframe(df_act_view, use_container_width=True, hide_index=True)
    else:
        st.info("No se registraron clientes activados para los filtros seleccionados.")

    st.divider()

    # ==========================================
    # BLOQUE 5: AUDITORÍA DE CONVERSIÓN A FULLY DIGITAL
    # ==========================================
    st.markdown("### 📱 Auditoría: Clientes Convertidos a FullyDigital en el Día Venta")
    st.markdown(f"**Total Convertidos a FullyDigital:** {tot_conversion_fd:,} clientes que alcanzaron el umbral del 70% de adopción digital en la jornada.")

    df_conversion_audit = df_filtrado[df_filtrado["Es_Conversion_FullyDigital"]].groupby("Cliente", as_index=False).agg(
        NombreCliente=("NombreCliente", "first"),
        SUP=("SUP", "first"),
        Taxonomia=("Taxonomia", "first"),
        PesoKg=("PesoKg", "sum"),
        ImporteNeto=("ImporteNeto", "sum")
    )

    if not df_conversion_audit.empty:
        df_conv_view = df_conversion_audit[
            ["Cliente", "NombreCliente", "SUP", "Taxonomia", "PesoKg", "ImporteNeto"]
        ].copy()
        
        df_conv_view = df_conv_view.rename(columns={
            "Cliente": "Cód. Cliente",
            "NombreCliente": "Razón Social",
            "SUP": "Supervisor",
            "Taxonomia": "Taxonomía",
            "PesoKg": "Kilos Día (kg)",
            "ImporteNeto": "Importe Día ($)"
        })
        df_conv_view["Kilos Día (kg)"] = df_conv_view["Kilos Día (kg)"].apply(lambda x: f"{x:,.2f} kg")
        df_conv_view["Importe Día ($)"] = df_conv_view["Importe Día ($)"].apply(lambda x: f"${x:,.2f}")

        st.dataframe(df_conv_view, use_container_width=True, hide_index=True)
    else:
        st.info("No se registraron conversiones a FullyDigital para los filtros seleccionados.")

    st.divider()

    # Descarga a Excel integrada con openpyxl e io.BytesIO
    buffer_vesp = io.BytesIO()
    with pd.ExcelWriter(buffer_vesp, engine="openpyxl") as writer:
        df_seg_view.to_excel(writer, index=False, sheet_name="Kilos_Por_Segmento")
        if not df_ccc_tax.empty:
            df_ccc_tax.to_excel(writer, index=False, sheet_name="CCC_Por_Taxonomia")
        df_mn_tax.to_excel(writer, index=False, sheet_name="Adopcion_MiNegocio")
        if not df_activados_audit.empty:
            df_act_view.to_excel(writer, index=False, sheet_name="Clientes_Activados_Auditoria")
        if not df_conversion_audit.empty:
            df_conv_view.to_excel(writer, index=False, sheet_name="Conversion_FullyDigital")
    buffer_vesp.seek(0)

    st.download_button(
        label="📥 Descargar Reporte Vespertina a Excel",
        data=buffer_vesp,
        file_name="Reporte_Vespertina_Resumen.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="vesp_resumen_btn_dl"
    )

def render_rep_vespertina(df_vta, df_universo, filtros_globales=None):
    st.subheader("🌙 Reporte Vespertina - Resumen Ejecutivo del Día Venta")
    st.markdown("Consolidado operativo riguroso con motor de estados (No Digital, Híbrido, Fully Digital) y activaciones CCC basados en Arrastre + Actual.")

    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
    except Exception:
        maestro_v = pd.DataFrame()

    df_filtrado = generar_reporte_vespertina_resumen(df_vta, df_universo, maestro_v, filtros_globales)
    render_fragmento_vespertina_resumen(df_filtrado)