### Glosario de Reglas de Negocio - MATINAL
  
Versión: 2.0
Fecha de actualización: 28/09/2026
Estado: Vigente
Estado de validación: Producción Operativa

## 1. Identificación y Propósito
  
El presente documento constituye la Fuente de Verdad Institucional sobre las reglas funcionales, operativas y comerciales del sistema MATINAL.
  
Su propósito es:
- Definir las reglas vigentes.
- Clasificar cada regla dentro de una capa arquitectónica.
- Preservar el conocimiento funcional del negocio.
- Mantener alineación entre documentación y código.

Arquitectura oficial:

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

Principio institucional:

```text
STAGING normaliza.
CORE interpreta operación.
BUSINESS RULES aplica decisiones comerciales.
REPORTES construyen indicadores y visualizaciones.
```

## 2. REGLAS DE STAGING
  
Las reglas de esta sección pertenecen exclusivamente a STAGING.

Objetivo:

```text
Construir contratos de datos consistentes.
```

STAGING no puede contener:

```text
Objetivos
CCC
MN+
Coberturas
Compensaciones
Pace
KPIs
Lógica Comercial
```

### STG-001 - Normalización de Ventas

#### Capa

STAGING

#### Entidad

obtener_staging_vta()

#### Objetivo
  
Convertir la tabla transaccional de ventas en una entidad técnicamente consistente.

#### Responsabilidades

```text
Tipado de identificadores
Conversión numérica
Parseo robusto de fechas
Normalización de marcas
Generación de contrato técnico
```

#### Contrato Generado

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

### STG-002 - Normalización de Clientes

#### Capa

STAGING

#### Entidad

obtener_staging_clientes()

#### Objetivo
  
Normalizar el padrón institucional de clientes.

#### Responsabilidades

```text
Tipado de identificadores
Normalización de taxonomías
Normalización de nombre cliente
Normalización de vendedor
```

#### Contrato Generado

```text
Cliente
Taxonomia
NombreCliente
CodVendedor
```

### STG-003 - Normalización de Rutas

#### Capa

STAGING

#### Entidad

obtener_staging_rutas()

#### Objetivo
  
Centralizar el acceso técnico al calendario operativo.

#### Responsabilidades

```text
Lectura SQLite
Entrega consistente del calendario
```

### STG-004 - Normalización de Ausencias

#### Capa

STAGING

#### Entidad

obtener_staging_ausencias()

#### Estado

```text
Implementada
Validada en Producción
FASE 4.7 Completada
```

#### Objetivo
  
Convertir ausencias en una entidad técnica independiente.

#### Responsabilidades

```text
Lectura SQLite
Detección de columnas
Parseo robusto de fechas
Conversión a Int64
Normalización
```

#### Contrato Generado

```text
Fecha_dt
CodVend_clean
Reemplazo_clean
```

### STG-005 - Centralización de Maestros

#### Capa

STAGING

#### Entidad

obtener_staging_maestros()

#### Objetivo
  
Centralizar maestros institucionales consumidos por CORE.

#### Entidades Incluidas

```text
maestro_vendedores
maestro_ccc
maestro_marcas_cebe
maestro_segmentos
ausencias
```

## 3. REGLAS CORE
  
Las reglas de esta sección pertenecen a CORE.

CORE transforma contratos técnicos en estructuras operativas.

### COR-001 - Titularidad Operativa de Venta

#### Capa

CORE

#### Entidad

procesar_ausencias_y_reemplazos()

#### Objetivo
  
Determinar quién ejecutó realmente una venta.

#### Resultado

```text
CodVendedorOperativo
```

### COR-002 - Reasignación por Ausencias

#### Capa

CORE

#### Entidad

procesar_ausencias_y_reemplazos()

#### Objetivo
  
Garantizar continuidad operativa ante ausencias.

#### Regla

Sin reemplazo:

```text
CodVendedorOperativo = CodVendedor
```

Con reemplazo:

```text
CodVendedorOperativo = Reemplazo
```

### COR-003 - Construcción de Claves AUS

#### Capa

CORE

#### Objetivo
  
Vincular ventas con ausencias.

#### ClaveAUS_Carga

```text
CodVendedor + FechaCarga
```

#### ClaveAUS_Entrega

