import tkinter as tk

import config
from estilos import FONDO, configurar_estilos
from login import Login, Registro
from container import Container


class Manager(tk.Tk):
    """Ventana principal: cambia entre el inicio de sesión y el sistema."""

    ANCHO, ALTO = 1100, 650

    def __init__(self, aviso_inicial=None):
        super().__init__()
        self.title(f"{config.NEGOCIO['nombre']} · Sistema de facturación e inventario v{config.VERSION}")
        x = max((self.winfo_screenwidth() - self.ANCHO) // 2, 0)
        y = max((self.winfo_screenheight() - self.ALTO) // 2 - 30, 0)
        self.geometry(f"{self.ANCHO}x{self.ALTO}+{x}+{y}")
        self.resizable(False, False)
        self.configure(bg=FONDO)
        try:
            self.iconbitmap("imagenes/icono.ico")
        except tk.TclError:
            pass
        configurar_estilos(self)

        self.usuario_actual = None
        self.rol_actual = None
        self.clave_por_defecto = False
        contenedor = tk.Frame(self, bg=FONDO)
        contenedor.pack(fill="both", expand=True)

        self.frames = {}
        for F in (Login, Registro, Container):
            self.frames[F] = F(contenedor, self)

        self.show_frame(Login)
        if aviso_inicial:
            self.frames[Login].mostrar_mensaje(aviso_inicial, error=False)

    def show_frame(self, clase):
        frame = self.frames[clase]
        frame.tkraise()
        if hasattr(frame, "al_mostrar"):
            frame.al_mostrar()

    def puede(self, permiso):
        """True si el rol de quien tiene la sesión abierta puede hacer esto."""
        return permiso in config.PERMISOS.get(self.rol_actual, set())

    @property
    def es_admin(self):
        return self.rol_actual == "admin"

    def iniciar_sesion(self, usuario, rol="cajero", clave_por_defecto=False):
        self.usuario_actual = usuario
        self.rol_actual = rol
        self.clave_por_defecto = clave_por_defecto
        self.show_frame(Container)

    def cerrar_sesion(self):
        self.usuario_actual = None
        self.rol_actual = None
        self.clave_por_defecto = False
        self.show_frame(Login)


def main():
    Manager().mainloop()


if __name__ == "__main__":
    main()
