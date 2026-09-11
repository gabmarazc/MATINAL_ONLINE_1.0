# generar_objetivos_manuales.py
import io
import streamlit as st
import pandas as pd
from modules import database as db
from modules.rep_obj_kilos import generar_distribucion_objetivos_macro

st.set_page_config(
    page_title="Generador Exclusivo de Objetivos Globales",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Desagregación Global de Objetivos por Vendedor y Segmento")
st.markdown("Esta herramienta procesa la participación histórica y la distribuye sobre los objetivos globales ingresados, generando el archivo Excel final para la calibración.")

OBJETIVOS_GLOBALES_DICT = {
    1: 2500,
    2: 2144,
    3: 2500,
    4: 2800,
    5: 2100,
    6: 3814,
    8: 3100,
    9: 3350,
    10: 3764,
    11: 2296,
    13: 3100,
    14: 3078,
    15: 3020,
    19: 2800,
    22: 2850,
    23: 3580,
    24: 2259,
    25: 2606,
    28: 2300,
    32: 2400,
    37: 2135,
    39: 1950,
    40: 2200
}

col1, col2 = st.columns(2)
with col1:
    anio_op = st.number_input("Año Operativo", value=2026, step=1)
with col2:
    mes_op = st.number_input("Mes Operativo", value=9, min_value=1, max_value=12, step=1)

if st.button("🚀 Calcular y Generar Excel Desagregado", type="primary"):
    with st.spinner("Cargando bases operativas y calculando participaciones..."):
        df_vta = db.cargar_tabla_sql("SELECT * FROM vta")
        maestro_v = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        maestro_seg = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos")
        maestro_cebe_act = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        maestro_cebe_ant = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")

        if df_vta.empty or maestro_v.empty:
            st.error("⚠️ No se encontraron las tablas 'vta' o 'maestro_vendedores' en la base SQLite. Verifique que el sistema principal haya sido inicializado.")
        else:
            df_base, seg_orden = generar_distribucion_objetivos_macro(
                df_vta, maestro_v, maestro_cebe_act, maestro_cebe_ant, maestro_seg, int(anio_op), int(mes_op)
            )

            if df_base.empty:
                st.warning("⚠️ El motor no pudo calcular participaciones para el período seleccionado.")
            else:
                # CONSOLIDACIÓN CRÍTICA: Agrupación estricta por Vendedor y Segmento para evitar filas duplicadas por marca
                df_base = df_base.groupby(
                    ["Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "SEGMENTO"],
                    as_index=False
                ).agg({
                    "Kilos_Mes_Anterior": "sum",
                    "Objetivo_Mes_Anterior_Kg": "sum"
                })

                df_base["Logro_Anterior_Pct"] = (
                    df_base["Kilos_Mes_Anterior"] / df_base["Objetivo_Mes_Anterior_Kg"].replace(0, pd.NA)
                ).mul(100).fillna(0.0)

                # Cálculo de la participación porcentual de cada segmento sobre el total histórico consolidado del vendedor
                totales_vendedor = df_base.groupby("CodVendedor")["Kilos_Mes_Anterior"].transform("sum")
                df_base["Participacion_Segmento"] = (df_base["Kilos_Mes_Anterior"] / totales_vendedor.replace(0, pd.NA)).fillna(0.0)

                # Mapeo y aplicación del objetivo global fijo por CodVendedor
                df_base["Objetivo_Global_Vendor"] = df_base["CodVendedor"].map(OBJETIVOS_GLOBALES_DICT).fillna(0.0)
                df_base["Obj_Sugerido_Kg"] = df_base["Objetivo_Global_Vendor"] * df_base["Participacion_Segmento"]

                df_final = df_base[[
                    "Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "SEGMENTO", 
                    "Kilos_Mes_Anterior", "Objetivo_Mes_Anterior_Kg", "Logro_Anterior_Pct", 
                    "Obj_Sugerido_Kg"
                ]].copy()

                df_final = df_final.sort_values(by=["Supervisor", "Nombre", "SEGMENTO"]).reset_index(drop=True)

                st.success("¡Desagregación completada con éxito!")
                st.dataframe(df_final, width="stretch")

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df_final.to_excel(writer, index=False, sheet_name="Objetivos_Desagregados")
                buffer.seek(0)

                st.download_button(
                    label="📥 Descargar Excel de Objetivos Desagregados para Importar",
                    data=buffer,
                    file_name=f"Objetivos_Desagregados_{mes_op}_{anio_op}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )