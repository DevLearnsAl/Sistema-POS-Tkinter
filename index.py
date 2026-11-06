import rutas

# Deja lista la carpeta donde el programa guarda la base, las facturas y los
# respaldos, y se para en ella: así el resto del código usa rutas relativas,
# tanto corriendo el código como desde el .exe.
rutas.preparar()

import ajustes
import crear_bd
import nube
import registro
from manager import Manager

if __name__ == "__main__":
    registro.iniciar()
    try:
        aviso = crear_bd.preparar_base()
    except Exception as e:
        registro.error("No se pudo preparar la base de datos", e)
        raise
    # Si la sincronización con Firebase está encendida, un hilo en segundo
    # plano va vaciando la cola. Con la sincronización apagada no hace nada.
    ajustes.cargar()
    nube.iniciar()
    app = Manager(aviso_inicial=aviso)
    try:
        app.mainloop()
    finally:
        nube.detener()
