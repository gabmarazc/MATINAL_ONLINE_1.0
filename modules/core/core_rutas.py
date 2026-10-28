# modules/core/core_rutas.py
"""
CORE operativo de RUTAS para MATINAL ONLINE.

Arquitectura:
    SQLite.rutas -> STAGING_RUTAS -> CORE_RUTAS

Entidad institucional:
    programación operativa de visita de un cliente por un vendedor en una fecha.

Contrato real de STAGING_RUTAS auditado:
    Fecha
    Codigo
    Razon_Social
    codven

Granularidad CORE:
    una fila única por Cliente + CodVendedor + FechaRuta.

Esta capa:
- consume exclusivamente STAGING_RUTAS;
- interpreta los nombres físicos de RUTAS en un contrato operativo estable;
- tipa cliente, vendedor y fecha;
- conserva el nombre del cliente informado por RUTAS;
- consolida duplicados técnicos de la misma asignación;
- valida contradicciones antes de consolidar.

Esta capa NO:
- lee Excel ni SQLite directamente;
- persiste datos;
- cruza con CHKIN, VTA, Universo ni maestros;
- determina visitas realizadas, válidas, en ruta o fuera de ruta;
- calcula KPI, objetivos, porcentajes ni métricas de reporte;
- filtra vendedores, clientes, fechas o periodos.
"""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from modules.staging import obtener_staging_rutas


COLUMNAS_STAGING_RUTAS = [
    "Fecha",
    "Codigo",
    "Razon_Social",
    "codven",
]

COLUMNAS_CORE_RUTAS = [
    "Cliente",
    "NombreClienteRuta",
    "CodVendedor",
    "FechaRuta",
]

CLAVE_CORE_RUTAS = ["Cliente", "CodVendedor", "FechaRuta"]


def _dataframe_core_rutas_vacio() -> pd.DataFrame:
    """Devuelve el contrato vacío de CORE_RUTAS con tipos estables."""
    return pd.DataFrame(
        {
            "Cliente": pd.Series(dtype="Int64"),
            "NombreClienteRuta": pd.Series(dtype="string"),
            "CodVendedor": pd.Series(dtype="Int64"),
            "FechaRuta": pd.Series(dtype="datetime64[ns]"),
        }
    )[COLUMNAS_CORE_RUTAS]


def _normalizar_texto_nullable(serie: pd.Series) -> pd.Series:
    """Normaliza texto descriptivo sin aplicar reglas comerciales."""
    salida = serie.astype("string").str.strip()
    return salida.mask(
        salida.isna() | salida.str.upper().isin(["", "NAN", "NONE", "NAT", "<NA>"]),
        pd.NA,
    )


def _validar_contrato_staging(df_staging: pd.DataFrame) -> None:
    """Valida el contrato físico real auditado de STAGING_RUTAS."""
    faltantes = [
        columna
        for columna in COLUMNAS_STAGING_RUTAS
        if columna not in df_staging.columns
    ]
    if faltantes:
        raise ValueError(
            "STAGING_RUTAS no cumple el contrato real auditado. "
            f"Columnas faltantes: {faltantes}. "
            f"Esperadas: {COLUMNAS_STAGING_RUTAS}."
        )


def construir_core_rutas(df_staging: pd.DataFrame) -> pd.DataFrame:
    """
    Construye CORE_RUTAS desde STAGING_RUTAS.

    Mapeo institucional confirmado por auditoría:
        Codigo       -> Cliente
        Razon_Social -> NombreClienteRuta
        codven       -> CodVendedor
        Fecha        -> FechaRuta

    La clave operativa es:
        Cliente + CodVendedor + FechaRuta
    """
    if not isinstance(df_staging, pd.DataFrame):
        raise TypeError(
            "construir_core_rutas requiere un pandas.DataFrame de STAGING_RUTAS."
        )

    if df_staging.empty:
        return _dataframe_core_rutas_vacio()

    _validar_contrato_staging(df_staging)

    cliente = pd.to_numeric(df_staging["Codigo"], errors="coerce").astype("Int64")
    cod_vendedor = pd.to_numeric(df_staging["codven"], errors="coerce").astype("Int64")
    # Contrato auditado: Fecha llega uniformemente como texto ISO AAAA-MM-DD.
    # El formato explicito evita la inferencia dayfirst y la conversion erronea a NaT.
    fecha_ruta = pd.to_datetime(
        df_staging["Fecha"].astype("string").str.strip(),
        format="%Y-%m-%d",
        errors="coerce",
    ).dt.normalize()
    nombre_cliente = _normalizar_texto_nullable(df_staging["Razon_Social"])

    core = pd.DataFrame(
        {
            "Cliente": cliente,
            "NombreClienteRuta": nombre_cliente,
            "CodVendedor": cod_vendedor,
            "FechaRuta": fecha_ruta,
        },
        index=df_staging.index,
    )

    clave_incompleta = core[CLAVE_CORE_RUTAS].isna().any(axis=1)
    if clave_incompleta.any():
        muestra = core.loc[clave_incompleta, CLAVE_CORE_RUTAS].head(10)
        raise ValueError(
            "STAGING_RUTAS contiene asignaciones sin la clave operativa completa "
            "(Cliente + CodVendedor + FechaRuta). "
            f"Filas afectadas: {int(clave_incompleta.sum())}. "
            f"Muestra: {muestra.to_dict('records')}."
        )

    # Una clave duplicada puede ser un duplicado técnico. Antes de consolidarla,
    # se verifica que no asigne nombres de cliente contradictorios a la misma
    # combinación Cliente + CodVendedor + FechaRuta.
    duplicadas = core.duplicated(subset=CLAVE_CORE_RUTAS, keep=False)
    if duplicadas.any():
        grupos = core.loc[duplicadas].groupby(
            CLAVE_CORE_RUTAS,
            dropna=False,
            sort=False,
        )
        conflictos = []
        for clave, grupo in grupos:
            nombres = grupo["NombreClienteRuta"].dropna().unique()
            if len(nombres) > 1:
                conflictos.append(
                    {
                        "clave": clave,
                        "NombreClienteRuta": nombres.tolist(),
                    }
                )
                if len(conflictos) >= 10:
                    break

        if conflictos:
            raise ValueError(
                "STAGING_RUTAS contiene claves duplicadas con nombres de cliente "
                f"contradictorios. Muestra: {conflictos}."
            )

    core = (
        core.sort_values(CLAVE_CORE_RUTAS, kind="stable")
        .drop_duplicates(subset=CLAVE_CORE_RUTAS, keep="first")
        .reset_index(drop=True)
    )

    duplicadas_finales = core.duplicated(
        subset=CLAVE_CORE_RUTAS,
        keep=False,
    )
    if duplicadas_finales.any():
        raise AssertionError(
            "CORE_RUTAS no logró garantizar la unicidad de "
            "Cliente + CodVendedor + FechaRuta."
        )

    return core[COLUMNAS_CORE_RUTAS]


@st.cache_data(show_spinner=False)
def obtener_core_rutas() -> pd.DataFrame:
    """
    Obtiene CORE_RUTAS completo desde STAGING_RUTAS.

    No recibe filtros. Los recortes por vendedor, fecha o periodo corresponden
    a BUSINESS RULES o REPORTES.
    """
    t0 = time.perf_counter()
    df_staging = obtener_staging_rutas()
    core = construir_core_rutas(df_staging)
    print(
        f"[PERF_CORE] obtener_core_rutas -> "
        f"{time.perf_counter() - t0:.4f} s | filas={len(core)}"
    )
    return core
