# Minimarket: sistema de facturación en Python

Sistema de punto de venta (POS) para un minimarket, hecho con Python, Tkinter y SQLite.
Permite registrar ventas, controlar el inventario, administrar clientes y generar
facturas en PDF. Los precios están en córdobas (C$).

| | |
|---|---|
| <img src="figma/01%20Login.svg" alt="Inicio de sesión" width="420"> | <img src="figma/03%20Ventas.svg" alt="Ventas" width="420"> |
| <img src="figma/06%20Inventario.svg" alt="Inventario" width="420"> | <img src="figma/09%20Clientes.svg" alt="Clientes" width="420"> |

## Funciones

- **Inicio de sesión y registro.** Para crear usuarios nuevos se pide un código de autorización.
- **Ventas.** Se elige el cliente y el producto (con buscador), se ve el stock disponible
  y se arma la lista de cobro, que se puede editar antes de pagar. Al cobrar, el sistema
  calcula el cambio, guarda la venta, descuenta el stock y genera la factura en PDF.
- **Ventas realizadas.** Historial de ventas con filtro por número de factura o por cliente.
- **Inventario.** Productos en tarjetas con foto, búsqueda, y formularios para agregar y
  editar precio, costo, stock y estado. Los productos inactivos no se pueden vender.
- **Clientes.** Registro y modificación de clientes (nombre, cédula, celular, dirección y
  correo). Las ventas de mostrador usan el cliente «Consumidor final».
- **Pedidos, Proveedor e Información.** Módulos pendientes.

## Tecnologías

Python 3 · Tkinter / ttk · SQLite3 · Pillow (imágenes) · ReportLab (facturas PDF)

## Cómo ejecutarlo

Requiere Python 3 en Windows.

```powershell
git clone https://github.com/DevLearnsAl/Sistema-POS-Tkinter.git
cd Sistema-POS-Tkinter
py -m pip install -r requirements.txt
py index.py
```

Datos de acceso:

- Usuario: `admin` · Contraseña: `admin`
- Código para registrar usuarios nuevos: `1234`

La primera vez que se ejecuta, el programa crea `database.db` con 6 productos de ejemplo
y el cliente «Consumidor final». Para empezar de cero, basta con borrar `database.db`.

## Cómo funciona

Al abrir el programa aparece el inicio de sesión. Después de entrar, la ventana principal
muestra una barra con los seis módulos. Ventas e Inventario recargan sus datos cada vez
que se abren, así un producto agregado en Inventario aparece de inmediato en Ventas.

Flujo de una venta:

1. Elegir el cliente, el producto y la cantidad, y pulsar **Agregar artículo**.
2. Repetir con cada producto. La lista muestra el total a pagar.
3. Pulsar **Pagar** e ingresar el monto recibido. El sistema muestra el cambio.
4. La venta se guarda en una sola transacción junto con el descuento del stock. Si algo
   falla, se deshace completa y el stock no cambia.
5. La factura se guarda en `facturas/Factura_<número>.pdf` y se abre automáticamente.

### Estructura del proyecto

| Archivo | Qué hace |
|---|---|
| `index.py` | Punto de entrada: crea la base de datos si no existe y abre la aplicación |
| `manager.py` | Ventana principal; cambia entre el inicio de sesión y el sistema |
| `container.py` | Barra de módulos y área donde se muestra cada uno |
| `login.py` | Inicio de sesión y registro de usuarios |
| `ventas.py` | Lista de cobro, pago, historial de ventas y factura PDF |
| `inventario.py` | Tarjetas de productos, búsqueda, agregar y editar |
| `clientes.py` | Registro y modificación de clientes |
| `pedidos.py`, `proveedor.py`, `informacion.py` | Módulos pendientes |
| `schema.sql`, `crear_bd.py` | Tablas de la base de datos y datos de ejemplo |
| `imagenes/`, `fotos/` | Fondo, logo y foto por defecto de los productos |
| `figma/` | Las pantallas del diseño en SVG |

### Base de datos

Cuatro tablas en SQLite: `usuarios`, `articulos`, `ventas` y `clientes`. Las reglas de
negocio están en el propio esquema: nombres de usuario y de producto únicos, cédula
única, precio mayor que cero, y stock que nunca puede quedar negativo después de una venta.

## Diseño en Figma

Las 10 pantallas del sistema están diseñadas en Figma con componentes y variables de color:
https://www.figma.com/design/6CKct9Qie9gWxHvhaddS1C

La carpeta `figma/` tiene las mismas pantallas en SVG, listas para arrastrar a un lienzo de Figma.

## Próximas mejoras

- Guardar las contraseñas con hash.
- Guardar el dinero en centavos enteros en lugar de números decimales (`REAL`).
- Separar las ventas en `ventas` y `detalle_venta`.
- Calcular el IVA y agregar lectura de código de barras.
- Construir los módulos de Pedidos, Proveedor e Información.

## Créditos

Basado en el curso [Crea un Sistema de Punto de Venta (POS) en Python Tkinter + SQLite3](https://www.youtube.com/playlist?list=PLoHtVmh39Q8Sg4wcyGPiiX3N0bOmvxrql)
de InnovaSoft Code, con correcciones y mejoras.
