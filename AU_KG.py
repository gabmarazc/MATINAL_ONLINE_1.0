from __future__ import annotations

import argparse
import re
import sqlite3
import unicodedata
from calendar import monthrange
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from modules.business_rules.business_rules_kilos import obtener_matriz_kilos_comercial
from modules.core.core_operaciones import obtener_core_operacion
from modules.staging import obtener_staging_rutas
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

DB_DEFAULT = Path("data") / "matinal.db"
OUT_DEFAULT = Path("reportes") / "evolucion_kilos_vendedor"
TABLA_PARAMETROS = "parametros"
PROVEEDOR_OBJETIVO = "PEPSICO DE ARGENTINA SRL"
TIPOS_EXCLUIDOS = {
    "Comodato Devolución",
    "Comodato Ficticio",
    "Comodato Ficticio Devolución",
    "Comodato Préstamo",
}


def normalizar(valor):
    texto = unicodedata.normalize("NFKD", "" if valor is None else str(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", texto.lower())


def qi(valor):
    return '"' + str(valor).replace('"', '""') + '"'


def tablas(conn):
    return {
        fila[0]
        for fila in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def columnas(conn, tabla):
    return [fila[1] for fila in conn.execute(f"PRAGMA table_info({qi(tabla)})")]


def elegir(disponibles, candidatos, etiqueta):
    mapa = {normalizar(columna): columna for columna in disponibles}
    for candidato in candidatos:
        clave = normalizar(candidato)
        if clave in mapa:
            return mapa[clave]
    raise RuntimeError(
        f"No se encontro columna para {etiqueta}. Disponibles: {disponibles}"
    )


def fmt_kg(valor):
    return f"{float(valor):,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(valor):
    return f"{float(valor):.1f}%".replace(".", ",")


def leer_contexto_operativo(conn, anio_arg, mes_arg):
    if (anio_arg is None) != (mes_arg is None):
        raise ValueError("Debe indicar --anio y --mes juntos.")

    valores = {}
    if TABLA_PARAMETROS in tablas(conn):
        cols = columnas(conn, TABLA_PARAMETROS)
        cp = elegir(cols, ["PARAMETRO", "Parametro"], "parametro")
        cv = elegir(cols, ["VALOR", "Valor"], "valor")
        df = pd.read_sql_query(
            f"SELECT {qi(cp)} parametro, {qi(cv)} valor FROM {qi(TABLA_PARAMETROS)}",
            conn,
        )
        valores = {
            normalizar(parametro): valor
            for parametro, valor in zip(df["parametro"], df["valor"])
        }

    if anio_arg is not None:
        anio = int(anio_arg)
        mes = int(mes_arg)
        fuente = "argumentos"
    else:
        if "ano" not in valores or "mes" not in valores:
            raise RuntimeError(
                "No se pudo determinar Año y Mes desde parametros. "
                "Indique --anio y --mes."
            )
        anio = int(float(valores["ano"]))
        mes = int(float(valores["mes"]))
        fuente = "parametros"

    if not 1 <= mes <= 12:
        raise ValueError("El mes operativo debe estar entre 1 y 12.")

    dia_matinal = str(valores.get("diamatinal", f"02/{mes:02d}/{anio}"))
    dia_venta = str(valores.get("diaventa", f"01/{mes:02d}/{anio}"))
    dia_anterior = str(valores.get("diaanterior", dia_venta))

    return {
        "anio": anio,
        "mes": mes,
        "dia_matinal": dia_matinal,
        "dia_venta": dia_venta,
        "dia_anterior": dia_anterior,
        "fuente": fuente,
    }


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#68717D"))
    canvas.drawString(
        15 * mm,
        8 * mm,
        "MATINAL ONLINE - Evolucion y exigencia diaria de kilos PEPSICO",
    )
    canvas.drawRightString(282 * mm, 8 * mm, f"Pagina {doc.page}")
    canvas.restoreState()


def estilos():
    base = getSampleStyleSheet()
    return {
        "portada": ParagraphStyle(
            "portada",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=29,
            textColor=colors.HexColor("#17324D"),
            alignment=TA_CENTER,
        ),
        "centro": ParagraphStyle(
            "centro",
            parent=base["Normal"],
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#52616F"),
            alignment=TA_CENTER,
        ),
        "titulo": ParagraphStyle(
            "titulo",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=20,
            textColor=colors.HexColor("#17324D"),
            alignment=TA_LEFT,
        ),
        "sub": ParagraphStyle(
            "sub",
            parent=base["Normal"],
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#52616F"),
            alignment=TA_LEFT,
        ),
        "kpi": ParagraphStyle(
            "kpi",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            textColor=colors.HexColor("#17324D"),
            alignment=TA_CENTER,
        ),
        "label": ParagraphStyle(
            "label",
            parent=base["Normal"],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#68717D"),
            alignment=TA_CENTER,
        ),
    }


def tabla_estilo(encabezado="#17324D", tam=8):
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(encabezado)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), tam),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7DEE5")),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#F7F9FA")],
            ),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]
    )


