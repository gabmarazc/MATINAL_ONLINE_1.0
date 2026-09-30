###### FASE 4: STAGING y CORE (Arquitectura por Capas)

### Objetivo

Implementar de forma gradual la arquitectura institucional:

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

sin afectar la operación productiva.

---

### Estado General

EN EJECUCIÓN

---

### FASE 4.1 a 4.6

Estado:

COMPLETADAS ✅

Resultado:

- Definición formal de arquitectura por capas.
- Creación de estrategias de migración incremental.
- Separación conceptual entre STAGING y CORE.
- Auditoría del circuito de ausencias.
- Diseño de contratos técnicos para futuras entidades STAGING.

---

### FASE 4.7

Nombre:

Migración de AUSENCIAS hacia STAGING.

Estado:

COMPLETADA ✅

Fecha de cierre:

27/09/2026

Objetivo:

Crear una puerta de entrada especializada para la entidad AUSENCIAS.

Implementación:

Se creó:

obtener_staging_ausencias()

Responsabilidades asignadas:

- Lectura SQLite
- Detección de columnas
- Parseo robusto de fechas
- Tipado
- Normalización

---

### Cambio de Orquestación

Antes:

df_ausencias = maestros["ausencias"]

Después:

df_ausencias = obtener_staging_ausencias()

---

### Validación Ejecutada

Resultado:

APROBADA ✅

Controles realizados:

✅ Arranque Streamlit

✅ Carga SQLite

✅ Ejecución STAGING

✅ Ejecución CORE

✅ Renderizado completo

✅ Integración Ausencias

✅ Sin errores de importación

✅ Sin errores de ejecución

---

### Evidencia de Producción

Tiempos observados:

obtener_staging_ausencias:
0.0087 s

procesar_ausencias_y_reemplazos:
0.7176 s

obtener_core_operacion:
13.4367 s

obtener_matriz_kilos_comercial:
14.6438 s

Conclusión:

La migración de AUSENCIAS a STAGING no introdujo degradación visible de rendimiento.

---

### FASE 4.8

Estado:

PRÓXIMA ITERACIÓN APROBADA ⏳

Nombre:

Eliminación de ETL duplicado en CORE.

Objetivo:

Eliminar lógica técnica redundante de:

procesar_ausencias_y_reemplazos()

que actualmente ya existe en:

obtener_staging_ausencias()

---

### Elementos candidatos a eliminar

- cols_vend_cand
- cols_f_cand
- cols_reemp_cand
- parsear_fecha_robusta()
- CodVend_clean
- Reemplazo_clean

---

### Resultado esperado

STAGING:

100% ETL.

CORE:

100% lógica operativa.

---

### Restricción obligatoria

La refactorización no podrá realizarse sin validación de producción posterior.

La separación arquitectónica tiene prioridad por encima de la reducción de código.
#### FASE 4.9

Estado:

APROBADA ⏳

Nombre:

Migración MiNegocio hacia Business Rules.

Objetivo:

Separar la lógica comercial de MiNegocio del reporte histórico.

Implementación esperada:

rep_MN.py
↓
business_rules_mn.py
↓
rep_MN_core.py

Resultado esperado:

- Eliminación de lógica comercial del reporte.
- Reutilización de Core institucional.
- Fuente única de reglas MiNegocio.
- Preparación para desacoplar Gerencial.

Restricción:

No duplicar lógica existente en Core.
FASE 4.9
MiNegocio

FASE 4.10
CCC

FASE 4.11
Coberturas

FASE 4.12
Gerencial

FASE 4.13
Vespertina
