# modules/business_rules/business_rules_cobertura.py

import pandas as pd

UMBRAL_COBERTURA = 3.0


# =====================================================
# BR01 - PEPSICO
# =====================================================


def aplicar_regla_pepsico(
    df: pd.DataFrame,
) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame()

    if "Proveedor" not in df.columns:
        return df.copy()

    return df[
        df["Proveedor"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .str.contains("PEPSICO", na=False)
    ].copy()


# =====================================================
# BR02 - EXCLUSIÓN COMODATOS
# =====================================================


def aplicar_regla_excluir_comodatos(
    df: pd.DataFrame,
) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame()

    if "TipoDeVenta" not in df.columns:
        return df.copy()

    tipos_excluidos = [
        "Comodato Devolución",
        "Comodato Ficticio",
        "Comodato Ficticio Devolución",
        "Comodato Préstamo",
    ]

    return df[
        ~df["TipoDeVenta"].fillna("").astype(str).str.strip().isin(tipos_excluidos)
    ].copy()


# =====================================================
# BR03 - PERÍODOS COBERTURA
# =====================================================


def aplicar_regla_periodo_cobertura(
    df: pd.DataFrame,
) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame()

    if "Periodo" not in df.columns:
        return df.copy()

    return df[
        df["Periodo"].isin(
            [
                "Arrastre",
                "Actual",
            ]
        )
    ].copy()


# =====================================================
# BR04 - EXCLUSIÓN VENDEDOR 20
# =====================================================


def aplicar_regla_excluir_vendedor_20(
    df: pd.DataFrame,
) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame()

    if "CodVendedor" not in df.columns:
        return df.copy()

    return df[df["CodVendedor"] != 20].copy()


# =====================================================
# BR05 - CLIENTE CUBIERTO
# =====================================================


def aplicar_regla_cliente_cubierto(
    df: pd.DataFrame,
    umbral: float = UMBRAL_COBERTURA,
) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame()

    if "Total_Cant" not in df.columns:
        return pd.DataFrame()

    return df[df["Total_Cant"] >= umbral].copy()


# =====================================================
# BR06 - CLIENTE NO CUBIERTO
# =====================================================


def aplicar_regla_cliente_no_cubierto(
    df: pd.DataFrame,
    umbral: float = UMBRAL_COBERTURA,
) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame()

    if "Total_Cant" not in df.columns:
        return pd.DataFrame()

    return df[df["Total_Cant"] < umbral].copy()


# =====================================================
# BR07 - ES CLIENTE BATALLA
# =====================================================


def es_cliente_batalla(
    total_cant: float,
    umbral: float = UMBRAL_COBERTURA,
) -> bool:
    if pd.isna(total_cant):
        return True
    return float(total_cant) < float(umbral)


# =====================================================
# BR08 - CALCULAR DEL DÍA
# =====================================================


def calcular_del_dia(
    dia_visita: str,
    dia_operativo: str,
) -> str:
    dv = str(dia_visita).strip().upper()
    do = str(dia_operativo).strip().upper()
    if dv and do and dv == do:
        return "SI"
    return "NO"


# =====================================================
# BR09 - ES CLIENTE CUBIERTO
# =====================================================


def es_cliente_cubierto(
    total_cant: float,
    umbral: float = UMBRAL_COBERTURA,
) -> bool:
    if pd.isna(total_cant):
        return False
    return float(total_cant) >= float(umbral)


# =====================================================
# BR10 - OBTENER ESTADO COBERTURA
# =====================================================


def obtener_estado_cobertura(
    total_cant: float,
    umbral: float = UMBRAL_COBERTURA,
) -> str:
    if es_cliente_cubierto(total_cant, umbral):
        return "CUBIERTO"
    return "NO CUBIERTO"


# =====================================================
# PIPELINE COBERTURA ESTÁNDAR
# =====================================================


def aplicar_reglas_base_cobertura(
    df_vtas: pd.DataFrame,
) -> pd.DataFrame:

    if df_vtas is None or df_vtas.empty:
        return pd.DataFrame()

    df = df_vtas.copy()

    df = aplicar_regla_pepsico(df)

    df = aplicar_regla_excluir_comodatos(df)

    df = aplicar_regla_periodo_cobertura(df)

    df = aplicar_regla_excluir_vendedor_20(df)

    return df
