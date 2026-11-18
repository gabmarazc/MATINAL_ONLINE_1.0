
Gescom Developers
Guías
Referencia
OpenAPI
MCP
Base de datos

Conectar
Sin conexión: podés leer la referencia y ver ejemplos. Para ejecutar requests contra tu tenant, usá Conectar.

Abrir búsquedaBuscar
Atajo de teclado:Control⌃ k
Introducción
Configuración

Cerrar grupo - Configuración
Alícuotas de IVA
Método HTTP: GET
Empresas
Método HTTP: GET
Etiquetas
Método HTTP: GET
Etiquetas-Categorías
Método HTTP: GET
Provincias
Método HTTP: GET
Inventario

Cerrar grupo - Inventario
Artículos (v1)
Método HTTP: GET
Artículos (v2)
Método HTTP: GET
Artículos (v3)
Método HTTP: GET
Artículos (v4)
Método HTTP: GET
Familias
Método HTTP: GET
Marcas
Método HTTP: GET
Líneas
Método HTTP: GET
Rubros
Método HTTP: GET
Segmento margen
Método HTTP: GET
Stock
Método HTTP: GET
Unidades
Método HTTP: GET
Crear operaciones de stock
Método HTTP: POST
Ventas

Cerrar grupo - Ventas
Set Contacto Cliente
Método HTTP: POST
Lectura (v1)
Método HTTP: GET
Lectura (v2)
Método HTTP: GET
Clientes
Método HTTP: GET
Combos
Método HTTP: GET
Comodatos activos
Método HTTP: GET
Condiciones de pago
Método HTTP: GET
Empleados
Método HTTP: GET
Etapas de venta
Método HTTP: GET
Feriados
Método HTTP: GET
Grupos de fuerza de venta
Método HTTP: GET
Listas de precios
Método HTTP: GET
Motivos de venta
Método HTTP: GET
Motivos de no venta
Método HTTP: GET
Pendientes de facturación
Método HTTP: GET
Precios (v1)
Método HTTP: GET
Precios (v2)
Método HTTP: GET
Rutas de preventa
Método HTTP: GET
Ramos
Método HTTP: GET
Sub Ramos
Método HTTP: GET
Tipos de empleado
Método HTTP: GET
Tipos de comprobante
Método HTTP: GET
Tipos de facturación
Método HTTP: GET
Vendedores
Método HTTP: GET
Exhibidores
Método HTTP: GET
Productos Infaltables
Método HTTP: GET
Tienda Perfecta
Método HTTP: GET
Cliente Impuestos
Método HTTP: GET
Actualización de ubicación de Clientes
Método HTTP: POST
Alta de comprobantes
Método HTTP: POST
Crear listas de precios
Método HTTP: POST
Generación de ventas (v1)
Método HTTP: POST
Generación de ventas (v2)
Método HTTP: POST
Generación de ventas (v3)
Método HTTP: POST
Generación de ventas con comprobante
Método HTTP: POST
Generación de visitas no exitosas
Método HTTP: POST
Modificación de precios
Método HTTP: POST
Reducción de ítems del pedido
Método HTTP: POST
Cambios de ventas (v2)
Método HTTP: GET
Cambios de ventas (v3)
Método HTTP: GET
Avance de ventas
Método HTTP: GET
Compras

Cerrar grupo - Compras
Proveedores
Método HTTP: GET
Compras
Método HTTP: GET
Impuestos de compra
Método HTTP: GET
Distribución

Cerrar grupo - Distribución
Órdenes de Preparación
Método HTTP: GET
Entradas Reparto
Método HTTP: POST
Preparación de ventas
Método HTTP: POST
Repartos (v1)
Método HTTP: GET
Repartos (v2)
Método HTTP: GET
Asignaciones por vehículo
Método HTTP: POST
Cambios de repartos (v1)
Método HTTP: GET
Cambios de repartos (v2)
Método HTTP: GET
Precarga de valores de repartos
Método HTTP: GET
Tesorería

Cerrar grupo - Tesorería
Bancos
Método HTTP: GET
Cajas
Método HTTP: GET
Cuenta corriente clientes (v1)
Método HTTP: GET
Cuenta corriente clientes (v2)
Método HTTP: GET
Cuenta corriente clientes - detalle (v1)
Método HTTP: GET
Cuenta corriente clientes - detalle (v2)
Método HTTP: GET
Cuenta corriente clientes - detalle (v3)
Método HTTP: GET
Cuenta corriente clientes - detalle (v4)
Método HTTP: GET
Monedas
Método HTTP: GET
Tipos de valores
Método HTTP: GET
Generación de cobros e Imputaciones (v1)
Método HTTP: POST
Generación de cobros e Imputaciones (v2)
Método HTTP: POST
Cuenta corriente proveedores
Método HTTP: GET
Cuenta corriente proveedores - detalle
Método HTTP: GET
Cuenta corriente proveedores - pagos
Método HTTP: GET
Pedidos

Cerrar grupo - Pedidos
Crear pedidos
Método HTTP: POST
Lectura de estados
Método HTTP: GET
Lectura de pedidos
Método HTTP: GET
Schemas

Cerrar grupo - Schemas
Error
ResultadoEscritura
Venta
Desarrollado por Scalar
v1.0.0
OpenAPI 3.1.0
API de Gescom Web
Gescom
API externa de Gescom Web. Todas las operaciones responden en https://<sitioweb>/data/cmd/<modulo>/api/v<N>/<endpoint> y requieren un token de Keycloak. Ver las guías de Primeros pasos, Autenticación y Convenciones.

Servidor
Servidor:
https://{sitioweb}
sitioweb
sitio.gescom.online
Sitio del tenant


Autenticación
Obligatorio
Tipo de autenticación seleccionado: bearerAuth
Token de Keycloak obtenido con grant_type=password y client_id=gcw-web-api. Ver la guía de Autenticación.
More
Token Bearer
:
Token
Mostrar contraseña
Bibliotecas cliente
Shell Curl
Configuración ​Copiar enlace
ConfiguraciónOperaciones
get
/data/cmd/config/api/v1/get-alicuotas-iva
get
/data/cmd/config/api/v1/get-empresas
get
/data/cmd/config/api/v1/get-tags
get
/data/cmd/config/api/v1/get-categorias-tag
get
/data/cmd/config/api/v1/get-provincias
Alícuotas de IVA​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve todas las alícuotas de IVA cargadas en el sistema.

No recibe parámetros. No acepta paginación: siempre devuelve el listado completo.

El orden de los resultados no está garantizado.

Respuestas

200
Array de alícuotas. Si no hay ninguna cargada devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/config/api/v1/get-alicuotas-iva
Shell Curl
curl https://sitio.gescom.online/data/cmd/config/api/v1/get-alicuotas-iva \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/config/api/v1/get-alicuotas-iva)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "I21",
    "descripcion": "IVA 21",
    "noGravado": false,
    "porcentaje": 0.21
  },
  {
    "codigo": "I105",
    "descripcion": "Iva 10.5",
    "noGravado": false,
    "porcentaje": 0.105
  }
]

Array de alícuotas. Si no hay ninguna cargada devuelve [].

Empresas​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve las empresas activas cargadas en el sistema, con sus datos fiscales vigentes. Las empresas inactivas no se devuelven.

No recibe parámetros. No acepta paginación: siempre devuelve el listado completo.

El orden de los resultados no está garantizado.

Respuestas

200
Array de empresas. Si no hay ninguna activa devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/config/api/v1/get-empresas
Shell Curl
curl https://sitio.gescom.online/data/cmd/config/api/v1/get-empresas \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/config/api/v1/get-empresas)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "E1",
    "nombre": "Empresa A",
    "razonSocial": "Empresa A S.R.L",
    "documento": "20252525253",
    "direccion": "Manuel Artigas 2020"
  },
  {
    "codigo": "E2",
    "nombre": "Empresa B",
    "razonSocial": "Empresa B S.R.L",
    "documento": "20203678943",
    "direccion": "Perón 2021"
  }
]

Array de empresas. Si no hay ninguna activa devuelve [].

Etiquetas​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve todas las etiquetas (tags) cargadas en el sistema con el nombre de su categoría. Incluye también las etiquetas propias del sistema (de solo lectura o no seleccionables por el usuario).

No recibe parámetros. No acepta paginación: siempre devuelve el listado completo.

Para obtener las etiquetas agrupadas por categoría, ver Etiquetas-Categorías.

El orden de los resultados no está garantizado.

Respuestas

200
Array de etiquetas. Si no hay ninguna devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/config/api/v1/get-tags
Shell Curl
curl https://sitio.gescom.online/data/cmd/config/api/v1/get-tags \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/config/api/v1/get-tags)
Estado:200
Estado:401
Estado:403

[
  {
    "categoria": "Varios",
    "id": 1,
    "nombre": "Especiales",
    "descripcion": "Distingue a la entidad como especial",
    "colorLetra": "#ffff00",
    "colorFondo": "#e040fb"
  }
]

Array de etiquetas. Si no hay ninguna devuelve [].

Etiquetas-Categorías​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve todas las categorías de etiquetas. Opcionalmente incluye, dentro de cada categoría, la lista de sus etiquetas.

No acepta paginación: siempre devuelve el listado completo.

Ejemplo: categorías con sus etiquetas:

GET https://<sitioweb>/data/cmd/config/api/v1/get-categorias-tag?includeTags=true
Ejemplo con includeTags=true:

Sin includeTags=true el campo viene en null: "tags": null.

El orden de las categorías y de las etiquetas dentro de cada categoría no está garantizado.

Parámetros de consulta
includeTags
Tipo:string
Copiar enlace a includeTags
true (no distingue mayúsculas) incluye las etiquetas de cada categoría en el campo tags. Cualquier otro valor, o no enviarlo, devuelve tags en null.

Respuestas

200
Array de categorías. Si no hay ninguna devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/config/api/v1/get-categorias-tag
Shell Curl
curl https://sitio.gescom.online/data/cmd/config/api/v1/get-categorias-tag \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/config/api/v1/get-categorias-tag)
Estado:200
Estado:401
Estado:403

[
  {
    "tags": [
      {
        "id": 2,
        "nombre": "Pepsi"
      }
    ],
    "id": 1,
    "nombre": "Varios",
    "descripcion": "Etiquetas varias",
    "colorLetra": "#fafafa",
    "colorFondo": "#9e9e9e"
  }
]

Array de categorías. Si no hay ninguna devuelve [].

Provincias​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve todas las provincias cargadas en el sistema. Sirve para completar codigoProvincia en las retenciones de Generación de cobros (v2).

No recibe parámetros. No pagina: devuelve la lista completa en una sola respuesta.

GET https://<sitioweb>/data/cmd/config/api/v1/get-provincias
El resultado no tiene un orden definido.

Respuestas

200
Array con todas las provincias. Si no hay ninguna devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/config/api/v1/get-provincias
Shell Curl
curl https://sitio.gescom.online/data/cmd/config/api/v1/get-provincias \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/config/api/v1/get-provincias)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "AR-B",
    "descripcion": "Buenos Aires"
  },
  {
    "codigo": "AR-C",
    "descripcion": "Ciudad Autónoma de Buenos Aires"
  }
]

Array con todas las provincias. Si no hay ninguna devuelve [].

Inventario ​Copiar enlace
InventarioOperaciones
get
/data/cmd/inventario/api/v1/get-articulos
get
/data/cmd/inventario/api/v2/get-articulos
get
/data/cmd/inventario/api/v3/get-articulos
get
/data/cmd/inventario/api/v4/get-articulos
get
/data/cmd/inventario/api/v1/get-familias
get
/data/cmd/inventario/api/v1/get-marcas
get
/data/cmd/inventario/api/v1/get-lineas
get
/data/cmd/inventario/api/v1/get-rubros
get
/data/cmd/inventario/api/v1/get-segmento-margen
get
/data/cmd/inventario/api/v1/get-stock
get
/data/cmd/inventario/api/v1/get-unidades
post
/data/cmd/inventario/api/v1/create-operacion
Artículos (v1)​Copiar enlace

Autenticación requerida

Copiar como Markdown
Versión v1 · Vigente. Formato más antiguo. Se recomienda la v4.

No recibe parámetros: siempre devuelve todos los artículos activos y habilitados para la venta, sin paginar y sin orden definido.

Diferencias con v4:

No tiene codigoSegmentoMargen, codigoEmpresa, factorPeso, factorVolumen, ponderadoPieza, preparacionConsolidada ni trackPiezasEnStock.
Tiene multiplicadorCapacidad (siempre 1, obsoleto).
Cada elemento de unidadesPermitidas tiene solo codigoUnidad, factor y default (lista de texto).
Nota: descuentoMaximo (siempre 100) y comboIteractivo (siempre false) tienen valores fijos.

Todas las versiones
Versión	URL	Estado
v1	/data/cmd/inventario/api/v1/get-articulos	Vigente. Sin parámetros ni paginación. Formato más antiguo.
v2	/data/cmd/inventario/api/v2/get-articulos	Vigente. Agrega filtros por código o id y campos nuevos. Sin paginación.
v3	/data/cmd/inventario/api/v3/get-articulos	Vigente. Igual que v2, pero paginada y ordenada por código.
v4	/data/cmd/inventario/api/v4/get-articulos	Vigente (recomendada). Igual que v3, con más detalle en unidadesPermitidas.
Respuestas

200
Array de artículos.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/inventario/api/v1/get-articulos
Shell Curl
curl https://sitio.gescom.online/data/cmd/inventario/api/v1/get-articulos \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/inventario/api/v1/get-articulos)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "300028468",
    "descripcion": "Toddy Galletas Extra 100gx55 Ne",
    "codigoRubro": "9",
    "precioCosto": 8.07,
    "impuestoInterno": 0,
    "codigoAlicuotaIva": "I21",
    "codigoLinea": "4",
    "codigoMarca": "28",
    "codigoFamilia": "F1",
    "unidadVenta": "Unidades",
    "unidadesBultoVenta": 1,
    "unidadVentaBase": "Unidades",
    "unidadesMinimaVenta": 1,
    "descuentoMaximo": 100,
    "codigoBarras": "",
    "codigoProveedor": "111",
    "tags": [],
    "aptoComodato": false,
    "bloqueado": false,
    "bloqueadoMotivo": null,
    "comboIteractivo": false,
    "incontable": false,
    "unidadesPorBulto": 25,
    "motivoBloqueo": null,
    "unidadesPermitidas": [
      {
        "codigoUnidad": "Unidad",
        "factor": 1,
        "default": [
          "venta"
        ]
      },
      {
        "codigoUnidad": "Pack",
        "factor": 25,
        "default": [
          "carga",
          "compra"
        ]
      }
    ],
    "multiplicadorCapacidad": 1
  }
]

Array de artículos.

Artículos (v2)​Copiar enlace

Autenticación requerida

Copiar como Markdown
Versión v2 · Vigente. Se recomienda la v4.

Acepta los mismos filtros que v4 (codigo, codigos, ids, con la misma prioridad) y devuelve los mismos campos, salvo:

preparacionConsolidada es boolean.
Cada elemento de unidadesPermitidas tiene solo codigoUnidad, factor, default (lista de texto) y codigoBarras.
Nota: v2 no pagina. Acepta pagesize, pagestoskip y pagestotake sin error pero los ignora, y devuelve todos los artículos en una sola respuesta, sin orden definido. Si el maestro es grande, usar v3 o v4.

Todas las versiones
Versión	URL	Estado
v1	/data/cmd/inventario/api/v1/get-articulos	Vigente. Sin parámetros ni paginación. Formato más antiguo.
v2	/data/cmd/inventario/api/v2/get-articulos	Vigente. Agrega filtros por código o id y campos nuevos. Sin paginación.
v3	/data/cmd/inventario/api/v3/get-articulos	Vigente. Igual que v2, pero paginada y ordenada por código.
v4	/data/cmd/inventario/api/v4/get-articulos	Vigente (recomendada). Igual que v3, con más detalle en unidadesPermitidas.
Parámetros de consulta
codigo
Tipo:string
Copiar enlace a codigo
Código exacto de un artículo.

codigos
Tipo:array of string
Copiar enlace a codigos
Códigos de artículo separados por coma (codigos=A1,A2). No dejar espacios después de la coma: el espacio pasa a formar parte del código.

ids
Tipo:array of integer
Copiar enlace a ids
Ids internos de artículo separados por coma. Un valor no numérico responde 400.

Respuestas

200
Array de artículos. Si no hay resultados devuelve [].
application/json

400
Un valor de ids no numérico.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/inventario/api/v2/get-articulos
Shell Curl
curl https://sitio.gescom.online/data/cmd/inventario/api/v2/get-articulos \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/inventario/api/v2/get-articulos)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "codigo": "300028468",
    "descripcion": "Toddy Galletas Extra 100gx55 Ne",
    "codigoRubro": "9",
    "precioCosto": 8.07,
    "impuestoInterno": 0,
    "codigoAlicuotaIva": "I21",
    "codigoLinea": "4",
    "codigoMarca": "28",
    "codigoFamilia": "F1",
    "codigoSegmentoMargen": "S1",
    "unidadVenta": "Unidades",
    "unidadesBultoVenta": 1,
    "unidadVentaBase": "Unidades",
    "unidadesMinimaVenta": 1,
    "descuentoMaximo": 100,
    "factorPeso": 100,
    "factorVolumen": null,
    "codigoBarras": "",
    "codigoProveedor": "111",
    "codigoEmpresa": "1",
    "tags": [],
    "aptoComodato": false,
    "bloqueado": false,
    "bloqueadoMotivo": null,
    "comboIteractivo": false,
    "incontable": false,
    "unidadesPorBulto": 25,
    "motivoBloqueo": null,
    "ponderadoPieza": null,
    "unidadesPermitidas": [
      {
        "codigoUnidad": "Unidad",
        "factor": 1,
        "default": [
          "venta"
        ],
        "codigoBarras": null
      },
      {
        "codigoUnidad": "Pack",
        "factor": 25,
        "default": [
          "carga",
          "compra"
        ],
        "codigoBarras": null
      }
    ],
    "preparacionConsolidada": false,
    "trackPiezasEnStock": false
  }
]

Array de artículos. Si no hay resultados devuelve [].

Marcas​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve todos los marcas cargados en el sistema. Sirve para traducir el campo codigoMarca de Artículos.

No recibe parámetros. No pagina: devuelve la lista completa en una sola respuesta.

GET https://<sitioweb>/data/cmd/inventario/api/v1/get-marcas
El resultado no tiene un orden definido.

Respuestas

200
Array con todos los registros. Si no hay ninguno devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/inventario/api/v1/get-marcas
Shell Curl
curl https://sitio.gescom.online/data/cmd/inventario/api/v1/get-marcas \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/inventario/api/v1/get-marcas)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "M1",
    "descripcion": "Oats"
  },
  {
    "codigo": "M2",
    "descripcion": "Kinder"
  }
]

Array con todos los registros. Si no hay ninguno devuelve [].

Modifica datos
Crear operaciones de stock​Copiar enlace

Autenticación requerida

Copiar como Markdown
Registra movimientos de stock (entradas, salidas y ajustes) sobre un depósito. Todos los ítems del request se procesan en una sola transacción: si uno falla, no se aplica ninguno.

El sistema agrupa los ítems por tipo de operación y genera una operación de stock por cada tipo presente en el request. Los grupos se ejecutan en este orden: primero entrada, después salida y por último ajuste.

Body JSON. Todo el contenido va dentro de la clave data:

Nota: el endpoint no valida motivo, pero el sistema lo exige al guardar la operación. Si falta, la operación se rechaza con un error 406. Enviarlo siempre.

Errores posibles en errores. Las validaciones se hacen en este orden y el endpoint se detiene en la primera que falla:

Code	Causa
400	Falta codigoDeposito o items (mensaje de validación del modelo).
100	items está vacío.
101	Se enviaron más de 100 ítems.
405	codigoDeposito, algún codigoItem u operacion no son válidos ("El campo … tiene un codigo invalido").
430	codigoLote no existe para el codigoItem de ese ítem ("El lote '…' no existe para el item '…'"). En cada ítem se valida después de codigoItem y antes de operacion.
406	Error al aplicar los movimientos. Por ejemplo: el artículo no maneja stock, falta piezas en un artículo que lo requiere, falta o sobra numeroSerie, un ajuste sobre un artículo con número de serie (no está permitido), o falta motivo.
Cuerpo
obligatorio
application/json

