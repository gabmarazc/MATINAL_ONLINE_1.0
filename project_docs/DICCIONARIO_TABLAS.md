## Diccionario de Tablas - MATINAL (Versión 2.0)

### 1. Identificación y Propósito

El presente documento constituye la Fuente de Verdad Institucional para la estructura de datos de MATINAL.

Su objetivo es documentar las tablas físicas alojadas en SQLite, las entidades utilizadas por la capa STAGING, las estructuras consumidas por CORE y las entidades actualmente disponibles dentro de BUSINESS RULES.

Ante cualquier discrepancia entre documentación y código:

1. Revisar ARQUITECTURA.md
2. Revisar ESTADO_ACTUAL.md
3. Revisar DECISIONES_TECNICAS.md
4. Revisar este documento
5. Recién después analizar el código fuente

---

## 2. Arquitectura de Datos Oficial

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

Principios institucionales:

- RAW recibe información externa.
- SQLITE persiste información.
- STAGING normaliza y tipa.
- CORE interpreta operación.
- BUSINESS RULES aplica reglas de negocio.
- REPORTES consumen resultados finales.

---

## 3. Persistencia Oficial

Ubicación:

```text
data/matinal.db
```

Motor:

```text
SQLite
```

Modo:

```text
WAL (Write Ahead Logging)
```

Características:

- Fuente única de verdad.
- Persistencia local.
- Lectura desacoplada de Excel.
- Alto rendimiento de lectura.
- Índices optimizados para tablas críticas.

---

# A. TABLAS TRANSACCIONALES

## 1. vta

### Nombre Técnico

```text
vta
```

### Clasificación

```text
Transaccional
```

### Descripción

Contiene el registro completo de transacciones comerciales consumidas por los distintos procesos analíticos del sistema.

Es la principal fuente de datos operativos de MATINAL.

### Origen

```text
VTA.xlsx
```

### Campos Relevantes

```text
CodVendedor
Cliente
FechaCarga
FechaEntrega
FechaLiquidacion
PesoKg
CantBase
ImporteNetoItem
Marca
Proveedor
Articulo
Subramo
TipoDeVenta
```

### Índices Institucionales

```text
idx_vta_vendedor
idx_vta_cliente
idx_vta_fechacarga
idx_vta_fechaentrega
idx_vta_marca
```

### Consumidores

```text
staging.py
core_operaciones.py
core_ventas_base.py
reportes comerciales
```

### Entidad STAGING Asociada

```python
obtener_staging_vta()
```

### Contrato STAGING Garantizado

```text
FechaCarga_dt
FechaEntrega_dt
CodVendedor
Cliente
PesoKg
CantBase
ImporteNetoItem
Marca
```

---

# B. TABLAS MAESTRAS

## 2. universo

### Nombre Técnico

```text
universo
```

### Clasificación

```text
Maestra
```

### Descripción

Padrón institucional de clientes.

Constituye la base para los análisis de cartera, taxonomías y segmentación comercial.

### Origen

```text
UNIVERSO.xlsx
```

### Campos Relevantes

```text
Codigo
Cliente
SegmentoClienteCodigo
CodVen
Razon_Social
Subramo
Direccion
```

### Consumidores

```text
staging.py
CCC
Mi Negocio
Gerencial
Vespertina
```

### Entidad STAGING Asociada

```python
obtener_staging_clientes()
```

### Contrato STAGING Garantizado

```text
Cliente
Taxonomia
NombreCliente
CodVendedor
```

---

## 3. rutas

### Nombre Técnico

```text
rutas
```

### Clasificación

```text
Maestra Operativa
```

### Descripción

Calendario operativo de visitas comerciales.

Es la fuente oficial para el cálculo de:

- días pasados
- días restantes
- ritmo operativo
- proyecciones

### Origen

```text
RUTAS.xlsx
```

### Campos Relevantes

```text
Fecha
CodVen
CodVendedor
Vendedor
```

### Consumidores

```text
staging.py
core_operaciones.py
rep_kilos.py
rep_gerencial.py
```

### Entidad STAGING Asociada

```python
obtener_staging_rutas()
```

---

## 4. altas

### Nombre Técnico

```text
altas
```

### Clasificación

```text
Maestra Operativa
```

### Descripción

Registro consolidado de movimientos de cartera.

Durante la carga se generan tablas auxiliares por hoja y un consolidado institucional.

### Origen

```text
ALTAS.xlsx
```

### Campos Relevantes

```text
Fecha
Codigo
Estado
Origen_Hoja
```

### Tablas Auxiliares Asociadas

```text
altas_creacion
altas_activacion
altas_inactivacion
altas_modificacion
```

### Consumidores

```text
CCC
Gerencial
```

---

## 5. ausencias

### Nombre Técnico

```text
ausencias
```

### Clasificación

```text
Operativa
```

### Estado

```text
Implementada en SQLite
```

### Descripción

Contiene registros de ausencias y reemplazos de vendedores.

Es la fuente oficial utilizada para determinar:

```text
CodVendedorOperativo
```

### Consumidores

```text
obtener_staging_ausencias()
procesar_ausencias_y_reemplazos()
```

### Entidad STAGING Asociada

```python
obtener_staging_ausencias()
```

### Contrato STAGING Garantizado

```text
Fecha_dt
CodVend_clean
Reemplazo_clean
```

### 