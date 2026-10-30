# modules/business_rules/business_rules_sugerido_mesa.py
"""
Motor analitico de SUGERIDO MESA para COMPROMISOS.

Arquitectura:
    CORE_CLIENTES + CORE_VENTAS_BASE -> BUSINESS_RULES_SUGERIDO_MESA

Principios institucionales:
- CORE_CLIENTES determina la cartera actual Cliente -> CodVendedor.
- La historia de ventas pertenece al cliente, no al vendedor historico.
- El sugerido solo se calcula para clientes de la cartera actual cuyo DiaVisita
  coincide con el Dia Matinal.
- La historia utiliza exclusivamente compras positivas de los tres meses
  anteriores al Dia Matinal.
- La unidad analitica es Cliente x Segmento.
- Los segmentos iniciales son PLAT_GOLD y SILVER_BRZ.
- El patron principal buscado es LLENADO_REPOSICION, pero no se impone.
- Si existe otro patron, se identifica y se aplica un modelo compatible.
- Esta capa no lee SQLite, Excel, RAW ni STAGING directamente.
- Esta capa no renderiza Streamlit ni modifica COMPROMISOS.
"""

from __future__ import annotations

import math
import time
import unicodedata
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd
import streamlit as st

from modules.core.core_clientes import obtener_core_clientes
from modules.core.core_ventas_base import obtener_core_ventas_base


# =============================================================================
# CONTRATOS Y CONSTANTES
# =============================================================================

SEGMENTOS_SUGERIDO = ("PLAT_GOLD", "SILVER_BRZ")

TIPOS_VENTA_EXCLUIDOS = {
    "COMODATO DEVOLUCION",
    "COMODATO FICTICIO",
    "COMODATO FICTICIO DEVOLUCION",
    "COMODATO PRESTAMO",
}

MAPEO_DIA_SEMANA = {
    0: "LUNES",
    1: "MARTES",
    2: "MIERCOLES",
    3: "JUEVES",
    4: "VIERNES",
    5: "SABADO",
    6: "DOMINGO",
}

PATRON_LLENADO_REPOSICION = "LLENADO_REPOSICION"
PATRON_ESTABLE = "ESTABLE"
PATRON_TENDENCIA_CRECIENTE = "TENDENCIA_CRECIENTE"
PATRON_TENDENCIA_DECRECIENTE = "TENDENCIA_DECRECIENTE"
PATRON_ERRATICO = "ERRATICO"
PATRON_HISTORIA_INSUFICIENTE = "HISTORIA_INSUFICIENTE"
PATRON_SIN_HISTORIA = "SIN_HISTORIA"

MODELO_ALTERNANCIA = "ALTERNANCIA_LLENADO_REPOSICION"
MODELO_MEDIANA = "MEDIANA"
MODELO_PROMEDIO = "PROMEDIO"
MODELO_PENULTIMA = "PENULTIMA_COMPRA"
MODELO_PONDERADO_PENULTIMA = "PONDERADO_PENULTIMA"
MODELO_PONDERADO_RECIENTE = "PONDERADO_RECIENTE"
MODELO_TENDENCIA = "TENDENCIA_CONTROLADA"
MODELO_UNICA_COMPRA = "UNICA_COMPRA"
MODELO_DOS_COMPRAS = "PROMEDIO_DOS_COMPRAS"
MODELO_SIN_HISTORIA = "SIN_HISTORIA"

COLUMNAS_DETALLE = [
    "DiaMatinal",
    "Cliente",
    "NombreCliente",
    "CodVendedor",
    "Ruta",
    "DiaVisita",
    "Segmento",
    "CantidadCompras3M",
    "PrimeraCompraFecha",
    "UltimaCompraFecha",
    "UltimaCompraKg",
    "PenultimaCompraKg",
    "MediaKg",
    "MedianaKg",
    "DesvioKg",
    "CoeficienteVariacion",
    "PendienteTendencia",
    "ProporcionAlternancia",
    "PromedioNivelAlto",
    "PromedioNivelBajo",
    "RelacionAltoBajo",
    "PatronDetectado",
    "FaseUltimaCompra",
    "FaseProximaEsperada",
    "ModeloSeleccionado",
    "ErrorHistoricoMAE",
    "NivelConfianza",
    "SugeridoKgCliente",
]

COLUMNAS_RESUMEN = [
    "DiaMatinal",
    "CodVendedor",
    "ClientesRuta",
    "Sugerido_PLAT_GOLD",
    "Sugerido_SILVER_BRZ",
    "ClientesConHistoria_PLAT_GOLD",
    "ClientesConHistoria_SILVER_BRZ",
    "ClientesSinHistoria_PLAT_GOLD",
    "ClientesSinHistoria_SILVER_BRZ",
    "Confianza_PLAT_GOLD",
    "Confianza_SILVER_BRZ",
]


class BusinessRulesSugeridoMesaError(RuntimeError):
    """Error de contrato o integridad del motor Sugerido Mesa."""


@dataclass(frozen=True)
class ConfiguracionSugeridoMesa:
    """Parametros controlados de clasificacion y modelado."""

    meses_historia: int = 3
    minimo_compras_clasificacion: int = 4
    minimo_compras_backtesting: int = 5
    cv_estable_max: float = 0.25
    proporcion_alternancia_min: float = 0.75
    relacion_alto_bajo_min: float = 1.50
    correlacion_alternancia_max: float = -0.30
    tendencia_relativa_min: float = 0.08
    recorte_tendencia_inferior: float = 0.50
    recorte_tendencia_superior: float = 1.50