data
Tipo:object
obligatorio
{ codigoDeposito, motivo, items }
Copiar enlace a data
Contenedor del request.

Propiedades: 3
Respuestas

200
Siempre que el request llegue al endpoint, incluso si fue rechazado. Revisar resultado.
application/json

400
El body no es un objeto JSON o falta la clave data.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forpost/data/cmd/inventario/api/v1/create-operacion
Shell Curl
curl https://sitio.gescom.online/data/cmd/inventario/api/v1/create-operacion \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "data": {
    "codigoDeposito": "PRI",
    "motivo": "Operación de prueba",
    "items": [
      {
        "operacion": "entrada",
        "codigoItem": "3044448",
        "cantidad": 2
      },
      {
        "operacion": "ajuste",
        "codigoItem": "ART001",
        "cantidad": 400
      },
      {
        "operacion": "salida",
        "codigoItem": "QUESO01",
        "cantidad": 3500,
        "piezas": 2,
        "codigoLote": "L-2025-10"
      }
    ]
  }
}'


Probar solicitud
(post /data/cmd/inventario/api/v1/create-operacion)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "resultado": "A",
  "errores": [],
  "detalle": [
    112,
    113,
    114
  ]
}

Siempre que el request llegue al endpoint, incluso si fue rechazado. Revisar resultado.

Ventas ​Copiar enlace
VentasOperaciones
post
/data/cmd/ventas/api/v1/clientes/set-contacto-principal
get
/data/cmd/ventas/api/v1/get
get
/data/cmd/ventas/api/v2/get
get
/data/cmd/ventas/api/v1/get-clientes
get
/data/cmd/ventas/api/v1/get-combos
get
/data/cmd/ventas/api/v1/get-comodatos-activos
get
/data/cmd/ventas/api/v1/get-condiciones-pago
get
/data/cmd/ventas/api/v1/get-empleados
get
/data/cmd/ventas/api/v1/get-etapas
get
/data/cmd/ventas/api/v1/get-feriados
get
/data/cmd/ventas/api/v1/get-grupos-fuerza-venta
get
/data/cmd/ventas/api/v1/get-listas-precio
get
/data/cmd/ventas/api/v1/get-motivos-venta
get
/data/cmd/ventas/api/v1/get-motivos-no-venta
get
/data/cmd/ventas/api/v1/get-pendientes-facturacion
get
/data/cmd/ventas/api/v1/get-precios
get
/data/cmd/ventas/api/v2/get-precios
get
/data/cmd/ventas/api/v1/get-rutas-preventa
get
/data/cmd/ventas/api/v1/get-ramos
get
/data/cmd/ventas/api/v1/get-subramos
get
/data/cmd/ventas/api/v1/get-tipos-empleado
get
/data/cmd/ventas/api/v1/get-tipos-comprobante
get
/data/cmd/ventas/api/v1/get-tipos-facturacion
get
/data/cmd/ventas/api/v1/get-vendedores
get
/data/cmd/ventas/api/v1/pepsico/get-cliente-exhibidor
get
/data/cmd/ventas/api/v1/pepsico/get-productos-infaltables
get
/data/cmd/ventas/api/v1/pepsico/get-resultado-tienda-perfecta
get
/data/cmd/ventas/api/v1/get-clienteimpuestos
post
/data/cmd/ventas/api/v1/clientes/set-ubicacion
post
/data/cmd/ventas/api/v1/set-comprobante
post
/data/cmd/ventas/precios/abm/new-lista-precio
post
/data/cmd/ventas/api/v1/pedidos/create-bulk
post
/data/cmd/ventas/api/v2/pedidos/create-bulk
post
/data/cmd/ventas/api/v3/pedidos/create-bulk
post
/data/cmd/ventas/api/v3/pedidos/create-invoiced
post
/data/cmd/ventas/api/v1/visitas/create-no-exitosa-bulk
post
/data/cmd/ventas/precios/abm/save-lista-precio
post
/data/cmd/ventas/api/v1/remove-items
get
/data/cmd/ventas/api/v2/cambios
get
/data/cmd/ventas/api/v3/cambios
get
/data/cmd/ventas/api/v1/get-avance-ventas
Modifica datos
Set Contacto Cliente​Copiar enlace

Autenticación requerida

Copiar como Markdown
Actualiza el teléfono y/o el email principal de uno o más clientes. Es una operación de escritura: cada cambio queda registrado en la auditoría del sistema.

Body JSON con la clave contactos (este endpoint no usa la clave data):

Cada contacto se procesa y se guarda por separado: si uno falla, los demás se aplican igual.

Errores posibles en errores:

Código	Mensaje	Causa
100	No se han enviado registros para procesar	contactos está vacío. resultado = R.
101	Se ha superado la cantidad maxima de registros a procesar. El maximo es de 100.	Más de 100 contactos. No se procesa ninguno; resultado = R.
400	Mensaje de validación del campo	Falta codigoCliente, o telefono / email superan el largo máximo. El mensaje no indica el cliente.
405	El campo CodigoCliente tiene un codigo invalido. (código)	No existe un cliente con ese código.
406	No hubo modificaciones para el cliente (código)	Los valores enviados son iguales a los actuales, o no se envió ni telefono ni email.
Los errores 400, 405 y 406 son por contacto: ese contacto no se aplica y cuenta como fallido para calcular resultado.

Nota: la comparación del código de cliente distingue mayúsculas y minúsculas: enviar el código exactamente como figura en el sistema (por ejemplo, tal como lo devuelve la lectura de Clientes). Si no coincide, responde error 405.

Nota: no enviar el mismo cliente dos veces en un request. Los dos elementos se comparan contra los datos que el cliente tenía antes del request, así que ambos se aplican y queda el último.

Cuerpo
obligatorio
application/json

contactos
Tipo:array of object
obligatorio
{ codigoCliente, telefono, email }
Copiar enlace a contactos
Un elemento por cliente a modificar. Entre 1 y 100 elementos.

Propiedades: 3
Respuestas

200
Siempre que el request llegue al endpoint, incluso si hubo errores. El resultado real está en resultado y errores.
application/json

400
El body no es un objeto JSON, falta la clave contactos, o contactos no tiene el formato esperado.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forpost/data/cmd/ventas/api/v1/clientes/set-contacto-principal
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/clientes/set-contacto-principal \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "contactos": [
    {
      "codigoCliente": "1",
      "telefono": "1123334444",
      "email": "info@computacionidea.com.ar"
    },
    {
      "codigoCliente": "2594",
      "email": "info@computacionidea.com.ar"
    },
    {
      "codigoCliente": "5653",
      "telefono": "153183933 - 4925912"
    }
  ]
}'


Probar solicitud
(post /data/cmd/ventas/api/v1/clientes/set-contacto-principal)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "resultado": "P",
  "errores": [
    {
      "code": 405,
      "msg": "El campo CodigoCliente tiene un codigo invalido. (2594)"
    },
    {
      "code": 406,
      "msg": "No hubo modificaciones para el cliente (5653)"
    }
  ],
  "detalle": []
}

Siempre que el request llegue al endpoint, incluso si hubo errores. El resultado real está en resultado y errores.

Lectura (v1)​Copiar enlace

Autenticación requerida

Copiar como Markdown
Versión v1 · Vigente. Se recomienda la v2.

Recibe los mismos parámetros que v2, aplica los mismos filtros, la misma paginación y los mismos límites, y responde con la misma estructura. Ver la v2 para el detalle de cada parámetro y campo.

Nota: internamente v1 arma los mismos objetos que v2, por eso su respuesta también trae los campos agregados en v2. No conviene depender de eso: si una integración necesita esos campos, debe usar v2.

Todas las versiones
Versión	URL	Estado
v1	/data/cmd/ventas/api/v1/get	Vigente. Mismos parámetros y, según el código, la misma respuesta que v2 (ver nota).
v2	/data/cmd/ventas/api/v2/get	Vigente (recomendada).
Parámetros de consulta
fechadesde
Tipo:string
Copiar enlace a fechadesde
Ventas con fecha de carga (fechaPedido) mayor o igual a este valor.

fechahasta
Tipo:string
Copiar enlace a fechahasta
Ventas con fecha de carga menor o igual a este valor (ver Convenciones → Fechas).

fechamodificaciondesde
Tipo:string
Copiar enlace a fechamodificaciondesde
Ventas modificadas en esta fecha o después. Útil para sincronizaciones incrementales.

ids
Tipo:array of integer
Copiar enlace a ids
Ids de venta.

repartos
Tipo:array of integer
Copiar enlace a repartos
Números de reparto (codigo del reparto). Devuelve las ventas asignadas a esos repartos (ver nota).

etapas
Tipo:array of string
Copiar enlace a etapas
Etapas de la venta: TipoVenta, Precios, Promociones, Descuentos, LineaCredito, ReservaStock, Impuestos, Facturacion, AsignacionDeuda, Entrega. No distingue mayúsculas. Los valores no reconocidos se ignoran; si ninguno es válido no se filtra por etapa.

empresas
Tipo:array of string
Copiar enlace a empresas
Códigos de empresa.

clientes
Tipo:array of string
Copiar enlace a clientes
Códigos de cliente.

sedes
Tipo:array of string
Copiar enlace a sedes
Códigos de sede.

vendedores
Tipo:array of string
Copiar enlace a vendedores
Códigos de vendedor. Las ventas sin vendedor asignado no se devuelven cuando se usa este filtro. No tiene el límite de 100 valores de las demás listas.

cerrada
Tipo:boolean
Copiar enlace a cerrada
true o false. Una venta cerrada tiene comprobantes generados que fueron registrados fiscalmente.

pagesize
Tipo:integer
mín.:  
1
máx.:  
500
Predeterminado
Copiar enlace a pagesize
Registros por página. Default y máximo: 500.

pagestoskip
Tipo:integer
mín.:  
0
Predeterminado
Copiar enlace a pagestoskip
Páginas a saltear. Default 0.

pagestotake
Tipo:integer
mín.:  
1
máx.:  
2
Predeterminado
Copiar enlace a pagestotake
Páginas a traer. Default 1, máximo 2.

Respuestas

200
Array de ventas. Si no hay resultados devuelve [].
application/json

400
pagesize > 500, pagestotake > 2, una lista con más de 100 valores (salvo vendedores), o un valor de ids o repartos no numérico.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get
Shell Curl
curl 'https://sitio.gescom.online/data/cmd/ventas/api/v1/get?pagesize=500&pagestoskip=0&pagestotake=1' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "id": 2,
    "estado": "Pendiente",
    "etapa": "Facturacion",
    "etapaNota": null,
    "requiereAutorizacion": false,
    "cerrada": false,
    "origen": "gcw",
    "ventaReferenciada": {
      "id": 1,
      "numeroComprobante": 1,
      "origen": "gcw",
      "identificador": null,
      "codigoEmpresa": "E1",
      "codigoPuntoVenta": 3,
      "codigoTipoComprobante": "FAC-A"
    },
    "numeroComprobante": 2,
    "motivo": "Sin Dinero",
    "items": [
      {
        "orden": 0,
        "ventaItemID": 15,
        "itemID": 812,
        "codigoItem": "300030783",
        "codigoAlicuotaIva": "I21",
        "codigoListaPrecio": "1",
        "codigoDeposito": "PRI",
        "codigoLote": null,
        "codigoCombo": null,
        "codigoComboComp": null,
        "cantidad": 123,
        "codigoUnidad": "Unidad",
        "unidadFactor": 1,
        "piezas": null,
        "precioUnitario": 11.54,
        "precioUnitarioIva": 2.4234,
        "precioUnitarioTotal": 13.9634,
        "precioCosto": 8.1,
        "descuento": 0.1744,
        "descuentoNeto": 2.012576,
        "descuentoFinal": 2.43521696,
        "descuentos": [
          {
            "descuentoFuenteId": null,
            "descuento": 0.1744,
            "descuentoDetalle": null,
            "otorgadoPorPromocion": true,
            "promocionId": 44,
            "comboComponenteId": null,
            "propiedades": {}
          }
        ],
        "numeroSerie": null,
        "estadoPesaje": 0,
        "importeNeto": 1171.873152,
        "importeExento": 0,
        "importeConc": 0,
        "importeIva": 246.09336192,
        "importeTributos": 15129,
        "importeTotal": 16546.96651392,
        "comentario": null,
        "propiedades": {}
      }
    ],
    "importeNeto": 1171.873152,
    "importeExento": 0,
    "importeConc": 0,
    "importeIva": 246.09336192,
    "importeTributos": 15129,
    "importeTotal": 16546.96651392,
    "codigoReparto": 1,
    "codigoChofer": "21",
    "comprobantePrincipal": null,
    "esCredito": true,
    "esSinCargo": false,
    "tags": [],
    "propiedades": {},
    "identificador": null,
    "codigoTipoVenta": "DEV-RE",
    "codigoCliente": "4517",
    "codigoVendedor": "1",
    "codigoRuta": "99",
    "codigoEmpresa": "E1",
    "codigoPuntoVenta": 3,
    "codigoSede": "1",
    "codigoCondicionPago": "15D",
    "codigoMotivoCambio": "2",
    "fechaPedido": "2023-03-10T12:15:45-03:00",
    "fechaEntrega": null,
    "observaciones": null,
    "observacionesInternas": null,
    "descuentoGlobal": 0.14,
    "combos": [],
    "ventaDirecta": false,
    "metodoEntrega": 0,
    "loteId": null
  }
]

Array de ventas. Si no hay resultados devuelve [].

Recomendada
Lectura (v2)​Copiar enlace

Autenticación requerida

Copiar como Markdown
Versión v2 · Vigente (recomendada).

Devuelve las ventas (pedidos, devoluciones, cambios, etc.) con sus ítems, importes calculados, comprobante principal y reparto asignado. Las ventas se devuelven ordenadas por fecha de creación (de la más antigua a la más nueva).

Las dos versiones ejecutan exactamente la misma consulta y aceptan los mismos parámetros. La v2 declara formalmente los campos origen, comprobantePrincipal, esCredito, esSinCargo, propiedades, los datos extendidos de ventaReferenciada y, en cada ítem, itemID, descuentos y precioCosto. Usar v2 en integraciones nuevas.

Nota: en el código, v1 construye internamente los mismos objetos que v2, por lo que su respuesta también incluye los campos de v2. No conviene depender de eso: si se necesitan esos campos, usar v2.

Todos los parámetros son opcionales. Sin filtros devuelve las primeras 500 ventas.

Cada lista admite hasta 100 valores; con más responde 400. La excepción es vendedores, que no tiene ese límite. Los códigos inexistentes no dan error: simplemente no devuelven resultados.

Nota: repartos se convierte internamente en la lista de ids de las ventas de esos repartos y se suma a ids: si se envían los dos, se devuelven las ventas de los ids indicados más las de los repartos (no la intersección). Además, el límite de 100 se aplica a esa lista combinada, así que un reparto con más de 100 ventas responde 400 ("La cantidad máxima de elementos en la lista Ids es 100"). Si los repartos no existen o no tienen ventas, la respuesta es [].

Ejemplo: ventas cargadas en marzo de 2023 que están en las etapas Impuestos o Facturación:

GET https://<sitioweb>/data/cmd/ventas/api/v2/get?fechadesde=2023-03-01&fechahasta=2023-04-01&etapas=impuestos,facturacion
Todas las versiones
Versión	URL	Estado
v1	/data/cmd/ventas/api/v1/get	Vigente. Mismos parámetros y, según el código, la misma respuesta que v2 (ver nota).
v2	/data/cmd/ventas/api/v2/get	Vigente (recomendada).
Parámetros de consulta
fechadesde
Tipo:string
Copiar enlace a fechadesde
Ventas con fecha de carga (fechaPedido) mayor o igual a este valor.

fechahasta
Tipo:string
Copiar enlace a fechahasta
Ventas con fecha de carga menor o igual a este valor (ver Convenciones → Fechas).

fechamodificaciondesde
Tipo:string
Copiar enlace a fechamodificaciondesde
Ventas modificadas en esta fecha o después. Útil para sincronizaciones incrementales.

ids
Tipo:array of integer
Copiar enlace a ids
Ids de venta.

repartos
Tipo:array of integer
Copiar enlace a repartos
Números de reparto (codigo del reparto). Devuelve las ventas asignadas a esos repartos (ver nota).

etapas
Tipo:array of string
Copiar enlace a etapas
Etapas de la venta: TipoVenta, Precios, Promociones, Descuentos, LineaCredito, ReservaStock, Impuestos, Facturacion, AsignacionDeuda, Entrega. No distingue mayúsculas. Los valores no reconocidos se ignoran; si ninguno es válido no se filtra por etapa.

empresas
Tipo:array of string
Copiar enlace a empresas
Códigos de empresa.

clientes
Tipo:array of string
Copiar enlace a clientes
Códigos de cliente.

sedes
Tipo:array of string
Copiar enlace a sedes
Códigos de sede.

vendedores
Tipo:array of string
Copiar enlace a vendedores
Códigos de vendedor. Las ventas sin vendedor asignado no se devuelven cuando se usa este filtro. No tiene el límite de 100 valores de las demás listas.

cerrada
Tipo:boolean
Copiar enlace a cerrada
true o false. Una venta cerrada tiene comprobantes generados que fueron registrados fiscalmente.

pagesize
Tipo:integer
mín.:  
1
máx.:  
500
Predeterminado
Copiar enlace a pagesize
Registros por página. Default y máximo: 500.

pagestoskip
Tipo:integer
mín.:  
0
Predeterminado
Copiar enlace a pagestoskip
Páginas a saltear. Default 0.

pagestotake
Tipo:integer
mín.:  
1
máx.:  
2
Predeterminado
Copiar enlace a pagestotake
Páginas a traer. Default 1, máximo 2.

Respuestas

200
Array de ventas. Si no hay resultados devuelve [].
application/json

400
pagesize > 500, pagestotake > 2, una lista con más de 100 valores (salvo vendedores), o un valor de ids o repartos no numérico.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v2/get
Shell Curl
curl 'https://sitio.gescom.online/data/cmd/ventas/api/v2/get?pagesize=500&pagestoskip=0&pagestotake=1' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v2/get)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "id": 2,
    "estado": "Pendiente",
    "etapa": "Facturacion",
    "etapaNota": null,
    "requiereAutorizacion": false,
    "cerrada": false,
    "origen": "gcw",
    "ventaReferenciada": {
      "id": 1,
      "numeroComprobante": 1,
      "origen": "gcw",
      "identificador": null,
      "codigoEmpresa": "E1",
      "codigoPuntoVenta": 3,
      "codigoTipoComprobante": "FAC-A"
    },
    "numeroComprobante": 2,
    "motivo": "Sin Dinero",
    "items": [
      {
        "orden": 0,
        "ventaItemID": 15,
        "itemID": 812,
        "codigoItem": "300030783",
        "codigoAlicuotaIva": "I21",
        "codigoListaPrecio": "1",
        "codigoDeposito": "PRI",
        "codigoLote": null,
        "codigoCombo": null,
        "codigoComboComp": null,
        "cantidad": 123,
        "codigoUnidad": "Unidad",
        "unidadFactor": 1,
        "piezas": null,
        "precioUnitario": 11.54,
        "precioUnitarioIva": 2.4234,
        "precioUnitarioTotal": 13.9634,
        "precioCosto": 8.1,
        "descuento": 0.1744,
        "descuentoNeto": 2.012576,
        "descuentoFinal": 2.43521696,
        "descuentos": [
          {
            "descuentoFuenteId": null,
            "descuento": 0.1744,
            "descuentoDetalle": null,
            "otorgadoPorPromocion": true,
            "promocionId": 44,
            "comboComponenteId": null,
            "propiedades": {}
          }
        ],
        "numeroSerie": null,
        "estadoPesaje": 0,
        "importeNeto": 1171.873152,
        "importeExento": 0,
        "importeConc": 0,
        "importeIva": 246.09336192,
        "importeTributos": 15129,
        "importeTotal": 16546.96651392,
        "comentario": null,
        "propiedades": {}
      }
    ],
    "importeNeto": 1171.873152,
    "importeExento": 0,
    "importeConc": 0,
    "importeIva": 246.09336192,
    "importeTributos": 15129,
    "importeTotal": 16546.96651392,
    "codigoReparto": 1,
    "codigoChofer": "21",
    "comprobantePrincipal": null,
    "esCredito": true,
    "esSinCargo": false,
    "tags": [],
    "propiedades": {},
    "identificador": null,
    "codigoTipoVenta": "DEV-RE",
    "codigoCliente": "4517",
    "codigoVendedor": "1",
    "codigoRuta": "99",
    "codigoEmpresa": "E1",
    "codigoPuntoVenta": 3,
    "codigoSede": "1",
    "codigoCondicionPago": "15D",
    "codigoMotivoCambio": "2",
    "fechaPedido": "2023-03-10T12:15:45-03:00",
    "fechaEntrega": null,
    "observaciones": null,
    "observacionesInternas": null,
    "descuentoGlobal": 0.14,
    "combos": [],
    "ventaDirecta": false,
    "metodoEntrega": 0,
    "loteId": null
  }
]

