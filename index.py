import os

# Las rutas (database.db, fotos/, facturas/) son relativas a la carpeta del
# programa. Con esta línea funciona aunque se ejecute desde otra carpeta.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import crear_bd
from manager import Manager

if __name__ == "__main__":
    aviso = crear_bd.preparar_base()
    app = Manager(aviso_inicial=aviso)
    app.mainloop()
