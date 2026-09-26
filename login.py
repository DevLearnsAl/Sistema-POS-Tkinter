import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageTk

from container import Container

db_name = "database.db"
COLOR_FONDO = "#C6D9E3"


class Login(tk.Frame):
    def __init__(self, padre, controlador):
        super().__init__(padre)
        self.pack()
        self.place(x=0, y=0, width=1100, height=650)
        self.controlador = controlador
        self.widgets()

    def validacion(self, user, pas):
        return len(user) > 0 and len(pas) > 0

    def login(self):
        user = self.username.get()
        pas = self.password.get()

        if self.validacion(user, pas):
            # Los "?" hacen que sqlite3 meta los datos por separado: así se evita la inyección SQL.
            consulta = "SELECT * FROM usuarios WHERE username = ? AND password = ?"
            parametros = (user, pas)
            try:
                with sqlite3.connect(db_name) as conn:
                    cursor = conn.cursor()
                    cursor.execute(consulta, parametros)
                    result = cursor.fetchall()

                if result:
                    self.username.delete(0, "end")
                    self.password.delete(0, "end")
                    self.control1()
                else:
                    self.username.delete(0, "end")
                    self.password.delete(0, "end")
                    messagebox.showerror(title="Error", message="Usuario o contraseña incorrecta")
            except sqlite3.Error as e:
                messagebox.showerror(title="Error", message=f"No se conectó a la base de datos: {e}")
        else:
            messagebox.showerror(title="Error", message="Llene todas las casillas")

    def control1(self):
        self.controlador.show_frame(Container)

    def control2(self):
        self.controlador.show_frame(Registro)

    def widgets(self):
        fondo = tk.Frame(self, bg=COLOR_FONDO)
        fondo.pack()
        fondo.place(x=0, y=0, width=1100, height=650)

        # Hay que guardar la imagen en self: si queda en una variable local,
        # Python la borra al terminar la función y el Label queda vacío.
        self.bg_image = Image.open("imagenes/fondo.png")
        self.bg_image = self.bg_image.resize((1100, 650))
        self.bg_image = ImageTk.PhotoImage(self.bg_image)
        self.bg_label = ttk.Label(fondo, image=self.bg_image)
        self.bg_label.place(x=0, y=0, width=1100, height=650)

        frame1 = tk.Frame(self, bg="#FFFFFF", highlightbackground="black", highlightthickness=1)
        frame1.place(x=350, y=70, width=400, height=560)

        self.logo_image = Image.open("imagenes/logo.png")
        self.logo_image = self.logo_image.resize((200, 200))
        self.logo_image = ImageTk.PhotoImage(self.logo_image)
        self.logo_label = ttk.Label(frame1, image=self.logo_image, background="#FFFFFF")
        self.logo_label.place(x=100, y=20)

        user = ttk.Label(frame1, text="Nombre de usuario", font="arial 16 bold", background="#FFFFFF")
        user.place(x=100, y=250)
        # Corrección (guía, video 5): el widget se crea en una línea y se posiciona en otra.
        # place() devuelve None; si lo encadenás, self.username quedaría en None.
        self.username = ttk.Entry(frame1, font="arial 16 bold")
        self.username.place(x=80, y=290, width=240, height=40)

        pas = ttk.Label(frame1, text="Contraseña", font="arial 16 bold", background="#FFFFFF")
        pas.place(x=100, y=340)
        self.password = ttk.Entry(frame1, show="*", font="arial 16 bold")
        self.password.place(x=80, y=380, width=240, height=40)

        # Corrección (guía, video 3, [0:53:37]): "Iniciar" llama a login, que valida.
        # Si llamara a control1 entraría cualquiera sin contraseña.
        btn1 = tk.Button(frame1, text="Iniciar", font="arial 16 bold", command=self.login)
        btn1.place(x=80, y=440, width=240, height=40)

        btn2 = tk.Button(frame1, text="Registrar", font="arial 16 bold", command=self.control2)
        btn2.place(x=80, y=500, width=240, height=40)


