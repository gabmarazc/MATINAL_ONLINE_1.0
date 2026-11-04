from __future__ import annotations

"""
modules/business_rules/business_rules_ryc.py

Motor comercial RyC (Rechazos y Cambios).

Arquitectura:
    CORE_OPERACION + CORE_VENDEDORES -> BUSINESS_RULES_RYC

Reglas aprobadas:
- Fuerza de venta: exclusivamente CORE_VENDEDORES; vendedor 20 queda excluido.
- Titularidad: CodVendedorVigente.
- Proveedor: exclusivamente PepsiCo.
- Periodos: Arrastre + Actual.
- Rechazos: TipoDeVenta == "Devolución por Rechazo";
  valor monetario = ABS(ImporteNetoItem).
- Cambios: TipoDeVenta == "Devolución por Canje";
  valor monetario = ABS(PrecioCosto).
- Presupuesto de Cambios: proviene de CORE_VENDEDORES.Cambios y es individual por vendedor.
- El motor calcula consumo y saldo del presupuesto; no define todavía semáforos visuales.
- Exclusión temporal de Innovaciones: un canje se excluye solamente cuando su Codigo
  pertenece a CORE_COBERTURA y FechaCarga_dt está entre Desde y Hasta, inclusive.
- Si Desde o Hasta están vacíos, la regla temporal no opera para ese SKU.
- La capa no lee SQLite/Excel/RAW/STAGING directamente y no renderiza Streamlit.

Nota sobre porcentajes:
- El motor expone Venta_Total_Neta y los numeradores RyC.
- Los porcentajes quedan calculados contra Venta_Total_Neta.
"""

import time
import unicodedata

import numpy as np
import pandas as pd
import streamlit as st

from modules.core.core_operaciones import obtener_core_operacion
from modules.core.core_vendedores import obtener_core_vendedores
from modules.core.core_cobertura import obtener_core_innovaciones
from modules.core.core_rutas import obtener_core_rutas

TIPO_RECHAZO = "DEVOLUCION POR RECHAZO"
TIPO_CANJE = "DEVOLUCION POR CANJE"
PERIODOS_VALIDOS = ("Arrastre", "Actual")

COLUMNAS_MATRIZ = [
    "CodVendedor",
    "Nombre",
    "SUP",
    "Venta_Total",
    "Rechazos",
    "Pct_Rechazos",
    "Cambios",
    "Presupuesto_Cambios",
    "Pct_Presupuesto_Cambios",
    "Saldo_Presupuesto_Cambios",
    "Excede_Presupuesto_Cambios",
    "Pct_Cambios",
    "RyC_Total",
    "Pct_RyC",
    "Cantidad_Rechazos",
    "Cantidad_Cambios",
]


class BusinessRulesRyCError(RuntimeError):
    """Error de contrato o integridad de BUSINESS_RULES_RYC."""


def _normalizar_texto(valor) -> str:
    if valor is None or pd.isna(valor):
        return ""
    texto = str(valor).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split())


def _normalizar_fecha(valor, nombre: str) -> pd.Timestamp:
    fecha = pd.to_datetime(valor, errors="coerce", dayfirst=True)
    if pd.isna(fecha):
        raise BusinessRulesRyCError(f"{nombre} inválido: {valor!r}.")
    return pd.Timestamp(fecha).normalize()


def _validar_columnas(df: pd.DataFrame, requeridas: list[str], origen: str) -> None:
    faltantes = [c for c in requeridas if c not in df.columns]
    if faltantes:
        raise BusinessRulesRyCError(
            f"{origen} no cumple el contrato RyC. Faltan columnas: {faltantes}."
        )


