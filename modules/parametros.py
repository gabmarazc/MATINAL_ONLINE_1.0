from io import BytesIO
import pandas as pd
import streamlit as st


def render_parametros():
  st.subheader("Gestión de Parámetros Globales (Fechas)")

  # Inicializar el DataFrame de parámetros en el session_state si no existe
  if "df_parametros" not in st.session_state:
    st.session_state["df_parametros"] = pd.DataFrame({
        "PARAMETRO": [
            "Año",
            "Mes",
            "Dia Matinal",
            "Dia Venta",
            "Dia Anterior",
        ],
        "VALOR": ["2026", "9", "02/09/2026", "01/09/2026", "31/08/2026"],
    })

  st.info(
      "Modifica los valores de la tabla inferior para actualizar los"
      " parámetros de fecha en todo el sistema de forma dinámica en memoria."
  )

  # Editor interactivo de datos
  edited_df = st.data_editor(
      st.session_state["df_parametros"],
      num_rows="fixed",
      width="stretch",
      key="editor_parametros_fechas",
  )

  # Actualizar el estado global con los cambios realizados por el usuario en tiempo real
  st.session_state["df_parametros"] = edited_df

  # Botón con key única para evitar bloqueos visuales o estados grisados
  if st.button("💾 Aplicar cambios de fechas y recalcular", key="btn_aplicar_cambios_fechas_modulo"):
    st.success(
        "¡Parámetros actualizados correctamente para el resto de los"
        " reportes!"
    )
    st.rerun()

  # Generación del archivo Excel en memoria usando openpyxl
  buffer = BytesIO()
  with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    edited_df.to_excel(writer, index=False, sheet_name="FECHAS")
  buffer.seek(0)

  # Botón funcional de descarga a Excel obligatorio al final de la vista
  st.download_button(
      label="📥 Descargar Parámetros a Excel",
      data=buffer,
      file_name="parametros_fechas_sistema.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      key="btn_descargar_parametros_excel"
  )