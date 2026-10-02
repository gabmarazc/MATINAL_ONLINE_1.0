# BITÁCORA - MATINAL

Versión: 3.0  
Fecha de actualización: 30/09/2026  
Estado: Vigente  
Naturaleza: Registro histórico institucional

---

# ESTADO GENERAL DEL PROYECTO

## Estado Productivo

✅ Producción Operativa

## Arquitectura Oficial

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

## Estado Arquitectónico

RAW               ✅

SQLITE            ✅

STAGING           ✅

CORE              ✅

BUSINESS RULES    ✅

REPORTES          ✅

## Fase Actual

FASE 4.8 APROBADA ⏳

Eliminación de ETL duplicado en CORE

## Próxima Migración

CCC

---

# INC-2026-09-24-001

## Título

Eliminación de referencia obsoleta a la tabla parametros_marcas

## Fecha de Apertura

24/09/2026

## Fecha de Cierre

24/09/2026

## Origen

Durante la validación operativa de la Fase 2A (Logging Estructurado) se detectaron advertencias recurrentes asociadas a consultas sobre una tabla inexistente.

## Evidencia

```text
WARNING | matinal.database |
La tabla consultada no existe en el catálogo de SQLite.
SELECT * FROM parametros_marcas
```

## Acción Realizada

Eliminación de referencias remanentes a:

parametros_marcas

## Validación Final

✅ Reinicio completo

✅ Recarga total de módulos

✅ Reportes operativos

✅ Sin nuevas referencias detectadas

## Estado

CERRADO

---

# INC-2026-09-25-001

## Título

Unificación de padrón de vendedores y supervisor en Tienda Perfecta

## Fecha de Apertura

25/09/2026

## Fecha de Cierre

25/09/2026

## Cambio

Integración de:

rep_tp.py

con:

maestro_vendedores

## Resultado

✅ Supervisor operativo

✅ Catálogos actualizados

✅ Exportaciones funcionales

✅ Sin degradación observable

## Estado

CERRADO

---

# INC-2026-09-26-001

## Título

Auditoría forense de paridad en STAGING_CLIENTES

## Fecha de Apertura

26/09/2026

## Fecha de Cierre

26/09/2026

## Contexto

Se detectó una diferencia entre:

RAW_UNIVERSO = 5719

STAGING_CLIENTES = 5615

## Hallazgos

Diferencia total:

104 registros

Los registros faltantes corresponden exclusivamente a:

SubSegmento = Empleados

## Verificaciones

✅ SQLite contiene 5719 registros

✅ Sin pérdidas por tipado

✅ Sin pérdidas por duplicados

✅ Sin pérdidas por nulos

## Resultado

✅ FASE 4.1 cerrada

✅ Inicio autorizado de CORE

## Estado

CERRADO

---

# INC-2026-09-27-001

## Título

Migración de AUSENCIAS hacia STAGING

## Fecha de Apertura

27/09/2026

## Fecha de Cierre

27/09/2026

## Objetivo

Separar responsabilidades ETL y operativas mediante la formalización de STAGING.

## Implementación

Creación de:

obtener_staging_ausencias()

## Contrato Aprobado

- Fecha_dt
- CodVend_clean
- Reemplazo_clean

## Resultado

✅ Menor acoplamiento

✅ Contrato explícito

✅ Preparación para futuras migraciones

## Estado

CERRADO

---

# INC-2026-09-27-002

## Título

Validación productiva de Migración AUSENCIAS → STAGING

## Fecha de Apertura

27/09/2026

## Fecha de Cierre

27/09/2026

## Validaciones

✅ Arranque Streamlit

✅ Carga SQLite

✅ Ejecución STAGING

✅ Ejecución CORE

✅ Integración AUSENCIAS

✅ Sin errores de ejecución

## Evidencia Operativa

```text
obtener_staging_ausencias        0.0087 s
procesar_ausencias_y_reemplazos  0.7176 s
obtener_core_operacion          13.4367 s
obtener_matriz_kilos_comercial  14.6438 s
```

## Resultado

✅ Integración aprobada

✅ Sin regresiones funcionales

✅ Sin impacto perceptible de performance

## Estado

CERRADO

---

# INC-2026-09-27-003

## Título

Cierre formal de FASE 4.7

## Fecha de Apertura

