"""Sincronización opcional con Firebase (Cloud Firestore).

La base local sigue siendo la fuente de la verdad. Este módulo no reemplaza a
SQLite: un punto de venta de mostrador tiene que poder cobrar sin internet, y
las reglas del negocio (las transacciones, los CHECK del esquema) viven en la
base local. Lo que hace acá es copiar hacia la nube lo que ya quedó guardado,
para que el dueño vea las ventas y los arqueos desde el teléfono y para tener
una copia fuera de la computadora.

Cómo funciona:

1. Cuando se registra una venta o se cierra un turno, se escribe una fila en la
   tabla `cola_nube` **dentro de la misma transacción**. Si la venta no se
   guarda, tampoco queda encolada; si se guarda, queda encolada sí o sí.
2. Un hilo en segundo plano saca lo que haya en la cola y lo sube a Firestore.
   Si no hay internet, la cola espera: nada se pierde y nadie se entera.
3. Al subir un documento se borra de la cola. Si la factura cambia después
   (se anula o se devuelve), se vuelve a encolar y se sobrescribe en la nube.

No usa el SDK de Firebase sino su API REST, con `urllib` de la biblioteca
estándar. Es a propósito: el SDK arrastra dependencias compiladas (grpc) que no
se pueden armar para Android con python-for-android, y así este módulo funciona
igual en la computadora y en el teléfono.
"""
import datetime
import json
import sqlite3
import threading
import time
import urllib.error
import urllib.request

import ajustes
import db
import registro

AUTENTICACION = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={clave}"
DOCUMENTOS = ("https://firestore.googleapis.com/v1/projects/{proyecto}/databases/(default)/documents"
              "/{coleccion}/{documento}")

ESPERA_ENTRE_RONDAS = 60          # segundos entre una pasada de la cola y la siguiente
POR_RONDA = 25                    # documentos que se suben de una vez
TIEMPO_DE_ESPERA = 15             # segundos que se le dan a cada petición
MARGEN_DEL_TOKEN = 120            # se renueva el token 2 minutos antes de que venza


class ErrorDeNube(Exception):
    """No se pudo hablar con Firebase. El mensaje es apto para mostrar al usuario.

    `codigo` es el estado HTTP que respondió el servidor, o None si ni siquiera
    se pudo llegar (sin internet, DNS caído, tiempo agotado). De eso depende si
    conviene reintentar: ver `_pasajero`.
    """

    def __init__(self, mensaje, codigo=None):
        super().__init__(mensaje)
        self.codigo = codigo


def _pasajero(error):
    """¿Vale la pena reintentar más tarde, o el documento está mal y nunca va a entrar?

    Sin respuesta (None), demasiadas peticiones (429) o un problema del lado de
    Firebase (5xx) son pasajeros: se corta la ronda y se reintenta después. Un
    rechazo 4xx es del documento o de los permisos: reintentarlo no cambia nada.
    """
    return error.codigo is None or error.codigo == 429 or error.codigo >= 500


# ============================================================ configuración
def configurada():
    """¿Están puestos los datos mínimos y la sincronización encendida?"""
    return bool(ajustes.obtener("nube_activa") == "1"
                and ajustes.obtener("nube_proyecto")
                and ajustes.obtener("nube_api_key")
                and ajustes.obtener("nube_usuario"))


def pendientes():
    """Cuántos documentos esperan en la cola."""
    try:
        return db.uno("SELECT COUNT(*) FROM cola_nube")[0]
    except sqlite3.Error:
        return 0


# ================================================================ la cola
def _encolar(conn, coleccion, documento, datos):
    """Deja el documento listo para subir. Va dentro de la transacción de quien llama.

    Si ese documento ya estaba en la cola se reemplaza: siempre se sube el
    estado más reciente, no una secuencia de versiones intermedias.
    """
    conn.execute(
        "INSERT INTO cola_nube (coleccion, documento, datos, creado) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (coleccion, documento) DO UPDATE SET "
        "datos = excluded.datos, creado = excluded.creado, intentos = 0, ultimo_error = NULL",
        (coleccion, documento, json.dumps(datos, ensure_ascii=False),
         datetime.datetime.now().isoformat(timespec="seconds")))


