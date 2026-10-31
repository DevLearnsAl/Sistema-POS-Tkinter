"""Registrar el cobro de una venta.

Es la operación más delicada del sistema: tiene que guardar la factura, descontar
el inventario y no dejar nada a medias. Vive fuera de las pantallas para que la
versión de escritorio y la de Android cobren exactamente igual.

Todo ocurre dentro de una transacción `BEGIN IMMEDIATE`, que toma el bloqueo de
escritura desde el principio. Así dos cajas no pueden sacar el mismo número de
factura ni vender la misma última unidad.
"""
import datetime

import db


class StockInsuficiente(Exception):
    def __init__(self, articulo, disponible):
        super().__init__(articulo)
        self.articulo = articulo
        self.disponible = disponible


class CajaCerrada(Exception):
    """No hay turno de caja abierto para registrar el cobro."""


def registrar_venta(carrito, cliente, usuario, metodo, recibido):
    """Guarda la venta completa y descuenta el stock.

    `carrito` es una lista de diccionarios con: codigo, articulo, precio, costo,
    cantidad, total, iva. Devuelve (numero_de_factura, caja_id, fecha, hora).
    """
    if not carrito:
        raise ValueError("No hay productos para cobrar.")
    ahora = datetime.datetime.now()
    fecha, hora = ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S")

    with db.conectar() as conn:
        conn.execute("BEGIN IMMEDIATE")
        # El turno se vuelve a leer adentro de la transacción: pudo cerrarse
        # mientras la pantalla de cobro estaba abierta.
        fila_caja = conn.execute("SELECT id FROM cajas WHERE estado = 'ABIERTA'").fetchone()
        if fila_caja is None:
            raise CajaCerrada
        caja_id = fila_caja[0]

        # Se revisa el stock de todo antes de tocar nada, para no guardar media venta.
        for linea in carrito:
            fila = conn.execute("SELECT stock, estado FROM articulos WHERE articulo = ?",
                                (linea["articulo"],)).fetchone()
            if fila is None or fila[1] != "Activo" or fila[0] < linea["cantidad"]:
                raise StockInsuficiente(linea["articulo"], fila[0] if fila else 0)

        numero = conn.execute("SELECT COALESCE(MAX(factura), 0) + 1 FROM ventas").fetchone()[0]
        for linea in carrito:
            conn.execute(
                "INSERT INTO ventas (factura, cliente, codigo, articulo, precio, cantidad, total, iva, costo, "
                "fecha, hora, usuario, caja_id, metodo_pago, recibido, estado) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'EMITIDA')",
                (numero, cliente, linea["codigo"], linea["articulo"], linea["precio"], linea["cantidad"],
                 linea["total"], linea["iva"], round(linea["costo"] * linea["cantidad"], 2), fecha, hora,
                 usuario, caja_id, metodo, recibido))
            conn.execute("UPDATE articulos SET stock = stock - ? WHERE articulo = ?",
                         (linea["cantidad"], linea["articulo"]))
    return numero, caja_id, fecha, hora
