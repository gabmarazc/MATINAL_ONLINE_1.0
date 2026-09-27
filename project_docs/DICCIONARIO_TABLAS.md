# Diccionario de Tablas - MATINAL (Versión 1.0)

## 1. Identificación y Propósito
El presente documento constituye la **Fuente de Verdad Institucional** para la estructura de datos que sostiene el motor analítico de MATINAL. Documenta de forma exhaustiva las tablas físicas alojadas en la base de datos local SQLite (`data/matinal.db`) y sus equivalentes lógicas provenientes de las fuentes Excel de ingesta externa[cite: 1].

---

## 2. Inventario Normativo de Estructuras de Datos

### A. Tablas Transaccionales
*   **1. vta**
    *   **Nombre Técnico**: `vta`[cite: 2]
    *   **Clasificación**: Transaccional[cite: 2]
    *   **Origen**: Archivo Excel `VTA.xlsx` (~133 MB)[cite: 1].
    *   **Descripción Funcional**: Contiene el registro histórico y operativo bruto de todas las transacciones de ventas comerciales de la compañía procesadas por la fuerza de preventa[cite: 1].
    *   **Fuente de Datos**: Archivo Excel periódico cargado mediante `data_loader.py` y persistido por `database.py`.
    *   **Clave Primaria Efectiva**: Ninguna (tabla plana basada en registros secuenciales de origen).
    *   **Campos Principales**: `CodVendedor`, `Cliente`, `FechaCarga`, `FechaEntrega`, `PesoKg`, `ImporteNetoItem`, `CantBase`, `Marca`, `Subramo`, `TipoDeVenta`, `Proveedor`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Subramo` (Filtro N1 Empleados), `TipoDeVenta` (Exclusión comodatos), `Proveedor` (Filtro PepsiCo), `FechaCarga` (Corte Día Matinal), `CodVendedor` (Exclusión Depósito 20)[cite: 2, 3].
    *   **Módulos Consumidores**: `database.py`, `data_loader.py`, y todos los submódulos analíticos de reportes (`rep_*.py`)[cite: 2].
    *   **Frecuencia de Actualización**: 3 veces al día en producción.
    *   **Observaciones Operativas**: Es la tabla de mayor volumetría (~350 MB en SQLite junto con índices). Cuenta con índices optimizados en `CodVendedor`, `Cliente`, `FechaCarga`, `FechaEntrega` y `Marca`[cite: 2].

---

### B. Tablas Maestras
*   **2. universo**
    *   **Nombre Técnico**: `universo`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Archivo Excel `UNIVERSO.xlsx`[cite: 1].
    *   **Descripción Funcional**: Padrón oficial de cartera de clientes activos, conteniendo su segmentación, taxonomía (A/B/C/D), direcciones y asignación comercial[cite: 1].
    *   **Fuente de Datos**: Archivo Excel periódico procesado por `data_loader.py`.
    *   **Clave Primaria Efectiva**: Ninguna en origen (identificado lógicamente por `Codigo` / `Cliente`).
    *   **Campos Principales**: `Codigo` (o `Cliente`), `SegmentoClienteCodigo` (Taxonomía), `CodVen`, `Razon_Social`, `Subramo`, `Direccion`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `SegmentoClienteCodigo` (Taxonomías A, B, C, D), `Subramo` (Exclusión empleados), `CodVen`[cite: 2, 3].
    *   **Módulos Consumidores**: `data_loader.py`, `rep_ccc.py`, `rep_MN.py`, `rep_gerencial.py`, `rep_vespertina.py`[cite: 3, 5].
    *   **Frecuencia de Actualización**: Periódica / Mensual.
    *   **Observaciones Operativas**: Sus campos sufren un proceso de renombrado dinámico en `data_loader.py` para normalizar referencias a `Cliente` y `Taxonomia`.

*   **3. rutas**
    *   **Nombre Técnico**: `rutas`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Archivo Excel `RUTAS.xlsx`[cite: 1].
    *   **Descripción Funcional**: Calendario de visitas planificadas por preventista y fecha, base fundamental para el cálculo de días hábiles transcurridos y restantes del mes[cite: 1].
    *   **Fuente de Datos**: Archivo Excel periódico procesado por `data_loader.py`.
    *   **Clave Primaria Efectiva**: Ninguna.
    *   **Campos Principales**: `Fecha`, `CodVen` (o `CodVendedor`), campos de día de visita o ruta[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Fecha` (para acotar el corte con el Día Venta), `CodVen`[cite: 2].
    *   **Módulos Consumidores**: `data_loader.py`, `rep_kilos.py`, `rep_gerencial.py`.
    *   **Frecuencia de actualización**: Mensual.
    *   **Observaciones Operativas**: Se procesa vectorialmente para extraer y unificar el día de la semana correspondiente a cada visita.