def normalizar_rutas(df_rutas, anio, mes):
    if df_rutas is None or df_rutas.empty:
        raise RuntimeError("La tabla de rutas esta vacia.")

    rutas = df_rutas.copy()
    col_fecha = next(
        (c for c in ["Fecha", "fecha", "Dia", "Date", "FECHA"] if c in rutas.columns),
        None,
    )
    col_vendedor = next(
        (
            c
            for c in [
                "codven",
                "CodVen",
                "CodVendedor",
                "Vendedor",
                "Cod_Vendedor",
                "CODVEN",
            ]
            if c in rutas.columns
        ),
        None,
    )
    if col_fecha is None or col_vendedor is None:
        raise RuntimeError(
            f"RUTAS no cumple el contrato. Fecha={col_fecha}; Vendedor={col_vendedor}."
        )

    fechas_txt = (
        rutas[col_fecha]
        .astype(str)
        .str.strip()
        .str.replace(" 00:00:00", "", regex=False)
    )
    directo = pd.to_datetime(fechas_txt, format="%Y-%m-%d", errors="coerce")
    invertido = pd.to_datetime(fechas_txt, format="%Y-%d-%m", errors="coerce")
    score_directo = ((directo.dt.year == anio) & (directo.dt.month == mes)).sum()
    score_invertido = ((invertido.dt.year == anio) & (invertido.dt.month == mes)).sum()
    rutas["Fecha"] = directo if score_directo >= score_invertido else invertido
    rutas["CodVendedor"] = pd.to_numeric(rutas[col_vendedor], errors="coerce").astype(
        "Int64"
    )
    rutas = rutas[
        (rutas["Fecha"].dt.year == anio)
        & (rutas["Fecha"].dt.month == mes)
        & rutas["CodVendedor"].notna()
    ][["CodVendedor", "Fecha"]].drop_duplicates()
    return rutas.sort_values(["CodVendedor", "Fecha"]).reset_index(drop=True)


def filtrar_operaciones_comerciales(df):
    if df is None or df.empty:
        return pd.DataFrame()
    requeridas = {
        "Periodo",
        "Proveedor",
        "FechaCarga_dt",
        "PesoKg",
        "CodVendedor",
        "TipoDeVenta",
    }
    faltantes = sorted(requeridas - set(df.columns))
    if faltantes:
        raise RuntimeError(
            "CORE_OPERACION no cumple el contrato requerido. "
            f"Faltan columnas: {faltantes}."
        )
    trabajo = df.copy()
    proveedor = trabajo["Proveedor"].fillna("").astype(str).str.strip().str.upper()
    trabajo = trabajo[proveedor.eq(PROVEEDOR_OBJETIVO)].copy()
    trabajo["TipoDeVenta"] = trabajo["TipoDeVenta"].fillna("").astype(str).str.strip()
    trabajo = trabajo[~trabajo["TipoDeVenta"].isin(TIPOS_EXCLUIDOS)].copy()
    trabajo = trabajo[trabajo["Periodo"].isin(["Arrastre", "Actual"])].copy()

    trabajo["FechaCarga_dt"] = pd.to_datetime(
        trabajo["FechaCarga_dt"], errors="coerce"
    ).dt.normalize()
    if "FechaEntrega_dt" in trabajo.columns:
        trabajo["FechaEntrega_dt"] = pd.to_datetime(
            trabajo["FechaEntrega_dt"], errors="coerce"
        ).dt.normalize()
    elif "FechaEntrega" in trabajo.columns:
        trabajo["FechaEntrega_dt"] = pd.to_datetime(
            trabajo["FechaEntrega"], errors="coerce", dayfirst=True
        ).dt.normalize()
    else:
        trabajo["FechaEntrega_dt"] = pd.NaT

    if "FechaLiquidacion_dt" in trabajo.columns:
        trabajo["FechaLiquidacion_dt"] = pd.to_datetime(
            trabajo["FechaLiquidacion_dt"], errors="coerce"
        ).dt.normalize()
    elif "FechaLiquidacion" in trabajo.columns:
        trabajo["FechaLiquidacion_dt"] = pd.to_datetime(
            trabajo["FechaLiquidacion"], errors="coerce", dayfirst=True
        ).dt.normalize()
    else:
        trabajo["FechaLiquidacion_dt"] = pd.NaT

    trabajo["PesoKg"] = pd.to_numeric(trabajo["PesoKg"], errors="coerce").fillna(0.0)
    trabajo["CodVendedor"] = pd.to_numeric(
        trabajo["CodVendedor"], errors="coerce"
    ).astype("Int64")
    trabajo["EsRechazo"] = (
        trabajo["TipoDeVenta"].str.casefold().eq("devolución por rechazo".casefold())
    )

    # Contrato temporal diario:
    # - Venta: impacta en FechaCarga.
    # - Devolución por Rechazo: impacta cuando el rechazo se materializa.
    #   Se prioriza FechaLiquidacion, luego FechaEntrega y finalmente FechaCarga.
    fecha_rechazo = (
        trabajo["FechaLiquidacion_dt"]
        .combine_first(trabajo["FechaEntrega_dt"])
        .combine_first(trabajo["FechaCarga_dt"])
    )
    trabajo["FechaImpacto"] = trabajo["FechaCarga_dt"]
    trabajo.loc[trabajo["EsRechazo"], "FechaImpacto"] = fecha_rechazo.loc[
        trabajo["EsRechazo"]
    ]
    trabajo["FechaImpacto"] = pd.to_datetime(
        trabajo["FechaImpacto"], errors="coerce"
    ).dt.normalize()
    return trabajo