CONFIG_DEFAULT = ConfiguracionSugeridoMesa()


# =============================================================================
# UTILIDADES DE NORMALIZACION Y CONTRATO
# =============================================================================


def _normalizar_texto(valor) -> str:
    if valor is None or pd.isna(valor):
        return ""
    texto = str(valor).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split())


def _normalizar_serie_texto(serie: pd.Series) -> pd.Series:
    return serie.map(_normalizar_texto).astype("string")


def _normalizar_fecha_unica(valor, nombre: str) -> pd.Timestamp:
    fecha = pd.to_datetime(valor, errors="coerce", dayfirst=True)
    if pd.isna(fecha):
        raise BusinessRulesSugeridoMesaError(
            f"No se pudo interpretar {nombre}: {valor!r}."
        )
    return pd.Timestamp(fecha).normalize()


def _validar_columnas(df: pd.DataFrame, requeridas: list[str], origen: str) -> None:
    faltantes = [col for col in requeridas if col not in df.columns]
    if faltantes:
        raise BusinessRulesSugeridoMesaError(
            f"{origen} no cumple el contrato requerido. Faltan: {faltantes}."
        )


def _resolver_columna(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    for candidato in candidatos:
        if candidato in df.columns:
            return candidato
    return None


def _dataframe_detalle_vacio() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNAS_DETALLE)


def _dataframe_resumen_vacio() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNAS_RESUMEN)


# =============================================================================
# CARTERA ACTUAL DEL DIA MATINAL
# =============================================================================


def _obtener_nombre_cliente(df: pd.DataFrame) -> pd.Series:
    columna = _resolver_columna(
        df,
        ["NombreCliente", "Razon_Social", "RazonSocial", "NombreClienteRuta"],
    )
    if columna is None:
        return pd.Series("", index=df.index, dtype="string")
    return df[columna].astype("string").fillna("").str.strip()


