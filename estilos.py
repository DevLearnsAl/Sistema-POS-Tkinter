"""Tema visual de la aplicación: colores, fuentes y fábricas de widgets.

Todas las pantallas usan estas funciones, así el sistema se ve igual en todas
partes y un cambio de color se hace en un solo lugar."""
import tkinter as tk
from tkinter import ttk

# El formato de los montos depende del negocio (símbolo y decimales), así que
# vive en ajustes.py. Se reexporta acá porque todas las pantallas ya lo piden a
# este módulo. `ajustes` no importa `estilos`, así que no hay círculo.
from ajustes import moneda  # noqa: F401  (reexportado a propósito)

FUENTE = "Segoe UI"

# Paleta
NAVY = "#1D3F7A"
NAVY_OSCURO = "#152E59"
NAVY_HOVER = "#2A5298"
FONDO = "#F3F5F9"
BLANCO = "#FFFFFF"
BORDE = "#D6DDE8"
TEXTO = "#1B2433"
TEXTO_SUAVE = "#4A5568"
TEXTO_CLARO = "#C9D6EA"
VERDE = "#1E7B4A"
VERDE_HOVER = "#17633B"
VERDE_FONDO = "#E3F1E8"
ROJO = "#B42318"
ROJO_HOVER = "#8F1C13"
ROJO_FONDO = "#FBE9E7"
AMBAR = "#9A6200"
AMBAR_FONDO = "#FDF1DC"
CLARO = "#E6ECF5"
CLARO_HOVER = "#D5DFEE"
GRIS_FONDO = "#ECEFF3"
FILA_PAR = "#F7F9FC"
SELECCION = "#CFE0F7"

# Fuentes
F_NORMAL = (FUENTE, 11)
F_PEQUE = (FUENTE, 10)
F_NEGRITA = (FUENTE, 11, "bold")
F_SUBTITULO = (FUENTE, 13, "bold")
F_TITULO = (FUENTE, 18, "bold")
F_GRANDE = (FUENTE, 26, "bold")
F_CAMPO = (FUENTE, 12)

TIPOS_BOTON = {
    "primario": (NAVY, "white", NAVY_HOVER),
    "exito": (VERDE, "white", VERDE_HOVER),
    "peligro": (ROJO, "white", ROJO_HOVER),
    "secundario": (CLARO, NAVY, CLARO_HOVER),
}


def boton(padre, texto, comando, tipo="primario", fuente=F_NEGRITA):
    """Botón plano con color según el tipo y efecto al pasar el mouse."""
    fondo, letra, hover = TIPOS_BOTON[tipo]
    b = tk.Button(padre, text=texto, command=comando, bg=fondo, fg=letra, activebackground=hover,
                  activeforeground=letra, font=fuente, relief="flat", bd=0, cursor="hand2",
                  highlightthickness=0, disabledforeground="#9AA3B2")
    b.colores = (fondo, letra, hover)
    b.bind("<Enter>", lambda e: b.config(bg=b.colores[2]) if str(b["state"]) != "disabled" else None)
    b.bind("<Leave>", lambda e: b.config(bg=b.colores[0]))
    return b


def cambiar_tipo(b, tipo):
    """Cambia el color de un botón ya creado (se usa en los botones de selección)."""
    b.colores = TIPOS_BOTON[tipo]
    b.config(bg=b.colores[0], fg=b.colores[1], activebackground=b.colores[2], activeforeground=b.colores[1])


def panel(padre, titulo=None, bg=BLANCO):
    """Recuadro blanco con borde fino y título opcional."""
    p = tk.Frame(padre, bg=bg, highlightthickness=1, highlightbackground=BORDE, highlightcolor=BORDE)
    if titulo:
        p.titulo = tk.Label(p, text=titulo, font=F_SUBTITULO, fg=NAVY, bg=bg)
        p.titulo.place(x=16, y=10)
    return p


def etiqueta(padre, texto="", fuente=F_NORMAL, fg=TEXTO, bg=BLANCO, **kw):
    return tk.Label(padre, text=texto, font=fuente, fg=fg, bg=bg, **kw)


def campo(padre, **kw):
    return ttk.Entry(padre, font=F_CAMPO, **kw)


def lista(padre, **kw):
    return ttk.Combobox(padre, font=F_CAMPO, **kw)


