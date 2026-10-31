"""Dónde están los archivos, tanto al correr el código como al correr el .exe.

Corriendo el código, todo vive en la carpeta del proyecto. Empaquetado con
PyInstaller hay dos carpetas distintas:

- **recursos**: lo que viene dentro del programa (schema.sql, las fotos de
  ejemplo, el ícono). Es de solo lectura y PyInstaller la descomprime aparte.
- **datos**: la carpeta donde está el .exe, que es donde el programa escribe
  la base de datos, las facturas, los reportes, los respaldos y el registro.

Para no llenar el resto del código de condicionales, al arrancar se copian los
recursos a la carpeta de datos si todavía no están. De ahí en adelante todo
funciona con rutas relativas, igual que corriendo el código.
"""
import os
import shutil
import sys

# Lo que se copia la primera vez. Son los archivos que el programa necesita
# para crear la base y mostrar los productos de ejemplo.
ARCHIVOS = ["schema.sql"]
CARPETAS = ["fotos", "imagenes"]


def empaquetado():
    """True si esto corre desde el .exe y no desde el código."""
    return getattr(sys, "frozen", False)


def recursos():
    """Carpeta de solo lectura con lo que viene dentro del programa."""
    if empaquetado():
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def datos():
    """Carpeta donde el programa guarda lo suyo."""
    if empaquetado():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def preparar():
    """Deja lista la carpeta de datos y se para en ella. Devuelve esa ruta."""
    destino = datos()
    origen = recursos()
    if origen != destino:
        for archivo in ARCHIVOS:
            if os.path.exists(os.path.join(origen, archivo)) and not os.path.exists(os.path.join(destino, archivo)):
                shutil.copyfile(os.path.join(origen, archivo), os.path.join(destino, archivo))
        for carpeta in CARPETAS:
            ruta_origen = os.path.join(origen, carpeta)
            ruta_destino = os.path.join(destino, carpeta)
            if os.path.isdir(ruta_origen):
                # dirs_exist_ok: si el usuario ya agregó fotos propias, no se pisan.
                shutil.copytree(ruta_origen, ruta_destino, dirs_exist_ok=True)
    os.chdir(destino)
    return destino
