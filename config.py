# config.py
import os

# Directorio raíz del proyecto y directorio de datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Rutas completas a los archivos dentro de la carpeta /data
ARCHIVO_VTA_EXCEL = os.path.join(DATA_DIR, "VTA.xlsx")
ARCHIVO_VTA_PARQUET = os.path.join(DATA_DIR, "VTA.parquet")
ARCHIVO_UNIVERSO = os.path.join(DATA_DIR, "UNIVERSO.xlsx")
ARCHIVO_PARAMETROS = os.path.join(DATA_DIR, "PARAMETROS.xlsx")
ARCHIVO_RUTAS = os.path.join(DATA_DIR, "RUTAS.xlsx")

# Mantener compatibilidad por variable genérica si algún módulo usa ARCHIVO_VTA
ARCHIVO_VTA = ARCHIVO_VTA_PARQUET if os.path.exists(ARCHIVO_VTA_PARQUET) else ARCHIVO_VTA_EXCEL

# URL Google Sheets Ausencias
URL_AUSENCIAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTt1sbO_3jsIldtNBos3vFN3kKQ68y1lcF1qUy5MfzFzNez0VSli0WGkjC_BG6UaHPYmg1aP9eJPiKk/pub?output=csv"

# Definición de columnas matriciales
COLUMNAS_BASE_EXTVTA = [
    "Cliente", "FechaEntrega", "FechaCarga", "TipoDeVenta", "Codigo",
    "CantBase", "ImporteNetoItem", "ImporteItem", "PrecioCosto",
    "MotivoDevolucion", "CodVendedor", "Articulo", "Reparto", "Subramo",
    "Proveedor", "PesoKg", "Marca", "Rubro", "Tags",
    "SegmentoRentabilidad", "Origen", "Taxonomia",
]

COLUMNAS_FINALES_EXTVTA = [
    "Cliente", "FechaEntrega", "FechaCarga", "TipoDeVenta", "Codigo",
    "CantBase", "ImporteNetoItem", "ImporteItem", "PrecioCosto",
    "MotivoDevolucion", "CodVendedor", "CodVendedorOperativo", "Articulo",
    "Reparto", "Subramo", "Proveedor", "PesoKg", "Marca", "Rubro", "Tags",
    "SegmentoRentabilidad", "SEGMENTO", "Origen", "Taxonomia",
    "MesCarga", "AñoCarga", "MesEntrega", "AñoEntrega", "Periodo",
]