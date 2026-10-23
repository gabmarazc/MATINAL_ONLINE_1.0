# MATINAL ONLINE | Arquitectura objetivo y arquitectura real

## 1. Arquitectura institucional objetivo

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
↓
STREAMLIT
```

Principio rector:

```text
CORE interpreta.
BUSINESS RULES decide.
REPORTES muestran.
```

## 2. Responsabilidades por capa

### RAW

Recibe archivos y fuentes externas. No define decisiones comerciales.

### SQLITE

Persiste datos, mantiene índices, historización y acceso físico institucional.

### STAGING

Realiza ETL técnico: tipado, parseo, normalización, limpieza y contratos de entrada. No debe contener objetivos, coberturas, KPIs ni compensaciones.

### CORE

Interpreta la operación y construye datasets reutilizables. Incluye calendario, clasificación temporal, titularidad, ausencias y reemplazos. No debe decidir objetivos o criterios comerciales.

### BUSINESS RULES

Aplica elegibilidad, objetivos, compensaciones, cobertura, atribuciones, proyecciones y métricas comerciales.

### REPORTES

Presentan resultados mediante filtros visuales, tablas, tarjetas y exportaciones. No deben constituir una fuente paralela de reglas.

### STREAMLIT

Gestiona interfaz, sesión, navegación, controles y reruns.

## 3. Patrones objetivo

Permitido:

```text
Reporte → Business Rules → Core → Staging → SQLite
Business Rules → Core
Core → Staging
Staging → SQLite
```

No permitido para desarrollos nuevos:

```text
Reporte → Reporte
Reporte → SQLite
Reporte → Excel
Business Rules → Reporte
Business Rules → archivo físico
CORE → Business Rules
```

## 4. Arquitectura real observada

El código actual contiene excepciones que deben documentarse, no negarse ni ampliarse automáticamente.

### Gerencial

- `rep_gerencial_core.py` consume `business_rules_gerencial.py`.
- También importa funciones de `rep_ccc_core.py` y `rep_MN_core.py`.
- Consulta maestros en SQLite.
- El motor gerencial utiliza matrices propias de Kilos y Gross, con venta titular, vendedor 20 incluido y compensaciones en cero.

### Cobertura

- `rep_cobertura_core.py` consulta SQLite.
- Construye catálogos, agregados, pivotes y matrices.
- `core_cobertura.py` consume reglas de `business_rules_cobertura.py`.
- Cobertura es el dominio más híbrido observado.

### CCC

- `business_rules_ccc.py` accede a SQLite.
- Mantiene un fallback a `ALTAS.xlsx`.
- `rep_ccc_core.py` consulta datos para resolver el Día Matinal.

### Tienda Perfecta

- `core_tp.py` accede a SQLite.
- `rep_tp_core.py` recalcula KPIs y rankings tras aplicar filtros visuales.

### Objetivos

- Business Rules consulta Universo para elegibilidad.
- `core_potencial_cliente_segmento.py` importa una función privada de `business_rules_kilos.py`.

## 5. Política ante excepciones

- No calificar automáticamente una excepción como error.
- Identificar primero la finalidad funcional y los consumidores.
- No extender el patrón híbrido a nuevos módulos.
- Refactorizar solo con alcance, evidencia, equivalencia funcional y validación.
