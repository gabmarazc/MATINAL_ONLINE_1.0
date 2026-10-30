"""
PRUEBA CONTROLADA READ ONLY DEL LABORATORIO V2

Objetivo:
- Confirmar que los tres CORE cargan correctamente.
- Construir una muestra pequena RUTAS x VTA.
- Validar el contrato de oportunidades, compras y fechas.
- No ejecutar clustering ni modelos pesados.
- No escribir en SQLite, Excel ni archivos productivos.
"""

from __future__ import annotations

import sys
import traceback
import unicodedata
from pathlib import Path

import pandas as pd

from modules.core.core_clientes import obtener_core_clientes
from modules.core.core_rutas import obtener_core_rutas
from modules.core.core_ventas_base import obtener_core_ventas_base

DIA_CORTE = "30/10/2026"
DIAS_PRUEBA = 45
MAX_CLIENTES = 150
SEGMENTOS = ("PLAT_GOLD", "SILVER_BRZ")
TIPOS_VENTA_EXCLUIDOS = {
    "COMODATO DEVOLUCION",
    "COMODATO FICTICIO",
    "COMODATO FICTICIO DEVOLUCION",
    "COMODATO PRESTAMO",
}
ANCHO = 130


def titulo(texto: str) -> None:
    print("\n" + "=" * ANCHO)
    print(texto)
    print("=" * ANCHO)


def seccion(numero: int, texto: str) -> None:
    print(f"\n{numero}. {texto}")
    print("-" * ANCHO)


def normalizar_texto(valor) -> str:
    if valor is None or pd.isna(valor):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor).strip().upper())
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).split())


def normalizar_serie(serie: pd.Series) -> pd.Series:
    return serie.map(normalizar_texto).astype("object")


def validar_columnas(df: pd.DataFrame, requeridas: list[str], origen: str) -> None:
    faltantes = [c for c in requeridas if c not in df.columns]
    if faltantes:
        raise RuntimeError(f"{origen}: faltan columnas {faltantes}")


