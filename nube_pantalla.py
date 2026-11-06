"""Pantalla de sincronización con la nube (solo administradores).

Acá se encienden y se apagan las copias a Firebase y se ven las credenciales.
Los datos se guardan en la misma tabla `configuracion` que el resto de los
ajustes del negocio; la lógica de subida está en `nube.py`, que no sabe nada de
ventanas.

Las credenciales se piden y se prueban desde acá en vez de escribirlas en el
código, por la misma razón que el nombre o el impuesto: el programa se instala
en cualquier negocio sin recompilarlo.
"""
import sqlite3
import threading
import tkinter as tk
from tkinter import messagebox

import ajustes
import nube
import registro
from estilos import (BLANCO, NAVY, TEXTO, TEXTO_SUAVE, ROJO, VERDE, FUENTE, F_PEQUE,
                     F_SUBTITULO, F_TITULO, boton, etiqueta, campo, ventana_modal)

ALTO_FILA = 58


class VentanaNube:
    def __init__(self, padre, controlador):
        self.controlador = controlador
        top = self.top = ventana_modal(padre, "Sincronización con la nube", 700, 598)

        etiqueta(top, "Sincronización con la nube", F_TITULO, TEXTO).place(x=28, y=20)
        etiqueta(top, "Copia las ventas y los arqueos a Firebase para verlos desde otro lado. "
                      "La base de este equipo sigue siendo la que manda: el sistema cobra igual "
                      "sin internet y lo pendiente se sube cuando vuelve la conexión.",
                 F_PEQUE, TEXTO_SUAVE, wraplength=640, justify="left").place(x=28, y=58)

        self.activa = tk.BooleanVar(value=ajustes.obtener("nube_activa") == "1")
        tk.Checkbutton(top, text="Mantener este negocio sincronizado con Firebase", variable=self.activa,
                       font=F_SUBTITULO, bg=BLANCO, fg=NAVY, activebackground=BLANCO,
                       highlightthickness=0, anchor="w").place(x=25, y=112, width=560, height=28)

        self.e = {}
        etiqueta(top, "Datos del proyecto de Firebase", F_SUBTITULO, NAVY).place(x=28, y=156)
        self._campo("nube_proyecto", "ID del proyecto *", 28, 184, ancho=300)
        self._campo("nube_api_key", "Clave de API web *", 348, 184, ancho=300)
        self._campo("nube_usuario", "Correo de la cuenta que escribe *", 28, 184 + ALTO_FILA, ancho=300)
        self._campo("nube_clave", "Contraseña de esa cuenta *", 348, 184 + ALTO_FILA, ancho=300, oculto=True)
        etiqueta(top, "Cómo se obtienen estos datos está en docs/Firebase.md. La cuenta se crea en "
                      "Authentication, y conviene que sea una sola, de uso exclusivo del sistema.",
                 F_PEQUE, TEXTO_SUAVE, wraplength=640, justify="left").place(x=28, y=184 + ALTO_FILA * 2 + 2)

        etiqueta(top, "Estado", F_SUBTITULO, NAVY).place(x=28, y=334)
        self.lbl_estado = etiqueta(top, "", F_PEQUE, TEXTO_SUAVE, wraplength=640, justify="left")
        self.lbl_estado.place(x=28, y=360)

        boton(top, "Probar conexión", self.probar, "secundario", F_PEQUE).place(x=28, y=398, width=160, height=38)
        boton(top, "Subir el historial", self.subir_historial, "secundario", F_PEQUE).place(
            x=200, y=398, width=160, height=38)
        etiqueta(top, "«Subir el historial» encola las facturas y los arqueos que ya existen, "
                      "para que la nube no arranque vacía.",
                 F_PEQUE, TEXTO_SUAVE, wraplength=300, justify="left").place(x=376, y=398)

        self.lbl_mensaje = etiqueta(top, "", F_PEQUE, ROJO, wraplength=640, justify="left")
        self.lbl_mensaje.place(x=28, y=466)

        boton(top, "Cancelar", top.destroy, "secundario").place(x=400, y=534, width=130, height=44)
        boton(top, "Guardar", self.guardar, "primario", (FUENTE, 12, "bold")).place(
            x=542, y=534, width=130, height=44)
        top.bind("<Escape>", lambda e: top.destroy())

        self.cargar()
        self.actualizar_estado()

    # ------------------------------------------------------------------ interfaz
    def _campo(self, clave, texto, x, y, ancho=300, oculto=False):
        etiqueta(self.top, texto, F_PEQUE, TEXTO_SUAVE).place(x=x, y=y)
        entrada = campo(self.top, show="•" if oculto else "")
        entrada.place(x=x, y=y + 20, width=ancho, height=34)
        self.e[clave] = entrada

    def cargar(self):
        for clave, entrada in self.e.items():
            entrada.delete(0, "end")
            entrada.insert(0, ajustes.obtener(clave))

    def actualizar_estado(self):
        if not nube.configurada():
            self.lbl_estado.config(text="Apagada. Nada se está copiando a la nube.", fg=TEXTO_SUAVE)
            return
        cuantos = nube.pendientes()
        if cuantos:
            self.lbl_estado.config(
                text=f"Encendida. {cuantos} documento(s) esperando a subir. "
                     "Se suben solos cuando haya internet.", fg=TEXTO_SUAVE)
        else:
            self.lbl_estado.config(text="Encendida y al día: no hay nada pendiente.", fg=VERDE)

    def aviso(self, texto, color=ROJO):
        self.lbl_mensaje.config(text=texto, fg=color)

    # ------------------------------------------------------------------ acciones
    def _valores(self):
        return {clave: entrada.get().strip() for clave, entrada in self.e.items()}

    def _faltan_datos(self, valores):
        if not self.activa.get():
            return None
        for clave, nombre in [("nube_proyecto", "ID del proyecto"),
                              ("nube_api_key", "clave de API web"),
                              ("nube_usuario", "correo de la cuenta"),
                              ("nube_clave", "contraseña")]:
            if not valores[clave]:
                return f"Para encender la sincronización falta el {nombre}."
        if "@" not in valores["nube_usuario"]:
            return "El correo de la cuenta no parece un correo."
        return None

    def probar(self):
        """Prueba las credenciales que están escritas, sin guardarlas todavía."""
        valores = self._valores()
        for clave, nombre in [("nube_proyecto", "ID del proyecto"), ("nube_api_key", "clave de API web"),
                              ("nube_usuario", "correo"), ("nube_clave", "contraseña")]:
            if not valores[clave]:
                return self.aviso(f"Escriba el {nombre} antes de probar.")

        self.aviso("Probando…", TEXTO_SUAVE)
        self.top.update_idletasks()

        # La prueba sale a internet: se hace en otro hilo para que la ventana no
        # se congele, y el resultado vuelve al hilo de la interfaz con after().
        # Se le pasan los datos escritos, que todavía no se guardaron.
        def trabajo():
            try:
                nube.probar(valores["nube_proyecto"], valores["nube_api_key"],
                            valores["nube_usuario"], valores["nube_clave"])
                resultado = (True, "Conexión verificada. Se escribió un documento de prueba "
                                   "en la colección «diagnostico».")
            except nube.ErrorDeNube as e:
                resultado = (False, str(e))
            except Exception as e:                       # noqa: BLE001 - se le muestra al usuario
                registro.error("Falló la prueba de conexión con la nube", e)
                resultado = (False, f"No se pudo probar: {e}")
            self.top.after(0, lambda: self._fin_prueba(*resultado))

        threading.Thread(target=trabajo, daemon=True).start()

    def _fin_prueba(self, bien, mensaje):
        if self.top.winfo_exists():
            self.aviso(mensaje, VERDE if bien else ROJO)

    def subir_historial(self):
        if not nube.configurada():
            return self.aviso("Primero guarde los datos con la sincronización encendida.")
        if not messagebox.askyesno(
                "Subir el historial",
                "Se van a encolar todas las facturas y los arqueos que ya existen.\n\n"
                "Se suben de a poco en segundo plano. ¿Continuar?", parent=self.top):
            return
        try:
            cuantos = nube.encolar_historial()
        except sqlite3.Error as e:
            registro.error("No se pudo encolar el historial para la nube", e)
            return self.aviso(f"No se pudo encolar: {e}")
        self.actualizar_estado()
        self.aviso(f"Se encolaron {cuantos} documento(s). Se suben en segundo plano.", VERDE)

    def guardar(self):
        valores = self._valores()
        falta = self._faltan_datos(valores)
        if falta:
            return self.aviso(falta)
        valores["nube_activa"] = "1" if self.activa.get() else "0"
        try:
            ajustes.guardar(valores)
        except (sqlite3.Error, KeyError) as e:
            registro.error("No se pudo guardar la configuración de la nube", e)
            return self.aviso(f"No se pudo guardar: {e}")

        if self.activa.get():
            nube.iniciar()
        registro.info("Sincronización con la nube %s por %s",
                      "encendida" if self.activa.get() else "apagada",
                      self.controlador.usuario_actual)
        self.top.destroy()
        messagebox.showinfo(
            "Sincronización",
            "Configuración guardada.\n\n"
            + ("La sincronización quedó encendida. Lo que se venda de ahora en adelante se "
               "copia a la nube; para subir lo anterior use «Subir el historial»."
               if self.activa.get() else "La sincronización quedó apagada."),
            parent=self.controlador)
