#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gescom_vta_downloader.py

Descarga el reporte "Detallado de ventas extendido" de GESCOM Web para
el mes calendario corriente y lo guarda como data/VTA/YYYY-MM.csv.

Contrato:
- Solo escribe el CSV del mes corriente.
- Si el archivo ya existe, lo reemplaza de forma atomica.
- Si no existe, lo crea.
- No modifica meses historicos, SQLite ni VTA_CONSOLIDADO.parquet.
- Ante un error conserva intacto el archivo mensual previo.
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
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


# ============================================================
# CONFIGURACION MANUAL
# ============================================================
# Complete estos dos valores en su copia local.
GESCOM_USUARIO = "gazcona"
GESCOM_PASSWORD = "Vecinos2015!"

# False: se ejecuta una vez y termina. Recomendado para pruebas y
# para usar luego con el Programador de tareas de Windows.
# True: queda ejecutandose y repite la descarga cada X minutos.
MODO_CONTINUO = False
INTERVALO_MINUTOS = 60

# Durante la primera prueba se recomienda False para ver el navegador.
# Cuando el proceso este validado, puede cambiarse a True.
NAVEGADOR_OCULTO = False

# Rutas y tiempos.
BASE_DIR = Path(__file__).resolve().parent
CARPETA_VTA = BASE_DIR / "data" / "VTA"
CARPETA_LOGS = BASE_DIR / "logs"
TIMEOUT_NAVEGADOR_MS = 90_000
TIMEOUT_DESCARGA_SEGUNDOS = 600

# Reporte capturado empiricamente desde GESCOM.
GESCOM_INICIO_URL = "https://mabelherdi.gescom.online/"
GESCOM_REPORTE_URL = "https://mabelherdi.gescom.online/data/cmd/report/render"
GESCOM_REPORTE_ID = "2b43054b-4bb9-4d10-ac60-d300a4b2d1a3"

# Validacion basica de descarga. El reporte real observado es grande;
# este minimo solo evita aceptar respuestas vacias o paginas de error.
TAMANO_MINIMO_BYTES = 1_024


# ============================================================
# LOGGING
# ============================================================
def configurar_logging() -> None:
    CARPETA_LOGS.mkdir(parents=True, exist_ok=True)
    log_path = CARPETA_LOGS / "gescom_vta_downloader.log"

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
# PERIODO Y PAYLOAD
# ============================================================
def calcular_periodo_mes_corriente() -> tuple[datetime, datetime, str]:
    ahora = datetime.now()
    ultimo_dia = calendar.monthrange(ahora.year, ahora.month)[1]

    fecha_inicio = datetime(ahora.year, ahora.month, 1)
    fecha_fin = datetime(ahora.year, ahora.month, ultimo_dia)
    nombre_archivo = f"{ahora.year:04d}-{ahora.month:02d}.csv"

    return fecha_inicio, fecha_fin, nombre_archivo


def fecha_gescom(fecha: datetime) -> str:
    # GESCOM envio empiricamente las fechas locales de Argentina como
    # 03:00:00.000Z. Se conserva exactamente ese contrato observado.
    return fecha.strftime("%Y-%m-%dT03:00:00.000Z")


def construir_payload(fecha_inicio: datetime, fecha_fin: datetime) -> dict[str, Any]:
    return {
        "id": GESCOM_REPORTE_ID,
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
    boton = page.get_by_role("button", name="Iniciar sesion", exact=False).first
    try:
        if boton.is_visible(timeout=3_000):
            boton.click()
            return
    except Exception:
        pass

    # El texto visible puede incluir tilde aunque el selector accesible varie.
    boton = page.get_by_text("Iniciar sesión", exact=True).first
    try:
        if boton.is_visible(timeout=3_000):
            boton.click()
            return
    except Exception:
        pass

    submit = page.locator('button[type="submit"], input[type="submit"]').first
    try:
        if submit.is_visible(timeout=3_000):
            submit.click()
            return
    except Exception:
        pass

    raise RuntimeError("No se encontro el boton 'Iniciar sesion'.")


def obtener_sesion_autenticada() -> tuple[requests.Session, str]:
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

            # Login correcto: la navegacion debe salir de auth.gescom.online
            # y volver al tenant mabelherdi.gescom.online.
            page.wait_for_url(
                "https://mabelherdi.gescom.online/**",
                timeout=TIMEOUT_NAVEGADOR_MS,
            )
            page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAVEGADOR_MS)

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
            return session, user_agent

        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "Tiempo agotado durante el login. Revise credenciales, conexion o cambios en la pantalla."
            ) from exc
        finally:
            context.close()
            browser.close()