27/09/2026

## Fecha de Cierre

27/09/2026

## Nombre

Migración de AUSENCIAS hacia STAGING

## Resultado Institucional

✅ STAGING consolidado

✅ CORE operativo

✅ Arquitectura por capas consolidada

## Estado

CERRADO

---

# EVENTO-2026-09-27-001

## Título

Aprobación formal de FASE 4.8

## Fecha

27/09/2026

## Estado

PENDIENTE

## Nombre

Eliminación de ETL duplicado en CORE

## Objetivo

Eliminar lógica técnica heredada ya migrada a:

obtener_staging_ausencias()

## Resultado Esperado

STAGING = 100% ETL

CORE = 100% Operación

---

# INC-2026-09-29-001

## Título

Cierre formal de Migración Kilos hacia Business Rules

## Fecha de Apertura

29/09/2026

## Fecha de Cierre

29/09/2026

## Implementación

rep_kilos_core.py
↓
business_rules_kilos.py
↓
core_*

## Resultado

✅ Migración validada

✅ Patrón arquitectónico aprobado

✅ Referencia institucional para futuras migraciones

## Estado

CERRADO

---

# INC-2026-09-30-001

## Título

Cierre formal de Migración MiNegocio hacia Business Rules

## Fecha de Apertura

30/09/2026

## Fecha de Cierre

30/09/2026

## Implementación

rep_MN_core.py
↓
business_rules_mn.py
↓
core_*

## Reglas Migradas

- Clasificación Digital
- No Digital
- Híbrido
- Fully Digital
- Pct_MiNegocio
- Minimo_Facturacion_70
- Matriz comercial por cliente
- Adopción por vendedor
- Adopción por taxonomía

## Resultado

✅ Migración validada

✅ Reporte productivo

✅ Reutilización de Core institucional

✅ Eliminación de lógica comercial del reporte

✅ Segundo caso exitoso de adopción de Business Rules

## Estado

CERRADO

---

# INC-2026-09-30-002

## Título

Validación funcional final de MiNegocio

## Fecha de Apertura

30/09/2026

## Fecha de Cierre

30/09/2026

## Contexto

Durante la estabilización final de la migración MiNegocio se realizó una auditoría completa de universo comercial, titularidad y métricas consolidadas.

## Hallazgos

TOTAL CARTERA = 5617

CodVendedor -998 = 0

## Verificaciones

✅ Universo consistente

✅ Titularidad preservada

✅ Sin contaminación por vendedor dummy

✅ Exportaciones validadas

✅ Resultados compatibles con producción

## Resultado

Validación final aprobada para producción.

## Estado

CERRADO

---

# EVENTO-2026-09-30-001

## Título

Validación institucional de BUSINESS RULES

## Fecha

30/09/2026

## Estado

COMPLETADO

## Contexto

La arquitectura:

Reporte
↓
Business Rules
↓
Core

fue sometida a validación mediante implementaciones productivas independientes.

## Implementaciones Utilizadas

### Kilos

rep_kilos_core.py
↓
business_rules_kilos.py
↓
core_*

### MiNegocio

rep_MN_core.py
↓
business_rules_mn.py
↓
core_*

## Resultado Institucional

✅ BUSINESS RULES validada

✅ Estrategia oficial aprobada

✅ Fin de etapa experimental

✅ Patrón obligatorio para nuevas migraciones

---

# RESUMEN INSTITUCIONAL

Estado General:

✅ Producción operativa

Arquitectura:

✅ RAW → SQLITE → STAGING → CORE → BUSINESS RULES → REPORTES

Migraciones completadas:

✅ Kilos

✅ MiNegocio

Validaciones institucionales:

✅ BUSINESS RULES

✅ MiNegocio

✅ CORE

✅ STAGING

Próxima migración aprobada:

⏳ CCC

Nivel de riesgo:

✅ Bajo
## INC-2026-10-02-001

### Título

Cierre formal de estabilización CORE Comercial

### Fecha de Apertura

30/09/2026

### Fecha de Cierre

02/10/2026

### Contexto

Durante la migración completa hacia arquitectura CORE + BUSINESS RULES se detectaron múltiples incidencias asociadas a escenarios borde, validaciones incompletas y dependencias heredadas.

