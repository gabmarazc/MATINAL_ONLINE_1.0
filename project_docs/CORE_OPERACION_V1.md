# CORE_OPERACION_V1

Versión: 3.0

Fecha de actualización: 30/09/2026

Estado: Vigente

Estado de Producción: Operativo

---

# 1. PROPÓSITO

CORE_OPERACION constituye el núcleo operativo institucional del sistema MATINAL.

Su responsabilidad es transformar contratos técnicos provenientes de STAGING en estructuras operativas reutilizables por cualquier dominio comercial.

CORE_OPERACION no realiza ETL.

CORE_OPERACION no aplica reglas comerciales.

CORE_OPERACION interpreta la operación.

---

# 2. POSICIÓN ARQUITECTÓNICA

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

# 3. RESPONSABILIDAD INSTITUCIONAL

CORE_OPERACION es responsable de determinar:

* construcción de cartera operativa por vendedor
* titularidad operativa
* vendedor operativo
* reemplazos
* ausencias
* clasificación temporal
* calendario operativo
* ritmo operativo



No es responsable de:

* CCC
* MiNegocio
* Coberturas
* Objetivos
* Pace
* Efectividad
* Compensaciones
* KPIs
* Clasificaciones comerciales



---

# 4. CONSTRUCCIÓN DE CARTERA OPERATIVA

## Principios Institucionales

* UNIVERSO = universo elegible
* VTA = evidencia transaccional válida
* CORE_OPERACION = constructor oficial de cartera operativa

## Resultado

* Cartera Operativa por Vendedor

## Flujo Institucional

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

## Consideración Metodológica

La cartera consumida por los dominios comerciales no surge directamente de UNIVERSO.

La cartera operativa institucional surge de la interpretación realizada por CORE_OPERACION utilizando:

* universo elegible
* evidencia transaccional válida
* reglas operativas institucionales

---

# 5. ENTRADAS OFICIALES

## obtener_staging_vta()

Contrato esperado:

* FechaCarga_dt
* FechaEntrega_dt
* CodVendedor
* Cliente
* CantBase
* ImporteNetoItem
* PesoKg
* Marca



---

## obtener_staging_rutas()

Contrato esperado:

Calendario operativo normalizado.

---

## obtener_staging_ausencias()

Contrato esperado:

* Fecha_dt
* CodVend_clean
* Reemplazo_clean

Estado:

✅ Implementado

✅ Validado

---

## obtener_staging_maestros()

Contrato esperado:

* maestro_vendedores
* maestro_ccc
* maestro_segmentos
* maestro_marcas_cebe



---

# 6. FLUJO OFICIAL

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

# 7. PROCESAR AUSENCIAS Y REEMPLAZOS

## Función

procesar_ausencias_y_reemplazos()

## Objetivo

Determinar quién ejecutó efectivamente una operación.

## Resultado Principal

CodVendedorOperativo

---

## Claves Generadas

### ClaveAUS_Carga

CodVendedor + FechaCarga

### ClaveAUS_Entrega

CodVendedor + FechaEntrega

### ClaveAUS

CodVend_clean + Fecha_dt

---

## Regla Operativa

### Sin Reemplazo

Condición:

No existe coincidencia en AUSENCIAS.

Resultado:

CodVendedorOperativo = CodVendedor

---

### Con Reemplazo

Condición:

Existe coincidencia en AUSENCIAS.

Resultado:

CodVendedorOperativo = Reemplazo

---

# 8. CLASIFICACIÓN TEMPORAL

## Función

calcular_ritmo_operativo()

## Categorías Institucionales

### Arrastre

Carga mes anterior

Entrega mes actual

---

### Actual

Carga mes actual

Entrega mes actual

---

### Futuro

Carga mes actual

Entrega mes siguiente

---

### Fuera de Periodo

No cumple criterios institucionales.

---

# 9. CALENDARIO OPERATIVO

## Función

calcular_calendario_y_rutas()

## Resultados

* dias_pasados_map
* dias_restantes_map
* total_dias_pasados
* total_dias_restantes



---

## Propósito

Entregar una interpretación oficial del avance operativo de cada vendedor.

---

# 10. CONTRATO DE SALIDA

## Función

obtener_core_operacion()

## Retorno

### df_vta_operativa

Estructura operativa consolidada.

### Métricas de Calendario

* dias_pasados_map
* dias_restantes_map
* total_dias_pasados
* total_dias_restantes



---

# 11. PRINCIPIOS INSTITUCIONALES

## PI-001

CORE_OPERACION no contiene reglas comerciales.

---

## PI-002

CORE_OPERACION sólo consume contratos provenientes de STAGING.

---

## PI-003

Toda lógica comercial debe residir en BUSINESS RULES.

---

## PI-004

Toda entidad comercial debe consumir CORE y no replicar lógica operativa.

---

# 12. CONSUMIDORES PRODUCTIVOS CONFIRMADOS

## Kilos

Arquitectura:

rep_kilos_core.py
↓
business_rules_kilos.py
↓
obtener_core_operacion()

Resultado:

✅ Productivo

✅ Validado

---

## MiNegocio

Arquitectura:

rep_MN_core.py
↓
business_rules_mn.py
↓
obtener_core_operacion()

Resultado:

✅ Productivo

✅ Validado

---

## CCC

Arquitectura:

rep_ccc_core.py
↓
business_rules_ccc.py
↓
obtener_core_operacion()

Resultado:

✅ Productivo

✅ Validado

---

# 13. VALIDACIÓN INSTITUCIONAL

CORE_OPERACION ha sido validado mediante múltiples dominios comerciales independientes.

Dominios validados:

✅ Kilos

✅ MiNegocio

✅ CCC

Resultado:

✅ Componente transversal

✅ Reutilizable

✅ Estable

✅ Sin conocimiento comercial embebido

---

# 14. EVOLUCIÓN APROBADA

## FASE 4.8

Estado:

⏳ Pendiente

Nombre:

Eliminación de ETL duplicado en CORE

Objetivo:

Eliminar lógica técnica heredada actualmente presente en:

procesar_ausencias_y_reemplazos()

que ya existe en:

obtener_staging_ausencias()

Resultado esperado:

STAGING = 100% ETL

CORE = 100% Operación

---

# 15. ESTADO ACTUAL

CORE_OPERACION

✅ Implementado

✅ Validado

✅ Productivo

✅ Reutilizable

✅ Consumido por múltiples dominios

✅ Componente institucional consolidado