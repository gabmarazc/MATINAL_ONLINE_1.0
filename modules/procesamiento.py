import pandas as pd
import config as cfg

def leer_parametros_con_encabezado(ruta_archivo: str) -> dict:
    tablas = {}
    hojas = pd.read_excel(ruta_archivo, sheet_name=None, header=None)
    for nombre_hoja, datos_sin_encabezado in hojas.items():
        filas_con_valores = datos_sin_encabezado.notna().sum(axis=1)
        candidatos = filas_con_valores[filas_con_valores >= 2]
        if candidatos.empty:
            raise ValueError(f"No se encontró una fila de encabezados en la hoja '{nombre_hoja}'.")
        fila_encabezado = candidatos.index[0]
        encabezados = datos_sin_encabezado.iloc[fila_encabezado].astype(str).str.strip().tolist()
        tabla = datos_sin_encabezado.iloc[fila_encabezado + 1:].copy()
        tabla.columns = encabezados
        tabla = tabla.dropna(axis=1, how="all").dropna(axis=0, how="all")
        tablas[nombre_hoja] = tabla.reset_index(drop=True)
    return tablas

def limpiar_vtas_crudas(df_vta: pd.DataFrame) -> pd.DataFrame:
    df = df_vta[cfg.COLUMNAS_BASE_EXTVTA].copy()
    excluidos = ["Comodato Devolución", "Comodato Ficticio", "Comodato Ficticio Devolución", "Comodato Préstamo"]
    df = df[~df["TipoDeVenta"].isin(excluidos)].copy()
    
    df["Subramo"] = df["Subramo"].fillna("").astype(str).str.strip()
    df = df[df["Subramo"] != "Empleados"].copy()
    
    for col in ["FechaEntrega", "FechaCarga"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ["Cliente", "Codigo", "CodVendedor"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ["CantBase", "ImporteNetoItem", "ImporteItem", "PrecioCosto", "PesoKg"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    
    df = df[df["CodVendedor"].fillna(0) != 220].copy()
    df["ID_UNICO_CLI_VEND"] = df["CodVendedor"].astype(str) + "-" + df["Cliente"].astype(str)
    df["SEGMENTO"] = None
    
    es_gold = df["SegmentoRentabilidad"].isin(["Platinum", "Gold"])
    es_silver = df["SegmentoRentabilidad"].isin(["Silver", "Bronze"])
    df.loc[es_gold, "SEGMENTO"] = "GOLD " + df.loc[es_gold, "Rubro"].fillna("").astype(str)
    df.loc[es_silver, "SEGMENTO"] = "SILVER " + df.loc[es_silver, "Rubro"].fillna("").astype(str)
    return df

def procesar_ext_vta(df_vtas_limpias, ausencias, parametros):
    df = df_vtas_limpias.copy()
    fechas = parametros["FECHAS"]
    
    parametros_por_nombre = {}
    for n, v in zip(fechas["PARAMETRO"], fechas["VALOR"]):
        if pd.notna(n):
            parametros_por_nombre[str(n).strip().casefold()] = v
            
    año_operativo = int(parametros_por_nombre.get("añooperativo", parametros_por_nombre.get("año", 2026)))
    
    # --- CORRECCIÓN ROBUSTA DEL MES OPERATIVO (SOPORTA /, - Y VALORES NUMÉRICOS) ---
    val_mes = parametros_por_nombre.get("mesoperativo", parametros_por_nombre.get("mes", 1))
    val_mes_str = str(val_mes).strip()
    if "-" in val_mes_str:
        partes = val_mes_str.split("-")
        mes_operativo = int(partes[1]) if len(partes[0]) == 4 else int(partes[0])
    elif "/" in val_mes_str:
        partes = val_mes_str.split("/")
        mes_operativo = int(partes[1]) if len(partes[0]) == 4 else int(partes[0])
    else:
        mes_operativo = int(float(val_mes_str))
    # -----------------------------------------------------------------------------
    
    # Manejo seguro de cambio de año/mes para Arrastre y Futuro
    if mes_operativo == 1:
        mes_anterior = 12
        año_anterior = año_operativo - 1
    else:
        mes_anterior = mes_operativo - 1
        año_anterior = año_operativo
        
    if mes_operativo == 12:
        mes_siguiente = 1
        año_siguiente = año_operativo + 1
    else:
        mes_siguiente = mes_operativo + 1
        año_siguiente = año_operativo
    
    df["MesCarga"] = df["FechaCarga"].dt.month.astype("Int64")
    df["AñoCarga"] = df["FechaCarga"].dt.year.astype("Int64")
    df["MesEntrega"] = df["FechaEntrega"].dt.month.astype("Int64")
    df["AñoEntrega"] = df["FechaEntrega"].dt.year.astype("Int64")
    
    cond_arrastre = (df["AñoCarga"] == año_anterior) & (df["MesCarga"] == mes_anterior) & (df["AñoEntrega"] == año_operativo) & (df["MesEntrega"] == mes_operativo)
    cond_actual = (df["AñoCarga"] == año_operativo) & (df["MesCarga"] == mes_operativo) & (df["AñoEntrega"] == año_operativo) & (df["MesEntrega"] == mes_operativo)
    cond_futuro = (df["AñoCarga"] == año_operativo) & (df["MesCarga"] == mes_operativo) & (df["AñoEntrega"] == año_siguiente) & (df["MesEntrega"] == mes_siguiente)
    
    df["Periodo"] = None
    df.loc[cond_arrastre, "Periodo"] = "Arrastre"
    df.loc[cond_actual, "Periodo"] = "Actual"
    df.loc[cond_futuro, "Periodo"] = "Futuro"
    
    df = df[df["Periodo"].notna()].copy()
    df["ClaveAUS"] = df["CodVendedor"].astype(str).str.strip() + "-" + df["FechaCarga"].dt.strftime("%Y-%m-%d")
    
    aus = ausencias.copy()
    col_fecha_aus = "Fecha"
    for c in aus.columns:
        if str(c).strip().lower() in ["fecha", "dia", "día", "fechacarga", "fecha_carga"]:
            col_fecha_aus = c
            break
            
    aus[col_fecha_aus] = pd.to_datetime(aus[col_fecha_aus], dayfirst=True, errors="coerce")
    aus["CodVend"] = pd.to_numeric(aus["Ausente"], errors="coerce").astype("Int64")
    aus["Reemplazo"] = pd.to_numeric(aus["Reemplazo"], errors="coerce").astype("Int64")
    aus["Cliente"] = pd.to_numeric(aus["Cliente"], errors="coerce").astype("Int64")
    
    aus["ClaveAUS"] = aus["CodVend"].astype(str).str.strip() + "-" + aus[col_fecha_aus].dt.strftime("%Y-%m-%d")
    
    aus_dia = aus[aus["Cliente"].isna()][["ClaveAUS", "Reemplazo"]].drop_duplicates("ClaveAUS")
    aus_cliente = aus[aus["Cliente"].notna()][["ClaveAUS", "Cliente", "Reemplazo"]].drop_duplicates(["ClaveAUS", "Cliente"])
    
    df = df.merge(aus_dia.rename(columns={"Reemplazo": "ReemplazoDia"}), on="ClaveAUS", how="left")
    df = df.merge(aus_cliente.rename(columns={"Reemplazo": "ReemplazoCliente"}), on=["ClaveAUS", "Cliente"], how="left")
    df["Reemplazo"] = df["ReemplazoDia"].combine_first(df["ReemplazoCliente"])
    df["CodVendedorOperativo"] = df["Reemplazo"].combine_first(df["CodVendedor"]).astype("Int64")
    
    return df[cfg.COLUMNAS_FINALES_EXTVTA]

def procesar_rutas_operativas(df_rutas, anio_operativo, mes_operativo):
    df = df_rutas.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df[(df["Fecha"].dt.year == anio_operativo) & (df["Fecha"].dt.month == mes_operativo)].copy()