def construir_movimientos_por_vendedor(df_operaciones, codigos_validos):
    columnas_salida = [
        "CodVendedor",
        "Periodo",
        "Fecha",
        "VentaBruta",
        "Rechazos",
        "KilosNetos",
    ]
    if df_operaciones.empty:
        return pd.DataFrame(columns=columnas_salida)

    df = df_operaciones.copy()
    df["CodVendedorHistorico"] = df["CodVendedor"]
    if "CodVendedorVigente" in df.columns:
        vigente = pd.to_numeric(df["CodVendedorVigente"], errors="coerce").astype(
            "Int64"
        )
        df["CodVendedorTitular"] = df["CodVendedor"].where(
            ~vigente.isin(codigos_validos), vigente
        )
    else:
        df["CodVendedorTitular"] = df["CodVendedor"]

    df["VentaBruta"] = np.where(~df["EsRechazo"], df["PesoKg"], 0.0)
    df["Rechazos"] = np.where(df["EsRechazo"], df["PesoKg"], 0.0)
    df["KilosNetos"] = df["VentaBruta"] + df["Rechazos"]

    base = df[
        [
            "CodVendedorTitular",
            "Periodo",
            "FechaImpacto",
            "VentaBruta",
            "Rechazos",
            "KilosNetos",
        ]
    ].rename(
        columns={
            "CodVendedorTitular": "CodVendedor",
            "FechaImpacto": "Fecha",
        }
    )
    movimientos = [base]

    if "CodVendedorOperativo" in df.columns:
        operativo = pd.to_numeric(df["CodVendedorOperativo"], errors="coerce").astype(
            "Int64"
        )
        mask_reemplazo = (
            operativo.notna()
            & operativo.ne(df["CodVendedorHistorico"])
            & operativo.isin(codigos_validos)
        )
        reemplazos = df[mask_reemplazo].copy()
        if not reemplazos.empty:
            salida = reemplazos[
                [
                    "CodVendedorTitular",
                    "Periodo",
                    "FechaImpacto",
                    "VentaBruta",
                    "Rechazos",
                    "KilosNetos",
                ]
            ].rename(
                columns={
                    "CodVendedorTitular": "CodVendedor",
                    "FechaImpacto": "Fecha",
                }
            )
            for columna in ["VentaBruta", "Rechazos", "KilosNetos"]:
                salida[columna] = -salida[columna]

            entrada = reemplazos[
                [
                    "CodVendedorOperativo",
                    "Periodo",
                    "FechaImpacto",
                    "VentaBruta",
                    "Rechazos",
                    "KilosNetos",
                ]
            ].rename(
                columns={
                    "CodVendedorOperativo": "CodVendedor",
                    "FechaImpacto": "Fecha",
                }
            )
            movimientos.extend([salida, entrada])

    resultado = pd.concat(movimientos, ignore_index=True)
    resultado["CodVendedor"] = pd.to_numeric(
        resultado["CodVendedor"], errors="coerce"
    ).astype("Int64")
    resultado = resultado[
        resultado["CodVendedor"].isin(codigos_validos) & resultado["Fecha"].notna()
    ]
    return (
        resultado.groupby(
            ["CodVendedor", "Periodo", "Fecha"], as_index=False, dropna=False
        )[["VentaBruta", "Rechazos", "KilosNetos"]]
        .sum()
        .sort_values(["CodVendedor", "Fecha"])
        .reset_index(drop=True)
    )


def resumir_matriz_por_vendedor(matriz):
    if matriz is None or matriz.empty:
        raise RuntimeError("BUSINESS_RULES_KILOS no devolvio la matriz comercial.")

    columnas_numericas = [
        "Objetivo Mes Corriente",
        "Arrastre",
        "Actual",
        "OPERATIVO",
        "Ajuste_Reemp_Arrastre",
        "Ajuste_Reemp_Actual",
    ]
    df = matriz.copy()
    for columna in columnas_numericas:
        if columna not in df.columns:
            df[columna] = 0.0
        df[columna] = pd.to_numeric(df[columna], errors="coerce").fillna(0.0)

    resumen = (
        df.groupby("CodVendedor", as_index=False)
        .agg(
            Nombre=("Nombre", "first"),
            Supervisor=("SUP", "first"),
            Objetivo=("Objetivo Mes Corriente", "sum"),
            Arrastre=("Arrastre", "sum"),
            Actual=("Actual", "sum"),
            Operativo=("OPERATIVO", "sum"),
            AjusteArrastre=("Ajuste_Reemp_Arrastre", "sum"),
            AjusteActual=("Ajuste_Reemp_Actual", "sum"),
            Rutas=("Rutas", "max"),
            RutasAjustadas=("Rutas_Ajustadas", "max"),
            DiasRestantes=("Días Restantes", "max"),
        )
        .reset_index(drop=True)
    )
    resumen["CodVendedor"] = pd.to_numeric(
        resumen["CodVendedor"], errors="coerce"
    ).astype("Int64")
    resumen = resumen[resumen["CodVendedor"].notna() & resumen["CodVendedor"].ne(99)]
    resumen["Logro"] = resumen["Operativo"]
    resumen["Pendiente"] = (resumen["Objetivo"] - resumen["Logro"]).clip(lower=0.0)
    resumen["Cumplimiento"] = (
        resumen["Logro"].div(resumen["Objetivo"].replace(0, pd.NA)).mul(100).fillna(0.0)
    )
    return resumen.sort_values(["Supervisor", "Nombre"]).reset_index(drop=True)


