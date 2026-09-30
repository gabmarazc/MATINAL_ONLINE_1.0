## INVENTARIO DEL PROYECTO MATINAL

Versión: 2.1
Fecha de actualización: 29/09/2026
Estado: Vigente
Estado de validación: Producción Operativa

---

# ESTADO ARQUITECTÓNICO

Arquitectura institucional vigente:

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

Estado actual:

RAW               ✅
SQLITE            ✅
STAGING           ✅
CORE              ✅
BUSINESS RULES    🟡 En consolidación
REPORTES          ✅

---

# SITUACIÓN DE LA ARQUITECTURA

## Migración validada

Kilos constituye el primer caso completamente migrado hacia la arquitectura institucional mediante la capa BUSINESS RULES.

Patrón aprobado:

rep_kilos_core.py
↓
business_rules_kilos.py
↓
core_*

Estado:

✅ Validado
✅ Operativo
✅ Commiteado
✅ Referencia oficial para futuras migraciones

---

# ROADMAP DE MIGRACIÓN DE REPORTES

Estado actual:

✅ Kilos

Próximas migraciones aprobadas:

⏳ MiNegocio
⏳ CCC
⏳ Cobertura Marca
⏳ Cobertura Innovación
⏳ Gerencial
⏳ Vespertina

Objetivo:

Eliminar dependencias entre reportes y migrar progresivamente toda la lógica comercial hacia BUSINESS RULES.

---

# ARCHIVOS RAÍZ

- .gitignore
- app copy.py
- app.py
- config.py
- contexto.py
- data_loader.py
- generar_objetivos_manuales.py
- iniciar_sistema.bat
- requirements.txt
- runtime.txt
- st_aggrid.py
- todo_el_proyecto.txt

---

# MODULES

## Persistencia

- modules\database.py
- modules\logger.py

## Configuración

- modules\parametros.py

## Utilidades

- modules\utils.py

## Arquitectura Institucional

### STAGING

- modules\staging.py

### CORE

- modules\core\core_clientes.py
- modules\core\core_operaciones.py
- modules\core\core_vendedores.py
- modules\core\core_ventas_base.py

### BUSINESS RULES

#### Implementadas

- modules\business_rules\business_rules_kilos.py
- modules\business_rules\business_rules_repository.py

#### Aprobadas para implementación

- modules\business_rules\business_rules_mn.py

---

# REPORTES

## Reportes históricos

- modules\rep_kilos.py
- modules\rep_MN.py
- modules\rep_ccc.py
- modules\rep_cob_marca.py
- modules\rep_cob_innovacion.py
- modules\rep_gerencial.py
- modules\rep_vespertina.py
- modules\rep_tp.py
- modules\rep_obj_kilos.py

## Reportes desacoplados

- modules\rep_kilos_core.py

## Reportes aprobados para migración

- modules\rep_MN_core.py

---

# DEPENDENCIAS ARQUITECTÓNICAS IDENTIFICADAS

## Dependencias entre reportes detectadas

rep_gerencial.py

→ rep_MN.py
→ rep_ccc.py
→ rep_cob_marca.py

rep_vespertina.py

→ rep_ccc.py

## Objetivo institucional

Eliminar completamente las dependencias:

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

Todo nuevo desarrollo deberá seguir la siguiente estructura:

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

Business Rules
↓
Reporte

Acceso directo desde Reportes a SQLite

---

# PROJECT_DOCS

- ARQUITECTURA.md
- BITACORA.md
- CODIGO_CONSOLIDADO.md
- CONTEXTO_GLOBAL.md
- CONTEXTO_IA.md
- CORE_OPERACION_V1.md
- CORE_VENTAS_BASE_V1.md
- DECISIONES_TECNICAS.md
- DICCIONARIO_TABLAS.md
- ESTADO_ACTUAL.md
- GLOSARIO_REGLAS.md
- GOBIERNO_IA.md
- INVENTARIO_PROYECTO.md
- ROADMAP.md

---

# RESUMEN EJECUTIVO

Estado del sistema:

✅ Producción estable

✅ STAGING implementado

✅ CORE implementado

✅ Primera migración BUSINESS RULES validada

✅ rep_kilos_core operativo

⏳ Próxima migración: MiNegocio

Objetivo estratégico:

Consolidar la arquitectura institucional mediante la eliminación progresiva de lógica comercial embebida en reportes y su migración hacia BUSINESS RULES reutilizables.