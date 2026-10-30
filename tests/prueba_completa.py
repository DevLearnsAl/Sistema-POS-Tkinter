"""Prueba completa del sistema manejando la interfaz como un usuario.

Uso:  py tests/prueba_completa.py

Trabaja sobre una copia temporal del proyecto (no toca tu database.db). Los
cuadros de diálogo se simulan para que la prueba no se detenga esperando clics.
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import tkinter as tk
from tkinter import ttk

PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPIA = tempfile.mkdtemp(prefix="minimarket_prueba_")
shutil.rmtree(COPIA)
shutil.copytree(PROYECTO, COPIA, ignore=shutil.ignore_patterns(
    "__pycache__", "database*.db", "facturas", "reportes", "respaldos", ".git", "figma", "tests", "docs"))
os.chdir(COPIA)
sys.path.insert(0, COPIA)

# ---- Diálogos simulados ----
import tkinter.messagebox as mb
import tkinter.simpledialog as sd

MENSAJES = []
RESPUESTA = {"si_no": True, "entero": None}
for nombre in ("showinfo", "showerror", "showwarning"):
    setattr(mb, nombre, lambda title=None, message=None, _n=nombre, **k: MENSAJES.append((_n, title, message)))
mb.askyesno = lambda title=None, message=None, **k: (MENSAJES.append(("askyesno", title, message)), RESPUESTA["si_no"])[1]
sd.askinteger = lambda *a, **k: RESPUESTA["entero"]
ABIERTOS = []
os.startfile = lambda ruta: ABIERTOS.append(ruta)

import ajustes
import config
import crear_bd
import db
import registro
from seguridad import verificar_password

registro.iniciar()

OK = 0


def check(condicion, descripcion):
    global OK
    if not condicion:
        print("FALLA:", descripcion)
        print("   últimos mensajes:", MENSAJES[-3:])
        try:
            app.destroy()
        except NameError:
            pass
        sys.exit(1)
    OK += 1
    print("ok -", descripcion)


def q(sql, p=()):
    return db.consultar(sql, p)


def valor(sql, p=()):
    return db.uno(sql, p)[0]


# ================= MIGRACIONES =================
# 1) Una base de la versión 1 no es compatible: se respalda y se crea una nueva.
v1 = sqlite3.connect(db.DB_NAME)
v1.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
v1.commit()
v1.close()
aviso_v1 = crear_bd.preparar_base()
check(os.path.exists("database_v1_respaldo.db") and crear_bd.version_actual() == crear_bd.VERSION_ESQUEMA
      and "versión anterior" in aviso_v1, "base v1 respaldada y base nueva creada")
shutil.copy(db.DB_NAME, "base_buena.db")

# 2) Una base de la versión 2 se actualiza sin perder los datos.
os.remove(db.DB_NAME)
v2 = sqlite3.connect(db.DB_NAME)
v2.executescript("""
    CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
                           password TEXT NOT NULL, creado TEXT NOT NULL DEFAULT (datetime('now','localtime')));
    CREATE TABLE articulos (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE, articulo TEXT NOT NULL UNIQUE,
                            precio REAL NOT NULL CHECK (precio > 0), costo REAL NOT NULL CHECK (costo >= 0),
                            stock INTEGER NOT NULL CHECK (stock >= 0),
                            stock_minimo INTEGER NOT NULL DEFAULT 5 CHECK (stock_minimo >= 0),
                            iva REAL NOT NULL DEFAULT 15 CHECK (iva IN (0, 15)),
                            estado TEXT NOT NULL CHECK (estado IN ('Activo', 'Inactivo')), image_path TEXT);
    CREATE TABLE ventas (factura INTEGER NOT NULL, cliente TEXT NOT NULL, codigo TEXT, articulo TEXT NOT NULL,
                         precio REAL NOT NULL, cantidad INTEGER NOT NULL, total REAL NOT NULL,
                         iva REAL NOT NULL DEFAULT 0, costo REAL NOT NULL, fecha TEXT NOT NULL, hora TEXT NOT NULL,
                         usuario TEXT, metodo_pago TEXT NOT NULL DEFAULT 'Efectivo', recibido REAL,
                         estado TEXT NOT NULL DEFAULT 'EMITIDA');
    CREATE TABLE clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, cedula TEXT UNIQUE,
                           celular TEXT, direccion TEXT, correo TEXT);
    CREATE TABLE proveedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, ruc TEXT UNIQUE,
                              telefono TEXT, direccion TEXT, correo TEXT);
    CREATE TABLE compras (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, hora TEXT NOT NULL,
                          proveedor TEXT NOT NULL, articulo TEXT NOT NULL, cantidad INTEGER NOT NULL,
                          costo REAL NOT NULL, total REAL NOT NULL, usuario TEXT);
    INSERT INTO usuarios (username, password) VALUES ('admin', 'hash-viejo'), ('pedro', 'hash-viejo');
    INSERT INTO clientes (nombre) VALUES ('Cliente de la v2');
    INSERT INTO articulos (articulo, precio, costo, stock, estado) VALUES ('Producto de la v2', 10, 5, 3, 'Activo');
    INSERT INTO ventas (factura, cliente, articulo, precio, cantidad, total, costo, fecha, hora)
         VALUES (1, 'Cliente de la v2', 'Producto de la v2', 10, 1, 10, 5, '2026-01-01', '10:00:00');
    PRAGMA user_version = 2;
