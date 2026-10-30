import tkinter as tk
from tkinter import messagebox

import ajustes
import config
import registro
from estilos import FONDO, configurar_estilos
from login import Login
from container import Container


class Manager(tk.Tk):
    """Ventana principal: cambia entre el inicio de sesión y el sistema."""

    ANCHO, ALTO = 1100, 650

    def __init__(self, aviso_inicial=None):
        super().__init__()
        registro.iniciar()
        # La configuración del negocio se lee una vez, antes de armar las pantallas:
        # varias toman de ahí sus textos (nombre, moneda, nombre del impuesto).
        ajustes.cargar()
        self.title(f"{ajustes.obtener('negocio_nombre')} · Sistema de facturación e inventario "
                   f"v{config.VERSION}")
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
        self.clave_insegura = False
        contenedor = tk.Frame(self, bg=FONDO)
        contenedor.pack(fill="both", expand=True)

        self.frames = {}
        for F in (Login, Container):
            self.frames[F] = F(contenedor, self)

        self.show_frame(Login)
        if aviso_inicial:
            self.frames[Login].mostrar_mensaje(aviso_inicial, error=False)

    def report_callback_exception(self, tipo, valor, rastro):
        """Cualquier error que no se haya atrapado antes cae acá.

        Tkinter, por su cuenta, lo escribiría en una consola que el usuario no ve.
        Así queda en el archivo de registro y la persona recibe un aviso claro en
        vez de una ventana que no responde."""
        registro.error("Error no controlado en la interfaz", valor)
        messagebox.showerror("Error inesperado",
                             f"Ocurrió un error inesperado:\n\n{valor}\n\n"
                             f"Quedó anotado en {registro.ARCHIVO}. Si se repite, pasale ese archivo "
                             "a quien da el soporte.", parent=self)

    def actualizar_titulo(self):
        self.title(f"{ajustes.obtener('negocio_nombre')} · Sistema de facturación e inventario "
                   f"v{config.VERSION}")

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

    def iniciar_sesion(self, usuario, rol="cajero", clave_insegura=False):
        self.usuario_actual = usuario
        self.rol_actual = rol
        self.clave_insegura = clave_insegura
        self.show_frame(Container)

    def cerrar_sesion(self):
        self.usuario_actual = None
        self.rol_actual = None
        self.clave_insegura = False
        self.show_frame(Login)


def main():
    Manager().mainloop()


if __name__ == "__main__":
    main()
