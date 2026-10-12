# -*- coding: utf-8 -*-
"""
Módulo centralizado de Feature Flags para el Sistema MATINAL 2.0.
Permite activar o desactivar módulos completos en desarrollo con costo computacional cero.

Ejemplos de uso:
    >>> from modules.feature_flags import is_enabled, ff, set_feature, enable_module, disable_module
    >>>
    >>> # Evaluar feature (lanza KeyError si no existe)
    >>> if is_enabled("GERENCIAL_UI"):
    ...     # Renderizar pestaña gerencial
    ...     pass
    >>>
    >>> # Activar un módulo completo (activa tanto *_UI como *_ENGINE)
    >>> enable_module("GERENCIAL")
    >>>
    >>> # Desactivar un módulo completo
    >>> disable_module("GERENCIAL")
    >>>
    >>> # Modificar una flag específica
    >>> set_feature("TP_CORE", False)
"""

from typing import List

# Diccionario oficial de gobernanza de features con doble control (UI / ENGINE)
FEATURE_FLAGS = {
    "GERENCIAL_UI": False,
    "GERENCIAL_ENGINE": False,
    "VESPERTINA_UI": False,
    "VESPERTINA_ENGINE": False,
    "COB_MARCA_UI": False,
    "COB_MARCA_ENGINE": False,
    "COB_INNOV_UI": False,
    "COB_INNOV_ENGINE": False,
    "TP_CORE": True,
    "CCC_CORE": True,
    "MN_CORE": True,
    "KILOS_CORE": True,
    "KILOS_LEGACY_UI": False,
    "KILOS_LEGACY_ENGINE": False,
    "CCC_LEGACY_UI": False,
    "CCC_LEGACY_ENGINE": False,
    "MN_LEGACY_UI": False,
    "MN_LEGACY_ENGINE": False,
    "TP_LEGACY_UI": False,
    "TP_LEGACY_ENGINE": False,
    "OBJ_KILOS_LEGACY_UI": False,
    "OBJ_KILOS_LEGACY_ENGINE": False,
}

# Listado oficial de módulos experimentales para operaciones masivas
EXPERIMENTAL_MODULES = ["GERENCIAL", "VESPERTINA", "COB_MARCA", "COB_INNOV"]

# Estructura interna para garantizar que el log [FEATURE_OFF] se emita una sola vez por estado inactivo
_LOGGED_OFF = set()


def is_enabled(nombre: str) -> bool:
    """
    Evalúa si una feature se encuentra habilitada.
    Lanza KeyError si la feature no existe en el diccionario oficial (detección de errores tipográficos).
    Si está apagada, emite el log obligatorio en consola con formato [FEATURE_OFF] una sola vez por ciclo de inactividad.
    """
    if nombre not in FEATURE_FLAGS:
        raise KeyError(f"La feature flag '{nombre}' no está definida en FEATURE_FLAGS.")

    estado = FEATURE_FLAGS[nombre]
    if not estado:
        if nombre not in _LOGGED_OFF:
            print(f"[FEATURE_OFF] {nombre}")
            _LOGGED_OFF.add(nombre)
    return estado


def ff(nombre: str) -> bool:
    """
    Alias corto para is_enabled(nombre).
    """
    return is_enabled(nombre)


def get_enabled_modules() -> List[str]:
    """
    Retorna la lista de nombres de features actualmente habilitadas.
    """
    return [nombre for nombre, activo in FEATURE_FLAGS.items() if activo]


def set_feature(nombre: str, estado: bool) -> None:
    """
    Establece de forma explícita el estado de una feature flag.
    Si la flag se activa, se limpia del registro _LOGGED_OFF para permitir futuras advertencias si se apaga de nuevo.
    Lanza KeyError si la feature no existe.
    """
    if nombre not in FEATURE_FLAGS:
        raise KeyError(f"La feature flag '{nombre}' no está definida en FEATURE_FLAGS.")

    FEATURE_FLAGS[nombre] = bool(estado)
    if estado and nombre in _LOGGED_OFF:
        _LOGGED_OFF.remove(nombre)


def enable_feature(nombre: str) -> None:
    """
    Activa una feature específica.
    """
    set_feature(nombre, True)


def disable_feature(nombre: str) -> None:
    """
    Desactiva una feature específica.
    """
    set_feature(nombre, False)


def enable_module(modulo: str) -> None:
    """
    Activa un módulo completo controlando estrictamente ambas dimensiones (_UI y _ENGINE).
    Ejemplo: enable_module("GERENCIAL") activa "GERENCIAL_UI" y "GERENCIAL_ENGINE".
    Lanza KeyError si el módulo no posee las claves correspondientes.
    """
    ui_key = f"{modulo}_UI"
    engine_key = f"{modulo}_ENGINE"

    encontrado = False
    if ui_key in FEATURE_FLAGS:
        set_feature(ui_key, True)
        encontrado = True
    if engine_key in FEATURE_FLAGS:
        set_feature(engine_key, True)
        encontrado = True

    if not encontrado:
        raise KeyError(
            f"El módulo '{modulo}' no posee las claves esperadas '{ui_key}' / '{engine_key}'."
        )


def disable_module(modulo: str) -> None:
    """
    Desactiva un módulo completo controlando estrictamente ambas dimensiones (_UI y _ENGINE).
    Ejemplo: disable_module("GERENCIAL") desactiva "GERENCIAL_UI" y "GERENCIAL_ENGINE".
    Lanza KeyError si el módulo no posee las claves correspondientes.
    """
    ui_key = f"{modulo}_UI"
    engine_key = f"{modulo}_ENGINE"

    encontrado = False
    if ui_key in FEATURE_FLAGS:
        set_feature(ui_key, False)
        encontrado = True
    if engine_key in FEATURE_FLAGS:
        set_feature(engine_key, False)
        encontrado = True

    if not encontrado:
        raise KeyError(
            f"El módulo '{modulo}' no posee las claves esperadas '{ui_key}' / '{engine_key}'."
        )