Array de ventas. Si no hay resultados devuelve [].

Clientes​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve los clientes con sus datos comerciales, fiscales, de entrega y sus rutas de preventa.

Todos los parámetros son opcionales. No tiene paginación: sin filtros devuelve todos los clientes activos.

Solo se aplica uno de los filtros codigo, codigos o ids, en ese orden de prioridad. Si no se envía ninguno, se devuelven solo los clientes activos. Si se envía alguno, se devuelven los clientes indicados aunque estén inactivos.

Ejemplo:

GET https://<sitioweb>/data/cmd/ventas/api/v1/get-clientes?codigos=4,4517
Parámetros de consulta
codigo
Tipo:string
Copiar enlace a codigo
Código de un cliente. Devuelve un array con ese cliente o vacío si no existe.

codigos
Tipo:array of string
Copiar enlace a codigos
Códigos de cliente separados por coma. Se ignora si se envió codigo.

ids
Tipo:array of integer
Copiar enlace a ids
Ids internos de cliente. Se ignora si se envió codigo o codigos.

empleadoid
Tipo:integer
Copiar enlace a empleadoid
Id interno (no el código) de un vendedor. Devuelve solo los clientes que tienen una ruta de preventa de ese vendedor, y en rutasPreventa solo esas rutas. Se combina con cualquiera de los filtros anteriores.

Respuestas

200
Array de clientes. Si no hay resultados devuelve [].
application/json

400
Un valor de ids no numérico.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-clientes
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-clientes \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-clientes)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "codigo": "4",
    "nombre": "Elito Revé y su Charangón",
    "razonSocial": "Elito Revé y su Charangón",
    "direccionEntrega": "Marco Polo 523",
    "telefono": null,
    "codigoEmpresa": "E1",
    "codigoListaPrecio": "1",
    "codigoRamo": "1",
    "codigoSubramo": "SB123",
    "codigoSede": "1",
    "codigoDeposito": null,
    "codigoSegmento": "P",
    "localidad": "Villa Gobernador Gálvez",
    "codigoTipoDocumento": "TD123",
    "codigoCondicionIva": "CI123",
    "descuentoGlobal": 0,
    "email": "elitoreve@gmail.com",
    "provincia": "Santa Fe",
    "codigoCondicionPago": "15D",
    "codigoPostal": null,
    "rutasPreventa": [
      {
        "codigoRuta": "CR123",
        "codigoVendedor": "CV123",
        "lunes": true,
        "martes": false,
        "miercoles": true,
        "jueves": false,
        "viernes": false,
        "sabado": false,
        "domingo": false,
        "frecuencia": "Semanal",
        "orden": 0,
        "fechaPrimeraVisita": null,
        "gruposFuerzaVenta": []
      }
    ],
    "nroDocumento": "12345678",
    "coordenadas": {
      "latitud": -33.0125679259,
      "longitud": -60.6397742791
    },
    "contacto": "Elito Revé",
    "esFoco": false,
    "percepcionIB": 0,
    "margenMaximo": null,
    "topeVenta": null,
    "ordenVisita": 0,
    "tags": [],
    "minimoDeVenta": {
      "importe": 0,
      "codigoMoneda": "ARS"
    },
    "demoraEntregaDias": 1,
    "comentario": null,
    "notas": null,
    "listasEspeciales": [],
    "propiedades": {},
    "topeSaldoDinero": null,
    "topeSaldoDineroMoneda": "ARS",
    "topeSaldoDineroFactor": 1,
    "topeSaldoDias": null,
    "topeSaldoBoletas": null
  }
]

Array de clientes. Si no hay resultados devuelve [].

Combos​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve los combos activos con sus componentes y las condiciones de aplicación.

No recibe parámetros. No tiene paginación.

Respuestas

200
Array de combos. Si no hay combos activos devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-combos
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-combos \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-combos)
Estado:200
Estado:401
Estado:403

[
  {
    "id": 12,
    "codigo": "400010007",
    "descripcion": "Global SB Auto 10X1",
    "componentes": [
      {
        "id": 1,
        "codigo": "1",
        "nombre": "VENTAS SM",
        "cantidad": 10,
        "descuento": 0,
        "items": [
          "300052822",
          "300043102",
          "300052820"
        ]
      },
      {
        "id": 2,
        "codigo": "2",
        "nombre": "VENTAS SM",
        "cantidad": 1,
        "descuento": 1,
        "items": [
          "300043017",
          "300046319"
        ]
      }
    ],
    "condicionJson": "{\"mainConditionCode\":1,\"conditions\":[{\"code\":1,\"type\":\"All\",\"description\":null,\"configuration\":{\"conditionCodes\":[1,2]}},{\"code\":2,\"type\":\"Ramo\",\"description\":null,\"configuration\":{\"ramoCodigos\":[\"pepsico-1\",\"pepsico-5\"]}}]}"
  }
]

Array de combos. Si no hay combos activos devuelve [].

Comodatos activos​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve, agrupados por cliente, los artículos entregados en comodato que el cliente todavía no devolvió, con la venta en la que se entregó cada uno.

Cómo se calcula:

Se toman solo ventas cerradas cuyo tipo de venta es COM-P, COM-F, COM-PD o COM-FD, o cuya descripción contiene la palabra "Comodato".
Se consideran solo los ítems de artículos que manejan stock y están marcados como aptos para comodato.
Son devoluciones las ventas de tipo COM-PD y COM-FD y las de cualquier tipo de venta de crédito. El resto son entregas.
Los movimientos se agrupan por cliente y artículo, no por número de serie. El número de serie se normaliza (sin espacios en los extremos y en mayúsculas); si queda vacío, el ítem se considera sin serie.
Una devolución con número de serie solo descuenta de las entregas que tienen esa misma serie. Una devolución sin número de serie descuenta de cualquier entrega del artículo, tenga o no serie.
Las entregas se recorren de la más nueva a la más vieja (por fecha de colocación y, a igual fecha, por número de comprobante). A cada una se le descuentan primero las devoluciones de su serie y, si todavía le queda saldo, las devoluciones sin serie.
Como se descuenta primero de las entregas más nuevas, quedan vigentes las más antiguas. Cada comodato informa la venta de esa entrega y la cantidad que le quedó; las entregas que quedan en 0 no aparecen.
Las devoluciones que sobran (por ejemplo, de una serie que ninguna entrega tiene) no generan saldo negativo: se ignoran.
No tiene paginación. Ejemplo:

GET https://<sitioweb>/data/cmd/ventas/api/v1/get-comodatos-activos?cliente=4517,4
Nota: el saldo se calcula con las cantidades tal como se cargaron en cada venta, sin convertir unidades.

Parámetros de consulta
cliente
Tipo:array of string
Copiar enlace a cliente
Códigos de cliente separados por coma. Sin este parámetro se devuelven los comodatos de todos los clientes.

Respuestas

200
Array con un elemento por cliente que tiene comodatos vigentes. Si no hay, devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-comodatos-activos
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-comodatos-activos \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-comodatos-activos)
Estado:200
Estado:401
Estado:403

[
  {
    "codigoCliente": "4517",
    "comodatos": [
      {
        "ventaId": 3021,
        "codigoEmpresa": "E1",
        "numeroComprobante": 1234,
        "codigoVendedor": "V123",
        "comprobante": "E1 REM 0003-00001234",
        "fechaColocacion": "2025-02-14T00:00:00-03:00",
        "items": [
          {
            "codigoItem": "HEL-01",
            "numeroSerie": "SN-99812",
            "cantidad": 1
          }
        ]
      }
    ]
  }
]

Array con un elemento por cliente que tiene comodatos vigentes. Si no hay, devuelve [].

Condiciones de pago​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve todas las condiciones de pago configuradas.

No recibe parámetros. No tiene paginación.

Respuestas

200
Array de condiciones de pago.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-condiciones-pago
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-condiciones-pago \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-condiciones-pago)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "CP15D",
    "descripcion": "15 días fecha de factura",
    "dias": 15,
    "cuotas": 1
  },
  {
    "codigo": "CON",
    "descripcion": "Contado",
    "dias": 0,
    "cuotas": 1
  }
]

Array de condiciones de pago.

Empleados​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve los empleados activos con sus tipos (vendedor, chofer, etc.).

No tiene paginación. Ejemplo para obtener solo los choferes:

GET https://<sitioweb>/data/cmd/ventas/api/v1/get-empleados?tipo=CHF
Parámetros de consulta
tipo
Tipo:string
Copiar enlace a tipo
Código de un tipo de empleado (ver Tipos de empleado). Devuelve solo los empleados que tienen ese tipo. Acepta un único código.

Respuestas

200
Array de empleados. Si no hay resultados devuelve [].
application/json

400
El tipo no existe. Mensaje: "El tipo de empleado indicado no es válido".
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-empleados
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-empleados \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-empleados)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "codigo": "V123",
    "nombre": "Eliades Ochoa",
    "tipos": [
      "VEN"
    ],
    "codigoSuperior": "V001"
  },
  {
    "codigo": "V001",
    "nombre": "Benny Moré",
    "tipos": [
      "VEN",
      "CHF"
    ],
    "codigoSuperior": null
  }
]

Array de empleados. Si no hay resultados devuelve [].

Etapas de venta​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve las etapas por las que pasa una venta, en el orden en que se procesan. Son valores fijos del sistema (no dependen de la configuración): sirven para interpretar el campo etapa de la lectura de ventas y para el filtro etapas.

No recibe parámetros.

Significado de cada etapa:

Etapa	Descripción
TipoVenta	Definir tipo de venta
Precios	Aplicar precios
Promociones	Aplicar promociones
Descuentos	Aplicar descuentos
LineaCredito	Validar línea de crédito
ReservaStock	Reservar stock
Impuestos	Calcular impuestos
Facturacion	Generar facturación
AsignacionDeuda	Asignar deuda
Entrega	Gestionar entrega
Respuestas

200
Array de etapas.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-etapas
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-etapas \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-etapas)
Estado:200
Estado:401
Estado:403

[
  {
    "etapa": "TipoVenta",
    "orden": 1
  },
  {
    "etapa": "Precios",
    "orden": 2
  },
  {
    "etapa": "Promociones",
    "orden": 3
  },
  {
    "etapa": "Descuentos",
    "orden": 4
  },
  {
    "etapa": "LineaCredito",
    "orden": 5
  },
  {
    "etapa": "ReservaStock",
    "orden": 6
  },
  {
    "etapa": "Impuestos",
    "orden": 7
  },
  {
    "etapa": "Facturacion",
    "orden": 8
  },
  {
    "etapa": "AsignacionDeuda",
    "orden": 9
  },
  {
    "etapa": "Entrega",
    "orden": 10
  }
]

Array de etapas.

Recomendada
Precios (v2)​Copiar enlace

Autenticación requerida

Copiar como Markdown
Versión v2 · Vigente (recomendada). codigoUnidad es el nombre de la unidad y codigoMoneda trae la moneda del precio.

Devuelve los precios vigentes de los artículos activos, agrupados por artículo y, dentro de cada artículo, por lista de precios. Cada lista trae un precio por unidad de venta (unidad + factor).

Las dos versiones aceptan los mismos parámetros, aplican los mismos filtros y devuelven los mismos campos. Solo cambian los valores de codigoUnidad y codigoMoneda.

Todos los parámetros son opcionales. No tiene paginación: sin filtros devuelve todos los precios vigentes de todos los artículos activos en una sola respuesta.

Ejemplo: precios que cambiaron desde el 1 de marzo de 2025, solo en la unidad de venta por defecto:

GET https://<sitioweb>/data/cmd/ventas/api/v2/get-precios?since=2025-03-01&defaultventaonly=true
Ejemplo de respuesta v2:

En v1 cambian dos valores: codigoUnidad trae el id interno de la unidad como texto (por ejemplo "3" en lugar de "Unidad") y codigoMoneda siempre es null.

Solo se incluyen artículos activos y precios vigentes. Un artículo sin ningún precio vigente no aparece.
No se filtra por el estado de la lista de precios: pueden venir precios de listas inactivas.
porcentajeAlicuotaIva e impuestoInterno son datos del artículo, no del precio: se repiten iguales en todas las listas y unidades.
Nota: since solo devuelve los precios cargados o modificados desde esa fecha. Los precios dados de baja y los artículos desactivados no aparecen en la respuesta, así que una sincronización incremental con since no detecta bajas. Conviene hacer una lectura completa (sin since) cada tanto.

Todas las versiones
Versión	URL	Estado
v1	/data/cmd/ventas/api/v1/get-precios	Vigente. codigoUnidad es el id interno de la unidad y codigoMoneda siempre es null.
v2	/data/cmd/ventas/api/v2/get-precios	Vigente (recomendada). codigoUnidad es el nombre de la unidad y codigoMoneda trae la moneda del precio.
Parámetros de consulta
since
Tipo:string
Copiar enlace a since
Solo precios que entraron en vigencia en esta fecha o después (fecha de inicio de validez mayor o igual al valor). Sirve para traer solo los precios que cambiaron.

defaultventaonly
Tipo:boolean
Copiar enlace a defaultventaonly
true: solo el precio de la unidad de venta por defecto de cada artículo. Default false (todas las unidades).

Respuestas

200
Array de artículos con sus precios. Si no hay resultados devuelve [].
application/json

400
since con formato de fecha inválido, o defaultventaonly con un valor que no es booleano.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v2/get-precios
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v2/get-precios \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v2/get-precios)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "codigoItem": "ART1",
    "listas": [
      {
        "codigoListaPrecio": "1",
        "precios": [
          {
            "codigoUnidad": "Unidad",
            "factor": 1,
            "precioNeto": 2.35,
            "codigoMoneda": "ARS",
            "defaultVenta": true,
            "porcentajeAlicuotaIva": 0.21,
            "impuestoInterno": 0
          },
          {
            "codigoUnidad": "Pack",
            "factor": 6,
            "precioNeto": 13.5,
            "codigoMoneda": "ARS",
            "defaultVenta": false,
            "porcentajeAlicuotaIva": 0.21,
            "impuestoInterno": 0
          }
        ]
      },
      {
        "codigoListaPrecio": "2",
        "precios": [
          {
            "codigoUnidad": "Unidad",
            "factor": 1,
            "precioNeto": 3.45,
            "codigoMoneda": "ARS",
            "defaultVenta": true,
            "porcentajeAlicuotaIva": 0.21,
            "impuestoInterno": 0
          }
        ]
      }
    ]
  }
]

Array de artículos con sus precios. Si no hay resultados devuelve [].

Rutas de preventa​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve las rutas de preventa activas, con el vendedor asignado y los días y la frecuencia de visita. Las rutas inactivas no se devuelven.

No recibe parámetros. No tiene paginación: devuelve todas las rutas activas.

Los días y la frecuencia de visita de cada cliente dentro de una ruta se obtienen en la lectura de Clientes (campo rutasPreventa).

Respuestas

200
Array de rutas. Si no hay ninguna activa devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-rutas-preventa
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-rutas-preventa \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-rutas-preventa)
Estado:200
Estado:401
Estado:403

[
  {
    "codigoVendedor": "1",
    "lunes": true,
    "martes": false,
    "miercoles": false,
    "jueves": true,
    "viernes": false,
    "sabado": false,
    "domingo": false,
    "frecuencia": 0,
    "codigo": "11",
    "descripcion": "Grupo Niche"
  },
  {
    "codigoVendedor": "1",
    "lunes": false,
    "martes": true,
    "miercoles": false,
    "jueves": false,
    "viernes": true,
    "sabado": false,
    "domingo": false,
    "frecuencia": 0,
    "codigo": "99",
    "descripcion": "Buena vista social club"
  }
]

Array de rutas. Si no hay ninguna activa devuelve [].

Ramos​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve todos los ramos (rubros de cliente) con sus sub ramos. Para obtener solo la lista de sub ramos ver Sub Ramos.

No recibe parámetros. No tiene paginación: devuelve todos los ramos.

Nota: cuando un ramo no tiene sub ramos, subRamos no viene vacío: trae un único elemento con codigo y descripcion en null (como el ramo SR001 del ejemplo). Descartar los elementos con codigo null.

Respuestas

200
Array de ramos. Si no hay ninguno devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-ramos
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-ramos \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-ramos)
Estado:200
Estado:401
Estado:403

[
  {
    "subRamos": [
      {
        "codigo": "112",
        "descripcion": "Cadena Regional"
      },
      {
        "codigo": "111",
        "descripcion": "Autoservicio Tradicional"
      }
    ],
    "codigo": "SR123",
    "descripcion": "Autoservicio"
  },
  {
    "subRamos": [
      {
        "codigo": null,
        "descripcion": null
      }
    ],
    "codigo": "SR001",
    "descripcion": "Vinoteca"
  }
]

Array de ramos. Si no hay ninguno devuelve [].

Sub Ramos​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve todos los sub ramos, sin indicar a qué ramo pertenecen. Para obtenerlos agrupados por ramo usar Ramos.

No recibe parámetros. No tiene paginación: devuelve todos los sub ramos.

Respuestas

200
Array de sub ramos. Si no hay ninguno devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-subramos
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-subramos \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-subramos)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "112",
    "descripcion": "Cadena Regional"
  },
  {
    "codigo": "111",
    "descripcion": "Autoservicio Tradicional"
  }
]

Array de sub ramos. Si no hay ninguno devuelve [].

Tipos de empleado​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve los tipos de empleado activos (por ejemplo chofer o vendedor). Los inactivos no se devuelven.

No recibe parámetros. No tiene paginación: devuelve todos los tipos activos.

Respuestas

200
Array de tipos de empleado. Si no hay ninguno activo devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-tipos-empleado
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-tipos-empleado \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-tipos-empleado)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "CHF",
    "descripcion": "Chofer"
  },
  {
    "codigo": "VEN",
    "descripcion": "Vendedor"
  }
]

Array de tipos de empleado. Si no hay ninguno activo devuelve [].

Tipos de facturación​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve todos los tipos de facturación (por ejemplo electrónica o preimpresa).

No recibe parámetros. No tiene paginación: devuelve todos los tipos de facturación.

Nota: a diferencia de otros maestros, este endpoint devuelve también los tipos de facturación inactivos, y la respuesta no indica cuáles lo están.

Respuestas

200
Array de tipos de facturación. Si no hay ninguno devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-tipos-facturacion
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-tipos-facturacion \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-tipos-facturacion)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "ELE",
    "descripcion": "Electrónica"
  },
  {
    "codigo": "PRE",
    "descripcion": "Preimpresa"
  }
]

Array de tipos de facturación. Si no hay ninguno devuelve [].

Vendedores​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve los empleados que tienen asignado el tipo de empleado "vendedor". Cuál es ese tipo lo define la configuración del sistema.

No recibe parámetros. No tiene paginación: devuelve todos los vendedores. Para filtrar empleados por otro tipo usar Empleados.

Nota: no se filtra por estado: también se devuelven los vendedores inactivos, y la respuesta no indica cuáles lo están.

Respuestas

200
Array de vendedores. Si no hay ninguno devuelve [].
application/json

400
El sistema no tiene configurado el tipo de empleado vendedor. Mensaje: "No se pudo obtener el tipo de empleado vendedor en las preferencias".
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-vendedores
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-vendedores \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-vendedores)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "codigo": "V123",
    "nombre": "Eliades Ochoa"
  },
  {
    "codigo": "V001",
    "nombre": "Benny Moré"
  }
]

Array de vendedores. Si no hay ninguno devuelve [].

Exhibidores​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve, agrupados por cliente, los exhibidores de productos Pepsico que tiene asignados cada cliente. Los datos se leen de la tabla de integración con Pepsico (Pepsico_ClienteExhibidor), que se carga por fuera de Gescom Web.

No recibe parámetros. No tiene paginación ni filtros: devuelve todos los registros de la tabla en una sola respuesta.

Nota: el cliente y el artículo se vinculan por id interno. Si un registro de la tabla apunta a un cliente o a un artículo que ya no existe, codigoCliente o codigoItem vienen en null.

