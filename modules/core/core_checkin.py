# modules/core_checkin.py
"""
CORE operativo de CHECK-IN para MATINAL ONLINE.

Arquitectura:
    SQLite.chkin -> STAGING_CHKIN -> CORE_CHECKIN

Responsabilidad de esta capa:
- interpretar cada fila de STAGING como un evento operativo de visita;
- separar fecha y hora de check-in/check-out sin perder los timestamps originales;
- determinar si check-in y check-out fueron realizados correctamente en el PDV;
- determinar la validez operativa de la visita;
- conservar independientemente el tiempo informado en el PDV;
- exponer una entidad reutilizable, sin filtros comerciales, KPI ni presentación.

Esta capa NO:
- lee Excel ni SQLite directamente;
- persiste datos;
- filtra supervisores, vendedores, fechas o periodos;
- cruza todavía con Rutas, VTA, Universo u otras entidades;
- calcula objetivos, porcentajes, rankings o KPI de reporte.
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st

from modules.staging import obtener_staging_chkin


COLUMNAS_STAGING_REQUERIDAS = [
    "Codigo Cliente",
    "Cliente",
    "Codigo Empleado",
    "Supervisor",
    "Coordenadas Check-in",
    "Coordenadas Check-out",
    "Fecha Check-in",
    "Fecha Check-out",
    "Motivo Invalidez Check-in",
    "Motivo Invalidez Check-out",
    "Existe Carga",
    "Tiempo en PDV",
    "Valido",
]

COLUMNAS_CORE_CHECKIN = [
    "Cliente",
    "NombreClienteCHKIN",
    "CodVendedorCHKIN",
    "SupervisorCHKIN",
    "FechaHoraCheckIn",
    "FechaHoraCheckOut",
    "FechaVisita",
    "HoraCheckIn",
    "HoraCheckOut",
    "CoordenadasCheckIn",
    "CoordenadasCheckOut",
    "MotivoInvalidezCheckIn",
    "MotivoInvalidezCheckOut",
    "CheckInCorrecto",
    "CheckOutCorrecto",
    "VisitaValidaCalculada",
    "ValidoOrigen",
    "CoincideValidezOrigen",
    "ExisteCarga",
    "TiempoPDV",
    "TiempoPDVSegundos",
]


def _dataframe_core_vacio() -> pd.DataFrame:
    """Devuelve el contrato vacío de CORE_CHECKIN con tipos estables."""
    return pd.DataFrame(
        {
            "Cliente": pd.Series(dtype="Int64"),
            "NombreClienteCHKIN": pd.Series(dtype="string"),
            "CodVendedorCHKIN": pd.Series(dtype="string"),
            "SupervisorCHKIN": pd.Series(dtype="string"),
            "FechaHoraCheckIn": pd.Series(dtype="datetime64[ns]"),
            "FechaHoraCheckOut": pd.Series(dtype="datetime64[ns]"),
            "FechaVisita": pd.Series(dtype="datetime64[ns]"),
            "HoraCheckIn": pd.Series(dtype="object"),
            "HoraCheckOut": pd.Series(dtype="object"),
            "CoordenadasCheckIn": pd.Series(dtype="string"),
            "CoordenadasCheckOut": pd.Series(dtype="string"),
            "MotivoInvalidezCheckIn": pd.Series(dtype="string"),
            "MotivoInvalidezCheckOut": pd.Series(dtype="string"),
            "CheckInCorrecto": pd.Series(dtype="boolean"),
            "CheckOutCorrecto": pd.Series(dtype="boolean"),
            "VisitaValidaCalculada": pd.Series(dtype="boolean"),
            "ValidoOrigen": pd.Series(dtype="string"),
            "CoincideValidezOrigen": pd.Series(dtype="boolean"),
            "ExisteCarga": pd.Series(dtype="string"),
            "TiempoPDV": pd.Series(dtype="timedelta64[ns]"),
            "TiempoPDVSegundos": pd.Series(dtype="Float64"),
        }
    )[COLUMNAS_CORE_CHECKIN]


def _normalizar_texto_nullable(serie: pd.Series) -> pd.Series:
    """Normalización defensiva de texto sin interpretar reglas de negocio."""
    resultado = serie.astype("string").str.strip()
    return resultado.mask(
        resultado.isna()
        | resultado.str.upper().isin(["", "NAN", "NONE", "NAT", "<NA>"]),
        pd.NA,
    )


def _validar_contrato_staging(df: pd.DataFrame) -> None:
    """Valida el contrato mínimo exigido a STAGING_CHKIN."""
    faltantes = [col for col in COLUMNAS_STAGING_REQUERIDAS if col not in df.columns]
    if faltantes:
        raise ValueError(
            "STAGING_CHKIN no cumple el contrato requerido por CORE_CHECKIN. "
            f"Columnas faltantes: {faltantes}."
        )

    claves_nulas = df["Codigo Cliente"].isna() | df["Fecha Check-in"].isna()
    if claves_nulas.any():
        raise ValueError(
            "STAGING_CHKIN contiene filas sin la KEY institucional completa "
            "(Codigo Cliente + Fecha Check-in). "
            f"Filas afectadas: {int(claves_nulas.sum())}."
        )

    duplicadas = df.duplicated(subset=["Codigo Cliente", "Fecha Check-in"], keep=False)
    if duplicadas.any():
        muestra = df.loc[duplicadas, ["Codigo Cliente", "Fecha Check-in"]].head(10)
        raise ValueError(
            "STAGING_CHKIN contiene KEY duplicadas. "
            f"Filas afectadas: {int(duplicadas.sum())}. "
            f"Muestra: {muestra.to_dict('records')}."
        )


def construir_core_checkin(df_staging: pd.DataFrame) -> pd.DataFrame:
    """
    Construye la entidad operativa reutilizable de visitas CHKIN.

    Regla funcional confirmada:
    - CheckInCorrecto = Motivo Invalidez Check-in vacío/nulo.
    - CheckOutCorrecto = Motivo Invalidez Check-out vacío/nulo.
    - VisitaValidaCalculada = CheckInCorrecto AND CheckOutCorrecto.
    - TiempoPDV se conserva independientemente de la validez.

    ValidoOrigen se conserva para control contra la regla calculada, pero no se
    utiliza para construir VisitaValidaCalculada.
    """
    if not isinstance(df_staging, pd.DataFrame):
        raise TypeError(
            "construir_core_checkin requiere un pandas.DataFrame de STAGING_CHKIN."
        )

    if df_staging.empty:
        return _dataframe_core_vacio()

    _validar_contrato_staging(df_staging)
    base = df_staging[COLUMNAS_STAGING_REQUERIDAS].copy()

    fecha_hora_checkin = pd.to_datetime(base["Fecha Check-in"], errors="coerce")
    fecha_hora_checkout = pd.to_datetime(base["Fecha Check-out"], errors="coerce")
    tiempo_pdv = pd.to_timedelta(base["Tiempo en PDV"], errors="coerce")

    if fecha_hora_checkin.isna().any():
        raise ValueError(
            "STAGING_CHKIN contiene Fecha Check-in no interpretable. "
            f"Filas afectadas: {int(fecha_hora_checkin.isna().sum())}."
        )

    motivo_checkin = _normalizar_texto_nullable(base["Motivo Invalidez Check-in"])
    motivo_checkout = _normalizar_texto_nullable(base["Motivo Invalidez Check-out"])
    valido_origen = _normalizar_texto_nullable(base["Valido"]).str.upper()
    existe_carga = _normalizar_texto_nullable(base["Existe Carga"]).str.upper()

    checkin_correcto = motivo_checkin.isna().astype("boolean")
    checkout_correcto = motivo_checkout.isna().astype("boolean")
    visita_valida = (checkin_correcto & checkout_correcto).astype("boolean")

    valido_origen_bool = valido_origen.map({"SI": True, "NO": False}).astype("boolean")
    coincide_validez = (
        valido_origen_bool.notna() & valido_origen_bool.eq(visita_valida)
    ).astype("boolean")

    core = pd.DataFrame(
        {
            "Cliente": pd.to_numeric(base["Codigo Cliente"], errors="coerce").astype(
                "Int64"
            ),
            "NombreClienteCHKIN": _normalizar_texto_nullable(base["Cliente"]),
            "CodVendedorCHKIN": _normalizar_texto_nullable(base["Codigo Empleado"]),
            "SupervisorCHKIN": _normalizar_texto_nullable(base["Supervisor"]),
            "FechaHoraCheckIn": fecha_hora_checkin,
            "FechaHoraCheckOut": fecha_hora_checkout,
            "FechaVisita": fecha_hora_checkin.dt.normalize(),
            "HoraCheckIn": fecha_hora_checkin.dt.time,
            "HoraCheckOut": fecha_hora_checkout.dt.time,
            "CoordenadasCheckIn": _normalizar_texto_nullable(
                base["Coordenadas Check-in"]
            ),
            "CoordenadasCheckOut": _normalizar_texto_nullable(
                base["Coordenadas Check-out"]
            ),
            "MotivoInvalidezCheckIn": motivo_checkin,
            "MotivoInvalidezCheckOut": motivo_checkout,
            "CheckInCorrecto": checkin_correcto,
            "CheckOutCorrecto": checkout_correcto,
            "VisitaValidaCalculada": visita_valida,
            "ValidoOrigen": valido_origen,
            "CoincideValidezOrigen": coincide_validez,
            "ExisteCarga": existe_carga,
            "TiempoPDV": tiempo_pdv,
            "TiempoPDVSegundos": pd.Series(
                np.where(tiempo_pdv.notna(), tiempo_pdv.dt.total_seconds(), np.nan),
                index=base.index,
                dtype="Float64",
            ),
        },
        index=base.index,
    )

    return core[COLUMNAS_CORE_CHECKIN].reset_index(drop=True)


@st.cache_data(show_spinner=False)
def obtener_core_checkin() -> pd.DataFrame:
    """
    Obtiene CORE_CHECKIN a partir del STAGING productivo.

    La función no recibe filtros para mantener el CORE completo y reutilizable.
    Los recortes temporales, comerciales o visuales corresponden a capas
    posteriores.
    """
    t0 = time.perf_counter()
    df_staging = obtener_staging_chkin()
    core = construir_core_checkin(df_staging)

    print(
        f"[PERF_CORE] obtener_core_checkin -> "
        f"{time.perf_counter() - t0:.4f} s | filas={len(core)}"
    )
    return core
