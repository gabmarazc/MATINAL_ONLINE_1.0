#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GESCOM RAW Sync v2.2 para MATINAL ONLINE.

- Solo endpoints GET.
- Destino exclusivo: data/matinal_api_test.db.
- Conserva payload completo, JSON por entidad y tablas RAW normalizadas.
- No calcula CantBase, PesoKg, NetoItem ni reglas MATINAL.
- No modifica data/matinal.db ni Excel.
Escrituras productivas: NINGUNA.
"""

from __future__ import annotations
import argparse, hashlib, json, os, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import requests

DB_PATH = Path("data") / "matinal_api_test.db"
AUTH_BASE = "https://auth.gescom.online"
CLIENT_ID = "gcw-web-api"
TIMEOUT = 90
PAGE_SALES = 500
PAGE_ARTICLES = 1000
SCHEMA_SQL = "-- GESCOM -> MATINAL ONLINE\n-- Esquema RAW completo v2.2 para SQLite\n-- Objetivo: recibir, congelar y auditar respuestas GET de GESCOM.\n-- Este archivo NO consume APIs. Define exclusivamente la persistencia SQLite.\n-- Destino previsto: data/matinal_api_test.db\n-- Escrituras productivas: NINGUNA.\n\nPRAGMA foreign_keys = ON;\nPRAGMA journal_mode = WAL;\n\nBEGIN IMMEDIATE;\n\n-- ============================================================================\n-- 0. CONTROL, TRAZABILIDAD Y RESPUESTA ORIGINAL DE CADA ENDPOINT\n-- ============================================================================\n\nCREATE TABLE IF NOT EXISTS raw_sync_runs (\n    run_id INTEGER PRIMARY KEY AUTOINCREMENT,\n    proceso TEXT NOT NULL,\n    modo TEXT NOT NULL CHECK (modo IN ('BOOTSTRAP','SNAPSHOT','INCREMENTAL','AUDITORIA')),\n    iniciado_utc TEXT NOT NULL,\n    finalizado_utc TEXT,\n    estado TEXT NOT NULL CHECK (estado IN ('EN_CURSO','OK','ERROR','CANCELADO')),\n    parametros_json TEXT,\n    detalle TEXT,\n    registros_recibidos INTEGER NOT NULL DEFAULT 0,\n    registros_insertados INTEGER NOT NULL DEFAULT 0,\n    registros_actualizados INTEGER NOT NULL DEFAULT 0,\n    registros_sin_cambios INTEGER NOT NULL DEFAULT 0,\n    registros_eliminados INTEGER NOT NULL DEFAULT 0,\n    error_texto TEXT\n);\n\nCREATE TABLE IF NOT EXISTS raw_sync_state (\n    entidad TEXT PRIMARY KEY,\n    endpoint TEXT NOT NULL,\n    cursor_tipo TEXT,\n    cursor_valor TEXT,\n    fecha_desde TEXT,\n    fecha_hasta TEXT,\n    ultima_sync_utc TEXT,\n    ultima_sync_ok_utc TEXT,\n    estado TEXT,\n    detalle TEXT\n);\n\nCREATE TABLE IF NOT EXISTS raw_api_payloads (\n    payload_id INTEGER PRIMARY KEY AUTOINCREMENT,\n    run_id INTEGER,\n    modulo TEXT NOT NULL,\n    endpoint TEXT NOT NULL,\n    metodo TEXT NOT NULL DEFAULT 'GET' CHECK (metodo = 'GET'),\n    parametros_json TEXT,\n    http_status INTEGER,\n    capturado_utc TEXT NOT NULL,\n    hash_payload TEXT NOT NULL,\n    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),\n    UNIQUE(endpoint, hash_payload),\n    FOREIGN KEY (run_id) REFERENCES raw_sync_runs(run_id)\n);\nCREATE INDEX IF NOT EXISTS ix_raw_api_payloads_endpoint_fecha\nON raw_api_payloads(endpoint, capturado_utc);\n\nCREATE TABLE IF NOT EXISTS raw_sync_errors (\n    error_id INTEGER PRIMARY KEY AUTOINCREMENT,\n    run_id INTEGER,\n    entidad TEXT,\n    clave TEXT,\n    endpoint TEXT,\n    error_tipo TEXT,\n    error_texto TEXT NOT NULL,\n    payload_json TEXT,\n    ocurrido_utc TEXT NOT NULL,\n    FOREIGN KEY (run_id) REFERENCES raw_sync_runs(run_id)\n);\n\n-- ============================================================================\n-- 1. RAW TRANSACCIONAL DE VENTAS. Lectura v2 y Cambios v3.\n-- ============================================================================\n\nCREATE TABLE IF NOT EXISTS raw_ventas (\n    venta_id INTEGER PRIMARY KEY,\n    identificador TEXT,\n    origen TEXT,\n    estado TEXT,\n    etapa TEXT,\n    etapa_nota TEXT,\n    requiere_autorizacion INTEGER,\n    cerrada INTEGER,\n    codigo_tipo_venta TEXT,\n    es_credito INTEGER,\n    es_sin_cargo INTEGER,\n    codigo_cliente TEXT,\n    codigo_vendedor TEXT,\n    codigo_ruta TEXT,\n    codigo_empresa TEXT,\n    codigo_punto_venta INTEGER,\n    codigo_sede TEXT,\n    codigo_condicion_pago TEXT,\n    codigo_motivo_cambio TEXT,\n    motivo TEXT,\n    fecha_pedido TEXT,\n    fecha_entrega TEXT,\n    observaciones TEXT,\n    observaciones_internas TEXT,\n    descuento_global REAL,\n    venta_directa INTEGER,\n    metodo_entrega INTEGER,\n    lote_id TEXT,\n    numero_comprobante INTEGER,\n    codigo_reparto INTEGER,\n    codigo_chofer TEXT,\n    importe_neto REAL,\n    importe_exento REAL,\n    importe_conc REAL,\n    importe_iva REAL,\n    importe_tributos REAL,\n    importe_total REAL,\n    tags_json TEXT CHECK (tags_json IS NULL OR json_valid(tags_json)),\n    propiedades_json TEXT CHECK (propiedades_json IS NULL OR json_valid(propiedades_json)),\n    combos_json TEXT CHECK (combos_json IS NULL OR json_valid(combos_json)),\n    venta_referenciada_json TEXT CHECK (venta_referenciada_json IS NULL OR json_valid(venta_referenciada_json)),\n    comprobante_principal_json TEXT CHECK (comprobante_principal_json IS NULL OR json_valid(comprobante_principal_json)),\n    json_raw TEXT NOT NULL CHECK (json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    actualizado_utc TEXT NOT NULL,\n    eliminado INTEGER NOT NULL DEFAULT 0,\n    eliminado_utc TEXT\n);\nCREATE INDEX IF NOT EXISTS ix_raw_ventas_fecha ON raw_ventas(fecha_pedido);\nCREATE INDEX IF NOT EXISTS ix_raw_ventas_cliente ON raw_ventas(codigo_cliente);\nCREATE INDEX IF NOT EXISTS ix_raw_ventas_vendedor ON raw_ventas(codigo_vendedor);\nCREATE INDEX IF NOT EXISTS ix_raw_ventas_reparto ON raw_ventas(codigo_reparto);\n\nCREATE TABLE IF NOT EXISTS raw_venta_items (\n    venta_id INTEGER NOT NULL,\n    venta_item_id INTEGER NOT NULL,\n    orden_item INTEGER,\n    item_id INTEGER,\n    codigo_item TEXT,\n    codigo_alicuota_iva TEXT,\n    codigo_lista_precio TEXT,\n    codigo_deposito TEXT,\n    codigo_lote TEXT,\n    codigo_combo TEXT,\n    codigo_combo_comp TEXT,\n    cantidad REAL,\n    codigo_unidad TEXT,\n    unidad_factor REAL,\n    piezas REAL,\n    precio_unitario REAL,\n    precio_unitario_iva REAL,\n    precio_unitario_total REAL,\n    precio_costo REAL,\n    descuento REAL,\n    descuento_neto REAL,\n    descuento_final REAL,\n    numero_serie TEXT,\n    estado_pesaje INTEGER,\n    importe_neto REAL,\n    importe_exento REAL,\n    importe_conc REAL,\n    importe_iva REAL,\n    importe_tributos REAL,\n    importe_total REAL,\n    comentario TEXT,\n    descuentos_json TEXT CHECK (descuentos_json IS NULL OR json_valid(descuentos_json)),\n    propiedades_json TEXT CHECK (propiedades_json IS NULL OR json_valid(propiedades_json)),\n    json_raw TEXT NOT NULL CHECK (json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    actualizado_utc TEXT NOT NULL,\n    PRIMARY KEY (venta_id, venta_item_id),\n    FOREIGN KEY (venta_id) REFERENCES raw_ventas(venta_id) ON DELETE CASCADE\n);\nCREATE INDEX IF NOT EXISTS ix_raw_venta_items_codigo ON raw_venta_items(codigo_item);\n\nCREATE TABLE IF NOT EXISTS raw_venta_item_descuentos (\n    venta_id INTEGER NOT NULL,\n    venta_item_id INTEGER NOT NULL,\n    descuento_orden INTEGER NOT NULL,\n    descuento_fuente_id INTEGER,\n    descuento REAL,\n    descuento_detalle TEXT,\n    otorgado_por_promocion INTEGER,\n    promocion_id INTEGER,\n    combo_componente_id INTEGER,\n    propiedades_json TEXT CHECK (propiedades_json IS NULL OR json_valid(propiedades_json)),\n    json_raw TEXT NOT NULL CHECK (json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    PRIMARY KEY (venta_id, venta_item_id, descuento_orden),\n    FOREIGN KEY (venta_id, venta_item_id)\n        REFERENCES raw_venta_items(venta_id, venta_item_id) ON DELETE CASCADE\n);\n\nCREATE TABLE IF NOT EXISTS raw_venta_combos (\n    venta_id INTEGER NOT NULL,\n    combo_orden INTEGER NOT NULL,\n    codigo_combo TEXT,\n    cantidad INTEGER,\n    json_raw TEXT NOT NULL CHECK (json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    PRIMARY KEY (venta_id, combo_orden),\n    FOREIGN KEY (venta_id) REFERENCES raw_ventas(venta_id) ON DELETE CASCADE\n);\n\nCREATE TABLE IF NOT EXISTS raw_venta_referenciada (\n    venta_id INTEGER PRIMARY KEY,\n    venta_referenciada_id INTEGER,\n    numero_comprobante INTEGER,\n    origen TEXT,\n    identificador TEXT,\n    codigo_empresa TEXT,\n    codigo_punto_venta INTEGER,\n    codigo_tipo_comprobante TEXT,\n    json_raw TEXT NOT NULL CHECK (json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    FOREIGN KEY (venta_id) REFERENCES raw_ventas(venta_id) ON DELETE CASCADE\n);\n\n-- Se conserva el objeto completo porque el mapa documenta 17 propiedades.\n-- Las columnas conocidas se normalizan; cualquier propiedad adicional permanece en json_raw.\nCREATE TABLE IF NOT EXISTS raw_comprobante_principal (\n    venta_id INTEGER PRIMARY KEY,\n    numero_comprobante INTEGER,\n    codigo_tipo_comprobante TEXT,\n    letra_comprobante TEXT,\n    codigo_empresa TEXT,\n    codigo_punto_venta INTEGER,\n    fecha_comprobante TEXT,\n    codigo_tipo_facturacion TEXT,\n    importe_neto REAL,\n    importe_exento REAL,\n    importe_conc REAL,\n    importe_iva REAL,\n    importe_tributos REAL,\n    importe_total REAL,\n    cae TEXT,\n    json_raw TEXT NOT NULL CHECK (json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    FOREIGN KEY (venta_id) REFERENCES raw_ventas(venta_id) ON DELETE CASCADE\n);\n\nCREATE TABLE IF NOT EXISTS raw_ventas_cambios (\n    cambio_id INTEGER PRIMARY KEY AUTOINCREMENT,\n    run_id INTEGER,\n    position_origen TEXT,\n    last_position TEXT NOT NULL,\n    tipo TEXT NOT NULL CHECK (tipo IN ('NOVEDAD','ELIMINADA')),\n    venta_id INTEGER NOT NULL,\n    numero_comprobante INTEGER,\n    origen TEXT,\n    identificador TEXT,\n    procesado INTEGER NOT NULL DEFAULT 0,\n    procesado_utc TEXT,\n    json_raw TEXT NOT NULL CHECK (json_valid(json_raw)),\n    capturado_utc TEXT NOT NULL,\n    UNIQUE(last_position, tipo, venta_id),\n    FOREIGN KEY (run_id) REFERENCES raw_sync_runs(run_id)\n);\n\n-- ============================================================================\n-- 2. RAW CLIENTES Y ASIGNACION ACTUAL\n-- ============================================================================\n\nCREATE TABLE IF NOT EXISTS raw_clientes (\n    codigo TEXT PRIMARY KEY,\n    nombre TEXT,\n    razon_social TEXT,\n    direccion_entrega TEXT,\n    telefono TEXT,\n    codigo_empresa TEXT,\n    codigo_lista_precio TEXT,\n    codigo_ramo TEXT,\n    codigo_subramo TEXT,\n    codigo_sede TEXT,\n    codigo_deposito TEXT,\n    codigo_segmento TEXT,\n    localidad TEXT,\n    codigo_tipo_documento TEXT,\n    codigo_condicion_iva TEXT,\n    descuento_global REAL,\n    email TEXT,\n    provincia TEXT,\n    codigo_condicion_pago TEXT,\n    codigo_postal TEXT,\n    nro_documento TEXT,\n    contacto TEXT,\n    es_foco INTEGER,\n    percepcion_ib REAL,\n    margen_maximo REAL,\n    tope_venta REAL,\n    orden_visita INTEGER,\n    latitud REAL,\n    longitud REAL,\n    minimo_venta_importe REAL,\n    minimo_venta_moneda TEXT,\n    demora_entrega_dias INTEGER,\n    comentario TEXT,\n    notas TEXT,\n    tope_saldo_dinero REAL,\n    tope_saldo_dinero_moneda TEXT,\n    tope_saldo_dinero_factor REAL,\n    tope_saldo_dias INTEGER,\n    tope_saldo_boletas INTEGER,\n    tags_json TEXT CHECK (tags_json IS NULL OR json_valid(tags_json)),\n    listas_especiales_json TEXT CHECK (listas_especiales_json IS NULL OR json_valid(listas_especiales_json)),\n    propiedades_json TEXT CHECK (propiedades_json IS NULL OR json_valid(propiedades_json)),\n    rutas_preventa_json TEXT CHECK (rutas_preventa_json IS NULL OR json_valid(rutas_preventa_json)),\n    json_raw TEXT NOT NULL CHECK (json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    actualizado_utc TEXT NOT NULL\n);\n\nCREATE TABLE IF NOT EXISTS raw_cliente_rutas (\n    codigo_cliente TEXT NOT NULL,\n    ruta_orden INTEGER NOT NULL,\n    codigo_ruta TEXT,\n    codigo_vendedor TEXT,\n    lunes INTEGER,\n    martes INTEGER,\n    miercoles INTEGER,\n    jueves INTEGER,\n    viernes INTEGER,\n    sabado INTEGER,\n    domingo INTEGER,\n    frecuencia TEXT,\n    orden_visita INTEGER,\n    fecha_primera_visita TEXT,\n    grupos_fuerza_venta_json TEXT CHECK (grupos_fuerza_venta_json IS NULL OR json_valid(grupos_fuerza_venta_json)),\n    json_raw TEXT NOT NULL CHECK (json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    PRIMARY KEY (codigo_cliente, ruta_orden),\n    FOREIGN KEY (codigo_cliente) REFERENCES raw_clientes(codigo) ON DELETE CASCADE\n);\nCREATE INDEX IF NOT EXISTS ix_raw_cliente_rutas_vendedor\nON raw_cliente_rutas(codigo_vendedor, codigo_ruta);\n\n-- ============================================================================\n-- 3. RAW ARTICULOS, UNIDADES Y CLASIFICACIONES\n-- ============================================================================\n\nCREATE TABLE IF NOT EXISTS raw_articulos (\n    codigo TEXT PRIMARY KEY,\n    descripcion TEXT,\n    codigo_rubro TEXT,\n    precio_costo REAL,\n    impuesto_interno REAL,\n    codigo_alicuota_iva TEXT,\n    codigo_linea TEXT,\n    codigo_marca TEXT,\n    codigo_familia TEXT,\n    codigo_segmento_margen TEXT,\n    unidad_venta TEXT,\n    unidades_bulto_venta REAL,\n    unidad_venta_base TEXT,\n    unidades_minima_venta REAL,\n    descuento_maximo REAL,\n    factor_peso REAL,\n    factor_volumen REAL,\n    codigo_barras TEXT,\n    codigo_proveedor TEXT,\n    codigo_empresa TEXT,\n    apto_comodato INTEGER,\n    bloqueado INTEGER,\n    bloqueado_motivo TEXT,\n    combo_iteractivo INTEGER,\n    incontable INTEGER,\n    unidades_por_bulto REAL,\n    motivo_bloqueo TEXT,\n    ponderado_pieza REAL,\n    preparacion_consolidada TEXT,\n    track_piezas_en_stock INTEGER,\n    tags_json TEXT CHECK (tags_json IS NULL OR json_valid(tags_json)),\n    unidades_permitidas_json TEXT CHECK (unidades_permitidas_json IS NULL OR json_valid(unidades_permitidas_json)),\n    json_raw TEXT NOT NULL CHECK (json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    actualizado_utc TEXT NOT NULL\n);\nCREATE INDEX IF NOT EXISTS ix_raw_articulos_proveedor ON raw_articulos(codigo_proveedor);\nCREATE INDEX IF NOT EXISTS ix_raw_articulos_marca ON raw_articulos(codigo_marca);\n\nCREATE TABLE IF NOT EXISTS raw_articulo_unidades (\n    codigo_articulo TEXT NOT NULL,\n    unidad_orden INTEGER NOT NULL,\n    codigo_unidad TEXT,\n    factor REAL,\n    habilita_venta INTEGER,\n    habilita_compra INTEGER,\n    habilita_carga INTEGER,\n    minimo_venta REAL,\n    multiplo_venta REAL,\n    default_venta INTEGER,\n    default_compra INTEGER,\n    default_carga INTEGER,\n    codigo_barras TEXT,\n    json_raw TEXT NOT NULL CHECK (json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    PRIMARY KEY (codigo_articulo, unidad_orden),\n    FOREIGN KEY (codigo_articulo) REFERENCES raw_articulos(codigo) ON DELETE CASCADE\n);\n\nCREATE TABLE IF NOT EXISTS raw_marcas (codigo TEXT PRIMARY KEY, descripcion TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_familias (codigo TEXT PRIMARY KEY, descripcion TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_lineas (codigo TEXT PRIMARY KEY, descripcion TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_rubros (codigo TEXT PRIMARY KEY, descripcion TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_segmentos_margen (codigo TEXT PRIMARY KEY, descripcion TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_unidades (codigo TEXT PRIMARY KEY, descripcion TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\n\n-- ============================================================================\n-- 4. RAW COMERCIAL Y CONFIGURACION\n-- ============================================================================\n\nCREATE TABLE IF NOT EXISTS raw_proveedores (\n    codigo TEXT PRIMARY KEY,\n    nombre TEXT,\n    direccion TEXT,\n    telefono TEXT,\n    localidad TEXT,\n    codigo_tipo_documento TEXT,\n    codigo_condicion_iva TEXT,\n    email TEXT,\n    provincia TEXT,\n    codigo_condicion_pago TEXT,\n    codigo_postal TEXT,\n    nro_documento TEXT,\n    contacto TEXT,\n    tags_json TEXT CHECK(tags_json IS NULL OR json_valid(tags_json)),\n    comentario TEXT,\n    notas TEXT,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    actualizado_utc TEXT NOT NULL\n);\n\nCREATE TABLE IF NOT EXISTS raw_empresas (\n    codigo TEXT PRIMARY KEY, nombre TEXT, razon_social TEXT, documento TEXT, direccion TEXT,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL\n);\n\nCREATE TABLE IF NOT EXISTS raw_empleados (\n    codigo TEXT PRIMARY KEY, nombre TEXT, codigo_superior TEXT,\n    tipos_json TEXT CHECK(tipos_json IS NULL OR json_valid(tipos_json)),\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL\n);\nCREATE TABLE IF NOT EXISTS raw_vendedores (codigo TEXT PRIMARY KEY, nombre TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_tipos_empleado (codigo TEXT PRIMARY KEY, descripcion TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\n\nCREATE TABLE IF NOT EXISTS raw_rutas_preventa (\n    codigo TEXT PRIMARY KEY, descripcion TEXT, codigo_vendedor TEXT,\n    lunes INTEGER, martes INTEGER, miercoles INTEGER, jueves INTEGER,\n    viernes INTEGER, sabado INTEGER, domingo INTEGER, frecuencia TEXT,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL\n);\n\nCREATE TABLE IF NOT EXISTS raw_condiciones_pago (\n    codigo TEXT PRIMARY KEY, descripcion TEXT, dias INTEGER, cuotas INTEGER,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL\n);\nCREATE TABLE IF NOT EXISTS raw_listas_precio (\n    codigo TEXT PRIMARY KEY, descripcion TEXT, es_general INTEGER,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL\n);\nCREATE TABLE IF NOT EXISTS raw_ramos (\n    codigo TEXT PRIMARY KEY, descripcion TEXT,\n    subramos_json TEXT CHECK(subramos_json IS NULL OR json_valid(subramos_json)),\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL\n);\nCREATE TABLE IF NOT EXISTS raw_ramo_subramos (\n    codigo_ramo TEXT NOT NULL, codigo_subramo TEXT NOT NULL, descripcion_subramo TEXT,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    PRIMARY KEY(codigo_ramo, codigo_subramo),\n    FOREIGN KEY(codigo_ramo) REFERENCES raw_ramos(codigo) ON DELETE CASCADE\n);\nCREATE TABLE IF NOT EXISTS raw_subramos (codigo TEXT PRIMARY KEY, descripcion TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_grupos_fuerza_venta (codigo TEXT PRIMARY KEY, descripcion TEXT, tags_json TEXT CHECK(tags_json IS NULL OR json_valid(tags_json)), json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_etapas_venta (etapa TEXT PRIMARY KEY, orden INTEGER, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_motivos_venta (id INTEGER PRIMARY KEY, codigo TEXT, descripcion TEXT, codigo_tipo_venta TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_tipos_comprobante (codigo TEXT PRIMARY KEY, descripcion TEXT, codigo_clase TEXT, descripcion_clase TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_tipos_facturacion (codigo TEXT PRIMARY KEY, descripcion TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_alicuotas_iva (codigo TEXT PRIMARY KEY, descripcion TEXT, no_gravado INTEGER, porcentaje REAL, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_tags (id INTEGER PRIMARY KEY, categoria TEXT, nombre TEXT, descripcion TEXT, color_letra TEXT, color_fondo TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_categorias_tag (id INTEGER PRIMARY KEY, nombre TEXT, descripcion TEXT, color_letra TEXT, color_fondo TEXT, tags_json TEXT CHECK(tags_json IS NULL OR json_valid(tags_json)), json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_provincias (codigo TEXT PRIMARY KEY, descripcion TEXT, json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\n\n-- Combos y precios vigentes: separados de la fotografia transaccional.\nCREATE TABLE IF NOT EXISTS raw_combos (id INTEGER PRIMARY KEY, codigo TEXT, descripcion TEXT, condicion_json TEXT, componentes_json TEXT CHECK(componentes_json IS NULL OR json_valid(componentes_json)), json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL, capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL);\nCREATE TABLE IF NOT EXISTS raw_precios_vigentes (\n    codigo_item TEXT NOT NULL, codigo_lista_precio TEXT NOT NULL,\n    codigo_unidad TEXT NOT NULL, factor REAL NOT NULL,\n    precio_neto REAL, codigo_moneda TEXT, default_venta INTEGER,\n    porcentaje_alicuota_iva REAL, impuesto_interno REAL,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)), hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL, actualizado_utc TEXT NOT NULL,\n    PRIMARY KEY(codigo_item, codigo_lista_precio, codigo_unidad, factor)\n);\n\n-- ============================================================================\n-- 5. RAW INTEGRACIONES PEPSICO\n-- ============================================================================\n\nCREATE TABLE IF NOT EXISTS raw_pepsico_exhibidores (\n    source_orden INTEGER PRIMARY KEY AUTOINCREMENT,\n    codigo_cliente TEXT,\n    codigo_item TEXT,\n    cantidad_disponible REAL,\n    es_foto_exito INTEGER,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    snapshot_utc TEXT NOT NULL\n);\nCREATE INDEX IF NOT EXISTS ix_raw_pepsico_exhibidores_cliente\nON raw_pepsico_exhibidores(codigo_cliente, codigo_item);\n\nCREATE TABLE IF NOT EXISTS raw_pepsico_infaltables (\n    source_orden INTEGER PRIMARY KEY AUTOINCREMENT,\n    codigo_cliente TEXT,\n    codigo_item TEXT,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    snapshot_utc TEXT NOT NULL\n);\nCREATE INDEX IF NOT EXISTS ix_raw_pepsico_infaltables_cliente\nON raw_pepsico_infaltables(codigo_cliente, codigo_item);\n\n-- Sin PK por cliente: la API permite clientes repetidos.\nCREATE TABLE IF NOT EXISTS raw_pepsico_tienda_perfecta (\n    source_orden INTEGER PRIMARY KEY AUTOINCREMENT,\n    codigo_cliente TEXT,\n    ramo TEXT,\n    subramo TEXT,\n    perfect_store_type INTEGER,\n    perfect_store_comment TEXT,\n    perfect_store_state TEXT,\n    perfect_store_portafolio_porc REAL,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    snapshot_utc TEXT NOT NULL\n);\nCREATE INDEX IF NOT EXISTS ix_raw_pepsico_tp_cliente\nON raw_pepsico_tienda_perfecta(codigo_cliente);\n\n-- ============================================================================\n-- 6. RAW DISTRIBUCION\n-- ============================================================================\n\nCREATE TABLE IF NOT EXISTS raw_ordenes_preparacion (\n    orden_id INTEGER PRIMARY KEY,\n    estado TEXT,\n    fecha_carga TEXT,\n    fecha_creacion TEXT,\n    fecha_armado TEXT,\n    bodeguista TEXT,\n    nombre_bodeguista TEXT,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    actualizado_utc TEXT NOT NULL\n);\nCREATE TABLE IF NOT EXISTS raw_ordenes_preparacion_ventas (\n    orden_id INTEGER NOT NULL,\n    venta_id INTEGER NOT NULL,\n    empresa TEXT,\n    punto_venta INTEGER,\n    tipo_venta TEXT,\n    numero_comprobante INTEGER,\n    comprobante TEXT,\n    estado_venta TEXT,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    PRIMARY KEY(orden_id, venta_id),\n    FOREIGN KEY(orden_id) REFERENCES raw_ordenes_preparacion(orden_id) ON DELETE CASCADE\n);\n\n-- Repartos v2 puede aportar mas atributos. Se conserva el objeto completo y\n-- se normalizan las claves de enlace confirmadas por ventas y cambios.\nCREATE TABLE IF NOT EXISTS raw_repartos (\n    reparto_id INTEGER PRIMARY KEY,\n    codigo_reparto INTEGER,\n    fecha TEXT,\n    etapa TEXT,\n    cerrado INTEGER,\n    codigo_chofer TEXT,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    actualizado_utc TEXT NOT NULL,\n    eliminado INTEGER NOT NULL DEFAULT 0,\n    eliminado_utc TEXT\n);\nCREATE TABLE IF NOT EXISTS raw_reparto_ventas (\n    reparto_id INTEGER NOT NULL,\n    venta_id INTEGER NOT NULL,\n    json_raw TEXT NOT NULL CHECK(json_valid(json_raw)),\n    hash_raw TEXT NOT NULL,\n    capturado_utc TEXT NOT NULL,\n    PRIMARY KEY(reparto_id, venta_id),\n    FOREIGN KEY(reparto_id) REFERENCES raw_repartos(reparto_id) ON DELETE CASCADE\n);\nCREATE TABLE IF NOT EXISTS raw_repartos_cambios (\n    cambio_id INTEGER PRIMARY KEY AUTOINCREMENT,\n    run_id INTEGER,\n    trxid_origen TEXT,\n    ultima_trxid TEXT NOT NULL,\n    tipo TEXT NOT NULL CHECK(tipo IN ('NOVEDAD','ELIMINADO')),\n    reparto_id INTEGER NOT NULL,\n    procesado INTEGER NOT NULL DEFAULT 0,\n    procesado_utc TEXT,\n    capturado_utc TEXT NOT NULL,\n    UNIQUE(ultima_trxid, tipo, reparto_id),\n    FOREIGN KEY(run_id) REFERENCES raw_sync_runs(run_id)\n);\n\n-- ============================================================================\n-- 7. VISTAS DE AUDITORIA RAW. SIN REGLAS DE NEGOCIO.\n-- ============================================================================\n\nCREATE VIEW IF NOT EXISTS audit_raw_conteos AS\nSELECT 'raw_ventas' entidad, COUNT(*) filas FROM raw_ventas\nUNION ALL SELECT 'raw_venta_items', COUNT(*) FROM raw_venta_items\nUNION ALL SELECT 'raw_clientes', COUNT(*) FROM raw_clientes\nUNION ALL SELECT 'raw_cliente_rutas', COUNT(*) FROM raw_cliente_rutas\nUNION ALL SELECT 'raw_articulos', COUNT(*) FROM raw_articulos\nUNION ALL SELECT 'raw_articulo_unidades', COUNT(*) FROM raw_articulo_unidades\nUNION ALL SELECT 'raw_proveedores', COUNT(*) FROM raw_proveedores\nUNION ALL SELECT 'raw_pepsico_exhibidores', COUNT(*) FROM raw_pepsico_exhibidores\nUNION ALL SELECT 'raw_pepsico_infaltables', COUNT(*) FROM raw_pepsico_infaltables\nUNION ALL SELECT 'raw_pepsico_tienda_perfecta', COUNT(*) FROM raw_pepsico_tienda_perfecta\nUNION ALL SELECT 'raw_ordenes_preparacion', COUNT(*) FROM raw_ordenes_preparacion\nUNION ALL SELECT 'raw_repartos', COUNT(*) FROM raw_repartos;\n\nCREATE VIEW IF NOT EXISTS audit_raw_integridad AS\nSELECT 'items_huerfanos_venta' control, COUNT(*) resultado\nFROM raw_venta_items i LEFT JOIN raw_ventas v ON v.venta_id=i.venta_id\nWHERE v.venta_id IS NULL\nUNION ALL\nSELECT 'descuentos_huerfanos_item', COUNT(*)\nFROM raw_venta_item_descuentos d\nLEFT JOIN raw_venta_items i\n  ON i.venta_id=d.venta_id AND i.venta_item_id=d.venta_item_id\nWHERE i.venta_id IS NULL\nUNION ALL\nSELECT 'cliente_rutas_huerfanas', COUNT(*)\nFROM raw_cliente_rutas r LEFT JOIN raw_clientes c ON c.codigo=r.codigo_cliente\nWHERE c.codigo IS NULL\nUNION ALL\nSELECT 'articulo_unidades_huerfanas', COUNT(*)\nFROM raw_articulo_unidades u LEFT JOIN raw_articulos a ON a.codigo=u.codigo_articulo\nWHERE a.codigo IS NULL\nUNION ALL\nSELECT 'orden_ventas_huerfanas', COUNT(*)\nFROM raw_ordenes_preparacion_ventas ov\nLEFT JOIN raw_ordenes_preparacion o ON o.orden_id=ov.orden_id\nWHERE o.orden_id IS NULL;\n\nCREATE VIEW IF NOT EXISTS audit_raw_json_invalido AS\nSELECT 'raw_ventas' entidad, COUNT(*) resultado FROM raw_ventas WHERE NOT json_valid(json_raw)\nUNION ALL SELECT 'raw_venta_items', COUNT(*) FROM raw_venta_items WHERE NOT json_valid(json_raw)\nUNION ALL SELECT 'raw_clientes', COUNT(*) FROM raw_clientes WHERE NOT json_valid(json_raw)\nUNION ALL SELECT 'raw_articulos', COUNT(*) FROM raw_articulos WHERE NOT json_valid(json_raw)\nUNION ALL SELECT 'raw_proveedores', COUNT(*) FROM raw_proveedores WHERE NOT json_valid(json_raw)\nUNION ALL SELECT 'raw_api_payloads', COUNT(*) FROM raw_api_payloads WHERE NOT json_valid(payload_json);\n\nCOMMIT;\n\n-- Fin del esquema.\n-- No crea vistas de negocio, no calcula CantBase/PesoKg/NetoItem y no realiza\n-- JOINs analiticos. Todo eso corresponde a STAGING, despues de auditar RAW.\n"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def jdump(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def jhash(v):
    return hashlib.sha256(jdump(v).encode("utf-8")).hexdigest()


def b(v):
    return None if v is None else int(bool(v))


def env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Falta variable de entorno obligatoria: {name}")
    if name == "GESCOM_SITE" and ("<a " in value.lower() or "</a>" in value.lower()):
        raise RuntimeError("GESCOM_SITE contiene HTML; debe contener solo la URL")
    return value


class Client:
    def __init__(self):
        self.realm = env("GESCOM_REALM")
        self.site = env("GESCOM_SITE").rstrip("/")
        self.user = env("GESCOM_USER")
        self.password = env("GESCOM_PASSWORD")
        self.s = requests.Session()
        self.token = ""
        self.expires = 0.0

    def auth(self):
        r = self.s.post(
            f"{AUTH_BASE}/realms/{self.realm}/protocol/openid-connect/token",
            data={
                "client_id": CLIENT_ID,
                "grant_type": "password",
                "username": self.user,
                "password": self.password,
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        p = r.json()
        self.token = p["access_token"]
        self.expires = time.time() + int(p.get("expires_in", 300)) - 30

    def get(self, path, params=None):
        if not self.token or time.time() >= self.expires:
            self.auth()
        r = self.s.get(
            self.site + path,
            params=params,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=TIMEOUT,
        )
        if r.status_code == 401:
            self.auth()
            r = self.s.get(
                self.site + path,
                params=params,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=TIMEOUT,
            )
        r.raise_for_status()
        return r.json(), r.status_code


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init_db(c):
    c.executescript(SCHEMA_SQL)
    c.commit()


def run_begin(c, proceso, modo, params):
    cur = c.execute(
        "INSERT INTO raw_sync_runs(proceso,modo,iniciado_utc,estado,parametros_json) VALUES(?,?,?,?,?)",
        (proceso, modo, utc_now(), "EN_CURSO", jdump(params)),
    )
    c.commit()
    return cur.lastrowid


def run_end(c, rid, state, detail, received=0, error=None):
    c.execute(
        "UPDATE raw_sync_runs SET finalizado_utc=?,estado=?,detalle=?,registros_recibidos=?,error_texto=? WHERE run_id=?",
        (utc_now(), state, detail, received, error, rid),
    )
    c.commit()


def payload(c, rid, module, path, params, status, data):
    raw = jdump(data)
    c.execute(
        "INSERT OR IGNORE INTO raw_api_payloads(run_id,modulo,endpoint,parametros_json,http_status,capturado_utc,hash_payload,payload_json) VALUES(?,?,?,?,?,?,?,?)",
        (
            rid,
            module,
            path,
            jdump(params or {}),
            status,
            utc_now(),
            hashlib.sha256(raw.encode()).hexdigest(),
            raw,
        ),
    )


def fetch(cli, c, rid, module, path, params=None):
    data, status = cli.get(path, params)
    payload(c, rid, module, path, params, status, data)
    return data


def replace_simple(c, table, rows, mapfn):
    c.execute(f"DELETE FROM {table}")
    now = utc_now()
    n = 0
    for r in rows:
        cols, vals = mapfn(r, now)
        marks = ",".join("?" for _ in vals)
        c.execute(f"INSERT INTO {table}({','.join(cols)}) VALUES({marks})", vals)
        n += 1
    return n


def simple_catalog(c, table, rows, key="codigo", desc="descripcion"):
    def m(r, now):
        return (
            [key, desc, "json_raw", "hash_raw", "capturado_utc", "actualizado_utc"],
            [
                str(r.get(key)),
                r.get(desc) or r.get("nombre"),
                jdump(r),
                jhash(r),
                now,
                now,
            ],
        )

    return replace_simple(c, table, [r for r in rows if r.get(key) is not None], m)


def sync_sales(cli, c, rid, fd, fh):
    page = 0
    nv = ni = 0
    while True:
        params = {
            "fechadesde": fd,
            "fechahasta": fh,
            "pagesize": PAGE_SALES,
            "pagestoskip": page,
            "pagestotake": 1,
        }
        rows = fetch(cli, c, rid, "ventas", "/data/cmd/ventas/api/v2/get", params)
        if not isinstance(rows, list):
            raise RuntimeError("Ventas v2 no devolvio array")
        for s in rows:
            upsert_sale(c, s)
            nv += 1
            ni += len(s.get("items") or [])
        c.commit()
        if len(rows) < PAGE_SALES:
            break
        page += 1
    return nv, ni


def upsert_sale(c, s):
    now = utc_now()
    sid = int(s["id"])
    raw = jdump(s)
    cols = [
        "venta_id",
        "identificador",
        "origen",
        "estado",
        "etapa",
        "etapa_nota",
        "requiere_autorizacion",
        "cerrada",
        "codigo_tipo_venta",
        "es_credito",
        "es_sin_cargo",
        "codigo_cliente",
        "codigo_vendedor",
        "codigo_ruta",
        "codigo_empresa",
        "codigo_punto_venta",
        "codigo_sede",
        "codigo_condicion_pago",
        "codigo_motivo_cambio",
        "motivo",
        "fecha_pedido",
        "fecha_entrega",
        "observaciones",
        "observaciones_internas",
        "descuento_global",
        "venta_directa",
        "metodo_entrega",
        "lote_id",
        "numero_comprobante",
        "codigo_reparto",
        "codigo_chofer",
        "importe_neto",
        "importe_exento",
        "importe_conc",
        "importe_iva",
        "importe_tributos",
        "importe_total",
        "tags_json",
        "propiedades_json",
        "combos_json",
        "venta_referenciada_json",
        "comprobante_principal_json",
        "json_raw",
        "hash_raw",
        "capturado_utc",
        "actualizado_utc",
        "eliminado",
        "eliminado_utc",
    ]
    vals = [
        sid,
        s.get("identificador"),
        s.get("origen"),
        s.get("estado"),
        s.get("etapa"),
        s.get("etapaNota"),
        b(s.get("requiereAutorizacion")),
        b(s.get("cerrada")),
        s.get("codigoTipoVenta"),
        b(s.get("esCredito")),
        b(s.get("esSinCargo")),
        s.get("codigoCliente"),
        s.get("codigoVendedor"),
        s.get("codigoRuta"),
        s.get("codigoEmpresa"),
        s.get("codigoPuntoVenta"),
        s.get("codigoSede"),
        s.get("codigoCondicionPago"),
        s.get("codigoMotivoCambio"),
        s.get("motivo"),
        s.get("fechaPedido"),
        s.get("fechaEntrega"),
        s.get("observaciones"),
        s.get("observacionesInternas"),
        s.get("descuentoGlobal"),
        b(s.get("ventaDirecta")),
        s.get("metodoEntrega"),
        s.get("loteId"),
        s.get("numeroComprobante"),
        s.get("codigoReparto"),
        s.get("codigoChofer"),
        s.get("importeNeto"),
        s.get("importeExento"),
        s.get("importeConc"),
        s.get("importeIva"),
        s.get("importeTributos"),
        s.get("importeTotal"),
        jdump(s.get("tags") or []),
        jdump(s.get("propiedades") or {}),
        jdump(s.get("combos") or []),
        jdump(s.get("ventaReferenciada"))
        if s.get("ventaReferenciada") is not None
        else None,
        jdump(s.get("comprobantePrincipal"))
        if s.get("comprobantePrincipal") is not None
        else None,
        raw,
        jhash(s),
        now,
        now,
        0,
        None,
    ]
    upd = ",".join(f"{x}=excluded.{x}" for x in cols[1:])
    c.execute(
        f"INSERT INTO raw_ventas({','.join(cols)}) VALUES({','.join('?' for _ in vals)}) ON CONFLICT(venta_id) DO UPDATE SET {upd}",
        vals,
    )
    for t in [
        "raw_venta_item_descuentos",
        "raw_venta_items",
        "raw_venta_combos",
        "raw_venta_referenciada",
        "raw_comprobante_principal",
    ]:
        c.execute(f"DELETE FROM {t} WHERE venta_id=?", (sid,))
    ref = s.get("ventaReferenciada")
    if ref:
        c.execute(
            "INSERT INTO raw_venta_referenciada VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                sid,
                ref.get("id"),
                ref.get("numeroComprobante"),
                ref.get("origen"),
                ref.get("identificador"),
                ref.get("codigoEmpresa"),
                ref.get("codigoPuntoVenta"),
                ref.get("codigoTipoComprobante"),
                jdump(ref),
                jhash(ref),
                now,
            ),
        )
    cp = s.get("comprobantePrincipal")
    if cp:
        c.execute(
            "INSERT INTO raw_comprobante_principal VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sid,
                cp.get("numeroComprobante"),
                cp.get("codigoTipoComprobante"),
                cp.get("letraComprobante"),
                cp.get("codigoEmpresa"),
                cp.get("codigoPuntoVenta"),
                cp.get("fechaComprobante"),
                cp.get("codigoTipoFacturacion"),
                cp.get("importeNeto"),
                cp.get("importeExento"),
                cp.get("importeConc") or cp.get("importeTotalConc"),
                cp.get("importeIva"),
                cp.get("importeTributos"),
                cp.get("importeTotal"),
                cp.get("cae"),
                jdump(cp),
                jhash(cp),
                now,
            ),
        )
    for z, co in enumerate(s.get("combos") or []):
        c.execute(
            "INSERT INTO raw_venta_combos VALUES(?,?,?,?,?,?,?)",
            (
                sid,
                z,
                co.get("codigoCombo"),
                co.get("cantidad"),
                jdump(co),
                jhash(co),
                now,
            ),
        )
    for z, it in enumerate(s.get("items") or []):
        vi = it.get("ventaItemID")
        vi = int(vi) if vi is not None else -(z + 1)
        icols = [
            "venta_id",
            "venta_item_id",
            "orden_item",
            "item_id",
            "codigo_item",
            "codigo_alicuota_iva",
            "codigo_lista_precio",
            "codigo_deposito",
            "codigo_lote",
            "codigo_combo",
            "codigo_combo_comp",
            "cantidad",
            "codigo_unidad",
            "unidad_factor",
            "piezas",
            "precio_unitario",
            "precio_unitario_iva",
            "precio_unitario_total",
            "precio_costo",
            "descuento",
            "descuento_neto",
            "descuento_final",
            "numero_serie",
            "estado_pesaje",
            "importe_neto",
            "importe_exento",
            "importe_conc",
            "importe_iva",
            "importe_tributos",
            "importe_total",
            "comentario",
            "descuentos_json",
            "propiedades_json",
            "json_raw",
            "hash_raw",
            "capturado_utc",
            "actualizado_utc",
        ]
        iv = [
            sid,
            vi,
            it.get("orden"),
            it.get("itemID"),
            it.get("codigoItem"),
            it.get("codigoAlicuotaIva"),
            it.get("codigoListaPrecio"),
            it.get("codigoDeposito"),
            it.get("codigoLote"),
            it.get("codigoCombo"),
            it.get("codigoComboComp"),
            it.get("cantidad"),
            it.get("codigoUnidad"),
            it.get("unidadFactor"),
            it.get("piezas"),
            it.get("precioUnitario"),
            it.get("precioUnitarioIva"),
            it.get("precioUnitarioTotal"),
            it.get("precioCosto"),
            it.get("descuento"),
            it.get("descuentoNeto"),
            it.get("descuentoFinal"),
            it.get("numeroSerie"),
            it.get("estadoPesaje"),
            it.get("importeNeto"),
            it.get("importeExento"),
            it.get("importeConc"),
            it.get("importeIva"),
            it.get("importeTributos"),
            it.get("importeTotal"),
            it.get("comentario"),
            jdump(it.get("descuentos") or []),
            jdump(it.get("propiedades") or {}),
            jdump(it),
            jhash(it),
            now,
            now,
        ]
        c.execute(
            f"INSERT INTO raw_venta_items({','.join(icols)}) VALUES({','.join('?' for _ in iv)})",
            iv,
        )
        for dno, d in enumerate(it.get("descuentos") or []):
            c.execute(
                "INSERT INTO raw_venta_item_descuentos VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    sid,
                    vi,
                    dno,
                    d.get("descuentoFuenteId"),
                    d.get("descuento"),
                    d.get("descuentoDetalle"),
                    b(d.get("otorgadoPorPromocion")),
                    d.get("promocionId"),
                    d.get("comboComponenteId"),
                    jdump(d.get("propiedades") or {}),
                    jdump(d),
                    jhash(d),
                    now,
                ),
            )


def sync_clients(cli, c, rid):
    rows = fetch(cli, c, rid, "ventas", "/data/cmd/ventas/api/v1/get-clientes")
    now = utc_now()
    c.execute("DELETE FROM raw_cliente_rutas")
    c.execute("DELETE FROM raw_clientes")
    for r in rows:
        co = r.get("coordenadas") or {}
        mv = r.get("minimoDeVenta") or {}
        code = str(r["codigo"])
        cols = [
            "codigo",
            "nombre",
            "razon_social",
            "direccion_entrega",
            "telefono",
            "codigo_empresa",
            "codigo_lista_precio",
            "codigo_ramo",
            "codigo_subramo",
            "codigo_sede",
            "codigo_deposito",
            "codigo_segmento",
            "localidad",
            "codigo_tipo_documento",
            "codigo_condicion_iva",
            "descuento_global",
            "email",
            "provincia",
            "codigo_condicion_pago",
            "codigo_postal",
            "nro_documento",
            "contacto",
            "es_foco",
            "percepcion_ib",
            "margen_maximo",
            "tope_venta",
            "orden_visita",
            "latitud",
            "longitud",
            "minimo_venta_importe",
            "minimo_venta_moneda",
            "demora_entrega_dias",
            "comentario",
            "notas",
            "tope_saldo_dinero",
            "tope_saldo_dinero_moneda",
            "tope_saldo_dinero_factor",
            "tope_saldo_dias",
            "tope_saldo_boletas",
            "tags_json",
            "listas_especiales_json",
            "propiedades_json",
            "rutas_preventa_json",
            "json_raw",
            "hash_raw",
            "capturado_utc",
            "actualizado_utc",
        ]
        vals = [
            code,
            r.get("nombre"),
            r.get("razonSocial"),
            r.get("direccionEntrega"),
            r.get("telefono"),
            r.get("codigoEmpresa"),
            r.get("codigoListaPrecio"),
            r.get("codigoRamo"),
            r.get("codigoSubramo"),
            r.get("codigoSede"),
            r.get("codigoDeposito"),
            r.get("codigoSegmento"),
            r.get("localidad"),
            r.get("codigoTipoDocumento"),
            r.get("codigoCondicionIva"),
            r.get("descuentoGlobal"),
            r.get("email"),
            r.get("provincia"),
            r.get("codigoCondicionPago"),
            r.get("codigoPostal"),
            r.get("nroDocumento"),
            r.get("contacto"),
            b(r.get("esFoco")),
            r.get("percepcionIB"),
            r.get("margenMaximo"),
            r.get("topeVenta"),
            r.get("ordenVisita"),
            co.get("latitud"),
            co.get("longitud"),
            mv.get("importe"),
            mv.get("codigoMoneda"),
            r.get("demoraEntregaDias"),
            r.get("comentario"),
            r.get("notas"),
            r.get("topeSaldoDinero"),
            r.get("topeSaldoDineroMoneda"),
            r.get("topeSaldoDineroFactor"),
            r.get("topeSaldoDias"),
            r.get("topeSaldoBoletas"),
            jdump(r.get("tags") or []),
            jdump(r.get("listasEspeciales") or []),
            jdump(r.get("propiedades") or {}),
            jdump(r.get("rutasPreventa") or []),
            jdump(r),
            jhash(r),
            now,
            now,
        ]
        c.execute(
            f"INSERT INTO raw_clientes({','.join(cols)}) VALUES({','.join('?' for _ in vals)})",
            vals,
        )
        for z, x in enumerate(r.get("rutasPreventa") or []):
            c.execute(
                "INSERT INTO raw_cliente_rutas VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    code,
                    z,
                    x.get("codigoRuta"),
                    x.get("codigoVendedor"),
                    b(x.get("lunes")),
                    b(x.get("martes")),
                    b(x.get("miercoles")),
                    b(x.get("jueves")),
                    b(x.get("viernes")),
                    b(x.get("sabado")),
                    b(x.get("domingo")),
                    str(x.get("frecuencia"))
                    if x.get("frecuencia") is not None
                    else None,
                    x.get("orden"),
                    x.get("fechaPrimeraVisita"),
                    jdump(x.get("gruposFuerzaVenta") or []),
                    jdump(x),
                    jhash(x),
                    now,
                ),
            )
    c.commit()
    return len(rows)


def sync_articles(cli, c, rid):
    allrows = []
    p = 0
    while True:
        params = {"pagesize": PAGE_ARTICLES, "pagestoskip": p, "pagestotake": 1}
        rows = fetch(
            cli,
            c,
            rid,
            "inventario",
            "/data/cmd/inventario/api/v4/get-articulos",
            params,
        )
        allrows.extend(rows)
        if len(rows) < PAGE_ARTICLES:
            break
        p += 1
    now = utc_now()
    c.execute("DELETE FROM raw_articulo_unidades")
    c.execute("DELETE FROM raw_articulos")
    for r in allrows:
        code = str(r["codigo"])
        cols = [
            "codigo",
            "descripcion",
            "codigo_rubro",
            "precio_costo",
            "impuesto_interno",
            "codigo_alicuota_iva",
            "codigo_linea",
            "codigo_marca",
            "codigo_familia",
            "codigo_segmento_margen",
            "unidad_venta",
            "unidades_bulto_venta",
            "unidad_venta_base",
            "unidades_minima_venta",
            "descuento_maximo",
            "factor_peso",
            "factor_volumen",
            "codigo_barras",
            "codigo_proveedor",
            "codigo_empresa",
            "apto_comodato",
            "bloqueado",
            "bloqueado_motivo",
            "combo_iteractivo",
            "incontable",
            "unidades_por_bulto",
            "motivo_bloqueo",
            "ponderado_pieza",
            "preparacion_consolidada",
            "track_piezas_en_stock",
            "tags_json",
            "unidades_permitidas_json",
            "json_raw",
            "hash_raw",
            "capturado_utc",
            "actualizado_utc",
        ]
        vals = [
            code,
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
            r.get("descuentoMaximo"),
            r.get("factorPeso"),
            r.get("factorVolumen"),
            r.get("codigoBarras"),
            r.get("codigoProveedor"),
            r.get("codigoEmpresa"),
            b(r.get("aptoComodato")),
            b(r.get("bloqueado")),
            r.get("bloqueadoMotivo"),
            b(r.get("comboIteractivo")),
            b(r.get("incontable")),
            r.get("unidadesPorBulto"),
            r.get("motivoBloqueo"),
            r.get("ponderadoPieza"),
            str(r.get("preparacionConsolidada"))
            if r.get("preparacionConsolidada") is not None
            else None,
            b(r.get("trackPiezasEnStock")),
            jdump(r.get("tags") or []),
            jdump(r.get("unidadesPermitidas") or []),
            jdump(r),
            jhash(r),
            now,
            now,
        ]
        c.execute(
            f"INSERT INTO raw_articulos({','.join(cols)}) VALUES({','.join('?' for _ in vals)})",
            vals,
        )
        for z, u in enumerate(r.get("unidadesPermitidas") or []):
            ena = u.get("enable") or {}
            de = u.get("default") or []
            if isinstance(de, dict):
                defaults = de
            else:
                defaults = {x: True for x in de}
            c.execute(
                "INSERT INTO raw_articulo_unidades VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    code,
                    z,
                    u.get("codigoUnidad"),
                    u.get("factor"),
                    b(ena.get("venta") if isinstance(ena, dict) else None),
                    b(ena.get("compra") if isinstance(ena, dict) else None),
                    b(ena.get("carga") if isinstance(ena, dict) else None),
                    u.get("minimoVenta"),
                    u.get("multiploVenta"),
                    b(defaults.get("venta")),
                    b(defaults.get("compra")),
                    b(defaults.get("carga")),
                    u.get("codigoBarras"),
                    jdump(u),
                    jhash(u),
                    now,
                ),
            )
    c.commit()
    return len(allrows)


def sync_provider(cli, c, rid):
    rows = fetch(cli, c, rid, "compras", "/data/cmd/compras/api/v1/get-proveedores")
    now = utc_now()
    c.execute("DELETE FROM raw_proveedores")
    for r in rows:
        vals = [
            str(r["codigo"]),
            r.get("nombre"),
            r.get("direccion"),
            r.get("telefono"),
            r.get("localidad"),
            r.get("codigoTipoDocumento"),
            r.get("codigoCondicionIva"),
            r.get("email"),
            r.get("provincia"),
            r.get("codigoCondicionPago"),
            r.get("codigoPostal"),
            r.get("nroDocumento"),
            r.get("contacto"),
            jdump(r.get("tags") or []),
            r.get("comentario"),
            r.get("notas"),
            jdump(r),
            jhash(r),
            now,
            now,
        ]
        c.execute(
            "INSERT INTO raw_proveedores VALUES(" + ",".join("?" for _ in vals) + ")",
            vals,
        )
    c.commit()
    return len(rows)


def sync_pepsico(cli, c, rid):
    specs = [
        (
            "raw_pepsico_exhibidores",
            "/data/cmd/ventas/api/v1/pepsico/get-cliente-exhibidor",
        ),
        (
            "raw_pepsico_infaltables",
            "/data/cmd/ventas/api/v1/pepsico/get-productos-infaltables",
        ),
        (
            "raw_pepsico_tienda_perfecta",
            "/data/cmd/ventas/api/v1/pepsico/get-resultado-tienda-perfecta",
        ),
    ]
    out = {}
    for table, path in specs:
        rows = fetch(cli, c, rid, "ventas", path)
        c.execute(f"DELETE FROM {table}")
        now = utc_now()
        n = 0
        if table.endswith("exhibidores"):
            for g in rows:
                for x in g.get("exhibidores") or []:
                    rr = {"codigoCliente": g.get("codigoCliente"), **x}
                    c.execute(
                        f"INSERT INTO {table}(codigo_cliente,codigo_item,cantidad_disponible,es_foto_exito,json_raw,hash_raw,snapshot_utc) VALUES(?,?,?,?,?,?,?)",
                        (
                            g.get("codigoCliente"),
                            x.get("codigoItem"),
                            x.get("cantidadDisponible"),
                            b(x.get("esFotoExito")),
                            jdump(rr),
                            jhash(rr),
                            now,
                        ),
                    )
                    n += 1
        elif table.endswith("infaltables"):
            for g in rows:
                for item in g.get("productos") or []:
                    rr = {"codigoCliente": g.get("codigoCliente"), "codigoItem": item}
                    c.execute(
                        f"INSERT INTO {table}(codigo_cliente,codigo_item,json_raw,hash_raw,snapshot_utc) VALUES(?,?,?,?,?)",
                        (g.get("codigoCliente"), item, jdump(rr), jhash(rr), now),
                    )
                    n += 1
        else:
            for r in rows:
                c.execute(
                    f"INSERT INTO {table}(codigo_cliente,ramo,subramo,perfect_store_type,perfect_store_comment,perfect_store_state,perfect_store_portafolio_porc,json_raw,hash_raw,snapshot_utc) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        r.get("codigoCliente"),
                        r.get("ramo"),
                        r.get("subRamo"),
                        r.get("perfectStoreType"),
                        r.get("perfectStoreComment"),
                        r.get("perfectStoreState"),
                        r.get("perfectStorePortafolioPorc"),
                        jdump(r),
                        jhash(r),
                        now,
                    ),
                )
                n += 1
        c.commit()
        out[table] = n
    return out


def sync_catalogs(cli, c, rid):
    simple = [
        (
            "raw_marcas",
            "inventario",
            "/data/cmd/inventario/api/v1/get-marcas",
            "codigo",
            "descripcion",
        ),
        (
            "raw_familias",
            "inventario",
            "/data/cmd/inventario/api/v1/get-familias",
            "codigo",
            "descripcion",
        ),
        (
            "raw_lineas",
            "inventario",
            "/data/cmd/inventario/api/v1/get-lineas",
            "codigo",
            "descripcion",
        ),
        (
            "raw_rubros",
            "inventario",
            "/data/cmd/inventario/api/v1/get-rubros",
            "codigo",
            "descripcion",
        ),
        (
            "raw_segmentos_margen",
            "inventario",
            "/data/cmd/inventario/api/v1/get-segmento-margen",
            "codigo",
            "descripcion",
        ),
        (
            "raw_unidades",
            "inventario",
            "/data/cmd/inventario/api/v1/get-unidades",
            "codigo",
            "descripcion",
        ),
        (
            "raw_vendedores",
            "ventas",
            "/data/cmd/ventas/api/v1/get-vendedores",
            "codigo",
            "nombre",
        ),
        (
            "raw_tipos_empleado",
            "ventas",
            "/data/cmd/ventas/api/v1/get-tipos-empleado",
            "codigo",
            "descripcion",
        ),
        (
            "raw_subramos",
            "ventas",
            "/data/cmd/ventas/api/v1/get-subramos",
            "codigo",
            "descripcion",
        ),
        (
            "raw_tipos_facturacion",
            "ventas",
            "/data/cmd/ventas/api/v1/get-tipos-facturacion",
            "codigo",
            "descripcion",
        ),
        (
            "raw_provincias",
            "config",
            "/data/cmd/config/api/v1/get-provincias",
            "codigo",
            "descripcion",
        ),
    ]
    out = {}
    for table, module, path, key, desc in simple:
        rows = fetch(cli, c, rid, module, path)
        out[table] = simple_catalog(c, table, rows, key, desc)
        c.commit()
    return out


def sync_special_catalogs(cli, c, rid):
    now = utc_now()
    out = {}
    # empresas
    rows = fetch(cli, c, rid, "config", "/data/cmd/config/api/v1/get-empresas")
    c.execute("DELETE FROM raw_empresas")
    for r in rows:
        c.execute(
            "INSERT INTO raw_empresas VALUES(?,?,?,?,?,?,?,?,?)",
            (
                str(r["codigo"]),
                r.get("nombre"),
                r.get("razonSocial"),
                r.get("documento"),
                r.get("direccion"),
                jdump(r),
                jhash(r),
                now,
                now,
            ),
        )
    out["raw_empresas"] = len(rows)
    # empleados
    rows = fetch(cli, c, rid, "ventas", "/data/cmd/ventas/api/v1/get-empleados")
    c.execute("DELETE FROM raw_empleados")
    for r in rows:
        c.execute(
            "INSERT INTO raw_empleados VALUES(?,?,?,?,?,?,?,?)",
            (
                str(r["codigo"]),
                r.get("nombre"),
                r.get("codigoSuperior"),
                jdump(r.get("tipos") or []),
                jdump(r),
                jhash(r),
                now,
                now,
            ),
        )
    out["raw_empleados"] = len(rows)
    # specs custom
    endpoints = [
        ("raw_condiciones_pago", "/data/cmd/ventas/api/v1/get-condiciones-pago"),
        ("raw_listas_precio", "/data/cmd/ventas/api/v1/get-listas-precio"),
        ("raw_rutas_preventa", "/data/cmd/ventas/api/v1/get-rutas-preventa"),
        ("raw_grupos_fuerza_venta", "/data/cmd/ventas/api/v1/get-grupos-fuerza-venta"),
        ("raw_etapas_venta", "/data/cmd/ventas/api/v1/get-etapas"),
        ("raw_motivos_venta", "/data/cmd/ventas/api/v1/get-motivos-venta"),
        ("raw_tipos_comprobante", "/data/cmd/ventas/api/v1/get-tipos-comprobante"),
        ("raw_alicuotas_iva", "/data/cmd/config/api/v1/get-alicuotas-iva"),
        ("raw_tags", "/data/cmd/config/api/v1/get-tags"),
        ("raw_categorias_tag", "/data/cmd/config/api/v1/get-categorias-tag"),
    ]
    for table, path in endpoints:
        params = {"includeTags": "true"} if table == "raw_categorias_tag" else None
        rows = fetch(
            cli, c, rid, "ventas" if "/ventas/" in path else "config", path, params
        )
        c.execute(f"DELETE FROM {table}")
        for r in rows:
            common = (jdump(r), jhash(r), now, now)
            if table == "raw_condiciones_pago":
                vals = (
                    str(r["codigo"]),
                    r.get("descripcion"),
                    r.get("dias"),
                    r.get("cuotas"),
                    *common,
                )
            elif table == "raw_listas_precio":
                vals = (
                    str(r["codigo"]),
                    r.get("descripcion"),
                    b(r.get("esGeneral")),
                    *common,
                )
            elif table == "raw_rutas_preventa":
                vals = (
                    str(r["codigo"]),
                    r.get("descripcion"),
                    r.get("codigoVendedor"),
                    b(r.get("lunes")),
                    b(r.get("martes")),
                    b(r.get("miercoles")),
                    b(r.get("jueves")),
                    b(r.get("viernes")),
                    b(r.get("sabado")),
                    b(r.get("domingo")),
                    str(r.get("frecuencia"))
                    if r.get("frecuencia") is not None
                    else None,
                    *common,
                )
            elif table == "raw_grupos_fuerza_venta":
                vals = (
                    str(r["codigo"]),
                    r.get("descripcion"),
                    jdump(r.get("tags") or []),
                    *common,
                )
            elif table == "raw_etapas_venta":
                vals = (r.get("etapa"), r.get("orden"), *common)
            elif table == "raw_motivos_venta":
                vals = (
                    r.get("id"),
                    r.get("codigo"),
                    r.get("descripcion"),
                    r.get("codigoTipoVenta"),
                    *common,
                )
            elif table == "raw_tipos_comprobante":
                vals = (
                    str(r["codigo"]),
                    r.get("descripcion"),
                    r.get("codigoClase"),
                    r.get("descripcionClase"),
                    *common,
                )
            elif table == "raw_alicuotas_iva":
                vals = (
                    str(r["codigo"]),
                    r.get("descripcion"),
                    b(r.get("noGravado")),
                    r.get("porcentaje"),
                    *common,
                )
            elif table == "raw_tags":
                vals = (
                    r.get("id"),
                    r.get("categoria"),
                    r.get("nombre"),
                    r.get("descripcion"),
                    r.get("colorLetra"),
                    r.get("colorFondo"),
                    *common,
                )
            else:
                vals = (
                    r.get("id"),
                    r.get("nombre"),
                    r.get("descripcion"),
                    r.get("colorLetra"),
                    r.get("colorFondo"),
                    jdump(r.get("tags") or []),
                    *common,
                )
            c.execute(
                f"INSERT INTO {table} VALUES({','.join('?' for _ in vals)})", vals
            )
        out[table] = len(rows)
    # ramos relation
    rows = fetch(cli, c, rid, "ventas", "/data/cmd/ventas/api/v1/get-ramos")
    c.execute("DELETE FROM raw_ramo_subramos")
    c.execute("DELETE FROM raw_ramos")
    for r in rows:
        c.execute(
            "INSERT INTO raw_ramos VALUES(?,?,?,?,?,?,?)",
            (
                str(r["codigo"]),
                r.get("descripcion"),
                jdump(r.get("subRamos") or []),
                jdump(r),
                jhash(r),
                now,
                now,
            ),
        )
        for sr in r.get("subRamos") or []:
            if sr.get("codigo") is not None:
                c.execute(
                    "INSERT INTO raw_ramo_subramos VALUES(?,?,?,?,?,?)",
                    (
                        str(r["codigo"]),
                        str(sr["codigo"]),
                        sr.get("descripcion"),
                        jdump(sr),
                        jhash(sr),
                        now,
                    ),
                )
    out["raw_ramos"] = len(rows)
    c.commit()
    return out


def sync_distribution(cli, c, rid, fd, fh):
    # Ordenes: paginacion especial, pagina desde 1.
    out = {}
    allorders = []
    page = 1
    while True:
        params = {
            "fechadesde": fd,
            "fechahasta": fh,
            "pagesize": 500,
            "pagestotake": page,
        }
        obj = fetch(
            cli,
            c,
            rid,
            "distribucion",
            "/data/cmd/distribucion/api/v1/get-ordenespreparacion",
            params,
        )
        rows = obj.get("ordenesPreparacion", []) if isinstance(obj, dict) else []
        allorders.extend(rows)
        totalp = int(obj.get("totalPaginas", 1)) if isinstance(obj, dict) else 1
        if page >= totalp:
            break
        page += 1
    now = utc_now()
    c.execute("DELETE FROM raw_ordenes_preparacion_ventas")
    c.execute("DELETE FROM raw_ordenes_preparacion")
    for r in allorders:
        c.execute(
            "INSERT INTO raw_ordenes_preparacion VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                r.get("id"),
                r.get("estado"),
                r.get("fechaCarga"),
                r.get("fechaCreacion"),
                r.get("fechaArmado"),
                r.get("bodeguista"),
                r.get("nombreBodeguista"),
                jdump(r),
                jhash(r),
                now,
                now,
            ),
        )
        for v in r.get("ventas") or []:
            c.execute(
                "INSERT INTO raw_ordenes_preparacion_ventas VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    r.get("id"),
                    v.get("ventaID"),
                    v.get("empresa"),
                    v.get("puntoVenta"),
                    v.get("tipoVenta"),
                    v.get("numeroComprobante"),
                    v.get("comprobante"),
                    v.get("estadoVenta"),
                    jdump(v),
                    jhash(v),
                    now,
                ),
            )
    c.commit()
    out["raw_ordenes_preparacion"] = len(allorders)
    return out


def diagnostic(c):
    print(f"DB: {DB_PATH.resolve()}")
    for r in c.execute("SELECT entidad,filas FROM audit_raw_conteos ORDER BY entidad"):
        print(f"{r[0]}: {r[1]}")
    print("INTEGRIDAD")
    for r in c.execute("SELECT control,resultado FROM audit_raw_integridad"):
        print(f"{r[0]}: {r[1]}")
    print("JSON_INVALIDO")
    for r in c.execute("SELECT entidad,resultado FROM audit_raw_json_invalido"):
        print(f"{r[0]}: {r[1]}")
    print("Escrituras productivas: NINGUNA")


def main():
    ap = argparse.ArgumentParser(description="GESCOM RAW Sync v2.2")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--diagnostico", action="store_true")
    ap.add_argument("--fecha-desde")
    ap.add_argument("--fecha-hasta")
    ap.add_argument("--sin-distribucion", action="store_true")
    a = ap.parse_args()
    if not any([a.init, a.sync, a.diagnostico]):
        ap.error("Indica --init, --sync o --diagnostico")
    c = connect()
    init_db(c)
    try:
        if a.init:
            print(
                f"Base RAW v2.2 inicializada: {DB_PATH.resolve()}\nEscrituras productivas: NINGUNA"
            )
        if a.sync:
            if not a.fecha_desde or not a.fecha_hasta:
                ap.error("--sync requiere --fecha-desde y --fecha-hasta")
            rid = run_begin(c, "sync_raw_v2_2", "BOOTSTRAP", vars(a))
            cli = Client()
            result = {}
            try:
                result["ventas"] = sync_sales(cli, c, rid, a.fecha_desde, a.fecha_hasta)
                result["clientes"] = sync_clients(cli, c, rid)
                result["articulos"] = sync_articles(cli, c, rid)
                result["proveedores"] = sync_provider(cli, c, rid)
                result.update(sync_catalogs(cli, c, rid))
                result.update(sync_special_catalogs(cli, c, rid))
                result.update(sync_pepsico(cli, c, rid))
                if not a.sin_distribucion:
                    result.update(
                        sync_distribution(cli, c, rid, a.fecha_desde, a.fecha_hasta)
                    )
                total = sum(
                    sum(x) if isinstance(x, tuple) else x for x in result.values()
                )
                run_end(c, rid, "OK", jdump(result), total)
                print(
                    "Sincronizacion RAW v2.2 finalizada.\n"
                    + jdump(result)
                    + "\nEscrituras productivas: NINGUNA"
                )
            except Exception as e:
                run_end(c, rid, "ERROR", "Fallo", 0, repr(e))
                raise
        if a.diagnostico:
            diagnostic(c)
    finally:
        c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
