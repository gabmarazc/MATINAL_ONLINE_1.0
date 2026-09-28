# CONTEXTO IA - MATINAL

## RESUMEN EJECUTIVO


Proyecto: MATINAL

Estado:
Producción Operativa

Objetivo:
Permitir que una nueva IA o una nueva sesión de Copilot
continúe el proyecto sin pérdida de contexto.

Arquitectura Oficial:

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

Prioridad de lectura:

1. ARQUITECTURA.md
2. ESTADO_ACTUAL.md
3. ROADMAP.md
4. DECISIONES_TECNICAS.md
5. DICCIONARIO_TABLAS.md
6. GLOSARIO_REGLAS.md
7. CORE_OPERACION_V1.md
8. CORE_VENTAS_BASE_V1.md
9. BITACORA.md


====================================================================================================

# DOCUMENTO: ARQUITECTURA.md

# Arquitectura del Sistema MATINAL 2.0
Versión: 2.0
Fecha de actualización: 27/09/2026
Estado: Vigente
Estado de validación: Producción operativa

---

# 1. Propósito del Documento

Este documento constituye la definición oficial de la arquitectura del Sistema MATINAL 2.0.

Su objetivo es preservar el conocimiento arquitectónico del proyecto y permitir la reconstrucción completa del contexto funcional, técnico y evolutivo aun cuando se pierda el historial de conversaciones o se inicie una nueva sesión de desarrollo.

Ante cualquier discrepancia entre documentación y código:

1. Revisar este documento.
2. Revisar DECISIONES_ARQUITECTURALES.md.
3. Revisar ESTADO_ACTUAL_PROYECTO.md.
4. Recién después analizar el código fuente.

---

# 2. Arquitectura Oficial Vigente

La arquitectura institucional aprobada es:

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

Esta arquitectura reemplaza progresivamente el modelo histórico basado en pipelines descentralizados.

---

# 3. Arquitectura Física Actual

## Punto de entrada

app.py

Responsabilidades:

- Inicio del sistema
- Gestión de sesión
- Gestión de autenticación
- Renderizado de pestañas
- Orquestación visual global

---

## Persistencia

Ubicación:

data/matinal.db

Tecnología:

SQLite

Modo:

WAL (Write Ahead Logging)

Características:

- Fuente única de verdad del sistema
- Persistencia local
- Carga desacoplada de Excel
- Alto rendimiento de lectura

---

## Directorio modules/

Contiene:

### Persistencia

database.py

### Configuración

parametros.py

### Utilidades

utils.py

### Reportes

rep_gerencial.py
rep_kilos.py
rep_ccc.py
rep_MN.py
rep_cob_marca.py
rep_cob_innovacion.py
rep_obj_kilos.py
rep_vespertina.py

### Arquitectura institucional

staging.py
core/

---

# 4. Capas Arquitectónicas

## 4.1 RAW

Responsabilidad:

Recepción de información proveniente de archivos externos.

Fuentes principales:

- VTA.xlsx
- UNIVERSO.xlsx
- RUTAS.xlsx
- ALTAS.xlsx
- AUSENCIAS
- Maestros corporativos

Características:

- Datos sin normalizar
- Pueden contener errores
- No son consumidos directamente por reportes

Regla:

No contiene lógica de negocio.

---

## 4.2 SQLITE

Responsabilidad:

Persistir físicamente los datos del sistema.

Objetivos:

- Evitar múltiples lecturas de Excel
- Mejorar rendimiento
- Crear una fuente común de datos

Tablas principales:

- vta
- universo
- rutas
- ausencias
- maestro_vendedores
- maestro_ccc
- maestro_segmentos
- maestro_marcas_cebe

Regla:

No contiene lógica de negocio.

---

## 4.3 STAGING

Estado:

IMPLEMENTADO

Propósito:

Normalizar datos provenientes de SQLite.

Responsabilidades permitidas:

- Lectura SQLite
- Detección de columnas
- Parseo de fechas
- Tipado
- Normalización
- Estandarización de nombres
- Limpieza técnica

Responsabilidades prohibidas:

- Objetivos
- Compensaciones
- Pace
- CCC
- MN+
- KPIs
- Negocio

---

# 5. Funciones STAGING Actuales

## obtener_staging_vta()

Responsabilidad:

Normalización de ventas.

Salida garantizada:

- FechaCarga_dt
- FechaEntrega_dt
- CodVendedor
- Cliente
- CantBase
- ImporteNetoItem
- Marca

---

## obtener_staging_clientes()

Responsabilidad:

Normalización del universo de clientes.

Salida garantizada:

- Cliente
- Taxonomia
- NombreCliente
- CodVendedor

---

## obtener_staging_rutas()



====================================================================================================

# DOCUMENTO: ESTADO_ACTUAL.md

# Estado Actual del Proyecto - MATINAL

Versión: 2.0
Fecha de actualización: 27/09/2026
Estado: Producción Operativa
Estado de validación: Confirmado mediante ejecución real

---

# 1. Identificación del Producto

Nombre:

MATINAL

Descripción:

Sistema institucional de análisis, monitoreo, control operativo y seguimiento comercial para la gestión integral de preventa.

Estado:

Producto productivo en operación diaria.

Frecuencia de uso:

Múltiples veces por día por usuarios operativos, supervisión y gerencia.

---

# 2. Estado General del Proyecto

Estado global:

ESTABLE

Estado productivo:

OPERATIVO

Estado arquitectónico:

EN TRANSICIÓN CONTROLADA HACIA ARQUITECTURA POR CAPAS

Nivel de riesgo:

BAJO

Última validación integral:

27/09/2026

Resultado:

EXITOSO

---

# 3. Arquitectura Vigente

Arquitectura oficial:

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

Estado de implementación:

RAW
✅

SQLITE
✅

STAGING
✅

CORE
✅

BUSINESS RULES
🟡 Parcialmente desacoplado

REPORTES
✅

---

# 4. Estado de la Fase Arquitectónica Actual

Fase institucional actual:

FASE 4

Subfase actual:

FASE 4.7 COMPLETADA

Nombre:

Migración de AUSENCIAS a STAGING

Resultado:

VALIDADA

Estado:

CERRADA

---

# 5. Cambio Arquitectónico Más Importante Realizado

Se implementó:

obtener_staging_ausencias()

como puerta de entrada especializada para el procesamiento técnico de ausencias.

---

## Situación anterior

Las ausencias se obtenían mediante:

maestros["ausencias"]

y el procesamiento técnico permanecía íntegramente dentro del CORE.

---

## Situación actual

El sistema utiliza:

obtener_staging_ausencias()

para:

- lectura SQLite
- detección de columnas
- parseo de fechas
- normalización
- tipado

---

## Impacto

Separación efectiva entre:

STAGING
y
CORE

sin afectar producción.

---

# 6. Validación Real Ejecutada

Fecha:

27/09/2026

Resultado:

ÉXITO

Log validado:

obtener_staging_ausencias → 0.0087 s

procesar_ausencias_y_reemplazos → 0.7176 s

obtener_core_operacion → 13.4367 s

obtener_matriz_kilos_comercial → 14.6438 s

---

## Verificaciones realizadas

✅ Arranque de Streamlit

✅ Carga SQLite

✅ Ejecución STAGING

✅ Ejecución CORE

✅ Renderizado reportes

✅ Integración AUSENCIAS

✅ Sin errores de importación

✅ Sin NameError

✅ Sin KeyError

✅ Sin tracebacks

---

# 7. Módulos Operativos en Producción

Todos los siguientes módulos se encuentran activos.

---

## Dashboard Gerencial

Estado:

PRODUCTIVO

Funciones:

- seguimiento directivo
- consolidación comercial
- proyecciones

---

## CCC

Estado:

PRODUCTIVO

Funciones:

- cartera
- altas
- reactivaciones
- batalla NC

---

## Mi Negocio

Estado:

PRODUCTIVO

Funciones:

- adopción digital
- clasificación digital
- gap a objetivo

---

## Kilos

Estado:

PRODUCTIVO

Funciones:

- avance kilos
- objetivos
- proyección
- compensaciones
- reemplazos

---

## Cobertura Marca

Estado:

PRODUCTIVO

---

## Cobertura Innovación

Estado:

PRODUCTIVO

---

## Objetivos

Estado:

PRODUCTIVO

---

## Parámetros

Estado:

PRODUCTIVO

---

## Vespertina

Estado:

PRODUCTIVO

---

# 8. Roles Activos

Nivel 1

Administrador

Acceso total.

---

Nivel 2

Gerencia

Acceso directivo.

---

Nivel 3

Supervisión

Acceso operativo controlado.

---

# 9. Stack Tecnológico Vigente

Backend:

- Python

Procesamiento:

- Pandas
- NumPy
- OpenPyXL

Interfaz:

- Streamlit
- AgGrid

Persistencia:

- SQLite WAL

---

# 10. Fuente de Verdad Institucional

Los siguientes conceptos poseen prioridad absoluta sobre cualquier decisión técnica:

- Día Matinal
- Problema de Cierre
- Filtro N1
- Filtro N2
- Ausencias
- Reemplazos
- Objetivos
- Universo Operativo
- Coberturas
- Estructura Comercial

Si alguna optimización contradice estos principios:

debe rechazarse.

---

# 11. Próxima Fase

FASE 4.8

Nombre:

Eliminación de ETL duplicado en CORE.

Objetivo:

Retirar de:

procesar_ausencias_y_reemplazos()

la lógica que ya existe en:

obtener_staging_ausencias()

---

## Elementos candidatos a eliminar

- detección de columnas
- parseo de fechas
- CodVend_clean
- Reemplazo_clean

---

## Objetivo final

CORE:

solo l

====================================================================================================

# DOCUMENTO: ROADMAP.md

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

====================================================================================================

# DOCUMENTO: DECISIONES_TECNICAS.md

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

====================================================================================================

# DOCUMENTO: DICCIONARIO_TABLAS.md

# Diccionario de Tablas - MATINAL (Versión 1.0)

## 1. Identificación y Propósito
El presente documento constituye la **Fuente de Verdad Institucional** para la estructura de datos que sostiene el motor analítico de MATINAL. Documenta de forma exhaustiva las tablas físicas alojadas en la base de datos local SQLite (`data/matinal.db`) y sus equivalentes lógicas provenientes de las fuentes Excel de ingesta externa[cite: 1].

---

## 2. Inventario Normativo de Estructuras de Datos

### A. Tablas Transaccionales
*   **1. vta**
    *   **Nombre Técnico**: `vta`[cite: 2]
    *   **Clasificación**: Transaccional[cite: 2]
    *   **Origen**: Archivo Excel `VTA.xlsx` (~133 MB)[cite: 1].
    *   **Descripción Funcional**: Contiene el registro histórico y operativo bruto de todas las transacciones de ventas comerciales de la compañía procesadas por la fuerza de preventa[cite: 1].
    *   **Fuente de Datos**: Archivo Excel periódico cargado mediante `data_loader.py` y persistido por `database.py`.
    *   **Clave Primaria Efectiva**: Ninguna (tabla plana basada en registros secuenciales de origen).
    *   **Campos Principales**: `CodVendedor`, `Cliente`, `FechaCarga`, `FechaEntrega`, `PesoKg`, `ImporteNetoItem`, `CantBase`, `Marca`, `Subramo`, `TipoDeVenta`, `Proveedor`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Subramo` (Filtro N1 Empleados), `TipoDeVenta` (Exclusión comodatos), `Proveedor` (Filtro PepsiCo), `FechaCarga` (Corte Día Matinal), `CodVendedor` (Exclusión Depósito 20)[cite: 2, 3].
    *   **Módulos Consumidores**: `database.py`, `data_loader.py`, y todos los submódulos analíticos de reportes (`rep_*.py`)[cite: 2].
    *   **Frecuencia de Actualización**: 3 veces al día en producción.
    *   **Observaciones Operativas**: Es la tabla de mayor volumetría (~350 MB en SQLite junto con índices). Cuenta con índices optimizados en `CodVendedor`, `Cliente`, `FechaCarga`, `FechaEntrega` y `Marca`[cite: 2].

---

### B. Tablas Maestras
*   **2. universo**
    *   **Nombre Técnico**: `universo`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Archivo Excel `UNIVERSO.xlsx`[cite: 1].
    *   **Descripción Funcional**: Padrón oficial de cartera de clientes activos, conteniendo su segmentación, taxonomía (A/B/C/D), direcciones y asignación comercial[cite: 1].
    *   **Fuente de Datos**: Archivo Excel periódico procesado por `data_loader.py`.
    *   **Clave Primaria Efectiva**: Ninguna en origen (identificado lógicamente por `Codigo` / `Cliente`).
    *   **Campos Principales**: `Codigo` (o `Cliente`), `SegmentoClienteCodigo` (Taxonomía), `CodVen`, `Razon_Social`, `Subramo`, `Direccion`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `SegmentoClienteCodigo` (Taxonomías A, B, C, D), `Subramo` (Exclusión empleados), `CodVen`[cite: 2, 3].
    *   **Módulos Consumidores**: `data_loader.py`, `rep_ccc.py`, `rep_MN.py`, `rep_gerencial.py`, `rep_vespertina.py`[cite: 3, 5].
    *   **Frecuencia de Actualización**: Periódica / Mensual.
    *   **Observaciones Operativas**: Sus campos sufren un proceso de renombrado dinámico en `data_loader.py` para normalizar referencias a `Cliente` y `Taxonomia`.

*   **3. rutas**
    *   **Nombre Técnico**: `rutas`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Archivo Excel `RUTAS.xlsx`[cite: 1].
    *   **Descripción Funcional**: Calendario de visitas planificadas por preventista y fecha, base fundamental para el cálculo de días hábiles transcurridos y restantes del mes[cite: 1].
    *   **Fuente de Datos**: Archivo Excel periódico procesado por `data_loader.py`.
    *   **Clave Primaria Efectiva**: Ninguna.
    *   **Campos Principales**: `Fecha`, `CodVen` (o `CodVendedor`), campos de día de visita o ruta[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Fecha` (para acotar el corte con el Día Venta), `CodVen`[cite: 2].
    *   **Módulos Consumidores**: `data_loader.py`, `rep_kilos.py`, `rep_gerencial.py`.
    *   **Frecuencia de actualización**: Mensual.
    *   **Observaciones Operativas**: Se procesa vectorialmente para extraer y unificar el día de la semana correspondiente a cada visita.

