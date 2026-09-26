# Minimarket (versión de referencia)

El sistema completo del curso [Crea un Sistema de Punto de Venta (POS) en Python Tkinter + SQLite3](https://www.youtube.com/playlist?list=PLoHtVmh39Q8Sg4wcyGPiiX3N0bOmvxrql)
(Kevin Arboleda, InnovaSoft Code), con las correcciones de la
[guía](https://claude.ai/artifact/XuQ86DFGdQQgsoHwj22E92).

**Es un solucionario.** Tu versión la seguís escribiendo en `Sistema de facturación`.
Usá esta solo para comparar después de intentarlo, o cuando lleves un rato trabado.

## Cómo correrlo

```powershell
py -m pip install pillow reportlab
py index.py
```

- Usuario: `admin` · Contraseña: `admin`
- Código para registrar usuarios nuevos: `1234`
- La primera vez se crea `database.db` con 6 productos de ejemplo y el cliente
  «Consumidor final». Para empezar de cero, borrá `database.db`.
- Las facturas en PDF se guardan en `facturas/` y se abren solas.

## Diseño en Figma

Archivo de Figma con las 10 pantallas, construidas con componentes y variables de
color: https://www.figma.com/design/6CKct9Qie9gWxHvhaddS1C

La carpeta `figma/` tiene las mismas pantallas como SVG, por si necesitás
importarlas en otro archivo (arrastralas al lienzo de Figma).

## Qué archivo corresponde a cada video

| Archivo | Videos | Qué hace |
|---|---|---|
| `index.py`, `manager.py` | 1 | Arranque, ventana principal, cambio entre login y sistema |
| `container.py` | 1, 2 | Barra de 6 botones y área de módulos |
| `login.py` | 3, 4 | Login y registro |
| `schema.sql`, `crear_bd.py` | 3, 5, 7, 10 | Las tablas (en el curso se crean con clics en DB Browser) |
| `inventario.py` | 4, 5 | Tarjetas de productos, buscar, agregar y editar |
| `ventas.py` | 6, 7, 8 | Carrito, cobro, ventas realizadas y factura PDF |
| `clientes.py` | 9, 10 | Registrar y modificar clientes |
| `pedidos.py`, `proveedor.py`, `informacion.py` | 10 | Vacíos: el curso los deja para que los hagás vos |

## Correcciones

Cada cambio respecto del video tiene un comentario que empieza con `Corrección`
(o `Reto`, cuando resuelve un reto de la guía). Buscalos con Ctrl+Shift+F en VS Code.

**De la guía:** centavos visibles (`.2f`) y `C$`; `UNIQUE` y `CHECK` en las tablas;
cédula y celular como `TEXT`; estado con Combobox de solo lectura; `self.after` en
vez de `threading.Timer`; «Pago realizado» después del `commit`, con `rollback` si
falla; «Consumidor final» por defecto; la carpeta `facturas` se crea sola; el filtro
de ventas hecho con SQL; y todos los errores que el autor corrige en cámara.

**Encontradas al construirlo (no están en la guía):**

1. Un producto agregado en Inventario no aparecía en Ventas hasta reiniciar. Ahora
   cada módulo se actualiza al mostrarse (`al_mostrar`).
2. Se podían vender productos inactivos.
3. Después de cargar una foto, el siguiente producto sin foto se llevaba la foto
   del anterior.
4. Si agregabas el mismo producto dos veces y eliminabas una línea, se borraban
   las dos de la lista de cobro pero solo una de la pantalla.
5. Cada línea guardaba el cliente que estaba elegido al agregarla, no el del cobro.
6. Elegir «No se encontraron resultados» en el producto cerraba el programa con un error.
7. Si un INSERT fallaba (por ejemplo, una cédula repetida), la conexión quedaba
   abierta con la base bloqueada y la siguiente venta daba «database is locked».
   Por eso las escrituras cierran la conexión en un `finally`, e Inventario hace
   `rollback()` en el `except`.

## Lo que no cambié

Queda igual que en el curso y va en la sección «Después del curso» de la guía:
dinero como `REAL` en vez de centavos enteros, una sola tabla `ventas` sin
`detalle_venta`, número de factura con `MAX + 1`, sin IVA, sin código de barras
y contraseñas sin hash.
