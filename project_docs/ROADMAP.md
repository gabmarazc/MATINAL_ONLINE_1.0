# ROADMAP - MATINAL

Versión: 3.0  
Fecha de actualización: 30/09/2026  
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

- Definición formal de arquitectura por capas.
- Incorporación de SQLite como fuente física única.
- Definición de responsabilidades STAGING.
- Definición de responsabilidades CORE.
- Estrategia de migración incremental aprobada.
- Contratos técnicos institucionales definidos.

---

## FASE 4.7

Nombre:

Migración de AUSENCIAS hacia STAGING

Estado:

✅ COMPLETADA

Fecha de cierre:

27/09/2026

Resultado:

- Implementación de obtener_staging_ausencias().
- Separación efectiva entre ETL y lógica operativa.
- Contrato técnico validado.
- Producción validada sin regresiones.

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

## Validación 2

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

- cols_vend_cand
- cols_f_cand
- cols_reemp_cand
- parsear_fecha_robusta()
- CodVend_clean
- Reemplazo_clean

Resultado esperado:

STAGING = 100% ETL

CORE = 100% Operación

Restricción obligatoria:

Toda eliminación deberá validarse nuevamente en producción.

---

# Próxima Migración Aprobada

## FASE 4.10

Nombre:

Migración CCC hacia BUSINESS RULES

Estado:

⏳ APROBADA

Arquitectura objetivo:

rep_ccc.py
↓
business_rules_ccc.py
↓
rep_ccc_core.py

Objetivos:

- Eliminar lógica comercial embebida en rep_ccc.py.
- Crear una fuente única de verdad para CCC.
- Reutilizar Core institucional.
- Preparar el desacoplamiento de Vespertina.
- Preparar el desacoplamiento de Gerencial.
- Eliminar dependencias futuras entre reportes.

Restricción:

No duplicar lógica ya existente en CORE o BUSINESS RULES.

---

# Roadmap de Migraciones

## Completadas

✅ Kilos

✅ MiNegocio

---

## Pendientes

⏳ CCC

⏳ Cobertura Marca

⏳ Cobertura Innovación

⏳ Gerencial

⏳ Vespertina

---

# Orden Estratégico Vigente

1. CCC
2. Cobertura Marca
3. Cobertura Innovación
4. Gerencial
5. Vespertina

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