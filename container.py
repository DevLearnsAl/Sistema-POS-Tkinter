import datetime
import tkinter as tk
from tkinter import messagebox

import ajustes
from configuracion import VentanaConfiguracion
from estilos import FONDO, NAVY, NAVY_HOVER, BLANCO, AMBAR, TEXTO_CLARO, FUENTE, F_NEGRITA, F_PEQUE
from ventas import Ventas
from caja import Caja
from compras import Compras
from inventario import Inventario
from catalogo import Clientes, Proveedores
from reportes import Reportes
from usuarios import VentanaMiCuenta, VentanaUsuarios

# (texto, clase, permiso que hace falta). Sin permiso, el módulo es para todos.
MODULOS = [
    ("Ventas", Ventas, None),
    ("Caja", Caja, None),
    ("Compras", Compras, "compras"),
    ("Inventario", Inventario, None),
    ("Clientes", Clientes, None),
    ("Proveedores", Proveedores, "proveedores"),
    ("Reportes", Reportes, "reportes"),
]
ALTO_BARRA = 44
INICIO_PESTANAS = 150
FIN_PESTANAS = 916


class Container(tk.Frame):
    """Sistema principal: barra superior con los módulos y el área de trabajo."""

    def __init__(self, padre, controlador):
        super().__init__(padre, bg=FONDO)
        self.controlador = controlador
        self.place(x=0, y=0, width=1100, height=650)
        self.actual = Ventas
        self.atajos = {}
        self.barra_superior()

        self.frames = {}
        for _, clase, _ in MODULOS:
            frame = clase(self, controlador)
            frame.place(x=0, y=ALTO_BARRA, width=1100, height=650 - ALTO_BARRA)
            self.frames[clase] = frame

        # Atajos: F1 a F7 cambian de módulo. Qué módulo abre cada tecla depende de
        # los que vea el rol, así los números coinciden con los botones de la barra.
        # (F12 cobra, lo maneja Ventas.)
        for numero in range(1, len(MODULOS) + 1):
            controlador.bind(f"<F{numero}>", lambda e, n=numero: self._atajo(n), add="+")
        self.actualizar_reloj()

    # ------------------------------------------------------------------ barra
    def barra_superior(self):
        self.barra = tk.Frame(self, bg=NAVY)
        self.barra.place(x=0, y=0, width=1100, height=ALTO_BARRA)
        self.lbl_marca = tk.Label(self.barra, font=(FUENTE, 14, "bold"), fg=BLANCO, bg=NAVY, anchor="w")
        self.lbl_marca.place(x=18, y=0, width=INICIO_PESTANAS - 26, height=ALTO_BARRA)
        self.actualizar_marca()

        self.pestanas = {}
        self.btn_usuario = tk.Button(self.barra, text="", font=F_PEQUE, fg=TEXTO_CLARO, bg=NAVY,
                                     activebackground=NAVY_HOVER, activeforeground=BLANCO, relief="flat", bd=0,
                                     cursor="hand2", highlightthickness=0, anchor="e", padx=10,
                                     command=self.menu_usuario)
        self.btn_usuario.place(x=FIN_PESTANAS + 8, y=4, width=168, height=ALTO_BARRA - 8)

    def _construir_pestanas(self):
        """Arma los botones según el rol: el cajero no ve Compras, Proveedores ni Reportes."""
        for b in self.pestanas.values():
            b.destroy()
        self.pestanas = {}
        visibles = [(t, c) for t, c, permiso in MODULOS if permiso is None or self.controlador.puede(permiso)]
        self.atajos = {i + 1: clase for i, (_, clase) in enumerate(visibles)}
        ancho = max(96, min(132, (FIN_PESTANAS - INICIO_PESTANAS) // max(len(visibles), 1)))
        for i, (texto, clase) in enumerate(visibles):
            # "c=clase" guarda la clase de esta vuelta del for; sin eso, todos los
            # botones abrirían el último módulo.
            b = tk.Button(self.barra, text=f"{texto}  ·  F{i + 1}" if ancho >= 120 else texto, font=F_NEGRITA,
                          fg=BLANCO, bg=NAVY, activebackground=NAVY_HOVER, activeforeground=BLANCO, relief="flat",
                          bd=0, cursor="hand2", highlightthickness=0,
                          command=lambda c=clase: self.show_frames(c))
            b.place(x=INICIO_PESTANAS + i * ancho, y=0, width=ancho, height=ALTO_BARRA)
            b.bind("<Enter>", lambda e, c=clase: self._hover(c, True))
            b.bind("<Leave>", lambda e, c=clase: self._hover(c, False))
            self.pestanas[clase] = b
        if self.actual not in self.pestanas:
            self.actual = Ventas

    def _hover(self, clase, dentro):
        if clase is not self.actual:
            self.pestanas[clase].config(bg=NAVY_HOVER if dentro else NAVY)

    def menu_usuario(self):
        menu = tk.Menu(self, tearoff=0, font=F_PEQUE)
        rol = "Administrador" if self.controlador.es_admin else "Cajero"
        menu.add_command(label=f"{self.controlador.usuario_actual} · {rol}", state="disabled")
        menu.add_separator()
        if self.controlador.clave_por_defecto:
            menu.add_command(label="Cambiar contraseña (está usando la de fábrica)", command=self.mi_cuenta)
        else:
            menu.add_command(label="Mi cuenta", command=self.mi_cuenta)
        if self.controlador.puede("usuarios"):
            menu.add_command(label="Usuarios", command=self.gestionar_usuarios)
        if self.controlador.puede("configuracion"):
            menu.add_command(label="Configuración", command=self.configurar)
        menu.add_separator()
        menu.add_command(label="Cerrar sesión", command=self.salir)
        x = self.btn_usuario.winfo_rootx()
        y = self.btn_usuario.winfo_rooty() + self.btn_usuario.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def mi_cuenta(self):
        VentanaMiCuenta(self, self.controlador)

    def gestionar_usuarios(self):
        if self.controlador.puede("usuarios"):
            VentanaUsuarios(self, self.controlador)

    def configurar(self):
        if self.controlador.puede("configuracion"):
            VentanaConfiguracion(self, self.controlador)

    def actualizar_marca(self):
        """El nombre del negocio en la barra. Se vuelve a leer al guardar la configuración."""
        nombre = ajustes.obtener("negocio_nombre").upper()
        self.lbl_marca.config(text=nombre if len(nombre) <= 14 else nombre[:13] + "…",
                              font=(FUENTE, 14 if len(nombre) <= 11 else 11, "bold"))

    # ------------------------------------------------------------------ módulos
    def show_frames(self, clase):
        if clase not in self.pestanas:
            return
        self.actual = clase
        for c, b in self.pestanas.items():
            activo = c is clase
            b.config(bg=FONDO if activo else NAVY, fg=NAVY if activo else BLANCO,
                     activebackground=FONDO if activo else NAVY_HOVER, activeforeground=NAVY if activo else BLANCO)
        frame = self.frames[clase]
        frame.tkraise()
        if hasattr(frame, "al_mostrar"):
            frame.al_mostrar()

    def _atajo(self, numero):
        # Solo con la sesión abierta y sin una ventana emergente encima.
        clase = self.atajos.get(numero)
        if clase and self.controlador.usuario_actual and not self.grab_current():
            self.show_frames(clase)

    def al_mostrar(self):
        self._construir_pestanas()
        self.actualizar_reloj(programar=False)
        self.show_frames(self.actual)

    def actualizar_reloj(self, programar=True):
        usuario = self.controlador.usuario_actual or ""
        if usuario:
            # El rol va en el menú: en el botón no cabe sin cortar el nombre.
            aviso = " ⚠" if self.controlador.clave_por_defecto else ""
            self.btn_usuario.config(text=f"{usuario}{aviso}  ▾   {datetime.datetime.now():%H:%M}",
                                    fg=AMBAR if self.controlador.clave_por_defecto else TEXTO_CLARO)
        else:
            self.btn_usuario.config(text="")
        if programar:
            self._reloj = self.after(20_000, self.actualizar_reloj)

    def destroy(self):
        # Cancela la actualización pendiente del reloj al cerrar el programa.
        if getattr(self, "_reloj", None):
            self.after_cancel(self._reloj)
        super().destroy()

    def salir(self):
        ventas = self.frames[Ventas]
        pregunta = "¿Desea cerrar la sesión?"
        if ventas.carrito:
            pregunta = "Hay una venta sin cobrar. Si cierra la sesión se descartará.\n\n¿Desea cerrar la sesión?"
        if messagebox.askyesno("Cerrar sesión", pregunta, parent=self):
            ventas.vaciar(confirmar=False)
            self.actual = Ventas
            self.controlador.cerrar_sesion()
