"""Crea database.db a partir de schema.sql.

En el curso las tablas se crean con clics en DB Browser. Aquí se crean desde
código, así la base se puede recrear en segundos: borrá database.db y corré
    py crear_bd.py
index.py también la crea sola si no existe.
"""
import sqlite3

DB_NAME = "database.db"

# Productos de ejemplo para probar el sistema apenas lo abrís (precios en córdobas).
ARTICULOS_EJEMPLO = [
    ("Coca-Cola 1.5 L", 55.00, 42.00, 24, "Activo"),
    ("Doritos Nacho 45 g", 25.50, 18.00, 30, "Activo"),
    ("Arroz 1 lb", 18.75, 14.50, 50, "Activo"),
    ("Azúcar 1 lb", 16.00, 12.00, 40, "Activo"),
    ("Leche entera 1 L", 38.50, 31.00, 12, "Activo"),
    ("Jugo de naranja 1 L", 45.00, 35.00, 10, "Inactivo"),
]


def crear_base_de_datos(con_ejemplos=True):
    with open("schema.sql", encoding="utf-8") as archivo:
        script = archivo.read()

    conn = sqlite3.connect(DB_NAME)
    conn.executescript(script)

    # El usuario inicial del curso (video 3): admin / admin.
    conn.execute("INSERT OR IGNORE INTO usuarios (username, password) VALUES ('admin', 'admin')")

    # Corrección (guía, video 10): cliente por defecto para las ventas de mostrador.
    conn.execute(
        "INSERT INTO clientes (nombre, cedula, celular, direccion, correo) "
        "SELECT 'Consumidor final', NULL, '', '', '' "
        "WHERE NOT EXISTS (SELECT 1 FROM clientes WHERE nombre = 'Consumidor final')"
    )

    if con_ejemplos:
        conn.executemany(
            "INSERT OR IGNORE INTO articulos (articulo, precio, costo, stock, estado, image_path) "
            "VALUES (?, ?, ?, ?, ?, 'fotos/default.png')",
            ARTICULOS_EJEMPLO,
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    crear_base_de_datos()
    print("Base de datos lista:", DB_NAME)
