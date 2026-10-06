## Estado Actual del Proyecto - MATINAL

Versión: 3.1
Fecha de actualización: 04/10/2026
Estado: Producción Operativa
Estado de validación: Confirmado mediante ejecución real y auditoría forense

## 1. Identificación del Producto

### Nombre

MATINAL

### Descripción

Sistema institucional de análisis, monitoreo, control operativo y seguimiento comercial para la gestión integral de preventa.

### Estado

Producto productivo en operación diaria.

### Frecuencia de uso

Múltiples veces por día por usuarios operativos, supervisión y gerencia.

---

## 2. Estado General del Proyecto

### Estado global

ESTABLE

### Estado productivo

OPERATIVO

### Estado arquitectónico

ARQUITECTURA POR CAPAS IMPLEMENTADA Y VALIDADA

### Nivel de riesgo

BAJO

### Última validación integral

04/10/2026

### Resultado

EXITOSO

---

## 3. Arquitectura Vigente

### Arquitectura oficial

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

### Estado de implementación

RAW
✅

SQLITE
✅

STAGING
✅

CORE
✅

BUSINESS RULES
✅

REPORTES
✅

---

## 4. Estado Arquitectónico Actual

### Capas validadas

#### RAW

✅ Productivo

#### SQLITE

✅ Productivo

#### STAGING

✅ Productivo

#### CORE

✅ Productivo

#### BUSINESS RULES

✅ Productivo

#### REPORTES

✅ Productivo

---

## 5. Validaciones Productivas Confirmadas

### CORE

Validado mediante ejecución real.

Verificaciones:

✅ Carga SQLite
✅ Ejecución STAGING
✅ Ejecución CORE
✅ Integración Ausencias
✅ Integración Reemplazos
✅ Integración Calendario
✅ Integración Titularidad Operativa
✅ Sin errores de importación
✅ Sin NameError
✅ Sin KeyError
✅ Sin Tracebacks

### BUSINESS RULES

Validado mediante ejecución real.

Implementaciones productivas:

#### Kilos

rep_kilos_core.py
↓
business_rules_kilos.py
↓
core_*

Estado:

✅ Migrado
✅ Validado
✅ Productivo

#### MiNegocio

rep_MN_core.py
↓
business_rules_mn.py
↓
core_*

Estado:

✅ Migrado
✅ Validado
✅ Productivo

---

## 6. Auditoría Forense de Reemplazos (04/10/2026)

### Objetivo

Validar la consistencia funcional y técnica del modelo de compensaciones por reemplazo implementado en BUSINESS RULES y alimentado por CORE.

### Componentes Auditados

- core_operaciones.py
- procesar_ausencias_y_reemplazos()
- business_rules_kilos.py
- calcular_compensaciones_reemplazos()

### Hallazgos Confirmados

#### H-001

El vendedor comodín institucional válido es:

CodVendedor = 99

Nombre:

REEMPLAZO

#### H-002

El uso histórico de:

-998

queda descartado como identificador válido dentro del flujo operativo actual.

#### H-003

La columna:

CodVendedorHistorico

se encuentra implementada y utilizada para preservar la titularidad original de las operaciones antes de cualquier reasignación hacia CodVendedorVigente.

#### H-004

La función:

calcular_compensaciones_reemplazos()

utiliza:

CodVendedorHistorico

cuando dicha columna existe.

#### H-005

Las compensaciones excluyen explícitamente:

Periodo = Fuera de Periodo

y únicamente consideran:

- Arrastre
- Actual

#### H-006

No se detectaron pérdidas de masa en las compensaciones.

Toda salida posee una entrada equivalente.

Balance validado.

---

## 7. Caso de Auditoría Principal

### Caso

CodVendedor = 11

ORTIZ

### Contexto

Se observó una diferencia significativa entre:

- venta propia visible
- ajuste por reemplazo

lo que motivó una auditoría completa.

### Resultado

Se verificó que:

CodVendedorOperativo = 99

posee operaciones reales asociadas a la cartera del vendedor 11.

### Evidencia Consolidada

Transferencias auditadas:

CodVendedor 11 → 99

86.504 kg

CodVendedor 25 → 99

68.973 kg

CodVendedor 10 → 99

3.464 kg

Total:

158.941 kg

### Conclusión

No se encontró evidencia de generación artificial de kilos.

Las compensaciones provienen de operaciones reales.

---

## 8. Hallazgos No Confirmados

Actualmente NO existe evidencia que demuestre errores en:

- CodVendedorHistorico
- CodVendedorOperativo
- vendedor 99
- compensaciones
- balance de reemplazos
- exclusión de Fuera de Período

---

## 9. Investigación Actualmente Abierta

### Estado

ABIERTA

### Objetivo

Explicar completamente la diferencia observada entre:

- kilos transferidos auditados
- kilos visibles por segmento en la matriz comercial

### Hipótesis pendientes

- diferencias de segmentación comercial
- clasificación por Rubro
- clasificación por Familia
- exclusiones posteriores al cálculo operativo

### Restricción

No modificar código hasta identificar evidencia del primer punto de divergencia.

---

## 10. Módulos Operativos en Producción

### Dashboard Gerencial

✅ Productivo

### CCC

✅ Productivo

### Mi Negocio

✅ Productivo

### Kilos

✅ Productivo

Incluye:

- objetivos
- compensaciones
- reemplazos
- proyecciones
- titularidad operativa

### Cobertura Marca

✅ Productivo

### Cobertura Innovación

✅ Productivo

### Parámetros

✅ Productivo

### Vespertina

✅ Productivo

---

## 11. Fuente de Verdad Institucional

Los siguientes conceptos tienen prioridad absoluta:

- Día Matinal
- Problema de Cierre
- Ausencias
- Reemplazos
- Titularidad Operativa
- Objetivos
- Universo Operativo
- Estructura Comercial

Toda optimización que contradiga alguno de estos conceptos deberá rechazarse.

---

## 12. Estado Técnico Consolidado

### STAGING

✅ Consolidado

### CORE

✅ Consolidado

### BUSINESS RULES

✅ Consolidado

### Patrón Arquitectónico

Reporte
↓
Business Rules
↓
Core

Estado:

✅ Validado
✅ Productivo

---

## 13. Historización

Implementado:

✅ universo_hist

✅ universo_versiones

✅ HashSnapshot

✅ snapshots automáticos

✅ persistencia SQLite validada

---

## 14. Resumen Ejecutivo

Estado General:

✅ Producción Operativa

Arquitectura:

✅ RAW → SQLITE → STAGING → CORE → BUSINESS RULES → REPORTES

Migraciones Validadas:

✅ Kilos
✅ MiNegocio
✅ CCC

Auditoría de Reemplazos:

✅ vendedor 99 validado
✅ CodVendedorHistorico validado
✅ balance validado
✅ Fuera de Período descartado
✅ reemplazos auditados con datos reales

Investigación Abierta:

⏳ reconciliación final entre compensaciones segmentadas y matriz comercial

Nivel de Riesgo:

✅ Bajo