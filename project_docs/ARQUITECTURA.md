# Arquitectura del Sistema MATINAL

Versión: 3.0

Fecha de actualización: 02/10/2026

Estado: Vigente

Estado de validation: Producción Operativa

---

# 1. Propósito del Documento

Este documento constituye la definición oficial de la arquitectura del sistema MATINAL.

Su objetivo es:

* Definir la arquitectura institucional vigente.
* Delimitar responsabilidades por capa.
* Establecer las reglas de interacción entre componentes.
* Preservar el conocimiento arquitectónico del proyecto.
* Permitir la continuidad del desarrollo independientemente de conversaciones previas.

Ante cualquier discrepancia entre documentación y código deberá revisarse primero:

1. ESTADO_ACTUAL.md


2. ARQUITECTURA.md


3. DECISIONES_TECNICAS.md


4. ROADMAP.md



Recién después analizar el código fuente.

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

Este modelo constituye la arquitectura oficial del proyecto.

---

# 3. Estado de Implementación

RAW
✅ Productivo

SQLITE
✅ Productivo

STAGING
✅ Productivo

CORE
✅ Productivo

BUSINESS RULES
✅ Validado en producción

REPORTES
✅ Productivo

---

# 4. Arquitectura Física

## Punto de Entrada

app.py

Responsabilidades:

* Inicio de la aplicación.
* Gestión de sesión.
* Gestión de autenticación.
* Renderizado de pantallas.
* Coordinación general de la interfaz.

---

## Persistencia

Ubicación:

data/matinal.db

Motor:

SQLite

Modo:

WAL (Write Ahead Logging)

Características:

* Fuente física única de datos.
* Persistencia local.
* Alto rendimiento de lectura.
* Desacoplamiento respecto de Excel.
* Soporte para persistencia vigente, historización (`universo_hist`) y control de versiones (`universo_versiones`).



---

## Estructura Principal

### Persistencia

* database.py
* logger.py

### Configuración

* parametros.py

### Utilidades

* utils.py

### Arquitectura Institucional

* staging.py
* core/*
* business_rules/*

### Reportes

* rep_kilos.py
* rep_kilos_core.py
* rep_MN.py
* rep_MN_core.py
* rep_ccc.py
* rep_ccc_core.py
* rep_cob_marca.py
* rep_cob_innovacion.py
* rep_gerencial.py
* rep_vespertina.py
* rep_tp.py
* rep_obj_kilos.py
* rep_obj_kilos_core.py

---

# 5. Capas Arquitectónicas

## RAW

Responsabilidad:

Recepción de información externa.

Ejemplos:

* VTA.xlsx
* UNIVERSO.xlsx
* RUTAS.xlsx
* ALTAS.xlsx
* AUSENCIAS
* Maestros corporativos

Restricción:

No contiene lógica de negocio.

---

## SQLITE

Responsabilidad:

Persistencia institucional de datos y gestión de versiones.

Tablas principales:

* vta
* universo
* universo_hist


* universo_versiones


* rutas
* ausencias
* maestro_vendedores
* maestro_ccc
* maestro_segmentos
* maestro_marcas_cebe

Restricción:

No contiene lógica de negocio.

---

## STAGING

Estado:

✅ Implementado

Objetivo:

Transformar datos persistidos en contratos técnicos consistentes.

Responsabilidades permitidas:

* Lectura SQLite
* Tipado
* Parseo de fechas
* Detección de columnas
* Normalización
* Limpieza técnica
* Contratos de datos

Responsabilidades prohibidas:

* Objetivos
* Coberturas
* CCC
* MiNegocio
* Pace
* Compensaciones
* KPIs
* Reglas comerciales

---

## CORE

Estado:

✅ Implementado

Objetivo:

Interpretar la operación comercial utilizando contratos provenientes de STAGING.

Responsabilidades:

* Titularidad operativa
* Reemplazos
* Ausencias
* Calendario
* Clasificación temporal
* Venta institucional
* Construcción de cartera operativa por vendedor

## Modelo de Cartera Operativa

# UNIVERSO

universo elegible

# VTA

evidencia transaccional válida

# CORE_OPERACION

constructor oficial de cartera operativa

# BUSINESS RULES

consumidores de cartera operativa

# REPORTES

consumidores finales

Flujo arquitectónico oficial:

VTA
+
UNIVERSO
↓
CORE_OPERACION
↓
Cartera Operativa por Vendedor
↓
BUSINESS RULES
↓
REPORTES

Aclaración arquitectónica explícita:
La cartera utilizada por BUSINESS RULES y REPORTES no surge directamente de UNIVERSO.
La cartera operativa institucional surge de la interpretación realizada por CORE_OPERACION utilizando:

* universo elegible
* evidencia transaccional válida
* reglas operativas institucionales

Responsabilidades prohibidas:

* KPIs
* Objetivos
* Coberturas
* CCC
* MiNegocio
* Compensaciones

---

## BUSINESS RULES

Estado:

✅ Validado en Producción

Objetivo:

Aplicar reglas comerciales reutilizables.

Responsabilidades:

* CCC
* MiNegocio
* Coberturas
* Objetivos
* Problema de Cierre
* Reglas comerciales institucionales
* Distribución institucional de objetivos sobre universo vigente.

### Arquitectura Oficial de Objetivos

Objetivo:
Distribuir objetivos comerciales institucionales utilizando una población elegible validada y reutilizable.
Flujo Arquitectónico Oficial:
Objetivos Corporativos
+
Universo Vigente
+
Potencial Comercial
↓
business_rules_objetivo_clientes
↓
ObjetivoClienteKg
↓
business_rules_objetivo_carteras
↓
Objetivos por Vendedor
↓
REPORTES
Validación Obligatoria de Elegibilidad:
Antes de cualquier distribución de objetivos deberá validarse la población elegible utilizando exclusivamente el Universo vigente.
Flujo Obligatorio:
Universo Vigente
↓
Clientes Elegibles
↓
ParticipacionMarcaSegmento
↓
ParticipacionClienteDentroSegmento
↓
ObjetivoClienteKg
Responsabilidad de BUSINESS RULES:

* distribución de objetivos
* participación comercial
* apropiación por cliente
* apropiación por cartera
* apropiación por vendedor
Responsabilidades Excluidas:
* lectura directa de Excel
* construcción de Universo
* interpretación operativa
* normalización técnica
Principio Arquitectónico:
La distribución de objetivos deberá operar exclusivamente sobre clientes pertenecientes al Universo vigente.

Responsabilidades prohibidas:

* Lectura directa de SQLite
* Lectura directa de Excel
* Dependencias entre reportes

---

## REPORTES

Estado:

✅ Operativos

Objetivo:

Presentar información a usuarios.

Responsabilidades:

* KPIs
* Visualizaciones
* Indicadores
* Proyecciones
* Exportaciones

Restricción:

Los reportes no deben contener reglas comerciales institucionales.

---

# 6. Componentes Institucionales

## STAGING

Implementados:

* obtener_staging_vta()
* obtener_staging_clientes()
* obtener_staging_rutas()
* obtener_staging_ausencias()
* obtener_staging_maestros()

---

## CORE

Implementados:

* obtener_core_ventas_base()
* obtener_core_clientes()
* obtener_core_vendedores()
* obtener_core_operacion()
* core_clientes.py
* core_operaciones.py
* core_vendedores.py
* core_ventas_base.py
* core_potencial_cliente.py
* core_potencial_cliente_segmento.py
* core_validacion_periodo.py

---

## BUSINESS RULES

Implementados:

* business_rules_repository.py
* business_rules_kilos.py
* business_rules_mn.py
* business_rules_ccc.py
* business_rules_objetivo_clientes.py
* business_rules_objetivo_segmentos.py
* business_rules_objetivo_carteras.py

---

# 7. Business Rules Validadas

## Kilos

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

## MiNegocio

Arquitectura:

rep_MN_core.py
↓
business_rules_mn.py
↓
core_*

Estado:

✅ Productivo

✅ Validado

---

## CCC

Arquitectura:

rep_ccc_core.py
↓
business_rules_ccc.py
↓
core_*

Estado:

✅ Productivo

✅ Validado

---

# 8. Regla Arquitectónica Fundamental

Permitido:

Reporte
↓
Business Rules
↓
Core

Core
↓
Staging

Business Rules
↓
Core

---

Prohibido:

Reporte
↓
Reporte

Business Rules
↓
Reporte

Reporte
↓
SQLite

Reporte
↓
Excel

Business Rules
↓
SQLite

Business Rules
↓
Excel

---

# 9. Estado de Migraciones Arquitectónicas

## Migraciones Arquitectónicas Validadas

* ✅ Kilos
* ✅ MiNegocio
* ✅ CCC

## Migraciones Pendientes

* ⏳ Cobertura Marca
* ⏳ Cobertura Innovación
* ⏳ Gerencial
* ⏳ Vespertina

Objetivo:

* Consolidar fuentes únicas de verdad para los reportes restantes mediante la adopción progresiva del patrón `Reporte -> Business Rules -> Core`.

---

# 10. Objetivo Arquitectónico Final

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

hasta alcanzar una arquitectura completamente desacoplada, reutilizable y gobernada mediante una única fuente institucional de reglas comerciales.