# DECISIONES TÉCNICAS - MATINAL

Versión: 3.0

Fecha de actualización: 30/09/2026

Estado: Vigente

Estado de validación: Producción Operativa

---

# A. DECISIONES ARQUITECTÓNICAS FUNDAMENTALES

## DT.01: Arquitectura Institucional Oficial

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

La arquitectura oficial de MATINAL es:

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

### Objetivo

Separar responsabilidades técnicas, operativas y comerciales.

### Principios

RAW recibe datos.

SQLITE persiste datos.

STAGING normaliza datos.

CORE interpreta operación.

BUSINESS RULES aplica reglas comerciales.

REPORTES presentan resultados.

---

## DT.02: SQLite como Fuente Física Única

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

SQLite constituye la fuente física única de datos del sistema.

### Ubicación

data/matinal.db

### Tecnología

SQLite

### Configuración

WAL (Write Ahead Logging)

### Objetivos

* Reducir lecturas de Excel.
* Mejorar rendimiento.
* Centralizar persistencia.
* Garantizar consistencia.

---

## DT.03: Separación Formal de Capas

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Cada capa posee responsabilidades exclusivas.

### STAGING

Permitido:

* Lectura SQLite
* Tipado
* Normalización
* Parseo de fechas
* Contratos de datos

Prohibido:

* Objetivos
* CCC
* MiNegocio
* Coberturas
* Pace
* KPIs
* Compensaciones
* Lógica comercial

### CORE

Permitido:

* Interpretación operativa
* Calendario
* Clasificación temporal
* Titularidad operativa
* Reemplazos

Prohibido:

* ETL
* Parseos heredados
* Normalización técnica
* KPIs
* Reglas comerciales

### BUSINESS RULES

Permitido:

* CCC
* MiNegocio
* Coberturas
* Objetivos
* Problema de Cierre
* Reglas comerciales institucionales

### REPORTES

Permitido:

* KPIs
* Visualizaciones
* Proyecciones
* Exportaciones
* Dashboards

---

# B. DECISIONES SOBRE STAGING

## DT.10: Implementación Formal de STAGING

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

La capa STAGING se considera implementada y operativa.

### Entidades Activas

* obtener_staging_vta()
* obtener_staging_clientes()
* obtener_staging_rutas()
* obtener_staging_ausencias()
* obtener_staging_maestros()

### Resultado

✅ STAGING implementado.

✅ STAGING validado.

✅ STAGING productivo.

---

## DT.11: STAGING como Dueño Exclusivo del ETL

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Toda transformación técnica debe residir en STAGING.

### Incluye

* Parseo de fechas.
* Tipado.
* Normalización.
* Detección de columnas.
* Conversión de tipos.
* Contratos técnicos.

### Objetivo

Eliminar ETL duplicado en capas superiores.

---

## DT.12: Contratos Obligatorios de STAGING

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Las entidades STAGING deben entregar contratos explícitos y estables.

### STAGING_VTA

Contrato mínimo:

* FechaCarga_dt
* FechaEntrega_dt
* CodVendedor
* Cliente
* PesoKg
* CantBase
* ImporteNetoItem
* Marca

### STAGING_CLIENTES

Contrato mínimo:

* Cliente
* Taxonomia
* NombreCliente
* CodVendedor

### STAGING_AUSENCIAS

Contrato mínimo:

* Fecha_dt
* CodVend_clean
* Reemplazo_clean

---

# C. DECISIONES SOBRE CORE

## DT.20: Implementación Formal de CORE

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

La capa CORE se encuentra implementada y operativa.

### Componentes Activos

* obtener_core_operacion()
* obtener_core_clientes()
* obtener_core_vendedores()
* obtener_core_ventas_base()

### Resultado

✅ CORE implementado.

✅ CORE validado.

✅ CORE productivo.

---

## DT.21: CORE como Dueño de la Interpretación Operativa

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

CORE is responsable de interpretar entidades provenientes de STAGING.

### Responsabilidades

* Construcción de cartera operativa por vendedor.
* Titularidad operativa.
* Vendedor operativo.
* Ausencias.
* Reemplazos.
* Calendario.
* Clasificación temporal.

### Exclusiones

* Objetivos.
* CCC.
* MiNegocio.
* Coberturas.
* KPIs.
* Compensaciones.

---

