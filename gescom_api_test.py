#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GESCOM API -> SQLite laboratorio MATINAL.

Escrituras productivas: NINGUNA.
Base permitida: data/matinal_api_test.db
Métodos HTTP usados contra GESCOM: GET (más POST de autenticación OAuth a Keycloak).
No modifica data/matinal.db ni archivos Excel.

Uso en PowerShell:
  $env:GESCOM_REALM="gcw-demo"
  $env:GESCOM_SITE="https://TU-SITIO.gescom.online"
  $env:GESCOM_USER="TU_USUARIO"
  $env:GESCOM_PASSWORD="TU_CLAVE"

  python gescom_api_test.py --init
  python gescom_api_test.py --sync --fecha-desde 2026-11-01 --fecha-hasta 2026-12-01
  python gescom_api_test.py --diagnostico
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

DB_PATH = Path("data") / "matinal_api_test.db"
AUTH_BASE = "https://auth.gescom.online"
CLIENT_ID = "gcw-web-api"
TIMEOUT = 60


SCHEMA_SQL = r"""
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS api_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iniciado_utc TEXT NOT NULL,
    finalizado_utc TEXT,
    proceso TEXT NOT NULL,
    estado TEXT NOT NULL,
    detalle TEXT,
    filas INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gescom_ventas (
    venta_id INTEGER PRIMARY KEY,
    estado TEXT,
    etapa TEXT,
    etapa_nota TEXT,
    requiere_autorizacion INTEGER,
    cerrada INTEGER,
    origen TEXT,
    numero_comprobante INTEGER,
    motivo TEXT,
    importe_neto REAL,
    importe_exento REAL,
    importe_conc REAL,
    importe_iva REAL,
    importe_tributos REAL,
    importe_total REAL,
    codigo_reparto INTEGER,
    codigo_chofer TEXT,
    es_credito INTEGER,
    es_sin_cargo INTEGER,
    identificador TEXT,
    codigo_tipo_venta TEXT,
    codigo_cliente TEXT,
    codigo_vendedor TEXT,
    codigo_ruta TEXT,
    codigo_empresa TEXT,
    codigo_punto_venta INTEGER,
    codigo_sede TEXT,
    codigo_condicion_pago TEXT,
    codigo_motivo_cambio TEXT,
    fecha_pedido TEXT,
    fecha_entrega TEXT,
    observaciones TEXT,
    observaciones_internas TEXT,
    descuento_global REAL,
    venta_directa INTEGER,
    metodo_entrega INTEGER,
    lote_id INTEGER,
    venta_referenciada_id INTEGER,
    json_raw TEXT NOT NULL,
    actualizado_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gescom_venta_items (
    venta_id INTEGER NOT NULL,
    venta_item_id INTEGER NOT NULL,
    orden_item INTEGER,
    item_id INTEGER,
    codigo_item TEXT,
    codigo_alicuota_iva TEXT,
    codigo_lista_precio TEXT,
    codigo_deposito TEXT,
    codigo_lote TEXT,
    codigo_combo TEXT,
    codigo_combo_comp TEXT,
    cantidad REAL,
    codigo_unidad TEXT,
    unidad_factor REAL,
    piezas REAL,
    precio_unitario REAL,
    precio_unitario_iva REAL,
    precio_unitario_total REAL,
    precio_costo REAL,
    descuento REAL,
    descuento_neto REAL,
    descuento_final REAL,
    importe_neto REAL,
    importe_exento REAL,
    importe_conc REAL,
    importe_iva REAL,
    importe_tributos REAL,
    importe_total REAL,
    comentario TEXT,
    json_raw TEXT NOT NULL,
    PRIMARY KEY (venta_id, venta_item_id),
    FOREIGN KEY (venta_id) REFERENCES gescom_ventas(venta_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS gescom_articulos (
    codigo TEXT PRIMARY KEY,
    descripcion TEXT,
    codigo_rubro TEXT,
    precio_costo REAL,
    impuesto_interno REAL,
    codigo_alicuota_iva TEXT,
    codigo_linea TEXT,
    codigo_marca TEXT,
    codigo_familia TEXT,
    codigo_segmento_margen TEXT,
    unidad_venta TEXT,
    unidades_bulto_venta REAL,
    unidad_venta_base TEXT,
    unidades_minima_venta REAL,
    factor_peso REAL,
    factor_volumen REAL,
    codigo_barras TEXT,
    codigo_proveedor TEXT,
    codigo_empresa TEXT,
    unidades_por_bulto REAL,
    bloqueado INTEGER,
    incontable INTEGER,
    json_raw TEXT NOT NULL,
    actualizado_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gescom_marcas (
    codigo TEXT PRIMARY KEY,
    descripcion TEXT,
    json_raw TEXT NOT NULL,
    actualizado_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gescom_familias (
    codigo TEXT PRIMARY KEY,
    descripcion TEXT,
    json_raw TEXT NOT NULL,
    actualizado_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gescom_lineas (
    codigo TEXT PRIMARY KEY,
    descripcion TEXT,
    json_raw TEXT NOT NULL,
    actualizado_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gescom_rubros (
    codigo TEXT PRIMARY KEY,
    descripcion TEXT,
    json_raw TEXT NOT NULL,
    actualizado_utc TEXT NOT NULL
);

DROP VIEW IF EXISTS vta_api;
CREATE VIEW vta_api AS
SELECT
    v.venta_id AS VentaID,
    i.venta_item_id AS VentaItemID,
    v.fecha_pedido AS FechaCarga,
    v.fecha_entrega AS FechaEntrega,
    v.codigo_cliente AS Cliente,
    v.codigo_vendedor AS CodVend,
    v.codigo_ruta AS Ruta,
    v.codigo_tipo_venta AS TipoDeVentaCodigo,
    v.estado AS Estado,
    v.etapa AS Etapa,
    v.cerrada AS Cerrada,
    i.codigo_item AS Codigo,
    a.descripcion AS Articulo,
    a.codigo_marca AS CodigoMarca,
    m.descripcion AS Marca,
    a.codigo_familia AS CodigoFamilia,
    f.descripcion AS Familia,
    a.codigo_linea AS CodigoLinea,
    l.descripcion AS Linea,
    a.codigo_rubro AS CodigoRubro,
    r.descripcion AS Rubro,
    a.codigo_segmento_margen AS CodigoSegmentoMargen,
    i.cantidad AS Cantidad,
    i.codigo_unidad AS Unidad,
    i.unidad_factor AS UnidadFactor,
    CASE WHEN i.cantidad IS NULL OR i.unidad_factor IS NULL THEN NULL
         ELSE i.cantidad * i.unidad_factor END AS CantBase,
    a.factor_peso AS FactorPeso,
    CASE WHEN i.cantidad IS NULL OR i.unidad_factor IS NULL OR a.factor_peso IS NULL THEN NULL
         ELSE (i.cantidad * i.unidad_factor * a.factor_peso) / 1000.0 END AS KilosCandidato,
    i.precio_unitario AS PrecioUnitario,
    i.precio_costo AS PrecioCosto,
    i.descuento AS Descuento,
    i.importe_neto AS ImporteNetoItem,
    i.importe_iva AS ImporteIVAItem,
    i.importe_total AS ImporteTotalItem,
    v.codigo_empresa AS CodigoEmpresa,
    v.numero_comprobante AS NumeroComprobante,
    v.venta_referenciada_id AS VentaReferenciadaID
FROM gescom_venta_items i
JOIN gescom_ventas v ON v.venta_id = i.venta_id
LEFT JOIN gescom_articulos a ON a.codigo = i.codigo_item
LEFT JOIN gescom_marcas m ON m.codigo = a.codigo_marca
LEFT JOIN gescom_familias f ON f.codigo = a.codigo_familia
LEFT JOIN gescom_lineas l ON l.codigo = a.codigo_linea
LEFT JOIN gescom_rubros r ON r.codigo = a.codigo_rubro;
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_bool(value: Any) -> int | None:
    if value is None:
        return None
    return int(bool(value))


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Falta variable de entorno obligatoria: {name}")
    return value


class GescomClient:
    def __init__(self) -> None:
        self.realm = env_required("GESCOM_REALM")
        self.site = env_required("GESCOM_SITE").rstrip("/")
        self.user = env_required("GESCOM_USER")
        self.password = env_required("GESCOM_PASSWORD")
        self.session = requests.Session()
        self.token = ""
        self.expires_at = 0.0

    def authenticate(self) -> None:
        url = f"{AUTH_BASE}/realms/{self.realm}/protocol/openid-connect/token"
        response = self.session.post(
            url,
            data={
                "client_id": CLIENT_ID,
                "grant_type": "password",
                "username": self.user,
                "password": self.password,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        self.token = payload["access_token"]
        self.expires_at = time.time() + int(payload.get("expires_in", 300)) - 30

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.token or time.time() >= self.expires_at:
            self.authenticate()
        response = self.session.get(
            f"{self.site}{path}",
            params=params,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=TIMEOUT,
        )
        if response.status_code == 401:
            self.authenticate()
            response = self.session.get(
                f"{self.site}{path}",
                params=params,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=TIMEOUT,
            )
        response.raise_for_status()
        return response.json()


def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def upsert_simple_catalog(
    conn: sqlite3.Connection, table: str, rows: Iterable[dict[str, Any]]
) -> int:
    now = utc_now()
    values = []
    for row in rows:
        codigo = row.get("codigo")
        if codigo is None:
            continue
        values.append(
            (
                str(codigo),
                row.get("descripcion") or row.get("nombre"),
                json.dumps(row, ensure_ascii=False),
                now,
            )
        )
    conn.executemany(
        f"""INSERT INTO {table}(codigo, descripcion, json_raw, actualizado_utc)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(codigo) DO UPDATE SET
                descripcion=excluded.descripcion,
                json_raw=excluded.json_raw,
                actualizado_utc=excluded.actualizado_utc""",
        values,
    )
    return len(values)


def sync_catalogos(client: GescomClient, conn: sqlite3.Connection) -> None:
    endpoints = {
        "gescom_marcas": "/data/cmd/inventario/api/v1/get-marcas",
        "gescom_familias": "/data/cmd/inventario/api/v1/get-familias",
        "gescom_lineas": "/data/cmd/inventario/api/v1/get-lineas",
        "gescom_rubros": "/data/cmd/inventario/api/v1/get-rubros",
    }
    for table, endpoint in endpoints.items():
        payload = client.get(endpoint)
        if not isinstance(payload, list):
            raise RuntimeError(
                f"Respuesta inesperada de {endpoint}: se esperaba array JSON"
            )
        upsert_simple_catalog(conn, table, payload)
    conn.commit()


def sync_articulos(client: GescomClient, conn: sqlite3.Connection) -> int:
    page = 0
    page_size = 1000
    total = 0
    now = utc_now()
    while True:
        rows = client.get(
            "/data/cmd/inventario/api/v4/get-articulos",
            {"pagesize": page_size, "pagestoskip": page, "pagestotake": 1},
        )
        if not isinstance(rows, list):
            raise RuntimeError("Respuesta inesperada de Artículos v4")
        values = []
        for r in rows:
            values.append(
                (
                    str(r.get("codigo")),
                    r.get("descripcion"),
                    r.get("codigoRubro"),
                    r.get("precioCosto"),
                    r.get("impuestoInterno"),
                    r.get("codigoAlicuotaIva"),
                    r.get("codigoLinea"),
                    r.get("codigoMarca"),
                    r.get("codigoFamilia"),
                    r.get("codigoSegmentoMargen"),
                    r.get("unidadVenta"),
                    r.get("unidadesBultoVenta"),
                    r.get("unidadVentaBase"),
                    r.get("unidadesMinimaVenta"),
                    r.get("factorPeso"),
                    r.get("factorVolumen"),
                    r.get("codigoBarras"),
                    r.get("codigoProveedor"),
                    r.get("codigoEmpresa"),
                    r.get("unidadesPorBulto"),
                    as_bool(r.get("bloqueado")),
                    as_bool(r.get("incontable")),
                    json.dumps(r, ensure_ascii=False),
                    now,
                )
            )
        conn.executemany(
            """
            INSERT INTO gescom_articulos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(codigo) DO UPDATE SET
                descripcion=excluded.descripcion, codigo_rubro=excluded.codigo_rubro,
                precio_costo=excluded.precio_costo, impuesto_interno=excluded.impuesto_interno,
                codigo_alicuota_iva=excluded.codigo_alicuota_iva, codigo_linea=excluded.codigo_linea,
                codigo_marca=excluded.codigo_marca, codigo_familia=excluded.codigo_familia,
                codigo_segmento_margen=excluded.codigo_segmento_margen, unidad_venta=excluded.unidad_venta,
                unidades_bulto_venta=excluded.unidades_bulto_venta, unidad_venta_base=excluded.unidad_venta_base,
                unidades_minima_venta=excluded.unidades_minima_venta, factor_peso=excluded.factor_peso,
                factor_volumen=excluded.factor_volumen, codigo_barras=excluded.codigo_barras,
                codigo_proveedor=excluded.codigo_proveedor, codigo_empresa=excluded.codigo_empresa,
                unidades_por_bulto=excluded.unidades_por_bulto, bloqueado=excluded.bloqueado,
                incontable=excluded.incontable, json_raw=excluded.json_raw, actualizado_utc=excluded.actualizado_utc
        """,
            values,
        )
        conn.commit()
        total += len(rows)
        if len(rows) < page_size:
            break
        page += 1
    return total


def sync_ventas(
    client: GescomClient, conn: sqlite3.Connection, fecha_desde: str, fecha_hasta: str
) -> tuple[int, int]:
    page = 0
    ventas_count = 0
    items_count = 0
    while True:
        ventas = client.get(
            "/data/cmd/ventas/api/v2/get",
            {
                "fechadesde": fecha_desde,
                "fechahasta": fecha_hasta,
                "pagesize": 500,
                "pagestoskip": page,
                "pagestotake": 1,
            },
        )
        if not isinstance(ventas, list):
            raise RuntimeError("Respuesta inesperada de Ventas v2")
        if not ventas:
            break
        with conn:
            for v in ventas:
                venta_id = int(v["id"])
                ref = v.get("ventaReferenciada") or {}
                conn.execute(
                    "DELETE FROM gescom_venta_items WHERE venta_id = ?", (venta_id,)
                )
                conn.execute(
                    """
                    INSERT INTO gescom_ventas VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(venta_id) DO UPDATE SET
                        estado=excluded.estado, etapa=excluded.etapa, etapa_nota=excluded.etapa_nota,
                        requiere_autorizacion=excluded.requiere_autorizacion, cerrada=excluded.cerrada,
                        origen=excluded.origen, numero_comprobante=excluded.numero_comprobante, motivo=excluded.motivo,
                        importe_neto=excluded.importe_neto, importe_exento=excluded.importe_exento,
                        importe_conc=excluded.importe_conc, importe_iva=excluded.importe_iva,
                        importe_tributos=excluded.importe_tributos, importe_total=excluded.importe_total,
                        codigo_reparto=excluded.codigo_reparto, codigo_chofer=excluded.codigo_chofer,
                        es_credito=excluded.es_credito, es_sin_cargo=excluded.es_sin_cargo,
                        identificador=excluded.identificador, codigo_tipo_venta=excluded.codigo_tipo_venta,
                        codigo_cliente=excluded.codigo_cliente, codigo_vendedor=excluded.codigo_vendedor,
                        codigo_ruta=excluded.codigo_ruta, codigo_empresa=excluded.codigo_empresa,
                        codigo_punto_venta=excluded.codigo_punto_venta, codigo_sede=excluded.codigo_sede,
                        codigo_condicion_pago=excluded.codigo_condicion_pago,
                        codigo_motivo_cambio=excluded.codigo_motivo_cambio, fecha_pedido=excluded.fecha_pedido,
                        fecha_entrega=excluded.fecha_entrega, observaciones=excluded.observaciones,
                        observaciones_internas=excluded.observaciones_internas,
                        descuento_global=excluded.descuento_global, venta_directa=excluded.venta_directa,
                        metodo_entrega=excluded.metodo_entrega, lote_id=excluded.lote_id,
                        venta_referenciada_id=excluded.venta_referenciada_id,
                        json_raw=excluded.json_raw, actualizado_utc=excluded.actualizado_utc
                """,
                    (
                        venta_id,
                        v.get("estado"),
                        v.get("etapa"),
                        v.get("etapaNota"),
                        as_bool(v.get("requiereAutorizacion")),
                        as_bool(v.get("cerrada")),
                        v.get("origen"),
                        v.get("numeroComprobante"),
                        v.get("motivo"),
                        v.get("importeNeto"),
                        v.get("importeExento"),
                        v.get("importeConc"),
                        v.get("importeIva"),
                        v.get("importeTributos"),
                        v.get("importeTotal"),
                        v.get("codigoReparto"),
                        v.get("codigoChofer"),
                        as_bool(v.get("esCredito")),
                        as_bool(v.get("esSinCargo")),
                        v.get("identificador"),
                        v.get("codigoTipoVenta"),
                        v.get("codigoCliente"),
                        v.get("codigoVendedor"),
                        v.get("codigoRuta"),
                        v.get("codigoEmpresa"),
                        v.get("codigoPuntoVenta"),
                        v.get("codigoSede"),
                        v.get("codigoCondicionPago"),
                        v.get("codigoMotivoCambio"),
                        v.get("fechaPedido"),
                        v.get("fechaEntrega"),
                        v.get("observaciones"),
                        v.get("observacionesInternas"),
                        v.get("descuentoGlobal"),
                        as_bool(v.get("ventaDirecta")),
                        v.get("metodoEntrega"),
                        v.get("loteId"),
                        ref.get("id"),
                        json.dumps(v, ensure_ascii=False),
                        utc_now(),
                    ),
                )
                for idx, item in enumerate(v.get("items") or []):
                    venta_item_id = item.get("ventaItemID")
                    if venta_item_id is None:
                        venta_item_id = -(idx + 1)
                    conn.execute(
                        """
                        INSERT INTO gescom_venta_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                        (
                            venta_id,
                            int(venta_item_id),
                            item.get("orden"),
                            item.get("itemID"),
                            item.get("codigoItem"),
                            item.get("codigoAlicuotaIva"),
                            item.get("codigoListaPrecio"),
                            item.get("codigoDeposito"),
                            item.get("codigoLote"),
                            item.get("codigoCombo"),
                            item.get("codigoComboComp"),
                            item.get("cantidad"),
                            item.get("codigoUnidad"),
                            item.get("unidadFactor"),
                            item.get("piezas"),
                            item.get("precioUnitario"),
                            item.get("precioUnitarioIva"),
                            item.get("precioUnitarioTotal"),
                            item.get("precioCosto"),
                            item.get("descuento"),
                            item.get("descuentoNeto"),
                            item.get("descuentoFinal"),
                            item.get("importeNeto"),
                            item.get("importeExento"),
                            item.get("importeConc"),
                            item.get("importeIva"),
                            item.get("importeTributos"),
                            item.get("importeTotal"),
                            item.get("comentario"),
                            json.dumps(item, ensure_ascii=False),
                        ),
                    )
                    items_count += 1
                ventas_count += 1
        if len(ventas) < 500:
            break
        page += 1
    return ventas_count, items_count