def _preparar_padron() -> pd.DataFrame:
    padron = obtener_core_vendedores(incluir_vendedor_20=False)
    if padron is None or padron.empty:
        raise BusinessRulesRyCError("CORE_VENDEDORES no devolvió vendedores válidos.")

    _validar_columnas(
        padron, ["CodVendedor", "Nombre", "SUP", "Cambios", "Combos"], "CORE_VENDEDORES"
    )
    resultado = padron[["CodVendedor", "Nombre", "SUP", "Cambios", "Combos"]].copy()
    resultado["CodVendedor"] = pd.to_numeric(
        resultado["CodVendedor"], errors="coerce"
    ).astype("Int64")
    resultado = resultado.loc[
        resultado["CodVendedor"].notna() & resultado["CodVendedor"].ne(20)
    ].copy()
    resultado["Nombre"] = resultado["Nombre"].fillna("").astype(str).str.strip()
    resultado["SUP"] = resultado["SUP"].fillna("").astype(str).str.strip()
    resultado["Cambios"] = (
        pd.to_numeric(resultado["Cambios"], errors="coerce").fillna(0).astype(int)
    )
    resultado["Combos"] = (
        pd.to_numeric(resultado["Combos"], errors="coerce").fillna(0).astype(int)
    )
    resultado = resultado.rename(columns={"Cambios": "Presupuesto_Cambios"})
    return (
        resultado.drop_duplicates("CodVendedor")
        .sort_values("CodVendedor", kind="stable")
        .reset_index(drop=True)
    )


def _preparar_ventas_ryc(
    df_vta_operativa: pd.DataFrame,
    padron: pd.DataFrame,
    innovaciones: pd.DataFrame,
) -> pd.DataFrame:
    requeridas = [
        "CodVendedorVigente",
        "Proveedor",
        "TipoDeVenta",
        "Periodo",
        "ImporteNetoItem",
        "PrecioCosto",
        "Codigo",
        "FechaCarga_dt",
    ]
    _validar_columnas(df_vta_operativa, requeridas, "CORE_OPERACION.df_vta_operativa")

    df = df_vta_operativa.copy()
    df["CodVendedorVigente"] = pd.to_numeric(
        df["CodVendedorVigente"], errors="coerce"
    ).astype("Int64")
    df["ImporteNetoItem"] = pd.to_numeric(
        df["ImporteNetoItem"], errors="coerce"
    ).fillna(0.0)
    df["PrecioCosto"] = pd.to_numeric(df["PrecioCosto"], errors="coerce").fillna(0.0)
    df["ProveedorNorm"] = df["Proveedor"].map(_normalizar_texto)
    df["TipoDeVentaNorm"] = df["TipoDeVenta"].map(_normalizar_texto)

    vendedores_validos = set(padron["CodVendedor"].dropna().astype(int).tolist())
    df = df.loc[
        df["Periodo"].isin(PERIODOS_VALIDOS)
        & df["ProveedorNorm"].str.contains("PEPSICO", na=False)
        & df["CodVendedorVigente"].isin(vendedores_validos)
    ].copy()

    df["Codigo"] = pd.to_numeric(df["Codigo"], errors="coerce").astype("Int64")
    df["FechaCarga_eval"] = pd.to_datetime(
        df["FechaCarga_dt"], errors="coerce"
    ).dt.normalize()
    df["Es_Canje"] = df["TipoDeVentaNorm"].eq(TIPO_CANJE)
    df["ValorCambioBruto"] = np.where(df["Es_Canje"], df["PrecioCosto"].abs(), 0.0)

    df["Es_Innovacion"] = False
    df["Ventana_Innovacion_Completa"] = False
    df["Excluir_Cambio_Innovacion"] = False
    df["Innovacion_RyC"] = ""
    df["Desde_Innovacion"] = pd.NaT
    df["Hasta_Innovacion"] = pd.NaT

    if innovaciones is not None and not innovaciones.empty:
        inv = innovaciones[["Codigo", "Innovacion", "Desde", "Hasta"]].copy()
        inv["Codigo"] = pd.to_numeric(inv["Codigo"], errors="coerce").astype("Int64")
        inv["Desde"] = pd.to_datetime(inv["Desde"], errors="coerce").dt.normalize()
        inv["Hasta"] = pd.to_datetime(inv["Hasta"], errors="coerce").dt.normalize()
        inv = (
            inv.loc[inv["Codigo"].notna()]
            .drop_duplicates("Codigo", keep="last")
            .rename(
                columns={
                    "Innovacion": "Innovacion_RyC_inv",
                    "Desde": "Desde_Innovacion_inv",
                    "Hasta": "Hasta_Innovacion_inv",
                }
            )
        )
        df = df.merge(inv, on="Codigo", how="left")
        df["Es_Innovacion"] = df["Innovacion_RyC_inv"].notna()
        df["Innovacion_RyC"] = (
            df["Innovacion_RyC_inv"].fillna("").astype(str).str.strip()
        )
        df["Desde_Innovacion"] = df["Desde_Innovacion_inv"]
        df["Hasta_Innovacion"] = df["Hasta_Innovacion_inv"]
        df["Ventana_Innovacion_Completa"] = (
            df["Desde_Innovacion"].notna() & df["Hasta_Innovacion"].notna()
        )
        df["Excluir_Cambio_Innovacion"] = (
            df["Es_Canje"]
            & df["Es_Innovacion"]
            & df["Ventana_Innovacion_Completa"]
            & df["FechaCarga_eval"].notna()
            & df["FechaCarga_eval"].ge(df["Desde_Innovacion"])
            & df["FechaCarga_eval"].le(df["Hasta_Innovacion"])
        )
        df = df.drop(
            columns=[
                "Innovacion_RyC_inv",
                "Desde_Innovacion_inv",
                "Hasta_Innovacion_inv",
            ],
            errors="ignore",
        )

    df["ValorCambioExcluido"] = np.where(
        df["Excluir_Cambio_Innovacion"], df["ValorCambioBruto"], 0.0
    )
    df["ValorCambioComputable"] = df["ValorCambioBruto"] - df["ValorCambioExcluido"]

    return df.reset_index(drop=True)


