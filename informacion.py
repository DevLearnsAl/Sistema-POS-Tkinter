import tkinter as tk

COLOR_FONDO = "#C6D9E3"


# El curso deja este módulo vacío para que lo construyás vos (video 10).
class Informacion(tk.Frame):
    def __init__(self, padre):
        super().__init__(padre)
        self.widgets()

    def widgets(self):
        label = tk.Label(self, text="Información: módulo pendiente", font="sans 20 bold", bg=COLOR_FONDO)
        label.pack(pady=40)
