"""Mi cuenta y administración de usuarios.

Las dos pantallas son ventanas emergentes que se abren desde la barra superior.
Cambiar la contraseña lo puede hacer cualquiera; crear usuarios, cambiar roles y
desactivar cuentas, solo un administrador.
"""
import sqlite3
import tkinter as tk
from tkinter import messagebox

import db
from estilos import (BORDE, NAVY, TEXTO, TEXTO_SUAVE, VERDE, ROJO, FUENTE, F_PEQUE, F_NORMAL, F_NEGRITA,
                     F_SUBTITULO, F_TITULO, boton, panel, etiqueta, campo, lista, tabla, llenar_tabla,
                     ventana_modal)
from seguridad import hash_password, verificar_password

LARGO_MINIMO = 6


def _validar_nueva(clave, confirmacion):
    """Devuelve un mensaje de error, o None si la contraseña sirve."""
    if len(clave) < LARGO_MINIMO:
        return f"La contraseña debe tener al menos {LARGO_MINIMO} caracteres."
    if clave != confirmacion:
        return "Las contraseñas no coinciden."
    return None


class VentanaMiCuenta:
    """Cambiar la contraseña propia."""

    def __init__(self, padre, controlador):
        self.controlador = controlador
        top = self.top = ventana_modal(padre, "Mi cuenta", 420, 420)
        etiqueta(top, "Mi cuenta", F_TITULO, TEXTO).place(x=28, y=22)
        etiqueta(top, f"{controlador.usuario_actual}  ·  {controlador.rol_actual}", F_PEQUE,
                 TEXTO_SUAVE).place(x=28, y=62)

        self.campos = {}
        for i, (clave, texto) in enumerate([("actual", "Contraseña actual"),
                                            ("nueva", f"Contraseña nueva (mínimo {LARGO_MINIMO})"),
                                            ("confirmar", "Confirmar contraseña nueva")]):
            y = 102 + i * 76
            etiqueta(top, texto, F_NEGRITA, TEXTO).place(x=28, y=y)
            e = campo(top, show="•")
            e.place(x=28, y=y + 26, width=364, height=38)
            e.bind("<Return>", lambda ev: self.confirmar())
            self.campos[clave] = e

        self.lbl_mensaje = etiqueta(top, "", F_PEQUE, ROJO, wraplength=364, justify="left")
        self.lbl_mensaje.place(x=28, y=330)
        boton(top, "Cancelar", top.destroy, "secundario").place(x=28, y=358, width=150, height=44)
        boton(top, "Cambiar contraseña", self.confirmar, "primario", (FUENTE, 12, "bold")).place(
            x=190, y=358, width=202, height=44)
        top.bind("<Escape>", lambda e: top.destroy())
        self.campos["actual"].focus_set()

    def confirmar(self):
        usuario = self.controlador.usuario_actual
        actual = self.campos["actual"].get()
        nueva = self.campos["nueva"].get()
        fila = db.uno("SELECT password FROM usuarios WHERE username = ?", (usuario,))
        if not fila or not verificar_password(actual, fila[0]):
            self.lbl_mensaje.config(text="La contraseña actual no es correcta.")
            return
        error = _validar_nueva(nueva, self.campos["confirmar"].get())
        if error:
            self.lbl_mensaje.config(text=error)
            return
        if nueva == actual:
            self.lbl_mensaje.config(text="La contraseña nueva debe ser distinta de la actual.")
            return
        try:
            db.ejecutar("UPDATE usuarios SET password = ? WHERE username = ?", (hash_password(nueva), usuario))
        except sqlite3.Error as e:
            self.lbl_mensaje.config(text=f"No se pudo guardar: {e}")
            return
        self.controlador.clave_por_defecto = False
        self.top.destroy()
        messagebox.showinfo("Mi cuenta", "Contraseña cambiada.", parent=self.controlador)


