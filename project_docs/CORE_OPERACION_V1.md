# CORE_OPERACION V1

Versión: 2.0

Fecha última actualización:
27/09/2026

Estado:
IMPLEMENTADO Y VALIDADO

Estado de Producción:
OPERATIVO

---

# Objetivo

CORE_OPERACION constituye el núcleo operativo institucional del sistema MATINAL.

Su responsabilidad es transformar entidades previamente normalizadas por STAGING en estructuras operativas listas para ser consumidas por BUSINESS RULES y REPORTES.

CORE_OPERACION no realiza ETL.

CORE_OPERACION asume que STAGING entrega datos consistentes.

---

# Posición Arquitectónica

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

# Responsabilidad Principal

Determinar:

- quién figura como titular de una venta
- quién ejecutó realmente esa venta
- qué reemplazos deben aplicarse
- cómo clasificar temporalmente cada transacción
- qué calendario operativo corresponde

---

# Entradas Oficiales

## obtener_staging_vta()

Entrega:

- FechaCarga_dt
- FechaEntrega_dt
- CodVendedor
- Cliente
- CantBase
- ImporteNetoItem

---

## obtener_staging_rutas()

Entrega:

calendario de visitas.

---

## obtener_staging_ausencias()

Implementado en FASE 4.7.

Entrega:

- Fecha_dt
- CodVend_clean
- Reemplazo_clean

---

## obtener_staging_maestros()

Entrega:

- maestro_vendedores
- maestro_ccc
- maestro_segmentos
- maestro_marcas_cebe

---

# Flujo Oficial

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

# Procesar Ausencias y Reemplazos

Función:

procesar_ausencias_y_reemplazos()

Responsabilidad:

Determinar:

CodVendedorOperativo

---

# Claves Generadas

## ClaveAUS_Carga

Formato:

CodVendedor + FechaCarga

---

## ClaveAUS_Entrega

Formato:

CodVendedor + FechaEntrega

---

## ClaveAUS

Formato:

CodVend_clean + Fecha_dt

---

# Lógica de Reemplazo

## Sin reemplazo

Condición:

No existe coincidencia en AUSENCIAS.

Resultado:

CodVendedorOperativo = CodVendedor

---

## Con reemplazo

Condición:

Existe coincidencia por clave.

Resultado:

CodVendedorOperativo = Reemplazo

---

# Salidas Operativas

Columnas generadas:

- Reemplazo
- CodVendedorOperativo

Columnas utilizadas:

- FechaCarga_dt
- FechaEntrega_dt
- CodVendedor

---

# Clasificación Temporal

Función:

calcular_ritmo_operativo()

Clasificaciones:

- Arrastre
- Actual
- Futuro
- Fuera de Periodo

---

# Calendario Operativo

Función:

calcular_calendario_y_rutas()

Produce:

- dias_pasados_map
- dias_restantes_map
- total_dias_pasados
- total_dias_restantes

---

# Contrato de Salida

obtener_core_operacion()

retorna:

- df_vta_operativa
- dias_pasados_map
- dias_restantes_map
- total_dias_pasados
- total_dias_restantes

---

# Estado Actual

FASE 4.7

Completada.

Validada en producción.

---

# Pendiente

FASE 4.8

Eliminar ETL redundante heredado dentro de:

procesar_ausencias_y_reemplazos()

Actualmente aún existen componentes técnicos duplicados que ya fueron migrados a:

obtener_staging_ausencias()

La eliminación deberá realizarse únicamente luego de validaciones de producción.