class Registro(tk.Frame):
    def __init__(self, padre, controlador):
        super().__init__(padre)
        self.pack()
        self.place(x=0, y=0, width=1100, height=650)
        self.controlador = controlador
        self.widgets()

    def validacion(self, user, pas):
        return len(user) > 0 and len(pas) > 0

    def ejecutar_consulta(self, consulta, parametros=()):
        # Mini reto (guía, video 3): devuelve True o False. En el video, si el
        # INSERT fallaba, se mostraba el error pero igual entrabas al sistema.
        try:
            with sqlite3.connect(db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(consulta, parametros)
            return True
        except sqlite3.IntegrityError:
            messagebox.showerror(title="Error", message="Ese nombre de usuario ya existe")
            return False
        except sqlite3.Error as e:
            messagebox.showerror(title="Error", message=f"Error al ejecutar la consulta: {e}")
            return False

    def registro(self):
        user = self.username.get()
        pas = self.password.get()
        key = self.key.get()

        if self.validacion(user, pas):
            if len(pas) < 6:
                messagebox.showinfo(title="Error", message="Contraseña demasiado corta")
                self.username.delete(0, "end")
                self.password.delete(0, "end")
            else:
                if key == "1234":
                    consulta = "INSERT INTO usuarios (username, password) VALUES (?, ?)"
                    parametros = (user, pas)
                    if self.ejecutar_consulta(consulta, parametros):
                        self.username.delete(0, "end")
                        self.password.delete(0, "end")
                        self.key.delete(0, "end")
                        self.control1()
                else:
                    messagebox.showerror(title="Registro", message="Error al ingresar el código de registro")
        else:
            messagebox.showerror(title="Error", message="Llene sus datos")

    def control1(self):
        self.controlador.show_frame(Container)

    def control2(self):
        self.controlador.show_frame(Login)

    def widgets(self):
        fondo = tk.Frame(self, bg=COLOR_FONDO)
        fondo.pack()
        fondo.place(x=0, y=0, width=1100, height=650)

        self.bg_image = Image.open("imagenes/fondo.png")
        self.bg_image = self.bg_image.resize((1100, 650))
        self.bg_image = ImageTk.PhotoImage(self.bg_image)
        self.bg_label = ttk.Label(fondo, image=self.bg_image)
        self.bg_label.place(x=0, y=0, width=1100, height=650)

        frame1 = tk.Frame(self, bg="#FFFFFF", highlightbackground="black", highlightthickness=1)
        frame1.place(x=350, y=10, width=400, height=630)

        self.logo_image = Image.open("imagenes/logo.png")
        self.logo_image = self.logo_image.resize((200, 200))
        self.logo_image = ImageTk.PhotoImage(self.logo_image)
        self.logo_label = ttk.Label(frame1, image=self.logo_image, background="#FFFFFF")
        self.logo_label.place(x=100, y=20)

        user = ttk.Label(frame1, text="Nombre de usuario", font="arial 16 bold", background="#FFFFFF")
        user.place(x=100, y=250)
        self.username = ttk.Entry(frame1, font="arial 16 bold")
        self.username.place(x=80, y=290, width=240, height=40)

        pas = ttk.Label(frame1, text="Contraseña", font="arial 16 bold", background="#FFFFFF")
        pas.place(x=100, y=340)
        self.password = ttk.Entry(frame1, show="*", font="arial 16 bold")
        self.password.place(x=80, y=380, width=240, height=40)

        key = ttk.Label(frame1, text="Código de registro", font="arial 16 bold", background="#FFFFFF")
        key.place(x=100, y=430)
        self.key = ttk.Entry(frame1, show="*", font="arial 16 bold")
        self.key.place(x=80, y=470, width=240, height=40)

        btn3 = tk.Button(frame1, text="Registrarse", font="arial 16 bold", command=self.registro)
        btn3.place(x=80, y=520, width=240, height=40)

        btn4 = tk.Button(frame1, text="Regresar", font="arial 16 bold", command=self.control2)
        btn4.place(x=80, y=570, width=240, height=40)
