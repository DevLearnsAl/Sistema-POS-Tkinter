"""Pantalla de caja: abrir el turno, ver el resumen y cerrarlo con arqueo.

Toda la lógica está en `turnos.py`, compartido con la computadora. Acá solo se
muestra y se toca.
"""
import sqlite3

from kivy.metrics import dp, sp
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

import ajustes
import turnos
from utilidades import fecha_corta
from tema import (BLANCO, NAVY, ROJO, TEXTO, TEXTO_SUAVE, VERDE, AMBAR, Boton, Campo, Fondo,
                  columna, etiqueta, fila, separador)

from . import PantallaBase
from .ventas import aviso


class PantallaCaja(PantallaBase):
    nombre = "caja"
    titulo_modulo = "Caja"

    def construir(self):
        self.caja_id = None

        tarjeta = Fondo(color=BLANCO, orientation="vertical", size_hint_y=None, height=dp(300),
                        padding=dp(14), spacing=dp(6))
        self.lbl_estado = etiqueta("", tamano=sp(20), negrita=True, height=dp(32))
        self.lbl_detalle = etiqueta("", tamano=sp(12), color=TEXTO_SUAVE, height=dp(34))
        tarjeta.add_widget(self.lbl_estado)
        tarjeta.add_widget(self.lbl_detalle)
        tarjeta.add_widget(separador())

        self.valores = {}
        for texto, clave in [("Monto inicial", "inicial"), ("Ventas en efectivo", "efectivo"),
                             ("Entradas", "entradas"), ("Salidas", "salidas")]:
            renglon = fila(etiqueta(texto, tamano=sp(13), color=TEXTO_SUAVE, height=dp(26)),
                           etiqueta("", tamano=sp(13), color=TEXTO, negrita=True, alineacion="right",
                                    height=dp(26)), alto=dp(26))
            self.valores[clave] = renglon.children[0]
            tarjeta.add_widget(renglon)
        tarjeta.add_widget(separador())
        esperado = fila(etiqueta("Efectivo esperado", tamano=sp(15), color=TEXTO_SUAVE, height=dp(40)),
                        etiqueta("", tamano=sp(24), color=NAVY, negrita=True, alineacion="right",
                                 height=dp(40)), alto=dp(40))
        self.lbl_esperado = esperado.children[0]
        tarjeta.add_widget(esperado)
        self.cuerpo.add_widget(tarjeta)

        self.btn_abrir = Boton("Abrir caja", self.abrir, "exito", tamano=sp(17))
        self.cuerpo.add_widget(self.btn_abrir)
        self.btn_movimientos = fila(
            Boton("Entrada", lambda: self.movimiento("ENTRADA"), "secundario", tamano=sp(14)),
            Boton("Salida", lambda: self.movimiento("SALIDA"), "secundario", tamano=sp(14)))
        self.cuerpo.add_widget(self.btn_movimientos)
        self.btn_cerrar = Boton("Cerrar caja y arquear", self.cerrar, "peligro", tamano=sp(16))
        self.cuerpo.add_widget(self.btn_cerrar)

        self.cuerpo.add_widget(etiqueta("Arqueos anteriores", tamano=sp(15), negrita=True, height=dp(30)))
        desplazable = ScrollView()
        self.lista = columna(espacio=dp(4), size_hint_y=None)
        self.lista.bind(minimum_height=self.lista.setter("height"))
        desplazable.add_widget(self.lista)
        self.cuerpo.add_widget(desplazable)

    # ------------------------------------------------------------------ datos
    def al_mostrar(self):
        self.refrescar()

    def refrescar(self):
        turno = turnos.caja_abierta()
        self.caja_id = turno[0] if turno else None
        propio = bool(turno) and (turno[1] == self.app.usuario or self.app.es_admin)

        if turno:
            self.lbl_estado.text = "Caja abierta"
            self.lbl_estado.color = VERDE
            self.lbl_detalle.text = f"Abierta por {turno[1]} el {fecha_corta(turno[2])} a las {turno[3][:5]}."
            datos = turnos.resumen(self.caja_id)
        else:
            self.lbl_estado.text = "Caja cerrada"
            self.lbl_estado.color = ROJO
            self.lbl_detalle.text = "Abrí el turno con el dinero con el que arranca la caja."
            datos = {"inicial": 0, "efectivo": 0, "entradas": 0, "salidas": 0, "esperado": 0}

        for clave, lbl in self.valores.items():
            lbl.text = ajustes.moneda(datos[clave])
        self.lbl_esperado.text = ajustes.moneda(datos["esperado"])

        self.btn_abrir.habilitar(not turno)
        self.btn_cerrar.habilitar(propio)
        for b in self.btn_movimientos.children:
            b.habilitar(propio)

        self.lista.clear_widgets()
        solo_mios = None if self.app.puede("ver_todas_las_cajas") else self.app.usuario
        for f in turnos.arqueos(solo_mios, 30):
            diferencia = f[4] or 0
            color = VERDE if abs(diferencia) < 0.005 else (ROJO if diferencia < 0 else AMBAR)
            renglon = Fondo(color=BLANCO, orientation="horizontal", size_hint_y=None, height=dp(44),
                            padding=[dp(10), 0, dp(10), 0])
            renglon.add_widget(etiqueta(f"{fecha_corta(f[0])}  ·  {f[1]}", tamano=sp(12),
                                        color=TEXTO_SUAVE, height=dp(44)))
            renglon.add_widget(etiqueta(ajustes.moneda(diferencia), tamano=sp(13), color=color,
                                        negrita=True, alineacion="right", height=dp(44)))
            self.lista.add_widget(renglon)

    # ------------------------------------------------------------------ acciones
    def abrir(self):
        PedirMonto("Abrir caja", "Efectivo con el que arranca el turno", "Abrir",
                   self._abrir_con).open()

    def _abrir_con(self, monto, ventana):
        try:
            turnos.abrir_turno(self.app.usuario, monto)
        except (ValueError, sqlite3.Error) as e:
            ventana.error(str(e))
            return
        ventana.dismiss()
        self.refrescar()

    def movimiento(self, tipo):
        texto = "Entrada de efectivo" if tipo == "ENTRADA" else "Salida de efectivo"
        PedirMonto(texto, "Monto", "Registrar",
                   lambda m, v: self._movimiento_con(tipo, m, v), con_motivo=True).open()

    def _movimiento_con(self, tipo, monto, ventana):
        motivo = ventana.motivo.text.strip() or ("Entrada de efectivo" if tipo == "ENTRADA" else "Salida")
        try:
            turnos.registrar_movimiento(self.caja_id, tipo, monto, motivo, self.app.usuario)
        except (ValueError, sqlite3.Error) as e:
            ventana.error(str(e))
            return
        ventana.dismiss()
        self.refrescar()

    def cerrar(self):
        datos = turnos.resumen(self.caja_id)
        VentanaCierre(self, datos).open()


class PedirMonto(Popup):
    """Ventanita para escribir un monto, con un motivo opcional."""

    def __init__(self, titulo_texto, pista, boton, al_confirmar, con_motivo=False, **kw):
        contenido = columna(padding=dp(16), espacio=dp(10))
        super().__init__(title=titulo_texto, content=contenido, size_hint=(0.9, None),
                         height=dp(380) if con_motivo else dp(300), title_color=TEXTO,
                         separator_color=NAVY, **kw)
        contenido.add_widget(etiqueta(pista, tamano=sp(13), color=TEXTO_SUAVE, height=dp(24)))
        self.monto = Campo(pista="0.00", input_filter="float")
        contenido.add_widget(self.monto)
        if con_motivo:
            contenido.add_widget(etiqueta("Motivo", tamano=sp(13), color=TEXTO_SUAVE, height=dp(24)))
            self.motivo = Campo(pista="Por ejemplo: pago a proveedor")
            contenido.add_widget(self.motivo)
        self.lbl_error = etiqueta("", tamano=sp(12), color=ROJO, height=dp(30))
        contenido.add_widget(self.lbl_error)
        contenido.add_widget(Widget())
        contenido.add_widget(fila(Boton("Cancelar", self.dismiss, "secundario", size_hint_x=0.4),
                                  Boton(boton, lambda: self._confirmar(al_confirmar), "primario",
                                        size_hint_x=0.6)))

    def error(self, texto):
        self.lbl_error.text = texto

    def _confirmar(self, al_confirmar):
        monto = ajustes.leer_monto(self.monto.text)
        if monto is None or monto < 0:
            self.error("Escribí un monto válido.")
            return
        al_confirmar(round(monto, 2), self)


class VentanaCierre(Popup):
    """Cierre del turno: se cuenta el efectivo y se ve la diferencia."""

    def __init__(self, pantalla, datos, **kw):
        self.pantalla = pantalla
        self.datos = datos
        contenido = columna(padding=dp(16), espacio=dp(8))
        super().__init__(title="Cerrar caja", content=contenido, size_hint=(0.94, None),
                         height=dp(440), title_color=TEXTO, separator_color=ROJO, **kw)
        contenido.add_widget(etiqueta("Contá el efectivo de la caja y escribí el total.",
                                      tamano=sp(13), color=TEXTO_SUAVE, height=dp(34)))
        renglon = fila(etiqueta("Efectivo esperado", tamano=sp(14), color=TEXTO_SUAVE, height=dp(34)),
                       etiqueta(ajustes.moneda(datos["esperado"]), tamano=sp(18), color=NAVY,
                                negrita=True, alineacion="right", height=dp(34)), alto=dp(34))
        contenido.add_widget(renglon)
        self.contado = Campo(pista="Efectivo contado", input_filter="float")
        self.contado.bind(text=lambda *_: self.actualizar())
        contenido.add_widget(self.contado)
        self.lbl_diferencia = etiqueta("", tamano=sp(17), negrita=True, height=dp(34))
        contenido.add_widget(self.lbl_diferencia)
        self.observacion = Campo(pista="Observación (opcional)")
        contenido.add_widget(self.observacion)
        self.lbl_error = etiqueta("", tamano=sp(12), color=ROJO, height=dp(26))
        contenido.add_widget(self.lbl_error)
        contenido.add_widget(Widget())
        contenido.add_widget(fila(Boton("Cancelar", self.dismiss, "secundario", size_hint_x=0.4),
                                  Boton("Cerrar caja", self.confirmar, "peligro", size_hint_x=0.6)))

    def actualizar(self):
        contado = ajustes.leer_monto(self.contado.text)
        if contado is None:
            self.lbl_diferencia.text = ""
            return
        diferencia = round(contado - self.datos["esperado"], 2)
        if abs(diferencia) < 0.005:
            self.lbl_diferencia.text = "Cuadra exacto."
            self.lbl_diferencia.color = VERDE
        elif diferencia < 0:
            self.lbl_diferencia.text = f"Faltan {ajustes.moneda(-diferencia)}"
            self.lbl_diferencia.color = ROJO
        else:
            self.lbl_diferencia.text = f"Sobran {ajustes.moneda(diferencia)}"
            self.lbl_diferencia.color = AMBAR

    def confirmar(self):
        contado = ajustes.leer_monto(self.contado.text)
        if contado is None or contado < 0:
            self.lbl_error.text = "Escribí el efectivo contado."
            return
        try:
            arqueo = turnos.cerrar_turno(self.pantalla.caja_id, self.pantalla.app.usuario, contado,
                                         self.observacion.text.strip() or None)
        except turnos.TurnoCerrado:
            self.lbl_error.text = "Ese turno ya está cerrado."
            return
        except sqlite3.Error as e:
            self.lbl_error.text = f"No se pudo cerrar: {e}"
            return
        self.dismiss()
        self.pantalla.refrescar()
        aviso("Caja cerrada",
              f"Esperado: {ajustes.moneda(arqueo['esperado'])}\n"
              f"Contado: {ajustes.moneda(arqueo['contado'])}\n"
              f"Diferencia: {ajustes.moneda(arqueo['diferencia'])}")
