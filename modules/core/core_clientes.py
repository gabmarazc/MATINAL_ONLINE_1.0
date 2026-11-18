import streamlit as st
import pandas as pd
from modules.staging import obtener_staging_clientes
from modules.utils import extraer_dia_de_ruta
from modules import database as db


def _obtener_periodo_operativo_desde_parametros() -> tuple[int, int]:
    """
    Obtiene Anio y Mes del escenario operativo sincronizado en SQLite.parametros.

    No aplica valores por defecto ni toma el ultimo periodo disponible. Si el
    periodo institucional no esta disponible o es invalido, falla explicitamente.
    """
    parametros = db.cargar_tabla_sql(
        "SELECT PARAMETRO, VALOR FROM parametros WHERE PARAMETRO IN ('Año', 'Mes')"
    )

    if parametros is None or parametros.empty:
        raise ValueError(
            "CORE_CLIENTES: no se encontro el periodo operativo en SQLite.parametros."
        )

    requeridas = {"PARAMETRO", "VALOR"}
    if not requeridas.issubset(set(parametros.columns)):
        raise ValueError(
            "CORE_CLIENTES: SQLite.parametros no cumple el contrato PARAMETRO/VALOR."
        )

    valores = {
        str(fila.PARAMETRO).strip(): fila.VALOR
        for fila in parametros[["PARAMETRO", "VALOR"]].itertuples(index=False)
    }

    if "Año" not in valores or "Mes" not in valores:
        raise ValueError("CORE_CLIENTES: SQLite.parametros debe contener Año y Mes.")

    try:
        anio = int(float(str(valores["Año"]).strip()))
        mes = int(float(str(valores["Mes"]).strip()))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "CORE_CLIENTES: Año y Mes de SQLite.parametros no son valores numericos validos."
        ) from exc

    if mes < 1 or mes > 12:
        raise ValueError(
            f"CORE_CLIENTES: Mes operativo invalido en SQLite.parametros: {mes}."
        )

    return anio, mes


def _obtener_taxonomias_activas_periodo(anio: int, mes: int) -> list[str]:
    """
    Obtiene exclusivamente las taxonomias activas del maestro institucional.

    No existe fallback hardcodeado. Si el periodo no tiene maestro o no posee
    taxonomias activas, falla explicitamente para evitar operar con otro periodo.
    """
    maestro = db.obtener_maestro_taxonomias(anio, mes)

    if maestro is None or maestro.empty:
        raise ValueError(
            "CORE_CLIENTES: no existe maestro_taxonomias para el periodo "
            f"{mes:02d}/{anio}."
        )

    requeridas = {"Taxonomia", "Activa"}
    if not requeridas.issubset(set(maestro.columns)):
        raise ValueError(
            "CORE_CLIENTES: maestro_taxonomias no cumple el contrato Taxonomia/Activa."
        )

    trabajo = maestro.copy()
    trabajo["Taxonomia"] = trabajo["Taxonomia"].astype("string").str.strip().str.upper()
    trabajo["Activa"] = pd.to_numeric(trabajo["Activa"], errors="coerce")

    taxonomias = (
        trabajo.loc[
            trabajo["Activa"].eq(1)
            & trabajo["Taxonomia"].notna()
            & trabajo["Taxonomia"].ne(""),
            "Taxonomia",
        ]
        .drop_duplicates()
        .tolist()
    )

    if not taxonomias:
        raise ValueError(
            "CORE_CLIENTES: maestro_taxonomias no posee taxonomias activas para "
            f"{mes:02d}/{anio}."
        )

    return taxonomias


@st.cache_data(show_spinner=False)
def obtener_core_clientes():
    """
    CORE_CLIENTES

    Responsabilidades:
    - Consumir STAGING_CLIENTES
    - Excluir empleados
    - Validar taxonomias comerciales contra maestro_taxonomias del periodo
    - Garantizar claves operativas validas

    No aplica reglas CCC.
    No aplica reglas MN+.
    No aplica reglas TP.
    """
    df = obtener_staging_clientes().copy()

    if df.empty:
        return pd.DataFrame()

    # -------------------------------------------------
    # EXCLUSION EMPLEADOS
    # -------------------------------------------------
    col_subsegmento = next(
        (c for c in df.columns if str(c).strip().lower() == "subsegmento"), None
    )

    if col_subsegmento:
        df = df[
            df[col_subsegmento].fillna("").astype(str).str.strip().str.casefold()
            != "empleados"
        ].copy()

    col_subramo = next(
        (c for c in df.columns if str(c).strip().lower() == "subramo"), None
    )

    if col_subramo:
        df = df[
            df[col_subramo].fillna("").astype(str).str.strip().str.casefold()
            != "empleados"
        ].copy()

    # -------------------------------------------------
    # TAXONOMIAS VALIDAS - MAESTRO INSTITUCIONAL
    # -------------------------------------------------
    if "Taxonomia" in df.columns:
        anio_operativo, mes_operativo = _obtener_periodo_operativo_desde_parametros()
        taxonomias_activas = _obtener_taxonomias_activas_periodo(
            anio_operativo, mes_operativo
        )

        df["Taxonomia"] = df["Taxonomia"].fillna("").astype(str).str.strip().str.upper()
        df = df[df["Taxonomia"].isin(taxonomias_activas)].copy()

    # -------------------------------------------------
    # CLIENTE VALIDO
    # -------------------------------------------------
    if "Cliente" in df.columns:
        df = df[df["Cliente"].notna()].copy()

    # -------------------------------------------------
    # VENDEDOR VALIDO
    # -------------------------------------------------
    if "CodVendedor" in df.columns:
        df = df[df["CodVendedor"].notna()].copy()

    if "Ruta" in df.columns:
        df["DiaVisita"] = df["Ruta"].apply(extraer_dia_de_ruta)
    else:
        df["DiaVisita"] = "SIN DÍA"

    return df
