# BITACORA - MATINAL

Estado General del Proyecto: Producción Operativa  
Arquitectura Oficial:

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

Estado Arquitectónico:

```text
RAW               ✅
SQLITE            ✅
STAGING           ✅
CORE              ✅
BUSINESS RULES    🟡 Parcial
REPORTES          ✅
```

Fase Actual:

```text
FASE 4.7 COMPLETADA ✅
FASE 4.8 APROBADA ⏳
```

---

# INC-2026-09-24-001

## Título

Eliminación de referencia obsoleta a la tabla `parametros_marcas`

## Fecha de Apertura

24/09/2026

## Fecha de Cierre

24/09/2026

## Origen

Durante la validación operativa de la Fase 2A (Logging Estructurado) se detectaron advertencias recurrentes en los registros del sistema relacionadas con consultas a una tabla inexistente.

## Evidencia

```text
WARNING | matinal.database |
La tabla consultada no existe en el catálogo de SQLite.

SELECT * FROM parametros_marcas
```

## Acción Realizada

Se eliminaron las referencias remanentes a:

```text
parametros_marcas
```

## Validación Final

### Prueba 1 - Reinicio Completo

- Cierre total de la aplicación.
- Reinicio de Streamlit.
- Recarga completa de módulos.
- Verificación de reportes principales.

### Resultado

```text
✅ Aplicación operativa
✅ Sin errores observados
✅ Sin referencias nuevas a parametros_marcas
```

## Estado

```text
CERRADO
```

---

# INC-2026-09-25-001

## Título

Unificación de padrón de vendedores y supervisor en Tienda Perfecta

## Fecha de Apertura

25/09/2026

## Fecha de Cierre

25/09/2026

## Cambio

Se integró:

```text
modules/rep_tp.py
```

con:

```text
maestro_vendedores
```

adoptando el mismo criterio institucional utilizado por CCC.

## Implementación

- Cruce por código de vendedor.
- Visualización de nombres corporativos.
- Incorporación de Supervisor.
- Compatibilidad con filtros globales.
- Regeneración dinámica de catálogos.
- Conservación de compatibilidad histórica.

## Validación

```text
✅ Supervisor específico
✅ Retorno a TODOS
✅ Catálogos regenerados
✅ Rankings operativos
✅ Exportaciones operativas
```

## Resultado

```text
✅ TP alineado arquitectónicamente con CCC
✅ Sin degradación observable de performance
```

## Estado

```text
CERRADO
```

---

# INC-2026-09-26-001

## Título

Auditoría forense de paridad en STAGING_CLIENTES

## Fecha de Apertura

26/09/2026

## Fecha de Cierre

26/09/2026

## Contexto

Durante la validación de la arquitectura por capas se detectó una diferencia entre:

```text
RAW_UNIVERSO = 5719 registros
STAGING_CLIENTES = 5615 registros
```

## Investigación Realizada

Se auditó:

- UNIVERSO.xlsx
- SQLite
- database.py
- staging.py
- data_loader.py
- cache de Streamlit
- tipado
- duplicados
- valores nulos

## Hallazgos

```text
Diferencia total: 104 registros
```

Los registros faltantes corresponden exactamente a:

```text
SubSegmento = Empleados
```

Además:

```text
✅ SQLite contiene 5719 registros
✅ No existen pérdidas por tipado
✅ No existen pérdidas por duplicados
✅ No existen pérdidas por valores nulos
```

## Impacto

```text
Nulo
```

## Decisión Arquitectónica

Se ratifica el modelo:

```text
RAW
↓
STAGING
↓
CORE
↓
REPORTES
```

## Resultado

```text
✅ FASE 4.1 cerrada
✅ Inicio autorizado de CORE
```

## Estado

```text
CERRADO
```

---

# INC-2026-09-27-001

## Título

Migración de AUSENCIAS a STAGING

## Fecha de Apertura

27/09/2026

## Fecha de Cierre

27/09/2026

## Contexto

La entidad AUSENCIAS era consumida mediante:

```python
maestros["ausencias"]
```

y gran parte del procesamiento técnico permanecía mezclado con lógica operativa.

La arquitectura institucional exigía separar:

```text
ETL
↓
Operación
```

mediante la incorporación formal de STAGING.

## Objetivo

Crear una puerta de entrada especializada para AUSENCIAS dentro de la capa STAGING.

## Implementación

Se incorporó:

```python
obtener_staging_ausencias()
```

## Responsabilidades Asignadas

