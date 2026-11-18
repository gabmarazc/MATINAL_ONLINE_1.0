#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AU FASE 4 - Auditoría incremental estrictamente READ ONLY.
Abre exclusivamente data/matinal_api_test.db con mode=ro&immutable=1.
Escrituras productivas: NINGUNA.
"""

from __future__ import annotations
import json, sqlite3
from pathlib import Path
from urllib.parse import quote

DB = Path("data") / "matinal_api_test.db"


def one(c, q, p=()):
    r = c.execute(q, p).fetchone()
    return None if r is None else r[0]


def rows(c, q, p=()):
    return c.execute(q, p).fetchall()


def section(s):
    print("\n[" + s + "]")


def main():
    print("=" * 78)
    print("AU FASE 4 - INCREMENTAL READ ONLY")
    print(f"Base: {DB.resolve()}")
    print("SQLite: SOLO LECTURA, IMMUTABLE")
    print("Escrituras productivas: NINGUNA")
    print("=" * 78)
    if not DB.exists():
        print("FAIL Base inexistente")
        return 2
    uri = f"file:{quote(str(DB.resolve()))}?mode=ro&immutable=1"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    c = con.cursor()
    fail = []
    warn = []
    try:
        section("1] INTEGRIDAD SQLITE")
        ic = one(c, "PRAGMA integrity_check")
        print("integrity_check:", ic)
        if ic != "ok":
            fail.append("integrity_check")
        section("2] CURSORES")
        curs = {
            r["entidad"]: dict(r)
            for r in rows(
                c,
                "SELECT entidad,endpoint,cursor_tipo,cursor_valor,ultima_sync_ok_utc,estado,detalle FROM raw_sync_state WHERE entidad IN ('ventas','repartos')",
            )
        }
        for e, tipo in [("ventas", "position"), ("repartos", "trxid")]:
            r = curs.get(e)
            print(e, r if r else "SIN CURSOR")
            if not r:
                fail.append(f"{e} sin cursor")
            elif (
                r["cursor_tipo"] != tipo or r["estado"] != "OK" or not r["cursor_valor"]
            ):
                fail.append(f"cursor {e} inválido")
        section("3] CAMBIOS VENTAS")
        vn = one(c, "SELECT COUNT(*) FROM raw_ventas_cambios WHERE tipo='NOVEDAD'")
        ve = one(c, "SELECT COUNT(*) FROM raw_ventas_cambios WHERE tipo='ELIMINADA'")
        vp = one(c, "SELECT COUNT(*) FROM raw_ventas_cambios WHERE procesado=0")
        vt = one(c, "SELECT COUNT(*) FROM raw_ventas_cambios")
        print(f"novedades={vn}; eliminadas={ve}; total={vt}; pendientes={vp}")
        if vn + ve != vt:
            fail.append("conteo cambios ventas inconsistente")
        if vp:
            fail.append(f"cambios ventas pendientes={vp}")
        dup = one(
            c,
            "SELECT COUNT(*) FROM (SELECT last_position,tipo,venta_id,COUNT(*) n FROM raw_ventas_cambios GROUP BY 1,2,3 HAVING n>1)",
        )
        print("duplicados referencias:", dup)
        if dup:
            fail.append("duplicados cambios ventas")
        section("4] BAJAS / TOMBSTONES VENTAS")
        marked = one(c, "SELECT COUNT(*) FROM raw_ventas WHERE eliminado=1")
        tomb = one(
            c,
            "SELECT COUNT(*) FROM raw_ventas WHERE eliminado=1 AND json_extract(json_raw,'$.items') IS NULL",
        )
        active = one(c, "SELECT COUNT(*) FROM raw_ventas WHERE eliminado=0")
        active_items = one(c, "SELECT COUNT(DISTINCT venta_id) FROM raw_venta_items")
        print(
            f"ventas eliminadas marcadas={marked}; tombstones mínimos={tomb}; activas={active}; ventas con items={active_items}"
        )
        if marked < ve:
            fail.append("menos bajas marcadas que referencias eliminadas")
        # Toda novedad procesada debe existir como RAW y no estar eliminada.
        missing_nov = one(
            c,
            "SELECT COUNT(*) FROM raw_ventas_cambios ch LEFT JOIN raw_ventas v ON v.venta_id=ch.venta_id WHERE ch.tipo='NOVEDAD' AND ch.procesado=1 AND (v.venta_id IS NULL OR v.eliminado<>0)",
        )
        print("novedades procesadas sin RAW activo:", missing_nov)
        if missing_nov:
            fail.append("novedades sin RAW activo")
        section("5] CAMBIOS REPARTOS")
        rn = one(c, "SELECT COUNT(*) FROM raw_repartos_cambios WHERE tipo='NOVEDAD'")
        re = one(c, "SELECT COUNT(*) FROM raw_repartos_cambios WHERE tipo='ELIMINADO'")
        rp = one(c, "SELECT COUNT(*) FROM raw_repartos_cambios WHERE procesado=0")
        rt = one(c, "SELECT COUNT(*) FROM raw_repartos_cambios")
        print(f"novedades={rn}; eliminados={re}; total={rt}; pendientes={rp}")
        if rn + re != rt:
            fail.append("conteo cambios repartos inconsistente")
        if rp:
            fail.append(f"cambios repartos pendientes={rp}")
        missing_rep = one(
            c,
            "SELECT COUNT(*) FROM raw_repartos_cambios ch LEFT JOIN raw_repartos r ON r.reparto_id=ch.reparto_id WHERE ch.tipo='NOVEDAD' AND ch.procesado=1 AND (r.reparto_id IS NULL OR r.eliminado<>0)",
        )
        print("novedades procesadas sin RAW activo:", missing_rep)
        if missing_rep:
            fail.append("repartos nuevos sin RAW")
        section("6] SNAPSHOT REPARTOS")
        reparto = one(c, "SELECT COUNT(*) FROM raw_repartos")
        rv = one(c, "SELECT COUNT(*) FROM raw_reparto_ventas")
        rc = one(c, "SELECT COUNT(*) FROM raw_reparto_clientes")
        print(
            f"raw_repartos={reparto}; raw_reparto_ventas={rv}; raw_reparto_clientes={rc}"
        )
        rhv = one(
            c,
            "SELECT COUNT(*) FROM raw_reparto_ventas x LEFT JOIN raw_repartos r ON r.reparto_id=x.reparto_id WHERE r.reparto_id IS NULL",
        )
        rhc = one(
            c,
            "SELECT COUNT(*) FROM raw_reparto_clientes x LEFT JOIN raw_repartos r ON r.reparto_id=x.reparto_id WHERE r.reparto_id IS NULL",
        )
        print(f"ventas reparto huérfanas={rhv}; clientes reparto huérfanos={rhc}")
        if rhv or rhc:
            fail.append("hijos reparto huérfanos")
        # Fidelidad de arrays reparto contra tablas hijas.
        expv = expc = 0
        bad = 0
        for r in rows(c, "SELECT json_raw FROM raw_repartos WHERE eliminado=0"):
            try:
                o = json.loads(r[0])
                expv += len(o.get("ventas") or [])
                expc += len(o.get("clientes") or [])
            except Exception:
                bad += 1
        print(
            f"JSON ventas={expv} vs tabla={rv}; JSON clientes={expc} vs tabla={rc}; JSON inválidos={bad}"
        )
        if expv != rv:
            fail.append("pérdida reparto ventas")
        if expc != rc:
            fail.append("pérdida reparto clientes")
        if bad:
            fail.append("json repartos inválidos")
        section("7] INTEGRIDAD RAW GENERAL")
        for r in rows(c, "SELECT control,resultado FROM audit_raw_integridad"):
            print(f"{r['control']}: {r['resultado']}")
            if r["resultado"]:
                fail.append(f"{r['control']}={r['resultado']}")
        for r in rows(c, "SELECT entidad,resultado FROM audit_raw_json_invalido"):
            print(f"json {r['entidad']}: {r['resultado']}")
            if r["resultado"]:
                fail.append(f"json {r['entidad']}={r['resultado']}")
        section("8] RUNS DE SINCRONIZACIÓN")
        enc = one(c, "SELECT COUNT(*) FROM raw_sync_runs WHERE estado='EN_CURSO'")
        errs = one(c, "SELECT COUNT(*) FROM raw_sync_runs WHERE estado='ERROR'")
        oks = one(c, "SELECT COUNT(*) FROM raw_sync_runs WHERE estado='OK'")
        print(f"OK={oks}; ERROR={errs}; EN_CURSO={enc}")
        if enc:
            fail.append(f"runs EN_CURSO={enc}")
        for r in rows(
            c,
            "SELECT run_id,proceso,modo,estado,iniciado_utc,finalizado_utc,registros_recibidos,error_texto FROM raw_sync_runs ORDER BY run_id DESC LIMIT 12",
        ):
            print(dict(r))
        section("9] IDEMPOTENCIA OBSERVABLE")
        for proc in ["incremental_ventas_v23", "incremental_repartos_v23"]:
            rr = rows(
                c,
                "SELECT run_id,estado,detalle FROM raw_sync_runs WHERE proceso=? ORDER BY run_id DESC LIMIT 2",
                (proc,),
            )
            print(proc, [dict(x) for x in rr])
            if len(rr) < 2:
                warn.append(
                    f"{proc}: menos de dos ejecuciones para demostrar idempotencia"
                )
            elif rr[0]["estado"] != "OK":
                fail.append(f"{proc} último run no OK")
            else:
                try:
                    d = json.loads(rr[0]["detalle"] or "{}")
                    changes = sum(
                        v
                        for k, v in d.items()
                        if k in ("novedades", "eliminadas", "eliminados")
                        and isinstance(v, int)
                    )
                    print("último ciclo cambios=", changes)
                    if changes != 0:
                        warn.append(f"{proc}: último ciclo no fue vacío")
                except Exception:
                    warn.append(f"{proc}: detalle no parseable")
        section("10] DICTAMEN")
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
