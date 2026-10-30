import csv
import datetime
import os
import re
import sqlite3
import tkinter as tk
import unicodedata
import uuid
from tkinter import ttk, messagebox, filedialog

from PIL import Image, ImageOps, ImageTk

import ajustes
import db
from estilos import (FONDO, BLANCO, BORDE, NAVY, TEXTO, TEXTO_SUAVE, VERDE, VERDE_FONDO, ROJO, ROJO_FONDO, AMBAR,
                     AMBAR_FONDO, GRIS_FONDO, CLARO, FUENTE, F_PEQUE, F_NEGRITA, F_SUBTITULO, F_TITULO, moneda,
                     boton, cambiar_tipo, panel, etiqueta, campo, lista, ventana_modal)
from utilidades import codigo_interno

CARPETA_FOTOS = "fotos"
FOTO_DEFECTO = os.path.join(CARPETA_FOTOS, "default.png")
COLUMNAS = ["id", "codigo", "articulo", "precio", "costo", "stock", "stock_minimo", "iva", "estado", "image_path"]
FILTROS = ["Todos", "Stock bajo", "Inactivos"]


def estado_stock(p):
    """Texto y colores de la etiqueta de stock de un producto."""
    if p["estado"] == "Inactivo":
        return "Inactivo", TEXTO_SUAVE, GRIS_FONDO
    if p["stock"] == 0:
        return "Agotado", ROJO, ROJO_FONDO
    if p["stock"] <= p["stock_minimo"]:
        return f"Stock bajo · {p['stock']}", AMBAR, AMBAR_FONDO
    return f"Stock: {p['stock']}", VERDE, VERDE_FONDO