def _construir_batalla_ryc(
    ventas: pd.DataFrame,
    padron: pd.DataFrame,
    core_rutas: pd.DataFrame,
    dia_matinal: pd.Timestamp,
) -> pd.DataFrame:
    """Construye detalle operativo RyC a granularidad de fila/SKU de VTA."""
    columnas_salida = [
        "Cliente",
        "Razon_Social",
        "Fecha",
        "Codigo",
        "Articulo",
        "Cantidad",
        "Importe",
        "CodVendedor",
        "Nombre",
        "Tipo",
        "DiaVisita",
        "Cliente_Dia_Visita",
    ]
    if ventas is None or ventas.empty:
        return pd.DataFrame(columns=columnas_salida)

    es_rech = ventas["TipoDeVentaNorm"].eq(TIPO_RECHAZO)
    es_cambio = ventas["TipoDeVentaNorm"].eq(TIPO_CANJE) & ~ventas[
        "Excluir_Cambio_Innovacion"
    ].fillna(False)
    df = ventas.loc[es_rech | es_cambio].copy()
    if df.empty:
        return pd.DataFrame(columns=columnas_salida)

    col_cliente = next(
        (
            c
            for c in ["Cliente", "CLIENTE", "NroCliente", "CodCliente"]
            if c in df.columns
        ),
        None,
    )
    col_cantidad = next(
        (
            c
            for c in ["CantBase", "Cantidad", "Cant", "CantidadItem"]
            if c in df.columns
        ),
        None,
    )
    if col_cliente is None:
        raise BusinessRulesRyCError(
            "CORE_OPERACION no expone Cliente para Batalla RyC."
        )

    df["Cliente_Batalla"] = pd.to_numeric(df[col_cliente], errors="coerce").astype(
        "Int64"
    )
    df["Cantidad_Batalla"] = (
        pd.to_numeric(df[col_cantidad], errors="coerce").fillna(0.0)
        if col_cantidad
        else 0.0
    )
    col_articulo = next(
        (
            c
            for c in ["Articulo", "Artículo", "Descripcion", "Descripción"]
            if c in df.columns
        ),
        None,
    )
    df["Articulo_Batalla"] = (
        df[col_articulo].fillna("").astype(str).str.strip() if col_articulo else ""
    )
    df["Fecha_Batalla"] = pd.to_datetime(
        df["FechaCarga_dt"], errors="coerce"
    ).dt.normalize()
    df["Tipo_Batalla"] = df["TipoDeVentaNorm"].map(
        {TIPO_RECHAZO: "RECHAZOS", TIPO_CANJE: "CAMBIOS"}
    )
    df["Importe_Batalla"] = np.where(
        df["TipoDeVentaNorm"].eq(TIPO_RECHAZO),
        df["ImporteNetoItem"].abs(),
        df["ValorCambioComputable"],
    )

    nombres = padron[["CodVendedor", "Nombre"]].copy()
    df = df.merge(
        nombres,
        left_on="CodVendedorVigente",
        right_on="CodVendedor",
        how="left",
    )

    # CORE_RUTAS es el contrato institucional para determinar la programacion
    # Cliente + CodVendedor + FechaRuta. No se infiere desde Cobertura ni STAGING.
    df["Razon_Social_Batalla"] = ""
    df["DiaVisita_Batalla"] = "SIN DÍA"
    df["Cliente_Dia_Visita_Batalla"] = False

    if core_rutas is not None and not core_rutas.empty:
        _validar_columnas(
            core_rutas,
            ["Cliente", "NombreClienteRuta", "CodVendedor", "FechaRuta"],
            "CORE_RUTAS",
        )
        rutas = core_rutas.copy()
        rutas["Cliente_Ruta"] = pd.to_numeric(rutas["Cliente"], errors="coerce").astype(
            "Int64"
        )
        rutas["CodVendedor_Ruta"] = pd.to_numeric(
            rutas["CodVendedor"], errors="coerce"
        ).astype("Int64")
        rutas["FechaRuta_eval"] = pd.to_datetime(
            rutas["FechaRuta"], errors="coerce"
        ).dt.normalize()
        rutas["NombreClienteRuta"] = (
            rutas["NombreClienteRuta"].fillna("").astype(str).str.strip()
        )

        # Nombre de cliente: se toma del contrato CORE_RUTAS cuando existe una
        # programacion del cliente; no participa en la regla del flag del dia.
        nombres_ruta = (
            rutas.loc[rutas["Cliente_Ruta"].notna()]
            .sort_values(["Cliente_Ruta", "FechaRuta_eval"], kind="stable")
            .drop_duplicates("Cliente_Ruta", keep="last")
            .set_index("Cliente_Ruta")["NombreClienteRuta"]
            .to_dict()
        )
        df["Razon_Social_Batalla"] = df["Cliente_Batalla"].map(nombres_ruta).fillna("")

        rutas_vendedor = (
            rutas.loc[
                rutas["Cliente_Ruta"].notna()
                & rutas["CodVendedor_Ruta"].notna()
                & rutas["FechaRuta_eval"].notna()
            ]
            .sort_values(
                ["Cliente_Ruta", "CodVendedor_Ruta", "FechaRuta_eval"],
                kind="stable",
            )
            .drop_duplicates(
                ["Cliente_Ruta", "CodVendedor_Ruta", "FechaRuta_eval"],
                keep="first",
            )
        )
        dia_eval = pd.Timestamp(dia_matinal).normalize()
        claves_dia = set(
            rutas_vendedor.loc[
                rutas_vendedor["FechaRuta_eval"].eq(dia_eval),
                ["Cliente_Ruta", "CodVendedor_Ruta"],
            ].itertuples(index=False, name=None)
        )
        claves_batalla = list(
            zip(
                df["Cliente_Batalla"],
                pd.to_numeric(df["CodVendedorVigente"], errors="coerce").astype(
                    "Int64"
                ),
            )
        )
        df["Cliente_Dia_Visita_Batalla"] = [
            (cliente, vendedor) in claves_dia
            if pd.notna(cliente) and pd.notna(vendedor)
            else False
            for cliente, vendedor in claves_batalla
        ]

        # Día de visita descriptivo de la programación del mismo Cliente+Vendedor.
        # Si existen varias fechas, se conserva la más reciente del contrato.
        rv = (
            rutas_vendedor.sort_values("FechaRuta_eval", kind="stable")
            .drop_duplicates(["Cliente_Ruta", "CodVendedor_Ruta"], keep="last")
            .copy()
        )
        rv["DiaVisita_Batalla"] = rv["FechaRuta_eval"].dt.day_name().str.upper()
        mapa_dia = {
            (int(row.Cliente_Ruta), int(row.CodVendedor_Ruta)): row.DiaVisita_Batalla
            for row in rv.itertuples(index=False)
        }
        df["DiaVisita_Batalla"] = [
            mapa_dia.get((int(cliente), int(vendedor)), "SIN DÍA")
            if pd.notna(cliente) and pd.notna(vendedor)
            else "SIN DÍA"
            for cliente, vendedor in claves_batalla
        ]

    salida = pd.DataFrame(
        {
            "Cliente": df["Cliente_Batalla"],
            "Razon_Social": df["Razon_Social_Batalla"],
            "Fecha": df["Fecha_Batalla"],
            "Codigo": pd.to_numeric(df["Codigo"], errors="coerce").astype("Int64"),
            "Articulo": df["Articulo_Batalla"],
            "Cantidad": df["Cantidad_Batalla"],
            "Importe": pd.to_numeric(df["Importe_Batalla"], errors="coerce").fillna(
                0.0
            ),
            "CodVendedor": pd.to_numeric(
                df["CodVendedorVigente"], errors="coerce"
            ).astype("Int64"),
            "Nombre": df["Nombre"].fillna("").astype(str),
            "Tipo": df["Tipo_Batalla"],
            "DiaVisita": df["DiaVisita_Batalla"],
            "Cliente_Dia_Visita": df["Cliente_Dia_Visita_Batalla"].astype(bool),
        }
    )
    return salida[columnas_salida].reset_index(drop=True)


