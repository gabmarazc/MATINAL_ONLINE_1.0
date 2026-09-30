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
### Actualización 29/09/2026

Se inició la consolidación práctica de CORE_VENTAS_BASE mediante:

core_ventas_base.py

La entidad ya se encuentra siendo utilizada como base de futuras migraciones hacia Business Rules.

Migraciones asociadas:

✅ Kilos
⏳ MiNegocio
⏳ CCC
⏳ Coberturas

Estado:

Implementación inicial en evolución.