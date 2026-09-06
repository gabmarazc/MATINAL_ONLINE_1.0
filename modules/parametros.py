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
    """Carga la relación Marca - CEBE y objetivos desde SQLite. Si mes está vacío, devuelve la base completa."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_marcas_cebe")
        if df_all is None or df_all.empty:
            return pd.DataFrame(columns=["Anio", "Mes", "Marca", "CEBE", "Obj_TN_Mes", "Obj_Gross_Mes"])
        
        for col_nec in ["Obj_TN_Mes", "Obj_Gross_Mes"]:
            if col_nec not in df_all.columns:
                df_all[col_nec] = 0.0

        if not mes or str(mes).strip() == "":
            return df_all
        
        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = (df_all["Mes"].astype(str) == str(mes))
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]
            
        return df_all
    except Exception:
        return pd.DataFrame(columns=["Anio", "Mes", "Marca", "CEBE", "Obj_TN_Mes", "Obj_Gross_Mes"])

def obtener_objetivos_vendedores_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga los objetivos calibrados desde SQLite. Si mes está vacío, devuelve la base completa."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM objetivos_vendedores")
        if df_all is None or df_all.empty:
            return pd.DataFrame(columns=["Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "Marca", "CEBE", "SEGMENTO", "Obj_Sugerido_Kg"])
        
        if not mes or str(mes).strip() == "":
            return df_all
        
        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = (df_all["Mes"].astype(str) == str(mes))
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]
            
        return df_all
    except Exception:
        return pd.DataFrame(columns=["Anio", "Mes", "CodVendedor", "Nombre", "Supervisor", "Marca", "CEBE", "SEGMENTO", "Obj_Sugerido_Kg"])

def render_parametros_view(filtros_globales: dict = None):
    if not es_entorno_local():
        st.warning("⚠️ Esta sección de configuración y parámetros está restringida al entorno de desarrollo local.")
        return

    st.subheader("⚙️ Configuración de Dimensiones y Maestros")
    st.markdown("Los filtros operativos de Año, Mes, Fechas y Supervisor se gestionan desde la barra lateral izquierda. Esta sección permite cargar y mantener los maestros de Vendedores, Segmentos, Marcas / CEBE e importar los objetivos calibrados.")

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
    # 3. SECCIÓN: MAESTRO MARCA - CEBE Y OBJETIVOS (Obj_TN_Mes, Obj_Gross_Mes)
    # =========================================================================
    st.markdown("### 🏷️ 3. Maestro de Marcas, CEBE y Objetivos (Obj_TN_Mes / Obj_Gross_Mes)")
    st.markdown("Descargue la plantilla, complete los objetivos mensuales en toneladas (`Obj_TN_Mes`) y en gross (`Obj_Gross_Mes`), y suba el archivo actualizado.")

    col5, col6 = st.columns(2)
    with col5:
        sel_anio_m = st.text_input("Año Operativo (Marcas/CEBE)", value=anio_def, key="anio_marca_cebe")
    with col6:
        sel_mes_m = st.text_input("Mes Operativo (Marcas/CEBE)", value=mes_def, placeholder="Dejar vacío para ver toda la base", key="mes_marca_cebe")

    df_marcas_cebe_actual = obtener_maestro_marcas_cebe_sql(sel_anio_m, sel_mes_m)

    output_plantilla = BytesIO()
    with pd.ExcelWriter(output_plantilla, engine='openpyxl') as writer:
        df_plantilla = df_marcas_cebe_actual.copy()
        if df_plantilla.empty:
            df_plantilla = pd.DataFrame(columns=["Anio", "Mes", "Marca", "CEBE", "Obj_TN_Mes", "Obj_Gross_Mes"])
        df_plantilla.to_excel(writer, index=False, sheet_name='Maestro_Marcas_CEBE')

    st.download_button(
        label="📥 Descargar Plantilla de Marcas y CEBE para Completar",
        data=output_plantilla.getvalue(),
        file_name=f"plantilla_marcas_cebe_{sel_mes_m}_{sel_anio_m}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    archivo_marcas = st.file_uploader("📂 Subir Excel Actualizado de Marcas, CEBE y Objetivos", type=["xlsx", "xls"], key="up_excel_marcas_cebe")

    if archivo_marcas is not None:
        try:
            df_nuevo_cebe = pd.read_excel(archivo_marcas)
            columnas_cebe = list(df_nuevo_cebe.columns)

            nuevos_nombres_cebe = {}
            for col in columnas_cebe:
                col_str = str(col).strip().lower()
                if "marca" in col_str or "marcaupper" in col_str:
                    nuevos_nombres_cebe[col] = "Marca"
                elif "cebe" in col_str or "tipo" in col_str or "categoria" in col_str or "cebe 2" in col_str:
                    nuevos_nombres_cebe[col] = "CEBE"
                elif "obj_tn" in col_str or "tn" in col_str:
                    nuevos_nombres_cebe[col] = "Obj_TN_Mes"
                elif "obj_gross" in col_str or "gross" in col_str:
                    nuevos_nombres_cebe[col] = "Obj_Gross_Mes"

            df_nuevo_cebe = df_nuevo_cebe.rename(columns=nuevos_nombres_cebe)

            for col_req in ["Marca", "CEBE", "Obj_TN_Mes", "Obj_Gross_Mes"]:
                if col_req not in df_nuevo_cebe.columns:
                    if col_req in ["Obj_TN_Mes", "Obj_Gross_Mes"]:
                        df_nuevo_cebe[col_req] = 0.0
                    else:
                        df_nuevo_cebe[col_req] = ""

            df_nuevo_cebe["Obj_TN_Mes"] = pd.to_numeric(df_nuevo_cebe["Obj_TN_Mes"], errors="coerce").fillna(0.0)
            df_nuevo_cebe["Obj_Gross_Mes"] = pd.to_numeric(df_nuevo_cebe["Obj_Gross_Mes"], errors="coerce").fillna(0.0)

            cols_requeridas = ["Marca", "CEBE", "Obj_TN_Mes", "Obj_Gross_Mes"]
            df_nuevo_cebe = df_nuevo_cebe[cols_requeridas].copy()
            df_nuevo_cebe = df_nuevo_cebe.dropna(subset=["Marca", "CEBE"])
            df_nuevo_cebe["Marca"] = df_nuevo_cebe["Marca"].astype(str).str.strip()
            df_nuevo_cebe["CEBE"] = df_nuevo_cebe["CEBE"].astype(str).str.strip()

            st.write("Vista previa de Marcas, CEBE y Objetivos mapeados:", df_nuevo_cebe.head())

            if st.button("📥 Registrar y Guardar Marcas/CEBE y Objetivos en Base de Datos"):
                if not sel_mes_m or str(sel_mes_m).strip() == "":
                    st.error("⚠️ Debe especificar un Mes Operativo válido para registrar las marcas, CEBE y objetivos.")
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
                    st.success(f"¡Maestro Marca/CEBE y Objetivos guardado exitosamente para el período {sel_mes_m}/{sel_anio_m}!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel de Marcas/CEBE: {e}")

    titulo_tabla_m = f"📋 Marcas, CEBE y Objetivos registrados en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_m or str(sel_mes_m).strip() == '' else f'Período {sel_mes_m}/{sel_anio_m}'})"
    st.markdown(f"#### {titulo_tabla_m}")

    df_marcas_cebe_actual = obtener_maestro_marcas_cebe_sql(sel_anio_m, sel_mes_m)
    st.dataframe(df_marcas_cebe_actual, width="stretch")

    st.divider()

    # =========================================================================
    # 4. SECCIÓN: IMPORTACIÓN DE OBJETIVOS CALIBRADOS (DEFINITIVOS)
    # =========================================================================
    st.markdown("### 📥 4. Importación de Objetivos Calibrados (Definitivos)")
    st.markdown("Cargue aquí el archivo Excel exportado y ajustado desde el generador de objetivos para consolidar los objetivos oficiales del período operativo en la base de datos.")

    col7, col8 = st.columns(2)
    with col7:
        sel_anio_obj = st.text_input("Año Operativo (Objetivos Calibrados)", value=anio_def, key="anio_objetivos_calib")
    with col8:
        sel_mes_obj = st.text_input("Mes Operativo (Objetivos Calibrados)", value=mes_def, key="mes_objetivos_calib")

    archivo_objetivos_subido = st.file_uploader(
        "📂 Subir Excel de Objetivos Calibrados (.xlsx)",
        type=["xlsx", "xls"],
        key="up_excel_objetivos_calibrados"
    )

    if archivo_objetivos_subido is not None:
        try:
            st.write("Vista previa del Excel calibrado:", pd.read_excel(archivo_objetivos_subido).head())
            
            if st.button("🚀 Procesar e Ingresar Objetivos Calibrados a la Base de Datos"):
                if not sel_mes_obj or str(sel_mes_obj).strip() == "":
                    st.error("⚠️ Debe especificar un Mes Operativo válido para versionar los objetivos.")
                else:
                    with st.spinner("Guardando y versionando objetivos en SQLite..."):
                        exito, mensaje = db.guardar_objetivos_calibrados_desde_excel(archivo_objetivos_subido, sel_anio_obj, sel_mes_obj)
                        if exito:
                            st.success(mensaje)
                            st.rerun()
                        else:
                            st.error(mensaje)
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel calibrado: {e}")

    titulo_tabla_obj = f"📋 Objetivos Calibrados registrados en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_obj or str(sel_mes_obj).strip() == '' else f'Período {sel_mes_obj}/{sel_anio_obj}'})"
    st.markdown(f"#### {titulo_tabla_obj}")

    df_objetivos_actual = obtener_objetivos_vendedores_sql(sel_anio_obj, sel_mes_obj)
    st.dataframe(df_objetivos_actual, width="stretch")

    st.divider()

    # =========================================================================
    # BOTÓN DE DESCARGA GLOBAL A EXCEL
    # =========================================================================
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_maestro_actual.to_excel(writer, index=False, sheet_name='Maestro_Vendedores')
        df_segmentos_actual.to_excel(writer, index=False, sheet_name='Maestro_Segmentos')
        df_marcas_cebe_actual.to_excel(writer, index=False, sheet_name='Maestro_Marcas_CEBE')
        df_objetivos_actual.to_excel(writer, index=False, sheet_name='Objetivos_Calibrados')
    
    st.download_button(
        label="📥 Descargar Maestros y Objetivos Completos a Excel",
        data=output.getvalue(),
        file_name="maestros_y_objetivos_matinal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )