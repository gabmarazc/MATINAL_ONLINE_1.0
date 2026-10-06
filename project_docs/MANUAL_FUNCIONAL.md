# MANUAL_FUNCIONAL.md

Versión: 3.0
Fecha de actualización: 30/09/2026
Estado: Vigente
Naturaleza: Fuente de Verdad Funcional Institucional

---

# 1. PROPÓSITO

Este documento constituye la referencia funcional oficial del sistema MATINAL.

Su objetivo es definir:

* Cómo se interpreta la operación comercial.


* Qué reglas funcionales son válidas.


* Qué criterios utiliza el negocio.


* Qué condiciones determinan indicadores, coberturas y métricas.


* Qué reglas tienen prioridad cuando existe conflicto.



Este documento no describe:

* Código.


* Arquitectura.


* Migraciones.


* Implementaciones técnicas.



Su propósito es describir exclusivamente el comportamiento funcional esperado del sistema.

---

# 2. JERARQUÍA DE REGLAS

Cuando dos reglas entren en conflicto deberá respetarse la siguiente jerarquía.

## Nivel 1

Reglas Institucionales Críticas.

## Nivel 2

Reglas Operativas.

## Nivel 3

Reglas Comerciales.

## Nivel 4

Reglas de Dominio.

## Nivel 5

Reglas de Reporte.

Una regla de mayor nivel siempre prevalece sobre una de nivel inferior.

---

# 3. REGLAS INSTITUCIONALES CRÍTICAS

## RC-001 - Problema de Cierre

### Prioridad

Nivel 1

### Definición

Una venta pertenece al período operativo cuando:

FechaCarga y FechaLiquidacion pertenecen al mismo período operativo

o bien

FechaLiquidacion es nula.

### Alcance

Toda la plataforma.

### Observación

Ninguna optimización técnica puede modificar esta definición.

---

## RC-002 - Exclusión Global de Empleados

### Prioridad

Nivel 1

### Objetivo

Excluir registros que no representan actividad comercial real.

### Campo Evaluado

Subramo

### Valores Excluidos

* EMPLEADOS


* EMPLOYEES



### Alcance

Toda la plataforma.

---

## RC-003 - Filtro Corporativo PepsiCo

### Prioridad

Nivel 1

### Objetivo

Restringir el análisis a operaciones PepsiCo.

### Campo Evaluado

Proveedor

### Resultado

Sólo se consideran operaciones correspondientes al proveedor PepsiCo.

---

## RC-004 - Exclusión del Vendedor 20

### Prioridad

Nivel 1

### Objetivo

Excluir movimientos correspondientes al depósito.

### Campo

CodVendedor

### Regla

Excluir:

CodVendedor = 20

---

# 4. REGLAS OPERATIVAS

## RO-001 - Titularidad Operativa y Cartera Operativa

### Objetivo

Determinar quién ejecutó efectivamente una venta y construir la cartera operativa institucional a partir del universo elegible y la evidencia transaccional.

### Resultado

* CodVendedorOperativo


* Cartera Operativa por Vendedor

---

## RO-002 - Reemplazos

### Regla

Sin reemplazo:

CodVendedorOperativo = CodVendedor

Con reemplazo:

CodVendedorOperativo = Reemplazo

---

## RO-003 - Continuidad Operativa

### Objetivo

Garantizar continuidad comercial frente a ausencias temporales.

### Resultado

La operación se atribuye al vendedor que efectivamente ejecutó la gestión.

---

## RO-003A - Compensaciones por Reemplazo

### Objetivo

Preservar la correcta atribución comercial del volumen cuando una operación es ejecutada por un vendedor distinto del titular original.

### Principio

La ejecución operativa y la titularidad comercial constituyen conceptos diferentes.

Una venta puede:

* pertenecer comercialmente a un vendedor


* ser ejecutada operativamente por otro



simultáneamente.

### Variables Involucradas

CodVendedorHistorico

Titular original de la operación.

CodVendedorOperativo

Vendedor que ejecutó efectivamente la gestión.

### Regla

Cuando:

CodVendedorOperativo ≠ CodVendedorHistorico

se considera que existe una operación realizada mediante reemplazo.

### Consecuencia

El volumen comercial deberá:

* descontarse del titular histórico


* acreditarse al vendedor operativo



manteniendo conservación total de masa.

### Restricción Temporal

Sólo participan operaciones clasificadas como:

* Arrastre


* Actual



Quedan excluidas:

* Futuro


* Fuera de Período



### Principio de Balance

Toda compensación deberá cumplir:

Suma de descuentos = Suma de acreditaciones

No se admiten pérdidas ni generación artificial de volumen.

### Vendedor Institucional de Reemplazo

Cuando corresponda utilizar un vendedor comodín de reemplazos, el identificador institucional aprobado es:

CodVendedor = 99

Nombre:

REEMPLAZO

### Estado

✅ Regla validada mediante auditoría forense de compensaciones.

---

## RO-004 - Clasificación Temporal