Respuestas

200
Array con un elemento por cliente. Si la tabla está vacía devuelve [].
application/json

400
Error al consultar la base de datos (por ejemplo, si la instalación no tiene la tabla de integración con Pepsico).
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/pepsico/get-cliente-exhibidor
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/pepsico/get-cliente-exhibidor \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/pepsico/get-cliente-exhibidor)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "codigoCliente": "4",
    "exhibidores": [
      {
        "codigoItem": "1500002438",
        "cantidadDisponible": 4,
        "esFotoExito": false
      },
      {
        "codigoItem": "1500002439",
        "cantidadDisponible": 11,
        "esFotoExito": true
      }
    ]
  }
]

Array con un elemento por cliente. Si la tabla está vacía devuelve [].

Productos Infaltables​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve, agrupados por cliente, los códigos de los productos Pepsico que el cliente no debería dejar de tener ("infaltables"). Los datos se leen de la tabla de integración con Pepsico (Pepsico_ProductosInfaltables), que se carga por fuera de Gescom Web.

No recibe parámetros. No tiene paginación ni filtros: devuelve todos los registros de la tabla en una sola respuesta.

Nota: el cliente y el artículo se vinculan por id interno. Si un registro de la tabla apunta a un cliente o a un artículo que ya no existe, codigoCliente o el código dentro de productos vienen en null.

Respuestas

200
Array con un elemento por cliente. Si la tabla está vacía devuelve [].
application/json

400
Error al consultar la base de datos (por ejemplo, si la instalación no tiene la tabla de integración con Pepsico).
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/pepsico/get-productos-infaltables
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/pepsico/get-productos-infaltables \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/pepsico/get-productos-infaltables)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "codigoCliente": "4",
    "productos": [
      "3200014",
      "3200015",
      "3200016",
      "3200017"
    ]
  }
]

Array con un elemento por cliente. Si la tabla está vacía devuelve [].

Tienda Perfecta​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve el resultado del programa "Tienda Perfecta" de Pepsico para cada cliente, junto con el ramo, el subramo y el segmento del cliente en Gescom Web. Los datos del resultado se leen de la tabla de integración con Pepsico (Pepsico_ResultadoTiendaPerfecta), que se carga por fuera de Gescom Web.

No recibe parámetros. No tiene paginación ni filtros: devuelve todos los registros de la tabla en una sola respuesta.

Nota: solo se devuelven los registros cuyo cliente existe en Gescom Web. Si un cliente tiene más de un registro en la tabla de integración, aparece repetido.

Respuestas

200
Array con un elemento por registro de la tabla. Si la tabla está vacía devuelve [].
application/json

400
Error al consultar la base de datos (por ejemplo, si la instalación no tiene la tabla de integración con Pepsico).
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/pepsico/get-resultado-tienda-perfecta
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/pepsico/get-resultado-tienda-perfecta \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/pepsico/get-resultado-tienda-perfecta)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "codigoCliente": "400010007",
    "ramo": "Global SB Auto 10X1",
    "subRamo": "Global SB Auto 10X1",
    "perfectStoreType": 2,
    "perfectStoreComment": "Lo que el supervisor puso",
    "perfectStoreState": "Tienda Confirmada",
    "perfectStorePortafolioPorc": 80
  }
]

Array con un elemento por registro de la tabla. Si la tabla está vacía devuelve [].

Cliente Impuestos​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve los impuestos de venta asignados a cada cliente (por ejemplo, percepciones), con la empresa y la alícuota que corresponde a cada uno.

No recibe parámetros. No tiene paginación ni filtros: devuelve todos los clientes que tienen al menos un impuesto asignado.

A diferencia de la mayoría de los endpoints de lectura, la respuesta no es un array: es un objeto con el array dentro de data.

Nota: si un impuesto tiene configurada su alícuota general para más de una empresa, el mismo impuesto puede aparecer repetido dentro de clienteImpuestos (una vez por cada empresa configurada, siempre con el empresaCodigo de la asignación del cliente). Conviene quedarse con una sola entrada por impuestoCodigo + empresaCodigo.

Respuestas

200
Objeto con data y message. Si ningún cliente tiene impuestos asignados, data es [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-clienteimpuestos
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/get-clienteimpuestos \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-clienteimpuestos)
Estado:200
Estado:401
Estado:403

Con impuestos asignados
{
  "data": [
    {
      "clienteCodigo": "7",
      "clienteImpuestos": [
        {
          "impuestoCodigo": "IIBB",
          "empresaCodigo": "1",
          "alicuotaValor": 0.08,
          "aplicaImpuesto": "true"
        },
        {
          "impuestoCodigo": "RG5",
          "empresaCodigo": "99",
          "alicuotaValor": 0.025,
          "aplicaImpuesto": "false"
        }
      ]
    },
    {
      "clienteCodigo": "1052",
      "clienteImpuestos": [
        {
          "impuestoCodigo": "IIBB",
          "empresaCodigo": "1",
          "alicuotaValor": 0.08,
          "aplicaImpuesto": "true"
        }
      ]
    }
  ],
  "message": "Se obtuvieron 2 registros"
}


Con impuestos asignados
Objeto con data y message. Si ningún cliente tiene impuestos asignados, data es [].

Modifica datos
Actualización de ubicación de Clientes​Copiar enlace

Autenticación requerida

Copiar como Markdown
Actualiza las coordenadas GPS (latitud y longitud) de la dirección de entrega o de la dirección fiscal de uno o más clientes. La coordenada queda marcada como exacta (no aproximada).

Body JSON con la lista de ubicaciones dentro de la clave ubicaciones. Se pueden enviar hasta 100 ubicaciones por request.

Nota: si se omite latitud o longitud se toma como 0 y la ubicación se graba igual. Enviar siempre las dos coordenadas.

Errores posibles:

code	Mensaje	Causa
100	No se han enviado registros para procesar	ubicaciones está vacío. Rechaza todo el request.
101	Se ha superado la cantidad maxima de registros a procesar. El maximo es de 100.	Más de 100 ubicaciones. Rechaza todo el request.
405	El campo CodigoCliente tiene un codigo invalido	No existe un cliente con ese código.
416	Tipo de ubicación no reconocido	tipoUbicacion no es UbicacionEntrega ni UbicacionFiscal.
417	La ubicación indicada no es válida	Latitud o longitud fuera de rango.
Los errores por ubicación no indican a qué elemento corresponden. Para saber cuál falló, validar los datos antes de enviarlos o enviar las ubicaciones de a una.

Nota: cada ubicación válida se graba en el momento, sin transacción. Si un elemento no trae codigoCliente (o viene en null), el endpoint responde 400, pero las ubicaciones anteriores a ese elemento ya quedaron grabadas.

Cuerpo
obligatorio
application/json

ubicaciones
Tipo:array of object
obligatorio
{ codigoCliente, tipoUbicacion, latitud, +1 }
Copiar enlace a ubicaciones
Entre 1 y 100 elementos.

Propiedades: 4
Respuestas

200
Siempre que el request llegue al endpoint, incluso si hubo errores. El resultado real está en resultado y errores.
application/json

400
El body no es un objeto JSON, falta la clave ubicaciones, o algún elemento no trae codigoCliente (ver nota).
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forpost/data/cmd/ventas/api/v1/clientes/set-ubicacion
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/clientes/set-ubicacion \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "ubicaciones": [
    {
      "codigoCliente": "112",
      "tipoUbicacion": "UbicacionEntrega",
      "latitud": -33.867886,
      "longitud": -63.987
    },
    {
      "codigoCliente": "450",
      "tipoUbicacion": "UbicacionFiscal",
      "latitud": -34.603722,
      "longitud": -58.381592
    }
  ]
}'


Probar solicitud
(post /data/cmd/ventas/api/v1/clientes/set-ubicacion)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "resultado": "P",
  "errores": [
    {
      "code": 417,
      "msg": "La ubicación indicada no es válida"
    }
  ],
  "detalle": []
}

Siempre que el request llegue al endpoint, incluso si hubo errores. El resultado real está en resultado y errores.

deprecated
Modifica datos
Alta de comprobantes​Copiar enlace

Autenticación requerida

Copiar como Markdown
Fuera de servicio. Este endpoint está deprecado y ya no registra comprobantes: cualquier llamada responde con error, sin validar ni grabar nada. Lo que sigue describe cómo funcionaba y queda solo como referencia.

Registraba en Gescom Web el comprobante (factura, ticket, etc.) que un sistema externo generó para una venta. Se usaba junto con la lectura de ventas pendientes de facturación: se leían las ventas, se facturaban afuera y con este endpoint se informaba el comprobante de cada una.

Body JSON con la lista de comprobantes dentro de la clave data. Se pueden enviar hasta 100 comprobantes por request.

Datos de la venta

Datos generales

Datos del comprobante generado externamente

Nota: en los campos numéricos "obligatorios" la omisión no da error: un campo omitido se graba como 0. Enviar siempre todos los importes y el número de comprobante.

Para aceptar el comprobante, la venta tiene que cumplir todas estas condiciones:

Existe y no está cerrada.
Está en la etapa Impuestos o Facturación.
Tanto la etapa como la venta están en estado suspendido (detenidas a la espera de una acción).
Errores posibles:

code	Mensaje	Causa
100	No se han enviado registros para procesar	data está vacío (general).
101	Se ha superado la cantidad maxima de registros a procesar. El maximo es de 100.	Más de 100 comprobantes (general).
400	Mensaje de validación con el nombre del campo	Falta codigoEmpresa, codigoTipoComprobante o codigoTipoFacturacion.
401	Identificador no definido	id es 0 o no existe una venta con ese id.
402	Identificador repetido	El mismo id aparece más de una vez. Se informa una sola vez y no se procesa ninguna de las repetidas.
405	El campo CodigoEmpresa tiene un codigo invalido	La empresa no existe. Mismo mensaje con CodigoPuntoVenta, CodigoTipoComprobante o CodigoTipoFacturacion si el que no existe es ese. Los códigos distinguen mayúsculas.
407	La fecha del registro no es valida	fechaComprobante es anterior a la creación de la venta o está más de 30 días en el futuro.
419	La etapa de la venta no permite establecer el comprobante de facturación	La venta no está en Impuestos ni en Facturación. Variantes: "El estado de la etapa…" y "El estado de la venta…" si no están suspendidos.
420	La venta ya se encuentra cerrada	
421	La venta ya tiene asignada una empresa y es diferente a la indicada en el comprobante	
422	La información en el campo PropiedadesAdicionales no es válida. No se permite un array en esta propiedad	propiedadesAdicionales es un array.
500	Error desconocido	Error inesperado al grabar.
Nota: los comprobantes se graban de a uno, sin una transacción que abarque todo el request: los que se registraron quedan registrados aunque otros fallen.

Cuerpo
obligatorio
application/json

data
Tipo:array of object
obligatorio
{ id, codigoEmpresa, codigoPuntoVenta, +15 }
Copiar enlace a data
Entre 1 y 100 elementos.

Propiedades: 18
Respuestas

200
Ya no se devuelve. Cuando funcionaba: siempre que el request llegara al endpoint, incluso si hubo errores. El resultado real estaba en resultado, errores y detalle.
application/json

400
El body no es un objeto JSON, o falta la clave data.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.


default
Hoy, cualquier llamada: el endpoint está fuera de servicio y rechaza el request sin procesarlo.
application/json
Request Example forpost/data/cmd/ventas/api/v1/set-comprobante
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/set-comprobante \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "data": [
    {
      "id": 4,
      "aprobado": true,
      "cae": "123456789",
      "codigoEmpresa": "E2",
      "codigoPuntoVenta": 3,
      "codigoTipoComprobante": "FAC-A",
      "codigoTipoFacturacion": "EXT",
      "fechaComprobante": "2023-03-06T10:13:38-03:00",
      "numeroComprobante": 125546,
      "importeExento": 0,
      "importeIva": 525,
      "importeNeto": 2175,
      "importeTotal": 2500,
      "importeTotalConc": 0,
      "importeTributos": 0,
      "comprobanteAdicional": false
    }
  ]
}'


Probar solicitud
(post /data/cmd/ventas/api/v1/set-comprobante)
Estado:200
Estado:400
Estado:401
Estado:403
Estado:default

{
  "resultado": "P",
  "errores": [],
  "detalle": [
    {
      "id": 5,
      "resultado": "A",
      "errores": []
    },
    {
      "id": 6,
      "resultado": "R",
      "errores": [
        {
          "code": 420,
          "msg": "La venta ya se encuentra cerrada"
        }
      ]
    }
  ]
}

Ya no se devuelve. Cuando funcionaba: siempre que el request llegara al endpoint, incluso si hubo errores. El resultado real estaba en resultado, errores y detalle.

Modifica datos
Crear listas de precios​Copiar enlace

Autenticación requerida

Copiar como Markdown
Crea una lista de precios nueva con sus precios iniciales. Para modificar una lista existente usar Modificación de precios.

Este endpoint no sigue el formato /<módulo>/api/v<N>/. También se puede llamar como /data/cmd/ventas.precios.abm/new-lista-precio (es el mismo comando).

Body JSON con la lista dentro de la clave listaPrecio. La estructura es la misma que en Modificación de precios, sin fullSync:

Nota: el endpoint no valida que el código de lista no exista ni que los códigos de artículo, unidad y moneda sean válidos. Con un código repetido se crea una segunda lista con el mismo código, y Modificación de precios, que busca por código, puede tomar cualquiera de las dos. Un precio con artículo, unidad, factor o moneda inexistentes se graba igual, sin quedar asociado al artículo. Verificar los datos antes de enviarlos (por ejemplo con los endpoints de listas de precios y de artículos).

Cuerpo
obligatorio
application/json

listaPrecio
Tipo:object
obligatorio
{ codigo, itemUnidadList, titulo, +3 }
Copiar enlace a listaPrecio
Datos de la lista.

Propiedades: 6
Respuestas

200
La lista se creó. El body es solo el id numérico de la lista nueva (no es un objeto).
application/json

400
Un artículo tiene precios en más de una moneda ("Los precios del item '116002' deben definirse con una misma moneda"), falta listaPrecio o itemUnidadList, u otro error al grabar. No se crea nada.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forpost/data/cmd/ventas/precios/abm/new-lista-precio
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/precios/abm/new-lista-precio \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "listaPrecio": {
    "codigo": "MAY",
    "titulo": "Mayorista",
    "descripcion": "Lista mayorista",
    "activo": true,
    "esGeneral": true,
    "itemUnidadList": [
      {
        "item": "116002",
        "unidad": "Unidad",
        "factor": 1,
        "moneda": "ARS",
        "precio": 29.39
      },
      {
        "item": "116002",
        "unidad": "Pack",
        "factor": 12,
        "moneda": "ARS",
        "precio": 340
      }
    ]
  }
}'


Probar solicitud
(post /data/cmd/ventas/precios/abm/new-lista-precio)
Estado:200
Estado:400
Estado:401
Estado:403

57

La lista se creó. El body es solo el id numérico de la lista nueva (no es un objeto).

Modifica datos
Generación de ventas (v1)​Copiar enlace

Autenticación requerida

Copiar como Markdown
Versión v1 · Vigente. Se recomienda la v3, que indica la unidad de cada ítem en forma explícita.

Crea ventas a partir de pedidos externos, en forma masiva.

Recibe los mismos campos de pedido que v3 y devuelve la misma respuesta. Solo cambia cómo se expresa la cantidad de cada ítem:

cantidad: en la unidad de venta configurada en el artículo.
unidades: en la unidad base del artículo (entero).
Hay que enviar cantidad o unidades. codigoUnidad y unidadFactor se ignoran, y bultos da error 406 ("Esta version utiliza el campo Cantidad en lugar de Bultos").
En artículos incontables (pesables) también se puede enviar solo piezas. piezas en un artículo contable da error 406.
Nota: si se envían a la vez cantidad y unidades, gana unidades y la otra cantidad se descarta sin aviso. Enviar solo una.

Cada pedido del request se procesa por separado: algunos pueden entrar y otros no. Un pedido puede generar más de una venta (ítems de distintas empresas, artículos con etiquetas que exigen venta separada o precios en distintas monedas); todas se informan bajo el mismo identificador.

Body JSON con la lista en la clave pedidos. Máximo 20 pedidos por request (el valor es configurable; 20 es el default).

Nota: si falta codigoVendedor en algún pedido, el endpoint responde 400 en lugar de informar el error en el detalle, y los pedidos anteriores del mismo request pueden haber quedado grabados. Verificar que todos los pedidos lo traigan.

Nota: los pedidos con un identificador repetido dentro del request no se procesan y se informan en una sola entrada de detalle con error 402. Como resultado se calcula sobre la cantidad de pedidos enviados, puede venir P aunque no se haya grabado ninguna venta. Revisar siempre el detalle de cada pedido.

Errores por pedido (detalle[].errores): los mismos que en v3 (400, 402, 403, 404, 405, 406, 407, 408, 410-415, 418, 430 y 500). Ver la versión v3.

Todas las versiones
Versión	URL	Estado
v1	/data/cmd/ventas/api/v1/pedidos/create-bulk	Vigente. cantidad en la unidad de venta del artículo.
v2	/data/cmd/ventas/api/v2/pedidos/create-bulk	Vigente. Usa bultos en lugar de cantidad.
v3	/data/cmd/ventas/api/v3/pedidos/create-bulk	Vigente (recomendada). cantidad en la unidad indicada con codigoUnidad y unidadFactor.
Cuerpo
obligatorio
application/json

pedidos
Tipo:array of object
obligatorio
{ codigoCliente, codigoVendedor, items, +19 }
Copiar enlace a pedidos
Propiedades: 22
Respuestas

200
Siempre que el request llegue al endpoint, incluso si hubo errores. Revisar resultado y el detalle de cada pedido.
application/json

400
El body no es un objeto JSON, o falta codigoVendedor (ver nota).
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forpost/data/cmd/ventas/api/v1/pedidos/create-bulk
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/pedidos/create-bulk \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "pedidos": [
    {
      "identificador": "PED-EJEMPLO-0001",
      "codigoTipoVenta": "VEN",
      "codigoCliente": "CLI-0001",
      "codigoVendedor": "VEND-01",
      "codigoRuta": "RUTA-01",
      "fechaEntrega": "2025-05-24",
      "observaciones": "Entregar por la tarde",
      "items": [
        {
          "codigoItem": "ART-0001",
          "cantidad": 2
        },
        {
          "codigoItem": "ART-0002",
          "unidades": 12,
          "precioUnitario": 150.5,
          "descuento": 0.1
        }
      ]
    }
  ]
}'


Probar solicitud
(post /data/cmd/ventas/api/v1/pedidos/create-bulk)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "resultado": "P",
  "errores": [],
  "detalle": [
    {
      "identificador": "PED-000123",
      "ventas": [
        {
          "id": 878,
          "codigoEmpresa": "E1",
          "numero": 80,
          "comprobante": "E1 VEN 00000080"
        },
        {
          "id": 879,
          "codigoEmpresa": "E2",
          "numero": 81,
          "comprobante": "E2 VEN 00000081"
        }
      ],
      "errores": []
    },
    {
      "identificador": "PED-000124",
      "ventas": null,
      "errores": [
        {
          "code": 403,
          "msg": "Pedido ya procesado"
        }
      ]
    }
  ]
}

Siempre que el request llegue al endpoint, incluso si hubo errores. Revisar resultado y el detalle de cada pedido.

Modifica datos
Generación de ventas (v2)​Copiar enlace

Autenticación requerida

Copiar como Markdown
Versión v2 · Vigente. Se recomienda la v3, que indica la unidad de cada ítem en forma explícita.

Crea ventas a partir de pedidos externos, en forma masiva.

Recibe los mismos campos de pedido que v3 y devuelve la misma respuesta. Solo cambia cómo se expresa la cantidad de cada ítem:

bultos: en la primera presentación del artículo con factor mayor a 1 (por ejemplo, el pack); si el artículo no tiene, en la unidad base.
unidades: en la unidad base del artículo (entero).
Hay que enviar bultos o unidades. codigoUnidad y unidadFactor se ignoran, y cantidad da error 406 ("Esta version utiliza el campo Bultos en lugar de Cantidad").
En artículos incontables (pesables) también se puede enviar solo piezas. piezas en un artículo contable da error 406.
Nota: si se envían a la vez bultos y unidades, gana unidades y la otra cantidad se descarta sin aviso. Enviar solo una.

