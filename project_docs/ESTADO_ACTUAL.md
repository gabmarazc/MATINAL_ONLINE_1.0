# Estado Actual del Proyecto - MATINAL

Versión: 2.0
Fecha de actualización: 27/09/2026
Estado: Producción Operativa
Estado de validación: Confirmado mediante ejecución real

---

# 1. Identificación del Producto

Nombre:

MATINAL

Descripción:

Sistema institucional de análisis, monitoreo, control operativo y seguimiento comercial para la gestión integral de preventa.

Estado:

Producto productivo en operación diaria.

Frecuencia de uso:

Múltiples veces por día por usuarios operativos, supervisión y gerencia.

---

# 2. Estado General del Proyecto

Estado global:

ESTABLE

Estado productivo:

OPERATIVO

Estado arquitectónico:

EN TRANSICIÓN CONTROLADA HACIA ARQUITECTURA POR CAPAS

Nivel de riesgo:

BAJO

Última validación integral:

27/09/2026

Resultado:

EXITOSO

---

# 3. Arquitectura Vigente

Arquitectura oficial:

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

Estado de implementación:

RAW
✅

SQLITE
✅

STAGING
✅

CORE
✅

BUSINESS RULES
🟡 Parcialmente desacoplado

REPORTES
✅

---

# 4. Estado de la Fase Arquitectónica Actual

Fase institucional actual:

FASE 4

Subfase actual:

FASE 4.7 COMPLETADA

Nombre:

Migración de AUSENCIAS a STAGING

Resultado:

VALIDADA

Estado:

CERRADA

---

# 5. Cambio Arquitectónico Más Importante Realizado

Se implementó:

obtener_staging_ausencias()

como puerta de entrada especializada para el procesamiento técnico de ausencias.

---

## Situación anterior

Las ausencias se obtenían mediante:

maestros["ausencias"]

y el procesamiento técnico permanecía íntegramente dentro del CORE.

---

## Situación actual

El sistema utiliza:

obtener_staging_ausencias()

para:

- lectura SQLite
- detección de columnas
- parseo de fechas
- normalización
- tipado

---

## Impacto

Separación efectiva entre:

STAGING
y
CORE

sin afectar producción.

---

# 6. Validación Real Ejecutada

Fecha:

27/09/2026

Resultado:

ÉXITO

Log validado:

obtener_staging_ausencias → 0.0087 s

procesar_ausencias_y_reemplazos → 0.7176 s

obtener_core_operacion → 13.4367 s

obtener_matriz_kilos_comercial → 14.6438 s

---

## Verificaciones realizadas

✅ Arranque de Streamlit

✅ Carga SQLite

✅ Ejecución STAGING

✅ Ejecución CORE

✅ Renderizado reportes

✅ Integración AUSENCIAS

✅ Sin errores de importación

✅ Sin NameError

✅ Sin KeyError

✅ Sin tracebacks

---

# 7. Módulos Operativos en Producción

Todos los siguientes módulos se encuentran activos.

---

## Dashboard Gerencial

Estado:

PRODUCTIVO

Funciones:

- seguimiento directivo
- consolidación comercial
- proyecciones

---

## CCC

Estado:

PRODUCTIVO

Funciones:

- cartera
- altas
- reactivaciones
- batalla NC

---

## Mi Negocio

Estado:

PRODUCTIVO

Funciones:

- adopción digital
- clasificación digital
- gap a objetivo

---

## Kilos

Estado:

PRODUCTIVO

Funciones:

- avance kilos
- objetivos
- proyección
- compensaciones
- reemplazos

---

## Cobertura Marca

Estado:

PRODUCTIVO

---

## Cobertura Innovación

Estado:

PRODUCTIVO

---

## Objetivos

Estado:

PRODUCTIVO

---

## Parámetros

Estado:

PRODUCTIVO

---

## Vespertina

Estado:

PRODUCTIVO

---

# 8. Roles Activos

Nivel 1

Administrador

Acceso total.

---

Nivel 2

Gerencia

Acceso directivo.

---

Nivel 3

Supervisión

Acceso operativo controlado.

---

# 9. Stack Tecnológico Vigente

Backend:

- Python

Procesamiento:

- Pandas
- NumPy
- OpenPyXL

Interfaz:

- Streamlit
- AgGrid

Persistencia:

- SQLite WAL

---

# 10. Fuente de Verdad Institucional

Los siguientes conceptos poseen prioridad absoluta sobre cualquier decisión técnica:

- Día Matinal
- Problema de Cierre
- Filtro N1
- Filtro N2
- Ausencias
- Reemplazos
- Objetivos
- Universo Operativo
- Coberturas
- Estructura Comercial

Si alguna optimización contradice estos principios:

debe rechazarse.

---

# 11. Próxima Fase

FASE 4.8

Nombre:

Eliminación de ETL duplicado en CORE.

Objetivo:

Retirar de:

procesar_ausencias_y_reemplazos()

la lógica que ya existe en:

obtener_staging_ausencias()

---

## Elementos candidatos a eliminar

- detección de columnas
- parseo de fechas
- CodVend_clean
- Reemplazo_clean

---

## Objetivo final

CORE:

solo l
## 12. Estado de BUSINESS RULES

Estado:

IMPLEMENTACIÓN INICIAL VALIDADA

Componentes productivos:

- business_rules_repository.py
- business_rules_kilos.py

Reporte migrado:

- rep_kilos_core.py

Resultado:

✅ Kilos desacoplado del reporte histórico.

✅ Arquitectura Business Rules validada en producción.

✅ Patrón reutilizable para futuras migraciones.