"""Arqueo de caja: turnos, movimientos de efectivo y cierre con conteo.

Un turno se abre con el dinero con el que arranca la caja. Durante el turno se
suman las ventas en efectivo y los movimientos (entradas y salidas que no son
ventas). Al cerrar, el cajero cuenta el efectivo y el sistema compara:

    esperado  = monto inicial + ventas en efectivo + entradas - salidas
    diferencia = contado - esperado       (negativo = falta, positivo = sobra)

Las facturas anuladas no suman, porque ese dinero se devolvió.
"""
import datetime
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

import db
from estilos import (FONDO, BORDE, NAVY, TEXTO, TEXTO_SUAVE, VERDE, ROJO, AMBAR, FUENTE, F_PEQUE, F_NORMAL,
                     F_NEGRITA, F_SUBTITULO, F_TITULO, F_GRANDE, moneda, boton, panel, etiqueta, campo,
                     lista, tabla, llenar_tabla, ventana_modal)
from utilidades import fecha_corta


def caja_abierta():
    """El turno abierto, o None. Solo puede haber uno (índice único en el esquema)."""
    return db.uno("SELECT id, usuario, fecha_apertura, hora_apertura, monto_inicial FROM cajas "
                  "WHERE estado = 'ABIERTA'")


def resumen(caja_id):
    """Cuánto debería haber en la caja de este turno y de dónde viene."""
    efectivo, tarjeta, facturas = db.uno(
        "SELECT COALESCE(SUM(CASE WHEN metodo_pago = 'Efectivo' THEN total ELSE 0 END), 0), "
        "       COALESCE(SUM(CASE WHEN metodo_pago = 'Tarjeta'  THEN total ELSE 0 END), 0), "
        "       COUNT(DISTINCT factura) "
        "FROM ventas WHERE caja_id = ? AND estado = 'EMITIDA'", (caja_id,))
    entradas, salidas = db.uno(
        "SELECT COALESCE(SUM(CASE WHEN tipo = 'ENTRADA' THEN monto ELSE 0 END), 0), "
        "       COALESCE(SUM(CASE WHEN tipo = 'SALIDA'  THEN monto ELSE 0 END), 0) "
        "FROM movimientos_caja WHERE caja_id = ?", (caja_id,))
    inicial = db.uno("SELECT monto_inicial FROM cajas WHERE id = ?", (caja_id,))[0]
    return {"inicial": inicial, "efectivo": efectivo, "tarjeta": tarjeta, "facturas": facturas,
            "entradas": entradas, "salidas": salidas,
            "esperado": round(inicial + efectivo + entradas - salidas, 2)}


