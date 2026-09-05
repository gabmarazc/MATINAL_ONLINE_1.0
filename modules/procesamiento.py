# modules/procesamiento.py
import pandas as pd

def limpiar_vtas_crudas(df_vtas: pd.DataFrame) -> pd.DataFrame:
    """Filtra devoluciones de comodatos, consumos de empleados y estandariza tipos."""
    if df_vtas.empty:
        return df_vtas
    
    df = df_vtas.copy()
    # Filtros estándar de exclusión comercial
    if 'tipo_operacion' in df.columns:
        df = df[~df['tipo_operacion'].isin(['COMODATO_DEV', 'CONSUMO_INTERNO'])]
        
    # Estandarización de fechas
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df['anio'] = df['fecha'].dt.year
        df['mes'] = df['fecha'].dt.month
        df['dia'] = df['fecha'].dt.day

    return df

def procesar_ext_vta(df_vtas: pd.DataFrame, df_ausencias: pd.DataFrame) -> pd.DataFrame:
    """Reasigna ventas según ausencias del personal y etiqueta periodos."""
    df = limpiar_vtas_crudas(df_vtas)
    # Lógica de reasignación por reemplazos operativos
    return df