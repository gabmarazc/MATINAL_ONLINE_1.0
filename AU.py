# AU_BUSINESS_RULES_CHECKIN.py
# Auditoria forense y de solo lectura de BUSINESS_RULES_CHECKIN.
# Ejecutar desde la raiz de MATINAL ONLINE:
#     python AU_BUSINESS_RULES_CHECKIN.py

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent

ESTADOS_ESPERADOS = {
    "EN_RUTA",
    "FUERA_RUTA_CLIENTE",
    "SIN_RUTA_ESE_DIA",
    "VENDEDOR_NO_MAPEABLE",
}

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


def titulo(texto: str) -> None:
    print("\n" + "=" * 96)
    print(texto)
    print("=" * 96)


def control(etiqueta: str, condicion: bool, detalle: str = "") -> bool:
    estado = "OK" if condicion else "ERROR"
    sufijo = f" | {detalle}" if detalle else ""
    print(f"[{estado}] {etiqueta}{sufijo}")
    return bool(condicion)


def normalizar_codigo_vendedor(serie: pd.Series) -> pd.Series:
    numerico = pd.to_numeric(serie.astype("string").str.strip(), errors="coerce")
    entero = numerico.notna() & np.isclose(numerico, np.floor(numerico))
    salida = pd.Series(pd.NA, index=serie.index, dtype="Int64")
    salida.loc[entero] = numerico.loc[entero].astype("int64")
    return salida


def resolver_maestro(maestros: dict[str, pd.DataFrame]) -> pd.DataFrame:
    maestro = maestros.get("maestro_vendedores", pd.DataFrame())
    if maestro.empty:
        raise ValueError("maestro_vendedores no esta disponible o esta vacio.")

    col_codigo = next(
        (
            c
            for c in ["Codigo_Vendedor", "CodVend", "CodVendedor", "Codigo", "codven"]
            if c in maestro.columns
        ),
        None,
    )
    col_nombre = next(
        (
            c
            for c in ["Nombre_Vendedor", "Nombre", "Vendedor", "NombreVendedor"]
            if c in maestro.columns
        ),
        None,
    )
    col_sup = next(
        (c for c in ["SUP", "Sup", "Supervisor"] if c in maestro.columns),
        None,
    )
    if not all([col_codigo, col_nombre, col_sup]):
        raise ValueError(
            "No se pudo resolver el contrato del maestro. "
            f"Columnas encontradas: {list(maestro.columns)}"
        )

    return pd.DataFrame(
        {
            "CodVend": pd.to_numeric(maestro[col_codigo], errors="coerce").astype(
                "Int64"
            ),
            "Vendedor": maestro[col_nombre].astype("string").str.strip(),
            "SUP": pd.to_numeric(maestro[col_sup], errors="coerce").astype("Int64"),
        }
    )


def comparar_porcentaje(
    df: pd.DataFrame,
    numerador: str,
    denominador: str,
    porcentaje: str,
) -> int:
    den = (
        pd.to_numeric(df[denominador], errors="coerce").fillna(0).to_numpy(dtype=float)
    )
    num = pd.to_numeric(df[numerador], errors="coerce").fillna(0).to_numpy(dtype=float)
    esperado = np.divide(num, den, out=np.zeros(len(df), dtype=float), where=den != 0)
    real = (
        pd.to_numeric(df[porcentaje], errors="coerce")
        .fillna(np.nan)
        .to_numpy(dtype=float)
    )
    return int((~np.isclose(esperado, real, equal_nan=False)).sum())


