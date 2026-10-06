# INVENTARIO DEL PROYECTO MATINAL

Versión: 3.0

Fecha de actualización: 30/09/2026

Estado: Vigente

Estado de validación: Producción Operativa

---

# ESTADO ARQUITECTÓNICO

## Arquitectura institucional vigente

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

## Estado actual

RAW               ✅

SQLITE            ✅

STAGING           ✅

CORE              ✅

BUSINESS RULES    ✅

REPORTES          ✅

---

# ESTADO DE LAS MIGRACIONES

## Migraciones completadas

### Kilos

Arquitectura:

rep_kilos_core.py
↓
business_rules_kilos.py
↓
core_*

Estado:

✅ Validado

✅ Productivo

✅ Patrón institucional aprobado

---

### MiNegocio

Arquitectura:

rep_MN_core.py
↓
business_rules_mn.py
↓
core_*

Estado:

✅ Validado

✅ Productivo

✅ Segundo patrón institucional aprobado

---

### CCC

Arquitectura:

rep_ccc_core.py
↓
business_rules_ccc.py
↓
core_*

Estado:

✅ Validado

✅ Productivo

✅ Tercer patrón institucional aprobado

---

## Migraciones pendientes

⏳ Cobertura Marca

⏳ Cobertura Innovación

⏳ Gerencial

⏳ Vespertina

---

# ARCHIVOS RAÍZ

* .gitignore
* app.py
* app copy.py
* config.py
* contexto.py
* data_loader.py
* generar_objetivos_manuales.py
* iniciar_sistema.bat
* requirements.txt
* runtime.txt
* st_aggrid.py
* todo_el_proyecto.txt

---

# MODULES

## Persistencia

* modules/database.py
* modules/logger.py

## Configuración

* modules/parametros.py

## Utilidades

* modules/utils.py

---

# ARQUITECTURA INSTITUCIONAL

## STAGING

* modules/staging.py

## CORE

* modules/core/core_clientes.py
* modules/core/core_operaciones.py
* modules/core/core_vendedores.py
* modules/core/core_ventas_base.py
* modules/core/core_potencial_cliente.py
* modules/core/core_potencial_cliente_segmento.py
* modules/core/core_validacion_periodo.py

---

# BUSINESS RULES

## Implementadas y productivas

* modules/business_rules/business_rules_repository.py
* modules/business_rules/business_rules_kilos.py
* modules/business_rules/business_rules_mn.py
* modules/business_rules/business_rules_ccc.py
* modules/business_rules/business_rules_objetivo_clientes.py
* modules/business_rules/business_rules_objetivo_segmentos.py
* modules/business_rules/business_rules_objetivo_carteras.py

---

# REPORTES

## Históricos

* modules/rep_kilos.py
* modules/rep_MN.py
* modules/rep_ccc.py
* modules/rep_cob_marca.py
* modules/rep_cob_innovacion.py
* modules/rep_gerencial.py
* modules/rep_vespertina.py
* modules/rep_tp.py
* modules/rep_obj_kilos.py

## Desacoplados y productivos

* modules/rep_kilos_core.py
* modules/rep_MN_core.py
* modules/rep_ccc_core.py
* modules/rep_obj_kilos_core.py

---

# DEPENDENCIAS ARQUITECTÓNICAS CONOCIDAS

## Dependencias entre reportes

### Gerencial

rep_gerencial.py
↓
rep_MN.py

rep_gerencial.py
↓
rep_ccc.py

rep_gerencial.py
↓
rep_cob_marca.py

### Vespertina

rep_vespertina.py
↓
rep_ccc.py

---

# OBJETIVO DE DESACOPLAMIENTO

Eliminar progresivamente:

Reporte
↓
Reporte

y reemplazarlas por:

Reporte
↓
Business Rules
↓
Core

---

# PATRÓN OFICIAL DE DESARROLLO

Toda nueva funcionalidad deberá respetar:

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

---

## Permitido

Reporte
↓
Business Rules
↓
Core

Business Rules
↓
Core

Core
↓
Staging

---

## Prohibido

Reporte
↓
Reporte

Business Rules
↓
Reporte

Acceso directo desde Reportes a SQLite

Acceso directo desde Reportes a Excel

---

# DOCUMENTACIÓN DEL PROYECTO

## Documentos rectores

* ARQUITECTURA.md
* ESTADO_ACTUAL.md
* DECISIONES_TECNICAS.md
* ROADMAP.md

## Documentos funcionales

* DICCIONARIO_TABLAS.md
* GLOSARIO_REGLAS.md
* CORE_OPERACION_V1.md
* CORE_VENTAS_BASE_V1.md

## Documentos de contexto

* CONTEXTO_GLOBAL.md
* CONTEXTO_IA.md
* GOBIERNO_IA.md

## Documentos históricos

* BITACORA.md

## Inventario

* INVENTARIO_PROYECTO.md

## Referencia de código

* CODIGO_CONSOLIDADO.md

---

# RESUMEN EJECUTIVO

Estado general:

✅ Producción operativa

Arquitectura:

✅ RAW → SQLITE → STAGING → CORE → BUSINESS RULES → REPORTES

Migraciones completadas:

✅ Kilos

✅ MiNegocio

✅ CCC

Business Rules:

✅ Validada en producción

Implementaciones productivas:

✅ business_rules_kilos.py

✅ business_rules_mn.py

✅ business_rules_ccc.py

✅ business_rules_objetivo_clientes.py

✅ business_rules_objetivo_segmentos.py

✅ business_rules_objetivo_carteras.py

Reportes desacoplados:

✅ rep_kilos_core.py

✅ rep_MN_core.py

✅ rep_ccc_core.py

✅ rep_obj_kilos_core.py

Objetivo estratégico final:

Eliminar completamente las dependencias entre reportes y consolidar BUSINESS RULES como única capa institucional de reglas comerciales reutilizables.