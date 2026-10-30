"""Clientes y Proveedores: la misma pantalla de catálogo con distinta configuración."""
import re
import sqlite3
import tkinter as tk
from tkinter import messagebox

import db
from estilos import (FONDO, NAVY, TEXTO_SUAVE, VERDE, ROJO, F_PEQUE, F_SUBTITULO, boton, panel, etiqueta, campo,
                     tabla, llenar_tabla)


class Catalogo(tk.Frame):
    TABLA = ""
    SINGULAR = ""
    PLURAL = ""
    CAMPOS = []          # (columna, etiqueta, obligatorio)
    COLUMNAS = []        # columnas de la tabla: (id, título, ancho, alineación); la primera es el id
    BUSCAR_EN = []       # columnas en las que busca el buscador
    UNICO = ""           # columna única (para el mensaje de error)
    PROTEGIDO = None     # nombre de un registro del sistema que no se puede editar

    def __init__(self, padre, controlador):
        super().__init__(padre, bg=FONDO)
        self.controlador = controlador
        self.editando = None
        self.editando_activo = True
        self.widgets()

    def widgets(self):
        f = panel(self)
        f.place(x=16, y=16, width=340, height=574)
        self.lbl_form = etiqueta(f, f"Nuevo {self.SINGULAR}", F_SUBTITULO, NAVY)
        self.lbl_form.place(x=16, y=10)
        self.entradas = {}
        for i, (columna, texto, obligatorio) in enumerate(self.CAMPOS):
            y = 52 + i * 66
            etiqueta(f, texto + (" *" if obligatorio else ""), F_PEQUE, TEXTO_SUAVE).place(x=16, y=y)
            e = campo(f)
            e.place(x=16, y=y + 22, width=306, height=36)
            e.bind("<Return>", lambda ev: self.guardar())
            self.entradas[columna] = e
        y = 52 + len(self.CAMPOS) * 66 + 8
        self.btn_guardar = boton(f, f"Guardar {self.SINGULAR}", self.guardar)
        self.btn_guardar.place(x=16, y=y, width=306, height=42)
        boton(f, "Nuevo", self.limpiar, "secundario").place(x=16, y=y + 52, width=148, height=38)
        self.btn_baja = boton(f, "Dar de baja", self.cambiar_estado, "secundario")
        self.btn_baja.place(x=174, y=y + 52, width=148, height=38)
        self.btn_baja.config(state="disabled")
        self.lbl_mensaje = etiqueta(f, "", F_PEQUE, VERDE, wraplength=306, justify="left")
        self.lbl_mensaje.place(x=16, y=y + 100)
        etiqueta(f, "* Campo obligatorio", F_PEQUE, TEXTO_SUAVE).place(x=16, y=540)

        t = panel(self, f"{self.PLURAL.capitalize()} registrados")
        t.place(x=372, y=16, width=712, height=574)
        etiqueta(t, "Buscar", F_PEQUE, TEXTO_SUAVE).place(x=392, y=16)
        self.entry_buscar = campo(t)
        self.entry_buscar.place(x=446, y=10, width=250, height=32)
        self.entry_buscar.bind("<KeyRelease>", lambda e: self.cargar_registros())
        marco, self.tre = tabla(t, self.COLUMNAS)
        marco.place(x=16, y=52, width=680, height=460)
        self.tre.bind("<<TreeviewSelect>>", self.al_seleccionar)
        self.lbl_total = etiqueta(t, "", F_PEQUE, TEXTO_SUAVE)
        self.lbl_total.place(x=16, y=528)
        etiqueta(t, "Seleccione una fila para editarla.", F_PEQUE, TEXTO_SUAVE).place(x=696, y=528, anchor="ne")

    def al_mostrar(self):
        self.cargar_registros()

    def cargar_registros(self):
        columnas = ["id"] + [c[0] for c in self.CAMPOS] + ["activo"]
        texto = self.entry_buscar.get().strip()
        sql = f"SELECT {', '.join(columnas)} FROM {self.TABLA}"
        parametros = []
        if texto:
            sql += " WHERE " + " OR ".join(f"{c} LIKE ?" for c in self.BUSCAR_EN)
            parametros = [f"%{texto}%"] * len(self.BUSCAR_EN)
        # Los dados de baja van al final; el registro protegido, primero de todos.
        sql += " ORDER BY activo DESC, "
        if self.PROTEGIDO:
            sql += "nombre = ? DESC, "
            parametros.append(self.PROTEGIDO)
        filas = db.consultar(sql + "nombre", parametros)

        orden = [c[0] for c in self.COLUMNAS]
        i_estado = orden.index("estado")
        vista = []
        for f in filas:
            d = dict(zip(columnas, f))
            d["estado"] = "Activo" if d["activo"] else "Baja"
            vista.append(tuple("" if d[c] is None else d[c] for c in orden))
        llenar_tabla(self.tre, vista, lambda fila: [] if fila[i_estado] == "Activo" else ["anulada"])
        activos = sum(1 for f in filas if f[-1])
        de_baja = len(filas) - activos
        self.lbl_total.config(text=f"{activos} {self.PLURAL if activos != 1 else self.SINGULAR}"
                                   + (f"  ·  {de_baja} de baja" if de_baja else ""))

    def limpiar(self):
        self.editando = None
        for e in self.entradas.values():
            e.delete(0, "end")
        self.lbl_form.config(text=f"Nuevo {self.SINGULAR}")
        self.btn_guardar.config(text=f"Guardar {self.SINGULAR}")
        self.btn_baja.config(state="disabled", text="Dar de baja")
        self.tre.selection_remove(*self.tre.selection())
        self.lbl_mensaje.config(text="")
        self.entradas[self.CAMPOS[0][0]].focus_set()

    def al_seleccionar(self, event=None):
        seleccion = self.tre.selection()
        if not seleccion:
            return
        id_registro = int(str(self.tre.item(seleccion[0], "values")[0]))
        columnas = [c[0] for c in self.CAMPOS]
        fila = db.uno(f"SELECT {', '.join(columnas)}, activo FROM {self.TABLA} WHERE id = ?", (id_registro,))
        if fila is None:
            return
        if self.PROTEGIDO and fila[0] == self.PROTEGIDO:
            self.limpiar()
            self.lbl_mensaje.config(text=f"«{self.PROTEGIDO}» es un registro del sistema y no se puede modificar.",
                                    fg=ROJO)
            return
        self.editando = id_registro
        self.editando_activo = bool(fila[-1])
        for columna, valor in zip(columnas, fila):
            self.entradas[columna].delete(0, "end")
            self.entradas[columna].insert(0, valor or "")
        self.lbl_form.config(text=f"Editar {self.SINGULAR}")
        self.btn_guardar.config(text="Guardar cambios")
        self.btn_baja.config(state="normal", text="Dar de baja" if self.editando_activo else "Reactivar")
        self.lbl_mensaje.config(text="")

    def cambiar_estado(self):
        """Da de baja o reactiva. No se borra: las ventas y compras viejas lo nombran."""
        if not self.editando:
            return
        nombre = self.entradas["nombre"].get().strip()
        baja = self.editando_activo
        if baja and not messagebox.askyesno(
                f"Dar de baja {self.SINGULAR}",
                f"¿Dar de baja a «{nombre}»?\n\nDeja de aparecer al vender o comprar, pero el historial se "
                "conserva y lo podés reactivar cuando quieras.", parent=self):
            return
        try:
            db.ejecutar(f"UPDATE {self.TABLA} SET activo = ? WHERE id = ?", (0 if baja else 1, self.editando))
        except sqlite3.Error as e:
            self.lbl_mensaje.config(text=f"No se pudo guardar: {e}", fg=ROJO)
            return
        self.limpiar()
        self.lbl_mensaje.config(text=f"«{nombre}» quedó {'de baja' if baja else 'activo'}.", fg=VERDE)
        self.cargar_registros()

    def validar(self, datos):
        """Devuelve un mensaje de error o None. Las subclases agregan sus reglas."""
        correo = datos.get("correo")
        if correo and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
            return "El correo no es válido (ejemplo: nombre@correo.com)."
        return None

    def guardar(self):
        datos = {c: (e.get().strip() or None) for c, e in self.entradas.items()}
        for columna, texto, obligatorio in self.CAMPOS:
            if obligatorio and not datos[columna]:
                self.lbl_mensaje.config(text=f"El campo «{texto}» es obligatorio.", fg=ROJO)
                return
        error = self.validar(datos)
        if error:
            self.lbl_mensaje.config(text=error, fg=ROJO)
            return
        columnas = list(datos)
        try:
            if self.editando:
                db.ejecutar(f"UPDATE {self.TABLA} SET {', '.join(c + ' = ?' for c in columnas)} WHERE id = ?",
                            tuple(datos.values()) + (self.editando,))
                mensaje = f"Cambios guardados: {datos['nombre']}."
            else:
                db.ejecutar(f"INSERT INTO {self.TABLA} ({', '.join(columnas)}) VALUES ({', '.join('?' * len(columnas))})",
                            tuple(datos.values()))
                mensaje = f"{self.SINGULAR.capitalize()} registrado: {datos['nombre']}."
        except sqlite3.IntegrityError:
            self.lbl_mensaje.config(text=f"Ya existe un {self.SINGULAR} con ese {self.UNICO}.", fg=ROJO)
            return
        except sqlite3.Error as e:
            self.lbl_mensaje.config(text=f"No se pudo guardar: {e}", fg=ROJO)
            return
        self.limpiar()
        self.lbl_mensaje.config(text=mensaje, fg=VERDE)
        self.cargar_registros()


