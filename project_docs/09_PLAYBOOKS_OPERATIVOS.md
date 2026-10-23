# MATINAL ONLINE | Playbooks operativos

## Playbook 1: kilos o filas duplicados

### Objetivo

Detectar el primer punto donde aumenta indebidamente la granularidad.

### Secuencia

1. Congelar archivos productivos.
2. Verificar conteos y sumas en la fuente física.
3. Comparar CSV, Parquet y SQLite por período.
4. Revisar claves de negocio y hashes.
5. Auditar joins por cardinalidad antes y después.
6. Identificar el primer módulo donde crecen filas o kilos.
7. Corregir únicamente la causa raíz.
8. Revalidar conteos, sumas y períodos.

## Playbook 2: SQLite correcta, interfaz incorrecta

1. Confirmar el valor en SQLite.
2. Confirmar el valor devuelto por STAGING/CORE.
3. Revisar `st.cache_data`, `st.cache_resource` y `session_state`.
4. Revisar reruns y objetos en memoria.
5. No recargar datos físicos si la divergencia nace en caché.

## Playbook 3: diferencias de objetivos

1. Validar objetivo corporativo de entrada.
2. Identificar población origen.
3. Cruzar población con Universo vigente.
4. Clasificar excluidos y no asignados.
5. Calcular participaciones solo sobre elegibles.
6. Validar suma por Marca, Segmento y Cliente.
7. Verificar conservación de masa.
8. Documentar residuos por datos maestros incompletos.

## Playbook 4: compensaciones por reemplazo

1. Verificar `CodVendedorHistorico`.
2. Verificar `CodVendedorOperativo`.
3. Confirmar ausencia y reemplazo.
4. Limitar a Arrastre y Actual.
5. Calcular descuento y acreditación.
6. Validar que la suma neta sea cero.
7. Separar vendedor 99 de vendedores reales cuando corresponda.

## Playbook 5: TODO frente a AJUSTADO

1. Confirmar que la venta acumulada sea la misma.
2. Verificar `Rutas_Ajustadas` por vendedor.
3. Comparar días restantes TODO y AJUSTADO.
4. Recalcular proyección sin cambiar el operativo acumulado.
5. Validar la selección del escenario en el reporte.

## Playbook 6: filtro de vendedor 20

1. Identificar dominio solicitado.
2. Confirmar si el dominio lo excluye o incluye.
3. Verificar `incluir_vendedor_20` en CORE Vendedores.
4. No trasladar la regla de un reporte a otro sin validación.
5. Comparar resultados con y sin vendedor 20.

## Playbook 7: batalla de Cobertura

1. Confirmar Marca o Innovación.
2. Validar catálogo y claves normalizadas.
3. Deduplicar cartera por la clave funcional correcta.
4. Agregar `CantBase` por cliente y elemento.
5. Aplicar umbral 3.
6. Verificar matriz y detalle de no cubiertos.
7. Comparar totales antes y después del pivote.

## Playbook 8: revisión de código generado por IA

1. Comparar contra el archivo vigente completo.
2. Verificar alcance autorizado.
3. Compilar sintácticamente.
4. Revisar imports y nombres.
5. Comparar firmas y contratos.
6. Identificar cambios laterales.
7. Evaluar performance y cardinalidad.
8. Emitir APROBADO o NO APROBADO con puntuación.

## Playbook 9: alta o modificación de maestro

1. Confirmar la tabla y período de destino.
2. Validar columnas y tipos.
3. Cargar mediante el flujo de Parámetros.
4. Confirmar persistencia en SQLite.
5. Limpiar caché solo si la evidencia lo requiere.
6. Revalidar filtro, padrón y reporte consumidor.

## Regla común

Ningún playbook autoriza modificaciones automáticas. Primero evidencia, luego causa raíz, después cambio mínimo y revalidación.
