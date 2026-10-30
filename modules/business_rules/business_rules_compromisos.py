# modules/business_rules/business_rules_compromisos.py
import pandas as pd

from modules.core.core_compromisos import (
    COLUMNAS_COMPROMISOS,
    obtener_core_compromisos,
)


CODIGOS_SUPERVISORES = (60, 70)
INDICADOR_PROMEDIO = "PORC SELLOUT MN"
INDICADORES_SUMA = [
    indicador for indicador in COLUMNAS_COMPROMISOS if indicador != INDICADOR_PROMEDIO
]


class BusinessRulesCompromisosError(RuntimeError):
    """Error de contrato o integridad en BUSINESS_RULES_COMPROMISOS."""


def _normalizar_supervisor(valor) -> int:
    supervisor = pd.to_numeric(pd.Series([valor]), errors="coerce").iloc[0]
    if pd.isna(supervisor):
        raise BusinessRulesCompromisosError(f"Supervisor invalido: {valor!r}.")
    supervisor = int(supervisor)
    if supervisor not in CODIGOS_SUPERVISORES:
        raise BusinessRulesCompromisosError(
            f"Supervisor fuera del contrato actual: {supervisor}. "
            f"Admitidos={list(CODIGOS_SUPERVISORES)}."
        )
    return supervisor


def _validar_core(core: pd.DataFrame) -> None:
    requeridas = [
        "DiaMatinal",
        "CodVend",
        "Nombre",
        "SUP",
        *COLUMNAS_COMPROMISOS,
        "TieneAlgunaCarga",
        "PrimeraMarcaTemporal",
        "UltimaMarcaTemporal",
    ]
    faltantes = [columna for columna in requeridas if columna not in core.columns]
    if faltantes:
        raise BusinessRulesCompromisosError(
            f"CORE_COMPROMISOS no cumple el contrato. Faltan: {faltantes}."
        )
    if core["CodVend"].duplicated().any():
        duplicados = (
            core.loc[core["CodVend"].duplicated(keep=False), "CodVend"]
            .astype(str)
            .tolist()
        )
        raise BusinessRulesCompromisosError(
            f"CORE_COMPROMISOS contiene CodVend duplicados: {duplicados}."
        )


def _preparar_core(core: pd.DataFrame) -> pd.DataFrame:
    trabajo = core.copy()
    trabajo["CodVend"] = pd.to_numeric(trabajo["CodVend"], errors="coerce").astype(
        "Int64"
    )
    trabajo["SUP_Numerico"] = pd.to_numeric(trabajo["SUP"], errors="coerce").astype(
        "Int64"
    )
    for indicador in COLUMNAS_COMPROMISOS:
        trabajo[indicador] = pd.to_numeric(trabajo[indicador], errors="coerce").astype(
            "Float64"
        )
    return trabajo


def _obtener_vendedores_supervisor(
    core: pd.DataFrame,
    supervisor: int,
) -> pd.DataFrame:
    vendedores = core.loc[
        core["SUP_Numerico"].eq(supervisor)
        & ~core["CodVend"].isin(CODIGOS_SUPERVISORES)
    ].copy()
    return vendedores.sort_values("CodVend").reset_index(drop=True)


def _obtener_fila_supervisor(
    core: pd.DataFrame,
    supervisor: int,
) -> pd.Series:
    filas = core.loc[core["CodVend"].eq(supervisor)].copy()
    if len(filas) != 1:
        raise BusinessRulesCompromisosError(
            f"Se esperaba exactamente una fila CORE para supervisor {supervisor}; "
            f"encontradas={len(filas)}."
        )
    return filas.iloc[0]


def _agregar_compromisos_vendedores(vendedores: pd.DataFrame) -> dict:
    resultado = {}
    for indicador in INDICADORES_SUMA:
        serie = pd.to_numeric(vendedores[indicador], errors="coerce")
        resultado[indicador] = (
            float(serie.sum(skipna=True)) if serie.notna().any() else pd.NA
        )

    sellout = pd.to_numeric(vendedores[INDICADOR_PROMEDIO], errors="coerce")
    resultado[INDICADOR_PROMEDIO] = (
        float(sellout.mean(skipna=True)) if sellout.notna().any() else pd.NA
    )
    return resultado