# ============================================================
# DESCARGA Y VALIDACION
# ============================================================
def parece_html(inicio: bytes) -> bool:
    muestra = inicio.lstrip().lower()
    return muestra.startswith(b"<!doctype html") or muestra.startswith(b"<html")


def validar_archivo_temporal(path: Path, content_type: str) -> None:
    if not path.exists():
        raise RuntimeError("GESCOM no genero el archivo temporal.")

    tamano = path.stat().st_size
    if tamano < TAMANO_MINIMO_BYTES:
        raise RuntimeError(
            f"La descarga es demasiado pequena ({tamano} bytes); no se reemplaza el CSV existente."
        )

    with path.open("rb") as archivo:
        inicio = archivo.read(4_096)

    if parece_html(inicio):
        raise RuntimeError(
            "GESCOM devolvio HTML en lugar de CSV; posiblemente la sesion expiro."
        )

    content_type_normalizado = (content_type or "").lower()
    tipos_admitidos = ("text/csv", "application/csv", "application/octet-stream")
    if content_type_normalizado and not any(
        tipo in content_type_normalizado for tipo in tipos_admitidos
    ):
        raise RuntimeError(
            f"Content-Type inesperado: {content_type!r}. No se reemplaza el archivo."
        )

    # Control estructural minimo sobre la primera linea. Admite CSV separado
    # por coma, punto y coma o tabulacion.
    primera_linea = inicio.splitlines()[0] if inicio.splitlines() else b""
    if not any(separador in primera_linea for separador in (b",", b";", b"\t")):
        raise RuntimeError("La primera linea no parece una cabecera CSV valida.")


def descargar_reporte(session: requests.Session) -> Path:
    fecha_inicio, fecha_fin, nombre_archivo = calcular_periodo_mes_corriente()
    destino = CARPETA_VTA / nombre_archivo
    temporal = CARPETA_VTA / f".{nombre_archivo}.descarga.tmp"
    payload = construir_payload(fecha_inicio, fecha_fin)

    CARPETA_VTA.mkdir(parents=True, exist_ok=True)

    logging.info(
        "Periodo solicitado: %s -> %s",
        fecha_inicio.strftime("%d/%m/%Y"),
        fecha_fin.strftime("%d/%m/%Y"),
    )
    logging.info("Destino mensual: %s", destino)
    logging.info("Destino existente: %s", "SI" if destino.exists() else "NO")

    if temporal.exists():
        temporal.unlink()

    try:
        with session.post(
            GESCOM_REPORTE_URL,
            data=json.dumps(payload, ensure_ascii=False),
            stream=True,
            timeout=(30, TIMEOUT_DESCARGA_SEGUNDOS),
        ) as respuesta:
            if respuesta.status_code != 200:
                detalle = respuesta.text[:500].replace("\n", " ")
                raise RuntimeError(
                    f"GESCOM respondio HTTP {respuesta.status_code}: {detalle}"
                )

            content_type = respuesta.headers.get("Content-Type", "")
            logging.info("Content-Type recibido: %s", content_type or "NO INFORMADO")

            bytes_descargados = 0
            with temporal.open("wb") as archivo:
                for bloque in respuesta.iter_content(chunk_size=1024 * 1024):
                    if not bloque:
                        continue
                    archivo.write(bloque)
                    bytes_descargados += len(bloque)

            logging.info(
                "Descarga finalizada: %.2f MB",
                bytes_descargados / (1024 * 1024),
            )

        validar_archivo_temporal(temporal, content_type)
        logging.info("Validacion del CSV temporal: OK")

        # Reemplazo atomico en el mismo volumen. Si destino no existe, lo crea.
        os.replace(temporal, destino)
        logging.info("Archivo mensual materializado correctamente: %s", destino)
        return destino

    except Exception:
        if temporal.exists():
            try:
                temporal.unlink()
            except OSError:
                logging.exception(
                    "No se pudo eliminar el temporal fallido: %s", temporal
                )
        raise


def ejecutar_una_vez() -> None:
    validar_configuracion()
    session, _ = obtener_sesion_autenticada()
    try:
        descargar_reporte(session)
    finally:
        session.close()


def main() -> int:
    configurar_logging()
    logging.info("=== GESCOM VTA DOWNLOADER ===")

    while True:
        try:
            ejecutar_una_vez()
            logging.info("Proceso finalizado: OK")
        except KeyboardInterrupt:
            logging.info("Proceso interrumpido por el usuario.")
            return 130
        except Exception as exc:
            logging.exception("Proceso finalizado con ERROR: %s", exc)
            logging.error("El CSV mensual previo, si existia, permanece intacto.")
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
