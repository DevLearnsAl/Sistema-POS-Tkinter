"""Configuración del negocio, guardada en la base de datos.

Todo lo que cambia de un negocio a otro (nombre, RUC, logo, moneda, impuesto)
vive acá y se edita desde la pantalla de Configuración. El código no se toca:
el mismo programa sirve para cualquier cliente.

Es un módulo de datos, sin interfaz, para que `estilos` pueda usarlo sin
importaciones circulares. La pantalla está en `configuracion.py`.
"""
import sqlite3

import db

# Valores con los que arranca una instalación nueva. La base guarda todo como
# texto; los ayudantes de abajo lo convierten a número cuando hace falta.
DEFECTOS = {
    "negocio_nombre": "Minimarket",
    "negocio_ruc": "J0000000000000",
    "negocio_direccion": "Managua, Nicaragua",
    "negocio_telefono": "+505 2222 0000",
    "negocio_correo": "info@minimarket.com",
    "negocio_logo": "",                     # ruta a una imagen, opcional
    "moneda_simbolo": "C$",
    "moneda_decimales": "2",
    "moneda_billetes": "100,200,500,1000",  # botones de pago rápido en el cobro
    "impuesto_nombre": "IVA",
    "impuesto_tasa": "15",                  # tasa general; cada producto es gravado o exento
    "factura_despedida": "¡Gracias por su compra!",
    "factura_nota": "Conserve esta factura como comprobante de su compra.",
}

_valores = dict(DEFECTOS)


def cargar():
    """Lee la configuración de la base. Si algo falta, queda el valor por defecto."""
    global _valores
    _valores = dict(DEFECTOS)
    try:
        for clave, valor in db.consultar("SELECT clave, valor FROM configuracion"):
            if clave in DEFECTOS:
                _valores[clave] = valor
    except sqlite3.Error:
        # Sin base todavía (primer arranque): se usan los valores por defecto.
        pass
    return _valores


def guardar(cambios):
    """Guarda los cambios y los deja activos de inmediato."""
    with db.conectar() as conn:
        for clave, valor in cambios.items():
            if clave not in DEFECTOS:
                raise KeyError(f"Ajuste desconocido: {clave}")
            conn.execute("INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
                         "ON CONFLICT (clave) DO UPDATE SET valor = excluded.valor", (clave, str(valor)))
    cargar()


def obtener(clave):
    return _valores.get(clave, DEFECTOS.get(clave, ""))


def numero(clave, por_defecto=0.0):
    try:
        return float(_valores.get(clave, DEFECTOS.get(clave)))
    except (TypeError, ValueError):
        return por_defecto


def negocio():
    """Los datos que salen en la factura y en los encabezados."""
    return {campo: obtener(f"negocio_{campo}")
            for campo in ("nombre", "ruc", "direccion", "telefono", "correo", "logo")}


def tasa_impuesto():
    return numero("impuesto_tasa", 15.0)


def nombre_impuesto():
    return obtener("impuesto_nombre") or "IVA"


def simbolo():
    return obtener("moneda_simbolo")


def moneda(valor):
    """Formatea un monto con el símbolo y los decimales del negocio."""
    decimales = int(numero("moneda_decimales", 2))
    return f"{simbolo()} {valor:,.{decimales}f}"


def leer_monto(texto):
    """Convierte en número lo que escribió una persona, o None si no se puede.

    Acepta que venga con el símbolo de la moneda y con separadores de miles,
    porque es lo que queda al copiar un monto de otra pantalla."""
    limpio = texto.replace(simbolo(), "").replace(",", "").replace(" ", "").strip()
    try:
        return float(limpio)
    except ValueError:
        return None


def billetes():
    """Denominaciones para los botones de pago rápido del cobro."""
    valores = []
    for parte in obtener("moneda_billetes").split(","):
        parte = parte.strip()
        if parte.isdigit() and int(parte) > 0:
            valores.append(int(parte))
    return valores[:4]      # en la ventana de cobro caben cuatro
