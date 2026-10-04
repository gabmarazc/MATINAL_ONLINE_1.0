import pandas as pd
from modules.business_rules.business_rules_objetivo_carteras import (
    generar_business_rules_objetivo_cartera,
)


def generar_business_rules_objetivo_segmentos(
    anio_operativo: int, mes_operativo: int
) -> pd.DataFrame:
    """Asigna los objetivos de cartera agrupando directamente por vendedor,

    ruta y segmento sin calcular segmento dominante.

    Arquitectura: BUSINESS RULES (Sistema Matinal 2.0)
    """
    columnas_salida = ["codven", "Vendedor", "Ruta", "SEGMENTO", "ObjetivoKg"]

    # 1. Obtener objetivos desde la capa de cartera
    df_cartera = generar_business_rules_objetivo_cartera(anio_operativo, mes_operativo)
    if df_cartera is None or df_cartera.empty:
        return pd.DataFrame(columns=columnas_salida)

    suma_entrada = (
        pd.to_numeric(df_cartera["ObjetivoClienteKg"], errors="coerce")
        .fillna(0.0)
        .sum()
    )

    df_cartera["ObjetivoClienteKg"] = pd.to_numeric(
        df_cartera["ObjetivoClienteKg"], errors="coerce"
    ).fillna(0.0)

    for col in ["codven", "Vendedor", "Ruta", "SEGMENTO"]:
        if col not in df_cartera.columns:
            df_cartera[col] = None

    # 2. Agrupar exclusivamente por codven, Vendedor, Ruta, SEGMENTO y sumar ObjetivoClienteKg
    agrupado = df_cartera.groupby(
        ["codven", "Vendedor", "Ruta", "SEGMENTO"], as_index=False, dropna=False
    )["ObjetivoClienteKg"].sum()
    agrupado = agrupado.rename(columns={"ObjetivoClienteKg": "ObjetivoKg"})

    # Validación obligatoria de integridad (Tolerancia cero)
    suma_salida = (
        pd.to_numeric(agrupado["ObjetivoKg"], errors="coerce").fillna(0.0).sum()
    )
    assert abs(suma_entrada - suma_salida) < 1e-6, (
        f"Error de integridad: La suma de objetivos de entrada ({suma_entrada}) no coincide con la suma de salida ({suma_salida})."
    )

    return agrupado[columnas_salida]
