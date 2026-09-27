# Arquitectura del Sistema - MATINAL (Versión 1.0)

## 1. Arquitectura Física Actual
MATINAL opera como una aplicación monolítica modular basada en Python y Streamlit, estructurada físicamente en un directorio local de ejecución que contiene:
- **Punto de Entrada (`app.py`)**: Script raíz que gestiona el ciclo de vida de la interfaz, autenticación y enrutamiento por solapas[cite: 8].
- **Capa de Ingesta (`data_loader.py`)**: Script raíz encargado de sincronizar fuentes Excel locales y remotas hacia el motor persistente[cite: 9].
- **Capa de Módulos de Negocio (`/modules/`)**: Directorio contenedor de los submódulos funcionales de persistencia (`database.py`), configuración (`parametros.py`), utilidades (`utils.py`) y motores analíticos de reportes (`rep_kilos.py`, `rep_gerencial.py`, `rep_ccc.py`, `rep_MN.py`, `rep_cob_marca.py`, `rep_cob_innovacion.py`, `rep_obj_kilos.py`, `rep_vespertina.py`)[cite: 8].
- **Capa de Almacenamiento Persistente (`/data/matinal.db`)**: Base de datos local SQLite con el modo de concurrencia WAL (*Write-Ahead Logging*) habilitado y una volumetría aproximada de ~350 MB[cite: 8, 9].
- **Orígenes Externos (RAW)**: Archivos Excel periódicos (`VTA.xlsx` ~133 MB, `UNIVERSO.xlsx`, `RUTAS.xlsx`, `ALTAS.xlsx`) y catálogos maestros[cite: 5, 8, 9].

## 2. Arquitectura Lógica Actual
La arquitectura lógica se divide en tres grandes capas operativas acopladas:
1. **Capa de Persistencia e Ingesta**: A través de `database.py` y `data_loader.py`, los archivos Excel crudos se transforman implícitamente mediante Pandas e insertan en SQLite con la directiva `if_exists='replace'`[cite: 2, 9].
2. **Capa de Reglas de Negocio Descentralizadas**: Cada submódulo en `/modules/` implementa sus propias tuberías analíticas (ej. `preparar_ventas_gerencial_puro`, `preparar_ventas_ccc`, `preparar_datos_ventas_segmento`) aplicando de forma repetida los filtros corporativos N1 y N2[cite: 10].
3. **Capa de Presentación y Visualización**: Construida sobre Streamlit, utilizando componentes interactivos basados en grillas de datos (`AgGrid`) y tarjetas métricas HTML unificadas (`utils.py`)[cite: 8, 10].

## 3. Flujo de Datos Actual
1. **Ingesta (RAW ➔ SQLite)**: `data_loader.py` escanea los Excel en disco, estandariza fechas a cadenas ISO (`YYYY-MM-DD`) y ejecuta inserciones por bloques (`chunksize=10000`) en SQLite[cite: 2, 9].
2. **Hidratación en Memoria**: Al iniciar la aplicación o pulsar "Recargar Bases", `app.py` recupera los DataFrames principales (`VTA`, `UNIVERSO`, `RUTAS`, `ALTAS`) y los almacena en `st.session_state["bases"]`[cite: 8, 9].
3. **Derivación de la Única Fuente de Verdad (SSOT)**: Todos los reportes consumen las transacciones a través de `db.obtener_df_maestro_corporativo()`, aplicando el Filtro N1 (exclusión de empleados)[cite: 2].
4. **Procesamiento de Dominio**: Los submódulos aplican los Filtros N2 (comodatos, PepsiCo, depósito, Día Matinal, períodos de arrastre/actual/futuro) y cruzan con padrones de ausencias, reemplazos y universos[cite: 10].
5. **Renderizado Visual**: Los resultados agregados se entregan a la interfaz para su visualización y exportación funcional a Excel[cite: 10].

## 4. Componentes Actuales
- `app.py`: Orquestador global, control de sesión, autenticación y renderizado de pestañas por rol[cite: 8].
- `data_loader.py`: Pasarela de sincronización de archivos Excel locales a SQLite y carga de ausencias remotas vía HTTP[cite: 9].
- `modules/database.py`: DAL (Data Access Layer) para gestión de conexiones SQLite, índices de rendimiento y transacciones atómicas[cite: 8].
- `modules/parametros.py`: Administración de dimensiones, maestros e importador global multi-solapa[cite: 2].
- Submódulos de Reportes (`rep_*.py`): Motores analíticos especializados (Gerencial, Kilos, CCC, MiNegocio, Cobertura de Marcas, Cobertura de Innovaciones, Objetivos y Vespertina)[cite: 8].
- `modules/utils.py`: Funciones auxiliares de parseo robusto de fechas, normalización vectorial de rutas y componentes HTML estéticos[cite: 10].

## 5. Dependencias Actuales
- **Librerías de Ejecución**: Python, Streamlit, Pandas, NumPy, OpenPyXL, st-aggrid[cite: 8, 10].
- **Infraestructura de Datos**: SQLite (modo WAL)[cite: 8, 9].
- **Dependencias Externas**: Conectividad HTTP opcional para la descarga remota de ausencias (`cfg.URL_AUSENCIAS`)[cite: 9].

