# modules/business_rules/business_rules_sugerido_mesa.py
"""
Motor analitico SUGERIDO MESA V1 para COMPROMISOS.

Arquitectura:
    CORE_CLIENTES + CORE_VENTAS_BASE -> BUSINESS_RULES_SUGERIDO_MESA

Regla V1:
- CORE_CLIENTES determina la cartera actual Cliente -> CodVendedor.
- Solo se consideran clientes cuya visita corresponde al Dia Matinal.
- La historia pertenece al cliente, no al vendedor historico de VTA.
- Se utilizan exclusivamente compras positivas de los tres meses anteriores.
- La unidad historica es Cliente x FechaCompra x Segmento.
- Los segmentos son PLAT_GOLD y SILVER_BRZ.
- SugeridoKgCliente es la mediana de KgCompra positivos.
- Sin historia positiva, el sugerido es 0.0.
- Esta capa no lee SQLite, Excel, RAW ni STAGING directamente.
- Esta capa no renderiza Streamlit ni modifica COMPROMISOS.
"""

from __future__ import annotations

import time
import unicodedata
from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

from modules.core.core_clientes import obtener_core_clientes
from modules.core.core_ventas_base import obtener_core_ventas_base


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

MODELO_MEDIANA = "MEDIANA"
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
    "ModeloSeleccionado",
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
    """Parametros controlados de Sugerido Mesa V1."""

    meses_historia: int = 3


CONFIG_DEFAULT = ConfiguracionSugeridoMesa()


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
    La apropiacion Cliente -> CodVendedor proviene de CORE_CLIENTES.
    """
    fecha_matinal = _normalizar_fecha_unica(dia_matinal, "dia_matinal")
    clientes = (
        obtener_core_clientes() if core_clientes is None else core_clientes.copy()
    )

    columnas_salida = [
        "DiaMatinal",
        "Cliente",
        "NombreCliente",
        "CodVendedor",
        "Ruta",
        "DiaVisita",
    ]

    if clientes is None or clientes.empty:
        return pd.DataFrame(columns=columnas_salida)

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
        return pd.DataFrame(columns=columnas_salida)

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

    return (
        trabajo[columnas_salida]
        .sort_values(["CodVendedor", "Cliente"], kind="stable")
        .drop_duplicates(subset=["Cliente"], keep="first")
        .reset_index(drop=True)
    )


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
    Construye compras positivas por Cliente x FechaCompra x Segmento.
    Los dias sin compra no se incorporan como cero.
    """
    fecha_matinal = _normalizar_fecha_unica(dia_matinal, "dia_matinal")
    fecha_desde = fecha_matinal - pd.DateOffset(months=configuracion.meses_historia)
    fecha_hasta = fecha_matinal - pd.Timedelta(days=1)
    columnas_historia = ["Cliente", "FechaCompra", "Segmento", "KgCompra"]

    if cartera_dia is None or cartera_dia.empty:
        return pd.DataFrame(columns=columnas_historia), fecha_desde, fecha_hasta

    ventas = obtener_core_ventas_base() if core_ventas is None else core_ventas.copy()
    if ventas is None or ventas.empty:
        return pd.DataFrame(columns=columnas_historia), fecha_desde, fecha_hasta

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
        & trabajo["FechaCompra"].between(
            fecha_desde,
            fecha_hasta,
            inclusive="both",
        )
    ].copy()

    trabajo = _filtrar_universo_ventas(trabajo)
    trabajo = _asegurar_segmento_comercial(trabajo)
    trabajo = trabajo.loc[
        trabajo["Segmento"].isin(SEGMENTOS_SUGERIDO) & trabajo["PesoKg"].gt(0)
    ].copy()

    if trabajo.empty:
        return pd.DataFrame(columns=columnas_historia), fecha_desde, fecha_hasta

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
        ["Cliente", "Segmento", "FechaCompra"],
        kind="stable",
    ).reset_index(drop=True)

    return historia, fecha_desde, fecha_hasta


