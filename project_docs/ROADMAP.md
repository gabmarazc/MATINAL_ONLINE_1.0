# ROADMAP - MATINAL

Versión: 3.0

Fecha de actualización: 02/10/2026

Estado: Vigente

Estado de validación: Producción Operativa

---

# Objetivo Estratégico

Consolidar la arquitectura institucional:

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

mediante migraciones incrementales, controladas y validadas en producción.

---

# Estado Arquitectónico General

RAW
✅

SQLITE
✅

STAGING
✅

CORE
✅

BUSINESS RULES
✅ Validada en producción

REPORTES
✅

---

# Fases Completadas

## FASE 4.1 a 4.6

Estado:
✅ COMPLETADAS

Resultados alcanzados:

* Definición formal de arquitectura por capas.
* Incorporación de SQLite como fuente física única.
* Definición de responsabilidades STAGING.
* Definición de responsabilidades CORE.
* Estrategia de migración incremental aprobada.
* Contratos técnicos institucionales definidos.

---

## FASE 4.7

Nombre:

Migración de AUSENCIAS hacia STAGING

Estado:

✅ COMPLETADA

Fecha de cierre:

27/09/2026

Resultado:

* Implementación de obtener_staging_ausencias().
* Separación efectiva entre ETL y lógica operativa.
* Contrato técnico validado.
* Producción validada sin regresiones.

---

## FASE 4.9

Nombre:

Migración MiNegocio hacia BUSINESS RULES

Estado:

✅ COMPLETADA

Fecha de cierre:

30/09/2026

Arquitectura implementada:

rep_MN_core.py
↓
business_rules_mn.py
↓
core_*

Resultado:

✅ Eliminación de lógica comercial del reporte histórico.

✅ Reutilización de Core institucional.

✅ Clasificación Digital migrada.

✅ Matriz comercial centralizada.

✅ Segundo caso exitoso de adopción de BUSINESS RULES.

---

# Validaciones Arquitectónicas Alcanzadas

## Validación 1

Kilos

Arquitectura:

rep_kilos_core.py
↓
business_rules_kilos.py
↓
core_*

Estado:

✅ Productivo

✅ Validado

---

## Validation 2

MiNegocio

Arquitectura:

rep_MN_core.py
↓
business_rules_mn.py
↓
core_*

Estado:

✅ Productivo

✅ Validado

Validaciones finales:

✅ TOTAL CARTERA = 5617

✅ CodVendedor -998 = 0

---

### Validación 3

Objetivos
Estado:
✅ Productivo
✅ Validado
✅ Distribución sobre Universo vigente validada
Resultado:
✅ Elegibilidad institucional validada.
✅ Distribución compatible con Universo vigente.
✅ Integración validada dentro de BUSINESS RULES.

---

## Validación Institucional de Objetivos

Estado:
✅ COMPLETADA Y VALIDADA
Fecha de cierre:
06/10/2026
Objetivo:
Validar la consistencia institucional de la distribución de objetivos comerciales.
Resultados Alcanzados:
✅ Distribución validada sobre Universo vigente.
✅ Universo oficializado como fuente de elegibilidad para objetivos.
✅ Conservación de masa validada.
✅ Reglas de distribución formalizadas.
✅ Integración validada dentro de BUSINESS RULES.
Impacto Institucional:

* Actualización de documentación funcional.
* Actualización de documentación técnica.
* Actualización de arquitectura.
* Formalización de reglas de elegibilidad.
Estado Final:
CERRADO

---

# Estado Actual de BUSINESS RULES

La arquitectura:

Reporte
↓
Business Rules
↓
Core

se considera oficialmente validada en producción.

A partir de esta fecha deja de considerarse una prueba de concepto y se transforma en la estrategia institucional oficial para nuevas migraciones.

---

# Fase Pendiente Inmediata

## FASE 4.8

Nombre:

Eliminación de ETL duplicado en CORE

Estado:

⏳ Pendiente

Objetivo:

Eliminar lógica técnica redundante actualmente presente en:

procesar_ausencias_y_reemplazos()

y ya implementada en:

obtener_staging_ausencias()

Elementos identificados:

* cols_vend_cand
* cols_f_cand
* cols_reemp_cand
* parsear_fecha_robusta()
* CodVend_clean
* Reemplazo_clean

Resultado esperado:

STAGING = 100% ETL

CORE = 100% Operación

Restricción obligatoria:

Toda eliminación deberá validarse nuevamente en producción.

---

# Migraciones Completadas

## FASE 4.10

Nombre:

Migración CCC hacia BUSINESS RULES

Estado:

✅ COMPLETADA Y VALIDADA

Fecha de cierre:

04/10/2026

Arquitectura implementada:

rep_ccc_core.py
↓
business_rules_ccc.py
↓
core_*

Objetivos alcanzados:

* Eliminación de lógica comercial embebida en rep_ccc.py.
* Creación de fuente única de verdad para CCC.
* Reutilización de Core institucional.
* Validación y despliegue productivo completados.

---

# Roadmap de Migraciones

## Completadas

✅ Kilos

✅ MiNegocio

✅ CCC

---

## Pendientes

⏳ Cobertura Marca

⏳ Cobertura Innovación

⏳ Gerencial

⏳ Vespertina

---

# Orden Estratégico Vigente

1. Cobertura Marca
2. Cobertura Innovación
3. Gerencial
4. Vespertina

---

# Iniciativa Estratégica Futura

## Historización Institucional de Maestros

Estado:

⏳ Líneas futuras de investigación y evolution

Líneas de trabajo identificadas tras la implementación validada de `universo_hist`, `universo_versiones`, `HashSnapshot` y snapshots automáticos:

* Auditoría histórica de cartera.
* Comparación entre versiones de Universo.
* Herramientas de administración SQL.
* Reconstrucción temporal de estados históricos.
* Análisis de transferencias comerciales.
* Apropiación histórica (pendiente de validación).
* Evoluciones futuras de CORE_OPERACION.

Restricción:

No constituyen fases activas aprobadas ni alteran las prioridades del roadmap operativo vigente.

---

# Objetivo Final

Eliminar progresivamente todas las dependencias:

Reporte
↓
Reporte

y reemplazarlas por:

Reporte
↓
Business Rules
↓
Core

hasta alcanzar una arquitectura completamente desacoplada, reutilizable y gobernada por una única fuente institucional de reglas comerciales.