"""Compras: entrada de mercadería de un proveedor. Sube el stock y actualiza el costo."""
import datetime
import sqlite3
import tkinter as tk
from tkinter import ttk

import ajustes
import caja
import db
from estilos import (FONDO, BLANCO, BORDE, NAVY, TEXTO_SUAVE, VERDE, ROJO, F_PEQUE, F_NORMAL, F_SUBTITULO,
                     F_CAMPO,
                     moneda, boton, panel, etiqueta, campo, lista, tabla, llenar_tabla)
from utilidades import buscar_producto, fecha_corta


class Compras(tk.Frame):
    def __init__(self, padre, controlador):
        super().__init__(padre, bg=FONDO)
        self.controlador = controlador
        self.nombres = []
        self.por_codigo = {}
        self.proveedores = []
        self.widgets()

    def widgets(self):
        f = panel(self, "Registrar entrada de mercadería")
        f.place(x=16, y=16, width=420, height=574)

        etiqueta(f, "Proveedor *", F_PEQUE, TEXTO_SUAVE).place(x=16, y=52)
        self.combo_proveedor = lista(f, state="readonly")
        self.combo_proveedor.place(x=16, y=74, width=386, height=36)

        etiqueta(f, "Código de barras o producto *", F_PEQUE, TEXTO_SUAVE).place(x=16, y=122)
        self.combo_producto = lista(f)
        self.combo_producto.place(x=16, y=144, width=386, height=36)
        self.combo_producto.bind("<<ComboboxSelected>>", lambda e: self.mostrar_producto())
        self.combo_producto.bind("<Return>", lambda e: self.mostrar_producto())
        self.combo_producto.bind("<FocusOut>", lambda e: self.mostrar_producto())
        self.lbl_info = etiqueta(f, "", F_PEQUE, TEXTO_SUAVE, justify="left")
        self.lbl_info.place(x=16, y=186)

        etiqueta(f, "Cantidad *", F_PEQUE, TEXTO_SUAVE).place(x=16, y=218)
        self.entry_cantidad = ttk.Spinbox(f, from_=1, to=99999, font=F_CAMPO)
        self.entry_cantidad.place(x=16, y=240, width=185, height=36)
        etiqueta(f, f"Costo unitario ({ajustes.simbolo()}) *", F_PEQUE, TEXTO_SUAVE).place(x=217, y=218)
        self.entry_costo = campo(f)
        self.entry_costo.place(x=217, y=240, width=185, height=36)
        for w in (self.entry_cantidad, self.entry_costo):
            w.bind("<KeyRelease>", lambda e: self.actualizar_total())
            w.bind("<<Increment>>", lambda e: self.after(1, self.actualizar_total))
            w.bind("<<Decrement>>", lambda e: self.after(1, self.actualizar_total))

        tk.Frame(f, bg=BORDE).place(x=16, y=294, width=386, height=1)
        etiqueta(f, "Total de la compra", F_NORMAL, TEXTO_SUAVE).place(x=16, y=306)
        self.lbl_total_compra = etiqueta(f, moneda(0), F_SUBTITULO, NAVY)
        self.lbl_total_compra.place(x=402, y=304, anchor="ne")

        # Si la compra se paga con el efectivo de la caja, el arqueo tiene que
        # enterarse: si no, al cerrar el turno faltaría ese dinero sin explicación.
        self.pagar_de_caja = tk.BooleanVar(value=False)
        self.chk_caja = tk.Checkbutton(f, text="", variable=self.pagar_de_caja, font=F_PEQUE, bg=BLANCO,
                                       fg=TEXTO_SUAVE, activebackground=BLANCO, highlightthickness=0, anchor="w",
                                       wraplength=366, justify="left")
        self.chk_caja.place(x=13, y=332, width=390, height=40)

        boton(f, "Registrar entrada", self.registrar, "exito").place(x=16, y=380, width=386, height=46)
        self.lbl_mensaje = etiqueta(f, "", F_PEQUE, VERDE, wraplength=386, justify="left")
        self.lbl_mensaje.place(x=16, y=438)
        etiqueta(f, "Al registrar la entrada, la cantidad se suma al stock y el costo del producto se actualiza "
                    "con el de esta compra.", F_PEQUE, TEXTO_SUAVE, wraplength=386, justify="left").place(x=16, y=500)

        t = panel(self, "Entradas recientes")
        t.place(x=452, y=16, width=632, height=574)
        columnas = [("fecha", "Fecha", 90, "center"), ("proveedor", "Proveedor", 150, "w"),
                    ("producto", "Producto", 140, "w"), ("cant", "Cant.", 50, "center"),
                    ("costo", "Costo", 74, "e"), ("total", "Total", 80, "e")]
        marco, self.tree = tabla(t, columnas)
        marco.place(x=16, y=52, width=600, height=460)
        self.lbl_resumen = etiqueta(t, "", F_PEQUE, TEXTO_SUAVE)
        self.lbl_resumen.place(x=16, y=528)

    def al_mostrar(self):
        self.proveedores = [f[0] for f in db.consultar("SELECT nombre FROM proveedores WHERE activo = 1 "
                                                       "ORDER BY nombre")]
        self.combo_proveedor["values"] = self.proveedores
        if self.combo_proveedor.get() not in self.proveedores:
            self.combo_proveedor.set(self.proveedores[0] if self.proveedores else "")
        filas = db.consultar("SELECT articulo, codigo FROM articulos ORDER BY articulo")
        self.nombres = [f[0] for f in filas]
        self.por_codigo = {f[1]: f[0] for f in filas if f[1]}
        self.combo_producto["values"] = self.nombres
        self.actualizar_caja()
        self.cargar_compras()

    def actualizar_caja(self):
        """Solo se puede pagar de la caja si hay un turno abierto."""
        turno = caja.caja_abierta()
        if turno:
            disponible = caja.resumen(turno[0])["esperado"]
            self.chk_caja.config(text=f"Pagada con el efectivo de la caja (hay {moneda(disponible)})",
                                 state="normal")
        else:
            self.pagar_de_caja.set(False)
            self.chk_caja.config(text="Pagada con el efectivo de la caja (no hay turno abierto)", state="disabled")

    def cargar_compras(self):
        filas = db.consultar("SELECT fecha, proveedor, articulo, cantidad, costo, total FROM compras "
                             "ORDER BY id DESC LIMIT 200")
        llenar_tabla(self.tree, [(fecha_corta(f[0]), f[1], f[2], f[3], moneda(f[4]), moneda(f[5])) for f in filas])
        desde = (datetime.date.today() - datetime.timedelta(days=29)).isoformat()
        total = db.uno("SELECT COALESCE(SUM(total), 0) FROM compras WHERE fecha >= ?", (desde,))[0]
        self.lbl_resumen.config(text=f"Compras de los últimos 30 días: {moneda(total)}")

    def mostrar_producto(self):
        nombre = buscar_producto(self.combo_producto.get(), self.nombres, self.por_codigo)
        if not nombre:
            self.lbl_info.config(text="")
            return None
        if self.combo_producto.get() != nombre:
            self.combo_producto.set(nombre)
        stock, costo = db.uno("SELECT stock, costo FROM articulos WHERE articulo = ?", (nombre,))
        self.lbl_info.config(text=f"Stock actual: {stock}   ·   Costo actual: {moneda(costo)}")
        if not self.entry_costo.get().strip():
            self.entry_costo.insert(0, f"{costo:.2f}")
        self.actualizar_total()
        return nombre

    def _numeros(self):
        try:
            cantidad = int(self.entry_cantidad.get())
            costo = round(float(self.entry_costo.get().replace(",", "")), 2)
        except ValueError:
            return None, None
        return cantidad, costo

    def actualizar_total(self):
        cantidad, costo = self._numeros()
        self.lbl_total_compra.config(text=moneda(cantidad * costo) if cantidad and costo is not None else moneda(0))

    def registrar(self):
        proveedor = self.combo_proveedor.get()
        if not proveedor:
            self.lbl_mensaje.config(text="Primero registre un proveedor en el módulo Proveedores.", fg=ROJO)
            return
        nombre = buscar_producto(self.combo_producto.get(), self.nombres, self.por_codigo)
        if not nombre:
            self.lbl_mensaje.config(text="Elija un producto de la lista o escriba su código de barras.", fg=ROJO)
            return
        cantidad, costo = self._numeros()
        if not cantidad or cantidad <= 0 or costo is None or costo < 0:
            self.lbl_mensaje.config(text="La cantidad debe ser un entero mayor que 0 y el costo un número válido.",
                                    fg=ROJO)
            return
        total = round(cantidad * costo, 2)
        turno = caja.caja_abierta() if self.pagar_de_caja.get() else None
        if self.pagar_de_caja.get():
            if not turno:
                self.lbl_mensaje.config(text="No hay un turno de caja abierto para pagar la compra.", fg=ROJO)
                self.actualizar_caja()
                return
            if total > caja.resumen(turno[0])["esperado"]:
                self.lbl_mensaje.config(text="No hay suficiente efectivo en la caja para pagar esta compra.",
                                        fg=ROJO)
                return

        ahora = datetime.datetime.now()
        fecha, hora = ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S")
        try:
            # La compra, el stock y la salida de caja van juntos: o se guarda todo
            # o no se guarda nada.
            with db.conectar() as conn:
                conn.execute("INSERT INTO compras (fecha, hora, proveedor, articulo, cantidad, costo, total, usuario) "
                             "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (fecha, hora, proveedor, nombre, cantidad, costo, total,
                              self.controlador.usuario_actual))
                conn.execute("UPDATE articulos SET stock = stock + ?, costo = ? WHERE articulo = ?",
                             (cantidad, costo, nombre))
                if turno:
                    conn.execute("INSERT INTO movimientos_caja (caja_id, tipo, monto, motivo, fecha, hora, usuario) "
                                 "VALUES (?, 'SALIDA', ?, ?, ?, ?, ?)",
                                 (turno[0], total, f"Compra a {proveedor}", fecha, hora,
                                  self.controlador.usuario_actual))
                stock = conn.execute("SELECT stock FROM articulos WHERE articulo = ?", (nombre,)).fetchone()[0]
        except sqlite3.Error as e:
            self.lbl_mensaje.config(text=f"No se pudo registrar la entrada: {e}", fg=ROJO)
            return
        aviso = f"Entrada registrada: +{cantidad} de {nombre}. Stock actual: {stock}."
        if turno:
            aviso += f" Se descontaron {moneda(total)} de la caja."
        self.lbl_mensaje.config(text=aviso, fg=VERDE)
        self.pagar_de_caja.set(False)
        self.actualizar_caja()
        self.combo_producto.set("")
        self.entry_cantidad.set(1)
        self.entry_costo.delete(0, "end")
        self.lbl_info.config(text="")
        self.actualizar_total()
        self.cargar_compras()
