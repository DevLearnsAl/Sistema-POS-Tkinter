import os

# Corrección (guía, video 3): rutas como "database.db" o "imagenes/fondo.png" son
# relativas a la carpeta desde donde se ejecuta el programa. Con esta línea el
# programa funciona aunque lo corras desde otra carpeta.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import crear_bd
from manager import Manager

if __name__ == "__main__":
    if not os.path.exists(crear_bd.DB_NAME):
        crear_bd.crear_base_de_datos()
    app = Manager()
    app.mainloop()
