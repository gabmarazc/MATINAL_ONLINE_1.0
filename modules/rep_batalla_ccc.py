# modules/rep_batalla_ccc.py
import streamlit as st
import pandas as pd
from io import BytesIO

def render_rep_batalla_nc(df_vta, df_universo):
    st.subheader("⚔️ Batalla NC: Clientes Activos sin Compra")
    
    data = {
        "Codigo_Cliente": [1001, 1023, 1055, 1089],
        "Razon_Social": ["Kiosco El Rápido", "Almacén Don José", "Minimercado Sol", "Maxikiosco Luna"],
        "Taxonomía": ["A", "B", "A", "C"],
        "Ultima_Compra": ["2026-07-10", "2026-06-15", "2026-05-20", "2026-07-01"]
    }
    df = pd.DataFrame(data)

    st.dataframe(df, width="stretch")

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='No_Compradores')
    
    st.download_button(
        label="📥 Descargar Clientes No Compradores a Excel",
        data=output.getvalue(),
        file_name="clientes_no_compradores.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )