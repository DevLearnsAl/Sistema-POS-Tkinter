"""Factura en PDF (ReportLab)."""
import os
import subprocess
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

import ajustes
import db
from utilidades import fecha_corta

NAVY = colors.HexColor("#1D3F7A")
TEXTO = colors.HexColor("#1B2433")
SUAVE = colors.HexColor("#4A5568")
FONDO_CLARO = colors.HexColor("#EEF2F8")
FILA = colors.HexColor("#F5F7FB")
BORDE = colors.HexColor("#D6DDE8")
ROJO = colors.HexColor("#B42318")

ANCHO, ALTO = letter
M = 40                         # margen
LIMITE_INFERIOR = 190          # espacio reservado para totales y pie en la última página


def datos_desde_bd(numero):
    filas = db.consultar(
        "SELECT codigo, articulo, precio, cantidad, total, iva, cliente, fecha, hora, usuario, metodo_pago, "
        "recibido, estado FROM ventas WHERE factura = ? ORDER BY rowid", (numero,))
    if not filas:
        raise ValueError(f"No existe la factura {numero}")
    f = filas[0]
    return {"numero": numero, "cliente": f[6], "fecha": f[7], "hora": f[8], "usuario": f[9], "metodo": f[10],
            "recibido": f[11], "estado": f[12],
            "lineas": [{"codigo": r[0] or "", "articulo": r[1], "precio": r[2], "cantidad": r[3], "total": r[4],
                        "iva": r[5]} for r in filas]}


def _logo(ruta, alto):
    """Devuelve (imagen, ancho) para dibujar el logo, o None si no se puede usar."""
    if not ruta or not os.path.exists(ruta):
        return None
    try:
        imagen = ImageReader(ruta)
        ancho_original, alto_original = imagen.getSize()
        return imagen, alto * ancho_original / alto_original
    except Exception:
        return None


def _encabezado(c, d, pagina):
    negocio = ajustes.negocio()
    c.setFillColor(NAVY)
    c.rect(0, ALTO - 96, ANCHO, 96, stroke=0, fill=1)
    c.setFillColor(colors.white)
    x = M
    logo = _logo(negocio["logo"], 44)
    if logo:
        imagen, ancho = logo
        c.drawImage(imagen, M, ALTO - 72, width=ancho, height=44, mask="auto")
        x = M + ancho + 14
    c.setFont("Helvetica-Bold", 22)
    c.drawString(x, ALTO - 50, negocio["nombre"].upper()[:28])
    c.setFont("Helvetica", 10)
    c.drawString(x, ALTO - 68, "Sistema de facturación e inventario")
    c.setFont("Helvetica-Bold", 20)
    c.drawRightString(ANCHO - M, ALTO - 50, "FACTURA")
    c.setFont("Helvetica", 11)
    c.drawRightString(ANCHO - M, ALTO - 68, f"N° {d['numero']:06d}")
    if pagina > 1:
        c.setFont("Helvetica", 9)
        c.drawRightString(ANCHO - M, ALTO - 84, f"Página {pagina}")
    return ALTO - 96


def _sello_anulada(c, d):
    """Sello semitransparente encima del contenido de la página."""
    if d.get("estado") != "ANULADA":
        return
    c.saveState()
    c.setFillColor(ROJO)
    c.setFillAlpha(0.18)
    c.translate(ANCHO / 2, ALTO / 2 - 40)
    c.rotate(32)
    c.setFont("Helvetica-Bold", 96)
    c.drawCentredString(0, 0, "ANULADA")
    c.restoreState()


COLUMNAS = [("Código", M + 8, "l"), ("Descripción", M + 104, "l"), ("Cant.", 372, "r"), ("Precio", 442, "r"),
            ("Imp.", 504, "r"), ("Total", ANCHO - M - 8, "r")]


def _cabecera_tabla(c, y):
    c.setFillColor(NAVY)
    c.rect(M, y - 22, ANCHO - 2 * M, 22, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9.5)
    for titulo, x, alin in COLUMNAS:
        (c.drawRightString if alin == "r" else c.drawString)(x, y - 15, titulo)
    return y - 22


def _recortar(c, texto, ancho, fuente="Helvetica", tam=9.5):
    if c.stringWidth(texto, fuente, tam) <= ancho:
        return texto
    while texto and c.stringWidth(texto + "…", fuente, tam) > ancho:
        texto = texto[:-1]
    return texto + "…"


