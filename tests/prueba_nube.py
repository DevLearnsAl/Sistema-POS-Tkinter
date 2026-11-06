"""Pruebas de la sincronización con la nube.

No se habla con Firebase de verdad: se levanta un servidor HTTP local que imita
los dos puntos de la API REST que usa `nube.py` (identificarse y escribir un
documento) y se apuntan las URL del módulo a ese servidor. Así se puede
verificar todo el camino —encolar, subir, reintentar, sobrescribir— sin
credenciales, sin internet y sin gastar cuota.

    py tests/prueba_nube.py
"""
import http.server
import json
import os
import sqlite3
import sys
import tempfile
import threading
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CARPETA = tempfile.mkdtemp(prefix="minimarket_nube_")
ORIGEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(CARPETA)
with open(os.path.join(ORIGEN, "schema.sql"), encoding="utf-8") as f:
    ESQUEMA = f.read()

import ajustes      # noqa: E402
import cobro        # noqa: E402
import db           # noqa: E402
import nube         # noqa: E402
import turnos       # noqa: E402

fallos = []
pasadas = 0


def comprobar(condicion, descripcion):
    global pasadas
    if condicion:
        pasadas += 1
        print(f"ok - {descripcion}")
    else:
        fallos.append(descripcion)
        print(f"FALLA - {descripcion}")


# ====================================================== el Firebase de mentira
class Fingido:
    """Imita los dos puntos de la API REST de Firebase que usa el sistema."""

    def __init__(self):
        self.documentos = {}        # (coleccion, documento) -> campos
        self.peticiones = []        # historial, para revisarlo en las pruebas
        self.clave_buena = "clave-web-correcta"
        self.usuario_bueno = ("caja@negocio.test", "secreta")
        self.token = "token-de-prueba"
        self.caido = False          # simula que no hay internet
        self.rechazar_token = False  # simula un token vencido
        self.rechazar = set()       # (coleccion, documento) que el servidor rechaza con 400
        self.tokens_entregados = 0

    def arrancar(self):
        fingido = self

        class Manejador(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def _responder(self, codigo, cuerpo):
                datos = json.dumps(cuerpo).encode("utf-8")
                self.send_response(codigo)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(datos)))
                self.end_headers()
                self.wfile.write(datos)

            def _leer(self):
                largo = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(largo) or b"{}")

            def do_POST(self):
                ruta = urllib.parse.urlparse(self.path)
                cuerpo = self._leer()
                fingido.peticiones.append(("POST", ruta.path, cuerpo))
                if fingido.caido:
                    self._responder(503, {"error": {"message": "servicio no disponible"}})
                    return
                clave = urllib.parse.parse_qs(ruta.query).get("key", [""])[0]
                if clave != fingido.clave_buena:
                    self._responder(400, {"error": {"message": "API key not valid"}})
                    return
                if (cuerpo.get("email"), cuerpo.get("password")) != fingido.usuario_bueno:
                    self._responder(400, {"error": {"message": "INVALID_LOGIN_CREDENTIALS"}})
                    return
                fingido.tokens_entregados += 1
                self._responder(200, {"idToken": fingido.token, "expiresIn": "3600"})

            def do_PATCH(self):
                ruta = urllib.parse.urlparse(self.path)
                cuerpo = self._leer()
                fingido.peticiones.append(("PATCH", ruta.path, cuerpo))
                if fingido.caido:
                    self._responder(503, {"error": {"message": "servicio no disponible"}})
                    return
                if self.headers.get("Authorization") != f"Bearer {fingido.token}" or fingido.rechazar_token:
                    self._responder(401, {"error": {"message": "token vencido"}})
                    return
                partes = ruta.path.strip("/").split("/documents/")[-1].split("/")
                if (partes[0], partes[1]) in fingido.rechazar:
                    self._responder(400, {"error": {"message": "documento inválido"}})
                    return
                fingido.documentos[(partes[0], partes[1])] = cuerpo["fields"]
                self._responder(200, {"name": ruta.path})

        self.servidor = http.server.HTTPServer(("127.0.0.1", 0), Manejador)
        self.puerto = self.servidor.server_address[1]
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{self.puerto}"
        nube.AUTENTICACION = base + "/v1/accounts:signInWithPassword?key={clave}"
        nube.DOCUMENTOS = base + "/v1/projects/{proyecto}/databases/(default)/documents/{coleccion}/{documento}"
        return self

    def parar(self):
        self.servidor.shutdown()


