# modules/core/core_compromisos.py
import pandas as pd
import streamlit as st

from modules import database as db
from modules.core.core_vendedores import obtener_core_vendedores


COLUMNAS_COMPROMISOS = [
    "PLAT_GOLD",
    "SILVER_BRZ",
    "VARIOS ($)",
    "CCC (Efect)",
    "NC",
    "PORC SELLOUT MN",
    "ADOPCIÓN MN",
    "TIENDAS PERFECTAS",
]

COLUMNAS_RAW_REQUERIDAS = [
    "Marca temporal",
    "CodVend",
    *COLUMNAS_COMPROMISOS,
]

CODIGOS_SUPERVISORES = [60, 70]


class CoreCompromisosError(RuntimeError):
    """Error de contrato o integridad en CORE_COMPROMISOS."""


def _dataframe_salida_vacio() -> pd.DataFrame:
    """Devuelve el contrato vacío estable de CORE_COMPROMISOS."""
    return pd.DataFrame(
        {
            "DiaMatinal": pd.Series(dtype="datetime64[ns]"),
            "CodVend": pd.Series(dtype="Int64"),
            "Nombre": pd.Series(dtype="string"),
            "SUP": pd.Series(dtype="string"),
            **{columna: pd.Series(dtype="Float64") for columna in COLUMNAS_COMPROMISOS},
            "TieneAlgunaCarga": pd.Series(dtype="boolean"),
            "PrimeraMarcaTemporal": pd.Series(dtype="datetime64[ns]"),
            "UltimaMarcaTemporal": pd.Series(dtype="datetime64[ns]"),
        }
    )


def _cargar_compromisos_raw() -> pd.DataFrame:
    """Carga la fotografía RAW persistida en SQLite.compromisos."""
    df = db.cargar_tabla_sql("SELECT * FROM compromisos")
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS_RAW_REQUERIDAS)
    return df.copy()


def _obtener_dia_matinal_sqlite() -> pd.Timestamp:
    """Obtiene Dia Matinal desde la tabla institucional parametros."""
    df = db.cargar_tabla_sql(
        """
        SELECT VALOR
        FROM parametros
        WHERE TRIM(PARAMETRO) = 'Dia Matinal'
        LIMIT 1
        """
    )
    if df is None or df.empty or "VALOR" not in df.columns:
        raise CoreCompromisosError(
            "No se encontró el parámetro institucional 'Dia Matinal'."
        )

    valor = df.iloc[0]["VALOR"]
    dia_matinal = pd.to_datetime(valor, dayfirst=True, errors="coerce")
    if pd.isna(dia_matinal):
        raise CoreCompromisosError(
            f"El parámetro 'Dia Matinal' no contiene una fecha válida: {valor!r}."
        )

    return pd.Timestamp(dia_matinal).normalize()


def _resolver_dia_matinal(dia_matinal=None) -> pd.Timestamp:
    """Normaliza una fecha explícita o utiliza el parámetro institucional."""
    if dia_matinal is None:
        return _obtener_dia_matinal_sqlite()

    fecha = pd.to_datetime(dia_matinal, dayfirst=True, errors="coerce")
    if pd.isna(fecha):
        raise CoreCompromisosError(
            f"dia_matinal no contiene una fecha válida: {dia_matinal!r}."
        )
    return pd.Timestamp(fecha).normalize()


def _validar_columnas_raw(df: pd.DataFrame) -> None:
    """Exige el contrato estructural mínimo de SQLite.compromisos."""
    faltantes = [
        columna for columna in COLUMNAS_RAW_REQUERIDAS if columna not in df.columns
    ]
    if faltantes:
        raise CoreCompromisosError(
            "SQLite.compromisos no cumple el contrato RAW. "
            f"Faltan columnas: {faltantes}. "
            f"Columnas encontradas: {list(df.columns)}."
        )