def construir_serie_vendedor(
    cod_vendedor,
    objetivo,
    arrastre_inicial,
    movimientos,
    rutas_vendedor,
    inicio,
    fin_reporte,
):
    calendario = pd.date_range(inicio, fin_reporte, freq="D")
    actual = movimientos[
        (movimientos["CodVendedor"] == cod_vendedor)
        & movimientos["Periodo"].eq("Actual")
    ][["Fecha", "VentaBruta", "Rechazos", "KilosNetos"]].copy()
    actual = actual.groupby("Fecha", as_index=False)[
        ["VentaBruta", "Rechazos", "KilosNetos"]
    ].sum()

    diario = pd.DataFrame({"Fecha": calendario}).merge(actual, on="Fecha", how="left")
    for columna in ["VentaBruta", "Rechazos", "KilosNetos"]:
        diario[columna] = diario[columna].fillna(0.0)
    diario["KilosDia"] = diario["KilosNetos"]
    diario["KilosAcumulados"] = diario["KilosNetos"].cumsum()
    diario["LogroAcumulado"] = arrastre_inicial + diario["KilosAcumulados"]
    diario["DiaSemana"] = diario["Fecha"].dt.dayofweek.map(
        {0: "Lu", 1: "Ma", 2: "Mi", 3: "Ju", 4: "Vi", 5: "Sa", 6: "Do"}
    )

    fechas_ruta = pd.DatetimeIndex(
        sorted(pd.to_datetime(rutas_vendedor["Fecha"].dropna().unique()))
    )
    rutas_transcurridas = fechas_ruta[fechas_ruta <= fin_reporte]
    comparacion = pd.DataFrame({"Fecha": rutas_transcurridas})
    columnas_vacias = [
        "Fecha",
        "VentaBruta",
        "Rechazos",
        "VentaReal",
        "MediaNecesaria",
        "Diferencia",
        "RutasRestantesIncluyendoDia",
        "LogroPrevio",
        "Estado",
    ]
    if comparacion.empty:
        return diario, pd.DataFrame(columns=columnas_vacias)

    mapas = diario.set_index("Fecha")[["VentaBruta", "Rechazos", "KilosNetos"]]
    filas = []
    for fecha in rutas_transcurridas:
        venta_previa = diario.loc[diario["Fecha"] < fecha, "KilosNetos"].sum()
        logro_previo = float(arrastre_inicial + venta_previa)
        pendiente_previo = max(float(objetivo) - logro_previo, 0.0)
        rutas_restantes = int((fechas_ruta >= fecha).sum())
        media_necesaria = (
            pendiente_previo / rutas_restantes if rutas_restantes > 0 else 0.0
        )
        if fecha in mapas.index:
            venta_bruta = float(mapas.loc[fecha, "VentaBruta"])
            rechazos = float(mapas.loc[fecha, "Rechazos"])
            venta_real = float(mapas.loc[fecha, "KilosNetos"])
        else:
            venta_bruta = rechazos = venta_real = 0.0
        diferencia = venta_real - media_necesaria
        if venta_real < 0:
            estado = "NETO NEGATIVO POR RECHAZOS"
        elif venta_bruta == 0 and rechazos == 0:
            estado = "SIN MOVIMIENTO"
        elif diferencia >= 0:
            estado = "SUPERO LA MEDIA"
        elif rechazos < 0:
            estado = "BAJO LA MEDIA CON RECHAZOS"
        else:
            estado = "BAJO LA MEDIA"
        filas.append(
            {
                "Fecha": fecha,
                "VentaBruta": venta_bruta,
                "Rechazos": rechazos,
                "VentaReal": venta_real,
                "MediaNecesaria": media_necesaria,
                "Diferencia": diferencia,
                "RutasRestantesIncluyendoDia": rutas_restantes,
                "LogroPrevio": logro_previo,
                "Estado": estado,
            }
        )
    return diario, pd.DataFrame(filas)


def _configurar_eje_fechas(ax, fechas):
    fechas = pd.DatetimeIndex(pd.to_datetime(fechas))
    ax.set_xticks(fechas)
    ax.set_xticklabels(
        [f.strftime("%d/%m") for f in fechas], rotation=90, ha="center", fontsize=6
    )
    ax.margins(x=0.02)