## DT.22: Clasificación Oficial de Períodos

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Toda transacción debe clasificarse en:

* Arrastre
* Actual
* Futuro
* Fuera de Período

### Implementación

calcular_ritmo_operativo()

---

## DT.23: Gestión Oficial de Reemplazos

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

La reasignación operativa de ventas corresponde exclusivamente a CORE.

### Implementación

procesar_ausencias_y_reemplazos()

### Resultado

CodVendedorOperativo

---

## DT.24: Modelo Vigente de Construcción de Cartera Operativa

### Fecha

04/10/2026

### Estado

Vigente ✅

### Decisión

Se establece formalmente el modelo institucional de construcción de cartera operativa bajo los siguientes principios institucionales:

* UNIVERSO = universo elegible
* VTA = evidencia transaccional válida
* CORE_OPERACION = constructor oficial de cartera operativa
* BUSINESS RULES = consumidores de cartera operativa
* REPORTES = consumidores finales

### Flujo Institucional

VTA
+
UNIVERSO
↓
CORE_OPERACION
↓
Cartera Operativa por Vendedor
↓
Business Rules
↓
Reportes

### Objetivo

* Eliminar dependencia directa de reportes respecto de asignaciones estáticas de cartera.
* Formalizar una única fuente operativa reutilizable.
* Preservar consistencia entre CCC, MiNegocio, Kilos y futuras migraciones.

---

# D. DECISIONES SOBRE AUSENCIAS

## DT.30: Implementación de STAGING_AUSENCIAS

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Se implementa:

obtener_staging_ausencias()

como punto oficial de entrada para ausencias.

### Contrato Oficial

* Fecha_dt
* CodVend_clean
* Reemplazo_clean

---

## DT.31: Cambio de Orquestación de AUSENCIAS

### Fecha

27/09/2026

### Estado

Vigente ✅

### Antes

maestros["ausencias"]

### Después

obtener_staging_ausencias()

### Resultado

* Menor acoplamiento.
* Contratos explícitos.
* Mayor mantenibilidad.

---

## DT.32: Cierre Formal de FASE 4.7

### Fecha

27/09/2026

### Estado

Vigente ✅

### Nombre

Migración de AUSENCIAS a STAGING

### Resultado

✅ Validada en producción.

---

# E. DECISIONES SOBRE BUSINESS RULES

## DT.40: BUSINESS RULES como Capa Institucional Oficial

### Fecha

30/09/2026

### Estado

Vigente ✅

### Decisión

La capa BUSINESS RULES deja de considerarse experimental.

### Estado Arquitectónico

✅ Validada en producción.

✅ Utilizada por múltiples dominios.

✅ Estrategia oficial de evolución del proyecto.

---

## DT.41: Acceso Controlado a Objetivos

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

La consulta institucional de objetivos deberá realizarse mediante:

obtener_objetivos_vendedores()

### Fuente

objetivos_vendedores

### Contrato

* CodVendedor
* SEGMENTO
* Obj_Sugerido_Kg

---

## DT.42: Desacoplamiento de Reportes

### Fecha

29/09/2026

### Estado

Vigente ✅

### Decisión

Los reportes no podrán depender entre sí.

### Permitido

Reporte
↓
Business Rules
↓
Core

### Prohibido

Reporte
↓
Reporte

### Objetivo

Eliminar dependencias cruzadas.

---

## DT.43: Kilos como Patrón de Referencia

### Fecha

29/09/2026

### Estado

Vigente ✅

### Decisión

Kilos constituye el primer patrón oficial de migración.

### Arquitectura

rep_kilos_core.py
↓
business_rules_kilos.py
↓
core_*

---

## DT.44: Validación Productiva de BUSINESS RULES

### Fecha

30/09/2026

### Estado

Vigente ✅

### Decisión

La arquitectura:

Reporte
↓
Business Rules
↓
Core

queda validada mediante implementaciones productivas independientes.

### Implementaciones Validadas

#### Kilos

✅ Productivo

✅ Validado

#### MiNegocio

✅ Productivo

✅ Validado

### Consecuencia

Toda nueva migración deberá adoptar este patrón.

---

## DT.45: MiNegocio como Segundo Patrón de Referencia

### Fecha

30/09/2026

### Estado

Vigente ✅

### Decisión

La migración MiNegocio se considera completada y validada.

