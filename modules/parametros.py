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
        df_default = pd.DataFrame(
            {
                "PARAMETRO": ["Año", "Mes", "Dia Matinal", "Dia Venta", "Dia Anterior"],
                "VALOR": ["2026", "9", "02/09/2026", "01/09/2026", "31/08/2026"],
            }
        )
        db.guardar_dataframe_sql(df_default, "parametros", if_exists="replace")
        return df_default

    return db.cargar_tabla_sql("SELECT * FROM parametros")


def obtener_maestro_vendedores_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga el maestro de vendedores desde SQLite asegurando la columna Rutas_Ajustadas."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_vendedores")
        if df_all is None or df_all.empty:
            return pd.DataFrame(
                columns=[
                    "Anio",
                    "Mes",
                    "Codigo_Vendedor",
                    "Nombre_Vendedor",
                    "Supervisor",
                    "Rutas_Ajustadas",
                ]
            )

        if "Rutas_Ajustadas" not in df_all.columns:
            df_all["Rutas_Ajustadas"] = 0

        if not mes or str(mes).strip() == "":
            return df_all

        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = df_all["Mes"].astype(str) == str(mes)
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]

        return df_all
    except Exception:
        return pd.DataFrame(
            columns=[
                "Anio",
                "Mes",
                "Codigo_Vendedor",
                "Nombre_Vendedor",
                "Supervisor",
                "Rutas_Ajustadas",
            ]
        )


def obtener_maestro_segmentos_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga el maestro de segmentos desde SQLite. Si mes está vacío, devuelve la base completa."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_segmentos")
        if df_all is None or df_all.empty:
            return pd.DataFrame(columns=["Anio", "Mes", "Segmento"])

        if not mes or str(mes).strip() == "":
            return df_all

        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = df_all["Mes"].astype(str) == str(mes)
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
            return pd.DataFrame(
                columns=[
                    "Anio",
                    "Mes",
                    "Marca",
                    "CEBE",
                    "Obj_TN_Mes",
                    "Obj_Gross_Mes",
                    "Obj_Pepsico_Cobertura",
                    "Obj_Empresa_Cobertura",
                ]
            )

        for col_nec in [
            "Obj_TN_Mes",
            "Obj_Gross_Mes",
            "Obj_Pepsico_Cobertura",
            "Obj_Empresa_Cobertura",
        ]:
            if col_nec not in df_all.columns:
                df_all[col_nec] = 0.0

        if not mes or str(mes).strip() == "":
            return df_all

        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = df_all["Mes"].astype(str) == str(mes)
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]

        return df_all
    except Exception:
        return pd.DataFrame(
            columns=[
                "Anio",
                "Mes",
                "Marca",
                "CEBE",
                "Obj_TN_Mes",
                "Obj_Gross_Mes",
                "Obj_Pepsico_Cobertura",
                "Obj_Empresa_Cobertura",
            ]
        )


def obtener_maestro_ccc_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga los porcentajes y objetivos de clientes CCC por taxonomía desde SQLite aplicando versionado estricto."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
        if df_all is None or df_all.empty:
            df_default = pd.DataFrame(
                {
                    "Anio": [int(anio) if anio else 2026] * 4,
                    "Mes": [int(mes) if mes else 9] * 4,
                    "Taxonomia": ["A", "B", "C", "D"],
                    "Porcentaje_Cartera": [80.0, 70.0, 60.0, 50.0],
                    "Obj_CCC_Pepsico": [0.0, 0.0, 0.0, 0.0],
                }
            )
            db.guardar_dataframe_sql(df_default, "maestro_ccc", if_exists="append")
            return df_default

        if "Obj_CCC_Pepsico" not in df_all.columns:
            df_all["Obj_CCC_Pepsico"] = 0.0

        if not mes or str(mes).strip() == "":
            return df_all

        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = df_all["Mes"].astype(str) == str(mes)
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            res = df_all[cond]
            if res.empty:
                return pd.DataFrame(
                    {
                        "Anio": [int(anio) if anio else 2026] * 4,
                        "Mes": [int(mes)] * 4,
                        "Taxonomia": ["A", "B", "C", "D"],
                        "Porcentaje_Cartera": [80.0, 70.0, 60.0, 50.0],
                        "Obj_CCC_Pepsico": [0.0, 0.0, 0.0, 0.0],
                    }
                )
            return res

        return df_all
    except Exception:
        return pd.DataFrame(
            {
                "Anio": [2026] * 4,
                "Mes": [9] * 4,
                "Taxonomia": ["A", "B", "C", "D"],
                "Porcentaje_Cartera": [80.0, 70.0, 60.0, 50.0],
                "Obj_CCC_Pepsico": [0.0, 0.0, 0.0, 0.0],
            }
        )