*   **4. altas** (y sub-tablas `altas_*` por solapa)
    *   **Nombre Técnico**: `altas` / `altas_{sheet}`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Archivo Excel multi-solapa `ALTAS.xlsx`[cite: 3].
    *   **Descripción Funcional**: Registro mensual de movimientos de cartera (creaciones, activaciones, inactivaciones y cierres definitivos) utilizado para el cálculo de la Cartera Neta en el módulo CCC[cite: 3].
    *   **Fuente de Datos**: Archivo Excel procesado por `database.py` e hidratado por `data_loader.py`[cite: 2].
    *   **Clave Primaria Efectiva**: Ninguna.
    *   **Campos Principales**: `Fecha`, `Codigo` (Cliente), `Estado`, `Vendedor`, `Origen_Hoja`[cite: 3].
    *   **Campos Críticos para Reglas de Negocio**: `Origen_Hoja` (diferencia 'Creacion', 'Activacion', 'Inactivacion'), `Estado` (exclusión de 'CIERRE DEFINITIVO')[cite: 3].
    *   **Módulos Consumidores**: `database.py`, `data_loader.py`, `rep_ccc.py`[cite: 2, 3].
    *   **Frecuencia de actualización**: Mensual.
    *   **Observaciones Operativas**: Como respaldo, si la tabla SQL está vacía, el código intenta leer directamente el archivo físico `ALTAS.xlsx` en disco[cite: 3].

*   **5. maestro_vendedores**
    *   **Nombre Técnico**: `maestro_vendedores`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Módulo de Parámetros / Excel consolidado multi-solapa (`Maestro_Vendedores`)[cite: 2].
    *   **Descripción Funcional**: Padrón normativo de preventistas con asignación de supervisores, días de ajuste y rutas ajustadas específicas por período[cite: 2].
    *   **Fuente de Datos**: Importación manual desde interfaz de Parámetros[cite: 2].
    *   **Clave Primaria Efectiva**: `Codigo_Vendedor` (versionado por período Anio/Mes)[cite: 2].
    *   **Campos Principales**: `Anio`, `Mes`, `Codigo_Vendedor`, `Nombre_Vendedor`, `Supervisor`, `Rutas_Ajustadas`, `Ajuste_Entrega`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Supervisor` (para filtros gerenciales y de supervisión), `Rutas_Ajustadas` (para cálculo de días restantes ajustados)[cite: 2].
    *   **Módulos Consumidores**: `app.py`, `database.py`, `parametros.py`, `rep_kilos.py`, `rep_gerencial.py`, `rep_ccc.py`[cite: 2].
    *   **Frecuencia de actualización**: Mensual / Versionada[cite: 2].
    *   **Observaciones Operativas**: Clave para la vinculación jerárquica con los preventistas y supervisores en todos los reportes.

*   **6. maestro_segmentos**
    *   **Nombre Técnico**: `maestro_segmentos`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Módulo de Parámetros / Excel consolidado multi-solapa (`Maestro_Segmentos`)[cite: 2].
    *   **Descripción Funcional**: Catálogo oficial de segmentos comerciales vigentes (ej. GOLD Salty, SILVER Salty, etc.)[cite: 2].
    *   **Fuente de Datos**: Importación manual desde Parámetros[cite: 2].
    *   **Clave Primaria Efectiva**: `Segmento` (versionado por período Anio/Mes)[cite: 2].
    *   **Campos Principales**: `Anio`, `Mes`, `Segmento`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Segmento`[cite: 2].
    *   **Módulos Consumidores**: `database.py`, `parametros.py`, `rep_kilos.py`, `rep_gerencial.py`, `rep_obj_kilos.py`[cite: 2].
    *   **Frecuencia de actualización**: Mensual / Versionada[cite: 2].

*   **7. maestro_marcas_cebe**
    *   **Nombre Técnico**: `maestro_marcas_cebe`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Módulo de Parámetros / Excel consolidado multi-solapa (`Maestro_Marcas_CEBE`)[cite: 2].
    *   **Descripción Funcional**: Relación de marcas corporativas con unidades de negocio (CEBE) y objetivos macro de toneladas, gross y cobertura[cite: 2].
    *   **Fuente de Datos**: Importación manual desde Parámetros[cite: 2].
    *   **Clave Primaria Efectiva**: `Marca` / `CEBE` (versionado por período Anio/Mes)[cite: 2].
    *   **Campos Principales**: `Anio`, `Mes`, `Marca`, `CEBE`, `Obj_TN_Mes`, `Obj_Gross_Mes`, `Obj_Pepsico_Cobertura`, `Obj_Empresa_Cobertura`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: Objetivos de cobertura y metas macro[cite: 2].
    *   **Módulos Consumidores**: `database.py`, `parametros.py`, `rep_kilos.py`, `rep_gerencial.py`[cite: 2].
    *   **Frecuencia de actualización**: Mensual / Versionada[cite: 2].

