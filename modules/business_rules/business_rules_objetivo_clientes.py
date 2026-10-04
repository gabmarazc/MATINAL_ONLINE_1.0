import pandas as pd
from modules.core.core_potencial_cliente import generar_core_potencial_cliente
from modules.staging import obtener_staging_maestros


def generar_business_rules_objetivos_cliente(
    anio_operativo: int, mes_operativo: int
) -> pd.DataFrame:
    """
    Transforma el potencial de Cliente + Marca en ObjetivoClienteKg utilizando
    los objetivos corporativos provenientes de los maestros de Staging.

    Arquitectura: BUSINESS RULES (Sistema Matinal 2.0)
    """
    columnas_salida = [
        "Cliente",
        "Marca",
        "PotencialKg",
        "PotencialMarcaTotal",
        "ParticipacionPotencialPct",
        "ObjetivoMarcaKg",
        "ObjetivoClienteKg",
        "MetodoAsignacion",
    ]

    # 1. Obtener datos de la capa CORE
    df_core = generar_core_potencial_cliente(anio_operativo, mes_operativo)

    if df_core is None or df_core.empty:
        return pd.DataFrame(columns=columnas_salida)

    # 2. Obtener diccionario de maestros desde Staging y extraer maestro_marcas_cebe de forma segura
    maestros = obtener_staging_maestros()

    if not isinstance(maestros, dict) or "maestro_marcas_cebe" not in maestros:
        df_vacio = df_core[["Cliente", "Marca", "PotencialKg"]].copy()
        df_vacio["PotencialMarcaTotal"] = 0.0
        df_vacio["ParticipacionPotencialPct"] = 0.0
        df_vacio["ObjetivoMarcaKg"] = 0.0
        df_vacio["ObjetivoClienteKg"] = 0.0
        df_vacio["MetodoAsignacion"] = "SIN_MAESTRO_MARCAS"
        return df_vacio[columnas_salida]

    df_maestro = maestros["maestro_marcas_cebe"]

    if df_maestro is None or df_maestro.empty:
        df_vacio = df_core[["Cliente", "Marca", "PotencialKg"]].copy()
        df_vacio["PotencialMarcaTotal"] = 0.0
        df_vacio["ParticipacionPotencialPct"] = 0.0
        df_vacio["ObjetivoMarcaKg"] = 0.0
        df_vacio["ObjetivoClienteKg"] = 0.0
        df_vacio["MetodoAsignacion"] = "SIN_MAESTRO_MARCAS"
        return df_vacio[columnas_salida]

    # Estandarizar nombres de columnas clave para el merge
    df_core["Marca_Upper"] = df_core["Marca"].astype(str).str.upper().str.strip()
    df_maestro["Marca_Upper"] = df_maestro["Marca"].astype(str).str.upper().str.strip()

    # Asegurar conversión de Toneladas a Kilogramos (Obj_TN_Mes -> ObjetivoMarcaKg)
    if "Obj_TN_Mes" in df_maestro.columns:
        df_maestro["ObjetivoMarcaKg"] = (
            pd.to_numeric(df_maestro["Obj_TN_Mes"], errors="coerce").fillna(0.0)
            * 1000.0
        )
    else:
        df_maestro["ObjetivoMarcaKg"] = 0.0

    df_maestro_clean = df_maestro[["Marca_Upper", "ObjetivoMarcaKg"]].drop_duplicates(
        subset=["Marca_Upper"]
    )

    # Cruzar Core con Maestro de Marcas
    df_merged = pd.merge(df_core, df_maestro_clean, on="Marca_Upper", how="left")

    # Si alguna marca del core no está en el maestro, su objetivo corporativo es 0
    df_merged["ObjetivoMarcaKg"] = df_merged["ObjetivoMarcaKg"].fillna(0.0)

    # 3. Calcular Potencial Marca Total = SUM(PotencialKg)
    potencial_marca_totales = df_merged.groupby("Marca_Upper")["PotencialKg"].transform(
        "sum"
    )
    df_merged["PotencialMarcaTotal"] = potencial_marca_totales

    # 4. Calcular el potencial total histórico de cada cliente
    potencial_cliente_totales = df_merged.groupby("Cliente")["PotencialKg"].transform(
        "sum"
    )
    df_merged["Cliente_Potencial_Total"] = potencial_cliente_totales

    # 5. Inicializar columnas de salida
    df_merged["ParticipacionPotencialPct"] = 0.0
    df_merged["ObjetivoClienteKg"] = 0.0
    df_merged["MetodoAsignacion"] = "PROPORCIONAL_DIRECTA"

    # 6. Identificar y aplicar reglas especiales

    # CASO A: Cliente sin historia (PotencialKg total del cliente == 0)
    mask_cliente_sin_historia = df_merged["Cliente_Potencial_Total"] == 0.0
    df_merged.loc[mask_cliente_sin_historia, "ParticipacionPotencialPct"] = 0.0
    df_merged.loc[mask_cliente_sin_historia, "ObjetivoClienteKg"] = 0.0
    df_merged.loc[mask_cliente_sin_historia, "MetodoAsignacion"] = (
        "CLIENTE_SIN_HISTORIA"
    )

    # CASO B: Marcas normales (PotencialMarcaTotal > 0) para clientes con historia
    mask_marca_normal = (df_merged["PotencialMarcaTotal"] > 0.0) & (
        ~mask_cliente_sin_historia
    )
    df_merged.loc[mask_marca_normal, "ParticipacionPotencialPct"] = (
        df_merged.loc[mask_marca_normal, "PotencialKg"]
        / df_merged.loc[mask_marca_normal, "PotencialMarcaTotal"]
    )
    df_merged.loc[mask_marca_normal, "ObjetivoClienteKg"] = (
        df_merged.loc[mask_marca_normal, "ParticipacionPotencialPct"]
        * df_merged.loc[mask_marca_normal, "ObjetivoMarcaKg"]
    )
    df_merged.loc[mask_marca_normal, "MetodoAsignacion"] = "PROPORCIONAL_DIRECTA"

    # Calcular participación individual del cliente en cada marca normal para uso transversal en regla C
    df_merged["Participacion_Marca_Temp"] = 0.0
    df_merged.loc[mask_marca_normal, "Participacion_Marca_Temp"] = (
        df_merged.loc[mask_marca_normal, "PotencialKg"]
        / df_merged.loc[mask_marca_normal, "PotencialMarcaTotal"]
    )

    # CASO C: Marca nueva (PotencialMarcaTotal == 0) para clientes con historia
    # Regla: PROMEDIO_PARTICIPACION_CLIENTE (participación histórica promedio ponderada por PotencialKg en el resto de marcas)
    mask_marca_nueva = (df_merged["PotencialMarcaTotal"] == 0.0) & (
        ~mask_cliente_sin_historia
    )

    if mask_marca_nueva.any():
        df_con_historia = df_merged[df_merged["Cliente_Potencial_Total"] > 0.0].copy()
        df_con_historia["Prod_Pot_Part"] = (
            df_con_historia["PotencialKg"] * df_con_historia["Participacion_Marca_Temp"]
        )

        suma_prod = df_con_historia.groupby("Cliente")["Prod_Pot_Part"].sum()
        suma_pot = df_con_historia.groupby("Cliente")["PotencialKg"].sum()

        factor_cliente = (suma_prod / suma_pot).fillna(0.0)

        df_merged["Factor_Cliente_Promedio"] = (
            df_merged["Cliente"].map(factor_cliente).fillna(0.0)
        )

        suma_factores_marca_nueva = df_merged.loc[
            mask_marca_nueva, "Factor_Cliente_Promedio"
        ].sum()

        if suma_factores_marca_nueva > 0:
            df_merged.loc[mask_marca_nueva, "ParticipacionPotencialPct"] = (
                df_merged.loc[mask_marca_nueva, "Factor_Cliente_Promedio"]
                / suma_factores_marca_nueva
            )
        else:
            df_merged.loc[mask_marca_nueva, "ParticipacionPotencialPct"] = 0.0

        df_merged.loc[mask_marca_nueva, "ObjetivoClienteKg"] = (
            df_merged.loc[mask_marca_nueva, "ParticipacionPotencialPct"]
            * df_merged.loc[mask_marca_nueva, "ObjetivoMarcaKg"]
        )
        df_merged.loc[mask_marca_nueva, "MetodoAsignacion"] = (
            "PROMEDIO_PARTICIPACION_CLIENTE"
        )

    # Limpieza final de columnas auxiliares y selección estricta del contrato de salida
    resultado = df_merged[columnas_salida].copy()

    return resultado
