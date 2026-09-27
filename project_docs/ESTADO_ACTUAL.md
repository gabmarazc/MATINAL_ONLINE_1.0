# Estado Actual del Proyecto - MATINAL

## 1. Identificación y Propósito
- **Nombre del Producto**: MATINAL (Sistema de Gestión y Análisis Comercial).
- **Naturaleza**: Motor analítico comercial de alta precisión para control de preventa, cumplimiento de objetivos, cobertura de marcas, innovaciones y adopción digital (`MiNegocio`).
- **Nivel de Operación**: En producción activa, actualizado preventivamente 3 veces al día.

## 2. Alcance Funcional Actual (Operativo en Producción)
Todos los siguientes módulos se encuentran plenamente operativos y funcionales en producción:
- **Dashboard Gerencial**: Vista directiva consolidada con proyecciones de volumen e importes, desacoplando la operación con corte matinal frente al potencial disponible futuro.
- **CCC (Clientes con Compra)**: Evaluación de cartera neta, altas, reactivaciones y desgloses por taxonomía (A, B, C, D) con herramientas de combate (Batalla NC).
- **MiNegocio**: Medición de adopción digital (No Digital, Híbridos, Fully Digital) sobre el universo corporativo y cálculo de faltantes para el umbral del 70%.
- **Kilos**: Seguimiento analítico de avance de kilogramos por segmento, preventista y supervisor con proyección basada en días pasados y restantes (incluyendo rutas ajustadas).
- **Cobertura Marca**: Auditoría de cumplimiento de objetivos de cobertura por marca oficial frente a las compras reales de la cartera.
- **Cobertura Innovación**: Control de penetración de lanzamientos y productos nuevos en los clientes activos.
- **Objetivos**: Generador tentativo de metas de kilos por vendedor y segmento basados en distribuciones proporcionales históricas.
- **Parámetros**: Administración de dimensiones, maestros y un importador global multi-solapa transaccional.
- **Vespertina**: Resumen ejecutivo y de auditoría en tiempo real del Día Venta.

### Roles de Usuario Activos
- **Administrador** (Nivel 1): Acceso total a parámetros, configuración de maestros y todos los reportes analíticos.
- **Gerencia** (Nivel 2): Acceso al tablero gerencial y vistas analíticas de control directivo.
- **Supervisión** (Nivel 3): Acceso a reportes operativos segmentados por equipo de preventistas a su cargo.

## 3. Stack Tecnológico Aprobado
- **Backend / Procesamiento**: Python, Pandas, OpenPyXL.
- **Interfaz de Usuario**: Streamlit, AgGrid (`st-aggrid`).
- **Capa de Datos**: SQLite (modo WAL habilitado, archivo `data/matinal.db` con volumetría aproximada de ~350 MB).
- **Fuentes de Entrada (RAW)**: Archivos Excel periódicos (`VTA.xlsx` ~133 MB, `UNIVERSO.xlsx`, `RUTAS.xlsx`, `ALTAS.xlsx`) y un archivo consolidado multi-solapa para la parametrización de maestros y objetivos.

## 4. Estado de la Arquitectura
- **Estado Actual**: Arquitectura modular orientada a submódulos funcionales dentro de `/modules/`. La ingesta procesa y persiste de forma transaccional atómica en SQLite mediante `database.py`, y los reportes aplican filtrado analítico en memoria con Pandas.
- **Arquitectura Objetivo en Tránsito**: 
  RAW ➔ STAGING ➔ CORE ➔ BUSINESS RULES ➔ REPORTES
- **Estado Real de STAGING**: Decisión arquitectónica ya tomada y aprobada institucionalmente, pendiente de implementación formal dentro de la estructura de código. Existen conversaciones y diseños previos conceptualizados, pero falta su despliegue definitivo.

## 5. Principios Arquitectónicos Oficiales
1. **Evolución incremental**.
2. **Prohibida la reescritura total del sistema**.
3. **Streamlit es tecnología aprobada**.
4. **SQLite es tecnología aprobada**.
5. **Pandas es tecnología aprobada**.
6. **Toda mejora debe preservar compatibilidad con los módulos existentes**.
7. **Las reglas de negocio son más importantes que las decisiones técnicas**.
8. **El conocimiento funcional debe quedar documentado institucionalmente**.
9. **La arquitectura objetivo debe alcanzarse progresivamente sin afectar producción**.

## 6. Fuente de Verdad Institucional
La lógica corporativa e inteligencia comercial de MATINAL se sostiene de forma inquebrantable sobre:
- Glosario de Reglas (N1 y N2)
- Día Matinal
- Problema de Cierre
- Ausencias y Reemplazos
- Objetivos Comerciales
- Universos Operativos
- Coberturas
- Estructura Comercial

*Estas definiciones funcionales tienen prioridad absoluta sobre cualquier optimización técnica futura.*

## 7. Evoluciones Planificadas (Roadmap Institucional)
Forman parte oficial del roadmap de evolución del producto, las cuales deben ser contempladas y respetadas durante cualquier rediseño arquitectónico futuro:
- Módulo de Compromisos (Integración con formularios externos de forma desacoplada)
- Check-In físico
- Ejecución Comercial
- Comisiones Dinámicas
- Seguimiento Operativo de Vendedores

## 8. Gaps Técnicos Identificados
- Ausencia temporal de un subsistema de logging estructurado (se depende de excepciones silenciadas).
- Falta de validadores de esquemas preventivos para los archivos Excel de entrada.
- **Ausencia de documentación institucional formalizada** (brecha que estamos cerrando activamente mediante la creación de la carpeta `project_docs/`).