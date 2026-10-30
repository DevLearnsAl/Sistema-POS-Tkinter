"""Crea, respalda y actualiza database.db.

- Si no existe, la crea con schema.sql y datos de ejemplo.
- Si es de la versión 2, le agrega lo nuevo de la 3 sin perder los datos.
- Si es de la versión 1, la respalda como database_v1_respaldo.db y crea una nueva.
- En cada arranque guarda una copia en respaldos/ y conserva las últimas.

Para empezar de cero: borrá database.db y abrí el programa (o corré
`py crear_bd.py`).
"""
import datetime
import os
import random
import sqlite3

import config
from db import DB_NAME
from seguridad import hash_password
from utilidades import calcular_linea, codigo_interno

VERSION_ESQUEMA = 3

# (nombre, precio, costo, stock, stock mínimo, IVA %, estado, foto)
# Precios al público en córdobas, IVA incluido. Los productos de la canasta
# básica van exentos (IVA 0).
ARTICULOS_EJEMPLO = [
    ("Coca-Cola 1.5 L", 55.00, 42.00, 24, 6, 15, "Activo", "coca_cola.png"),
    ("Doritos Nacho 45 g", 25.50, 18.00, 30, 8, 15, "Activo", "doritos.png"),
    ("Galletas de chocolate", 30.00, 22.00, 20, 6, 15, "Activo", "galletas.png"),
    ("Agua purificada 600 ml", 20.00, 13.00, 36, 12, 15, "Activo", "agua.png"),
    ("Jugo de naranja 1 L", 45.00, 35.00, 10, 4, 15, "Inactivo", "jugo.png"),
    ("Arroz 1 lb", 18.75, 14.50, 50, 10, 0, "Activo", "arroz.png"),
    ("Azúcar 1 lb", 16.00, 12.00, 40, 10, 0, "Activo", "azucar.png"),
    ("Frijoles rojos 1 lb", 32.00, 25.00, 4, 10, 0, "Activo", "frijoles.png"),
    ("Aceite vegetal 1 L", 78.00, 62.00, 18, 5, 0, "Activo", "aceite.png"),
    ("Leche entera 1 L", 38.50, 31.00, 12, 6, 0, "Activo", "leche.png"),
    ("Huevos (15 unidades)", 95.00, 80.00, 3, 5, 0, "Activo", "huevos.png"),
]

CLIENTES_EJEMPLO = [
    ("Consumidor final", None, "", "", ""),
    ("María López", "001-150390-0001X", "+505 8888 7777", "Managua, Bello Horizonte", "maria.lopez@correo.com"),
    ("Pedro Ruiz", "281-010185-0002Y", "+505 8765 4321", "León, Barrio San Felipe", "pedro.ruiz@correo.com"),
    ("Ana Gutiérrez", "401-220794-0003K", "+505 8123 4567", "Masaya, Monimbó", "ana.gutierrez@correo.com"),
]

PROVEEDORES_EJEMPLO = [
    ("Distribuidora La Económica", "J0310000000011", "+505 2255 1100", "Managua, Km 7 Carretera Norte", "ventas@laeconomica.com"),
    ("Granos y Más S.A.", "J0310000000022", "+505 2266 2200", "Tipitapa", "pedidos@granosymas.com"),
    ("Lácteos del Norte", "J0310000000033", "+505 2777 3300", "Matagalpa", "contacto@lacteosdelnorte.com"),
]


def crear_base_de_datos(con_ejemplos=True):
    with open("schema.sql", encoding="utf-8") as archivo:
        script = archivo.read()

    conn = sqlite3.connect(DB_NAME)
    try:
        conn.executescript(script)
        conn.execute("INSERT OR IGNORE INTO usuarios (username, password, rol) VALUES (?, ?, 'admin')",
                     ("admin", hash_password("admin")))
        conn.execute("INSERT OR IGNORE INTO clientes (nombre, cedula, celular, direccion, correo) "
                     "SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM clientes WHERE nombre = ?)",
                     CLIENTES_EJEMPLO[0] + (CLIENTES_EJEMPLO[0][0],))
        if con_ejemplos:
            _cargar_ejemplos(conn)
        conn.commit()
    finally:
        conn.close()


