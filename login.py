import os
import sqlite3
import tkinter as tk

from PIL import Image, ImageOps, ImageTk

import ajustes
import config
import db
from seguridad import hash_password, verificar_password
from estilos import (BLANCO, NAVY, ROJO, VERDE, TEXTO, TEXTO_SUAVE, TEXTO_CLARO, FUENTE, F_NORMAL, F_PEQUE,
                     F_NEGRITA, boton, campo, etiqueta)


def dibujar_logo(canvas, cx, cy, r):
    """Logo dibujado con formas: se ve nítido en cualquier pantalla."""
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=BLANCO, outline="")
    canvas.create_oval(cx - r + 9, cy - r + 9, cx + r - 9, cy + r - 9, outline=NAVY, width=2)
    canvas.create_text(cx, cy - r * 0.17, text="MINI", fill=NAVY, font=(FUENTE, int(r * 0.34), "bold"))
    canvas.create_text(cx, cy + r * 0.25, text="MARKET", fill=NAVY, font=(FUENTE, int(r * 0.24), "bold"))


class PantallaAcceso(tk.Frame):
    """Base de Login y Registro: panel de marca a la izquierda y formulario a la derecha."""

    def __init__(self, padre, controlador):
        super().__init__(padre, bg=BLANCO)
        self.controlador = controlador
        self.place(x=0, y=0, width=1100, height=650)
        self.marca = tk.Canvas(self, bg=NAVY, highlightthickness=0)
        self.marca.place(x=0, y=0, width=440, height=650)
        self.dibujar_marca()
        self.widgets()

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

    def mensaje(self, y):
        self.lbl_mensaje = etiqueta(self, "", F_PEQUE, ROJO, wraplength=320, justify="left")
        self.lbl_mensaje.place(x=610, y=y)

    def mostrar_mensaje(self, texto, error=True):
        self.lbl_mensaje.config(text=texto, fg=ROJO if error else VERDE)

    def enviar(self):
        raise NotImplementedError


class Login(PantallaAcceso):
    def widgets(self):
        etiqueta(self, "Iniciar sesión", (FUENTE, 24, "bold"), TEXTO).place(x=610, y=150)
        etiqueta(self, "Ingrese su usuario y contraseña para continuar.", F_NORMAL, TEXTO_SUAVE).place(x=610, y=196)
        self.username = self.fila("Usuario", 250)
        self.password = self.fila("Contraseña", 332, oculto=True)
        self.mensaje(412)
        self.btn_ingresar = boton(self, "Ingresar", self.enviar, "primario", (FUENTE, 12, "bold"))
        self.btn_ingresar.place(x=610, y=450, width=320, height=44)
        etiqueta(self, "¿No tiene una cuenta?", F_NORMAL, TEXTO_SUAVE).place(x=610, y=515)
        link = tk.Label(self, text="Crear una cuenta", font=(FUENTE, 11, "bold", "underline"), fg=NAVY, bg=BLANCO,
                        cursor="hand2")
        link.place(x=772, y=515)
        link.bind("<Button-1>", lambda e: self.controlador.show_frame(Registro))
        self.link_registro = link

    def al_mostrar(self):
        self.dibujar_marca()
        self.password.delete(0, "end")
        self.username.focus_set()

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
            # Avisa si todavía tiene la contraseña con la que se creó la cuenta.
            self.controlador.iniciar_sesion(user, fila[1], clave_por_defecto=(pas == "admin"))
        else:
            self.password.delete(0, "end")
            self.mostrar_mensaje("Usuario o contraseña incorrectos.")
            self.password.focus_set()


class Registro(PantallaAcceso):
    def widgets(self):
        etiqueta(self, "Crear cuenta", (FUENTE, 24, "bold"), TEXTO).place(x=610, y=40)
        etiqueta(self, "Para registrarse necesita el código de autorización.", F_NORMAL, TEXTO_SUAVE).place(x=610, y=86)
        self.username = self.fila("Usuario", 130)
        self.password = self.fila("Contraseña (mínimo 6 caracteres)", 206, oculto=True)
        self.confirmar = self.fila("Confirmar contraseña", 282, oculto=True)
        self.key = self.fila("Código de autorización", 358, oculto=True)
        self.mensaje(436)
        boton(self, "Crear cuenta", self.enviar, "primario", (FUENTE, 12, "bold")).place(x=610, y=478, width=320, height=44)
        boton(self, "Volver a iniciar sesión", self.volver, "secundario").place(x=610, y=534, width=320, height=40)

    def al_mostrar(self):
        self.dibujar_marca()
        for e in (self.username, self.password, self.confirmar, self.key):
            e.delete(0, "end")
        self.mostrar_mensaje("")
        self.username.focus_set()

    def volver(self):
        self.controlador.show_frame(Login)

    def enviar(self):
        user = self.username.get().strip()
        pas = self.password.get()
        if len(user) < 3:
            self.mostrar_mensaje("El usuario debe tener al menos 3 caracteres.")
        elif len(pas) < 6:
            self.mostrar_mensaje("La contraseña debe tener al menos 6 caracteres.")
        elif pas != self.confirmar.get():
            self.mostrar_mensaje("Las contraseñas no coinciden.")
        elif self.key.get() != ajustes.obtener("codigo_registro"):
            self.mostrar_mensaje("El código de autorización no es correcto.")
        else:
            try:
                # Las cuentas creadas desde aquí entran como cajeros: el rol de
                # administrador solo lo da otro administrador, desde Usuarios.
                db.ejecutar("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, 'cajero')",
                            (user, hash_password(pas)))
            except sqlite3.IntegrityError:
                self.mostrar_mensaje(f"El usuario «{user}» ya existe. Elija otro nombre.")
                return
            except sqlite3.Error as e:
                self.mostrar_mensaje(f"No se pudo crear la cuenta: {e}")
                return
            login = self.controlador.frames[Login]
            self.controlador.show_frame(Login)
            login.username.delete(0, "end")
            login.username.insert(0, user)
            login.password.focus_set()
            login.mostrar_mensaje(f"Cuenta «{user}» creada. Ya puede iniciar sesión.", error=False)
