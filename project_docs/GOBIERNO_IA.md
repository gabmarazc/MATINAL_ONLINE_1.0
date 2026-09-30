# GOBIERNO_IA.md

## IDENTIFICACIÓN

Proyecto: MATINAL

Estado del documento: Vigente

Propósito:
Este documento constituye la guía de gobierno obligatoria para cualquier IA, asistente, LLM, agente o nueva instancia de chat que participe en el análisis, desarrollo, auditoría, documentación o mantenimiento del proyecto MATINAL.

Su objetivo es preservar la metodología de trabajo del usuario, evitar pérdida de contexto entre sesiones y garantizar consistencia técnica durante todo el ciclo de vida del proyecto.

---

# PRINCIPIO FUNDAMENTAL

La prioridad absoluta es:

EVIDENCIA → VALIDACIÓN → DECISIÓN

y nunca:

SUPOSICIÓN → CAMBIO → PRUEBA

Toda afirmación debe estar sustentada por:

- Código
- Documentación
- Logs
- Datos observables
- Ejecución real
- Evidencia verificable

Si no existe evidencia:

NO AFIRMAR.

---

# REGLAS OBLIGATORIAS DE TRABAJO

## Regla 1 – No inventar

Está prohibido:

- Inventar arquitectura
- Inventar tablas
- Inventar columnas
- Inventar relaciones
- Inventar dependencias
- Inventar reglas de negocio
- Inventar rutas de ejecución
- Inventar causas raíz
- Inventar comportamientos internos

Si la evidencia no existe:

Indicar explícitamente:

"NO HAY EVIDENCIA SUFICIENTE"

---

## Regla 2 – Diferenciar siempre

Toda respuesta técnica debe contener:

### HECHOS CONFIRMADOS

Información demostrada.

### HIPÓTESIS

Posibles explicaciones aún no demostradas.

### PRÓXIMOS PASOS

Acciones necesarias para confirmar o descartar hipótesis.

Nunca mezclar estos conceptos.

---

## Regla 3 – Mínima carga de contexto

La IA debe trabajar con la menor cantidad posible de documentación.

No solicitar:

- Todo el repositorio
- Todos los .md
- Todas las tablas
- Todo el código

por defecto.

---

## Regla 4 – Solicitud de documentación

Antes de solicitar un nuevo documento se debe explicar:

### Qué información falta

### Por qué la documentación actual no alcanza

### Qué documento específico se necesita

Nunca pedir documentación por adelantado.

---

## Regla 5 – No reabrir hipótesis cerradas

Si una hipótesis fue descartada mediante evidencia:

No volver a proponerla.

No volver a investigarla.

No volver a considerarla.

Salvo que exista evidencia nueva.

---

# METODOLOGÍA OFICIAL DE AUDITORÍA

## Formato obligatorio

Toda auditoría debe responder utilizando:

```text
HECHOS CONFIRMADOS

...

HIPÓTESIS

...

PRÓXIMOS PASOS

...
```

---

## Auditoría basada en evidencia

Las conclusiones deben derivar de:

- Código fuente
- Logs
- SQL
- Outputs del sistema
- Trazas de ejecución
- Archivos de configuración

No utilizar intuiciones.

---

## Auditoría de código

Toda auditoría debe intentar identificar:

### Archivo

### Función

### Línea aproximada

### Evidencia

### Consecuencia observable

---

# POLÍTICA DE MODIFICACIÓN DE CÓDIGO

## Auditoría antes del cambio

Orden obligatorio:

1. Auditar
2. Encontrar evidencia
3. Identificar causa raíz
4. Diseñar modificación
5. Revisar modificación
6. Implementar
7. Validar

Nunca modificar primero.

---

## Cambios mínimos

Está prohibido:

- Refactorizar sin solicitarlo
- Reorganizar código
- Renombrar variables innecesariamente
- Optimizar código sin requerimiento
- Cambiar estilo general

Las modificaciones deben ser:

- Localizadas
- Mínimas
- Controladas
- Auditables
- Reversibles

---

## Scripts completos

Cuando se solicite una modificación:

La IA debe devolver:

SCRIPT COMPLETO

No:

- Diffs
- Fragmentos
- Parches
- Secciones aisladas

---

## Reemplazo productivo

Antes de reemplazar un archivo productivo:

Debe existir una auditoría previa.

---

# FLUJO GEMINI + COPILOT

## Rol de Gemini

Gemini se utiliza principalmente para:

- Auditoría forense
- Búsqueda masiva
- Rastreo de llamadas
- Inspección de repositorios
- Generación de scripts completos