def obtener_cartera_dia_matinal(
    dia_matinal,
    core_clientes: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Devuelve la cartera actual que corresponde gestionar en el Dia Matinal.

    La apropiacion Cliente -> CodVendedor proviene exclusivamente de
    CORE_CLIENTES. No se utiliza el vendedor historico de VTA ni el vendedor
    historico de CORE_RUTAS.
    """
    fecha_matinal = _normalizar_fecha_unica(dia_matinal, "dia_matinal")
    clientes = (
        obtener_core_clientes() if core_clientes is None else core_clientes.copy()
    )

    if clientes is None or clientes.empty:
        return pd.DataFrame(
            columns=[
                "DiaMatinal",
                "Cliente",
                "NombreCliente",
                "CodVendedor",
                "Ruta",
                "DiaVisita",
            ]
        )

    _validar_columnas(
        clientes,
        ["Cliente", "CodVendedor", "DiaVisita"],
        "CORE_CLIENTES",
    )

    trabajo = clientes.copy()
    trabajo["Cliente"] = pd.to_numeric(trabajo["Cliente"], errors="coerce").astype(
        "Int64"
    )
    trabajo["CodVendedor"] = pd.to_numeric(
        trabajo["CodVendedor"], errors="coerce"
    ).astype("Int64")
    trabajo["DiaVisitaNormalizado"] = _normalizar_serie_texto(trabajo["DiaVisita"])
    dia_objetivo = MAPEO_DIA_SEMANA[int(fecha_matinal.weekday())]

    trabajo = trabajo.loc[
        trabajo["Cliente"].notna()
        & trabajo["CodVendedor"].notna()
        & trabajo["DiaVisitaNormalizado"].eq(dia_objetivo)
    ].copy()

    if trabajo.empty:
        return pd.DataFrame(
            columns=[
                "DiaMatinal",
                "Cliente",
                "NombreCliente",
                "CodVendedor",
                "Ruta",
                "DiaVisita",
            ]
        )

    contradicciones = (
        trabajo.groupby("Cliente", dropna=False)["CodVendedor"]
        .nunique(dropna=True)
        .loc[lambda x: x.gt(1)]
    )
    if not contradicciones.empty:
        raise BusinessRulesSugeridoMesaError(
            "CORE_CLIENTES contiene clientes con mas de un propietario actual "
            f"para el Dia Matinal. Clientes={contradicciones.index.tolist()[:20]}."
        )

    trabajo["NombreCliente"] = _obtener_nombre_cliente(trabajo)
    if "Ruta" not in trabajo.columns:
        trabajo["Ruta"] = pd.NA

    trabajo["DiaMatinal"] = fecha_matinal
    resultado = trabajo[
        [
            "DiaMatinal",
            "Cliente",
            "NombreCliente",
            "CodVendedor",
            "Ruta",
            "DiaVisita",
        ]
    ].copy()

    resultado = (
        resultado.sort_values(["CodVendedor", "Cliente"], kind="stable")
        .drop_duplicates(subset=["Cliente"], keep="first")
        .reset_index(drop=True)
    )
    return resultado


# =============================================================================
# HISTORIA POSITIVA DE COMPRAS
# =============================================================================


def _asegurar_segmento_comercial(df: pd.DataFrame) -> pd.DataFrame:
    trabajo = df.copy()

    if "SEGMENTO" in trabajo.columns and trabajo["SEGMENTO"].notna().any():
        segmento_origen = _normalizar_serie_texto(trabajo["SEGMENTO"])
    else:
        col_rent = _resolver_columna(
            trabajo,
            ["SegmentoRentabilidad", "SEGMENTORENTABILIDAD"],
        )
        col_rubro = _resolver_columna(trabajo, ["Rubro", "RUBRO"])
        if col_rent is None or col_rubro is None:
            raise BusinessRulesSugeridoMesaError(
                "CORE_VENTAS_BASE no permite construir SEGMENTO. Se requieren "
                "SEGMENTO o SegmentoRentabilidad + Rubro."
            )
        segmento_origen = (
            _normalizar_serie_texto(trabajo[col_rent])
            + " "
            + _normalizar_serie_texto(trabajo[col_rubro])
        ).str.strip()

    mapeo = {
        "PLATINUM SALTY": "PLAT_GOLD",
        "PLATINUM CRAKERS": "PLAT_GOLD",
        "PLATINUM CRACKERS": "PLAT_GOLD",
        "GOLD SALTY": "PLAT_GOLD",
        "GOLD CRAKERS": "PLAT_GOLD",
        "GOLD CRACKERS": "PLAT_GOLD",
        "PLAT_GOLD": "PLAT_GOLD",
        "PLAT_GOLD SALTY": "PLAT_GOLD",
        "PLAT_GOLD CRAKERS": "PLAT_GOLD",
        "PLAT_GOLD CRACKERS": "PLAT_GOLD",
        "SILVER SALTY": "SILVER_BRZ",
        "SILVER CRAKERS": "SILVER_BRZ",
        "SILVER CRACKERS": "SILVER_BRZ",
        "SILVER CEREALS": "SILVER_BRZ",
        "BRONZE SALTY": "SILVER_BRZ",
        "BRONZE CRAKERS": "SILVER_BRZ",
        "BRONZE CRACKERS": "SILVER_BRZ",
        "BRONZE CEREALS": "SILVER_BRZ",
        "SILVER_BRZ": "SILVER_BRZ",
        "SILVER_BRZ SALTY": "SILVER_BRZ",
        "SILVER_BRZ CRAKERS": "SILVER_BRZ",
        "SILVER_BRZ CRACKERS": "SILVER_BRZ",
        "SILVER_BRZ CEREALS": "SILVER_BRZ",
    }
    trabajo["Segmento"] = segmento_origen.map(mapeo).astype("string")
    return trabajo


def _filtrar_universo_ventas(df: pd.DataFrame) -> pd.DataFrame:
    trabajo = df.copy()

    if "Proveedor" in trabajo.columns:
        proveedor = _normalizar_serie_texto(trabajo["Proveedor"])
        trabajo = trabajo.loc[proveedor.str.contains("PEPSICO", na=False)].copy()

    if "TipoDeVenta" in trabajo.columns:
        tipo = _normalizar_serie_texto(trabajo["TipoDeVenta"])
        trabajo = trabajo.loc[~tipo.isin(TIPOS_VENTA_EXCLUIDOS)].copy()

    return trabajo


def preparar_historia_compras_positivas(
    cartera_dia: pd.DataFrame,
    dia_matinal,
    core_ventas: pd.DataFrame | None = None,
    configuracion: ConfiguracionSugeridoMesa = CONFIG_DEFAULT,
) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    """
    Construye compras positivas agregadas por Cliente x FechaCompra x Segmento.

    La historia se filtra por Cliente, no por vendedor historico. De este modo,
    un cambio de cartera no elimina el comportamiento previo del cliente.
    """
    fecha_matinal = _normalizar_fecha_unica(dia_matinal, "dia_matinal")
    fecha_desde = fecha_matinal - pd.DateOffset(months=configuracion.meses_historia)
    fecha_hasta = fecha_matinal - pd.Timedelta(days=1)

    if cartera_dia is None or cartera_dia.empty:
        return (
            pd.DataFrame(columns=["Cliente", "FechaCompra", "Segmento", "KgCompra"]),
            fecha_desde,
            fecha_hasta,
        )

    ventas = obtener_core_ventas_base() if core_ventas is None else core_ventas.copy()
    if ventas is None or ventas.empty:
        return (
            pd.DataFrame(columns=["Cliente", "FechaCompra", "Segmento", "KgCompra"]),
            fecha_desde,
            fecha_hasta,
        )

    _validar_columnas(
        ventas,
        ["Cliente", "PesoKg", "FechaCarga_dt"],
        "CORE_VENTAS_BASE",
    )

    trabajo = ventas.copy()
    trabajo["Cliente"] = pd.to_numeric(trabajo["Cliente"], errors="coerce").astype(
        "Int64"
    )
    trabajo["PesoKg"] = pd.to_numeric(trabajo["PesoKg"], errors="coerce").fillna(0.0)
    trabajo["FechaCompra"] = pd.to_datetime(
        trabajo["FechaCarga_dt"], errors="coerce"
    ).dt.normalize()

    clientes_dia = set(cartera_dia["Cliente"].dropna().astype("Int64").tolist())
    trabajo = trabajo.loc[
        trabajo["Cliente"].isin(clientes_dia)
        & trabajo["FechaCompra"].between(fecha_desde, fecha_hasta, inclusive="both")
    ].copy()

    trabajo = _filtrar_universo_ventas(trabajo)
    trabajo = _asegurar_segmento_comercial(trabajo)
    trabajo = trabajo.loc[
        trabajo["Segmento"].isin(SEGMENTOS_SUGERIDO) & trabajo["PesoKg"].gt(0)
    ].copy()

    if trabajo.empty:
        return (
            pd.DataFrame(columns=["Cliente", "FechaCompra", "Segmento", "KgCompra"]),
            fecha_desde,
            fecha_hasta,
        )

    historia = (
        trabajo.groupby(
            ["Cliente", "FechaCompra", "Segmento"],
            as_index=False,
            dropna=False,
        )["PesoKg"]
        .sum()
        .rename(columns={"PesoKg": "KgCompra"})
    )
    historia = historia.loc[historia["KgCompra"].gt(0)].copy()
    historia = historia.sort_values(
        ["Cliente", "Segmento", "FechaCompra"], kind="stable"
    ).reset_index(drop=True)
    return historia, fecha_desde, fecha_hasta


# =============================================================================
# CARACTERISTICAS Y DETECCION DE PATRONES
# =============================================================================


def _pendiente_lineal(valores: np.ndarray) -> float:
    if len(valores) < 2:
        return 0.0
    x = np.arange(len(valores), dtype=float)
    return float(np.polyfit(x, valores.astype(float), 1)[0])


def _alternancias(valores: np.ndarray) -> tuple[float, float]:
    """Devuelve proporcion de alternancia y correlacion lag-1."""
    if len(valores) < 3:
        return 0.0, 0.0

    dif = np.diff(valores.astype(float))
    signos = np.sign(dif)
    signos = signos[signos != 0]
    if len(signos) < 2:
        proporcion = 0.0
    else:
        proporcion = float(np.mean(signos[1:] != signos[:-1]))

    x = valores[:-1].astype(float)
    y = valores[1:].astype(float)
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        correlacion = 0.0
    else:
        correlacion = float(np.corrcoef(x, y)[0, 1])
        if not np.isfinite(correlacion):
            correlacion = 0.0
    return proporcion, correlacion


def _niveles_alto_bajo(valores: np.ndarray) -> tuple[float, float, float]:
    if len(valores) == 0:
        return 0.0, 0.0, 0.0
    mediana = float(np.median(valores))
    altos = valores[valores > mediana]
    bajos = valores[valores <= mediana]
    promedio_alto = float(np.mean(altos)) if len(altos) else mediana
    promedio_bajo = float(np.mean(bajos)) if len(bajos) else mediana
    relacion = promedio_alto / promedio_bajo if promedio_bajo > 0 else 0.0
    return promedio_alto, promedio_bajo, float(relacion)


def extraer_caracteristicas_patron(valores: np.ndarray) -> dict:
    valores = np.asarray(valores, dtype=float)
    valores = valores[np.isfinite(valores) & (valores > 0)]

    if len(valores) == 0:
        return {
            "cantidad": 0,
            "ultima": 0.0,
            "penultima": 0.0,
            "media": 0.0,
            "mediana": 0.0,
            "desvio": 0.0,
            "cv": 0.0,
            "pendiente": 0.0,
            "pendiente_relativa": 0.0,
            "proporcion_alternancia": 0.0,
            "correlacion_lag1": 0.0,
            "promedio_alto": 0.0,
            "promedio_bajo": 0.0,
            "relacion_alto_bajo": 0.0,
        }

    media = float(np.mean(valores))
    mediana = float(np.median(valores))
    desvio = float(np.std(valores, ddof=1)) if len(valores) > 1 else 0.0
    cv = desvio / media if media > 0 else 0.0
    pendiente = _pendiente_lineal(valores)
    pendiente_relativa = pendiente / media if media > 0 else 0.0
    proporcion, correlacion = _alternancias(valores)
    promedio_alto, promedio_bajo, relacion = _niveles_alto_bajo(valores)

    return {
        "cantidad": int(len(valores)),
        "ultima": float(valores[-1]),
        "penultima": float(valores[-2]) if len(valores) >= 2 else 0.0,
        "media": media,
        "mediana": mediana,
        "desvio": desvio,
        "cv": float(cv),
        "pendiente": pendiente,
        "pendiente_relativa": float(pendiente_relativa),
        "proporcion_alternancia": proporcion,
        "correlacion_lag1": correlacion,
        "promedio_alto": promedio_alto,
        "promedio_bajo": promedio_bajo,
        "relacion_alto_bajo": relacion,
    }


def detectar_patron_compra(
    caracteristicas: dict,
    configuracion: ConfiguracionSugeridoMesa = CONFIG_DEFAULT,
) -> str:
    n = int(caracteristicas["cantidad"])
    if n == 0:
        return PATRON_SIN_HISTORIA
    if n < configuracion.minimo_compras_clasificacion:
        return PATRON_HISTORIA_INSUFICIENTE

    es_alternancia = (
        caracteristicas["proporcion_alternancia"]
        >= configuracion.proporcion_alternancia_min
        and caracteristicas["relacion_alto_bajo"]
        >= configuracion.relacion_alto_bajo_min
        and caracteristicas["correlacion_lag1"]
        <= configuracion.correlacion_alternancia_max
        and abs(caracteristicas["pendiente_relativa"])
        < configuracion.tendencia_relativa_min
    )
    if es_alternancia:
        return PATRON_LLENADO_REPOSICION

    if caracteristicas["cv"] <= configuracion.cv_estable_max:
        if (
            caracteristicas["pendiente_relativa"]
            >= configuracion.tendencia_relativa_min
        ):
            return PATRON_TENDENCIA_CRECIENTE
        if (
            caracteristicas["pendiente_relativa"]
            <= -configuracion.tendencia_relativa_min
        ):
            return PATRON_TENDENCIA_DECRECIENTE
        return PATRON_ESTABLE

    if caracteristicas["pendiente_relativa"] >= configuracion.tendencia_relativa_min:
        return PATRON_TENDENCIA_CRECIENTE
    if caracteristicas["pendiente_relativa"] <= -configuracion.tendencia_relativa_min:
        return PATRON_TENDENCIA_DECRECIENTE
    return PATRON_ERRATICO


def _fase_valor(valor: float, mediana: float) -> str:
    if valor <= 0:
        return "SIN_FASE"
    return "LLENADO" if valor > mediana else "REPOSICION"


# =============================================================================
# MODELOS CANDIDATOS
# =============================================================================


def _modelo_mediana(historia: np.ndarray) -> float:
    return float(np.median(historia))


def _modelo_promedio(historia: np.ndarray) -> float:
    return float(np.mean(historia))


def _modelo_penultima(historia: np.ndarray) -> float:
    if len(historia) < 2:
        return float(historia[-1])
    return float(historia[-2])


def _modelo_ponderado_penultima(historia: np.ndarray) -> float:
    if len(historia) == 1:
        return float(historia[-1])
    if len(historia) == 2:
        return float(0.60 * historia[-2] + 0.40 * historia[-1])
    resto = float(np.mean(historia[:-2]))
    return float(0.50 * historia[-2] + 0.25 * historia[-1] + 0.25 * resto)


def _modelo_ponderado_reciente(historia: np.ndarray) -> float:
    if len(historia) == 1:
        return float(historia[-1])
    if len(historia) == 2:
        return float(0.60 * historia[-1] + 0.40 * historia[-2])
    resto = float(np.mean(historia[:-2]))
    return float(0.50 * historia[-1] + 0.30 * historia[-2] + 0.20 * resto)


def _modelo_alternancia(historia: np.ndarray) -> float:
    if len(historia) < 2:
        return float(historia[-1])

    mediana = float(np.median(historia))
    ultima_fase = _fase_valor(float(historia[-1]), mediana)
    fase_esperada = "REPOSICION" if ultima_fase == "LLENADO" else "LLENADO"

    if fase_esperada == "LLENADO":
        misma_fase = historia[historia > mediana]
    else:
        misma_fase = historia[historia <= mediana]

    promedio_fase = (
        float(np.mean(misma_fase)) if len(misma_fase) else float(historia[-2])
    )
    return float(0.50 * historia[-2] + 0.30 * promedio_fase + 0.20 * mediana)


def _modelo_tendencia_controlada(
    historia: np.ndarray,
    configuracion: ConfiguracionSugeridoMesa = CONFIG_DEFAULT,
) -> float:
    if len(historia) < 2:
        return float(historia[-1])
    pendiente = _pendiente_lineal(historia)
    proyectado = float(historia[-1] + pendiente)
    mediana = float(np.median(historia))
    piso = mediana * configuracion.recorte_tendencia_inferior
    techo = mediana * configuracion.recorte_tendencia_superior
    return float(np.clip(proyectado, piso, techo))


MODELOS_BASE: dict[str, Callable[[np.ndarray], float]] = {
    MODELO_MEDIANA: _modelo_mediana,
    MODELO_PROMEDIO: _modelo_promedio,
    MODELO_PENULTIMA: _modelo_penultima,
    MODELO_PONDERADO_PENULTIMA: _modelo_ponderado_penultima,
    MODELO_PONDERADO_RECIENTE: _modelo_ponderado_reciente,
    MODELO_ALTERNANCIA: _modelo_alternancia,
}


def _modelos_compatibles(patron: str) -> list[str]:
    if patron == PATRON_LLENADO_REPOSICION:
        return [
            MODELO_ALTERNANCIA,
            MODELO_PONDERADO_PENULTIMA,
            MODELO_PENULTIMA,
            MODELO_MEDIANA,
        ]
    if patron == PATRON_ESTABLE:
        return [MODELO_MEDIANA, MODELO_PROMEDIO, MODELO_PONDERADO_RECIENTE]
    if patron in {PATRON_TENDENCIA_CRECIENTE, PATRON_TENDENCIA_DECRECIENTE}:
        return [MODELO_TENDENCIA, MODELO_PONDERADO_RECIENTE, MODELO_MEDIANA]
    if patron == PATRON_ERRATICO:
        return [MODELO_MEDIANA, MODELO_PONDERADO_PENULTIMA, MODELO_PROMEDIO]
    return [MODELO_MEDIANA]


def _predecir_modelo(
    nombre_modelo: str,
    historia: np.ndarray,
    configuracion: ConfiguracionSugeridoMesa,
) -> float:
    if nombre_modelo == MODELO_TENDENCIA:
        valor = _modelo_tendencia_controlada(historia, configuracion)
    else:
        funcion = MODELOS_BASE[nombre_modelo]
        valor = funcion(historia)
    if not np.isfinite(valor):
        return 0.0
    return max(0.0, float(valor))


def evaluar_modelos_historicos(
    valores: np.ndarray,
    patron: str,
    configuracion: ConfiguracionSugeridoMesa = CONFIG_DEFAULT,
) -> tuple[str, float | pd._libs.missing.NAType]:
    """Selecciona modelo mediante backtesting cronologico con error MAE."""
    historia = np.asarray(valores, dtype=float)
    historia = historia[np.isfinite(historia) & (historia > 0)]

    if len(historia) == 0:
        return MODELO_SIN_HISTORIA, pd.NA
    if len(historia) == 1:
        return MODELO_UNICA_COMPRA, pd.NA
    if len(historia) == 2:
        return MODELO_DOS_COMPRAS, pd.NA

    candidatos = _modelos_compatibles(patron)
    if len(historia) < configuracion.minimo_compras_backtesting:
        preferido = candidatos[0]
        return preferido, pd.NA

    errores: dict[str, list[float]] = {modelo: [] for modelo in candidatos}
    inicio = max(3, configuracion.minimo_compras_clasificacion - 1)

    for posicion in range(inicio, len(historia)):
        entrenamiento = historia[:posicion]
        real = float(historia[posicion])
        patron_parcial = detectar_patron_compra(
            extraer_caracteristicas_patron(entrenamiento),
            configuracion,
        )
        compatibles_parciales = _modelos_compatibles(patron_parcial)

        for modelo in candidatos:
            if modelo not in compatibles_parciales and modelo not in {
                MODELO_MEDIANA,
                MODELO_PROMEDIO,
            }:
                continue
            predicho = _predecir_modelo(modelo, entrenamiento, configuracion)
            errores[modelo].append(abs(real - predicho))

    mae = {
        modelo: float(np.mean(valores_error))
        for modelo, valores_error in errores.items()
        if valores_error
    }
    if not mae:
        return candidatos[0], pd.NA

    prioridad = {modelo: i for i, modelo in enumerate(candidatos)}
    ganador = min(mae, key=lambda modelo: (mae[modelo], prioridad[modelo]))
    return ganador, float(mae[ganador])


def _nivel_confianza(cantidad: int, error_mae, media: float) -> str:
    if cantidad == 0:
        return "SIN_HISTORIA"
    if cantidad < 4:
        return "BAJA"
    if pd.isna(error_mae):
        return "MEDIA"
    error_relativo = float(error_mae) / media if media > 0 else math.inf
    if cantidad >= 6 and error_relativo <= 0.25:
        return "ALTA"
    if error_relativo <= 0.50:
        return "MEDIA"
    return "BAJA"


def calcular_sugerido_serie(
    valores: np.ndarray,
    configuracion: ConfiguracionSugeridoMesa = CONFIG_DEFAULT,
) -> dict:
    historia = np.asarray(valores, dtype=float)
    historia = historia[np.isfinite(historia) & (historia > 0)]
    caracteristicas = extraer_caracteristicas_patron(historia)
    patron = detectar_patron_compra(caracteristicas, configuracion)
    modelo, error_mae = evaluar_modelos_historicos(
        historia,
        patron,
        configuracion,
    )

    if modelo == MODELO_SIN_HISTORIA:
        sugerido = 0.0
    elif modelo == MODELO_UNICA_COMPRA:
        sugerido = float(historia[-1])
    elif modelo == MODELO_DOS_COMPRAS:
        sugerido = float(np.mean(historia))
    else:
        sugerido = _predecir_modelo(modelo, historia, configuracion)

    fase_ultima = "SIN_FASE"
    fase_proxima = "SIN_FASE"
    if patron == PATRON_LLENADO_REPOSICION and len(historia):
        fase_ultima = _fase_valor(float(historia[-1]), caracteristicas["mediana"])
        fase_proxima = "REPOSICION" if fase_ultima == "LLENADO" else "LLENADO"

    return {
        "caracteristicas": caracteristicas,
        "patron": patron,
        "modelo": modelo,
        "error_mae": error_mae,
        "nivel_confianza": _nivel_confianza(
            caracteristicas["cantidad"],
            error_mae,
            caracteristicas["media"],
        ),
        "fase_ultima": fase_ultima,
        "fase_proxima": fase_proxima,
        "sugerido": round(float(sugerido), 3),
    }


# =============================================================================
# DETALLE Y RESUMEN COMERCIAL
# =============================================================================


def construir_detalle_sugerido_mesa(
    cartera_dia: pd.DataFrame,
    historia: pd.DataFrame,
    dia_matinal,
    configuracion: ConfiguracionSugeridoMesa = CONFIG_DEFAULT,
) -> pd.DataFrame:
    fecha_matinal = _normalizar_fecha_unica(dia_matinal, "dia_matinal")
    if cartera_dia is None or cartera_dia.empty:
        return _dataframe_detalle_vacio()

    base = cartera_dia.copy()
    segmentos = pd.DataFrame({"Segmento": list(SEGMENTOS_SUGERIDO)})
    base["_k"] = 1
    segmentos["_k"] = 1
    universo = base.merge(segmentos, on="_k", how="inner").drop(columns="_k")

    grupos_historia = {}
    if historia is not None and not historia.empty:
        for clave, grupo in historia.groupby(["Cliente", "Segmento"], sort=False):
            grupos_historia[clave] = grupo.sort_values("FechaCompra", kind="stable")

    filas = []
    for fila in universo.itertuples(index=False):
        clave = (fila.Cliente, fila.Segmento)
        grupo = grupos_historia.get(clave)

        if grupo is None or grupo.empty:
            fechas = pd.Series(dtype="datetime64[ns]")
            valores = np.array([], dtype=float)
        else:
            fechas = grupo["FechaCompra"]
            valores = grupo["KgCompra"].to_numpy(dtype=float)

        calculo = calcular_sugerido_serie(valores, configuracion)
        car = calculo["caracteristicas"]

        filas.append(
            {
                "DiaMatinal": fecha_matinal,
                "Cliente": fila.Cliente,
                "NombreCliente": fila.NombreCliente,
                "CodVendedor": fila.CodVendedor,
                "Ruta": fila.Ruta,
                "DiaVisita": fila.DiaVisita,
                "Segmento": fila.Segmento,
                "CantidadCompras3M": car["cantidad"],
                "PrimeraCompraFecha": fechas.min() if not fechas.empty else pd.NaT,
                "UltimaCompraFecha": fechas.max() if not fechas.empty else pd.NaT,
                "UltimaCompraKg": car["ultima"],
                "PenultimaCompraKg": car["penultima"],
                "MediaKg": car["media"],
                "MedianaKg": car["mediana"],
                "DesvioKg": car["desvio"],
                "CoeficienteVariacion": car["cv"],
                "PendienteTendencia": car["pendiente"],
                "ProporcionAlternancia": car["proporcion_alternancia"],
                "PromedioNivelAlto": car["promedio_alto"],
                "PromedioNivelBajo": car["promedio_bajo"],
                "RelacionAltoBajo": car["relacion_alto_bajo"],
                "PatronDetectado": calculo["patron"],
                "FaseUltimaCompra": calculo["fase_ultima"],
                "FaseProximaEsperada": calculo["fase_proxima"],
                "ModeloSeleccionado": calculo["modelo"],
                "ErrorHistoricoMAE": calculo["error_mae"],
                "NivelConfianza": calculo["nivel_confianza"],
                "SugeridoKgCliente": calculo["sugerido"],
            }
        )

    detalle = pd.DataFrame(filas, columns=COLUMNAS_DETALLE)
    return detalle.sort_values(
        ["CodVendedor", "Cliente", "Segmento"], kind="stable"
    ).reset_index(drop=True)


def _confianza_agregada(serie: pd.Series) -> str:
    valores = serie.astype("string").fillna("SIN_HISTORIA")
    con_historia = valores.loc[~valores.eq("SIN_HISTORIA")]
    if con_historia.empty:
        return "SIN_HISTORIA"
    pesos = {"BAJA": 1.0, "MEDIA": 2.0, "ALTA": 3.0}
    promedio = con_historia.map(pesos).dropna().mean()
    if pd.isna(promedio):
        return "SIN_HISTORIA"
    if promedio >= 2.5:
        return "ALTA"
    if promedio >= 1.5:
        return "MEDIA"
    return "BAJA"


def construir_resumen_sugerido_mesa(
    detalle: pd.DataFrame,
    cartera_dia: pd.DataFrame,
    dia_matinal,
) -> pd.DataFrame:
    fecha_matinal = _normalizar_fecha_unica(dia_matinal, "dia_matinal")
    if cartera_dia is None or cartera_dia.empty:
        return _dataframe_resumen_vacio()

    vendedores = (
        cartera_dia.groupby("CodVendedor", as_index=False)["Cliente"]
        .nunique()
        .rename(columns={"Cliente": "ClientesRuta"})
    )
    vendedores["DiaMatinal"] = fecha_matinal

    if detalle is None or detalle.empty:
        for columna in COLUMNAS_RESUMEN:
            if columna not in vendedores.columns:
                vendedores[columna] = 0.0 if columna.startswith("Sugerido_") else pd.NA
        return vendedores[COLUMNAS_RESUMEN]

    sugeridos = detalle.pivot_table(
        index="CodVendedor",
        columns="Segmento",
        values="SugeridoKgCliente",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()
    sugeridos.columns.name = None
    sugeridos = sugeridos.rename(
        columns={segmento: f"Sugerido_{segmento}" for segmento in SEGMENTOS_SUGERIDO}
    )

    con_historia = (
        detalle.assign(ConHistoria=detalle["CantidadCompras3M"].gt(0).astype(int))
        .pivot_table(
            index="CodVendedor",
            columns="Segmento",
            values="ConHistoria",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    con_historia.columns.name = None
    con_historia = con_historia.rename(
        columns={
            segmento: f"ClientesConHistoria_{segmento}"
            for segmento in SEGMENTOS_SUGERIDO
        }
    )

    confianza = (
        detalle.groupby(["CodVendedor", "Segmento"], as_index=False)["NivelConfianza"]
        .agg(_confianza_agregada)
        .pivot(index="CodVendedor", columns="Segmento", values="NivelConfianza")
        .reset_index()
    )
    confianza.columns.name = None
    confianza = confianza.rename(
        columns={segmento: f"Confianza_{segmento}" for segmento in SEGMENTOS_SUGERIDO}
    )

    resumen = vendedores.merge(sugeridos, on="CodVendedor", how="left")
    resumen = resumen.merge(con_historia, on="CodVendedor", how="left")
    resumen = resumen.merge(confianza, on="CodVendedor", how="left")

    for segmento in SEGMENTOS_SUGERIDO:
        col_sugerido = f"Sugerido_{segmento}"
        col_historia = f"ClientesConHistoria_{segmento}"
        col_sin = f"ClientesSinHistoria_{segmento}"
        col_confianza = f"Confianza_{segmento}"

        resumen[col_sugerido] = pd.to_numeric(
            resumen.get(col_sugerido, 0.0), errors="coerce"
        ).fillna(0.0)
        resumen[col_historia] = (
            pd.to_numeric(resumen.get(col_historia, 0), errors="coerce")
            .fillna(0)
            .astype(int)
        )
        resumen[col_sin] = (resumen["ClientesRuta"] - resumen[col_historia]).clip(
            lower=0
        )
        if col_confianza not in resumen.columns:
            resumen[col_confianza] = "SIN_HISTORIA"
        else:
            resumen[col_confianza] = resumen[col_confianza].fillna("SIN_HISTORIA")

    return (
        resumen[COLUMNAS_RESUMEN]
        .sort_values("CodVendedor", kind="stable")
        .reset_index(drop=True)
    )


# =============================================================================
# PUNTO DE ENTRADA OFICIAL
# =============================================================================


@st.cache_data(show_spinner=False)
def obtener_sugerido_mesa(
    dia_matinal,
    cod_vendedor: int | None = None,
    configuracion: ConfiguracionSugeridoMesa = CONFIG_DEFAULT,
) -> dict:
    """
    Punto de entrada oficial del motor Sugerido Mesa.

    Devuelve:
    - detalle: una fila por Cliente actual x Segmento;
    - resumen: sugeridos agregados por CodVendedor;
    - historia: compras positivas utilizadas;
    - cartera_dia: clientes actuales correspondientes al Dia Matinal;
    - metadata: trazabilidad del procesamiento.

    No integra aun BUSINESS_RULES_COMPROMISOS. Esa integracion debe realizarse
    despues de auditar y aprobar este motor de forma independiente.
    """
    t0 = time.perf_counter()
    fecha_matinal = _normalizar_fecha_unica(dia_matinal, "dia_matinal")

    cartera_dia = obtener_cartera_dia_matinal(fecha_matinal)
    if cod_vendedor is not None:
        vendedor = pd.to_numeric(pd.Series([cod_vendedor]), errors="coerce").iloc[0]
        if pd.isna(vendedor):
            raise BusinessRulesSugeridoMesaError(
                f"cod_vendedor invalido: {cod_vendedor!r}."
            )
        cartera_dia = cartera_dia.loc[
            cartera_dia["CodVendedor"].eq(int(vendedor))
        ].copy()

    historia, fecha_desde, fecha_hasta = preparar_historia_compras_positivas(
        cartera_dia,
        fecha_matinal,
        configuracion=configuracion,
    )
    detalle = construir_detalle_sugerido_mesa(
        cartera_dia,
        historia,
        fecha_matinal,
        configuracion,
    )
    resumen = construir_resumen_sugerido_mesa(
        detalle,
        cartera_dia,
        fecha_matinal,
    )

    metadata = {
        "dia_matinal": fecha_matinal,
        "dia_semana": MAPEO_DIA_SEMANA[int(fecha_matinal.weekday())],
        "fecha_historia_desde": fecha_desde,
        "fecha_historia_hasta": fecha_hasta,
        "meses_historia": configuracion.meses_historia,
        "cantidad_clientes_ruta": int(cartera_dia["Cliente"].nunique())
        if not cartera_dia.empty
        else 0,
        "cantidad_vendedores": int(cartera_dia["CodVendedor"].nunique())
        if not cartera_dia.empty
        else 0,
        "compras_positivas_agregadas": int(len(historia)),
        "clientes_segmento_evaluados": int(len(detalle)),
        "clientes_segmento_con_historia": int(detalle["CantidadCompras3M"].gt(0).sum())
        if not detalle.empty
        else 0,
        "clientes_segmento_sin_historia": int(detalle["CantidadCompras3M"].eq(0).sum())
        if not detalle.empty
        else 0,
        "duracion_segundos": round(time.perf_counter() - t0, 4),
    }

    print(
        "[PERF_BR] obtener_sugerido_mesa -> "
        f"{metadata['duracion_segundos']:.4f} s | "
        f"clientes={metadata['cantidad_clientes_ruta']} | "
        f"vendedores={metadata['cantidad_vendedores']} | "
        f"detalle={metadata['clientes_segmento_evaluados']}"
    )

    return {
        "detalle": detalle,
        "resumen": resumen,
        "historia": historia,
        "cartera_dia": cartera_dia.reset_index(drop=True),
        "metadata": metadata,
    }