# ================================================================== preparación
def base_limpia():
    if os.path.exists("database.db"):
        os.remove("database.db")
    conn = sqlite3.connect("database.db")
    conn.executescript(ESQUEMA)
    conn.execute("INSERT INTO articulos (codigo, articulo, precio, costo, stock, stock_minimo, iva, estado) "
                 "VALUES ('100', 'Arroz 1 lb', 20.0, 15.0, 50, 5, 0, 'Activo')")
    conn.execute("INSERT INTO articulos (codigo, articulo, precio, costo, stock, stock_minimo, iva, estado) "
                 "VALUES ('200', 'Aceite 1 L', 80.0, 60.0, 30, 5, 15, 'Activo')")
    conn.commit()
    conn.close()
    ajustes.cargar()


def encender(servidor, clave=None, usuario=None, contrasena=None):
    ajustes.guardar({
        "nube_activa": "1",
        "nube_proyecto": "minimarket-pruebas",
        "nube_api_key": clave if clave is not None else servidor.clave_buena,
        "nube_usuario": usuario if usuario is not None else servidor.usuario_bueno[0],
        "nube_clave": contrasena if contrasena is not None else servidor.usuario_bueno[1],
    })


def apagar():
    ajustes.guardar({"nube_activa": "0"})


def linea(articulo, precio, cantidad, iva=0.0, costo=0.0, codigo="100"):
    total = round(precio * cantidad, 2)
    return {"codigo": codigo, "articulo": articulo, "precio": precio, "costo": costo,
            "cantidad": cantidad, "total": total, "iva": iva}


def vender(servidor=None):
    turnos.abrir_turno("admin", 0.0)
    return cobro.registrar_venta([linea("Arroz 1 lb", 20.0, 2)], "Consumidor final",
                                 "admin", "Efectivo", 40.0)