La estabilización incluyó validación productiva sobre múltiples reconstrucciones de SQLite, reinicios completos de Streamlit y cambios de período operativo.

### Alcance

#### CORE KILOS

rep_kilos_core.py
↓
business_rules_kilos.py
↓
core_operaciones.py
↓
core_vendedores.py

#### CORE CCC

rep_ccc_core.py
↓
business_rules_ccc.py
↓
core_*

#### CORE MiNegocio

rep_MN_core.py
↓
business_rules_mn.py
↓
core_*

### Correcciones Realizadas

#### KILOS

✅ Corrección de columnas opcionales de objetivos

✅ Corrección de escenarios con objetivos vacíos

✅ Corrección de cálculos de tendencias

✅ Corrección de cálculos de promedio diario

✅ Corrección de escenarios con reemplazos inexistentes

✅ Corrección de escenarios con compensaciones vacías

✅ Eliminación de AttributeError por fillna() sobre float

✅ Eliminación de AttributeError por copy() sobre float

✅ Fortalecimiento defensivo sobre DataFrames vacíos

#### CCC

✅ Corrección de referencias inconsistentes de columnas auxiliares

✅ Validación de generación de matriz comercial

✅ Validación de detalle comercial

✅ Validación de ejecución completa sin errores

#### MiNegocio

✅ Validación definitiva de clasificación digital

✅ Validación de objetivos

✅ Validación de métricas comerciales

✅ Validación de adopción por vendedor

✅ Validación de adopción por taxonomía

### Validaciones Ejecutadas

✅ Reinicio completo de Streamlit

✅ Recarga completa de SQLite

✅ Recarga completa de bases operativas

✅ Reconstrucción total de caché

✅ Cambio de período operativo

✅ Período sin objetivos cargados

✅ Escenarios sin reemplazos

✅ Escenarios con objetivos vacíos

✅ Escenarios con compensaciones vacías

✅ Navegación completa de reportes

### Resultados Funcionales

#### CORE KILOS

✅ Render correcto

✅ Sin Traceback

✅ Sin AttributeError

✅ Sin KeyError

✅ Aprobado para producción

#### CORE CCC

✅ Render correcto

✅ Sin Traceback

✅ Sin KeyError

✅ Aprobado para producción

#### CORE MiNegocio

✅ Render correcto

✅ Sin Traceback

✅ Sin errores funcionales observados

✅ Aprobado para producción

### Evidencia Operativa Final

render_rep_kilos_core ≈ 24 s

render_rep_ccc_core ≈ 8 s

render_rep_mn_core ≈ 6 s

Sin errores de ejecución observados.

### Resultado Institucional

✅ CORE KILOS estabilizado

✅ CORE CCC estabilizado

✅ CORE MiNegocio estabilizado

✅ Arquitectura CORE validada en producción

✅ BUSINESS RULES consolidado como capa oficial de lógica comercial

### Estado

CERRADO


## EVENTO-2026-10-02-001

### Título

Fin de la Fase de Migración Comercial a CORE

### Fecha

02/10/2026

### Estado

COMPLETADO

### Resultado

La arquitectura comercial basada en:

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

queda formalmente validada para:

✅ KILOS

✅ CCC

✅ MiNegocio

### Próxima Fase Aprobada

FASE 5.0

Control de Integridad del Período Operativo

Objetivos:

- Validación automática de bases mensuales
- Semáforo de integridad del período
- Diagnóstico operativo
- Migración futura de Gerencial a CORE
- Migración futura de Vespertina a CORE


## RESUMEN EJECUTIVO ACTUALIZADO

Estado General:

✅ Producción operativa

Arquitectura:

✅ RAW → SQLITE → STAGING → CORE → BUSINESS RULES → REPORTES

Migraciones completadas:

✅ Kilos

✅ MiNegocio

✅ CCC

Estabilizaciones completadas:

✅ CORE KILOS

✅ CORE CCC

✅ CORE MiNegocio

Validaciones institucionales:

✅ BUSINESS RULES

✅ CORE

✅ STAGING

✅ Kilos

✅ CCC

✅ MiNegocio

Próxima fase:

⏳ Validación de Integridad de Período Operativo

Migraciones futuras:

⏳ CORE GERENCIAL

⏳ CORE VESPERTINA

Nivel de riesgo:

✅ Bajo