Cada pedido del request se procesa por separado: algunos pueden entrar y otros no. Un pedido puede generar más de una venta (ítems de distintas empresas, artículos con etiquetas que exigen venta separada o precios en distintas monedas); todas se informan bajo el mismo identificador.

Body JSON con la lista en la clave pedidos. Máximo 20 pedidos por request (el valor es configurable; 20 es el default).

Nota: si falta codigoVendedor en algún pedido, el endpoint responde 400 en lugar de informar el error en el detalle, y los pedidos anteriores del mismo request pueden haber quedado grabados. Verificar que todos los pedidos lo traigan.

Nota: los pedidos con un identificador repetido dentro del request no se procesan y se informan en una sola entrada de detalle con error 402. Como resultado se calcula sobre la cantidad de pedidos enviados, puede venir P aunque no se haya grabado ninguna venta. Revisar siempre el detalle de cada pedido.

Errores por pedido (detalle[].errores): los mismos que en v3 (400, 402, 403, 404, 405, 406, 407, 408, 410-415, 418, 430 y 500). Ver la versión v3.

Todas las versiones
Versión	URL	Estado
v1	/data/cmd/ventas/api/v1/pedidos/create-bulk	Vigente. cantidad en la unidad de venta del artículo.
v2	/data/cmd/ventas/api/v2/pedidos/create-bulk	Vigente. Usa bultos en lugar de cantidad.
v3	/data/cmd/ventas/api/v3/pedidos/create-bulk	Vigente (recomendada). cantidad en la unidad indicada con codigoUnidad y unidadFactor.
Cuerpo
obligatorio
application/json

pedidos
Tipo:array of object
obligatorio
{ codigoCliente, codigoVendedor, items, +19 }
Copiar enlace a pedidos
Propiedades: 22
Respuestas

200
Siempre que el request llegue al endpoint, incluso si hubo errores. Revisar resultado y el detalle de cada pedido.
application/json

400
El body no es un objeto JSON, o falta codigoVendedor (ver nota).
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forpost/data/cmd/ventas/api/v2/pedidos/create-bulk
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v2/pedidos/create-bulk \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "pedidos": [
    {
      "identificador": "PED-EJEMPLO-0001",
      "codigoTipoVenta": "VEN",
      "codigoCliente": "CLI-0001",
      "codigoVendedor": "VEND-01",
      "codigoRuta": "RUTA-01",
      "fechaEntrega": "2025-05-24",
      "observaciones": "Entregar por la tarde",
      "items": [
        {
          "codigoItem": "ART-0001",
          "bultos": 2
        },
        {
          "codigoItem": "ART-0002",
          "unidades": 12,
          "precioUnitario": 150.5,
          "descuento": 0.1
        }
      ]
    }
  ]
}'


Probar solicitud
(post /data/cmd/ventas/api/v2/pedidos/create-bulk)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "resultado": "P",
  "errores": [],
  "detalle": [
    {
      "identificador": "PED-000123",
      "ventas": [
        {
          "id": 878,
          "codigoEmpresa": "E1",
          "numero": 80,
          "comprobante": "E1 VEN 00000080"
        },
        {
          "id": 879,
          "codigoEmpresa": "E2",
          "numero": 81,
          "comprobante": "E2 VEN 00000081"
        }
      ],
      "errores": []
    },
    {
      "identificador": "PED-000124",
      "ventas": null,
      "errores": [
        {
          "code": 403,
          "msg": "Pedido ya procesado"
        }
      ]
    }
  ]
}

Siempre que el request llegue al endpoint, incluso si hubo errores. Revisar resultado y el detalle de cada pedido.

Modifica datos
Recomendada
Generación de ventas (v3)​Copiar enlace

Autenticación requerida

Copiar como Markdown
Versión v3 · Vigente (recomendada). cantidad en la unidad indicada con codigoUnidad y unidadFactor.

Crea ventas a partir de pedidos externos, en forma masiva. Cada pedido del request se procesa por separado: algunos pueden entrar y otros no.

Un pedido puede generar más de una venta. El sistema lo divide automáticamente cuando sus ítems pertenecen a distintas empresas, cuando hay artículos con etiquetas que exigen venta separada (según configuración) o cuando los ítems tienen precios en distintas monedas. Todas las ventas generadas se informan bajo el mismo identificador.

Las tres versiones reciben los mismos campos de pedido, aplican las mismas validaciones y devuelven la misma respuesta. Solo cambia cómo se expresa la cantidad de cada ítem:

Versión	Cantidad del ítem
v1	cantidad en la unidad de venta configurada en el artículo, o unidades en unidad base. codigoUnidad y unidadFactor se ignoran. bultos da error.
v2	bultos en la primera presentación del artículo con factor mayor a 1 (si no tiene, en unidad base), o unidades en unidad base. cantidad da error.
v3	cantidad en la unidad indicada por codigoUnidad + unidadFactor, que tienen que ser una de las unidades permitidas del artículo. Los tres campos son obligatorios, salvo cantidad en un artículo incontable que lleva piezas en stock cuando se envía piezas: ahí se calcula con el peso ponderado de la pieza. bultos y unidades dan error.
Nota: en v1 y v2, si se envían a la vez cantidad (o bultos) y unidades, gana unidades y la otra cantidad se descarta sin aviso. Enviar solo una.

Body JSON con la lista en la clave pedidos. Máximo 20 pedidos por request (el valor es configurable; 20 es el default).

Reglas de negocio:

Si el tipo de venta requiere una venta referenciada (por ejemplo, una devolución) y no se envía ventaReferenciadaId, el sistema referencia automáticamente la última venta del cliente de un tipo compatible.
Los artículos inactivos, bloqueados o no disponibles para venta se rechazan (406, por ejemplo "El item X esta inactivo o bloqueado."), salvo en un tipo de venta de crédito que trae ventaReferenciadaId, si el artículo estaba en esa venta y la cantidad devuelta (cantidad × factor, sumando las líneas del artículo) no supera la de la venta original. La venta que el sistema referencia automáticamente no habilita esta excepción.
Todo combo usado en los ítems (codigoCombo) tiene que estar declarado con su cantidad en combos.
Los ítems de un combo no se dividen por empresa ni por moneda; todos tienen que tener la misma moneda.
Nota: si falta codigoVendedor en algún pedido, el endpoint responde 400 en lugar de informar el error en el detalle, y los pedidos anteriores del mismo request pueden haber quedado grabados. Verificar que todos los pedidos lo traigan.

Errores por pedido (detalle[].errores):

Code	Causa
400	Falla la validación del modelo (falta codigoCliente o items, texto demasiado largo).
402	identificador repetido dentro del request.
403	Ya existe una venta con ese identificador cargada por el mismo usuario de la API.
404	codigoTipoVenta no está entre los admitidos.
405	Código inválido (cliente, vendedor, ruta, tipo de venta, empresa, punto de venta, sede, motivo, condición de pago, artículo o depósito).
406	Error de cantidades o unidades del ítem, o error al grabar la venta (mensaje del sistema).
407	fechaPedido con más de 4 días de antigüedad.
408, 410-415	Errores de combos (combo inválido, combo usado y no declarado, componente no encontrado, falta el descuento, etc.).
418	Algún descuento fuera del rango 0 a 1.
430	codigoLote no existe para el artículo de la línea: "El lote '' no existe para el item ''".
500	Error inesperado al armar o grabar la venta.
Todas las versiones
Versión	URL	Estado
v1	/data/cmd/ventas/api/v1/pedidos/create-bulk	Vigente. cantidad en la unidad de venta del artículo.
v2	/data/cmd/ventas/api/v2/pedidos/create-bulk	Vigente. Usa bultos en lugar de cantidad.
v3	/data/cmd/ventas/api/v3/pedidos/create-bulk	Vigente (recomendada). cantidad en la unidad indicada con codigoUnidad y unidadFactor.
Cuerpo
obligatorio
application/json

pedidos
Tipo:array of object
obligatorio
{ codigoCliente, codigoVendedor, items, +19 }
Copiar enlace a pedidos
Propiedades: 22
Respuestas

200
Siempre que el request llegue al endpoint, incluso si hubo errores. Revisar resultado y el detalle de cada pedido.
application/json

400
El body no es un objeto JSON, o falta codigoVendedor (ver nota).
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forpost/data/cmd/ventas/api/v3/pedidos/create-bulk
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v3/pedidos/create-bulk \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "pedidos": [
    {
      "identificador": "PED-000123",
      "codigoTipoVenta": "VEN",
      "codigoCliente": "CC123",
      "codigoVendedor": "CV123",
      "codigoRuta": "CR123",
      "fechaEntrega": "2025-05-24",
      "observaciones": "Entregar por la tarde",
      "items": [
        {
          "codigoItem": "300030687",
          "cantidad": 2,
          "codigoUnidad": "Pack",
          "unidadFactor": 18
        },
        {
          "codigoItem": "300030700",
          "cantidad": 5,
          "codigoUnidad": "Unidad",
          "unidadFactor": 1,
          "precioUnitario": 1250.5,
          "descuento": 0.1
        }
      ]
    }
  ]
}'


Probar solicitud
(post /data/cmd/ventas/api/v3/pedidos/create-bulk)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "resultado": "P",
  "errores": [],
  "detalle": [
    {
      "identificador": "PED-000123",
      "ventas": [
        {
          "id": 878,
          "codigoEmpresa": "E1",
          "numero": 80,
          "comprobante": "E1 VEN 00000080"
        },
        {
          "id": 879,
          "codigoEmpresa": "E2",
          "numero": 81,
          "comprobante": "E2 VEN 00000081"
        }
      ],
      "errores": []
    },
    {
      "identificador": "PED-000124",
      "ventas": null,
      "errores": [
        {
          "code": 403,
          "msg": "Pedido ya procesado"
        }
      ]
    }
  ]
}

Siempre que el request llegue al endpoint, incluso si hubo errores. Revisar resultado y el detalle de cada pedido.

Modifica datos
Generación de ventas con comprobante​Copiar enlace

Autenticación requerida

Copiar como Markdown
Está pensado para ingresar pedidos que ya fueron facturados en un sistema externo, junto con los datos de sus comprobantes.

Nota: hoy el endpoint no procesa los comprobantes. Acepta la propiedad comprobantes (y un eventual impuestos en los ítems) sin error, pero la descarta: el pedido se procesa exactamente igual que en Generación de ventas v3 y las ventas quedan sin comprobante. Hoy la API no ofrece una forma de registrar el comprobante externo: Alta de comprobantes (/data/cmd/ventas/api/v1/set-comprobante), que era la alternativa, está deprecada y fuera de servicio.

Body JSON con la lista en la clave pedidos. Cada pedido tiene los mismos campos, reglas y límites que Generación de ventas v3 (ítems con cantidad, codigoUnidad y unidadFactor; máximo 20 pedidos por request), más la propiedad comprobantes:

Igual que Generación de ventas: resultado, errores y un detalle por pedido con las ventas creadas y sus errores. Los códigos HTTP y los errores posibles también son los mismos.

Cuerpo
obligatorio
application/json

pedidos
Tipo:array of object
obligatorio
{ comprobantes }
Copiar enlace a pedidos
Pedidos con la misma estructura que Generación de ventas v3.

Propiedades: 1
Respuestas

200
OK
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forpost/data/cmd/ventas/api/v3/pedidos/create-invoiced
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v3/pedidos/create-invoiced \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "pedidos": [
    {
      "identificador": "FAC-A-0001-00125546",
      "codigoTipoVenta": "VEN",
      "codigoCliente": "7",
      "codigoVendedor": "21",
      "codigoRuta": "11",
      "items": [
        {
          "codigoItem": "300030687",
          "cantidad": 2,
          "codigoUnidad": "Pack",
          "unidadFactor": 18
        }
      ],
      "comprobantes": [
        {
          "cae": "123456789",
          "codigoEmpresa": "E1",
          "codigoPuntoVenta": 1,
          "codigoTipoComprobante": "FAC-A",
          "codigoTipoFacturacion": "EXT",
          "numeroComprobante": 125546,
          "importeExento": 0,
          "importeIva": 525,
          "importeNeto": 2175,
          "importeTotal": 2500,
          "importeTotalConc": 0,
          "importeTributos": 0,
          "comprobanteAdicional": false
        }
      ]
    }
  ]
}'


Probar solicitud
(post /data/cmd/ventas/api/v3/pedidos/create-invoiced)
Estado:200
Estado:401
Estado:403

{
  "resultado": "A",
  "errores": [],
  "detalle": [
    {
      "identificador": "FAC-A-0001-00125546",
      "ventas": [
        {
          "id": 901,
          "codigoEmpresa": "E1",
          "numero": 95,
          "comprobante": "E1 VEN 00000095"
        }
      ],
      "errores": []
    }
  ]
}

OK

Modifica datos
Generación de visitas no exitosas​Copiar enlace

Autenticación requerida

Copiar como Markdown
Registra visitas a clientes que no terminaron en venta, con el motivo de no venta. Si ya existe una visita para la misma fecha, cliente, ruta y vendedor (por ejemplo, una visita planificada), se actualiza su motivo en lugar de crear otra.

Body JSON con la lista en la clave visitas. Entre 1 y 100 visitas por request.

Errores posibles:

Code	Causa
100	No se enviaron visitas.
101	Se enviaron más de 100 visitas.
400	Falta un campo obligatorio (mensaje de validación del modelo).
405	codigoCliente, codigoRuta, codigoVendedor o codigoMotivo no existe.
407	La fecha es anterior a ayer.
Nota: los errores no indican a qué visita corresponden. Si el resultado es P, identificar las visitas rechazadas por el contenido del mensaje o reenviarlas de a una. Reenviar una visita que ya se grabó no la duplica: solo actualiza el motivo.

Cuerpo
obligatorio
application/json

visitas
Tipo:array of object
obligatorio
{ codigoCliente, codigoRuta, codigoVendedor, +2 }
Copiar enlace a visitas
Propiedades: 5
Respuestas

200
Siempre que el request llegue al endpoint, incluso si hubo errores. Revisar resultado.
application/json

400
El body no es un objeto JSON, falta la clave visitas o falla la grabación.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forpost/data/cmd/ventas/api/v1/visitas/create-no-exitosa-bulk
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/visitas/create-no-exitosa-bulk \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "visitas": [
    {
      "fecha": "2025-08-05",
      "codigoCliente": "112",
      "codigoRuta": "12",
      "codigoVendedor": "11",
      "codigoMotivo": "31"
    },
    {
      "fecha": "2025-08-05",
      "codigoCliente": "12",
      "codigoRuta": "12",
      "codigoVendedor": "132",
      "codigoMotivo": "10"
    }
  ]
}'


Probar solicitud
(post /data/cmd/ventas/api/v1/visitas/create-no-exitosa-bulk)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "resultado": "P",
  "errores": [
    {
      "code": 405,
      "msg": "El campo CodigoMotivo tiene un codigo invalido"
    }
  ],
  "detalle": []
}

Siempre que el request llegue al endpoint, incluso si hubo errores. Revisar resultado.

Modifica datos
Modificación de precios​Copiar enlace

Autenticación requerida

Copiar como Markdown
Actualiza los datos y los precios de una lista de precios existente. Agrega los precios nuevos y reemplaza los que cambiaron; el precio anterior queda en el historial. Opcionalmente (fullSync) elimina los precios que no vengan en el request.

Este endpoint no sigue el formato /<módulo>/api/v<N>/. También se puede llamar como /data/cmd/ventas.precios.abm/save-lista-precio (es el mismo comando).

Cada precio se identifica por artículo + unidad + factor. Si ya existe y cambió el precio o el porcentaje de ganancia, el precio anterior se cierra (queda en el historial) y se crea uno nuevo. Si no cambió, no se toca. Si no existe, se agrega.

Nota: con fullSync en true, los precios que se rechazan (artículo, unidad o moneda inválidos) o se descartan (precio null o negativo) cuentan como "no enviados": si el artículo tenía precio en la lista, ese precio se elimina.

Nota: si la misma combinación artículo + unidad + factor aparece dos veces en itemUnidadList, responde 400 y no se graba nada.

Mensajes posibles en errores:

Mensaje	Causa
El codigo 'X' no representa ningun item activo en el sistema	El artículo no existe o está inactivo.
El codigo 'X' no representa ninguna moneda en el sistema	La moneda no existe.
El nombre 'X' no representa ninguna unidad en el sistema	La unidad no existe.
Solo se verifica que existan el artículo, la unidad y la moneda por separado: no se verifica que la unidad y el factor correspondan a una presentación configurada para el artículo.

Cuerpo
obligatorio
application/json

listaPrecio
Tipo:object
obligatorio
{ codigo, titulo, descripcion, +4 }
Copiar enlace a listaPrecio
Datos de la lista.

Propiedades: 7
fullSync
Tipo:boolean
Copiar enlace a fullSync
Default false: solo se agregan y actualizan precios. En true, además se eliminan los precios actuales de los artículos activos que no estén entre los precios aceptados del request, dejando la lista solo con lo enviado.

Respuestas

200
Se procesó la lista. Los precios rechazados se informan en conError y errores.
application/json

400
La lista no existe ("No existe la lista de precios …"), esGeneral no coincide ("La lista X es General y eso no se puede modificar"), el código ya lo usa otra lista ("Ya existe una lista con el codigo X"), precio repetido, o falta listaPrecio o itemUnidadList. En todos estos casos no se graba nada.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forpost/data/cmd/ventas/precios/abm/save-lista-precio
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/precios/abm/save-lista-precio \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "listaPrecio": {
    "codigo": "1",
    "titulo": "Lista General",
    "descripcion": "Lista General",
    "activo": true,
    "esGeneral": true,
    "itemUnidadList": [
      {
        "item": "1100000130",
        "unidad": "Unidad",
        "factor": 1,
        "moneda": "ARS",
        "precio": 0
      },
      {
        "item": "116002",
        "unidad": "Unidad",
        "factor": 1,
        "moneda": "ARS",
        "precio": 29.39
      }
    ]
  },
  "fullSync": false
}'


Probar solicitud
(post /data/cmd/ventas/precios/abm/save-lista-precio)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "resultado": "P",
  "registros": 175,
  "sinError": 174,
  "conError": 1,
  "errores": [
    "El nombre 'Pac' no representa ninguna unidad en el sistema"
  ]
}

Se procesó la lista. Los precios rechazados se informan en conError y errores.

Modifica datos
Reducción de ítems del pedido​Copiar enlace

Autenticación requerida

Copiar como Markdown
Reduce la cantidad de uno o más ítems de una venta existente que todavía no fue facturada. La venta tiene que estar entre las etapas de Reserva de stock y Facturación.

Se indica la venta por su id y, por cada línea, su ventaItemId y la nueva cantidad, que tiene que ser menor o igual a la actual. El sistema:

Libera de la reserva de stock la cantidad sobrante, dejando reservado solo lo indicado.
Elimina la línea si la nueva cantidad es 0 (queda registrada entre las líneas eliminadas de la venta).
Si la venta ya estaba en la etapa Impuestos o posterior, la vuelve a la etapa Impuestos para que se recalcule.
Agrega al comentario interno de la venta la marca "Venta modificada el " y registra el cambio en la auditoría.
Body JSON con los campos en el primer nivel (sin clave contenedora):

En este ejemplo, en la venta 1 la línea 1 queda en 2 unidades base, la línea 2 en 5 y la línea 3 (un artículo pesable) en 2100 gramos y 3 piezas.

Unidad de la línea modificada
Como la nueva cantidad se informa en unidades base, el sistema decide la unidad de la línea así:

Si la línea ya está en unidad base (factor 1), se guarda la cantidad tal cual.
Si la nueva cantidad es múltiplo del factor de la línea (o el artículo es incontable), se mantiene la unidad y la cantidad se divide por el factor. Ejemplo: una línea de 5 packs x 12 reducida a 24 queda en 2 packs x 12.
Si no es múltiplo, la línea pasa a la unidad base y el precio unitario se divide por el factor (redondeado a 2 decimales). Ejemplo: 5 packs x 12 reducida a 2 queda en 2 unidades; se quitaron 58.
Errores posibles:

Code	Causa
401	No existe una venta con ese id.
419	La venta no está entre las etapas de Reserva de stock y Facturación.
406	La venta no se puede modificar en su estado actual (por ejemplo, está asignada a un reparto que no lo permite), o falló la eliminación de la venta (mensaje del sistema).
427	Todas las líneas quedarían en 0 y deleteVentaIfEmpty es false.
424	Un ventaItemId no pertenece a la venta o no es un artículo que maneje stock (uno por línea).
425	La nueva cantidad es mayor a la actual (uno por línea).
429	Falta nuevaCantidadDePiezas en un artículo con control de piezas (uno por línea).
426	La nueva cantidad de piezas es mayor a la actual (uno por línea).
500	Error inesperado al aplicar los cambios.
Cuerpo
obligatorio
application/json
id
Tipo:integer
obligatorio
Copiar enlace a id
Id de la venta.