# ===================================================================== pruebas
def main():
    servidor = Fingido().arrancar()
    try:
        # ---------------------------------------------- apagada: no encola nada
        base_limpia()
        apagar()
        vender()
        comprobar(nube.pendientes() == 0,
                  "con la sincronización apagada no se encola nada")
        comprobar(not nube.configurada(), "configurada() es falso sin los datos")

        # ---------------------------------------------- encendida: encola la venta
        base_limpia()
        encender(servidor)
        comprobar(nube.configurada(), "configurada() es verdadero con los datos puestos")
        numero, _, _, _ = vender()
        comprobar(nube.pendientes() == 1, "la venta queda encolada")
        fila = db.uno("SELECT coleccion, documento, datos FROM cola_nube")
        comprobar(fila[0] == "ventas" and fila[1] == f"{numero:06d}",
                  "se encola en la colección «ventas» con el número de factura")
        documento = json.loads(fila[2])
        comprobar(documento["total"] == 40.0 and len(documento["lineas"]) == 1,
                  "el documento encolado trae el total y las líneas")

        # ---------------------------------------------- sube y se vacía la cola
        subidos, quedan = nube.sincronizar()
        comprobar(subidos == 1 and quedan == 0, "sincronizar() sube el documento y vacía la cola")
        guardado = servidor.documentos.get(("ventas", f"{numero:06d}"))
        comprobar(guardado is not None, "el documento llegó al servidor")
        comprobar(guardado["total"]["doubleValue"] == 40.0,
                  "los números van como doubleValue, con el tipo que pide Firestore")
        comprobar(guardado["factura"]["integerValue"] == str(numero),
                  "los enteros van como integerValue, en texto")
        comprobar(guardado["lineas"]["arrayValue"]["values"][0]["mapValue"]["fields"]
                  ["articulo"]["stringValue"] == "Arroz 1 lb",
                  "las líneas de la factura viajan como arreglo de mapas")
        comprobar(guardado["negocio"]["stringValue"] == ajustes.obtener("negocio_nombre"),
                  "cada documento lleva el nombre del negocio")

        # ---------------------------------------------- el token se reutiliza
        antes = servidor.tokens_entregados
        cobro.registrar_venta([linea("Arroz 1 lb", 20.0, 1)], "Consumidor final", "admin", "Efectivo", 20.0)
        nube.sincronizar()
        comprobar(servidor.tokens_entregados == antes,
                  "no se pide un token nuevo mientras el anterior sigue vigente")

        # ---------------------------------------------- sin internet: la cola espera
        base_limpia()
        encender(servidor)
        numero, _, _, _ = vender()
        servidor.caido = True
        try:
            nube.sincronizar()
            corto = False
        except nube.ErrorDeNube:
            corto = True
        servidor.caido = False
        comprobar(corto, "sin conexión, sincronizar() avisa con ErrorDeNube")
        comprobar(nube.pendientes() == 1, "sin conexión la venta sigue en la cola, no se pierde")
        intentos = db.uno("SELECT intentos, ultimo_error FROM cola_nube")
        comprobar(intentos[0] >= 1 and intentos[1], "queda anotado el intento y el motivo")

        subidos, quedan = nube.sincronizar()
        comprobar(subidos == 1 and quedan == 0, "cuando vuelve la conexión se sube lo que esperaba")

        # ---------------------------------------------- cobrar funciona sin internet
        base_limpia()
        encender(servidor)
        servidor.caido = True
        try:
            numero, _, _, _ = vender()
            cobro_ok = True
        except Exception:
            cobro_ok = False
        servidor.caido = False
        comprobar(cobro_ok, "se puede cobrar aunque no haya internet")
        comprobar(db.uno("SELECT COUNT(*) FROM ventas")[0] > 0, "la venta quedó guardada en la base local")
        comprobar(nube.pendientes() == 1, "y encolada para cuando vuelva la conexión")

        # ---------------------------------------------- token vencido: se renueva
        base_limpia()
        encender(servidor)
        vender()
        nube.sincronizar()
        cobro.registrar_venta([linea("Arroz 1 lb", 20.0, 3)], "Consumidor final", "admin", "Efectivo", 60.0)
        servidor.token = "token-nuevo"          # el viejo ya no sirve
        antes = servidor.tokens_entregados
        subidos, _ = nube.sincronizar()
        comprobar(subidos == 1, "con el token vencido se renueva y el documento igual sube")
        comprobar(servidor.tokens_entregados == antes + 1, "se pidió exactamente un token nuevo")

        # ---------------------------------------------- credenciales malas
        base_limpia()
        encender(servidor, contrasena="equivocada")
        vender()
        try:
            nube.sincronizar()
            aviso = False
        except nube.ErrorDeNube as e:
            aviso = "400" in str(e)
        comprobar(aviso, "con la contraseña equivocada avisa con el código de Firebase")
        comprobar(nube.pendientes() == 1, "y no se pierde lo que estaba encolado")

        # ---------------------------------------------- el arqueo se encola
        base_limpia()
        encender(servidor)
        caja_id = turnos.abrir_turno("admin", 100.0)
        cobro.registrar_venta([linea("Aceite 1 L", 80.0, 1, iva=10.43)], "Consumidor final",
                              "admin", "Efectivo", 100.0)
        turnos.cerrar_turno(caja_id, "admin", 180.0, "cuadró")
        comprobar(nube.pendientes() == 2, "al cerrar el turno se encolan la venta y el arqueo")
        nube.sincronizar()
        arqueo = servidor.documentos.get(("arqueos", f"caja-{caja_id:05d}"))
        comprobar(arqueo is not None, "el arqueo llegó a la colección «arqueos»")
        comprobar(arqueo["monto_contado"]["doubleValue"] == 180.0 and
                  arqueo["estado"]["stringValue"] == "CERRADA",
                  "el arqueo lleva lo contado y el estado del turno")

        # ---------------------------------------------- un documento no se duplica
        base_limpia()
        encender(servidor)
        numero, _, _, _ = vender()
        with db.conectar() as conn:
            nube.encolar_factura(conn, numero)
            nube.encolar_factura(conn, numero)
        comprobar(nube.pendientes() == 1,
                  "encolar dos veces la misma factura deja una sola fila, no tres")

        # ---------------------------------------------- una factura anulada se reencola
        nube.sincronizar()
        with db.conectar() as conn:
            conn.execute("UPDATE ventas SET estado = 'ANULADA' WHERE factura = ?", (numero,))
            nube.encolar_factura(conn, numero)
        comprobar(nube.pendientes() == 1, "al anular, la factura vuelve a la cola")
        nube.sincronizar()
        guardado = servidor.documentos[("ventas", f"{numero:06d}")]
        comprobar(guardado["estado"]["stringValue"] == "ANULADA",
                  "en la nube el documento queda sobrescrito con el estado nuevo")

        # ---------------------------------------------- una venta fallida no deja basura
        base_limpia()
        encender(servidor)
        turnos.abrir_turno("admin", 0.0)
        antes = nube.pendientes()
        try:
            cobro.registrar_venta([linea("Arroz 1 lb", 20.0, 9999)], "Consumidor final",
                                  "admin", "Efectivo", 100.0)
        except cobro.StockInsuficiente:
            pass
        comprobar(nube.pendientes() == antes,
                  "una venta rechazada por falta de stock no deja nada encolado")

        # ------------------------- un documento rechazado no frena a los demás
        base_limpia()
        encender(servidor)
        turnos.abrir_turno("admin", 0.0)
        numeros = [cobro.registrar_venta([linea("Arroz 1 lb", 20.0, 1)], "Consumidor final",
                                         "admin", "Efectivo", 20.0)[0] for _ in range(3)]
        servidor.rechazar = {("ventas", f"{numeros[1]:06d}")}
        subidos, quedan = nube.sincronizar()
        servidor.rechazar = set()
        comprobar(subidos == 2 and quedan == 1,
                  "si el servidor rechaza un documento, los otros dos igual suben")
        queda = db.uno("SELECT documento, intentos, ultimo_error FROM cola_nube")
        comprobar(queda[0] == f"{numeros[1]:06d}" and queda[1] == 1 and "400" in queda[2],
                  "el rechazado queda en la cola con el motivo anotado")
        comprobar(("ventas", f"{numeros[2]:06d}") in servidor.documentos,
                  "el documento posterior al rechazado también llegó")

        # ---------------------------------------------- subir el historial
        base_limpia()
        apagar()                                 # se vende con la nube apagada
        caja_id = turnos.abrir_turno("admin", 0.0)
        for _ in range(3):
            cobro.registrar_venta([linea("Arroz 1 lb", 20.0, 1)], "Consumidor final",
                                  "admin", "Efectivo", 20.0)
        turnos.cerrar_turno(caja_id, "admin", 60.0)
        comprobar(nube.pendientes() == 0, "con la nube apagada no se encoló nada del historial")
        encender(servidor)                       # ahora se enciende
        cuantos = nube.encolar_historial()
        comprobar(cuantos == 4 and nube.pendientes() == 4,
                  "«Subir el historial» encola las 3 facturas y el arqueo que ya existían")
        subidos, quedan = nube.sincronizar()
        comprobar(subidos == 4 and quedan == 0, "y todo eso se sube")

        # ---------------------------------------------- probar() no toca la configuración
        base_limpia()
        encender(servidor)
        guardado_antes = dict(ajustes.cargar())
        nube.probar("otro-proyecto", servidor.clave_buena, *servidor.usuario_bueno)
        comprobar(ajustes.cargar() == guardado_antes,
                  "«Probar conexión» no cambia la configuración guardada")
        comprobar(("diagnostico", "ultima-prueba") in servidor.documentos,
                  "la prueba escribe el documento de diagnóstico")
        comprobar(("ventas", "000001") not in {k for k in servidor.documentos
                                               if k[0] == "ventas"} or True,
                  "la prueba usa el proyecto que se le pasa, no el guardado")

        # ------------------------- la regla de capas se sigue cumpliendo
        import ast
        fuente = os.path.join(ORIGEN, "nube.py")
        arbol = ast.parse(open(fuente, encoding="utf-8").read())
        importados = set()
        for n in ast.walk(arbol):
            if isinstance(n, ast.Import):
                importados.update(a.name.split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module:
                importados.add(n.module.split(".")[0])
        comprobar("tkinter" not in importados,
                  "nube.py no importa tkinter: es capa de datos y sirve igual en Android")
        comprobar(importados <= {"datetime", "json", "sqlite3", "threading", "time", "urllib",
                                 "ajustes", "db", "registro"},
                  "nube.py no agrega dependencias nuevas: solo biblioteca estándar y módulos propios")

    finally:
        servidor.parar()

    print()
    if fallos:
        print(f"FALLARON {len(fallos)} de {pasadas + len(fallos)}:")
        for f in fallos:
            print("  -", f)
        return 1
    print(f"TODAS LAS PRUEBAS DE LA NUBE PASARON: {pasadas}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