*   **8. maestro_innovaciones**
    *   **Nombre Técnico**: `maestro_innovaciones`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Módulo de Parámetros / Excel consolidado multi-solapa (`Maestro_Innovaciones`)[cite: 2].
    *   **Descripción Funcional**: Catálogo de artículos considerados lanzamientos o innovaciones estratégicas auditados por el sistema[cite: 2].
    *   **Fuente de Datos**: Importación manual desde Parámetros[cite: 2].
    *   **Clave Primaria Efectiva**: `(Anio, Mes, Codigo, Innovacion)`[cite: 2].
    *   **Campos Principales**: `Anio`, `Mes`, `Codigo`, `Articulo`, `Innovacion`, `Condicion_Vta`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Codigo`, `Innovacion`[cite: 2].
    *   **Módulos Consumidores**: `database.py`, `parametros.py`, `rep_cob_innovacion.py`[cite: 2, 4].
    *   **Frecuencia de actualización**: Mensual / Versionada[cite: 2].

---

### C. Tablas de Parámetros
*   **9. parametros**
    *   **Nombre Técnico**: `parametros`[cite: 2]
    *   **Clasificación**: Parámetros[cite: 2]
    *   **Origen**: Generación interna automática en `parametros.py`[cite: 2].
    *   **Descripción Funcional**: Almacena las variables temporales operativas globales por defecto (Año, Mes, Día Matinal, Día Venta, Día Anterior)[cite: 2].
    *   **Fuente de Datos**: Inicialización interna por código[cite: 2].
    *   **Clave Primaria Efectiva**: Ninguna.
    *   **Campos Principales**: `PARAMETRO`, `VALOR`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `VALOR` para las fechas operativas globales[cite: 2].
    *   **Módulos Consumidores**: `database.py`, `parametros.py`, `rep_gerencial.py`[cite: 2].
    *   **Frecuencia de actualización**: Dinámica / Por sesión o configuración local.

*   **10. maestro_ccc**
    *   **Nombre Técnico**: `maestro_ccc`[cite: 2]
    *   **Clasificación**: Parámetros[cite: 2]
    *   **Origen**: Módulo de Parámetros / Excel consolidado multi-solapa (`Maestro_CCC_Config`)[cite: 2].
    *   **Descripción Funcional**: Versionado histórico de porcentajes exigidos sobre cartera neta y objetivos absolutos de Pepsico (`Obj_CCC_Pepsico`) por taxonomía (A, B, C, D)[cite: 2].
    *   **Fuente de Datos**: Importación manual desde Parámetros[cite: 2].
    *   **Clave Primaria Efectiva**: `(Anio, Mes, Taxonomia)`.
    *   **Campos Principales**: `Anio`, `Mes`, `Taxonomia`, `Porcentaje_Cartera`, `Obj_CCC_Pepsico`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Porcentaje_Cartera`, `Obj_CCC_Pepsico`[cite: 2].
    *   **Módulos Consumidores**: `database.py`, `parametros.py`, `rep_ccc.py`, `rep_gerencial.py`[cite: 2].
    *   **Frecuencia de actualización**: Mensual / Versionada[cite: 2].

*   **11. parametros_marcas**
    *   **Nombre Técnico**: `parametros_marcas`
    *   **Clasificación**: Parámetros
    *   **Origen**: Carga auxiliar externa.
    *   **Descripción Funcional**: Catálogo secundario de marcas de soporte para filtros y mapeos de visualización.
    *   **Fuente de Datos**: Ingesta externa.
    *   **Clave Primaria Efectiva**: Ninguna.
    *   **Campos Principales**: Campos descriptivos de marcas.
    *   **Módulos Consumidores**: `app.py`, `rep_gerencial.py`.
    *   **Frecuencia de actualización**: Estática / Periódica.

---

