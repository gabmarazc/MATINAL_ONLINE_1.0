# modules/parametros.py
import streamlit as st
import pandas as pd
from io import BytesIO

def render_parametros():
    """
    Renderiza la pestaña de configuración de Parámetros y Fechas de forma limpia,
    asegurando un único botón de guardado/recalculo y su respectiva descarga a Excel.
    """
    st.markdown("### Configuración de Parámetros Operativos y Fechas")
    st.markdown("Modifique los valores necesarios en la tabla inferior y haga clic en el botón de guardado para actualizar el motor de cálculo en tiempo real.")

    # Inicializar el DataFrame de parámetros en session_state si no existe
    if "bases" in st.session_state and st.session_state["bases"] is not None:
        bases = st.session_state["bases"]
        if "df_parametros" not in st.session_state:
            st.session_state["df_parametros"] = bases["PARAMETROS"].get("FECHAS", pd.DataFrame()).copy()

    df_param = st.session_state.get("df_parametros", pd.DataFrame())

    if df_param.empty:
        st.warning("No se encontraron parámetros cargados en el sistema.")
        return

    # Editor interactivo de parámetros
    df_editado = st.data_editor(
        df_param,
        key="editor_parametros_fechas",
        num_rows="dynamic",
        use_container_width=True
    )

    st.markdown("---")

    # Contenedor para alinear o mostrar las acciones de forma limpia
    col_btn1, col_btn2 = st.columns([1, 1])

    with col_btn1:
        # ÚNICO BOTÓN DE APLICAR CAMBIOS
        if st.button("💾 Aplicar cambios de fechas y recalcular", key="btn_aplicar_cambios_fechas_modulo", type="primary"):
            st.session_state["df_parametros"] = df_editado
            st.success("¡Parámetros actualizados con éxito! Recargando cálculos...")
            st.rerun()

    with col_btn2:
        # BOTÓN OBLIGATORIO DE DESCARGA A EXCEL
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_editado.to_excel(writer, index=False, sheet_name='Parametros_Fechas')
        excel_data = output.getvalue()

        st.download_button(
            label="📥 Descargar Parámetros a Excel",
            data=excel_data,
            file_name="parametros_fechas_sistema_matinal.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_descargar_parametros_excel_unico"
        )