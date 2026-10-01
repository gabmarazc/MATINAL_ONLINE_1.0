# CONTEXTO_IA

Versión: 3.0
Fecha de actualización: 30/09/2026
Estado: Vigente
Naturaleza: Documento de Onboarding Institucional para IA

---

# 1. PROPÓSITO

Este documento existe para permitir que una nueva instancia de IA, un nuevo chat o un nuevo desarrollador pueda incorporarse al proyecto MATINAL sin pérdida de contexto funcional, técnico o metodológico.

No constituye una copia de la documentación.

Constituye una guía de orientación para entender:

- qué es MATINAL
- cómo funciona
- cómo está construido
- qué decisiones ya fueron tomadas
- qué decisiones no deben volver a discutirse
- cuál es el siguiente objetivo institucional

---

# 2. ¿QUÉ ES MATINAL?

MATINAL es un sistema institucional de análisis, monitoreo y gestión comercial utilizado para la operación diaria de preventa.

El sistema se encuentra en producción operativa.

Es utilizado por:

- administración
- supervisión
- gerencia

El sistema procesa:

- ventas
- clientes
- cartera
- objetivos
- cobertura
- adopción digital
- indicadores gerenciales
- seguimiento comercial

---

# 3. ESTADO ACTUAL DEL PROYECTO

Estado General:

✅ Producción Operativa

Nivel de Riesgo:

✅ Bajo

Estado Arquitectónico:

✅ Validado

Estado Documental:

✅ Normalizado

Estado de Business Rules:

✅ Validada

---

# 4. ARQUITECTURA OFICIAL

La arquitectura institucional vigente es:

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

Esta arquitectura se considera:

✅ Validada

✅ Productiva

✅ Consolidada

No constituye una propuesta futura.

Constituye el modelo oficial actual del proyecto.

---

# 5. SIGNIFICADO DE CADA CAPA

## RAW

Recepción de datos externos.

Ejemplos:

- VTA.xlsx
- UNIVERSO.xlsx
- RUTAS.xlsx
- ALTAS.xlsx

---

## SQLITE

Fuente física única de datos.

Ubicación:

data/matinal.db

Responsabilidad:

Persistencia institucional.

---

## STAGING

Responsabilidad:

Normalización técnica.

Incluye:

- tipado
- parseo de fechas
- normalización
- contratos de datos

No contiene:

- objetivos
- CCC
- MiNegocio
- coberturas
- reglas comerciales

---

## CORE

Responsabilidad:

Interpretación operativa.

Incluye:

- reemplazos
- ausencias
- calendario
- titularidad operativa
- clasificación temporal

No contiene:

- decisiones comerciales
- KPIs
- objetivos
- compensaciones

---

## BUSINESS RULES

Responsabilidad:

Aplicar reglas comerciales.

Incluye:

- CCC
- MiNegocio
- Coberturas
- Objetivos

---

## REPORTES

Responsabilidad:

Visualización.

Incluye:

- dashboards
- KPIs
- proyecciones
- exportaciones

---

# 6. DECISIONES ARQUITECTÓNICAS CERRADAS

Las siguientes discusiones se consideran cerradas.

No deben reabrirse salvo evidencia nueva.

## DA-001

La arquitectura por capas es definitiva.

---

## DA-002

SQLite es la fuente física única de datos.

---

## DA-003

STAGING es responsable exclusivo del ETL.

---

## DA-004

CORE es responsable exclusivo de la interpretación operativa.

---

## DA-005

BUSINESS RULES es responsable exclusivo de las decisiones comerciales.

---

## DA-006

Los reportes no deben depender entre sí.

---

## DA-007

La arquitectura correcta es:

Reporte
↓
Business Rules
↓
Core

Y no:

Reporte
↓
Reporte

---

# 7. ESTADO DE BUSINESS RULES

La capa BUSINESS RULES se encuentra validada.

Implementaciones productivas confirmadas:

## Kilos

✅ Productivo

✅ Validado

---

## MiNegocio

✅ Productivo

✅ Validado

---

Resultado institucional:

BUSINESS RULES ya no se considera experimental.

Constituye la estrategia oficial de evolución del sistema.

---

# 8. MIGRACIONES COMPLETADAS