def resolver_columna(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    return next((c for c in candidatos if c in df.columns), None)


def asegurar_segmento(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    if "SEGMENTO" in x.columns and x["SEGMENTO"].notna().any():
        origen = normalizar_serie(x["SEGMENTO"])
    else:
        rent = resolver_columna(x, ["SegmentoRentabilidad", "SEGMENTORENTABILIDAD"])
        rubro = resolver_columna(x, ["Rubro", "RUBRO"])
        if rent is None or rubro is None:
            raise RuntimeError("No se puede construir SEGMENTO desde CORE_VENTAS_BASE")
        origen = (
            normalizar_serie(x[rent]) + " " + normalizar_serie(x[rubro])
        ).str.strip()

    mapa = {
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
    }
    x["Segmento"] = origen.map(mapa).astype("object")
    return x


def main() -> None:
    titulo("PRUEBA CONTROLADA READ ONLY - LABORATORIO V2")
    print(f"Proyecto: {Path.cwd()}")
    print(
        f"Corte: {DIA_CORTE} | Ventana: {DIAS_PRUEBA} dias | Max clientes: {MAX_CLIENTES}"
    )
    print("Escrituras productivas: NINGUNA")

    corte = pd.to_datetime(DIA_CORTE, dayfirst=True).normalize()
    desde = corte - pd.Timedelta(days=DIAS_PRUEBA)

    seccion(1, "CARGA DE CORE")
    clientes = obtener_core_clientes().copy()
    rutas = obtener_core_rutas().copy()
    ventas = obtener_core_ventas_base().copy()

    validar_columnas(clientes, ["Cliente", "CodVendedor"], "CORE_CLIENTES")
    validar_columnas(rutas, ["Cliente", "FechaRuta"], "CORE_RUTAS")
    validar_columnas(ventas, ["Cliente", "FechaCarga_dt", "PesoKg"], "CORE_VENTAS_BASE")

    print(f"CORE_CLIENTES: {len(clientes):,} filas")
    print(f"CORE_RUTAS: {len(rutas):,} filas")
    print(f"CORE_VENTAS_BASE: {len(ventas):,} filas")

    seccion(2, "MUESTRA CONTROLADA DE CLIENTES")
    clientes["Cliente"] = pd.to_numeric(clientes["Cliente"], errors="coerce").astype(
        "Int64"
    )
    clientes = clientes.dropna(subset=["Cliente"]).drop_duplicates("Cliente")

    rutas["Cliente"] = pd.to_numeric(rutas["Cliente"], errors="coerce").astype("Int64")
    rutas["FechaOportunidad"] = pd.to_datetime(
        rutas["FechaRuta"], errors="coerce"
    ).dt.normalize()
    rutas = rutas.loc[
        rutas["FechaOportunidad"].between(desde, corte, inclusive="left")
    ].copy()

    conteo = (
        rutas.groupby("Cliente")["FechaOportunidad"]
        .nunique()
        .sort_values(ascending=False)
    )
    muestra_clientes = conteo.head(MAX_CLIENTES).index
    rutas = rutas.loc[
        rutas["Cliente"].isin(muestra_clientes), ["Cliente", "FechaOportunidad"]
    ]
    rutas = (
        rutas.dropna().drop_duplicates().sort_values(["Cliente", "FechaOportunidad"])
    )
    rutas["SiguienteFechaRuta"] = rutas.groupby("Cliente")["FechaOportunidad"].shift(-1)

    print(f"Clientes de prueba: {rutas['Cliente'].nunique():,}")
    print(f"Oportunidades de prueba: {len(rutas):,}")
    print(f"Fecha minima: {rutas['FechaOportunidad'].min()}")
    print(f"Fecha maxima: {rutas['FechaOportunidad'].max()}")

    seccion(3, "PREPARACION DE VTA")
    ventas["Cliente"] = pd.to_numeric(ventas["Cliente"], errors="coerce").astype(
        "Int64"
    )
    ventas["FechaVenta"] = pd.to_datetime(
        ventas["FechaCarga_dt"], errors="coerce"
    ).dt.normalize()
    ventas["PesoKg"] = pd.to_numeric(ventas["PesoKg"], errors="coerce").fillna(0.0)
    ventas = ventas.loc[
        ventas["Cliente"].isin(muestra_clientes)
        & ventas["FechaVenta"].between(desde, corte, inclusive="left")
        & ventas["PesoKg"].gt(0)
    ].copy()

    if "Proveedor" in ventas.columns:
        ventas = ventas.loc[
            normalizar_serie(ventas["Proveedor"]).str.contains("PEPSICO", na=False)
        ]
    if "TipoDeVenta" in ventas.columns:
        ventas = ventas.loc[
            ~normalizar_serie(ventas["TipoDeVenta"]).isin(TIPOS_VENTA_EXCLUIDOS)
        ]

    ventas = asegurar_segmento(ventas)
    ventas = ventas.loc[ventas["Segmento"].isin(SEGMENTOS)].copy()
    ventas = (
        ventas.groupby(["Cliente", "FechaVenta", "Segmento"], as_index=False)["PesoKg"]
        .sum()
        .rename(columns={"PesoKg": "KgVenta"})
    )
    print(f"Compras positivas agregadas: {len(ventas):,}")

    seccion(4, "ASOCIACION ENTRE RUTAS Y VTA")
    asignadas = []
    fuera = []
    for (cliente, segmento), gv in ventas.groupby(["Cliente", "Segmento"], sort=False):
        calendario = rutas.loc[
            rutas["Cliente"].eq(cliente),
            ["FechaOportunidad", "SiguienteFechaRuta"],
        ].sort_values("FechaOportunidad")

        if calendario.empty:
            fuera.append(gv.assign(Motivo="SIN_RUTA"))
            continue

        z = pd.merge_asof(
            gv.sort_values("FechaVenta"),
            calendario,
            left_on="FechaVenta",
            right_on="FechaOportunidad",
            direction="backward",
            allow_exact_matches=True,
        )
        z["DiasDesdeRuta"] = (z["FechaVenta"] - z["FechaOportunidad"]).dt.days
        valido = z["FechaOportunidad"].notna() & (
            z["SiguienteFechaRuta"].isna() | z["FechaVenta"].lt(z["SiguienteFechaRuta"])
        )
        asignadas.append(z.loc[valido].copy())
        fuera.append(z.loc[~valido].assign(Motivo="FUERA_DE_VENTANA"))

    asignadas_df = (
        pd.concat(asignadas, ignore_index=True) if asignadas else pd.DataFrame()
    )
    fuera_df = pd.concat(fuera, ignore_index=True) if fuera else pd.DataFrame()

    segmentos = pd.DataFrame({"Segmento": list(SEGMENTOS)})
    oportunidades = (
        rutas.assign(_k=1).merge(segmentos.assign(_k=1), on="_k").drop(columns="_k")
    )

    if asignadas_df.empty:
        oportunidades["KgCompra"] = 0.0
    else:
        kg = (
            asignadas_df.groupby(
                ["Cliente", "Segmento", "FechaOportunidad"], as_index=False
            )["KgVenta"]
            .sum()
            .rename(columns={"KgVenta": "KgCompra"})
        )
        oportunidades = oportunidades.merge(
            kg,
            on=["Cliente", "Segmento", "FechaOportunidad"],
            how="left",
            validate="one_to_one",
        )
        oportunidades["KgCompra"] = oportunidades["KgCompra"].fillna(0.0)

    oportunidades["HuboCompra"] = oportunidades["KgCompra"].gt(0).astype(int)

    print(f"Ventas asignadas: {len(asignadas_df):,}")
    print(f"Ventas fuera: {len(fuera_df):,}")
    print(f"Oportunidades Cliente x Segmento: {len(oportunidades):,}")
    print(f"Con compra: {int(oportunidades['HuboCompra'].sum()):,}")
    print(f"Sin compra: {int((oportunidades['HuboCompra'] == 0).sum()):,}")

    seccion(5, "CONTROLES")
    errores = []
    if oportunidades.duplicated(["Cliente", "Segmento", "FechaOportunidad"]).any():
        errores.append("Existen oportunidades duplicadas")
    if oportunidades["Cliente"].isna().any():
        errores.append("Existen clientes nulos")
    if oportunidades["FechaOportunidad"].isna().any():
        errores.append("Existen fechas de oportunidad nulas")
    if (oportunidades["KgCompra"] < 0).any():
        errores.append("Existen KgCompra negativos")
    if len(oportunidades) != len(rutas) * len(SEGMENTOS):
        errores.append("No concilia rutas x cantidad de segmentos")

    muestra = oportunidades.sort_values(
        ["Cliente", "Segmento", "FechaOportunidad"]
    ).head(40)
    print(
        muestra[
            ["Cliente", "Segmento", "FechaOportunidad", "KgCompra", "HuboCompra"]
        ].to_string(index=False)
    )

    seccion(6, "DICTAMEN")
    if errores:
        print("NO APROBADO")
        for error in errores:
            print(f"- {error}")
        raise RuntimeError("La prueba controlada detecto errores estructurales")

    print("APROBADO")
    print("CORE cargados, asociacion RUTAS x VTA construida y contratos conciliados.")
    print("La prueba no ejecuto clustering ni modelos pesados.")
    print("PRUEBA FINALIZADA. ESCRITURAS PRODUCTIVAS: NINGUNA.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        titulo("PRUEBA INTERRUMPIDA")
        print(f"Tipo: {type(exc).__name__}")
        print(f"Detalle: {exc}")
        traceback.print_exc()
        print("Escrituras productivas: NINGUNA")
        sys.exit(1)
