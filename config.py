"""Parámetros del programa.

Acá va lo que es igual en toda instalación. Lo que cambia de un negocio a otro
(nombre, RUC, logo, moneda, tasa de impuesto, textos de la factura) está en la
base de datos y se edita desde la pantalla de Configuración: ver `ajustes.py`.
"""

VERSION = "5.0"

# Carpetas que el programa crea junto a database.db.
CARPETA_RESPALDOS = "respaldos"
CARPETA_LOGS = "logs"
RESPALDOS_A_CONSERVAR = 10

# Qué puede hacer cada rol. El cajero vende; lo que afecta plata, precios o
# historial queda para el administrador.
PERMISOS = {
    "admin": {"compras", "proveedores", "reportes", "editar_inventario", "anular", "usuarios", "ver_costos",
              "ver_todas_las_cajas", "configuracion"},
    "cajero": set(),
}
