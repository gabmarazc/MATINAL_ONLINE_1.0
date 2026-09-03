# modules/parametros.py
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date, timedelta

def obtener_dia_habil_anterior(d: date) -> date:
    """Retorna el día hábil inmediato anterior (excluyendo sábados y domingos)."""
    d = d - timedelta(days=1)
    while d.weekday() >= 5:  # 5 = Sábado, 6 = Domingo
        d = d - timedelta(days=1)
    return d

def render_parametros():
    """
    Renderiza la pestaña de configuración de Parámetros y Fechas,
    forzando los valores por defecto correctos basados en la fecha actual real.
    """
    st.markdown("### Configuración de Parámetros Operativos y Fechas")
    st.markdown("Modifique los valores necesarios en la tabla inferior y haga clic en el botón de guardado para actualizar el motor de cálculo en tiempo real.")

    # Forzar la inicialización o recálculo limpio basado en la fecha de hoy
    if "bases" in st.session_state and st.session_state["bases"] is not None:
        bases = st.session_state["bases"]
        
        # Forzamos la actualización de fechas por defecto con la fecha real de hoy
        df_temp = bases["PARAMETROS"].get("FECHAS", pd.DataFrame()).copy()
        
        if not df_temp.empty:
            hoy = date.today() # Fecha actual real del sistema
            dia_matinal = hoy
            dia_venta = obtener_dia_habil_anterior(dia_matinal)
            dia_anterior = obtener_dia_habil_anterior(dia_venta)

            col_param = df_temp.columns[0]
            col_val = df_temp.columns[1] if len(df_temp.columns) > 1 else None
            
            if col_val is not None:
                for idx, row in df_temp.iterrows():
                    p_nombre = str(row[col_param]).strip().lower()
                    if "mes" in p_nombre:
                        df_temp.at[idx, col_val] = hoy.strftime("%Y-%m")
                    elif "matinal" in p_nombre:
                        df_temp.at[idx, col_val] = dia_matinal.strftime("%d/%m/%Y")
                    elif "venta" in p_nombre:
                        df_temp.at[idx, col_val] = dia_venta.strftime("%d/%m/%Y")
                    elif "anterior" in p_nombre:
                        df_temp.at[idx, col_val] = dia_anterior.strftime("%d/%m/%Y")

        st.session_state["df_parametros"] = df_temp

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

    col_btn1, col_btn2 = st.columns([1, 1])

    with col_btn1:
        if st.button("💾 Aplicar cambios de fechas y recalcular", key="btn_aplicar_cambios_fechas_modulo", type="primary"):
            st.session_state["df_parametros"] = df_editado
            st.success("¡Parámetros actualizados con éxito! Recargando cálculos...")
            st.rerun()

    with col_btn2:
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