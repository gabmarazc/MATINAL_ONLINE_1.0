## Decisiones Técnicas y Arquitectónicas - MATINAL (Versión 1.1)

### 1. Identificación y Propósito

El presente documento consolida y formaliza todas las decisiones arquitectónicas, operativas y tecnológicas vigentes en el proyecto **MATINAL**. Su propósito es servir como marco normativo inalterable para orientar cualquier evolución futura, garantizando la estabilidad operativa del sistema en producción.

---

### 2. Inventario Normativo de Decisiones Técnicas

#### A. Decisiones de Stack y Tecnología

- **DT.1: Aprobación y Vigencia de Monolito Modular en Python**
- _Descripción_: Se ratifica el uso de Python, Streamlit, Pandas y SQLite como la arquitectura base inalterable del producto. Se prohíben explícitamente migraciones a arquitecturas distribuidas, bases de datos relacionales pesadas (PostgreSQL/MySQL) o frameworks de frontend complejos (React/Angular) por carecer de justificación de negocio para un motor analítico comercial.

- **DT.2: Uso Exclusivo de Grillas AgGrid (st-aggrid)**
- _Descripción_: Estandarización de la librería st-aggrid para la renderización de tablas analíticas complejas y grillas de detalle ("Batallas"), asegurando filtrado avanzado y una experiencia visual directiva profesional.

---

#### B. Decisiones de Persistencia y Datos

- **DT.3: SQLite con Modo WAL Activo**
- _Descripción_: Uso de SQLite (`data/matinal.db`) configurado con `PRAGMA journal_mode=WAL;` para garantizar concurrencia segura y estabilidad en lecturas y escrituras concurrentes durante la operación en producción.

- **DT.4: Ingesta Plana por Volcado Masivo (to_sql)**
- _Descripción_: Adopción del método de reemplazo total (`if_exists='replace'`) por bloques (`chunksize`) para la sincronización inicial de fuentes RAW desde Excel, priorizando la simplicidad operativa frente a procesos ETL complejos.

---

#### C. Decisiones de Rendimiento y Estado

- **DT.5: Estrategia de Caché por Huellas de Datos (@st.cache_data)**
- _Descripción_: Aceleración de motores analíticos pesados mediante decoradores de caché en Pandas parametrizados con cadenas de huellas (`huella_datos`), evitando recomputaciones redundantes ante cambios menores en la interfaz.

- **DT.6: Persistencia Volátil en st.session_state**
- _Descripción_: Utilización del estado de sesión de Streamlit exclusivamente para control de credenciales, perfiles de usuario, estado de autenticación y carga inicial de DataFrames maestros globales.

---

#### D. Decisiones de Gobierno de Negocio

- **DT.7: SSOT Corporativo e Inmutabilidad del Maestro N1**
- _Descripción_: Centralización de la limpieza de cuentas de empleados a través de `obtener_df_maestro_corporativo()`, garantizando que ninguna vista derive su información de fuentes que no hayan atravesado este filtro normativo.

- **DT.8: Desacoplamiento del Bloque "Futuro"**
- _Descripción_: Decisión explícita de separar la analítica operativa diaria (sometida al corte estricto del Día Matinal) frente al potencial disponible futuro (procesado sin restricciones temporales), permitiendo auditar el volumen disponible inminente.

---

#### E. Decisiones Arquitectónicas Fundacionales

- **DT.9: Evolución Incremental y Prohibición de Reescritura Total**
- _Descripción_: Toda evolución de software debe preservar compatibilidad absoluta con la operación en producción. Queda terminantemente prohibida la reescritura completa o masiva del sistema.

- **DT.10: Prioridad de las Reglas de Negocio sobre las Decisiones Técnicas**
- _Descripción_: Las definiciones funcionales instituidas en el GLOSARIO_REGLAS.md tienen prioridad absoluta y prevalecen por encima de cualquier optimización o decisión técnica futura.

- **DT.11: Arquitectura Objetivo Aprobada**
- _Descripción_: Se adopta formalmente el modelo de transición gradual hacia las cinco capas objetivo:

RAW → STAGING → CORE → BUSINESS_RULES → REPORTES

Asegurando que cualquier cambio acerque progresivamente al sistema a esta estructura sin afectar la producción.

- **DT.12: Documentación Institucional como Activo Estratégico**
- _Descripción_: Toda decisión relevante de diseño o negocio debe reflejarse en la memoria institucional. Los documentos ESTADO_ACTUAL.md, ARQUITECTURA.md, GLOSARIO_REGLAS.md, DICCIONARIO_TABLAS.md, DECISIONES_TECNICAS.md y ROADMAP.md constituyen la verdad oficial vigente del proyecto.

---

#### F. Decisiones de Observabilidad y Diagnóstico

- **DT.13: Logging Estructurado Institucional y Observabilidad Operativa**
- _Descripción_: Se adopta formalmente un subsistema centralizado de logging basado en la librería estándar logging de Python y archivos rotativos locales mediante RotatingFileHandler.

##### Implementación Inicial (Fase 2A)

- Creación de modules/logger.py como punto único de configuración.
- Creación automática del directorio logs/.
- Creación automática del archivo logs/matinal.log.
- Incorporación de trazas estructuradas en el núcleo de la DAL.

##### Componentes Alcanzados

- init_db()
- cargar_tabla_sql()
- tablas_existen()
- guardar_dataframe_sql()

##### Principios de Implementación

- No modificar lógica de negocio.
- No modificar consultas SQL.
- No modificar firmas de funciones.
- No modificar tipos de retorno.
- No modificar transacciones existentes.
- Mantener compatibilidad total con SQLite en modo WAL.

##### Resultado Validado

- Logging INFO validado.
- Logging WARNING validado.
- Persistencia UTF-8 validada.
- Lectura SQLite validada.
- Streamlit validado.
- Ausencia de regresiones observadas.
- Compatibilidad operativa confirmada sobre entorno de desarrollo.

##### Estado

- Vigente ✅
- Implementado y validado durante la Fase 2A del Roadmap Institucional.

##### G. Decisiones de Padrones Corporativos

- **DT.14: Maestro Único de Preventistas y Supervisores**
- _Descripción_: Se establece a `maestro_vendedores` como fuente oficial y única para la identificación de preventistas y supervisores en los módulos analíticos. Los códigos operativos contenidos en fuentes transaccionales o relevamientos externos deberán considerarse exclusivamente claves técnicas de cruce.

###### Alcance Inicial
- Avance CCC (`rep_ccc.py`)
- Tienda Perfecta (`rep_tp.py`)

###### Criterios de Implementación
- Visualización mediante nombre corporativo del preventista.
- Obtención del supervisor desde `maestro_vendedores`.
- Compatibilidad con filtros globales de supervisor.
- Regeneración dinámica de catálogos dependientes del supervisor seleccionado.
- Conservación de compatibilidad con los mecanismos existentes de `st.session_state`.

###### Resultado Esperado
- Coherencia transversal entre módulos.
- Eliminación de dependencias visuales sobre códigos de vendedor.
- Unificación de criterios de filtrado por supervisor.

###### Estado
- Vigente ✅
- Implementado y validado en CCC y Tienda Perfecta (25/09/2026).