```text
CodVendedor + FechaEntrega
```

#### ClaveAUS

```text
CodVend_clean + Fecha_dt
```

### COR-004 - Corte por Día Matinal

#### Capa

CORE

#### Entidad

calcular_ritmo_operativo()

#### Objetivo
  
Construir la fotografía operacional del período.

#### Regla

```text
Excluir registros cuya FechaCarga sea igual o posterior al Día Matinal.
```

### COR-005 - Clasificación Temporal Institucional

#### Capa

CORE

#### Entidad

calcular_ritmo_operativo()

#### Clasificaciones

##### Arrastre

```text
Carga mes anterior
Entrega mes actual
```

##### Actual

```text
Carga mes actual
Entrega mes actual
```

##### Futuro

```text
Carga mes actual
Entrega mes siguiente
```

##### Fuera de Periodo

```text
No cumple criterios institucionales
```

### COR-006 - Calendario Operativo

#### Capa

CORE

#### Entidad

calcular_calendario_y_rutas()

#### Objetivo
  
Determinar días operativos por vendedor.

#### Resultados

```text
dias_pasados_map
dias_restantes_map
total_dias_pasados
total_dias_restantes
```

### COR-007 - Ajuste por Rutas Ajustadas

#### Capa

CORE

#### Entidad

calcular_calendario_y_rutas()

#### Objetivo
  
Descontar rutas ajustadas de los días restantes.

#### Modo AJUSTADO

```text
Aplica descuento de rutas ajustadas.
```

#### Modo TODO

```text
No aplica descuento.
```

### COR-008 - Definición de Venta Base

#### Capa

CORE

#### Entidad

obtener_core_ventas_base()

#### Estado

IMPLEMENTADO PARCIALMENTE

#### Situación Arquitectónica

La entidad existe en producción y actualmente proporciona una primera definición institucional de venta basada en contratos normalizados provenientes de STAGING.

La consolidación definitiva de CORE_VENTAS_BASE continúa formando parte del roadmap arquitectónico y evolucionará hasta convertirse en la fuente única de verdad para todas las interpretaciones comerciales de venta.

#### Objetivo

Representar una venta mediante una definición institucional única y reutilizable para toda la plataforma.

#### Entidad Base

```text
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
```

#### Restricciones

No aplica:

```text
CCC
MN+
Coberturas
Compensaciones
Objetivos
Reemplazos
```

#### Evolución Esperada

CORE_VENTAS_BASE deberá transformarse progresivamente en la entidad institucional común consumida por:

- CCC
- Mi Negocio
- Kilos
- Coberturas
- Gerencial
- Vespertina
- Objetivos

con el fin de eliminar interpretaciones divergentes sobre qué constituye una venta válida dentro de MATINAL.

## 4. REGLAS BUSINESS RULES
  
Las reglas de esta sección representan decisiones de negocio.

Actualmente la capa BUSINESS RULES se encuentra parcialmente desacoplada.

### BR-001 - Filtro Global de Empleados

#### Capa Objetivo

BUSINESS RULES

#### Objetivo
  
Excluir empleados de los análisis comerciales.

#### Campo

Subramo

#### Valores

```text
EMPLOYEES
EMPLEADOS
```

#### Prioridad

```text
Crítica
```

### BR-002 - Exclusión de Comodatos y Préstamos

#### Capa Objetivo

BUSINESS RULES

#### Objetivo
  
Excluir operaciones que no representan ventas comerciales.

#### Valores Excluidos

```text
Comodato Devolución
Comodato Ficticio
Comodato Ficticio Devolución
Comodato Préstamo
```

### BR-003 - Filtro Corporativo PepsiCo

#### Capa Objetivo

BUSINESS RULES

#### Objetivo
  
Delimitar los análisis a ventas PepsiCo.

#### Campo

```text
Proveedor
```

### BR-004 - Exclusión del Vendedor 20

#### Capa Objetivo

BUSINESS RULES

#### Objetivo
  
Excluir movimientos correspondientes al depósito.

#### Campo

```text
CodVendedor
```

#### Regla

```text
Excluir vendedor 20.
```

### BR-005 - Problema de Cierre

#### Capa Objetivo

BUSINESS RULES

#### Estado

