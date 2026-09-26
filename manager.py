from tkinter import Tk, Frame
from tkinter import ttk

from login import Login, Registro
from container import Container


class Manager(Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Minimarket versión 1.0")
        self.geometry("1100x650+120+20")
        self.resizable(False, False)

        container = Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.configure(bg="#C6D9E3")

        # Diccionario de pantallas: la llave es la clase y el valor es la pantalla ya creada.
        self.frames = {}
        for F in (Login, Registro, Container):
            frame = F(container, self)
            self.frames[F] = frame

        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Durante el desarrollo el autor pone Container aquí para no iniciar sesión
        # en cada prueba (video 4). La versión final arranca en Login.
        self.show_frame(Login)

    def show_frame(self, container):
        frame = self.frames[container]
        frame.tkraise()
        if hasattr(frame, "al_mostrar"):
            frame.al_mostrar()


def main():
    app = Manager()
    app.mainloop()


if __name__ == "__main__":
    main()
