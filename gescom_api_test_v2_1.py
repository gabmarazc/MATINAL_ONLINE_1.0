#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GESCOM API -> SQLite laboratorio MATINAL, version 2.1.

Destino permitido: data/matinal_api_test.db
Escrituras productivas: NINGUNA.
No modifica data/matinal.db ni archivos Excel.

La version 2:
- conserva entidades API separadas en SQLite;
- usa claves estables y UPSERT, sin duplicar ventas ni items;
- actualiza filas existentes cuando GESCOM cambia;
- conserva json_raw para trazabilidad;
- sincroniza ventas, articulos y maestros comerciales documentados;
- crea vta_api_raw y vta_api_matinal;
- registra cada ejecucion en api_sync_log.

PowerShell:
  $env:GESCOM_REALM="gcw-demo"
  $env:GESCOM_SITE="https://demo.gescom.online"
  $env:GESCOM_USER="gustavo"
  $env:GESCOM_PASSWORD="TU_CLAVE"

  python gescom_api_test_v2.py --init
  python gescom_api_test_v2.py --sync --fecha-desde 2026-11-01 --fecha-hasta 2026-11-16
  python gescom_api_test_v2.py --diagnostico
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

DB_PATH = Path("data") / "matinal_api_test.db"
AUTH_BASE = "https://auth.gescom.online"
CLIENT_ID = "gcw-web-api"
TIMEOUT = 60
PAGE_SIZE_VENTAS = 500
PAGE_SIZE_ARTICULOS = 1000

