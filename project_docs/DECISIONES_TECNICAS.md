## Decisiones Técnicas - MATINAL

Versión: 2.0  
Fecha de actualización: 28/09/2026  
Estado: Vigente  
Estado de validación: Producción Operativa

---

# A. Decisiones Arquitectónicas Fundamentales

## DT.01: Arquitectura Institucional Oficial

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

La arquitectura oficial de MATINAL es:

```text
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
```

### Objetivo

Separar responsabilidades técnicas y funcionales.

### Principios

```text
RAW recibe datos.
SQLITE persiste datos.
STAGING normaliza.
CORE interpreta operación.
BUSINESS RULES aplica reglas.
REPORTES presentan resultados.
```

---

## DT.02: SQLite como Fuente Física Única

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

SQLite constituye la fuente física única de datos del sistema.

### Ubicación

```text
data/matinal.db
```

### Tecnología

```text
SQLite
```

### Configuración

```text
WAL (Write Ahead Logging)
```

### Objetivos

```text
Reducir lecturas de Excel.
Aumentar rendimiento.
Centralizar persistencia.
Garantizar consistencia.
```

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

```text
Lectura SQLite
Tipado
Normalización
Parseo de Fechas
Contratos de Datos
```

Prohibido:

```text
Objetivos
CCC
MN+
Coberturas
Pace
Compensaciones
KPIs
Lógica Comercial
```

### CORE

Permitido:

```text
Interpretación Operativa
Calendario
Períodos
Reemplazos
Titularidad Operativa
```

Prohibido:

```text
ETL
Parseos heredados
Normalización técnica
```

### BUSINESS RULES

Permitido:

```text
Aplicación de reglas comerciales
Objetivos
Coberturas
CCC
MN+
Problema de Cierre
```

### REPORTES

Permitido:

```text
KPIs
Proyecciones
Visualizaciones
Compensaciones
Dashboards
```

---

# B. Decisiones sobre STAGING

## DT.10: Implementación Formal de STAGING

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

La capa STAGING se encuentra oficialmente implementada.

### Entidades Activas

```python
obtener_staging_vta()
obtener_staging_clientes()
obtener_staging_rutas()
obtener_staging_ausencias()
obtener_staging_maestros()
```

### Resultado

```text
STAGING implementado y operativo.
```

---

## DT.11: STAGING como Dueño Exclusivo del ETL

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Toda transformación técnica debe residir en STAGING.

### Incluye

```text
Parseo de fechas
Tipado
Normalización
Detección de columnas
Conversión de tipos
Contratos técnicos
```

### Objetivo

Eliminar ETL duplicado en capas superiores.

---

## DT.12: Contratos Obligatorios de STAGING

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Las entidades STAGING deben entregar contratos estables.

### STAGING_VTA

Contrato mínimo:

```text
FechaCarga_dt
FechaEntrega_dt
CodVendedor
Cliente
PesoKg
CantBase
ImporteNetoItem
Marca
```

### STAGING_CLIENTES

Contrato mínimo:

```text
Cliente
Taxonomia
NombreCliente
CodVendedor
```

### STAGING_AUSENCIAS

Contrato mínimo:

```text
Fecha_dt
CodVend_clean
Reemplazo_clean
```

---

# C. Decisiones sobre CORE

## DT.20: Implementación Formal de CORE

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

La capa CORE se encuentra implementada y operativa en producción.

### Componentes Activos

```python
procesar_ausencias_y_reemplazos()
calcular_ritmo_operativo()
calcular_calendario_y_rutas()
obtener_core_operacion()
```

### Resultado

```text
CORE implementado.
CORE validado.
CORE operativo.
```

---

## DT.21: CORE como Dueño de la Interpretación Operativa

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

CORE es responsable de interpretar entidades provenientes de STAGING.

### Responsabilidades

```text
Titularidad operativa
Vendedor operativo
Ausencias
Reemplazos
Calendario
Clasificación temporal
```

### No Responsabilidades

```text
Objetivos
CCC
MN+
Coberturas
KPIs
Compensaciones
```

---

## DT.22: Clasificación Oficial de Períodos

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Toda transacción debe clasificarse en uno de los siguientes estados:

```text
Arrastre
Actual
Futuro
Fuera de Periodo
```

### Implementación

```python
calcular_ritmo_operativo()
```

---

## DT.23: Gestión Oficial de Reemplazos

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

La reasignación operativa de ventas corresponde a CORE.

### Implementación

```python
procesar_ausencias_y_reemplazos()
```

### Resultado

```text
CodVendedorOperativo
```

---

# D. Decisiones sobre AUSENCIAS

## DT.30: Implementación de STAGING_AUSENCIAS

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Se implementa la entidad:

```python
obtener_staging_ausencias()
```

como puerta oficial de entrada para ausencias.

### Responsabilidades

```text
Lectura SQLite
Detección de columnas
Parseo robusto
Tipado
Normalización
```

### Contrato Oficial

```text
Fecha_dt
CodVend_clean
Reemplazo_clean
```