def _cargar_ejemplos(conn):
    for i, (nombre, precio, costo, stock, minimo, iva, estado, foto) in enumerate(ARTICULOS_EJEMPLO, start=1):
        ruta = os.path.join("fotos", foto)
        if not os.path.exists(ruta):
            ruta = os.path.join("fotos", "default.png")
        conn.execute(
            "INSERT OR IGNORE INTO articulos (codigo, articulo, precio, costo, stock, stock_minimo, iva, estado, image_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (codigo_interno(i), nombre, precio, costo, stock, minimo, iva, estado, ruta))

    for cliente in CLIENTES_EJEMPLO[1:]:
        conn.execute("INSERT OR IGNORE INTO clientes (nombre, cedula, celular, direccion, correo) VALUES (?, ?, ?, ?, ?)",
                     cliente)
    for proveedor in PROVEEDORES_EJEMPLO:
        conn.execute("INSERT OR IGNORE INTO proveedores (nombre, ruc, telefono, direccion, correo) VALUES (?, ?, ?, ?, ?)",
                     proveedor)

    if conn.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] == 0:
        _ventas_ejemplo(conn)
        _compras_ejemplo(conn)


def _ventas_ejemplo(conn):
    """Una semana de ventas de ejemplo (hasta hoy), para que los reportes tengan datos.

    Cada día es un turno de caja ya cerrado, así el historial de arqueos también
    tiene contenido."""
    rnd = random.Random(2026)
    productos = conn.execute(
        "SELECT codigo, articulo, precio, costo, iva FROM articulos WHERE estado = 'Activo' ORDER BY id").fetchall()
    clientes = ["Consumidor final"] * 6 + ["María López", "Pedro Ruiz", "Ana Gutiérrez"]
    ahora = datetime.datetime.now()
    minutos_ahora = ahora.hour * 60 + ahora.minute
    factura = 0

    for dias_atras in range(6, -1, -1):
        fecha = (ahora.date() - datetime.timedelta(days=dias_atras)).isoformat()
        inicial = 500.0
        caja_id = conn.execute(
            "INSERT INTO cajas (usuario, fecha_apertura, hora_apertura, monto_inicial, estado) "
            "VALUES ('admin', ?, '07:50:00', ?, 'ABIERTA')", (fecha, inicial)).lastrowid
        efectivo = 0.0

        for minutos in sorted(rnd.sample(range(8 * 60, 19 * 60), rnd.randint(3, 6))):
            if dias_atras == 0 and minutos > minutos_ahora - 20:
                continue
            factura += 1
            hora = f"{minutos // 60:02d}:{minutos % 60:02d}:{rnd.randint(0, 59):02d}"
            cliente = rnd.choice(clientes)
            metodo = "Tarjeta" if rnd.random() < 0.25 else "Efectivo"
            lineas = []
            for codigo, articulo, precio, costo, iva in rnd.sample(productos, rnd.randint(1, 4)):
                cantidad = rnd.randint(1, 3)
                total, iva_linea = calcular_linea(precio, cantidad, iva)
                lineas.append((codigo, articulo, precio, cantidad, total, iva_linea, round(costo * cantidad, 2)))
            total_factura = sum(l[4] for l in lineas)
            recibido = total_factura if metodo == "Tarjeta" else float((int(total_factura) // 100 + 1) * 100)
            if metodo == "Efectivo":
                efectivo += total_factura
            for codigo, articulo, precio, cantidad, total, iva_linea, costo in lineas:
                conn.execute(
                    "INSERT INTO ventas (factura, cliente, codigo, articulo, precio, cantidad, total, iva, costo, "
                    "fecha, hora, usuario, caja_id, metodo_pago, recibido, estado) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'EMITIDA')",
                    (factura, cliente, codigo, articulo, precio, cantidad, total, iva_linea, costo,
                     fecha, hora, "admin", caja_id, metodo, recibido))

        # Todos los turnos de ejemplo quedan cerrados: al abrir el programa por
        # primera vez hay que abrir la caja, que es como se usa de verdad.
        esperado = round(inicial + efectivo, 2)
        contado = esperado + rnd.choice([0, 0, 0, -20, 5])     # a veces falta o sobra algo
        conn.execute(
            "UPDATE cajas SET fecha_cierre = ?, hora_cierre = '19:30:00', usuario_cierre = 'admin', "
            "esperado = ?, monto_contado = ?, diferencia = ?, estado = 'CERRADA' WHERE id = ?",
            (fecha, esperado, round(contado, 2), round(contado - esperado, 2), caja_id))

    # Una factura anulada de ejemplo (el stock no se toca: son datos históricos).
    if factura >= 3:
        conn.execute("UPDATE ventas SET estado = 'ANULADA' WHERE factura = 3")


def _compras_ejemplo(conn):
    ahora = datetime.datetime.now()
    compras = [
        (5, "Granos y Más S.A.", "Arroz 1 lb", 40, 14.50),
        (3, "Distribuidora La Económica", "Coca-Cola 1.5 L", 24, 42.00),
        (1, "Lácteos del Norte", "Leche entera 1 L", 12, 31.00),
    ]
    for dias_atras, proveedor, articulo, cantidad, costo in compras:
        fecha = (ahora.date() - datetime.timedelta(days=dias_atras)).isoformat()
        conn.execute("INSERT INTO compras (fecha, hora, proveedor, articulo, cantidad, costo, total, usuario) "
                     "VALUES (?, '09:15:00', ?, ?, ?, ?, ?, 'admin')",
                     (fecha, proveedor, articulo, cantidad, costo, round(cantidad * costo, 2)))


def version_actual():
    conn = sqlite3.connect(DB_NAME)
    try:
        return conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()


def _columnas(conn, tabla):
    return {f[1] for f in conn.execute(f"PRAGMA table_info({tabla})")}


def migrar_v2_a_v3():
    """Agrega roles, cajas y las columnas nuevas sin tocar los datos existentes.

    SQLite permite ALTER TABLE ADD COLUMN con DEFAULT y CHECK, así que las filas
    que ya existen toman el valor por defecto."""
    conn = sqlite3.connect(DB_NAME)
    try:
        agregar = [
            ("usuarios", "rol", "TEXT NOT NULL DEFAULT 'cajero' CHECK (rol IN ('admin', 'cajero'))"),
            ("usuarios", "activo", "INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))"),
            ("clientes", "activo", "INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))"),
            ("proveedores", "activo", "INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))"),
            ("ventas", "caja_id", "INTEGER REFERENCES cajas (id)"),
        ]
        for tabla, columna, definicion in agregar:
            if columna not in _columnas(conn, tabla):
                conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")

        # Las tablas e índices nuevos se crean con el mismo schema.sql: todo lo
        # que ya existe lleva IF NOT EXISTS, así que no se toca.
        with open("schema.sql", encoding="utf-8") as archivo:
            conn.executescript(archivo.read())

        # El usuario admin de la versión 2 pasa a ser administrador; los demás, cajeros.
        conn.execute("UPDATE usuarios SET rol = 'admin' WHERE username = 'admin'")
        conn.commit()
    finally:
        conn.close()


def hacer_respaldo():
    """Copia la base en respaldos/ y conserva solo las últimas. Devuelve la ruta."""
    os.makedirs(config.CARPETA_RESPALDOS, exist_ok=True)
    nombre = f"database_{datetime.datetime.now():%Y%m%d_%H%M%S}.db"
    ruta = os.path.join(config.CARPETA_RESPALDOS, nombre)

    # La API backup() de sqlite3 copia una base aunque esté en uso, a diferencia
    # de copiar el archivo con shutil.
    origen = sqlite3.connect(DB_NAME)
    destino = sqlite3.connect(ruta)
    try:
        origen.backup(destino)
    finally:
        destino.close()
        origen.close()

    viejos = sorted(f for f in os.listdir(config.CARPETA_RESPALDOS)
                    if f.startswith("database_") and f.endswith(".db"))
    for archivo in viejos[:-config.RESPALDOS_A_CONSERVAR]:
        try:
            os.remove(os.path.join(config.CARPETA_RESPALDOS, archivo))
        except OSError:
            pass
    return ruta


def preparar_base():
    """Deja lista la base al abrir el programa. Devuelve un aviso para el login, o None."""
    mensaje = None
    if os.path.exists(DB_NAME):
        version = version_actual()
        if version < 2:
            # La versión 1 no es compatible: se guarda aparte y se empieza de nuevo.
            respaldo = "database_v1_respaldo.db"
            if os.path.exists(respaldo):
                respaldo = f"database_v1_respaldo_{datetime.datetime.now():%Y%m%d_%H%M%S}.db"
            os.replace(DB_NAME, respaldo)
            mensaje = f"La base de datos de la versión anterior se guardó como {respaldo}."
        else:
            hacer_respaldo()
            if version < VERSION_ESQUEMA:
                migrar_v2_a_v3()
                mensaje = "La base de datos se actualizó a la versión 3 (roles y arqueo de caja)."
    if not os.path.exists(DB_NAME):
        crear_base_de_datos()
    return mensaje


if __name__ == "__main__":
    print(preparar_base() or "Base de datos lista:", DB_NAME)