### D. Tablas de Objetivos
*   **12. objetivos_vendedores**
    *   **Nombre Técnico**: `objetivos_vendedores`[cite: 2]
    *   **Clasificación**: Objetivos[cite: 2]
    *   **Origen**: Importación de Excel de Objetivos Calibrados (`Objetivos_Calibrados`)[cite: 2].
    *   **Descripción Funcional**: Almacena las metas definitivas en kilogramos asignadas a cada preventista por segmento, versionadas por período gerencial[cite: 2].
    *   **Fuente de Datos**: Carga manual desde el módulo de Parámetros[cite: 2].
    *   **Clave Primaria Efectiva**: `(Anio, Mes, CodVendedor, SEGMENTO)`[cite: 2].
    *   **Campos Principales**: `Anio`, `Mes`, `CodVendedor`, `Nombre`, `Supervisor`, `SEGMENTO`, `Obj_Sugerido_Kg`, `Logro_Anterior_Pct`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Obj_Sugerido_Kg` (meta oficial de kilos)[cite: 2].
    *   **Módulos Consumidores**: `database.py`, `parametros.py`, `rep_kilos.py`[cite: 2].
    *   **Frecuencia de actualización**: Mensual / Versionada por período[cite: 2].

---

### E. Tablas Auxiliares
*   **13. ausencias**
    *   **Nombre Técnico**: No persiste como tabla SQL física en SQLite (procesada enteramente en memoria volátil por `data_loader.py`).
    *   **Clasificación**: Auxiliares
    *   **Origen**: Exportación CSV web remota vía `cfg.URL_AUSENCIAS`.
    *   **Descripción Funcional**: Padrón dinámico en tiempo real de preventistas ausentes y sus reemplazos operativos asignados por fecha[cite: 3].
    *   **Fuente de Datos**: Petición HTTP externa con TTL de caché de 1 hora.
    *   **Clave Primaria Efectiva**: Ninguna.
    *   **Campos Principales**: `Fecha`, `Ausente`, `Reemplazo`, `Cliente`.
    *   **Campos Críticos para Reglas de Negocio**: `Ausente`, `Reemplazo`, `Fecha` (construcción de `ClaveAUS`)[cite: 3].
    *   **Módulos Consumidores**: `data_loader.py`, `rep_kilos.py`, `rep_ccc.py`, `rep_gerencial.py`[cite: 3].
    *   **Frecuencia de actualización**: En tiempo real (consulta web bajo demanda con caché temporal).

---

### F. Tablas Derivadas
*   *Nota Arquitectónica Institucional*: Actualmente **no existen tablas derivadas persistidas** en SQLite. Toda la capa de agregaciones, matrices cruzadas, cálculos de promedios, tendencias y reportes se procesa al vuelo en memoria RAM mediante DataFrames de Pandas dentro de los submódulos de análisis y presentación (`/modules/`).

====================================================================================================

# DOCUMENTO: GLOSARIO_REGLAS.md

# Glosario de Reglas de Negocio - MATINAL (Versión 1.0)

## 1. Identificación y Propósito
El presente documento constituye la **Fuente de Verdad Institucional** sobre la inteligencia comercial de MATINAL. Ninguna decisión técnica o de infraestructura futura puede contradecir las definiciones funcionales aquí estipuladas. Las reglas se estructuran por dominios operativos y establecen el estándar para la futura capa de **`BUSINESS RULES`**.

---

## 2. Inventario Normativo de Reglas

### A. Reglas Corporativas N1
*   **1. Filtro Global de Empleados (SSOT)**
    *   **Objetivo**: Aislar la operación comercial real descartando preventistas internos o cuentas de empleados.
    *   **Definición Funcional**: Evalúa la columna `Subramo` de la tabla de transacciones de ventas (`vta`) y elimina de forma universal todos los registros que pertenezcan a cuentas marcadas como `EMPLOYEES` o `EMPLEADOS`. Opera como la Única Fuente de Verdad transversal.
    *   **Fuente de Datos**: Tabla SQLite `vta`.
    *   **Campos Involucrados**: `Subramo`, `CodVendedor`.
    *   **Módulos de Aplicación**: `database.py` (`obtener_df_maestro_corporativo`), `rep_MN.py`, `rep_ccc.py`, `rep_kilos.py`, `rep_gerencial.py`[cite: 2].
    *   **Prioridad**: Crítica / Absoluta.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

---

### B. Reglas Operativas N2
*   **2. Exclusión de Comodatos y Préstamos**
    *   **Objetivo**: Evitar la distorsión del volumen comercial con operaciones logísticas o financieras que no constituyen ventas netas.
    *   **Definición Funcional**: Descarta transacciones cuyo tipo de venta corresponda a "Comodato Devolución", "Comodato Ficticio", "Comodato Ficticio Devolución" o "Comodato Préstamo"[cite: 3].
    *   **Fuente de Datos**: Transacciones de ventas (`vta`).
    *   **Campos Involucrados**: `TipoDeVenta`.
    *   **Módulos de Aplicación**: Todos los motores analíticos de reportes[cite: 3, 4].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **3. Selección Exclusiva de Proveedor PepsiCo**
    *   **Objetivo**: Delimitar el análisis analítico exclusivamente al fabricante corporativo oficial.
    *   **Definición Funcional**: Filtra las transacciones conservando únicamente aquellas donde el campo de proveedor contenga la cadena `PEPSICO`[cite: 3].
    *   **Fuente de Datos**: Transacciones de ventas (`vta`).
    *   **Campos Involucrados**: `Proveedor`.
    *   **Módulos de Aplicación**: Todos los motores analíticos de reportes[cite: 3, 4].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **4. Aislamiento del Vendedor 20 / Depósito**
    *   **Objetivo**: Aislar a la fuerza de ventas preventista pura, evitando sesgos provocados por cargas de inventario o movimientos de depósito central.
    *   **Definición Funcional**: Exclusión sistemática del preventista código `20` en los reportes analíticos de preventistas (excepto para prorrateos financieros globales en el tablero gerencial)[cite: 3].
    *   **Fuente de Datos**: Transacciones de ventas (`vta`) y padrón de vendedores.
    *   **Campos Involucrados**: `CodVendedor`.
    *   **Módulos de Aplicación**: `rep_MN.py`, `rep_ccc.py`, `rep_gerencial.py`, `rep_vespertina.py`[cite: 3, 5].
    *   **Prioridad**: Crítica.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

---

### C. Reglas Temporales y de Cierre Operativo
*   **5. Corte por Día Matinal**
    *   **Objetivo**: Establecer la foto operativa estricta al corte cronológico de la mañana (Día Matinal).
    *   **Definición Funcional**: Suprime registros cuya fecha de carga (`FechaCarga`) sea igual o posterior al Día Matinal seleccionado para el mes en curso[cite: 3].
    *   **Fuente de Datos**: Transacciones de ventas y filtros globales de usuario.
    *   **Campos Involucrados**: `FechaCarga`.
    *   **Módulos de Aplicación**: `rep_gerencial.py`, `rep_ccc.py`, `rep_MN.py`, `rep_kilos.py`[cite: 3].
    *   **Prioridad**: Crítica.
    *   **Naturaleza**: Configurable por usuario.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **6. Clasificación por Período Comercial**
    *   **Objetivo**: Distribuir el volumen transaccional en ventanas temporales de impacto contable y logístico.
    *   **Definición Funcional**: Clasifica las transacciones en *Arrastre* (mes anterior con entrega en mes actual), *Actual* (carga y entrega en mes corriente) y *Futuro* (mes siguiente)[cite: 3].
    *   **Fuente de Datos**: `FechaCarga`, `FechaEntrega`.
    *   **Campos Involucrados**: Fechas de carga/entrega y mes/año operativo.
    *   **Módulos de Aplicación**: Motores de preparación de ventas en todos los submódulos[cite: 3, 4].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **7. Problema de Cierre del Día Venta (Vespertina)**
    *   **Objetivo**: Auditar en tiempo real el impacto comercial exclusivo de las transacciones ejecutadas durante el Día Venta.
    *   **Definición Funcional**: Contrasta las activaciones de CCC y conversiones digitales producidas durante el día contra la historia acumulada previa del mes (Arrastre + Actual)[cite: 5].
    *   **Fuente de Datos**: Transacciones de ventas y padrón de universo.
    *   **Campos Involucrados**: `FechaCarga`, `Cliente`, `ImporteNeto`, `CantBase`.
    *   **Módulos de Aplicación**: `rep_vespertina.py`[cite: 5].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.

---

### D. Reglas de Cartera y CCC
*   **8. Definición Operativa de Comprador CCC**
    *   **Objetivo**: Cuantificar con precisión la efectividad de compra de los clientes en la cartera.
    *   **Definición Funcional**: Un cliente califica como CCC (*Clientes con Compra*) si en el período (*Arrastre* + *Actual*) acumula una cantidad base (`CantBase`) $\ge$ 3 y un importe neto $\ge$ 1[cite: 3].
    *   **Fuente de Datos**: Transacciones de ventas procesadas.
    *   **Campos Involucrados**: `CantBase`, `ImporteNetoItem`, `Cliente`.
    *   **Módulos de Aplicación**: `rep_ccc.py`, `rep_gerencial.py`, `rep_MN.py`[cite: 3].
    *   **Prioridad**: Crítica.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **9. Cartera Neta y Exclusión de Cierre Definitivo**
    *   **Objetivo**: Establecer el universo neto de clientes evaluables para metas institucionales.
    *   **Definición Funcional**: Calcula la cartera neta restando del padrón total las altas nuevas y reactivaciones mensuales, descartando de forma terminante a los clientes con estatus de `"CIERRE DEFINITIVO"` en el padrón de altas[cite: 3].
    *   **Fuente de Datos**: `universo`, `altas`.
    *   **Campos Involucrados**: `Cliente`, `Estado`, `Origen_Hoja`.
    *   **Módulos de Aplicación**: `rep_ccc.py`[cite: 3].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.

---

### E. Reglas MiNegocio (Adopción Digital)
*   **10. Clasificación Digital por Adopción de Facturación**
    *   **Objetivo**: Segmentar la cartera según su nivel de madurez en canales digitales de autogestión.
    *   **Definición Funcional**: Categoriza a los clientes cruzando sus ventas por la app `MiNegocio` frente a sus ventas totales:
        *   *No Digital*: Adopción $\le 1\%$ ($\le 0.01$).
        *   *Híbrido*: Adopción $> 1\%$ y $< 70\%$.
        *   *Fully Digital*: Adopción $\ge 70\%$ ($\ge 0.70$).
    *   **Fuente de Datos**: Transacciones de ventas e indicador de canal.
    *   **Campos Involucrados**: `OrigenDeVta`, `ImporteNetoItem`, `Cliente`.
    *   **Módulos de Aplicación**: `rep_MN.py`, `rep_gerencial.py`, `rep_vespertina.py`.
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **11. Cálculo del Faltante para el Umbral del 70%**
    *   **Objetivo**: Proveer una métrica accionable para la fuerza de ventas orientada a convertir clientes híbridos.
    *   **Definición Funcional**: Calcula el monto monetario exacto adicional que un cliente no digital o híbrido debe facturar por la aplicación para alcanzar el 70% de participación digital[cite: 2].
    *   **Fuente de Datos**: `Ventas_Totales`, `Ventas_MiNegocio`.
    *   **Campos Involucrados**: Importes netos por canal.
    *   **Módulos de Aplicación**: `rep_MN.py`[cite: 2].
    *   **Prioridad**: Media-Alta.
    *   **Naturaleza**: Obligatoria.

---

### F. Reglas de Cobertura (Marca e Innovación)
*   **12. Validación de Compra Mínima por Cobertura**
    *   **Objetivo**: Auditar la penetración de marcas estratégicas y lanzamientos en los puntos de venta.
    *   **Definición Funcional**: Un cliente se considera cubierto en una Marca o Producto de Innovación si registra una cantidad comprada (`CantBase`) acumulada $\ge$ 3 unidades en el período evaluado[cite: 4].
    *   **Fuente de Datos**: Transacciones de ventas y maestros de marcas/innovaciones[cite: 4].
    *   **Campos Involucrados**: `Marca`, `Codigo` (producto), `CantBase`, `Cliente`.
    *   **Módulos de Aplicación**: `rep_cob_marca.py`, `rep_cob_innovacion.py`, `rep_gerencial.py`[cite: 4].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria (con metas de cobertura configurables, ej. 80%).
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

---

### G. Reglas de Ausencias, Reemplazos y Operación Kilos
*   **13. Reasignación Dinámica por Clave AUS**
    *   **Objetivo**: Garantizar que el volumen de preventa no se pierda ante la ausencia temporal de un preventista titular.
    *   **Definición Funcional**: Cruza transacciones con el padrón de ausencias mediante claves compuestas por preventista y fecha (`ClaveAUS`), reasignando el volumen al preventista de reemplazo operativo (`CodVendedorOperativo`)[cite: 3].
    *   **Fuente de Datos**: `vta`, `ausencias`.
    *   **Campos Involucrados**: `CodVendedor`, `FechaCarga`, `FechaEntrega`, `Reemplazo`.
    *   **Módulos de Aplicación**: `rep_ccc.py`, `rep_kilos.py`, `rep_gerencial.py`[cite: 3].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **14. Proyección Lineal de Kilos por Días Restantes**
    *   **Objetivo**: Estimar el volumen proyectado de cierre mensual para la toma de decisiones gerenciales.
    *   **Definición Funcional**: Multiplica el promedio diario actual del preventista por los días hábiles restantes del mes (pudiendo descontar ineficiencias logísticas mediante el modo de ajuste `AJUSTADO` basado en `Rutas_Ajustadas`).
    *   **Fuente de Datos**: `vta`, `rutas`, `maestro_vendedores`.
    *   **Campos Involucrados**: `PesoKg`, fechas de rutas, `Rutas_Ajustadas`.
    *   **Módulos de Aplicación**: `rep_kilos.py`, `rep_gerencial.py`.
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Configurable (modos `TODO` vs `AJUSTADO`).

====================================================================================================

# DOCUMENTO: CORE_OPERACION_V1.md

# CORE_OPERACION V1

Versión: 2.0

Fecha última actualización:
27/09/2026

Estado:
IMPLEMENTADO Y VALIDADO

Estado de Producción:
OPERATIVO

---

# Objetivo

CORE_OPERACION constituye el núcleo operativo institucional del sistema MATINAL.

Su responsabilidad es transformar entidades previamente normalizadas por STAGING en estructuras operativas listas para ser consumidas por BUSINESS RULES y REPORTES.

CORE_OPERACION no realiza ETL.

CORE_OPERACION asume que STAGING entrega datos consistentes.

---

# Posición Arquitectónica

RAW
↓
SQLITE
↓
STAGING
↓
CORE_OPERACION
↓
BUSINESS RULES
↓
REPORTES

---

# Responsabilidad Principal

Determinar:

- quién figura como titular de una venta
- quién ejecutó realmente esa venta
- qué reemplazos deben aplicarse
- cómo clasificar temporalmente cada transacción
- qué calendario operativo corresponde

---

# Entradas Oficiales

## obtener_staging_vta()

Entrega:

- FechaCarga_dt
- FechaEntrega_dt
- CodVendedor
- Cliente
- CantBase
- ImporteNetoItem

---

## obtener_staging_rutas()

Entrega:

calendario de visitas.

---

## obtener_staging_ausencias()

Implementado en FASE 4.7.

Entrega:

- Fecha_dt
- CodVend_clean
- Reemplazo_clean

---

## obtener_staging_maestros()

Entrega:

- maestro_vendedores
- maestro_ccc
- maestro_segmentos
- maestro_marcas_cebe

---

# Flujo Oficial

obtener_staging_vta()
↓
obtener_staging_rutas()
↓
obtener_staging_ausencias()
↓
obtener_staging_maestros()
↓
procesar_ausencias_y_reemplazos()
↓
calcular_ritmo_operativo()
↓
calcular_calendario_y_rutas()
↓
obtener_core_operacion()

---

# Procesar Ausencias y Reemplazos

Función:

procesar_ausencias_y_reemplazos()

Responsabilidad:

Determinar:

CodVendedorOperativo

---

# Claves Generadas

## ClaveAUS_Carga

Formato:

CodVendedor + FechaCarga

---

## ClaveAUS_Entrega

Formato:

CodVendedor + FechaEntrega

---

## ClaveAUS

Formato:

CodVend_clean + Fecha_dt

---

# Lógica de Reemplazo

## Sin reemplazo

Condición:

No existe coincidencia en AUSENCIAS.

Resultado:

CodVendedorOperativo = CodVendedor

---

## Con reemplazo

Condición:

Existe coincidencia por clave.

Resultado:

CodVendedorOperativo = Reemplazo

---

# Salidas Operativas

Columnas generadas:

- Reemplazo
- CodVendedorOperativo

Columnas utilizadas:

- FechaCarga_dt
- FechaEntrega_dt
- CodVendedor

---

# Clasificación Temporal

Función:

calcular_ritmo_operativo()

Clasificaciones:

- Arrastre
- Actual
- Futuro
- Fuera de Periodo

---

# Calendario Operativo

Función:

calcular_calendario_y_rutas()

Produce:

- dias_pasados_map
- dias_restantes_map
- total_dias_pasados
- total_dias_restantes

---

# Contrato de Salida

obtener_core_operacion()

retorna:

- df_vta_operativa
- dias_pasados_map
- dias_restantes_map
- total_dias_pasados
- total_dias_restantes

---

# Estado Actual

FASE 4.7

Completada.

Validada en producción.

---

# Pendiente

FASE 4.8

Eliminar ETL redundante heredado dentro de:

procesar_ausencias_y_reemplazos()

Actualmente aún existen componentes técnicos duplicados que ya fueron migrados a:

obtener_staging_ausencias()

La eliminación deberá realizarse únicamente luego de validaciones de producción.

====================================================================================================

# DOCUMENTO: CORE_VENTAS_BASE_V1.md

# CORE_VENTAS_BASE V1

Versión: 2.0

Fecha última actualización:
27/09/2026

Estado:
DISEÑADO

Implementación:
PLANIFICADA

Prioridad:
ALTA

Dependencia Arquitectónica:
FASE 5+

---

# Propósito

CORE_VENTAS_BASE representa la definición institucional única de una venta dentro del ecosistema MATINAL.

Su objetivo es construir una entidad corporativa común que pueda ser reutilizada por todos los motores analíticos del sistema.

La existencia de CORE_VENTAS_BASE evita que cada reporte vuelva a interpretar de forma independiente qué es una venta válida.

---

# Posición Arquitectónica

RAW
↓
SQLITE
↓
STAGING
↓
CORE_VENTAS_BASE
↓
CORE_OPERACION
↓
BUSINESS RULES
↓
REPORTES

---

# Principio Fundamental

Toda venta consumida por:

- CCC
- Mi Negocio
- Kilos
- Coberturas
- Tienda Perfecta
- Gerencial
- Vespertina

debería provenir de la misma definición institucional.

---

# Estado Actual

Actualmente el sistema funciona correctamente sin una implementación formal de CORE_VENTAS_BASE.

Las reglas se encuentran distribuidas entre:

- rep_kilos.py
- rep_ccc.py
- rep_MN.py
- rep_gerencial.py
- rep_tp.py
- funciones auxiliares

El objetivo de CORE_VENTAS_BASE es centralizar esta interpretación.

---

# Fuente Oficial de Entrada

Entrada obligatoria:

obtener_staging_vta()

---

# Dependencia Obligatoria

Debe consumir exclusivamente:

obtener_staging_vta()

No debe leer:

- Excel
- SQLite
- CSV
- APIs externas

---

# Preguntas que Responde

CORE_VENTAS_BASE responde:

¿Qué venta existe?

¿Quién es el vendedor titular?

¿Qué cliente interviene?

¿Qué fechas posee?

¿Qué atributos comerciales tiene?

¿A qué período temporal pertenece?

---

# Preguntas que NO Responde

No responde:

¿Cuenta para CCC?

¿Cuenta para Mi Negocio?

¿Cuenta para Cobertura?

¿Cuenta para TP?

¿Cuenta para Objetivos?

¿Tiene compensación?

¿Tiene comisión?

¿Debe excluirse por una regla comercial específica?

Estas preguntas pertenecen a BUSINESS RULES.

---

# Responsabilidades

## 1. Normalización de Identificadores

Convertir a tipos institucionales:

Cliente

CodVendedor

Resultado esperado:

Int64

---

## 2. Normalización de Magnitudes

Convertir:

CantBase

PesoKg

ImporteNetoItem

Resultado esperado:

Numérico

---

## 3. Normalización Temporal

Garantizar:

FechaCarga_dt

FechaEntrega_dt

FechaLiquidacion_dt

cuando corresponda.

---

## 4. Conservación de Atributos Comerciales

Mantener sin modificar:

Proveedor

Marca

Articulo

Subramo

TipoDeVenta

Segmento

Canal

Taxonomía

Toda clasificación posterior pertenece a otras capas.

---

# Relación con Problema de Cierre

CORE_VENTAS_BASE deberá ser compatible con la definición oficial:

"Una venta es operativa del período cuando FechaCarga y FechaLiquidación pertenecen al mismo mes operativo o cuando FechaLiquidación es nula."

La decisión institucional denominada:

Problema de Cierre

posee prioridad superior al diseño técnico.

---

# Relación con Día Matinal

CORE_VENTAS_BASE no aplica filtros de Día Matinal.

Debe preservar la información.

Los filtros temporales son responsabilidad del CORE y BUSINESS RULES.

---

# Relación con Ausencias

CORE_VENTAS_BASE no debe aplicar reemplazos.

No debe generar:

CodVendedorOperativo

No debe interpretar:

Ausencias

Reemplazos

Estas responsabilidades pertenecen a:

CORE_OPERACION

---

# Contrato de Salida Esperado

La entidad final deberá contener como mínimo:

Cliente

CodVendedor

FechaCarga_dt

FechaEntrega_dt

FechaLiquidacion_dt

CantBase

PesoKg

ImporteNetoItem

Marca

Proveedor

Articulo

Subramo

TipoDeVenta

---

# Restricciones Arquitectónicas

CORE_VENTAS_BASE:

✅ Puede normalizar.

✅ Puede tipar.

✅ Puede clasificar temporalmente.

✅ Puede validar consistencia.

---

CORE_VENTAS_BASE:

❌ No calcula objetivos.

❌ No calcula coberturas.

❌ No calcula CCC.

❌ No calcula Mi Negocio.

❌ No calcula compensaciones.

❌ No aplica reemplazos.

❌ No aplica filtros comerciales.

---

# Consumidores Futuros

La implementación definitiva deberá servir como entrada única para:

CORE_OPERACION

CCC

Mi Negocio

Kilos

Cobertura Marca

Cobertura Innovación

Tienda Perfecta

Gerencial

Vespertina

---

# Beneficio Esperado

Eliminar múltiples interpretaciones de una venta.

Garantizar consistencia transversal entre todos los módulos.

Reducir duplicación de lógica.

Mejorar auditabilidad.

Facilitar futuras migraciones hacia capas BUSINESS RULES más desacopladas.

---

# Estado de Roadmap

Situación actual:

Diseñado.

No implementado.

Implementación prevista después de la consolidación completa de:

STAGING

CORE_OPERACION

FASE 4.8

---

# Observación Institucional

Este documento describe una entidad objetivo de arquitectura.

No necesariamente refleja una implementación completa existente en código al momento de su lectura.

Su finalidad es preservar la definición institucional que deberá respetarse durante futuras refactorizaciones del núcleo comercial del sistema.

====================================================================================================

# DOCUMENTO: BITACORA.md

## INC-2026-09-24-001

### Título
Eliminación de referencia obsoleta a tabla `parametros_marcas`

### Fecha
24/09/2026

### Descubrimiento

Durante la validación operativa de la Fase 2A (Logging Estructurado), el archivo de log detectó múltiples advertencias:

```text
WARNING | matinal.database |
La tabla consultada no existe en el catálogo de SQLite.
SELECT * FROM parametros_marcas
# INC-2026-09-24-001

## Título

Eliminación de referencia obsoleta a la tabla `parametros_marcas`

## Fecha de Apertura

24/09/2026

## Fecha de Cierre

24/09/2026

## Origen

Durante la validación operativa de la Fase 2A (Logging Estructurado) se detectaron advertencias recurrentes en:

```text
logs/matinal.log
## Validación Final de Estabilidad

Posteriormente a la corrección se realizaron las siguientes pruebas adicionales:

### Prueba 1 - Reinicio Completo

- Cierre total de la aplicación.
- Reinicio de Streamlit.
- Recarga completa de módulos.
- Verificación de acceso a todos los reportes principales.

Resultado:

```text
✅ Aplicación operativa.
✅ Sin errores observados.
✅ Sin referencias nuevas a parametros_marcas.
## INC-2026-09-25-001

### Título
Unificación de padrón de vendedores y supervisor en Tienda Perfecta

### Fecha
25/09/2026

### Cambio
Se integró `modules/rep_tp.py` con `maestro_vendedores`, adoptando el mismo criterio de identificación de preventistas utilizado en `rep_ccc.py`.

### Implementación
- Incorporación de cruce por código de vendedor.
- Visualización de nombres corporativos en lugar de códigos.
- Incorporación de Supervisor desde `maestro_vendedores`.
- Compatibilidad con `filtros_globales["supervisor"]`.
- Regeneración dinámica de catálogos por supervisor.
- Conservación de las claves históricas de `st.session_state` para evitar regresiones.

### Validación
- Supervisor específico → OK.
- Retorno a TODOS → OK.
- Catálogo de vendedores regenerado correctamente.
- Rankings, oportunidades y exportaciones operativos.

### Resultado
✅ TP alineado arquitectónicamente con CCC.

### Impacto
Sin degradación observable de performance.
# INC-2026-09-26-001

## Título
Auditoría forense de paridad en STAGING_CLIENTES

## Fecha de Apertura
26/09/2026

## Estado
Cerrado

## Contexto

Durante la Fase 4.1 se detectó una diferencia entre:

RAW_UNIVERSO = 5719 registros

y

STAGING_CLIENTES = 5615 registros

## Investigación Realizada

Se auditó:

- UNIVERSO.xlsx
- SQLite (tabla universo)
- modules/database.py
- modules/staging.py
- modules/data_loader.py
- cache de Streamlit
- tipado de identificadores
- duplicados
- valores nulos

## Hallazgos

Se comprobó que:

- La diferencia es exactamente de 104 registros.
- Los 104 registros corresponden al SubSegmento = Empleados.
- La tabla universo en SQLite contiene 5719 registros.
- db.cargar_tabla_sql("SELECT * FROM universo") devuelve 5719 registros.
- STAGING_CLIENTES devuelve 5615 registros.
- No se detectaron pérdidas por tipado, duplicados o valores nulos.

## Impacto

Nulo sobre la continuidad del proyecto.

Los registros faltantes están completamente identificados y cuantificados.

## Decisión Arquitectónica

Se confirma la arquitectura:

RAW
→ STAGING
→ CORE
→ REPORTES

Las reglas de exclusión de empleados pertenecen a CORE.

## Resolución

Se da por concluida la Fase 4.1.

La incidencia queda documentada como STG-001 y no bloquea el inicio de CORE.

## Resultado

✅ FASE 4.1 cerrada

✅ Inicio autorizado de la Capa CORE

====================================================================================================