def grafico_evolucion(diario, titulo, ruta):
    fig, ax1 = plt.subplots(figsize=(12.8, 3.2))
    colores_barras = np.where(diario["KilosDia"] < 0, "#D97706", "#2F6B8A")
    barras = ax1.bar(
        diario["Fecha"],
        diario["KilosDia"],
        color=colores_barras,
        width=0.72,
        label="Kg netos por dia",
    )
    con_venta = diario.loc[diario["KilosDia"] != 0, "KilosDia"]
    promedio = float(con_venta.mean()) if not con_venta.empty else 0.0
    ax1.axhline(
        promedio,
        color="#2E8B57",
        linewidth=1.8,
        linestyle="--",
        label=f"Promedio diario: {fmt_kg(promedio)} kg",
    )
    ax1.set_ylabel("Kilos por dia")
    ax1.grid(axis="y", alpha=0.25)
    _configurar_eje_fechas(ax1, diario["Fecha"])
    for barra, valor in zip(barras, diario["KilosDia"]):
        if float(valor) != 0.0:
            ax1.annotate(
                fmt_kg(valor),
                xy=(barra.get_x() + barra.get_width() / 2, float(valor)),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=5.5,
                color="#17324D",
                rotation=90,
                clip_on=False,
            )
    ax2 = ax1.twinx()
    ax2.plot(
        diario["Fecha"],
        diario["KilosAcumulados"],
        color="#E67E22",
        linewidth=2.0,
        marker="o",
        markersize=3.2,
        label="Kg acumulados",
    )
    ax2.set_ylabel("Kilos acumulados")
    for fecha, acumulado in zip(diario["Fecha"], diario["KilosAcumulados"]):
        ax2.annotate(
            fmt_kg(acumulado),
            xy=(fecha, float(acumulado)),
            xytext=(3, -8),
            textcoords="offset points",
            ha="left",
            va="top",
            fontsize=4.8,
            color="#A9540B",
            rotation=35,
            clip_on=False,
        )
    ax1.set_ylim(top=max(float(diario["KilosDia"].max()), 1.0) * 1.25)
    ax1.set_title(titulo, fontsize=11, fontweight="bold")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(ruta, dpi=180, bbox_inches="tight")
    plt.close(fig)


def grafico_media_vs_real(comparacion, titulo, ruta):
    fig, ax = plt.subplots(figsize=(12.8, 3.2))
    if comparacion.empty:
        ax.text(
            0.5,
            0.5,
            "Sin calendario de rutas disponible para el vendedor",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=12,
            color="#68717D",
        )
        ax.set_axis_off()
    else:
        ax.plot(
            comparacion["Fecha"],
            comparacion["MediaNecesaria"],
            color="#C0392B",
            linewidth=2.2,
            marker="o",
            markersize=4.5,
            label="Media necesaria al iniciar el dia",
        )
        ax.plot(
            comparacion["Fecha"],
            comparacion["VentaReal"],
            color="#2F6B8A",
            linewidth=2.2,
            marker="o",
            markersize=4.5,
            label="Venta neta real del dia",
        )
        ax.fill_between(
            comparacion["Fecha"],
            comparacion["MediaNecesaria"],
            comparacion["VentaReal"],
            where=comparacion["VentaReal"] >= comparacion["MediaNecesaria"],
            color="#2E8B57",
            alpha=0.12,
            interpolate=True,
        )
        ax.fill_between(
            comparacion["Fecha"],
            comparacion["MediaNecesaria"],
            comparacion["VentaReal"],
            where=comparacion["VentaReal"] < comparacion["MediaNecesaria"],
            color="#C0392B",
            alpha=0.10,
            interpolate=True,
        )
        for fecha, media, real in zip(
            comparacion["Fecha"],
            comparacion["MediaNecesaria"],
            comparacion["VentaReal"],
        ):
            ax.annotate(
                f"M {fmt_kg(media)}",
                xy=(fecha, float(media)),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=5.5,
                color="#922B21",
                rotation=45,
                clip_on=False,
            )
            ax.annotate(
                f"R {fmt_kg(real)}",
                xy=(fecha, float(real)),
                xytext=(0, -10),
                textcoords="offset points",
                ha="center",
                va="top",
                fontsize=5.5,
                color="#1F4E66",
                rotation=45,
                clip_on=False,
            )
        ax.axhline(0, color="#697278", linewidth=0.6)
        ax.set_ylabel("Kilos")
        ax.set_xlabel("Dia de ruta")
        ax.grid(axis="y", alpha=0.25)
        _configurar_eje_fechas(ax, comparacion["Fecha"])
        maximo = max(
            float(comparacion["MediaNecesaria"].max()),
            float(comparacion["VentaReal"].max()),
            1.0,
        )
        ax.set_ylim(
            bottom=min(0.0, float(comparacion["VentaReal"].min()) * 1.15),
            top=maximo * 1.25,
        )
        ax.legend(loc="upper right", frameon=False, fontsize=8)
    ax.set_title(titulo, fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(ruta, dpi=180, bbox_inches="tight")
    plt.close(fig)


def bloque_vendedor(reporte, periodo, st):
    kpis = [
        (fmt_kg(reporte["objetivo"]), "Objetivo mensual"),
        (fmt_kg(reporte["arrastre"]), "Arrastre inicial"),
        (fmt_kg(reporte["actual"]), "Actual acumulado"),
        (fmt_kg(reporte["logro"]), "Logro operativo"),
        (fmt_pct(reporte["cumplimiento"]), "Cumplimiento"),
        (fmt_kg(reporte["pendiente"]), "Pendiente"),
        (str(reporte["rutas_totales"]), "Rutas del mes"),
        (fmt_kg(reporte["media_vigente"]), "Media necesaria vigente"),
    ]
    tabla_kpi = Table(
        [
            [Paragraph(valor, st["kpi"]) for valor, _ in kpis],
            [Paragraph(etiqueta, st["label"]) for _, etiqueta in kpis],
        ],
        colWidths=[32 * mm] * 8,
        rowHeights=[11 * mm, 7 * mm],
    )
    tabla_kpi.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F6F8")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E0E6")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E0E6")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    return [
        Paragraph(f"{reporte['id']} - {reporte['nombre']}", st["titulo"]),
        Paragraph(
            (
                f"Mes operativo: {periodo} | Proveedor: {PROVEEDOR_OBJETIVO} | "
                f"Proxima ruta: {reporte['proxima_ruta'].strftime('%d/%m/%Y') if pd.notna(reporte['proxima_ruta']) else 'Sin ruta futura'} | "
                f"Rutas futuras: {reporte['rutas_futuras']}"
            ),
            st["sub"],
        ),
        Spacer(1, 2 * mm),
        tabla_kpi,
        Spacer(1, 1.5 * mm),
        Image(str(reporte["grafico_evolucion"]), width=260 * mm, height=66 * mm),
        Spacer(1, 0.8 * mm),
        Image(str(reporte["grafico_media"]), width=260 * mm, height=66 * mm),
    ]


