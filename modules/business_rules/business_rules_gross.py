# modules/business_rules/business_rules_gross.py
import time
import streamlit as st
import pandas as pd
import numpy as np

# REGLA DE ORO: Consumo exclusivo de la Capa CORE y el Repositorio / Staging Autorizado (Cero acceso a bases de datos o SQL directo)
from modules.core.core_vendedores import obtener_core_vendedores
from modules.core.core_operaciones import obtener_core_operacion
from modules.staging import obtener_staging_maestros, obtener_staging_vta


def _filtrar_universo_comercial_gross(df: pd.DataFrame) -> pd.DataFrame:
    """
    BUSINESS_RULES: Aplica las reglas institucionales de exclusión sobre el universo bruto operativo para Gross.
    - Filtra transacciones restringiendo al proveedor PEPSICO.
    - Excluye tipologías de venta atípicas (Comodatos, Préstamos y Devoluciones Ficticias).
    """
    if df is None or df.empty:
        return df

    df_filtrado = df.copy()

    # Regla 1: Restricción exclusiva a Portafolio PEPSICO
    if "Proveedor" in df_filtrado.columns:
        df_filtrado = df_filtrado[
            df_filtrado["Proveedor"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.contains("PEPSICO", na=False)
        ]

    # Regla 2: Exclusión de Comodatos y Préstamos Logísticos
    if "TipoDeVenta" in df_filtrado.columns:
        tipos_excluidos = [
            "Comodato Devolución",
            "Comodato Ficticio",
            "Comodato Ficticio Devolución",
            "Comodato Préstamo",
        ]
        df_filtrado = df_filtrado[
            ~df_filtrado["TipoDeVenta"].astype(str).str.strip().isin(tipos_excluidos)
        ]

    return df_filtrado


def _asegurar_segmento_comercial(df: pd.DataFrame) -> pd.DataFrame:
    """
    BUSINESS_RULES: Replica exactamente la lógica de segmentación (rep_kilos.py / rep_gerencial.py)
    a partir de SegmentoRentabilidad y Rubro, asegurando la existencia de la columna 'SEGMENTO'.
    """
    if df is None or df.empty:
        return df

    df_trabajo = df.copy()

    if "SEGMENTO" not in df_trabajo.columns or df_trabajo["SEGMENTO"].isna().all():
        col_rent = (
            "SegmentoRentabilidad"
            if "SegmentoRentabilidad" in df_trabajo.columns
            else None
        )
        col_rubro = "Rubro" if "Rubro" in df_trabajo.columns else None

        sr = (
            df_trabajo.get(col_rent, pd.Series("", index=df_trabajo.index))
            .fillna("")
            .astype(str)
            .str.strip()
            .str.title()
            if col_rent
            else pd.Series("", index=df_trabajo.index)
        )
        rubro = (
            df_trabajo.get(col_rubro, pd.Series("", index=df_trabajo.index))
            .fillna("")
            .astype(str)
            .str.strip()
            if col_rubro
            else pd.Series("", index=df_trabajo.index)
        )

        cond_gold = sr.isin(["Platinum", "Gold"]).fillna(False)
        cond_silver = sr.isin(["Silver", "Bronze"]).fillna(False)

        gold_val = "GOLD " + rubro
        silver_val = "SILVER " + rubro
        df_trabajo["SEGMENTO"] = np.select(
            [cond_gold, cond_silver],
            [gold_val.str.strip(), silver_val.str.strip()],
            default=None,
        )

    return df_trabajo


def _obtener_futuro_completo_gross(
    anio: int, mes: int, padron_vendedores: pd.DataFrame
) -> pd.DataFrame:
    """Obtiene Gross Futuro completo desde STAGING, sin corte de Dia Matinal."""
    columnas = ["CodVendedor", "SEGMENTO", "Gross_Disponible"]
    futuro = obtener_staging_vta()
    if futuro is None or futuro.empty or padron_vendedores.empty:
        return pd.DataFrame(columns=columnas)
    futuro = _asegurar_segmento_comercial(_filtrar_universo_comercial_gross(futuro))
    carga = pd.to_datetime(futuro["FechaCarga_dt"], errors="coerce")
    entrega = pd.to_datetime(futuro["FechaEntrega_dt"], errors="coerce")
    siguiente = pd.Timestamp(anio, mes, 1) + pd.offsets.MonthBegin(1)
    futuro = futuro[
        carga.dt.year.eq(anio)
        & carga.dt.month.eq(mes)
        & entrega.dt.year.eq(siguiente.year)
        & entrega.dt.month.eq(siguiente.month)
    ].copy()
    futuro["CodVendedor"] = pd.to_numeric(
        futuro["CodVendedor"], errors="coerce"
    ).astype("Int64")
    futuro["ImporteNetoItem"] = pd.to_numeric(
        futuro["ImporteNetoItem"], errors="coerce"
    ).fillna(0.0)
    futuro["SEGMENTO"] = futuro["SEGMENTO"].fillna("").astype(str).str.strip()
    validos = set(
        pd.to_numeric(padron_vendedores["CodVendedor"], errors="coerce")
        .dropna()
        .astype("Int64")
        .tolist()
    )
    futuro = futuro[futuro["CodVendedor"].isin(validos) & futuro["SEGMENTO"].ne("")]
    if futuro.empty:
        return pd.DataFrame(columns=columnas)
    return (
        futuro.groupby(["CodVendedor", "SEGMENTO"], as_index=False)["ImporteNetoItem"]
        .sum()
        .rename(columns={"ImporteNetoItem": "Gross_Disponible"})[columnas]
    )


@st.cache_data(show_spinner=False)
def calcular_objetivos_comerciales_gross(
    anio: int, mes: int, df_vta_prep: pd.DataFrame
) -> pd.DataFrame:
    """
    BUSINESS_RULES: Recupera el maestro de marcas por CEBE vía Staging y distribuye proporcionalmente
    el Objetivo_Importe_Arg (Obj_Gross_Mes) según la participación histórica en kilos por marca y segmento,
    garantizando conservación exacta de masa (SUM(Objetivo_Importe_Arg) = SUM(Obj_Gross_Mes)).
    """
    t0 = time.perf_counter()
    padron_vendedores = obtener_core_vendedores()
    if padron_vendedores.empty:
        raise ValueError(
            "CORE_VENDEDORES no retornó padrón activo para validar los objetivos comerciales de Gross."
        )

    maestros = obtener_staging_maestros()
    maestro_cebe = (
        maestros.get("maestro_marcas_cebe", pd.DataFrame())
        if isinstance(maestros, dict)
        else pd.DataFrame()
    )

    if (
        not maestro_cebe.empty
        and "Mes" in maestro_cebe.columns
        and "Anio" in maestro_cebe.columns
    ):
        mc_per = maestro_cebe[
            (maestro_cebe["Mes"].astype(str) == str(mes))
            & (maestro_cebe["Anio"].astype(str) == str(anio))
        ]
        if not mc_per.empty:
            maestro_cebe = mc_per

    if maestro_cebe.empty or df_vta_prep is None or df_vta_prep.empty:
        print(
            f"[PERF_CORE] calcular_objetivos_comerciales_gross (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Objetivo_Importe_Arg"])

    col_m_cebe = next(
        (c for c in maestro_cebe.columns if "marca" in str(c).strip().lower()),
        maestro_cebe.columns[0],
    )
    col_obj_gross = next(
        (
            c
            for c in maestro_cebe.columns
            if any(
                k in str(c).strip().lower()
                for k in ["obj_gross", "gross", "obj_gross_mes"]
            )
        ),
        None,
    )

    if not col_obj_gross:
        raise ValueError(
            "No se encontró la columna de objetivo gross en maestro_marcas_cebe."
        )

    maestro_cebe_clean = maestro_cebe.copy()
    maestro_cebe_clean["Marca_Key"] = (
        maestro_cebe_clean[col_m_cebe].fillna("").astype(str).str.strip().str.upper()
    )
    maestro_cebe_clean["Obj_Val_Imp"] = pd.to_numeric(
        maestro_cebe_clean[col_obj_gross], errors="coerce"
    ).fillna(0.0)

    mapa_obj_imp = (
        maestro_cebe_clean.groupby("Marca_Key")["Obj_Val_Imp"].sum().to_dict()
    )

    col_sup_v = next(
        (c for c in padron_vendedores.columns if "sup" in str(c).strip().lower()), "SUP"
    )
    sup_map = padron_vendedores.set_index("CodVendedor")[col_sup_v].to_dict()
    codigos_validos = set(padron_vendedores["CodVendedor"].dropna().tolist())

    df_v = df_vta_prep.copy()
    df_v["CodVendedor"] = pd.to_numeric(
        df_v.get("CodVendedor", pd.Series(index=df_v.index)), errors="coerce"
    ).astype("Int64")

    # Filtrar solo preventistas válidos del padrón
    df_v = df_v[df_v["CodVendedor"].isin(codigos_validos)].copy()
    if df_v.empty:
        return pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Objetivo_Importe_Arg"])

    col_marca = next((c for c in ["Marca", "MARCA"] if c in df_v.columns), None)
    if not col_marca:
        raise ValueError("No se encontró la columna Marca en las ventas operativas.")

    df_v["Marca_Key"] = df_v[col_marca].fillna("").astype(str).str.strip().str.upper()
    df_v = _asegurar_segmento_comercial(df_v)
    df_v["PesoKg"] = pd.to_numeric(df_v.get("PesoKg", 0), errors="coerce").fillna(0.0)

    # Cálculo de participación de mercado por marca y segmento (Part_Marca_Seg) a nivel de preventista
    tot_marca_vta = (
        df_v[df_v["SEGMENTO"].notna() & (df_v["SEGMENTO"] != "SIN SEGMENTO")]
        .groupby(["CodVendedor", "Marca_Key", "SEGMENTO"], as_index=False)["PesoKg"]
        .sum()
    )

    tot_marca_vta["Total_Marca"] = (
        tot_marca_vta.groupby("Marca_Key")["PesoKg"].transform("sum").replace(0, 1.0)
    )
    tot_marca_vta["Part_Marca_Seg"] = (
        tot_marca_vta["PesoKg"] / tot_marca_vta["Total_Marca"]
    )
    tot_marca_vta["Obj_Gross_Marca"] = (
        tot_marca_vta["Marca_Key"].map(mapa_obj_imp).fillna(0.0)
    )
    tot_marca_vta["Objetivo_Importe_Arg"] = (
        tot_marca_vta["Obj_Gross_Marca"] * tot_marca_vta["Part_Marca_Seg"]
    )

    resultado = tot_marca_vta.groupby(["CodVendedor", "SEGMENTO"], as_index=False).agg(
        Objetivo_Importe_Arg=("Objetivo_Importe_Arg", "sum")
    )
    print(
        f"[PERF_CORE] calcular_objetivos_comerciales_gross -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado


@st.cache_data(show_spinner=False)
def calcular_compensaciones_reemplazos_gross(
    df_vta_operativa: pd.DataFrame,
) -> pd.DataFrame:
    """
    BUSINESS_RULES: Detecta operaciones realizadas por reemplazantes mediante la titularidad operativa
    y calcula los ajustes compensatorios monetarios de Gross (Arrastre, Actual y Total) usando ImporteNetoItem.
    """
    t0 = time.perf_counter()
    if df_vta_operativa is None or df_vta_operativa.empty:
        print(
            f"[PERF_CORE] calcular_compensaciones_reemplazos_gross (vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame(
            columns=[
                "CodVendedor",
                "SEGMENTO",
                "Ajuste_Reemp_Arrastre",
                "Ajuste_Reemp_Actual",
                "Ajuste_Por_Reemp",
            ]
        )

    df = _asegurar_segmento_comercial(df_vta_operativa)

    for col_req in [
        "CodVendedor",
        "CodVendedorOperativo",
        "SEGMENTO",
        "Periodo",
        "ImporteNetoItem",
    ]:
        if col_req not in df.columns:
            raise ValueError(
                f"Falta la columna obligatoria '{col_req}' para calcular las compensaciones por reemplazo de Gross."
            )

    col_det = (
        "CodVendedorHistorico"
        if "CodVendedorHistorico" in df.columns
        else "CodVendedor"
    )
    col_imp = (
        "CodVendedorVigente" if "CodVendedorVigente" in df.columns else "CodVendedor"
    )

    df["CodVendedor"] = pd.to_numeric(df["CodVendedor"], errors="coerce").astype(
        "Int64"
    )
    df[col_det] = pd.to_numeric(df[col_det], errors="coerce").astype("Int64")
    df[col_imp] = pd.to_numeric(df[col_imp], errors="coerce").astype("Int64")
    df["CodVendedorOperativo"] = pd.to_numeric(
        df["CodVendedorOperativo"], errors="coerce"
    ).astype("Int64")
    df["SEGMENTO"] = df["SEGMENTO"].fillna("").astype(str).str.strip()
    df["ImporteNetoItem"] = pd.to_numeric(
        df["ImporteNetoItem"], errors="coerce"
    ).fillna(0.0)

    # Identificación de transacciones con divergencia entre titular histórico y operador
    reemplazos = df[
        df["CodVendedorOperativo"].ne(df[col_det])
        & df["Periodo"].isin(["Arrastre", "Actual"])
    ].copy()

    if reemplazos.empty:
        print(
            f"[PERF_CORE] calcular_compensaciones_reemplazos_gross (sin reemplazos) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame(
            columns=[
                "CodVendedor",
                "SEGMENTO",
                "Ajuste_Reemp_Arrastre",
                "Ajuste_Reemp_Actual",
                "Ajuste_Por_Reemp",
            ]
        )

    # Descuento al titular vigente (salida monetaria)
    mov_titular = reemplazos[
        [col_imp, "SEGMENTO", "Periodo", "ImporteNetoItem"]
    ].rename(columns={col_imp: "CodVend"})
    mov_titular["Ajuste_Valor"] = -mov_titular.pop("ImporteNetoItem")

    # Suma al reemplazante operativo (entrada monetaria)
    mov_reemp = reemplazos[
        ["CodVendedorOperativo", "SEGMENTO", "Periodo", "ImporteNetoItem"]
    ].rename(columns={"CodVendedorOperativo": "CodVend"})
    mov_reemp["Ajuste_Valor"] = mov_reemp.pop("ImporteNetoItem")

    ajustes_totales = pd.concat([mov_titular, mov_reemp], ignore_index=True)
    ajustes_totales["CodVend"] = pd.to_numeric(
        ajustes_totales["CodVend"], errors="coerce"
    ).astype("Int64")

    aj_arr = (
        ajustes_totales[ajustes_totales["Periodo"] == "Arrastre"]
        .groupby(["CodVend", "SEGMENTO"], as_index=False)["Ajuste_Valor"]
        .sum()
        .rename(
            columns={"Ajuste_Valor": "Ajuste_Reemp_Arrastre", "CodVend": "CodVendedor"}
        )
    )
    aj_act = (
        ajustes_totales[ajustes_totales["Periodo"] == "Actual"]
        .groupby(["CodVend", "SEGMENTO"], as_index=False)["Ajuste_Valor"]
        .sum()
        .rename(
            columns={"Ajuste_Valor": "Ajuste_Reemp_Actual", "CodVend": "CodVendedor"}
        )
    )

    consolidado = aj_arr.merge(
        aj_act, on=["CodVendedor", "SEGMENTO"], how="outer"
    ).fillna(0.0)
    consolidado["Ajuste_Por_Reemp"] = (
        consolidado["Ajuste_Reemp_Arrastre"] + consolidado["Ajuste_Reemp_Actual"]
    )

    resultado = consolidado[
        [
            "CodVendedor",
            "SEGMENTO",
            "Ajuste_Reemp_Arrastre",
            "Ajuste_Reemp_Actual",
            "Ajuste_Por_Reemp",
        ]
    ]
    print(
        f"[PERF_CORE] calcular_compensaciones_reemplazos_gross -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado


def _calcular_calendario_ajustado_comercial(
    matriz_comercial: pd.DataFrame,
    padron_vendedores: pd.DataFrame,
    dias_pasados_map: dict,
    rutas_totales_map: dict,
    dias_restantes_todo_map: dict,
    dias_restantes_ajustado_map: dict,
) -> pd.DataFrame:
    """
    BUSINESS_RULES: Incorpora los parámetros logísticos utilizando los mapas seguros y explícitos
    provistos por CORE, garantizando que Rutas sea el total del mes y que TODO y AJUSTADO diverjan correctamente.
    """
    df = matriz_comercial.copy()
    if df.empty or padron_vendedores.empty:
        df["Ajuste_Entrega"] = 1
        df["Rutas_Ajustadas"] = 0
        df["Días Pasados"] = 0
        df["Rutas"] = 0
        df["Días Restantes Todo"] = 0
        df["Días Restantes Ajustado"] = 0
        df["Días Restantes"] = 0
        return df

    mv = padron_vendedores.copy()

    map_ajuste = (
        mv.set_index("CodVendedor")["Ajuste_Entrega"].to_dict()
        if "Ajuste_Entrega" in mv.columns
        else {}
    )
    map_rutas_ajust = (
        mv.set_index("CodVendedor")["Rutas_Ajustadas"].to_dict()
        if "Rutas_Ajustadas" in mv.columns
        else {}
    )

    df["Ajuste_Entrega"] = df["CodVendedor"].map(map_ajuste).fillna(1).astype(int)
    df["Rutas_Ajustadas"] = df["CodVendedor"].map(map_rutas_ajust).fillna(0).astype(int)

    df["Días Pasados"] = (
        df["CodVendedor"].map(dias_pasados_map).fillna(0).astype("Int64")
    )
    df["Rutas"] = df["CodVendedor"].map(rutas_totales_map).fillna(0).astype("Int64")
    df["Días Restantes Todo"] = (
        df["CodVendedor"].map(dias_restantes_todo_map).fillna(0).astype("Int64")
    )
    df["Días Restantes Ajustado"] = (
        df["CodVendedor"].map(dias_restantes_ajustado_map).fillna(0).astype("Int64")
    )
    df["Días Restantes"] = df["Días Restantes Ajustado"]

    return df


def _calcular_proyecciones_y_tendencias_gross(
    matriz_comercial: pd.DataFrame,
) -> pd.DataFrame:
    """
    BUSINESS_RULES: Calcula de manera centralizada el Promedio Diario Gross, la Tendencia Total (Gross_Proyectado_Arg),
    el Cumplimiento Proyectado en Porcentaje y la Media Necesaria Diaria para ambos escenarios (TODO y AJUSTADO).
    """
    df = matriz_comercial.copy()
    if df.empty:
        for suf in ["_TODO", "_AJUSTADO", ""]:
            df[f"Promedio_Diario{suf}"] = 0.0
            df[f"Gross_Proyectado_Arg{suf}"] = 0.0
            df[f"Cumplimiento_Gross_Proy_Pct{suf}"] = 0.0
            df[f"Media_Necesaria_Diaria{suf}"] = 0.0
        return df

    dp_s = (
        df["Días Pasados"]
        if "Días Pasados" in df.columns
        else pd.Series(0, index=df.index)
    )
    dp_s = dp_s.astype(float).replace(0, 1.0)

    actual_val = (
        df["Actual"] if "Actual" in df.columns else pd.Series(0.0, index=df.index)
    )
    ajuste_act_val = (
        df["Ajuste_Reemp_Actual"]
        if "Ajuste_Reemp_Actual" in df.columns
        else pd.Series(0.0, index=df.index)
    )
    operativo_val = (
        df["OPERATIVO"] if "OPERATIVO" in df.columns else pd.Series(0.0, index=df.index)
    )
    objetivo_val = (
        df["Objetivo_Importe_Arg"]
        if "Objetivo_Importe_Arg" in df.columns
        else pd.Series(0.0, index=df.index)
    )

    p_diario = (actual_val + ajuste_act_val) / dp_s

    # Escenario TODO (Usa Días Restantes Todo)
    dr_todo = (
        df["Días Restantes Todo"]
        if "Días Restantes Todo" in df.columns
        else pd.Series(0, index=df.index)
    )
    dr_todo = dr_todo.astype(float)
    tend_todo = operativo_val.copy()
    mask_todo = dr_todo > 0
    if mask_todo.any():
        tend_todo.loc[mask_todo] = (
            p_diario[mask_todo] * dr_todo[mask_todo]
        ) + operativo_val.loc[mask_todo]

    media_nec_todo = pd.Series(0.0, index=df.index)
    if mask_todo.any():
        media_nec_todo.loc[mask_todo] = (
            (objetivo_val.loc[mask_todo] - operativo_val.loc[mask_todo])
            / dr_todo[mask_todo]
        ).clip(lower=0)

    df["Promedio_Diario_TODO"] = p_diario
    df["Gross_Proyectado_Arg_TODO"] = tend_todo
    df["Cumplimiento_Gross_Proy_Pct_TODO"] = (
        (tend_todo / objetivo_val.replace(0, pd.NA)).mul(100).fillna(0.0)
    )
    df["Media_Necesaria_Diaria_TODO"] = media_nec_todo

    # Escenario AJUSTADO (Usa Días Restantes Ajustado)
    dr_ajust = (
        df["Días Restantes Ajustado"]
        if "Días Restantes Ajustado" in df.columns
        else dr_todo
    )
    dr_ajust = dr_ajust.astype(float)
    tend_ajust = operativo_val.copy()
    mask_ajust = dr_ajust > 0
    if mask_ajust.any():
        tend_ajust.loc[mask_ajust] = (
            p_diario[mask_ajust] * dr_ajust[mask_ajust]
        ) + operativo_val.loc[mask_ajust]

    media_nec_ajust = pd.Series(0.0, index=df.index)
    if mask_ajust.any():
        media_nec_ajust.loc[mask_ajust] = (
            (objetivo_val.loc[mask_ajust] - operativo_val.loc[mask_ajust])
            / dr_ajust[mask_ajust]
        ).clip(lower=0)

    df["Promedio_Diario_AJUSTADO"] = p_diario
    df["Gross_Proyectado_Arg_AJUSTADO"] = tend_ajust
    df["Cumplimiento_Gross_Proy_Pct_AJUSTADO"] = (
        (tend_ajust / objetivo_val.replace(0, pd.NA)).mul(100).fillna(0.0)
    )
    df["Media_Necesaria_Diaria_AJUSTADO"] = media_nec_ajust

    # Columnas por defecto (AJUSTADO como principal)
    df["Promedio_Diario"] = df["Promedio_Diario_AJUSTADO"]
    df["Gross_Proyectado_Arg"] = df["Gross_Proyectado_Arg_AJUSTADO"]
    df["Cumplimiento_Gross_Proy_Pct"] = df["Cumplimiento_Gross_Proy_Pct_AJUSTADO"]
    df["Media_Necesaria_Diaria"] = df["Media_Necesaria_Diaria_AJUSTADO"]

    return df


def _incorporar_ventas_temporales_soporte_gross(
    matriz_comercial: pd.DataFrame, df_vta_operativa: pd.DataFrame, dia_matinal: str
) -> pd.DataFrame:
    """
    BUSINESS_RULES: Extrae y adjunta los valores monetarios (Gross) de la última y penúltima semana a partir
    del histórico operativo bruto para trazabilidad analítica de soporte.
    """
    df = matriz_comercial.copy()
    if df.empty or df_vta_operativa is None or df_vta_operativa.empty:
        df["Ultima_Vta"] = 0.0
        df["Penultima_Vta"] = 0.0
        return df

    from modules.utils import parsear_fecha_robusta

    fecha_mat_dt = parsear_fecha_robusta(pd.Series([dia_matinal])).iloc[0]
    if pd.notna(fecha_mat_dt):
        f_ult = (fecha_mat_dt - pd.Timedelta(days=7)).date()
        f_penult = (fecha_mat_dt - pd.Timedelta(days=14)).date()

        u_vta = (
            df_vta_operativa[df_vta_operativa["FechaCarga_dt"].dt.date.eq(f_ult)]
            .groupby(["CodVendedor", "SEGMENTO"])["ImporteNetoItem"]
            .sum()
            .reset_index()
            .rename(columns={"ImporteNetoItem": "Ultima_Vta"})
        )
        p_vta = (
            df_vta_operativa[df_vta_operativa["FechaCarga_dt"].dt.date.eq(f_penult)]
            .groupby(["CodVendedor", "SEGMENTO"])["ImporteNetoItem"]
            .sum()
            .reset_index()
            .rename(columns={"ImporteNetoItem": "Penultima_Vta"})
        )
    else:
        u_vta = pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Ultima_Vta"])
        p_vta = pd.DataFrame(columns=["CodVendedor", "SEGMENTO", "Penultima_Vta"])

    if not u_vta.empty:
        u_vta["CodVendedor"] = pd.to_numeric(
            u_vta["CodVendedor"], errors="coerce"
        ).astype("Int64")
        df = df.merge(u_vta, on=["CodVendedor", "SEGMENTO"], how="left")
    else:
        df["Ultima_Vta"] = 0.0

    if not p_vta.empty:
        p_vta["CodVendedor"] = pd.to_numeric(
            p_vta["CodVendedor"], errors="coerce"
        ).astype("Int64")
        df = df.merge(p_vta, on=["CodVendedor", "SEGMENTO"], how="left")
    else:
        df["Penultima_Vta"] = 0.0

    df["Ultima_Vta"] = (
        df["Ultima_Vta"].fillna(0.0) if "Ultima_Vta" in df.columns else 0.0
    )
    df["Penultima_Vta"] = (
        df["Penultima_Vta"].fillna(0.0) if "Penultima_Vta" in df.columns else 0.0
    )

    return df


@st.cache_data(show_spinner=False)
def obtener_matriz_gross_comercial(
    anio: int, mes: int, filtros_globales: dict
) -> pd.DataFrame:
    """
    BUSINESS_RULES (Orquestador Comercial de Gross): Consume servicios de la Capa CORE y Staging,
    construyendo la matriz comercial completa para la dimensión monetaria (Gross) con equivalencia estricta a Kilos.
    """
    t0 = time.perf_counter()
    padron_vend = obtener_core_vendedores()
    if padron_vend.empty:
        print(
            f"[PERF_CORE] obtener_matriz_gross_comercial (padrón vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    sup_map = padron_vend.set_index("CodVendedor")["SUP"].to_dict()

    dia_matinal = (
        filtros_globales.get("dia_matinal", "02/09/2026")
        if filtros_globales
        else "02/09/2026"
    )
    dia_venta = (
        filtros_globales.get("dia_venta", "01/09/2026")
        if filtros_globales
        else "01/09/2026"
    )

    datos_operativos = obtener_core_operacion(
        anio, mes, dia_matinal, dia_venta, modo_ajuste="AJUSTADO"
    )
    df_vta_op_bruto = datos_operativos["df_vta_operativa"]
    dias_pasados_map = datos_operativos["dias_pasados_map"]
    dias_restantes_map = datos_operativos["dias_restantes_map"]

    rutas_totales_map = datos_operativos.get("rutas_totales_map", dias_restantes_map)
    dias_restantes_todo_map = datos_operativos.get(
        "dias_restantes_todo_map", dias_restantes_map
    )
    dias_restantes_ajustado_map = datos_operativos.get(
        "dias_restantes_ajustado_map", dias_restantes_map
    )

    if df_vta_op_bruto.empty:
        print(
            f"[PERF_CORE] obtener_matriz_gross_comercial (vta_op vacía) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    # APLICACIÓN DE LA REGLA INSTITUCIONAL DE PORTAFOLIO (PEPSICO Y SIN COMODATOS)
    df_vta_op = _filtrar_universo_comercial_gross(df_vta_op_bruto)

    if df_vta_op.empty:
        print(
            f"[PERF_CORE] obtener_matriz_gross_comercial (vta_op vacía tras filtrado de portafolio) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    # Asegurar segmentación comercial sobre los datos operativos (Incluye la creación obligatoria de SEGMENTO)
    df_vta_op = _asegurar_segmento_comercial(df_vta_op)

    # Creación de CodVendedorHistorico antes de cualquier mutación a vigente
    if "CodVendedor" in df_vta_op.columns:
        df_vta_op["CodVendedorHistorico"] = pd.to_numeric(
            df_vta_op["CodVendedor"], errors="coerce"
        ).astype("Int64")

    # Alineación de titularidad comercial con CodVendedorVigente
    codigos_validos = set(padron_vend["CodVendedor"].dropna().tolist())
    if "CodVendedorVigente" in df_vta_op.columns:
        cod_vig = pd.to_numeric(df_vta_op["CodVendedorVigente"], errors="coerce")
        cod_tit_orig = pd.to_numeric(df_vta_op["CodVendedor"], errors="coerce")
        df_vta_op["CodVendedor"] = np.where(
            cod_vig.isin(codigos_validos).fillna(False), cod_vig, cod_tit_orig
        )
        df_vta_op["CodVendedor"] = pd.Series(df_vta_op["CodVendedor"]).astype("Int64")

    # Filtrado por período comercial operativo (Arrastre y Actual)
    df_periodo = df_vta_op[
        df_vta_op["Periodo"].isin(["Arrastre", "Actual"])
        & df_vta_op["SEGMENTO"].notna()
    ].copy()
    if df_periodo.empty:
        print(
            f"[PERF_CORE] obtener_matriz_gross_comercial (periodo vacío) -> {time.perf_counter() - t0:.4f} s"
        )
        return pd.DataFrame()

    # Mapeo de titularidad operativa con soporte para comodines especiales (99)
    cod_op = df_periodo["CodVendedorOperativo"]
    cod_tit = df_periodo["CodVendedor"]
    reemp = df_periodo.get("Reemplazo", pd.Series(pd.NA, index=df_periodo.index))

    is_special = ((reemp == 99) | (cod_op == 99) | (cod_tit == 99)).fillna(False)
    valid_op_mask = cod_op.isin(codigos_validos).fillna(False)
    valid_tit_mask = cod_tit.isin(codigos_validos).fillna(False)

    df_periodo["CodVend_Op"] = np.select(
        [is_special, valid_op_mask, valid_tit_mask],
        [99, cod_op.fillna(-999).astype(int), cod_tit.fillna(-999).astype(int)],
        default=cod_tit.fillna(-999).astype(int),
    )
    df_periodo["CodVend_Op"] = (
        pd.Series(df_periodo["CodVend_Op"]).replace(-999, pd.NA).astype("Int64")
    )
    df_periodo["SEGMENTO"] = df_periodo["SEGMENTO"].astype(str).str.strip()

    # Agregación monetaria por vendedor vigente y segmento
    gross_agrup = (
        df_periodo.groupby(["CodVendedor", "SEGMENTO", "Periodo"], dropna=False)[
            "ImporteNetoItem"
        ]
        .sum()
        .reset_index()
    )

    gross_pivot = gross_agrup.pivot_table(
        index=["CodVendedor", "SEGMENTO"],
        columns="Periodo",
        values="ImporteNetoItem",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()
    gross_pivot.columns.name = None

    for p in ["Arrastre", "Actual"]:
        if p not in gross_pivot.columns:
            gross_pivot[p] = 0.0

    # Construcción de matriz base cruzando padrón y segmentos
    orden_segmentos = [
        "GOLD Salty",
        "GOLD Crakers",
        "SILVER Salty",
        "SILVER Crakers",
        "SILVER Cereals",
    ]
    segs_vta = df_periodo["SEGMENTO"].dropna().unique()
    for s in segs_vta:
        if s not in orden_segmentos:
            orden_segmentos.append(s)

    df_comodin = pd.DataFrame(
        {
            "CodVendedor": pd.Series([99], dtype="Int64"),
            "Nombre": ["REEMPLAZO"],
            "SUP": ["GENERAL"],
        }
    )
    padron_full = pd.concat([padron_vend, df_comodin], ignore_index=True)

    padron_full["_k"] = 1
    segmentos_df = pd.DataFrame({"SEGMENTO": orden_segmentos})
    segmentos_df["_k"] = 1
    matriz_base = padron_full.merge(segmentos_df, on="_k").drop(columns="_k")

    # Integración de transacciones
    matriz_comercial = matriz_base.merge(
        gross_pivot[["CodVendedor", "SEGMENTO", "Arrastre", "Actual"]],
        on=["CodVendedor", "SEGMENTO"],
        how="left",
    )
    matriz_comercial[["Arrastre", "Actual"]] = matriz_comercial[
        ["Arrastre", "Actual"]
    ].fillna(0.0)

    # Integración de Objetivos Comerciales de Gross (vía distribución proporcional por marca y segmento)
    df_objetivos = calcular_objetivos_comerciales_gross(anio, mes, df_vta_op)
    if not df_objetivos.empty:
        matriz_comercial = matriz_comercial.merge(
            df_objetivos, on=["CodVendedor", "SEGMENTO"], how="left"
        )
    if "Objetivo_Importe_Arg" in matriz_comercial.columns:
        matriz_comercial["Objetivo_Importe_Arg"] = matriz_comercial[
            "Objetivo_Importe_Arg"
        ].fillna(0.0)
    else:
        matriz_comercial["Objetivo_Importe_Arg"] = 0.0

    # Integración de Compensaciones por Reemplazo para Gross
    df_compensaciones = calcular_compensaciones_reemplazos_gross(df_vta_op)
    if not df_compensaciones.empty:
        matriz_comercial = matriz_comercial.merge(
            df_compensaciones, on=["CodVendedor", "SEGMENTO"], how="left"
        )

    # Asignación defensiva segura evitando AttributeError en columnas ausentes
    for col_c in ["Ajuste_Reemp_Arrastre", "Ajuste_Reemp_Actual", "Ajuste_Por_Reemp"]:
        if col_c in matriz_comercial.columns:
            matriz_comercial[col_c] = matriz_comercial[col_c].fillna(0.0)
        else:
            matriz_comercial[col_c] = 0.0

    # Cálculo del Neto Operativo Gross
    matriz_comercial["OPERATIVO"] = (
        matriz_comercial["Arrastre"]
        + matriz_comercial["Actual"]
        + matriz_comercial["Ajuste_Por_Reemp"]
    )
    matriz_comercial["Importe_Operativo_Arg"] = matriz_comercial["OPERATIVO"]

    # Incorporación de Parámetros Logísticos y Calendario
    matriz_comercial = _calcular_calendario_ajustado_comercial(
        matriz_comercial,
        padron_vend,
        dias_pasados_map,
        rutas_totales_map,
        dias_restantes_todo_map,
        dias_restantes_ajustado_map,
    )

    # Incorporación de Métricas Analíticas de Proyección y Tendencia Gross
    matriz_comercial = _calcular_proyecciones_y_tendencias_gross(matriz_comercial)

    # Incorporación de Ventas Temporales de Soporte Gross
    matriz_comercial = _incorporar_ventas_temporales_soporte_gross(
        matriz_comercial, df_vta_op, dia_matinal
    )

    # Gross Futuro completo: STAGING sin corte de Dia Matinal.
    fut_agg = _obtener_futuro_completo_gross(anio, mes, padron_vend)
    if not fut_agg.empty:
        matriz_comercial = matriz_comercial.merge(
            fut_agg, on=["CodVendedor", "SEGMENTO"], how="left"
        )
    matriz_comercial["Gross_Disponible"] = matriz_comercial.get(
        "Gross_Disponible", pd.Series(0.0, index=matriz_comercial.index)
    ).fillna(0.0)
    matriz_comercial["Gross_Futuro"] = matriz_comercial["Gross_Disponible"]
    matriz_comercial["Gross_Pendiente"] = (
        matriz_comercial["Objetivo_Importe_Arg"]
        - matriz_comercial["Importe_Operativo_Arg"]
    ).clip(lower=0.0)
    matriz_comercial["Gross_Futuro_Necesario"] = np.minimum(
        matriz_comercial["Gross_Futuro"], matriz_comercial["Gross_Pendiente"]
    )
    matriz_comercial["Gross_Gap_Post_Futuro"] = (
        matriz_comercial["Gross_Pendiente"] - matriz_comercial["Gross_Futuro"]
    ).clip(lower=0.0)
    matriz_comercial["Cobertura_Gap_Futuro_Gross_Pct"] = (
        matriz_comercial["Gross_Futuro"]
        .div(matriz_comercial["Gross_Pendiente"].replace(0, pd.NA))
        .clip(upper=1.0)
        .mul(100)
        .fillna(0.0)
    )

    # Cálculo histórico de Futuro_A_Incorporar_Gross (compatibilidad)
    matriz_comercial["Raw_Bache_Gross"] = (
        matriz_comercial["Objetivo_Importe_Arg"]
        - matriz_comercial["Gross_Proyectado_Arg"]
    ).clip(lower=0)

    tot_obj_g = float(matriz_comercial["Objetivo_Importe_Arg"].sum())
    tot_proy_g = float(matriz_comercial["Gross_Proyectado_Arg"].sum())
    global_gap_g = max(0.0, tot_obj_g - tot_proy_g)
    sum_baches_g = matriz_comercial["Raw_Bache_Gross"].sum()
    factor_g = (global_gap_g / sum_baches_g) if sum_baches_g > 0 else 0.0

    matriz_comercial["Futuro_A_Incorporar_Gross"] = (
        matriz_comercial["Raw_Bache_Gross"] * factor_g
    ).round(2)

    # Ordenamiento institucional por supervisor, preventista y segmento
    mapping_orden = {str(seg).strip(): i for i, seg in enumerate(orden_segmentos)}
    matriz_comercial["_orden_idx"] = (
        matriz_comercial["SEGMENTO"]
        .astype(str)
        .str.strip()
        .map(mapping_orden)
        .fillna(999)
    )
    matriz_comercial = (
        matriz_comercial.sort_values(by=["SUP", "Nombre", "_orden_idx"])
        .drop(columns=["_orden_idx"])
        .reset_index(drop=True)
    )

    columnas_salida = [
        "CodVendedor",
        "Nombre",
        "SUP",
        "SEGMENTO",
        "Objetivo_Importe_Arg",
        "Arrastre",
        "Actual",
        "Ultima_Vta",
        "Penultima_Vta",
        "Importe_Operativo_Arg",
        "Ajuste_Reemp_Arrastre",
        "Ajuste_Reemp_Actual",
        "Ajuste_Por_Reemp",
        "Gross_Proyectado_Arg",
        "Gross_Proyectado_Arg_TODO",
        "Gross_Proyectado_Arg_AJUSTADO",
        "Cumplimiento_Gross_Proy_Pct",
        "Cumplimiento_Gross_Proy_Pct_TODO",
        "Cumplimiento_Gross_Proy_Pct_AJUSTADO",
        "Promedio_Diario",
        "Promedio_Diario_TODO",
        "Promedio_Diario_AJUSTADO",
        "Media_Necesaria_Diaria",
        "Media_Necesaria_Diaria_TODO",
        "Media_Necesaria_Diaria_AJUSTADO",
        "Gross_Disponible",
        "Gross_Futuro",
        "Gross_Pendiente",
        "Gross_Futuro_Necesario",
        "Gross_Gap_Post_Futuro",
        "Cobertura_Gap_Futuro_Gross_Pct",
        "Futuro_A_Incorporar_Gross",
        "Días Pasados",
        "Rutas",
        "Ajuste_Entrega",
        "Rutas_Ajustadas",
        "Días Restantes",
        "Días Restantes Todo",
        "Días Restantes Ajustado",
    ]

    resultado_final = matriz_comercial[
        [c for c in columnas_salida if c in matriz_comercial.columns]
    ]
    print(
        f"[PERF_CORE] obtener_matriz_gross_comercial -> {time.perf_counter() - t0:.4f} s"
    )
    return resultado_final
