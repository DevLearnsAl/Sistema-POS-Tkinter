import rutas

# Deja lista la carpeta donde el programa guarda la base, las facturas y los
# respaldos, y se para en ella: así el resto del código usa rutas relativas,
# tanto corriendo el código como desde el .exe.
rutas.preparar()

import crear_bd
import registro
from manager import Manager

if __name__ == "__main__":
    registro.iniciar()
    try:
        aviso = crear_bd.preparar_base()
    except Exception as e:
        registro.error("No se pudo preparar la base de datos", e)
        raise
    app = Manager(aviso_inicial=aviso)
    app.mainloop()