def bloque_tabla_diaria(reporte, periodo, st):
    comp = reporte["comparacion"].copy()
    dias = {0: "Lu", 1: "Ma", 2: "Mi", 3: "Ju", 4: "Vi", 5: "Sa", 6: "Do"}
    filas = [
        [
            "Fecha",
            "Dia",
            "Rutas rest.",
            "Media",
            "Venta bruta",
            "Rechazos",
            "Venta neta",
            "Diferencia",
            "Estado",
        ]
    ]
    for x in comp.itertuples(index=False):
        filas.append(
            [
                x.Fecha.strftime("%d/%m/%Y"),
                dias.get(x.Fecha.dayofweek, ""),
                str(int(x.RutasRestantesIncluyendoDia)),
                fmt_kg(x.MediaNecesaria),
                fmt_kg(x.VentaBruta),
                fmt_kg(x.Rechazos),
                fmt_kg(x.VentaReal),
                ("+" if x.Diferencia > 0 else "") + fmt_kg(x.Diferencia),
                x.Estado,
            ]
        )
    tabla = Table(
        filas,
        colWidths=[
            25 * mm,
            12 * mm,
            22 * mm,
            24 * mm,
            27 * mm,
            24 * mm,
            27 * mm,
            27 * mm,
            55 * mm,
        ],
        repeatRows=1,
    )
    estilo = tabla_estilo(tam=6.5)
    for i, x in enumerate(comp.itertuples(index=False), start=1):
        if x.VentaReal < 0:
            fondo = colors.HexColor("#FDE7C7")
            texto = colors.HexColor("#9A4D00")
        elif x.Diferencia >= 0:
            fondo = colors.HexColor("#DFF3E5")
            texto = colors.HexColor("#176B3A")
        else:
            fondo = colors.HexColor("#FBE3E1")
            texto = colors.HexColor("#A12622")
        estilo.add("BACKGROUND", (-2, i), (-1, i), fondo)
        estilo.add("TEXTCOLOR", (-2, i), (-1, i), texto)
        estilo.add("FONTNAME", (-2, i), (-1, i), "Helvetica-Bold")
        if x.Rechazos < 0:
            estilo.add("BACKGROUND", (5, i), (5, i), colors.HexColor("#FFF2CC"))
            estilo.add("TEXTCOLOR", (5, i), (5, i), colors.HexColor("#9A4D00"))
    tabla.setStyle(estilo)

    positivas = comp[comp["VentaReal"] > 0]
    if positivas.empty:
        mejor_txt = peor_txt = "Sin dias con venta neta positiva"
    else:
        mejor = positivas.loc[positivas["VentaReal"].idxmax()]
        peor = positivas.loc[positivas["VentaReal"].idxmin()]
        mejor_txt = (
            f"{mejor['Fecha'].strftime('%d/%m/%Y')}<br/>{fmt_kg(mejor['VentaReal'])} kg"
        )
        peor_txt = (
            f"{peor['Fecha'].strftime('%d/%m/%Y')}<br/>{fmt_kg(peor['VentaReal'])} kg"
        )
    total_rechazos = float(comp["Rechazos"].sum()) if not comp.empty else 0.0
    dias_rechazo = int((comp["Rechazos"] < 0).sum()) if not comp.empty else 0
    dias_supera = int((comp["Diferencia"] >= 0).sum()) if not comp.empty else 0
    tasa = dias_supera / len(comp) * 100 if len(comp) else 0.0
    resumen = Table(
        [
            [
                Paragraph(mejor_txt, st["kpi"]),
                Paragraph(peor_txt, st["kpi"]),
                Paragraph(
                    f"{fmt_kg(total_rechazos)} kg<br/>{dias_rechazo} dias", st["kpi"]
                ),
                Paragraph(
                    f"{dias_supera} de {len(comp)}<br/>{fmt_pct(tasa)}", st["kpi"]
                ),
            ],
            [
                Paragraph("Mejor dia de venta neta", st["label"]),
                Paragraph("Peor dia con venta neta positiva", st["label"]),
                Paragraph("Rechazos acumulados", st["label"]),
                Paragraph("Dias que supero la media", st["label"]),
            ],
        ],
        colWidths=[64 * mm] * 4,
    )
    resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F6F8")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E0E6")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E0E6")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#DFF3E5")),
                ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#FBE3E1")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#FFF2CC")),
            ]
        )
    )
    return [
        Paragraph(
            f"{reporte['id']} - {reporte['nombre']} | Detalle diario", st["titulo"]
        ),
        Paragraph(
            f"Mes operativo: {periodo} | Venta: FechaCarga. Rechazo: FechaLiquidacion, con respaldo en FechaEntrega y FechaCarga.",
            st["sub"],
        ),
        Spacer(1, 3 * mm),
        tabla,
        Spacer(1, 4 * mm),
        resumen,
    ]