### Arquitectura

rep_MN_core.py
↓
business_rules_mn.py
↓
core_*

### Resultado

✅ Desacoplamiento del reporte histórico.

✅ Reutilización de Core institucional.

✅ Compatibilidad con futuras integraciones.

---

## DT.46: Validación Institucional de MiNegocio

### Fecha

30/09/2026

### Estado

Vigente ✅

### Validaciones

TOTAL CARTERA = 5617

CodVendedor -998 = 0

### Resultado

✅ Universo comercial consistente.

✅ Titularidad preservada.

✅ Exportaciones validadas.

---

## DT.47: Prioridad de Migración Arquitectónica

### Fecha

30/09/2026

### Estado

Vigente ✅

### Decisión

Una vez completadas las migraciones de:

* Kilos
* MiNegocio

la siguiente prioridad institucional pasa a ser:

CCC

### Roadmap Aprobado

1. CCC
2. Cobertura Marca
3. Cobertura Innovación
4. Gerencial
5. Vespertina

---

# F. ESTRATEGIA DE MIGRACIÓN

## DT.50: Estrategia de Migración Incremental

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Toda migración deberá seguir:

1. Crear entidad.
2. Consumir desde CORE.
3. Validar en producción.
4. Eliminar duplicidades.

---

## DT.51: Prohibición de Refactorización Masiva

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

No combinar simultáneamente:

* Creación de STAGING.
* Cambio de orquestación.
* Eliminación de lógica heredada.

### Motivo

Reducir riesgo operativo.

---

# G. FASE APROBADA ACTUALMENTE

## DT.60: FASE 4.8

### Estado

⏳ Pendiente

### Nombre

Eliminación de ETL duplicado en CORE

### Objetivo

Eliminar lógica técnica duplicada actualmente presente en:

procesar_ausencias_y_reemplazos()

### Resultado esperado

STAGING = 100% ETL

CORE = 100% Operación

### Restricción

Validación obligatoria en producción posterior.

---

# H. CONSERVACIÓN DEL CONOCIMIENTO

## DT.70: Documentación Mínima Obligatoria

### Estado

Vigente ✅

### Documentos

* ARQUITECTURA.md
* ESTADO_ACTUAL.md
* DECISIONES_TECNICAS.md
* ROADMAP.md
* DICCIONARIO_TABLAS.md
* GLOSARIO_REGLAS.md
* CORE_OPERACION_V1.md
* CORE_VENTAS_BASE_V1.md

---

## DT.71: Prioridad de la Documentación

### Estado

Vigente ✅

### Regla

Ante discrepancias:

Documentación institucional
↓
Código fuente

### Orden de Consulta

1. ESTADO_ACTUAL.md
2. ARQUITECTURA.md
3. ROADMAP.md
4. DECISIONES_TECNICAS.md
5. DICCIONARIO_TABLAS.md
6. GLOSARIO_REGLAS.md
7. CORE_OPERACION_V1.md
8. CORE_VENTAS_BASE_V1.md

---

# I. HISTORIZACIÓN Y TRAZABILIDAD TEMPORAL

## DT.72: Historización Institucional de Universo

### Fecha

02/10/2026

### Estado

Vigente ✅

### Decisión

Se aprueba la historización institucional del Universo Comercial mediante versionado automático de snapshots almacenados en SQLite.

### Contexto

Se identificó la necesidad de preservar la evolución temporal de la cartera comercial para soportar futuras auditorías, reconstrucciones históricas y análisis de cambios de titularidad.

El detonante funcional fue el análisis del caso ID2, donde se observó que un cambio futuro en la asignación de cartera podría eliminar evidencia necesaria para reconstruir apropiaciones históricas.

### Implementación

Se incorporan las siguientes entidades persistidas:

* universo_hist
* universo_versiones

#### universo

Fuente oficial vigente de universo elegible.

Contiene exclusivamente la versión actual del Universo.

#### CORE_OPERACION

Fuente oficial de cartera operativa.

#### universo_hist

Almacena snapshots históricos completos.

Cada registro conserva:

* información original del cliente
* FechaSnapshot
* FechaCargaSistema
* HashSnapshot

Modelo:

Una fila por cliente por versión.

#### universo_versiones

Almacena catálogo de versiones.

Cada registro conserva:

