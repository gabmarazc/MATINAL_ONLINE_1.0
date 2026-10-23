# MATINAL ONLINE | Contratos CORE y BUSINESS RULES

## 1. STAGING público

Funciones activas observadas:

- `obtener_staging_vta()`
- `obtener_staging_clientes()`
- `obtener_staging_rutas()`
- `obtener_staging_ausencias()`
- `obtener_staging_maestros()`

## 2. CORE Operación

### Responsabilidad

Interpretar ventas, calendario, ausencias, reemplazos, titularidad y clasificación temporal.

### Flujo

```text
staging_vta
+ staging_rutas
+ staging_ausencias
+ staging_maestros
→ procesar ausencias y reemplazos
→ calcular ritmo y calendario
→ obtener_core_operacion
```

### Salidas relevantes

- `df_vta_operativa`
- `df_vta_titular`
- `dias_pasados_map`
- `dias_restantes_map`
- `rutas_totales_map`
- `dias_restantes_todo_map`
- `dias_restantes_ajustado_map`
- `total_dias_pasados`
- `total_dias_restantes`

## 3. CORE Ventas Base

Construye la venta institucional reusable desde STAGING. No debe aplicar por sí solo filtros PepsiCo, empleados, vendedor 20, comodatos, CCC ni reemplazos salvo que una decisión posterior lo formalice y valide.

## 4. CORE Vendedores

Salida esperada:

- `CodVendedor`
- `Nombre`
- `SUP`
- `Ajuste_Entrega`
- `Rutas_Ajustadas`

Excluye vendedor 20 por defecto y admite inclusión explícita.

## 5. CORE Clientes

Construye clientes operativos normalizados. En el código observado aplica exclusión de empleados, taxonomías A-D y validaciones de cliente y vendedor.

## 6. CORE Tienda Perfecta

Contrato estable:

- `Cliente_id`
- `CodVendedor`
- `Vendedor`
- `Supervisor`
- `RazonSocial`
- `SubCanal`
- `Taxonomia`
- `Score`
- `Es_TP`

## 7. CORE Cobertura

Construye:

- base de ventas de cobertura;
- cartera enriquecida;
- clientes del Día Matinal;
- agregados por vendedor, cliente y elemento;
- matriz porcentual;
- batalla por cliente;
- detalle de no cubiertos.

## 8. Potencial

### Cliente y Marca

Promedio simple de kilos de los tres meses completos anteriores al período operativo.

### Cliente, Marca y Segmento

Misma ventana con granularidad adicional de segmento y preservación de multisegmentación.

## 9. Business Rules Kilos

Produce matriz por vendedor y segmento con:

- Objetivo
- Arrastre
- Actual
- Operativo
- Compensaciones
- Proyección TODO/AJUSTADO
- Cumplimiento
- Promedio diario
- Media necesaria
- Calendario y rutas

## 10. Business Rules Gross

Contrato paralelo al de Kilos expresado en importe.

## 11. Business Rules TP

Devuelve:

- `detalle_tp`
- `kpis`
- `ranking_vendedor`
- `ranking_subcanal`
- `ranking_taxonomia`
- `tabla_oportunidades`

## 12. Contratos de cambio

- No renombrar columnas sin revisar consumidores.
- Los cambios de firma requieren mapa de impacto.
- Los resultados vacíos deben conservar columnas cuando el contrato vigente lo hace.
- Toda modificación de contrato debe validar sintaxis, imports, columnas, joins, granularidad y conservación de masa.
