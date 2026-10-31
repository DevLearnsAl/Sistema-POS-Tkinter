"""Pantalla de inventario: consultar precios y existencias.

En el teléfono el inventario es sobre todo de consulta, que es lo que se hace
en el mostrador: ver el precio y cuánto queda. El administrador además puede
corregir el stock, que es lo que más urge cuando algo no cuadra.
"""
import sqlite3

from kivy.metrics import dp, sp
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

import ajustes
import db
from tema import (BLANCO, NAVY, ROJO, TEXTO, TEXTO_SUAVE, VERDE, AMBAR, Boton, Campo, Fondo,
                  columna, etiqueta, fila)

from . import PantallaBase
from .ventas import aviso


def estado_stock(producto):
    """Texto y color del estado, igual que en la versión de escritorio."""
    if producto["estado"] == "Inactivo":
        return "Inactivo", TEXTO_SUAVE
    if producto["stock"] == 0:
        return "Agotado", ROJO
    if producto["stock"] <= producto["stock_minimo"]:
        return f"Stock bajo · {producto['stock']}", AMBAR
    return f"Stock: {producto['stock']}", VERDE


class PantallaInventario(PantallaBase):
    nombre = "inventario"
    titulo_modulo = "Inventario"

    COLUMNAS = ["id", "codigo", "articulo", "precio", "costo", "stock", "stock_minimo", "iva", "estado"]

    def construir(self):
        self.buscador = Campo(pista="Buscar por nombre o código")
        self.buscador.bind(text=lambda *_: self.refrescar())
        self.cuerpo.add_widget(self.buscador)

        self.filtros = fila(alto=dp(42))
        self.filtro = "Todos"
        self.botones_filtro = {}
        for nombre in ("Todos", "Stock bajo", "Inactivos"):
            b = Boton(nombre, lambda n=nombre: self.cambiar_filtro(n),
                      "primario" if nombre == "Todos" else "secundario", tamano=sp(13), height=dp(42))
            self.botones_filtro[nombre] = b
            self.filtros.add_widget(b)
        self.cuerpo.add_widget(self.filtros)

        self.lbl_conteo = etiqueta("", tamano=sp(12), color=TEXTO_SUAVE, height=dp(22))
        self.cuerpo.add_widget(self.lbl_conteo)

        desplazable = ScrollView()
        self.lista = columna(espacio=dp(6), size_hint_y=None)
        self.lista.bind(minimum_height=self.lista.setter("height"))
        desplazable.add_widget(self.lista)
        self.cuerpo.add_widget(desplazable)

    def al_mostrar(self):
        self.refrescar()

    def cambiar_filtro(self, nombre):
        self.filtro = nombre
        for n, b in self.botones_filtro.items():
            b.cambiar_tipo("primario" if n == nombre else "secundario")
        self.refrescar()

    def _pasa(self, p):
        if self.filtro == "Stock bajo":
            return p["estado"] == "Activo" and p["stock"] <= p["stock_minimo"]
        if self.filtro == "Inactivos":
            return p["estado"] == "Inactivo"
        return True

    def refrescar(self):
        filas = db.consultar(f"SELECT {', '.join(self.COLUMNAS)} FROM articulos ORDER BY articulo")
        productos = [dict(zip(self.COLUMNAS, f)) for f in filas]
        texto = self.buscador.text.strip().lower()
        visibles = [p for p in productos
                    if (not texto or texto in p["articulo"].lower() or texto in (p["codigo"] or ""))
                    and self._pasa(p)]

        self.lista.clear_widgets()
        for p in visibles:
            self.lista.add_widget(self.tarjeta(p))
        if not visibles:
            self.lista.add_widget(etiqueta("No hay productos que coincidan.", tamano=sp(13),
                                           color=TEXTO_SUAVE, alineacion="center", height=dp(40)))
        self.lbl_conteo.text = f"{len(visibles)} de {len(productos)} productos"

    def tarjeta(self, producto):
        texto_estado, color = estado_stock(producto)
        caja = Fondo(color=BLANCO, orientation="horizontal", size_hint_y=None, height=dp(70),
                     padding=[dp(12), dp(8), dp(12), dp(8)], spacing=dp(8))
        izquierda = columna(espacio=0)
        izquierda.add_widget(etiqueta(producto["articulo"], tamano=sp(14), color=TEXTO, negrita=True,
                                      height=dp(24)))
        izquierda.add_widget(etiqueta(producto["codigo"] or "Sin código", tamano=sp(11),
                                      color=TEXTO_SUAVE, height=dp(18)))
        izquierda.add_widget(etiqueta(texto_estado, tamano=sp(12), color=color, height=dp(18)))
        caja.add_widget(izquierda)

        derecha = columna(espacio=dp(2), size_hint_x=0.42)
        derecha.add_widget(etiqueta(ajustes.moneda(producto["precio"]), tamano=sp(16), color=NAVY,
                                    negrita=True, alineacion="right", height=dp(26)))
        if self.app.puede("editar_inventario"):
            derecha.add_widget(Boton("Corregir stock", lambda p=producto: self.corregir(p), "secundario",
                                     tamano=sp(11), height=dp(32)))
        else:
            derecha.add_widget(Widget())
        caja.add_widget(derecha)
        return caja

    def corregir(self, producto):
        if not self.app.puede("editar_inventario"):
            aviso("Inventario", "Solo un administrador puede corregir el stock.")
            return
        VentanaStock(self, producto).open()


class VentanaStock(Popup):
    """Corregir las existencias de un producto, contando lo que hay."""

    def __init__(self, pantalla, producto, **kw):
        self.pantalla = pantalla
        self.producto = producto
        contenido = columna(padding=dp(16), espacio=dp(10))
        super().__init__(title="Corregir stock", content=contenido, size_hint=(0.9, None),
                         height=dp(340), title_color=TEXTO, separator_color=NAVY, **kw)
        contenido.add_widget(etiqueta(producto["articulo"], tamano=sp(16), color=TEXTO, negrita=True,
                                      height=dp(28)))
        contenido.add_widget(etiqueta(f"El sistema dice que hay {producto['stock']} unidades.",
                                      tamano=sp(13), color=TEXTO_SUAVE, height=dp(26)))
        self.cantidad = Campo(pista="Unidades contadas", input_filter="int")
        self.cantidad.text = str(producto["stock"])
        contenido.add_widget(self.cantidad)
        self.lbl_error = etiqueta("", tamano=sp(12), color=ROJO, height=dp(28))
        contenido.add_widget(self.lbl_error)
        contenido.add_widget(Widget())
        contenido.add_widget(fila(Boton("Cancelar", self.dismiss, "secundario", size_hint_x=0.4),
                                  Boton("Guardar", self.confirmar, "primario", size_hint_x=0.6)))

    def confirmar(self):
        texto = self.cantidad.text.strip()
        if not texto.isdigit():
            self.lbl_error.text = "Escribí un número entero de unidades."
            return
        try:
            db.ejecutar("UPDATE articulos SET stock = ? WHERE id = ?", (int(texto), self.producto["id"]))
        except sqlite3.Error as e:
            self.lbl_error.text = f"No se pudo guardar: {e}"
            return
        self.dismiss()
        self.pantalla.refrescar()
