# MATINAL ONLINE | Reglas funcionales y dominios

## 1. Jerarquía funcional

1. Reglas institucionales críticas.
2. Reglas operativas.
3. Reglas comerciales.
4. Reglas de dominio.
5. Reglas de presentación.

Una regla inferior no debe contradecir una superior.

## 2. Reglas críticas

### Problema de Cierre

Una venta pertenece al período operativo si `FechaCarga` y `FechaLiquidacion` pertenecen al mismo período operativo, o si `FechaLiquidacion` es nula.

### Empleados

Excluir registros cuyo `Subramo` sea `EMPLEADOS` o `EMPLOYEES`.

### PepsiCo

Cuando existe `Proveedor`, restringir el análisis al portafolio PepsiCo.

### Vendedor 20

El vendedor 20 se excluye por defecto en los flujos comerciales observados, pero el motor Gerencial lo incluye explícitamente. No tratar la exclusión como universal.

### Comodatos y préstamos

Excluir:

- Comodato Devolución
- Comodato Ficticio
- Comodato Ficticio Devolución
- Comodato Préstamo

## 3. Titularidad y reemplazos

- `CodVendedorHistorico`: titular original de la operación.
- `CodVendedorVigente`: titular comercial vigente cuando existe.
- `CodVendedorOperativo`: quien ejecutó la operación.
- Vendedor comodín: código 99, nombre REEMPLAZO.

Cuando `CodVendedorOperativo` difiere del titular histórico, la compensación descuenta del titular y acredita al ejecutor. Debe cumplirse:

```text
SUM descuentos = SUM acreditaciones
```

Participan Arrastre y Actual. No participan Futuro ni Fuera de Periodo.

## 4. Clasificación temporal

- **Arrastre:** carga en mes anterior y entrega en mes operativo.
- **Actual:** carga y entrega en mes operativo.
- **Futuro:** carga en mes operativo y entrega en el siguiente.
- **Fuera de Periodo:** no cumple las condiciones anteriores.

## 5. Día Matinal y calendario

- El Día Matinal define la fotografía operativa vigente.
- Las ventas posteriores no participan de esa fotografía.
- El calendario determina días pasados, días restantes y ritmo.

### Escenarios

- **TODO:** utiliza todas las rutas restantes.
- **AJUSTADO:** descuenta las rutas configuradas en `Rutas_Ajustadas`.

## 6. CCC

- Cliente comprador: `CantBase >= 3` e importe neto positivo.
- La cartera neta considera altas, reactivaciones, inactivaciones y cierres según las reglas activas.
- El objetivo se calcula sobre clientes válidos de la cartera evaluable y según porcentajes configurados por taxonomía.

## 7. MiNegocio

- No Digital: porcentaje <= 0,01.
- Híbrido: porcentaje > 0,01 y < 70.
- Fully Digital: porcentaje >= 70.
- `Minimo_Facturacion_70` representa el volumen adicional requerido para alcanzar el umbral.

## 8. Cobertura

- Marca e Innovación están unificadas en el reporte actual.
- Cliente cubierto: `Total_Cant >= 3`.
- Cliente batalla: menos de 3.
- Semáforo observado: rojo para 0, amarillo para valores entre 0 y 3, verde para 3 o más.

## 9. Objetivos

Los objetivos corporativos no se generan desde el potencial. El potencial distribuye objetivos existentes.

```text
Objetivo Marca
→ Segmento
→ Cliente
```

Solo participan clientes del Universo vigente.

```text
ObjetivoClienteKg
=
ObjetivoMarcaKg
× ParticipacionMarcaSegmento
× ParticipacionClienteDentroSegmento
```

La suma distribuida debe conservar el objetivo de la marca.

## 10. Kilos y Gross

### Kilos

Mide volumen con `PesoKg`. Combina objetivo, operativo, compensaciones, calendario y proyecciones TODO/AJUSTADO.

### Gross

Mide importe y utiliza un contrato paralelo al de Kilos, con disponibilidad e incorporación futura cuando corresponde.

### Gerencial

Utiliza motores propios de Kilos y Gross basados en venta titular. Incluye vendedor 20 y no aplica compensaciones en esas matrices.

## 11. Tienda Perfecta

Se basa en clientes censados, `Score` y `Es_TP`. Produce KPIs, rankings y oportunidades.

## 12. Vespertina

El módulo histórico no es la definición funcional futura. Vespertina debe redefinirse desde cero antes de implementarse.