class VentanaUsuarios:
    """Lista de usuarios: crear, cambiar rol, activar o desactivar y restablecer la contraseña."""

    def __init__(self, padre, controlador):
        self.controlador = controlador
        top = self.top = ventana_modal(padre, "Usuarios", 720, 520)
        etiqueta(top, "Usuarios", F_TITULO, TEXTO).place(x=28, y=22)
        etiqueta(top, "El cajero vende y maneja su caja. El administrador además anula facturas, compra, "
                      "cambia precios y ve los reportes.", F_PEQUE, TEXTO_SUAVE, wraplength=644,
                 justify="left").place(x=28, y=62)

        columnas = [("usuario", "Usuario", 190, "w"), ("rol", "Rol", 120, "center"),
                    ("estado", "Estado", 120, "center"), ("creado", "Creado", 170, "center")]
        marco, self.tree = tabla(top, columnas)
        marco.place(x=28, y=104, width=664, height=270)

        boton(top, "Nuevo usuario", self.nuevo).place(x=28, y=392, width=150, height=40)
        boton(top, "Cambiar rol", self.cambiar_rol, "secundario").place(x=188, y=392, width=140, height=40)
        self.btn_estado = boton(top, "Activar / Desactivar", self.cambiar_estado, "secundario")
        self.btn_estado.place(x=338, y=392, width=180, height=40)
        boton(top, "Restablecer contraseña", self.restablecer, "secundario").place(x=528, y=392, width=164, height=40)

        self.lbl_mensaje = etiqueta(top, "", F_PEQUE, TEXTO_SUAVE, wraplength=644, justify="left")
        self.lbl_mensaje.place(x=28, y=444)
        boton(top, "Cerrar", top.destroy, "secundario").place(x=572, y=468, width=120, height=38)
        top.bind("<Escape>", lambda e: top.destroy())
        self.cargar()

    # ------------------------------------------------------------------ datos
    def cargar(self):
        filas = db.consultar("SELECT username, rol, activo, creado FROM usuarios ORDER BY rol, username")
        llenar_tabla(self.tree,
                     [(f[0], "Administrador" if f[1] == "admin" else "Cajero",
                       "Activo" if f[2] else "Desactivado", f[3][:16]) for f in filas],
                     lambda f: [] if f[2] == "Activo" else ["anulada"])

    def seleccionado(self):
        seleccion = self.tree.selection()
        if not seleccion:
            self.aviso("Seleccione un usuario de la lista.", error=True)
            return None
        nombre = str(self.tree.item(seleccion[0], "values")[0])
        return db.uno("SELECT username, rol, activo FROM usuarios WHERE username = ?", (nombre,))

    def aviso(self, texto, error=False):
        self.lbl_mensaje.config(text=texto, fg=ROJO if error else VERDE)

    def _otros_admins(self, excepto):
        return db.uno("SELECT COUNT(*) FROM usuarios WHERE rol = 'admin' AND activo = 1 AND username <> ?",
                      (excepto,))[0]

    # ------------------------------------------------------------------ acciones
    def nuevo(self):
        FormularioUsuario(self)

    def cambiar_rol(self):
        fila = self.seleccionado()
        if not fila:
            return
        usuario, rol, _ = fila
        nuevo = "cajero" if rol == "admin" else "admin"
        if rol == "admin" and not self._otros_admins(usuario):
            self.aviso("No puede quitarle el rol: es el único administrador activo.", error=True)
            return
        if not messagebox.askyesno("Cambiar rol", f"¿«{usuario}» pasa a ser {nuevo}?", parent=self.top):
            return
        db.ejecutar("UPDATE usuarios SET rol = ? WHERE username = ?", (nuevo, usuario))
        if usuario == self.controlador.usuario_actual:
            self.controlador.rol_actual = nuevo
        self.cargar()
        self.aviso(f"«{usuario}» ahora es {nuevo}. El cambio se aplica la próxima vez que inicie sesión.")

    def cambiar_estado(self):
        fila = self.seleccionado()
        if not fila:
            return
        usuario, rol, activo = fila
        if usuario == self.controlador.usuario_actual:
            self.aviso("No puede desactivar su propia cuenta.", error=True)
            return
        if activo and rol == "admin" and not self._otros_admins(usuario):
            self.aviso("No puede desactivarlo: es el único administrador activo.", error=True)
            return
        db.ejecutar("UPDATE usuarios SET activo = ? WHERE username = ?", (0 if activo else 1, usuario))
        self.cargar()
        self.aviso(f"«{usuario}» quedó {'desactivado' if activo else 'activo'}.")

    def restablecer(self):
        fila = self.seleccionado()
        if not fila:
            return
        FormularioUsuario(self, usuario=fila[0])


class FormularioUsuario:
    """Crear un usuario nuevo, o ponerle otra contraseña a uno existente."""

    def __init__(self, ventana, usuario=None):
        self.ventana = ventana
        self.usuario = usuario
        titulo = f"Contraseña de {usuario}" if usuario else "Nuevo usuario"
        top = self.top = ventana_modal(ventana.top, titulo, 420, 400 if usuario else 440)
        etiqueta(top, titulo, F_SUBTITULO, TEXTO, wraplength=364, justify="left").place(x=28, y=22)

        y = 70
        if not usuario:
            etiqueta(top, "Usuario", F_NEGRITA, TEXTO).place(x=28, y=y)
            self.entry_usuario = campo(top)
            self.entry_usuario.place(x=28, y=y + 24, width=364, height=38)
            y += 76
            etiqueta(top, "Rol", F_NEGRITA, TEXTO).place(x=28, y=y)
            self.combo_rol = lista(top, values=["Cajero", "Administrador"], state="readonly")
            self.combo_rol.place(x=28, y=y + 24, width=364, height=38)
            self.combo_rol.set("Cajero")
            y += 76

        etiqueta(top, f"Contraseña (mínimo {LARGO_MINIMO})", F_NEGRITA, TEXTO).place(x=28, y=y)
        self.entry_clave = campo(top, show="•")
        self.entry_clave.place(x=28, y=y + 24, width=364, height=38)
        y += 76
        etiqueta(top, "Confirmar contraseña", F_NEGRITA, TEXTO).place(x=28, y=y)
        self.entry_confirmar = campo(top, show="•")
        self.entry_confirmar.place(x=28, y=y + 24, width=364, height=38)
        self.entry_confirmar.bind("<Return>", lambda e: self.confirmar())
        y += 76

        self.lbl_error = etiqueta(top, "", F_PEQUE, ROJO, wraplength=364, justify="left")
        self.lbl_error.place(x=28, y=y)
        boton(top, "Cancelar", top.destroy, "secundario").place(x=28, y=y + 30, width=150, height=42)
        boton(top, "Guardar", self.confirmar, "primario", (FUENTE, 12, "bold")).place(x=190, y=y + 30, width=202, height=42)
        top.bind("<Escape>", lambda e: top.destroy())
        (self.entry_clave if usuario else self.entry_usuario).focus_set()

    def confirmar(self):
        clave = self.entry_clave.get()
        error = _validar_nueva(clave, self.entry_confirmar.get())
        if error:
            self.lbl_error.config(text=error)
            return
        try:
            if self.usuario:
                db.ejecutar("UPDATE usuarios SET password = ? WHERE username = ?",
                            (hash_password(clave), self.usuario))
                mensaje = f"Contraseña de «{self.usuario}» restablecida."
            else:
                nombre = self.entry_usuario.get().strip()
                if len(nombre) < 3:
                    self.lbl_error.config(text="El usuario debe tener al menos 3 caracteres.")
                    return
                rol = "admin" if self.combo_rol.get() == "Administrador" else "cajero"
                db.ejecutar("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)",
                            (nombre, hash_password(clave), rol))
                mensaje = f"Usuario «{nombre}» creado como {rol}."
        except sqlite3.IntegrityError:
            self.lbl_error.config(text="Ya existe un usuario con ese nombre.")
            return
        except sqlite3.Error as e:
            self.lbl_error.config(text=f"No se pudo guardar: {e}")
            return
        self.top.destroy()
        self.ventana.cargar()
        self.ventana.aviso(mensaje)
