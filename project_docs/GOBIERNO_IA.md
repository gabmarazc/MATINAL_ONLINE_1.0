# GOBIERNO_IA

Versión: 3.0  
Fecha de actualización: 30/09/2026  
Estado: Vigente  
Naturaleza: Norma Institucional Obligatoria

---

# 1. PROPÓSITO

Este documento constituye la guía de gobierno obligatoria para cualquier IA, LLM, asistente, agente, auditor técnico o desarrollador que participe en el análisis, mantenimiento, documentación o evolución del proyecto MATINAL.

Su objetivo es:

- Preservar la metodología de trabajo.
- Garantizar consistencia técnica.
- Evitar pérdida de contexto.
- Reducir riesgos de cambios incorrectos.
- Asegurar continuidad entre sesiones.

---

# 2. PRINCIPIO FUNDAMENTAL

La secuencia obligatoria es:

EVIDENCIA
↓
VALIDACIÓN
↓
DECISIÓN
↓
CAMBIO
↓
REVALIDACIÓN

Está explícitamente prohibido trabajar mediante:

HIPÓTESIS
↓
CAMBIO
↓
PRUEBA

---

# 3. REGLA DE ORO

Si no existe evidencia:

NO AFIRMAR.

Si no existe documentación:

SOLICITAR ÚNICAMENTE LA NECESARIA.

Si no existe validación:

NO CONSIDERAR RESUELTO EL PROBLEMA.

---

# 4. POLÍTICA DE EVIDENCIA

Toda afirmación técnica debe estar sustentada por al menos una de las siguientes fuentes:

- Código fuente
- Base SQLite
- Logs
- Outputs observables
- Resultados de ejecución
- Documentación institucional
- Evidencia reproducible

---

# 5. POLÍTICA DE AUDITORÍA

## Formato Obligatorio

Toda auditoría debe distinguir explícitamente:

### HECHOS CONFIRMADOS

Información demostrada.

### HIPÓTESIS

Información pendiente de validación.

### PRÓXIMOS PASOS

Acciones necesarias para confirmar o descartar hipótesis.

---

## Regla

Nunca mezclar:

hechos

con

hipótesis.

---

# 6. POLÍTICA DE INVESTIGACIÓN

Ante cualquier problema:

Identificar:

1. Dónde nace.
2. Dónde se transforma.
3. Dónde se persiste.
4. Dónde se consume.
5. Dónde deja de coincidir.

Objetivo:

Detectar el primer punto de divergencia.

No el síntoma final.

---

# 7. POLÍTICA DE MODIFICACIÓN DE CÓDIGO

## Secuencia Obligatoria

1. Auditoría.
2. Evidencia.
3. Causa raíz.
4. Diseño.
5. Revisión.
6. Implementación.
7. Validación.
8. Revalidación.

---

## Prohibido

- Refactorizar sin requerimiento.
- Reordenar componentes innecesariamente.
- Renombrar estructuras sin necesidad.
- Optimizar sin objetivo concreto.
- Rediseñar arquitectura sin evidencia.

---

## Principio

Toda modificación debe ser:

- Mínima
- Localizada
- Auditada
- Reversible
- Explicable

---

# 8. POLÍTICA DE ENTREGA DE CÓDIGO

Cuando se solicite modificar código:

Entregar:

✅ Archivo completo

No entregar:

❌ Diffs

❌ Fragmentos

❌ Parches

❌ Secciones aisladas

---

## Regla Institucional

Si un archivo cambia:

Se devuelve completo.

Aunque cambie una sola línea.

---

# 9. POLÍTICA DE DOCUMENTACIÓN

Cuando se modifique documentación:

Entregar:

✅ Documento completo

No entregar:

❌ Inserciones parciales

❌ Agregar después de

❌ Reemplazar párrafo

❌ Modificaciones fragmentadas

---

## Secuencia Documental

1. Auditoría.
2. Reconstrucción completa.
3. Reemplazo total.

---

# 10. POLÍTICA DE DOCUMENTACIÓN DEL PROYECTO

## Documentos Rectores

Constituyen la fuente principal de verdad:

- ESTADO_ACTUAL.md
- ARQUITECTURA.md
- DECISIONES_TECNICAS.md
- ROADMAP.md

---

## Documentos Funcionales

