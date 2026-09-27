# modules/logger.py
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Directorio de logs centralizado en la raíz del proyecto
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "matinal.log"

# Configuración global base (Nivel INFO por defecto para producción)
DEFAULT_LOG_LEVEL = logging.INFO
MAX_BYTES = 5 * 1024 * 1024  # 5 MB por archivo de log
BACKUP_COUNT = 5             # Conserva hasta 5 respaldos históricos rotados

def setup_root_logger():
    """Configura y retorna el logger raíz de MATINAL con soporte de rotación y consola."""
    root_logger = logging.getLogger("matinal")
    if root_logger.handlers:
        return root_logger

    root_logger.setLevel(DEFAULT_LOG_LEVEL)

    # Formato estructurado estricto: Timestamp | Nivel | Módulo | Mensaje
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Handler para archivo con rotación automática (evita saturación de disco)
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=MAX_BYTES, 
        backupCount=BACKUP_COUNT, 
        encoding="utf-8"
    )
    file_handler.setLevel(DEFAULT_LOG_LEVEL)
    file_handler.setFormatter(formatter)

    # 2. Handler para salida estándar en consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(DEFAULT_LOG_LEVEL)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    root_logger.info("=== SUBSISTEMA DE LOGGING MATINAL INICIALIZADO CORRECTAMENTE ===")
    return root_logger

def get_logger(module_name: str) -> logging.Logger:
    """
    Retorna un logger hijo bajo la jerarquía 'matinal.<module_name>' 
    respetando la convención de nombres por módulo del proyecto.
    Ejemplo:
        logger = get_logger("database")
    """
    setup_root_logger()
    return logging.getLogger(f"matinal.{module_name}")

def set_debug_mode(enabled: bool = True):
    """
    Permite habilitar dinámicamente el nivel DEBUG para diagnósticos temporales.
    Deshabilitado por defecto en producción.
    """
    root_logger = logging.getLogger("matinal")
    new_level = logging.DEBUG if enabled else DEFAULT_LOG_LEVEL
    root_logger.setLevel(new_level)
    for handler in root_logger.handlers:
        handler.setLevel(new_level)
    
    if enabled:
        root_logger.debug("--- MODO DEBUG ACTIVADO TEMPORALMENTE ---")
    else:
        root_logger.info("--- MODO DEBUG DESACTIVADO (Nivel producción restablecido) ---")