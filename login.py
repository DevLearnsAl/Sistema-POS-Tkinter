"""Pantalla de inicio de sesión.

No hay registro público: las cuentas las crea un administrador desde Usuarios
(`usuarios.py`). En un punto de venta, quién puede cobrar no es algo que cada
quien decida por su cuenta.
"""
import os
import sqlite3
import tkinter as tk

from PIL import Image, ImageOps, ImageTk

import ajustes
import config
import db
from seguridad import verificar_password
from estilos import (BLANCO, NAVY, ROJO, VERDE, TEXTO, TEXTO_SUAVE, TEXTO_CLARO, FUENTE, F_NORMAL, F_PEQUE,
                     F_NEGRITA, boton, campo, etiqueta)


def dibujar_logo(canvas, cx, cy, r):
    """Logo dibujado con formas: se ve nítido en cualquier pantalla."""
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=BLANCO, outline="")
    canvas.create_oval(cx - r + 9, cy - r + 9, cx + r - 9, cy + r - 9, outline=NAVY, width=2)
    canvas.create_text(cx, cy - r * 0.17, text="MINI", fill=NAVY, font=(FUENTE, int(r * 0.34), "bold"))
    canvas.create_text(cx, cy + r * 0.25, text="MARKET", fill=NAVY, font=(FUENTE, int(r * 0.24), "bold"))


class Login(tk.Frame):
    """Panel de marca a la izquierda y formulario de acceso a la derecha."""

    def __init__(self, padre, controlador):
        super().__init__(padre, bg=BLANCO)
        self.controlador = controlador
        self.place(x=0, y=0, width=1100, height=650)
        self.marca = tk.Canvas(self, bg=NAVY, highlightthickness=0)
        self.marca.place(x=0, y=0, width=440, height=650)
        self.dibujar_marca()
        self.widgets()

    # ------------------------------------------------------------------ interfaz
    def dibujar_marca(self):
        """Panel de la izquierda. Se vuelve a dibujar al mostrarse, así el nombre
        y el logo cambian apenas se guarda la configuración."""
        marca = self.marca
        marca.delete("all")
        # Franjas diagonales suaves de fondo
        for x in range(-650, 440, 70):
            marca.create_line(x, 650, x + 650, 0, fill="#224682", width=18)

        ruta = ajustes.obtener("negocio_logo")
        self._logo = None
        if ruta and os.path.exists(ruta):
            try:
                imagen = ImageOps.contain(Image.open(ruta).convert("RGBA"), (200, 170))
                fondo = Image.new("RGBA", imagen.size, NAVY)
                self._logo = ImageTk.PhotoImage(Image.alpha_composite(fondo, imagen))
                marca.create_image(220, 200, image=self._logo)
            except OSError:
                self._logo = None
        if self._logo is None:
            dibujar_logo(marca, 220, 200, 78)

        nombre = ajustes.obtener("negocio_nombre")
        marca.create_text(220, 320, text=nombre, fill=BLANCO, width=400,
                          font=(FUENTE, 28 if len(nombre) <= 16 else 20, "bold"))
        marca.create_text(220, 362, text="Sistema de facturación e inventario", fill=TEXTO_CLARO, font=(FUENTE, 12))
        y = 430
        for linea in ("Ventas con factura en PDF", "Control de inventario y compras", "Reportes de ventas y ganancias"):
            marca.create_oval(112, y - 4, 120, y + 4, fill=TEXTO_CLARO, outline="")
            marca.create_text(132, y, text=linea, fill=BLANCO, font=(FUENTE, 11), anchor="w")
            y += 32
        marca.create_text(220, 615, text=f"Versión {config.VERSION}", fill=TEXTO_CLARO, font=(FUENTE, 9))

    def fila(self, texto, y, oculto=False):
        etiqueta(self, texto, F_NEGRITA, TEXTO).place(x=610, y=y)
        entrada = campo(self, show="•" if oculto else "")
        entrada.place(x=610, y=y + 26, width=320, height=40)
        entrada.bind("<Return>", lambda e: self.enviar())
        return entrada

    def widgets(self):
        etiqueta(self, "Iniciar sesión", (FUENTE, 24, "bold"), TEXTO).place(x=610, y=170)
        etiqueta(self, "Ingrese su usuario y contraseña para continuar.", F_NORMAL, TEXTO_SUAVE).place(x=610, y=216)
        self.username = self.fila("Usuario", 270)
        self.password = self.fila("Contraseña", 352, oculto=True)
        self.lbl_mensaje = etiqueta(self, "", F_PEQUE, ROJO, wraplength=320, justify="left")
        self.lbl_mensaje.place(x=610, y=432)
        self.btn_ingresar = boton(self, "Ingresar", self.enviar, "primario", (FUENTE, 12, "bold"))
        self.btn_ingresar.place(x=610, y=470, width=320, height=44)
        etiqueta(self, "¿No tiene cuenta? Las crea el administrador del sistema.", F_PEQUE, TEXTO_SUAVE,
                 wraplength=320, justify="left").place(x=610, y=530)

    def mostrar_mensaje(self, texto, error=True):
        self.lbl_mensaje.config(text=texto, fg=ROJO if error else VERDE)

    def al_mostrar(self):
        self.dibujar_marca()
        self.password.delete(0, "end")
        self.username.focus_set()

    # ------------------------------------------------------------------ acceso
    def enviar(self):
        user = self.username.get().strip()
        pas = self.password.get()
        if not user or not pas:
            self.mostrar_mensaje("Escriba su usuario y su contraseña.")
            return
        try:
            fila = db.uno("SELECT password, rol, activo FROM usuarios WHERE username = ?", (user,))
        except sqlite3.Error as e:
            self.mostrar_mensaje(f"No se pudo conectar a la base de datos: {e}")
            return
        if fila and verificar_password(pas, fila[0]):
            if not fila[2]:
                self.mostrar_mensaje(f"La cuenta «{user}» está desactivada. Pídale a un administrador que la active.")
                self.password.delete(0, "end")
                return
            self.mostrar_mensaje("")
            self.username.delete(0, "end")
            self.password.delete(0, "end")
            # Avisa si entró con una contraseña conocida, como la del primer arranque.
            self.controlador.iniciar_sesion(user, fila[1], clave_insegura=(pas in CLAVES_INSEGURAS))
        else:
            self.password.delete(0, "end")
            self.mostrar_mensaje("Usuario o contraseña incorrectos.")
            self.password.focus_set()


# Contraseñas que no deberían quedar en uso. La primera es la del usuario que
# crea el programa en el primer arranque.
CLAVES_INSEGURAS = {"admin", "123456", "password", "1234"}