SCHEMA_SQL = r"""
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS api_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iniciado_utc TEXT NOT NULL,
    finalizado_utc TEXT,
    proceso TEXT NOT NULL,
    estado TEXT NOT NULL,
    detalle TEXT,
    filas INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS api_sync_state (
    entidad TEXT PRIMARY KEY,
    ultima_sync_utc TEXT,
    fecha_desde TEXT,
    fecha_hasta TEXT,
    estado TEXT,
    detalle TEXT
);

CREATE TABLE IF NOT EXISTS gescom_ventas (
    venta_id INTEGER PRIMARY KEY,
    estado TEXT, etapa TEXT, etapa_nota TEXT,
    requiere_autorizacion INTEGER, cerrada INTEGER, origen TEXT,
    numero_comprobante INTEGER, motivo TEXT,
    importe_neto REAL, importe_exento REAL, importe_conc REAL,
    importe_iva REAL, importe_tributos REAL, importe_total REAL,
    codigo_reparto TEXT, codigo_chofer TEXT,
    es_credito INTEGER, es_sin_cargo INTEGER, identificador TEXT,
    codigo_tipo_venta TEXT, codigo_cliente TEXT, codigo_vendedor TEXT,
    codigo_ruta TEXT, codigo_empresa TEXT, codigo_punto_venta INTEGER,
    codigo_sede TEXT, codigo_condicion_pago TEXT, codigo_motivo_cambio TEXT,
    fecha_pedido TEXT, fecha_entrega TEXT,
    observaciones TEXT, observaciones_internas TEXT,
    descuento_global REAL, venta_directa INTEGER, metodo_entrega INTEGER,
    lote_id INTEGER, venta_referenciada_id INTEGER,
    hash_raw TEXT, json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gescom_venta_items (
    venta_id INTEGER NOT NULL,
    venta_item_id INTEGER NOT NULL,
    orden_item INTEGER, item_id INTEGER, codigo_item TEXT,
    codigo_alicuota_iva TEXT, codigo_lista_precio TEXT,
    codigo_deposito TEXT, codigo_lote TEXT, codigo_combo TEXT,
    codigo_combo_comp TEXT, cantidad REAL, codigo_unidad TEXT,
    unidad_factor REAL, piezas REAL,
    precio_unitario REAL, precio_unitario_iva REAL,
    precio_unitario_total REAL, precio_costo REAL,
    descuento REAL, descuento_neto REAL, descuento_final REAL,
    importe_neto REAL, importe_exento REAL, importe_conc REAL,
    importe_iva REAL, importe_tributos REAL, importe_total REAL,
    comentario TEXT, hash_raw TEXT, json_raw TEXT NOT NULL,
    actualizado_utc TEXT NOT NULL,
    PRIMARY KEY (venta_id, venta_item_id),
    FOREIGN KEY (venta_id) REFERENCES gescom_ventas(venta_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_venta_items_codigo ON gescom_venta_items(codigo_item);
CREATE INDEX IF NOT EXISTS ix_ventas_fecha ON gescom_ventas(fecha_pedido);
CREATE INDEX IF NOT EXISTS ix_ventas_cliente ON gescom_ventas(codigo_cliente);

CREATE TABLE IF NOT EXISTS gescom_articulos (
    codigo TEXT PRIMARY KEY,
    descripcion TEXT, codigo_rubro TEXT, precio_costo REAL,
    impuesto_interno REAL, codigo_alicuota_iva TEXT,
    codigo_linea TEXT, codigo_marca TEXT, codigo_familia TEXT,
    codigo_segmento_margen TEXT, unidad_venta TEXT,
    unidades_bulto_venta REAL, unidad_venta_base TEXT,
    unidades_minima_venta REAL, factor_peso REAL, factor_volumen REAL,
    codigo_barras TEXT, codigo_proveedor TEXT, codigo_empresa TEXT,
    unidades_por_bulto REAL, bloqueado INTEGER, incontable INTEGER,
    ponderado_pieza REAL, tags_json TEXT,
    hash_raw TEXT, json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_articulos_proveedor ON gescom_articulos(codigo_proveedor);
CREATE INDEX IF NOT EXISTS ix_articulos_marca ON gescom_articulos(codigo_marca);

CREATE TABLE IF NOT EXISTS gescom_marcas (
    codigo TEXT PRIMARY KEY, descripcion TEXT, hash_raw TEXT,
    json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gescom_familias (
    codigo TEXT PRIMARY KEY, descripcion TEXT, hash_raw TEXT,
    json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gescom_lineas (
    codigo TEXT PRIMARY KEY, descripcion TEXT, hash_raw TEXT,
    json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gescom_rubros (
    codigo TEXT PRIMARY KEY, descripcion TEXT, hash_raw TEXT,
    json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gescom_segmentos_margen (
    codigo TEXT PRIMARY KEY, descripcion TEXT, hash_raw TEXT,
    json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gescom_ramos (
    codigo TEXT PRIMARY KEY, descripcion TEXT, hash_raw TEXT,
    json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gescom_subramos (
    codigo TEXT PRIMARY KEY, descripcion TEXT, hash_raw TEXT,
    json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gescom_condiciones_pago (
    codigo TEXT PRIMARY KEY, descripcion TEXT, hash_raw TEXT,
    json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gescom_vendedores (
    codigo TEXT PRIMARY KEY, descripcion TEXT, hash_raw TEXT,
    json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gescom_empresas (
    codigo TEXT PRIMARY KEY, descripcion TEXT, hash_raw TEXT,
    json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gescom_clientes (
    codigo TEXT PRIMARY KEY,
    nombre TEXT, razon_social TEXT, direccion TEXT, localidad TEXT,
    codigo_ramo TEXT, codigo_subramo TEXT,
    latitud REAL, longitud REAL,
    hash_raw TEXT, json_raw TEXT NOT NULL, actualizado_utc TEXT NOT NULL
);

-- El endpoint de proveedores no esta confirmado en la referencia disponible.
-- La tabla queda preparada para cargarlo cuando se confirme.
CREATE TABLE IF NOT EXISTS gescom_proveedores (
    codigo TEXT PRIMARY KEY,
    descripcion TEXT,
    razon_social TEXT,
    direccion TEXT,
    telefono TEXT,
    localidad TEXT,
    codigo_tipo_documento TEXT,
    codigo_condicion_iva TEXT,
    email TEXT,
    provincia TEXT,
    codigo_condicion_pago TEXT,
    codigo_postal TEXT,
    nro_documento TEXT,
    contacto TEXT,
    tags_json TEXT,
    comentario TEXT,
    notas TEXT,
    hash_raw TEXT,
    json_raw TEXT NOT NULL,
    actualizado_utc TEXT NOT NULL
);

DROP VIEW IF EXISTS vta_api;
DROP VIEW IF EXISTS vta_api_matinal;
DROP VIEW IF EXISTS vta_api_raw;

CREATE VIEW vta_api_raw AS
SELECT
    v.venta_id AS VentaID,
    i.venta_item_id AS VentaItemID,
    v.fecha_pedido AS FechaCarga,
    v.fecha_entrega AS FechaEntrega,
    v.codigo_cliente AS Cliente,
    c.nombre AS ClienteNombre,
    c.razon_social AS RazonSocial,
    c.direccion AS Direccion,
    c.localidad AS Localidad,
    c.codigo_ramo AS CodigoRamo,
    ra.descripcion AS Ramo,
    c.codigo_subramo AS CodigoSubramo,
    sr.descripcion AS Subramo,
    v.codigo_vendedor AS CodVendedor,
    ve.descripcion AS Vendedor,
    v.codigo_ruta AS RutaPreventa,
    v.codigo_tipo_venta AS TipoDeVentaCodigo,
    v.estado AS Estado,
    v.etapa AS Etapa,
    v.cerrada AS Cerrada,
    v.codigo_empresa AS CodigoEmpresa,
    em.descripcion AS Empresa,
    v.codigo_condicion_pago AS CodigoCondicionPago,
    cp.descripcion AS CondicionPago,
    v.codigo_reparto AS Reparto,
    v.codigo_chofer AS Chofer,
    v.numero_comprobante AS NroComprobante,
    v.venta_referenciada_id AS VentaReferenciadaID,
    v.origen AS Origen,
    v.venta_directa AS VentaDirecta,
    v.motivo AS MotivoDevolucion,
    v.observaciones_internas AS ComentarioInterno,
    i.codigo_item AS Codigo,
    a.descripcion AS Articulo,
    a.codigo_proveedor AS CodigoProveedor,
    p.descripcion AS Proveedor,
    a.codigo_marca AS CodigoMarca,
    m.descripcion AS Marca,
    a.codigo_familia AS CodigoFamilia,
    f.descripcion AS Familia,
    a.codigo_linea AS CodigoLinea,
    l.descripcion AS Linea,
    a.codigo_rubro AS CodigoRubro,
    r.descripcion AS Rubro,
    a.codigo_segmento_margen AS CodigoSegmentoMargen,
    sm.descripcion AS SegmentoRentabilidad,
    a.tags_json AS Tags,
    a.impuesto_interno AS ImpuestoInterno,
    a.factor_peso AS FactorPeso,
    a.incontable AS Incontable,
    a.unidad_venta_base AS UnidadVentaBase,
    i.cantidad AS CantidadGESCOM,
    i.codigo_unidad AS Unidad,
    i.unidad_factor AS UnidadFactor,
    i.piezas AS Piezas,
    CASE
      WHEN i.cantidad IS NULL OR i.unidad_factor IS NULL THEN NULL
      WHEN lower(coalesce(i.codigo_unidad,'')) IN ('kg','kgs','gr','grs') THEN i.piezas
      ELSE i.cantidad * i.unidad_factor
    END AS CantBaseCandidata,
    CASE
      WHEN i.cantidad IS NULL OR i.unidad_factor IS NULL THEN NULL
      WHEN lower(coalesce(i.codigo_unidad,'')) IN ('kg','kgs') THEN i.cantidad
      WHEN lower(coalesce(i.codigo_unidad,'')) IN ('gr','grs') THEN i.cantidad / 1000.0
      WHEN a.factor_peso IS NOT NULL AND a.factor_peso > 0
        THEN (i.cantidad * i.unidad_factor * a.factor_peso) / 1000.0
      ELSE NULL
    END AS PesoKgCandidato,
    i.precio_unitario AS PrecioUnitario,
    i.precio_costo AS PrecioCosto,
    i.descuento AS Descuento,
    i.descuento_final AS ValorDescuentoAPI,
    i.importe_neto AS ImporteNetoItem,
    i.importe_total AS ImporteItem,
    i.codigo_lista_precio AS ListaPrecio,
    i.codigo_combo AS ComboCodigo,
    v.json_raw AS VentaJsonRaw,
    i.json_raw AS ItemJsonRaw,
    a.json_raw AS ArticuloJsonRaw
FROM gescom_venta_items i
JOIN gescom_ventas v ON v.venta_id = i.venta_id
LEFT JOIN gescom_articulos a ON a.codigo = i.codigo_item
LEFT JOIN gescom_marcas m ON m.codigo = a.codigo_marca
LEFT JOIN gescom_familias f ON f.codigo = a.codigo_familia
LEFT JOIN gescom_lineas l ON l.codigo = a.codigo_linea
LEFT JOIN gescom_rubros r ON r.codigo = a.codigo_rubro
LEFT JOIN gescom_segmentos_margen sm ON sm.codigo = a.codigo_segmento_margen
LEFT JOIN gescom_proveedores p ON p.codigo = a.codigo_proveedor
LEFT JOIN gescom_clientes c ON c.codigo = v.codigo_cliente
LEFT JOIN gescom_ramos ra ON ra.codigo = c.codigo_ramo
LEFT JOIN gescom_subramos sr ON sr.codigo = c.codigo_subramo
LEFT JOIN gescom_vendedores ve ON ve.codigo = v.codigo_vendedor
LEFT JOIN gescom_condiciones_pago cp ON cp.codigo = v.codigo_condicion_pago
LEFT JOIN gescom_empresas em ON em.codigo = v.codigo_empresa;

CREATE VIEW vta_api_matinal AS
SELECT
    Cliente, Direccion, Localidad,
    NULL AS FechaComprobante,
    FechaEntrega, FechaCarga,
    NroComprobante,
    TipoDeVentaCodigo AS TipoDeVenta,
    Empresa, Codigo,
    CantBaseCandidata AS CantBase,
    ImporteNetoItem, ImporteItem,
    RazonSocial, MotivoDevolucion, Descuento,
    CodVendedor, Vendedor, RutaPreventa, Articulo,
    CASE WHEN CantBaseCandidata IS NOT NULL AND CantBaseCandidata <> 0
         THEN ImporteNetoItem / CantBaseCandidata ELSE NULL END AS NetoItem,
    Reparto, ComentarioInterno, Ramo, Subramo,
    PrecioCosto, Chofer, ValorDescuentoAPI AS valorDescuento,
    Proveedor, PesoKgCandidato AS PesoKg,
    ImpuestoInterno, CondicionPago,
    NULL AS FechaLiquidacion,
    ComboCodigo, Marca, Linea,
    NULL AS Sabor, NULL AS Calibre,
    Familia, Rubro, Tags,
    NULL AS Promociones,
    SegmentoRentabilidad,
    Origen,
    VentaReferenciadaID AS ComprobanteReferencia,
    VentaDirecta,
    VentaID AS NumeroVenta,
    Estado AS Pendiente,
    ListaPrecio,
    UnidadFactor
FROM vta_api_raw;

CREATE VIEW vta_api AS SELECT * FROM vta_api_raw;
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def raw_hash(value: Any) -> str:
    import hashlib

    return hashlib.sha256(compact_json(value).encode("utf-8")).hexdigest()


def as_bool(value: Any) -> int | None:
    return None if value is None else int(bool(value))


def pick(row: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return None


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Falta variable de entorno obligatoria: {name}")
    if name == "GESCOM_SITE" and ("<a " in value.lower() or "</a>" in value.lower()):
        raise RuntimeError(
            "GESCOM_SITE contiene HTML. Debe ser solo https://demo.gescom.online"
        )
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
        response = self.session.post(
            f"{AUTH_BASE}/realms/{self.realm}/protocol/openid-connect/token",
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


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(r[1] == column for r in conn.execute(f"PRAGMA table_info({table})"))


def migrate_v1(conn: sqlite3.Connection) -> None:
    migrations = {
        "gescom_ventas": [("hash_raw", "TEXT")],
        "gescom_venta_items": [("hash_raw", "TEXT"), ("actualizado_utc", "TEXT")],
        "gescom_articulos": [
            ("ponderado_pieza", "REAL"),
            ("tags_json", "TEXT"),
            ("hash_raw", "TEXT"),
        ],
        "gescom_marcas": [("hash_raw", "TEXT")],
        "gescom_familias": [("hash_raw", "TEXT")],
        "gescom_lineas": [("hash_raw", "TEXT")],
        "gescom_rubros": [("hash_raw", "TEXT")],
        "gescom_proveedores": [
            ("razon_social", "TEXT"),
            ("direccion", "TEXT"),
            ("telefono", "TEXT"),
            ("localidad", "TEXT"),
            ("codigo_tipo_documento", "TEXT"),
            ("codigo_condicion_iva", "TEXT"),
            ("email", "TEXT"),
            ("provincia", "TEXT"),
            ("codigo_condicion_pago", "TEXT"),
            ("codigo_postal", "TEXT"),
            ("nro_documento", "TEXT"),
            ("contacto", "TEXT"),
            ("tags_json", "TEXT"),
            ("comentario", "TEXT"),
            ("notas", "TEXT"),
            ("hash_raw", "TEXT"),
        ],
    }
    for table, columns in migrations.items():
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            continue
        for column, sql_type in columns:
            if not column_exists(conn, table, column):
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
    conn.commit()


def init_db(conn: sqlite3.Connection) -> None:
    migrate_v1(conn)
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def begin_log(conn: sqlite3.Connection, proceso: str) -> int:
    cur = conn.execute(
        "INSERT INTO api_sync_log(iniciado_utc,proceso,estado) VALUES(?,?,?)",
        (utc_now(), proceso, "EN_CURSO"),
    )
    conn.commit()
    return int(cur.lastrowid)


def end_log(
    conn: sqlite3.Connection, log_id: int, estado: str, detalle: str, filas: int
) -> None:
    conn.execute(
        "UPDATE api_sync_log SET finalizado_utc=?,estado=?,detalle=?,filas=? WHERE id=?",
        (utc_now(), estado, detalle, filas, log_id),
    )
    conn.commit()


def upsert_catalog(
    conn: sqlite3.Connection, table: str, rows: Iterable[dict[str, Any]]
) -> int:
    now = utc_now()
    count = 0
    for row in rows:
        codigo = pick(row, "codigo", "id")
        if codigo is None:
            continue
        raw = compact_json(row)
        conn.execute(
            f"""INSERT INTO {table}(codigo,descripcion,hash_raw,json_raw,actualizado_utc)
                VALUES(?,?,?,?,?)
                ON CONFLICT(codigo) DO UPDATE SET
                  descripcion=excluded.descripcion, hash_raw=excluded.hash_raw,
                  json_raw=excluded.json_raw, actualizado_utc=excluded.actualizado_utc
                WHERE coalesce({table}.hash_raw,'') <> excluded.hash_raw""",
            (
                str(codigo),
                pick(row, "descripcion", "nombre", "razonSocial"),
                raw_hash(row),
                raw,
                now,
            ),
        )
        count += 1
    return count


def sync_catalogs(client: GescomClient, conn: sqlite3.Connection) -> dict[str, int]:
    endpoints = {
        "gescom_marcas": "/data/cmd/inventario/api/v1/get-marcas",
        "gescom_familias": "/data/cmd/inventario/api/v1/get-familias",
        "gescom_lineas": "/data/cmd/inventario/api/v1/get-lineas",
        "gescom_rubros": "/data/cmd/inventario/api/v1/get-rubros",
        "gescom_segmentos_margen": "/data/cmd/inventario/api/v1/get-segmento-margen",
        "gescom_ramos": "/data/cmd/ventas/api/v1/get-ramos",
        "gescom_subramos": "/data/cmd/ventas/api/v1/get-subramos",
        "gescom_condiciones_pago": "/data/cmd/ventas/api/v1/get-condiciones-pago",
        "gescom_vendedores": "/data/cmd/ventas/api/v1/get-vendedores",
        "gescom_empresas": "/data/cmd/config/api/v1/get-empresas",
    }
    result: dict[str, int] = {}
    for table, endpoint in endpoints.items():
        payload = client.get(endpoint)
        if not isinstance(payload, list):
            raise RuntimeError(
                f"Respuesta inesperada de {endpoint}: se esperaba array JSON"
            )
        result[table] = upsert_catalog(conn, table, payload)
    conn.commit()
    return result


def sync_clients(client: GescomClient, conn: sqlite3.Connection) -> int:
    payload = client.get("/data/cmd/ventas/api/v1/get-clientes")
    if not isinstance(payload, list):
        raise RuntimeError("Respuesta inesperada de Clientes")
    now = utc_now()
    count = 0
    for row in payload:
        codigo = pick(row, "codigo", "codigoCliente", "id")
        if codigo is None:
            continue
        domicilio = pick(row, "direccion", "direccionEntrega", "domicilio")
        localidad = pick(row, "localidad", "descripcionLocalidad")
        raw = compact_json(row)
        conn.execute(
            """
            INSERT INTO gescom_clientes(
              codigo,nombre,razon_social,direccion,localidad,codigo_ramo,codigo_subramo,
              latitud,longitud,hash_raw,json_raw,actualizado_utc
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(codigo) DO UPDATE SET
              nombre=excluded.nombre, razon_social=excluded.razon_social,
              direccion=excluded.direccion, localidad=excluded.localidad,
              codigo_ramo=excluded.codigo_ramo, codigo_subramo=excluded.codigo_subramo,
              latitud=excluded.latitud, longitud=excluded.longitud,
              hash_raw=excluded.hash_raw, json_raw=excluded.json_raw,
              actualizado_utc=excluded.actualizado_utc
            WHERE coalesce(gescom_clientes.hash_raw,'') <> excluded.hash_raw
        """,
            (
                str(codigo),
                pick(row, "nombre", "nombreFantasia"),
                pick(row, "razonSocial"),
                domicilio,
                localidad,
                pick(row, "codigoRamo"),
                pick(row, "codigoSubramo"),
                pick(row, "latitud"),
                pick(row, "longitud"),
                raw_hash(row),
                raw,
                now,
            ),
        )
        count += 1
    conn.commit()
    return count


def sync_providers(client: GescomClient, conn: sqlite3.Connection) -> int:
    """Sincroniza todos los proveedores activos documentados por Compras v1."""
    payload = client.get("/data/cmd/compras/api/v1/get-proveedores")
    if not isinstance(payload, list):
        raise RuntimeError("Respuesta inesperada de Proveedores")
    now = utc_now()
    count = 0
    with conn:
        for row in payload:
            codigo = row.get("codigo")
            if codigo is None:
                continue
            raw = compact_json(row)
            nombre = row.get("nombre")
            conn.execute(
                """
                INSERT INTO gescom_proveedores(
                  codigo,descripcion,razon_social,direccion,telefono,localidad,
                  codigo_tipo_documento,codigo_condicion_iva,email,provincia,
                  codigo_condicion_pago,codigo_postal,nro_documento,contacto,
                  tags_json,comentario,notas,hash_raw,json_raw,actualizado_utc
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(codigo) DO UPDATE SET
                  descripcion=excluded.descripcion, razon_social=excluded.razon_social,
                  direccion=excluded.direccion, telefono=excluded.telefono,
                  localidad=excluded.localidad, codigo_tipo_documento=excluded.codigo_tipo_documento,
                  codigo_condicion_iva=excluded.codigo_condicion_iva, email=excluded.email,
                  provincia=excluded.provincia, codigo_condicion_pago=excluded.codigo_condicion_pago,
                  codigo_postal=excluded.codigo_postal, nro_documento=excluded.nro_documento,
                  contacto=excluded.contacto, tags_json=excluded.tags_json,
                  comentario=excluded.comentario, notas=excluded.notas,
                  hash_raw=excluded.hash_raw, json_raw=excluded.json_raw,
                  actualizado_utc=excluded.actualizado_utc
                WHERE coalesce(gescom_proveedores.hash_raw,'') <> excluded.hash_raw
            """,
                (
                    str(codigo),
                    nombre,
                    nombre,
                    row.get("direccion"),
                    row.get("telefono"),
                    row.get("localidad"),
                    row.get("codigoTipoDocumento"),
                    row.get("codigoCondicionIva"),
                    row.get("email"),
                    row.get("provincia"),
                    row.get("codigoCondicionPago"),
                    row.get("codigoPostal"),
                    row.get("nroDocumento"),
                    row.get("contacto"),
                    compact_json(row.get("tags") or []),
                    row.get("comentario"),
                    row.get("notas"),
                    raw_hash(row),
                    raw,
                    now,
                ),
            )
            count += 1
    return count


def sync_articles(client: GescomClient, conn: sqlite3.Connection) -> int:
    page = 0
    total = 0
    while True:
        rows = client.get(
            "/data/cmd/inventario/api/v4/get-articulos",
            {
                "pagesize": PAGE_SIZE_ARTICULOS,
                "pagestoskip": page,
                "pagestotake": 1,
            },
        )
        if not isinstance(rows, list):
            raise RuntimeError("Respuesta inesperada de Articulos v4")
        now = utc_now()
        with conn:
            for r in rows:
                codigo = r.get("codigo")
                if codigo is None:
                    continue
                raw = compact_json(r)
                conn.execute(
                    """
                    INSERT INTO gescom_articulos(
                      codigo,descripcion,codigo_rubro,precio_costo,impuesto_interno,codigo_alicuota_iva,
                      codigo_linea,codigo_marca,codigo_familia,codigo_segmento_margen,unidad_venta,
                      unidades_bulto_venta,unidad_venta_base,unidades_minima_venta,factor_peso,
                      factor_volumen,codigo_barras,codigo_proveedor,codigo_empresa,unidades_por_bulto,
                      bloqueado,incontable,ponderado_pieza,tags_json,hash_raw,json_raw,actualizado_utc
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(codigo) DO UPDATE SET
                      descripcion=excluded.descripcion,codigo_rubro=excluded.codigo_rubro,
                      precio_costo=excluded.precio_costo,impuesto_interno=excluded.impuesto_interno,
                      codigo_alicuota_iva=excluded.codigo_alicuota_iva,codigo_linea=excluded.codigo_linea,
                      codigo_marca=excluded.codigo_marca,codigo_familia=excluded.codigo_familia,
                      codigo_segmento_margen=excluded.codigo_segmento_margen,unidad_venta=excluded.unidad_venta,
                      unidades_bulto_venta=excluded.unidades_bulto_venta,unidad_venta_base=excluded.unidad_venta_base,
                      unidades_minima_venta=excluded.unidades_minima_venta,factor_peso=excluded.factor_peso,
                      factor_volumen=excluded.factor_volumen,codigo_barras=excluded.codigo_barras,
                      codigo_proveedor=excluded.codigo_proveedor,codigo_empresa=excluded.codigo_empresa,
                      unidades_por_bulto=excluded.unidades_por_bulto,bloqueado=excluded.bloqueado,
                      incontable=excluded.incontable,ponderado_pieza=excluded.ponderado_pieza,
                      tags_json=excluded.tags_json,hash_raw=excluded.hash_raw,json_raw=excluded.json_raw,
                      actualizado_utc=excluded.actualizado_utc
                    WHERE coalesce(gescom_articulos.hash_raw,'') <> excluded.hash_raw
                """,
                    (
                        str(codigo),
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
                        r.get("ponderadoPieza"),
                        compact_json(r.get("tags") or []),
                        raw_hash(r),
                        raw,
                        now,
                    ),
                )
                total += 1
        if len(rows) < PAGE_SIZE_ARTICULOS:
            break
        page += 1
    return total


def upsert_sale(conn: sqlite3.Connection, sale: dict[str, Any]) -> tuple[int, int]:
    now = utc_now()
    sale_id = int(sale["id"])
    ref = sale.get("ventaReferenciada") or {}
    raw = compact_json(sale)
    conn.execute(
        """
      INSERT INTO gescom_ventas VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(venta_id) DO UPDATE SET
        estado=excluded.estado,etapa=excluded.etapa,etapa_nota=excluded.etapa_nota,
        requiere_autorizacion=excluded.requiere_autorizacion,cerrada=excluded.cerrada,
        origen=excluded.origen,numero_comprobante=excluded.numero_comprobante,motivo=excluded.motivo,
        importe_neto=excluded.importe_neto,importe_exento=excluded.importe_exento,
        importe_conc=excluded.importe_conc,importe_iva=excluded.importe_iva,
        importe_tributos=excluded.importe_tributos,importe_total=excluded.importe_total,
        codigo_reparto=excluded.codigo_reparto,codigo_chofer=excluded.codigo_chofer,
        es_credito=excluded.es_credito,es_sin_cargo=excluded.es_sin_cargo,
        identificador=excluded.identificador,codigo_tipo_venta=excluded.codigo_tipo_venta,
        codigo_cliente=excluded.codigo_cliente,codigo_vendedor=excluded.codigo_vendedor,
        codigo_ruta=excluded.codigo_ruta,codigo_empresa=excluded.codigo_empresa,
        codigo_punto_venta=excluded.codigo_punto_venta,codigo_sede=excluded.codigo_sede,
        codigo_condicion_pago=excluded.codigo_condicion_pago,
        codigo_motivo_cambio=excluded.codigo_motivo_cambio,fecha_pedido=excluded.fecha_pedido,
        fecha_entrega=excluded.fecha_entrega,observaciones=excluded.observaciones,
        observaciones_internas=excluded.observaciones_internas,
        descuento_global=excluded.descuento_global,venta_directa=excluded.venta_directa,
        metodo_entrega=excluded.metodo_entrega,lote_id=excluded.lote_id,
        venta_referenciada_id=excluded.venta_referenciada_id,hash_raw=excluded.hash_raw,
        json_raw=excluded.json_raw,actualizado_utc=excluded.actualizado_utc
      WHERE coalesce(gescom_ventas.hash_raw,'') <> excluded.hash_raw
    """,
        (
            sale_id,
            sale.get("estado"),
            sale.get("etapa"),
            sale.get("etapaNota"),
            as_bool(sale.get("requiereAutorizacion")),
            as_bool(sale.get("cerrada")),
            sale.get("origen"),
            sale.get("numeroComprobante"),
            sale.get("motivo"),
            sale.get("importeNeto"),
            sale.get("importeExento"),
            sale.get("importeConc"),
            sale.get("importeIva"),
            sale.get("importeTributos"),
            sale.get("importeTotal"),
            sale.get("codigoReparto"),
            sale.get("codigoChofer"),
            as_bool(sale.get("esCredito")),
            as_bool(sale.get("esSinCargo")),
            sale.get("identificador"),
            sale.get("codigoTipoVenta"),
            sale.get("codigoCliente"),
            sale.get("codigoVendedor"),
            sale.get("codigoRuta"),
            sale.get("codigoEmpresa"),
            sale.get("codigoPuntoVenta"),
            sale.get("codigoSede"),
            sale.get("codigoCondicionPago"),
            sale.get("codigoMotivoCambio"),
            sale.get("fechaPedido"),
            sale.get("fechaEntrega"),
            sale.get("observaciones"),
            sale.get("observacionesInternas"),
            sale.get("descuentoGlobal"),
            as_bool(sale.get("ventaDirecta")),
            sale.get("metodoEntrega"),
            sale.get("loteId"),
            ref.get("id"),
            raw_hash(sale),
            raw,
            now,
        ),
    )

    incoming_ids: set[int] = set()
    item_count = 0
    for idx, item in enumerate(sale.get("items") or []):
        item_id = item.get("ventaItemID")
        if item_id is None:
            item_id = -(idx + 1)
        item_id = int(item_id)
        incoming_ids.add(item_id)
        iraw = compact_json(item)
        conn.execute(
            """
          INSERT INTO gescom_venta_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(venta_id,venta_item_id) DO UPDATE SET
            orden_item=excluded.orden_item,item_id=excluded.item_id,codigo_item=excluded.codigo_item,
            codigo_alicuota_iva=excluded.codigo_alicuota_iva,codigo_lista_precio=excluded.codigo_lista_precio,
            codigo_deposito=excluded.codigo_deposito,codigo_lote=excluded.codigo_lote,
            codigo_combo=excluded.codigo_combo,codigo_combo_comp=excluded.codigo_combo_comp,
            cantidad=excluded.cantidad,codigo_unidad=excluded.codigo_unidad,
            unidad_factor=excluded.unidad_factor,piezas=excluded.piezas,
            precio_unitario=excluded.precio_unitario,precio_unitario_iva=excluded.precio_unitario_iva,
            precio_unitario_total=excluded.precio_unitario_total,precio_costo=excluded.precio_costo,
            descuento=excluded.descuento,descuento_neto=excluded.descuento_neto,
            descuento_final=excluded.descuento_final,importe_neto=excluded.importe_neto,
            importe_exento=excluded.importe_exento,importe_conc=excluded.importe_conc,
            importe_iva=excluded.importe_iva,importe_tributos=excluded.importe_tributos,
            importe_total=excluded.importe_total,comentario=excluded.comentario,
            hash_raw=excluded.hash_raw,json_raw=excluded.json_raw,actualizado_utc=excluded.actualizado_utc
          WHERE coalesce(gescom_venta_items.hash_raw,'') <> excluded.hash_raw
        """,
            (
                sale_id,
                item_id,
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
                raw_hash(item),
                iraw,
                now,
            ),
        )
        item_count += 1

    # Si GESCOM devuelve la venta completa, elimina solo items que ya no forman parte de esa venta.
    if incoming_ids:
        marks = ",".join("?" for _ in incoming_ids)
        conn.execute(
            f"DELETE FROM gescom_venta_items WHERE venta_id=? AND venta_item_id NOT IN ({marks})",
            (sale_id, *sorted(incoming_ids)),
        )
    else:
        conn.execute("DELETE FROM gescom_venta_items WHERE venta_id=?", (sale_id,))
    return 1, item_count


def sync_sales(
    client: GescomClient, conn: sqlite3.Connection, fecha_desde: str, fecha_hasta: str
) -> tuple[int, int]:
    page = 0
    sales_total = 0
    items_total = 0
    while True:
        rows = client.get(
            "/data/cmd/ventas/api/v2/get",
            {
                "fechadesde": fecha_desde,
                "fechahasta": fecha_hasta,
                "pagesize": PAGE_SIZE_VENTAS,
                "pagestoskip": page,
                "pagestotake": 1,
            },
        )
        if not isinstance(rows, list):
            raise RuntimeError("Respuesta inesperada de Ventas v2")
        if not rows:
            break
        with conn:
            for sale in rows:
                s, i = upsert_sale(conn, sale)
                sales_total += s
                items_total += i
        if len(rows) < PAGE_SIZE_VENTAS:
            break
        page += 1
    conn.execute(
        """
      INSERT INTO api_sync_state(entidad,ultima_sync_utc,fecha_desde,fecha_hasta,estado,detalle)
      VALUES('ventas',?,?,?,?,?)
      ON CONFLICT(entidad) DO UPDATE SET ultima_sync_utc=excluded.ultima_sync_utc,
        fecha_desde=excluded.fecha_desde,fecha_hasta=excluded.fecha_hasta,
        estado=excluded.estado,detalle=excluded.detalle
    """,
        (
            utc_now(),
            fecha_desde,
            fecha_hasta,
            "OK",
            f"ventas={sales_total};items={items_total}",
        ),
    )
    conn.commit()
    return sales_total, items_total


def diagnostico(conn: sqlite3.Connection) -> None:
    names = [
        "gescom_ventas",
        "gescom_venta_items",
        "gescom_articulos",
        "gescom_clientes",
        "gescom_vendedores",
        "gescom_marcas",
        "gescom_familias",
        "gescom_lineas",
        "gescom_rubros",
        "gescom_segmentos_margen",
        "gescom_proveedores",
        "vta_api_raw",
        "vta_api_matinal",
    ]
    print(f"DB: {DB_PATH.resolve()}")
    for name in names:
        print(f"{name}: {conn.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]}")
    checks = {
        "items_sin_articulo": "SELECT COUNT(*) FROM gescom_venta_items i LEFT JOIN gescom_articulos a ON a.codigo=i.codigo_item WHERE a.codigo IS NULL",
        "ventas_sin_cliente": "SELECT COUNT(*) FROM gescom_ventas v LEFT JOIN gescom_clientes c ON c.codigo=v.codigo_cliente WHERE c.codigo IS NULL",
        "ventas_sin_vendedor": "SELECT COUNT(*) FROM gescom_ventas v LEFT JOIN gescom_vendedores x ON x.codigo=v.codigo_vendedor WHERE x.codigo IS NULL",
        "articulos_con_codigo_proveedor_sin_maestro": "SELECT COUNT(*) FROM gescom_articulos a LEFT JOIN gescom_proveedores p ON p.codigo=a.codigo_proveedor WHERE a.codigo_proveedor IS NOT NULL AND p.codigo IS NULL",
        "items_duplicados": "SELECT COUNT(*) FROM (SELECT venta_id,venta_item_id,COUNT(*) n FROM gescom_venta_items GROUP BY 1,2 HAVING n>1)",
    }
    for name, sql in checks.items():
        print(f"{name}: {conn.execute(sql).fetchone()[0]}")
    print("Escrituras productivas: NINGUNA")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GESCOM API -> SQLite laboratorio MATINAL v2.1"
    )
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("--diagnostico", action="store_true")
    parser.add_argument("--fecha-desde")
    parser.add_argument("--fecha-hasta")
    args = parser.parse_args()
    if not any((args.init, args.sync, args.diagnostico)):
        parser.error("Indica --init, --sync o --diagnostico")

    conn = connect_db()
    try:
        init_db(conn)
        if args.init:
            print(f"Base v2 inicializada/migrada: {DB_PATH.resolve()}")
            print("Escrituras productivas: NINGUNA")
        if args.sync:
            if not args.fecha_desde or not args.fecha_hasta:
                parser.error("--sync requiere --fecha-desde y --fecha-hasta")
            log_id = begin_log(conn, "sync_v2")
            try:
                client = GescomClient()
                catalogs = sync_catalogs(client, conn)
                clients = sync_clients(client, conn)
                providers = sync_providers(client, conn)
                articles = sync_articles(client, conn)
                sales, items = sync_sales(
                    client, conn, args.fecha_desde, args.fecha_hasta
                )
                total = (
                    sum(catalogs.values())
                    + clients
                    + providers
                    + articles
                    + sales
                    + items
                )
                detail = f"catalogos={catalogs};clientes={clients};proveedores={providers};articulos={articles};ventas={sales};items={items}"
                end_log(conn, log_id, "OK", detail, total)
                print("Sincronizacion v2 finalizada.")
                print(detail)
                print("Escrituras productivas: NINGUNA")
            except Exception as exc:
                end_log(conn, log_id, "ERROR", repr(exc), 0)
                raise
        if args.diagnostico:
            diagnostico(conn)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