""")
v2.commit()
v2.close()
aviso_v2 = crear_bd.preparar_base()
check(crear_bd.version_actual() == crear_bd.VERSION_ESQUEMA and "versión 2 a la 4" in aviso_v2,
      "base v2 migrada a v4 en un solo paso")
check(valor("SELECT COUNT(*) FROM ventas") == 1 and valor("SELECT COUNT(*) FROM clientes") == 1
      and valor("SELECT articulo FROM articulos") == "Producto de la v2", "la migración conserva los datos")
check(q("SELECT username, rol FROM usuarios ORDER BY username") == [("admin", "admin"), ("pedro", "cajero")],
      "migración: admin queda administrador y el resto cajeros")
check(valor("SELECT activo FROM clientes") == 1 and valor("SELECT caja_id FROM ventas") is None
      and valor("SELECT COUNT(*) FROM cajas") == 0, "migración: columnas y tablas nuevas agregadas")
check(os.path.isdir("respaldos") and len(os.listdir("respaldos")) >= 1, "respaldo automático al abrir")

# La v3 solo admitía IVA 0 o 15; la v4 reconstruye la tabla para aceptar cualquier tasa.
db.ejecutar("UPDATE articulos SET iva = 18 WHERE articulo = 'Producto de la v2'")
check(valor("SELECT iva FROM articulos WHERE articulo = 'Producto de la v2'") == 18,
      "migración: la tasa de impuesto ya no está atada al 15 %")
try:
    db.ejecutar("UPDATE articulos SET iva = 120 WHERE articulo = 'Producto de la v2'")
    sin_limite = True
except sqlite3.IntegrityError:
    sin_limite = False
check(not sin_limite, "pero sigue rechazando una tasa imposible (CHECK nuevo)")
check(valor("SELECT COUNT(*) FROM configuracion") == 0 and ajustes.obtener("moneda_simbolo") == "C$",
      "sin configuración guardada se usan los valores por defecto")

# Se vuelve a la base con datos de ejemplo para probar la interfaz.
os.remove(db.DB_NAME)
shutil.move("base_buena.db", db.DB_NAME)

from manager import Manager
from container import Container
from login import Login, Registro
from ventas import Ventas
from caja import Caja
from compras import Compras
from inventario import Inventario
from catalogo import Clientes, Proveedores
from reportes import Reportes

app = Manager()
app.withdraw()
app.update()


def ultimo():
    return MENSAJES[-1][2] if MENSAJES else ""


def ventanas(w):
    return [x for x in w.winfo_children() if isinstance(x, tk.Toplevel)]


def recorrer(w):
    for hijo in w.winfo_children():
        yield hijo
        yield from recorrer(hijo)


def boton(w, texto):
    return next(b for b in recorrer(w) if isinstance(b, tk.Button) and b.cget("text") == texto)


def entradas_de(w):
    """Los campos de texto de una ventana. Combobox hereda de Entry, por eso se excluye."""
    return [e for e in recorrer(w) if isinstance(e, ttk.Entry) and not isinstance(e, ttk.Combobox)]


def error_de(w):
    return next(x for x in recorrer(w) if isinstance(x, tk.Label) and x.cget("fg") == "#B42318")


def escribir(e, texto):
    e.delete(0, "end")
    e.insert(0, texto)


check(valor("SELECT COUNT(*) FROM articulos") == 11 and valor("SELECT COUNT(DISTINCT factura) FROM ventas") > 10,
      "datos de ejemplo: 11 productos y una semana de ventas")
check(verificar_password("admin", valor("SELECT password FROM usuarios WHERE username = 'admin'"))
      and valor("SELECT password FROM usuarios WHERE username = 'admin'").startswith("pbkdf2_sha256$"),
      "la contraseña se guarda con hash, no en texto")
check(valor("SELECT COUNT(*) FROM cajas WHERE estado = 'CERRADA'") == 7
      and valor("SELECT COUNT(*) FROM cajas WHERE estado = 'ABIERTA'") == 0,
      "los 7 turnos de ejemplo quedan cerrados")

# ================= LOGIN Y REGISTRO =================
lg, rg = app.frames[Login], app.frames[Registro]
lg.enviar()
check("Escriba su usuario" in lg.lbl_mensaje.cget("text"), "login vacío avisa")
escribir(lg.username, "admin"); escribir(lg.password, "mala"); lg.enviar()
check("incorrectos" in lg.lbl_mensaje.cget("text") and app.usuario_actual is None, "contraseña mala rechazada")

app.show_frame(Registro)
for datos, esperado in [(("ab", "123456", "123456", "1234"), "al menos 3"),
                        (("cajero", "123", "123", "1234"), "al menos 6"),
                        (("cajero", "123456", "654321", "1234"), "no coinciden"),
                        (("cajero", "123456", "123456", "9999"), "código"),
                        (("admin", "123456", "123456", "1234"), "ya existe")]:
    for e, v in zip((rg.username, rg.password, rg.confirmar, rg.key), datos):
        escribir(e, v)
    rg.enviar()
    check(esperado in rg.lbl_mensaje.cget("text"), f"registro rechaza: {esperado}")
for e, v in zip((rg.username, rg.password, rg.confirmar, rg.key), ("cajero", "cajero123", "cajero123", "1234")):
    escribir(e, v)
rg.enviar()
check(lg.username.get() == "cajero" and "creada" in lg.lbl_mensaje.cget("text"), "registro válido vuelve al login")
check(valor("SELECT rol FROM usuarios WHERE username = 'cajero'") == "cajero",
      "quien se registra entra como cajero, no como administrador")

# ================= PERMISOS DEL CAJERO =================
escribir(lg.password, "cajero123"); lg.enviar()
check(app.usuario_actual == "cajero" and app.rol_actual == "cajero", "el usuario nuevo inicia sesión")
ct = app.frames[Container]
visibles = {c.__name__ for c in ct.pestanas}
check(visibles == {"Ventas", "Caja", "Inventario", "Clientes"},
      "el cajero solo ve Ventas, Caja, Inventario y Clientes")
check(not app.puede("anular") and not app.puede("reportes") and not app.puede("editar_inventario"),
      "el cajero no tiene permisos de administrador")
ct.show_frames(Reportes)
check(ct.actual is not Reportes, "el cajero no puede abrir Reportes ni con el atajo")
check(ct.atajos == {1: Ventas, 2: Caja, 3: Inventario, 4: Clientes},
      "los atajos F1-F4 siguen los módulos que ve el cajero")
ct._atajo(3)
check(ct.actual is Inventario, "F3 abre Inventario, que es el tercer botón de su barra")
ct.show_frames(Inventario)
inv = ct.frames[Inventario]
check(str(inv.btn_nuevo.cget("state")) == "disabled" and str(inv.btn_editar.cget("state")) == "disabled",
      "el cajero no puede crear ni editar productos")
inv.agregar_articulo()
check("Solo un administrador" in ultimo() and not ventanas(inv), "si lo intenta igual, se le avisa")

RESPUESTA["si_no"] = True
ct.salir()
check(app.usuario_actual is None and app.rol_actual is None, "cerrar sesión")
escribir(lg.username, "admin"); escribir(lg.password, "admin"); lg.enviar()
check(app.usuario_actual == "admin" and app.es_admin and "admin" in ct.btn_usuario.cget("text"),
      "admin entra y aparece en la barra")
check(app.clave_por_defecto, "avisa que admin sigue con la contraseña de fábrica")
check(len(ct.pestanas) == 7 and ct.atajos[3] is Compras,
      "el administrador ve los 7 módulos y F3 le abre Compras")

# ================= CAJA: APERTURA =================
cj = ct.frames[Caja]
ct.show_frames(Caja)
check(cj.caja_id is None and "cerrada" in cj.lbl_estado.cget("text").lower(), "arranca sin turno abierto")

v = ct.frames[Ventas]
ct.show_frames(Ventas)
codigo_coca = valor("SELECT codigo FROM articulos WHERE articulo = 'Coca-Cola 1.5 L'")


def agregar(producto, cantidad):
    v.entry_producto.set(producto)
    v.entry_cantidad.set(cantidad)
    v.agregar_articulo()


agregar(codigo_coca, 1)
RESPUESTA["si_no"] = False
v.realizar_pago()
check("No hay un turno de caja abierto" in ultimo() and not ventanas(v), "sin caja abierta no se puede cobrar")
v.vaciar(confirmar=False)

ct.show_frames(Caja)
cj.abrir()
top = ventanas(cj)[-1]
escribir(entradas_de(top)[0], "abc")
boton(top, "Abrir caja").invoke()
check(cj.caja_id is None, "monto inicial inválido rechazado")
escribir(entradas_de(top)[0], "500")
boton(top, "Abrir caja").invoke()
check(cj.caja_id and valor("SELECT monto_inicial FROM cajas WHERE id = ?", (cj.caja_id,)) == 500.0
      and valor("SELECT usuario FROM cajas WHERE id = ?", (cj.caja_id,)) == "admin", "abre el turno con C$ 500")
caja_id = cj.caja_id
try:
    db.ejecutar("INSERT INTO cajas (usuario, fecha_apertura, hora_apertura, monto_inicial) "
                "VALUES ('otro', '2026-01-01', '08:00:00', 0)")
    dos_abiertas = True
except sqlite3.IntegrityError:
    dos_abiertas = False
check(not dos_abiertas, "la base impide dos turnos abiertos a la vez")

# ================= VENTAS =================
ct.show_frames(Ventas)
check("Jugo de naranja 1 L" not in v.productos, "productos inactivos no se venden")
check(v.entry_cliente.get() == "Consumidor final", "cliente por defecto")
check("Caja abierta" in v.lbl_cajero.cget("text"), "Ventas muestra el turno abierto")
siguiente = valor("SELECT MAX(factura) + 1 FROM ventas")
check(v.lbl_factura.cget("text") == f"N° {siguiente:06d}", "muestra el próximo número de factura")

agregar(codigo_coca, 2)
check(len(v.carrito) == 1 and v.carrito[0]["articulo"] == "Coca-Cola 1.5 L", "agrega por código de barras")
agregar("doritos", 3)
check(v.carrito[1]["articulo"] == "Doritos Nacho 45 g", "agrega por parte del nombre")
agregar("Coca-Cola 1.5 L", 1)
check(len(v.carrito) == 2 and v.carrito[0]["cantidad"] == 3, "el mismo producto suma en la misma línea")
check(v.label_precio_total.cget("text") == "C$ 241.50" and v.lbl_iva.cget("text") == "C$ 31.50"
      and v.lbl_subtotal.cget("text") == "C$ 210.00", "total, IVA 15 % y subtotal correctos")
agregar("Arroz 1 lb", 1)
check(v.label_precio_total.cget("text") == "C$ 260.25" and v.lbl_iva.cget("text") == "C$ 31.50",
      "producto exento no suma IVA")
stock_leche = valor("SELECT stock FROM articulos WHERE articulo = 'Leche entera 1 L'")
agregar("Leche entera 1 L", 7)
agregar("Leche entera 1 L", stock_leche)
check("ya agregó 7" in ultimo() and v.carrito[-1]["cantidad"] == 7, "no deja pasar el stock sumando líneas")
agregar("Arroz 1 lb", "0")
check("mayor que cero" in ultimo(), "cantidad 0 rechazada")
agregar("xyz123", 1)
check("No se encontró" in ultimo(), "producto inexistente avisa")

v.tree.selection_set(v.tree.get_children()[1])
RESPUESTA["entero"] = 4
v.editar_articulo()
check(v.carrito[1]["cantidad"] == 4 and v.carrito[1]["total"] == 102.0, "cambiar cantidad recalcula")
RESPUESTA["entero"] = 999
v.tree.selection_set(v.tree.get_children()[1])
v.editar_articulo()
check("Stock insuficiente" in ultimo() and v.carrito[1]["cantidad"] == 4, "cambiar cantidad respeta el stock")
v.tree.selection_set(v.tree.get_children()[3])
v.eliminar_articulo()
check([l["articulo"] for l in v.carrito] == ["Coca-Cola 1.5 L", "Doritos Nacho 45 g", "Arroz 1 lb"],
      "quitar producto")
total_venta = v.totales()["total"]
stock_coca = valor("SELECT stock FROM articulos WHERE articulo = 'Coca-Cola 1.5 L'")

v.realizar_pago()
cobro = ventanas(v)[-1]
entrada = next(w for w in recorrer(cobro) if isinstance(w, ttk.Entry))
escribir(entrada, "100")
check("Falta" in next(w for w in recorrer(cobro) if isinstance(w, tk.Label) and w.cget("text").startswith("Falta")).cget("text"),
      "el cobro muestra lo que falta")
boton(cobro, "Confirmar pago").invoke()
check(valor("SELECT COUNT(*) FROM ventas WHERE factura = ?", (siguiente,)) == 0 and cobro.winfo_exists(),
      "monto insuficiente no guarda")
boton(cobro, "C$ 500").invoke()
check(any(isinstance(w, tk.Label) and w.cget("text") == f"Cambio: C$ {500 - total_venta:,.2f}" for w in recorrer(cobro)),
      "cambio en vivo con los botones de billetes")
boton(cobro, "Confirmar pago").invoke()
app.update()
exito = ventanas(v)[-1]
check(any(isinstance(w, tk.Label) and "Venta registrada" in w.cget("text") for w in recorrer(exito)),
      "ventana de venta registrada")
filas = q("SELECT articulo, cantidad, total, iva, metodo_pago, recibido, usuario, estado, caja_id FROM ventas "
          "WHERE factura = ? ORDER BY rowid", (siguiente,))
check([f[0] for f in filas] == ["Coca-Cola 1.5 L", "Doritos Nacho 45 g", "Arroz 1 lb"]
      and all(f[4] == "Efectivo" and f[5] == 500 and f[6] == "admin" and f[7] == "EMITIDA" and f[8] == caja_id
              for f in filas)
      and filas[2][3] == 0, "venta guardada con método, recibido, cajero, turno de caja e IVA por línea")
check(valor("SELECT stock FROM articulos WHERE articulo = 'Coca-Cola 1.5 L'") == stock_coca - 3, "stock descontado")
check(os.path.exists(f"facturas/Factura_{siguiente}.pdf"), "factura PDF generada")
boton(exito, "Ver factura (PDF)").invoke()
check(ABIERTOS and ABIERTOS[-1].endswith(f"Factura_{siguiente}.pdf"), "botón Ver factura abre el PDF")
check(not v.carrito and v.lbl_factura.cget("text") == f"N° {siguiente + 1:06d}", "carrito limpio y número siguiente")

agregar("Galletas de chocolate", 2)
v.realizar_pago()
cobro = ventanas(v)[-1]
boton(cobro, "Tarjeta").invoke()
entrada = next(w for w in recorrer(cobro) if isinstance(w, ttk.Entry))
check(str(entrada.cget("state")) == "disabled" and entrada.get() == "60.00", "tarjeta: monto fijo igual al total")
boton(cobro, "Confirmar pago").invoke()
app.update()
ventanas(v)[-1].destroy()
check(q("SELECT DISTINCT metodo_pago, recibido FROM ventas WHERE factura = ?", (siguiente + 1,)) == [("Tarjeta", 60.0)],
      "venta con tarjeta guardada")

agregar("Aceite vegetal 1 L", 2)
db.ejecutar("UPDATE articulos SET stock = 1 WHERE articulo = 'Aceite vegetal 1 L'")   # otra caja vendió
v._atajo_cobrar()
cobro = ventanas(v)[-1]
check(cobro.winfo_exists(), "F12 abre el cobro")
boton(cobro, "C$ 200").invoke()
boton(cobro, "Confirmar pago").invoke()
app.update()
check("No hay suficiente" in ultimo() and valor("SELECT COUNT(*) FROM ventas WHERE factura = ?", (siguiente + 2,)) == 0
      and valor("SELECT stock FROM articulos WHERE articulo = 'Aceite vegetal 1 L'") == 1 and len(v.carrito) == 1,
      "si el stock cambió antes de cobrar, la venta se rechaza completa")
RESPUESTA["si_no"] = True
v.vaciar()
check(not v.carrito, "vaciar venta")
try:
    db.ejecutar("UPDATE articulos SET stock = -1 WHERE articulo = 'Arroz 1 lb'")
    negativo = True
except sqlite3.IntegrityError:
    negativo = False
check(not negativo, "la base rechaza stock negativo (CHECK)")

# ================= HISTORIAL Y ANULACIÓN =================
v.ver_ventas_realizadas()
h = ventanas(v)[-1]
arbol = next(w for w in recorrer(h) if isinstance(w, ttk.Treeview))
check(len(arbol.get_children()) == valor("SELECT COUNT(DISTINCT factura) FROM ventas"), "historial: una fila por factura")
entradas = [w for w in recorrer(h) if isinstance(w, ttk.Entry) and not isinstance(w, ttk.Combobox)]
escribir(entradas[0], str(siguiente)); boton(h, "Buscar").invoke()
check(len(arbol.get_children()) == 1, "filtro por número de factura")
escribir(entradas[0], ""); escribir(entradas[1], "maría"); boton(h, "Buscar").invoke()
check(len(arbol.get_children()) == valor("SELECT COUNT(DISTINCT factura) FROM ventas WHERE cliente LIKE '%maría%'"),
      "filtro por parte del nombre del cliente")
combos = [w for w in recorrer(h) if isinstance(w, ttk.Combobox)]
escribir(entradas[1], ""); combos[1].set("Anuladas"); boton(h, "Buscar").invoke()
check(len(arbol.get_children()) == 1, "filtro de facturas anuladas")
combos[1].set("Todos"); boton(h, "Buscar").invoke()
arbol.selection_set(arbol.get_children()[0])       # la más reciente
numero = int(str(arbol.item(arbol.get_children()[0], "values")[0]))
stock_galletas = valor("SELECT stock FROM articulos WHERE articulo = 'Galletas de chocolate'")
RESPUESTA["si_no"] = True
boton(h, "Anular factura").invoke()
check(q("SELECT DISTINCT estado FROM ventas WHERE factura = ?", (numero,)) == [("ANULADA",)]
      and valor("SELECT stock FROM articulos WHERE articulo = 'Galletas de chocolate'") == stock_galletas + 2,
      "anular factura: queda ANULADA y el stock vuelve")
arbol.selection_set(arbol.get_children()[0])
boton(h, "Anular factura").invoke()
check("ya está anulada" in ultimo(), "no se anula dos veces")
boton(h, "Ver factura").invoke()
check(ABIERTOS[-1].endswith(f"Factura_{numero}.pdf"), "reimprimir factura anulada")
h.destroy()

# ================= INVENTARIO =================
ct.show_frames(Inventario)
check(len(inv.tarjetas) == valor("SELECT COUNT(*) FROM articulos"), "una tarjeta por producto")
check(str(inv.btn_nuevo.cget("state")) == "normal", "el administrador sí puede crear productos")
inv.cambiar_filtro("Stock bajo")
check(len(inv.tarjetas) == valor("SELECT COUNT(*) FROM articulos WHERE estado = 'Activo' AND stock <= stock_minimo"),
      "filtro de stock bajo")
inv.cambiar_filtro("Inactivos")
check(len(inv.tarjetas) == 1, "filtro de inactivos")
inv.cambiar_filtro("Todos")
escribir(inv.entry_buscar, codigo_coca); inv.refrescar()
check(len(inv.tarjetas) == 1, "buscar por código de barras")
escribir(inv.entry_buscar, ""); inv.refrescar()

inv.agregar_articulo()
top = ventanas(inv)[-1]
campos = [w for w in top.winfo_children() if type(w) is ttk.Entry]
nombre_e, codigo_e, precio_e, costo_e, stock_e, minimo_e = campos
escribir(nombre_e, "Arroz 1 lb"); escribir(precio_e, "20"); escribir(costo_e, "15")
boton(top, "Guardar").invoke()
error = next(w for w in top.winfo_children() if isinstance(w, tk.Label) and w.cget("fg") == "#B42318")
check("Ya existe un producto" in error.cget("text"), "nombre repetido rechazado")
escribir(nombre_e, "Café molido 200 g"); escribir(precio_e, "0"); boton(top, "Guardar").invoke()
check("mayor que 0" in error.cget("text"), "precio 0 rechazado")
escribir(precio_e, "95"); escribir(codigo_e, codigo_coca); boton(top, "Guardar").invoke()
check("código de barras ya está asignado" in error.cget("text"), "código de barras repetido rechazado")
boton(top, "Generar código").invoke()
codigo_nuevo = codigo_e.get()
escribir(stock_e, "15")
top.formulario.imagen_nueva = os.path.join("fotos", "agua.png")   # simula elegir una imagen
boton(top, "Guardar").invoke()
fila = db.uno("SELECT codigo, precio, stock, image_path FROM articulos WHERE articulo = 'Café molido 200 g'")
check(fila and fila[0] == codigo_nuevo and codigo_nuevo.startswith("200") and fila[1] == 95 and fila[2] == 15
      and fila[3].startswith(os.path.join("fotos", "cafe_molido_200_g_")) and os.path.exists(fila[3]),
      "producto nuevo con código generado e imagen con nombre único")
check(inv.producto(inv.seleccionado)["articulo"] == "Café molido 200 g"
      and "Margen" in inv.det_valores and inv.det_valores["Precio"].cget("text") == "C$ 95.00",
      "queda seleccionado y se ve su detalle")
inv.editar_articulo()
top = ventanas(inv)[-1]
campos = [w for w in top.winfo_children() if type(w) is ttk.Entry]
escribir(campos[2], "99.50"); boton(top, "Guardar").invoke()
check(valor("SELECT precio FROM articulos WHERE articulo = 'Café molido 200 g'") == 99.5, "editar precio")
RESPUESTA["si_no"] = False
inv.exportar()
csv_inventario = [f for f in os.listdir("reportes") if f.startswith("inventario_")]
with open(os.path.join("reportes", csv_inventario[0]), encoding="utf-8-sig") as f:
    lineas = f.read().splitlines()
check(len(csv_inventario) == 1 and lineas[0].startswith("Código,Producto")
      and len(lineas) == valor("SELECT COUNT(*) FROM articulos") + 1, "exportar inventario a CSV")

# ================= COMPRAS =================
cp = ct.frames[Compras]
ct.show_frames(Compras)
check(cp.combo_proveedor.get() in cp.proveedores and cp.proveedores, "proveedor por defecto")
stock_frijoles, _ = db.uno("SELECT stock, costo FROM articulos WHERE articulo = 'Frijoles rojos 1 lb'")
codigo_frijoles = valor("SELECT codigo FROM articulos WHERE articulo = 'Frijoles rojos 1 lb'")
cp.combo_producto.set(codigo_frijoles); cp.mostrar_producto()
check(cp.combo_producto.get() == "Frijoles rojos 1 lb" and cp.entry_costo.get() == "25.00",
      "compras: busca por código y propone el costo actual")
cp.entry_cantidad.set("abc"); cp.registrar()
check("cantidad" in cp.lbl_mensaje.cget("text"), "compras: cantidad inválida")
cp.entry_cantidad.set(20); escribir(cp.entry_costo, "26"); cp.registrar()
check(db.uno("SELECT stock, costo FROM articulos WHERE articulo = 'Frijoles rojos 1 lb'") == (stock_frijoles + 20, 26.0)
      and valor("SELECT COUNT(*) FROM compras WHERE articulo = 'Frijoles rojos 1 lb'") == 1,
      "compra suma stock y actualiza costo")

# ================= CLIENTES Y PROVEEDORES =================
cl = ct.frames[Clientes]
ct.show_frames(Clientes)
check(str(cl.tre.item(cl.tre.get_children()[0], "values")[1]) == "Consumidor final", "Consumidor final primero")
cl.guardar()
check("obligatorio" in cl.lbl_mensaje.cget("text"), "nombre obligatorio")
escribir(cl.entradas["nombre"], "Luis Pérez"); escribir(cl.entradas["cedula"], "12345"); cl.guardar()
check("Cédula no válida" in cl.lbl_mensaje.cget("text"), "cédula con formato inválido")
escribir(cl.entradas["cedula"], "0012304950005a"); escribir(cl.entradas["correo"], "luis@"); cl.guardar()
check("correo no es válido" in cl.lbl_mensaje.cget("text"), "correo inválido")
escribir(cl.entradas["correo"], "luis@correo.com"); cl.guardar()
check(valor("SELECT cedula FROM clientes WHERE nombre = 'Luis Pérez'") == "001-230495-0005A", "cédula normalizada")
escribir(cl.entradas["nombre"], "Otro"); escribir(cl.entradas["cedula"], "001-230495-0005A"); cl.guardar()
check("Ya existe un cliente" in cl.lbl_mensaje.cget("text"), "cédula repetida rechazada")
cl.limpiar()
check(str(cl.btn_baja.cget("state")) == "disabled", "sin selección no se puede dar de baja")
fila_maria = next(i for i in cl.tre.get_children() if cl.tre.item(i, "values")[1] == "María López")
cl.tre.selection_set(fila_maria); app.update()
check(cl.editando and cl.entradas["cedula"].get() == "001-150390-0001X", "seleccionar carga el formulario")
escribir(cl.entradas["celular"], "+505 8000 0000"); cl.guardar()
check(valor("SELECT celular FROM clientes WHERE nombre = 'María López'") == "+505 8000 0000"
      and valor("SELECT COUNT(*) FROM clientes WHERE nombre = 'María López'") == 1, "editar cliente sin duplicar")
fila_cf = next(i for i in cl.tre.get_children() if cl.tre.item(i, "values")[1] == "Consumidor final")
cl.tre.selection_set(fila_cf); app.update()
check("no se puede modificar" in cl.lbl_mensaje.cget("text") and not cl.editando, "Consumidor final protegido")

fila_luis = next(i for i in cl.tre.get_children() if cl.tre.item(i, "values")[1] == "Luis Pérez")
cl.tre.selection_set(fila_luis); app.update()
check(cl.btn_baja.cget("text") == "Dar de baja" and str(cl.btn_baja.cget("state")) == "normal",
      "con un cliente activo seleccionado se ofrece darlo de baja")
RESPUESTA["si_no"] = True
cl.cambiar_estado()
check(valor("SELECT activo FROM clientes WHERE nombre = 'Luis Pérez'") == 0
      and valor("SELECT COUNT(*) FROM clientes WHERE nombre = 'Luis Pérez'") == 1,
      "dar de baja no borra el cliente")
ct.show_frames(Ventas)
check("Luis Pérez" not in v.clientes, "un cliente de baja no aparece al vender")
ct.show_frames(Clientes)
fila_luis = next(i for i in cl.tre.get_children() if cl.tre.item(i, "values")[1] == "Luis Pérez")
cl.tre.selection_set(fila_luis); app.update()
check(cl.btn_baja.cget("text") == "Reactivar", "a un cliente de baja se le ofrece reactivar")
cl.cambiar_estado()
check(valor("SELECT activo FROM clientes WHERE nombre = 'Luis Pérez'") == 1, "reactivar cliente")
ct.show_frames(Ventas)
check("Luis Pérez" in v.clientes, "cliente reactivado disponible en Ventas")

pv = ct.frames[Proveedores]
ct.show_frames(Proveedores)
escribir(pv.entradas["nombre"], "Snacks del Pacífico"); escribir(pv.entradas["ruc"], "J031"); pv.guardar()
check("14 caracteres" in pv.lbl_mensaje.cget("text"), "RUC inválido")
escribir(pv.entradas["ruc"], "j0310000000044"); pv.guardar()
check(valor("SELECT ruc FROM proveedores WHERE nombre = 'Snacks del Pacífico'") == "J0310000000044", "proveedor guardado")
escribir(pv.entradas["nombre"], "Otro"); escribir(pv.entradas["ruc"], "J0310000000044"); pv.guardar()
check("Ya existe un proveedor" in pv.lbl_mensaje.cget("text"), "RUC repetido rechazado")
pv.limpiar()
fila_snacks = next(i for i in pv.tre.get_children() if pv.tre.item(i, "values")[1] == "Snacks del Pacífico")
pv.tre.selection_set(fila_snacks); app.update()
pv.cambiar_estado()
ct.show_frames(Compras)
check("Snacks del Pacífico" not in cp.proveedores, "un proveedor de baja no aparece al comprar")

# ================= USUARIOS =================
from usuarios import VentanaMiCuenta, VentanaUsuarios

vu = VentanaUsuarios(ct, app)
check(len(vu.tree.get_children()) == valor("SELECT COUNT(*) FROM usuarios"), "la lista muestra todos los usuarios")


def elegir_usuario(nombre):
    """La tabla se vuelve a llenar después de cada cambio, así que hay que buscar la fila de nuevo."""
    vu.tree.selection_set(next(i for i in vu.tree.get_children() if vu.tree.item(i, "values")[0] == nombre))


elegir_usuario("cajero")
vu.cambiar_rol()
check(valor("SELECT rol FROM usuarios WHERE username = 'cajero'") == "admin", "cambiar el rol de un usuario")
elegir_usuario("cajero")
vu.cambiar_rol()
check(valor("SELECT rol FROM usuarios WHERE username = 'cajero'") == "cajero", "y volver a dejarlo como cajero")
elegir_usuario("admin")
vu.cambiar_rol()
check(valor("SELECT rol FROM usuarios WHERE username = 'admin'") == "admin"
      and "único administrador" in vu.lbl_mensaje.cget("text"), "no se puede quitar al único administrador")
elegir_usuario("admin")
vu.cambiar_estado()
check(valor("SELECT activo FROM usuarios WHERE username = 'admin'") == 1
      and "propia cuenta" in vu.lbl_mensaje.cget("text"), "no se puede desactivar la cuenta propia")
elegir_usuario("cajero")
vu.cambiar_estado()
check(valor("SELECT activo FROM usuarios WHERE username = 'cajero'") == 0, "desactivar un usuario")
vu.top.destroy()

mc = VentanaMiCuenta(ct, app)
mc.campos["actual"].insert(0, "equivocada")
mc.campos["nueva"].insert(0, "nueva123")
mc.campos["confirmar"].insert(0, "nueva123")
mc.confirmar()
check("actual no es correcta" in mc.lbl_mensaje.cget("text"), "cambiar contraseña exige la actual")
escribir(mc.campos["actual"], "admin"); escribir(mc.campos["confirmar"], "otra123")
mc.confirmar()
check("no coinciden" in mc.lbl_mensaje.cget("text"), "las contraseñas nuevas deben coincidir")
escribir(mc.campos["confirmar"], "nueva123")
mc.confirmar()
check(verificar_password("nueva123", valor("SELECT password FROM usuarios WHERE username = 'admin'"))
      and not app.clave_por_defecto, "contraseña cambiada y aviso de clave de fábrica apagado")

# El usuario desactivado ya no puede entrar.
db.ejecutar("UPDATE usuarios SET activo = 1, password = ? WHERE username = 'cajero'",
            (valor("SELECT password FROM usuarios WHERE username = 'cajero'"),))
db.ejecutar("UPDATE usuarios SET activo = 0 WHERE username = 'cajero'")
RESPUESTA["si_no"] = True
ct.salir()
escribir(lg.username, "cajero"); escribir(lg.password, "cajero123"); lg.enviar()
check(app.usuario_actual is None and "desactivada" in lg.lbl_mensaje.cget("text"),
      "una cuenta desactivada no puede iniciar sesión")
escribir(lg.username, "admin"); escribir(lg.password, "nueva123"); lg.enviar()
check(app.usuario_actual == "admin" and not app.clave_por_defecto, "admin entra con la contraseña nueva")

# ================= CAJA: MOVIMIENTOS Y CIERRE =================
ct.show_frames(Caja)
check(cj.caja_id == caja_id, "sigue abierto el mismo turno")
datos = cj.valores
efectivo_bd = valor("SELECT COALESCE(SUM(total), 0) FROM ventas WHERE caja_id = ? AND estado = 'EMITIDA' "
                    "AND metodo_pago = 'Efectivo'", (caja_id,))
import caja as mod_caja
r = mod_caja.resumen(caja_id)
check(abs(r["efectivo"] - efectivo_bd) < 0.005 and r["esperado"] == round(500 + efectivo_bd, 2),
      "el resumen suma el efectivo del turno")
check(r["tarjeta"] == 0, "la venta con tarjeta anulada no cuenta")

cj.movimiento("ENTRADA")
top = ventanas(cj)[-1]
escribir(entradas_de(top)[0], "0")
boton(top, "Registrar").invoke()
check("mayor que cero" in error_de(top).cget("text"), "movimiento con monto 0 rechazado")
escribir(entradas_de(top)[0], "300")
boton(top, "Registrar").invoke()
check(valor("SELECT COUNT(*) FROM movimientos_caja WHERE caja_id = ? AND tipo = 'ENTRADA'", (caja_id,)) == 1
      and mod_caja.resumen(caja_id)["esperado"] == round(500 + efectivo_bd + 300, 2), "entrada de efectivo")

cj.movimiento("SALIDA")
top = ventanas(cj)[-1]
escribir(entradas_de(top)[0], "999999")
boton(top, "Registrar").invoke()
check("más efectivo del que hay" in error_de(top).cget("text"),
      "no se puede sacar más de lo que hay en caja")
escribir(entradas_de(top)[0], "200")
boton(top, "Registrar").invoke()
esperado = mod_caja.resumen(caja_id)["esperado"]
check(esperado == round(500 + efectivo_bd + 300 - 200, 2), "salida de efectivo")
check(len(cj.tree_mov.get_children()) == 2, "los movimientos aparecen en la tabla del turno")

cj.cerrar()
cierre = ventanas(cj)[-1]
entrada_cierre = entradas_de(cierre)[0]
escribir(entrada_cierre, str(esperado - 50))
app.update()
check("Faltan C$ 50.00" in next(w for w in recorrer(cierre)
                                if isinstance(w, tk.Label) and w.cget("text").startswith("Faltan")).cget("text"),
      "el cierre avisa en vivo cuánto falta")
RESPUESTA["si_no"] = False
boton(cierre, "Cerrar caja").invoke()
check(valor("SELECT estado FROM cajas WHERE id = ?", (caja_id,)) == "ABIERTA",
      "si no se confirma la diferencia, la caja no se cierra")
escribir(entrada_cierre, str(esperado))
app.update()
boton(cierre, "Cerrar caja").invoke()
fila = db.uno("SELECT estado, esperado, monto_contado, diferencia, usuario_cierre FROM cajas WHERE id = ?",
              (caja_id,))
check(fila[0] == "CERRADA" and fila[1] == esperado and fila[2] == esperado and fila[3] == 0
      and fila[4] == "admin", "cerrar caja guarda el arqueo")
check(cj.caja_id is None and "cerrada" in cj.lbl_estado.cget("text").lower(), "después del cierre no hay turno")
agregar("Agua purificada 600 ml", 1)
RESPUESTA["si_no"] = False
v.realizar_pago()
check("No hay un turno de caja abierto" in ultimo(), "cerrada la caja, no se puede volver a cobrar")
v.vaciar(confirmar=False)

# ================= REPORTES =================
rp = ct.frames[Reportes]
ct.show_frames(Reportes)
import datetime
desde = (datetime.date.today() - datetime.timedelta(days=6)).isoformat()
esperado_ventas = valor("SELECT SUM(total) FROM ventas WHERE estado = 'EMITIDA' AND fecha >= ?", (desde,))
check(rp.kpis["ventas"][0].cget("text") == f"C$ {esperado_ventas:,.2f}", "KPI de ventas de 7 días (sin anuladas)")
check(len(rp.tree_top.get_children()) == 5, "top 5 productos")
check(len(rp.tree_bajo.get_children()) == valor("SELECT COUNT(*) FROM articulos WHERE estado = 'Activo' "
                                                "AND stock <= stock_minimo"), "lista de stock bajo")
check(len(rp.canvas.find_all()) > 20 and len(rp.ventas_por_dia()) == 7, "gráfico de 7 días dibujado")
rp.cambiar_periodo(0)
hoy = valor("SELECT COALESCE(SUM(total), 0) FROM ventas WHERE estado = 'EMITIDA' AND fecha = ?",
            (datetime.date.today().isoformat(),))
check(rp.kpis["ventas"][0].cget("text") == f"C$ {hoy:,.2f}", "KPI de hoy")
rp.cambiar_periodo(29)
check(len(rp.ventas_por_dia()) == 30 and "30 días" in rp.panel_grafico.titulo.cget("text"),
      "el gráfico sigue el período elegido")
RESPUESTA["si_no"] = False
rp.exportar()
archivos = [f for f in os.listdir("reportes") if f.startswith("ventas_")]
with open(os.path.join("reportes", archivos[0]), encoding="utf-8-sig") as f:
    lineas = f.read().splitlines()
check(len(archivos) == 1 and lineas[0].startswith("Factura,Fecha") and len(lineas) > 20, "exportar ventas a CSV")

# ================= CONFIGURACIÓN DEL NEGOCIO =================
# Va al final porque cambia la moneda y el impuesto de toda la aplicación.
from configuracion import VentanaConfiguracion
import estilos

check(app.puede("configuracion") and "configuracion" not in config.PERMISOS["cajero"],
      "solo el administrador puede abrir la configuración")

vc = VentanaConfiguracion(ct, app)
check(vc.e["negocio_nombre"].get() == "Minimarket" and vc.e["moneda_simbolo"].get() == "C$",
      "la configuración se abre con los valores vigentes")

for clave, texto, esperado in [("negocio_nombre", "", "nombre del negocio es obligatorio"),
                               ("moneda_simbolo", "", "símbolo de la moneda"),
                               ("impuesto_nombre", "", "nombre del impuesto"),
                               ("codigo_registro", "12", "al menos 4 caracteres"),
                               ("moneda_decimales", "ocho", "deben ser números"),
                               ("moneda_decimales", "9", "decimales van de 0 a 4"),
                               ("impuesto_tasa", "150", "tasa del impuesto va de 0"),
                               ("moneda_billetes", "100,abc", "separados por coma")]:
    vc.cargar()
    escribir(vc.e[clave], texto)
    vc.guardar()
    check(esperado in vc.lbl_mensaje.cget("text"), f"configuración rechaza: {clave} = «{texto}»")

vc.cargar()
escribir(vc.e["negocio_nombre"], "Pulpería La Esquina")
escribir(vc.e["negocio_ruc"], "J0310000000099")
escribir(vc.e["moneda_simbolo"], "$")
escribir(vc.e["moneda_decimales"], "2")
escribir(vc.e["moneda_billetes"], "50,100,500,1000")
escribir(vc.e["impuesto_nombre"], "ITBMS")
escribir(vc.e["impuesto_tasa"], "7")
escribir(vc.e["factura_despedida"], "Gracias por preferirnos")
vc.logo_nuevo = os.path.join("fotos", "agua.png")    # simula elegir un logo
vc.aplicar_tasa.set(True)
gravados = valor("SELECT COUNT(*) FROM articulos WHERE iva > 0")
vc.guardar()

check(ajustes.obtener("negocio_nombre") == "Pulpería La Esquina"
      and valor("SELECT valor FROM configuracion WHERE clave = 'negocio_nombre'") == "Pulpería La Esquina",
      "la configuración se guarda en la base")
check(estilos.moneda(1234.5) == "$ 1,234.50" and ajustes.moneda(0) == "$ 0.00",
      "el símbolo de la moneda cambia en toda la aplicación")
check(ajustes.billetes() == [50, 100, 500, 1000], "los billetes del cobro rápido son configurables")
check(ajustes.nombre_impuesto() == "ITBMS" and ajustes.tasa_impuesto() == 7,
      "el impuesto se puede renombrar y cambiarle la tasa")
check(valor("SELECT COUNT(*) FROM articulos WHERE iva = 7") == gravados
      and valor("SELECT COUNT(*) FROM articulos WHERE iva = 15") == 0,
      "la tasa nueva se aplica a los productos gravados")
check(os.path.exists(ajustes.obtener("negocio_logo"))
      and ajustes.obtener("negocio_logo").startswith("imagenes"), "el logo se copia junto al programa")
check("Pulpería La Esquina" in app.title(), "el título de la ventana toma el nombre nuevo")
check(ct.lbl_marca.cget("text").startswith("PULPER"), "la barra superior toma el nombre nuevo")
ct.show_frames(Ventas)
check(v.titulos["lbl_iva"].cget("text") == "ITBMS" and v.tree.heading("iva")["text"] == "ITBMS"
      and "ITBMS" in v.lbl_nota_impuesto.cget("text"),
      "Ventas se renombra al impuesto nuevo sin reiniciar")

app.show_frame(Login)
check("Pulpería La Esquina" in str(lg.marca.itemcget(lg.marca.find_all()[-4], "text"))
      or any("Pulpería" in str(lg.marca.itemcget(i, "text"))
             for i in lg.marca.find_all() if lg.marca.type(i) == "text"),
      "el inicio de sesión muestra el nombre nuevo")

# La factura se arma con la configuración nueva.
import factura
numero_factura = valor("SELECT MAX(factura) FROM ventas")
ruta_pdf = factura.generar_pdf(factura.datos_desde_bd(numero_factura))
check(os.path.exists(ruta_pdf) and os.path.getsize(ruta_pdf) > 1000, "la factura se genera con la configuración nueva")

# ================= REGISTRO DE ERRORES =================
try:
    raise ValueError("error de prueba")
except ValueError as e:
    app.report_callback_exception(ValueError, e, None)
check("Error inesperado" in [m[1] for m in MENSAJES][-1] if MENSAJES else False,
      "un error no controlado avisa al usuario en vez de cerrarse en silencio")
with open(registro.ARCHIVO, encoding="utf-8") as f:
    contenido = f.read()
check("error de prueba" in contenido and "Minimarket v" in contenido,
      "el error queda anotado en logs/minimarket.log para dar soporte")

app.destroy()
print(f"\nTODAS LAS PRUEBAS PASARON: {OK}")
shutil.rmtree(COPIA, ignore_errors=True)
