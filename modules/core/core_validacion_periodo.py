# modules/core/core_validacion_periodo.py

import pandas as pd

from modules.parametros import (
    obtener_maestro_vendedores_sql,
    obtener_maestro_segmentos_sql,
    obtener_maestro_marcas_cebe_sql,
    obtener_maestro_ccc_sql,
    obtener_maestro_innovaciones_sql,
    obtener_objetivos_vendedores_sql,
)


def _validar_dataframe(df: pd.DataFrame) -> bool:
    """
    Determina si una tabla contiene información válida.
    """

    return df is not None and isinstance(df, pd.DataFrame) and not df.empty


def validar_integridad_periodo_operativo(anio: int | str, mes: int | str) -> dict:
    """
    Valida que todas las bases mensuales obligatorias
    existan para el período operativo seleccionado.

    Retorna un diccionario único de estado.
    """

    estado = {}

    estado["Maestro Vendedores"] = _validar_dataframe(
        obtener_maestro_vendedores_sql(anio, mes)
    )

    estado["Maestro Segmentos"] = _validar_dataframe(
        obtener_maestro_segmentos_sql(anio, mes)
    )

    estado["Maestro Marcas CEBE"] = _validar_dataframe(
        obtener_maestro_marcas_cebe_sql(anio, mes)
    )

    estado["Maestro CCC"] = _validar_dataframe(obtener_maestro_ccc_sql(anio, mes))

    estado["Maestro Innovaciones"] = _validar_dataframe(
        obtener_maestro_innovaciones_sql(anio, mes)
    )

    estado["Objetivos Calibrados"] = _validar_dataframe(
        obtener_objetivos_vendedores_sql(anio, mes)
    )

    faltantes = [nombre for nombre, existe in estado.items() if not existe]

    return {
        "completo": len(faltantes) == 0,
        "bases_ok": len(estado) - len(faltantes),
        "bases_total": len(estado),
        "estado": estado,
        "faltantes": faltantes,
        "anio": str(anio),
        "mes": str(mes).zfill(2),
    }
