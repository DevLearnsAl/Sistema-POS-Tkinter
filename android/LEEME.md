# Minimarket para Android

La misma lógica del sistema de escritorio, con una interfaz hecha para el teléfono.

## Qué comparte con la versión de escritorio

Lo que no tiene nada que ver con la pantalla se usa **sin cambios**. `preparar.py` lo copia
desde la carpeta del proyecto:

| Módulo | Qué aporta |
|---|---|
| `db.py` | Conexión a SQLite que siempre cierra y deshace si hay error |
| `crear_bd.py`, `schema.sql` | Las 9 tablas, los datos de ejemplo y las migraciones |
| `ajustes.py` | Nombre del negocio, moneda e impuesto configurables |
| `seguridad.py` | Contraseñas con hash PBKDF2 |
| `utilidades.py` | Cálculo del impuesto y búsqueda de productos |
| `turnos.py` | Abrir y cerrar caja, movimientos y arqueo |
| `cobro.py` | La transacción que guarda la venta y descuenta el stock |
| `factura.py` | La factura en PDF |

Son 1 036 líneas que no se reescribieron. **Las copias no se editan**: el original está
arriba, y `preparar.py` las vuelve a traer.

Lo propio de Android son las pantallas (`main.py`, `tema.py`, `pantallas/`), porque Tkinter
no corre en un teléfono y un diseño de 1100×650 no entra en una mano.

## Qué hace la aplicación

- **Inicio de sesión** con las mismas cuentas y los mismos roles.
- **Ventas**: buscar por código de barras o por nombre, carrito, cobro en efectivo o con
  tarjeta, cambio calculado y factura en PDF.
- **Caja**: abrir el turno, entradas y salidas de efectivo, cerrar con arqueo.
- **Inventario**: consultar precios y existencias, filtrar por stock bajo; el administrador
  puede corregir el stock contando lo que hay.

## Probarla en la computadora

Kivy todavía no funciona en Python 3.14, así que se usa 3.12:

```powershell
py -3.12 -m pip install kivy reportlab pillow
py preparar.py
py -3.12 main.py
```

Se abre una ventana con proporción de teléfono. La base queda en la carpeta de datos del
usuario, no junto al código.

## Armar el APK

Buildozer solo corre en Linux. En Windows se usa WSL, que ya viene con el sistema.

Una sola vez, dentro de Ubuntu:

```bash
sudo apt install -y python3-pip python3-venv openjdk-17-jdk git zip unzip     autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev
```

Después, desde PowerShell, cada vez que se quiera armar el APK:

```powershell
wsl -d Ubuntu -- bash "/mnt/c/Users/TU_USUARIO/Documents/Minimarket referencia/android/construir_apk.sh"
```

El script hace el resto: instala las herramientas en la versión que corresponde, copia el
proyecto a la carpeta de Linux (construir sobre `/mnt/c` es mucho más lento), limpia los
restos de construcciones anteriores y arma el APK. El registro completo queda en
`~/minimarket-android/construccion.log`; cuando algo falla, el motivo suele estar a cientos
de líneas del final.

**La primera vez tarda entre 30 y 90 minutos** y descarga unos 2 GB: el SDK de Android, el
NDK y las herramientas que compilan Python para el teléfono. Las veces siguientes son
minutos.

El APK queda en `~/minimarket-android/bin/minimarket-5.0-arm64-v8a-debug.apk` y pesa 20 MB.

### Por qué se fijan versiones viejas

Las herramientas de Android van por detrás de lo que traen los sistemas nuevos, y hay tres
cosas que sujetar para que la construcción llegue al final:

- **python-for-android en `v2024.01.21`** (en `buildozer.spec`). La versión actual compila
  Python 3.14 para el teléfono, y para esa versión PyPI publica paquetes precompilados de
  Android que las propias herramientas eligen pero después no saben instalar.
- **Buildozer 1.5.0**, que es la que combina con esa versión de python-for-android.
- **Python 3.11** para correr buildozer, instalado con `uv`. Ubuntu 26.04 trae 3.14, que
  las herramientas de Android todavía no soportan.

Aparte, el script resuelve dos tropiezos del entorno nuevo, los dos en la receta de
`libjpeg`: su `CMakeLists` pide una versión mínima que CMake 4 ya no acepta, y empieza
borrando restos con `rm -f`, que no sirve para carpetas, así que una construcción cortada a
la mitad la deja trabada. Está explicado en los comentarios del script.

## Instalarlo en el teléfono

Copiar el `.apk` al teléfono y abrirlo. Android pide permiso para instalar de orígenes
desconocidos; hay que dárselo.

Con el teléfono conectado por USB y la depuración USB activada también se puede:

```bash
cd ~/minimarket-android && python3.11 -m buildozer android deploy run
```

## La factura en PDF

Es lo único que falta en el teléfono. ReportLab, la librería que la genera, descarga su
código de `hg.reportlab.com` al compilarse para Android, y ese servidor hoy responde 403.
Por eso quedó fuera de `requirements` en `buildozer.spec`.

La aplicación está preparada: la venta se guarda igual y avisa que no pudo generar el PDF.
La factura se puede imprimir después desde la computadora, que usa la misma base. Para
volver a intentarlo, alcanza con agregar `reportlab` de nuevo a `requirements`.
