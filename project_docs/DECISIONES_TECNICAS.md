---

##### H. Decisiones de Arquitectura por Capas (Fase 4)

---

### DT.15: Implementación Formal de la Capa STAGING

#### Fecha
27/09/2026

#### Estado
Vigente ✅

#### Descripción

Se declara oficialmente implementada la capa STAGING dentro de la arquitectura institucional MATINAL.

La transición desde el modelo histórico:

RAW
↓
SQLite
↓
Pipelines Analíticos

hacia el modelo objetivo:

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

deja de ser un objetivo teórico y pasa a ser una realidad operativa validada.

#### Principios

La capa STAGING debe encargarse exclusivamente de:

- Lectura SQLite
- Parseo de fechas
- Detección de columnas
- Normalización
- Conversión de tipos
- Limpieza técnica
- Contratos de datos

La capa STAGING no debe contener:

- Objetivos
- KPIs
- Pace
- Compensaciones
- CCC
- MN+
- Coberturas
- Lógica comercial

---

### DT.16: Implementación del Módulo obtener_staging_ausencias()

#### Fecha

27/09/2026

#### Estado

Vigente ✅

#### Descripción

Se crea la función:

obtener_staging_ausencias()

como punto oficial de entrada para la entidad AUSENCIAS.

#### Motivación

Históricamente el procesamiento de ausencias se encontraba mezclado con lógica operativa dentro del CORE.

La decisión institucional consiste en trasladar progresivamente toda responsabilidad ETL asociada a ausencias hacia la capa STAGING.

#### Responsabilidades asignadas

obtener_staging_ausencias() es responsable de:

- Lectura de la tabla SQLite ausencias
- Detección de vendedor
- Detección de fecha
- Detección de reemplazo
- Parseo robusto de fechas
- Conversión a Int64
- Generación de columnas normalizadas

#### Contrato de salida aprobado

Columnas garantizadas:

- Fecha_dt
- CodVend_clean
- Reemplazo_clean

---

### DT.17: Cambio de Orquestación para Ausencias

#### Fecha

27/09/2026

#### Estado

Vigente ✅

#### Cambio aprobado

Antes:

df_ausencias = maestros["ausencias"]

Después:

df_ausencias = obtener_staging_ausencias()

#### Resultado

El CORE deja de depender de estructuras internas del diccionario de maestros para obtener ausencias.

La entidad pasa a poseer un acceso especializado y desacoplado.

#### Beneficios

- Menor acoplamiento
- Mejor mantenibilidad
- Preparación para futuras entidades STAGING
- Contratos de datos explícitos

---

### DT.18: Estrategia de Migración Incremental STAGING → CORE

#### Fecha

27/09/2026

#### Estado

Vigente ✅

#### Decisión

Toda migración arquitectónica deberá realizarse mediante dos etapas separadas:

ETAPA 1

Crear STAGING especializado.

ETAPA 2

Consumir STAGING desde CORE.

ETAPA 3

Validar producción.

ETAPA 4

Eliminar duplicidades.

#### Prohibición

No realizar simultáneamente:

- creación de STAGING
- cambio de orquestación
- eliminación de lógica heredada

en una única iteración.

Motivo:

Dificulta la detección de regresiones.

---

### DT.19: Validación Operativa de la FASE 4.7

#### Fecha

27/09/2026

#### Estado

Vigente ✅

#### Resultado

La implementación fue validada mediante ejecución real del sistema.

Verificaciones aprobadas:

✅ Arranque Streamlit

✅ Carga SQLite

✅ Ejecución STAGING

✅ Ejecución CORE

✅ Generación de reportes

✅ Integración de ausencias

✅ Ausencia de errores de importación

✅ Ausencia de errores de ejecución

#### Evidencia

Tiempos observados:

obtener_staging_ausencias:
0.0087 s

procesar_ausencias_y_reemplazos:
0.7176 s

obtener_core_operacion:
13.4367 s

obtener_matriz_kilos_comercial:
14.6438 s

#### Conclusión

La FASE 4.7 queda formalmente cerrada.

---

### DT.20: Refactor Pendiente de Ausencias (FASE 4.8)

#### Estado

Pendiente ⏳

#### Objetivo

Eliminar ETL redundante dentro de:

procesar_ausencias_y_reemplazos()

#### Elementos candidatos

- cols_vend_cand
- cols_f_cand
- cols_reemp_cand
- parsear_fecha_robusta()
- CodVend_clean
- Reemplazo_clean

#### Resultado esperado

STAGING:

100% ETL.

CORE:

100% lógica operativa.

#### Restricción

No ejecutar esta refactorización sin validación previa de producción.

---

### DT.21: Política de Conservación del Conocimiento Institucional

#### Fecha

27/09/2026

#### Estado

Vigente ✅

#### Decisión

Los siguientes documentos constituyen la memoria mínima obligatoria del proyecto:

- ARQUITECTURA.md
- ESTADO_ACTUAL.md
- DECISIONES_TECNICAS.md
- ROADMAP.md
- PIPELINE_CORE.md
- DICCIONARIO_TABLAS.md
- GLOSARIO_REGLAS.md

#### Objetivo

Permitir que cualquier instancia futura de Copilot, desarrollador o auditor reconstruya el contexto técnico y funcional completo sin depender del historial de conversaciones.