"""Turnos de caja: abrir, movimientos de efectivo, resumen y cierre con arqueo.

Este módulo no sabe nada de pantallas: solo habla con la base de datos. Así la
misma regla sirve para la versión de escritorio (`caja.py`) y para la de Android,
sin copiar la lógica en dos lados.

    esperado   = monto inicial + ventas en efectivo + entradas - salidas
    diferencia = contado - esperado      (negativo = falta, positivo = sobra)

Las facturas anuladas no suman, porque ese dinero se devolvió. Las devoluciones
parciales tampoco llevan un movimiento aparte: la venta queda con el monto neto,
así que el esperado ya las descuenta.
"""
import datetime
import sqlite3

import db


class TurnoCerrado(Exception):
    """Se intentó operar sobre un turno que ya no está abierto."""


def caja_abierta():
    """El turno abierto, o None. Solo puede haber uno (índice único en el esquema)."""
    return db.uno("SELECT id, usuario, fecha_apertura, hora_apertura, monto_inicial FROM cajas "
                  "WHERE estado = 'ABIERTA'")


def resumen(caja_id):
    """Cuánto debería haber en la caja de este turno y de dónde viene."""
    efectivo, tarjeta, facturas = db.uno(
        "SELECT COALESCE(SUM(CASE WHEN metodo_pago = 'Efectivo' THEN total ELSE 0 END), 0), "
        "       COALESCE(SUM(CASE WHEN metodo_pago = 'Tarjeta'  THEN total ELSE 0 END), 0), "
        "       COUNT(DISTINCT factura) "
        "FROM ventas WHERE caja_id = ? AND estado = 'EMITIDA'", (caja_id,))
    entradas, salidas = db.uno(
        "SELECT COALESCE(SUM(CASE WHEN tipo = 'ENTRADA' THEN monto ELSE 0 END), 0), "
        "       COALESCE(SUM(CASE WHEN tipo = 'SALIDA'  THEN monto ELSE 0 END), 0) "
        "FROM movimientos_caja WHERE caja_id = ?", (caja_id,))
    inicial = db.uno("SELECT monto_inicial FROM cajas WHERE id = ?", (caja_id,))[0]
    return {"inicial": inicial, "efectivo": efectivo, "tarjeta": tarjeta, "facturas": facturas,
            "entradas": entradas, "salidas": salidas,
            "esperado": round(inicial + efectivo + entradas - salidas, 2)}


def abrir_turno(usuario, monto_inicial):
    """Abre un turno. Devuelve el id, o lanza ValueError si ya hay uno abierto."""
    ahora = datetime.datetime.now()
    try:
        with db.conectar() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM cajas WHERE estado = 'ABIERTA'").fetchone():
                raise ValueError("Ya hay un turno de caja abierto.")
            cur = conn.execute(
                "INSERT INTO cajas (usuario, fecha_apertura, hora_apertura, monto_inicial, estado) "
                "VALUES (?, ?, ?, ?, 'ABIERTA')",
                (usuario, ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"), monto_inicial))
            return cur.lastrowid
    except sqlite3.IntegrityError:
        # El índice único idx_caja_abierta lo impide aunque dos cajas lo intenten a la vez.
        raise ValueError("Ya hay un turno de caja abierto.")


def registrar_movimiento(caja_id, tipo, monto, motivo, usuario):
    """Entrada o salida de efectivo que no es una venta."""
    if tipo not in ("ENTRADA", "SALIDA"):
        raise ValueError("El movimiento debe ser ENTRADA o SALIDA.")
    if monto <= 0:
        raise ValueError("El monto debe ser mayor que cero.")
    if tipo == "SALIDA" and monto > resumen(caja_id)["esperado"]:
        raise ValueError("No puede sacar más efectivo del que hay en la caja.")
    ahora = datetime.datetime.now()
    db.ejecutar("INSERT INTO movimientos_caja (caja_id, tipo, monto, motivo, fecha, hora, usuario) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (caja_id, tipo, round(monto, 2), motivo, ahora.strftime("%Y-%m-%d"),
                 ahora.strftime("%H:%M:%S"), usuario))


def cerrar_turno(caja_id, usuario, contado, observacion=None):
    """Cierra el turno con el efectivo contado. Devuelve el arqueo.

    El esperado se vuelve a calcular acá y no se recibe de afuera: es el número
    que queda guardado, y tiene que salir de la base en el momento del cierre."""
    datos = resumen(caja_id)
    esperado = datos["esperado"]
    diferencia = round(contado - esperado, 2)
    ahora = datetime.datetime.now()
    with db.conectar() as conn:
        cur = conn.execute(
            "UPDATE cajas SET fecha_cierre = ?, hora_cierre = ?, usuario_cierre = ?, esperado = ?, "
            "monto_contado = ?, diferencia = ?, observacion = ?, estado = 'CERRADA' "
            "WHERE id = ? AND estado = 'ABIERTA'",
            (ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"), usuario, esperado,
             round(contado, 2), diferencia, observacion, caja_id))
        if cur.rowcount == 0:
            raise TurnoCerrado("Ese turno ya está cerrado.")
    return {"esperado": esperado, "contado": round(contado, 2), "diferencia": diferencia}


def arqueos(usuario=None, limite=100):
    """Turnos ya cerrados. Con `usuario`, solo los de esa persona."""
    sql = "SELECT fecha_cierre, usuario, esperado, monto_contado, diferencia FROM cajas WHERE estado = 'CERRADA'"
    parametros = []
    if usuario:
        sql += " AND usuario = ?"
        parametros.append(usuario)
    return db.consultar(sql + " ORDER BY id DESC LIMIT ?", parametros + [limite])
