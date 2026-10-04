import pandas as pd
from datetime import datetime, timedelta
from modules.staging import obtener_staging_vta


def generar_core_potencial_cliente(
    anio_operativo: int, mes_operativo: int
) -> pd.DataFrame:
    """
    Genera la única fuente de verdad para Potencial Cliente + Marca
    basado exclusivamente en los últimos 3 meses completos anteriores al período operativo
    definido por anio_operativo y mes_operativo.

    ARQUITECTURA: CORE (Sistema Matinal 2.0)
    VERSIÓN V1: Actualmente consume obtener_staging_vta(). En futuras versiones podrá
    migrarse a una fuente institucional de ventas operativas válidas alineada con la
    regla funcional "Problema de Cierre".

    DOCUMENTACIÓN DE CONTRATO TEMPORAL (Ejemplo para Período Operativo 10/2026):
    - Kg_Mes_1 = Mes más reciente (09/2026)
    - Kg_Mes_2 = Segundo mes anterior (08/2026)
    - Kg_Mes_3 = Tercer mes anterior (07/2026)
    """
    columnas_contrato = [
        "Cliente",
        "Marca",
        "Kg_Mes_1",
        "Kg_Mes_2",
        "Kg_Mes_3",
        "PotencialKg",
        "Mes_Referencia_1",
        "Mes_Referencia_2",
        "Mes_Referencia_3",
    ]

    # 1. Obtener datos exclusivamente de Staging
    df = obtener_staging_vta()

    if df is None or df.empty:
        return pd.DataFrame(columns=columnas_contrato)

    # Asegurar formato datetime en la fecha de entrega
    if "FechaEntrega_dt" in df.columns:
        df["FechaEntrega_dt"] = pd.to_datetime(df["FechaEntrega_dt"], errors="coerce")
    else:
        return pd.DataFrame(columns=columnas_contrato)

    # 2. Calcular la ventana histórica determinísticamente a partir de anio_operativo y mes_operativo
    primer_dia_mes_operativo = datetime(anio_operativo, mes_operativo, 1)

    mes_1_fin = primer_dia_mes_operativo - timedelta(days=1)
    mes_1_inicio = datetime(mes_1_fin.year, mes_1_fin.month, 1)

    mes_2_fin = mes_1_inicio - timedelta(days=1)
    mes_2_inicio = datetime(mes_2_fin.year, mes_2_fin.month, 1)

    mes_3_fin = mes_2_inicio - timedelta(days=1)
    mes_3_inicio = datetime(mes_3_fin.year, mes_3_fin.month, 1)

    label_mes_3 = mes_3_inicio.strftime("%m/%Y")
    label_mes_2 = mes_2_inicio.strftime("%m/%Y")
    label_mes_1 = mes_1_inicio.strftime("%m/%Y")

    # 3. Filtrar por rango de fechas (desde el inicio del mes 3 hasta el fin del mes 1)
    df_filtered = df[
        (df["FechaEntrega_dt"] >= mes_3_inicio) & (df["FechaEntrega_dt"] <= mes_1_fin)
    ].copy()

    if df_filtered.empty:
        return pd.DataFrame(columns=columnas_contrato)

    # 4. Aplicar Reglas de Negocio del Core (Filtros institucionales)
    # Proveedor PEPSICO (búsqueda robusta para variantes como PEPSICO FOODS, PEPSICO ALIMENTOS, etc.)
    if "Proveedor" in df_filtered.columns:
        df_filtered = df_filtered[
            df_filtered["Proveedor"]
            .astype(str)
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    # Excluir EMPLOYEES y EMPLEADOS
    cols_a_chequear = [
        c for c in ["Subramo", "TipoDeVenta", "Cliente"] if c in df_filtered.columns
    ]
    for col in cols_a_chequear:
        mask_empleados = (
            df_filtered[col]
            .astype(str)
            .str.upper()
            .str.contains("EMPLOYEES|EMPLEADOS", na=False)
        )
        df_filtered = df_filtered[~mask_empleados]

    # Excluir Tipos de Venta específicos (Comodatos y Préstamos)
    tipos_excluidos = [
        "COMODATO DEVOLUCIÓN",
        "COMODATO FICTICIO",
        "COMODATO FICTICIO DEVOLUCIÓN",
        "COMODATO PRÉSTAMO",
    ]
    if "TipoDeVenta" in df_filtered.columns:
        mask_comodatos = (
            df_filtered["TipoDeVenta"].astype(str).str.upper().isin(tipos_excluidos)
        )
        df_filtered = df_filtered[~mask_comodatos]

    if df_filtered.empty:
        return pd.DataFrame(columns=columnas_contrato)

    # 5. Asignar etiqueta de mes de referencia a cada transacción
    def asignar_mes_ref(fecha):
        if pd.isna(fecha):
            return None
        if mes_3_inicio <= fecha <= mes_3_fin:
            return label_mes_3
        elif mes_2_inicio <= fecha <= mes_2_fin:
            return label_mes_2
        elif mes_1_inicio <= fecha <= mes_1_fin:
            return label_mes_1
        return None

    df_filtered["Mes_Ref"] = df_filtered["FechaEntrega_dt"].apply(asignar_mes_ref)
    df_filtered = df_filtered.dropna(subset=["Mes_Ref"])

    if df_filtered.empty:
        return pd.DataFrame(columns=columnas_contrato)

    # 6. Agregación por Cliente, Marca y Mes de Referencia
    df_agregado = df_filtered.groupby(["Cliente", "Marca", "Mes_Ref"], as_index=False)[
        "PesoKg"
    ].sum()

    # Pivotar para alinear los meses como columnas individuales
    df_pivot = df_agregado.pivot_table(
        index=["Cliente", "Marca"], columns="Mes_Ref", values="PesoKg", fill_value=0.0
    ).reset_index()

    # Garantizar presencia de las columnas de los 3 meses en el DataFrame resultante
    for label in [label_mes_1, label_mes_2, label_mes_3]:
        if label not in df_pivot.columns:
            df_pivot[label] = 0.0

    # Mapear etiquetas temporales a los nombres estandarizados del contrato
    df_pivot = df_pivot.rename(
        columns={
            label_mes_1: "Kg_Mes_1",
            label_mes_2: "Kg_Mes_2",
            label_mes_3: "Kg_Mes_3",
        }
    )

    # Forzar tipos numéricos y rellenar nulos
    df_pivot["Kg_Mes_1"] = pd.to_numeric(df_pivot["Kg_Mes_1"], errors="coerce").fillna(
        0.0
    )
    df_pivot["Kg_Mes_2"] = pd.to_numeric(df_pivot["Kg_Mes_2"], errors="coerce").fillna(
        0.0
    )
    df_pivot["Kg_Mes_3"] = pd.to_numeric(df_pivot["Kg_Mes_3"], errors="coerce").fillna(
        0.0
    )

    # 7. Cálculo del Potencial (Versión V1: Promedio Simple)
    df_pivot["PotencialKg"] = (
        df_pivot["Kg_Mes_1"] + df_pivot["Kg_Mes_2"] + df_pivot["Kg_Mes_3"]
    ) / 3.0

    # 8. Inclusión de metadatos de los meses de referencia según contrato
    df_pivot["Mes_Referencia_1"] = label_mes_1
    df_pivot["Mes_Referencia_2"] = label_mes_2
    df_pivot["Mes_Referencia_3"] = label_mes_3

    return df_pivot[columnas_contrato]