*   **4. altas** (y sub-tablas `altas_*` por solapa)
    *   **Nombre Técnico**: `altas` / `altas_{sheet}`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Archivo Excel multi-solapa `ALTAS.xlsx`[cite: 3].
    *   **Descripción Funcional**: Registro mensual de movimientos de cartera (creaciones, activaciones, inactivaciones y cierres definitivos) utilizado para el cálculo de la Cartera Neta en el módulo CCC[cite: 3].
    *   **Fuente de Datos**: Archivo Excel procesado por `database.py` e hidratado por `data_loader.py`[cite: 2].
    *   **Clave Primaria Efectiva**: Ninguna.
    *   **Campos Principales**: `Fecha`, `Codigo` (Cliente), `Estado`, `Vendedor`, `Origen_Hoja`[cite: 3].
    *   **Campos Críticos para Reglas de Negocio**: `Origen_Hoja` (diferencia 'Creacion', 'Activacion', 'Inactivacion'), `Estado` (exclusión de 'CIERRE DEFINITIVO')[cite: 3].
    *   **Módulos Consumidores**: `database.py`, `data_loader.py`, `rep_ccc.py`[cite: 2, 3].
    *   **Frecuencia de actualización**: Mensual.
    *   **Observaciones Operativas**: Como respaldo, si la tabla SQL está vacía, el código intenta leer directamente el archivo físico `ALTAS.xlsx` en disco[cite: 3].

*   **5. maestro_vendedores**
    *   **Nombre Técnico**: `maestro_vendedores`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Módulo de Parámetros / Excel consolidado multi-solapa (`Maestro_Vendedores`)[cite: 2].
    *   **Descripción Funcional**: Padrón normativo de preventistas con asignación de supervisores, días de ajuste y rutas ajustadas específicas por período[cite: 2].
    *   **Fuente de Datos**: Importación manual desde interfaz de Parámetros[cite: 2].
    *   **Clave Primaria Efectiva**: `Codigo_Vendedor` (versionado por período Anio/Mes)[cite: 2].
    *   **Campos Principales**: `Anio`, `Mes`, `Codigo_Vendedor`, `Nombre_Vendedor`, `Supervisor`, `Rutas_Ajustadas`, `Ajuste_Entrega`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Supervisor` (para filtros gerenciales y de supervisión), `Rutas_Ajustadas` (para cálculo de días restantes ajustados)[cite: 2].
    *   **Módulos Consumidores**: `app.py`, `database.py`, `parametros.py`, `rep_kilos.py`, `rep_gerencial.py`, `rep_ccc.py`[cite: 2].
    *   **Frecuencia de actualización**: Mensual / Versionada[cite: 2].
    *   **Observaciones Operativas**: Clave para la vinculación jerárquica con los preventistas y supervisores en todos los reportes.

*   **6. maestro_segmentos**
    *   **Nombre Técnico**: `maestro_segmentos`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Módulo de Parámetros / Excel consolidado multi-solapa (`Maestro_Segmentos`)[cite: 2].
    *   **Descripción Funcional**: Catálogo oficial de segmentos comerciales vigentes (ej. GOLD Salty, SILVER Salty, etc.)[cite: 2].
    *   **Fuente de Datos**: Importación manual desde Parámetros[cite: 2].
    *   **Clave Primaria Efectiva**: `Segmento` (versionado por período Anio/Mes)[cite: 2].
    *   **Campos Principales**: `Anio`, `Mes`, `Segmento`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Segmento`[cite: 2].
    *   **Módulos Consumidores**: `database.py`, `parametros.py`, `rep_kilos.py`, `rep_gerencial.py`, `rep_obj_kilos.py`[cite: 2].
    *   **Frecuencia de actualización**: Mensual / Versionada[cite: 2].

