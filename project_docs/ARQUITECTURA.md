# Arquitectura del Sistema MATINAL 2.0
Versión: 2.0
Fecha de actualización: 27/09/2026
Estado: Vigente
Estado de validación: Producción operativa

---

# 1. Propósito del Documento

Este documento constituye la definición oficial de la arquitectura del Sistema MATINAL 2.0.

Su objetivo es preservar el conocimiento arquitectónico del proyecto y permitir la reconstrucción completa del contexto funcional, técnico y evolutivo aun cuando se pierda el historial de conversaciones o se inicie una nueva sesión de desarrollo.

Ante cualquier discrepancia entre documentación y código:

1. Revisar este documento.
2. Revisar DECISIONES_ARQUITECTURALES.md.
3. Revisar ESTADO_ACTUAL_PROYECTO.md.
4. Recién después analizar el código fuente.

---

# 2. Arquitectura Oficial Vigente

La arquitectura institucional aprobada es:

RAW
↓
SQLITE
↓
STAGING
↓
CORE
↓
BUSINESS RULES
↓
REPORTES

Esta arquitectura reemplaza progresivamente el modelo histórico basado en pipelines descentralizados.

---

# 3. Arquitectura Física Actual

## Punto de entrada

app.py

Responsabilidades:

- Inicio del sistema
- Gestión de sesión
- Gestión de autenticación
- Renderizado de pestañas
- Orquestación visual global

---

## Persistencia

Ubicación:

data/matinal.db

Tecnología:

SQLite

Modo:

WAL (Write Ahead Logging)

Características:

- Fuente única de verdad del sistema
- Persistencia local
- Carga desacoplada de Excel
- Alto rendimiento de lectura

---

## Directorio modules/

Contiene:

### Persistencia

database.py

### Configuración

parametros.py

### Utilidades

utils.py

### Reportes

rep_gerencial.py
rep_kilos.py
rep_ccc.py
rep_MN.py
rep_cob_marca.py
rep_cob_innovacion.py
rep_obj_kilos.py
rep_vespertina.py

### Arquitectura institucional

staging.py
core/

---

# 4. Capas Arquitectónicas

## 4.1 RAW

Responsabilidad:

Recepción de información proveniente de archivos externos.

Fuentes principales:

- VTA.xlsx
- UNIVERSO.xlsx
- RUTAS.xlsx
- ALTAS.xlsx
- AUSENCIAS
- Maestros corporativos

Características:

- Datos sin normalizar
- Pueden contener errores
- No son consumidos directamente por reportes

Regla:

No contiene lógica de negocio.

---

## 4.2 SQLITE

Responsabilidad:

Persistir físicamente los datos del sistema.

Objetivos:

- Evitar múltiples lecturas de Excel
- Mejorar rendimiento
- Crear una fuente común de datos

Tablas principales:

- vta
- universo
- rutas
- ausencias
- maestro_vendedores
- maestro_ccc
- maestro_segmentos
- maestro_marcas_cebe

Regla:

No contiene lógica de negocio.

---

## 4.3 STAGING

Estado:

IMPLEMENTADO

Propósito:

Normalizar datos provenientes de SQLite.

Responsabilidades permitidas:

- Lectura SQLite
- Detección de columnas
- Parseo de fechas
- Tipado
- Normalización
- Estandarización de nombres
- Limpieza técnica

Responsabilidades prohibidas:

- Objetivos
- Compensaciones
- Pace
- CCC
- MN+
- KPIs
- Negocio

---

# 5. Funciones STAGING Actuales

## obtener_staging_vta()

Responsabilidad:

Normalización de ventas.

Salida garantizada:

- FechaCarga_dt
- FechaEntrega_dt
- CodVendedor
- Cliente
- CantBase
- ImporteNetoItem
- Marca

---

## obtener_staging_clientes()

Responsabilidad:

Normalización del universo de clientes.

Salida garantizada:

- Cliente
- Taxonomia
- NombreCliente
- CodVendedor

---

## obtener_staging_rutas()

## 6. Evolución de BUSINESS RULES

### Estado

ACTIVO

### Objetivo

Desacoplar progresivamente la lógica comercial de los reportes.

### Estructura objetivo

RAW
↓
SQLITE
↓
STAGING
↓
CORE
↓
BUSINESS RULES
↓
REPORTES

### Capas implementadas

STAGING

- obtener_staging_vta()
- obtener_staging_clientes()
- obtener_staging_ausencias()
- obtener_staging_rutas()

CORE

- obtener_core_ventas_base()
- obtener_core_clientes()
- obtener_core_vendedores()
- obtener_core_operacion()

BUSINESS RULES

- business_rules_repository.py
- business_rules_kilos.py

BUSINESS RULES APROBADAS PARA PRÓXIMA IMPLEMENTACIÓN

- business_rules_mn.py

REPORTES CORE

- rep_kilos_core.py

REPORTES APROBADOS PARA MIGRACIÓN

- rep_MN_core.py

### Regla Arquitectónica

Permitido:

Reporte
↓
Business Rules
↓
Core

Prohibido:

Reporte
↓
Reporte

Objetivo:

Eliminar dependencias cruzadas entre reportes.