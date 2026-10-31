"""Minimarket para Android: punto de entrada.

Es la misma lógica de la versión de escritorio con otra capa de presentación.
Los módulos `db`, `crear_bd`, `ajustes`, `seguridad`, `utilidades`, `turnos`,
`cobro` y `factura` se comparten sin cambios: acá solo está la interfaz, hecha
con Kivy en lugar de Tkinter.

Para probarlo en la computadora:   py -3.12 main.py
Para armar el APK:                 ver LEEME.md
"""
import os
import sys

from kivy.config import Config

# Al probarlo en la computadora, una ventana con proporción de teléfono.
if sys.platform in ("win32", "darwin"):
    Config.set("graphics", "width", "420")
    Config.set("graphics", "height", "820")

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, NoTransition

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import almacenamiento
import tema
from tema import (NAVY, BLANCO, FONDO, TEXTO_CLARO, Boton, Fondo, columna, etiqueta)


class Navegacion(Fondo):
    """Barra de abajo para cambiar de módulo, con el pulgar."""

    MODULOS = [("Ventas", "ventas"), ("Caja", "caja"), ("Inventario", "inventario")]

    def __init__(self, app, **kw):
        super().__init__(color=NAVY, radio=0, orientation="horizontal", size_hint_y=None,
                         height=dp(62), **kw)
        self.app = app
        self.botones = {}
        for texto, destino in self.MODULOS:
            b = Boton(texto, lambda d=destino: app.ir_a(d), "primario", tamano=sp(14),
                      size_hint_y=1, height=dp(62))
            b.pintar(NAVY)
            self.botones[destino] = b
            self.add_widget(b)
        self.add_widget(Boton("Salir", app.cerrar_sesion, "primario", tamano=sp(14),
                              size_hint_y=1, height=dp(62)))

    def marcar(self, destino):
        for nombre, boton in self.botones.items():
            boton.pintar(FONDO if nombre == destino else NAVY)
            boton.etiqueta.color = NAVY if nombre == destino else BLANCO


class Encabezado(Fondo):
    """Barra de arriba: nombre del módulo y quién tiene la sesión abierta."""

    def __init__(self, texto, app, **kw):
        super().__init__(color=NAVY, radio=0, orientation="horizontal", size_hint_y=None,
                         height=dp(58), padding=[dp(14), 0, dp(14), 0], **kw)
        self.app = app
        self.lbl_titulo = etiqueta(texto, tamano=sp(19), color=BLANCO, negrita=True, height=dp(58))
        self.lbl_usuario = etiqueta("", tamano=sp(13), color=TEXTO_CLARO, alineacion="right",
                                    height=dp(58), size_hint_x=0.5)
        self.add_widget(self.lbl_titulo)
        self.add_widget(self.lbl_usuario)

    def actualizar(self):
        usuario = self.app.usuario or ""
        rol = "admin" if self.app.es_admin else "cajero"
        self.lbl_usuario.text = f"{usuario} · {rol}" if usuario else ""


class MinimarketApp(App):
    """La aplicación. Guarda quién inició sesión, igual que `Manager` en escritorio."""

    title = "Minimarket"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.usuario = None
        self.rol = None
        self.pantallas = {}

    # ------------------------------------------------------------------ arranque
    def build(self):
        Window.clearcolor = FONDO
        # Que el teclado no tape el campo donde se está escribiendo.
        Window.softinput_mode = "below_target"

        almacenamiento.preparar(self.user_data_dir)
        import crear_bd, ajustes, registro
        registro.iniciar()
        crear_bd.preparar_base()
        ajustes.cargar()

        from pantallas.acceso import PantallaLogin
        from pantallas.caja import PantallaCaja
        from pantallas.inventario import PantallaInventario
        from pantallas.ventas import PantallaVentas

        self.gestor = ScreenManager(transition=NoTransition())
        for clase in (PantallaLogin, PantallaVentas, PantallaCaja, PantallaInventario):
            pantalla = clase(self)
            self.pantallas[pantalla.name] = pantalla
            self.gestor.add_widget(pantalla)
        self.gestor.current = "login"
        return self.gestor

    # ------------------------------------------------------------------ sesión
    @property
    def es_admin(self):
        return self.rol == "admin"

    def puede(self, permiso):
        import config
        return permiso in config.PERMISOS.get(self.rol, set())

    def iniciar_sesion(self, usuario, rol):
        self.usuario = usuario
        self.rol = rol
        self.ir_a("ventas")

    def cerrar_sesion(self):
        self.usuario = None
        self.rol = None
        self.gestor.current = "login"

    def ir_a(self, destino):
        self.gestor.current = destino
        pantalla = self.pantallas[destino]
        if hasattr(pantalla, "navegacion"):
            pantalla.navegacion.marcar(destino)


def main():
    MinimarketApp().run()


if __name__ == "__main__":
    main()
