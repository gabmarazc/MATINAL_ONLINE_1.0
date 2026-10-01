# CORE_VENTAS_BASE_V1

Versión: 3.0  
Fecha de actualización: 30/09/2026  
Estado: Vigente  
Estado de Implementación: Implementado Parcialmente  
Estado de Producción: Utilizado en producción  
Estado Arquitectónico: En consolidación

---

# 1. PROPÓSITO

CORE_VENTAS_BASE representa la definición institucional única de una venta dentro del ecosistema MATINAL.

Su objetivo es construir una entidad comercial común que pueda ser reutilizada por todos los dominios funcionales del sistema.

La existencia de CORE_VENTAS_BASE evita que cada reporte o dominio comercial vuelva a reinterpretar qué constituye una venta válida.

---

# 2. POSICIÓN ARQUITECTÓNICA

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

# 3. PRINCIPIO FUNDAMENTAL

Toda venta consumida por:

- CCC
- MiNegocio
- Kilos
- Coberturas
- Tienda Perfecta
- Gerencial
- Vespertina

debería provenir de una definición institucional común.

---

# 4. ESTADO ACTUAL

CORE_VENTAS_BASE ya participa activamente en la arquitectura del sistema.

Actualmente es utilizado por migraciones productivas validadas.

Sin embargo todavía continúa evolucionando hacia su objetivo final de convertirse en la fuente única institucional de venta.

Estado actual:

✅ Implementado parcialmente

✅ Utilizado por Kilos

✅ Utilizado por MiNegocio

✅ Validado en producción

🟡 En consolidación progresiva

---

# 5. FUENTE OFICIAL DE ENTRADA

## Entrada Obligatoria

obtener_staging_vta()

---

## Dependencia Obligatoria

CORE_VENTAS_BASE debe consumir exclusivamente:

obtener_staging_vta()

---

## Prohibiciones

No debe leer directamente:

- Excel
- SQLite
- CSV
- APIs externas
- Reportes

---

# 6. PREGUNTAS QUE RESPONDE

CORE_VENTAS_BASE responde:

- ¿Qué venta existe?
- ¿Qué cliente interviene?
- ¿Quién es el vendedor titular?
- ¿Qué fechas posee?
- ¿Qué atributos comerciales posee?
- ¿Qué magnitudes posee?
- ¿Qué información institucional debe preservarse?

---

# 7. PREGUNTAS QUE NO RESPONDE

CORE_VENTAS_BASE no responde:

- ¿Cuenta para CCC?
- ¿Cuenta para MiNegocio?
- ¿Cuenta para Cobertura?
- ¿Cuenta para TP?
- ¿Cuenta para Objetivos?
- ¿Tiene comisión?
- ¿Tiene compensación?
- ¿Debe excluirse por una regla comercial?

Estas preguntas pertenecen exclusivamente a BUSINESS RULES.

---

# 8. RESPONSABILIDADES

## R-001 Normalización de Identificadores

Garantizar:

- Cliente
- CodVendedor

en formato institucional consistente.

Resultado esperado:

Int64

---

## R-002 Normalización de Magnitudes

Garantizar tipado consistente de:

- CantBase
- PesoKg
- ImporteNetoItem

Resultado esperado:

Numérico

---

## R-003 Normalización Temporal

Garantizar disponibilidad de:

- FechaCarga_dt
- FechaEntrega_dt
- FechaLiquidacion_dt

cuando corresponda.

---

## R-004 Conservación de Atributos

Mantener sin reinterpretar:

- Proveedor
- Marca
- Articulo
- Subramo
- TipoDeVenta
- Segmento
- Canal
- Taxonomía

Las clasificaciones posteriores pertenecen a otras capas.

---

# 9. RELACIÓN CON PROBLEMA DE CIERRE

CORE_VENTAS_BASE debe mantener compatibilidad con la definición institucional:

```text
Una venta pertenece al período operativo cuando:

FechaCarga y FechaLiquidacion
pertenecen al mismo período operativo

o bien

FechaLiquidacion es nula.
```

La regla:

Problema de Cierre

posee prioridad institucional superior a cualquier consideración técnica.

---

# 10. RELACIÓN CON DÍA MATINAL

CORE_VENTAS_BASE no aplica filtros de Día Matinal.

Debe conservar íntegramente la información disponible.

La interpretación temporal pertenece a:

- CORE_OPERACION
- BUSINESS RULES

---

# 11. RELACIÓN CON AUSENCIAS

CORE_VENTAS_BASE no aplica reemplazos.

No genera:

CodVendedorOperativo

No interpreta:

- Ausencias
- Reemplazos

Estas responsabilidades pertenecen a:

CORE_OPERACION

---

# 12. CONTRATO DE SALIDA ESPERADO

La entidad deberá contener como mínimo:

- Cliente
- CodVendedor
- FechaCarga_dt
- FechaEntrega_dt
- FechaLiquidacion_dt
- CantBase
- PesoKg
- ImporteNetoItem
- Marca
- Proveedor
- Articulo
- Subramo
- TipoDeVenta

---

# 13. RESTRICCIONES ARQUITECTÓNICAS

## Permitido

✅ Normalizar

✅ Tipar

✅ Validar consistencia

✅ Construir contratos institucionales

✅ Unificar interpretación de venta

---

## Prohibido

❌ Aplicar reemplazos

❌ Calcular CCC

❌ Calcular MiNegocio

❌ Calcular Coberturas

❌ Calcular Objetivos

❌ Calcular Pace

❌ Calcular Efectividad

❌ Calcular Compensaciones

❌ Aplicar filtros comerciales

---

# 14. CONSUMIDORES ACTUALES

## Kilos

Arquitectura:

rep_kilos_core.py
↓
business_rules_kilos.py
↓
core_ventas_base.py

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
core_ventas_base.py

Estado:

✅ Productivo

✅ Validado

---

# 15. CONSUMIDORES FUTUROS APROBADOS

- CCC
- Cobertura Marca
- Cobertura Innovación
- Gerencial
- Vespertina
- Objetivos

---

# 16. BENEFICIO INSTITUCIONAL

CORE_VENTAS_BASE busca:

- Eliminar interpretaciones múltiples de venta.
- Garantizar consistencia transversal.
- Reducir duplicación de lógica.
- Facilitar auditorías.
- Simplificar migraciones.
- Consolidar BUSINESS RULES.

---

# 17. VALIDACIÓN ARQUITECTÓNICA

Las migraciones exitosas de:

✅ Kilos

✅ MiNegocio

han validado la conveniencia de mantener una definición institucional única de venta.

Resultado:

✅ Estrategia confirmada

✅ Reutilización efectiva observada

✅ Compatibilidad entre dominios comerciales

✅ Menor duplicación de reglas

---

# 18. PRÓXIMO CONSUMIDOR APROBADO

CCC

Arquitectura objetivo:

rep_ccc_core.py
↓
business_rules_ccc.py
↓
core_ventas_base.py

---

# 19. ESTADO FINAL

CORE_VENTAS_BASE

✅ Implementado parcialmente

✅ Utilizado en producción

✅ Consumido por múltiples dominios

✅ Estratégicamente validado

🟡 En consolidación como fuente única institucional de venta

Objetivo final:

Convertirse en la definición oficial única de venta para todo MATINAL.