def _normalizar_numero(serie: pd.Series) -> pd.Series:
    """Normaliza números locales preservando vacíos como NULL."""
    texto = serie.astype("string").str.strip()
    texto = texto.mask(texto.eq(""), pd.NA)
    texto = texto.str.replace("%", "", regex=False)
    texto = texto.str.replace("$", "", regex=False)
    texto = texto.str.replace("Kg.", "", regex=False)
    texto = texto.str.replace("Kg", "", regex=False)
    texto = texto.str.replace(" ", "", regex=False)

    contiene_coma = texto.str.contains(",", regex=False, na=False)
    contiene_punto = texto.str.contains(".", regex=False, na=False)
    ambos = contiene_coma & contiene_punto

    texto = texto.where(
        ~ambos,
        texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    solo_coma = contiene_coma & ~contiene_punto
    texto = texto.where(
        ~solo_coma,
        texto.str.replace(",", ".", regex=False),
    )

    solo_punto = contiene_punto & ~contiene_coma
    punto_miles = solo_punto & texto.str.match(
        r"^-?\d{1,3}(?:\.\d{3})+$",
        na=False,
    )
    texto = texto.where(
        ~punto_miles,
        texto.str.replace(".", "", regex=False),
    )

    return pd.to_numeric(texto, errors="coerce").astype("Float64")


def _normalizar_compromisos_raw(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza claves, timestamps e indicadores sin aplicar reglas comerciales."""
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS_RAW_REQUERIDAS)

    trabajo = df.copy()
    trabajo.columns = [str(columna).strip() for columna in trabajo.columns]
    _validar_columnas_raw(trabajo)
    trabajo = trabajo[COLUMNAS_RAW_REQUERIDAS].copy()

    trabajo["Marca temporal"] = pd.to_datetime(
        trabajo["Marca temporal"],
        dayfirst=True,
        errors="coerce",
    )
    trabajo["CodVend"] = pd.to_numeric(
        trabajo["CodVend"],
        errors="coerce",
    ).astype("Int64")

    for columna in COLUMNAS_COMPROMISOS:
        trabajo[columna] = _normalizar_numero(trabajo[columna])

    filas_sin_clave = trabajo["CodVend"].isna()
    filas_sin_fecha = trabajo["Marca temporal"].isna()
    invalidas = filas_sin_clave | filas_sin_fecha
    if invalidas.any():
        muestra = (
            trabajo.loc[
                invalidas,
                ["Marca temporal", "CodVend"],
            ]
            .head(10)
            .to_dict("records")
        )
        raise CoreCompromisosError(
            "SQLite.compromisos contiene filas sin CodVend o Marca temporal válidos. "
            f"Cantidad={int(invalidas.sum())}; muestra={muestra}."
        )

    trabajo = trabajo.sort_values(
        ["CodVend", "Marca temporal"],
        kind="stable",
    ).reset_index(drop=True)
    return trabajo


def _filtrar_dia_matinal(
    df: pd.DataFrame,
    dia_matinal: pd.Timestamp,
) -> pd.DataFrame:
    """Conserva exclusivamente respuestas cuya fecha coincide con Dia Matinal."""
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS_RAW_REQUERIDAS)

    mascara = df["Marca temporal"].dt.normalize().eq(dia_matinal)
    return df.loc[mascara].copy().reset_index(drop=True)


def _resolver_ultimos_valores_no_nulos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resuelve una fila por CodVend.

    Para cada indicador conserva de forma independiente el último valor no nulo
    según Marca temporal. Una carga posterior nula no anula un valor anterior.
    """
    columnas_salida = [
        "CodVend",
        *COLUMNAS_COMPROMISOS,
        "PrimeraMarcaTemporal",
        "UltimaMarcaTemporal",
    ]
    if df is None or df.empty:
        return pd.DataFrame(columns=columnas_salida)

    ordenado = df.sort_values(
        ["CodVend", "Marca temporal"],
        kind="stable",
    )

    valores = ordenado.groupby("CodVend", as_index=False, sort=True)[
        COLUMNAS_COMPROMISOS
    ].last()
    marcas = ordenado.groupby("CodVend", as_index=False, sort=True).agg(
        PrimeraMarcaTemporal=("Marca temporal", "min"),
        UltimaMarcaTemporal=("Marca temporal", "max"),
    )

    resultado = valores.merge(
        marcas,
        on="CodVend",
        how="left",
        validate="one_to_one",
    )
    return resultado[columnas_salida].copy()


def _construir_universo_codigos(
    vigentes: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construye el universo del CORE.

    - Conserva todos los vendedores institucionales de core_vendedores.
    - Incorpora 60 y 70 como códigos operativos equivalentes en esta capa.
    - Incorpora defensivamente cualquier CodVend presente en compromisos RAW.
    """
    vendedores = obtener_core_vendedores().copy()

    if vendedores.empty:
        universo = pd.DataFrame(
            {
                "CodVend": pd.Series(dtype="Int64"),
                "Nombre": pd.Series(dtype="string"),
                "SUP": pd.Series(dtype="string"),
            }
        )
    else:
        requeridas = ["CodVendedor", "Nombre", "SUP"]
        faltantes = [
            columna for columna in requeridas if columna not in vendedores.columns
        ]
        if faltantes:
            raise CoreCompromisosError(
                "core_vendedores no cumple el contrato requerido. "
                f"Faltan columnas: {faltantes}."
            )

        universo = (
            vendedores[requeridas].rename(columns={"CodVendedor": "CodVend"}).copy()
        )
        universo["CodVend"] = pd.to_numeric(
            universo["CodVend"], errors="coerce"
        ).astype("Int64")
        universo["Nombre"] = universo["Nombre"].astype("string").fillna("").str.strip()
        universo["SUP"] = universo["SUP"].astype("string").fillna("").str.strip()
        universo = universo.dropna(subset=["CodVend"])

    especiales = pd.DataFrame(
        {
            "CodVend": pd.Series(CODIGOS_SUPERVISORES, dtype="Int64"),
            "Nombre": pd.Series(["", ""], dtype="string"),
            "SUP": pd.Series(["", ""], dtype="string"),
        }
    )

    codigos_raw = pd.DataFrame(
        {
            "CodVend": (
                vigentes["CodVend"].astype("Int64")
                if vigentes is not None and not vigentes.empty
                else pd.Series(dtype="Int64")
            )
        }
    )
    codigos_raw["Nombre"] = pd.Series(pd.NA, index=codigos_raw.index, dtype="string")
    codigos_raw["SUP"] = pd.Series(pd.NA, index=codigos_raw.index, dtype="string")

    universo = pd.concat(
        [universo, especiales, codigos_raw],
        ignore_index=True,
    )
    universo = universo.sort_values(
        ["CodVend", "Nombre"],
        kind="stable",
        na_position="last",
    )
    universo = universo.drop_duplicates("CodVend", keep="first")
    universo["Nombre"] = universo["Nombre"].astype("string").fillna("")
    universo["SUP"] = universo["SUP"].astype("string").fillna("")

    if universo["CodVend"].duplicated().any():
        raise CoreCompromisosError(
            "El universo CORE_COMPROMISOS contiene CodVend duplicados."
        )

    return universo.sort_values("CodVend").reset_index(drop=True)


def _integrar_universo_y_compromisos(
    universo: pd.DataFrame,
    vigentes: pd.DataFrame,
    dia_matinal: pd.Timestamp,
) -> pd.DataFrame:
    """Integra el universo institucional con los compromisos vigentes."""
    if universo is None or universo.empty:
        return _dataframe_salida_vacio()

    if vigentes is None or vigentes.empty:
        vigentes = pd.DataFrame(
            columns=[
                "CodVend",
                *COLUMNAS_COMPROMISOS,
                "PrimeraMarcaTemporal",
                "UltimaMarcaTemporal",
            ]
        )

    core = universo.merge(
        vigentes,
        on="CodVend",
        how="left",
        validate="one_to_one",
    )

    for columna in COLUMNAS_COMPROMISOS:
        core[columna] = pd.to_numeric(core[columna], errors="coerce").astype("Float64")

    core["TieneAlgunaCarga"] = (
        core[COLUMNAS_COMPROMISOS].notna().any(axis=1).astype("boolean")
    )
    core["DiaMatinal"] = dia_matinal
    core["CodVend"] = core["CodVend"].astype("Int64")
    core["Nombre"] = core["Nombre"].astype("string").fillna("")
    core["SUP"] = core["SUP"].astype("string").fillna("")
    core["PrimeraMarcaTemporal"] = pd.to_datetime(
        core["PrimeraMarcaTemporal"], errors="coerce"
    )
    core["UltimaMarcaTemporal"] = pd.to_datetime(
        core["UltimaMarcaTemporal"], errors="coerce"
    )

    columnas_salida = [
        "DiaMatinal",
        "CodVend",
        "Nombre",
        "SUP",
        *COLUMNAS_COMPROMISOS,
        "TieneAlgunaCarga",
        "PrimeraMarcaTemporal",
        "UltimaMarcaTemporal",
    ]
    core = core[columnas_salida].sort_values("CodVend").reset_index(drop=True)

    if core["CodVend"].duplicated().any():
        duplicados = (
            core.loc[core["CodVend"].duplicated(keep=False), "CodVend"]
            .astype(str)
            .tolist()
        )
        raise CoreCompromisosError(
            f"CORE_COMPROMISOS produjo CodVend duplicados: {duplicados}."
        )

    return core


def _calcular_version_compromisos() -> tuple:
    """
    Obtiene una versión barata y exclusiva de SQLite.compromisos.

    La versión cambia cuando cambia la cantidad de filas o la mayor Marca temporal.
    No modifica SQLite y no invalida cachés de otros dominios.
    """
    control = db.cargar_tabla_sql(
        """
        SELECT
            COUNT(*) AS CantidadFilas,
            MAX("Marca temporal") AS UltimaMarcaTemporal
        FROM compromisos
        """
    )
    if control is None or control.empty:
        return (0, None)

    cantidad = int(
        pd.to_numeric(control.iloc[0].get("CantidadFilas"), errors="coerce") or 0
    )
    ultima = control.iloc[0].get("UltimaMarcaTemporal")
    ultima = None if pd.isna(ultima) else str(ultima)
    return (cantidad, ultima)


@st.cache_data(show_spinner=False)
def _obtener_core_compromisos_cacheado(
    dia_matinal_iso: str,
    version_compromisos: tuple,
) -> pd.DataFrame:
    """Construye y cachea exclusivamente CORE_COMPROMISOS."""
    del version_compromisos

    dia_matinal = pd.Timestamp(dia_matinal_iso).normalize()
    raw = _cargar_compromisos_raw()
    normalizado = _normalizar_compromisos_raw(raw)
    del_dia = _filtrar_dia_matinal(normalizado, dia_matinal)
    vigentes = _resolver_ultimos_valores_no_nulos(del_dia)
    universo = _construir_universo_codigos(vigentes)
    return _integrar_universo_y_compromisos(
        universo=universo,
        vigentes=vigentes,
        dia_matinal=dia_matinal,
    )


def obtener_core_compromisos(
    dia_matinal=None,
    version_compromisos=None,
) -> pd.DataFrame:
    """
    Punto de entrada público de CORE_COMPROMISOS.

    Retorna una fila por CodVend para Dia Matinal. Cada indicador contiene el
    último valor no nulo cargado por ese código durante la jornada. Los códigos
    sin cargas permanecen en el universo con todos sus indicadores en NULL.

    Los códigos 60 y 70 se procesan exactamente igual que cualquier otro código.
    La separación posterior entre vendedores y supervisores no corresponde a CORE.
    """
    fecha = _resolver_dia_matinal(dia_matinal)
    version = (
        _calcular_version_compromisos()
        if version_compromisos is None
        else version_compromisos
    )

    resultado = _obtener_core_compromisos_cacheado(
        dia_matinal_iso=fecha.strftime("%Y-%m-%d"),
        version_compromisos=version,
    )
    return resultado.copy()