def tabla(padre, columnas, bg=BLANCO, estilo="Treeview"):
    """Crea una tabla con barra de desplazamiento.

    columnas: lista de (id, título, ancho, alineación) con alineación "w", "center" o "e".
    Devuelve (marco, tree): el marco se posiciona y el tree se llena."""
    marco = tk.Frame(padre, bg=bg)
    barra = ttk.Scrollbar(marco, orient="vertical")
    tree = ttk.Treeview(marco, columns=[c[0] for c in columnas], show="headings", style=estilo,
                        yscrollcommand=barra.set, selectmode="browse")
    barra.config(command=tree.yview)
    barra.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    for cid, titulo, ancho, alineacion in columnas:
        tree.heading(cid, text=titulo, anchor=alineacion)
        tree.column(cid, width=ancho, minwidth=30, anchor=alineacion, stretch=True)
    tree.tag_configure("par", background=FILA_PAR)
    tree.tag_configure("anulada", foreground="#9AA3B2")
    tree.tag_configure("alerta", foreground=ROJO)
    return marco, tree


def llenar_tabla(tree, filas, etiquetas=None):
    """Reemplaza el contenido de la tabla. etiquetas(fila) puede devolver tags extra."""
    tree.delete(*tree.get_children())
    for i, fila in enumerate(filas):
        tags = ["par"] if i % 2 else []
        if etiquetas:
            tags += etiquetas(fila)
        tree.insert("", "end", values=fila, tags=tags)


def centrar(ventana, ancho, alto):
    """Centra una ventana emergente sobre la ventana principal."""
    raiz = ventana.master.winfo_toplevel()
    raiz.update_idletasks()
    x = raiz.winfo_rootx() + (raiz.winfo_width() - ancho) // 2
    y = raiz.winfo_rooty() + (raiz.winfo_height() - alto) // 2
    ventana.geometry(f"{ancho}x{alto}+{max(x, 0)}+{max(y, 0)}")


def ventana_modal(padre, titulo, ancho, alto, bg=BLANCO):
    """Ventana emergente que bloquea la principal hasta que se cierra."""
    top = tk.Toplevel(padre)
    top.title(titulo)
    top.configure(bg=bg)
    top.resizable(False, False)
    centrar(top, ancho, alto)
    top.transient(padre.winfo_toplevel())
    top.grab_set()
    top.focus_set()
    return top


def configurar_estilos(raiz):
    s = ttk.Style(raiz)
    s.theme_use("clam")
    s.configure(".", font=F_NORMAL, background=BLANCO, foreground=TEXTO)

    s.configure("TEntry", fieldbackground=BLANCO, foreground=TEXTO, bordercolor=BORDE, lightcolor=BORDE,
                darkcolor=BORDE, insertcolor=TEXTO, padding=(8, 4))
    s.map("TEntry", bordercolor=[("focus", NAVY)], lightcolor=[("focus", NAVY)], darkcolor=[("focus", NAVY)],
          fieldbackground=[("disabled", FONDO)])

    for estilo in ("TCombobox", "TSpinbox"):
        s.configure(estilo, fieldbackground=BLANCO, background=CLARO, foreground=TEXTO, bordercolor=BORDE,
                    lightcolor=BORDE, darkcolor=BORDE, arrowcolor=NAVY, arrowsize=14, padding=(8, 4),
                    insertcolor=TEXTO)
        s.map(estilo, bordercolor=[("focus", NAVY)], lightcolor=[("focus", NAVY)], darkcolor=[("focus", NAVY)],
              fieldbackground=[("readonly", BLANCO), ("disabled", FONDO)], background=[("active", CLARO_HOVER)],
              selectbackground=[("readonly", BLANCO)], selectforeground=[("readonly", TEXTO)])

    s.configure("Treeview", background=BLANCO, fieldbackground=BLANCO, foreground=TEXTO, rowheight=30,
                font=F_NORMAL, bordercolor=BORDE, lightcolor=BORDE, darkcolor=BORDE, borderwidth=0)
    s.map("Treeview", background=[("selected", SELECCION)], foreground=[("selected", TEXTO)])
    s.configure("Treeview.Heading", background=NAVY, foreground="white", font=F_NEGRITA, relief="flat",
                borderwidth=0, padding=(8, 7))
    s.map("Treeview.Heading", background=[("active", NAVY_HOVER)], relief=[("pressed", "flat")])
    s.configure("Compacta.Treeview", rowheight=26)

    s.configure("Vertical.TScrollbar", troughcolor=FONDO, background="#C3CCDA", bordercolor=FONDO,
                lightcolor="#C3CCDA", darkcolor="#C3CCDA", arrowcolor=NAVY, gripcount=0)
    s.map("Vertical.TScrollbar", background=[("active", "#AAB6C8")])

    raiz.option_add("*TCombobox*Listbox.font", F_NORMAL)
    raiz.option_add("*TCombobox*Listbox.selectBackground", NAVY)
    raiz.option_add("*TCombobox*Listbox.selectForeground", "white")
