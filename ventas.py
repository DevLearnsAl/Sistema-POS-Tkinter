import datetime
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import caja
import db
import factura
from estilos import (FONDO, BLANCO, BORDE, NAVY, TEXTO, TEXTO_SUAVE, VERDE, VERDE_FONDO, ROJO, FUENTE, F_NORMAL,
                     F_PEQUE, F_NEGRITA, F_SUBTITULO, F_TITULO, F_GRANDE, F_CAMPO, moneda, boton, cambiar_tipo,
                     panel, etiqueta, campo, lista, tabla, llenar_tabla, ventana_modal)
from utilidades import buscar_producto, calcular_linea, fecha_corta

TECLAS_NAVEGACION = {"Return", "KP_Enter", "Up", "Down", "Left", "Right", "Escape", "Tab", "Shift_L",
                     "Shift_R", "Control_L", "Control_R", "Alt_L", "F12"}


class StockInsuficiente(Exception):
    def __init__(self, articulo, disponible):
        super().__init__(articulo)
        self.articulo = articulo
        self.disponible = disponible


class CajaCerrada(Exception):
    """El turno se cerró entre que se abrió el cobro y se confirmó el pago."""


class Ventas(tk.Frame):
    def __init__(self, padre, controlador):
        super().__init__(padre, bg=FONDO)
        self.controlador = controlador
        self.carrito = []        # cada línea es un dict; la tabla solo la muestra
        self.caja_actual = None  # turno de caja abierto (sin turno no se puede cobrar)
        self.productos = {}      # nombre -> datos
        self.por_codigo = {}     # código de barras -> nombre
        self.nombres = []
        self.clientes = []
        self.timer_producto = None
        self.timer_cliente = None
        self.widgets()
        controlador.bind("<F12>", self._atajo_cobrar, add="+")

    # ------------------------------------------------------------------ interfaz
    def widgets(self):
        p = panel(self, "Nueva venta")
        p.place(x=16, y=16, width=720, height=186)

        etiqueta(p, "Cliente", F_PEQUE, TEXTO_SUAVE).place(x=16, y=46)
        self.entry_cliente = lista(p)
        self.entry_cliente.place(x=16, y=68, width=300, height=36)
        self.entry_cliente.bind("<KeyRelease>", self._programar_filtro_clientes)

        etiqueta(p, "Próxima factura", F_PEQUE, TEXTO_SUAVE).place(x=560, y=46)
        self.lbl_factura = etiqueta(p, "N° —", F_SUBTITULO, NAVY)
        self.lbl_factura.place(x=560, y=70)

        etiqueta(p, "Código de barras o producto", F_PEQUE, TEXTO_SUAVE).place(x=16, y=112)
        self.entry_producto = lista(p)
        self.entry_producto.place(x=16, y=134, width=300, height=36)
        self.entry_producto.bind("<KeyRelease>", self._programar_filtro_productos)
        self.entry_producto.bind("<Return>", lambda e: self.agregar_articulo())
        self.entry_producto.bind("<KP_Enter>", lambda e: self.agregar_articulo())
        self.entry_producto.bind("<<ComboboxSelected>>", lambda e: self.mostrar_info())

        etiqueta(p, "Cantidad", F_PEQUE, TEXTO_SUAVE).place(x=330, y=112)
        self.entry_cantidad = ttk.Spinbox(p, from_=1, to=9999, font=F_CAMPO)
        self.entry_cantidad.place(x=330, y=134, width=90, height=36)
        self.entry_cantidad.set(1)
        self.entry_cantidad.bind("<Return>", lambda e: self.agregar_articulo())

        self.btn_agregar = boton(p, "Agregar", self.agregar_articulo)
        self.btn_agregar.place(x=434, y=134, width=110, height=36)
        self.lbl_info = etiqueta(p, "", F_PEQUE, TEXTO_SUAVE, justify="left", anchor="nw")
        self.lbl_info.place(x=560, y=122, width=150, height=54)

        # ---- Productos de la venta ----
        c = panel(self, "Productos en la venta")
        c.place(x=16, y=214, width=720, height=376)
        columnas = [("n", "#", 40, "center"), ("codigo", "Código", 120, "center"), ("producto", "Producto", 196, "w"),
                    ("precio", "Precio", 86, "e"), ("cant", "Cant.", 56, "center"), ("iva", "IVA", 80, "e"),
                    ("total", "Total", 96, "e")]
        marco, self.tree = tabla(c, columnas)
        marco.place(x=16, y=44, width=688, height=270)
        self.tree.bind("<Delete>", lambda e: self.eliminar_articulo())
        self.tree.bind("<Double-1>", lambda e: self.editar_articulo())

        boton(c, "Cambiar cantidad", self.editar_articulo, "secundario").place(x=16, y=326, width=160, height=36)
        boton(c, "Quitar producto", self.eliminar_articulo, "secundario").place(x=186, y=326, width=150, height=36)
        boton(c, "Vaciar venta", self.vaciar, "peligro").place(x=346, y=326, width=130, height=36)
        etiqueta(c, "Supr: quitar  ·  F12: cobrar", F_PEQUE, TEXTO_SUAVE).place(x=704, y=334, anchor="ne")

        # ---- Resumen ----
        r = panel(self, "Resumen")
        r.place(x=752, y=16, width=332, height=574)
        filas = [("Artículos", "lbl_articulos"), ("Subtotal (sin IVA)", "lbl_subtotal"), ("IVA", "lbl_iva")]
        for i, (texto, atributo) in enumerate(filas):
            y = 56 + i * 34
            etiqueta(r, texto, F_NORMAL, TEXTO_SUAVE).place(x=16, y=y)
            lbl = etiqueta(r, "0", F_NEGRITA, TEXTO)
            lbl.place(x=314, y=y, anchor="ne")
            setattr(self, atributo, lbl)
        tk.Frame(r, bg=BORDE).place(x=16, y=164, width=298, height=1)
        etiqueta(r, "Total a pagar", F_NORMAL, TEXTO_SUAVE).place(x=16, y=178)
        self.label_precio_total = etiqueta(r, moneda(0), F_GRANDE, NAVY)
        self.label_precio_total.place(x=314, y=200, anchor="ne")

        self.btn_cobrar = boton(r, "Cobrar   (F12)", self.realizar_pago, "exito", (FUENTE, 14, "bold"))
        self.btn_cobrar.place(x=16, y=268, width=298, height=54)
        boton(r, "Ventas realizadas", self.ver_ventas_realizadas, "secundario").place(x=16, y=334, width=298, height=40)
        tk.Frame(r, bg=BORDE).place(x=16, y=392, width=298, height=1)
        etiqueta(r, "Los precios incluyen IVA. Los productos de la canasta básica están exentos.",
                 F_PEQUE, TEXTO_SUAVE, wraplength=296, justify="left").place(x=16, y=404)
        self.lbl_cajero = etiqueta(r, "", F_PEQUE, TEXTO_SUAVE, justify="left")
        self.lbl_cajero.place(x=16, y=520)

        self.refrescar_carrito()

    # ------------------------------------------------------------------ datos
    def al_mostrar(self):
        self.cargar_productos()
        self.cargar_clientes()
        self.actualizar_numero_factura()
        self.actualizar_caja()
        self.entry_producto.focus_set()

    def actualizar_caja(self):
        """Muestra el turno de caja y bloquea el cobro si no hay ninguno abierto."""
        fila = caja.caja_abierta()
        self.caja_actual = fila[0] if fila else None
        usuario = self.controlador.usuario_actual or "—"
        estado = f"Caja abierta por {fila[1]} ({fila[3][:5]})" if fila else "Caja cerrada · abrila para cobrar"
        self.lbl_cajero.config(text=f"Cajero: {usuario}\n{datetime.date.today():%d/%m/%Y}\n{estado}",
                               fg=TEXTO_SUAVE if fila else ROJO)

    def cargar_productos(self):
        filas = db.consultar("SELECT articulo, codigo, precio, costo, stock, iva FROM articulos "
                             "WHERE estado = 'Activo' ORDER BY articulo")
        self.productos = {f[0]: {"codigo": f[1] or "", "precio": f[2], "costo": f[3], "stock": f[4], "iva": f[5]}
                          for f in filas}
        self.por_codigo = {d["codigo"]: nombre for nombre, d in self.productos.items() if d["codigo"]}
        self.nombres = list(self.productos)
        self.entry_producto["values"] = self.nombres

    def cargar_clientes(self):
        filas = db.consultar("SELECT nombre FROM clientes WHERE activo = 1 "
                             "ORDER BY nombre = 'Consumidor final' DESC, nombre")
        self.clientes = [f[0] for f in filas]
        self.entry_cliente["values"] = self.clientes
        if not self.entry_cliente.get():
            self.entry_cliente.set("Consumidor final")

    def actualizar_numero_factura(self):
        numero = db.uno("SELECT COALESCE(MAX(factura), 0) + 1 FROM ventas")[0]
        self.lbl_factura.config(text=f"N° {numero:06d}")

    # ------------------------------------------------------------------ búsqueda
    def _programar_filtro_productos(self, event):
        if event.keysym in TECLAS_NAVEGACION:
            return
        if self.timer_producto:
            self.after_cancel(self.timer_producto)
        self.timer_producto = self.after(250, self._filtrar_productos)

    def _filtrar_productos(self):
        self.timer_producto = None
        texto = self.entry_producto.get().strip().lower()
        if not texto:
            self.entry_producto["values"] = self.nombres
        else:
            self.entry_producto["values"] = [n for n in self.nombres if texto in n.lower()
                                             or self.productos[n]["codigo"].startswith(texto)]
        self.mostrar_info()

    def _programar_filtro_clientes(self, event):
        if event.keysym in TECLAS_NAVEGACION:
            return
        if self.timer_cliente:
            self.after_cancel(self.timer_cliente)
        self.timer_cliente = self.after(250, self._filtrar_clientes)

    def _filtrar_clientes(self):
        self.timer_cliente = None
        texto = self.entry_cliente.get().strip().lower()
        self.entry_cliente["values"] = [c for c in self.clientes if texto in c.lower()] if texto else self.clientes

    def buscar_producto(self, texto, parcial=True):
        return buscar_producto(texto, self.nombres, self.por_codigo, parcial)

    def mostrar_info(self):
        nombre = self.buscar_producto(self.entry_producto.get(), parcial=False)
        if not nombre:
            self.lbl_info.config(text="")
            return
        d = self.productos[nombre]
        iva = f"IVA {d['iva']:.0f} %" if d["iva"] else "Exento de IVA"
        self.lbl_info.config(text=f"Precio {moneda(d['precio'])}\nDisponible: {d['stock']}\n{iva}")

    # ------------------------------------------------------------------ carrito
    def aviso(self, mensaje):
        messagebox.showwarning("Ventas", mensaje, parent=self)

    @staticmethod
    def _recalcular(linea):
        linea["total"], linea["iva"] = calcular_linea(linea["precio"], linea["cantidad"], linea["tasa"])

    def agregar_articulo(self):
        texto = self.entry_producto.get()
        if not texto.strip():
            self.aviso("Escriba el código de barras o elija un producto.")
            return
        nombre = self.buscar_producto(texto)
        if not nombre:
            self.aviso(f"No se encontró ningún producto activo con «{texto.strip()}».")
            return
        cantidad_texto = self.entry_cantidad.get().strip()
        if not cantidad_texto.isdigit() or int(cantidad_texto) <= 0:
            self.aviso("La cantidad debe ser un número entero mayor que cero.")
            return
        cantidad = int(cantidad_texto)

        fila = db.uno("SELECT codigo, precio, costo, stock, iva, estado FROM articulos WHERE articulo = ?", (nombre,))
        if fila is None or fila[5] != "Activo":
            self.aviso("Ese producto ya no está disponible para la venta.")
            self.cargar_productos()
            return
        codigo, precio, costo, stock, tasa, _ = fila

        # El stock se valida contra lo que ya hay de ese producto en la venta.
        en_venta = sum(l["cantidad"] for l in self.carrito if l["articulo"] == nombre)
        if en_venta + cantidad > stock:
            if en_venta:
                self.aviso(f"Stock insuficiente de «{nombre}».\n"
                           f"Hay {stock} en inventario y ya agregó {en_venta} a esta venta.")
            else:
                self.aviso(f"Stock insuficiente de «{nombre}». Disponible: {stock}.")
            return

        linea = next((l for l in self.carrito if l["articulo"] == nombre), None)
        if linea:
            linea["cantidad"] += cantidad
        else:
            linea = {"codigo": codigo or "", "articulo": nombre, "precio": precio, "costo": costo, "tasa": tasa,
                     "cantidad": cantidad}
            self.carrito.append(linea)
        self._recalcular(linea)
        self.refrescar_carrito(seleccionar=self.carrito.index(linea))

        self.entry_producto.set("")
        self.entry_producto["values"] = self.nombres
        self.entry_cantidad.set(1)
        self.lbl_info.config(text="")
        self.entry_producto.focus_set()

    def totales(self):
        total = round(sum(l["total"] for l in self.carrito), 2)
        iva = round(sum(l["iva"] for l in self.carrito), 2)
        return {"articulos": sum(l["cantidad"] for l in self.carrito), "total": total, "iva": iva,
                "subtotal": round(total - iva, 2)}

    def refrescar_carrito(self, seleccionar=None):
        filas = [(i + 1, l["codigo"], l["articulo"], moneda(l["precio"]), l["cantidad"], moneda(l["iva"]),
                  moneda(l["total"])) for i, l in enumerate(self.carrito)]
        llenar_tabla(self.tree, filas)
        if seleccionar is not None and self.tree.get_children():
            iid = self.tree.get_children()[seleccionar]
            self.tree.selection_set(iid)
            self.tree.see(iid)
        t = self.totales()
        self.lbl_articulos.config(text=str(t["articulos"]))
        self.lbl_subtotal.config(text=moneda(t["subtotal"]))
        self.lbl_iva.config(text=moneda(t["iva"]))
        self.label_precio_total.config(text=moneda(t["total"]))

    def _linea_seleccionada(self, accion):
        seleccion = self.tree.selection()
        if not seleccion:
            self.aviso(f"Seleccione en la tabla el producto que quiere {accion}.")
            return None
        return self.tree.index(seleccion[0])

    def editar_articulo(self):
        i = self._linea_seleccionada("cambiar")
        if i is None:
            return
        linea = self.carrito[i]
        nueva = simpledialog.askinteger("Cambiar cantidad", f"Nueva cantidad de «{linea['articulo']}»:",
                                        initialvalue=linea["cantidad"], minvalue=1, maxvalue=9999, parent=self)
        if nueva is None:
            return
        fila = db.uno("SELECT stock FROM articulos WHERE articulo = ?", (linea["articulo"],))
        stock = fila[0] if fila else 0
        if nueva > stock:
            self.aviso(f"Stock insuficiente de «{linea['articulo']}». Disponible: {stock}.")
            return
        linea["cantidad"] = nueva
        self._recalcular(linea)
        self.refrescar_carrito(seleccionar=i)

    def eliminar_articulo(self):
        i = self._linea_seleccionada("quitar")
        if i is None:
            return
        del self.carrito[i]
        self.refrescar_carrito()

    def vaciar(self, confirmar=True):
        if not self.carrito:
            return
        if confirmar and not messagebox.askyesno("Vaciar venta", "¿Quitar todos los productos de esta venta?",
                                                 parent=self):
            return
        self.carrito.clear()
        self.refrescar_carrito()

    # ------------------------------------------------------------------ cobro
    def _atajo_cobrar(self, event=None):
        if self.controlador.usuario_actual and getattr(self.master, "actual", None) is Ventas \
                and not self.grab_current():
            self.realizar_pago()

    def realizar_pago(self):
        if not self.carrito:
            self.aviso("Agregue al menos un producto antes de cobrar.")
            return
        self.actualizar_caja()
        if not self.caja_actual:
            # Sin turno abierto no hay dónde registrar el efectivo, así que se
            # ofrece abrirlo y, si se abre, el cobro sigue solo.
            if messagebox.askyesno("Caja cerrada",
                                   "No hay un turno de caja abierto y la venta no se puede cobrar.\n\n"
                                   "¿Quiere abrir la caja ahora?", parent=self):
                caja.VentanaAbrirCaja(self, al_abrir=self.realizar_pago)
            return
        VentanaCobro(self, self.totales()["total"])

    def procesar_pago(self, recibido, metodo):
        """Guarda la venta en una sola transacción. Devuelve los datos para el recibo, o None si no se guardó."""
        if not self.carrito:
            return None
        usuario = self.controlador.usuario_actual or "—"
        cliente = self.entry_cliente.get().strip() or "Consumidor final"
        ahora = datetime.datetime.now()
        fecha, hora = ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S")
        t = self.totales()
        try:
            with db.conectar() as conn:
                # BEGIN IMMEDIATE bloquea la base mientras se asigna el número y se descuenta
                # el stock: dos cajas no pueden sacar el mismo número de factura.
                conn.execute("BEGIN IMMEDIATE")
                # El turno se vuelve a leer adentro de la transacción: pudo cerrarse
                # mientras la ventana de cobro estaba abierta.
                fila_caja = conn.execute("SELECT id FROM cajas WHERE estado = 'ABIERTA'").fetchone()
                if fila_caja is None:
                    raise CajaCerrada
                caja_id = fila_caja[0]
                for l in self.carrito:
                    fila = conn.execute("SELECT stock, estado FROM articulos WHERE articulo = ?",
                                        (l["articulo"],)).fetchone()
                    if fila is None or fila[1] != "Activo" or fila[0] < l["cantidad"]:
                        raise StockInsuficiente(l["articulo"], fila[0] if fila else 0)
                numero = conn.execute("SELECT COALESCE(MAX(factura), 0) + 1 FROM ventas").fetchone()[0]
                for l in self.carrito:
                    conn.execute(
                        "INSERT INTO ventas (factura, cliente, codigo, articulo, precio, cantidad, total, iva, costo, "
                        "fecha, hora, usuario, caja_id, metodo_pago, recibido, estado) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'EMITIDA')",
                        (numero, cliente, l["codigo"], l["articulo"], l["precio"], l["cantidad"], l["total"],
                         l["iva"], round(l["costo"] * l["cantidad"], 2), fecha, hora, usuario, caja_id, metodo,
                         recibido))
                    conn.execute("UPDATE articulos SET stock = stock - ? WHERE articulo = ?",
                                 (l["cantidad"], l["articulo"]))
        except CajaCerrada:
            messagebox.showwarning("Caja cerrada", "El turno de caja se cerró. Abrí la caja para poder cobrar.\n"
                                                   "La venta no se guardó.", parent=self)
            self.actualizar_caja()
            return None
        except StockInsuficiente as e:
            messagebox.showwarning("Stock insuficiente",
                                   f"No hay suficiente «{e.articulo}» (disponible: {e.disponible}).\n"
                                   "La venta no se guardó. Revise las cantidades.", parent=self)
            self.cargar_productos()
            return None
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"No se pudo registrar la venta: {e}", parent=self)
            return None

        datos = {"numero": numero, "cliente": cliente, "fecha": fecha, "hora": hora, "usuario": usuario,
                 "metodo": metodo, "recibido": recibido, "estado": "EMITIDA",
                 "lineas": [dict(l) for l in self.carrito]}
        # La factura se genera después de guardar: si el PDF falla, la venta igual queda registrada.
        try:
            ruta = factura.generar_pdf(datos)
        except Exception as e:
            print("No se pudo generar la factura:", e)
            ruta = None
        cambio = round(recibido - t["total"], 2) if metodo == "Efectivo" else 0.0

        self.carrito.clear()
        self.refrescar_carrito()
        self.entry_cliente.set("Consumidor final")
        self.actualizar_numero_factura()
        self.cargar_productos()
        return numero, t["total"], recibido, cambio, metodo, ruta

    def ver_ventas_realizadas(self):
        HistorialVentas(self)


class VentanaCobro:
    """Ventana de cobro: método de pago, monto recibido y cambio en vivo."""

    BILLETES = [100, 200, 500, 1000]

    def __init__(self, ventas, total):
        self.ventas = ventas
        self.total = total
        self.metodo = "Efectivo"
        top = self.top = ventana_modal(ventas, "Cobrar venta", 440, 520)

        etiqueta(top, "Cobrar venta", F_TITULO, TEXTO).place(x=28, y=20)
        etiqueta(top, "Total a pagar", F_NORMAL, TEXTO_SUAVE).place(x=28, y=72)
        etiqueta(top, moneda(total), F_GRANDE, NAVY).place(x=28, y=94)

        etiqueta(top, "Método de pago", F_NEGRITA, TEXTO).place(x=28, y=162)
        self.btn_efectivo = boton(top, "Efectivo", lambda: self.elegir("Efectivo"), "primario")
        self.btn_efectivo.place(x=28, y=188, width=188, height=38)
        self.btn_tarjeta = boton(top, "Tarjeta", lambda: self.elegir("Tarjeta"), "secundario")
        self.btn_tarjeta.place(x=224, y=188, width=188, height=38)

        etiqueta(top, "Monto recibido", F_NEGRITA, TEXTO).place(x=28, y=242)
        # Con una variable vigilada, el cambio se recalcula con cualquier modificación
        # del campo: teclado, pegar con el mouse o los botones de billetes.
        self.monto = tk.StringVar()
        self.entry_monto = ttk.Entry(top, font=(FUENTE, 16), textvariable=self.monto)
        self.entry_monto.place(x=28, y=268, width=384, height=44)
        self.entry_monto.bind("<Return>", lambda e: self.confirmar())
        self.monto.trace_add("write", lambda *args: self.actualizar_cambio())

        self.rapidos = []
        opciones = [("Exacto", total)] + [(f"C$ {b:,}", b) for b in self.BILLETES]
        for i, (texto, valor) in enumerate(opciones):
            b = boton(top, texto, lambda v=valor: self.poner_monto(v), "secundario", F_PEQUE)
            b.place(x=28 + i * 78, y=322, width=72, height=34)
            self.rapidos.append(b)

        self.lbl_cambio = etiqueta(top, "", F_SUBTITULO, VERDE)
        self.lbl_cambio.place(x=28, y=374)

        boton(top, "Cancelar", top.destroy, "secundario").place(x=28, y=446, width=150, height=48)
        self.btn_confirmar = boton(top, "Confirmar pago", self.confirmar, "exito", (FUENTE, 13, "bold"))
        self.btn_confirmar.place(x=190, y=446, width=222, height=48)
        top.bind("<Escape>", lambda e: top.destroy())
        self.entry_monto.focus_set()
        self.actualizar_cambio()

    def elegir(self, metodo):
        self.metodo = metodo
        tarjeta = metodo == "Tarjeta"
        cambiar_tipo(self.btn_efectivo, "secundario" if tarjeta else "primario")
        cambiar_tipo(self.btn_tarjeta, "primario" if tarjeta else "secundario")
        self.entry_monto.config(state="normal")
        self.entry_monto.delete(0, "end")
        if tarjeta:
            self.entry_monto.insert(0, f"{self.total:.2f}")
            self.entry_monto.config(state="disabled")
        for b in self.rapidos:
            b.config(state="disabled" if tarjeta else "normal")
        if not tarjeta:
            self.entry_monto.focus_set()
        self.actualizar_cambio()

    def poner_monto(self, valor):
        self.entry_monto.delete(0, "end")
        self.entry_monto.insert(0, f"{valor:.2f}")
        self.actualizar_cambio()

    def leer_monto(self):
        texto = self.entry_monto.get().replace("C$", "").replace(",", "").strip()
        try:
            return float(texto)
        except ValueError:
            return None

    def actualizar_cambio(self):
        if self.metodo == "Tarjeta":
            self.lbl_cambio.config(text=f"Se cobrarán {moneda(self.total)} con tarjeta", fg=NAVY)
            return
        monto = self.leer_monto()
        if monto is None:
            self.lbl_cambio.config(text="")
        elif monto >= self.total - 0.004:
            self.lbl_cambio.config(text=f"Cambio: {moneda(monto - self.total)}", fg=VERDE)
        else:
            self.lbl_cambio.config(text=f"Falta: {moneda(self.total - monto)}", fg=ROJO)

    def confirmar(self):
        if self.metodo == "Tarjeta":
            recibido = self.total
        else:
            monto = self.leer_monto()
            if monto is None:
                self.lbl_cambio.config(text="Escriba el monto recibido.", fg=ROJO)
                return
            if monto < self.total - 0.004:
                self.lbl_cambio.config(text=f"El monto no alcanza. Falta: {moneda(self.total - monto)}", fg=ROJO)
                return
            recibido = round(monto, 2)
        resultado = self.ventas.procesar_pago(recibido, self.metodo)
        self.top.destroy()
        if resultado:
            VentanaVentaExitosa(self.ventas, *resultado)