def _agregar_matriz(df: pd.DataFrame, padron: pd.DataFrame) -> pd.DataFrame:
    matriz = padron.copy()

    if df.empty:
        for c in [
            "Venta_Total",
            "Rechazos",
            "Pct_Rechazos",
            "Cambios",
            "Pct_Presupuesto_Cambios",
            "Saldo_Presupuesto_Cambios",
            "Excede_Presupuesto_Cambios",
            "Pct_Cambios",
            "RyC_Total",
            "Pct_RyC",
            "Cantidad_Rechazos",
            "Cantidad_Cambios",
        ]:
            matriz[c] = 0.0 if not c.startswith("Cantidad_") else 0
        presupuesto = pd.to_numeric(
            matriz["Presupuesto_Cambios"], errors="coerce"
        ).fillna(0.0)
        matriz["Saldo_Presupuesto_Cambios"] = presupuesto
        matriz["Pct_Presupuesto_Cambios"] = 0.0
        matriz["Excede_Presupuesto_Cambios"] = False
        return matriz[COLUMNAS_MATRIZ]

    # Denominador neto del universo PepsiCo operativo vigente.
    venta = (
        df.groupby("CodVendedorVigente", as_index=False)["ImporteNetoItem"]
        .sum()
        .rename(
            columns={
                "CodVendedorVigente": "CodVendedor",
                "ImporteNetoItem": "Venta_Total",
            }
        )
    )

    rech = df.loc[df["TipoDeVentaNorm"].eq(TIPO_RECHAZO)].copy()
    if rech.empty:
        rech_agg = pd.DataFrame(
            columns=["CodVendedor", "Rechazos", "Cantidad_Rechazos"]
        )
    else:
        rech["ValorRechazo"] = rech["ImporteNetoItem"].abs()
        rech_agg = (
            rech.groupby("CodVendedorVigente", as_index=False)
            .agg(
                Rechazos=("ValorRechazo", "sum"),
                Cantidad_Rechazos=("TipoDeVentaNorm", "size"),
            )
            .rename(columns={"CodVendedorVigente": "CodVendedor"})
        )

    canjes = df.loc[
        df["TipoDeVentaNorm"].eq(TIPO_CANJE)
        & ~df["Excluir_Cambio_Innovacion"].fillna(False)
    ].copy()
    if canjes.empty:
        canje_agg = pd.DataFrame(columns=["CodVendedor", "Cambios", "Cantidad_Cambios"])
    else:
        canjes["ValorCambio"] = canjes["ValorCambioComputable"]
        canje_agg = (
            canjes.groupby("CodVendedorVigente", as_index=False)
            .agg(
                Cambios=("ValorCambio", "sum"),
                Cantidad_Cambios=("TipoDeVentaNorm", "size"),
            )
            .rename(columns={"CodVendedorVigente": "CodVendedor"})
        )

    matriz = matriz.merge(venta, on="CodVendedor", how="left")
    matriz = matriz.merge(rech_agg, on="CodVendedor", how="left")
    matriz = matriz.merge(canje_agg, on="CodVendedor", how="left")

    for c in ["Venta_Total", "Rechazos", "Cambios"]:
        matriz[c] = pd.to_numeric(matriz[c], errors="coerce").fillna(0.0)
    for c in ["Cantidad_Rechazos", "Cantidad_Cambios"]:
        matriz[c] = pd.to_numeric(matriz[c], errors="coerce").fillna(0).astype(int)

    matriz["Presupuesto_Cambios"] = (
        pd.to_numeric(matriz["Presupuesto_Cambios"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    presupuesto_cambios = matriz["Presupuesto_Cambios"].replace(0, np.nan)
    matriz["Pct_Presupuesto_Cambios"] = (
        matriz["Cambios"] / presupuesto_cambios * 100.0
    ).fillna(0.0)
    matriz["Saldo_Presupuesto_Cambios"] = (
        matriz["Presupuesto_Cambios"].astype(float) - matriz["Cambios"]
    )
    matriz["Excede_Presupuesto_Cambios"] = matriz["Presupuesto_Cambios"].gt(0) & matriz[
        "Cambios"
    ].gt(matriz["Presupuesto_Cambios"])

    matriz["RyC_Total"] = matriz["Rechazos"] + matriz["Cambios"]
    denominador = matriz["Venta_Total"].replace(0.0, np.nan)
    matriz["Pct_Rechazos"] = (matriz["Rechazos"] / denominador * 100.0).fillna(0.0)
    matriz["Pct_Cambios"] = (matriz["Cambios"] / denominador * 100.0).fillna(0.0)
    matriz["Pct_RyC"] = (matriz["RyC_Total"] / denominador * 100.0).fillna(0.0)

    return (
        matriz[COLUMNAS_MATRIZ]
        .sort_values("CodVendedor", kind="stable")
        .reset_index(drop=True)
    )


def _construir_resumen(matriz: pd.DataFrame) -> dict:
    venta = float(pd.to_numeric(matriz["Venta_Total"], errors="coerce").fillna(0).sum())
    rechazos = float(pd.to_numeric(matriz["Rechazos"], errors="coerce").fillna(0).sum())
    cambios = float(pd.to_numeric(matriz["Cambios"], errors="coerce").fillna(0).sum())
    ryc = rechazos + cambios
    presupuesto_cambios = float(
        pd.to_numeric(matriz["Presupuesto_Cambios"], errors="coerce").fillna(0).sum()
    )
    saldo_presupuesto_cambios = presupuesto_cambios - cambios
    return {
        "Venta_Total": venta,
        "Rechazos": rechazos,
        "Pct_Rechazos": (rechazos / venta * 100.0) if venta else 0.0,
        "Cambios": cambios,
        "Presupuesto_Cambios": presupuesto_cambios,
        "Pct_Presupuesto_Cambios": (
            cambios / presupuesto_cambios * 100.0 if presupuesto_cambios else 0.0
        ),
        "Saldo_Presupuesto_Cambios": saldo_presupuesto_cambios,
        "Vendedores_Excedidos_Cambios": int(
            matriz["Excede_Presupuesto_Cambios"].fillna(False).sum()
        ),
        "Pct_Cambios": (cambios / venta * 100.0) if venta else 0.0,
        "RyC_Total": ryc,
        "Pct_RyC": (ryc / venta * 100.0) if venta else 0.0,
        "Cantidad_Rechazos": int(matriz["Cantidad_Rechazos"].sum()),
        "Cantidad_Cambios": int(matriz["Cantidad_Cambios"].sum()),
    }


@st.cache_data(show_spinner=False)
def obtener_business_rules_ryc(
    anio: int,
    mes: int,
    dia_matinal,
    dia_venta,
    modo_ajuste: str = "AJUSTADO",
) -> dict:
    """Punto de entrada oficial de BUSINESS_RULES_RYC."""
    t0 = time.perf_counter()
    anio_int = int(anio)
    mes_int = int(mes)
    fecha_matinal = _normalizar_fecha(dia_matinal, "dia_matinal")
    fecha_venta = _normalizar_fecha(dia_venta, "dia_venta")

    padron = _preparar_padron()
    innovaciones = obtener_core_innovaciones(anio_int, mes_int)
    core_rutas = obtener_core_rutas()
    core = obtener_core_operacion(
        anio_int,
        mes_int,
        fecha_matinal.strftime("%d/%m/%Y"),
        fecha_venta.strftime("%d/%m/%Y"),
        modo_ajuste=modo_ajuste,
    )
    if not isinstance(core, dict) or "df_vta_operativa" not in core:
        raise BusinessRulesRyCError(
            "CORE_OPERACION no devolvió df_vta_operativa para RyC."
        )

    ventas = _preparar_ventas_ryc(core["df_vta_operativa"], padron, innovaciones)
    matriz = _agregar_matriz(ventas, padron)
    batalla = _construir_batalla_ryc(ventas, padron, core_rutas, fecha_matinal)
    resumen = _construir_resumen(matriz)
    canjes_brutos = ventas["TipoDeVentaNorm"].eq(TIPO_CANJE)
    canjes_excluidos = ventas["Excluir_Cambio_Innovacion"].fillna(False)
    resumen["Cantidad_Cambios_Brutos"] = int(canjes_brutos.sum())
    resumen["Cantidad_Cambios_Excluidos_Innovacion"] = int(canjes_excluidos.sum())
    resumen["Importe_Cambios_Excluidos_Innovacion"] = float(
        pd.to_numeric(ventas["ValorCambioExcluido"], errors="coerce").fillna(0).sum()
    )
    resumen["Cambios_Brutos"] = float(
        pd.to_numeric(ventas["ValorCambioBruto"], errors="coerce").fillna(0).sum()
    )

    metadata = {
        "anio": anio_int,
        "mes": mes_int,
        "dia_matinal": fecha_matinal,
        "dia_venta": fecha_venta,
        "modo_ajuste": modo_ajuste,
        "periodos": list(PERIODOS_VALIDOS),
        "proveedor": "PEPSICO",
        "tipo_rechazo": TIPO_RECHAZO,
        "tipo_canje": TIPO_CANJE,
        "campo_rechazos": "ImporteNetoItem",
        "campo_cambios": "PrecioCosto",
        "campo_presupuesto_cambios": "CORE_VENDEDORES.Cambios",
        "core_innovaciones": "CORE_COBERTURA.obtener_core_innovaciones",
        "fecha_exclusion_innovaciones": "FechaCarga_dt",
        "regla_ventana_innovaciones": "Desde y Hasta informados; intervalo inclusivo",
        "cantidad_innovaciones": int(len(innovaciones)),
        "cantidad_cambios_excluidos_innovacion": resumen[
            "Cantidad_Cambios_Excluidos_Innovacion"
        ],
        "importe_cambios_excluidos_innovacion": resumen[
            "Importe_Cambios_Excluidos_Innovacion"
        ],
        "cantidad_vendedores_padron": int(len(padron)),
        "filas_universo": int(len(ventas)),
        "filas_batalla": int(len(batalla)),
        "fecha_batalla": "FechaCarga_dt",
        "core_rutas_batalla": "CORE_RUTAS.obtener_core_rutas",
        "clave_cliente_dia_visita": "Cliente + CodVendedor + Dia Matinal",
        "duracion_segundos": round(time.perf_counter() - t0, 4),
    }

    print(
        "[PERF_BR] obtener_business_rules_ryc -> "
        f"{metadata['duracion_segundos']:.4f} s | "
        f"vendedores={metadata['cantidad_vendedores_padron']} | "
        f"filas={metadata['filas_universo']} | "
        f"rechazos={resumen['Cantidad_Rechazos']} | "
        f"cambios={resumen['Cantidad_Cambios']}"
    )

    return {
        "matriz": matriz,
        "resumen": resumen,
        "detalle": ventas,
        "batalla": batalla,
        "padron": padron,
        "metadata": metadata,
    }