def encolar_factura(conn, numero):
    """Arma el documento de una factura y lo encola. Se llama dentro de la transacción.

    Con la sincronización apagada no hace nada: en una instalación que nunca usa
    Firebase, la cola se queda vacía en vez de crecer sin que nadie la vacíe.
    """
    if not configurada():
        return
    filas = conn.execute(
        "SELECT cliente, codigo, articulo, precio, cantidad, devuelto, total, iva, costo, "
        "fecha, hora, usuario, caja_id, metodo_pago, recibido, estado "
        "FROM ventas WHERE factura = ?", (numero,)).fetchall()
    if not filas:
        return
    primera = filas[0]
    documento = {
        "factura": numero,
        "cliente": primera[0],
        "fecha": primera[9],
        "hora": primera[10],
        "usuario": primera[11],
        "caja_id": primera[12],
        "metodo_pago": primera[13],
        "recibido": primera[14],
        "estado": primera[15],
        "total": round(sum(f[6] for f in filas), 2),
        "impuesto": round(sum(f[7] for f in filas), 2),
        "costo": round(sum(f[8] for f in filas), 2),
        "lineas": [{"codigo": f[1], "articulo": f[2], "precio": f[3],
                    "cantidad": f[4], "devuelto": f[5], "total": f[6], "iva": f[7]}
                   for f in filas],
    }
    _encolar(conn, "ventas", f"{numero:06d}", documento)


def encolar_arqueo(conn, caja_id):
    """Arma el documento de un turno cerrado y lo encola."""
    if not configurada():
        return
    fila = conn.execute(
        "SELECT usuario, fecha_apertura, hora_apertura, monto_inicial, fecha_cierre, hora_cierre, "
        "usuario_cierre, esperado, monto_contado, diferencia, observacion, estado "
        "FROM cajas WHERE id = ?", (caja_id,)).fetchone()
    if fila is None:
        return
    campos = ("usuario", "fecha_apertura", "hora_apertura", "monto_inicial", "fecha_cierre",
              "hora_cierre", "usuario_cierre", "esperado", "monto_contado", "diferencia",
              "observacion", "estado")
    documento = dict(zip(campos, fila), caja_id=caja_id)
    _encolar(conn, "arqueos", f"caja-{caja_id:05d}", documento)


def encolar_historial():
    """Encola todo lo que ya está guardado: facturas y turnos cerrados.

    Se usa al encender la sincronización, para que la nube arranque con el
    historial y no solo con lo que se venda de ahí en adelante.
    """
    with db.conectar() as conn:
        facturas = [f[0] for f in conn.execute("SELECT DISTINCT factura FROM ventas ORDER BY factura")]
        for numero in facturas:
            encolar_factura(conn, numero)
        cajas = [f[0] for f in conn.execute("SELECT id FROM cajas WHERE estado = 'CERRADA' ORDER BY id")]
        for caja_id in cajas:
            encolar_arqueo(conn, caja_id)
    return len(facturas) + len(cajas)


# ====================================================== conversión a Firestore
def _valor(v):
    """Traduce un valor de Python al formato con tipos que pide Firestore."""
    if v is None:
        return {"nullValue": None}
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, (list, tuple)):
        return {"arrayValue": {"values": [_valor(x) for x in v]}}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {k: _valor(x) for k, x in v.items()}}}
    return {"stringValue": str(v)}


def _documento(datos):
    return {"fields": {clave: _valor(valor) for clave, valor in datos.items()}}


# =================================================================== la red
_token = {"valor": None, "vence": 0.0, "credenciales": None}
_candado = threading.Lock()