class VentanaVentaExitosa:
    def __init__(self, ventas, numero, total, recibido, cambio, metodo, ruta):
        self.ruta = ruta
        top = self.top = ventana_modal(ventas, "Venta registrada", 420, 330)
        icono = tk.Canvas(top, width=64, height=64, bg=BLANCO, highlightthickness=0)
        icono.place(x=178, y=22)
        icono.create_oval(2, 2, 62, 62, fill=VERDE_FONDO, outline="")
        icono.create_line(18, 34, 28, 44, 46, 22, fill=VERDE, width=5, capstyle="round", joinstyle="round")

        etiqueta(top, "Venta registrada", F_TITULO, TEXTO).place(relx=0.5, y=96, anchor="n")
        etiqueta(top, f"Factura N° {numero:06d}  ·  Total {moneda(total)}", F_NORMAL, TEXTO_SUAVE).place(
            relx=0.5, y=138, anchor="n")
        if metodo == "Efectivo":
            etiqueta(top, f"Cambio: {moneda(cambio)}", (FUENTE, 20, "bold"), VERDE).place(relx=0.5, y=172, anchor="n")
        else:
            etiqueta(top, "Pagado con tarjeta", F_SUBTITULO, NAVY).place(relx=0.5, y=178, anchor="n")

        self.btn_factura = boton(top, "Ver factura (PDF)", self.abrir_factura, "primario")
        self.btn_factura.place(x=28, y=252, width=176, height=46)
        self.btn_nueva = boton(top, "Nueva venta", top.destroy, "secundario")
        self.btn_nueva.place(x=216, y=252, width=176, height=46)
        if not ruta:
            self.btn_factura.config(state="disabled")
            etiqueta(top, "No se pudo generar el PDF de la factura.", F_PEQUE, ROJO).place(relx=0.5, y=222, anchor="n")
        top.bind("<Return>", lambda e: top.destroy())
        top.bind("<Escape>", lambda e: top.destroy())

    def abrir_factura(self):
        if self.ruta:
            factura.abrir(self.ruta)
        self.top.destroy()


