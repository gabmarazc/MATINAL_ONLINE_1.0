# modules/rep_gerencial.py
import io
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode
from modules import database as db
from modules.utils import tarjeta_metrica_html
from modules.rep_kilos import preparar_datos_ventas_segmento, generar_reporte_avance_kilos_segmento
from modules.rep_ccc import generar_reporte_ccc_taxonomia
from modules.rep_MN import generar_reporte_mn_taxonomia
from modules.rep_cob_marca import generar_reporte_cobertura_marca

def render_rep_gerencial(df_vta, df_universo, df_rutas, df_ausencias, filtros_globales=None):
    st.subheader("📈 Tablero Ejecutivo Gerencial - Consolidado Integral")
    st.markdown("Vista directiva completa con el desglose de objetivos y desempeño por segmento, taxonomía y marcas de la compañía.")

    if filtros_globales is None:
        filtros_globales = {"anio": 2026, "mes": 9, "dia_matinal": "02/09/2026", "dia_venta": "01/09/2026", "supervisor": "TODOS"}

    anio_op = int(filtros_globales.get("anio", 2026))
    mes_op = int(filtros_globales.get("mes", 9))
    dia_matinal = filtros_globales.get("dia_matinal", "02/09/2026")
    dia_venta = filtros_globales.get("dia_venta", "01/09/2026")

    # Carga de maestros
    try:
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        if not maestro_v.empty and "Mes" in maestro_v.columns:
            mv_per = maestro_v[(maestro_v["Mes"].astype(str) == str(mes_op)) & (maestro_v["Anio"].astype(str) == str(anio_op))]
            if not mv_per.empty:
                maestro_v = mv_per
    except Exception:
        maestro_v = pd.DataFrame()

    try:
        maestro_s = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos ORDER BY rowid ASC")
    except Exception:
        maestro_s = pd.DataFrame()

    try:
        maestro_cebe = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
    except Exception:
        maestro_cebe = pd.DataFrame()

    try:
        maestro_ccc_param = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
    except Exception:
        maestro_ccc_param = pd.DataFrame(columns=["Taxonomia", "Porcentaje_Cartera"])

    df_marcas_maestro = db.cargar_tabla_sql("SELECT * FROM parametros_marcas")

    if maestro_v.empty:
        st.warning("⚠️ No se encontró el Maestro de Vendedores cargado para este período.")
        return

    # 1. KILOS: Objetivo vs Operativo por Segmento
    df_vta_prep_k = preparar_datos_ventas_segmento(df_vta, df_ausencias, anio_op, mes_op, dia_matinal)
    rep_kilos = generar_reporte_avance_kilos_segmento(df_vta_prep_k, df_rutas, maestro_v, maestro_s, maestro_cebe, dia_venta, anio_op, mes_op, "TODOS")
    rep_kilos_puro = rep_kilos[~rep_kilos["CodVendedor"].isin([-999, -998])].copy()
    rep_kilos_puro["Neto_Operativo"] = rep_kilos_puro["Arrastre"] + rep_kilos_puro["Actual"] + rep_kilos_puro.get("Ajuste_Por_Reemp", 0.0)

    df_kilos_seg = rep_kilos_puro.groupby("SEGMENTO", as_index=False).agg(
        Objetivo_Kg=("Objetivo Mes Corriente", "sum"),
        Operativo_Kg=("Neto_Operativo", "sum")
    )
    df_kilos_seg["% Cumplimiento"] = (df_kilos_seg["Operativo_Kg"] / df_kilos_seg["Objetivo_Kg"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)

    # 2. CCC: Objetivos y Cantidades por Taxonomía
    rep_ccc = generar_reporte_ccc_taxonomia(df_vta, df_universo, maestro_v, maestro_ccc_param, filtros_globales)
    if not rep_ccc.empty:
        df_ccc_tax = rep_ccc.groupby("Taxonomia", as_index=False).agg(
            Cartera_Neta=("Cartera_Neta", "sum"),
            Objetivo_CCC=("Objetivo_CCC", "sum"),
            CCC_Real=("CCC", "sum")
        )
        df_ccc_tax["% Cumplimiento CCC"] = (df_ccc_tax["CCC_Real"] / df_ccc_tax["Objetivo_CCC"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    else:
        df_ccc_tax = pd.DataFrame(columns=["Taxonomia", "Cartera_Neta", "Objetivo_CCC", "CCC_Real", "% Cumplimiento CCC"])

    # 3. MI NEGOCIO: Clientes del Universo por Taxonomía (No Digital, Híbridos, FullyDigital)
    rep_mn = generar_reporte_mn_taxonomia(df_vta, df_universo, maestro_v, filtros_globales)
    if not rep_mn.empty:
        df_mn_tax = rep_mn.groupby("Taxonomia", as_index=False).agg(
            Universo_Clientes=("Cliente", "count"),
            No_Digital=("Es_NoDigital", lambda x: int(x.sum())),
            Hibridos=("Es_Hibrido", lambda x: int(x.sum())),
            Fully_Digital=("Es_FullyDigital", lambda x: int(x.sum()))
        )
        df_mn_tax["% Adopción App"] = ((df_mn_tax["Hibridos"] + df_mn_tax["Fully_Digital"]) / df_mn_tax["Universo_Clientes"].replace(0, pd.NA)).mul(100.0).fillna(0.0).round(2)
    else:
        df_mn_tax = pd.DataFrame(columns=["Taxonomia", "Universo_Clientes", "No_Digital", "Hibridos", "Fully_Digital", "% Adopción App"])

    # 4. COBERTURA POR MARCA: Objetivos y Real
    generar_reporte_cobertura_marca(df_vta, df_universo, maestro_v, df_marcas_maestro, filtros_globales)
    cartera_base = st.session_state.get("_cob_cartera_base", pd.DataFrame())
    vtas_agrup = st.session_state.get("_cob_vtas_agrupadas", pd.DataFrame())
    marcas_lst = st.session_state.get("_cob_marcas", [])
    mapa_obj = st.session_state.get("_cob_mapa_objetivos", {})

    registros_marca = []
    total_cartera_global = len(cartera_base) if not cartera_base.empty else 0
    if not cartera_base.empty and marcas_lst:
        clientes_unicos_cartera = set(cartera_base["Cliente_Cod"].unique())
        for m in marcas_lst:
            obj_m = mapa_obj.get(m, 80.0)
            if not vtas_agrup.empty:
                cubiertos_m = vtas_agrup[
                    vtas_agrup["Cliente"].isin(clientes_unicos_cartera) &
                    (vtas_agrup["Marca"] == m) &
                    (vtas_agrup["Total_Cant"] >= 3)
                ]["Cliente"].nunique()
            else:
                cubiertos_m = 0
            
            cob_real_pct = (cubiertos_m / total_cartera_global * 100.0) if total_cartera_global > 0 else 0.0
            cumpl_marca_pct = (cob_real_pct / obj_m * 100.0) if obj_m > 0 else 0.0
            
            registros_marca.append({
                "Marca": m,
                "Objetivo_Cobertura_Pct": obj_m,
                "Clientes_Cubiertos": cubiertos_m,
                "Cartera_Total": total_cartera_global,
                "Cobertura_Real_Pct": round(cob_real_pct, 2),
                "Cumplimiento_Marca_Pct": round(cumpl_marca_pct, 2)
            })
    df_marcas_res = pd.DataFrame(registros_marca)

    # RENDERIZADO EN PESTAÑAS LIMPIAS
    tab_k, tab_c, tab_mn, tab_m = st.tabs(["📦 Kilos por Segmento", "📈 CCC por Taxonomía", "📱 MiNegocio por Taxonomía", "🎯 Cobertura por Marca"])

    with tab_k:
        st.markdown("### 📦 1. Kilos: Objetivo de la Compañía vs Kilos Operativos por Segmento")
        st.dataframe(df_kilos_seg, width="stretch", hide_index=True)
        
        buf1 = io.BytesIO()
        with pd.ExcelWriter(buf1, engine="openpyxl") as w:
            df_kilos_seg.to_excel(w, index=False, sheet_name="Kilos_Segmento")
        st.download_button("📥 Descargar Kilos por Segmento a Excel", data=buf1.getvalue(), file_name="kilos_por_segmento.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_kilos_seg")

    with tab_c:
        st.markdown("### 📈 2. CCC: Objetivo, Cantidad de CCC y Cumplimiento por Taxonomía")
        st.dataframe(df_ccc_tax, width="stretch", hide_index=True)

        buf2 = io.BytesIO()
        with pd.ExcelWriter(buf2, engine="openpyxl") as w:
            df_ccc_tax.to_excel(w, index=False, sheet_name="CCC_Taxonomia")
        st.download_button("📥 Descargar CCC por Taxonomía a Excel", data=buf2.getvalue(), file_name="ccc_por_taxonomia.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_ccc_tax")

    with tab_mn:
        st.markdown("### 📱 3. MiNegocio: Clientes del Universo por Taxonomía (No Digital, Híbridos, FullyDigital)")
        st.dataframe(df_mn_tax, width="stretch", hide_index=True)

        buf3 = io.BytesIO()
        with pd.ExcelWriter(buf3, engine="openpyxl") as w:
            df_mn_tax.to_excel(w, index=False, sheet_name="MiNegocio_Taxonomia")
        st.download_button("📥 Descargar MiNegocio por Taxonomía a Excel", data=buf3.getvalue(), file_name="minegocio_por_taxonomia.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_mn_tax")

    with tab_m:
        st.markdown("### 🎯 4. Cobertura por Marca: Objetivo, Cobertura Real y Cumplimiento de la Compañía")
        st.dataframe(df_marcas_res, width="stretch", hide_index=True)

        buf4 = io.BytesIO()
        with pd.ExcelWriter(buf4, engine="openpyxl") as w:
            df_marcas_res.to_excel(w, index=False, sheet_name="Cobertura_Marca")
        st.download_button("📥 Descargar Cobertura por Marca a Excel", data=buf4.getvalue(), file_name="cobertura_por_marca_resumen.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_marca_res")