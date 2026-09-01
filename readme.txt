Aquí tienes la versión del texto completamente adaptada y redactada para que puedas copiarla y pegarla al iniciar cualquier nueva sesión. Contiene todos los detalles técnicos, de negocio y de arquitectura actualizados para retomar el desarrollo sin perder contexto:

---

Hola. Vamos a continuar con el desarrollo del **"Sistema Matinal 2.0"** en **Streamlit**. Es un software comercial modular de 3 capas diseñado para optimizar la toma de decisiones matinales de ventas y la gestión de preventistas.

### 📐 Arquitectura del Proyecto (7 Archivos Estables):

1. **`app.py`**: Orquestador principal e interfaz UI con pestañas (`st.tabs`), filtros laterales de supervisores/segmentos, gestión de sesión y formateo dinámico de tablas con `AgGrid` (incluye `autoSizeAllColumns` e `allow_unsafe_jscode=True`).
2. **`config.py`**: Configuración centralizada de nombres de archivos local (`VTA.xlsx`, `UNIVERSO.xlsx`, `PARAMETROS.xlsx`, `RUTAS.xlsx`), URLs remotas y listas de columnas requeridas.
3. **`data_loader.py`**: Capa de extracción optimizada que automatiza la conversión de `VTA.xlsx` a **`VTA.parquet`** para reducir tiempos de carga de 1 minuto a <1 segundo, integrando la caché de Streamlit y lectura remota de ausencias (Google Sheets CSV).
4. **`procesamiento.py`**: Limpieza de ventas crudas (exclusión de comodatos, empleados y vendedor 220), clasificación de segmentos GOLD/SILVER y cálculo operativo cruzado de sustitución de preventistas (ausencias por día o por cliente).
5. **`rep_kilos.py`**: Generación de la matriz vendedor x segmento, proyecciones de kilos, cálculo de días pasados/restantes de ruta, comparativa histórica de ventas de las últimas 2 semanas y cálculo de tendencia y promedio diario necesario.
6. **`rep_ccc.py`**: Reporte de avance de Cobertura CCC por Taxonomía (clientes con $\ge 3$ unidades y $>\$1$ en taxonomías A, B, C y D), determinando la cartera total, el cumplimiento de objetivos y el porcentaje de cobertura por vendedor.
7. **`rep_batalla_ccc.py`**: Panel operativo táctico para filtrar e identificar la cartera de clientes No Compradores (NC) en taxonomías objetivo, agrupados por supervisor, preventista asignado y día de la semana para exportación directa a Excel.

### ⚡ Estado del Proyecto y Optimización Reciente:

* **Carga de Datos Ultrafast**: Implementada persistencia en archivo binario Parquet con invalidación automática por fecha de modificación del archivo original o mediante botón manual de recarga (`st.cache_data.clear()`).
* **Visualización Limpia**: Tablas en `AgGrid` configuradas con auto-ajuste automático al ancho del texto, formato dinámico de miles con comas en enteros y redondeo a 1 decimal para porcentajes y kilos.

Confirmame que leíste y procesaste este contexto completo para indicarte cuál es el siguiente paso exacto en el que vamos a trabajar.