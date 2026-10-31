"""Pantalla de ventas: buscar productos, armar el carrito y cobrar.

El carrito y los totales se calculan con `utilidades.calcular_linea`, y el cobro
lo guarda `cobro.registrar_venta`: los mismos módulos que usa la computadora. Lo
único propio de Android es cómo se ve y cómo se toca.
"""
import sqlite3

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

import ajustes
import cobro
import db
import turnos
from utilidades import buscar_producto, calcular_linea
from tema import (BLANCO, BORDE, CLARO, FONDO, NAVY, ROJO, TEXTO, TEXTO_SUAVE, VERDE, AMBAR, MARGEN,
                  Boton, Campo, Fondo, columna, etiqueta, fila, separador)

from . import PantallaBase


def aviso(titulo_texto, mensaje):
    """Mensaje corto, el equivalente a messagebox en la computadora."""
    contenido = columna(padding=dp(16))
    contenido.add_widget(etiqueta(mensaje, tamano=sp(15), color=TEXTO, size_hint_y=1))
    ventana = Popup(title=titulo_texto, content=contenido, size_hint=(0.9, None), height=dp(240),
                    title_color=TEXTO, separator_color=NAVY)
    contenido.add_widget(Boton("Entendido", ventana.dismiss, "secundario"))
    ventana.open()
    return ventana


class FilaCarrito(Fondo):
    """Una línea del carrito. Tocarla ofrece quitarla."""

    def __init__(self, linea, al_quitar, **kw):
        super().__init__(color=BLANCO, orientation="horizontal", size_hint_y=None, height=dp(58),
                         padding=[dp(10), dp(6), dp(10), dp(6)], spacing=dp(6), **kw)
        izquierda = columna(espacio=0)
        izquierda.add_widget(etiqueta(linea["articulo"], tamano=sp(14), color=TEXTO, negrita=True,
                                      height=dp(22)))
        izquierda.add_widget(etiqueta(f"{linea['cantidad']} × {ajustes.moneda(linea['precio'])}",
                                      tamano=sp(12), color=TEXTO_SUAVE, height=dp(20)))
        self.add_widget(izquierda)
        self.add_widget(etiqueta(ajustes.moneda(linea["total"]), tamano=sp(15), color=TEXTO,
                                 negrita=True, alineacion="right", size_hint_x=0.4, height=dp(46)))
        # Una "X" común: la fuente que trae Kivy no tiene el símbolo ✕ y en su
        # lugar dibuja un cuadrito vacío.
        self.add_widget(Boton("X", al_quitar, "secundario", tamano=sp(15), size_hint_x=None,
                              width=dp(44), height=dp(44)))


class PantallaVentas(PantallaBase):
    nombre = "ventas"
    titulo_modulo = "Ventas"

    def construir(self):
        self.carrito = []
        self.productos = {}
        self.por_codigo = {}
        self.nombres = []
        self.caja_id = None

        # ---- buscador ----
        self.buscador = Campo(pista="Código de barras o nombre del producto")
        self.buscador.bind(text=lambda *_: self.filtrar())
        self.buscador.bind(on_text_validate=lambda *_: self.agregar_escrito())
        self.cuerpo.add_widget(self.buscador)

        self.caja_resultados = ScrollView(size_hint_y=None, height=dp(0))
        self.lista_resultados = columna(espacio=dp(4), size_hint_y=None, padding=[0, 0, 0, 0])
        self.lista_resultados.bind(minimum_height=self.lista_resultados.setter("height"))
        self.caja_resultados.add_widget(self.lista_resultados)
        self.cuerpo.add_widget(self.caja_resultados)

        # ---- carrito ----
        self.lbl_vacio = etiqueta("Buscá un producto para empezar la venta.", tamano=sp(14),
                                  color=TEXTO_SUAVE, alineacion="center", height=dp(40))
        self.cuerpo.add_widget(self.lbl_vacio)

        desplazable = ScrollView()
        self.lista_carrito = columna(espacio=dp(6), size_hint_y=None)
        self.lista_carrito.bind(minimum_height=self.lista_carrito.setter("height"))
        desplazable.add_widget(self.lista_carrito)
        self.cuerpo.add_widget(desplazable)

        # ---- totales ----
        self.cuerpo.add_widget(separador())
        self.lbl_impuesto = etiqueta("", tamano=sp(13), color=TEXTO_SUAVE, height=dp(22))
        self.cuerpo.add_widget(self.lbl_impuesto)
        caja_total = fila(etiqueta("Total", tamano=sp(16), color=TEXTO_SUAVE, height=dp(42)),
                          etiqueta("", tamano=sp(28), color=NAVY, negrita=True, alineacion="right",
                                   height=dp(42)), alto=dp(42))
        self.lbl_total = caja_total.children[0]
        self.cuerpo.add_widget(caja_total)

        self.lbl_caja = etiqueta("", tamano=sp(12), color=TEXTO_SUAVE, height=dp(20))
        self.cuerpo.add_widget(self.lbl_caja)

        self.btn_cobrar = Boton("Cobrar", self.cobrar, "exito", tamano=sp(19))
        self.btn_cobrar.height = dp(58)
        self.cuerpo.add_widget(self.btn_cobrar)

    # ------------------------------------------------------------------ datos
    def al_mostrar(self):
        self.cargar_productos()
        self.actualizar_caja()
        self.refrescar_carrito()

    def cargar_productos(self):
        filas = db.consultar("SELECT articulo, codigo, precio, costo, stock, iva FROM articulos "
                             "WHERE estado = 'Activo' ORDER BY articulo")
        self.productos = {f[0]: {"codigo": f[1] or "", "precio": f[2], "costo": f[3], "stock": f[4], "iva": f[5]}
                          for f in filas}
        self.por_codigo = {d["codigo"]: n for n, d in self.productos.items() if d["codigo"]}
        self.nombres = list(self.productos)

    def actualizar_caja(self):
        turno = turnos.caja_abierta()
        self.caja_id = turno[0] if turno else None
        if turno:
            self.lbl_caja.text = f"Caja abierta por {turno[1]} ({turno[3][:5]})"
            self.lbl_caja.color = TEXTO_SUAVE
        else:
            self.lbl_caja.text = "Caja cerrada · abrila antes de cobrar"
            self.lbl_caja.color = ROJO

    # ------------------------------------------------------------------ búsqueda
    def filtrar(self):
        texto = self.buscador.text.strip().lower()
        self.lista_resultados.clear_widgets()
        if not texto:
            self.caja_resultados.height = dp(0)
            return
        coincidencias = [n for n in self.nombres
                         if texto in n.lower() or self.productos[n]["codigo"].startswith(texto)][:6]
        for nombre in coincidencias:
            datos = self.productos[nombre]
            boton = Boton(f"{nombre}   ·   {ajustes.moneda(datos['precio'])}   ·   {datos['stock']} u.",
                          lambda n=nombre: self.agregar(n), "secundario", tamano=sp(14))
            boton.height = dp(46)
            boton.etiqueta.halign = "left"
            boton.etiqueta.padding_x = dp(10)
            self.lista_resultados.add_widget(boton)
        self.caja_resultados.height = min(len(coincidencias), 4) * dp(50)

    def agregar_escrito(self):
        """Lo que se escribió y se confirmó con Enter, o lo que mandó el lector de códigos."""
        texto = self.buscador.text.strip()
        if not texto:
            return
        nombre = buscar_producto(texto, self.nombres, self.por_codigo)
        if not nombre:
            parecidos = [n for n in self.nombres if texto.lower() in n.lower()]
            if len(parecidos) > 1:
                aviso("Ventas", f"Hay {len(parecidos)} productos que coinciden con «{texto}». "
                                "Elegí uno de la lista.")
            else:
                aviso("Ventas", f"No se encontró ningún producto activo con «{texto}».")
            return
        self.agregar(nombre)

    def agregar(self, nombre, cantidad=1):
        datos = self.productos.get(nombre)
        if not datos:
            return
        en_carrito = sum(l["cantidad"] for l in self.carrito if l["articulo"] == nombre)
        if en_carrito + cantidad > datos["stock"]:
            aviso("Stock insuficiente",
                  f"De «{nombre}» hay {datos['stock']} en inventario"
                  + (f" y ya agregaste {en_carrito}." if en_carrito else "."))
            return
        linea = next((l for l in self.carrito if l["articulo"] == nombre), None)
        if linea:
            linea["cantidad"] += cantidad
        else:
            linea = {"codigo": datos["codigo"], "articulo": nombre, "precio": datos["precio"],
                     "costo": datos["costo"], "tasa": datos["iva"], "cantidad": cantidad}
            self.carrito.append(linea)
        linea["total"], linea["iva"] = calcular_linea(linea["precio"], linea["cantidad"], linea["tasa"])
        self.buscador.text = ""
        self.refrescar_carrito()

    def quitar(self, linea):
        if linea in self.carrito:
            self.carrito.remove(linea)
        self.refrescar_carrito()

    # ------------------------------------------------------------------ totales
    def totales(self):
        total = round(sum(l["total"] for l in self.carrito), 2)
        impuesto = round(sum(l["iva"] for l in self.carrito), 2)
        return {"total": total, "iva": impuesto, "subtotal": round(total - impuesto, 2),
                "articulos": sum(l["cantidad"] for l in self.carrito)}

    def refrescar_carrito(self):
        self.lista_carrito.clear_widgets()
        for linea in self.carrito:
            self.lista_carrito.add_widget(FilaCarrito(linea, lambda l=linea: self.quitar(l)))
        t = self.totales()
        self.lbl_vacio.height = dp(0) if self.carrito else dp(40)
        self.lbl_vacio.opacity = 0 if self.carrito else 1
        self.lbl_total.text = ajustes.moneda(t["total"])
        impuesto = ajustes.nombre_impuesto()
        self.lbl_impuesto.text = (f"{t['articulos']} artículos  ·  Subtotal {ajustes.moneda(t['subtotal'])}  ·  "
                                  f"{impuesto} {ajustes.moneda(t['iva'])}") if self.carrito else ""
        self.btn_cobrar.habilitar(bool(self.carrito))

    # ------------------------------------------------------------------ cobro
    def cobrar(self):
        if not self.carrito:
            return
        self.actualizar_caja()
        if not self.caja_id:
            aviso("Caja cerrada", "No hay un turno de caja abierto.\n\nAbrilo desde el módulo Caja "
                                  "para poder cobrar.")
            return
        VentanaCobro(self, self.totales()["total"]).open()

    def confirmar_cobro(self, recibido, metodo, ventana):
        cliente = "Consumidor final"
        try:
            numero, _, _, _ = cobro.registrar_venta(self.carrito, cliente, self.app.usuario, metodo, recibido)
        except cobro.CajaCerrada:
            ventana.dismiss()
            aviso("Caja cerrada", "El turno se cerró. La venta no se guardó.")
            self.actualizar_caja()
            return
        except cobro.StockInsuficiente as e:
            ventana.dismiss()
            aviso("Stock insuficiente", f"No hay suficiente «{e.articulo}» (disponible: {e.disponible}).\n"
                                        "La venta no se guardó.")
            self.cargar_productos()
            return
        except sqlite3.Error as e:
            ventana.dismiss()
            aviso("Error", f"No se pudo registrar la venta: {e}")
            return

        total = self.totales()["total"]
        cambio = round(recibido - total, 2) if metodo == "Efectivo" else 0.0
        # La factura se genera después de guardar: si falla, la venta ya está.
        ruta = None
        try:
            import factura
            ruta = factura.generar_pdf(factura.datos_desde_bd(numero))
        except Exception as e:
            import registro
            registro.error("No se pudo generar la factura en el teléfono", e)

        self.carrito.clear()
        self.cargar_productos()
        self.refrescar_carrito()
        ventana.dismiss()
        VentanaVentaHecha(numero, total, cambio, metodo, ruta).open()


class VentanaCobro(Popup):
    """Cobro: método de pago, monto recibido y cambio en vivo."""

    def __init__(self, pantalla, total, **kw):
        self.pantalla = pantalla
        self.total = total
        self.metodo = "Efectivo"
        contenido = columna(padding=dp(16), espacio=dp(10))
        super().__init__(title="Cobrar venta", content=contenido, size_hint=(0.94, None),
                         height=dp(520), title_color=TEXTO, separator_color=NAVY, **kw)

        contenido.add_widget(etiqueta("Total a pagar", tamano=sp(14), color=TEXTO_SUAVE, height=dp(22)))
        contenido.add_widget(etiqueta(ajustes.moneda(total), tamano=sp(30), color=NAVY, negrita=True,
                                      height=dp(44)))

        self.btn_efectivo = Boton("Efectivo", lambda: self.elegir("Efectivo"), "primario", size_hint_x=0.5)
        self.btn_tarjeta = Boton("Tarjeta", lambda: self.elegir("Tarjeta"), "secundario", size_hint_x=0.5)
        contenido.add_widget(fila(self.btn_efectivo, self.btn_tarjeta))

        self.monto = Campo(pista="Monto recibido", input_filter="float")
        self.monto.bind(text=lambda *_: self.actualizar_cambio())
        contenido.add_widget(self.monto)

        rapidos = fila(alto=dp(44))
        rapidos.add_widget(Boton("Exacto", lambda: self.poner(total), "secundario", tamano=sp(13),
                                 height=dp(44)))
        for billete in ajustes.billetes()[:3]:
            rapidos.add_widget(Boton(f"{billete:,}", lambda b=billete: self.poner(b), "secundario",
                                     tamano=sp(13), height=dp(44)))
        contenido.add_widget(rapidos)

        self.lbl_cambio = etiqueta("", tamano=sp(18), color=VERDE, negrita=True, height=dp(36))
        contenido.add_widget(self.lbl_cambio)
        contenido.add_widget(Widget())
        contenido.add_widget(fila(Boton("Cancelar", self.dismiss, "secundario", size_hint_x=0.4),
                                  Boton("Confirmar pago", self.confirmar, "exito", size_hint_x=0.6)))
        self.actualizar_cambio()

    def elegir(self, metodo):
        self.metodo = metodo
        tarjeta = metodo == "Tarjeta"
        self.btn_efectivo.cambiar_tipo("secundario" if tarjeta else "primario")
        self.btn_tarjeta.cambiar_tipo("primario" if tarjeta else "secundario")
        self.monto.disabled = tarjeta
        if tarjeta:
            self.monto.text = f"{self.total:.2f}"
        self.actualizar_cambio()

    def poner(self, valor):
        self.monto.text = f"{valor:.2f}"

    def leer(self):
        return ajustes.leer_monto(self.monto.text)

    def actualizar_cambio(self):
        if self.metodo == "Tarjeta":
            self.lbl_cambio.text = f"Se cobran {ajustes.moneda(self.total)} con tarjeta"
            self.lbl_cambio.color = NAVY
            return
        monto = self.leer()
        if monto is None:
            self.lbl_cambio.text = ""
        elif monto >= self.total - 0.004:
            self.lbl_cambio.text = f"Cambio: {ajustes.moneda(monto - self.total)}"
            self.lbl_cambio.color = VERDE
        else:
            self.lbl_cambio.text = f"Falta: {ajustes.moneda(self.total - monto)}"
            self.lbl_cambio.color = ROJO

    def confirmar(self):
        if self.metodo == "Tarjeta":
            recibido = self.total
        else:
            monto = self.leer()
            if monto is None:
                self.lbl_cambio.text = "Escribí el monto recibido."
                self.lbl_cambio.color = ROJO
                return
            if monto < self.total - 0.004:
                self.actualizar_cambio()
                return
            recibido = round(monto, 2)
        self.pantalla.confirmar_cobro(recibido, self.metodo, self)


class VentanaVentaHecha(Popup):
    """Confirmación después de cobrar."""

    def __init__(self, numero, total, cambio, metodo, ruta, **kw):
        contenido = columna(padding=dp(18), espacio=dp(8))
        super().__init__(title="Venta registrada", content=contenido, size_hint=(0.9, None),
                         height=dp(340), title_color=TEXTO, separator_color=VERDE, **kw)
        contenido.add_widget(etiqueta(f"Factura N° {numero:06d}", tamano=sp(20), color=TEXTO,
                                      negrita=True, alineacion="center", height=dp(36)))
        contenido.add_widget(etiqueta(f"Total {ajustes.moneda(total)}", tamano=sp(15), color=TEXTO_SUAVE,
                                      alineacion="center", height=dp(26)))
        if metodo == "Efectivo":
            contenido.add_widget(etiqueta(f"Cambio: {ajustes.moneda(cambio)}", tamano=sp(26), color=VERDE,
                                          negrita=True, alineacion="center", height=dp(46)))
        else:
            contenido.add_widget(etiqueta("Pagado con tarjeta", tamano=sp(17), color=NAVY,
                                          alineacion="center", height=dp(46)))
        contenido.add_widget(etiqueta("Factura guardada en el teléfono." if ruta else
                                      "No se pudo generar el PDF de la factura.",
                                      tamano=sp(12), color=TEXTO_SUAVE if ruta else AMBAR,
                                      alineacion="center", height=dp(30)))
        contenido.add_widget(Widget())
        contenido.add_widget(Boton("Nueva venta", self.dismiss, "primario"))
