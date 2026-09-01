# st_aggrid.py (Módulo de compatibilidad local actualizado)
import streamlit as st
import pandas as pd

def AgGrid(df, gridOptions=None, height=400, width="100%", **kwargs):
    if isinstance(df, pd.DataFrame) and not df.empty:
        st.dataframe(df, height=height, use_container_width=True)
    else:
        st.warning("No hay datos disponibles para mostrar.")
    return {"data": df, "selected_rows": []}

class GridOptionsBuilder:
    @classmethod
    def from_dataframe(cls, dataframe):
        return cls()
    def configure_default_column(self, *args, **kwargs): pass
    def configure_column(self, *args, **kwargs): pass
    def configure_pagination(self, *args, **kwargs): pass
    def build(self): return {}

class DataReturnMode:
    FILTERED_AND_SORTED = "FILTERED_AND_SORTED"

class GridUpdateMode:
    VALUE_CHANGED = "VALUE_CHANGED"

def JsCode(text):
    return text