```text
Regla Institucional Prioritaria
```

#### Definición

Una venta pertenece al período operativo cuando:

```text
FechaCarga y FechaLiquidacion
pertenecen al mismo período operativo
```

o bien:

```text
FechaLiquidacion es nula.
```

### BR-006 - Definición de Cliente CCC

#### Capa Objetivo

BUSINESS RULES

#### Objetivo
  
Determinar clientes con compra válida.

#### Requisitos

```text
CantBase >= 3
Importe Neto > 0
```

### BR-007 - Cartera Neta

#### Capa Objetivo

BUSINESS RULES

#### Objetivo
  
Construir el universo evaluable de CCC.

#### Consideraciones

```text
Altas
Reactivaciones
Inactivaciones
Cierre Definitivo
```

### BR-008 - Cobertura por Marca

#### Capa Objetivo

BUSINESS RULES

#### Objetivo
  
Determinar cobertura efectiva de marca.

#### Regla

```text
CantBase >= 3
```

### BR-009 - Cobertura por Innovación

#### Capa Objetivo

BUSINESS RULES

#### Objetivo
  
Determinar cobertura efectiva de innovación.

#### Regla

```text
CantBase >= 3
```

#### Fuente

```text
maestro_innovaciones
```

### BR-010 - Clasificación Digital

#### Capa Objetivo

BUSINESS RULES

#### Objetivo
  
Clasificar adopción digital.

#### Categorías

```text
No Digital
Híbrido
Fully Digital
```

### BR-011 - Gap a 70% Digital

#### Capa Objetivo

BUSINESS RULES

#### Objetivo
  
Determinar el faltante para alcanzar 70% de adopción digital.

### BR-012 - Objetivos de Vendedores

#### Capa

BUSINESS RULES

#### Entidad

obtener_objetivos_vendedores()

#### Fuente

```text
objetivos_vendedores
```

#### Contrato

```text
CodVendedor
SEGMENTO
Obj_Sugerido_Kg
```

## 5. REGLAS DE REPORTES
  
Las reglas de esta sección pertenecen a los reportes y tableros.

### REP-001 - Proyección de Kilos

#### Capa

REPORTES

#### Objetivo
  
Estimar el cierre mensual.

#### Insumos

```text
CORE_OPERACION
Dias Restantes
PesoKg
Calendario Operativo
```

### REP-002 - Pace

#### Capa

REPORTES

#### Objetivo
  
Medir velocidad de ejecución comercial.

### REP-003 - Efectividad

#### Capa

REPORTES

#### Objetivo
  
Medir desempeño comercial respecto de objetivos.

### REP-004 - Compensaciones

#### Capa

REPORTES

#### Objetivo
  
Determinar niveles de cumplimiento y compensación.

### REP-005 - Dashboard Gerencial

#### Capa

REPORTES

#### Funciones

```text
Seguimiento Directivo
Consolidación Comercial
Proyecciones
```

### REP-006 - Kilos

#### Capa

REPORTES

#### Funciones

```text
Avance
Objetivos
Proyecciones
Compensaciones
Reemplazos
```

### REP-007 - CCC

#### Capa

REPORTES

#### Funciones

```text
Cartera
Altas
Reactivaciones
Batalla NC
```

### REP-008 - Mi Negocio

#### Capa

REPORTES

#### Funciones

```text
Adopción Digital
Clasificación Digital
Gap a Objetivo
```

### REP-009 - Cobertura Marca

#### Capa

REPORTES

#### Función

```text
Cobertura de marcas estratégicas.
```

### REP-010 - Cobertura Innovación

#### Capa

REPORTES

#### Función

```text
Cobertura de innovaciones estratégicas.
```

### REP-011 - Vespertina

#### Capa

REPORTES

#### Función

```text
Auditoría operativa del Día Venta.
```

### REP-012 - Objetivos

#### Capa

REPORTES

#### Función

```text
Seguimiento de objetivos comerciales.
```

## 6. Fuente de Verdad
  
Las reglas definidas en este documento constituyen la referencia institucional vigente para:

```text
STAGING
CORE
BUSINESS RULES
REPORTES
```

Toda nueva regla deberá clasificarse explícitamente dentro de una de estas capas antes de incorporarse al sistema.