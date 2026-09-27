# CORE_VENTAS_BASE V1

## Estado

Proyecto: MATINAL ONLINE

Fase:
5.3

Estado:
DISEÑADO

Implementación:
Pendiente

---

# Objetivo

CORE_VENTAS_BASE constituye la definición corporativa única de una venta dentro del ecosistema MATINAL.

Su misión es transformar una venta proveniente de STAGING_VTA en una venta corporativa normalizada, tipada y temporalmente clasificada.

CORE_VENTAS_BASE debe ser completamente independiente de cualquier reporte específico.

No pertenece a CCC.

No pertenece a MN+.

No pertenece a TP.

No pertenece a Coberturas.

Debe servir como base común para todos ellos.

---

# Fuente

Entrada:

STAGING_VTA

---

# Preguntas que responde

CORE_VENTAS_BASE responde:

¿Qué venta existe?

¿Quién realizó originalmente la venta?

¿Cuándo ocurrió?

¿Cómo debe interpretarse temporalmente?

No responde:

¿Cuenta para CCC?

¿Cuenta para MN?

¿Cuenta para TP?

¿Tiene reemplazo?

¿Es PepsiCo?

---

# Responsabilidades

## 1. Normalización de identificadores

Normalizar y tipar:

Cliente

CodVendedor

Resultado esperado:

Int64

---

## 2. Normalización de magnitudes

Normalizar:

CantBase

ImporteNeto

PesoKg

Resultado esperado:

Numérico

---

## 3. Parseo corporativo de fechas

Generar:

FechaCarga_dt

FechaEntrega_dt

FechaLiquidacion_dt

cuando corresponda.

---

## 4. Conservación de atributos comerciales

Mantener sin filtrar:

Proveedor

Marca

Articulo

TipoDeVenta

---
