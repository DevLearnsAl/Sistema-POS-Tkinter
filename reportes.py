"""Reportes: indicadores del período, ventas por día, productos más vendidos y stock bajo."""
import csv
import datetime
import math
import os
import tkinter as tk
from tkinter import messagebox

import ajustes
import db
from estilos import (FONDO, BLANCO, NAVY, TEXTO, TEXTO_SUAVE, VERDE, FUENTE, F_PEQUE, F_SUBTITULO, moneda, boton,
                     cambiar_tipo, panel, etiqueta, tabla, llenar_tabla)
from utilidades import DIAS, fecha_corta


def paso_redondo(valor):
    """Redondea hacia arriba a 1, 2 o 5 por una potencia de 10 (para las divisiones del gráfico)."""
    if valor <= 0:
        return 1
    exponente = math.floor(math.log10(valor))
    fraccion = valor / 10 ** exponente
    for n in (1, 2, 5, 10):
        if fraccion <= n:
            return n * 10 ** exponente


class Reportes(tk.Frame):
    PERIODOS = [("Hoy", 0), ("7 días", 6), ("30 días", 29)]

    def __init__(self, padre, controlador):
        super().__init__(padre, bg=FONDO)
        self.controlador = controlador
        self.dias = 6
        self.widgets()

    def widgets(self):
        barra = panel(self)
        barra.place(x=16, y=16, width=1068, height=56)
        etiqueta(barra, "Resumen de ventas", F_SUBTITULO, NAVY).place(x=16, y=14)
        self.lbl_rango = etiqueta(barra, "", F_PEQUE, TEXTO_SUAVE)
        self.lbl_rango.place(x=206, y=19)
        self.btns_periodo = {}
        for i, (texto, dias) in enumerate(self.PERIODOS):
            b = boton(barra, texto, lambda d=dias: self.cambiar_periodo(d),
                      "primario" if dias == self.dias else "secundario", F_PEQUE)
            b.place(x=636 + i * 96, y=10, width=88, height=34)
            self.btns_periodo[dias] = b
        boton(barra, "Exportar CSV", self.exportar, "secundario", F_PEQUE).place(x=940, y=10, width=112, height=34)

        self.kpis = {}
        for i, (clave, titulo) in enumerate([("ventas", "Ventas"), ("facturas", "Facturas"),
                                             ("ticket", "Ticket promedio"), ("ganancia", "Ganancia bruta")]):
            tarjeta = panel(self)
            tarjeta.place(x=16 + i * 271, y=86, width=255, height=100)
            etiqueta(tarjeta, titulo, F_PEQUE, TEXTO_SUAVE).place(x=16, y=12)
            valor = etiqueta(tarjeta, "", (FUENTE, 20, "bold"), NAVY)
            valor.place(x=16, y=32)
            detalle = etiqueta(tarjeta, "", F_PEQUE, TEXTO_SUAVE)
            detalle.place(x=16, y=70)
            self.kpis[clave] = (valor, detalle)

        self.panel_grafico = panel(self, "Ventas por día")
        self.panel_grafico.place(x=16, y=200, width=640, height=390)
        self.canvas = tk.Canvas(self.panel_grafico, bg=BLANCO, highlightthickness=0)
        self.canvas.place(x=16, y=44, width=606, height=334)

        top = panel(self, "Productos más vendidos")
        top.place(x=672, y=200, width=412, height=220)
        marco, self.tree_top = tabla(top, [("producto", "Producto", 196, "w"), ("cant", "Cant.", 64, "center"),
                                           ("total", "Total", 106, "e")], estilo="Compacta.Treeview")
        marco.place(x=16, y=44, width=380, height=168)

        bajo = panel(self, "Stock bajo")
        bajo.place(x=672, y=432, width=412, height=158)
        marco, self.tree_bajo = tabla(bajo, [("producto", "Producto", 220, "w"), ("stock", "Stock", 70, "center"),
                                             ("minimo", "Mínimo", 76, "center")], estilo="Compacta.Treeview")
        marco.place(x=16, y=44, width=380, height=106)

    def al_mostrar(self):
        self.actualizar()

    def cambiar_periodo(self, dias):
        self.dias = dias
        for d, b in self.btns_periodo.items():
            cambiar_tipo(b, "primario" if d == dias else "secundario")
        self.actualizar()

    def desde(self):
        return datetime.date.today() - datetime.timedelta(days=self.dias)

    def actualizar(self):
        desde = self.desde().isoformat()
        hoy = datetime.date.today()
        self.lbl_rango.config(text="Hoy, " + hoy.strftime("%d/%m/%Y") if self.dias == 0 else
                              f"Del {fecha_corta(desde)} al {hoy:%d/%m/%Y}")

        ventas, iva, costo, articulos, facturas = db.uno(
            "SELECT COALESCE(SUM(total), 0), COALESCE(SUM(iva), 0), COALESCE(SUM(costo), 0), "
            "COALESCE(SUM(cantidad), 0), COUNT(DISTINCT factura) FROM ventas WHERE estado = 'EMITIDA' AND fecha >= ?",
            (desde,))
        anuladas = db.uno("SELECT COUNT(DISTINCT factura) FROM ventas WHERE estado = 'ANULADA' AND fecha >= ?",
                          (desde,))[0]
        neto = ventas - iva
        ganancia = neto - costo
        margen = ganancia / neto * 100 if neto else 0
        impuesto = ajustes.nombre_impuesto()
        self._kpi("ventas", moneda(ventas), f"{impuesto} incluido: {moneda(iva)}")
        self._kpi("facturas", str(facturas),
                  f"{anuladas} anulada{'s' if anuladas != 1 else ''}" if anuladas else "Sin anulaciones")
        self._kpi("ticket", moneda(ventas / facturas if facturas else 0), f"{articulos} artículos vendidos")
        self._kpi("ganancia", moneda(ganancia), f"Margen {margen:.1f} % (sin {impuesto})")

        filas = db.consultar("SELECT articulo, SUM(cantidad), SUM(total) FROM ventas WHERE estado = 'EMITIDA' "
                             "AND fecha >= ? GROUP BY articulo ORDER BY SUM(cantidad) DESC, SUM(total) DESC LIMIT 5",
                             (desde,))
        llenar_tabla(self.tree_top, [(f[0], f[1], moneda(f[2])) for f in filas])
        filas = db.consultar("SELECT articulo, stock, stock_minimo FROM articulos WHERE estado = 'Activo' "
                             "AND stock <= stock_minimo ORDER BY stock * 1.0 / MAX(stock_minimo, 1), articulo")
        llenar_tabla(self.tree_bajo, filas, lambda f: ["alerta"])
        self.dibujar_grafico()

    def _kpi(self, clave, valor, detalle):
        self.kpis[clave][0].config(text=valor)
        self.kpis[clave][1].config(text=detalle)

    def dias_grafico(self):
        """Cuántas barras dibujar. Con «Hoy» una sola barra no diría nada, así que
        el mínimo son 7 días."""
        return max(self.dias + 1, 7)

    def ventas_por_dia(self):
        hoy = datetime.date.today()
        n = self.dias_grafico()
        dias = [hoy - datetime.timedelta(days=i) for i in range(n - 1, -1, -1)]
        totales = dict(db.consultar("SELECT fecha, SUM(total) FROM ventas WHERE estado = 'EMITIDA' AND fecha >= ? "
                                    "GROUP BY fecha", (dias[0].isoformat(),)))
        return [(d, totales.get(d.isoformat(), 0)) for d in dias]

    def dibujar_grafico(self):
        c = self.canvas
        c.delete("all")
        datos = self.ventas_por_dia()
        self.panel_grafico.titulo.config(text=f"Ventas por día · últimos {len(datos)} días")
        ancho, alto = 606, 334
        izquierda, derecha, arriba, abajo = 70, ancho - 10, 30, alto - 36
        paso = paso_redondo(max(v for _, v in datos) / 4)
        maximo = paso * 4
        for k in range(5):
            y = abajo - (abajo - arriba) * k / 4
            c.create_line(izquierda, y, derecha, y, fill="#E6EAF0")
            c.create_text(izquierda - 10, y, text=f"{paso * k:,.0f}", anchor="e", fill=TEXTO_SUAVE, font=(FUENTE, 9))
        c.create_text(izquierda - 10, arriba - 12, text=ajustes.simbolo(), anchor="e", fill=TEXTO_SUAVE,
                      font=(FUENTE, 9, "bold"))
        hueco = (derecha - izquierda) / len(datos)
        ancho_barra = min(48, hueco * 0.6)
        hoy = datetime.date.today()
        # Con muchas barras no cabe el valor encima ni el nombre de cada día.
        pocas = len(datos) <= 10
        for i, (dia, valor) in enumerate(datos):
            cx = izquierda + hueco * (i + 0.5)
            altura = (abajo - arriba) * valor / maximo if maximo else 0
            es_hoy = dia == hoy
            if valor > 0:
                c.create_rectangle(cx - ancho_barra / 2, abajo - altura, cx + ancho_barra / 2, abajo,
                                   fill=VERDE if es_hoy else NAVY, width=0)
                if pocas:
                    c.create_text(cx, abajo - altura - 10, text=f"{valor:,.0f}", fill=TEXTO, font=(FUENTE, 9, "bold"))
            if pocas:
                texto = "Hoy" if es_hoy else f"{DIAS[dia.weekday()]} {dia.day}"
            elif es_hoy or i % 5 == 0:
                texto = "Hoy" if es_hoy else str(dia.day)
            else:
                continue
            c.create_text(cx, abajo + 16, text=texto, fill=TEXTO if es_hoy else TEXTO_SUAVE,
                          font=(FUENTE, 9, "bold" if es_hoy else "normal"))

    def exportar(self):
        desde = self.desde().isoformat()
        filas = db.consultar(
            "SELECT factura, fecha, hora, cliente, codigo, articulo, cantidad, precio, total, iva, costo, "
            "metodo_pago, usuario, estado FROM ventas WHERE fecha >= ? ORDER BY factura, rowid", (desde,))
        os.makedirs("reportes", exist_ok=True)
        ruta = os.path.join("reportes", f"ventas_{desde}_al_{datetime.date.today().isoformat()}.csv")
        # utf-8-sig: Excel abre bien las tildes.
        with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
            w = csv.writer(archivo)
            w.writerow(["Factura", "Fecha", "Hora", "Cliente", "Código", "Producto", "Cantidad", "Precio", "Total",
                        ajustes.nombre_impuesto(), "Costo", "Pago", "Cajero", "Estado"])
            w.writerows(filas)
        if messagebox.askyesno("Reporte exportado", f"Se exportaron {len(filas)} líneas de venta a:\n{ruta}\n\n"
                                                    "¿Abrir la carpeta?", parent=self):
            os.startfile(os.path.abspath("reportes"))
