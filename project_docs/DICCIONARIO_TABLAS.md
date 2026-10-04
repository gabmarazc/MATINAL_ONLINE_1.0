# DICCIONARIO DE TABLAS - MATINAL

Versión: 3.0  
Fecha de actualización: 30/09/2026  
Estado: Vigente  
Estado de validación: Producción Operativa

---

# 1. PROPÓSITO DEL DOCUMENTO

El presente documento constituye la fuente de verdad institucional para la estructura de datos de MATINAL.

Su objetivo es documentar:

- Tablas físicas persistidas en SQLite.
- Entidades expuestas por STAGING.
- Entidades consumidas por CORE.
- Entidades disponibles en BUSINESS RULES.
- Contratos de datos institucionales.

Ante cualquier discrepancia:

1. ESTADO_ACTUAL.md
2. ARQUITECTURA.md
3. DECISIONES_TECNICAS.md
4. DICCIONARIO_TABLAS.md

Recién después revisar el código fuente.

---

# 2. ARQUITECTURA DE DATOS OFICIAL

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

## Principios Institucionales

### RAW

Recibe información externa.

### SQLITE

Persiste información.

### STAGING

Normaliza y tipa.

### CORE

Interpreta la operación.

### BUSINESS RULES

Aplica reglas comerciales.

### REPORTES

Presentan resultados.

---

# 3. PERSISTENCIA OFICIAL

## Ubicación

data/matinal.db

## Motor

SQLite

## Modo

WAL (Write Ahead Logging)

## Características

- Fuente física única de datos.
- Persistencia institucional.
- Lectura desacoplada de Excel.
- Alto rendimiento.
- Base oficial de la arquitectura.

---

# A. TABLAS TRANSACCIONALES

## VTA

### Nombre Técnico

vta

### Clasificación

Transaccional

### Descripción

Registro completo de transacciones comerciales utilizadas por los procesos operativos y analíticos del sistema.

### Origen

VTA.xlsx

### Campos Relevantes

- CodVendedor
- Cliente
- FechaCarga
- FechaEntrega
- FechaLiquidacion
- PesoKg
- CantBase
- ImporteNetoItem
- Marca
- Proveedor
- Articulo
- Subramo
- TipoDeVenta

### Índices Institucionales

- idx_vta_vendedor
- idx_vta_cliente
- idx_vta_fechacarga
- idx_vta_fechaentrega
- idx_vta_marca

### Consumidores

#### STAGING

obtener_staging_vta()

#### CORE

obtener_core_operacion()

obtener_core_ventas_base()

#### BUSINESS RULES

business_rules_kilos.py

business_rules_mn.py

#### REPORTES

Todos los reportes comerciales a través de capas intermedias.

---

### Contrato STAGING Garantizado

- FechaCarga_dt
- FechaEntrega_dt
- CodVendedor
- Cliente
- PesoKg
- CantBase
- ImporteNetoItem
- Marca

---

# B. TABLAS MAESTRAS

## UNIVERSO

### Nombre Técnico

universo

### Clasificación

Maestra

### Descripción

Padrón institucional de clientes.

Constituye la fuente oficial de:

- cartera
- taxonomías
- segmentación
- titularidad comercial

### Origen

UNIVERSO.xlsx

### Campos Relevantes

- Codigo
- Cliente
- SegmentoClienteCodigo
- CodVen
- Razon_Social
- Subramo
- Direccion

### Consumidores

#### STAGING

obtener_staging_clientes()

#### CORE

obtener_core_clientes()

#### BUSINESS RULES

business_rules_mn.py

business_rules_ccc.py (planificada)

#### REPORTES

CCC

MiNegocio

Gerencial

Vespertina

---

### Contrato STAGING Garantizado

- Cliente
- Taxonomia
- NombreCliente
- CodVendedor

---

## UNIVERSO_HIST

### Nombre Técnico

universo_hist

### Clasificación

Maestra Histórica

### Estado

✅ Implementada

### Descripción

Histórico completo de snapshots del universo comercial. Permite preservar la evolución temporal de la cartera y registrar los cambios de titularidad.

### Origen

Proceso automático de versionado de Universo

### Campos Relevantes

- FechaSnapshot
- FechaCargaSistema
- HashSnapshot

### Modelo

Una fila por cliente por versión.

### Consumidores

#### Consumidores Actuales

Ninguno.

#### Consumidores Futuros

- Administración SQL
- Auditorías
- Comparación histórica
- Reconstrucción temporal de cartera

---

## UNIVERSO_VERSIONES

### Nombre Técnico

universo_versiones

### Clasificación

