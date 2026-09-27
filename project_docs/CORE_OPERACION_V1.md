CORE_OPERACION V1

OBJETIVO

Determinar quién ejecutó operativamente cada venta.

ENTRADAS

- CORE_VENDEDORES
- AUSENCIAS
- STAGING_VTA

TIPOS DE REEMPLAZO

1) REEMPLAZO TOTAL

Si:
Cliente es NULL

Aplicar:
Fecha + Ausente

Resultado:
Todas las ventas del día pasan al reemplazo.

---------------------------------------------------

2) REEMPLAZO PARCIAL

Si:
Cliente tiene valor

Aplicar:
Fecha + Ausente + Cliente

Resultado:
Sólo ese cliente pasa al reemplazo.

---------------------------------------------------

3) SIN REEMPLAZO

Si no existe coincidencia.

Resultado:
La venta permanece en el vendedor titular.

SALIDA

CodVendedorTitular

CodVendedorOperativo

CodReemplazo

EsReemplazo

TipoReemplazo

SIN_REEMPLAZO
REEMPLAZO_TOTAL
REEMPLAZO_PARCIAL

NombreTitular

SUPTitular

NombreOperativo

SUPOperativo