## Kilos

Estado:

✅ Completado

---

## MiNegocio

Estado:

✅ Completado

---

# 9. MIGRACIONES PENDIENTES

Orden aprobado:

1. CCC
2. Cobertura Marca
3. Cobertura Innovación
4. Gerencial
5. Vespertina

---

# 10. SIGUIENTE OBJETIVO INSTITUCIONAL

## CCC

Es la próxima migración aprobada.

Arquitectura objetivo:

rep_ccc_core.py
↓
business_rules_ccc.py
↓
core_*

Objetivos:

- desacoplar lógica comercial
- reutilizar CORE
- consolidar fuente única CCC
- eliminar dependencias futuras

---

# 11. DEPENDENCIAS PENDIENTES

Actualmente existen dependencias históricas que deberán eliminarse.

## Gerencial

Depende parcialmente de:

- CCC
- Cobertura Marca

---

## Vespertina

Depende parcialmente de:

- CCC

---

Objetivo institucional:

Eliminar toda dependencia:

Reporte
↓
Reporte

---

# 12. REGLAS FUNCIONALES CRÍTICAS

Toda IA debe asumir como prioritarias las reglas documentadas en:

MANUAL_FUNCIONAL.md

Especialmente:

- Problema de Cierre
- Filtro Empleados
- Filtro PepsiCo
- Exclusión Vendedor 20
- Titularidad Operativa
- Clasificación Temporal

Ninguna optimización técnica puede contradecir estas reglas.

---

# 13. DOCUMENTOS OFICIALES DEL PROYECTO

## Gobierno

GOBIERNO_IA.md

---

## Estado

ESTADO_ACTUAL.md

---

## Arquitectura

ARQUITECTURA.md

---

## Decisiones

DECISIONES_TECNICAS.md

---

## Funcional

MANUAL_FUNCIONAL.md

---

## Datos

DICCIONARIO_TABLAS.md

---

## Core

CORE_OPERACION_V1.md

CORE_VENTAS_BASE_V1.md

---

## Historial

BITACORA.md

---

# 14. ORDEN DE LECTURA PARA UNA NUEVA IA

1. GOBIERNO_IA.md
2. CONTEXTO_IA.md
3. ESTADO_ACTUAL.md
4. ARQUITECTURA.md
5. DECISIONES_TECNICAS.md
6. MANUAL_FUNCIONAL.md
7. DICCIONARIO_TABLAS.md
8. CORE_OPERACION_V1.md
9. CORE_VENTAS_BASE_V1.md
10. BITACORA.md

---

# 15. METODOLOGÍA OBLIGATORIA

Toda IA debe trabajar siguiendo:

AUDITORÍA
↓
EVIDENCIA
↓
VALIDACIÓN
↓
DISEÑO
↓
IMPLEMENTACIÓN
↓
REVALIDACIÓN

Nunca:

HIPÓTESIS
↓
CAMBIO
↓
PRUEBA

---

# 16. REGLAS ESPECÍFICAS DEL USUARIO

El proyecto adopta las siguientes preferencias obligatorias:

## Código

Devolver siempre:

✅ Script completo

Nunca:

❌ Diff

❌ Fragmento

❌ Parches parciales

---

## Documentación

Devolver siempre:

✅ Documento completo

Nunca:

❌ Modificaciones parciales

❌ Agregados aislados

❌ Instrucciones de reemplazo por sección

---

## Auditoría

Separar siempre:

HECHOS CONFIRMADOS

HIPÓTESIS

PRÓXIMOS PASOS

---

## Cambios Productivos

No reemplazar código productivo sin auditoría previa.

---

# 17. ESTADO DE ONBOARDING

Si una nueva IA está leyendo este documento debe asumir que:

✅ La documentación fue normalizada.

✅ La arquitectura fue validada.

✅ Kilos fue migrado.

✅ MiNegocio fue migrado.

✅ Business Rules fue validada.

✅ CCC es el siguiente objetivo institucional.

✅ No deben proponerse arquitecturas alternativas sin evidencia objetiva.

Con esta información la IA dispone del contexto mínimo necesario para continuar el desarrollo del proyecto sin perder continuidad técnica, funcional ni documental.