Toda venta debe clasificarse en una única categoría temporal.

### Arrastre

Carga mes anterior.

Entrega mes actual.

### Actual

Carga mes actual.

Entrega mes actual.

### Futuro

Carga mes actual.

Entrega mes siguiente.

### Fuera de Período

No cumple ninguna condición institucional.

---

## RO-005 - Día Matinal

### Objetivo

Construir la fotografía operativa del período.

### Regla

Las ventas posteriores al Día Matinal no participan del estado operativo vigente.

---

## RO-006 - Calendario Operativo

### Objetivo

Determinar avance operativo de vendedores.

### Resultados

* días trabajados


* días restantes


* días ajustados


* ritmo de ejecución



---

# 5. REGLAS DE CCC

## CCC-001 - Cliente con Compra

### Definición

Un cliente se considera comprador cuando cumple simultáneamente:

CantBase >= 3

Importe Neto > 0

---

## CCC-002 - Cartera Neta

### Objetivo

Construir el universo evaluable de CCC a partir de la cartera operativa institucional.

### Consideraciones

* Altas


* Reactivaciones


* Inactivaciones


* Cierres definitivos



---

## CCC-003 - Evaluación Comercial

La evaluación CCC se realiza sobre la cartera neta del período.

---

## CCC-004 - Objetivo CCC

Los objetivos CCC se calculan sobre clientes válidos dentro de la cartera evaluable.

---

# 6. REGLAS DE MINEGOCIO

## MN-001 - Adopción Digital

### Objetivo

Medir participación del canal digital en las compras de un cliente.

### Variables

Ventas_Totales

Ventas_MiNegocio

### Indicador

Pct_MiNegocio

---

## MN-002 - Clasificación Digital

### No Digital

Pct_MiNegocio <= 0.01

### Híbrido

Pct_MiNegocio > 0.01

Pct_MiNegocio < 70

### Fully Digital

Pct_MiNegocio >= 70

---

## MN-003 - Gap de Digitalización

### Objetivo

Determinar cuánto volumen adicional necesita migrar un cliente hacia MiNegocio.

### Indicador

Minimo_Facturacion_70

---

## MN-004 - Fuente de Verdad Comercial

La adopción digital se define exclusivamente mediante:

* ventas totales


* ventas MiNegocio



No se utilizan encuestas ni clasificaciones manuales.

---

# 7. REGLAS DE COBERTURA

## COB-001 - Cobertura de Marca

### Definición

Un cliente se considera cubierto en una marca cuando:

CantBase >= 3

---

## COB-002 - Cobertura de Innovación

### Definición

Un cliente se considera cubierto en innovación cuando:

CantBase >= 3

---

## COB-003 - Cobertura Efectiva

La cobertura sólo puede generarse mediante compras válidas.

---

# 8. REGLAS DE OBJETIVOS

## OBJ-001 - Objetivos de Vendedor

Los objetivos se asignan por:

* vendedor


* segmento


* período



---

## OBJ-002 - Fuente Institucional

La fuente oficial de objetivos es:

objetivos_vendedores

---

## OBJ-003 - Cumplimiento

Toda evaluación de cumplimiento se realiza contra el objetivo vigente del período.

---

# 9. REGLAS DE KILOS

## KG-001 - Volumen Comercial

El volumen comercial se mide mediante:

PesoKg

---

## KG-002 - Ritmo de Ejecución

El ritmo de ejecución surge del cruce entre:

* volumen acumulado


* calendario operativo



---

## KG-003 - Proyección

Las proyecciones utilizan:

* avance actual


* días restantes


* calendario operativo



---

# 10. REGLAS DE REPORTES

## REP-001 - Pace

### Objetivo

Medir velocidad de ejecución comercial.

---

## REP-002 - Efectividad

### Objetivo

Medir cumplimiento respecto de objetivos.

---

## REP-003 - Compensaciones

### Objetivo

Determinar niveles de cumplimiento y compensación.

---

## REP-004 - Dashboard Gerencial

### Objetivo

Consolidar indicadores comerciales institucionales.

---

## REP-005 - Vespertina

### Objetivo

Auditar el impacto operativo del Día Venta.

---

# 11. CONFLICTOS Y PRECEDENCIAS

Si una venta cumple una regla comercial pero viola:

* Problema de Cierre


* Filtro Empleados


* Filtro PepsiCo


* Exclusión Vendedor 20



la venta queda excluida.

Las reglas críticas siempre prevalecen sobre reglas comerciales.

---

# 12. FUENTE DE VERDAD FUNCIONAL

Las reglas definidas en este documento constituyen la referencia funcional oficial del sistema MATINAL.

Toda nueva funcionalidad deberá:

1. Identificar la regla funcional asociada.


2. Clasificar la regla dentro de este manual.


3. Respetar la jerarquía institucional.


4. Mantener compatibilidad con las reglas críticas.



Si existe discrepancia entre código y este documento:

la discrepancia debe ser investigada y documentada explícitamente.