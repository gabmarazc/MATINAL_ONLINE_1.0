# MATINAL ONLINE | Deuda técnica, riesgos y decisiones

## 1. Decisiones vigentes

- Arquitectura por capas como objetivo institucional.
- SQLite como persistencia principal.
- STAGING como propietario del ETL técnico.
- CORE como propietario de la interpretación operativa.
- BUSINESS RULES como propietario de las decisiones comerciales.
- Reemplazos resueltos operativamente en CORE.
- Universo vigente como fuente de elegibilidad para objetivos.
- Preservación de `CodVendedorHistorico` para compensaciones.
- Vendedor 99 como comodín institucional de reemplazo.
- Exclusión de Futuro y Fuera de Periodo en compensaciones.
- Historización de Universo mediante snapshots y hashes.
- Migración incremental y prohibición de refactorización masiva.

## 2. Decisiones actualizadas

### Código vivo frente a documentación

La documentación histórica ya no tiene prioridad automática. Ante discrepancias:

```text
Código vivo + evidencia operativa
→ decisión actual confirmada
→ documentación vigente
→ documentación histórica
```

### Vendedor 20

La exclusión es contextual. Gerencial lo incluye; varios motores comerciales lo excluyen.

### Cobertura

Marca e Innovación están unificadas. El reporte separado de Innovación pasó a Legacy.

### Vespertina

El reporte histórico pasó a Legacy y no debe usarse como diseño del nuevo módulo.

### VTA

La fuente productiva actual prioriza CSV particionados y Parquet consolidado, no un único Excel.

## 3. Deuda técnica observada

### Cobertura

- SQL directo en reporte.
- Cálculos, catálogos y pivotes en UI.
- Dependencia CORE → Business Rules.

### Gerencial

- Dependencias Reporte → Reporte.
- SQL directo.
- Motores propios de Kilos y Gross.

### CCC

- Acceso de Business Rules a SQLite.
- Fallback físico a `ALTAS.xlsx`.

### Tienda Perfecta

- CORE accede a SQLite.
- KPIs recalculados en reporte tras filtros.

### Objetivos

- Importación de función privada desde Business Rules hacia CORE.
- Accesos directos para elegibilidad.

### Normalización

- Persisten parseos y conversiones defensivas fuera de STAGING.

## 4. Riesgos de modificación

- Confundir sufijo `_core` con pureza arquitectónica.
- Unificar motores Gerencial y comercial sin preservar diferencias.
- Eliminar fallbacks sin probar su uso real.
- Cambiar granularidad en joins y multiplicar filas.
- Renombrar columnas contratadas.
- Evitar vendedor 20 donde debe incluirse.
- Perder `CodVendedorHistorico`.
- Distribuir objetivos sobre clientes fuera de Universo.
- Modificar caché sin comprender el ciclo de rerun.

## 5. Casos institucionales preservados

### Reemplazos

La auditoría histórica validó transferencias reales hacia vendedor 99 y conservación de masa. Debe conservarse como playbook, no como prueba permanente para períodos futuros.

### Objetivos

Se detectaron clientes fuera de Universo participando en distribución. La corrección institucional fue validar elegibilidad antes de calcular participaciones y objetivos.

### Caché

Se documentó un caso en el que SQLite estaba correcta y la interfaz mostraba estado cacheado. La lección general es revisar persistencia y estado de UI por separado.

## 6. Política de deuda

La deuda técnica se documenta y prioriza, pero no se corrige automáticamente. Toda intervención requiere impacto, equivalencia funcional y pruebas.
