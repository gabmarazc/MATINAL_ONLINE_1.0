#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AU RAW V2.2 - auditoria estrictamente READ ONLY.

Objetivo: auditar fidelidad e integridad del bootstrap RAW GESCOM.
SQLite: mode=ro&immutable=1. No crea/repara/modifica datos.
Escrituras productivas: NINGUNA.
"""

from __future__ import annotations
import json, sqlite3, sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote

DB = Path("data") / "matinal_api_test.db"
EXPECTED_ENDPOINTS = [
    "/data/cmd/ventas/api/v2/get",
    "/data/cmd/ventas/api/v1/get-clientes",
    "/data/cmd/inventario/api/v4/get-articulos",
    "/data/cmd/compras/api/v1/get-proveedores",
    "/data/cmd/inventario/api/v1/get-marcas",
    "/data/cmd/inventario/api/v1/get-familias",
    "/data/cmd/inventario/api/v1/get-lineas",
    "/data/cmd/inventario/api/v1/get-rubros",
    "/data/cmd/inventario/api/v1/get-segmento-margen",
    "/data/cmd/inventario/api/v1/get-unidades",
    "/data/cmd/ventas/api/v1/get-empleados",
    "/data/cmd/ventas/api/v1/get-vendedores",
    "/data/cmd/ventas/api/v1/get-tipos-empleado",
    "/data/cmd/ventas/api/v1/get-rutas-preventa",
    "/data/cmd/ventas/api/v1/get-condiciones-pago",
    "/data/cmd/ventas/api/v1/get-listas-precio",
    "/data/cmd/ventas/api/v1/get-ramos",
    "/data/cmd/ventas/api/v1/get-subramos",
    "/data/cmd/ventas/api/v1/get-grupos-fuerza-venta",
    "/data/cmd/ventas/api/v1/get-etapas",
    "/data/cmd/ventas/api/v1/get-motivos-venta",
    "/data/cmd/ventas/api/v1/get-tipos-comprobante",
    "/data/cmd/ventas/api/v1/get-tipos-facturacion",
    "/data/cmd/config/api/v1/get-empresas",
    "/data/cmd/config/api/v1/get-alicuotas-iva",
    "/data/cmd/config/api/v1/get-tags",
    "/data/cmd/config/api/v1/get-categorias-tag",
    "/data/cmd/config/api/v1/get-provincias",
    "/data/cmd/ventas/api/v1/pepsico/get-cliente-exhibidor",
    "/data/cmd/ventas/api/v1/pepsico/get-productos-infaltables",
    "/data/cmd/ventas/api/v1/pepsico/get-resultado-tienda-perfecta",
    "/data/cmd/distribucion/api/v1/get-ordenespreparacion",
]

# Campos normalizados deliberadamente por V2.2. json_raw cubre el resto.
MAPPED = {
    "raw_ventas": {
        "id": "venta_id",
        "identificador": "identificador",
        "origen": "origen",
        "estado": "estado",
        "etapa": "etapa",
        "etapaNota": "etapa_nota",
        "requiereAutorizacion": "requiere_autorizacion",
        "cerrada": "cerrada",
        "codigoTipoVenta": "codigo_tipo_venta",
        "esCredito": "es_credito",
        "esSinCargo": "es_sin_cargo",
        "codigoCliente": "codigo_cliente",
        "codigoVendedor": "codigo_vendedor",
        "codigoRuta": "codigo_ruta",
        "codigoEmpresa": "codigo_empresa",
        "codigoPuntoVenta": "codigo_punto_venta",
        "codigoSede": "codigo_sede",
        "codigoCondicionPago": "codigo_condicion_pago",
        "codigoMotivoCambio": "codigo_motivo_cambio",
        "motivo": "motivo",
        "fechaPedido": "fecha_pedido",
        "fechaEntrega": "fecha_entrega",
        "observaciones": "observaciones",
        "observacionesInternas": "observaciones_internas",
        "descuentoGlobal": "descuento_global",
        "ventaDirecta": "venta_directa",
        "metodoEntrega": "metodo_entrega",
        "loteId": "lote_id",
        "numeroComprobante": "numero_comprobante",
        "codigoReparto": "codigo_reparto",
        "codigoChofer": "codigo_chofer",
        "importeNeto": "importe_neto",
        "importeExento": "importe_exento",
        "importeConc": "importe_conc",
        "importeIva": "importe_iva",
        "importeTributos": "importe_tributos",
        "importeTotal": "importe_total",
        "tags": "tags_json",
        "propiedades": "propiedades_json",
        "combos": "combos_json",
        "ventaReferenciada": "venta_referenciada_json",
        "comprobantePrincipal": "comprobante_principal_json",
    },
    "raw_venta_items": {
        "orden": "orden_item",
        "ventaItemID": "venta_item_id",
        "itemID": "item_id",
        "codigoItem": "codigo_item",
        "codigoAlicuotaIva": "codigo_alicuota_iva",
        "codigoListaPrecio": "codigo_lista_precio",
        "codigoDeposito": "codigo_deposito",
        "codigoLote": "codigo_lote",
        "codigoCombo": "codigo_combo",
        "codigoComboComp": "codigo_combo_comp",
        "cantidad": "cantidad",
        "codigoUnidad": "codigo_unidad",
        "unidadFactor": "unidad_factor",
        "piezas": "piezas",
        "precioUnitario": "precio_unitario",
        "precioUnitarioIva": "precio_unitario_iva",
        "precioUnitarioTotal": "precio_unitario_total",
        "precioCosto": "precio_costo",
        "descuento": "descuento",
        "descuentoNeto": "descuento_neto",
        "descuentoFinal": "descuento_final",
        "numeroSerie": "numero_serie",
        "estadoPesaje": "estado_pesaje",
        "importeNeto": "importe_neto",
        "importeExento": "importe_exento",
        "importeConc": "importe_conc",
        "importeIva": "importe_iva",
        "importeTributos": "importe_tributos",
        "importeTotal": "importe_total",
        "comentario": "comentario",
        "descuentos": "descuentos_json",
        "propiedades": "propiedades_json",
    },
}


def scalar(c, q, p=()):
    return c.execute(q, p).fetchone()[0]


def cols(c, t):
    return {r[1] for r in c.execute(f"PRAGMA table_info({t})")}


def json_keys(c, t):
    z = Counter()
    bad = 0
    for (raw,) in c.execute(f"SELECT json_raw FROM {t}"):
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                z.update(obj.keys())
        except Exception:
            bad += 1
    return z, bad


def main():
    print("=" * 78)
    print("AU RAW V2.2 - READ ONLY")
    print(f"Base: {DB.resolve()}")
    print("SQLite: mode=ro&immutable=1")
    print("Escrituras productivas: NINGUNA")
    print("=" * 78)
    if not DB.is_file():
        print("FAIL Base inexistente")
        return 2
    uri = f"file:{quote(str(DB.resolve()))}?mode=ro&immutable=1"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    fail = []
    warn = []
    try:
        c = con.cursor()
        print("\n[1] INTEGRIDAD SQLITE")
        ic = scalar(c, "PRAGMA integrity_check")
        print("integrity_check:", ic)
        if ic != "ok":
            fail.append("integrity_check")
        rawtables = [
            r[0]
            for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'raw_%' ORDER BY name"
            )
        ]
        print("tablas RAW:", len(rawtables))

        print("\n[2] ENDPOINTS EFECTIVAMENTE CAPTURADOS")
        got = {
            r[0]: r[1]
            for r in c.execute(
                "SELECT endpoint,COUNT(*) FROM raw_api_payloads GROUP BY endpoint"
            )
        }
        for e in EXPECTED_ENDPOINTS:
            ok = e in got
            print(("OK  " if ok else "MISS"), e, "payloads=", got.get(e, 0))
            if not ok:
                warn.append("endpoint no capturado: " + e)
        extras = sorted(set(got) - set(EXPECTED_ENDPOINTS))
        for e in extras:
            print("EXTRA", e, "payloads=", got[e])

        print("\n[3] CONTEOS RAW")
        for r in c.execute(
            "SELECT entidad,filas FROM audit_raw_conteos ORDER BY entidad"
        ):
            print(f"{r[0]}: {r[1]}")

        print("\n[4] INTEGRIDAD RELACIONAL")
        for r in c.execute("SELECT control,resultado FROM audit_raw_integridad"):
            print(f"{r[0]}: {r[1]}")
            if r[1]:
                fail.append(f"{r[0]}={r[1]}")

        print("\n[5] JSON INVALIDO")
        for r in c.execute("SELECT entidad,resultado FROM audit_raw_json_invalido"):
            print(f"{r[0]}: {r[1]}")
            if r[1]:
                fail.append(f"json invalido {r[0]}={r[1]}")

        print("\n[6] FIDELIDAD VENTAS: CAMPOS OBSERVADOS VS NORMALIZADOS")
        vk, bad = json_keys(c, "raw_ventas")
        normalized = cols(c, "raw_ventas")
        mapping = MAPPED["raw_ventas"]
        for k, n in sorted(vk.items()):
            dest = mapping.get(k)
            ok = (dest in normalized) if dest else False
            preserved = ok or "json_raw" in normalized
            print(
                f"{k:28} observaciones={n:4} normalizado={dest or 'NO':28} preservado={'SI' if preserved else 'NO'}"
            )
            if not preserved:
                fail.append("venta campo perdido " + k)
        if bad:
            fail.append(f"ventas json no parseable={bad}")

        print("\n[7] FIDELIDAD ITEMS: CAMPOS OBSERVADOS VS NORMALIZADOS")
        ik, bad = json_keys(c, "raw_venta_items")
        normalized = cols(c, "raw_venta_items")
        mapping = MAPPED["raw_venta_items"]
        for k, n in sorted(ik.items()):
            dest = mapping.get(k)
            ok = (dest in normalized) if dest else False
            preserved = ok or "json_raw" in normalized
            print(
                f"{k:28} observaciones={n:4} normalizado={dest or 'NO':28} preservado={'SI' if preserved else 'NO'}"
            )
            if not preserved:
                fail.append("item campo perdido " + k)
        if bad:
            fail.append(f"items json no parseable={bad}")

        print("\n[8] ARRAYS/OBJETOS DE VENTAS")
        sqls = {
            "items_raw": "SELECT COUNT(*) FROM raw_venta_items",
            "descuentos_normalizados": "SELECT COUNT(*) FROM raw_venta_item_descuentos",
            "combos_normalizados": "SELECT COUNT(*) FROM raw_venta_combos",
            "ventas_referenciadas": "SELECT COUNT(*) FROM raw_venta_referenciada",
            "comprobantes_principales": "SELECT COUNT(*) FROM raw_comprobante_principal",
        }
        for k, q in sqls.items():
            print(k, scalar(c, q))
        expected_disc = 0
        for (raw,) in c.execute("SELECT json_raw FROM raw_venta_items"):
            x = json.loads(raw)
            expected_disc += len(x.get("descuentos") or [])
        got_disc = scalar(c, "SELECT COUNT(*) FROM raw_venta_item_descuentos")
        print("descuentos JSON vs tabla:", expected_disc, "vs", got_disc)
        if expected_disc != got_disc:
            fail.append("perdida descuentos")

        print("\n[9] CLIENTES/ARTICULOS: COBERTURA DE SUBESTRUCTURAS")
        cr = scalar(c, "SELECT COUNT(*) FROM raw_cliente_rutas")
        au = scalar(c, "SELECT COUNT(*) FROM raw_articulo_unidades")
        print("raw_cliente_rutas:", cr)
        print("raw_articulo_unidades:", au)
        expected_routes = sum(
            len(json.loads(r[0]).get("rutasPreventa") or [])
            for r in c.execute("SELECT json_raw FROM raw_clientes")
        )
        expected_units = sum(
            len(json.loads(r[0]).get("unidadesPermitidas") or [])
            for r in c.execute("SELECT json_raw FROM raw_articulos")
        )
        print("rutas cliente JSON vs tabla:", expected_routes, "vs", cr)
        print("unidades articulo JSON vs tabla:", expected_units, "vs", au)
        if expected_routes != cr:
            fail.append("perdida rutas cliente")
        if expected_units != au:
            fail.append("perdida unidades articulo")

        print("\n[10] PEPSICO")
        for t in [
            "raw_pepsico_exhibidores",
            "raw_pepsico_infaltables",
            "raw_pepsico_tienda_perfecta",
        ]:
            n = scalar(c, f"SELECT COUNT(*) FROM {t}")
            nullc = scalar(c, f"SELECT COUNT(*) FROM {t} WHERE codigo_cliente IS NULL")
            print(f"{t}: {n}; codigo_cliente NULL={nullc}")

        print("\n[11] DISTRIBUCION E INCREMENTALES")
        for t in [
            "raw_ordenes_preparacion",
            "raw_ordenes_preparacion_ventas",
            "raw_repartos",
            "raw_reparto_ventas",
            "raw_ventas_cambios",
            "raw_repartos_cambios",
        ]:
            print(t, scalar(c, f"SELECT COUNT(*) FROM {t}"))
        if scalar(c, "SELECT COUNT(*) FROM raw_repartos") == 0:
            warn.append(
                "raw_repartos sin carga: Repartos v2 aun no consumido o sin datos"
            )
        if scalar(c, "SELECT COUNT(*) FROM raw_ventas_cambios") == 0:
            warn.append("Cambios v3 aun no implementado/capturado")

        print("\n[12] PAYLOADS Y TRAZABILIDAD")
        print("payloads:", scalar(c, "SELECT COUNT(*) FROM raw_api_payloads"))
        print("sync runs:", scalar(c, "SELECT COUNT(*) FROM raw_sync_runs"))
        for r in c.execute(
            "SELECT run_id,proceso,modo,estado,registros_recibidos,error_texto FROM raw_sync_runs ORDER BY run_id DESC LIMIT 5"
        ):
            print(dict(r))

        print("\n[13] DICTAMEN")
        for x in warn:
            print("WARN", x)
        for x in fail:
            print("FAIL", x)
        if fail:
            print("DICTAMEN: NO APROBADA")
            return 1
        if warn:
            print("DICTAMEN: APROBADA CON OBSERVACIONES")
            return 0
        print("DICTAMEN: APROBADA")
        return 0
    finally:
        con.close()
        print("\nEscrituras productivas: NINGUNA")


if __name__ == "__main__":
    raise SystemExit(main())