itemsList
Tipo:array of object
obligatorio
{ ventaItemId, nuevaCantidadEnUnidadesBase, nuevaCantidadDePiezas }
Copiar enlace a itemsList
Líneas a reducir.

Propiedades: 3
deleteVentaIfEmpty
Tipo:boolean
Copiar enlace a deleteVentaIfEmpty
Si es true y todas las líneas de la venta quedan en 0, se elimina la venta completa. Si es false (default), ese caso se rechaza.

Respuestas

200
Siempre que el request llegue al endpoint, incluso si fue rechazado. Revisar resultado.
application/json

400
El body no es un objeto JSON o falta itemsList.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forpost/data/cmd/ventas/api/v1/remove-items
Shell Curl
curl https://sitio.gescom.online/data/cmd/ventas/api/v1/remove-items \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "id": 1,
  "deleteVentaIfEmpty": false,
  "itemsList": [
    {
      "ventaItemId": 1,
      "nuevaCantidadEnUnidadesBase": 2
    },
    {
      "ventaItemId": 2,
      "nuevaCantidadEnUnidadesBase": 5
    },
    {
      "ventaItemId": 3,
      "nuevaCantidadEnUnidadesBase": 2100,
      "nuevaCantidadDePiezas": 3
    }
  ]
}'


Probar solicitud
(post /data/cmd/ventas/api/v1/remove-items)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "resultado": "R",
  "errores": [
    {
      "code": 425,
      "msg": "Se especificó una cantidad incorrecta en item 2"
    }
  ]
}

Siempre que el request llegue al endpoint, incluso si fue rechazado. Revisar resultado.

Cambios de ventas (v2)​Copiar enlace

Autenticación requerida

Copiar como Markdown
Versión v2 · Vigente. Devuelve cada venta modificada completa. Se recomienda la v3.

Permite mantener una copia de las ventas sincronizada sin volver a leerlas todas. Cada llamado devuelve las ventas que se crearon, modificaron o eliminaron después de una marca de posición (trxid), y la marca nueva (ultimaTrxId) para pedir los cambios siguientes.

v2 y v3 detectan exactamente los mismos cambios y aceptan los mismos filtros; solo cambia cuánto devuelven de cada venta. En v2, cada elemento de ventasNovedades es la venta completa, con el mismo formato que Lectura v2 (/data/cmd/ventas/api/v2/get), ordenadas por fecha de creación (no por momento del cambio). Conviene si se necesita el detalle de todas las ventas modificadas en un único llamado; si no, usar v3, que responde más liviano y deja pedir el detalle solo de las ventas que interesan.

Es una lectura: GET con los parámetros en la query string. Como todo comando, acepta también POST con los mismos parámetros en un body JSON. Todos los parámetros son opcionales.

Ejemplo: primer llamado y llamado siguiente con la marca recibida:

GET https://<sitioweb>/data/cmd/ventas/api/v2/cambios?pagesize=200

GET https://<sitioweb>/data/cmd/ventas/api/v2/cambios?trxid=17906029381234560&pagesize=200
Cómo sincronizar
Primer llamado: sin trxid. Se recorre desde el cambio más antiguo que conserva el registro. Si antes se hizo una carga completa con Lectura, se puede empezar con fechacambio = la fecha y hora en que empezó esa carga.
Procesar: cada venta de ventasNovedades se trata como "reemplazar la venta con este id" (la respuesta no distingue altas de modificaciones); cada una de ventasEliminadas es una baja: ya no existe y no se puede consultar con Lectura.
Guardar la marca: tomar ultimaTrxId y guardarla después de procesar la respuesta, así un error a mitad de camino no hace perder cambios.
Seguir: volver a llamar enseguida con la marca nueva en trxid, hasta que la respuesta traiga las dos listas vacías (en ese caso ultimaTrxId es igual a la marca enviada). Recién ahí se está al día: esperar un intervalo (por ejemplo, unos minutos) y volver a consultar. Si una respuesta trae menos de pagesize elementos entre las dos listas, tampoco quedan cambios pendientes por ahora.
Cada venta aparece una sola vez por respuesta, con su último cambio. Si se vuelve a modificar, reaparece en un llamado posterior.
Qué cambios se detectan
Un registro de cambios que mantiene la base de datos: cada alta, modificación o baja de la venta, o de sus ítems (VentaItem), descuentos e impuestos de ítems, combos, autorizaciones (VentaAutorizacion) y comprobantes (VentaComprobante), y cada ítem eliminado (VentaItemDeleted), marca la venta como cambiada en ese instante. Detecta también las ventas recién creadas que no se volvieron a modificar.

Nota: fechacreaciondesde tiene valor por defecto: si no se envía, no se informan los cambios de ventas creadas hace más de 30 días, aunque se hayan modificado hoy (por ejemplo, una venta vieja que se anula o se factura tarde), ni sus bajas. Si eso importa, enviar siempre una fecha fija anterior.

Nota: el registro de cambios se depura todos los días y conserva solo los últimos 30 días. Si una integración deja de consultar más de 30 días, pierde las bajas y modificaciones de ese período: hay que hacer una carga completa con Lectura y seguir con fechacambio.

Nota: las ventas cuyo registro de cambios no tiene la fecha de creación no se informan. Puede pasar con registros anteriores a la actualización que incorporó este mecanismo (por ejemplo, ventas eliminadas antes de esa actualización); para las ventas nuevas la fecha se guarda siempre al crearlas.

Nota: una marca inválida (vacía, con letras, mal copiada) no da error: reinicia la sincronización desde el principio. Validar que la marca guardada sea un número antes de enviarla.

Nota: pagesize es un tamaño objetivo y no un tope. El registro de cambios guarda los instantes con precisión de un segundo: si varios ventas cambian en el mismo instante que el último de la página, la respuesta los incluye a todos y puede traer más de pagesize elementos. Así la marca nunca queda en medio de un grupo de cambios simultáneos. Los cambios del segundo en curso no se informan hasta que ese segundo termina; aparecen en el llamado siguiente. Queda expuesto solo el cambio de una operación larga que se confirma después de que ya se consultó su instante: para cubrirlo, enviar la marca con un pequeño margen hacia atrás (por ejemplo, restarle 600000000, que equivale a 1 minuto), descartando repetidos por id, y hacer periódicamente (por ejemplo, una vez por día) una carga completa con Lectura.

Nota: zona horaria. trxid y ultimaTrxId están siempre en UTC (el registro de cambios guarda los instantes en UTC), así que no dependen de la zona horaria del servidor. fechacambio se interpreta en la hora local del servidor y se convierte a UTC.

Nota: esta versión antes detectaba los cambios con el historial de tablas de la base de datos; ahora usa el registro de cambios, con el mismo contrato. Detecta más casos que antes (comprobantes, autorizaciones, ítems eliminados y ventas recién creadas) y ya no depende de que el historial no se haya depurado.

Todas las versiones
Versión	URL	Estado
v2	/data/cmd/ventas/api/v2/cambios	Vigente. Marca trxid → ultimaTrxId. Devuelve cada venta modificada completa, con el formato de Lectura v2.
v3	/data/cmd/ventas/api/v3/cambios	Vigente (recomendada). Marca position → lastPosition. Devuelve solo la referencia de cada venta modificada.
No existe una v1. La v4 se eliminó: su implementación pasó a ser la v3, con el mismo contrato.

Parámetros de consulta
trxid
Tipo:string
Ejemplo
Copiar enlace a trxid
Marca de posición: el valor de ultimaTrxId del llamado anterior. Es un número enviado como string: cantidad de intervalos de 100 nanosegundos (ticks) desde el 01/01/1970 00:00 UTC. Se devuelven los cambios estrictamente posteriores a ese instante. Si no se envía, o no es un número, se toma el 01/01/1970, sin error: se recorre todo lo que conserva el registro de cambios (ver nota). No conviene interpretarla: solo guardarla y reenviarla.

fechacambio
Tipo:string
Copiar enlace a fechacambio
Alternativa a trxid: se devuelven los cambios posteriores a esta fecha y hora (hora local del servidor). Útil para el primer llamado después de una carga completa. No enviar junto con trxid.

fechacreaciondesde
Tipo:string
Copiar enlace a fechacreaciondesde
Solo se informan las ventas creadas en el sistema en esta fecha o después (fecha de alta del registro, no fechaPedido). Se aplica también a las eliminadas. Por defecto, 30 días antes del momento del llamado (ver nota).

pagesize
Tipo:integer
mín.:  
1
máx.:  
1000
Predeterminado
Copiar enlace a pagesize
Cantidad objetivo de elementos por respuesta, sumando novedades y eliminadas. Si varios cambios caen en el mismo instante que el último incluido, se incluyen todos y la respuesta puede superar pagesize (ver nota). Default 50, rango 1 a 1000. Fuera de ese rango (incluido 0) responde 400 ("El parametro PageSize debe estar en el rango [1;1000]"). No usa pagestoskip ni pagestotake: se avanza con la marca.

Respuestas

200
Objeto con la marca y las dos listas. Si no hubo cambios, las listas vienen vacías y ultimaTrxId repite la marca enviada.
application/json

400
pagesize fuera del rango 1 a 1000 ("El parametro PageSize debe estar en el rango [1;1000]"), o un parámetro con formato inválido (por ejemplo una fecha).
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v2/cambios
Shell Curl
curl 'https://sitio.gescom.online/data/cmd/ventas/api/v2/cambios?trxid=17906029381234560&pagesize=50' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v2/cambios)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "ultimaTrxId": "17906029381234560",
  "ventasNovedades": [
    {
      "id": 2,
      "estado": "Pendiente",
      "etapa": "Facturacion",
      "etapaNota": null,
      "requiereAutorizacion": false,
      "cerrada": false,
      "origen": "gcw",
      "ventaReferenciada": {
        "id": 1,
        "numeroComprobante": 1,
        "origen": "gcw",
        "identificador": null,
        "codigoEmpresa": "E1",
        "codigoPuntoVenta": 3,
        "codigoTipoComprobante": "FAC-A"
      },
      "numeroComprobante": 2,
      "motivo": "Sin Dinero",
      "items": [
        {
          "orden": 0,
          "ventaItemID": 15,
          "itemID": 812,
          "codigoItem": "300030783",
          "codigoAlicuotaIva": "I21",
          "codigoListaPrecio": "1",
          "codigoDeposito": "PRI",
          "codigoLote": null,
          "codigoCombo": null,
          "codigoComboComp": null,
          "cantidad": 123,
          "codigoUnidad": "Unidad",
          "unidadFactor": 1,
          "piezas": null,
          "precioUnitario": 11.54,
          "precioUnitarioIva": 2.4234,
          "precioUnitarioTotal": 13.9634,
          "precioCosto": 8.1,
          "descuento": 0.1744,
          "descuentoNeto": 2.012576,
          "descuentoFinal": 2.43521696,
          "descuentos": [
            {
              "descuentoFuenteId": null,
              "descuento": 0.1744,
              "descuentoDetalle": null,
              "otorgadoPorPromocion": true,
              "promocionId": 44,
              "comboComponenteId": null,
              "propiedades": {}
            }
          ],
          "numeroSerie": null,
          "estadoPesaje": 0,
          "importeNeto": 1171.873152,
          "importeExento": 0,
          "importeConc": 0,
          "importeIva": 246.09336192,
          "importeTributos": 15129,
          "importeTotal": 16546.96651392,
          "comentario": null,
          "propiedades": {}
        }
      ],
      "importeNeto": 1171.873152,
      "importeExento": 0,
      "importeConc": 0,
      "importeIva": 246.09336192,
      "importeTributos": 15129,
      "importeTotal": 16546.96651392,
      "codigoReparto": 1,
      "codigoChofer": "21",
      "comprobantePrincipal": null,
      "esCredito": true,
      "esSinCargo": false,
      "tags": [],
      "propiedades": {},
      "identificador": null,
      "codigoTipoVenta": "DEV-RE",
      "codigoCliente": "4517",
      "codigoVendedor": "1",
      "codigoRuta": "99",
      "codigoEmpresa": "E1",
      "codigoPuntoVenta": 3,
      "codigoSede": "1",
      "codigoCondicionPago": "15D",
      "codigoMotivoCambio": "2",
      "fechaPedido": "2023-03-10T12:15:45-03:00",
      "fechaEntrega": null,
      "observaciones": null,
      "observacionesInternas": null,
      "descuentoGlobal": 0.14,
      "combos": [],
      "ventaDirecta": false,
      "metodoEntrega": 0,
      "loteId": null
    }
  ],
  "ventasEliminadas": [
    {
      "id": 9,
      "numeroComprobante": 9,
      "origen": "gcw",
      "identificador": null
    }
  ]
}

Objeto con la marca y las dos listas. Si no hubo cambios, las listas vienen vacías y ultimaTrxId repite la marca enviada.

Avance de ventas​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve el avance de ventas de cada vendedor respecto de los objetivos del mes: un elemento por vendedor, con sus objetivos y, dentro de cada objetivo, un renglón por grupo de artículos (tag) con el valor objetivo, lo acumulado y los indicadores de avance.

Los datos los calcula un proceso nocturno (a las 3 AM, con datos hasta el día anterior) y se guardan por mes: la API solo lee lo ya calculado, no recalcula nada. Por eso el día 1 de cada mes, antes de que corra el proceso, el mes actual devuelve []; y un mes cerrado no se vuelve a calcular pasado el quinto día hábil, así que lo que se corrija después no entra.

La API tiene que estar habilitada para el tenant (hay que comunicarse con soporte) y el cliente debe tener instalado el proceso que arma los datos. Si no lo tiene, o el mes todavía no se calculó, responde [], no un error: desde fuera "sin proceso" y "sin datos" se ven igual.

Todos los parámetros son opcionales. Las listas de códigos (VendedorCodigo, SupervisorCodigo) se envían separadas por coma, admiten hasta 100 valores (con más responde 400) y un código que no existe no da error: simplemente no devuelve nada. No distingue mayúsculas en los nombres de los parámetros. No tiene paginación (son unos cientos de filas por mes).

Ejemplo: avance de importe (Medida=1) de agosto de 2026 de dos vendedores, con la variante PEPSICO:

GET https://<sitioweb>/data/cmd/ventas/api/v1/get-avance-ventas?PeriodoDesde=2026-08&Variante=PEPSICO&Medida=1&VendedorCodigo=8,13
Cómo leer los indicadores (todos los días cuentan hasta ayer):

acumulado: lo vendido en el mes según la fecha de entrega.
promedio = acumulado / diasTrabajados.
tendencia = acumulado / diasTrabajados × diasHabiles: a cuánto llegaría el mes al ritmo actual.
avance = tendencia / valorObjetivo × 100. Es el porcentaje de la tendencia, no del acumulado, y puede superar 100 (también valores muy altos si el objetivo es chico).
mediaNecesaria = (valorObjetivo − acumulado) / (diasHabiles − diasTrabajados): lo que hay que vender por día restante para llegar al objetivo. Es negativa si el objetivo ya se superó.
ultimaVisita, penultimaVisita y real: venta del día de referencia menos 7, menos 14 y del propio día, por fecha de creación (no de entrega).
Los importes pueden venir negativos (las notas de crédito superan a las ventas) y se devuelven tal cual.

Parámetros de consulta
PeriodoDesde
Tipo:string
Copiar enlace a PeriodoDesde
Mes a consultar, con formato yyyy-MM (por ejemplo 2026-08). Si no se envía, el mes actual. No se acepta una fecha completa (2026-08-01 responde 400). Un mes que nunca se calculó devuelve [].

Variante
Tipo:"GENERAL" or "PEPSICO"
enum
Copiar enlace a Variante
Cálculo a consultar: GENERAL o PEPSICO (no distingue mayúsculas; otro valor responde 400). Si no se envía y el mes tiene una sola variante, se usa esa; si tiene más de una responde 400 con el mensaje "El periodo tiene mas de una variante (GENERAL, PEPSICO): indicar Variante", para no mezclar números de dos cálculos distintos. PEPSICO excluye los tags de taxonomía y es la única que calcula acumuladoMN.

Medida
Tipo:integer
enum
Copiar enlace a Medida
Medida del objetivo: 1 Importe, 2 Cantidad, 3 Peso, 4 Volumen. Si no se envía, todas las medidas. Otro valor responde 400. Un objetivo con dos medidas aparece dos veces en la respuesta, una por medida.

valores
1
2
3
4
VendedorCodigo
Tipo:array of string
Copiar enlace a VendedorCodigo
Códigos de vendedor (máximo 100). Con un solo valor funciona igual.

SupervisorCodigo
Tipo:array of string
Copiar enlace a SupervisorCodigo
Códigos de supervisor (máximo 100). Deja afuera a los vendedores sin supervisor asignado en la variante PEPSICO (esa variante los guarda con supervisor nulo).

IncluirMN
Tipo:boolean
Predeterminado
Copiar enlace a IncluirMN
true: agrega acumuladoMN a cada grupo. Solo lo calcula la variante PEPSICO; con GENERAL sale null. Sin este parámetro (o con false) el campo no aparece en la respuesta. Solo se aceptan true y false: 1, vacío u otro valor responden 400.

Respuestas

200
Array con un elemento por vendedor, ordenado por nombre de vendedor; los objetivos por objetivo y medida; los grupos por código de grupo. Si no hay datos devuelve [].
application/json

400
Parámetro inválido. Mensajes: "PeriodoDesde debe tener el formato yyyy-MM (por ejemplo 2026-08)"; "Variante debe ser GENERAL o PEPSICO"; "Medida debe ser 1 (Importe), 2 (Cantidad), 3 (Peso) o 4 (Volumen)"; "La cantidad máxima de elementos en la lista VendedorCodigo es 100"; "El periodo tiene mas de una variante (...): indicar Variante". Un IncluirMN o Medida con un tipo que no corresponde (IncluirMN=1, Medida=abc) responde con el mensaje del deserializador (por ejemplo "Could not convert string to boolean: 1. Path 'IncluirMN'.").
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/ventas/api/v1/get-avance-ventas
Shell Curl
curl 'https://sitio.gescom.online/data/cmd/ventas/api/v1/get-avance-ventas?Variante=GENERAL&Medida=1&IncluirMN=false' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/ventas/api/v1/get-avance-ventas)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "periodoDesde": "2026-08-01",
    "fechaReferencia": "2026-08-26",
    "vendedorCodigo": "8",
    "vendedorNombre": "RF Juan I. Biurrun",
    "supervisorCodigo": "60018",
    "supervisorNombre": "G.Arroyo Pep RDF/JVG",
    "diasHabiles": 25,
    "diasTrabajados": 21,
    "objetivos": [
      {
        "objetivoCodigo": "19",
        "objetivoDescripcion": "AGOSTO 26 PGA/DREAMCO/OTROS",
        "medida": 1,
        "medidaDescripcion": "Importe",
        "grupos": [
          {
            "grupoCodigo": "dreamco",
            "grupoNombre": "1-Dreamco objetivo",
            "valorObjetivo": 8500000,
            "acumulado": 10584851.07,
            "acumuladoMN": 0,
            "tendencia": 12601013.17,
            "avance": 148.25,
            "promedio": 504040.53,
            "mediaNecesaria": -521212.77,
            "ultimaVisita": 231838.46,
            "penultimaVisita": 273872.8,
            "real": 0
          }
        ]
      },
      {
        "objetivoCodigo": "20",
        "objetivoDescripcion": "OBJETIVO PEPSICO AGOSTO 2026",
        "medida": 3,
        "medidaDescripcion": "Peso",
        "grupos": [
          {
            "grupoCodigo": "*P01",
            "grupoNombre": "Salty Platino + Gold Prop. 2022",
            "valorObjetivo": 1480,
            "acumulado": 1054.25,
            "acumuladoMN": 999.47,
            "tendencia": 1255.06,
            "avance": 84.8,
            "promedio": 50.2,
            "mediaNecesaria": 106.44,
            "ultimaVisita": 77.9,
            "penultimaVisita": 64.62,
            "real": 0
          }
        ]
      }
    ]
  }
]

