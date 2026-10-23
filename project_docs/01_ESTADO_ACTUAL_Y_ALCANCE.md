# MATINAL ONLINE | Estado actual y alcance

**Versión documental:** 4.0  
**Fecha de consolidación:** 23/10/2026  
**Naturaleza:** fotografía técnica consolidada  
**Regla de vigencia:** el código vivo y la evidencia de ejecución prevalecen sobre estados históricos.

## 1. Propósito del sistema

MATINAL ONLINE es una aplicación operativa y comercial desarrollada con Python y Streamlit. Consolida ventas, universo de clientes, rutas, ausencias, altas, Tienda Perfecta y parámetros comerciales para producir seguimiento diario y mensual.

## 2. Stack observado

- Python
- Streamlit
- Pandas
- SQLite
- CSV particionados
- Parquet consolidado
- Excel para determinadas fuentes, cargas de parámetros y exportaciones
- AgGrid para tablas interactivas

No se debe proponer un cambio de stack sin evidencia técnica, impacto cuantificado y aprobación expresa.

## 3. Fuentes y persistencia actuales

- Base principal: `data/matinal.db`
- Base auxiliar observada: `data/datamart.db`
- Ventas particionadas: `data/VTA/*.csv`
- Consolidado de ventas: `data/VTA/VTA_CONSOLIDADO.parquet`
- Fuentes auxiliares: `ALTAS.xlsx`, `RUTAS.xlsx`, `TP.xlsx`, `UNIVERSO.xlsx`

La VTA productiva prioriza los CSV particionados y el Parquet consolidado. Las referencias a un `VTA.xlsx` monolítico se consideran históricas o de compatibilidad mientras el código vivo no demuestre lo contrario.

## 4. Reportes productivos visibles

- Gerencial
- Kilos
- Objetivos de Kilos
- CCC
- Cobertura unificada, con Marca e Innovación
- MiNegocio
- Tienda Perfecta

## 5. Estado Legacy

- `rep_cob_innovacion.py` está en Legacy porque Innovaciones quedó integrada en Cobertura.
- `rep_vespertina.py` está en Legacy. El futuro reporte Vespertina debe diseñarse desde cero con parámetros nuevos.
- El contenido de `modules/Legacy/` no es fuente productiva por defecto.

## 6. Principios de mantenimiento

1. MATINAL ya funciona y se utiliza de forma operativa.
2. Los cambios deben ser mínimos, localizados, reversibles y explicables.
3. No se debe reescribir código estable por preferencia estética.
4. Toda afirmación técnica requiere evidencia.
5. Toda corrección debe preservar contratos y resultados no incluidos en el alcance.

## 7. Jerarquía de verdad

1. Código vivo y evidencia reproducible.
2. Decisiones actuales confirmadas por Gabriel.
3. Documentación técnica vigente.
4. Documentación histórica.
5. Hipótesis explícitamente identificadas.

## 8. Temas abiertos o futuros

- Reconstrucción de Vespertina con nuevos parámetros.
- Reducción progresiva de dependencias híbridas.
- Uso futuro de `universo_hist` para reconstrucción temporal.
- Evaluación específica del rol de `datamart.db` antes de documentarlo como fuente institucional.
