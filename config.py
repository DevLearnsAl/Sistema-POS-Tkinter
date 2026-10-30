"""Datos del negocio y parámetros generales. Cambialos aquí y se reflejan en
toda la aplicación y en las facturas."""

VERSION = "3.0"

NEGOCIO = {
    "nombre": "Minimarket",
    "ruc": "J0000000000000",
    "direccion": "Managua, Nicaragua",
    "telefono": "+505 2222 0000",
    "correo": "info@minimarket.com",
}

# Tasa general de IVA en Nicaragua. Cada producto puede ser gravado (15) o exento (0).
TASA_IVA = 15

# Código que se pide para crear usuarios nuevos desde la pantalla de registro.
# Los usuarios creados así entran como cajeros; el rol lo cambia un administrador.
CODIGO_REGISTRO = "1234"

# Respaldos automáticos de la base al abrir el programa.
CARPETA_RESPALDOS = "respaldos"
RESPALDOS_A_CONSERVAR = 10

# Qué puede hacer cada rol. El cajero vende; lo que afecta plata, precios o
# historial queda para el administrador.
PERMISOS = {
    "admin": {"compras", "proveedores", "reportes", "editar_inventario", "anular", "usuarios", "ver_costos",
              "ver_todas_las_cajas"},
    "cajero": set(),
}