def _nivel_confianza_por_cantidad(cantidad: int) -> str:
    if cantidad <= 0:
        return "SIN_HISTORIA"
    if cantidad <= 2:
        return "BAJA"
    if cantidad <= 5:
        return "MEDIA"
    return "ALTA"


def calcular_sugerido_serie(
    valores: np.ndarray,
    configuracion: ConfiguracionSugeridoMesa = CONFIG_DEFAULT,
) -> dict:
    """Calcula Sugerido Mesa V1 usando exclusivamente la mediana."""
    del configuracion

    historia = np.asarray(valores, dtype=float)
    historia = historia[np.isfinite(historia) & (historia > 0)]
    cantidad = int(len(historia))

    if cantidad == 0:
        return {
            "cantidad": 0,
            "ultima": 0.0,
            "penultima": 0.0,
            "media": 0.0,
            "mediana": 0.0,
            "modelo": MODELO_SIN_HISTORIA,
            "nivel_confianza": "SIN_HISTORIA",
            "sugerido": 0.0,
        }

    mediana = float(np.median(historia))
    media = float(np.mean(historia))

    return {
        "cantidad": cantidad,
        "ultima": float(historia[-1]),
        "penultima": float(historia[-2]) if cantidad >= 2 else 0.0,
        "media": media,
        "mediana": mediana,
        "modelo": MODELO_MEDIANA,
        "nivel_confianza": _nivel_confianza_por_cantidad(cantidad),
        "sugerido": round(mediana, 3),
    }


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

    grupos_historia: dict[tuple, pd.DataFrame] = {}
    if historia is not None and not historia.empty:
        for clave, grupo in historia.groupby(["Cliente", "Segmento"], sort=False):
            grupos_historia[clave] = grupo.sort_values(
                "FechaCompra",
                kind="stable",
            )

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
        filas.append(
            {
                "DiaMatinal": fecha_matinal,
                "Cliente": fila.Cliente,
                "NombreCliente": fila.NombreCliente,
                "CodVendedor": fila.CodVendedor,
                "Ruta": fila.Ruta,
                "DiaVisita": fila.DiaVisita,
                "Segmento": fila.Segmento,
                "CantidadCompras3M": calculo["cantidad"],
                "PrimeraCompraFecha": fechas.min() if not fechas.empty else pd.NaT,
                "UltimaCompraFecha": fechas.max() if not fechas.empty else pd.NaT,
                "UltimaCompraKg": calculo["ultima"],
                "PenultimaCompraKg": calculo["penultima"],
                "MediaKg": calculo["media"],
                "MedianaKg": calculo["mediana"],
                "ModeloSeleccionado": calculo["modelo"],
                "NivelConfianza": calculo["nivel_confianza"],
                "SugeridoKgCliente": calculo["sugerido"],
            }
        )

    detalle = pd.DataFrame(filas, columns=COLUMNAS_DETALLE)
    return detalle.sort_values(
        ["CodVendedor", "Cliente", "Segmento"],
        kind="stable",
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
            resumen.get(col_sugerido, 0.0),
            errors="coerce",
        ).fillna(0.0)
        resumen[col_historia] = (
            pd.to_numeric(
                resumen.get(col_historia, 0),
                errors="coerce",
            )
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


@st.cache_data(show_spinner=False)
def obtener_sugerido_mesa(
    dia_matinal,
    cod_vendedor: int | None = None,
    configuracion: ConfiguracionSugeridoMesa = CONFIG_DEFAULT,
) -> dict:
    """
    Punto de entrada oficial Sugerido Mesa V1.

    Devuelve detalle, resumen, historia, cartera del dia y metadata.
    No integra todavia BUSINESS_RULES_COMPROMISOS.
    """
    t0 = time.perf_counter()
    fecha_matinal = _normalizar_fecha_unica(dia_matinal, "dia_matinal")
    cartera_dia = obtener_cartera_dia_matinal(fecha_matinal)

    if cod_vendedor is not None:
        vendedor = pd.to_numeric(
            pd.Series([cod_vendedor]),
            errors="coerce",
        ).iloc[0]
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
        "modelo": MODELO_MEDIANA,
        "cantidad_clientes_ruta": (
            int(cartera_dia["Cliente"].nunique()) if not cartera_dia.empty else 0
        ),
        "cantidad_vendedores": (
            int(cartera_dia["CodVendedor"].nunique()) if not cartera_dia.empty else 0
        ),
        "compras_positivas_agregadas": int(len(historia)),
        "clientes_segmento_evaluados": int(len(detalle)),
        "clientes_segmento_con_historia": (
            int(detalle["CantidadCompras3M"].gt(0).sum()) if not detalle.empty else 0
        ),
        "clientes_segmento_sin_historia": (
            int(detalle["CantidadCompras3M"].eq(0).sum()) if not detalle.empty else 0
        ),
        "duracion_segundos": round(time.perf_counter() - t0, 4),
    }

    print(
        "[PERF_BR] obtener_sugerido_mesa -> "
        f"{metadata['duracion_segundos']:.4f} s | "
        f"modelo={metadata['modelo']} | "
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


# =============================================================================
# SUGERIDO MESA V2 - OCHO REGLAS DE COMPROMISOS
# =============================================================================

INDICADORES_SUGERIDO_MESA = (
    "PLAT_GOLD",
    "SILVER_BRZ",
    "VARIOS ($)",
    "CCC (Efect)",
    "NC",
    "PORC SELLOUT MN",
    "ADOPCIÓN MN",
    "TIENDAS PERFECTAS",
)

PORCENTAJE_CCC_EFECT = 0.70
PORCENTAJE_SELLOUT_MN = 90.0


def _importe_varios_por_cliente(
    cartera_dia: pd.DataFrame,
    dia_matinal,
    core_ventas: pd.DataFrame | None = None,
    configuracion: ConfiguracionSugeridoMesa = CONFIG_DEFAULT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mediana de venta diaria no-PepsiCo en $ por cliente de la ruta."""
    fecha_matinal = _normalizar_fecha_unica(dia_matinal, "dia_matinal")
    fecha_desde = fecha_matinal - pd.DateOffset(months=configuracion.meses_historia)
    fecha_hasta = fecha_matinal - pd.Timedelta(days=1)

    columnas_hist = ["Cliente", "FechaCompra", "ImporteVariosDia"]
    columnas_med = ["Cliente", "CantidadComprasVarios3M", "MedianaVariosCliente"]

    if cartera_dia is None or cartera_dia.empty:
        return pd.DataFrame(columns=columnas_hist), pd.DataFrame(columns=columnas_med)

    ventas = obtener_core_ventas_base() if core_ventas is None else core_ventas.copy()
    if ventas is None or ventas.empty:
        return pd.DataFrame(columns=columnas_hist), pd.DataFrame(columns=columnas_med)

    _validar_columnas(
        ventas,
        ["Cliente", "ImporteNetoItem", "FechaCarga_dt", "Proveedor"],
        "CORE_VENTAS_BASE",
    )

    trabajo = ventas.copy()
    trabajo["Cliente"] = pd.to_numeric(trabajo["Cliente"], errors="coerce").astype(
        "Int64"
    )
    trabajo["ImporteNetoItem"] = pd.to_numeric(
        trabajo["ImporteNetoItem"], errors="coerce"
    ).fillna(0.0)
    trabajo["FechaCompra"] = pd.to_datetime(
        trabajo["FechaCarga_dt"], errors="coerce"
    ).dt.normalize()

    clientes_dia = set(cartera_dia["Cliente"].dropna().astype("Int64").tolist())
    proveedor = _normalizar_serie_texto(trabajo["Proveedor"])

    trabajo = trabajo.loc[
        trabajo["Cliente"].isin(clientes_dia)
        & trabajo["FechaCompra"].between(fecha_desde, fecha_hasta, inclusive="both")
        & ~proveedor.str.contains("PEPSICO", na=False)
    ].copy()

    if "TipoDeVenta" in trabajo.columns:
        tipo = _normalizar_serie_texto(trabajo["TipoDeVenta"])
        trabajo = trabajo.loc[~tipo.isin(TIPOS_VENTA_EXCLUIDOS)].copy()

    if trabajo.empty:
        return pd.DataFrame(columns=columnas_hist), pd.DataFrame(columns=columnas_med)

    historia = (
        trabajo.groupby(["Cliente", "FechaCompra"], as_index=False, dropna=False)[
            "ImporteNetoItem"
        ]
        .sum()
        .rename(columns={"ImporteNetoItem": "ImporteVariosDia"})
    )
    historia = historia.loc[historia["ImporteVariosDia"].gt(0)].copy()

    if historia.empty:
        return pd.DataFrame(columns=columnas_hist), pd.DataFrame(columns=columnas_med)

    por_cliente = historia.groupby("Cliente", as_index=False).agg(
        CantidadComprasVarios3M=("ImporteVariosDia", "size"),
        MedianaVariosCliente=("ImporteVariosDia", "median"),
    )
    por_cliente["MedianaVariosCliente"] = pd.to_numeric(
        por_cliente["MedianaVariosCliente"], errors="coerce"
    ).fillna(0.0)

    return historia.reset_index(drop=True), por_cliente.reset_index(drop=True)


def _normalizar_cliente_serie(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce").astype("Int64")


def _construir_estado_oportunidades(
    cartera_dia: pd.DataFrame,
    anio: int,
    mes: int,
    filtros_globales: dict,
) -> pd.DataFrame:
    """Cruza la cartera del dia contra los estados productivos CCC, MN y TP."""
    if cartera_dia is None or cartera_dia.empty:
        return pd.DataFrame(
            columns=[
                "Cliente",
                "CodVendedor",
                "Es_NC",
                "Es_NoDigital",
                "Es_TP",
            ]
        )

    from modules.business_rules.business_rules_ccc import obtener_detalle_clientes_ccc
    from modules.business_rules.business_rules_mn import obtener_matriz_mn_comercial
    from modules.business_rules.business_rules_tp import generar_business_rules_tp

    base = cartera_dia[["Cliente", "CodVendedor"]].copy()
    base["Cliente"] = _normalizar_cliente_serie(base["Cliente"])
    base["CodVendedor"] = _normalizar_cliente_serie(base["CodVendedor"])
    base = base.dropna(subset=["Cliente", "CodVendedor"]).drop_duplicates("Cliente")

    # NC: cliente de la ruta que aun no es CCC del vendedor.
    df_ccc = obtener_detalle_clientes_ccc(anio, mes, filtros_globales)
    if df_ccc is not None and not df_ccc.empty and "Cliente" in df_ccc.columns:
        ccc = df_ccc.copy()
        ccc["Cliente"] = _normalizar_cliente_serie(ccc["Cliente"])
        if "Es_CCC_Vendedor" in ccc.columns:
            ccc_estado = (
                ccc.groupby("Cliente", as_index=False)["Es_CCC_Vendedor"]
                .max()
                .rename(columns={"Es_CCC_Vendedor": "Es_CCC_Vendedor"})
            )
            ccc_estado["Es_CCC_Vendedor"] = (
                ccc_estado["Es_CCC_Vendedor"].fillna(False).astype(bool)
            )
            base = base.merge(ccc_estado, on="Cliente", how="left")
        else:
            base["Es_CCC_Vendedor"] = False
    else:
        base["Es_CCC_Vendedor"] = False
    base["Es_CCC_Vendedor"] = base["Es_CCC_Vendedor"].fillna(False).astype(bool)
    base["Es_NC"] = ~base["Es_CCC_Vendedor"]

    # MiNegocio: oportunidad = cliente clasificado como No Digital.
    df_mn = obtener_matriz_mn_comercial(anio, mes, filtros_globales)
    if df_mn is not None and not df_mn.empty and "Cliente" in df_mn.columns:
        mn = df_mn.copy()
        mn["Cliente"] = _normalizar_cliente_serie(mn["Cliente"])
        if "Es_NoDigital" in mn.columns:
            mn_estado = mn[["Cliente", "Es_NoDigital"]].drop_duplicates("Cliente")
            mn_estado["Es_NoDigital"] = (
                mn_estado["Es_NoDigital"].fillna(False).astype(bool)
            )
            base = base.merge(mn_estado, on="Cliente", how="left")
        else:
            base["Es_NoDigital"] = False
    else:
        base["Es_NoDigital"] = False
    base["Es_NoDigital"] = base["Es_NoDigital"].fillna(False).astype(bool)

    # Tienda Perfecta: oportunidad = cliente visitable que aun no es TP.
    resultado_tp = generar_business_rules_tp()
    df_tp = (
        resultado_tp.get("tabla_oportunidades", pd.DataFrame())
        if isinstance(resultado_tp, dict)
        else pd.DataFrame()
    )
    if df_tp is not None and not df_tp.empty and "Cliente_id" in df_tp.columns:
        tp = df_tp.copy()
        tp["Cliente"] = _normalizar_cliente_serie(tp["Cliente_id"])
        if "Es_TP" in tp.columns:
            tp_estado = tp.groupby("Cliente", as_index=False)["Es_TP"].max()
            tp_estado["Es_TP"] = tp_estado["Es_TP"].fillna(False).astype(bool)
            base = base.merge(tp_estado, on="Cliente", how="left")
        else:
            base["Es_TP"] = False
    else:
        base["Es_TP"] = False
    base["Es_TP"] = base["Es_TP"].fillna(False).astype(bool)
    base["Es_NoTP"] = ~base["Es_TP"]

    return base.reset_index(drop=True)


def construir_sugerido_mesa_ocho_reglas(
    dia_matinal,
    anio: int,
    mes: int,
    filtros_globales: dict,
    cod_vendedor: int | None = None,
    configuracion: ConfiguracionSugeridoMesa = CONFIG_DEFAULT,
) -> dict:
    """Construye los ocho indicadores oficiales de SUGERIDO MESA por vendedor."""
    fecha_matinal = _normalizar_fecha_unica(dia_matinal, "dia_matinal")

    # Reutiliza el motor V1 ya aprobado empíricamente para kilos.
    base_kilos = obtener_sugerido_mesa(
        fecha_matinal,
        cod_vendedor=cod_vendedor,
        configuracion=configuracion,
    )
    cartera = base_kilos["cartera_dia"].copy()
    resumen_kilos = base_kilos["resumen"].copy()

    if cartera.empty:
        return {
            "tablero": pd.DataFrame(
                columns=["CodVendedor", "INDICADOR", "SUGERIDO_MESA"]
            ),
            "resumen_vendedor": pd.DataFrame(),
            "cartera_dia": cartera,
            "historia_varios": pd.DataFrame(),
            "detalle_varios": pd.DataFrame(),
            "oportunidades": pd.DataFrame(),
            "metadata": {
                "dia_matinal": fecha_matinal,
                "cantidad_clientes_ruta": 0,
                "cantidad_vendedores": 0,
            },
        }

    historia_varios, varios_cliente = _importe_varios_por_cliente(
        cartera,
        fecha_matinal,
        configuracion=configuracion,
    )

    cartera_varios = cartera[["Cliente", "CodVendedor"]].copy()
    cartera_varios["Cliente"] = _normalizar_cliente_serie(cartera_varios["Cliente"])
    cartera_varios = cartera_varios.merge(varios_cliente, on="Cliente", how="left")
    cartera_varios["MedianaVariosCliente"] = pd.to_numeric(
        cartera_varios.get("MedianaVariosCliente", 0.0), errors="coerce"
    ).fillna(0.0)

    varios_vendedor = (
        cartera_varios.groupby("CodVendedor", as_index=False)["MedianaVariosCliente"]
        .sum()
        .rename(columns={"MedianaVariosCliente": "Sugerido_VARIOS"})
    )

    oportunidades = _construir_estado_oportunidades(
        cartera,
        int(anio),
        int(mes),
        filtros_globales,
    )

    opp_vendedor = oportunidades.groupby("CodVendedor", as_index=False).agg(
        ClientesRuta=("Cliente", "nunique"),
        Sugerido_NC=("Es_NC", lambda s: int(s.sum())),
        Sugerido_ADOPCION_MN=("Es_NoDigital", lambda s: int(s.sum())),
        Sugerido_TIENDAS_PERFECTAS=("Es_NoTP", lambda s: int(s.sum())),
    )

    # CCC: al menos 70% de la cartera del dia, siempre redondeando hacia arriba.
    opp_vendedor["Sugerido_CCC_Efect"] = np.ceil(
        opp_vendedor["ClientesRuta"] * PORCENTAJE_CCC_EFECT
    ).astype(int)
    opp_vendedor["Sugerido_PORC_SELLOUT_MN"] = PORCENTAJE_SELLOUT_MN

    resumen = resumen_kilos[
        [
            "CodVendedor",
            "ClientesRuta",
            "Sugerido_PLAT_GOLD",
            "Sugerido_SILVER_BRZ",
        ]
    ].copy()
    resumen = resumen.rename(columns={"ClientesRuta": "ClientesRuta_Kilos"})
    resumen = resumen.merge(varios_vendedor, on="CodVendedor", how="left")
    resumen = resumen.merge(opp_vendedor, on="CodVendedor", how="left")
    resumen["Sugerido_VARIOS"] = pd.to_numeric(
        resumen["Sugerido_VARIOS"], errors="coerce"
    ).fillna(0.0)

    filas = []
    for fila in resumen.itertuples(index=False):
        valores = {
            "PLAT_GOLD": float(fila.Sugerido_PLAT_GOLD),
            "SILVER_BRZ": float(fila.Sugerido_SILVER_BRZ),
            "VARIOS ($)": float(fila.Sugerido_VARIOS),
            "CCC (Efect)": int(fila.Sugerido_CCC_Efect),
            "NC": int(fila.Sugerido_NC),
            "PORC SELLOUT MN": float(fila.Sugerido_PORC_SELLOUT_MN),
            "ADOPCIÓN MN": int(fila.Sugerido_ADOPCION_MN),
            "TIENDAS PERFECTAS": int(fila.Sugerido_TIENDAS_PERFECTAS),
        }
        for indicador in INDICADORES_SUGERIDO_MESA:
            filas.append(
                {
                    "DiaMatinal": fecha_matinal,
                    "CodVendedor": int(fila.CodVendedor),
                    "INDICADOR": indicador,
                    "SUGERIDO_MESA": valores[indicador],
                }
            )

    tablero = pd.DataFrame(filas)
    metadata = {
        "dia_matinal": fecha_matinal,
        "anio": int(anio),
        "mes": int(mes),
        "cantidad_clientes_ruta": int(cartera["Cliente"].nunique()),
        "cantidad_vendedores": int(cartera["CodVendedor"].nunique()),
        "porcentaje_ccc": PORCENTAJE_CCC_EFECT,
        "porcentaje_sellout_mn": PORCENTAJE_SELLOUT_MN,
        "meses_historia": configuracion.meses_historia,
    }

    return {
        "tablero": tablero.sort_values(["CodVendedor", "INDICADOR"]).reset_index(
            drop=True
        ),
        "resumen_vendedor": resumen.sort_values("CodVendedor").reset_index(drop=True),
        "cartera_dia": cartera.reset_index(drop=True),
        "historia_varios": historia_varios.reset_index(drop=True),
        "detalle_varios": cartera_varios.reset_index(drop=True),
        "oportunidades": oportunidades.reset_index(drop=True),
        "metadata": metadata,
    }