class HistorialVentas:
    """Ventas realizadas: filtros, reimpresión y anulación de facturas."""

    PERIODOS = ["Todas", "Hoy", "Últimos 7 días", "Este mes"]
    ESTADOS = ["Todos", "Emitidas", "Anuladas"]

    def __init__(self, ventas):
        self.ventas = ventas
        top = self.top = ventana_modal(ventas, "Ventas realizadas", 1040, 600, bg=FONDO)
        etiqueta(top, "Ventas realizadas", F_TITULO, TEXTO, bg=FONDO).place(x=24, y=16)

        p = panel(top)
        p.place(x=24, y=64, width=992, height=74)
        etiqueta(p, "Factura", F_PEQUE, TEXTO_SUAVE).place(x=16, y=6)
        self.entry_factura = campo(p)
        self.entry_factura.place(x=16, y=28, width=110, height=34)
        etiqueta(p, "Cliente", F_PEQUE, TEXTO_SUAVE).place(x=140, y=6)
        self.entry_cliente = campo(p)
        self.entry_cliente.place(x=140, y=28, width=220, height=34)
        etiqueta(p, "Período", F_PEQUE, TEXTO_SUAVE).place(x=374, y=6)
        self.combo_periodo = lista(p, values=self.PERIODOS, state="readonly")
        self.combo_periodo.set("Todas")
        self.combo_periodo.place(x=374, y=28, width=170, height=34)
        etiqueta(p, "Estado", F_PEQUE, TEXTO_SUAVE).place(x=558, y=6)
        self.combo_estado = lista(p, values=self.ESTADOS, state="readonly")
        self.combo_estado.set("Todos")
        self.combo_estado.place(x=558, y=28, width=140, height=34)
        boton(p, "Buscar", self.buscar).place(x=712, y=28, width=120, height=34)
        boton(p, "Limpiar", self.limpiar, "secundario").place(x=842, y=28, width=130, height=34)
        for w in (self.entry_factura, self.entry_cliente):
            w.bind("<Return>", lambda e: self.buscar())
        for w in (self.combo_periodo, self.combo_estado):
            w.bind("<<ComboboxSelected>>", lambda e: self.buscar())

        columnas = [("factura", "Factura", 80, "center"), ("fecha", "Fecha", 100, "center"),
                    ("hora", "Hora", 70, "center"), ("cliente", "Cliente", 200, "w"),
                    ("articulos", "Artículos", 80, "center"), ("total", "Total", 120, "e"),
                    ("pago", "Pago", 90, "center"), ("cajero", "Cajero", 100, "center"),
                    ("estado", "Estado", 110, "center")]
        marco, self.tree = tabla(top, columnas)
        marco.place(x=24, y=150, width=992, height=356)
        self.tree.bind("<Double-1>", lambda e: self.ver_factura())

        self.lbl_resumen = etiqueta(top, "", F_NEGRITA, TEXTO, bg=FONDO)
        self.lbl_resumen.place(x=24, y=528)
        boton(top, "Ver factura", self.ver_factura).place(x=592, y=520, width=130, height=42)
        self.btn_anular = boton(top, "Anular factura", self.anular, "peligro")
        self.btn_anular.place(x=732, y=520, width=150, height=42)
        if not ventas.controlador.puede("anular"):
            # Anular devuelve mercadería y plata: queda para el administrador.
            self.btn_anular.config(state="disabled")
            etiqueta(top, "Anular facturas requiere un administrador.", F_PEQUE, TEXTO_SUAVE, bg=FONDO).place(
                x=592, y=568)
        boton(top, "Cerrar", top.destroy, "secundario").place(x=892, y=520, width=124, height=42)
        top.bind("<Escape>", lambda e: top.destroy())
        self.buscar()

    def limpiar(self):
        self.entry_factura.delete(0, "end")
        self.entry_cliente.delete(0, "end")
        self.combo_periodo.set("Todas")
        self.combo_estado.set("Todos")
        self.buscar()

    def buscar(self):
        # "WHERE 1 = 1" permite agregar cada filtro con "AND ..." sin importar cuál va primero.
        condiciones, parametros = ["1 = 1"], []
        numero = self.entry_factura.get().strip()
        if numero:
            if not numero.isdigit():
                messagebox.showwarning("Ventas realizadas", "El número de factura debe ser un número.", parent=self.top)
                return
            condiciones.append("factura = ?")
            parametros.append(int(numero))
        cliente = self.entry_cliente.get().strip()
        if cliente:
            condiciones.append("cliente LIKE ?")
            parametros.append(f"%{cliente}%")
        hoy = datetime.date.today()
        desde = {"Hoy": hoy, "Últimos 7 días": hoy - datetime.timedelta(days=6),
                 "Este mes": hoy.replace(day=1)}.get(self.combo_periodo.get())
        if desde:
            condiciones.append("fecha >= ?")
            parametros.append(desde.isoformat())
        estado = {"Emitidas": "EMITIDA", "Anuladas": "ANULADA"}.get(self.combo_estado.get())
        if estado:
            condiciones.append("estado = ?")
            parametros.append(estado)

        filas = db.consultar(
            "SELECT factura, fecha, hora, cliente, SUM(cantidad), SUM(total), metodo_pago, usuario, estado "
            f"FROM ventas WHERE {' AND '.join(condiciones)} GROUP BY factura ORDER BY factura DESC", parametros)
        vista = [(f"{f[0]:06d}", fecha_corta(f[1]), f[2][:5], f[3], f[4], moneda(f[5]), f[6], f[7] or "—",
                  "Anulada" if f[8] == "ANULADA" else "Emitida") for f in filas]
        llenar_tabla(self.tree, vista, lambda fila: ["anulada"] if fila[8] == "Anulada" else [])

        emitidas = [f for f in filas if f[8] == "EMITIDA"]
        anuladas = len(filas) - len(emitidas)
        texto = f"{len(filas)} factura{'s' if len(filas) != 1 else ''}  ·  Vendido: {moneda(sum(f[5] for f in emitidas))}"
        if anuladas:
            texto += f"  ·  {anuladas} anulada{'s' if anuladas != 1 else ''}"
        self.lbl_resumen.config(text=texto)

    def _seleccion(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Ventas realizadas", "Seleccione una factura de la lista.", parent=self.top)
            return None, None
        valores = self.tree.item(seleccion[0], "values")
        return int(str(valores[0])), valores[8]

    def ver_factura(self):
        numero, _ = self._seleccion()
        if numero is None:
            return
        try:
            ruta = factura.generar_pdf(factura.datos_desde_bd(numero))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar la factura: {e}", parent=self.top)
            return
        factura.abrir(ruta)

    def anular(self):
        if not self.ventas.controlador.puede("anular"):
            messagebox.showwarning("Ventas realizadas", "Solo un administrador puede anular facturas.",
                                   parent=self.top)
            return
        numero, estado = self._seleccion()
        if numero is None:
            return
        if estado == "Anulada":
            messagebox.showinfo("Ventas realizadas", "Esa factura ya está anulada.", parent=self.top)
            return
        if not messagebox.askyesno("Anular factura",
                                   f"¿Anular la factura N° {numero:06d}?\n\nLos productos vuelven al inventario. "
                                   "La factura no se borra: queda registrada como anulada.", parent=self.top):
            return
        try:
            with db.conectar() as conn:
                conn.execute("BEGIN IMMEDIATE")
                lineas = conn.execute("SELECT codigo, articulo, cantidad FROM ventas "
                                      "WHERE factura = ? AND estado = 'EMITIDA'", (numero,)).fetchall()
                conn.execute("UPDATE ventas SET estado = 'ANULADA' WHERE factura = ?", (numero,))
                for codigo, articulo, cantidad in lineas:
                    # Se busca por código y, si el producto no tiene, por nombre.
                    conn.execute("UPDATE articulos SET stock = stock + ? "
                                 "WHERE (codigo = ? AND codigo <> '') OR articulo = ?", (cantidad, codigo or "", articulo))
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"No se pudo anular la factura: {e}", parent=self.top)
            return
        messagebox.showinfo("Factura anulada", f"La factura N° {numero:06d} quedó anulada y el stock se devolvió al "
                                               "inventario.", parent=self.top)
        self.buscar()
        self.ventas.cargar_productos()
