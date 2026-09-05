# modules/parametros.py
import streamlit as st
import pandas as pd
from modules import database as db
from io import BytesIO

def es_entorno_local() -> bool:
    """Valida si la app se ejecuta en entorno local basándose en los secretos."""
    try:
        return st.secrets.get("ENVIRONMENT", "production") == "local"
    except Exception:
        return False

def obtener_tabla_parametros() -> pd.DataFrame:
    """Obtiene los parámetros desde SQLite. Si la tabla no existe, crea valores por defecto."""
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name='parametros'"
    res = db.cargar_tabla_sql(query)
    
    if res is None or res.empty:
        df_default = pd.DataFrame({
            "PARAMETRO": ["Año", "Mes", "Dia Matinal", "Dia Venta", "Dia Anterior"],
            "VALOR": ["2026", "9", "02/09/2026", "01/09/2026", "31/08/2026"]
        })
        db.guardar_dataframe_sql(df_default, "parametros", if_exists='replace')
        return df_default
    
    return db.cargar_tabla_sql("SELECT * FROM parametros")

def obtener_maestro_vendedores_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga el maestro de vendedores desde SQLite. Si mes está vacío, devuelve la base completa."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        if df_all is None or df_all.empty:
            return pd.DataFrame(columns=["Anio", "Mes", "Codigo_Vendedor", "Nombre_Vendedor", "Supervisor"])
        
        if not mes or str(mes).strip() == "":
            return df_all
        
        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = (df_all["Mes"].astype(str) == str(mes))
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]
            
        return df_all
    except Exception:
        return pd.DataFrame(columns=["Anio", "Mes", "Codigo_Vendedor", "Nombre_Vendedor", "Supervisor"])

def obtener_maestro_segmentos_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga el maestro de segmentos desde SQLite. Si mes está vacío, devuelve la base completa."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos")
        if df_all is None or df_all.empty:
            return pd.DataFrame(columns=["Anio", "Mes", "Segmento"])
        
        if not mes or str(mes).strip() == "":
            return df_all
        
        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = (df_all["Mes"].astype(str) == str(mes))
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]
            
        return df_all
    except Exception:
        return pd.DataFrame(columns=["Anio", "Mes", "Segmento"])

def obtener_maestro_marcas_cebe_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga la relación Marca - CEBE desde SQLite. Si mes está vacío, devuelve la base completa."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if df_all is None or df_all.empty:
            return pd.DataFrame(columns=["Anio", "Mes", "Marca", "CEBE"])
        
        if not mes or str(mes).strip() == "":
            return df_all
        
        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = (df_all["Mes"].astype(str) == str(mes))
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]
            
        return df_all
    except Exception:
        return pd.DataFrame(columns=["Anio", "Mes", "Marca", "CEBE"])

