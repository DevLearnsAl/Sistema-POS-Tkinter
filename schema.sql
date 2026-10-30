-- Minimarket v3: esquema de la base de datos (SQLite).
-- Las reglas de negocio viven en el propio esquema (UNIQUE, CHECK), así la base
-- rechaza datos inválidos aunque el programa tuviera un error.

CREATE TABLE IF NOT EXISTS usuarios (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT NOT NULL UNIQUE,
    password  TEXT NOT NULL,                 -- hash PBKDF2, nunca la contraseña
    rol       TEXT NOT NULL DEFAULT 'cajero' CHECK (rol IN ('admin', 'cajero')),
    activo    INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    creado    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS articulos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo        TEXT UNIQUE,               -- código de barras (EAN-13); opcional
    articulo      TEXT NOT NULL UNIQUE,
    precio        REAL NOT NULL CHECK (precio > 0),       -- precio al público, IVA incluido
    costo         REAL NOT NULL CHECK (costo >= 0),
    stock         INTEGER NOT NULL CHECK (stock >= 0),    -- una venta nunca lo deja negativo
    stock_minimo  INTEGER NOT NULL DEFAULT 5 CHECK (stock_minimo >= 0),
    iva           REAL NOT NULL DEFAULT 15 CHECK (iva IN (0, 15)),  -- 0 = exento
    estado        TEXT NOT NULL CHECK (estado IN ('Activo', 'Inactivo')),
    image_path    TEXT
);

-- Turnos de caja. Se abre con un monto inicial y se cierra contando el efectivo:
-- la diferencia entre lo contado y lo esperado es el faltante o sobrante.
CREATE TABLE IF NOT EXISTS cajas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario         TEXT NOT NULL,                      -- quién abrió el turno
    fecha_apertura  TEXT NOT NULL,
    hora_apertura   TEXT NOT NULL,
    monto_inicial   REAL NOT NULL CHECK (monto_inicial >= 0),
    fecha_cierre    TEXT,
    hora_cierre     TEXT,
    usuario_cierre  TEXT,
    esperado        REAL,                               -- inicial + ventas en efectivo + entradas - salidas
    monto_contado   REAL,
    diferencia      REAL,                               -- contado - esperado
    observacion     TEXT,
    estado          TEXT NOT NULL DEFAULT 'ABIERTA' CHECK (estado IN ('ABIERTA', 'CERRADA'))
);
-- Solo puede haber un turno abierto a la vez.
CREATE UNIQUE INDEX IF NOT EXISTS idx_caja_abierta ON cajas (estado) WHERE estado = 'ABIERTA';

-- Entradas y salidas de efectivo que no son ventas (cambio, pago a proveedor, retiro).
CREATE TABLE IF NOT EXISTS movimientos_caja (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    caja_id   INTEGER NOT NULL REFERENCES cajas (id),
    tipo      TEXT NOT NULL CHECK (tipo IN ('ENTRADA', 'SALIDA')),
    monto     REAL NOT NULL CHECK (monto > 0),
    motivo    TEXT NOT NULL,
    fecha     TEXT NOT NULL,
    hora      TEXT NOT NULL,
    usuario   TEXT
);
CREATE INDEX IF NOT EXISTS idx_movimientos_caja ON movimientos_caja (caja_id);

-- Una fila por cada producto vendido. Todas las filas de una factura comparten
-- número, cliente, fecha, cajero, método de pago y estado.
CREATE TABLE IF NOT EXISTS ventas (
    factura      INTEGER NOT NULL,
    cliente      TEXT NOT NULL,
    codigo       TEXT,
    articulo     TEXT NOT NULL,
    precio       REAL NOT NULL,
    cantidad     INTEGER NOT NULL CHECK (cantidad > 0),
    total        REAL NOT NULL,              -- IVA incluido
    iva          REAL NOT NULL DEFAULT 0,    -- parte del total que es IVA
    costo        REAL NOT NULL,              -- costo del momento x cantidad
    fecha        TEXT NOT NULL,              -- AAAA-MM-DD
    hora         TEXT NOT NULL,
    usuario      TEXT,
    caja_id      INTEGER REFERENCES cajas (id),   -- turno en el que se cobró
    metodo_pago  TEXT NOT NULL DEFAULT 'Efectivo' CHECK (metodo_pago IN ('Efectivo', 'Tarjeta')),
    recibido     REAL,
    estado       TEXT NOT NULL DEFAULT 'EMITIDA' CHECK (estado IN ('EMITIDA', 'ANULADA'))
);
CREATE INDEX IF NOT EXISTS idx_ventas_factura ON ventas (factura);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas (fecha);
CREATE INDEX IF NOT EXISTS idx_ventas_caja ON ventas (caja_id);

CREATE TABLE IF NOT EXISTS clientes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre     TEXT NOT NULL,
    cedula     TEXT UNIQUE,                  -- TEXT: 001-150390-0001X no es un número
    celular    TEXT,
    direccion  TEXT,
    correo     TEXT,
    activo     INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS proveedores (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre     TEXT NOT NULL,
    ruc        TEXT UNIQUE,
    telefono   TEXT,
    direccion  TEXT,
    correo     TEXT,
    activo     INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

-- Entradas de mercadería: suben el stock y actualizan el costo del producto.
CREATE TABLE IF NOT EXISTS compras (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha      TEXT NOT NULL,
    hora       TEXT NOT NULL,
    proveedor  TEXT NOT NULL,
    articulo   TEXT NOT NULL,
    cantidad   INTEGER NOT NULL CHECK (cantidad > 0),
    costo      REAL NOT NULL CHECK (costo >= 0),
    total      REAL NOT NULL,
    usuario    TEXT
);

PRAGMA user_version = 3;
