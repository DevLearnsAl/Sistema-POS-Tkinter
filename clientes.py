import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

db_name = "database.db"
COLOR_FONDO = "#C6D9E3"


class Clientes(tk.Frame):
    def __init__(self, padre):
        super().__init__(padre)
        self.widgets()
        self.cargar_registros()

    # ---------------- Interfaz (video 9) ----------------
    def widgets(self):
        self.labelframe = tk.LabelFrame(self, text="Clientes", font="sans 20 bold", bg=COLOR_FONDO)
        self.labelframe.place(x=20, y=20, width=250, height=560)

        lblnombre = tk.Label(self.labelframe, text="Nombre: ", font="sans 14 bold", bg=COLOR_FONDO)
        lblnombre.place(x=10, y=20)
        self.nombre = ttk.Entry(self.labelframe, font="sans 14 bold")
        self.nombre.place(x=10, y=50, width=220, height=40)

        lblcedula = tk.Label(self.labelframe, text="Cédula: ", font="sans 14 bold", bg=COLOR_FONDO)
        lblcedula.place(x=10, y=100)
        self.cedula = ttk.Entry(self.labelframe, font="sans 14 bold")
        self.cedula.place(x=10, y=130, width=220, height=40)

        lblcelular = tk.Label(self.labelframe, text="Celular: ", font="sans 14 bold", bg=COLOR_FONDO)
        lblcelular.place(x=10, y=180)
        self.celular = ttk.Entry(self.labelframe, font="sans 14 bold")
        self.celular.place(x=10, y=210, width=220, height=40)

        lbldireccion = tk.Label(self.labelframe, text="Dirección: ", font="sans 14 bold", bg=COLOR_FONDO)
        lbldireccion.place(x=10, y=260)
        self.direccion = ttk.Entry(self.labelframe, font="sans 14 bold")
        self.direccion.place(x=10, y=290, width=220, height=40)

        lblcorreo = tk.Label(self.labelframe, text="Correo: ", font="sans 14 bold", bg=COLOR_FONDO)
        lblcorreo.place(x=10, y=340)
        self.correo = ttk.Entry(self.labelframe, font="sans 14 bold")
        self.correo.place(x=10, y=370, width=220, height=40)

        btn1 = tk.Button(self.labelframe, fg="black", text="Ingresar", font="sans 16 bold", command=self.registrar)
        btn1.place(x=10, y=420, width=220, height=40)

        btn2 = tk.Button(self.labelframe, fg="black", text="Modificar", font="sans 16 bold", command=self.modificar)
        btn2.place(x=10, y=470, width=220, height=40)

        treFrame = tk.Frame(self, bg="white")
        treFrame.place(x=280, y=20, width=800, height=560)

        scrol_y = ttk.Scrollbar(treFrame)
        scrol_y.pack(side="right", fill="y")

        scrol_x = ttk.Scrollbar(treFrame, orient="horizontal")
        scrol_x.pack(side="bottom", fill="x")

        self.tre = ttk.Treeview(treFrame, yscrollcommand=scrol_y.set, xscrollcommand=scrol_x.set, height=40,
                                columns=("ID", "Nombre", "Cédula", "Celular", "Dirección", "Correo"),
                                show="headings")
        self.tre.pack(expand=True, fill="both")

        scrol_y.config(command=self.tre.yview)
        scrol_x.config(command=self.tre.xview)

        self.tre.heading("ID", text="ID")
        self.tre.heading("Nombre", text="Nombre")
        self.tre.heading("Cédula", text="Cédula")
        self.tre.heading("Celular", text="Celular")
        self.tre.heading("Dirección", text="Dirección")
        self.tre.heading("Correo", text="Correo")

        self.tre.column("ID", width=50, anchor="center")
        self.tre.column("Nombre", width=150, anchor="center")
        self.tre.column("Cédula", width=120, anchor="center")
        self.tre.column("Celular", width=120, anchor="center")
        self.tre.column("Dirección", width=200, anchor="center")
        self.tre.column("Correo", width=200, anchor="center")

    # ---------------- Funciones (video 10) ----------------
    def validar_campos(self):
        if (not self.nombre.get() or not self.cedula.get() or not self.celular.get()
                or not self.direccion.get() or not self.correo.get()):
            messagebox.showerror("Error", "Todos los campos son requeridos.")
            return False
        return True

    def registrar(self):
        if not self.validar_campos():
            return

        nombre = self.nombre.get()
        cedula = self.cedula.get()
        celular = self.celular.get()
        direccion = self.direccion.get()
        correo = self.correo.get()

        # Corrección: en el video, conn.close() solo se ejecuta si todo sale bien. Si el INSERT
        # falla (por ejemplo, una cédula repetida), la conexión queda abierta con la base
        # bloqueada y la siguiente venta o modificación da "database is locked".
        # finally se ejecuta siempre, haya error o no.
        conn = sqlite3.connect(db_name)
        try:
            c = conn.cursor()
            c.execute("INSERT INTO clientes (nombre, cedula, celular, direccion, correo) VALUES (?, ?, ?, ?, ?)",
                      (nombre, cedula, celular, direccion, correo))
            conn.commit()
        except sqlite3.IntegrityError:
            # La cédula es UNIQUE: no pueden existir dos clientes con la misma.
            messagebox.showerror("Error", "Ya existe un cliente con esa cédula.")
            return
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"No se pudo registrar el cliente: {e}")
            return
        finally:
            conn.close()

        messagebox.showinfo("Éxito", "Cliente registrado correctamente.")
        self.limpiar_treeview()
        self.limpiar_campos()
        self.cargar_registros()

    def cargar_registros(self):
        try:
            conn = sqlite3.connect(db_name)
            c = conn.cursor()
            c.execute("SELECT * FROM clientes")
            rows = c.fetchall()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"No se pudieron cargar los registros: {e}")
            return

        for row in rows:
            # Un campo vacío (NULL) llega como None: se muestra en blanco.
            valores = ["" if valor is None else valor for valor in row]
            self.tre.insert("", "end", values=valores)

    def limpiar_treeview(self):
        # Corrección (guía, video 10, [0:52:11]): delete necesita saber qué item borrar.
        # Sin "item", la tabla no se limpiaba y los clientes aparecían duplicados.
        for item in self.tre.get_children():
            self.tre.delete(item)

    def limpiar_campos(self):
        self.nombre.delete(0, "end")
        self.cedula.delete(0, "end")
        self.celular.delete(0, "end")
        self.direccion.delete(0, "end")
        self.correo.delete(0, "end")

    def modificar(self):
        if not self.tre.selection():
            messagebox.showerror("Error", "Por favor seleccione un cliente para modificar.")
            return

        item = self.tre.selection()[0]
        id_cliente = self.tre.item(item, "values")[0]

        # Se leen los datos desde la base y no desde la tabla de la pantalla: el Treeview
        # puede devolver "0012345" como el número 12345.
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        c.execute("SELECT nombre, cedula, celular, direccion, correo FROM clientes WHERE id = ?", (id_cliente,))
        datos = c.fetchone()
        conn.close()
        if datos is None:
            messagebox.showerror("Error", "Cliente no encontrado.")
            return

        nombre_actual, cedula_actual, celular_actual, direccion_actual, correo_actual = \
            ["" if valor is None else valor for valor in datos]

        top_modificar = tk.Toplevel(self)
        top_modificar.title("Modificar cliente")
        top_modificar.geometry("400x400+400+50")
        top_modificar.config(bg=COLOR_FONDO)
        top_modificar.resizable(False, False)
        top_modificar.transient(self.master)
        top_modificar.grab_set()
        top_modificar.focus_set()
        top_modificar.lift()

        # grid acomoda los widgets en filas y columnas, como una tabla.
        # Encadenar .grid() a la creación (como en estos Label) solo está bien cuando no
        # guardás el widget en una variable: grid(), igual que place(), devuelve None.
        tk.Label(top_modificar, text="Nombre:", font="sans 14 bold", bg=COLOR_FONDO).grid(row=0, column=0, padx=10, pady=5)
        nombre_nuevo = tk.Entry(top_modificar, font="sans 14 bold")
        nombre_nuevo.insert(0, nombre_actual)
        nombre_nuevo.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(top_modificar, text="Cédula:", font="sans 14 bold", bg=COLOR_FONDO).grid(row=1, column=0, padx=10, pady=5)
        cedula_nuevo = tk.Entry(top_modificar, font="sans 14 bold")
        cedula_nuevo.insert(0, cedula_actual)
        cedula_nuevo.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(top_modificar, text="Celular:", font="sans 14 bold", bg=COLOR_FONDO).grid(row=2, column=0, padx=10, pady=5)
        celular_nuevo = tk.Entry(top_modificar, font="sans 14 bold")
        celular_nuevo.insert(0, celular_actual)
        celular_nuevo.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(top_modificar, text="Dirección:", font="sans 14 bold", bg=COLOR_FONDO).grid(row=3, column=0, padx=10, pady=5)
        direccion_nuevo = tk.Entry(top_modificar, font="sans 14 bold")
        direccion_nuevo.insert(0, direccion_actual)
        direccion_nuevo.grid(row=3, column=1, padx=10, pady=5)

        tk.Label(top_modificar, text="Correo:", font="sans 14 bold", bg=COLOR_FONDO).grid(row=4, column=0, padx=10, pady=5)
        correo_nuevo = tk.Entry(top_modificar, font="sans 14 bold")
        correo_nuevo.insert(0, correo_actual)
        correo_nuevo.grid(row=4, column=1, padx=10, pady=5)

        def guardar_modificaciones():
            nuevo_nombre = nombre_nuevo.get()
            # Una cédula vacía se guarda como NULL: UNIQUE permite varios NULL,
            # pero no dos textos vacíos iguales.
            nueva_cedula = cedula_nuevo.get() or None
            nuevo_celular = celular_nuevo.get()
            nueva_direccion = direccion_nuevo.get()
            nuevo_correo = correo_nuevo.get()

            if not nuevo_nombre:
                messagebox.showerror("Error", "El nombre es obligatorio.", parent=top_modificar)
                return

            conn = sqlite3.connect(db_name)
            try:
                c = conn.cursor()
                # Aquí sí se busca por id (video 10): dos clientes pueden llamarse igual.
                c.execute("UPDATE clientes SET nombre = ?, cedula = ?, celular = ?, direccion = ?, correo = ? "
                          "WHERE id = ?",
                          (nuevo_nombre, nueva_cedula, nuevo_celular, nueva_direccion, nuevo_correo, id_cliente))
                conn.commit()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Ya existe otro cliente con esa cédula.", parent=top_modificar)
                return
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"No se pudo modificar el cliente: {e}", parent=top_modificar)
                return
            finally:
                conn.close()

            messagebox.showinfo("Éxito", "Cliente modificado correctamente.")
            self.limpiar_treeview()
            self.cargar_registros()
            top_modificar.destroy()

        btn_guardar = tk.Button(top_modificar, text="Guardar cambios", font="sans 14 bold",
                                command=guardar_modificaciones)
        btn_guardar.grid(row=5, column=0, columnspan=2, pady=20)