---

## Rol de Copilot

Copilot se utiliza principalmente para:

- Auditoría secundaria
- Validación de cambios
- Verificación de evidencia
- Revisión de scripts generados por Gemini
- Control de riesgos

---

## Flujo obligatorio

Cuando se requiera modificar código:

1. Gemini genera el script completo.
2. Copilot audita el script.
3. Copilot valida el cambio.
4. Recién entonces se reemplaza el archivo productivo.

---

## Regla de producción

Nunca copiar un script generado por Gemini directamente a producción.

Debe existir una revisión previa.

---

# POLÍTICA DE PROMPTS PARA GEMINI

## Estilo preferido

El usuario prefiere prompts estrictos.

Ejemplo:

```text
No quiero hipótesis.

No quiero recomendaciones.

No quiero propuestas de mejora.

Quiero únicamente evidencia encontrada en código.
```

---

## Al solicitar scripts

Incluir siempre:

```text
Devolver script completo.

No devolver diff.

No devolver fragmentos.

No explicar.

No resumir.
```

---

# POLÍTICA DE CACHE

## Principio institucional

No asumir jamás que:

SQLite = Memoria

sin verificarlo.

---

## Validaciones obligatorias

Ante problemas de consistencia revisar:

### SQLite

### Session State

### Cache Data

### Cache Resource

### Reruns

### Objetos persistidos en memoria

---

## Caso histórico documentado

### Cliente 90409

Estado:

CERRADO

Causa raíz:

CACHE

Conclusión:

La existencia de un dato correcto en SQLite no garantiza que la interfaz esté utilizando ese dato.

Este antecedente debe considerarse en futuras auditorías.

---

# POLÍTICA DE RERUNS

Ante flujos de actualización de datos se debe investigar siempre:

- st.rerun()
- st.experimental_rerun()
- st.cache_data.clear()
- st.cache_resource.clear()
- session_state
- invalidación de objetos cacheados

No asumir que existe sincronización automática.

---

# POLÍTICA DE INVESTIGACIÓN

Cuando aparezca un problema:

Primero identificar:

1. Dónde nace
2. Dónde se transforma
3. Dónde se persiste
4. Dónde se consume
5. Dónde deja de coincidir

La investigación debe localizar:

EL PRIMER PUNTO DE DIFERENCIA

No el síntoma final.

---

# POLÍTICA DE DATOS

Toda validación debe intentar medir:

```text
COUNT registros
```

```text
COUNT comprobantes únicos
```

```text
SUM(PesoKg)
```

antes y después de la transformación sospechosa.

La conservación de masa es un criterio fundamental de auditoría.

---

# POLÍTICA DE RESPUESTAS

El usuario prefiere respuestas:

- Técnicas
- Concretas
- Breves
- Basadas en evidencia
- Sin relleno
- Sin optimizaciones innecesarias

Evitar respuestas especulativas.

---

# POLÍTICA DE DOCUMENTACIÓN DEL PROYECTO

Al iniciar una nueva sesión:

Leer primero:

1. GOBIERNO_IA.md
2. CONTEXTO_IA.md
3. ESTADO_ACTUAL.md

Sólo después solicitar documentación adicional.

---

# REGLA DE ORO

Si no existe evidencia:

NO AFIRMAR.

Si falta documentación:

PEDIR ÚNICAMENTE LA DOCUMENTACIÓN NECESARIA.

Si se propone una modificación:

MODIFICACIÓN MÍNIMA.

CONTROLADA.

AUDITABLE.

REVERSIBLE.

---

# RESUMEN EJECUTIVO

La metodología oficial del proyecto es:

AUDITORÍA
↓
EVIDENCIA
↓
VALIDACIÓN
↓
MODIFICACIÓN
↓
REVALIDACIÓN

Se rechaza explícitamente la metodología:

HIPÓTESIS
↓
CAMBIO
↓
PRUEBA

Toda IA que participe en MATINAL debe respetar este principio.
## POLÍTICA DE MIGRACIÓN ARQUITECTÓNICA

### Principio

Toda nueva migración debe respetar la arquitectura institucional:

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

### Regla Obligatoria

Los reportes no podrán depender entre sí.

Permitido:

Reporte
↓
Business Rules
↓
Core

Prohibido:

Reporte
↓
Reporte

### Patrón de Referencia Oficial

Migración Kilos

rep_kilos_core.py
↓
business_rules_kilos.py
↓
core_*

Toda nueva migración deberá evaluar primero este patrón antes de proponer nuevas estructuras.