import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from PIL import Image, ImageTk

db_name = "database.db"
COLOR_FONDO = "#C6D9E3"


def mensaje_integridad(error):
    """Traduce los errores de UNIQUE y CHECK de la tabla articulos a un mensaje claro."""
    texto = str(error)
    if "UNIQUE" in texto:
        return "Ya existe un artículo con ese nombre."
    if "CHECK" in texto:
        return "El precio debe ser mayor que 0, y el costo y el stock no pueden ser negativos."
    return f"No se pudo guardar el artículo: {texto}"


class Inventario(tk.Frame):
    def __init__(self, padre):
        super().__init__(padre)
        # Corrección (guía, video 5, [0:56:41]): en el video la conexión se crea dentro de
        # articulos_combobox y, si esa función no se llama primero, guardar falla.
        # Aquí se crea en el constructor, antes que todo lo demás.
        self.con = sqlite3.connect(db_name)
        self.cur = self.con.cursor()

        self.timer_articulos = None
        self.image_path = None
        self.articulos = []

        self.image_folder = "fotos"
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)

        self.widgets()
        self.articulos_combobox()
        self.cargar_articulos()

    def al_mostrar(self):
        # Una venta cambia el stock: al volver a Inventario se refresca la selección.
        self.articulos_combobox()
        if self.comboboxbuscar.get():
            self.actualizar_label()

    def widgets(self):
        # ---------------- Label frame 1: artículos ----------------
        canvas_articulos = tk.LabelFrame(self, text="Artículos", font="arial 14 bold", bg=COLOR_FONDO)
        canvas_articulos.place(x=300, y=10, width=780, height=580)

        # Canvas con barra de desplazamiento: el Canvas es lo que se desplaza, el Frame
        # de adentro (scrollable_frame) contiene las tarjetas, y cada vez que ese Frame
        # cambia de tamaño se actualiza la zona desplazable (scrollregion).
        self.canvas = tk.Canvas(canvas_articulos, bg=COLOR_FONDO)
        self.scrollbar = tk.Scrollbar(canvas_articulos, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=COLOR_FONDO)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # ---------------- Label frame 2: buscar ----------------
        lblframe_buscar = tk.LabelFrame(self, text="Buscar", font="arial 14 bold", bg=COLOR_FONDO)
        lblframe_buscar.place(x=10, y=10, width=280, height=80)

        self.comboboxbuscar = ttk.Combobox(lblframe_buscar, font="arial 12")
        self.comboboxbuscar.place(x=5, y=5, width=260, height=40)
        self.comboboxbuscar.bind("<<ComboboxSelected>>", self.on_combobox_select)
        self.comboboxbuscar.bind("<KeyRelease>", self.filtrar_articulos)

        # ---------------- Label frame 3: selección ----------------
        lblframe_seleccion = tk.LabelFrame(self, text="Selección", font="arial 14 bold", bg=COLOR_FONDO)
        lblframe_seleccion.place(x=10, y=95, width=280, height=190)

        self.label1 = tk.Label(lblframe_seleccion, text="Artículo: ", font="arial 12", bg=COLOR_FONDO, wraplength=260)
        self.label1.place(x=5, y=5)
        self.label2 = tk.Label(lblframe_seleccion, text="Precio: ", font="arial 12", bg=COLOR_FONDO)
        self.label2.place(x=5, y=40)
        self.label3 = tk.Label(lblframe_seleccion, text="Costo: ", font="arial 12", bg=COLOR_FONDO)
        self.label3.place(x=5, y=70)
        self.label4 = tk.Label(lblframe_seleccion, text="Stock: ", font="arial 12", bg=COLOR_FONDO)
        self.label4.place(x=5, y=100)
        self.label5 = tk.Label(lblframe_seleccion, text="Estado: ", font="arial 12", bg=COLOR_FONDO)
        self.label5.place(x=5, y=130)

        # ---------------- Label frame 4: opciones ----------------
        lblframe_botones = tk.LabelFrame(self, bg=COLOR_FONDO, text="Opciones", font="arial 14 bold")
        lblframe_botones.place(x=10, y=290, width=280, height=300)

        btn1 = tk.Button(lblframe_botones, text="Agregar", font="arial 14 bold", command=self.agregar_articulo)
        btn1.place(x=20, y=20, width=180, height=40)

        # Corrección (guía, video 5, [2:16:05]): el botón Editar necesita su command.
        btn2 = tk.Button(lblframe_botones, text="Editar", font="arial 14 bold", command=self.editar_articulo)
        btn2.place(x=20, y=80, width=180, height=40)

    # ---------------- Imágenes ----------------
    def load_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            image = Image.open(file_path)
            # Corrección (guía, video 5, [0:30:38]): el paréntesis se cierra después de LANCZOS.
            image = image.resize((200, 200), Image.LANCZOS)
            image_name = os.path.basename(file_path)
            image_save_path = os.path.join(self.image_folder, image_name)
            image.save(image_save_path)

            self.image_tk = ImageTk.PhotoImage(image)
            self.product_image = self.image_tk
            self.image_path = image_save_path

            img_label = tk.Label(self.frameimg, image=self.image_tk)
            img_label.place(x=0, y=0, width=200, height=200)

    # ---------------- Agregar ----------------
    def agregar_articulo(self):
        # Corrección extra: en el video, después de cargar una imagen, self.image_path
        # quedaba guardado y el siguiente producto sin foto se llevaba la foto del anterior.
        self.image_path = None

        top = tk.Toplevel(self)
        top.title("Agregar artículo")
        top.geometry("700x400+200+50")
        top.config(bg=COLOR_FONDO)
        top.resizable(False, False)
        # transient + grab_set: la ventana queda encima y bloquea la principal hasta cerrarla.
        top.transient(self.master)
        top.grab_set()
        top.focus_set()
        top.lift()

        label_articulo = tk.Label(top, text="Artículo: ", font="arial 12 bold", bg=COLOR_FONDO)
        label_articulo.place(x=20, y=20, width=80, height=25)
        entry_articulo = ttk.Entry(top, font="arial 12 bold")
        entry_articulo.place(x=120, y=20, width=250, height=30)

        label_precio = tk.Label(top, text="Precio: ", font="arial 12 bold", bg=COLOR_FONDO)
        label_precio.place(x=20, y=60, width=80, height=25)
        entry_precio = ttk.Entry(top, font="arial 12 bold")
        entry_precio.place(x=120, y=60, width=250, height=30)

        label_costo = tk.Label(top, text="Costo: ", font="arial 12 bold", bg=COLOR_FONDO)
        label_costo.place(x=20, y=100, width=80, height=25)
        entry_costo = ttk.Entry(top, font="arial 12 bold")
        entry_costo.place(x=120, y=100, width=250, height=30)

        label_stock = tk.Label(top, text="Stock: ", font="arial 12 bold", bg=COLOR_FONDO)
        label_stock.place(x=20, y=140, width=80, height=25)
        entry_stock = ttk.Entry(top, font="arial 12 bold")
        entry_stock.place(x=120, y=140, width=250, height=30)

        # Corrección (guía, video 5 y video 6 [0:04:07]): Combobox de solo lectura en vez de
        # un Entry, para que el estado solo pueda ser "Activo" o "Inactivo".
        label_estado = tk.Label(top, text="Estado: ", font="arial 12 bold", bg=COLOR_FONDO)
        label_estado.place(x=20, y=180, width=80, height=25)
        entry_estado = ttk.Combobox(top, font="arial 12 bold", values=["Activo", "Inactivo"], state="readonly")
        entry_estado.set("Activo")
        entry_estado.place(x=120, y=180, width=250, height=30)

        self.frameimg = tk.Frame(top, bg="white", highlightbackground="gray", highlightthickness=1)
        self.frameimg.place(x=440, y=30, width=200, height=200)

        btnimage = tk.Button(top, text="Cargar imagen", font="arial 12 bold", command=self.load_image)
        btnimage.place(x=470, y=260, width=150, height=40)

        def guardar():
            articulo = entry_articulo.get().strip()
            precio = entry_precio.get()
            costo = entry_costo.get()
            stock = entry_stock.get()
            estado = entry_estado.get()

            if not articulo or not precio or not costo or not stock or not estado:
                messagebox.showerror("Error", "Todos los campos deben ser completados")
                return

            try:
                precio = round(float(precio), 2)
                costo = round(float(costo), 2)
                stock = int(stock)
            except ValueError:
                messagebox.showerror("Error", "Precio, costo y stock deben ser números válidos")
                return

            if self.image_path:
                image_path = self.image_path
            else:
                image_path = os.path.join(self.image_folder, "default.png")

            try:
                self.cur.execute(
                    "INSERT INTO articulos (articulo, precio, costo, stock, estado, image_path) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (articulo, precio, costo, stock, estado, image_path),
                )
                self.con.commit()
            except sqlite3.IntegrityError as e:
                self.con.rollback()
                messagebox.showerror("Error", mensaje_integridad(e))
                return
            except sqlite3.Error as e:
                self.con.rollback()
                print("Error al cargar el artículo:", e)
                messagebox.showerror("Error", f"Error al agregar el artículo: {e}")
                return

            messagebox.showinfo("Éxito", "Artículo agregado correctamente")
            top.destroy()
            # Corrección (guía, video 5, [1:48:10]): recargar para que se vea el producto nuevo.
            self.cargar_articulos()
            self.articulos_combobox()

        btn_guardar = tk.Button(top, text="Guardar", font="arial 12 bold", command=guardar)
        btn_guardar.place(x=50, y=260, width=150, height=40)

        btn_cancelar = tk.Button(top, text="Cancelar", font="arial 12 bold", command=top.destroy)
        btn_cancelar.place(x=260, y=260, width=150, height=40)

    # ---------------- Mostrar ----------------
    def articulos_combobox(self):
        self.cur.execute("SELECT articulo FROM articulos")
        self.articulos = [row[0] for row in self.cur.fetchall()]
        self.comboboxbuscar["values"] = self.articulos

    def cargar_articulos(self, filtro=None):
        self.after(0, self._cargar_articulos, filtro)

    def _cargar_articulos(self, filtro=None):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Corrección (guía, video 5, [1:44:02] y [1:45:04]): el espacio antes de WHERE
        # y el % cerrado en los dos lados del filtro.
        query = "SELECT articulo, precio, image_path FROM articulos"
        params = []
        if filtro:
            query += " WHERE articulo LIKE ?"
            params.append(f"%{filtro}%")

        self.cur.execute(query, params)
        articulos = self.cur.fetchall()

        self.row = 0
        self.column = 0
        for articulo, precio, image_path in articulos:
            self.mostrar_articulo(articulo, precio, image_path)

    def mostrar_articulo(self, articulo, precio, image_path):
        article_frame = tk.Frame(self.scrollable_frame, bg="white", relief="solid")
        # grid acomoda las tarjetas en filas y columnas.
        article_frame.grid(row=self.row, column=self.column, padx=10, pady=10)

        if image_path and os.path.exists(image_path):
            image = Image.open(image_path)
            image = image.resize((150, 150), Image.LANCZOS)
            imagen = ImageTk.PhotoImage(image)
            image_label = tk.Label(article_frame, image=imagen)
            image_label.image = imagen  # guardar la referencia para que Python no borre la imagen
            image_label.pack(expand=True, fill="both")

        name_label = tk.Label(article_frame, text=articulo, bg="white", anchor="w",
                              wraplength=150, font="arial 10 bold")
        name_label.pack(side="top", fill="x")

        # Corrección (guía, video 7): .2f para ver los centavos, y C$ en vez de $.
        precio_label = tk.Label(article_frame, text=f"Precio: C$ {precio:,.2f}", bg="white",
                                anchor="w", wraplength=150, font="arial 8 bold")
        precio_label.pack(side="top", fill="x")

        # Cuatro tarjetas por fila: al pasar de la columna 3 se empieza una fila nueva.
        self.column += 1
        if self.column > 3:
            self.column = 0
            self.row += 1

    # ---------------- Selección ----------------
    def on_combobox_select(self, event):
        self.actualizar_label()

    def actualizar_label(self, event=None):
        articulo_seleccionado = self.comboboxbuscar.get()

        try:
            # Corrección (guía, video 5, [1:31:45]): la coma en (articulo_seleccionado,).
            # Sin la coma es un texto y SQLite toma cada letra como un parámetro.
            self.cur.execute(
                "SELECT articulo, precio, costo, stock, estado FROM articulos WHERE articulo = ?",
                (articulo_seleccionado,),
            )
            resultado = self.cur.fetchone()

            if resultado is not None:
                articulo, precio, costo, stock, estado = resultado

                self.label1.config(text=f"Artículo: {articulo}")
                self.label2.config(text=f"Precio: C$ {precio:,.2f}")
                self.label3.config(text=f"Costo: C$ {costo:,.2f}")
                self.label4.config(text=f"Stock: {stock}")
                self.label5.config(text=f"Estado: {estado}")

                # Corrección (guía, video 6, [0:03:06]): comparar en minúsculas.
                if estado.lower() == "activo":
                    self.label5.config(fg="green")
                elif estado.lower() == "inactivo":
                    self.label5.config(fg="red")
                else:
                    self.label5.config(fg="black")
            else:
                self.label1.config(text="Artículo: No encontrado")
                self.label2.config(text="Precio: N/A")
                self.label3.config(text="Costo: N/A")
                self.label4.config(text="Stock: N/A")
                self.label5.config(text="Estado: N/A", fg="black")
        except sqlite3.Error as e:
            print("Error al obtener los datos del artículo:", e)
            messagebox.showerror("Error", "Error al obtener los datos del artículo")

    # ---------------- Filtro mientras se escribe ----------------
    def filtrar_articulos(self, event):
        # Corrección (guía, video 5): self.after en vez de threading.Timer. Tkinter no es
        # seguro con hilos; after espera medio segundo sin salir del hilo de la ventana.
        # Si se presiona otra tecla antes, se cancela la espera anterior y empieza otra.
        if self.timer_articulos:
            self.after_cancel(self.timer_articulos)
        self.timer_articulos = self.after(500, self._filter_articulos)

    def _filter_articulos(self):
        self.timer_articulos = None
        typed = self.comboboxbuscar.get()

        if typed == "":
            data = self.articulos
        else:
            data = [item for item in self.articulos if typed.lower() in item.lower()]

        if data:
            self.comboboxbuscar["values"] = data
            self.comboboxbuscar.event_generate("<Down>")
        else:
            self.comboboxbuscar["values"] = ["No se encontraron resultados"]
            self.comboboxbuscar.event_generate("<Down>")

        self.cargar_articulos(filtro=typed)

    # ---------------- Editar ----------------
    def editar_articulo(self):
        selected_item = self.comboboxbuscar.get()

        if not selected_item:
            messagebox.showerror("Error", "Selecciona un artículo para editar")
            return

        self.cur.execute(
            "SELECT articulo, precio, costo, stock, estado, image_path FROM articulos WHERE articulo = ?",
            (selected_item,),
        )
        resultado = self.cur.fetchone()

        if not resultado:
            messagebox.showerror("Error", "Artículo no encontrado")
            return

        self.image_path = None

        top = tk.Toplevel(self)
        top.title("Editar artículo")
        top.geometry("700x400+200+50")
        top.config(bg=COLOR_FONDO)
        top.resizable(False, False)
        top.transient(self.master)
        top.grab_set()
        top.focus_set()
        top.lift()

        # Corrección (guía, video 5, [2:17:05]): el orden de las variables tiene que ser
        # el mismo orden de las columnas del SELECT.
        (articulo, precio, costo, stock, estado, image_path) = resultado

        label_articulo = tk.Label(top, text="Artículo: ", font="arial 12 bold", bg=COLOR_FONDO)
        label_articulo.place(x=20, y=20, width=80, height=25)
        entry_articulo = ttk.Entry(top, font="arial 12 bold")
        entry_articulo.place(x=120, y=20, width=250, height=30)
        entry_articulo.insert(0, articulo)

        label_precio = tk.Label(top, text="Precio: ", font="arial 12 bold", bg=COLOR_FONDO)
        label_precio.place(x=20, y=60, width=80, height=25)
        entry_precio = ttk.Entry(top, font="arial 12 bold")
        entry_precio.place(x=120, y=60, width=250, height=30)
        entry_precio.insert(0, f"{precio:.2f}")

        label_costo = tk.Label(top, text="Costo: ", font="arial 12 bold", bg=COLOR_FONDO)
        label_costo.place(x=20, y=100, width=80, height=25)
        entry_costo = ttk.Entry(top, font="arial 12 bold")
        entry_costo.place(x=120, y=100, width=250, height=30)
        entry_costo.insert(0, f"{costo:.2f}")

        label_stock = tk.Label(top, text="Stock: ", font="arial 12 bold", bg=COLOR_FONDO)
        label_stock.place(x=20, y=140, width=80, height=25)
        entry_stock = ttk.Entry(top, font="arial 12 bold")
        entry_stock.place(x=120, y=140, width=250, height=30)
        entry_stock.insert(0, stock)

        label_estado = tk.Label(top, text="Estado: ", font="arial 12 bold", bg=COLOR_FONDO)
        label_estado.place(x=20, y=180, width=80, height=25)
        entry_estado = ttk.Combobox(top, font="arial 12 bold", values=["Activo", "Inactivo"], state="readonly")
        entry_estado.place(x=120, y=180, width=250, height=30)
        # Un Combobox de solo lectura no acepta insert(): se usa set().
        entry_estado.set(estado)

        self.frameimg = tk.Frame(top, bg="white", highlightbackground="gray", highlightthickness=1)
        self.frameimg.place(x=440, y=30, width=200, height=200)

        if image_path and os.path.exists(image_path):
            image = Image.open(image_path)
            image = image.resize((200, 200), Image.LANCZOS)
            self.product_image = ImageTk.PhotoImage(image)
            image_label = tk.Label(self.frameimg, image=self.product_image)
            image_label.pack(expand=True, fill="both")

        btnimage = tk.Button(top, text="Cargar imagen", font="arial 12 bold", command=self.load_image)
        btnimage.place(x=470, y=260, width=150, height=40)

        def guardar():
            nuevo_articulo = entry_articulo.get().strip()
            precio = entry_precio.get()
            costo = entry_costo.get()
            stock = entry_stock.get()
            estado = entry_estado.get()

            if not nuevo_articulo or not precio or not costo or not stock or not estado:
                messagebox.showerror("Error", "Todos los campos deben ser completados")
                return

            try:
                precio = round(float(precio), 2)
                costo = round(float(costo), 2)
                stock = int(stock)
            except ValueError:
                messagebox.showerror("Error", "Precio, costo y stock deben ser números válidos")
                return

            if self.image_path:
                nueva_imagen = self.image_path
            else:
                nueva_imagen = image_path

            try:
                self.cur.execute(
                    "UPDATE articulos SET articulo = ?, precio = ?, costo = ?, stock = ?, estado = ?, "
                    "image_path = ? WHERE articulo = ?",
                    (nuevo_articulo, precio, costo, stock, estado, nueva_imagen, selected_item),
                )
                self.con.commit()
            except sqlite3.IntegrityError as e:
                self.con.rollback()
                messagebox.showerror("Error", mensaje_integridad(e))
                return
            except sqlite3.Error as e:
                self.con.rollback()
                messagebox.showerror("Error", f"Error al editar el artículo: {e}")
                return

            self.articulos_combobox()
            self.comboboxbuscar.set(nuevo_articulo)
            self.actualizar_label()
            self.after(0, lambda: self.cargar_articulos(filtro=nuevo_articulo))
            top.destroy()
            messagebox.showinfo("Éxito", "Artículo editado exitosamente")

        btn_guardar = tk.Button(top, text="Guardar", font="arial 12 bold", command=guardar)
        btn_guardar.place(x=260, y=260, width=150, height=40)
