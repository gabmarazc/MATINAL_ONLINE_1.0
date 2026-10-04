import pandas as pd
from modules.core.core_potencial_cliente_segmento import (
    generar_core_potencial_cliente_segmento,
)
from modules.staging import obtener_staging_maestros


def generar_business_rules_objetivos_cliente(
    anio_operativo: int, mes_operativo: int
) -> pd.DataFrame:
    """
    Transforma el potencial de Cliente + Marca + SEGMENTO en ObjetivoClienteKg utilizando
    una distribución jerárquica: Objetivo Marca -> Segmento -> Cliente, apoyada en
    los objetivos corporativos provenientes de los maestros de Staging.

    Arquitectura: BUSINESS RULES (Sistema Matinal 2.0)
    """
    columnas_salida = [
        "Cliente",
        "Marca",
        "SEGMENTO",
        "PotencialKg",
        "PotencialMarcaSegmentoTotal",
        "ParticipacionMarcaSegmento",
        "ParticipacionClienteDentroSegmento",
        "ObjetivoMarcaKg",
        "ObjetivoSegmentoKg",
        "ObjetivoClienteKg",
        "MetodoAsignacion",
    ]

    # 1. Obtener datos de la capa CORE ampliada con SEGMENTO
    df_core = generar_core_potencial_cliente_segmento(anio_operativo, mes_operativo)

    if df_core is None or df_core.empty:
        return pd.DataFrame(columns=columnas_salida)

    # 2. Obtener diccionario de maestros desde Staging y extraer maestro_marcas_cebe de forma segura
    maestros = obtener_staging_maestros()

    if not isinstance(maestros, dict) or "maestro_marcas_cebe" not in maestros:
        df_vacio = df_core[["Cliente", "Marca", "SEGMENTO", "PotencialKg"]].copy()
        df_vacio["PotencialMarcaSegmentoTotal"] = 0.0
        df_vacio["ParticipacionMarcaSegmento"] = 0.0
        df_vacio["ParticipacionClienteDentroSegmento"] = 0.0
        df_vacio["ObjetivoMarcaKg"] = 0.0
        df_vacio["ObjetivoSegmentoKg"] = 0.0
        df_vacio["ObjetivoClienteKg"] = 0.0
        df_vacio["MetodoAsignacion"] = "SIN_MAESTRO_MARCAS"
        return df_vacio[columnas_salida]

    df_maestro = maestros["maestro_marcas_cebe"]

    if df_maestro is None or df_maestro.empty:
        df_vacio = df_core[["Cliente", "Marca", "SEGMENTO", "PotencialKg"]].copy()
        df_vacio["PotencialMarcaSegmentoTotal"] = 0.0
        df_vacio["ParticipacionMarcaSegmento"] = 0.0
        df_vacio["ParticipacionClienteDentroSegmento"] = 0.0
        df_vacio["ObjetivoMarcaKg"] = 0.0
        df_vacio["ObjetivoSegmentoKg"] = 0.0
        df_vacio["ObjetivoClienteKg"] = 0.0
        df_vacio["MetodoAsignacion"] = "SIN_MAESTRO_MARCAS"
        return df_vacio[columnas_salida]

    # Estandarizar nombres de columnas clave para el merge
    df_core["Marca_Upper"] = df_core["Marca"].astype(str).str.upper().str.strip()
    df_maestro["Marca_Upper"] = df_maestro["Marca"].astype(str).str.upper().str.strip()

    # Asignar ObjetivoMarcaKg directamente desde Obj_TN_Mes sin conversión de unidades
    if "Obj_TN_Mes" in df_maestro.columns:
        df_maestro["ObjetivoMarcaKg"] = pd.to_numeric(
            df_maestro["Obj_TN_Mes"], errors="coerce"
        ).fillna(0.0)
    else:
        df_maestro["ObjetivoMarcaKg"] = 0.0

    df_maestro_clean = df_maestro[["Marca_Upper", "ObjetivoMarcaKg"]].drop_duplicates(
        subset=["Marca_Upper"]
    )

    # Cruzar Core con Maestro de Marcas
    df_merged = pd.merge(df_core, df_maestro_clean, on="Marca_Upper", how="left")

    # Si alguna marca del core no está en el maestro, su objetivo corporativo es 0
    df_merged["ObjetivoMarcaKg"] = df_merged["ObjetivoMarcaKg"].fillna(0.0)

    # 3. Calcular Potenciales Totales con manejo defensivo de agregaciones
    df_merged["PotencialKg"] = pd.to_numeric(
        df_merged["PotencialKg"], errors="coerce"
    ).fillna(0.0)

    df_merged["Cliente_Potencial_Total"] = df_merged.groupby("Cliente")[
        "PotencialKg"
    ].transform("sum")
    df_merged["PotencialMarcaSegmentoTotal"] = df_merged.groupby(
        ["Marca_Upper", "SEGMENTO"]
    )["PotencialKg"].transform("sum")
    df_merged["PotencialMarcaGlobal"] = df_merged.groupby("Marca_Upper")[
        "PotencialKg"
    ].transform("sum")

    # 4. Inicializar columnas de cálculo y salida
    df_merged["ParticipacionMarcaSegmento"] = 0.0
    df_merged["ParticipacionClienteDentroSegmento"] = 0.0
    df_merged["ObjetivoSegmentoKg"] = 0.0
    df_merged["ObjetivoClienteKg"] = 0.0
    df_merged["MetodoAsignacion"] = "JERARQUICO_MARCA_SEGMENTO_CLIENTE"

    # 5. Aplicación de reglas defensivas y de negocio especiales

    # CASO A: Cliente sin historia (PotencialKg total del cliente == 0)
    mask_cliente_sin_historia = df_merged["Cliente_Potencial_Total"] == 0.0
    df_merged.loc[mask_cliente_sin_historia, "MetodoAsignacion"] = (
        "CLIENTE_SIN_HISTORIA"
    )

    # CASO B: Validación defensiva y cálculo con PotencialMarcaGlobal > 0 y sin ser cliente sin historia
    mask_marca_global_valida = (df_merged["PotencialMarcaGlobal"] > 0.0) & (
        ~mask_cliente_sin_historia
    )
    df_merged.loc[mask_marca_global_valida, "ParticipacionMarcaSegmento"] = (
        df_merged.loc[mask_marca_global_valida, "PotencialMarcaSegmentoTotal"]
        / df_merged.loc[mask_marca_global_valida, "PotencialMarcaGlobal"]
    )

    # CASO C: Validación defensiva y cálculo con PotencialMarcaSegmentoTotal > 0 y sin ser cliente sin historia
    mask_marca_seg_valida = (df_merged["PotencialMarcaSegmentoTotal"] > 0.0) & (
        ~mask_cliente_sin_historia
    )
    df_merged.loc[mask_marca_seg_valida, "ParticipacionClienteDentroSegmento"] = (
        df_merged.loc[mask_marca_seg_valida, "PotencialKg"]
        / df_merged.loc[mask_marca_seg_valida, "PotencialMarcaSegmentoTotal"]
    )

    # 6. Distribución jerárquica segura de objetivos
    df_merged["ObjetivoSegmentoKg"] = (
        df_merged["ObjetivoMarcaKg"] * df_merged["ParticipacionMarcaSegmento"]
    )

    df_merged["ObjetivoClienteKg"] = (
        df_merged["ObjetivoSegmentoKg"]
        * df_merged["ParticipacionClienteDentroSegmento"]
    )

    # Forzar ceros en clientes sin historia explícitamente
    df_merged.loc[mask_cliente_sin_historia, "ObjetivoClienteKg"] = 0.0

    df_merged["ObjetivoClienteKg"] = pd.to_numeric(
        df_merged["ObjetivoClienteKg"], errors="coerce"
    ).fillna(0.0)

    # 7. Validación de integridad estricta (SUM ObjetivoMarcaKg únicos vs SUM ObjetivoClienteKg)
    suma_entrada = df_merged.drop_duplicates(subset=["Marca_Upper"])[
        "ObjetivoMarcaKg"
    ].sum()
    suma_salida = df_merged["ObjetivoClienteKg"].sum()

    assert abs(suma_entrada - suma_salida) < 1.0, (
        f"Error de integridad: La suma de objetivos de marca ({suma_entrada}) no coincide con la suma asignada a clientes ({suma_salida})."
    )

    resultado = df_merged[columnas_salida].copy()

    return resultado
