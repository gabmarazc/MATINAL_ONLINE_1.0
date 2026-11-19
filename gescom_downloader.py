#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gescom_downloader.py

Descarga desde GESCOM Web:
1. VTA del mes calendario corriente -> data/VTA/YYYY-MM.csv
2. ALTAS del mes calendario corriente -> data/ALTAS.xlsx
3. UNIVERSO actual -> data/UNIVERSO.xlsx

Reglas:
- Una sola autenticacion por ejecucion.
- VTA conserva su logica mensual dinamica.
- ALTAS se materializa desde el JSON del datasource "Creacion".
- Toda escritura se hace primero en un temporal.
- Ante un error, el archivo productivo anterior permanece intacto.
- No modifica SQLite ni VTA_CONSOLIDADO.parquet.
"""

from __future__ import annotations

import calendar
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from openpyxl import Workbook, load_workbook
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


# ============================================================
# CONFIGURACION MANUAL
# ============================================================
# Complete estos valores en su copia local. Mantener las comillas.
GESCOM_USUARIO = "gazcona"
GESCOM_PASSWORD = "Vecinos2015!"

# False: se ejecuta una vez y termina.
# True: repite el ciclo completo cada X minutos.
MODO_CONTINUO = False
INTERVALO_MINUTOS = 60

# En la primera prueba conviene False para observar el login.
# Tras validar el proceso puede cambiarse a True.
NAVEGADOR_OCULTO = False

# Activacion independiente de reportes.
DESCARGAR_VTA = True
DESCARGAR_ALTAS = True
DESCARGAR_UNIVERSO = True
DESCARGAR_TP = True

# Rutas.
BASE_DIR = Path(__file__).resolve().parent
CARPETA_DATA = BASE_DIR / "data"
CARPETA_VTA = CARPETA_DATA / "VTA"
CARPETA_LOGS = BASE_DIR / "logs"
DESTINO_ALTAS = CARPETA_DATA / "ALTAS.xlsx"
DESTINO_UNIVERSO = CARPETA_DATA / "UNIVERSO.xlsx"
DESTINO_TP = CARPETA_DATA / "TP.xlsx"

# Tiempos.
TIMEOUT_NAVEGADOR_MS = 90_000
TIMEOUT_DESCARGA_SEGUNDOS = 600

# Endpoints GESCOM.
GESCOM_INICIO_URL = "https://mabelherdi.gescom.online/"
GESCOM_REPORTE_URL = "https://mabelherdi.gescom.online/data/cmd/report/render"

# IDs de reportes capturados empiricamente.
GESCOM_REPORTE_VTA_ID = "2b43054b-4bb9-4d10-ac60-d300a4b2d1a3"
GESCOM_REPORTE_ALTAS_ID = "9b4f001a-5f31-4a76-b884-9df5d8b3896c"
GESCOM_REPORTE_UNIVERSO_ID = "540aa299-843e-4f6f-8b2f-44fcf092049d"
GESCOM_REPORTE_TP_ID = "81221fe2-5545-47ec-a149-6c95d47afb44"

# Contrato de ALTAS.
ALTAS_DATASOURCE = "Creacion"
ALTAS_COLUMNAS_ESPERADAS = [
    "Codigo",
    "Nombre",
    "Direccion",
    "Localidad",
    "Zona",
    "Vendedor",
    "Canal",
    "Subcanal",
    "Estado",
    "Fecha",
    "Creador",
    "Modificador",
]

# Contrato literal de UNIVERSO. Se preservan nombres, orden y duplicados.
UNIVERSO_DATASOURCE = "Principal"
UNIVERSO_COLUMNAS_ESPERADAS = [
    "Codigo",
    "Razon_Social",
    "Direccion",
    "Localidad",
    "Telefono",
    "SubRamo",
    "Ramo",
    "SubRamo",
    "Sede",
    "CondIva",
    "TipoDoc",
    "NumDocumento",
    "CondPago",
    "CodigoRuta",
    "Ruta",
    "Orden",
    "Lista",
    "SegmentoClienteCodigo",
    "SegmentoClienteDescripcion",
    "codven",
    "Vendedor",
    "Latitud",
    "Longitud",
    "Geocodificado",
    "SubSegmento",
    "DigitalID",
]

# Contrato literal de TP.
TP_DATASOURCE = "Principal"
TP_COLUMNAS_ESPERADAS = [
    "Cliente",
    "Razon_Social",
    "Direccion",
    "Vendedor_ID",
    "Tipologia",
    "SubCanal",
    "Segmento",
    "porcentajePortafolio",
    "CumplimientoEstandar",
    "rackadecuado",
    "rackposicion",
    "planograma",
    "preciosvisibles",
    "rotacionpreventiva",
    "Puntuacion",
    "TiendaPerfecta",
    "SupOk",
    "ultimafechacenso",
    "frecuencia",
    "SubCanalTiendaPerfecta",
    "FechaUltimaValidacionSupervisorJDRPromotor",
    "Usuario",
    "EstandarSOD",
    "PuntajeSOD",
    "CumpleTiendaPerfecta",
]

# Validacion basica de VTA.
TAMANO_MINIMO_VTA_BYTES = 1_024


# ============================================================
# LOGGING
# ============================================================
def configurar_logging() -> None:
    CARPETA_LOGS.mkdir(parents=True, exist_ok=True)
    log_path = CARPETA_LOGS / "gescom_downloader.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )


# ============================================================
# PERIODO Y PAYLOADS
# ============================================================
def calcular_periodo_mes_corriente() -> tuple[datetime, datetime, str]:
    ahora = datetime.now()
    ultimo_dia = calendar.monthrange(ahora.year, ahora.month)[1]
    fecha_inicio = datetime(ahora.year, ahora.month, 1)
    fecha_fin = datetime(ahora.year, ahora.month, ultimo_dia)
    nombre_vta = f"{ahora.year:04d}-{ahora.month:02d}.csv"
    return fecha_inicio, fecha_fin, nombre_vta


def fecha_gescom(fecha: datetime) -> str:
    # Contrato observado: fecha local Argentina representada a las 03:00 UTC.
    return fecha.strftime("%Y-%m-%dT03:00:00.000Z")


def construir_payload_vta(
    fecha_inicio: datetime,
    fecha_fin: datetime,
) -> dict[str, Any]:
    return {
        "id": GESCOM_REPORTE_VTA_ID,
        "reportInput": {
            "filtersInput": {"FiltroVentas": []},
            "parameters": {
                "empId": 0,
                "fechaIni": fecha_gescom(fecha_inicio),
                "fechaFin": fecha_gescom(fecha_fin),
                "facturadaId": 2,
                "supervisorId": 0,
                "sedeId": 0,
                "tipoVentaId": 0,
                "ventaEmpl": 0,
                "cliActivos": 0,
                "proveedorId": 0,
                "clienteId": 0,
            },
        },
    }


def construir_payload_altas(
    fecha_inicio: datetime,
    fecha_fin: datetime,
) -> dict[str, Any]:
    return {
        "id": GESCOM_REPORTE_ALTAS_ID,
        "reportInput": {
            "filtersInput": {"FiltroVentas": []},
            "parameters": {
                "fechaIni": fecha_gescom(fecha_inicio),
                "fechaFin": fecha_gescom(fecha_fin),
                "clienteId": 0,
                "rutaId": 0,
            },
        },
    }


def construir_payload_universo() -> dict[str, Any]:
    return {
        "id": GESCOM_REPORTE_UNIVERSO_ID,
        "reportInput": {
            "filtersInput": {"FiltroVentas": []},
            "parameters": {
                "vendedorId": 0,
                "rutaId": 0,
                "GrupoFuerzaVentaId": 0,
                "activoId": 1,
                "tags": [],
            },
        },
    }


def construir_payload_tp() -> dict[str, Any]:
    return {
        "id": GESCOM_REPORTE_TP_ID,
        "reportInput": {
            "filtersInput": {},
            "parameters": {"sedeId": 0, "soloTP": 0},
        },
    }


# ============================================================
# AUTENTICACION
# ============================================================
def validar_configuracion() -> None:
    if not GESCOM_USUARIO.strip() or GESCOM_USUARIO == "PONER_USUARIO_AQUI":
        raise RuntimeError("Complete GESCOM_USUARIO al inicio del script.")

    if not GESCOM_PASSWORD or GESCOM_PASSWORD == "PONER_CONTRASENA_AQUI":
        raise RuntimeError("Complete GESCOM_PASSWORD al inicio del script.")

    if INTERVALO_MINUTOS <= 0:
        raise RuntimeError("INTERVALO_MINUTOS debe ser mayor que cero.")

    if (
        not DESCARGAR_VTA
        and not DESCARGAR_ALTAS
        and not DESCARGAR_UNIVERSO
        and not DESCARGAR_TP
    ):
        raise RuntimeError("Debe habilitarse al menos un reporte.")


def completar_campo_usuario(page) -> None:
    selectores = [
        'input[name="username"]',
        'input[id="username"]',
        'input[type="text"]',
        'input[type="email"]',
    ]
    for selector in selectores:
        locator = page.locator(selector).first
        try:
            if locator.is_visible(timeout=2_000):
                locator.fill(GESCOM_USUARIO)
                return
        except Exception:
            continue
    raise RuntimeError("No se encontro el campo 'Usuario o email'.")


def completar_campo_password(page) -> None:
    selectores = [
        'input[name="password"]',
        'input[id="password"]',
        'input[type="password"]',
    ]
    for selector in selectores:
        locator = page.locator(selector).first
        try:
            if locator.is_visible(timeout=2_000):
                locator.fill(GESCOM_PASSWORD)
                return
        except Exception:
            continue
    raise RuntimeError("No se encontro el campo 'Contrasena'.")


def pulsar_iniciar_sesion(page) -> None:
    candidatos = [
        page.get_by_role("button", name="Iniciar sesión", exact=False).first,
        page.get_by_role("button", name="Iniciar sesion", exact=False).first,
        page.get_by_text("Iniciar sesión", exact=True).first,
        page.locator('button[type="submit"], input[type="submit"]').first,
    ]
    for boton in candidatos:
        try:
            if boton.is_visible(timeout=3_000):
                boton.click()
                return
        except Exception:
            continue
    raise RuntimeError("No se encontro el boton 'Iniciar sesion'.")


def obtener_sesion_autenticada() -> requests.Session:
    logging.info("Iniciando autenticacion en GESCOM...")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=NAVEGADOR_OCULTO)
        context = browser.new_context(locale="es-AR")
        context.set_default_timeout(TIMEOUT_NAVEGADOR_MS)
        page = context.new_page()

        try:
            page.goto(
                GESCOM_INICIO_URL,
                wait_until="domcontentloaded",
                timeout=TIMEOUT_NAVEGADOR_MS,
            )

            completar_campo_usuario(page)
            pulsar_iniciar_sesion(page)

            page.locator('input[type="password"]').wait_for(
                state="visible",
                timeout=TIMEOUT_NAVEGADOR_MS,
            )
            completar_campo_password(page)
            pulsar_iniciar_sesion(page)

            page.wait_for_url(
                "https://mabelherdi.gescom.online/**",
                timeout=TIMEOUT_NAVEGADOR_MS,
            )
            page.wait_for_load_state(
                "domcontentloaded",
                timeout=TIMEOUT_NAVEGADOR_MS,
            )

            cookies = context.cookies()
            nombres_cookies = {cookie["name"] for cookie in cookies}
            if "session" not in nombres_cookies:
                raise RuntimeError(
                    "El login termino, pero no se obtuvo la cookie de sesion esperada."
                )

            user_agent = page.evaluate("navigator.userAgent")

            session = requests.Session()
            session.headers.update(
                {
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json;charset=UTF-8",
                    "Origin": "https://mabelherdi.gescom.online",
                    "Referer": "https://mabelherdi.gescom.online/",
                    "User-Agent": user_agent,
                    "X-Requested-With": "XMLHttpRequest",
                }
            )

            for cookie in cookies:
                session.cookies.set(
                    name=cookie["name"],
                    value=cookie["value"],
                    domain=cookie.get("domain"),
                    path=cookie.get("path", "/"),
                )

            logging.info("Autenticacion GESCOM: OK")
            return session

        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Tiempo agotado durante el login. Revise credenciales, conexion o cambios en la pantalla."
            ) from exc
        finally:
            context.close()
            browser.close()


# ============================================================
# VTA
# ============================================================
def parece_html(inicio: bytes) -> bool:
    muestra = inicio.lstrip().lower()
    return muestra.startswith(b"<!doctype html") or muestra.startswith(b"<html")


def validar_vta_temporal(path: Path, content_type: str) -> None:
    if not path.exists():
        raise RuntimeError("GESCOM no genero el temporal de VTA.")

    tamano = path.stat().st_size
    if tamano < TAMANO_MINIMO_VTA_BYTES:
        raise RuntimeError(
            f"VTA es demasiado pequeno ({tamano} bytes); no se reemplaza el CSV existente."
        )

    with path.open("rb") as archivo:
        inicio = archivo.read(4_096)

    if parece_html(inicio):
        raise RuntimeError("GESCOM devolvio HTML en lugar del CSV de VTA.")

    content_type_normalizado = (content_type or "").lower()
    tipos_admitidos = ("text/csv", "application/csv", "application/octet-stream")
    if content_type_normalizado and not any(
        tipo in content_type_normalizado for tipo in tipos_admitidos
    ):
        raise RuntimeError(f"Content-Type inesperado para VTA: {content_type!r}.")

    lineas = inicio.splitlines()
    primera_linea = lineas[0] if lineas else b""
    if not any(separador in primera_linea for separador in (b",", b";", b"\t")):
        raise RuntimeError("La primera linea de VTA no parece una cabecera CSV valida.")


def descargar_vta(
    session: requests.Session,
    fecha_inicio: datetime,
    fecha_fin: datetime,
    nombre_archivo: str,
) -> Path:
    destino = CARPETA_VTA / nombre_archivo
    temporal = CARPETA_VTA / f".{nombre_archivo}.descarga.tmp"
    payload = construir_payload_vta(fecha_inicio, fecha_fin)

    CARPETA_VTA.mkdir(parents=True, exist_ok=True)
    logging.info("[VTA] Destino: %s", destino)
    logging.info("[VTA] Destino existente: %s", "SI" if destino.exists() else "NO")

    if temporal.exists():
        temporal.unlink()

    try:
        with session.post(
            GESCOM_REPORTE_URL,
            json=payload,
            stream=True,
            timeout=(30, TIMEOUT_DESCARGA_SEGUNDOS),
        ) as respuesta:
            if respuesta.status_code != 200:
                detalle = respuesta.text[:500].replace("\n", " ")
                raise RuntimeError(
                    f"[VTA] GESCOM respondio HTTP {respuesta.status_code}: {detalle}"
                )

            content_type = respuesta.headers.get("Content-Type", "")
            logging.info("[VTA] Content-Type: %s", content_type or "NO INFORMADO")

            bytes_descargados = 0
            with temporal.open("wb") as archivo:
                for bloque in respuesta.iter_content(chunk_size=1024 * 1024):
                    if not bloque:
                        continue
                    archivo.write(bloque)
                    bytes_descargados += len(bloque)

            logging.info(
                "[VTA] Descarga finalizada: %.2f MB",
                bytes_descargados / (1024 * 1024),
            )

        validar_vta_temporal(temporal, content_type)
        logging.info("[VTA] Validacion: OK")
        os.replace(temporal, destino)
        logging.info("[VTA] Archivo actualizado: %s", destino)
        return destino

    except Exception:
        if temporal.exists():
            try:
                temporal.unlink()
            except OSError:
                logging.exception("[VTA] No se pudo eliminar el temporal: %s", temporal)
        raise


# ============================================================
# ALTAS
# ============================================================
def extraer_tabla_altas(respuesta_json: Any) -> tuple[list[str], list[list[Any]]]:
    if not isinstance(respuesta_json, dict):
        raise RuntimeError("[ALTAS] La respuesta JSON no es un objeto.")

    main_datasource = respuesta_json.get("mainDatasource")
    if main_datasource != ALTAS_DATASOURCE:
        raise RuntimeError(
            f"[ALTAS] mainDatasource inesperado: {main_datasource!r}; "
            f"se esperaba {ALTAS_DATASOURCE!r}."
        )

    datasources = respuesta_json.get("datasources")
    if not isinstance(datasources, list):
        raise RuntimeError("[ALTAS] No existe una lista 'datasources' valida.")

    datasource = next(
        (
            item
            for item in datasources
            if isinstance(item, dict) and item.get("name") == ALTAS_DATASOURCE
        ),
        None,
    )
    if datasource is None:
        raise RuntimeError("[ALTAS] No se encontro el datasource 'Creacion'.")

    tabla = datasource.get("table")
    if not isinstance(tabla, list) or not tabla:
        raise RuntimeError("[ALTAS] El datasource 'Creacion' no contiene tabla.")

    cabecera = tabla[0]
    filas = tabla[1:]

    if cabecera != ALTAS_COLUMNAS_ESPERADAS:
        raise RuntimeError(
            "[ALTAS] Esquema inesperado. "
            f"Recibido={cabecera!r}; esperado={ALTAS_COLUMNAS_ESPERADAS!r}."
        )

    ancho = len(cabecera)
    for numero_fila, fila in enumerate(filas, start=2):
        if not isinstance(fila, list):
            raise RuntimeError(f"[ALTAS] La fila {numero_fila} no es una lista.")
        if len(fila) != ancho:
            raise RuntimeError(
                f"[ALTAS] La fila {numero_fila} tiene {len(fila)} valores; "
                f"se esperaban {ancho}."
            )

    return list(cabecera), filas


def escribir_altas_xlsx_temporal(
    temporal: Path,
    cabecera: list[str],
    filas: list[list[Any]],
) -> None:
    workbook = Workbook(write_only=True)
    worksheet = workbook.create_sheet(title="ALTAS")
    worksheet.append(cabecera)

    # Se conservan los valores tal como llegan desde GESCOM.
    for fila in filas:
        worksheet.append(fila)

    workbook.save(temporal)


def validar_altas_xlsx(temporal: Path, cantidad_filas_esperada: int) -> None:
    if not temporal.exists() or temporal.stat().st_size == 0:
        raise RuntimeError("[ALTAS] El XLSX temporal no existe o esta vacio.")

    workbook = load_workbook(temporal, read_only=True, data_only=True)
    try:
        if "ALTAS" not in workbook.sheetnames:
            raise RuntimeError("[ALTAS] El XLSX no contiene la hoja 'ALTAS'.")

        worksheet = workbook["ALTAS"]
        iterador = worksheet.iter_rows(values_only=True)
        cabecera_leida = list(next(iterador, ()))

        if cabecera_leida != ALTAS_COLUMNAS_ESPERADAS:
            raise RuntimeError(f"[ALTAS] Cabecera XLSX invalida: {cabecera_leida!r}.")

        filas_leidas = sum(1 for _ in iterador)
        if filas_leidas != cantidad_filas_esperada:
            raise RuntimeError(
                f"[ALTAS] Conteo inconsistente: XLSX={filas_leidas}, "
                f"JSON={cantidad_filas_esperada}."
            )
    finally:
        workbook.close()


def descargar_altas(
    session: requests.Session,
    fecha_inicio: datetime,
    fecha_fin: datetime,
) -> Path:
    destino = DESTINO_ALTAS
    temporal = destino.with_name(f".{destino.stem}.descarga.tmp.xlsx")
    payload = construir_payload_altas(fecha_inicio, fecha_fin)

    CARPETA_DATA.mkdir(parents=True, exist_ok=True)
    logging.info("[ALTAS] Destino: %s", destino)
    logging.info("[ALTAS] Destino existente: %s", "SI" if destino.exists() else "NO")

    if temporal.exists():
        temporal.unlink()

    try:
        respuesta = session.post(
            GESCOM_REPORTE_URL,
            json=payload,
            timeout=(30, TIMEOUT_DESCARGA_SEGUNDOS),
        )

        if respuesta.status_code != 200:
            detalle = respuesta.text[:500].replace("\n", " ")
            raise RuntimeError(
                f"[ALTAS] GESCOM respondio HTTP {respuesta.status_code}: {detalle}"
            )

        content_type = respuesta.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            raise RuntimeError(f"[ALTAS] Content-Type inesperado: {content_type!r}.")

        try:
            respuesta_json = respuesta.json()
        except ValueError as exc:
            raise RuntimeError("[ALTAS] La respuesta no contiene JSON valido.") from exc

        cabecera, filas = extraer_tabla_altas(respuesta_json)
        logging.info("[ALTAS] Filas recibidas: %s", len(filas))

        escribir_altas_xlsx_temporal(temporal, cabecera, filas)
        validar_altas_xlsx(temporal, len(filas))
        logging.info("[ALTAS] Validacion XLSX temporal: OK")

        os.replace(temporal, destino)
        logging.info("[ALTAS] Archivo actualizado: %s", destino)
        return destino

    except Exception:
        if temporal.exists():
            try:
                temporal.unlink()
            except OSError:
                logging.exception(
                    "[ALTAS] No se pudo eliminar el temporal: %s", temporal
                )
        raise


# ============================================================
# UNIVERSO
# ============================================================
def extraer_tabla_universo(respuesta_json: Any) -> tuple[list[str], list[list[Any]]]:
    if not isinstance(respuesta_json, dict):
        raise RuntimeError("[UNIVERSO] La respuesta JSON no es un objeto.")
    if respuesta_json.get("mainDatasource") != UNIVERSO_DATASOURCE:
        raise RuntimeError(
            f"[UNIVERSO] mainDatasource inesperado: {respuesta_json.get('mainDatasource')!r}."
        )
    datasources = respuesta_json.get("datasources")
    if not isinstance(datasources, list):
        raise RuntimeError("[UNIVERSO] No existe una lista 'datasources' valida.")
    datasource = next(
        (
            x
            for x in datasources
            if isinstance(x, dict) and x.get("name") == UNIVERSO_DATASOURCE
        ),
        None,
    )
    if datasource is None:
        raise RuntimeError("[UNIVERSO] No se encontro el datasource 'Principal'.")
    tabla = datasource.get("table")
    if not isinstance(tabla, list) or not tabla:
        raise RuntimeError("[UNIVERSO] El datasource 'Principal' no contiene tabla.")
    cabecera = tabla[0]
    filas = tabla[1:]
    if cabecera != UNIVERSO_COLUMNAS_ESPERADAS:
        raise RuntimeError(
            f"[UNIVERSO] Esquema alterado. Recibido={cabecera!r}; esperado={UNIVERSO_COLUMNAS_ESPERADAS!r}."
        )
    ancho = len(cabecera)
    for n, fila in enumerate(filas, start=2):
        if not isinstance(fila, list) or len(fila) != ancho:
            raise RuntimeError(
                f"[UNIVERSO] Fila {n} invalida; se esperaban exactamente {ancho} valores."
            )
    return list(cabecera), filas


def escribir_universo_xlsx_temporal(
    temporal: Path, cabecera: list[str], filas: list[list[Any]]
) -> None:
    wb = Workbook(write_only=True)
    ws = wb.create_sheet(title="UNIVERSO")
    ws.append(cabecera)
    for fila in filas:
        ws.append(fila)
    wb.save(temporal)


def validar_universo_xlsx(temporal: Path, cantidad_filas_esperada: int) -> None:
    if not temporal.exists() or temporal.stat().st_size == 0:
        raise RuntimeError("[UNIVERSO] El XLSX temporal no existe o esta vacio.")
    wb = load_workbook(temporal, read_only=True, data_only=True)
    try:
        if "UNIVERSO" not in wb.sheetnames:
            raise RuntimeError("[UNIVERSO] Falta la hoja 'UNIVERSO'.")
        it = wb["UNIVERSO"].iter_rows(values_only=True)
        cabecera = list(next(it, ()))
        if cabecera != UNIVERSO_COLUMNAS_ESPERADAS:
            raise RuntimeError(
                f"[UNIVERSO] La cabecera materializada fue alterada: {cabecera!r}."
            )
        filas_leidas = sum(1 for _ in it)
        if filas_leidas != cantidad_filas_esperada:
            raise RuntimeError(
                f"[UNIVERSO] Conteo inconsistente: XLSX={filas_leidas}, JSON={cantidad_filas_esperada}."
            )
    finally:
        wb.close()


def descargar_universo(session: requests.Session) -> Path:
    destino = DESTINO_UNIVERSO
    temporal = destino.with_name(f".{destino.stem}.descarga.tmp.xlsx")
    payload = construir_payload_universo()
    CARPETA_DATA.mkdir(parents=True, exist_ok=True)
    logging.info("[UNIVERSO] Destino: %s", destino)
    logging.info("[UNIVERSO] Destino existente: %s", "SI" if destino.exists() else "NO")
    if temporal.exists():
        temporal.unlink()
    try:
        respuesta = session.post(
            GESCOM_REPORTE_URL, json=payload, timeout=(30, TIMEOUT_DESCARGA_SEGUNDOS)
        )
        if respuesta.status_code != 200:
            raise RuntimeError(
                f"[UNIVERSO] GESCOM respondio HTTP {respuesta.status_code}: {respuesta.text[:500].replace(chr(10), ' ')}"
            )
        content_type = respuesta.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            raise RuntimeError(f"[UNIVERSO] Content-Type inesperado: {content_type!r}.")
        try:
            respuesta_json = respuesta.json()
        except ValueError as exc:
            raise RuntimeError(
                "[UNIVERSO] La respuesta no contiene JSON valido."
            ) from exc
        cabecera, filas = extraer_tabla_universo(respuesta_json)
        logging.info("[UNIVERSO] Filas recibidas: %s", len(filas))
        escribir_universo_xlsx_temporal(temporal, cabecera, filas)
        validar_universo_xlsx(temporal, len(filas))
        logging.info("[UNIVERSO] Validacion literal XLSX temporal: OK")
        os.replace(temporal, destino)
        logging.info("[UNIVERSO] Archivo actualizado sin alterar esquema: %s", destino)
        return destino
    except Exception:
        if temporal.exists():
            try:
                temporal.unlink()
            except OSError:
                logging.exception(
                    "[UNIVERSO] No se pudo eliminar el temporal: %s", temporal
                )
        raise


# ============================================================
# TP
# ============================================================
def extraer_tabla_tp(respuesta_json: Any) -> tuple[list[str], list[list[Any]]]:
    if not isinstance(respuesta_json, dict):
        raise RuntimeError("[TP] La respuesta JSON no es un objeto.")
    if respuesta_json.get("mainDatasource") != TP_DATASOURCE:
        raise RuntimeError(
            f"[TP] mainDatasource inesperado: {respuesta_json.get('mainDatasource')!r}."
        )
    datasources = respuesta_json.get("datasources")
    if not isinstance(datasources, list):
        raise RuntimeError("[TP] No existe una lista datasources valida.")
    datasource = next(
        (
            x
            for x in datasources
            if isinstance(x, dict) and x.get("name") == TP_DATASOURCE
        ),
        None,
    )
    if datasource is None:
        raise RuntimeError("[TP] No se encontro el datasource Principal.")
    tabla = datasource.get("table")
    if not isinstance(tabla, list) or not tabla:
        raise RuntimeError("[TP] El datasource Principal no contiene tabla.")
    cabecera, filas = tabla[0], tabla[1:]
    if cabecera != TP_COLUMNAS_ESPERADAS:
        raise RuntimeError(
            f"[TP] Esquema alterado. Recibido={cabecera!r}; esperado={TP_COLUMNAS_ESPERADAS!r}."
        )
    ancho = len(cabecera)
    for n, fila in enumerate(filas, start=2):
        if not isinstance(fila, list) or len(fila) != ancho:
            raise RuntimeError(f"[TP] Fila {n} invalida; se esperaban {ancho} valores.")
    return list(cabecera), filas


def escribir_tp_xlsx_temporal(
    temporal: Path, cabecera: list[str], filas: list[list[Any]]
) -> None:
    wb = Workbook(write_only=True)
    ws = wb.create_sheet(title="Principal")
    ws.append(cabecera)
    for fila in filas:
        ws.append(fila)
    wb.save(temporal)


def validar_tp_xlsx(temporal: Path, cantidad_filas_esperada: int) -> None:
    if not temporal.exists() or temporal.stat().st_size == 0:
        raise RuntimeError("[TP] El XLSX temporal no existe o esta vacio.")
    wb = load_workbook(temporal, read_only=True, data_only=True)
    try:
        if "Principal" not in wb.sheetnames:
            raise RuntimeError("[TP] Falta la hoja Principal.")
        it = wb["Principal"].iter_rows(values_only=True)
        cabecera = list(next(it, ()))
        if cabecera != TP_COLUMNAS_ESPERADAS:
            raise RuntimeError(f"[TP] Cabecera materializada alterada: {cabecera!r}.")
        filas_leidas = sum(1 for _ in it)
        if filas_leidas != cantidad_filas_esperada:
            raise RuntimeError(
                f"[TP] Conteo inconsistente: XLSX={filas_leidas}, JSON={cantidad_filas_esperada}."
            )
    finally:
        wb.close()


def descargar_tp(session: requests.Session) -> Path:
    destino = DESTINO_TP
    temporal = destino.with_name(f".{destino.stem}.descarga.tmp.xlsx")
    CARPETA_DATA.mkdir(parents=True, exist_ok=True)
    logging.info("[TP] Destino: %s", destino)
    logging.info("[TP] Destino existente: %s", "SI" if destino.exists() else "NO")
    if temporal.exists():
        temporal.unlink()
    try:
        respuesta = session.post(
            GESCOM_REPORTE_URL,
            json=construir_payload_tp(),
            timeout=(30, TIMEOUT_DESCARGA_SEGUNDOS),
        )
        if respuesta.status_code != 200:
            raise RuntimeError(
                f"[TP] GESCOM respondio HTTP {respuesta.status_code}: {respuesta.text[:500].replace(chr(10), ' ')}"
            )
        content_type = respuesta.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            raise RuntimeError(f"[TP] Content-Type inesperado: {content_type!r}.")
        try:
            dato = respuesta.json()
        except ValueError as exc:
            raise RuntimeError("[TP] La respuesta no contiene JSON valido.") from exc
        cabecera, filas = extraer_tabla_tp(dato)
        logging.info("[TP] Filas recibidas: %s", len(filas))
        escribir_tp_xlsx_temporal(temporal, cabecera, filas)
        validar_tp_xlsx(temporal, len(filas))
        logging.info("[TP] Validacion literal XLSX temporal: OK")
        os.replace(temporal, destino)
        logging.info("[TP] Archivo actualizado: %s", destino)
        return destino
    except Exception:
        if temporal.exists():
            try:
                temporal.unlink()
            except OSError:
                logging.exception("[TP] No se pudo eliminar el temporal: %s", temporal)
        raise


# ============================================================
# ORQUESTACION
# ============================================================
def ejecutar_una_vez() -> None:
    validar_configuracion()
    fecha_inicio, fecha_fin, nombre_vta = calcular_periodo_mes_corriente()

    logging.info(
        "Periodo solicitado: %s -> %s",
        fecha_inicio.strftime("%d/%m/%Y"),
        fecha_fin.strftime("%d/%m/%Y"),
    )

    session = obtener_sesion_autenticada()
    errores: list[str] = []

    try:
        if DESCARGAR_VTA:
            try:
                descargar_vta(session, fecha_inicio, fecha_fin, nombre_vta)
            except Exception as exc:
                logging.exception("[VTA] ERROR: %s", exc)
                errores.append(f"VTA: {exc}")

        if DESCARGAR_ALTAS:
            try:
                descargar_altas(session, fecha_inicio, fecha_fin)
            except Exception as exc:
                logging.exception("[ALTAS] ERROR: %s", exc)
                errores.append(f"ALTAS: {exc}")

        if DESCARGAR_UNIVERSO:
            try:
                descargar_universo(session)
            except Exception as exc:
                logging.exception("[UNIVERSO] ERROR: %s", exc)
                errores.append(f"UNIVERSO: {exc}")
        if DESCARGAR_TP:
            try:
                descargar_tp(session)
            except Exception as exc:
                logging.exception("[TP] ERROR: %s", exc)
                errores.append(f"TP: {exc}")
    finally:
        session.close()

    if errores:
        raise RuntimeError(" | ".join(errores))


def main() -> int:
    configurar_logging()
    logging.info("=== GESCOM DOWNLOADER: VTA + ALTAS + UNIVERSO + TP ===")

    while True:
        try:
            ejecutar_una_vez()
            logging.info("Proceso completo finalizado: OK")
        except KeyboardInterrupt:
            logging.info("Proceso interrumpido por el usuario.")
            return 130
        except Exception as exc:
            logging.exception("Proceso completo finalizado con ERROR: %s", exc)
            logging.error(
                "Los archivos productivos previos permanecen intactos para los reportes fallidos."
            )
            if not MODO_CONTINUO:
                return 1

        if not MODO_CONTINUO:
            return 0

        espera_segundos = INTERVALO_MINUTOS * 60
        logging.info("Proxima ejecucion en %s minutos.", INTERVALO_MINUTOS)
        try:
            time.sleep(espera_segundos)
        except KeyboardInterrupt:
            logging.info("Proceso continuo detenido por el usuario.")
            return 130


if __name__ == "__main__":
    raise SystemExit(main())