```text
Lectura SQLite
Detección de columnas
Parseo robusto de fechas
Tipado
Conversión a Int64
Normalización
Generación de contratos técnicos
```

## Contrato Aprobado

```text
Fecha_dt
CodVend_clean
Reemplazo_clean
```

## Cambio de Orquestación

### Antes

```python
df_ausencias = maestros["ausencias"]
```

### Después

```python
df_ausencias = obtener_staging_ausencias()
```

## Beneficios

```text
Menor acoplamiento
Contratos explícitos
Preparación para futuras entidades STAGING
Separación efectiva entre STAGING y CORE
```

## Estado

```text
CERRADO
```

---

# INC-2026-09-27-002

## Título

Validación productiva de la Migración AUSENCIAS → STAGING

## Fecha de Apertura

27/09/2026

## Fecha de Cierre

27/09/2026

## Objetivo

Verificar comportamiento funcional luego del cambio arquitectónico.

## Validaciones Ejecutadas

```text
✅ Arranque Streamlit
✅ Carga SQLite
✅ Ejecución STAGING
✅ Ejecución CORE
✅ Renderizado de reportes
✅ Integración AUSENCIAS
✅ Sin errores de importación
✅ Sin NameError
✅ Sin KeyError
✅ Sin tracebacks
```

## Evidencia Operativa

```text
obtener_staging_ausencias       → 0.0087 s
procesar_ausencias_y_reemplazos → 0.7176 s
obtener_core_operacion          → 13.4367 s
obtener_matriz_kilos_comercial  → 14.6438 s
```

## Resultado

```text
✅ Integración aprobada
✅ Sin regresiones observadas
✅ Sin degradación perceptible de performance
```

## Estado

```text
CERRADO
```

---

# INC-2026-09-27-003

## Título

Cierre formal de FASE 4.7

## Fecha de Apertura

27/09/2026

## Fecha de Cierre

27/09/2026

## Nombre de Fase

```text
Migración de AUSENCIAS a STAGING
```

## Alcance Completado

### STAGING

Implementado:

```python
obtener_staging_ausencias()
```

### CORE

Consumidor actualizado:

```python
procesar_ausencias_y_reemplazos()
```

### Producción

Validada mediante ejecución real.

## Resultado Institucional

```text
✅ FASE 4.7 COMPLETADA
✅ STAGING implementado
✅ CORE operativo
✅ Arquitectura por capas consolidada
```

## Estado

```text
CERRADO
```

---

# EVENTO-2026-09-27-001

## Título

Aprobación formal de FASE 4.8

## Fecha

27/09/2026

## Estado

APROBADA

## Nombre

```text
Eliminación de ETL duplicado en CORE
```

## Objetivo

Eliminar lógica técnica actualmente duplicada dentro de:

```python
procesar_ausencias_y_reemplazos()
```

una vez validado el funcionamiento de:

```python
obtener_staging_ausencias()
```

## Elementos Identificados

```text
cols_vend_cand
cols_f_cand
cols_reemp_cand
parsear_fecha_robusta()
CodVend_clean
Reemplazo_clean
```

## Resultado Esperado

```text
STAGING = 100% ETL
CORE = 100% Operación
```

## Estado

```text
PENDIENTE
```

---

# RESUMEN INSTITUCIONAL

Estado Productivo:

```text
OPERATIVO
```

Estado Arquitectónico:

```text
EN TRANSICIÓN CONTROLADA HACIA ARQUITECTURA POR CAPAS
```

Última Fase Cerrada:

```text
FASE 4.7
Migración de AUSENCIAS a STAGING
```

Próxima Fase:

```text
FASE 4.8
Eliminación de ETL duplicado en CORE
```

Nivel de Riesgo:

```text
BAJO
```

Resultado General:

```text
✅ Sistema estable
✅ Producción operativa
✅ STAGING implementado
✅ CORE implementado
✅ BUSINESS RULES parcial
✅ Reportes operativos
```
## INC-2026-09-29-001

### Título

Cierre formal de Migración Kilos hacia Business Rules

### Fecha de Apertura

29/09/2026

### Fecha de Cierre

29/09/2026

### Contexto

Se completó la migración del reporte histórico de Kilos hacia la arquitectura institucional por capas.

### Implementación

Se consolidó:

rep_kilos_core.py

consumiendo:

business_rules_kilos.py

y Core institucional.

### Resultado

✅ Migración validada.

✅ Patrón arquitectónico aprobado.

✅ Eliminación de archivos temporales de migración.

✅ Base de referencia para futuras migraciones.

### Estado

CERRADO