def _estado_carga_vendedores(vendedores: pd.DataFrame) -> pd.DataFrame:
    control = vendedores[
        [
            "CodVend",
            "Nombre",
            "SUP",
            *COLUMNAS_COMPROMISOS,
            "TieneAlgunaCarga",
            "PrimeraMarcaTemporal",
            "UltimaMarcaTemporal",
        ]
    ].copy()

    control["IndicadoresCargados"] = control[COLUMNAS_COMPROMISOS].notna().sum(axis=1)
    control["IndicadoresFaltantes"] = control[COLUMNAS_COMPROMISOS].isna().sum(axis=1)
    control["Faltantes"] = control[COLUMNAS_COMPROMISOS].apply(
        lambda fila: ", ".join(fila.index[fila.isna()].tolist()) or "",
        axis=1,
    )
    control["EstadoCarga"] = control["IndicadoresCargados"].map(
        lambda cantidad: (
            "SIN CARGA"
            if cantidad == 0
            else "COMPLETA"
            if cantidad == len(COLUMNAS_COMPROMISOS)
            else "PARCIAL"
        )
    )
    return control.reset_index(drop=True)


def _calcular_comparacion(
    compromisos_vendedores: dict,
    fila_supervisor: pd.Series,
) -> pd.DataFrame:
    filas = []
    for indicador in COLUMNAS_COMPROMISOS:
        comp_vendedores = compromisos_vendedores.get(indicador, pd.NA)
        comp_supervisor = fila_supervisor.get(indicador, pd.NA)

        vend = pd.to_numeric(pd.Series([comp_vendedores]), errors="coerce").iloc[0]
        sup = pd.to_numeric(pd.Series([comp_supervisor]), errors="coerce").iloc[0]

        diferencia = pd.NA
        relacion = pd.NA
        if pd.notna(vend) and pd.notna(sup):
            diferencia = float(vend) - float(sup)
            if float(sup) != 0.0:
                relacion = float(vend) / float(sup)

        filas.append(
            {
                "INDICADOR": indicador,
                "COMP_VENDEDORES": pd.NA if pd.isna(vend) else float(vend),
                "COMP_SUPERVISOR": pd.NA if pd.isna(sup) else float(sup),
                "DIF_VEND_SUP": diferencia,
                "COMP_VEND_VS_SUP": relacion,
            }
        )

    return pd.DataFrame(filas)


def obtener_business_rules_compromisos(
    supervisor,
    dia_matinal=None,
    version_compromisos=None,
) -> dict:
    """
    Punto de entrada de BUSINESS_RULES_COMPROMISOS.

    Consume CORE_COMPROMISOS validado y devuelve:
    - tablero: agregados de vendedores, compromiso del supervisor y comparaciones;
    - control_carga: estado de carga/faltantes por vendedor;
    - vendedores: detalle CORE de vendedores pertenecientes al supervisor;
    - supervisor: fila CORE del supervisor;
    - metadata: controles básicos del universo preparado.

    Regla de agregacion de COMP_VENDEDORES:
    - suma: PLAT_GOLD, SILVER_BRZ, VARIOS ($), CCC (Efect), NC,
      ADOPCIÓN MN y TIENDAS PERFECTAS;
    - promedio: PORC SELLOUT MN.

    Esta capa no calcula SUGERIDO_MESA y no renderiza UI.
    """
    supervisor_int = _normalizar_supervisor(supervisor)

    core = obtener_core_compromisos(
        dia_matinal=dia_matinal,
        version_compromisos=version_compromisos,
    )
    if core is None or core.empty:
        raise BusinessRulesCompromisosError("CORE_COMPROMISOS no devolvio registros.")

    _validar_core(core)
    trabajo = _preparar_core(core)
    vendedores = _obtener_vendedores_supervisor(trabajo, supervisor_int)
    fila_supervisor = _obtener_fila_supervisor(trabajo, supervisor_int)

    compromisos_vendedores = _agregar_compromisos_vendedores(vendedores)
    tablero = _calcular_comparacion(compromisos_vendedores, fila_supervisor)
    control_carga = _estado_carga_vendedores(vendedores)

    dia_valores = (
        pd.to_datetime(trabajo["DiaMatinal"], errors="coerce")
        .dropna()
        .dt.normalize()
        .unique()
    )
    if len(dia_valores) > 1:
        raise BusinessRulesCompromisosError(
            f"CORE_COMPROMISOS contiene mas de un DiaMatinal: {list(dia_valores)}."
        )

    metadata = {
        "supervisor": supervisor_int,
        "dia_matinal": pd.Timestamp(dia_valores[0])
        if len(dia_valores) == 1
        else pd.NaT,
        "cantidad_vendedores": int(len(vendedores)),
        "carga_completa": int(control_carga["EstadoCarga"].eq("COMPLETA").sum()),
        "carga_parcial": int(control_carga["EstadoCarga"].eq("PARCIAL").sum()),
        "sin_carga": int(control_carga["EstadoCarga"].eq("SIN CARGA").sum()),
    }

    return {
        "tablero": tablero,
        "control_carga": control_carga,
        "vendedores": vendedores.drop(columns=["SUP_Numerico"]).reset_index(drop=True),
        "supervisor": fila_supervisor.drop(labels=["SUP_Numerico"]),
        "metadata": metadata,
    }
