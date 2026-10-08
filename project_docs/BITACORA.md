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

* Fecha_dt
* CodVend_clean
* Reemplazo_clean

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

* Clasificación Digital
* No Digital
* Híbrido
* Fully Digital
* Pct_MiNegocio
* Minimo_Facturacion_70
* Matriz comercial por cliente
* Adopción por vendedor
* Adopción por taxonomía

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

✅ CCC

Validaciones institucionales:

✅ BUSINESS RULES

✅ MiNegocio

✅ CORE

✅ STAGING

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

* Validación automática de bases mensuales
* Semáforo de integridad del período
* Diagnóstico operativo
* Migración futura de Gerencial a CORE
* Migración futura de Vespertina a CORE

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

### INC-2026-10-02-002

#### Título

Implementación de Historización de Universo

#### Fecha de Apertura

02/10/2026

#### Fecha de Cierre

02/10/2026

#### Contexto

Durante el análisis del Caso ID2 se identificó la necesidad de preservar la evolución histórica de la cartera comercial.

La estructura existente conservaba únicamente el estado vigente del Universo.

#### Objetivo

Incorporar capacidades de auditoría y reconstrucción histórica sin modificar el funcionamiento operativo actual.

#### Implementación

Creación de:

* universo_hist
* universo_versiones

Implementación de snapshot automático basado en HashSnapshot.

#### Validaciones Ejecutadas

✅ creación de tablas

✅ validación de estructura

✅ validación de persistencia

✅ validación mediante logs

✅ validación mediante consultas SQLite

#### Evidencia

Se verificó:

* universo_versiones creada correctamente
* snapshot registrado correctamente
* hash registrado correctamente
* CantClientes registrado correctamente

#### Resultado Institucional

✅ historización operativa

✅ catálogo de versiones operativo

✅ trazabilidad temporal disponible

✅ preparado para futuras auditorías de cartera

✅ preparado för análisis futuro del Caso ID2

#### Estado

CERRADO

---

### EVENTO-2026-10-02-002

#### Título

Aprobación de Historización Institucional de Universo

#### Fecha

02/10/2026

#### Estado

COMPLETADO

#### Resultado

La plataforma incorpora formalmente persistencia histórica del Universo Comercial mediante:

* universo
* universo_hist
* universo_versiones

#### Alcance Futuro Aprobado

* reconstrucción histórica
* auditoría temporal
* administración SQL
* análisis retrospectivo de cartera
* futuras evoluciones de CORE_OPERACION

#### Observación

La iniciativa surge del análisis del Caso ID2 y constituye la primera implementación institucional de versionado de entidades maestras.
CORRECCION_UNIVERSO_SQLITE_2026

* universo SQLite sincronizado 1:1 con UNIVERSO.xlsx
* eliminación de esquema heredado incorrecto
* corrección automática de schema drift en universo_hist
* carga validada exitosamente
* versión estable de database.py aprobada
``

## INC-2026-10-04-001

### Título

Auditoría Forense de Compensaciones por Reemplazo

### Fecha de Apertura

04/10/2026

### Estado

ABIERTO

### Objetivo

Determinar la causa raíz de diferencias observadas en compensaciones por reemplazo dentro del módulo KILOS y validar la consistencia funcional de:

* CodVendedorHistorico
* CodVendedorOperativo
* CodVendedorVigente
* vendedor comodín 99
* calcular_compensaciones_reemplazos()

### Contexto

Durante la validación operativa de KILOS se observó un volumen de compensación elevado para determinados vendedores, particularmente:

CodVendedor = 11

ORTIZ

El análisis inicial sugería posibles problemas asociados a:

* vendedor 99
* migración desde -998
* CodVendedorHistorico
* participación de ventas Fuera de Período
* desbalance de compensaciones

Se inició auditoría forense completa utilizando únicamente evidencia observable.

### Componentes Auditados

#### CORE

* core_operaciones.py
* obtener_core_operacion()
* procesar_ausencias_y_reemplazos()

#### BUSINESS RULES

* business_rules_kilos.py
* calcular_compensaciones_reemplazos()

### Evidencia Relevante

#### Validación de Exclusión de Fuera de Período

Se verificó en:

calcular_compensaciones_reemplazos()

la existencia del filtro:

Periodo ∈ {Arrastre, Actual}

Resultado:

✅ Fuera de Período excluido de compensaciones.

#### Validación de Titularidad Histórica

Se verificó la existencia de:

CodVendedorHistorico

creada antes de la reasignación hacia:

CodVendedorVigente

Resultado:

✅ Titularidad histórica preservada.

#### Validación del Vendedor Comodín

Se verificó:

CodVendedor = 99

Nombre = REEMPLAZO

Resultado:

✅ Identificador operativo válido.

#### Validación de Eliminación de -998

Resultado:

✅ -998 descartado como mecanismo vigente de compensación.

### Auditoría de Reemplazos

Para:

Octubre 2026

se auditó:

