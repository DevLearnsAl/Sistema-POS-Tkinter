"""Funciones pequeñas que usan varios módulos."""
import datetime


def digito_ean13(base12):
    """Dígito verificador de un código EAN-13 a partir de sus primeros 12 dígitos."""
    suma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(base12))
    return str((10 - suma % 10) % 10)


def codigo_interno(numero):
    """Código EAN-13 para productos propios de la tienda.

    Los prefijos 200 a 299 están reservados por GS1 para uso interno, así estos
    códigos nunca chocan con los de productos comerciales."""
    base = f"200{numero:09d}"
    return base + digito_ean13(base)


def calcular_linea(precio, cantidad, tasa_iva):
    """Total e IVA de una línea. El precio ya incluye el IVA."""
    total = round(precio * cantidad, 2)
    iva = round(total * tasa_iva / (100 + tasa_iva), 2) if tasa_iva else 0.0
    return total, iva


def buscar_producto(texto, nombres, por_codigo, parcial=True):
    """Busca por código de barras exacto, por nombre exacto o, si hay una sola
    coincidencia, por parte del nombre. Devuelve el nombre o None."""
    t = texto.strip()
    if not t:
        return None
    if t in por_codigo:
        return por_codigo[t]
    bajo = t.lower()
    for nombre in nombres:
        if nombre.lower() == bajo:
            return nombre
    if parcial:
        coincidencias = [n for n in nombres if bajo in n.lower()]
        if len(coincidencias) == 1:
            return coincidencias[0]
    return None


def hoy():
    return datetime.date.today()


def fecha_corta(texto_iso):
    """'2026-09-25' -> '25/09/2026'."""
    try:
        return datetime.datetime.strptime(texto_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return texto_iso


DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
