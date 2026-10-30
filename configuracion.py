"""Pantalla de configuración del negocio (solo administradores).

Es lo que permite instalar el mismo programa en cualquier negocio: nombre, RUC,
logo, moneda, impuesto y textos de la factura se cambian desde acá, sin tocar
una línea de código. Los valores se guardan en la tabla `configuracion`; la
lectura está en `ajustes.py`.
"""
import os
import shutil
import sqlite3
import tkinter as tk
from tkinter import messagebox, filedialog

from PIL import Image, ImageOps, ImageTk

import ajustes
import db
import registro
from estilos import (BLANCO, BORDE, CLARO, NAVY, TEXTO, TEXTO_SUAVE, VERDE, ROJO, FUENTE, F_PEQUE, F_NEGRITA,
                     F_SUBTITULO, F_TITULO, boton, etiqueta, campo, ventana_modal)

CARPETA_LOGO = "imagenes"
ALTO_FILA = 58


class VentanaConfiguracion:
    def __init__(self, padre, controlador):
        self.controlador = controlador
        self.logo_nuevo = None
        self.quitar_logo = False
        top = self.top = ventana_modal(padre, "Configuración", 860, 692)
        etiqueta(top, "Configuración", F_TITULO, TEXTO).place(x=28, y=20)
        etiqueta(top, "Estos datos salen en la factura y en las pantallas. Son de este negocio, no del programa.",
                 F_PEQUE, TEXTO_SUAVE, wraplength=800, justify="left").place(x=28, y=58)

        self.e = {}
        self._titulo("Negocio", 28, 92)
        self._campo("negocio_nombre", "Nombre *", 28, 116)
        self._campo("negocio_ruc", "RUC", 28, 116 + ALTO_FILA)
        self._campo("negocio_direccion", "Dirección", 28, 116 + ALTO_FILA * 2)
        self._campo("negocio_telefono", "Teléfono", 28, 116 + ALTO_FILA * 3)
        self._campo("negocio_correo", "Correo", 28, 116 + ALTO_FILA * 4)
        self._logo(28, 116 + ALTO_FILA * 5)

        self._titulo("Moneda", 452, 92)
        self._campo("moneda_simbolo", "Símbolo *", 452, 116, ancho=120)
        self._campo("moneda_decimales", "Decimales", 592, 116, ancho=120)
        self._campo("moneda_billetes", "Billetes para el cobro rápido (separados por coma)", 452, 116 + ALTO_FILA,
                    ancho=380)

        self._titulo("Impuesto", 452, 116 + ALTO_FILA * 2 + 4)
        self._campo("impuesto_nombre", "Nombre *", 452, 116 + ALTO_FILA * 3, ancho=180)
        self._campo("impuesto_tasa", "Tasa general (%)", 652, 116 + ALTO_FILA * 3, ancho=180)
        self.aplicar_tasa = tk.BooleanVar(value=False)
        tk.Checkbutton(top, text="Aplicar la tasa nueva a los productos gravados", variable=self.aplicar_tasa,
                       font=F_PEQUE, bg=BLANCO, fg=TEXTO_SUAVE, activebackground=BLANCO, highlightthickness=0,
                       anchor="w").place(x=449, y=116 + ALTO_FILA * 4, width=390, height=24)

        self._titulo("Factura y acceso", 452, 116 + ALTO_FILA * 4 + 32)
        self._campo("factura_despedida", "Despedida en la factura", 452, 116 + ALTO_FILA * 5 + 4, ancho=380)
        self._campo("factura_nota", "Nota al pie", 452, 116 + ALTO_FILA * 6 + 4, ancho=380)
        self._campo("codigo_registro", "Código para registrar usuarios *", 452, 116 + ALTO_FILA * 7 + 4, ancho=380)

        self.lbl_mensaje = etiqueta(top, "", F_PEQUE, ROJO, wraplength=800, justify="left")
        self.lbl_mensaje.place(x=28, y=596)
        boton(top, "Cancelar", top.destroy, "secundario").place(x=560, y=628, width=130, height=44)
        boton(top, "Guardar", self.guardar, "primario", (FUENTE, 12, "bold")).place(x=702, y=628, width=130, height=44)
        top.bind("<Escape>", lambda e: top.destroy())
        self.cargar()
        self.e["negocio_nombre"].focus_set()

    # ------------------------------------------------------------------ interfaz
    def _titulo(self, texto, x, y):
        etiqueta(self.top, texto, F_SUBTITULO, NAVY).place(x=x, y=y)

    def _campo(self, clave, texto, x, y, ancho=380):
        etiqueta(self.top, texto, F_PEQUE, TEXTO_SUAVE).place(x=x, y=y)
        entrada = campo(self.top)
        entrada.place(x=x, y=y + 20, width=ancho, height=34)
        self.e[clave] = entrada

    def _logo(self, x, y):
        etiqueta(self.top, "Logo (sale en la factura y en el inicio de sesión)", F_PEQUE, TEXTO_SUAVE).place(x=x, y=y)
        marco = tk.Frame(self.top, bg=CLARO, highlightthickness=1, highlightbackground=BORDE)
        marco.place(x=x, y=y + 20, width=120, height=90)
        self.lbl_logo = tk.Label(marco, bg=CLARO, font=F_PEQUE, fg=TEXTO_SUAVE)
        self.lbl_logo.place(relx=0.5, rely=0.5, anchor="center")
        boton(self.top, "Elegir imagen", self.elegir_logo, "secundario", F_PEQUE).place(
            x=x + 132, y=y + 20, width=130, height=34)
        boton(self.top, "Quitar", self.borrar_logo, "secundario", F_PEQUE).place(
            x=x + 132, y=y + 62, width=130, height=34)

    def mostrar_logo(self, ruta):
        if ruta and os.path.exists(ruta):
            try:
                imagen = ImageOps.contain(Image.open(ruta).convert("RGB"), (112, 82))
                self.foto = ImageTk.PhotoImage(imagen)
                self.lbl_logo.config(image=self.foto, text="")
                return
            except OSError:
                pass
        self.foto = None
        self.lbl_logo.config(image="", text="Sin logo")

    def elegir_logo(self):
        ruta = filedialog.askopenfilename(parent=self.top, title="Elegir el logo del negocio",
                                          filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")])
        if ruta:
            self.logo_nuevo = ruta
            self.quitar_logo = False
            self.mostrar_logo(ruta)

    def borrar_logo(self):
        self.logo_nuevo = None
        self.quitar_logo = True
        self.mostrar_logo(None)

    # ------------------------------------------------------------------ datos
    def cargar(self):
        for clave, entrada in self.e.items():
            entrada.delete(0, "end")
            entrada.insert(0, ajustes.obtener(clave))
        self.mostrar_logo(ajustes.obtener("negocio_logo"))

    def error(self, texto):
        self.lbl_mensaje.config(text=texto, fg=ROJO)

    def guardar(self):
        valores = {clave: entrada.get().strip() for clave, entrada in self.e.items()}

        if not valores["negocio_nombre"]:
            return self.error("El nombre del negocio es obligatorio.")
        if not valores["moneda_simbolo"] or len(valores["moneda_simbolo"]) > 5:
            return self.error("El símbolo de la moneda es obligatorio y lleva 5 caracteres como máximo.")
        if not valores["impuesto_nombre"]:
            return self.error("El nombre del impuesto es obligatorio (por ejemplo IVA).")
        if len(valores["codigo_registro"]) < 4:
            return self.error("El código para registrar usuarios debe tener al menos 4 caracteres.")
        try:
            decimales = int(valores["moneda_decimales"])
            tasa = float(valores["impuesto_tasa"].replace(",", "."))
        except ValueError:
            return self.error("Decimales y tasa deben ser números (por ejemplo 2 y 15).")
        if not 0 <= decimales <= 4:
            return self.error("Los decimales van de 0 a 4.")
        if not 0 <= tasa < 100:
            return self.error("La tasa del impuesto va de 0 a 99.99.")
        billetes = [p.strip() for p in valores["moneda_billetes"].split(",") if p.strip()]
        if not all(p.isdigit() and int(p) > 0 for p in billetes):
            return self.error("Los billetes se escriben como números separados por coma: 100,200,500,1000.")
        valores["moneda_decimales"] = str(decimales)
        valores["impuesto_tasa"] = f"{tasa:g}"
        valores["moneda_billetes"] = ",".join(billetes[:4])

        # El logo se copia junto al programa: si el archivo original se mueve o
        # se borra, la factura lo seguiría necesitando.
        if self.quitar_logo:
            valores["negocio_logo"] = ""
        elif self.logo_nuevo:
            try:
                os.makedirs(CARPETA_LOGO, exist_ok=True)
                destino = os.path.join(CARPETA_LOGO, "logo" + os.path.splitext(self.logo_nuevo)[1].lower())
                if os.path.abspath(self.logo_nuevo) != os.path.abspath(destino):
                    shutil.copyfile(self.logo_nuevo, destino)
                valores["negocio_logo"] = destino
            except OSError as e:
                return self.error(f"No se pudo copiar el logo: {e}")
        else:
            valores["negocio_logo"] = ajustes.obtener("negocio_logo")

        tasa_anterior = ajustes.tasa_impuesto()
        try:
            ajustes.guardar(valores)
            if self.aplicar_tasa.get() and tasa != tasa_anterior:
                db.ejecutar("UPDATE articulos SET iva = ? WHERE iva > 0", (tasa,))
        except (sqlite3.Error, KeyError) as e:
            registro.error("No se pudo guardar la configuración", e)
            return self.error(f"No se pudo guardar: {e}")

        registro.info("Configuración actualizada por %s", self.controlador.usuario_actual)
        self.controlador.actualizar_titulo()
        padre = self.top.master
        if hasattr(padre, "actualizar_marca"):
            padre.actualizar_marca()
        self.top.destroy()
        messagebox.showinfo("Configuración", "Configuración guardada.", parent=self.controlador)