def crear_pdf(ruta, periodo, reportes):
    st = estilos()
    doc = BaseDocTemplate(
        str(ruta),
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=10 * mm,
        bottomMargin=14 * mm,
        title=f"Evolucion y exigencia diaria de kilos PEPSICO - {periodo}",
        author="MATINAL ONLINE",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="reporte", frames=frame, onPage=pie)])

    ranking = sorted(reportes, key=lambda r: r["logro"], reverse=True)
    objetivo_total = sum(r["objetivo"] for r in ranking)
    logro_total = sum(r["logro"] for r in ranking)
    cumplimiento = logro_total / objetivo_total * 100 if objetivo_total else 0.0

    story = [
        Spacer(1, 25 * mm),
        Paragraph("EVOLUCION Y EXIGENCIA DIARIA DE KILOS PEPSICO", st["portada"]),
        Spacer(1, 7 * mm),
        Paragraph(f"Mes operativo: {periodo}", st["centro"]),
        Paragraph(f"Vendedores incluidos: {len(ranking)}", st["centro"]),
        Paragraph(f"Objetivo total: {fmt_kg(objetivo_total)} kg", st["centro"]),
        Paragraph(f"Logro operativo: {fmt_kg(logro_total)} kg", st["centro"]),
        Paragraph(f"Cumplimiento: {fmt_pct(cumplimiento)}", st["centro"]),
        PageBreak(),
    ]

    ranking_data = [
        ["Pos.", "Codigo", "Vendedor", "Objetivo", "Arrastre", "Actual", "Logro", "%"]
    ] + [
        [
            posicion,
            reporte["id"],
            reporte["nombre"],
            fmt_kg(reporte["objetivo"]),
            fmt_kg(reporte["arrastre"]),
            fmt_kg(reporte["actual"]),
            fmt_kg(reporte["logro"]),
            fmt_pct(reporte["cumplimiento"]),
        ]
        for posicion, reporte in enumerate(ranking, 1)
    ]
    tabla_ranking = Table(
        ranking_data,
        colWidths=[
            14 * mm,
            20 * mm,
            78 * mm,
            30 * mm,
            28 * mm,
            28 * mm,
            28 * mm,
            22 * mm,
        ],
        repeatRows=1,
    )
    tabla_ranking.setStyle(tabla_estilo(tam=8))
    story += [
        Paragraph("Resumen general y ranking", st["titulo"]),
        Spacer(1, 3 * mm),
        tabla_ranking,
        PageBreak(),
    ]

    for indice, reporte in enumerate(ranking):
        story += bloque_vendedor(reporte, periodo, st)
        story.append(PageBreak())
        story += bloque_tabla_diaria(reporte, periodo, st)
        if indice < len(ranking) - 1:
            story.append(PageBreak())

    doc.build(story)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Genera un PDF con objetivo, arrastre, venta actual, evolucion diaria "
            "y media necesaria dinamica por vendedor."
        )
    )
    parser.add_argument("--db", type=Path, default=DB_DEFAULT)
    parser.add_argument("--salida", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--anio", type=int)
    parser.add_argument("--mes", type=int)
    argumentos = parser.parse_args()

    if not argumentos.db.exists():
        raise FileNotFoundError(f"No existe: {argumentos.db.resolve()}")

    conexion = sqlite3.connect(
        f"file:{argumentos.db.resolve().as_posix()}?mode=ro", uri=True
    )
    try:
        contexto = leer_contexto_operativo(conexion, argumentos.anio, argumentos.mes)
    finally:
        conexion.close()

    anio = contexto["anio"]
    mes = contexto["mes"]
    periodo = f"{anio:04d}-{mes:02d}"
    filtros_globales = {
        "anio": anio,
        "mes": mes,
        "supervisor": "TODOS",
        "dia_matinal": contexto["dia_matinal"],
        "dia_venta": contexto["dia_venta"],
        "dia_anterior": contexto["dia_anterior"],
    }

    dia_venta = pd.to_datetime(
        contexto["dia_venta"], format="%d/%m/%Y", errors="coerce"
    )
    if pd.isna(dia_venta):
        raise RuntimeError(f"Dia Venta invalido: {contexto['dia_venta']}")

    inicio = pd.Timestamp(date(anio, mes, 1))
    fin_mes = pd.Timestamp(date(anio, mes, monthrange(anio, mes)[1]))
    fin_reporte = min(fin_mes, dia_venta.normalize())

    matriz = obtener_matriz_kilos_comercial(anio, mes, filtros_globales)
    resumen = resumir_matriz_por_vendedor(matriz)
    if resumen.empty:
        raise RuntimeError(
            f"No hay vendedores con objetivos/operaciones para {periodo}."
        )

    core = obtener_core_operacion(
        anio,
        mes,
        contexto["dia_matinal"],
        contexto["dia_venta"],
        modo_ajuste="AJUSTADO",
    )
    operaciones = filtrar_operaciones_comerciales(core["df_vta_operativa"])
    if operaciones.empty:
        raise RuntimeError(
            f"No hay operaciones comerciales {PROVEEDOR_OBJETIVO} para {periodo}."
        )

    codigos_validos = set(resumen["CodVendedor"].dropna().astype(int).tolist())
    movimientos = construir_movimientos_por_vendedor(operaciones, codigos_validos)

    rutas = normalizar_rutas(obtener_staging_rutas(), anio, mes)

    argumentos.salida.mkdir(parents=True, exist_ok=True)
    temporal = argumentos.salida / "_tmp_graficos"
    temporal.mkdir(exist_ok=True)

    reportes = []
    try:
        for fila in resumen.itertuples(index=False):
            codigo = int(fila.CodVendedor)
            rutas_vendedor = rutas[rutas["CodVendedor"] == codigo].copy()

            mov_arrastre = movimientos[
                (movimientos["CodVendedor"] == codigo)
                & movimientos["Periodo"].eq("Arrastre")
            ]["KilosNetos"].sum()
            arrastre_inicial = float(mov_arrastre)

            diario, comparacion = construir_serie_vendedor(
                codigo,
                float(fila.Objetivo),
                arrastre_inicial,
                movimientos,
                rutas_vendedor,
                inicio,
                fin_reporte,
            )

            actual_diario = float(diario["KilosDia"].sum())
            logro = arrastre_inicial + actual_diario
            pendiente = max(float(fila.Objetivo) - logro, 0.0)
            cumplimiento = logro / float(fila.Objetivo) * 100 if fila.Objetivo else 0.0
            rutas_futuras = rutas_vendedor[
                rutas_vendedor["Fecha"] > fin_reporte
            ].sort_values("Fecha")
            cantidad_rutas_futuras = int(len(rutas_futuras))
            proxima_ruta = (
                pd.Timestamp(rutas_futuras.iloc[0]["Fecha"])
                if cantidad_rutas_futuras > 0
                else pd.NaT
            )
            media_vigente = (
                pendiente / cantidad_rutas_futuras
                if cantidad_rutas_futuras > 0
                else 0.0
            )

            grafico_1 = temporal / f"evolucion_{codigo}.png"
            grafico_2 = temporal / f"media_real_{codigo}.png"
            grafico_evolucion(
                diario,
                f"{codigo} - {fila.Nombre} | Evolucion diaria y acumulada",
                grafico_1,
            )
            grafico_media_vs_real(
                comparacion,
                (
                    f"{codigo} - {fila.Nombre} | Media necesaria al iniciar cada ruta "
                    "vs venta real"
                ),
                grafico_2,
            )

            reportes.append(
                {
                    "id": codigo,
                    "nombre": str(fila.Nombre),
                    "objetivo": float(fila.Objetivo),
                    "arrastre": arrastre_inicial,
                    "actual": actual_diario,
                    "logro": logro,
                    "pendiente": pendiente,
                    "cumplimiento": cumplimiento,
                    "rutas_totales": int(len(rutas_vendedor)),
                    "media_vigente": media_vigente,
                    "rutas_futuras": cantidad_rutas_futuras,
                    "proxima_ruta": proxima_ruta,
                    "diario": diario,
                    "comparacion": comparacion,
                    "grafico_evolucion": grafico_1,
                    "grafico_media": grafico_2,
                }
            )

        if not reportes:
            raise RuntimeError("No se generaron reportes por vendedor.")

        salida = argumentos.salida / f"EVOLUCION_KILOS_VENDEDORES_{periodo}.pdf"
        crear_pdf(salida, periodo, reportes)
        print(f"[OK] PDF unico: {salida.resolve()}")
        print(
            f"[OK] Vendedores: {len(reportes)} | Periodo: {periodo} "
            f"({contexto['fuente']})"
        )
    finally:
        for archivo in temporal.glob("*.png"):
            archivo.unlink()
        if temporal.exists() and not any(temporal.iterdir()):
            temporal.rmdir()


if __name__ == "__main__":
    main()
