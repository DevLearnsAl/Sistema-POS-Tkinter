import os
import sqlite3
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

db_name = "database.db"
COLOR_FONDO = "#C6D9E3"


class Ventas(tk.Frame):
    def __init__(self, padre):
        super().__init__(padre)
        self.numero_factura = self.obtener_numero_factura_actual()
        self.productos_seleccionados = []
        self.products = []
        self.clientes = []
        self.timer_producto = None
        self.timer_cliente = None
        self.widgets()
        self.cargar_productos()
        self.cargar_clientes()

    def al_mostrar(self):
        self.cargar_productos()
        self.cargar_clientes()

    # ---------------- Interfaz (video 6) ----------------
    def widgets(self):
        labelframe = tk.LabelFrame(self, font="sans 12 bold", bg=COLOR_FONDO)
        labelframe.place(x=25, y=30, width=1045, height=180)

        label_cliente = tk.Label(labelframe, text="Cliente: ", font="sans 14 bold", bg=COLOR_FONDO)
        label_cliente.place(x=10, y=11)
        self.entry_cliente = ttk.Combobox(labelframe, font="sans 14 bold")
        self.entry_cliente.place(x=120, y=8, width=260, height=40)
        self.entry_cliente.bind("<KeyRelease>", self.filtrar_clientes)

        label_producto = tk.Label(labelframe, text="Producto: ", font="sans 14 bold", bg=COLOR_FONDO)
        label_producto.place(x=10, y=70)
        self.entry_producto = ttk.Combobox(labelframe, font="sans 14 bold")
        self.entry_producto.place(x=120, y=60, width=260, height=40)
        self.entry_producto.bind("<KeyRelease>", self.filtrar_productos)
        self.entry_producto.bind("<<ComboboxSelected>>", self.actualizar_stock)

        label_cantidad = tk.Label(labelframe, text="Cantidad: ", font="sans 14 bold", bg=COLOR_FONDO)
        label_cantidad.place(x=500, y=11)
        self.entry_cantidad = ttk.Entry(labelframe, font="sans 14 bold")
        self.entry_cantidad.place(x=610, y=8, width=100, height=40)

        self.label_stock = tk.Label(labelframe, text="Stock: ", font="sans 14 bold", bg=COLOR_FONDO)
        self.label_stock.place(x=500, y=70)

        label_factura = tk.Label(labelframe, text="Número de factura", font="sans 14 bold", bg=COLOR_FONDO)
        label_factura.place(x=750, y=11)
        self.label_numero_factura = tk.Label(labelframe, text=f"{self.numero_factura}", font="sans 14 bold",
                                             bg=COLOR_FONDO)
        self.label_numero_factura.place(x=950, y=11)

        boton_agregar = tk.Button(labelframe, text="Agregar artículo", font="sans 14 bold",
                                  command=self.agregar_articulo)
        boton_agregar.place(x=90, y=120, width=200, height=40)

        boton_eliminar = tk.Button(labelframe, text="Eliminar artículo", font="sans 14 bold",
                                   command=self.eliminar_articulo)
        boton_eliminar.place(x=310, y=120, width=200, height=40)

        boton_editar = tk.Button(labelframe, text="Editar artículo", font="sans 14 bold",
                                 command=self.editar_articulo)
        boton_editar.place(x=530, y=120, width=200, height=40)

        boton_limpiar = tk.Button(labelframe, text="Limpiar lista", font="sans 14 bold",
                                  command=self.limpiar_lista)
        boton_limpiar.place(x=750, y=120, width=200, height=40)

        # ---- Tabla del carrito ----
        treFrame = tk.Frame(self, bg="white")
        treFrame.place(x=70, y=220, width=980, height=300)

        scrol_y = ttk.Scrollbar(treFrame)
        scrol_y.pack(side="right", fill="y")

        # Corrección (guía, video 6, [0:37:54]): sin orient="horizontal" la barra sale vertical.
        scrol_x = ttk.Scrollbar(treFrame, orient="horizontal")
        scrol_x.pack(side="bottom", fill="x")

        # Corrección (guía, video 6, [0:35:49]): los nombres de columns tienen que ser
        # exactamente los mismos que se usan en heading() y column().
        self.tre = ttk.Treeview(treFrame, yscrollcommand=scrol_y.set, xscrollcommand=scrol_x.set, height=40,
                                columns=("Factura", "Cliente", "Producto", "Precio", "Cantidad", "Total"),
                                show="headings")
        self.tre.pack(expand=True, fill="both")

        scrol_y.config(command=self.tre.yview)
        scrol_x.config(command=self.tre.xview)

        self.tre.heading("Factura", text="Factura")
        self.tre.heading("Cliente", text="Cliente")
        self.tre.heading("Producto", text="Producto")
        self.tre.heading("Precio", text="Precio")
        self.tre.heading("Cantidad", text="Cantidad")
        self.tre.heading("Total", text="Total")

        self.tre.column("Factura", width=70, anchor="center")
        self.tre.column("Cliente", width=250, anchor="center")
        self.tre.column("Producto", width=250, anchor="center")
        self.tre.column("Precio", width=120, anchor="center")
        self.tre.column("Cantidad", width=120, anchor="center")
        self.tre.column("Total", width=150, anchor="center")

        # Corrección (guía, video 6): C$ en vez de $, y dos decimales.
        self.label_precio_total = tk.Label(self, text="Precio a pagar: C$ 0.00", font="sans 18 bold",
                                           bg=COLOR_FONDO)
        self.label_precio_total.place(x=680, y=550)

        # Corrección (guía, video 7, [1:48:54]): el botón Pagar necesita su command.
        boton_pagar = tk.Button(self, text="Pagar", font="sans 14 bold", command=self.realizar_pago)
        boton_pagar.place(x=70, y=550, width=180, height=40)

        boton_ver_ventas = tk.Button(self, text="Ver ventas realizadas", font="sans 14 bold",
                                     command=self.ver_ventas_realizadas)
        boton_ver_ventas.place(x=290, y=550, width=280, height=40)

    # ---------------- Carga de datos (video 7) ----------------
    def obtener_numero_factura_actual(self):
        # Igual que en el curso: la siguiente factura es la mayor + 1.
        # Funciona con una sola caja; con dos cajas sobre la misma base podrían
        # salir números repetidos (queda para después del curso).
        try:
            conn = sqlite3.connect(db_name)
            c = conn.cursor()
            c.execute("SELECT MAX(factura) FROM ventas")
            last_invoice_number = c.fetchone()[0]
            conn.close()
            return last_invoice_number + 1 if last_invoice_number is not None else 1
        except sqlite3.Error as e:
            print("Error obteniendo el número de factura actual:", e)
            return 1

    def cargar_productos(self):
        try:
            conn = sqlite3.connect(db_name)
            c = conn.cursor()
            # Corrección extra: solo se venden productos activos. "Inactivo" significa
            # que ya no se vende (video 1), pero en el video igual aparecían aquí.
            c.execute("SELECT articulo FROM articulos WHERE estado = 'Activo'")
            self.products = [product[0] for product in c.fetchall()]
            self.entry_producto["values"] = self.products
            conn.close()
        except sqlite3.Error as e:
            print("Error cargando productos:", e)

    def cargar_clientes(self):
        try:
            conn = sqlite3.connect(db_name)
            c = conn.cursor()
            c.execute("SELECT nombre FROM clientes")
            self.clientes = [cliente[0] for cliente in c.fetchall()]
            self.entry_cliente["values"] = self.clientes
            conn.close()
        except sqlite3.Error as e:
            print("Error cargando clientes:", e)

        # Corrección (guía, video 10): "Consumidor final" por defecto.
        if not self.entry_cliente.get():
            self.entry_cliente.set("Consumidor final")

    # ---------------- Filtros mientras se escribe ----------------
    # Corrección (guía, video 5): self.after en vez de threading.Timer.
    def filtrar_productos(self, event):
        if self.timer_producto:
            self.after_cancel(self.timer_producto)
        self.timer_producto = self.after(500, self.filter_products)

    def filter_products(self):
        self.timer_producto = None
        typed = self.entry_producto.get()

        if typed == "":
            data = self.products
        else:
            data = [item for item in self.products if typed.lower() in item.lower()]

        if data:
            self.entry_producto["values"] = data
            self.entry_producto.event_generate("<Down>")
        else:
            self.entry_producto["values"] = ["No se encontraron resultados"]
            self.entry_producto.event_generate("<Down>")
            self.entry_producto.delete(0, tk.END)

    def filtrar_clientes(self, event):
        if self.timer_cliente:
            self.after_cancel(self.timer_cliente)
        self.timer_cliente = self.after(500, self.filter_clientes)

    def filter_clientes(self):
        self.timer_cliente = None
        typed = self.entry_cliente.get()

        if typed == "":
            data = self.clientes
        else:
            data = [item for item in self.clientes if typed.lower() in item.lower()]

        if data:
            self.entry_cliente["values"] = data
            self.entry_cliente.event_generate("<Down>")
        else:
            self.entry_cliente["values"] = ["No se encontraron resultados"]
            self.entry_cliente.event_generate("<Down>")
            self.entry_cliente.delete(0, tk.END)

    # ---------------- Carrito ----------------
    def agregar_articulo(self):
        cliente = self.entry_cliente.get()
        producto = self.entry_producto.get()
        cantidad = self.entry_cantidad.get()

        if not cliente:
            messagebox.showerror("Error", "Por favor seleccione un cliente.")
            return

        if not producto:
            messagebox.showerror("Error", "Por favor seleccione un producto.")
            return

        if not cantidad.isdigit() or int(cantidad) <= 0:
            messagebox.showerror("Error", "Por favor ingrese una cantidad válida.")
            return

        cantidad = int(cantidad)

        try:
            conn = sqlite3.connect(db_name)
            c = conn.cursor()
            c.execute("SELECT precio, costo, stock FROM articulos WHERE articulo = ? AND estado = 'Activo'",
                      (producto,))
            resultado = c.fetchone()
            conn.close()

            if resultado is None:
                messagebox.showerror("Error", "Producto no encontrado.")
                return

            precio, costo, stock = resultado

            if cantidad > stock:
                messagebox.showerror("Error", f"Stock insuficiente. Solo hay {stock} unidades disponibles.")
                return

            # Corrección (guía, video 7): {:,.2f} en vez de {:,.0f}. Con .0f un producto
            # de C$ 12.50 aparecía y se cobraba como C$ 12.
            total = precio * cantidad
            total_cop = "{:,.2f}".format(total)

            self.tre.insert("", "end", values=(self.numero_factura, cliente, producto,
                                               "{:,.2f}".format(precio), cantidad, total_cop))
            # Corrección (guía, video 7, [1:39:36]): una sola tupla dentro del append.
            self.productos_seleccionados.append((self.numero_factura, cliente, producto, precio,
                                                 cantidad, total_cop, costo))

            self.entry_producto.set("")
            self.entry_cantidad.delete(0, "end")
            self.label_stock.config(text="Stock: ")
        except sqlite3.Error as e:
            print("Error al agregar artículo:", e)

        self.calcular_precio_total()

    def calcular_precio_total(self):
        # Corrección (guía, video 7, [1:43:44]): str() antes de replace(), porque el
        # Treeview a veces devuelve los valores como número y no como texto.
        total_pagar = sum(float(str(self.tre.item(item)["values"][-1]).replace(",", ""))
                          for item in self.tre.get_children())
        total_pagar_cop = "{:,.2f}".format(total_pagar)
        self.label_precio_total.config(text=f"Precio a pagar: C$ {total_pagar_cop}")

    def actualizar_stock(self, event=None):
        producto_seleccionado = self.entry_producto.get()

        try:
            conn = sqlite3.connect(db_name)
            c = conn.cursor()
            c.execute("SELECT stock FROM articulos WHERE articulo = ?", (producto_seleccionado,))
            resultado = c.fetchone()
            conn.close()

            # Corrección extra: si se elige "No se encontraron resultados", fetchone()
            # devuelve None y en el video el programa fallaba al hacer stock[0].
            if resultado:
                self.label_stock.config(text=f"Stock: {resultado[0]}")
            else:
                self.label_stock.config(text="Stock: ")
        except sqlite3.Error as e:
            print("Error al obtener el stock del producto:", e)

    def eliminar_articulo(self):
        item_seleccionado = self.tre.selection()
        if not item_seleccionado:
            messagebox.showerror("Error", "No hay ningún artículo seleccionado.")
            return

        item_id = item_seleccionado[0]
        # Corrección extra: en el video se borraban de la lista todos los productos con
        # el mismo nombre. Si agregaste Coca-Cola dos veces y eliminabas una línea, la
        # tabla mostraba una pero se cobraban cero. La fila de la tabla y la de la lista
        # están en la misma posición, así que se borra por posición.
        posicion = self.tre.index(item_id)
        self.tre.delete(item_id)
        del self.productos_seleccionados[posicion]

        self.calcular_precio_total()

    def editar_articulo(self):
        selected_item = self.tre.selection()
        if not selected_item:
            messagebox.showerror("Error", "Por favor seleccione un artículo para editar.")
            return

        item_values = self.tre.item(selected_item[0], "values")
        if not item_values:
            return

        posicion = self.tre.index(selected_item[0])
        factura, cliente, producto, precio_anterior, cantidad_anterior, total_anterior, costo = \
            self.productos_seleccionados[posicion]

        new_cantidad = simpledialog.askinteger("Editar artículo", "Ingrese la nueva cantidad:",
                                               initialvalue=cantidad_anterior, minvalue=1, parent=self)

        if new_cantidad is not None:
            try:
                conn = sqlite3.connect(db_name)
                c = conn.cursor()
                c.execute("SELECT precio, costo, stock FROM articulos WHERE articulo = ?", (producto,))
                resultado = c.fetchone()
                conn.close()

                if resultado is None:
                    messagebox.showerror("Error", "Producto no encontrado.")
                    return

                precio, costo, stock = resultado

                if new_cantidad > stock:
                    messagebox.showerror("Error", f"Stock insuficiente. Solo hay {stock} unidades disponibles.")
                    return

                total = precio * new_cantidad
                total_cop = "{:,.2f}".format(total)

                self.tre.item(selected_item[0], values=(factura, cliente, producto, "{:,.2f}".format(precio),
                                                        new_cantidad, total_cop))
                self.productos_seleccionados[posicion] = (factura, cliente, producto, precio, new_cantidad,
                                                          total_cop, costo)
                self.calcular_precio_total()
            except sqlite3.Error as e:
                print("Error al editar el artículo:", e)

    def limpiar_lista(self):
        self.tre.delete(*self.tre.get_children())
        self.productos_seleccionados.clear()
        self.calcular_precio_total()

    def limpiar_campos(self):
        for item in self.tre.get_children():
            self.tre.delete(item)
        self.label_precio_total.config(text="Precio a pagar: C$ 0.00")
        self.entry_producto.set("")
        self.entry_cantidad.delete(0, "end")
        self.label_stock.config(text="Stock: ")
        self.entry_cliente.set("Consumidor final")

    # ---------------- Pago (video 7) ----------------
    def realizar_pago(self):
        if not self.tre.get_children():
            messagebox.showerror("Error", "No hay productos seleccionados para realizar el pago.")
            return

        total_venta = sum(float(str(self.tre.item(item)["values"][5]).replace(",", ""))
                          for item in self.tre.get_children())
        total_formateado = "{:,.2f}".format(total_venta)

        ventana_pago = tk.Toplevel(self)
        ventana_pago.title("Realizar pago")
        ventana_pago.geometry("400x400+450+80")
        ventana_pago.config(bg=COLOR_FONDO)
        ventana_pago.resizable(False, False)
        ventana_pago.transient(self.master)
        ventana_pago.grab_set()
        ventana_pago.focus_set()
        ventana_pago.lift()

        label_titulo = tk.Label(ventana_pago, text="Realizar pago", font="sans 30 bold", bg=COLOR_FONDO)
        label_titulo.place(x=70, y=10)

        label_total = tk.Label(ventana_pago, text=f"Total a pagar: C$ {total_formateado}", font="sans 14 bold",
                               bg=COLOR_FONDO)
        label_total.place(x=80, y=100)

        label_monto = tk.Label(ventana_pago, text="Ingrese el monto pagado:", font="sans 14 bold",
                               bg=COLOR_FONDO)
        label_monto.place(x=80, y=160)

        entry_monto = ttk.Entry(ventana_pago, font="sans 14 bold")
        entry_monto.place(x=80, y=210, width=240, height=40)
        entry_monto.focus_set()

        # Corrección (guía, video 7, [1:44:44]): con lambda, procesar_pago se ejecuta al
        # hacer clic. Sin lambda se ejecutaría en esta línea, al abrir la ventana.
        button_confirmar_pago = tk.Button(ventana_pago, text="Confirmar pago", font="sans 14 bold",
                                          command=lambda: self.procesar_pago(entry_monto.get(), ventana_pago,
                                                                             total_venta))
        button_confirmar_pago.place(x=80, y=270, width=240, height=40)

    def procesar_pago(self, cantidad_pagada, ventana_pago, total_venta):
        try:
            cantidad_pagada = float(cantidad_pagada)
        except ValueError:
            messagebox.showerror("Error", "Ingrese un monto válido.")
            return

        # Corrección extra: todas las líneas se guardan con el cliente que está elegido al
        # cobrar. En el video cada línea guardaba el cliente que había al agregarla.
        cliente = self.entry_cliente.get()

        if cantidad_pagada < total_venta:
            messagebox.showerror("Error", "La cantidad pagada es insuficiente.")
            return

        cambio = cantidad_pagada - total_venta
        total_formateado = "{:,.2f}".format(total_venta)
        mensaje = (f"Total: C$ {total_formateado}\n"
                   f"Cantidad pagada: C$ {cantidad_pagada:,.2f}\n"
                   f"Cambio: C$ {cambio:,.2f}")

        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d")
        hora_actual = datetime.datetime.now().strftime("%H:%M:%S")

        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        try:
            for item in self.productos_seleccionados:
                factura, _, producto, precio, cantidad, total, costo = item
                # Corrección (guía, video 7, [1:45:45]): la cantidad también va en el INSERT.
                c.execute(
                    "INSERT INTO ventas (factura, cliente, articulo, precio, cantidad, total, costo, fecha, hora) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (self.numero_factura, cliente, producto, precio, cantidad,
                     float(total.replace(",", "")), costo * cantidad, fecha_actual, hora_actual),
                )
                # Si esto deja el stock en negativo, el CHECK (stock >= 0) de la tabla
                # lanza IntegrityError y se deshace toda la venta.
                c.execute("UPDATE articulos SET stock = stock - ? WHERE articulo = ?", (cantidad, producto))
            conn.commit()
        except sqlite3.Error as e:
            # Corrección (guía, video 7): rollback para que no quede media venta guardada.
            conn.rollback()
            if "CHECK" in str(e):
                messagebox.showerror("Error", "No hay existencia suficiente para completar la venta. "
                                              "No se guardó nada: revisá las cantidades del carrito.")
            else:
                messagebox.showerror("Error", f"Error al registrar la venta: {e}")
            ventana_pago.destroy()
            return
        finally:
            conn.close()

        # Corrección (guía, video 7, [1:04:14]): "Pago realizado" se muestra después del
        # commit. En el video aparecía antes de guardar la venta.
        messagebox.showinfo("Pago realizado", mensaje)

        # El PDF se genera después de guardar: si falla, la venta igual queda registrada.
        self.generar_factura_pdf(total_venta, cliente)

        self.numero_factura += 1
        self.label_numero_factura.config(text=str(self.numero_factura))

        self.productos_seleccionados = []
        self.limpiar_campos()

        ventana_pago.destroy()

    # ---------------- Ventas realizadas (video 8) ----------------
    def ver_ventas_realizadas(self):
        ventana_ventas = tk.Toplevel(self)
        ventana_ventas.title("Ventas realizadas")
        ventana_ventas.geometry("1100x650+120+20")
        ventana_ventas.configure(bg=COLOR_FONDO)
        ventana_ventas.resizable(False, False)
        ventana_ventas.transient(self.master)
        ventana_ventas.grab_set()
        ventana_ventas.focus_set()
        ventana_ventas.lift()

        def filtrar_ventas():
            # Reto de SQL (guía, video 8): en el video se traen todas las ventas con
            # SELECT * y se filtran en Python. Aquí el filtro lo hace SQL.
            factura_a_buscar = entry_factura.get().strip()
            cliente_a_buscar = entry_cliente.get().strip()

            # "WHERE 1 = 1" siempre es verdadero. Sirve para poder agregar cada filtro
            # con "AND ..." sin preocuparse de cuál es el primero.
            consulta = ("SELECT factura, cliente, articulo, precio, cantidad, total, fecha, hora "
                        "FROM ventas WHERE 1 = 1")
            parametros = []

            if factura_a_buscar:
                if not factura_a_buscar.isdigit():
                    messagebox.showerror("Error", "El número de factura debe ser un número.", parent=ventana_ventas)
                    return
                consulta += " AND factura = ?"
                parametros.append(int(factura_a_buscar))

            if cliente_a_buscar:
                consulta += " AND cliente LIKE ?"
                parametros.append(f"%{cliente_a_buscar}%")

            consulta += " ORDER BY factura"

            for item in tree.get_children():
                tree.delete(item)

            try:
                conn = sqlite3.connect(db_name)
                c = conn.cursor()
                c.execute(consulta, parametros)
                ventas = c.fetchall()
                conn.close()
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Error al obtener las ventas: {e}", parent=ventana_ventas)
                return

            for venta in ventas:
                venta = list(venta)
                venta[3] = "{:,.2f}".format(venta[3])
                venta[5] = "{:,.2f}".format(venta[5])
                venta[6] = datetime.datetime.strptime(venta[6], "%Y-%m-%d").strftime("%d-%m-%Y")
                tree.insert("", "end", values=venta)

        label_ventas_realizadas = tk.Label(ventana_ventas, text="Ventas realizadas", font="sans 26 bold",
                                           bg=COLOR_FONDO)
        label_ventas_realizadas.place(x=350, y=20)

        filtro_frame = tk.Frame(ventana_ventas, bg=COLOR_FONDO)
        filtro_frame.place(x=20, y=60, width=1060, height=60)

        label_factura = tk.Label(filtro_frame, text="Número de factura", bg=COLOR_FONDO, font="sans 14 bold")
        label_factura.place(x=10, y=15)
        entry_factura = ttk.Entry(filtro_frame, font="sans 14 bold")
        entry_factura.place(x=200, y=10, width=200, height=40)

        label_cliente = tk.Label(filtro_frame, text="Cliente", bg=COLOR_FONDO, font="sans 14 bold")
        label_cliente.place(x=420, y=15)
        entry_cliente = ttk.Entry(filtro_frame, font="sans 14 bold")
        entry_cliente.place(x=620, y=10, width=200, height=40)

        btn_filtrar = tk.Button(filtro_frame, text="Filtrar", font="sans 14 bold", command=filtrar_ventas)
        btn_filtrar.place(x=840, y=10)

        tree_frame = tk.Frame(ventana_ventas, bg="white")
        tree_frame.place(x=20, y=130, width=1060, height=500)

        scrol_y = ttk.Scrollbar(tree_frame)
        scrol_y.pack(side="right", fill="y")

        scrol_x = ttk.Scrollbar(tree_frame, orient="horizontal")
        scrol_x.pack(side="bottom", fill="x")

        tree = ttk.Treeview(tree_frame,
                            columns=("Factura", "Cliente", "Producto", "Precio", "Cantidad", "Total", "Fecha",
                                     "Hora"),
                            show="headings")
        tree.pack(expand=True, fill="both")

        scrol_y.config(command=tree.yview)
        scrol_x.config(command=tree.xview)
        tree.configure(yscrollcommand=scrol_y.set, xscrollcommand=scrol_x.set)

        for columna in ("Factura", "Cliente", "Producto", "Precio", "Cantidad", "Total", "Fecha", "Hora"):
            tree.heading(columna, text=columna)

        tree.column("Factura", width=60, anchor="center")
        tree.column("Cliente", width=120, anchor="center")
        tree.column("Producto", width=120, anchor="center")
        tree.column("Precio", width=80, anchor="center")
        tree.column("Cantidad", width=80, anchor="center")
        tree.column("Total", width=80, anchor="center")
        tree.column("Fecha", width=80, anchor="center")
        tree.column("Hora", width=80, anchor="center")

        # Sin filtros, la consulta trae todas las ventas.
        filtrar_ventas()

    # ---------------- Factura en PDF (video 8) ----------------
    def generar_factura_pdf(self, total_venta, cliente):
        try:
            # Corrección (guía, video 8): la carpeta se crea desde el código.
            os.makedirs("facturas", exist_ok=True)
            factura_path = f"facturas/Factura_{self.numero_factura}.pdf"
            c = canvas.Canvas(factura_path, pagesize=letter)

            empresa_nombre = "Minimarket Versión 1.0"
            empresa_direccion = "Calle 1, Managua, Nicaragua"
            empresa_telefono = "+505 8888 8888"
            empresa_email = "info@minimarket.com"
            empresa_website = "www.minimarket.com"

            c.setFont("Helvetica-Bold", 18)
            c.setFillColor(colors.darkblue)
            c.drawCentredString(300, 750, "FACTURA DE VENTA")

            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, 710, f"{empresa_nombre}")
            c.setFont("Helvetica", 12)
            c.drawString(50, 690, f"Dirección: {empresa_direccion}")
            c.drawString(50, 670, f"Teléfono: {empresa_telefono}")
            c.drawString(50, 650, f"Email: {empresa_email}")
            c.drawString(50, 630, f"Website: {empresa_website}")

            c.setLineWidth(0.5)
            c.setStrokeColor(colors.gray)
            c.line(50, 620, 550, 620)

            c.setFont("Helvetica", 12)
            c.drawString(50, 600, f"Número de factura: {self.numero_factura}")
            c.drawString(50, 580, f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            c.line(50, 560, 550, 560)

            c.drawString(50, 540, f"Cliente: {cliente}")
            c.drawString(50, 520, "Descripción de productos:")

            y_offset = 500
            c.setFont("Helvetica-Bold", 12)
            c.drawString(70, y_offset, "Producto")
            c.drawString(270, y_offset, "Cantidad")
            c.drawString(370, y_offset, "Precio")
            c.drawString(470, y_offset, "Total")

            c.line(50, y_offset - 10, 550, y_offset - 10)
            y_offset -= 30
            c.setFont("Helvetica", 12)

            for item in self.productos_seleccionados:
                factura, _, producto, precio, cantidad, total, costo = item
                c.drawString(70, y_offset, producto)
                c.drawString(270, y_offset, str(cantidad))
                # Corrección (guía, video 8): C$ y dos decimales.
                c.drawString(370, y_offset, "C$ {:,.2f}".format(precio))
                c.drawString(470, y_offset, f"C$ {total}")
                y_offset -= 20

            c.line(50, y_offset, 550, y_offset)
            y_offset -= 20

            c.setFont("Helvetica-Bold", 14)
            c.setFillColor(colors.darkblue)
            c.drawString(50, y_offset, f"Total a pagar: C$ {total_venta:,.2f}")
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 12)

            y_offset -= 20
            c.line(50, y_offset, 550, y_offset)

            # Corrección (guía, video 8, [1:26:38]): sin comas de más dentro de drawString.
            c.setFont("Helvetica-Bold", 16)
            c.drawString(150, y_offset - 60, "¡Gracias por tu compra, vuelve pronto!")

            y_offset -= 100
            c.setFont("Helvetica", 10)
            c.drawString(50, y_offset, "Términos y condiciones:")
            c.drawString(50, y_offset - 20, "1. Los productos comprados no tienen devolución.")
            c.drawString(50, y_offset - 40, "2. Conserve esta factura como comprobante de su compra.")
            c.drawString(50, y_offset - 60, "3. Para más información, contacte a servicio al cliente.")

            c.save()

            messagebox.showinfo("Factura generada", f"Se ha generado la factura en: {factura_path}")
            os.startfile(os.path.abspath(factura_path))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar la factura: {e}")
