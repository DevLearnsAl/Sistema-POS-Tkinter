"""Dónde guarda sus archivos la aplicación en el teléfono.

En Android una aplicación no puede escribir en la carpeta donde está instalada:
solo en la suya privada, que Kivy entrega como `App.user_data_dir`. Entonces, la
primera vez se copian ahí los archivos que vienen dentro del APK (el esquema de
la base y las fotos de ejemplo) y el programa se para en esa carpeta.

De ahí en adelante el núcleo compartido (`db.py`, `crear_bd.py`, `factura.py`…)
usa rutas relativas y funciona igual que en la computadora, sin saber que está
en un teléfono.
"""
import os
import shutil

ARCHIVOS = ["schema.sql"]
CARPETAS = ["fotos"]


def preparar(carpeta_datos):
    """Copia lo necesario a la carpeta de datos y se para en ella."""
    origen = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(carpeta_datos, exist_ok=True)

    # Se sobrescriben siempre, no solo la primera vez: vienen dentro del APK y
    # no son datos del usuario. Si solo se copiaran cuando faltan, al instalar
    # una versión nueva la aplicación seguiría usando el schema.sql viejo y la
    # base nunca se migraría.
    for archivo in ARCHIVOS:
        fuente = os.path.join(origen, archivo)
        if os.path.exists(fuente):
            shutil.copyfile(fuente, os.path.join(carpeta_datos, archivo))

    for carpeta in CARPETAS:
        fuente = os.path.join(origen, carpeta)
        if os.path.isdir(fuente):
            shutil.copytree(fuente, os.path.join(carpeta_datos, carpeta), dirs_exist_ok=True)

    os.chdir(carpeta_datos)
    return carpeta_datos
