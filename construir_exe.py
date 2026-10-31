"""Arma el ejecutable del sistema con PyInstaller.

Uso:
    py -m pip install pyinstaller
    py construir_exe.py

Deja la aplicación en `dist/Minimarket/`. Esa carpeta es portátil: se copia a
otra computadora y se abre `Minimarket.exe`, sin instalar Python ni nada más.

Se arma en modo carpeta (no un único archivo) a propósito: el programa guarda
la base de datos, las facturas y los respaldos junto al .exe, y así quedan a la
vista y se pueden copiar. Un único archivo los escondería en una carpeta
temporal del sistema.
"""
import os
import subprocess
import sys

NOMBRE = "Minimarket"
PROYECTO = os.path.dirname(os.path.abspath(__file__))

# (origen, carpeta de destino dentro del programa)
RECURSOS = [("schema.sql", "."), ("fotos", "fotos"), ("imagenes", "imagenes")]


def main():
    os.chdir(PROYECTO)
    try:
        import PyInstaller  # noqa: F401  (solo para avisar si falta)
    except ImportError:
        print("Falta PyInstaller. Instalalo con:  py -m pip install pyinstaller")
        return 1

    orden = [sys.executable, "-m", "PyInstaller",
             "--name", NOMBRE,
             "--windowed",          # sin ventana negra de consola
             "--noconfirm",
             "--clean",
             "--distpath", "dist",
             "--workpath", "build",
             "--specpath", "build"]

    # Las rutas van absolutas: con --specpath, PyInstaller resuelve las relativas
    # contra la carpeta del .spec y no encontraría nada.
    icono = os.path.join(PROYECTO, "imagenes", "icono.ico")
    if os.path.exists(icono):
        orden += ["--icon", icono]
    for origen, destino in RECURSOS:
        ruta = os.path.join(PROYECTO, origen)
        if os.path.exists(ruta):
            orden += ["--add-data", f"{ruta}{os.pathsep}{destino}"]
    orden.append(os.path.join(PROYECTO, "index.py"))

    print("Construyendo...", " ".join(orden[3:]), "\n")
    resultado = subprocess.run(orden)
    if resultado.returncode:
        return resultado.returncode

    carpeta = os.path.join("dist", NOMBRE)
    # Un README corto para quien reciba la carpeta.
    with open(os.path.join(carpeta, "LEEME.txt"), "w", encoding="utf-8") as f:
        f.write(f"{NOMBRE} - Sistema de facturación e inventario\n\n"
                "Para usarlo, abrí Minimarket.exe. No hace falta instalar nada.\n\n"
                "Usuario: admin    Contraseña: admin\n"
                "Cambiala desde el menú de usuario, arriba a la derecha.\n\n"
                "El programa crea aquí mismo:\n"
                "  database.db   la base de datos\n"
                "  facturas/     las facturas en PDF\n"
                "  reportes/     los archivos CSV que exportes\n"
                "  respaldos/    una copia de la base en cada arranque\n"
                "  logs/         los errores, por si algo falla\n\n"
                "Para llevarlo a otra computadora, copiá esta carpeta entera.\n"
                "Para empezar de cero, borrá database.db.\n")

    tamano = sum(os.path.getsize(os.path.join(raiz, a))
                 for raiz, _, archivos in os.walk(carpeta) for a in archivos)
    print(f"\nListo: {carpeta}{os.sep}{NOMBRE}.exe")
    print(f"La carpeta pesa {tamano / 1024 / 1024:.0f} MB y es portátil.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
