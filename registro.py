"""Registro de errores en un archivo.

Si el programa falla en la computadora de un cliente, el error queda escrito en
logs/minimarket.log con la fecha y el detalle completo. Sin esto, dar soporte es
adivinar: el usuario solo sabe decir «se cerró».

El archivo rota al llegar a 1 MB y se conservan 3 anteriores, así no crece sin
control en una caja que trabaja todos los días.
"""
import logging
import logging.handlers
import os
import traceback

import config

ARCHIVO = os.path.join(config.CARPETA_LOGS, "minimarket.log")
log = logging.getLogger("minimarket")


def iniciar():
    if log.handlers:
        return log
    os.makedirs(config.CARPETA_LOGS, exist_ok=True)
    manejador = logging.handlers.RotatingFileHandler(ARCHIVO, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", "%Y-%m-%d %H:%M:%S"))
    log.addHandler(manejador)
    log.setLevel(logging.INFO)
    log.info("=== Minimarket v%s iniciado ===", config.VERSION)
    return log


def error(mensaje, excepcion=None):
    """Anota un error. Con la excepción, guarda también dónde ocurrió."""
    if excepcion is not None:
        mensaje = f"{mensaje}\n{''.join(traceback.format_exception(excepcion))}"
    log.error(mensaje)


def info(mensaje, *args):
    log.info(mensaje, *args)
