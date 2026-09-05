# modules/rep_ccc.py
import streamlit as st
import pandas as pd
from io import BytesIO

def render_rep_ccc(df_vta, df_universo):
    st.subheader("📈 Avance de Condiciones de Crédito Comercial (CCC)")
    
    data = {
        "Taxonomía": ["Clase A", "Clase B", "Clase C", "Clase D"],
        "Clientes_Totales": [120, 250, 400, 150],
        "Clientes_Con_CCC": [110, 200, 300, 90],
    }
    df = pd.DataFrame(data)
    df["Cobertura_CCC_%"] = (df["Clientes_Con_CCC"] / df["Clientes_Totales"] * 100).round(2)

    st.dataframe(df, width="stretch")

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Avance_CCC')
    
    st.download_button(
        label="📥 Descargar Reporte CCC a Excel",
        data=output.getvalue(),
        file_name="avance_ccc.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )