"""Pantallas de la aplicación Android.

Cada una hereda de `PantallaBase`, que arma el encabezado y la barra de abajo y
llama a `al_mostrar()` cada vez que la pantalla aparece. Es el mismo gancho que
usa la versión de escritorio, así las dos recargan sus datos igual.
"""
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen

from tema import FONDO, MARGEN, Fondo, columna


class PantallaBase(Screen):
    titulo_modulo = ""
    con_navegacion = True

    def __init__(self, app, **kw):
        super().__init__(name=self.nombre, **kw)
        self.app = app
        raiz = Fondo(color=FONDO, radio=0, orientation="vertical", spacing=0)

        if self.con_navegacion:
            from main import Encabezado, Navegacion
            self.encabezado = Encabezado(self.titulo_modulo, app)
            raiz.add_widget(self.encabezado)

        self.cuerpo = columna(padding=[MARGEN, MARGEN, MARGEN, MARGEN])
        raiz.add_widget(self.cuerpo)

        if self.con_navegacion:
            self.navegacion = Navegacion(app)
            raiz.add_widget(self.navegacion)

        self.add_widget(raiz)
        self.construir()

    def construir(self):
        """Las pantallas arman acá su contenido dentro de `self.cuerpo`."""

    def on_pre_enter(self, *_):
        if self.con_navegacion:
            self.encabezado.actualizar()
            self.navegacion.marcar(self.nombre)
        self.al_mostrar()

    def al_mostrar(self):
        """Se llama cada vez que la pantalla aparece: acá se recargan los datos."""