Maestra de Control de Versiones

### Estado

✅ Implementada

### Descripción

Catálogo de versiones del universo comercial, encargado de registrar los metadatos y resúmenes de cada snapshot generado.

### Origen

Proceso automático de control de cambios de Universo

### Campos Relevantes

- VersionID
- FechaSnapshot
- FechaCargaSistema
- HashSnapshot
- CantClientes

### Modelo

Una fila por snapshot.

### Consumidores

#### Consumidores Actuales

Ninguno.

#### Consumidores Futuros

- Administración SQL
- Auditorías
- Comparación histórica
- Reconstrucción temporal de cartera

---

## RUTAS

### Nombre Técnico

rutas

### Clasificación

Maestra Operativa

### Descripción

Calendario operativo institucional.

Fuente oficial para:

- días pasados
- días restantes
- ritmo operativo
- proyecciones

### Origen

RUTAS.xlsx

### Campos Relevantes

- Fecha
- CodVen
- CodVendedor
- Vendedor

### Consumidores

#### STAGING

obtener_staging_rutas()

#### CORE

calcular_calendario_y_rutas()

obtener_core_operacion()

---

## ALTAS

### Nombre Técnico

altas

### Clasificación

Maestra Operativa

### Descripción

Registro consolidado de movimientos de cartera.

### Origen

ALTAS.xlsx

### Campos Relevantes

- Fecha
- Codigo
- Estado
- Origen_Hoja

### Tablas Auxiliares

- altas_creacion
- altas_activacion
- altas_inactivacion
- altas_modificacion

### Consumidores

CCC

Gerencial

---

## AUSENCIAS

### Nombre Técnico

ausencias

### Clasificación

Operativa

### Estado

✅ Implementada

### Descripción

Fuente oficial de ausencias y reemplazos de vendedores.

### Propósito Institucional

Determinar:

- CodVendedorOperativo
- reemplazos
- titularidad temporal

### Consumidores

#### STAGING

obtener_staging_ausencias()

#### CORE

procesar_ausencias_y_reemplazos()

obtener_core_operacion()

---

### Contrato STAGING Garantizado

- Fecha_dt
- CodVend_clean
- Reemplazo_clean

---

# C. ENTIDADES STAGING

## Activas

### obtener_staging_vta()

Dominio:

Ventas

### obtener_staging_clientes()

Dominio:

Clientes

### obtener_staging_rutas()

Dominio:

Calendario operativo

### obtener_staging_ausencias()

Dominio:

Ausencias y reemplazos

### obtener_staging_maestros()

Dominio:

Catálogos institucionales

---

# D. ENTIDADES CORE

## obtener_core_ventas_base()

Responsabilidad:

Ventas institucionales base.

---

## obtener_core_clientes()

Responsabilidad:

Clientes institucionales.

---

## obtener_core_vendedores()

Responsabilidad:

Padrón institucional de vendedores.

---

## obtener_core_operacion()

Responsabilidad:

Interpretación operativa consolidada.

Incluye:

- reemplazos
- ausencias
- calendario
- clasificación temporal
- vendedor operativo

---

# E. ENTIDADES BUSINESS RULES

## business_rules_repository.py

### Estado

✅ Implementado

### Responsabilidad

Servicios compartidos reutilizables.

---

## business_rules_kilos.py

### Estado

✅ Implementado  
✅ Validado  
✅ Productivo

### Dominio Funcional

Kilos

### Responsabilidades

- Matriz comercial de Kilos
- Objetivos
- Clasificación operativa
- Integración con CORE
- Consumo de reemplazos

### Consumidores

rep_kilos_core.py

---

## business_rules_mn.py

### Estado

✅ Implementado  
✅ Validado  
✅ Productivo

### Dominio Funcional

MiNegocio

### Responsabilidades

- Ventas Totales
- Ventas MiNegocio
- Pct_MiNegocio
- Clasificación Digital
- No Digital
- Híbrido
- Fully Digital
- Minimo_Facturacion_70
- Adopción Digital
- Matriz Comercial de Cliente

### Validación Institucional

✅ TOTAL CARTERA = 5617

✅ CodVendedor -998 = 0

### Consumidores

rep_MN_core.py

### Consumidores Futuros Aprobados

rep_gerencial.py

---

## business_rules_ccc.py

### Estado

⏳ Planificada

### Próxima Prioridad Institucional

CCC

### Arquitectura Objetivo

rep_ccc_core.py
↓
business_rules_ccc.py
↓
core_*

### Objetivo

Desacoplar completamente las reglas comerciales de CCC del reporte histórico.