CodVendedorOperativo = 99

Resultado:

Actual = 158.941 kg

Distribución validada:

CodVendedor 11 → 86.504 kg

CodVendedor 25 → 68.973 kg

CodVendedor 10 → 3.464 kg

Total:

158.941 kg

Resultado:

✅ Conservación de masa validada.

✅ Balance contable validado.

### Caso Principal Auditado

#### Vendedor

CodVendedor = 11

ORTIZ

#### Evidencia

Se identificaron:

228 movimientos reales

asociados a:

CodVendedorOperativo = 99

para operaciones clasificadas dentro del período operativo vigente.

#### Segmentación Auditada

GOLD Salty      = 46.712 kg

GOLD Crakers    = 5.525 kg

SILVER Salty    = 13.867 kg

SILVER Crakers  = 2.790 kg

SILVER Cereals  = 0.470 kg

Total auditado:

69.364 kg

### Hipótesis Descartadas

Se descartó evidencia de:

❌ Participación de Fuera de Período.

❌ Desbalance de compensaciones.

❌ Error de vendedor 99.

❌ Error derivado de -998.

❌ Falla observable en CodVendedorHistorico.

❌ Generación artificial de kilos.

### Hallazgos Confirmados

✅ Compensaciones construidas exclusivamente sobre Arrastre y Actual.

✅ Balance completo entre titular y reemplazante.

✅ Vendedor 99 recibe únicamente kilos provenientes de operaciones reales.

✅ CodVendedorHistorico preserva correctamente la titularidad original para compensaciones.

✅ El volumen transferido a 99 proviene principalmente de vendedores:

* 11
* 25
* 10

### Investigación Pendiente

Determinar el origen exacto de la diferencia residual observada entre:

* kilos transferidos auditados por segmento
* kilos visibles en matriz comercial final

Líneas actualmente abiertas:

* segmentación comercial
* clasificación por Rubro
* clasificación por Familia
* exclusiones posteriores al cálculo operativo

### Resultado Parcial

No se encontró evidencia suficiente para afirmar la existencia de un bug en:

calcular_compensaciones_reemplazos()

La investigación continúa abierta hasta identificar el primer punto exacto de divergencia entre la auditoría de origen y la matriz comercial final.

---

# INC-2026-10-06-001

## Título

Auditoría Forense de Distribución de Objetivos sobre Universo Vigente

## Fecha de Apertura

06/10/2026

## Fecha de Cierre

06/10/2026

## Contexto

Durante la validación funcional del módulo de Objetivos se detectó una diferencia entre:
Objetivo Corporativo:
61.300 kg
Objetivo Visible:
61.227,37 kg
Diferencia:
72,630941 kg
Se inició una auditoría forense completa utilizando exclusivamente evidencia observable.

## Componentes Auditados

CORE

* core_potencial_cliente_segmento.py
BUSINESS RULES
* business_rules_objetivo_clientes.py
* business_rules_objetivo_carteras.py
* business_rules_objetivo_segmentos.py

## Hallazgos Confirmados

* 93 clientes fuera de Universo participaban en la distribución.
* Generaban 71,647538 kg.
* Clasificación:
CLIENTE_SIN_CARTERA

## Composición auditada

CLIENTE_SIN_CARTERA:
71,647538 kg
VENDEDOR_NO_ASIGNADO:
0,983403 kg
TOTAL:
72,630941 kg

## Causa Raíz

business_rules_objetivo_clientes utilizaba la población proveniente de core_potencial_cliente_segmento sin filtrado previo contra el universo vigente.

## Corrección Implementada

Filtrado obligatorio mediante:
SELECT Codigo FROM universo
antes del cálculo de:

* ParticipacionMarcaSegmento
* ParticipacionClienteDentroSegmento
* ObjetivoClienteKg

## Validaciones Ejecutadas

✅ Auditoría de población.
✅ Auditoría de universo vigente.
✅ Validación matemática de conservación de masa.
✅ Validación de distribución de objetivos.
✅ Identificación de diferencias residuales.

## Resultado

SUM ObjetivoClienteKg:
61.300 kg
Resultado visible posterior:
61.299,02 kg
Diferencia residual:
0,983403 kg

## Auditoría Residual

Cliente:
46987
Razon Social:
LAURA
Hallazgos:
✅ Existe en Universo.
❌ Sin codven.
❌ Sin Ruta.
Resultado:
Clasificación:
VENDEDOR_NO_ASIGNADO
Objetivo:
0,983403 kg

## Resultado Institucional

✅ Distribución validada sobre universo vigente.
✅ Clientes fuera de universo excluidos de la distribución.
✅ Conservación de masa validada.
✅ Identificación completa de la diferencia residual.

## Conclusión

Los 71,647538 kg asociados a clientes fuera de universo quedaron eliminados de la distribución.
La diferencia residual restante corresponde exclusivamente a datos maestros incompletos del cliente 46987 y no a una falla del algoritmo.

## Estado

CERRADO