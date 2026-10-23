# MATINAL ONLINE | Modelo de datos y persistencia

## 1. Persistencia principal

- Motor: SQLite
- Base principal: `data/matinal.db`
- Modo observado: WAL

SQLite es la fuente física institucional, pero la interfaz puede mostrar estado cacheado. Una base correcta no garantiza por sí sola una interfaz actualizada.

## 2. Tablas principales confirmadas

### `vta`

Transacciones comerciales.

Campos relevantes observados:

- `CodVendedor`
- `Cliente`
- `FechaCarga`
- `FechaEntrega`
- `FechaLiquidacion`
- `PesoKg`
- `CantBase`
- `ImporteNetoItem`
- `Marca`
- `Proveedor`
- `Articulo`
- `Subramo`
- `TipoDeVenta`

Índices históricos documentados:

- `idx_vta_vendedor`
- `idx_vta_cliente`
- `idx_vta_fechacarga`
- `idx_vta_fechaentrega`
- `idx_vta_marca`

### `universo`

Padrón vigente de clientes y fuente de elegibilidad comercial. Contiene taxonomía, segmentación y titularidad vigente.

Campos relevantes:

- `Codigo`
- `Cliente`
- `SegmentoClienteCodigo`
- `CodVen`
- `Razon_Social`
- `Subramo`
- `Direccion`

### `universo_hist`

Snapshots completos del universo. Modelo: una fila por cliente y versión.

Metadatos:

- `FechaSnapshot`
- `FechaCargaSistema`
- `HashSnapshot`

### `universo_versiones`

Catálogo de snapshots. Modelo: una fila por versión.

Campos:

- `VersionID`
- `FechaSnapshot`
- `FechaCargaSistema`
- `HashSnapshot`
- `CantClientes`

### `rutas`

Calendario operativo para días pasados, días restantes, ritmo y proyecciones.

### `altas`

Movimientos de cartera. Se observaron referencias históricas a altas de creación, activación, inactivación y modificación.

### `ausencias`

Ausencias y reemplazos. Alimenta `CodVendedorOperativo`.

### `tp`

Fuente persistida del dominio Tienda Perfecta.

### Maestros y parámetros

El sistema administra, entre otros:

- Maestro de vendedores
- Maestro de segmentos
- Maestro Marca/CEBE
- Maestro CCC
- Maestro de innovaciones
- Objetivos calibrados
- Objetivos TN, Gross y Cobertura

## 3. VTA física actual

La carga prioriza:

```text
data/VTA/*.csv
→ VTA_CONSOLIDADO.parquet
→ SQLite
```

El Excel monolítico de ventas no debe considerarse origen productivo actual sin evidencia específica.

## 4. Historización de Universo

Si el hash del Universo difiere del último snapshot:

1. Se genera el snapshot en `universo_hist`.
2. Se registra la versión en `universo_versiones`.

Si el hash coincide, no se genera una nueva versión.

Los procesos productivos continúan consumiendo `universo` como padrón vigente. La reconstrucción histórica automática no está documentada como consumo productivo actual.

## 5. Contratos STAGING mínimos

### Ventas

- `FechaCarga_dt`
- `FechaEntrega_dt`
- `CodVendedor`
- `Cliente`
- `PesoKg`
- `CantBase`
- `ImporteNetoItem`
- `Marca`

### Clientes

- `Cliente`
- `Taxonomia`
- `NombreCliente`
- `CodVendedor`

### Ausencias

- `Fecha_dt`
- `CodVend_clean`
- `Reemplazo_clean`

## 6. Reglas de integridad

- Validar `COUNT`, identificadores únicos y sumas antes y después de transformaciones.
- Validar población origen, elegible y excluida antes de revisar fórmulas.
- Validar conservación de masa en distribuciones y reasignaciones.
- Revisar caché, `session_state` y reruns cuando SQLite y la interfaz difieran.