*   **7. maestro_marcas_cebe**
    *   **Nombre Técnico**: `maestro_marcas_cebe`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Módulo de Parámetros / Excel consolidado multi-solapa (`Maestro_Marcas_CEBE`)[cite: 2].
    *   **Descripción Funcional**: Relación de marcas corporativas con unidades de negocio (CEBE) y objetivos macro de toneladas, gross y cobertura[cite: 2].
    *   **Fuente de Datos**: Importación manual desde Parámetros[cite: 2].
    *   **Clave Primaria Efectiva**: `Marca` / `CEBE` (versionado por período Anio/Mes)[cite: 2].
    *   **Campos Principales**: `Anio`, `Mes`, `Marca`, `CEBE`, `Obj_TN_Mes`, `Obj_Gross_Mes`, `Obj_Pepsico_Cobertura`, `Obj_Empresa_Cobertura`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: Objetivos de cobertura y metas macro[cite: 2].
    *   **Módulos Consumidores**: `database.py`, `parametros.py`, `rep_kilos.py`, `rep_gerencial.py`[cite: 2].
    *   **Frecuencia de actualización**: Mensual / Versionada[cite: 2].

*   **8. maestro_innovaciones**
    *   **Nombre Técnico**: `maestro_innovaciones`[cite: 2]
    *   **Clasificación**: Maestra[cite: 2]
    *   **Origen**: Módulo de Parámetros / Excel consolidado multi-solapa (`Maestro_Innovaciones`)[cite: 2].
    *   **Descripción Funcional**: Catálogo de artículos considerados lanzamientos o innovaciones estratégicas auditados por el sistema[cite: 2].
    *   **Fuente de Datos**: Importación manual desde Parámetros[cite: 2].
    *   **Clave Primaria Efectiva**: `(Anio, Mes, Codigo, Innovacion)`[cite: 2].
    *   **Campos Principales**: `Anio`, `Mes`, `Codigo`, `Articulo`, `Innovacion`, `Condicion_Vta`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Codigo`, `Innovacion`[cite: 2].
    *   **Módulos Consumidores**: `database.py`, `parametros.py`, `rep_cob_innovacion.py`[cite: 2, 4].
    *   **Frecuencia de actualización**: Mensual / Versionada[cite: 2].

---

### C. Tablas de Parámetros
*   **9. parametros**
    *   **Nombre Técnico**: `parametros`[cite: 2]
    *   **Clasificación**: Parámetros[cite: 2]
    *   **Origen**: Generación interna automática en `parametros.py`[cite: 2].
    *   **Descripción Funcional**: Almacena las variables temporales operativas globales por defecto (Año, Mes, Día Matinal, Día Venta, Día Anterior)[cite: 2].
    *   **Fuente de Datos**: Inicialización interna por código[cite: 2].
    *   **Clave Primaria Efectiva**: Ninguna.
    *   **Campos Principales**: `PARAMETRO`, `VALOR`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `VALOR` para las fechas operativas globales[cite: 2].
    *   **Módulos Consumidores**: `database.py`, `parametros.py`, `rep_gerencial.py`[cite: 2].
    *   **Frecuencia de actualización**: Dinámica / Por sesión o configuración local.

*   **10. maestro_ccc**
    *   **Nombre Técnico**: `maestro_ccc`[cite: 2]
    *   **Clasificación**: Parámetros[cite: 2]
    *   **Origen**: Módulo de Parámetros / Excel consolidado multi-solapa (`Maestro_CCC_Config`)[cite: 2].
    *   **Descripción Funcional**: Versionado histórico de porcentajes exigidos sobre cartera neta y objetivos absolutos de Pepsico (`Obj_CCC_Pepsico`) por taxonomía (A, B, C, D)[cite: 2].
    *   **Fuente de Datos**: Importación manual desde Parámetros[cite: 2].
    *   **Clave Primaria Efectiva**: `(Anio, Mes, Taxonomia)`.
    *   **Campos Principales**: `Anio`, `Mes`, `Taxonomia`, `Porcentaje_Cartera`, `Obj_CCC_Pepsico`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Porcentaje_Cartera`, `Obj_CCC_Pepsico`[cite: 2].
    *   **Módulos Consumidores**: `database.py`, `parametros.py`, `rep_ccc.py`, `rep_gerencial.py`[cite: 2].
    *   **Frecuencia de actualización**: Mensual / Versionada[cite: 2].