def abrir_turno(usuario, monto_inicial):
    """Abre un turno. Devuelve el id, o lanza ValueError si ya hay uno abierto."""
    ahora = datetime.datetime.now()
    try:
        with db.conectar() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM cajas WHERE estado = 'ABIERTA'").fetchone():
                raise ValueError("Ya hay un turno de caja abierto.")
            cur = conn.execute(
                "INSERT INTO cajas (usuario, fecha_apertura, hora_apertura, monto_inicial, estado) "
                "VALUES (?, ?, ?, ?, 'ABIERTA')",
                (usuario, ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"), monto_inicial))
            return cur.lastrowid
    except sqlite3.IntegrityError:
        # El índice único idx_caja_abierta lo impide aunque dos cajas lo intenten a la vez.
        raise ValueError("Ya hay un turno de caja abierto.")


class Caja(tk.Frame):
    def __init__(self, padre, controlador):
        super().__init__(padre, bg=FONDO)
        self.controlador = controlador
        self.caja_id = None
        self.widgets()

    # ------------------------------------------------------------------ interfaz
    def widgets(self):
        t = panel(self, "Turno actual")
        t.place(x=16, y=16, width=528, height=300)
        self.lbl_estado = etiqueta(t, "", F_SUBTITULO, TEXTO)
        self.lbl_estado.place(x=16, y=48)
        self.lbl_detalle = etiqueta(t, "", F_PEQUE, TEXTO_SUAVE, justify="left", anchor="nw")
        self.lbl_detalle.place(x=16, y=78, width=496, height=52)

        self.btn_abrir = boton(t, "Abrir caja", self.abrir, "exito", (FUENTE, 12, "bold"))
        self.btn_abrir.place(x=16, y=146, width=240, height=46)
        self.btn_cerrar = boton(t, "Cerrar caja y arquear", self.cerrar, "peligro", (FUENTE, 12, "bold"))
        self.btn_cerrar.place(x=272, y=146, width=240, height=46)
        self.btn_entrada = boton(t, "Registrar entrada", lambda: self.movimiento("ENTRADA"), "secundario")
        self.btn_entrada.place(x=16, y=206, width=240, height=40)
        self.btn_salida = boton(t, "Registrar salida", lambda: self.movimiento("SALIDA"), "secundario")
        self.btn_salida.place(x=272, y=206, width=240, height=40)
        etiqueta(t, "Las entradas y salidas son el efectivo que entra o sale sin ser una venta: cambio, "
                    "pago a un proveedor, retiro.", F_PEQUE, TEXTO_SUAVE, wraplength=496,
                 justify="left").place(x=16, y=256)

        r = panel(self, "Resumen del turno")
        r.place(x=560, y=16, width=524, height=300)
        self.valores = {}
        filas = [("Monto inicial", "inicial"), ("Ventas en efectivo", "efectivo"),
                 ("Entradas de efectivo", "entradas"), ("Salidas de efectivo", "salidas")]
        for i, (texto, clave) in enumerate(filas):
            y = 50 + i * 32
            etiqueta(r, texto, F_NORMAL, TEXTO_SUAVE).place(x=16, y=y)
            lbl = etiqueta(r, moneda(0), F_NEGRITA, TEXTO)
            lbl.place(x=506, y=y, anchor="ne")
            self.valores[clave] = lbl
        tk.Frame(r, bg=BORDE).place(x=16, y=186, width=490, height=1)
        etiqueta(r, "Efectivo esperado en caja", F_NORMAL, TEXTO_SUAVE).place(x=16, y=200)
        self.lbl_esperado = etiqueta(r, moneda(0), F_GRANDE, NAVY)
        self.lbl_esperado.place(x=506, y=222, anchor="ne")
        self.lbl_otros = etiqueta(r, "", F_PEQUE, TEXTO_SUAVE)
        self.lbl_otros.place(x=16, y=268)

        m = panel(self, "Movimientos del turno")
        m.place(x=16, y=330, width=528, height=260)
        marco, self.tree_mov = tabla(m, [("hora", "Hora", 70, "center"), ("tipo", "Tipo", 80, "center"),
                                         ("motivo", "Motivo", 220, "w"), ("monto", "Monto", 100, "e")],
                                    estilo="Compacta.Treeview")
        marco.place(x=16, y=44, width=496, height=200)

        h = panel(self, "Arqueos anteriores")
        h.place(x=560, y=330, width=524, height=260)
        marco, self.tree_hist = tabla(h, [("fecha", "Fecha", 86, "center"), ("cajero", "Cajero", 90, "w"),
                                          ("esperado", "Esperado", 96, "e"), ("contado", "Contado", 96, "e"),
                                          ("dif", "Diferencia", 96, "e")], estilo="Compacta.Treeview")
        marco.place(x=16, y=44, width=492, height=200)

    # ------------------------------------------------------------------ datos
    def al_mostrar(self):
        self.refrescar()

    def refrescar(self):
        fila = caja_abierta()
        self.caja_id = fila[0] if fila else None
        propia_o_admin = bool(fila) and (fila[1] == self.controlador.usuario_actual or self.controlador.es_admin)

        if fila:
            _, usuario, fecha, hora, _ = fila
            self.lbl_estado.config(text="Caja abierta", fg=VERDE)
            self.lbl_detalle.config(text=f"Abierta por {usuario} el {fecha_corta(fecha)} a las {hora[:5]}.\n"
                                         + ("" if propia_o_admin else
                                            "Solo ese cajero o un administrador puede cerrarla."))
            datos = resumen(self.caja_id)
            self.lbl_otros.config(text=f"{datos['facturas']} factura{'s' if datos['facturas'] != 1 else ''} en el "
                                       f"turno  ·  {moneda(datos['tarjeta'])} cobrados con tarjeta (no entran al "
                                       "efectivo)")
        else:
            self.lbl_estado.config(text="Caja cerrada", fg=ROJO)
            self.lbl_detalle.config(text="Abrí el turno con el dinero con el que arranca la caja. Sin caja abierta "
                                         "no se pueden cobrar ventas.")
            datos = {"inicial": 0, "efectivo": 0, "entradas": 0, "salidas": 0, "esperado": 0, "tarjeta": 0}
            self.lbl_otros.config(text="")

        for clave, lbl in self.valores.items():
            lbl.config(text=moneda(datos[clave]))
        self.lbl_esperado.config(text=moneda(datos["esperado"]))

        self.btn_abrir.config(state="disabled" if fila else "normal")
        for b in (self.btn_cerrar, self.btn_entrada, self.btn_salida):
            b.config(state="normal" if propia_o_admin else "disabled")

        if self.caja_id:
            filas = db.consultar("SELECT hora, tipo, motivo, monto FROM movimientos_caja WHERE caja_id = ? "
                                 "ORDER BY id DESC", (self.caja_id,))
            llenar_tabla(self.tree_mov, [(f[0][:5], f[1].capitalize(), f[2], moneda(f[3])) for f in filas],
                         lambda f: ["alerta"] if f[1] == "Salida" else [])
        else:
            llenar_tabla(self.tree_mov, [])

        # El cajero ve sus propios arqueos; el administrador ve los de todos.
        sql = ("SELECT fecha_cierre, usuario, esperado, monto_contado, diferencia FROM cajas "
               "WHERE estado = 'CERRADA'")
        parametros = []
        if not self.controlador.puede("ver_todas_las_cajas"):
            sql += " AND usuario = ?"
            parametros.append(self.controlador.usuario_actual)
        filas = db.consultar(sql + " ORDER BY id DESC LIMIT 100", parametros)
        llenar_tabla(self.tree_hist,
                     [(fecha_corta(f[0]), f[1], moneda(f[2]), moneda(f[3]), moneda(f[4])) for f in filas],
                     lambda f: ["alerta"] if f[4] != moneda(0) else [])

    # ------------------------------------------------------------------ acciones
    def abrir(self):
        VentanaAbrirCaja(self)

    def cerrar(self):
        if not self.caja_id:
            return
        VentanaCerrarCaja(self)

    def movimiento(self, tipo):
        if not self.caja_id:
            return
        VentanaMovimiento(self, tipo)


class VentanaAbrirCaja:
    """Pide el dinero con el que arranca la caja."""

    def __init__(self, padre, al_abrir=None):
        self.padre = padre
        self.al_abrir = al_abrir
        self.controlador = padre.controlador
        top = self.top = ventana_modal(padre, "Abrir caja", 420, 300)
        etiqueta(top, "Abrir caja", F_TITULO, TEXTO).place(x=28, y=22)
        etiqueta(top, "Escriba el efectivo con el que arranca el turno. Si arranca sin fondo, dejá 0.",
                 F_PEQUE, TEXTO_SUAVE, wraplength=364, justify="left").place(x=28, y=64)

        etiqueta(top, "Monto inicial (C$)", F_NEGRITA, TEXTO).place(x=28, y=116)
        self.entry = campo(top)
        self.entry.place(x=28, y=142, width=364, height=42)
        self.entry.insert(0, "0.00")
        self.entry.bind("<Return>", lambda e: self.confirmar())
        self.lbl_error = etiqueta(top, "", F_PEQUE, ROJO, wraplength=364, justify="left")
        self.lbl_error.place(x=28, y=192)

        boton(top, "Cancelar", top.destroy, "secundario").place(x=28, y=232, width=150, height=44)
        boton(top, "Abrir caja", self.confirmar, "exito", (FUENTE, 12, "bold")).place(x=190, y=232, width=202, height=44)
        top.bind("<Escape>", lambda e: top.destroy())
        self.entry.focus_set()
        self.entry.select_range(0, "end")

    def confirmar(self):
        try:
            monto = round(float(self.entry.get().replace("C$", "").replace(",", "").strip()), 2)
        except ValueError:
            self.lbl_error.config(text="Escriba un monto válido (por ejemplo 500.00).")
            return
        if monto < 0:
            self.lbl_error.config(text="El monto no puede ser negativo.")
            return
        try:
            abrir_turno(self.controlador.usuario_actual, monto)
        except (ValueError, sqlite3.Error) as e:
            self.lbl_error.config(text=str(e))
            return
        self.top.destroy()
        # La abre tanto el módulo Caja como la pantalla de Ventas; cada una se
        # actualiza a su manera.
        refrescar = getattr(self.padre, "refrescar", None) or getattr(self.padre, "actualizar_caja", None)
        if refrescar:
            refrescar()
        if self.al_abrir:
            self.al_abrir()


class VentanaMovimiento:
    """Entrada o salida de efectivo que no es una venta."""

    MOTIVOS = {
        "ENTRADA": ["Fondo adicional", "Cobro de un crédito", "Devolución de un proveedor", "Otro"],
        "SALIDA": ["Pago a proveedor", "Retiro a bóveda", "Gasto de la tienda", "Otro"],
    }

    def __init__(self, caja, tipo):
        self.caja = caja
        self.tipo = tipo
        titulo = "Registrar entrada de efectivo" if tipo == "ENTRADA" else "Registrar salida de efectivo"
        top = self.top = ventana_modal(caja, titulo, 440, 360)
        etiqueta(top, titulo, F_SUBTITULO, TEXTO, wraplength=384, justify="left").place(x=28, y=22)

        etiqueta(top, "Monto (C$)", F_NEGRITA, TEXTO).place(x=28, y=80)
        self.entry_monto = campo(top)
        self.entry_monto.place(x=28, y=106, width=384, height=40)
        self.entry_monto.bind("<Return>", lambda e: self.confirmar())

        etiqueta(top, "Motivo", F_NEGRITA, TEXTO).place(x=28, y=162)
        self.combo = lista(top, values=self.MOTIVOS[tipo])
        self.combo.place(x=28, y=188, width=384, height=40)
        self.combo.set(self.MOTIVOS[tipo][0])

        self.lbl_error = etiqueta(top, "", F_PEQUE, ROJO, wraplength=384, justify="left")
        self.lbl_error.place(x=28, y=240)

        boton(top, "Cancelar", top.destroy, "secundario").place(x=28, y=292, width=150, height=44)
        boton(top, "Registrar", self.confirmar, "primario", (FUENTE, 12, "bold")).place(x=190, y=292, width=222, height=44)
        top.bind("<Escape>", lambda e: top.destroy())
        self.entry_monto.focus_set()

    def confirmar(self):
        try:
            monto = round(float(self.entry_monto.get().replace("C$", "").replace(",", "").strip()), 2)
        except ValueError:
            self.lbl_error.config(text="Escriba un monto válido.")
            return
        if monto <= 0:
            self.lbl_error.config(text="El monto debe ser mayor que cero.")
            return
        motivo = self.combo.get().strip()
        if not motivo:
            self.lbl_error.config(text="Escriba el motivo.")
            return
        if self.tipo == "SALIDA" and monto > resumen(self.caja.caja_id)["esperado"]:
            self.lbl_error.config(text="No puede sacar más efectivo del que hay en la caja.")
            return
        ahora = datetime.datetime.now()
        try:
            db.ejecutar("INSERT INTO movimientos_caja (caja_id, tipo, monto, motivo, fecha, hora, usuario) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (self.caja.caja_id, self.tipo, monto, motivo, ahora.strftime("%Y-%m-%d"),
                         ahora.strftime("%H:%M:%S"), self.caja.controlador.usuario_actual))
        except sqlite3.Error as e:
            self.lbl_error.config(text=f"No se pudo registrar: {e}")
            return
        self.top.destroy()
        self.caja.refrescar()


class VentanaCerrarCaja:
    """Muestra lo que debería haber, pide el conteo y guarda la diferencia."""

    def __init__(self, caja):
        self.caja = caja
        self.datos = resumen(caja.caja_id)
        top = self.top = ventana_modal(caja, "Cerrar caja", 460, 580)
        etiqueta(top, "Cerrar caja y arquear", F_TITULO, TEXTO).place(x=28, y=22)
        etiqueta(top, "Cuente el efectivo que hay en la caja y escriba el total.", F_PEQUE, TEXTO_SUAVE,
                 wraplength=404, justify="left").place(x=28, y=62)

        filas = [("Monto inicial", self.datos["inicial"]), ("Ventas en efectivo", self.datos["efectivo"]),
                 ("Entradas", self.datos["entradas"]), ("Salidas", -self.datos["salidas"])]
        for i, (texto, valor) in enumerate(filas):
            y = 104 + i * 26
            etiqueta(top, texto, F_PEQUE, TEXTO_SUAVE).place(x=28, y=y)
            etiqueta(top, moneda(valor), F_PEQUE, TEXTO).place(x=432, y=y, anchor="ne")
        tk.Frame(top, bg=BORDE).place(x=28, y=212, width=404, height=1)
        etiqueta(top, "Efectivo esperado", F_NEGRITA, TEXTO).place(x=28, y=224)
        etiqueta(top, moneda(self.datos["esperado"]), F_SUBTITULO, NAVY).place(x=432, y=222, anchor="ne")

        etiqueta(top, "Efectivo contado (C$)", F_NEGRITA, TEXTO).place(x=28, y=272)
        self.monto = tk.StringVar()
        self.entry = ttk.Entry(top, textvariable=self.monto, font=(FUENTE, 16))
        self.entry.place(x=28, y=298, width=404, height=44)
        self.entry.bind("<Return>", lambda e: self.confirmar())
        self.monto.trace_add("write", lambda *a: self.actualizar_diferencia())

        self.lbl_dif = etiqueta(top, "", F_SUBTITULO, TEXTO_SUAVE, wraplength=404, justify="left")
        self.lbl_dif.place(x=28, y=354)

        etiqueta(top, "Observación (opcional)", F_PEQUE, TEXTO_SUAVE).place(x=28, y=404)
        self.entry_obs = campo(top)
        self.entry_obs.place(x=28, y=426, width=404, height=38)

        self.lbl_error = etiqueta(top, "", F_PEQUE, ROJO, wraplength=404, justify="left")
        self.lbl_error.place(x=28, y=476)

        boton(top, "Cancelar", top.destroy, "secundario").place(x=28, y=512, width=150, height=46)
        boton(top, "Cerrar caja", self.confirmar, "peligro", (FUENTE, 12, "bold")).place(x=190, y=512, width=242, height=46)
        top.bind("<Escape>", lambda e: top.destroy())
        self.entry.focus_set()
        self.actualizar_diferencia()

    def leer(self):
        try:
            return round(float(self.monto.get().replace("C$", "").replace(",", "").strip()), 2)
        except ValueError:
            return None

    def actualizar_diferencia(self):
        contado = self.leer()
        if contado is None:
            self.lbl_dif.config(text="", fg=TEXTO_SUAVE)
            return
        diferencia = round(contado - self.datos["esperado"], 2)
        if abs(diferencia) < 0.005:
            self.lbl_dif.config(text="Cuadra exacto.", fg=VERDE)
        elif diferencia < 0:
            self.lbl_dif.config(text=f"Faltan {moneda(-diferencia)}", fg=ROJO)
        else:
            self.lbl_dif.config(text=f"Sobran {moneda(diferencia)}", fg=AMBAR)

    def confirmar(self):
        contado = self.leer()
        if contado is None:
            self.lbl_error.config(text="Escriba el efectivo contado.")
            return
        if contado < 0:
            self.lbl_error.config(text="El monto no puede ser negativo.")
            return
        diferencia = round(contado - self.datos["esperado"], 2)
        if diferencia and not messagebox.askyesno(
                "Cerrar caja",
                f"{'Faltan' if diferencia < 0 else 'Sobran'} {moneda(abs(diferencia))}.\n\n"
                "¿Cerrar el turno de todos modos? El arqueo queda guardado con esa diferencia.",
                parent=self.top):
            return
        ahora = datetime.datetime.now()
        try:
            db.ejecutar("UPDATE cajas SET fecha_cierre = ?, hora_cierre = ?, usuario_cierre = ?, esperado = ?, "
                        "monto_contado = ?, diferencia = ?, observacion = ?, estado = 'CERRADA' "
                        "WHERE id = ? AND estado = 'ABIERTA'",
                        (ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"),
                         self.caja.controlador.usuario_actual, self.datos["esperado"], contado, diferencia,
                         self.entry_obs.get().strip() or None, self.caja.caja_id))
        except sqlite3.Error as e:
            self.lbl_error.config(text=f"No se pudo cerrar la caja: {e}")
            return
        self.top.destroy()
        self.caja.refrescar()
        messagebox.showinfo("Caja cerrada",
                            f"Turno cerrado.\n\nEsperado: {moneda(self.datos['esperado'])}\n"
                            f"Contado: {moneda(contado)}\n"
                            f"Diferencia: {moneda(diferencia)}", parent=self.caja)