Array con un elemento por vendedor, ordenado por nombre de vendedor; los objetivos por objetivo y medida; los grupos por código de grupo. Si no hay datos devuelve [].

Compras ​Copiar enlace
ComprasOperaciones
get
/data/cmd/compras/api/v1/get-proveedores
get
/data/cmd/compras/api/v1/get
get
/data/cmd/compras/api/v1/get-impuestos-compra
Proveedores​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve los proveedores activos con sus datos de contacto y fiscales vigentes. Los proveedores inactivos no se devuelven, aunque se pida su código.

No acepta paginación: siempre devuelve el listado completo. No hay límite para la cantidad de códigos.

Ejemplo: proveedores con código 1 y 100:

GET https://<sitioweb>/data/cmd/compras/api/v1/get-proveedores?codigos=1,100
Nota: los códigos se comparan tal cual se envían, sin quitar espacios: codigos=1, 100 busca el código " 100" (con un espacio adelante) y no lo encuentra. Enviar la lista sin espacios. Para obtener todos los proveedores, omitir el parámetro en lugar de enviarlo vacío.

El orden de los resultados no está garantizado.

Parámetros de consulta
codigos
Tipo:array of string
Copiar enlace a codigos
Códigos de proveedor separados por coma. Sin este parámetro devuelve todos los proveedores activos. Los códigos que no existen se ignoran.

Respuestas

200
Array de proveedores. Si ningún código coincide devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/compras/api/v1/get-proveedores
Shell Curl
curl https://sitio.gescom.online/data/cmd/compras/api/v1/get-proveedores \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/compras/api/v1/get-proveedores)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "100",
    "nombre": "Pepsico de Argentina SRL",
    "direccion": "REMEDIOS DE ESCALADA 2900",
    "telefono": null,
    "localidad": "LANUS",
    "codigoTipoDocumento": "80",
    "codigoCondicionIva": "INS",
    "email": null,
    "provincia": "Buenos Aires",
    "codigoCondicionPago": "15D",
    "codigoPostal": "1822",
    "nroDocumento": "30-53764771-6",
    "contacto": null,
    "tags": [
      "Pepsico"
    ],
    "comentario": "---",
    "notas": null
  }
]

Array de proveedores. Si ningún código coincide devuelve [].

Compras​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve las compras cargadas en el sistema con sus ítems, importes netos por alícuota de IVA e impuestos, ordenadas por fecha de carga (de la más antigua a la más nueva; a igual fecha, por id).

Todos los parámetros son opcionales. Sin filtros devuelve las primeras 500 compras. Cada lista admite hasta 100 valores; con más responde 400. Los parámetros de paginación no pueden ser negativos.

Los totales de la compra (importeNeto, importeExento, importeConc, importeIva, importeTributos e importeTotal) se calculan con importes e impuestos, con la misma clasificación que el libro de IVA compras, y no dependen de incluiritems. Los importes se devuelven tal como están guardados: en una nota de crédito no se invierte el signo.

Con incluiritems=false la respuesta trae items vacío y responde más rápido: conviene cuando solo se necesitan los importes (por ejemplo, para conciliar contra ARCA con codigoTipoDocumentoProveedor y nroDocumentoProveedor).

Ejemplo: compras del proveedor 223 cargadas entre el 1 y el 5 de enero de 2025 inclusive:

GET https://<sitioweb>/data/cmd/compras/api/v1/get?fechadesde=2025-01-01&fechahasta=2025-01-05T23:59:59&proveedores=223
Ejemplo: compras de septiembre de 2026 por período de imputación, sin ítems:

GET https://<sitioweb>/data/cmd/compras/api/v1/get?periodoimputacionmes=9&periodoimputacionanio=2026&incluiritems=false
Parámetros de consulta
pagesize
Tipo:integer
mín.:  
1
máx.:  
500
Predeterminado
Copiar enlace a pagesize
Registros por página. Default y máximo: 500.

pagestoskip
Tipo:integer
mín.:  
0
Predeterminado
Copiar enlace a pagestoskip
Páginas a saltear. Default 0.

pagestotake
Tipo:integer
mín.:  
1
máx.:  
2
Predeterminado
Copiar enlace a pagestotake
Páginas a traer. Default 1, máximo 2.

fechadesde
Tipo:string
Copiar enlace a fechadesde
Compras con fecha de carga mayor o igual a este valor.

fechahasta
Tipo:string
Copiar enlace a fechahasta
Compras con fecha de carga menor o igual a este valor (ver Convenciones → Fechas).

fechacomprobantedesde
Tipo:string
Copiar enlace a fechacomprobantedesde
Compras con fecha de comprobante mayor o igual a este día (se comparan solo las fechas).

fechacomprobantehasta
Tipo:string
Copiar enlace a fechacomprobantehasta
Compras con fecha de comprobante menor o igual a este día, inclusive (el día completo). No puede ser anterior a fechacomprobantedesde (400).

periodoimputacionmes
Tipo:integer
mín.:  
1
máx.:  
12
Copiar enlace a periodoimputacionmes
Mes (1 a 12) del período de imputación. Se envía junto con periodoimputacionanio; uno solo responde 400.

periodoimputacionanio
Tipo:integer
Copiar enlace a periodoimputacionanio
Año del período de imputación. Se envía junto con periodoimputacionmes.

ids
Tipo:array of integer
Copiar enlace a ids
Ids internos de compra. Un valor no numérico responde 400.

empresas
Tipo:array of string
Copiar enlace a empresas
Códigos de empresa.

proveedores
Tipo:array of string
Copiar enlace a proveedores
Códigos de proveedor.

sedes
Tipo:array of string
Copiar enlace a sedes
Códigos de sede.

tiposcomprobantes
Tipo:array of string
Copiar enlace a tiposcomprobantes
Códigos de tipo de comprobante.

incluiritems
Tipo:boolean
Predeterminado
Copiar enlace a incluiritems
false: items viene vacío ([]). Los importes, impuestos y totales no cambian. Default true.

Respuestas

200
Array de compras. Si no hay resultados devuelve [].
application/json

400
pagesize > 500, pagestotake > 2, parámetros de paginación negativos, pagestoskip demasiado grande para el tamaño de página, una lista con más de 100 valores, un valor de ids no numérico, fechacomprobantedesde posterior a fechacomprobantehasta, o un período de imputación incompleto o fuera de rango.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/compras/api/v1/get
Shell Curl
curl 'https://sitio.gescom.online/data/cmd/compras/api/v1/get?pagesize=500&pagestoskip=0&pagestotake=1&incluiritems=true' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/compras/api/v1/get)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "codigoProveedor": "223",
    "codigoTipoDocumentoProveedor": "CUIT",
    "nroDocumentoProveedor": "30-12345678-9",
    "fechaCarga": "2024-12-11T14:42:18-03:00",
    "fechaComprobante": "2024-12-11T00:00:00-03:00",
    "periodoImputacion": "2024-12-01T00:00:00-03:00",
    "codigoTipoDeComprobante": "FAC-A",
    "codigoPuntoVenta": 163,
    "numeroComprobante": 13692,
    "codigoEmpresa": "1",
    "codigoSede": "1",
    "comentario": null,
    "items": [
      {
        "codigoItem": "11314",
        "codigoDeposito": "DEP1",
        "cantidad": 10,
        "codigoUnidad": "Pack",
        "unidadFactor": 16,
        "piezas": null,
        "codigoLote": null,
        "numeroSerie": null,
        "importeTotal": 571224.9312
      }
    ],
    "importes": [
      {
        "codigoTipoNeto": "NET",
        "codigoAlicuotaIva": "I21",
        "porcentajeAlicuotaIva": 0.21,
        "importeNeto": 11000000,
        "importeIva": 2310000
      }
    ],
    "impuestos": [
      {
        "codigoImpuesto": "PIB",
        "descripcionImpuesto": "Percepción IIBB",
        "codigoTipoImpuesto": "PERC-IIBB",
        "codigoFeTipoImpuesto": 7,
        "importe": 955106.19
      }
    ],
    "importeNeto": 11000000,
    "importeExento": 0,
    "importeConc": 0,
    "importeIva": 2310000,
    "importeTributos": 955106.19,
    "importeTotal": 14265106.19
  }
]

Array de compras. Si no hay resultados devuelve [].

Impuestos de compra​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve todos los impuestos de compra cargados en el sistema e indica cuáles están habilitados para retenciones. Sirve para completar codigoImpuesto en las retenciones de Generación de cobros (v2): solo se aceptan los que tienen esRetencion: true.

No recibe parámetros. No pagina: devuelve la lista completa, incluidos los impuestos que no son de retención.

GET https://<sitioweb>/data/cmd/compras/api/v1/get-impuestos-compra
El resultado no tiene un orden definido.

Respuestas

200
Array con todos los impuestos de compra. Si no hay ninguno devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/compras/api/v1/get-impuestos-compra
Shell Curl
curl https://sitio.gescom.online/data/cmd/compras/api/v1/get-impuestos-compra \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/compras/api/v1/get-impuestos-compra)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "RIIBB",
    "descripcion": "Retención IIBB",
    "esRetencion": true
  },
  {
    "codigo": "PIVA",
    "descripcion": "Percepción IVA",
    "esRetencion": false
  }
]

Array con todos los impuestos de compra. Si no hay ninguno devuelve [].

Distribución ​Copiar enlace
DistribuciónOperaciones
get
/data/cmd/distribucion/api/v1/get-ordenespreparacion
post
/data/cmd/distribucion/api/v1/create-entrada-reparto
post
/data/cmd/distribucion/api/v1/set-preparacion-venta
get
/data/cmd/distribucion/api/v1/get-repartos
get
/data/cmd/distribucion/api/v2/get-repartos
post
/data/cmd/distribucion/api/v1/asignar-ventas-por-vehiculo
get
/data/cmd/distribucion/api/v1/reparto/cambios
get
/data/cmd/distribucion/api/v2/reparto/cambios
get
/data/cmd/distribucion/api/v1/get-precarga-valores
Órdenes de Preparación​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve las órdenes de preparación (armado de pedidos en depósito) creadas en un rango de fechas, con el preparador asignado y las ventas que incluye cada orden y su estado de preparación.

fechadesde y fechahasta son obligatorios: si falta alguno de los dos la respuesta viene vacía (no da error). El resto de los parámetros son opcionales.

Las listas se envían separadas por coma, sin espacios. No tienen límite de valores. Un valor no numérico en ordenId o ventaId responde 400.

Nota: la paginación de este endpoint funciona distinto que en el resto de la API (ver Convenciones → Paginación). pagestotake indica el número de página y pagestoskip se ignora. Para recorrer todo el listado: pedir pagestotake=1, leer totalPaginas y seguir con pagestotake=2, 3, … hasta totalPaginas. pagesize no tiene máximo validado. Ojo: un pagestotake mayor a totalPaginas no devuelve vacío sino la última página, así que no conviene usar "respuesta vacía" como condición de corte.

Ejemplo: órdenes creadas el 30 de marzo de 2026, del preparador 20000, con las ventas ya preparadas:

GET https://<sitioweb>/data/cmd/distribucion/api/v1/get-ordenespreparacion?fechadesde=2026-03-30&fechahasta=2026-03-30T23:59:59&bodeguistaCodigo=20000&estadoVenta=1
A diferencia de otros listados, la respuesta no es un array sino un objeto:

También se devuelven las ventas que no tienen empresa asignada: vienen con empresa en null y comprobante sin el código de empresa adelante.

Las páginas se arman con las órdenes de id más alto primero (las más nuevas). El orden de las órdenes dentro de la respuesta y el de las ventas dentro de cada orden no está garantizado.

Nota: fechaArmado existe en la respuesta pero hoy el sistema no lo completa: viene siempre en null. No usarlo para saber si una orden se terminó de armar; usar estado.

Parámetros de consulta
fechadesde
Tipo:string
obligatorio
Ejemplo
Copiar enlace a fechadesde
Órdenes con fecha de creación mayor o igual a este valor.

fechahasta
Tipo:string
obligatorio
Ejemplo
Copiar enlace a fechahasta
Órdenes con fecha de creación menor o igual a este valor (ver Convenciones → Fechas).

ordenId
Tipo:array of integer
Copiar enlace a ordenId
Ids de orden de preparación.

ventaId
Tipo:array of integer
Copiar enlace a ventaId
Ids de venta. Devuelve las órdenes que contienen esas ventas y, dentro de cada orden, solo esas ventas.

bodeguistaCodigo
Tipo:array of string
Copiar enlace a bodeguistaCodigo
Códigos de empleado del preparador (bodeguista).

estadoVenta
Tipo:integer
Copiar enlace a estadoVenta
Estado de preparación de la venta dentro de la orden: 0 sin preparar, 1 preparada, 2 preparada incompleta, 3 en preparación, 99 cancelada. Sin este parámetro trae todos. Como ventaId, filtra las ventas de cada orden: una orden sin ventas en ese estado no se devuelve.

pagesize
Tipo:integer
Copiar enlace a pagesize
Órdenes por página. Default 500.

pagestotake
Tipo:integer
Copiar enlace a pagestotake
Número de página a devolver, empezando en 1. Default 1. Si es mayor que la cantidad de páginas, devuelve la última (ver nota).

Respuestas

200
Objeto con la página de órdenes y los totales. Si no hay resultados, ordenesPreparacion es [].
application/json

400
Un valor de ordenId o ventaId no numérico.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/distribucion/api/v1/get-ordenespreparacion
Shell Curl
curl 'https://sitio.gescom.online/data/cmd/distribucion/api/v1/get-ordenespreparacion?fechadesde=2026-09-01&fechahasta=2026-09-30' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/distribucion/api/v1/get-ordenespreparacion)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "ordenesPreparacion": [
    {
      "id": 12211,
      "estado": "Orden Cerrada",
      "fechaCarga": "2026-03-27T12:39:49-03:00",
      "fechaCreacion": "2026-03-30T07:18:47-03:00",
      "fechaArmado": null,
      "bodeguista": "20000",
      "nombreBodeguista": "MOLINA JUAN",
      "ventas": [
        {
          "ventaID": 151339,
          "empresa": "1",
          "puntoVenta": 6,
          "tipoVenta": "VEN",
          "numeroComprobante": 151339,
          "comprobante": "1 0006-00151339",
          "estadoVenta": "Preparado"
        },
        {
          "ventaID": 151347,
          "empresa": "1",
          "puntoVenta": 6,
          "tipoVenta": "VEN",
          "numeroComprobante": 151347,
          "comprobante": "1 0006-00151347",
          "estadoVenta": "Preparado"
        }
      ]
    }
  ],
  "message": "Se obtuvieron 1 registros de 1 totales.",
  "totalRegistros": 1,
  "paginaActual": 1,
  "totalPaginas": 1
}

Objeto con la página de órdenes y los totales. Si no hay resultados, ordenesPreparacion es [].

Recomendada
Cambios de repartos (v2)​Copiar enlace

Autenticación requerida

Copiar como Markdown
Versión v2 · Vigente (recomendada). Devuelve solo los ids de los repartos que cambiaron.

Sincronización incremental de repartos: en lugar de volver a pedir todos los repartos, se piden solo los que cambiaron después de una marca de posición (trxid). La respuesta trae los ids de los repartos creados o modificados, los de los eliminados y la marca nueva (ultimaTrxId) para el llamado siguiente.

v1 y v2 detectan exactamente los mismos cambios y aceptan los mismos parámetros, incluido fechadesde; solo cambia cuánto devuelven de cada reparto. En v2, repartosNovedades es una lista de ids, ordenada por momento del cambio, y el detalle se pide después con Repartos v2 (/data/cmd/distribucion/api/v2/get-repartos?ids=..., hasta 100 ids por llamado), solo de los repartos que interesan. Usar v2 en integraciones nuevas: responde rápido y liviano aun con pagesize alto.

Si ya usabas esta v2: cambió de forma incompatible. Antes repartosNovedades traía los repartos completos (con el formato de Repartos v1) e ignoraba fechadesde; ahora trae solo ids ([12, 15]) y aplica fechadesde (por defecto, los últimos 30 días). Para seguir recibiendo los repartos completos en la misma respuesta, cambiá la URL a la v1.

Es una lectura: GET con los parámetros en la query string. Como todo comando, acepta también POST con los mismos parámetros en un body JSON. Todos los parámetros son opcionales.

Ejemplo: primer llamado y llamado siguiente con la marca recibida:

GET https://<sitioweb>/data/cmd/distribucion/api/v2/reparto/cambios?fechacambio=2026-09-28T10:00:00&pagesize=1000

GET https://<sitioweb>/data/cmd/distribucion/api/v2/reparto/cambios?trxid=17906029381234560&pagesize=1000
Cómo sincronizar
Primer llamado: sin trxid. Se recorre desde el cambio más antiguo que conserva el registro. Si antes se hizo una carga completa con Repartos, se puede empezar con fechacambio = la fecha y hora en que empezó esa carga.
Procesar: pedir con Repartos v2 los repartos de repartosNovedades (en tandas de hasta 100 ids) y reemplazar el reparto guardado con cada id (o agregarlo si no existe). Por cada id de repartosEliminados, borrar ese reparto. Procesar dos veces el mismo reparto no causa problemas.
Guardar la marca: tomar ultimaTrxId y guardarlo después de procesar la respuesta, así un error a mitad de camino no hace perder cambios.
Seguir: volver a llamar enseguida con la marca nueva en trxid, hasta que la respuesta traiga las dos listas vacías (en ese caso ultimaTrxId es igual a la marca enviada). Recién ahí se está al día: esperar al próximo ciclo (por ejemplo, cada 1 a 5 minutos). Si una respuesta trae menos de pagesize elementos entre las dos listas, tampoco quedan cambios pendientes por ahora.
Cada reparto aparece una sola vez por respuesta, con su último cambio.
Qué cambios se detectan
Un registro de cambios que mantiene la base de datos: cada alta, modificación o baja del reparto, de sus ventas asignadas (RepartoVenta: agregar, quitar o modificar una venta del reparto), de sus autorizaciones, de sus entradas (RepartoEntrada y sus ítems) y de su rendición marca el reparto como cambiado en ese instante. Detecta también los repartos recién creados que no se volvieron a modificar.

Nota: fechadesde tiene valor por defecto: si no se envía, no se informan los cambios de repartos con fecha de hace más de 30 días, ni sus bajas. Si eso importa, enviar una fecha fija anterior.

Nota: el registro de cambios se depura todos los días y conserva solo los últimos 30 días. Si una integración deja de consultar más de 30 días, pierde las bajas y modificaciones de ese período: hay que hacer una carga completa con Repartos y seguir con fechacambio.

Nota: los repartos cuyo registro de cambios no tiene la fecha del reparto no se informan. Afecta a los repartos eliminados antes de la actualización que incorporó este mecanismo; para los repartos nuevos la fecha se guarda siempre al crearlos.

Nota: una marca inválida (vacía, con letras, mal copiada) no da error: reinicia la sincronización desde el principio.

Nota: pagesize es un tamaño objetivo y no un tope. El registro de cambios guarda los instantes con precisión de un segundo: si varios repartos cambian en el mismo instante que el último de la página, la respuesta los incluye a todos y puede traer más de pagesize elementos. Así la marca nunca queda en medio de un grupo de cambios simultáneos. Los cambios del segundo en curso no se informan hasta que ese segundo termina; aparecen en el llamado siguiente. Queda expuesto solo el cambio de una operación larga que se confirma después de que ya se consultó su instante: para cubrirlo, enviar la marca con un pequeño margen hacia atrás (por ejemplo, restarle 600000000, que equivale a 1 minuto), descartando repetidos por id, y hacer periódicamente (por ejemplo, una vez por día) una carga completa con Repartos.

Nota: zona horaria. trxid y ultimaTrxId están siempre en UTC (el registro de cambios guarda los instantes en UTC), así que no dependen de la zona horaria del servidor. fechacambio se interpreta en la hora local del servidor y se convierte a UTC.

Todas las versiones
Versión	URL	Estado
v1	/data/cmd/distribucion/api/v1/reparto/cambios	Vigente. Devuelve cada reparto modificado completo, con el formato de Repartos v1.
v2	/data/cmd/distribucion/api/v2/reparto/cambios	Vigente (recomendada). Devuelve solo los ids de los repartos modificados; el detalle se pide con Repartos v2.
Parámetros de consulta
trxid
Tipo:string
Ejemplo
Copiar enlace a trxid
Marca de posición: el valor de ultimaTrxId del llamado anterior. Es un número enviado como string: cantidad de intervalos de 100 nanosegundos (ticks) desde el 01/01/1970 00:00 UTC. Se devuelven los cambios estrictamente posteriores a ese instante. Si no se envía, o no es un número, se toma el 01/01/1970, sin error: se recorre todo lo que conserva el registro de cambios (ver nota). No conviene interpretarla: solo guardarla y reenviarla.