def obtener_maestro_tp_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga el objetivo absoluto TP PepsiCo por taxonomía y período."""
    columnas = ["Anio", "Mes", "Taxonomia", "Obj_TP_Pepsico"]
    try:
        db.asegurar_tabla_maestro_tp()
        df_all = db.cargar_tabla_sql(
            "SELECT Anio, Mes, Taxonomia, Obj_TP_Pepsico "
            "FROM maestro_tp ORDER BY Anio, Mes, Taxonomia"
        )
        if df_all is None or df_all.empty:
            if anio and mes and str(mes).strip() != "":
                return pd.DataFrame(
                    {
                        "Anio": [int(float(anio))] * 4,
                        "Mes": [int(float(mes))] * 4,
                        "Taxonomia": ["A", "B", "C", "D"],
                        "Obj_TP_Pepsico": [0, 0, 0, 0],
                    }
                )
            return pd.DataFrame(columns=columnas)
        df_all["Anio"] = pd.to_numeric(df_all["Anio"], errors="coerce").astype("Int64")
        df_all["Mes"] = pd.to_numeric(df_all["Mes"], errors="coerce").astype("Int64")
        df_all["Taxonomia"] = (
            df_all["Taxonomia"].astype("string").str.strip().str.upper()
        )
        df_all["Obj_TP_Pepsico"] = (
            pd.to_numeric(df_all["Obj_TP_Pepsico"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
        if not mes or str(mes).strip() == "":
            return df_all[columnas].copy()
        condicion = df_all["Mes"].astype(str) == str(int(float(mes)))
        if anio and str(anio).strip() != "":
            condicion = condicion & (
                df_all["Anio"].astype(str) == str(int(float(anio)))
            )
        resultado = df_all.loc[condicion, columnas].copy()
        if resultado.empty:
            return pd.DataFrame(
                {
                    "Anio": [int(float(anio))] * 4,
                    "Mes": [int(float(mes))] * 4,
                    "Taxonomia": ["A", "B", "C", "D"],
                    "Obj_TP_Pepsico": [0, 0, 0, 0],
                }
            )
        return resultado.sort_values("Taxonomia").reset_index(drop=True)
    except Exception:
        if anio and mes and str(mes).strip() != "":
            return pd.DataFrame(
                {
                    "Anio": [int(float(anio))] * 4,
                    "Mes": [int(float(mes))] * 4,
                    "Taxonomia": ["A", "B", "C", "D"],
                    "Obj_TP_Pepsico": [0, 0, 0, 0],
                }
            )
        return pd.DataFrame(columns=columnas)


def obtener_objetivos_vendedores_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga los objetivos calibrados desde SQLite. Si mes está vacío, devuelve la base completa."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM objetivos_vendedores")
        if df_all is None or df_all.empty:
            return pd.DataFrame(
                columns=[
                    "Anio",
                    "Mes",
                    "CodVendedor",
                    "Nombre",
                    "Supervisor",
                    "SEGMENTO",
                    "Kilos_Mes_Anterior",
                    "Objetivo_Mes_Anterior_Kg",
                    "Logro_Anterior_Pct",
                    "Obj_Sugerido_Kg",
                ]
            )

        if not mes or str(mes).strip() == "":
            return df_all

        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = df_all["Mes"].astype(str) == str(mes)
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]

        return df_all
    except Exception:
        return pd.DataFrame(
            columns=[
                "Anio",
                "Mes",
                "CodVendedor",
                "Nombre",
                "Supervisor",
                "SEGMENTO",
                "Kilos_Mes_Anterior",
                "Objetivo_Mes_Anterior_Kg",
                "Logro_Anterior_Pct",
                "Obj_Sugerido_Kg",
            ]
        )


def obtener_maestro_innovaciones_sql(anio: str = None, mes: str = None) -> pd.DataFrame:
    """Carga el maestro de innovaciones desde SQLite. Si mes está vacío, devuelve la base completa."""
    try:
        df_all = db.cargar_tabla_sql("SELECT * FROM maestro_innovaciones")
        if df_all is None or df_all.empty:
            return pd.DataFrame(
                columns=[
                    "Anio",
                    "Mes",
                    "Codigo",
                    "Articulo",
                    "Innovacion",
                    "Condicion_Vta",
                ]
            )

        if not mes or str(mes).strip() == "":
            return df_all

        if "Anio" in df_all.columns and "Mes" in df_all.columns:
            cond = df_all["Mes"].astype(str) == str(mes)
            if anio and str(anio).strip() != "":
                cond = cond & (df_all["Anio"].astype(str) == str(anio))
            return df_all[cond]

        return df_all
    except Exception:
        return pd.DataFrame(
            columns=["Anio", "Mes", "Codigo", "Articulo", "Innovacion", "Condicion_Vta"]
        )


def render_parametros_view(filtros_globales: dict = None):
    if not es_entorno_local():
        st.warning(
            "⚠️ Esta sección de configuración y parámetros está restringida al entorno de desarrollo local."
        )
        return

    st.subheader("⚙️ Configuración de Dimensiones y Maestros")
    st.markdown(
        "Los filtros operativos de Año, Mes, Fechas y Supervisor se gestionan desde la barra lateral izquierda. Esta sección permite cargar y mantener los maestros de Vendedores, Segmentos, Marcas / CEBE, Porcentajes y Objetivos CCC, Innovaciones e importar los objetivos calibrados."
    )

    anio_def = filtros_globales.get("anio", "2026") if filtros_globales else "2026"
    mes_def = filtros_globales.get("mes", "9") if filtros_globales else "9"

    # =========================================================================
    # 0. IMPORTADOR GLOBAL MULTI-SOLAPA (SOLUCIÓN UNIFICADA)
    # =========================================================================
    st.markdown("### 📂 0. Importador Global Multi-solapa (Actualización Masiva)")
    st.markdown(
        "Sube aquí un único archivo Excel con múltiples solapas (exactamente con la estructura generada por el botón de descarga global) para poblar todas las bases de parámetros, maestros y objetivos de preventistas en un solo paso."
    )

    archivo_global_multisolapa = st.file_uploader(
        "📂 Subir Archivo Excel Multi-solapa Consolidado",
        type=["xlsx", "xls"],
        key="up_excel_global_multisolapa_principal",
    )

    if archivo_global_multisolapa is not None:
        try:
            xls_global = pd.ExcelFile(archivo_global_multisolapa)
            st.info(
                f"Solapas detectadas en el archivo: {', '.join(xls_global.sheet_names)}"
            )

            if st.button(
                "🚀 Procesar e Importar Masivamente Todas las Solapas",
                key="btn_ejecutar_importacion_global_multisolapa",
            ):
                conn = db.obtener_conexion()
                try:
                    sheet_to_table = {
                        "Maestro_Vendedores": "maestro_vendedores",
                        "Maestro_Segmentos": "maestro_segmentos",
                        "Maestro_Marcas_CEBE": "maestro_marcas_cebe",
                        "Maestro_CCC_Config": "maestro_ccc",
                        "Maestro_TP_Config": "maestro_tp",
                        "Maestro_Innovaciones": "maestro_innovaciones",
                        "Objetivos_Calibrados": "objetivos_vendedores",
                    }

                    importados_count = 0
                    for sheet_name, table_name in sheet_to_table.items():
                        if sheet_name in xls_global.sheet_names:
                            df_sheet = pd.read_excel(
                                archivo_global_multisolapa, sheet_name=sheet_name
                            )
                            if not df_sheet.empty:
                                if "Anio" in df_sheet.columns:
                                    df_sheet["Anio"] = (
                                        pd.to_numeric(df_sheet["Anio"], errors="coerce")
                                        .fillna(int(anio_def))
                                        .astype(int)
                                    )
                                if "Mes" in df_sheet.columns:
                                    df_sheet["Mes"] = (
                                        pd.to_numeric(df_sheet["Mes"], errors="coerce")
                                        .fillna(int(mes_def))
                                        .astype(int)
                                    )

                                df_sheet.to_sql(
                                    table_name,
                                    conn,
                                    if_exists="replace",
                                    index=False,
                                    chunksize=10000,
                                )
                                importados_count += 1

                    st.success(
                        f"¡Se han importado y actualizado exitosamente {importados_count} tablas en SQLite desde el archivo multi-solapa!"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al procesar la importación multi-solapa: {e}")
                finally:
                    conn.close()
        except Exception as e:
            st.error(f"Error al leer el archivo Excel: {e}")

    st.divider()

    # =========================================================================
    # 1. SECCIÓN: MAESTRO DE VENDEDORES
    # =========================================================================
    st.markdown("### 👥 1. Maestro de Vendedores y Asignación por Período")
    col1, col2 = st.columns(2)
    with col1:
        sel_anio_v = st.text_input(
            "Año Operativo (Vendedores)", value=anio_def, key="anio_vendedor"
        )
    with col2:
        sel_mes_v = st.text_input(
            "Mes Operativo (Vendedores)",
            value=mes_def,
            placeholder="Dejar vacío para ver toda la base",
            key="mes_vendedor",
        )

    archivo_vendedores = st.file_uploader(
        "📂 Subir Excel de Vendedores (Debe incluir 'Rutas_Ajustadas')",
        type=["xlsx", "xls"],
        key="up_excel_vendedores",
    )

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
                    elif (
                        "nombre" in col_str
                        or "vendedor" in col_str
                        or "razon" in col_str
                    ):
                        nuevos_nombres[col] = "Nombre_Vendedor"
                    elif "super" in col_str or "sup" in col_str:
                        nuevos_nombres[col] = "Supervisor"
                    elif (
                        "rutas_ajustadas" in col_str
                        or "rutasajustadas" in col_str
                        or "ajustadas" in col_str
                    ):
                        nuevos_nombres[col] = "Rutas_Ajustadas"

                df_nuevo_master = df_nuevo_master.rename(columns=nuevos_nombres)

                if (
                    "Codigo_Vendedor" not in df_nuevo_master.columns
                    and len(columnas_originales) > 0
                ):
                    df_nuevo_master = df_nuevo_master.rename(
                        columns={columnas_originales[0]: "Codigo_Vendedor"}
                    )
                if (
                    "Nombre_Vendedor" not in df_nuevo_master.columns
                    and len(columnas_originales) > 1
                ):
                    df_nuevo_master = df_nuevo_master.rename(
                        columns={columnas_originales[1]: "Nombre_Vendedor"}
                    )
                if (
                    "Supervisor" not in df_nuevo_master.columns
                    and len(columnas_originales) > 2
                ):
                    df_nuevo_master = df_nuevo_master.rename(
                        columns={columnas_originales[2]: "Supervisor"}
                    )
                if "Rutas_Ajustadas" not in df_nuevo_master.columns:
                    df_nuevo_master["Rutas_Ajustadas"] = 0

            st.write("Vista previa del archivo cargado:", df_nuevo_master.head())

            if st.button("📥 Registrar y Guardar Vendedores en Base de Datos"):
                if not sel_mes_v or str(sel_mes_v).strip() == "":
                    st.error(
                        "⚠️ Debe especificar un Mes Operativo válido para registrar el maestro."
                    )
                else:
                    df_nuevo_master["Anio"] = str(sel_anio_v)
                    df_nuevo_master["Mes"] = str(sel_mes_v)
                    df_nuevo_master["Rutas_Ajustadas"] = (
                        pd.to_numeric(
                            df_nuevo_master.get("Rutas_Ajustadas", 0), errors="coerce"
                        )
                        .fillna(0)
                        .astype(int)
                    )

                    query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_vendedores'"
                    res_check = db.cargar_tabla_sql(query_check)

                    if res_check is not None and not res_check.empty:
                        df_existente = db.cargar_tabla_sql(
                            "SELECT * FROM maestro_vendedores"
                        )
                        df_existente = df_existente[
                            ~(
                                (df_existente["Anio"].astype(str) == str(sel_anio_v))
                                & (df_existente["Mes"].astype(str) == str(sel_mes_v))
                            )
                        ]
                        df_final_master = pd.concat(
                            [df_existente, df_nuevo_master], ignore_index=True
                        )
                    else:
                        df_final_master = df_nuevo_master

                    db.guardar_dataframe_sql(
                        df_final_master, "maestro_vendedores", if_exists="replace"
                    )
                    st.success(
                        f"¡Maestro de vendedores guardado exitosamente con Rutas Ajustadas para el período {sel_mes_v}/{sel_anio_v}!"
                    )
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
    col3, col4 = st.columns(2)
    with col3:
        sel_anio_s = st.text_input(
            "Año Operativo (Segmentos)", value=anio_def, key="anio_segmento"
        )
    with col4:
        sel_mes_s = st.text_input(
            "Mes Operativo (Segmentos)",
            value=mes_def,
            placeholder="Dejar vacío para ver toda la base",
            key="mes_segmento",
        )

    archivo_segmentos = st.file_uploader(
        "📂 Subir Excel de Segmentos", type=["xlsx", "xls"], key="up_excel_segmentos"
    )

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
                df_nuevo_seg = df_nuevo_seg.rename(
                    columns={columnas_seg[0]: "Segmento"}
                )

            df_nuevo_seg = df_nuevo_seg.dropna(subset=["Segmento"])
            df_nuevo_seg["Segmento"] = df_nuevo_seg["Segmento"].astype(str).str.strip()

            st.write("Vista previa de Segmentos mapeados:", df_nuevo_seg.head())

            if st.button("📥 Registrar y Guardar Segmentos en Base de Datos"):
                if not sel_mes_s or str(sel_mes_s).strip() == "":
                    st.error(
                        "⚠️ Debe especificar un Mes Operativo válido para registrar los segmentos."
                    )
                else:
                    df_nuevo_seg["Anio"] = str(sel_anio_s)
                    df_nuevo_seg["Mes"] = str(sel_mes_s)

                    query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_segmentos'"
                    res_check = db.cargar_tabla_sql(query_check)

                    if res_check is not None and not res_check.empty:
                        df_existente_seg = db.cargar_tabla_sql(
                            "SELECT * FROM maestro_segmentos"
                        )
                        df_existente_seg = df_existente_seg[
                            ~(
                                (
                                    df_existente_seg["Anio"].astype(str)
                                    == str(sel_anio_s)
                                )
                                & (
                                    df_existente_seg["Mes"].astype(str)
                                    == str(sel_mes_s)
                                )
                            )
                        ]
                        df_final_seg = pd.concat(
                            [df_existente_seg, df_nuevo_seg], ignore_index=True
                        )
                    else:
                        df_final_seg = df_nuevo_seg

                    db.guardar_dataframe_sql(
                        df_final_seg, "maestro_segmentos", if_exists="replace"
                    )
                    st.success(
                        f"¡Maestro de segmentos guardado exitosamente para el período {sel_mes_s}/{sel_anio_s}!"
                    )
                    st.rerun()
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel de segmentos: {e}")

    titulo_tabla_s = f"📋 Segmentos registrados en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_s or str(sel_mes_s).strip() == '' else f'Período {sel_mes_s}/{sel_anio_s}'})"
    st.markdown(f"#### {titulo_tabla_s}")

    df_segmentos_actual = obtener_maestro_segmentos_sql(sel_anio_s, sel_mes_s)
    st.dataframe(df_segmentos_actual, width="stretch")

    st.divider()

    # =========================================================================
    # 3. SECCIÓN: MAESTRO MARCA - CEBE Y OBJETIVOS (INCL. COBERTURA)
    # =========================================================================
    st.markdown(
        "### 🏷️ 3. Maestro de Marcas, CEBE, Objetivos de TN/Gross y Cobertura (Pepsico / Empresa)"
    )
    col5, col6 = st.columns(2)
    with col5:
        sel_anio_m = st.text_input(
            "Año Operativo (Marcas/CEBE)", value=anio_def, key="anio_marca_cebe"
        )
    with col6:
        sel_mes_m = st.text_input(
            "Mes Operativo (Marcas/CEBE)",
            value=mes_def,
            placeholder="Dejar vacío para ver toda la base",
            key="mes_marca_cebe",
        )

    df_marcas_cebe_actual = obtener_maestro_marcas_cebe_sql(sel_anio_m, sel_mes_m)

    output_plantilla = BytesIO()
    with pd.ExcelWriter(output_plantilla, engine="openpyxl") as writer:
        df_plantilla = df_marcas_cebe_actual.copy()
        if df_plantilla.empty:
            df_plantilla = pd.DataFrame(
                columns=[
                    "Anio",
                    "Mes",
                    "Marca",
                    "CEBE",
                    "Obj_TN_Mes",
                    "Obj_Gross_Mes",
                    "Obj_Pepsico_Cobertura",
                    "Obj_Empresa_Cobertura",
                ]
            )
        df_plantilla.to_excel(writer, index=False, sheet_name="Maestro_Marcas_CEBE")

    st.download_button(
        label="📥 Descargar Plantilla de Marcas y CEBE para Completar",
        data=output_plantilla.getvalue(),
        file_name=f"plantilla_marcas_cebe_{sel_mes_m}_{sel_anio_m}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    archivo_marcas = st.file_uploader(
        "📂 Subir Excel Actualizado de Marcas, CEBE y Objetivos",
        type=["xlsx", "xls"],
        key="up_excel_marcas_cebe",
    )

    if archivo_marcas is not None:
        try:
            df_nuevo_cebe = pd.read_excel(archivo_marcas)
            columnas_cebe = list(df_nuevo_cebe.columns)

            nuevos_nombres_cebe = {}
            for col in columnas_cebe:
                col_str = str(col).strip().lower()
                if "marca" in col_str or "marcaupper" in col_str:
                    nuevos_nombres_cebe[col] = "Marca"
                elif "cebe" in col_str or "tipo" in col_str or "categoria" in col_str:
                    nuevos_nombres_cebe[col] = "CEBE"
                elif "obj_tn" in col_str or "tn" in col_str:
                    nuevos_nombres_cebe[col] = "Obj_TN_Mes"
                elif "obj_gross" in col_str or "gross" in col_str:
                    nuevos_nombres_cebe[col] = "Obj_Gross_Mes"
                elif "pepsico" in col_str or "coberturapepsico" in col_str:
                    nuevos_nombres_cebe[col] = "Obj_Pepsico_Cobertura"
                elif "empresa" in col_str or "coberturaempresa" in col_str:
                    nuevos_nombres_cebe[col] = "Obj_Empresa_Cobertura"

            df_nuevo_cebe = df_nuevo_cebe.rename(columns=nuevos_nombres_cebe)

            cols_necesarias_cebe = [
                "Obj_TN_Mes",
                "Obj_Gross_Mes",
                "Obj_Pepsico_Cobertura",
                "Obj_Empresa_Cobertura",
            ]
            for col_req in cols_necesarias_cebe:
                if col_req not in df_nuevo_cebe.columns:
                    df_nuevo_cebe[col_req] = 0.0
                else:
                    df_nuevo_cebe[col_req] = pd.to_numeric(
                        df_nuevo_cebe[col_req], errors="coerce"
                    ).fillna(0.0)

            if (
                "Marca" not in df_nuevo_cebe.columns
                or "CEBE" not in df_nuevo_cebe.columns
            ):
                st.error(
                    "⚠️ El archivo Excel debe contener al menos las columnas 'Marca' y 'CEBE'."
                )
            else:
                cols_requeridas = [
                    "Marca",
                    "CEBE",
                    "Obj_TN_Mes",
                    "Obj_Gross_Mes",
                    "Obj_Pepsico_Cobertura",
                    "Obj_Empresa_Cobertura",
                ]
                df_nuevo_cebe = df_nuevo_cebe[
                    [c for c in cols_requeridas if c in df_nuevo_cebe.columns]
                ].copy()
                df_nuevo_cebe = df_nuevo_cebe.dropna(subset=["Marca", "CEBE"])
                df_nuevo_cebe["Marca"] = df_nuevo_cebe["Marca"].astype(str).str.strip()
                df_nuevo_cebe["CEBE"] = df_nuevo_cebe["CEBE"].astype(str).str.strip()

                st.write(
                    "Vista previa de Marcas, CEBE y Objetivos mapeados:",
                    df_nuevo_cebe.head(),
                )

                if st.button(
                    "📥 Registrar y Guardar Marcas/CEBE y Objetivos en Base de Datos"
                ):
                    if not sel_mes_m or str(sel_mes_m).strip() == "":
                        st.error(
                            "⚠️ Debe especificar un Mes Operativo válido para registrar las marcas, CEBE y objetivos."
                        )
                    else:
                        df_nuevo_cebe["Anio"] = str(sel_anio_m)
                        df_nuevo_cebe["Mes"] = str(sel_mes_m)

                        query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_marcas_cebe'"
                        res_check = db.cargar_tabla_sql(query_check)

                        if res_check is not None and not res_check.empty:
                            df_existente_cebe = db.cargar_tabla_sql(
                                "SELECT * FROM maestro_marcas_cebe"
                            )
                            df_existente_cebe = df_existente_cebe[
                                ~(
                                    (
                                        df_existente_cebe["Anio"].astype(str)
                                        == str(sel_anio_m)
                                    )
                                    & (
                                        df_existente_cebe["Mes"].astype(str)
                                        == str(sel_mes_m)
                                    )
                                )
                            ]
                            df_final_cebe = pd.concat(
                                [df_existente_cebe, df_nuevo_cebe], ignore_index=True
                            )
                        else:
                            df_final_cebe = df_nuevo_cebe

                        db.guardar_dataframe_sql(
                            df_final_cebe, "maestro_marcas_cebe", if_exists="replace"
                        )
                        st.success(
                            f"¡Maestro Marca/CEBE y Objetivos guardado exitosamente para el período {sel_mes_m}/{sel_anio_m}!"
                        )
                        st.rerun()
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel de Marcas/CEBE: {e}")

    titulo_tabla_m = f"📋 Marcas, CEBE y Objetivos registrados en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_m or str(sel_mes_m).strip() == '' else f'Período {sel_mes_m}/{sel_anio_m}'})"
    st.markdown(f"#### {titulo_tabla_m}")

    df_marcas_cebe_actual = obtener_maestro_marcas_cebe_sql(sel_anio_m, sel_mes_m)
    st.dataframe(df_marcas_cebe_actual, width="stretch")

    st.divider()

    # =========================================================================
    # 3.B SECCIÓN: MAESTRO CCC (INCLUYENDO Obj_CCC_Pepsico) - VERSIONADO HISTÓRICO
    # =========================================================================
    st.markdown(
        "### 📊 3.B Maestro CCC (Porcentaje Cartera y Objetivo Absoluto Obj_CCC_Pepsico)"
    )
    st.markdown(
        "Configure el porcentaje (%) sobre la cartera neta y/o el **Objetivo en cantidad de clientes de Pepsico (`Obj_CCC_Pepsico`)** para cada taxonomía (A, B, C, D) en el período seleccionado."
    )

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        sel_anio_ccc = st.text_input(
            "Año Operativo (CCC)", value=anio_def, key="anio_ccc_param"
        )
    with col_c2:
        sel_mes_ccc = st.text_input(
            "Mes Operativo (CCC)", value=mes_def, key="mes_ccc_param"
        )

    df_ccc_actual = obtener_maestro_ccc_sql(sel_anio_ccc, sel_mes_ccc)

    df_editado_ccc = st.data_editor(
        df_ccc_actual[["Taxonomia", "Porcentaje_Cartera", "Obj_CCC_Pepsico"]],
        num_rows="fixed",
        key="editor_maestro_ccc",
        width="stretch",
    )

    if st.button("📥 Registrar y Guardar Configuración CCC en Base de Datos"):
        if not sel_mes_ccc or str(sel_mes_ccc).strip() == "":
            st.error(
                "⚠️ Debe especificar un Mes Operativo válido para guardar la configuración CCC."
            )
        else:
            df_nuevo_ccc = df_editado_ccc.copy()
            df_nuevo_ccc["Anio"] = int(float(sel_anio_ccc))
            df_nuevo_ccc["Mes"] = int(float(sel_mes_ccc))
            df_nuevo_ccc["Porcentaje_Cartera"] = pd.to_numeric(
                df_nuevo_ccc["Porcentaje_Cartera"], errors="coerce"
            ).fillna(0.0)
            df_nuevo_ccc["Obj_CCC_Pepsico"] = pd.to_numeric(
                df_nuevo_ccc["Obj_CCC_Pepsico"], errors="coerce"
            ).fillna(0.0)

            query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='maestro_ccc'"
            res_check = db.cargar_tabla_sql(query_check)

            if res_check is not None and not res_check.empty:
                df_existente_ccc = db.cargar_tabla_sql("SELECT * FROM maestro_ccc")
                df_existente_ccc = df_existente_ccc[
                    ~(
                        (df_existente_ccc["Anio"].astype(str) == str(sel_anio_ccc))
                        & (df_existente_ccc["Mes"].astype(str) == str(sel_mes_ccc))
                    )
                ]
                df_final_ccc = pd.concat(
                    [df_existente_ccc, df_nuevo_ccc], ignore_index=True
                )
            else:
                df_final_ccc = df_nuevo_ccc

            db.guardar_dataframe_sql(df_final_ccc, "maestro_ccc", if_exists="replace")
            st.success(
                f"¡Configuración CCC guardada y versionada exitosamente para el período {sel_mes_ccc}/{sel_anio_ccc}!"
            )
            st.rerun()

    titulo_tabla_ccc_reg = f"📋 Parámetros CCC registrados en Base de Datos (Período {sel_mes_ccc}/{sel_anio_ccc})"
    st.markdown(f"#### {titulo_tabla_ccc_reg}")
    st.dataframe(df_ccc_actual, width="stretch")

    st.divider()

    # =========================================================================
    # 3.C SECCIÓN: MAESTRO TIENDA PERFECTA - VERSIONADO HISTÓRICO
    # =========================================================================
    st.markdown("### ⭐ 3.C Maestro Tienda Perfecta (Objetivo Absoluto Obj_TP_Pepsico)")
    st.markdown(
        "Configure el **objetivo absoluto en cantidad de clientes de Tienda Perfecta solicitado por PepsiCo (`Obj_TP_Pepsico`)** para cada taxonomía (A, B, C, D) en el período seleccionado."
    )
    col_tp1, col_tp2 = st.columns(2)
    with col_tp1:
        sel_anio_tp = st.text_input(
            "Año Operativo (TP)", value=anio_def, key="anio_tp_param"
        )
    with col_tp2:
        sel_mes_tp = st.text_input(
            "Mes Operativo (TP)", value=mes_def, key="mes_tp_param"
        )
    df_tp_actual = obtener_maestro_tp_sql(sel_anio_tp, sel_mes_tp)
    df_editado_tp = st.data_editor(
        df_tp_actual[["Taxonomia", "Obj_TP_Pepsico"]],
        num_rows="fixed",
        column_config={
            "Taxonomia": st.column_config.TextColumn("Taxonomia", disabled=True),
            "Obj_TP_Pepsico": st.column_config.NumberColumn(
                "Obj_TP_Pepsico",
                help="Cantidad objetivo de clientes TP solicitada por PepsiCo.",
                min_value=0,
                step=1,
                format="%d",
            ),
        },
        key="editor_maestro_tp",
        width="stretch",
    )
    if st.button(
        "📥 Registrar y Guardar Configuración TP en Base de Datos",
        key="btn_guardar_maestro_tp",
    ):
        if not sel_mes_tp or str(sel_mes_tp).strip() == "":
            st.error(
                "⚠️ Debe especificar un Mes Operativo válido para guardar la configuración TP."
            )
        else:
            exito_tp, mensaje_tp = db.guardar_maestro_tp(
                df_editado_tp, sel_anio_tp, sel_mes_tp
            )
            if exito_tp:
                st.success(mensaje_tp)
                st.rerun()
            else:
                st.error(mensaje_tp)
    titulo_tabla_tp = f"📋 Parámetros TP registrados en Base de Datos (Período {sel_mes_tp}/{sel_anio_tp})"
    st.markdown(f"#### {titulo_tabla_tp}")
    st.dataframe(df_tp_actual, width="stretch", hide_index=True)
    st.divider()
    # =========================================================================
    # 3.D SECCIÓN: GENERACIÓN Y ADMINISTRACIÓN DEL SNAPSHOT TP
    # =========================================================================
    st.markdown("### 🎯 3.D Objetivos TP por Vendedor - Snapshot Congelado")
    st.markdown(
        "Genera una única vez los objetivos por vendedor y taxonomía usando el universo "
        "vigente como fotografía. Después de generados, los cambios del universo no "
        "recalculan el objetivo. Las modificaciones posteriores son exclusivamente manuales."
    )
    col_obj_tp1, col_obj_tp2 = st.columns(2)
    with col_obj_tp1:
        sel_anio_obj_tp = st.text_input(
            "Año del Snapshot TP", value=anio_def, key="anio_obj_tp_snapshot"
        )
    with col_obj_tp2:
        sel_mes_obj_tp = st.text_input(
            "Mes del Snapshot TP", value=mes_def, key="mes_obj_tp_snapshot"
        )

    if st.button(
        "⚙️ Generar y congelar objetivos TP del período",
        key="btn_generar_snapshot_obj_tp",
    ):
        exito_snapshot, mensaje_snapshot = db.generar_snapshot_objetivos_tp(
            sel_anio_obj_tp, sel_mes_obj_tp
        )
        if exito_snapshot:
            st.success(mensaje_snapshot)
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(mensaje_snapshot)

    df_obj_tp_snapshot = db.obtener_snapshot_objetivos_tp(
        sel_anio_obj_tp, sel_mes_obj_tp
    )
    df_obj_tp_periodo, df_obj_tp_control = db.obtener_control_objetivos_tp(
        sel_anio_obj_tp, sel_mes_obj_tp
    )

    if df_obj_tp_snapshot.empty:
        st.info("No existe un snapshot TP para el período seleccionado.")
    else:
        if not df_obj_tp_periodo.empty:
            total_crudo_tp = int(df_obj_tp_periodo["Obj_TP_Pepsico"].sum())
            minimo_tp = int(round(total_crudo_tp * 1.20))
            total_original_tp = int(df_obj_tp_snapshot["Obj_TP_Asignado"].sum())
            total_final_tp = int(df_obj_tp_snapshot["Obj_TP_Final"].sum())
            estado_tp = str(df_obj_tp_periodo["EstadoSnapshot"].iloc[0])
            ctp1, ctp2, ctp3, ctp4, ctp5 = st.columns(5)
            ctp1.metric("Objetivo crudo PepsiCo", f"{total_crudo_tp:,.0f}")
            ctp2.metric("Mínimo global +20%", f"{minimo_tp:,.0f}")
            ctp3.metric("Asignación original", f"{total_original_tp:,.0f}")
            ctp4.metric("Objetivo final vigente", f"{total_final_tp:,.0f}")
            ctp5.metric("Estado snapshot", estado_tp)
            st.dataframe(
                df_obj_tp_periodo[
                    [
                        "Taxonomia",
                        "Obj_TP_Pepsico",
                        "Factor_Ajuste",
                        "Objetivo_Base_Ajustado",
                        "Adicional_Global",
                        "Objetivo_Final_Taxonomia",
                        "Potencial_Taxonomia",
                        "EstadoSnapshot",
                    ]
                ],
                width="stretch",
                hide_index=True,
            )

        supervisores_tp = sorted(
            df_obj_tp_snapshot["Supervisor_Snapshot"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        vendedores_tp = sorted(
            df_obj_tp_snapshot["Vendedor_Snapshot"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        f_tp1, f_tp2, f_tp3 = st.columns(3)
        with f_tp1:
            filtro_sup_tp = st.multiselect(
                "Supervisor snapshot", supervisores_tp, key="filtro_sup_obj_tp"
            )
        with f_tp2:
            filtro_vend_tp = st.multiselect(
                "Vendedor snapshot", vendedores_tp, key="filtro_vend_obj_tp"
            )
        with f_tp3:
            filtro_tax_tp = st.multiselect(
                "Taxonomía snapshot", ["A", "B", "C", "D"], key="filtro_tax_obj_tp"
            )

        df_obj_tp_vista = df_obj_tp_snapshot.copy()
        if filtro_sup_tp:
            df_obj_tp_vista = df_obj_tp_vista[
                df_obj_tp_vista["Supervisor_Snapshot"].astype(str).isin(filtro_sup_tp)
            ]
        if filtro_vend_tp:
            df_obj_tp_vista = df_obj_tp_vista[
                df_obj_tp_vista["Vendedor_Snapshot"].astype(str).isin(filtro_vend_tp)
            ]
        if filtro_tax_tp:
            df_obj_tp_vista = df_obj_tp_vista[
                df_obj_tp_vista["Taxonomia"].isin(filtro_tax_tp)
            ]

        columnas_editor_tp = [
            "CodVendedor",
            "Vendedor_Snapshot",
            "Supervisor_Snapshot",
            "Taxonomia",
            "Clientes_Potenciales_Snapshot",
            "Obj_TP_Asignado",
            "Obj_TP_Manual",
            "Obj_TP_Final",
            "Motivo_Modificacion",
        ]
        df_obj_tp_editado = st.data_editor(
            df_obj_tp_vista[columnas_editor_tp],
            num_rows="fixed",
            disabled=[
                "CodVendedor",
                "Vendedor_Snapshot",
                "Supervisor_Snapshot",
                "Taxonomia",
                "Clientes_Potenciales_Snapshot",
                "Obj_TP_Asignado",
                "Obj_TP_Final",
            ],
            column_config={
                "Obj_TP_Manual": st.column_config.NumberColumn(
                    "Obj_TP_Manual", min_value=0, step=1, format="%d"
                ),
                "Motivo_Modificacion": st.column_config.TextColumn(
                    "Motivo_Modificacion",
                    help="Obligatorio cuando se informa Obj_TP_Manual.",
                ),
            },
            key="editor_snapshot_obj_tp",
            width="stretch",
            hide_index=True,
        )

        if st.button(
            "💾 Guardar modificaciones manuales del snapshot TP",
            key="btn_guardar_modificaciones_obj_tp",
        ):
            exito_manual, mensaje_manual = db.guardar_modificaciones_objetivos_tp(
                df_obj_tp_editado,
                sel_anio_obj_tp,
                sel_mes_obj_tp,
            )
            if exito_manual:
                st.success(mensaje_manual)
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(mensaje_manual)
    st.divider()

    # =========================================================================
    # 4. SECCIÓN: MAESTRO DE INNOVACIONES
    # =========================================================================
    st.markdown("### 🚀 4. Maestro de Innovaciones")
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        sel_anio_in = st.text_input(
            "Año Operativo (Innovaciones)", value=anio_def, key="anio_innovaciones"
        )
    with col_in2:
        sel_mes_in = st.text_input(
            "Mes Operativo (Innovaciones)",
            value=mes_def,
            placeholder="Dejar vacío para ver toda la base",
            key="mes_innovaciones",
        )

    archivo_innovaciones = st.file_uploader(
        "📂 Subir Excel de Innovaciones",
        type=["xlsx", "xls"],
        key="up_excel_innovaciones",
    )

    if archivo_innovaciones is not None:
        try:
            st.write(
                "Vista previa del archivo de innovaciones:",
                pd.read_excel(archivo_innovaciones).head(),
            )

            if st.button("📥 Registrar y Guardar Innovaciones en Base de Datos"):
                if not sel_mes_in or str(sel_mes_in).strip() == "":
                    st.error(
                        "⚠️ Debe especificar un Mes Operativo válido para registrar las innovaciones."
                    )
                else:
                    exito, mensaje = db.guardar_innovaciones_desde_excel(
                        archivo_innovaciones, sel_anio_in, sel_mes_in
                    )
                    if exito:
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.error(mensaje)
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel de innovaciones: {e}")

    titulo_tabla_in = f"📋 Innovaciones registradas en Base de Datos ({'Base Completa - Sin Filtro' if not sel_mes_in or str(sel_mes_in).strip() == '' else f'Período {sel_mes_in}/{sel_anio_in}'})"
    st.markdown(f"#### {titulo_tabla_in}")

    df_innovaciones_actual = obtener_maestro_innovaciones_sql(sel_anio_in, sel_mes_in)
    st.dataframe(df_innovaciones_actual, width="stretch")

    st.divider()

    # =========================================================================
    # 5. SECCIÓN: IMPORTACIÓN DE OBJETIVOS CALIBRADOS (DEFINITIVOS)
    # =========================================================================
    st.markdown("### 📥 5. Importación de Objetivos Calibrados (Definitivos)")
    col7, col8 = st.columns(2)
    with col7:
        sel_anio_obj = st.text_input(
            "Año Operativo (Objetivos Calibrados)",
            value=anio_def,
            key="anio_objetivos_calib",
        )
    with col8:
        sel_mes_obj = st.text_input(
            "Mes Operativo (Objetivos Calibrados)",
            value=mes_def,
            key="mes_objetivos_calib",
        )

    archivo_objetivos_subido = st.file_uploader(
        "📂 Subir Excel de Objetivos Calibrados (.xlsx)",
        type=["xlsx", "xls"],
        key="up_excel_objetivos_calibrados",
    )

    if archivo_objetivos_subido is not None:
        try:
            st.write(
                "Vista previa del Excel calibrado:",
                pd.read_excel(archivo_objetivos_subido).head(),
            )

            if st.button(
                "🚀 Procesar e Ingresar Objetivos Calibrados a la Base de Datos"
            ):
                if not sel_mes_obj or str(sel_mes_obj).strip() == "":
                    st.error(
                        "⚠️ Debe especificar un Mes Operativo válido para versionar los objetivos."
                    )
                else:
                    with st.spinner("Guardando y versionando objetivos en SQLite..."):
                        exito, mensaje = db.guardar_objetivos_calibrados_desde_excel(
                            archivo_objetivos_subido, sel_anio_obj, sel_mes_obj
                        )
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
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_maestro_actual.to_excel(writer, index=False, sheet_name="Maestro_Vendedores")
        df_segmentos_actual.to_excel(
            writer, index=False, sheet_name="Maestro_Segmentos"
        )
        df_marcas_cebe_actual.to_excel(
            writer, index=False, sheet_name="Maestro_Marcas_CEBE"
        )
        df_ccc_actual.to_excel(writer, index=False, sheet_name="Maestro_CCC_Config")
        df_tp_actual.to_excel(writer, index=False, sheet_name="Maestro_TP_Config")
        df_obj_tp_periodo.to_excel(
            writer, index=False, sheet_name="Objetivos_TP_Periodo"
        )
        df_obj_tp_snapshot.to_excel(
            writer, index=False, sheet_name="Objetivos_TP_Vendedor"
        )
        df_innovaciones_actual.to_excel(
            writer, index=False, sheet_name="Maestro_Innovaciones"
        )
        df_objetivos_actual.to_excel(
            writer, index=False, sheet_name="Objetivos_Calibrados"
        )

    st.download_button(
        label="📥 Descargar Maestros y Objetivos Completos a Excel",
        data=output.getvalue(),
        file_name="maestros_y_objetivos_matinal.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
