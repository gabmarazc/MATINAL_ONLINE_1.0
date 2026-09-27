## INC-2026-09-24-001

### Título
Eliminación de referencia obsoleta a tabla `parametros_marcas`

### Fecha
24/09/2026

### Descubrimiento

Durante la validación operativa de la Fase 2A (Logging Estructurado), el archivo de log detectó múltiples advertencias:

```text
WARNING | matinal.database |
La tabla consultada no existe en el catálogo de SQLite.
SELECT * FROM parametros_marcas
# INC-2026-09-24-001

## Título

Eliminación de referencia obsoleta a la tabla `parametros_marcas`

## Fecha de Apertura

24/09/2026

## Fecha de Cierre

24/09/2026

## Origen

Durante la validación operativa de la Fase 2A (Logging Estructurado) se detectaron advertencias recurrentes en:

```text
logs/matinal.log
## Validación Final de Estabilidad

Posteriormente a la corrección se realizaron las siguientes pruebas adicionales:

### Prueba 1 - Reinicio Completo

- Cierre total de la aplicación.
- Reinicio de Streamlit.
- Recarga completa de módulos.
- Verificación de acceso a todos los reportes principales.

Resultado:

```text
✅ Aplicación operativa.
✅ Sin errores observados.
✅ Sin referencias nuevas a parametros_marcas.
## INC-2026-09-25-001

### Título
Unificación de padrón de vendedores y supervisor en Tienda Perfecta

### Fecha
25/09/2026

### Cambio
Se integró `modules/rep_tp.py` con `maestro_vendedores`, adoptando el mismo criterio de identificación de preventistas utilizado en `rep_ccc.py`.

### Implementación
- Incorporación de cruce por código de vendedor.
- Visualización de nombres corporativos en lugar de códigos.
- Incorporación de Supervisor desde `maestro_vendedores`.
- Compatibilidad con `filtros_globales["supervisor"]`.
- Regeneración dinámica de catálogos por supervisor.
- Conservación de las claves históricas de `st.session_state` para evitar regresiones.

### Validación
- Supervisor específico → OK.
- Retorno a TODOS → OK.
- Catálogo de vendedores regenerado correctamente.
- Rankings, oportunidades y exportaciones operativos.

### Resultado
✅ TP alineado arquitectónicamente con CCC.

### Impacto
Sin degradación observable de performance.
# INC-2026-09-26-001

## Título
Auditoría forense de paridad en STAGING_CLIENTES

## Fecha de Apertura
26/09/2026

## Estado
Cerrado

## Contexto

Durante la Fase 4.1 se detectó una diferencia entre:

RAW_UNIVERSO = 5719 registros

y

STAGING_CLIENTES = 5615 registros

## Investigación Realizada

Se auditó:

- UNIVERSO.xlsx
- SQLite (tabla universo)
- modules/database.py
- modules/staging.py
- modules/data_loader.py
- cache de Streamlit
- tipado de identificadores
- duplicados
- valores nulos

## Hallazgos

Se comprobó que:

- La diferencia es exactamente de 104 registros.
- Los 104 registros corresponden al SubSegmento = Empleados.
- La tabla universo en SQLite contiene 5719 registros.
- db.cargar_tabla_sql("SELECT * FROM universo") devuelve 5719 registros.
- STAGING_CLIENTES devuelve 5615 registros.
- No se detectaron pérdidas por tipado, duplicados o valores nulos.

## Impacto

Nulo sobre la continuidad del proyecto.

Los registros faltantes están completamente identificados y cuantificados.

## Decisión Arquitectónica

Se confirma la arquitectura:

RAW
→ STAGING
→ CORE
→ REPORTES

Las reglas de exclusión de empleados pertenecen a CORE.

## Resolución

Se da por concluida la Fase 4.1.

La incidencia queda documentada como STG-001 y no bloquea el inicio de CORE.

## Resultado

✅ FASE 4.1 cerrada

✅ Inicio autorizado de la Capa CORE