class Clientes(Catalogo):
    TABLA = "clientes"
    SINGULAR = "cliente"
    PLURAL = "clientes"
    CAMPOS = [("nombre", "Nombre completo", True), ("cedula", "Cédula", False), ("celular", "Celular", False),
              ("direccion", "Dirección", False), ("correo", "Correo", False)]
    COLUMNAS = [("id", "ID", 40, "center"), ("nombre", "Nombre", 160, "w"), ("cedula", "Cédula", 134, "center"),
                ("celular", "Celular", 120, "center"), ("correo", "Correo", 146, "w"),
                ("estado", "Estado", 76, "center")]
    BUSCAR_EN = ["nombre", "cedula", "celular"]
    UNICO = "número de cédula"
    PROTEGIDO = "Consumidor final"

    def validar(self, datos):
        cedula = datos.get("cedula")
        if cedula:
            # Cédula nicaragüense: 3 dígitos, 6 de la fecha de nacimiento, 4 dígitos y una letra.
            m = re.fullmatch(r"(\d{3})-?(\d{6})-?(\d{4})([A-Za-z])", cedula)
            if not m:
                return "Cédula no válida. Formato: 001-150390-0001X."
            datos["cedula"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}{m.group(4).upper()}"
        return super().validar(datos)


class Proveedores(Catalogo):
    TABLA = "proveedores"
    SINGULAR = "proveedor"
    PLURAL = "proveedores"
    CAMPOS = [("nombre", "Razón social", True), ("ruc", "RUC", False), ("telefono", "Teléfono", False),
              ("direccion", "Dirección", False), ("correo", "Correo", False)]
    COLUMNAS = [("id", "ID", 40, "center"), ("nombre", "Razón social", 176, "w"), ("ruc", "RUC", 134, "center"),
                ("telefono", "Teléfono", 114, "center"), ("correo", "Correo", 136, "w"),
                ("estado", "Estado", 76, "center")]
    BUSCAR_EN = ["nombre", "ruc", "telefono"]
    UNICO = "RUC"

    def validar(self, datos):
        ruc = datos.get("ruc")
        if ruc:
            if not re.fullmatch(r"[A-Za-z0-9]{14}", ruc):
                return "El RUC debe tener 14 caracteres, sin guiones (ejemplo: J0310000000011)."
            datos["ruc"] = ruc.upper()
        return super().validar(datos)