def generar_pdf(d):
    os.makedirs("facturas", exist_ok=True)
    ruta = os.path.join("facturas", f"Factura_{d['numero']}.pdf")
    c = canvas.Canvas(ruta, pagesize=letter)
    c.setTitle(f"Factura {d['numero']:06d}")
    c.setAuthor(ajustes.obtener("negocio_nombre"))

    total = round(sum(l["total"] for l in d["lineas"]), 2)
    iva = round(sum(l["iva"] for l in d["lineas"]), 2)
    subtotal = round(total - iva, 2)
    n = ajustes.negocio()
    impuesto = ajustes.nombre_impuesto()

    pagina = 1
    y = _encabezado(c, d, pagina) - 30

    # Datos del negocio (izquierda) y de la factura (derecha)
    c.setFillColor(TEXTO)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y, n["nombre"])
    c.setFont("Helvetica", 9.5)
    c.setFillColor(SUAVE)
    for i, linea in enumerate([f"RUC: {n['ruc']}", n["direccion"], f"Tel.: {n['telefono']}", n["correo"]]):
        c.drawString(M, y - 15 - i * 13, linea)
    datos = [("Fecha", fecha_corta(d["fecha"])), ("Hora", d["hora"][:5]), ("Cajero", d.get("usuario") or "—"),
             ("Pago", d.get("metodo") or "Efectivo")]
    for i, (etiqueta, valor) in enumerate(datos):
        yy = y - i * 14
        c.setFillColor(SUAVE)
        c.setFont("Helvetica", 9.5)
        c.drawString(ANCHO - M - 190, yy, etiqueta)
        c.setFillColor(TEXTO)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawRightString(ANCHO - M, yy, valor)
    y -= 78

    # Cliente
    c.setFillColor(FONDO_CLARO)
    c.rect(M, y - 34, ANCHO - 2 * M, 34, stroke=0, fill=1)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(M + 10, y - 13, "CLIENTE")
    c.setFillColor(TEXTO)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M + 10, y - 27, d["cliente"])
    y -= 50

    # Detalle
    y = _cabecera_tabla(c, y)
    c.setFont("Helvetica", 9.5)
    for i, l in enumerate(d["lineas"]):
        if y - 20 < LIMITE_INFERIOR:
            _sello_anulada(c, d)
            c.showPage()
            pagina += 1
            y = _cabecera_tabla(c, _encabezado(c, d, pagina) - 30)
            c.setFont("Helvetica", 9.5)
        if i % 2:
            c.setFillColor(FILA)
            c.rect(M, y - 20, ANCHO - 2 * M, 20, stroke=0, fill=1)
        c.setFillColor(TEXTO)
        valores = [l["codigo"], _recortar(c, l["articulo"], 200), str(l["cantidad"]), f"{l['precio']:,.2f}",
                   f"{l['iva']:,.2f}" if l["iva"] else "Exento", f"{l['total']:,.2f}"]
        for (_, x, alin), valor in zip(COLUMNAS, valores):
            (c.drawRightString if alin == "r" else c.drawString)(x, y - 14, valor)
        y -= 20
    c.setStrokeColor(BORDE)
    c.setLineWidth(0.8)
    c.line(M, y, ANCHO - M, y)

    # Totales
    y -= 22
    x_etiqueta, x_valor = ANCHO - M - 210, ANCHO - M
    filas = [(f"Subtotal (sin {impuesto})", subtotal), (f"{impuesto} {ajustes.tasa_impuesto():g} %", iva)]
    c.setFont("Helvetica", 10)
    for etiqueta, valor in filas:
        c.setFillColor(SUAVE)
        c.drawString(x_etiqueta, y, etiqueta)
        c.setFillColor(TEXTO)
        c.drawRightString(x_valor, y, ajustes.moneda(valor))
        y -= 16
    y -= 6
    c.setFillColor(NAVY)
    c.rect(x_etiqueta - 10, y - 14, x_valor - x_etiqueta + 10, 26, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x_etiqueta, y - 5, "TOTAL")
    c.drawRightString(x_valor - 8, y - 5, ajustes.moneda(total))
    y -= 34
    recibido = d.get("recibido")
    if recibido is not None:
        c.setFont("Helvetica", 10)
        pagos = [("Recibido", recibido)]
        if (d.get("metodo") or "Efectivo") == "Efectivo":
            pagos.append(("Cambio", round(recibido - total, 2)))
        for etiqueta, valor in pagos:
            c.setFillColor(SUAVE)
            c.drawString(x_etiqueta, y, etiqueta)
            c.setFillColor(TEXTO)
            c.drawRightString(x_valor, y, ajustes.moneda(valor))
            y -= 16

    # Notas y pie
    c.setFillColor(SUAVE)
    c.setFont("Helvetica", 8.5)
    c.drawString(M, 110, f"Precios con {impuesto} incluido. Los productos exentos van marcados en la "
                         "columna «Imp.».")
    c.drawString(M, 97, ajustes.obtener("factura_nota"))
    c.setStrokeColor(BORDE)
    c.line(M, 80, ANCHO - M, 80)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(ANCHO / 2, 58, ajustes.obtener("factura_despedida"))
    c.setFillColor(SUAVE)
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(ANCHO / 2, 42, f"{n['nombre']}  ·  {n['direccion']}  ·  {n['telefono']}")
    _sello_anulada(c, d)
    c.save()
    return ruta


def abrir(ruta):
    ruta = os.path.abspath(ruta)
    if sys.platform.startswith("win"):
        os.startfile(ruta)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", ruta])
    else:
        subprocess.Popen(["xdg-open", ruta])