def render_parametros_view(filtros_globales: dict = None):
    if not es_entorno_local():
        st.warning("⚠️ Esta sección de configuración y parámetros está restringida al entorno de desarrollo local.")
        return

    st.subheader("⚙️ Configuración de Dimensiones y Maestros")
    st.markdown("Los filtros operativos de Año, Mes, Fechas y Supervisor se gestionan desde la barra lateral izquierda. Esta sección permite cargar y mantener los maestros de Vendedores, Segmentos y Marcas / CEBE.")

    anio_def = filtros_globales.get("anio", "2026") if filtros_globales else "2026"
    mes_def = filtros_globales.get("mes", "9") if filtros_globales else "9"

    # =========================================================================
    # 1. SECCIÓN: MAESTRO DE VENDEDORES
    # =========================================================================
    st.markdown("### 👥 1. Maestro de Vendedores y Asignación por Período")
    st.markdown("Cargue el archivo Excel con el padrón de vendedores para asignarlo al período operativo correspondiente.")

    col1, col2 = st.columns(2)
    with col1:
        sel_anio_v = st.text_input("Año Operativo (Vendedores)", value=anio_def, key="anio_vendedor")
    with col2:
        sel_mes_v = st.text_input("Mes Operativo (Vendedores)", value=mes_def, placeholder="Dejar vacío para ver toda la base", key="mes_vendedor")

    archivo_vendedores = st.file_uploader("📂 Subir Excel de Vendedores", type=["xlsx", "xls"], key="up_excel_vendedores")

    if archivo_vendedores is not None:
        try:
            df_nuevo_master = pd.read_excel(archivo_vendedores)
            columnas_originales = list(df_nuevo_master.columns)
            
            if len(columnas_originales) >= 3:
                nuevos_nombres = {}
                for col in columnas_originales:
                    col_str = str(col).lower()
                    if "codigo" in col_str or "cod" in col_str:
                        nuevos_nombres[col] = "Codigo_Vendedor"
                    elif "nombre" in col_str or "vendedor" in col_str or "razon" in col_str:
                        nuevos_nombres[col] = "Nombre_Vendedor"
                    elif "super" in col_str or "sup" in col_str:
                        nuevos_nombres[col] = "Supervisor"
                
                df_nuevo_master = df_nuevo_master.rename(columns=nuevos_nombres)
                
                if "Codigo_Vendedor" not in df_nuevo_master.columns and len(columnas_originales) > 0:
                    df_nuevo_master = df_nuevo_master.rename(columns={columnas_originales[0]: "Codigo_Vendedor"})
                if "Nombre_Vendedor" not in df_nuevo_master.columns and len(columnas_originales) > 1:
                    df_nuevo_master = df_nuevo_master.rename(columns={columnas_originales[1]: "Nombre_Vendedor"})
                if "Supervisor" not in df_nuevo_master.columns and len(columnas_originales) > 2:
                    df_nuevo_master = df_nuevo_master.rename(columns={columnas_originales[2]: "Supervisor"})

            st.write("Vista previa del archivo cargado:", df_nuevo_master.head())
            
            if st.button("📥 Registrar y Guardar Vendedores en Base de Datos"):
                if not sel_mes_v or str(sel_mes_v).strip() == "":
                    st.error("⚠️ Debe especificar un Mes Operativo válido para registrar el maestro.")
                else:
                    df_nuevo_master["Anio"] = str(sel_anio_v)
                    df_nuevo_master["Mes"] = str(sel_mes_v)
                    
                    query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_vendedores'"
                    res_check = db.cargar_tabla_sql(query_check)
                    
                    if res_check is not None and not res_check.empty:
                        df_existente = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
                        df_existente = df_existente[~((df_existente["Anio"].astype(str) == str(sel_anio_v)) & (df_existente["Mes"].astype(str) == str(sel_mes_v)))]
                        df_final_master = pd.concat([df_existente, df_nuevo_master], ignore_index=True)
                    else:
                        df_final_master = df_nuevo_master

                    db.guardar_dataframe_sql(df_final_master, "maestro_vendedores", if_exists='replace')
                    st.success(f"¡Maestro de vendedores guardado exitosamente para el período {sel_mes_v}/{sel_anio_v}!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel de vendedores: {e}")

    titulo_tabla_v = f"📋 Vendedores registrados en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_v or str(sel_mes_v).strip() == '' else f'Período {sel_mes_v}/{sel_anio_v}'})"
    st.markdown(f"#### {titulo_tabla_v}")
    
    df_maestro_actual = obtener_maestro_vendedores_sql(sel_anio_v, sel_mes_v)
    st.dataframe(df_maestro_actual, width="stretch")

    st.divider()

    # =========================================================================
    # 2. SECCIÓN: MAESTRO DE SEGMENTOS
    # =========================================================================
    st.markdown("### 🏷️ 2. Maestro de Objetivos por Segmento")
    st.markdown("Cargue la planilla Excel con la lista de Segmentos a medir para el período operativo.")

    col3, col4 = st.columns(2)
    with col3:
        sel_anio_s = st.text_input("Año Operativo (Segmentos)", value=anio_def, key="anio_segmento")
    with col4:
        sel_mes_s = st.text_input("Mes Operativo (Segmentos)", value=mes_def, placeholder="Dejar vacío para ver toda la base", key="mes_segmento")

    archivo_segmentos = st.file_uploader("📂 Subir Excel de Segmentos", type=["xlsx", "xls"], key="up_excel_segmentos")

    if archivo_segmentos is not None:
        try:
            df_nuevo_seg = pd.read_excel(archivo_segmentos)
            columnas_seg = list(df_nuevo_seg.columns)
            
            col_encontrada = None
            for c in columnas_seg:
                if "segmento" in str(c).strip().lower():
                    col_encontrada = c
                    break
            
            if col_encontrada:
                df_nuevo_seg = df_nuevo_seg.rename(columns={col_encontrada: "Segmento"})
            elif len(columnas_seg) > 0:
                df_nuevo_seg = df_nuevo_seg.rename(columns={columnas_seg[0]: "Segmento"})
            
            df_nuevo_seg = df_nuevo_seg.dropna(subset=["Segmento"])
            df_nuevo_seg["Segmento"] = df_nuevo_seg["Segmento"].astype(str).str.strip()

            st.write("Vista previa de Segmentos mapeados:", df_nuevo_seg.head())

            if st.button("📥 Registrar y Guardar Segmentos en Base de Datos"):
                if not sel_mes_s or str(sel_mes_s).strip() == "":
                    st.error("⚠️ Debe especificar un Mes Operativo válido para registrar los segmentos.")
                else:
                    df_nuevo_seg["Anio"] = str(sel_anio_s)
                    df_nuevo_seg["Mes"] = str(sel_mes_s)

                    query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_segmentos'"
                    res_check = db.cargar_tabla_sql(query_check)

                    if res_check is not None and not res_check.empty:
                        df_existente_seg = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos")
                        df_existente_seg = df_existente_seg[~((df_existente_seg["Anio"].astype(str) == str(sel_anio_s)) & (df_existente_seg["Mes"].astype(str) == str(sel_mes_s)))]
                        df_final_seg = pd.concat([df_existente_seg, df_nuevo_seg], ignore_index=True)
                    else:
                        df_final_seg = df_nuevo_seg

                    db.guardar_dataframe_sql(df_final_seg, "maestro_segmentos", if_exists='replace')
                    st.success(f"¡Maestro de segmentos guardado exitosamente para el período {sel_mes_s}/{sel_anio_s}!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel de segmentos: {e}")

    titulo_tabla_s = f"📋 Segmentos registrados en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_s or str(sel_mes_s).strip() == '' else f'Período {sel_mes_s}/{sel_anio_s}'})"
    st.markdown(f"#### {titulo_tabla_s}")

    df_segmentos_actual = obtener_maestro_segmentos_sql(sel_anio_s, sel_mes_s)
    st.dataframe(df_segmentos_actual, width="stretch")

    st.divider()

    # =========================================================================
    # 3. SECCIÓN: MAESTRO MARCA - CEBE
    # =========================================================================
    st.markdown("### 🏷️ 3. Maestro de Marcas y CEBE")
    st.markdown("Cargue la planilla Excel con la relación entre Marca y CEBE (Global, Pehuamar, Cracker, Cereal, etc.) para el período operativo.")

    col5, col6 = st.columns(2)
    with col5:
        sel_anio_m = st.text_input("Año Operativo (Marcas/CEBE)", value=anio_def, key="anio_marca_cebe")
    with col6:
        sel_mes_m = st.text_input("Mes Operativo (Marcas/CEBE)", value=mes_def, placeholder="Dejar vacío para ver toda la base", key="mes_marca_cebe")

    archivo_marcas = st.file_uploader("📂 Subir Excel de Marcas y CEBE (Columnas esperadas: Marca, CEBE)", type=["xlsx", "xls"], key="up_excel_marcas_cebe")

    if archivo_marcas is not None:
        try:
            df_nuevo_cebe = pd.read_excel(archivo_marcas)
            columnas_cebe = list(df_nuevo_cebe.columns)

            nuevos_nombres_cebe = {}
            for col in columnas_cebe:
                col_str = str(col).strip().lower()
                if "marca" in col_str:
                    nuevos_nombres_cebe[col] = "Marca"
                elif "cebe" in col_str or "tipo" in col_str or "categoria" in col_str:
                    nuevos_nombres_cebe[col] = "CEBE"

            df_nuevo_cebe = df_nuevo_cebe.rename(columns=nuevos_nombres_cebe)

            if "Marca" not in df_nuevo_cebe.columns and len(columnas_cebe) > 0:
                df_nuevo_cebe = df_nuevo_cebe.rename(columns={columnas_cebe[0]: "Marca"})
            if "CEBE" not in df_nuevo_cebe.columns and len(columnas_cebe) > 1:
                df_nuevo_cebe = df_nuevo_cebe.rename(columns={columnas_cebe[1]: "CEBE"})

            df_nuevo_cebe = df_nuevo_cebe.dropna(subset=["Marca", "CEBE"])
            df_nuevo_cebe["Marca"] = df_nuevo_cebe["Marca"].astype(str).str.strip()
            df_nuevo_cebe["CEBE"] = df_nuevo_cebe["CEBE"].astype(str).str.strip()

            st.write("Vista previa de Marcas y CEBE mapeados:", df_nuevo_cebe.head())

            if st.button("📥 Registrar y Guardar Marcas/CEBE en Base de Datos"):
                if not sel_mes_m or str(sel_mes_m).strip() == "":
                    st.error("⚠️ Debe especificar un Mes Operativo válido para registrar las marcas y CEBE.")
                else:
                    df_nuevo_cebe["Anio"] = str(sel_anio_m)
                    df_nuevo_cebe["Mes"] = str(sel_mes_m)

                    query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_marcas_cebe'"
                    res_check = db.cargar_tabla_sql(query_check)

                    if res_check is not None and not res_check.empty:
                        df_existente_cebe = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
                        df_existente_cebe = df_existente_cebe[~((df_existente_cebe["Anio"].astype(str) == str(sel_anio_m)) & (df_existente_cebe["Mes"].astype(str) == str(sel_mes_m)))]
                        df_final_cebe = pd.concat([df_existente_cebe, df_nuevo_cebe], ignore_index=True)
                    else:
                        df_final_cebe = df_nuevo_cebe

                    db.guardar_dataframe_sql(df_final_cebe, "maestro_marcas_cebe", if_exists='replace')
                    st.success(f"¡Maestro Marca/CEBE guardado exitosamente para el período {sel_mes_m}/{sel_anio_m}!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel de Marcas/CEBE: {e}")

    titulo_tabla_m = f"📋 Marcas y CEBE registrados en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_m or str(sel_mes_m).strip() == '' else f'Período {sel_mes_m}/{sel_anio_m}'})"
    st.markdown(f"#### {titulo_tabla_m}")

    df_marcas_cebe_actual = obtener_maestro_marcas_cebe_sql(sel_anio_m, sel_mes_m)
    st.dataframe(df_marcas_cebe_actual, width="stretch")

    # =========================================================================
    # BOTÓN DE DESCARGA GLOBAL A EXCEL
    # =========================================================================
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_maestro_actual.to_excel(writer, index=False, sheet_name='Maestro_Vendedores')
        df_segmentos_actual.to_excel(writer, index=False, sheet_name='Maestro_Segmentos')
        df_marcas_cebe_actual.to_excel(writer, index=False, sheet_name='Maestro_Marcas_CEBE')
    
    st.download_button(
        label="📥 Descargar Maestros Completos a Excel",
        data=output.getvalue(),
        file_name="maestros_matinal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )