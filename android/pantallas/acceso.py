"""Pantalla de inicio de sesión.

Igual que en la computadora: no hay registro público. Las cuentas las crea un
administrador, y en el teléfono se usan las mismas que en el escritorio.
"""
import sqlite3

from kivy.metrics import dp, sp
from kivy.uix.widget import Widget

import db
from seguridad import verificar_password
from tema import (BLANCO, NAVY, ROJO, TEXTO, TEXTO_SUAVE, Boton, Campo, Fondo, columna, etiqueta, titulo)

from . import PantallaBase


class PantallaLogin(PantallaBase):
    nombre = "login"
    con_navegacion = False

    def construir(self):
        import ajustes

        self.cuerpo.padding = [dp(26), dp(40), dp(26), dp(30)]
        self.cuerpo.add_widget(Widget(size_hint_y=0.2))

        marca = Fondo(color=NAVY, orientation="vertical", size_hint_y=None, height=dp(150),
                      padding=[dp(20), dp(24), dp(20), dp(20)], spacing=dp(6))
        self.lbl_negocio = etiqueta(ajustes.obtener("negocio_nombre"), tamano=sp(26), color=BLANCO,
                                    negrita=True, alineacion="center", height=dp(40))
        marca.add_widget(self.lbl_negocio)
        marca.add_widget(etiqueta("Sistema de facturación", tamano=sp(14), color=(1, 1, 1, 0.75),
                                  alineacion="center", height=dp(24)))
        marca.add_widget(Widget())
        self.cuerpo.add_widget(marca)

        self.cuerpo.add_widget(etiqueta("Iniciar sesión", tamano=sp(20), color=TEXTO, negrita=True,
                                        height=dp(40)))
        self.usuario = Campo(pista="Usuario")
        self.clave = Campo(pista="Contraseña", password=True)
        self.clave.bind(on_text_validate=lambda *_: self.entrar())
        self.cuerpo.add_widget(self.usuario)
        self.cuerpo.add_widget(self.clave)

        self.mensaje = etiqueta("", tamano=sp(13), color=ROJO, height=dp(44))
        self.cuerpo.add_widget(self.mensaje)
        self.cuerpo.add_widget(Boton("Ingresar", self.entrar, "primario", tamano=sp(17)))
        self.cuerpo.add_widget(etiqueta("Las cuentas las crea el administrador del sistema.",
                                        tamano=sp(12), color=TEXTO_SUAVE, alineacion="center",
                                        height=dp(30)))
        self.cuerpo.add_widget(Widget())

    def al_mostrar(self):
        import ajustes
        self.lbl_negocio.text = ajustes.obtener("negocio_nombre")
        self.clave.text = ""
        self.mensaje.text = ""

    def entrar(self):
        usuario = self.usuario.text.strip()
        clave = self.clave.text
        if not usuario or not clave:
            self.mensaje.text = "Escriba su usuario y su contraseña."
            return
        try:
            fila = db.uno("SELECT password, rol, activo FROM usuarios WHERE username = ?", (usuario,))
        except sqlite3.Error as e:
            self.mensaje.text = f"No se pudo leer la base de datos: {e}"
            return
        if not fila or not verificar_password(clave, fila[0]):
            self.clave.text = ""
            self.mensaje.text = "Usuario o contraseña incorrectos."
            return
        if not fila[2]:
            self.clave.text = ""
            self.mensaje.text = f"La cuenta «{usuario}» está desactivada."
            return
        self.usuario.text = ""
        self.clave.text = ""
        self.mensaje.text = ""
        self.app.iniciar_sesion(usuario, fila[1])
