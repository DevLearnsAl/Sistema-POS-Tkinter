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

Buildozer solo corre en Linux. En Windows se usa WSL, que ya viene con el sistema:

```powershell
wsl -d Ubuntu
```

Y dentro de Ubuntu, una sola vez:

```bash
sudo apt install -y python3-pip python3-venv openjdk-17-jdk git zip unzip \
    autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev
python3 -m venv ~/venv-buildozer
~/venv-buildozer/bin/pip install buildozer cython
```

Después, cada vez que se quiera armar el APK:

```bash
cp -r "/mnt/c/Users/TU_USUARIO/Documents/Minimarket referencia/android" ~/minimarket-android
cd ~/minimarket-android
~/venv-buildozer/bin/buildozer android debug
```

Se copia a la carpeta de Linux a propósito: construir sobre `/mnt/c` es mucho más lento.

**La primera vez tarda entre 30 y 90 minutos** y descarga unos 2 GB: el SDK de Android, el
NDK y las herramientas que compilan Python para el teléfono. Las veces siguientes son
minutos.

El APK queda en `bin/minimarket-5.0-arm64-v8a-debug.apk`.

## Instalarlo en el teléfono

Con el teléfono conectado por USB y la depuración USB activada:

```bash
~/venv-buildozer/bin/buildozer android deploy run
```

O copiando el `.apk` al teléfono y abriéndolo (hay que permitir instalar de orígenes
desconocidos).

## Si falla la construcción de ReportLab

ReportLab es lo único que puede dar problemas, porque tiene partes en C. Si el APK no se
arma por eso, quitalo de `requirements` en `buildozer.spec`:

```
requirements = python3,kivy==2.3.1,pillow
```

La aplicación sigue funcionando: la venta se guarda igual y avisa que no pudo generar el
PDF. La factura se puede imprimir después desde la computadora, que usa la misma base.