- DICCIONARIO_TABLAS.md
- GLOSARIO_REGLAS.md
- CORE_OPERACION_V1.md
- CORE_VENTAS_BASE_V1.md

---

## Documentos Históricos

- BITACORA.md

---

## Documentos de Contexto

- CONTEXTO_IA.md
- GOBIERNO_IA.md

---

# 11. ORDEN DE CONSULTA

Ante cualquier duda técnica:

1. ESTADO_ACTUAL.md
2. ARQUITECTURA.md
3. ROADMAP.md
4. DECISIONES_TECNICAS.md
5. DICCIONARIO_TABLAS.md
6. GLOSARIO_REGLAS.md
7. CORE_OPERACION_V1.md
8. CORE_VENTAS_BASE_V1.md
9. BITACORA.md

Recién después analizar código.

---

# 12. POLÍTICA DE DATOS

Toda validación deberá intentar medir:

- COUNT registros
- COUNT identificadores
- SUM magnitudes relevantes

antes y después de una transformación.

---

## Principio

La conservación de masa constituye un criterio obligatorio de auditoría.

---

# 13. POLÍTICA DE CACHE

Nunca asumir:

SQLite = lo que ve el usuario.

Siempre considerar:

- Cache Data
- Cache Resource
- Session State
- Objetos persistidos en memoria
- Reruns

---

## Caso Histórico

Cliente 90409

Resultado:

La información correcta existía en SQLite.

La interfaz utilizaba estado cacheado.

Conclusión:

SQLite correcta no implica interfaz correcta.

---

# 14. POLÍTICA DE RERUNS

Ante inconsistencias:

Verificar:

- st.rerun()
- st.experimental_rerun()
- st.cache_data.clear()
- st.cache_resource.clear()
- session_state

No asumir sincronización automática.

---

# 15. POLÍTICA DE MIGRACIÓN ARQUITECTÓNICA

Toda nueva migración debe respetar:

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

# 16. POLÍTICA DE DESACOPLAMIENTO

## Permitido

Reporte
↓
Business Rules
↓
Core

Business Rules
↓
Core

Core
↓
Staging

---

## Prohibido

Reporte
↓
Reporte

Business Rules
↓
Reporte

Reporte
↓
SQLite

Reporte
↓
Excel

Business Rules
↓
SQLite

Business Rules
↓
Excel

---

# 17. BUSINESS RULES

## Estado Institucional

BUSINESS RULES se considera:

✅ Implementada

✅ Validada

✅ Productiva

---

## Implementaciones Confirmadas

### Kilos

rep_kilos_core.py
↓
business_rules_kilos.py
↓
core_*

Resultado:

✅ Productivo

✅ Validado

---

### MiNegocio

rep_MN_core.py
↓
business_rules_mn.py
↓
core_*

Resultado:

✅ Productivo

✅ Validado

---

## Consecuencia

BUSINESS RULES deja de considerarse experimental.

A partir de esta fecha constituye la estrategia oficial de evolución del proyecto.

---

# 18. POLÍTICA DE MIGRACIONES FUTURAS

## Secuencia Aprobada

✅ Kilos

✅ MiNegocio

⏳ CCC

⏳ Cobertura Marca

⏳ Cobertura Innovación

⏳ Gerencial

⏳ Vespertina

---

## Regla

Antes de migrar un reporte:

1. Auditar.
2. Identificar Core.
3. Identificar Business Rules.
4. Diseñar matriz objetivo.
5. Implementar Business Rules.
6. Implementar reporte desacoplado.
7. Validar.
8. Recién entonces retirar el histórico.

---

# 19. DEPENDENCIAS PENDIENTES

## Dependencias Detectadas

Gerencial
↓
CCC

Gerencial
↓
Cobertura Marca

Vespertina
↓
CCC

---

## Próxima Dependencia a Eliminar

CCC

Arquitectura objetivo:

rep_ccc_core.py
↓
business_rules_ccc.py
↓
core_*

---

# 20. METODOLOGÍA OFICIAL MATINAL

La metodología institucional aprobada es:

AUDITORÍA
↓
EVIDENCIA
↓
VALIDACIÓN
↓
IMPLEMENTACIÓN
↓
REVALIDACIÓN

Toda IA que participe en MATINAL debe respetar este principio.

Su incumplimiento se considera una desviación metodológica.