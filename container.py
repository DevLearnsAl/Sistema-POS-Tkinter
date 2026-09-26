import tkinter as tk
from tkinter import Button

from ventas import Ventas
from inventario import Inventario
from clientes import Clientes
from pedidos import Pedidos
from proveedor import Proveedor
from informacion import Informacion

COLOR_FONDO = "#C6D9E3"


class Container(tk.Frame):
    def __init__(self, padre, controlador):
        super().__init__(padre)
        self.controlador = controlador
        self.pack()
        self.place(x=0, y=0, width=1100, height=650)
        self.actual = Ventas
        self.widgets()

        self.frames = {}
        for i in (Ventas, Inventario, Clientes, Pedidos, Proveedor, Informacion):
            frame = i(self)
            self.frames[i] = frame
            frame.pack()
            frame.config(bg=COLOR_FONDO, highlightbackground="gray", highlightthickness=1)
            # Los módulos arrancan en y=40: los 40 píxeles de arriba son para los botones.
            frame.place(x=0, y=40, width=1100, height=610)

        self.show_frames(Ventas)

    def show_frames(self, container):
        self.actual = container
        frame = self.frames[container]
        frame.tkraise()
        # Corrección extra (no está en la guía): en el video, Ventas carga los productos
        # y los clientes solo al abrir el programa. Un producto recién agregado en
        # Inventario no aparecía en Ventas hasta reiniciar. Ahora cada módulo se
        # actualiza al mostrarse.
        if hasattr(frame, "al_mostrar"):
            frame.al_mostrar()

    def al_mostrar(self):
        # Se llama al entrar desde el login: refresca el módulo que está a la vista.
        if hasattr(self, "frames"):
            self.show_frames(self.actual)

    def widgets(self):
        frame2 = tk.Frame(self)
        frame2.place(x=0, y=0, width=1100, height=40)

        # Reto (guía, video 2): los 6 botones con un for, en vez de copiar y pegar
        # seis veces y calcular las posiciones a mano.
        modulos = [
            ("Ventas", Ventas),
            ("Inventario", Inventario),
            ("Clientes", Clientes),
            ("Pedidos", Pedidos),
            ("Proveedor", Proveedor),
            ("Información", Informacion),
        ]
        self.buttons = []
        for i, (texto, clase) in enumerate(modulos):
            # "c=clase" guarda la clase de ESTA vuelta del for. Con "lambda: self.show_frames(clase)"
            # los seis botones abrirían el último módulo, porque la lambda lee "clase" al hacer
            # clic y para entonces el for ya terminó.
            btn = Button(frame2, fg="black", text=texto, font="sans 16 bold",
                         command=lambda c=clase: self.show_frames(c))
            btn.place(x=i * 184, y=0, width=184, height=40)
            self.buttons.append(btn)
