### Roadmap Institucional - MATINAL (Versión 1.1)

#### 1. Identificación y Propósito

El presente documento establece la **Hoja de Ruta Oficial** de evolución para el proyecto **MATINAL**. Su propósito es secuenciar de forma estricta, ordenada y no disruptiva las etapas de mejora técnica y funcional, garantizando que cada intervención acerque al sistema hacia la arquitectura objetivo aprobada sin poner en riesgo la operación comercial diaria en producción.

---

#### 2. Estructura de Fases del Roadmap

##### FASE 1: Estabilización y Memoria Institucional (Completada - Versión 1.0)

- **Objetivo**: Relevar, documentar y congelar la verdad oficial del sistema mediante ingeniería inversa.
- **Hitos Principales**:
  - Consolidación y cierre de los 6 documentos fundacionales de la memoria institucional (ESTADO_ACTUAL.md, ARQUITECTURA.md, GLOSARIO_REGLAS.md, DICCIONARIO_TABLAS.md, DECISIONES_TECNICAS.md, ROADMAP.md).
  - Inventario completo de reglas de negocio y estructuras de datos.

---

##### FASE 2: Logging Estructurado

- **Objetivo**: Proveer trazabilidad de ejecución y auditoría de errores en producción.
- **Hitos Principales**:
  - Implementación de un subsistema centralizado de logging basado en archivos rotativos locales para capturar excepciones, tiempos de ejecución de motores analíticos y fallos de ingesta.
  - Eliminación paulatina de bloques silenciados de excepción (`except Exception: pass`).

###### Estado de Avance

###### FASE 2A - Núcleo DAL (CERRADA ✅)

**Fecha de cierre:** 24/09/2026

**Objetivo cumplido:** Incorporar observabilidad básica al núcleo de la Capa de Acceso a Datos (DAL) sin modificar lógica de negocio, contratos de funciones, estructuras SQL ni comportamiento operativo existente.

**Componentes alcanzados:**
- modules/logger.py
- modules/database.py (núcleo DAL)

**Funciones instrumentadas:**
- init_db()
- cargar_tabla_sql()
- tablas_existen()
- guardar_dataframe_sql()

**Validaciones ejecutadas:**
- Creación automática del directorio `logs/`.
- Creación automática del archivo `logs/matinal.log`.
- Validación de escritura de eventos INFO.
- Validación de escritura de eventos WARNING.
- Validación de persistencia UTF-8.
- Validación de lectura SQLite sobre base productiva.
- Validación de `tablas_existen()`.
- Validación de consultas SQL reales.
- Validación de tabla inexistente con advertencia controlada.
- Validación completa de carga de Streamlit.
- Verificación de ausencia de regresiones funcionales.

**Resultado obtenido:**
- Eliminación de excepciones silenciosas en el núcleo DAL.
- Incorporación de trazabilidad operativa.
- Conservación total de firmas, retornos y lógica de negocio.
- Compatibilidad total con SQLite WAL.
- Compatibilidad total con Streamlit.

**Estado Final:** CERRADA ✅

---

###### FASE 2B - Procesos de Ingesta y Cargas Masivas (EN DISEÑO ✅)

**Fecha de apertura:** 24/09/2026

**Objetivo:** Extender la observabilidad a los procesos de carga e importación de datos desde Excel y componentes asociados.

**Alcance previsto:**
- inicializar_bd_desde_excel()
- importar_maestros_multisolapa_atomica()
- guardar_objetivos_calibrados_desde_excel()
- guardar_innovaciones_desde_excel()
- data_loader.py

**Estado de avance:**
- Auditoría técnica completada ✅
- Auditoría complementaria completada ✅
- PMV de logging aprobada ✅
- Plan quirúrgico de inserción aprobado ✅
- Implementación pendiente ⏳

**Estado:** EN DISEÑO ✅ / IMPLEMENTACIÓN PENDIENTE ⏳

---

##### FASE 3: Validación Preventiva de Archivos (Contratos de Datos)

- **Objetivo**: Blindar al sistema frente a modificaciones no previstas en las cabeceras o formatos de los archivos Excel externos de origen.
- **Hitos Principales**:
  - Despliegue de un módulo validador previo a la ingesta que compruebe la presencia obligatoria de columnas críticas (CodVendedor, Cliente, PesoKg, etc.) antes de actualizar SQLite.

---

##### FASE 4: STAGING (Capa de Limpieza Intermedia)

- **Objetivo**: Establecer la primera capa formal de la arquitectura objetivo hacia la separación de responsabilidades.
- **Hitos Principales**:
  - Creación de tablas intermedias de Staging en SQLite dedicadas a la normalización de tipos de datos, estandarización de cadenas de texto y limpieza de nulos con anterioridad al poblamiento de las tablas núcleo.

---

##### FASE 5: BUSINESS RULES (Centralización de Reglas)

- **Objetivo**: Aislar la inteligencia comercial desacoplándola de las vistas de presentación y reportes.
- **Hitos Principales**:
  - Extracción y centralización de los Filtros N1, N2, motor de períodos (_Arrastre_, _Actual_, _Futuro_), definición operativa de CCC y umbrales digitales de MiNegocio hacia un módulo exclusivo de reglas de negocio.

---

##### FASE 6: CORE (Modelo Relacional Normalizado)

- **Objetivo**: Evolucionar la persistencia SQLite hacia un esquema relacional estructurado y optimizado.
- **Hitos Principales**:
  - Diseño de tablas relacionales con claves foráneas e índices de rendimiento estrictos para transacciones y maestros, manteniendo compatibilidad total con la capa de reportes.

---

#### 3. Evoluciones Funcionales Futuras

##### FASE 7: Módulo de Compromisos Operativos

- **Objetivo**: Integrar la captura de compromisos comerciales de preventistas (originados vía formularios externos o cargas estructuradas online) de forma estrictamente desacoplada de los datos históricos de ventas.

- **Hitos Principales**:
  - Despliegue de tablas operativas independientes para compromisos y diseño de un tablero gerencial de seguimiento de promesas de venta.

---

##### FASE 8: Check-In Físico y Ejecución Comercial

- **Objetivo**: Incorporar telemetría y validación de visitas en campo para la fuerza de ventas.

---

##### FASE 9: Comisiones Dinámicas y Seguimiento Operativo

- **Objetivo**: Automatizar el cálculo de incentivos y comisiones de preventistas basados en los logros comerciales multivariable (Kilos, CCC, Cobertura) alcanzados en el mes operativo.