def _pedir(url, cuerpo=None, token=None, metodo=None):
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    peticion = urllib.request.Request(url, data=datos, method=metodo)
    peticion.add_header("Content-Type", "application/json")
    if token:
        peticion.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_DE_ESPERA) as respuesta:
            return json.loads(respuesta.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        detalle = ""
        try:
            detalle = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            pass
        raise ErrorDeNube(f"Firebase respondió {e.code}. {detalle}".strip(), e.code) from e
    except urllib.error.URLError as e:
        raise ErrorDeNube(f"No se pudo conectar con Firebase: {e.reason}") from e
    except (TimeoutError, OSError) as e:
        raise ErrorDeNube(f"No se pudo conectar con Firebase: {e}") from e


def _credenciales():
    return {"proyecto": ajustes.obtener("nube_proyecto"),
            "api_key": ajustes.obtener("nube_api_key"),
            "usuario": ajustes.obtener("nube_usuario"),
            "clave": ajustes.obtener("nube_clave")}


def _pedir_token(cred):
    respuesta = _pedir(AUTENTICACION.format(clave=cred["api_key"]),
                       {"email": cred["usuario"], "password": cred["clave"],
                        "returnSecureToken": True})
    return respuesta["idToken"], int(respuesta.get("expiresIn", 3600))


def _identificarse(forzar=False):
    """Devuelve un token válido, pidiendo uno nuevo solo cuando hace falta.

    El token se guarda junto con las credenciales con que se obtuvo: si el
    administrador cambia la cuenta o el proyecto, el token viejo deja de servir
    aunque no haya vencido, y se pide otro sin que nadie tenga que acordarse.
    """
    cred = _credenciales()
    with _candado:
        if (not forzar and _token["valor"] and time.time() < _token["vence"]
                and _token["credenciales"] == cred):
            return _token["valor"]
        valor, dura = _pedir_token(cred)
        _token["valor"] = valor
        _token["vence"] = time.time() + dura - MARGEN_DEL_TOKEN
        _token["credenciales"] = cred
        return valor


def _subir(coleccion, documento, datos, token, cred=None):
    cred = cred or _credenciales()
    url = DOCUMENTOS.format(proyecto=cred["proyecto"], coleccion=coleccion, documento=documento)
    _pedir(url, _documento(dict(datos, negocio=ajustes.obtener("negocio_nombre"))),
           token=token, metodo="PATCH")


# ============================================================ sincronización
def sincronizar():
    """Sube lo que haya en la cola. Devuelve (subidos, pendientes).

    Un error de red corta la ronda: si no hay internet, no tiene sentido
    intentar con los demás. Un rechazo del servidor (datos mal formados, por
    ejemplo) se anota en esa fila y la ronda sigue con la siguiente.
    """
    if not configurada():
        return 0, 0
    filas = db.consultar(
        "SELECT id, coleccion, documento, datos FROM cola_nube ORDER BY id LIMIT ?", (POR_RONDA,))
    if not filas:
        return 0, 0

    token = _identificarse()
    subidos = 0
    for id_fila, coleccion, documento, datos in filas:
        try:
            try:
                _subir(coleccion, documento, json.loads(datos), token)
            except ErrorDeNube as e:
                if e.codigo not in (401, 403):
                    raise
                # El token pudo vencer antes de lo previsto, o cambiaron los
                # permisos: se pide uno nuevo y se intenta una sola vez más.
                token = _identificarse(forzar=True)
                _subir(coleccion, documento, json.loads(datos), token)
        except ErrorDeNube as e:
            _anotar_fallo(id_fila, str(e))
            if _pasajero(e):
                # Sin internet o con Firebase caído: no tiene sentido seguir con
                # los demás. La cola queda como está y se reintenta en la ronda
                # siguiente.
                raise
            # El servidor rechazó este documento en particular. Se anota y se
            # sigue con el resto, que puede estar bien.
            continue
        db.ejecutar("DELETE FROM cola_nube WHERE id = ?", (id_fila,))
        subidos += 1
    return subidos, pendientes()


def _anotar_fallo(id_fila, mensaje):
    try:
        db.ejecutar("UPDATE cola_nube SET intentos = intentos + 1, ultimo_error = ? WHERE id = ?",
                    (mensaje[:300], id_fila))
    except sqlite3.Error:
        pass


def probar(proyecto, api_key, usuario, clave):
    """Comprueba unas credenciales escribiendo un documento de prueba.

    Recibe los datos en vez de leerlos de la configuración: el botón «Probar
    conexión» prueba lo que está escrito en la pantalla, que todavía no se
    guardó. Tampoco toca el token del hilo de fondo, así una prueba no
    interrumpe una sincronización en curso.
    """
    cred = {"proyecto": proyecto, "api_key": api_key, "usuario": usuario, "clave": clave}
    token, _ = _pedir_token(cred)
    _subir("diagnostico", "ultima-prueba",
           {"cuando": datetime.datetime.now().isoformat(timespec="seconds"),
            "mensaje": "Conexión verificada desde el sistema Minimarket"}, token, cred)
    return True


# ============================================================== hilo de fondo
_hilo = None
_parar = threading.Event()


def _rondas():
    while not _parar.is_set():
        try:
            if configurada():
                sincronizar()
        except ErrorDeNube:
            # Sin internet o credenciales vencidas: se reintenta en la ronda
            # siguiente. No se anota en el registro para no llenarlo de ruido.
            pass
        except Exception as e:
            registro.error("Falló la sincronización con la nube", e)
        _parar.wait(ESPERA_ENTRE_RONDAS)


def iniciar():
    """Arranca el hilo que vacía la cola. No hace nada si ya está corriendo."""
    global _hilo
    if _hilo is not None and _hilo.is_alive():
        return
    _parar.clear()
    _hilo = threading.Thread(target=_rondas, name="sincronizacion-nube", daemon=True)
    _hilo.start()


def detener():
    _parar.set()