---

## DT.31: Cambio de Orquestación de AUSENCIAS

### Fecha

27/09/2026

### Estado

Vigente ✅

### Antes

```python
maestros["ausencias"]
```

### Después

```python
obtener_staging_ausencias()
```

### Resultado

```text
Menor acoplamiento.
Contratos explícitos.
Mayor mantenibilidad.
```

---

## DT.32: Cierre Formal de la Fase 4.7

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

La Fase 4.7 se encuentra cerrada.

### Nombre

```text
Migración de AUSENCIAS a STAGING
```

### Resultado

```text
Validada en producción.
```

### Verificaciones

```text
Arranque Streamlit
Carga SQLite
Ejecución STAGING
Ejecución CORE
Integración AUSENCIAS
Renderizado de reportes
Sin errores de ejecución
```

---

# E. Decisiones sobre BUSINESS RULES

## DT.40: Estado Actual de BUSINESS RULES

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

La capa BUSINESS RULES existe y se encuentra parcialmente desacoplada.

### Situación Actual

Implementado:

```python
business_rules_repository.py
```

Disponible:

```python
obtener_objetivos_vendedores()
```

### Estado Arquitectónico

```text
Parcialmente desacoplado.
En evolución.
```

---

## DT.41: Acceso Controlado a Objetivos

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

La consulta de objetivos debe realizarse mediante:

```python
obtener_objetivos_vendedores()
```

### Fuente

```text
objetivos_vendedores
```

### Contrato

```text
CodVendedor
SEGMENTO
Obj_Sugerido_Kg
```

---

# F. Estrategia de Migración Arquitectónica

## DT.50: Estrategia de Migración Incremental

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Toda migración arquitectónica deberá seguir el siguiente proceso:

```text
ETAPA 1
Crear entidad STAGING

ETAPA 2
Consumir desde CORE

ETAPA 3
Validar en producción

ETAPA 4
Eliminar duplicidades
```

### Objetivo

Reducir riesgo operativo.

---

## DT.51: Prohibición de Refactorización Masiva

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

No combinar simultáneamente:

```text
Creación de STAGING
Cambio de Orquestación
Eliminación de Lógica Heredada
```

en una única iteración.

### Motivo

```text
Facilitar detección de regresiones.
```

---

# G. Próxima Fase Aprobada

## DT.60: Fase 4.8

### Estado

Pendiente ⏳

### Nombre

```text
Eliminación de ETL duplicado en CORE
```

### Objetivo

Eliminar lógica técnica redundante de:

```python
procesar_ausencias_y_reemplazos()
```

### Elementos Candidatos

```text
cols_vend_cand
cols_f_cand
cols_reemp_cand
parsear_fecha_robusta()
CodVend_clean
Reemplazo_clean
```

### Resultado Esperado

```text
STAGING = 100% ETL
CORE = 100% Operación
```

### Restricción

```text
Requiere validación en producción posterior.
```

---

# H. Conservación del Conocimiento Institucional

## DT.70: Documentación Mínima Obligatoria

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Los siguientes documentos constituyen la memoria institucional mínima obligatoria del sistema:

```text
ARQUITECTURA.md
ESTADO_ACTUAL.md
DECISIONES_TECNICAS.md
ROADMAP.md
DICCIONARIO_TABLAS.md
GLOSARIO_REGLAS.md
CORE_OPERACION_V1.md
CORE_VENTAS_BASE_V1.md
```

### Objetivo

Permitir reconstruir el contexto técnico y funcional completo independientemente de conversaciones previas.

---

## DT.71: Prioridad de la Documentación

### Fecha

27/09/2026

### Estado

Vigente ✅

### Decisión

Ante discrepancias:

```text
Documentación institucional
↓
Código fuente
```

### Orden de Consulta

```text
ARQUITECTURA.md
ESTADO_ACTUAL.md
ROADMAP.md
DECISIONES_TECNICAS.md
DICCIONARIO_TABLAS.md
GLOSARIO_REGLAS.md
CORE_OPERACION_V1.md
CORE_VENTAS_BASE_V1.md
```

---

## Estado General

```text
RAW               ✅
SQLITE            ✅
STAGING           ✅
CORE              ✅
BUSINESS RULES    🟡 Parcial
REPORTES          ✅
```

## Estado de Fase

```text
FASE 4.7 COMPLETADA ✅
FASE 4.8 APROBADA ⏳
```
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

### Motivación

Reducir acoplamiento.
Facilitar mantenimiento.
Permitir reutilización de reglas comerciales.

### Aplicación

Toda nueva migración deberá seguir este criterio.
## DT.43: Kilos como Patrón de Referencia

### Fecha

29/09/2026

### Estado

Vigente ✅

### Decisión

La migración de Kilos se considera el patrón oficial para futuras migraciones.

### Patrón aprobado

rep_kilos_core.py
↓
business_rules_kilos.py
↓
core_*

### Aplicación futura

MiNegocio
CCC
Cobertura
Gerencial
Vespertina