*   **11. parametros_marcas**
    *   **Nombre Técnico**: `parametros_marcas`
    *   **Clasificación**: Parámetros
    *   **Origen**: Carga auxiliar externa.
    *   **Descripción Funcional**: Catálogo secundario de marcas de soporte para filtros y mapeos de visualización.
    *   **Fuente de Datos**: Ingesta externa.
    *   **Clave Primaria Efectiva**: Ninguna.
    *   **Campos Principales**: Campos descriptivos de marcas.
    *   **Módulos Consumidores**: `app.py`, `rep_gerencial.py`.
    *   **Frecuencia de actualización**: Estática / Periódica.

---

### D. Tablas de Objetivos
*   **12. objetivos_vendedores**
    *   **Nombre Técnico**: `objetivos_vendedores`[cite: 2]
    *   **Clasificación**: Objetivos[cite: 2]
    *   **Origen**: Importación de Excel de Objetivos Calibrados (`Objetivos_Calibrados`)[cite: 2].
    *   **Descripción Funcional**: Almacena las metas definitivas en kilogramos asignadas a cada preventista por segmento, versionadas por período gerencial[cite: 2].
    *   **Fuente de Datos**: Carga manual desde el módulo de Parámetros[cite: 2].
    *   **Clave Primaria Efectiva**: `(Anio, Mes, CodVendedor, SEGMENTO)`[cite: 2].
    *   **Campos Principales**: `Anio`, `Mes`, `CodVendedor`, `Nombre`, `Supervisor`, `SEGMENTO`, `Obj_Sugerido_Kg`, `Logro_Anterior_Pct`[cite: 2].
    *   **Campos Críticos para Reglas de Negocio**: `Obj_Sugerido_Kg` (meta oficial de kilos)[cite: 2].
    *   **Módulos Consumidores**: `database.py`, `parametros.py`, `rep_kilos.py`[cite: 2].
    *   **Frecuencia de actualización**: Mensual / Versionada por período[cite: 2].

---

### E. Tablas Auxiliares
*   **13. ausencias**
    *   **Nombre Técnico**: No persiste como tabla SQL física en SQLite (procesada enteramente en memoria volátil por `data_loader.py`).
    *   **Clasificación**: Auxiliares
    *   **Origen**: Exportación CSV web remota vía `cfg.URL_AUSENCIAS`.
    *   **Descripción Funcional**: Padrón dinámico en tiempo real de preventistas ausentes y sus reemplazos operativos asignados por fecha[cite: 3].
    *   **Fuente de Datos**: Petición HTTP externa con TTL de caché de 1 hora.
    *   **Clave Primaria Efectiva**: Ninguna.
    *   **Campos Principales**: `Fecha`, `Ausente`, `Reemplazo`, `Cliente`.
    *   **Campos Críticos para Reglas de Negocio**: `Ausente`, `Reemplazo`, `Fecha` (construcción de `ClaveAUS`)[cite: 3].
    *   **Módulos Consumidores**: `data_loader.py`, `rep_kilos.py`, `rep_ccc.py`, `rep_gerencial.py`[cite: 3].
    *   **Frecuencia de actualización**: En tiempo real (consulta web bajo demanda con caché temporal).

---

### F. Tablas Derivadas
*   *Nota Arquitectónica Institucional*: Actualmente **no existen tablas derivadas persistidas** en SQLite. Toda la capa de agregaciones, matrices cruzadas, cálculos de promedios, tendencias y reportes se procesa al vuelo en memoria RAM mediante DataFrames de Pandas dentro de los submódulos de análisis y presentación (`/modules/`).