class Inventario(tk.Frame):
    def __init__(self, padre, controlador):
        super().__init__(padre, bg=FONDO)
        self.controlador = controlador
        self.productos = []
        self.seleccionado = None
        self.filtro = "Todos"
        self.timer = None
        self.imagenes = {}      # caché de imágenes: Tkinter necesita guardar la referencia
        self.tarjetas = {}
        os.makedirs(CARPETA_FOTOS, exist_ok=True)
        self.widgets()

    # ------------------------------------------------------------------ interfaz
    def widgets(self):
        barra = panel(self)
        barra.place(x=16, y=16, width=1068, height=64)
        etiqueta(barra, "Buscar", F_NEGRITA, TEXTO).place(x=16, y=20)
        self.entry_buscar = campo(barra)
        self.entry_buscar.place(x=80, y=14, width=280, height=36)
        self.entry_buscar.bind("<KeyRelease>", self._programar_busqueda)
        self.btns_filtro = {}
        for i, nombre in enumerate(FILTROS):
            b = boton(barra, nombre, lambda n=nombre: self.cambiar_filtro(n),
                      "primario" if nombre == self.filtro else "secundario")
            b.place(x=380 + i * 118, y=14, width=110, height=36)
            self.btns_filtro[nombre] = b
        boton(barra, "Exportar CSV", self.exportar, "secundario").place(x=734, y=14, width=116, height=36)
        self.btn_editar = boton(barra, "Editar", self.editar_articulo, "secundario")
        self.btn_editar.place(x=860, y=14, width=90, height=36)
        self.btn_nuevo = boton(barra, "Nuevo", self.agregar_articulo)
        self.btn_nuevo.place(x=960, y=14, width=92, height=36)

        cont = panel(self, "Productos")
        cont.place(x=16, y=92, width=740, height=498)
        self.lbl_conteo = etiqueta(cont, "", F_PEQUE, TEXTO_SUAVE)
        self.lbl_conteo.place(x=722, y=16, anchor="ne")
        self.canvas = tk.Canvas(cont, bg=BLANCO, highlightthickness=0)
        self.barra = ttk.Scrollbar(cont, orient="vertical", command=self.canvas.yview)
        self.grilla = tk.Frame(self.canvas, bg=BLANCO)
        self.grilla.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.grilla, anchor="nw")
        self.canvas.configure(yscrollcommand=self.barra.set)
        self.canvas.place(x=8, y=44, width=712, height=446)
        self.barra.place(x=722, y=44, width=14, height=446)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._rueda))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        det = panel(self, "Detalle")
        det.place(x=772, y=92, width=312, height=498)
        self.det_vacio = etiqueta(det, "Seleccione un producto para ver su detalle.", F_PEQUE, TEXTO_SUAVE,
                                  wraplength=280, justify="left")
        self.det = tk.Frame(det, bg=BLANCO)
        self.det_img = tk.Label(self.det, bg=BLANCO)
        self.det_img.place(x=15, y=0, width=120, height=120)
        self.det_nombre = etiqueta(self.det, "", F_NEGRITA, TEXTO, wraplength=150, justify="left", anchor="nw")
        self.det_nombre.place(x=147, y=4, width=150, height=60)
        self.det_codigo = etiqueta(self.det, "", F_PEQUE, TEXTO_SUAVE, justify="left", anchor="nw")
        self.det_codigo.place(x=147, y=66)
        self.det_badge = tk.Label(self.det, font=(FUENTE, 9, "bold"), padx=8, pady=2)
        self.det_badge.place(x=147, y=94)
        self.det_valores = {}
        for i, clave in enumerate(["Precio", "Costo", "Margen", "Stock", "Stock mínimo", "Impuesto", "Estado"]):
            y = 138 + i * 30
            etiqueta(self.det, clave, F_PEQUE, TEXTO_SUAVE).place(x=15, y=y)
            v = etiqueta(self.det, "", F_NEGRITA, TEXTO)
            v.place(x=295, y=y - 2, anchor="ne")
            self.det_valores[clave] = v
        self.btn_editar_detalle = boton(self.det, "Editar producto", self.editar_articulo)
        self.btn_editar_detalle.place(x=15, y=356, width=280, height=40)

    def _rueda(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    # ------------------------------------------------------------------ datos
    def al_mostrar(self):
        # El cajero consulta precios y existencias, pero no cambia el catálogo.
        estado = "normal" if self.controlador.puede("editar_inventario") else "disabled"
        for b in (self.btn_editar, self.btn_nuevo, self.btn_editar_detalle):
            b.config(state=estado)
        self.refrescar()

    def _programar_busqueda(self, event=None):
        if self.timer:
            self.after_cancel(self.timer)
        self.timer = self.after(250, self.refrescar)

    def cambiar_filtro(self, nombre):
        self.filtro = nombre
        for n, b in self.btns_filtro.items():
            cambiar_tipo(b, "primario" if n == nombre else "secundario")
        self.refrescar()

    def _pasa_filtro(self, p):
        if self.filtro == "Stock bajo":
            return p["estado"] == "Activo" and p["stock"] <= p["stock_minimo"]
        if self.filtro == "Inactivos":
            return p["estado"] == "Inactivo"
        return True

    def refrescar(self):
        self.timer = None
        filas = db.consultar(f"SELECT {', '.join(COLUMNAS)} FROM articulos ORDER BY articulo")
        self.productos = [dict(zip(COLUMNAS, f)) for f in filas]
        texto = self.entry_buscar.get().strip().lower()
        visibles = [p for p in self.productos
                    if (not texto or texto in p["articulo"].lower() or texto in (p["codigo"] or ""))
                    and self._pasa_filtro(p)]

        for w in self.grilla.winfo_children():
            w.destroy()
        self.tarjetas = {}
        for i, p in enumerate(visibles):
            self.tarjeta(p, i // 4, i % 4)
        if not visibles:
            etiqueta(self.grilla, "No hay productos que coincidan con la búsqueda.", F_PEQUE, TEXTO_SUAVE).grid(
                row=0, column=0, padx=16, pady=16)
        self.lbl_conteo.config(text=f"{len(visibles)} de {len(self.productos)} productos")
        self.canvas.yview_moveto(0)
        if self.seleccionado not in {p["id"] for p in self.productos}:
            self.seleccionado = None
        self.mostrar_detalle()

    def imagen(self, ruta, lado):
        clave = (ruta, lado)
        if clave not in self.imagenes:
            try:
                img = Image.open(ruta if ruta and os.path.exists(ruta) else FOTO_DEFECTO)
            except OSError:
                img = Image.open(FOTO_DEFECTO)
            self.imagenes[clave] = ImageTk.PhotoImage(ImageOps.fit(img.convert("RGB"), (lado, lado)))
        return self.imagenes[clave]

    def tarjeta(self, p, fila, columna):
        sel = p["id"] == self.seleccionado
        f = tk.Frame(self.grilla, bg=BLANCO, cursor="hand2", highlightthickness=2,
                     highlightbackground=NAVY if sel else BORDE)
        f.grid(row=fila, column=columna, padx=6, pady=6)
        tk.Label(f, image=self.imagen(p["image_path"], 128), bg=BLANCO).pack(padx=14, pady=(12, 6))
        tk.Label(f, text=p["articulo"], font=(FUENTE, 10, "bold"), fg=TEXTO, bg=BLANCO, wraplength=140,
                 justify="center", height=2).pack(padx=8)
        tk.Label(f, text=moneda(p["precio"]), font=(FUENTE, 12, "bold"), fg=NAVY, bg=BLANCO).pack()
        texto, fg, bg = estado_stock(p)
        tk.Label(f, text=texto, font=(FUENTE, 9, "bold"), fg=fg, bg=bg, padx=8, pady=2).pack(pady=(4, 12))
        for w in (f, *f.winfo_children()):
            w.bind("<Button-1>", lambda e, i=p["id"]: self.seleccionar(i))
            w.bind("<Double-1>", lambda e, i=p["id"]: self._editar_id(i))
        self.tarjetas[p["id"]] = f

    def seleccionar(self, id_producto):
        self.seleccionado = id_producto
        for i, f in self.tarjetas.items():
            f.config(highlightbackground=NAVY if i == id_producto else BORDE)
        self.mostrar_detalle()

    def producto(self, id_producto):
        return next((p for p in self.productos if p["id"] == id_producto), None)

    def mostrar_detalle(self):
        p = self.producto(self.seleccionado)
        if p is None:
            self.det.place_forget()
            self.det_vacio.place(x=16, y=48)
            return
        self.det_vacio.place_forget()
        self.det.place(x=1, y=44, width=310, height=450)
        self.det_img.config(image=self.imagen(p["image_path"], 120))
        self.det_nombre.config(text=p["articulo"])
        self.det_codigo.config(text=f"Código: {p['codigo']}" if p["codigo"] else "Sin código de barras")
        texto, fg, bg = estado_stock(p)
        self.det_badge.config(text=texto, fg=fg, bg=bg)
        precio_sin_iva = p["precio"] / (1 + p["iva"] / 100)
        margen = (precio_sin_iva - p["costo"]) / precio_sin_iva * 100 if precio_sin_iva else 0
        valores = {"Precio": moneda(p["precio"]), "Costo": moneda(p["costo"]), "Margen": f"{margen:.1f} %",
                   "Stock": f"{p['stock']} unidades", "Stock mínimo": str(p["stock_minimo"]),
                   "Impuesto": f"Gravado {p['iva']:g} %" if p["iva"] else "Exento", "Estado": p["estado"]}
        for clave, valor in valores.items():
            self.det_valores[clave].config(text=valor, fg=TEXTO)
        self.det_valores["Estado"].config(fg=VERDE if p["estado"] == "Activo" else ROJO)
        self.det_valores["Margen"].config(fg=ROJO if margen < 0 else TEXTO)

    # ------------------------------------------------------------------ acciones
    def _puede_editar(self):
        if self.controlador.puede("editar_inventario"):
            return True
        messagebox.showwarning("Inventario", "Solo un administrador puede crear o editar productos.", parent=self)
        return False

    def agregar_articulo(self):
        if self._puede_editar():
            FormularioProducto(self)

    def editar_articulo(self):
        if not self._puede_editar():
            return
        p = self.producto(self.seleccionado)
        if p is None:
            messagebox.showwarning("Inventario", "Seleccione un producto (haga clic en su tarjeta).", parent=self)
            return
        FormularioProducto(self, p)

    def exportar(self):
        """Guarda el inventario completo en un CSV que abre Excel."""
        filas = db.consultar("SELECT codigo, articulo, precio, costo, stock, stock_minimo, iva, estado "
                             "FROM articulos ORDER BY articulo")
        os.makedirs("reportes", exist_ok=True)
        ruta = os.path.join("reportes", f"inventario_{datetime.date.today().isoformat()}.csv")
        # utf-8-sig: Excel abre bien las tildes.
        with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
            w = csv.writer(archivo)
            w.writerow(["Código", "Producto", "Precio", "Costo", "Stock", "Stock mínimo", "IVA", "Estado",
                        "Valor del stock al costo"])
            for f in filas:
                w.writerow(list(f) + [round(f[3] * f[4], 2)])
        if messagebox.askyesno("Inventario exportado", f"Se exportaron {len(filas)} productos a:\n{ruta}\n\n"
                                                       "¿Abrir la carpeta?", parent=self):
            os.startfile(os.path.abspath("reportes"))

    def _editar_id(self, id_producto):
        self.seleccionar(id_producto)
        self.editar_articulo()


def _nombre_archivo(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")[:40] or "producto"


class FormularioProducto:
    """Mismo formulario para crear y para editar un producto."""


    def __init__(self, inventario, producto=None):
        self.inv = inventario
        self.producto = producto
        self.imagen_nueva = None
        # La tasa sale de la configuración: el mismo programa sirve con otro impuesto.
        self.opciones_iva = [f"Gravado {ajustes.tasa_impuesto():g} %", "Exento"]
        titulo = "Editar producto" if producto else "Nuevo producto"
        top = self.top = ventana_modal(inventario, titulo, 720, 520)
        top.formulario = self
        etiqueta(top, titulo, F_TITULO, TEXTO).place(x=28, y=18)

        self.e = {}
        self._fila("articulo", "Nombre del producto *", 28, 70, 416)
        self._fila("codigo", "Código de barras", 28, 140, 300)
        boton(top, "Generar código", self.generar_codigo, "secundario", F_PEQUE).place(x=336, y=160, width=108, height=36)
        self._fila("precio", f"Precio de venta ({ajustes.simbolo()}, {ajustes.nombre_impuesto()} incluido) *",
                   28, 210, 200)
        self._fila("costo", f"Costo ({ajustes.simbolo()}) *", 244, 210, 200)
        self._fila("stock", "Stock *", 28, 280, 200)
        self._fila("stock_minimo", "Stock mínimo (alerta)", 244, 280, 200)
        self._fila("iva", ajustes.nombre_impuesto(), 28, 350, 200,
                   lista(top, values=self.opciones_iva, state="readonly"))
        self._fila("estado", "Estado", 244, 350, 200, lista(top, values=["Activo", "Inactivo"], state="readonly"))

        marco = tk.Frame(top, bg=CLARO, highlightthickness=1, highlightbackground=BORDE)
        marco.place(x=480, y=70, width=210, height=210)
        self.lbl_img = tk.Label(marco, bg=CLARO)
        self.lbl_img.place(relx=0.5, rely=0.5, anchor="center")
        boton(top, "Cargar imagen", self.cargar_imagen, "secundario").place(x=480, y=292, width=210, height=36)

        self.lbl_error = etiqueta(top, "", F_PEQUE, ROJO, wraplength=416, justify="left")
        self.lbl_error.place(x=28, y=424)
        boton(top, "Cancelar", top.destroy, "secundario").place(x=400, y=458, width=130, height=42)
        self.btn_guardar = boton(top, "Guardar", self.guardar)
        self.btn_guardar.place(x=540, y=458, width=150, height=42)
        top.bind("<Escape>", lambda e: top.destroy())

        if producto:
            for clave in ("articulo", "codigo"):
                self.e[clave].insert(0, producto[clave] or "")
            self.e["precio"].insert(0, f"{producto['precio']:.2f}")
            self.e["costo"].insert(0, f"{producto['costo']:.2f}")
            self.e["stock"].insert(0, str(producto["stock"]))
            self.e["stock_minimo"].insert(0, str(producto["stock_minimo"]))
            self.e["iva"].set(self.opciones_iva[0] if producto["iva"] else self.opciones_iva[1])
            self.e["estado"].set(producto["estado"])
        else:
            self.e["stock"].insert(0, "0")
            self.e["stock_minimo"].insert(0, "5")
            self.e["iva"].set(self.opciones_iva[0])
            self.e["estado"].set("Activo")
        self.mostrar_imagen(producto["image_path"] if producto else None)
        self.e["articulo"].focus_set()

    def _fila(self, clave, texto, x, y, ancho, widget=None):
        etiqueta(self.top, texto, F_PEQUE, TEXTO_SUAVE).place(x=x, y=y)
        w = widget or campo(self.top)
        w.place(x=x, y=y + 20, width=ancho, height=36)
        if widget is None:
            w.bind("<Return>", lambda e: self.guardar())
        self.e[clave] = w

    def mostrar_imagen(self, ruta):
        try:
            img = Image.open(ruta if ruta and os.path.exists(ruta) else FOTO_DEFECTO)
        except OSError:
            img = Image.open(FOTO_DEFECTO)
        self.foto = ImageTk.PhotoImage(ImageOps.fit(img.convert("RGB"), (200, 200)))
        self.lbl_img.config(image=self.foto)

    def cargar_imagen(self):
        ruta = filedialog.askopenfilename(parent=self.top, title="Elegir imagen del producto",
                                          filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")])
        if ruta:
            self.imagen_nueva = ruta
            self.mostrar_imagen(ruta)

    def generar_codigo(self):
        usados = {f[0] for f in db.consultar("SELECT codigo FROM articulos WHERE codigo LIKE '200%'")}
        numero = 1
        while codigo_interno(numero) in usados:
            numero += 1
        self.e["codigo"].delete(0, "end")
        self.e["codigo"].insert(0, codigo_interno(numero))

    def guardar(self):
        v = {clave: w.get().strip() for clave, w in self.e.items()}
        try:
            if not v["articulo"]:
                raise ValueError("Escriba el nombre del producto.")
            precio = round(float(v["precio"].replace(",", "")), 2)
            costo = round(float(v["costo"].replace(",", "")), 2)
            stock = int(v["stock"])
            minimo = int(v["stock_minimo"] or 0)
        except ValueError as e:
            self.lbl_error.config(text=str(e) if "nombre" in str(e) else
                                  "Revise los números: precio y costo con decimales (ej. 25.50); stock y stock "
                                  "mínimo enteros.")
            return
        if precio <= 0 or costo < 0 or stock < 0 or minimo < 0:
            self.lbl_error.config(text="El precio debe ser mayor que 0; costo, stock y stock mínimo no pueden ser "
                                       "negativos.")
            return
        codigo = v["codigo"] or None
        if codigo and not re.fullmatch(r"[0-9A-Za-z-]{1,20}", codigo):
            self.lbl_error.config(text="El código solo puede tener letras, números y guiones (máximo 20).")
            return
        iva = ajustes.tasa_impuesto() if v["iva"] == self.opciones_iva[0] else 0

        ruta = self.producto["image_path"] if self.producto else FOTO_DEFECTO
        if self.imagen_nueva:
            try:
                img = ImageOps.fit(Image.open(self.imagen_nueva).convert("RGB"), (300, 300))
                # Nombre único: dos productos con una foto llamada igual no se pisan.
                ruta = os.path.join(CARPETA_FOTOS, f"{_nombre_archivo(v['articulo'])}_{uuid.uuid4().hex[:6]}.png")
                img.save(ruta)
            except OSError as e:
                self.lbl_error.config(text=f"No se pudo usar esa imagen: {e}")
                return

        datos = (codigo, v["articulo"], precio, costo, stock, minimo, iva, v["estado"], ruta)
        try:
            with db.conectar() as conn:
                if self.producto:
                    conn.execute("UPDATE articulos SET codigo = ?, articulo = ?, precio = ?, costo = ?, stock = ?, "
                                 "stock_minimo = ?, iva = ?, estado = ?, image_path = ? WHERE id = ?",
                                 datos + (self.producto["id"],))
                    id_producto = self.producto["id"]
                else:
                    cur = conn.execute("INSERT INTO articulos (codigo, articulo, precio, costo, stock, stock_minimo, "
                                       "iva, estado, image_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", datos)
                    id_producto = cur.lastrowid
        except sqlite3.IntegrityError as e:
            texto = str(e)
            if "articulos.articulo" in texto:
                self.lbl_error.config(text="Ya existe un producto con ese nombre.")
            elif "articulos.codigo" in texto:
                self.lbl_error.config(text="Ese código de barras ya está asignado a otro producto.")
            else:
                self.lbl_error.config(text=f"Datos no válidos: {texto}")
            return
        except sqlite3.Error as e:
            self.lbl_error.config(text=f"No se pudo guardar: {e}")
            return

        self.top.destroy()
        self.inv.seleccionado = id_producto
        self.inv.refrescar()
