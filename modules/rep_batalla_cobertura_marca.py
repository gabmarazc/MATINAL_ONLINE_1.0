# modules/rep_batalla_cobertura_marca.py
import streamlit as st
import pandas as pd
from io import BytesIO

def render_rep_batalla_cobertura():
    st.subheader("🎯 Batalla de Cobertura por Marca")
    
    data = {
        "Cliente": ["Supermercado Sur", "Comercial Oeste", "Despensa Norte"],
        "Marca": ["Marca A", "Marca B", "Marca C"],
        "Unidades_Ultimo_Mes": [1, 2, 0],
        "Oportunidad": ["Brecha Detectada", "Brecha Detectada", "Sin Compra"],
    }
    df = pd.DataFrame(data)

    st.dataframe(df, width="stretch")

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Cobertura_Marca')
    
    st.download_button(
        label="📥 Descargar Cobertura por Marca a Excel",
        data=output.getvalue(),
        file_name="cobertura_marca.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )