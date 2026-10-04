# Arquitectura del Sistema MATINAL

Versión: 3.0

Fecha de actualización: 02/10/2026

Estado: Vigente

Estado de validación: Producción Operativa

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


* rep_MN.py


* rep_ccc.py


* rep_cob_marca.py


* rep_cob_innovacion.py


* rep_gerencial.py


* rep_vespertina.py


* rep_tp.py


* rep_obj_kilos.py



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



---

## BUSINESS RULES

Implementados:

* business_rules_repository.py


* business_rules_kilos.py


* business_rules_mn.py



Planificados:

* business_rules_ccc.py



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

# 9. Próxima Migración Aprobada

CCC

Arquitectura objetivo:

rep_ccc.py
↓
business_rules_ccc.py
↓
rep_ccc_core.py

Objetivo:

* Desacoplar CCC.


* Crear fuente única de verdad para CCC.


* Preparar desacoplamiento de Vespertina.


* Preparar desacoplamiento de Gerencial.



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