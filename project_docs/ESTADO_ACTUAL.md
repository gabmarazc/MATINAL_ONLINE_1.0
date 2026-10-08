```markdown
## Estado Actual del Proyecto - MATINAL

Versión: 3.1
Fecha de actualización: 06/10/2026
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

Múltiples veces por day por usuarios operativos, supervisión y gerencia.

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

06/10/2026

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

## 8. Auditoría Forense de Objetivos (06/10/2026)

### Objetivo

Validar la correcta distribución de los objetivos comerciales y determinar la causa raíz de la diferencia detectada entre el Objetivo Corporativo y el Objetivo Visible.

### Componentes Auditados

- core_potencial_cliente_segmento.py
- business_rules_objetivo_clientes.py
- business_rules_objetivo_carteras.py
- business_rules_objetivo_segmentos.py

### Hechos Confirmados

- Objetivo Corporativo: 61.300 kg
- Objetivo Visible previo: 61.227,37 kg
- Diferencia identificada: 72,630941 kg

### Hallazgos

- 93 clientes fuera de Universo participaban en la distribución.
- Generaban 71,647538 kg.
- Clasificación: CLIENTE_SIN_CARTERA

### Composición Auditada

- CLIENTE_SIN_CARTERA: 71,647538 kg
- VENDEDOR_NO_ASIGNADO: 0,983403 kg
- TOTAL: 72,630941 kg

### Causa Raíz Validada

business_rules_objetivo_clientes distribuía objetivos utilizando la población proveniente de core_potencial_cliente_segmento sin filtrar previamente la población contra SELECT Codigo FROM universo. Como consecuencia, clientes fuera de universo seguían absorbiendo participación dentro de la distribución de objetivos.

### Corrección Implementada

Filtrado obligatorio mediante SELECT Codigo FROM universo antes del cálculo de:
- ParticipacionMarcaSegmento
- ParticipacionClienteDentroSegmento
- ObjetivoClienteKg

### Validaciones Ejecutadas

✅ Auditoría de población utilizada por Objetivos.
✅ Comparación entre Universo vigente y población de Potencial.
✅ Validación de clientes excluidos.
✅ Validación matemática de conservación de masa.
✅ Validación de SUM ObjetivoClienteKg.
✅ Validación de apropiación por cartera.
✅ Identificación individual de diferencias residuales.

### Resultados

- SUM ObjetivoClienteKg: 61.300 kg
- Resultado visible posterior: 61.299,02 kg
- Diferencia residual: 0,983403 kg

### Auditoría Residual

- Cliente: 46987
- Razón Social: LAURA
- Hallazgos: 
  - ✅ Existe en Universo.
  - ✅ Participa correctamente en la distribución.
  - ❌ Sin codven.
  - ❌ Sin Ruta.
- Resultado:
  - Clasificación: VENDEDOR_NO_ASIGNADO
  - Objetivo: 0,983403 kg

### Conclusión Institucional

✅ Distribución de objetivos validada exclusivamente sobre el padrón vigente de universo.
✅ Clientes fuera de universo excluidos de la distribución.
✅ Conservación de masa validada.
✅ Diferencia residual completamente explicada.
✅ No existe evidencia de falla algorítmica en la distribución.
La diferencia residual restante corresponde exclusivamente a datos maestros incompletos del cliente 46987.

---

## 9. Hallazgos No Confirmados

Actualmente NO existe evidencia que demuestre errores en:

- CodVendedorHistorico   
- CodVendedorOperativo   
- vendedor 99   
- compensaciones   
- balance de reemplazos   
- exclusión de Fuera de Período   

---

## 10. Investigación Actualmente Abierta

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

## 11. Módulos Operativos en Producción

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

## 12. Fuente de Verdad Institucional

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

## 13. Estado Técnico Consolidado

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

## 14. Historización

Implementado:

✅ universo_hist
✅ universo_versiones
✅ HashSnapshot
✅ snapshots automáticos
✅ persistencia SQLite validada   

---

## 15. Resumen Ejecutivo

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

Auditoría de Objetivos:

✅ Distribución sobre universo vigente validada
✅ Filtrado obligatorio contra universo implementado
✅ Diferencia huérfana de clientes fuera de universo eliminada
✅ Diferencia residual explicada (Cliente 46987)
✅ 93 clientes fuera de universo identificados y excluidos.
✅ Conservación de masa validada (61.300 kg).

Investigación Abierta:

⏳ reconciliación final entre compensaciones segmentadas y matriz comercial   

Nivel de Riesgo:

✅ Bajo   
