import pandas as pd
from modules.business_rules.business_rules_objetivo_clientes import (
    generar_business_rules_objetivos_cliente,
)
from modules.database import cargar_tabla_sql


def _obtener_tabla_universo() -> pd.DataFrame:
    """
    Obtiene la tabla 'universo' utilizando la utilidad institucional de base de datos.
    """
    try:
        query = "SELECT Codigo, codven, Vendedor, Ruta, SubSegmento FROM universo"
        df_universo = cargar_tabla_sql(query)
        if df_universo is None:
            return pd.DataFrame(
                columns=["Codigo", "codven", "Vendedor", "Ruta", "SubSegmento"]
            )
        return df_universo
    except Exception:
        # En caso de error, retorna DataFrame vacío con la estructura esperada
        return pd.DataFrame(
            columns=["Codigo", "codven", "Vendedor", "Ruta", "SubSegmento"]
        )


def generar_business_rules_objetivo_cartera(
    anio_operativo: int, mes_operativo: int
) -> pd.DataFrame:
    """
    Asigna los objetivos calculados a la cartera comercial vigente cruzando
    los objetivos por cliente con la tabla SQL 'universo'.

    Arquitectura: BUSINESS RULES (Sistema Matinal 2.0)
    """
    columnas_salida = [
        "Cliente",
        "Marca",
        "ObjetivoClienteKg",
        "codven",
        "Vendedor",
        "Ruta",
        "SubSegmento",
        "MetodoAsignacion",
    ]

    # 1. Obtener objetivos calculados de la capa previa de Business Rules
    df_objetivos = generar_business_rules_objetivos_cliente(
        anio_operativo, mes_operativo
    )

    if df_objetivos is None or df_objetivos.empty:
        return pd.DataFrame(columns=columnas_salida)

    # Validación de suma inicial para asegurar integridad estricta
    suma_inicial = (
        pd.to_numeric(df_objetivos["ObjetivoClienteKg"], errors="coerce")
        .fillna(0.0)
        .sum()
    )

    # 2. Obtener tabla universo
    df_universo = _obtener_tabla_universo()

    if not df_universo.empty:
        # Estandarizar clave de unión
        df_objetivos["Cliente_Join"] = df_objetivos["Cliente"].astype(str).str.strip()
        df_universo["Codigo_Join"] = df_universo["Codigo"].astype(str).str.strip()

        # Eliminar duplicados en universo si los hubiera para evitar explosión de filas
        df_universo_clean = df_universo.drop_duplicates(subset=["Codigo_Join"]).copy()

        # 3. Cruzar Objetivos con Universo (Left Join)
        df_merged = pd.merge(
            df_objetivos,
            df_universo_clean[
                ["Codigo_Join", "codven", "Vendedor", "Ruta", "SubSegmento"]
            ],
            left_on="Cliente_Join",
            right_on="Codigo_Join",
            how="left",
        )
    else:
        # Si el universo no está disponible, todos los clientes caen en caso sin cartera
        df_merged = df_objetivos.copy()
        df_merged["codven"] = None
        df_merged["Vendedor"] = None
        df_merged["Ruta"] = None
        df_merged["SubSegmento"] = None

    # 4. Manejo de Casos Borde

    # CASO 1: Cliente no encontrado en universo (Codigo_Join es nulo o no hizo match)
    if "Codigo_Join" in df_merged.columns:
        mask_sin_cartera = df_merged["Codigo_Join"].isna() | (
            df_merged["Codigo_Join"] == ""
        )
    else:
        mask_sin_cartera = pd.Series([True] * len(df_merged), index=df_merged.index)

    df_merged.loc[mask_sin_cartera, "codven"] = None
    df_merged.loc[mask_sin_cartera, "Vendedor"] = "CLIENTE_SIN_CARTERA"
    df_merged.loc[mask_sin_cartera, "MetodoAsignacion"] = "CLIENTE_SIN_CARTERA"

    # CASO 2: codven nulo en registros que sí matchearon en el universo
    mask_vendedor_no_asignado = (~mask_sin_cartera) & (
        df_merged["codven"].isna()
        | (df_merged["codven"].astype(str).str.strip() == "")
        | (df_merged["codven"].astype(str).str.upper() == "NAN")
    )
    df_merged.loc[mask_vendedor_no_asignado, "Vendedor"] = "VENDEDOR_NO_ASIGNADO"

    # 5. Validación de Integridad (Suma antes y después debe ser exactamente igual)
    suma_final = (
        pd.to_numeric(df_merged["ObjetivoClienteKg"], errors="coerce").fillna(0.0).sum()
    )

    # Tolerancia cero para pérdida de objetivos
    assert abs(suma_inicial - suma_final) < 1e-6, (
        f"Error de integridad: La suma de objetivos cambió de {suma_inicial} a {suma_final} tras el cruce con el universo."
    )

    # 6. Selección estricta del contrato de salida
    resultado = df_merged[columnas_salida].copy()

    return resultado
