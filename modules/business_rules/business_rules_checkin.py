# modules/business_rules/business_rules_checkin.py
"""
BUSINESS RULES de CHECK-IN para MATINAL ONLINE.

Arquitectura:
    CORE_CHECKIN + CORE_RUTAS + MAESTRO_VENDEDORES
        -> BUSINESS_RULES_CHECKIN

Objetivo:
- clasificar cada visita según su pertenencia a la ruta programada;
- calcular métricas de ejecución por vendedor;
- conservar como universo final todos los vendedores del maestro;
- no leer Excel ni SQLite directamente;
- no persistir datos;
- no renderizar Streamlit ni aplicar formato visual de reporte.

Reglas institucionales:
1. Visita única:
   Cliente + FechaHoraCheckIn.
2. Día con ruta:
   combinación distinta CodVendedor + FechaRuta.
3. Visita en ruta:
   coincide Cliente + CodVendedor + FechaVisita con CORE_RUTAS.
4. Fuera de ruta por cliente:
   el vendedor tiene ruta ese día, pero el cliente visitado no está programado.
5. Sin ruta ese día:
   el vendedor realizó la visita, pero no existe CodVendedor + FechaRuta.
6. Visita fuera de ruta:
   FUERA_RUTA_CLIENTE o SIN_RUTA_ESE_DIA.
7. Los porcentajes de check-in, check-out, visita válida y pertenencia a ruta
   utilizan VisitasUnicas como denominador.
8. TiempoPDV no interviene en la validez de la visita.
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st

from modules.core.core_checkin import obtener_core_checkin
from modules.core.core_rutas import obtener_core_rutas
from modules.staging import obtener_staging_maestros


ESTADO_EN_RUTA = "EN_RUTA"
ESTADO_FUERA_RUTA_CLIENTE = "FUERA_RUTA_CLIENTE"
ESTADO_SIN_RUTA_DIA = "SIN_RUTA_ESE_DIA"
ESTADO_VENDEDOR_NO_MAPEABLE = "VENDEDOR_NO_MAPEABLE"

COLUMNAS_DETALLE = [
    "Cliente",
    "NombreClienteCHKIN",
    "CodVendedorCHKIN",
    "CodVendedor",
    "SupervisorCHKIN",
    "FechaHoraCheckIn",
    "FechaHoraCheckOut",
    "FechaVisita",
    "CheckInCorrecto",
    "CheckOutCorrecto",
    "VisitaValida",
    "ValidoOrigen",
    "CoincideValidezOrigen",
    "ExisteCarga",
    "TiempoPDV",
    "TiempoPDVSegundos",
    "DiaConRuta",
    "ClienteProgramadoEnRuta",
    "EstadoRuta",
    "VisitaEnRuta",
    "VisitaFueraRuta",
]

COLUMNAS_RESUMEN = [
    "CodVend",
    "Vendedor",
    "SUP",
    "DiasConRuta",
    "VisitasUnicas",
    "VisitasEnRuta",
    "PctVisitasEnRuta",
    "VisitasFueraRuta",
    "PctVisitasFueraRuta",
    "VisitasFueraRutaCliente",
    "VisitasSinRutaEseDia",
    "CheckInValidos",
    "PctCheckInValidos",
    "CheckOutValidos",
    "PctCheckOutValidos",
    "VisitasValidas",
    "PctVisitasValidas",
]


def _detalle_vacio() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Cliente": pd.Series(dtype="Int64"),
            "NombreClienteCHKIN": pd.Series(dtype="string"),
            "CodVendedorCHKIN": pd.Series(dtype="string"),
            "CodVendedor": pd.Series(dtype="Int64"),
            "SupervisorCHKIN": pd.Series(dtype="string"),
            "FechaHoraCheckIn": pd.Series(dtype="datetime64[ns]"),
            "FechaHoraCheckOut": pd.Series(dtype="datetime64[ns]"),
            "FechaVisita": pd.Series(dtype="datetime64[ns]"),
            "CheckInCorrecto": pd.Series(dtype="boolean"),
            "CheckOutCorrecto": pd.Series(dtype="boolean"),
            "VisitaValida": pd.Series(dtype="boolean"),
            "ValidoOrigen": pd.Series(dtype="string"),
            "CoincideValidezOrigen": pd.Series(dtype="boolean"),
            "ExisteCarga": pd.Series(dtype="string"),
            "TiempoPDV": pd.Series(dtype="timedelta64[ns]"),
            "TiempoPDVSegundos": pd.Series(dtype="Float64"),
            "DiaConRuta": pd.Series(dtype="boolean"),
            "ClienteProgramadoEnRuta": pd.Series(dtype="boolean"),
            "EstadoRuta": pd.Series(dtype="string"),
            "VisitaEnRuta": pd.Series(dtype="boolean"),
            "VisitaFueraRuta": pd.Series(dtype="boolean"),
        }
    )[COLUMNAS_DETALLE]


def _resumen_vacio() -> pd.DataFrame:
    datos = {
        "CodVend": pd.Series(dtype="Int64"),
        "Vendedor": pd.Series(dtype="string"),
        "SUP": pd.Series(dtype="Int64"),
    }
    for columna in [
        "DiasConRuta",
        "VisitasUnicas",
        "VisitasEnRuta",
        "VisitasFueraRuta",
        "VisitasFueraRutaCliente",
        "VisitasSinRutaEseDia",
        "CheckInValidos",
        "CheckOutValidos",
        "VisitasValidas",
    ]:
        datos[columna] = pd.Series(dtype="Int64")
    for columna in [
        "PctVisitasEnRuta",
        "PctVisitasFueraRuta",
        "PctCheckInValidos",
        "PctCheckOutValidos",
        "PctVisitasValidas",
    ]:
        datos[columna] = pd.Series(dtype="Float64")
    return pd.DataFrame(datos)[COLUMNAS_RESUMEN]


def _normalizar_codigo_vendedor_checkin(serie: pd.Series) -> pd.Series:
    """
    Convierte a Int64 exclusivamente identificadores enteros.

    Valores alfanuméricos o decimales no enteros permanecen como NA. No se
    redondean ni se inventa una equivalencia con el maestro de vendedores.
    """
    numerico = pd.to_numeric(serie.astype("string").str.strip(), errors="coerce")
    entero = numerico.notna() & np.isclose(numerico, np.floor(numerico))
    salida = pd.Series(pd.NA, index=serie.index, dtype="Int64")
    salida.loc[entero] = numerico.loc[entero].astype("int64")
    return salida


def _aplicar_periodo(
    df: pd.DataFrame,
    columna_fecha: str,
    fecha_desde: Optional[pd.Timestamp],
    fecha_hasta: Optional[pd.Timestamp],
) -> pd.DataFrame:
    salida = df.copy()
    fechas = pd.to_datetime(salida[columna_fecha], errors="coerce").dt.normalize()
    salida[columna_fecha] = fechas

    if fecha_desde is not None:
        desde = pd.Timestamp(fecha_desde).normalize()
        salida = salida.loc[salida[columna_fecha] >= desde]
    if fecha_hasta is not None:
        hasta = pd.Timestamp(fecha_hasta).normalize()
        salida = salida.loc[salida[columna_fecha] <= hasta]

    return salida.copy()


def _validar_core_checkin(df: pd.DataFrame) -> None:
    requeridas = [
        "Cliente",
        "NombreClienteCHKIN",
        "CodVendedorCHKIN",
        "SupervisorCHKIN",
        "FechaHoraCheckIn",
        "FechaHoraCheckOut",
        "FechaVisita",
        "CheckInCorrecto",
        "CheckOutCorrecto",
        "VisitaValidaCalculada",
        "ValidoOrigen",
        "CoincideValidezOrigen",
        "ExisteCarga",
        "TiempoPDV",
        "TiempoPDVSegundos",
    ]
    faltantes = [c for c in requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(
            "CORE_CHECKIN no cumple el contrato requerido por BUSINESS RULES. "
            f"Columnas faltantes: {faltantes}."
        )

    duplicadas = df.duplicated(
        subset=["Cliente", "FechaHoraCheckIn"],
        keep=False,
    )
    if duplicadas.any():
        raise ValueError(
            "CORE_CHECKIN contiene visitas duplicadas por la KEY institucional. "
            f"Filas afectadas: {int(duplicadas.sum())}."
        )


def _validar_core_rutas(df: pd.DataFrame) -> None:
    requeridas = ["Cliente", "NombreClienteRuta", "CodVendedor", "FechaRuta"]
    faltantes = [c for c in requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(
            "CORE_RUTAS no cumple el contrato requerido por BUSINESS RULES. "
            f"Columnas faltantes: {faltantes}."
        )

    duplicadas = df.duplicated(
        subset=["Cliente", "CodVendedor", "FechaRuta"],
        keep=False,
    )
    if duplicadas.any():
        raise ValueError(
            "CORE_RUTAS contiene asignaciones duplicadas por la KEY operativa. "
            f"Filas afectadas: {int(duplicadas.sum())}."
        )


def construir_detalle_checkin_ruta(
    core_checkin: pd.DataFrame,
    core_rutas: pd.DataFrame,
    fecha_desde: Optional[pd.Timestamp] = None,
    fecha_hasta: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """Clasifica cada visita de CORE_CHECKIN respecto de CORE_RUTAS."""
    if not isinstance(core_checkin, pd.DataFrame):
        raise TypeError("core_checkin debe ser un pandas.DataFrame.")
    if not isinstance(core_rutas, pd.DataFrame):
        raise TypeError("core_rutas debe ser un pandas.DataFrame.")

    if core_checkin.empty:
        return _detalle_vacio()

    _validar_core_checkin(core_checkin)
    _validar_core_rutas(core_rutas)

    visitas = _aplicar_periodo(
        core_checkin,
        "FechaVisita",
        fecha_desde,
        fecha_hasta,
    )
    rutas = _aplicar_periodo(
        core_rutas,
        "FechaRuta",
        fecha_desde,
        fecha_hasta,
    )

    if visitas.empty:
        return _detalle_vacio()

    visitas["CodVendedor"] = _normalizar_codigo_vendedor_checkin(
        visitas["CodVendedorCHKIN"]
    )
    visitas["FechaVisita"] = pd.to_datetime(
        visitas["FechaVisita"], errors="coerce"
    ).dt.normalize()

    rutas_clave = rutas[["Cliente", "CodVendedor", "FechaRuta"]].drop_duplicates()
    dias_ruta = rutas[["CodVendedor", "FechaRuta"]].drop_duplicates()

    detalle = visitas.merge(
        dias_ruta.assign(DiaConRuta=True),
        how="left",
        left_on=["CodVendedor", "FechaVisita"],
        right_on=["CodVendedor", "FechaRuta"],
        validate="many_to_one",
    )
    detalle["DiaConRuta"] = detalle["DiaConRuta"].fillna(False).astype("boolean")
    detalle = detalle.drop(columns=["FechaRuta"], errors="ignore")

    detalle = detalle.merge(
        rutas_clave.assign(ClienteProgramadoEnRuta=True),
        how="left",
        left_on=["Cliente", "CodVendedor", "FechaVisita"],
        right_on=["Cliente", "CodVendedor", "FechaRuta"],
        validate="many_to_one",
    )
    detalle["ClienteProgramadoEnRuta"] = (
        detalle["ClienteProgramadoEnRuta"].fillna(False).astype("boolean")
    )
    detalle = detalle.drop(columns=["FechaRuta"], errors="ignore")

    vendedor_mapeable = detalle["CodVendedor"].notna()
    detalle["EstadoRuta"] = np.select(
        [
            ~vendedor_mapeable,
            detalle["ClienteProgramadoEnRuta"].fillna(False),
            detalle["DiaConRuta"].fillna(False),
        ],
        [
            ESTADO_VENDEDOR_NO_MAPEABLE,
            ESTADO_EN_RUTA,
            ESTADO_FUERA_RUTA_CLIENTE,
        ],
        default=ESTADO_SIN_RUTA_DIA,
    )
    detalle["EstadoRuta"] = detalle["EstadoRuta"].astype("string")
    detalle["VisitaEnRuta"] = detalle["EstadoRuta"].eq(ESTADO_EN_RUTA).astype("boolean")
    detalle["VisitaFueraRuta"] = (
        detalle["EstadoRuta"]
        .isin([ESTADO_FUERA_RUTA_CLIENTE, ESTADO_SIN_RUTA_DIA])
        .astype("boolean")
    )
    detalle["VisitaValida"] = detalle["VisitaValidaCalculada"].astype("boolean")

    if len(detalle) != len(visitas):
        raise AssertionError(
            "La clasificación de ruta alteró la cantidad de visitas de CORE_CHECKIN."
        )

    duplicadas = detalle.duplicated(
        subset=["Cliente", "FechaHoraCheckIn"],
        keep=False,
    )
    if duplicadas.any():
        raise AssertionError(
            "La clasificación de ruta multiplicó visitas. "
            f"Filas afectadas: {int(duplicadas.sum())}."
        )

    return detalle[COLUMNAS_DETALLE].reset_index(drop=True)


def _resolver_maestro_vendedores(maestros: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if not isinstance(maestros, dict):
        raise TypeError("obtener_staging_maestros debe devolver un diccionario.")

    maestro = maestros.get("maestro_vendedores", pd.DataFrame())
    if not isinstance(maestro, pd.DataFrame) or maestro.empty:
        raise ValueError("El maestro de vendedores está vacío o no disponible.")

    candidatos_codigo = [
        "Codigo_Vendedor",
        "CodVend",
        "CodVendedor",
        "Codigo",
        "codven",
    ]
    candidatos_nombre = ["Nombre_Vendedor", "Nombre", "Vendedor", "NombreVendedor"]
    candidatos_sup = ["SUP", "Sup", "Supervisor"]

    col_codigo = next((c for c in candidatos_codigo if c in maestro.columns), None)
    col_nombre = next((c for c in candidatos_nombre if c in maestro.columns), None)
    col_sup = next((c for c in candidatos_sup if c in maestro.columns), None)

    faltantes = []
    if col_codigo is None:
        faltantes.append(f"código {candidatos_codigo}")
    if col_nombre is None:
        faltantes.append(f"nombre {candidatos_nombre}")
    if col_sup is None:
        faltantes.append(f"supervisor {candidatos_sup}")
    if faltantes:
        raise ValueError(
            "El maestro de vendedores no cumple el contrato requerido: "
            + "; ".join(faltantes)
            + f". Columnas encontradas: {list(maestro.columns)}."
        )

    base = pd.DataFrame(
        {
            "CodVend": pd.to_numeric(maestro[col_codigo], errors="coerce").astype(
                "Int64"
            ),
            "Vendedor": maestro[col_nombre].astype("string").str.strip(),
            "SUP": pd.to_numeric(maestro[col_sup], errors="coerce").astype("Int64"),
        }
    )

    claves_nulas = base["CodVend"].isna()
    if claves_nulas.any():
        raise ValueError(
            "El maestro contiene vendedores sin CodVend válido. "
            f"Filas afectadas: {int(claves_nulas.sum())}."
        )

    duplicadas = base["CodVend"].duplicated(keep=False)
    if duplicadas.any():
        muestra = base.loc[duplicadas].head(10).to_dict("records")
        raise ValueError(
            "El maestro contiene CodVend duplicados. "
            f"Filas afectadas: {int(duplicadas.sum())}. Muestra: {muestra}."
        )

    return base.sort_values("CodVend", kind="stable").reset_index(drop=True)


def _porcentaje(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    num = pd.to_numeric(numerador, errors="coerce").fillna(0.0)
    den = pd.to_numeric(denominador, errors="coerce").fillna(0.0)
    resultado = np.divide(
        num,
        den,
        out=np.zeros(len(num), dtype="float64"),
        where=den.to_numpy() != 0,
    )
    return pd.Series(resultado, index=numerador.index, dtype="Float64")


def construir_resumen_checkin_vendedores(
    core_checkin: pd.DataFrame,
    core_rutas: pd.DataFrame,
    maestros: dict[str, pd.DataFrame],
    fecha_desde: Optional[pd.Timestamp] = None,
    fecha_hasta: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """Construye una fila por vendedor del maestro con las métricas acordadas."""
    base = _resolver_maestro_vendedores(maestros)
    rutas = _aplicar_periodo(
        core_rutas,
        "FechaRuta",
        fecha_desde,
        fecha_hasta,
    )
    detalle = construir_detalle_checkin_ruta(
        core_checkin,
        core_rutas,
        fecha_desde,
        fecha_hasta,
    )

    dias = (
        rutas[["CodVendedor", "FechaRuta"]]
        .drop_duplicates()
        .groupby("CodVendedor", as_index=False)
        .agg(DiasConRuta=("FechaRuta", "nunique"))
        .rename(columns={"CodVendedor": "CodVend"})
    )

    detalle_mapeado = detalle.loc[detalle["CodVendedor"].notna()].copy()
    if detalle_mapeado.empty:
        metricas = pd.DataFrame(columns=["CodVend"])
    else:
        detalle_mapeado["EsEnRuta"] = detalle_mapeado["EstadoRuta"].eq(ESTADO_EN_RUTA)
        detalle_mapeado["EsFueraRutaCliente"] = detalle_mapeado["EstadoRuta"].eq(
            ESTADO_FUERA_RUTA_CLIENTE
        )
        detalle_mapeado["EsSinRutaDia"] = detalle_mapeado["EstadoRuta"].eq(
            ESTADO_SIN_RUTA_DIA
        )

        metricas = (
            detalle_mapeado.groupby("CodVendedor", as_index=False)
            .agg(
                VisitasUnicas=("FechaHoraCheckIn", "count"),
                VisitasEnRuta=("EsEnRuta", "sum"),
                VisitasFueraRuta=("VisitaFueraRuta", "sum"),
                VisitasFueraRutaCliente=("EsFueraRutaCliente", "sum"),
                VisitasSinRutaEseDia=("EsSinRutaDia", "sum"),
                CheckInValidos=("CheckInCorrecto", "sum"),
                CheckOutValidos=("CheckOutCorrecto", "sum"),
                VisitasValidas=("VisitaValida", "sum"),
            )
            .rename(columns={"CodVendedor": "CodVend"})
        )

    resumen = base.merge(dias, on="CodVend", how="left", validate="one_to_one")
    resumen = resumen.merge(
        metricas,
        on="CodVend",
        how="left",
        validate="one_to_one",
    )

    columnas_conteo = [
        "DiasConRuta",
        "VisitasUnicas",
        "VisitasEnRuta",
        "VisitasFueraRuta",
        "VisitasFueraRutaCliente",
        "VisitasSinRutaEseDia",
        "CheckInValidos",
        "CheckOutValidos",
        "VisitasValidas",
    ]
    for columna in columnas_conteo:
        resumen[columna] = (
            pd.to_numeric(resumen[columna], errors="coerce").fillna(0).astype("Int64")
        )

    resumen["PctVisitasEnRuta"] = _porcentaje(
        resumen["VisitasEnRuta"], resumen["VisitasUnicas"]
    )
    resumen["PctVisitasFueraRuta"] = _porcentaje(
        resumen["VisitasFueraRuta"], resumen["VisitasUnicas"]
    )
    resumen["PctCheckInValidos"] = _porcentaje(
        resumen["CheckInValidos"], resumen["VisitasUnicas"]
    )
    resumen["PctCheckOutValidos"] = _porcentaje(
        resumen["CheckOutValidos"], resumen["VisitasUnicas"]
    )
    resumen["PctVisitasValidas"] = _porcentaje(
        resumen["VisitasValidas"], resumen["VisitasUnicas"]
    )

    if len(resumen) != len(base):
        raise AssertionError("El resumen alteró la cantidad de vendedores del maestro.")
    if resumen["CodVend"].duplicated().any():
        raise AssertionError("El resumen contiene vendedores duplicados.")

    controles = {
        "VisitasEnRuta <= VisitasUnicas": (
            resumen["VisitasEnRuta"] <= resumen["VisitasUnicas"]
        ).all(),
        "VisitasFueraRuta <= VisitasUnicas": (
            resumen["VisitasFueraRuta"] <= resumen["VisitasUnicas"]
        ).all(),
        "EnRuta + FueraRuta = VisitasUnicas": (
            resumen["VisitasEnRuta"] + resumen["VisitasFueraRuta"]
            == resumen["VisitasUnicas"]
        ).all(),
        "CheckInValidos <= VisitasUnicas": (
            resumen["CheckInValidos"] <= resumen["VisitasUnicas"]
        ).all(),
        "CheckOutValidos <= VisitasUnicas": (
            resumen["CheckOutValidos"] <= resumen["VisitasUnicas"]
        ).all(),
        "VisitasValidas <= CheckInValidos": (
            resumen["VisitasValidas"] <= resumen["CheckInValidos"]
        ).all(),
        "VisitasValidas <= CheckOutValidos": (
            resumen["VisitasValidas"] <= resumen["CheckOutValidos"]
        ).all(),
    }
    fallidos = [nombre for nombre, valido in controles.items() if not valido]
    if fallidos:
        raise AssertionError(
            f"Fallaron controles internos de BUSINESS RULES CHECKIN: {fallidos}."
        )

    return (
        resumen[COLUMNAS_RESUMEN]
        .sort_values(
            ["SUP", "CodVend"],
            kind="stable",
            na_position="last",
        )
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner=False)
def obtener_business_rules_checkin(
    fecha_desde: Optional[pd.Timestamp] = None,
    fecha_hasta: Optional[pd.Timestamp] = None,
) -> dict[str, pd.DataFrame]:
    """
    Obtiene las dos salidas reutilizables del dominio CHECKIN:
    - detalle_visitas: una fila por visita, clasificada respecto de la ruta;
    - resumen_vendedores: una fila por vendedor del maestro.
    """
    t0 = time.perf_counter()

    core_checkin = obtener_core_checkin()
    core_rutas = obtener_core_rutas()
    maestros = obtener_staging_maestros()

    detalle = construir_detalle_checkin_ruta(
        core_checkin,
        core_rutas,
        fecha_desde,
        fecha_hasta,
    )
    resumen = construir_resumen_checkin_vendedores(
        core_checkin,
        core_rutas,
        maestros,
        fecha_desde,
        fecha_hasta,
    )

    print(
        f"[PERF_BR] obtener_business_rules_checkin -> "
        f"{time.perf_counter() - t0:.4f} s | "
        f"visitas={len(detalle)} | vendedores={len(resumen)}"
    )

    return {
        "detalle_visitas": detalle,
        "resumen_vendedores": resumen,
    }