def main() -> int:
    inicio = time.perf_counter()
    errores = 0

    titulo("AU_BUSINESS_RULES_CHECKIN - AUDITORIA FORENSE")
    print(f"Proyecto : {ROOT}")
    print("Modo     : SOLO LECTURA")
    print("Objeto   : CORE_CHECKIN + CORE_RUTAS + MAESTRO -> BUSINESS_RULES_CHECKIN")

    titulo("1. IMPORTACION DE CAPAS PRODUCTIVAS")
    try:
        from modules.core.core_checkin import obtener_core_checkin
        from modules.core.core_rutas import obtener_core_rutas
        from modules.staging import obtener_staging_maestros
        from modules.business_rules.business_rules_checkin import (
            construir_detalle_checkin_ruta,
            construir_resumen_checkin_vendedores,
            obtener_business_rules_checkin,
        )
    except Exception as exc:
        print(f"[ERROR] Importacion: {type(exc).__name__}: {exc}")
        return 1

    print("[OK] CORE_CHECKIN")
    print("[OK] CORE_RUTAS")
    print("[OK] STAGING_MAESTROS")
    print("[OK] BUSINESS_RULES_CHECKIN")

    titulo("2. CARGA DE FUENTES REALES")
    try:
        for funcion in [
            obtener_core_checkin,
            obtener_core_rutas,
            obtener_staging_maestros,
        ]:
            if hasattr(funcion, "clear"):
                funcion.clear()
        core_checkin = obtener_core_checkin()
        core_rutas = obtener_core_rutas()
        maestros = obtener_staging_maestros()
        maestro = resolver_maestro(maestros)
    except Exception as exc:
        print(f"[ERROR] Carga de fuentes: {type(exc).__name__}: {exc}")
        return 1

    print(f"CORE_CHECKIN filas : {len(core_checkin)}")
    print(f"CORE_RUTAS filas   : {len(core_rutas)}")
    print(f"MAESTRO filas      : {len(maestro)}")
    errores += not control("CORE_CHECKIN no vacio", not core_checkin.empty)
    errores += not control("CORE_RUTAS no vacio", not core_rutas.empty)
    errores += not control("MAESTRO no vacio", not maestro.empty)
    errores += not control(
        "CodVend maestro sin duplicados", not maestro["CodVend"].duplicated().any()
    )
    errores += not control(
        "CodVend maestro completo", not maestro["CodVend"].isna().any()
    )

    titulo("3. DETALLE DE VISITAS CLASIFICADO")
    try:
        detalle = construir_detalle_checkin_ruta(core_checkin, core_rutas)
    except Exception as exc:
        print(f"[ERROR] construir_detalle_checkin_ruta: {type(exc).__name__}: {exc}")
        return 2

    print(f"Filas detalle   : {len(detalle)}")
    print(f"Columnas detalle: {len(detalle.columns)}")
    errores += not control(
        "Contrato exacto detalle", list(detalle.columns) == COLUMNAS_DETALLE
    )
    errores += not control(
        "Misma cantidad CORE_CHECKIN/detalle",
        len(detalle) == len(core_checkin),
        f"CORE={len(core_checkin)} | detalle={len(detalle)}",
    )

    duplicadas = int(
        detalle.duplicated(["Cliente", "FechaHoraCheckIn"], keep=False).sum()
    )
    nulas_key = int(detalle[["Cliente", "FechaHoraCheckIn"]].isna().any(axis=1).sum())
    print(f"KEY duplicadas detalle: {duplicadas}")
    print(f"KEY nulas detalle     : {nulas_key}")
    errores += not control("KEY detalle unica", duplicadas == 0)
    errores += not control("KEY detalle completa", nulas_key == 0)

    estados = set(detalle["EstadoRuta"].dropna().astype(str).unique())
    estados_desconocidos = estados - ESTADOS_ESPERADOS
    print(f"Estados encontrados   : {sorted(estados)}")
    print(f"Estados desconocidos  : {sorted(estados_desconocidos)}")
    errores += not control("Catalogo EstadoRuta valido", not estados_desconocidos)

    conteo_estados = detalle["EstadoRuta"].value_counts(dropna=False)
    print("\nDistribucion EstadoRuta:")
    print(conteo_estados.to_string())

    en_ruta_esperado = detalle["EstadoRuta"].eq("EN_RUTA")
    fuera_esperado = detalle["EstadoRuta"].isin(
        ["FUERA_RUTA_CLIENTE", "SIN_RUTA_ESE_DIA"]
    )
    dif_en_ruta = int((detalle["VisitaEnRuta"].astype(bool) != en_ruta_esperado).sum())
    dif_fuera = int((detalle["VisitaFueraRuta"].astype(bool) != fuera_esperado).sum())
    errores += not control(
        "Bandera VisitaEnRuta", dif_en_ruta == 0, f"diferencias={dif_en_ruta}"
    )
    errores += not control(
        "Bandera VisitaFueraRuta", dif_fuera == 0, f"diferencias={dif_fuera}"
    )

    mapeables = detalle["CodVendedor"].notna()
    particion_mapeables = detalle.loc[mapeables, "VisitaEnRuta"].astype(
        "Int64"
    ) + detalle.loc[mapeables, "VisitaFueraRuta"].astype("Int64")
    errores += not control(
        "Visitas mapeables particionadas En Ruta/Fuera Ruta",
        bool((particion_mapeables == 1).all()),
    )

    titulo("4. VALIDACION DIRECTA DEL CRUCE CON CORE_RUTAS")
    cod_checkin = normalizar_codigo_vendedor(core_checkin["CodVendedorCHKIN"])
    visitas_clave = pd.DataFrame(
        {
            "Cliente": core_checkin["Cliente"].astype("Int64"),
            "CodVendedor": cod_checkin,
            "Fecha": pd.to_datetime(
                core_checkin["FechaVisita"], errors="coerce"
            ).dt.normalize(),
        }
    )
    rutas_clave = set(
        map(
            tuple,
            core_rutas[["Cliente", "CodVendedor", "FechaRuta"]]
            .assign(FechaRuta=lambda x: pd.to_datetime(x["FechaRuta"]).dt.normalize())
            .itertuples(index=False, name=None),
        )
    )
    esperado_en_ruta = pd.Series(
        [
            False if pd.isna(v) else (c, v, f) in rutas_clave
            for c, v, f in visitas_clave.itertuples(index=False, name=None)
        ],
        index=detalle.index,
        dtype="boolean",
    )
    diferencias_cruce = int(
        (detalle["VisitaEnRuta"] != esperado_en_ruta).fillna(True).sum()
    )
    errores += not control(
        "Clasificacion EN_RUTA coincide con clave Cliente+Vendedor+Fecha",
        diferencias_cruce == 0,
        f"diferencias={diferencias_cruce}",
    )

    titulo("5. RESUMEN POR VENDEDOR")
    try:
        resumen = construir_resumen_checkin_vendedores(
            core_checkin,
            core_rutas,
            maestros,
        )
    except Exception as exc:
        print(
            f"[ERROR] construir_resumen_checkin_vendedores: {type(exc).__name__}: {exc}"
        )
        return 2

    print(f"Filas resumen   : {len(resumen)}")
    print(f"Columnas resumen: {len(resumen.columns)}")
    errores += not control(
        "Contrato exacto resumen", list(resumen.columns) == COLUMNAS_RESUMEN
    )
    errores += not control(
        "Una fila por vendedor del maestro",
        len(resumen) == len(maestro),
        f"maestro={len(maestro)} | resumen={len(resumen)}",
    )
    errores += not control(
        "CodVend resumen sin duplicados", not resumen["CodVend"].duplicated().any()
    )

    cod_maestro = set(maestro["CodVend"].dropna().astype(int).tolist())
    cod_resumen = set(resumen["CodVend"].dropna().astype(int).tolist())
    errores += not control(
        "Conservacion exacta del universo maestro",
        cod_maestro == cod_resumen,
        f"faltan={len(cod_maestro - cod_resumen)} | sobran={len(cod_resumen - cod_maestro)}",
    )

    controles_conteo = {
        "EnRuta + FueraRuta = VisitasUnicas": (
            resumen["VisitasEnRuta"] + resumen["VisitasFueraRuta"]
            == resumen["VisitasUnicas"]
        ).all(),
        "FueraRutaCliente + SinRutaDia = FueraRuta": (
            resumen["VisitasFueraRutaCliente"] + resumen["VisitasSinRutaEseDia"]
            == resumen["VisitasFueraRuta"]
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
    for nombre, valido in controles_conteo.items():
        errores += not control(nombre, bool(valido))

    titulo("6. PORCENTAJES")
    pares = [
        ("VisitasEnRuta", "VisitasUnicas", "PctVisitasEnRuta"),
        ("VisitasFueraRuta", "VisitasUnicas", "PctVisitasFueraRuta"),
        ("CheckInValidos", "VisitasUnicas", "PctCheckInValidos"),
        ("CheckOutValidos", "VisitasUnicas", "PctCheckOutValidos"),
        ("VisitasValidas", "VisitasUnicas", "PctVisitasValidas"),
    ]
    for numerador, denominador, porcentaje in pares:
        diferencias = comparar_porcentaje(resumen, numerador, denominador, porcentaje)
        rango_valido = bool(
            resumen[porcentaje].between(0, 1, inclusive="both").fillna(False).all()
        )
        errores += not control(
            f"Formula {porcentaje}", diferencias == 0, f"diferencias={diferencias}"
        )
        errores += not control(f"Rango 0..1 {porcentaje}", rango_valido)

    pct_particion = resumen["PctVisitasEnRuta"] + resumen["PctVisitasFueraRuta"]
    esperado_pct = pd.Series(
        np.where(resumen["VisitasUnicas"] > 0, 1.0, 0.0),
        index=resumen.index,
    )
    diferencias_particion = int(
        (~np.isclose(pct_particion.astype(float), esperado_pct)).sum()
    )
    errores += not control(
        "PctEnRuta + PctFueraRuta",
        diferencias_particion == 0,
        f"diferencias={diferencias_particion}",
    )

    titulo("7. CONCILIACION GLOBAL DETALLE vs RESUMEN")
    detalle_mapeado = detalle.loc[
        detalle["CodVendedor"].isin(resumen["CodVend"])
    ].copy()
    globales = {
        "VisitasUnicas": len(detalle_mapeado),
        "VisitasEnRuta": int(detalle_mapeado["VisitaEnRuta"].sum()),
        "VisitasFueraRuta": int(detalle_mapeado["VisitaFueraRuta"].sum()),
        "CheckInValidos": int(detalle_mapeado["CheckInCorrecto"].sum()),
        "CheckOutValidos": int(detalle_mapeado["CheckOutCorrecto"].sum()),
        "VisitasValidas": int(detalle_mapeado["VisitaValida"].sum()),
    }
    for columna, esperado in globales.items():
        real = int(resumen[columna].sum())
        errores += not control(
            f"Conciliacion {columna}",
            real == esperado,
            f"detalle={esperado} | resumen={real}",
        )

    print("\nTotales globales:")
    for columna, valor in globales.items():
        print(f"{columna:<28}: {valor}")

    titulo("8. CODIGOS CHKIN NO MAPEABLES")
    no_mapeables = detalle.loc[
        detalle["EstadoRuta"].eq("VENDEDOR_NO_MAPEABLE"),
        "CodVendedorCHKIN",
    ]
    print(f"Visitas vendedor no mapeable: {len(no_mapeables)}")
    print(f"Codigos distintos            : {no_mapeables.nunique(dropna=True)}")
    if not no_mapeables.empty:
        print("Muestra:")
        print(no_mapeables.value_counts(dropna=False).head(20).to_string())
    print("NOTA: se informan, pero no se atribuyen a vendedores del maestro.")

    titulo("9. FUNCION PRODUCTIVA")
    try:
        if hasattr(obtener_business_rules_checkin, "clear"):
            obtener_business_rules_checkin.clear()
        productivo = obtener_business_rules_checkin()
    except Exception as exc:
        print(f"[ERROR] obtener_business_rules_checkin: {type(exc).__name__}: {exc}")
        return 2

    det_prod = productivo.get("detalle_visitas")
    res_prod = productivo.get("resumen_vendedores")
    errores += not control(
        "Salida productiva contiene detalle_visitas",
        isinstance(det_prod, pd.DataFrame),
    )
    errores += not control(
        "Salida productiva contiene resumen_vendedores",
        isinstance(res_prod, pd.DataFrame),
    )
    if isinstance(det_prod, pd.DataFrame):
        errores += not control(
            "Misma cantidad detalle directo/productivo",
            len(det_prod) == len(detalle),
        )
    if isinstance(res_prod, pd.DataFrame):
        errores += not control(
            "Misma cantidad resumen directo/productivo",
            len(res_prod) == len(resumen),
        )
        errores += not control(
            "Mismos CodVend resumen directo/productivo",
            set(res_prod["CodVend"].dropna().astype(int)) == cod_resumen,
        )

    titulo("10. VEREDICTO")
    duracion = time.perf_counter() - inicio
    if errores == 0:
        print("BUSINESS_RULES_CHECKIN APROBADO")
        print(
            "La clasificacion de ruta, los agregados por vendedor, los porcentajes "
            "y la conservacion del universo maestro son consistentes."
        )
        print(f"Duracion total: {duracion:.2f} s")
        return 0

    print("BUSINESS_RULES_CHECKIN NO APROBADO")
    print(f"Controles fallidos: {errores}")
    print(f"Duracion total: {duracion:.2f} s")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nAuditoria interrumpida por el usuario.")
        raise SystemExit(130)
    except Exception as exc:
        print("\n" + "=" * 96)
        print("ERROR NO CONTROLADO EN AU_BUSINESS_RULES_CHECKIN")
        print("=" * 96)
        print(f"{type(exc).__name__}: {exc}")
        raise