* VersionID
* FechaSnapshot
* FechaCargaSistema
* HashSnapshot
* CantClientes

Modelo:

Una fila por snapshot.

### Regla de Generación

Si el hash del Universo difiere del último snapshot registrado:

* generar snapshot histórico
* registrar versión

Si el hash coincide:

* no generar snapshot
* no registrar versión

### Compatibilidad

La incorporación de la historización no modifica el comportamiento de:

* STAGING
* CORE
* BUSINESS RULES
* REPORTES

Los componentes productivos continúan consumiendo:

universo

como fuente vigente.

### Alcance Futuro

Esta decisión habilita capacidades futuras de:

* auditoría histórica
* reconstrucción de cartera
* análisis de transferencias
* versionado de maestros
* trazabilidad temporal
* apropiación histórica de clientes

### Principio Institucional Derivado

La determinación futura de titularidad podrá considerar simultáneamente:

Cliente
+
Momento Temporal
+
Versión de Universo

en lugar de depender exclusivamente del vendedor actualmente asignado.

### Estado de Validación

✅ universo_hist implementado

✅ universo_versiones implementado

✅ validado mediante SQLite

✅ validado mediante logs productivos

✅ aprobado para futuras evoluciones de CORE_OPERACION

---

# RESUMEN EJECUTIVO

Arquitectura oficial:

RAW → SQLITE → STAGING → CORE → BUSINESS RULES → REPORTES

Estado actual:

✅ STAGING validado

✅ CORE validado

✅ BUSINESS RULES validada

✅ Kilos migrado

✅ MiNegocio migrado

Patrón institucional vigente:

Reporte
↓
Business Rules
↓
Core

### DT.73: Preservación de Titularidad Histórica para Compensaciones

#### Fecha

04/10/2026

#### Estado

Vigente ✅

#### Decisión

Las compensaciones por reemplazo deberán determinarse utilizando la titularidad histórica de la operación cuando dicha información exista.

#### Implementación

Columna:

CodVendedorHistorico

#### Contexto

Durante la auditoría forense de compensaciones realizada sobre el módulo de Kilos se detectó la necesidad de preservar explícitamente la titularidad original de las operaciones antes de cualquier transformación posterior asociada a:

* CodVendedorVigente
* CodVendedorOperativo
* vendedor comodín 99

#### Regla

Si existe:

CodVendedorHistorico

las comparaciones de reemplazo deberán realizarse contra dicha columna.

En ausencia de dicha columna podrá utilizarse:

CodVendedor

como mecanismo de compatibilidad.

#### Objetivo

Evitar pérdida de trazabilidad de titularidad comercial.

Preservar consistencia en compensaciones históricas.

Garantizar balance institucional de reemplazos.

#### Resultado Validado

✅ Compatible con vendedor 99.

✅ Compatible con reasignaciones operativas.

✅ Compatible con CodVendedorVigente.

✅ Balance de compensaciones validado mediante auditoría.

#### Restricción

La existencia de:

CodVendedorVigente

no reemplaza la necesidad de conservar:

CodVendedorHistorico

para fines de auditoría y compensaciones.

### DT.74: Exclusión de Fuera de Período en Compensaciones

#### Fecha

04/10/2026

#### Estado

Vigente ✅

#### Decisión

Las compensaciones por reemplazo sólo podrán considerar operaciones clasificadas como:

* Arrastre
* Actual

#### Exclusiones

No participan:

* Futuro
* Fuera de Período

#### Implementación

calcular_compensaciones_reemplazos()

#### Justificación

Se validó mediante auditoría forense que las compensaciones deben reflejar exclusivamente volumen operativo vigente.

La incorporación de operaciones clasificadas como Fuera de Período alteraría la interpretación comercial del avance mensual.

#### Resultado Validado

✅ Fuera de Período excluido.

✅ Balance de compensaciones consistente.

✅ Resultado compatible con la matriz comercial institucional.

### DT.75: Oficialización del Vendedor Comodín de Reemplazos

#### Fecha

04/10/2026

### Estado

Vigente ✅

### Decisión

El identificador institucional aprobado para operaciones de reemplazo es:

CodVendedor = 99

Nombre:

REEMPLAZO

### Contexto

La auditoría forense de reemplazos confirmó la utilización operativa del vendedor 99 como entidad institucional de consolidación de reemplazos