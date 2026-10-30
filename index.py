import os

# Las rutas (database.db, fotos/, facturas/) son relativas a la carpeta del
# programa. Con esta línea funciona aunque se ejecute desde otra carpeta.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

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