## 6. Estado Actual de Session State
`st.session_state` mantiene de forma volátil las siguientes variables de control y estado operativo:
- `autenticado` y `nivel_usuario`: Control de acceso por perfiles (Admin, Gerencia, Supervisión)[cite: 8].
- `bases`: Diccionario global con los DataFrames maestros (`VTA`, `UNIVERSO`, `RUTAS`, `ALTAS`, `AUSENCIAS`)[cite: 8, 9].
- `bd_inicializada`: Bandera de control para evitar bucles en el arranque inicial[cite: 8].
- Variables de referencia temporal (`sel_dia_matinal`, `sel_dia_venta`, `sel_dia_anterior`)[cite: 8].
- Cachés de estado intermedias en submódulos (ej. `_ccc_df_clientes_detalle`).

## 7. Estado Actual de Cachés
- **Caché Global de Interfaz**: Mecanismos explícitos mediante `st.cache_data.clear()` y `st.cache_resource.clear()` accionados desde la barra lateral[cite: 8].
- **Caché Analítica de Motores**: Uso extensivo del decorador `@st.cache_data(show_spinner=False)` en funciones de cálculo pesado de los submódulos, parametrizadas mediante huellas basadas en longitud de DataFrames y filtros temporales[cite: 10].

## 8. Estado Actual de Persistencia SQLite
- **Ubicación y Concurrencia**: Archivo físico único en `data/matinal.db` con modo WAL activo[cite: 8, 9].
- **Esquema Implícito**: Las tablas se generan de forma dinámica a partir de los DataFrames de Pandas mediante `to_sql(..., if_exists='replace')`, sin una capa DDL relacional estricta normalizada, salvo por la creación explícita de índices secundarios en `database.py` (`idx_vta_vendedor`, `idx_vta_cliente`, `idx_vta_fechacarga`, `idx_vta_fechaentrega`, `idx_vta_marca`)[cite: 2].

## 9. Reglas de Negocio Detectadas
- **Filtro N1 (Empleados)**: Exclusión universal de registros comerciales asociados a cuentas internas o subramos de empleados[cite: 2, 7].
- **Filtros N2 (Operativos)**: Exclusión de comodatos/préstamos, selección exclusiva de proveedor PepsiCo, supresión del depósito (vendedor 20), corte temporal por **Día Matinal**, clasificación por **Período** (*Arrastre*, *Actual*, *Futuro*) y reasignación por ausencias/reemplazos[cite: 10].
- **Criterio CCC**: Un cliente es comprador efectivo si acumula `CantBase >= 3` e `ImporteNeto >= 1`.
- **Gestión de Cartera**: Cálculo de Cartera Neta descontando altas y reactivaciones del período mensual.

## 10. Riesgos Actuales
- **Fragilidad ante Cambios en Origen**: Dependencia estricta de la estructura de columnas de los archivos Excel externos provistos por terceros; variaciones en los nombres de cabeceras pueden degradar los parsers dinámicos.
- **Manejo Silencioso de Errores**: Presencia de bloques `except Exception: pass` en operaciones de base de datos y carga web, lo que dificulta la detección temprana de fallos en producción[cite: 2, 9].

## 11. Deuda Técnica Actual
- **Descentralización de Reglas**: La lógica analítica de filtrado N1 y N2 se repite de forma similar en múltiples submódulos en lugar de residir en un componente centralizado.
- **Funciones Monolíticas ("God Functions")**: Presencia de funciones de cálculo global excesivamente largas y complejas (ej. en `rep_gerencial.py` y `rep_kilos.py`)[cite: 10].
- **Ausencia de Logging Estructurado**: Falta de un sistema de registro de eventos y auditoría persistente.

---

## 12. Arquitectura Objetivo y Brecha Actual

### Estado Actual (Híbrido / Acoplado)
```text
Excel (RAW)
    ↓
SQLite (Persistencia Plana sin Staging)
    ↓
SSOT N1 (DataFrame Maestro Corporativo)
    ↓
Pipelines Analíticos Descentralizados (en cada submódulo)
    ↓
Reportes / Grillas Interactivas (Streamlit / AgGrid)
```[cite: 2, 8, 9, 10]

### Arquitectura Objetivo (Institucional Aprobada)
```text
RAW (Ingesta de Archivos Crudos)
    ↓
STAGING (Limpieza, Tipado y Normalización Estructural)
    ↓
CORE (Entidades Normalizadas y Relacionales en SQLite)
    ↓
BUSINESS RULES (Capa Centralizada de Reglas N1, N2 y Cálculos Comerciales)
    ↓
REPORTES (Vistas de Presentación desacopladas)
```[cite: 5]

### Análisis de la Brecha
- **Qué existe hoy**: Ingesta directa desde archivos Excel hacia tablas planas en SQLite, con reglas de negocio ejecutadas al vuelo dentro de cada reporte analítico mediante funciones de preparación en Pandas[cite: 2, 8, 9, 10].
- **Qué falta**: Una capa intermedia de `STAGING` que valide esquemas y limpie tipos antes de persistir, y una capa de `BUSINESS RULES` que centralice los filtros corporativos evitando la duplicación de código en los submódulos.
- **Componentes Futuros por Capa**:
  - *RAW*: Mantiene la ingesta de archivos Excel y CSV (`data_loader.py`).
  - *STAGING*: Futuras rutinas de validación de esquemas y tipado estricto previas al almacenamiento.
  - *CORE*: Futuro esquema relacional normalizado en SQLite para entidades transaccionales y maestras.
  - *BUSINESS RULES*: Futuro módulo centralizado contenedor del glosario de reglas N1, N2 y clasificaciones comerciales.
  - *REPORTES*: Los módulos actuales de visualización en Streamlit y AgGrid operando exclusivamente como capas de presentación desacopladas[cite: 8, 10].