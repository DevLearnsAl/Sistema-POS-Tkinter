-- Tablas del Minimarket (videos 3, 5, 7 y 10), con las correcciones de la guía.
-- crear_bd.py ejecuta este archivo. También podés pegarlo en la pestaña
-- "Ejecutar SQL" de DB Browser for SQLite.

-- Video 3
CREATE TABLE IF NOT EXISTS usuarios (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT NOT NULL UNIQUE,   -- Corrección: no pueden existir dos "admin"
    password  TEXT NOT NULL
);

-- Video 5
CREATE TABLE IF NOT EXISTS articulos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    articulo    TEXT NOT NULL UNIQUE,              -- Corrección: se edita y se vende buscando por nombre
    precio      REAL NOT NULL CHECK (precio > 0),  -- Corrección: CHECK en precio, costo y stock
    costo       REAL NOT NULL CHECK (costo >= 0),
    stock       INTEGER NOT NULL CHECK (stock >= 0),  -- Evita que una venta deje la existencia en negativo
    estado      TEXT NOT NULL CHECK (estado IN ('Activo', 'Inactivo')),
    image_path  TEXT
);

-- Video 7. Igual que en el curso: una fila por cada producto vendido.
-- Separarla en ventas + detalle_venta queda para después del curso.
CREATE TABLE IF NOT EXISTS ventas (
    factura   INTEGER NOT NULL,
    cliente   TEXT,
    articulo  TEXT,
    precio    REAL,
    cantidad  INTEGER,
    total     REAL,
    fecha     TEXT,
    hora      TEXT,
    costo     REAL
);

-- Video 10
CREATE TABLE IF NOT EXISTS clientes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre     TEXT NOT NULL,
    cedula     TEXT UNIQUE,   -- Corrección: TEXT y no NUMERIC (001-150390-0001X no es un número)
    celular    TEXT,          -- Corrección: TEXT para no perder el "+505" ni los ceros iniciales
    direccion  TEXT,
    correo     TEXT
);