fechacambio
Tipo:string
Copiar enlace a fechacambio
Alternativa a trxid: se devuelven los cambios posteriores a esta fecha y hora (hora local del servidor). Útil para el primer llamado después de una carga completa. No enviar junto con trxid.

fechadesde
Tipo:string
Copiar enlace a fechadesde
Solo se informan los repartos con fecha (la fecha del reparto) mayor o igual a este valor. Se aplica también a los eliminados. Por defecto, 30 días antes del momento del llamado (ver nota).

pagesize
Tipo:integer
mín.:  
1
máx.:  
1000
Predeterminado
Copiar enlace a pagesize
Cantidad objetivo de elementos por respuesta, sumando novedades y eliminadas. Si varios cambios caen en el mismo instante que el último incluido, se incluyen todos y la respuesta puede superar pagesize (ver nota). Default 50, rango 1 a 1000. Fuera de ese rango (incluido 0) responde 400 ("El parametro PageSize debe estar en el rango [1;1000]"). No usa pagestoskip ni pagestotake: se avanza con la marca.

Respuestas

200
Objeto con la marca y las dos listas. Si no hubo cambios, las listas vienen vacías y ultimaTrxId repite la marca enviada.
application/json

400
pagesize fuera del rango 1 a 1000 ("El parametro PageSize debe estar en el rango [1;1000]"), o un parámetro con formato inválido (por ejemplo una fecha).
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/distribucion/api/v2/reparto/cambios
Shell Curl
curl 'https://sitio.gescom.online/data/cmd/distribucion/api/v2/reparto/cambios?trxid=17906029381234560&pagesize=50' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/distribucion/api/v2/reparto/cambios)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "ultimaTrxId": "17906029381234560",
  "repartosNovedades": [
    2,
    15
  ],
  "repartosEliminados": [
    1498,
    1502
  ]
}

Objeto con la marca y las dos listas. Si no hubo cambios, las listas vienen vacías y ultimaTrxId repite la marca enviada.

Precarga de valores de repartos​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve, para los repartos de un rango de fechas, los valores que el chofer declaró haber cobrado (transferencias, QR, etc.) antes de la rendición, con el nombre del cliente ya resuelto. Reemplaza el recorrido por reparto (Repartos + receta de valores de cada uno): filtra por tipo de valor y devuelve solo los repartos que tienen valores.

No es la rendición de tesorería: esta puede corregir lo que el chofer declaró.

fechadesde es obligatoria. Si el rango incluye más de 1000 repartos responde 400 y hay que acotarlo (con fechahasta, etapas o cerrado). Solo se devuelven los repartos que tienen al menos un valor de los tipos pedidos (todos, si no se envía tiposvalor), y de cada uno solo esos valores. Los repartos vienen ordenados por fecha. Pagina como el resto de la API (máximo 500 por página y 2 páginas por llamado).

Las listas (etapas, tiposvalor) se envían separadas por coma y admiten hasta 100 valores. Un tipo de valor que no existe no da error; una etapa inválida sí (400).

Ejemplo: transferencias y QR declarados por los choferes en los repartos del 1 al 7 de octubre de 2026 que están en rendición:

GET https://<sitioweb>/data/cmd/distribucion/api/v1/get-precarga-valores?fechadesde=2026-10-01&fechahasta=2026-10-07&etapas=Rendicion&tiposvalor=TRF,QR
Parámetros de consulta
pagesize
Tipo:integer
mín.:  
1
máx.:  
500
Predeterminado
Copiar enlace a pagesize
Registros por página. Default y máximo: 500.

pagestoskip
Tipo:integer
mín.:  
0
Predeterminado
Copiar enlace a pagestoskip
Páginas a saltear. Default 0.

pagestotake
Tipo:integer
mín.:  
1
máx.:  
2
Predeterminado
Copiar enlace a pagestotake
Páginas a traer. Default 1, máximo 2.

fechadesde
Tipo:string
obligatorio
Copiar enlace a fechadesde
Obligatoria. Repartos con fecha mayor o igual a este día (inclusive, por día).

fechahasta
Tipo:string
Copiar enlace a fechahasta
Repartos con fecha menor o igual a este día (inclusive, por día). Sin enviar: sin tope. No puede ser anterior a fechadesde (400).

etapas
Tipo:array of string
enum
Copiar enlace a etapas
Etapas del reparto separadas por coma (máximo 100): AsignacionPreparacion, RetiroReserva, EnTransito, Liquidacion, Rendicion. Sin enviar: todas. No distingue mayúsculas.

valores
AsignacionPreparacion
RetiroReserva
EnTransito
Liquidacion
Rendicion
cerrado
Tipo:boolean
Copiar enlace a cerrado
true: solo repartos cerrados. false: solo abiertos. Sin enviar: ambos.

tiposvalor
Tipo:array of string
Copiar enlace a tiposvalor
Códigos de tipo de valor, por ejemplo TRF,QR (máximo 100). Sin enviar: todos.

Respuestas

200
Array de repartos que tienen valores precargados. Si no hay ninguno devuelve [].
application/json

400
fechadesde ausente, fechadesde posterior a fechahasta, una etapa inválida, una lista con más de 100 valores, pagesize > 500, pagestotake > 2, o un rango con más de 1000 repartos.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/distribucion/api/v1/get-precarga-valores
Shell Curl
curl 'https://sitio.gescom.online/data/cmd/distribucion/api/v1/get-precarga-valores?pagesize=500&pagestoskip=0&pagestotake=1&fechadesde=' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/distribucion/api/v1/get-precarga-valores)
Estado:200
Estado:400
Estado:401
Estado:403

[
  {
    "repartoId": 4410,
    "codigoReparto": 1873,
    "nombreChofer": "Pérez, Juan",
    "fecha": "2026-10-05T00:00:00-03:00",
    "etapa": "Rendicion",
    "valores": [
      {
        "tipoValorCodigo": "TRF",
        "importe": 45300.5,
        "codigoCliente": "1300",
        "nombreCliente": "Almacén Don José",
        "cuit": "20-11222333-4",
        "nombre": "José García",
        "fechaEmision": "2026-10-05",
        "identificacion": "00458712"
      }
    ]
  }
]

Array de repartos que tienen valores precargados. Si no hay ninguno devuelve [].

Tesorería ​Copiar enlace
TesoreríaOperaciones
get
/data/cmd/tesoreria/api/v1/get-bancos
get
/data/cmd/tesoreria/api/v1/get-cajas
get
/data/cmd/ctacte/api/v1/get-ctacte-clientes
get
/data/cmd/ctacte/api/v2/get-ctacte-clientes
get
/data/cmd/ctacte/api/v1/get-ctacte-clientes-detalle
get
/data/cmd/ctacte/api/v2/get-ctacte-clientes-detalle
get
/data/cmd/ctacte/api/v3/get-ctacte-clientes-detalle
get
/data/cmd/ctacte/api/v4/get-ctacte-clientes-detalle
get
/data/cmd/tesoreria/api/v1/get-monedas
get
/data/cmd/tesoreria/api/v1/get-tipo-valor
post
/data/cmd/ctacte/api/v1/create-cobro
post
/data/cmd/ctacte/api/v2/create-cobro
get
/data/cmd/ctacte/api/v1/get-ctacte-proveedores
get
/data/cmd/ctacte/api/v1/get-ctacte-proveedores-detalle
get
/data/cmd/ctacte/api/v1/get-ctacte-proveedores-pagos
Bancos​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve los bancos activos cargados en el sistema. Los bancos inactivos no se devuelven, aunque se pida su código.

No acepta paginación: siempre devuelve el listado completo.

Ejemplo: bancos con código 7 y 11:

GET https://<sitioweb>/data/cmd/tesoreria/api/v1/get-bancos?codigos=7,11
Nota: los códigos se comparan tal cual se envían, sin quitar espacios. codigos=7, 11 busca el código " 11" (con un espacio adelante) y no lo encuentra. Enviar la lista sin espacios.

El orden de los resultados no está garantizado.

Parámetros de consulta
codigos
Tipo:array of string
Copiar enlace a codigos
Códigos de banco separados por coma. Sin este parámetro devuelve todos los bancos activos. Los códigos que no existen se ignoran.

Respuestas

200
Array de bancos. Si ningún código coincide devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/tesoreria/api/v1/get-bancos
Shell Curl
curl https://sitio.gescom.online/data/cmd/tesoreria/api/v1/get-bancos \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/tesoreria/api/v1/get-bancos)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "7",
    "descripcion": "BANCO DE GALICIA Y BUENOS AIRES S.A."
  },
  {
    "codigo": "11",
    "descripcion": "BANCO DE LA NACION ARGENTINA"
  }
]

Array de bancos. Si ningún código coincide devuelve [].

Cajas​Copiar enlace

Autenticación requerida

Copiar como Markdown
Devuelve las cajas activas del sistema (cajas simples, cuentas bancarias y cajas de usuario), con los tipos de valor que acepta cada una y sus etiquetas.

No recibe parámetros. Siempre devuelve el listado completo, sin paginación.

GET https://<sitioweb>/data/cmd/tesoreria/api/v1/get-cajas
El orden de las cajas no está garantizado.

Respuestas

200
Array de cajas. Si no hay cajas activas devuelve [].
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forget/data/cmd/tesoreria/api/v1/get-cajas
Shell Curl
curl https://sitio.gescom.online/data/cmd/tesoreria/api/v1/get-cajas \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN'


Probar solicitud
(get /data/cmd/tesoreria/api/v1/get-cajas)
Estado:200
Estado:401
Estado:403

[
  {
    "codigo": "7",
    "descripcion": "Caja mostrador",
    "identificacion": "1234",
    "tiposValor": [
      {
        "codigo": "EFE",
        "descripcion": "Efectivo"
      }
    ],
    "tags": [
      "Mostrador"
    ]
  },
  {
    "codigo": "11",
    "descripcion": "Cuenta BBVA",
    "identificacion": "567834333",
    "tiposValor": [
      {
        "codigo": "CHE",
        "descripcion": "Cheque"
      },
      {
        "codigo": "TRF",
        "descripcion": "Transferencia"
      }
    ],
    "tags": []
  }
]

Array de cajas. Si no hay cajas activas devuelve [].

Pedidos ​Copiar enlace
PedidosOperaciones
post
/data/cmd/pedidos/api/v1/create-bulk
get
/data/cmd/pedidos/api/v1/get-status
get
/data/cmd/pedidos/api/v1/get
Modifica datos
Crear pedidos​Copiar enlace

Autenticación requerida

Copiar como Markdown
Crea uno o más pedidos en un solo request. Cada pedido se valida por separado: los que pasan las validaciones se guardan y los que no se informan con sus errores en detalle. Los pedidos guardados quedan en proceso: el sistema los convierte en ventas en segundo plano (ver Lectura de estados).

Body JSON con la clave pedidos, que contiene el array de pedidos. La cantidad máxima de pedidos por request se configura en el sistema (preferencia de máximo de pedidos por API); si no está configurada, el máximo es 20. Consultar el valor vigente con el administrador del sistema.

Los tipos de venta de devolución (DEV-CA, etc.) se pueden acompañar de codigoMotivoCambio.
Para informar el precio unitario de un ítem vendido en, por ejemplo, Pack x 25, el precio tiene que ser el del pack, no el de la unidad.
Los campos opcionales pueden omitirse o enviarse en null.
Un pedido no puede mezclar ítems que pertenecen a combos con combos no declarados: si un ítem indica un combo, ese combo tiene que figurar en combos con su cantidad.
Artículos inactivos, bloqueados o no disponibles para venta: se rechazan, salvo en un tipo de venta de crédito que trae ventaReferenciadaId, si el artículo estaba en esa venta y la cantidad devuelta (cantidad × factor, sumando las líneas del artículo) no supera la de la venta original. Si no se envía ventaReferenciadaId, la venta que el sistema referencia automáticamente no habilita esta excepción.
La venta referenciada tiene que existir, ser del mismo cliente y de un tipo que el tipo de venta admita como referencia.
Como el pedido se convierte en venta en segundo plano, los rechazos de los dos puntos anteriores no aparecen en detalle: se ven en el estado del pedido (Lectura de estados).
Nota: si algún pedido trae descuentos: null explícito en un ítem, o no trae items, el request completo se rechaza con resultado = R y el error 500 "Error desconocido". Omitir esos campos en lugar de enviarlos en null.

Nota: hoy, indicar los combos solo con codigoComboComp en los ítems y el combo declarado en combos falla con el error 406 "no es un codigo valido de Combo". Hasta que se corrija, indicar también codigoCombo en cada ítem del combo.

Cuerpo
obligatorio
application/json

pedidos
Tipo:array of object
obligatorio
{ identificador, codigoCliente, items, +19 }
Copiar enlace a pedidos
Propiedades: 22
Respuestas

200
Siempre que el body se pueda leer, incluso si todos los pedidos fallaron. El resultado real está en resultado, errores y detalle.
application/json

400
Falta la clave pedidos o el body no es JSON válido.
application/json
401
Copiar enlace a 401
Falta el token o está vencido.

403
Copiar enlace a 403
El usuario no tiene permisos para esta operación.

Request Example forpost/data/cmd/pedidos/api/v1/create-bulk
Shell Curl
curl https://sitio.gescom.online/data/cmd/pedidos/api/v1/create-bulk \
  --request POST \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer YOUR_SECRET_TOKEN' \
  --data '{
  "pedidos": [
    {
      "identificador": "983124b7-ca8f-4f5d-b099-07cf5b69dce7",
      "codigoTipoVenta": "VEN",
      "codigoCliente": "CC123",
      "codigoVendedor": "CV123",
      "codigoRuta": "CR123",
      "fechaEntrega": "2025-05-24",
      "observaciones": "Entregar por la mañana",
      "items": [
        {
          "codigoItem": "300030687",
          "cantidad": 2,
          "codigoUnidad": "Pack",
          "unidadFactor": 18,
          "descuentos": [
            {
              "descuento": 0.05
            }
          ]
        },
        {
          "codigoItem": "300028468",
          "cantidad": 6,
          "codigoUnidad": "Unidad",
          "unidadFactor": 1,
          "precioUnitario": 150.5
        }
      ]
    }
  ]
}'


Probar solicitud
(post /data/cmd/pedidos/api/v1/create-bulk)
Estado:200
Estado:400
Estado:401
Estado:403

{
  "resultado": "P",
  "errores": [],
  "detalle": [
    {
      "identificador": "983124b7-ca8f-4f5d-b099-07cf5b69dce7",
      "pedidoId": 21,
      "errores": []
    },
    {
      "identificador": "A-1002",
      "pedidoId": null,
      "errores": [
        {
          "code": 405,
          "msg": "El campo CodigoCliente tiene un codigo invalido"
        }
      ]
    }
  ]
}

Siempre que el body se pueda leer, incluso si todos los pedidos fallaron. El resultado real está en resultado, errores y detalle.

Schemas
Error​Copiar enlace
ResultadoEscritura​Copiar enlace
Venta​Copiar enlace
Venta con sus ítems, importes, comprobante principal y reparto asociado.

id
Tipo:integer
Copiar enlace a id
Id interno de la venta.

identificador
Tipo:string | null
Copiar enlace a identificador
Identificador externo con el que se creó la venta por API.

origen
Tipo:string
Copiar enlace a origen
Sistema u origen que generó la venta (ej. gcw).

estado
Tipo:string
Copiar enlace a estado
Pendiente, Finalizada o Error.

etapa
Tipo:string
Copiar enlace a etapa
Etapa actual: TipoVenta, Precios, Promociones, Descuentos, LineaCredito, ReservaStock, Impuestos, Facturacion, AsignacionDeuda o Entrega.

etapaNota
Tipo:string | null
Copiar enlace a etapaNota
Nota cargada para la etapa actual.

requiereAutorizacion
Tipo:boolean
Copiar enlace a requiereAutorizacion
true si la venta tiene alguna autorización pendiente o no aprobada.

cerrada
Tipo:boolean
Copiar enlace a cerrada
La venta tiene comprobantes registrados fiscalmente.

codigoTipoVenta
Tipo:string
Copiar enlace a codigoTipoVenta
Código del tipo de venta.

esCredito
Tipo:boolean
Copiar enlace a esCredito
El tipo de venta es de crédito (devolución, nota de crédito).

esSinCargo
Tipo:boolean
Copiar enlace a esSinCargo
El tipo de venta es sin cargo.

tags
Tipo:array of string
Copiar enlace a tags
Nombres de las etiquetas de la venta, ordenados alfabéticamente. [] si no tiene.

codigoCliente
Tipo:string
Copiar enlace a codigoCliente
codigoVendedor
Tipo:string | null
Copiar enlace a codigoVendedor
codigoRuta
Tipo:string | null
Copiar enlace a codigoRuta
codigoEmpresa
Tipo:string | null
Copiar enlace a codigoEmpresa
codigoPuntoVenta
Tipo:integer | null
Copiar enlace a codigoPuntoVenta
Integer numbers.

codigoSede
Tipo:string | null
Copiar enlace a codigoSede
codigoCondicionPago
Tipo:string
Copiar enlace a codigoCondicionPago
codigoMotivoCambio
Tipo:string | null
Copiar enlace a codigoMotivoCambio
Código del motivo de venta.

motivo
Tipo:string | null
Copiar enlace a motivo
Descripción del motivo de venta (por qué se hizo la venta, devolución, rechazo, etc.).

fechaPedido
Tipo:string
Copiar enlace a fechaPedido
Fecha de carga de la venta (es la fecha que usan fechadesde y fechahasta).

fechaEntrega
Tipo:string | null
Copiar enlace a fechaEntrega
observaciones
Tipo:string | null
Copiar enlace a observaciones
observacionesInternas
Tipo:string | null
Copiar enlace a observacionesInternas
descuentoGlobal
Tipo:number | null
Copiar enlace a descuentoGlobal
Descuento global de la venta, como fracción (0.14 = 14 %).

ventaDirecta
Tipo:boolean
Copiar enlace a ventaDirecta
metodoEntrega
Tipo:integer | null
Copiar enlace a metodoEntrega
0 = envío a domicilio, 1 = retiro directo, 2 = retiro por depósito.

loteId
Tipo:string | null
Copiar enlace a loteId
numeroComprobante
Tipo:integer | null
Copiar enlace a numeroComprobante
Integer numbers.


ventaReferenciada
Tipo:object | null
{ id, numeroComprobante, origen, +4 }
Copiar enlace a ventaReferenciada
Venta a la que hace referencia esta (por ejemplo, la venta original de una devolución). Ver abajo.

Propiedades: 7
codigoReparto
Tipo:integer | null
Copiar enlace a codigoReparto
Número del reparto al que está asignada la venta (se excluyen repartos cancelados y asignaciones marcadas como no entregadas).

codigoChofer
Tipo:string | null
Copiar enlace a codigoChofer
Código de empleado del chofer de ese reparto.


items
Tipo:array of object
{ orden, ventaItemID, itemID, +29 }
Copiar enlace a items
Ítems de la venta (ver abajo).

Propiedades: 32
combos
Tipo:array
Copiar enlace a combos
Combos de la venta: { "codigoCombo": string, "cantidad": int }. Si el combo ya no existe, codigoCombo vale undef-<id>.


comprobantePrincipal
Tipo:object | null
{ numeroComprobante, codigoTipoComprobante, letraComprobante, +14 }
Copiar enlace a comprobantePrincipal
Comprobante fiscal principal. null si todavía no se generó. Ver abajo.

Propiedades: 17
propiedades
Tipo:object
Copiar enlace a propiedades
Propiedades adicionales de la venta. {} si no tiene.

importeNeto
Tipo:number
Copiar enlace a importeNeto
Suma de los importes de todos los ítems.

importeExento
Tipo:number
Copiar enlace a importeExento
Suma de los importes de todos los ítems.

importeConc
Tipo:number
Copiar enlace a importeConc
Suma de los importes de todos los ítems.

importeIva
Tipo:number
Copiar enlace a importeIva
Suma de los importes de todos los ítems.

importeTributos
Tipo:number
Copiar enlace a importeTributos
Suma de los importes de todos los ítems.

importeTotal
Tipo:number
Copiar enlace a importeTotal
Suma de los importes de todos los ítems.