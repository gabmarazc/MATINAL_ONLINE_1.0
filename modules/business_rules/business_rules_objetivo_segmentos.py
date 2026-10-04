import pandas as pd
from modules.business_rules.business_rules_objetivo_carteras import (
    generar_business_rules_objetivo_cartera,
)
from modules.business_rules.business_rules_kilos import _asegurar_segmento_comercial
from modules.staging import obtener_staging_vta


def generar_business_rules_objetivo_segmentos(
    anio_operativo: int, mes_operativo: int
) -> pd.DataFrame:
    """Asigna los objetivos de cartera a la segmentación comercial oficial dominante por cliente,

    agrupando por vendedor, ruta y segmento.

    Arquitectura: BUSINESS RULES (Sistema Matinal 2.0)
    """
    columnas_salida = ["codven", "Vendedor", "Ruta", "SEGMENTO", "ObjetivoKg"]

    # 1. Obtener objetivos desde la capa de cartera[cite: 2]
    df_cartera = generar_business_rules_objetivo_cartera(anio_operativo, mes_operativo)
    if df_cartera is None or df_cartera.empty:
        return pd.DataFrame(columns=columnas_salida)

    suma_entrada = (
        pd.to_numeric(df_cartera["ObjetivoClienteKg"], errors="coerce")
        .fillna(0.0)
        .sum()
    )

    # 2 & 3 & 4. Obtener datos desde Staging y calcular el segmento dominante por Cliente[cite: 2]
    df_vta = obtener_staging_vta()
    dominant_seg = pd.DataFrame(columns=["Cliente_Str", "SEGMENTO"])

    if df_vta is not None and not df_vta.empty:
        df_vta_seg = _asegurar_segmento_comercial(df_vta)
        if (
            "Cliente" in df_vta_seg.columns
            and "SEGMENTO" in df_vta_seg.columns
            and "PesoKg" in df_vta_seg.columns
        ):
            df_vta_seg["Cliente_Str"] = df_vta_seg["Cliente"].astype(str).str.strip()
            df_vta_seg["PesoKg"] = pd.to_numeric(
                df_vta_seg["PesoKg"], errors="coerce"
            ).fillna(0.0)

            # Calcular PesoKg histórico por combinación y asignar la combinación con mayor PesoKg acumulado[cite: 2]
            combos = df_vta_seg.groupby(["Cliente_Str", "SEGMENTO"], as_index=False)[
                "PesoKg"
            ].sum()
            combos_sorted = combos.sort_values(
                by=["Cliente_Str", "PesoKg"], ascending=[True, False]
            )
            dominant_seg = combos_sorted.drop_duplicates(subset=["Cliente_Str"])[
                ["Cliente_Str", "SEGMENTO"]
            ]

    # 5. Cruzar Cliente contra objetivos cartera[cite: 2]
    df_cartera["Cliente_Str"] = df_cartera["Cliente"].astype(str).str.strip()
    df_merged = pd.merge(df_cartera, dominant_seg, on="Cliente_Str", how="left")
    df_merged["SEGMENTO"] = df_merged["SEGMENTO"].fillna("SIN SEGMENTO")
    df_merged["ObjetivoClienteKg"] = pd.to_numeric(
        df_merged["ObjetivoClienteKg"], errors="coerce"
    ).fillna(0.0)

    for col in ["codven", "Vendedor", "Ruta"]:
        if col not in df_merged.columns:
            df_merged[col] = None

    # 6 & 7 & 8. Agrupar por codven, Vendedor, Ruta, SEGMENTO y sumar ObjetivoClienteKg[cite: 2]
    agrupado = df_merged.groupby(
        ["codven", "Vendedor", "Ruta", "SEGMENTO"], as_index=False, dropna=False
    )["ObjetivoClienteKg"].sum()
    agrupado = agrupado.rename(columns={"ObjetivoClienteKg": "ObjetivoKg"})

    # Validación obligatoria de integridad (Tolerancia cero)[cite: 2]
    suma_salida = (
        pd.to_numeric(agrupado["ObjetivoKg"], errors="coerce").fillna(0.0).sum()
    )
    assert abs(suma_entrada - suma_salida) < 1e-6, (
        f"Error de integridad: La suma de objetivos de entrada ({suma_entrada}) no coincide con la suma de salida ({suma_salida})."
    )

    return agrupado[columnas_salida]
