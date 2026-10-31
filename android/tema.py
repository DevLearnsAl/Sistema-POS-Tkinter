"""Colores, medidas y widgets comunes de la versión Android.

Es el equivalente de `estilos.py` en la versión de escritorio: misma paleta, para
que las dos aplicaciones se vean de la misma familia, pero pensada para el dedo
en vez del mouse (botones altos, texto grande, una sola columna).
"""
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle


def rgb(hexa, alfa=1.0):
    """Convierte '#1D3F7A' al formato que usa Kivy (0 a 1)."""
    hexa = hexa.lstrip("#")
    return [int(hexa[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [alfa]


# Misma paleta que la versión de escritorio.
NAVY = rgb("#1D3F7A")
NAVY_OSCURO = rgb("#152E59")
FONDO = rgb("#F3F5F9")
BLANCO = rgb("#FFFFFF")
BORDE = rgb("#D6DDE8")
TEXTO = rgb("#1B2433")
TEXTO_SUAVE = rgb("#4A5568")
TEXTO_CLARO = rgb("#C9D6EA")
VERDE = rgb("#1E7B4A")
ROJO = rgb("#B42318")
AMBAR = rgb("#9A6200")
CLARO = rgb("#E6ECF5")

# Alturas pensadas para tocar con el dedo: 48 dp es el mínimo recomendado.
ALTO_BOTON = dp(52)
ALTO_CAMPO = dp(48)
ALTO_FILA = dp(64)
MARGEN = dp(12)


class Fondo(BoxLayout):
    """Caja con color de fondo y esquinas redondeadas opcionales."""

    def __init__(self, color=BLANCO, radio=dp(10), **kw):
        super().__init__(**kw)
        self._color = color
        self._radio = radio
        with self.canvas.before:
            self._instruccion = Color(*color)
            self._figura = RoundedRectangle(radius=[radio])
        self.bind(pos=self._redibujar, size=self._redibujar)

    def _redibujar(self, *_):
        self._figura.pos = self.pos
        self._figura.size = self.size

    def pintar(self, color):
        self._instruccion.rgba = color


class Boton(ButtonBehavior, Fondo):
    """Botón plano. Kivy no trae uno con color sólido y esquinas redondeadas."""

    TIPOS = {
        "primario": (NAVY, BLANCO),
        "exito": (VERDE, BLANCO),
        "peligro": (ROJO, BLANCO),
        "secundario": (CLARO, NAVY),
    }

    def __init__(self, texto, al_tocar=None, tipo="primario", tamano=None, **kw):
        fondo, letra = self.TIPOS[tipo]
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", ALTO_BOTON)
        super().__init__(color=fondo, **kw)
        self.tipo = tipo
        self.etiqueta = Label(text=texto, color=letra, bold=True, font_size=tamano or sp(16),
                              halign="center", valign="middle")
        self.etiqueta.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.add_widget(self.etiqueta)
        if al_tocar:
            self.bind(on_release=lambda *_: al_tocar())

    @property
    def texto(self):
        return self.etiqueta.text

    @texto.setter
    def texto(self, valor):
        self.etiqueta.text = valor

    def cambiar_tipo(self, tipo):
        fondo, letra = self.TIPOS[tipo]
        self.tipo = tipo
        self.pintar(fondo)
        self.etiqueta.color = letra

    def habilitar(self, activo):
        self.disabled = not activo
        self.etiqueta.color = self.TIPOS[self.tipo][1][:3] + [1.0 if activo else 0.4]


def etiqueta(texto="", tamano=sp(15), color=TEXTO, negrita=False, alineacion="left", **kw):
    kw.setdefault("size_hint_y", None)
    lbl = Label(text=texto, font_size=tamano, color=color, bold=negrita,
                halign=alineacion, valign="middle", **kw)
    lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
    if kw.get("height") is None and kw.get("size_hint_y", 1) is None:
        lbl.height = dp(24)
    return lbl


def titulo(texto, color=TEXTO):
    return etiqueta(texto, tamano=sp(22), color=color, negrita=True, height=dp(36))


class Campo(TextInput):
    """Campo de texto con el aspecto del resto de la aplicación."""

    def __init__(self, pista="", **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", ALTO_CAMPO)
        kw.setdefault("multiline", False)
        kw.setdefault("font_size", sp(17))
        kw.setdefault("padding", [dp(12), dp(12), dp(12), dp(12)])
        super().__init__(hint_text=pista, background_color=BLANCO, foreground_color=TEXTO,
                         cursor_color=NAVY, **kw)


def fila(*widgets, alto=None, espacio=None):
    caja = BoxLayout(orientation="horizontal", size_hint_y=None, height=alto or ALTO_BOTON,
                     spacing=espacio if espacio is not None else MARGEN)
    for w in widgets:
        caja.add_widget(w)
    return caja


def columna(espacio=None, **kw):
    kw.setdefault("orientation", "vertical")
    kw.setdefault("spacing", espacio if espacio is not None else MARGEN)
    return BoxLayout(**kw)


def separador(alto=dp(1), color=BORDE):
    return Fondo(color=color, radio=0, size_hint_y=None, height=alto)
