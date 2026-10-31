"""Trae a esta carpeta el núcleo que se comparte con la versión de escritorio.

La lógica del sistema (base de datos, migraciones, impuestos, contraseñas,
turnos de caja, cobro y factura en PDF) vive una sola vez, en la carpeta del
proyecto. Acá se copia porque el APK empaqueta una carpeta sola, pero el
original sigue siendo el de arriba: no se edita la copia.

    py preparar.py

Se ejecuta antes de probar la aplicación y antes de armar el APK.
"""
import os
import shutil
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PROYECTO = os.path.dirname(AQUI)

# Módulos sin interfaz: funcionan igual en la computadora y en el teléfono.
MODULOS = ["db.py", "crear_bd.py", "ajustes.py", "seguridad.py", "utilidades.py",
           "factura.py", "registro.py", "config.py", "turnos.py", "cobro.py"]
ARCHIVOS = ["schema.sql"]
CARPETAS = ["fotos"]

AVISO = "# Copia generada por preparar.py. No la edites: el original está en la carpeta del proyecto.\n"


def main():
    if not os.path.exists(os.path.join(PROYECTO, "db.py")):
        print("No encuentro el proyecto de escritorio en", PROYECTO)
        return 1

    for modulo in MODULOS:
        origen = os.path.join(PROYECTO, modulo)
        with open(origen, encoding="utf-8") as f:
            contenido = f.read()
        with open(os.path.join(AQUI, modulo), "w", encoding="utf-8") as f:
            f.write(AVISO + contenido)

    for archivo in ARCHIVOS:
        shutil.copyfile(os.path.join(PROYECTO, archivo), os.path.join(AQUI, archivo))

    for carpeta in CARPETAS:
        origen = os.path.join(PROYECTO, carpeta)
        if os.path.isdir(origen):
            destino = os.path.join(AQUI, carpeta)
            shutil.rmtree(destino, ignore_errors=True)
            shutil.copytree(origen, destino)

    print(f"Listo: {len(MODULOS)} módulos, {len(ARCHIVOS)} archivo y {len(CARPETAS)} carpeta "
          f"copiados desde {PROYECTO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