def diagnostico(conn: sqlite3.Connection) -> None:
    names = [
        "gescom_ventas",
        "gescom_venta_items",
        "gescom_articulos",
        "gescom_marcas",
        "gescom_familias",
        "vta_api",
    ]
    print(f"DB: {DB_PATH.resolve()}")
    for name in names:
        count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"{name}: {count}")
    faltantes = conn.execute("""
        SELECT COUNT(*) FROM gescom_venta_items i
        LEFT JOIN gescom_articulos a ON a.codigo = i.codigo_item
        WHERE a.codigo IS NULL
    """).fetchone()[0]
    print(f"items_sin_articulo: {faltantes}")
    print("Escrituras productivas: NINGUNA")


def main() -> int:
    parser = argparse.ArgumentParser(description="Laboratorio GESCOM API -> SQLite")
    parser.add_argument(
        "--init",
        action="store_true",
        help="Crea/valida el esquema de la base de prueba",
    )
    parser.add_argument(
        "--sync", action="store_true", help="Sincroniza catálogos, artículos y ventas"
    )
    parser.add_argument(
        "--diagnostico", action="store_true", help="Muestra conteos de control"
    )
    parser.add_argument(
        "--fecha-desde", help="Fecha inicial de fechaPedido, formato ISO"
    )
    parser.add_argument("--fecha-hasta", help="Fecha final de fechaPedido, formato ISO")
    args = parser.parse_args()

    if not any((args.init, args.sync, args.diagnostico)):
        parser.error("Indicá --init, --sync o --diagnostico")

    conn = connect_db()
    try:
        init_db(conn)
        if args.init:
            print(f"Base inicializada: {DB_PATH.resolve()}")
            print("Escrituras productivas: NINGUNA")
        if args.sync:
            if not args.fecha_desde or not args.fecha_hasta:
                parser.error("--sync requiere --fecha-desde y --fecha-hasta")
            client = GescomClient()
            sync_catalogos(client, conn)
            articulos = sync_articulos(client, conn)
            ventas, items = sync_ventas(
                client, conn, args.fecha_desde, args.fecha_hasta
            )
            print(
                f"Sincronización finalizada. artículos={articulos}, ventas={ventas}, ítems={items}"
            )
            print("Escrituras productivas: NINGUNA")
        if args.diagnostico:
            diagnostico(conn)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
