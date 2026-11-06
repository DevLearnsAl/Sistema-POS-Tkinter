# Sincronización con Firebase

El sistema puede copiar las ventas y los arqueos a **Cloud Firestore**, para verlos
desde otra computadora o desde el teléfono y para tener una copia fuera del equipo
del mostrador.

Viene **apagada**. Mientras no se llenen los datos de acá, el sistema funciona
exactamente igual que antes y no sale a internet.

## Qué hace y qué no

**Sí hace**

- Copia cada factura a la colección `ventas` y cada turno cerrado a `arqueos`.
- Reenvía la factura cuando cambia: si se anula o se devuelve algo, el documento
  en la nube se sobrescribe con el estado nuevo.
- Guarda lo pendiente en una cola local y lo sube cuando hay internet.

**No hace**

- No reemplaza la base local. `database.db` sigue siendo la que manda.
- No baja datos de la nube: la copia va en un solo sentido.
- No sincroniza entre dos cajas. El sistema sigue siendo de una caja a la vez.

## Por qué la base sigue siendo local

Un punto de venta de mostrador tiene que poder cobrar cuando se cae internet, que
en un comercio pequeño pasa seguido. Además, las reglas que impiden vender sin
existencias, dejar media venta guardada o abrir dos turnos a la vez están escritas
en el esquema de SQLite y en transacciones `BEGIN IMMEDIATE`; Firestore no tiene
`CHECK` ni índices únicos parciales, y reescribir esas garantías del lado del
cliente sería cambiar algo que funciona por algo más frágil.

Por eso Firebase entra como **una capa de copia encima**, no como reemplazo.

## Cómo queda armado

```
    Venta cobrada ──┐
                    ├─► misma transacción ─► ventas + stock + cola_nube
    Turno cerrado ──┘                                          │
                                                               ▼
                                              hilo de fondo (cada 60 s)
                                                               │
                                                               ▼
                                                     Firestore (REST)
```

La fila de la cola se escribe **dentro de la misma transacción** que guarda la
venta. Si la venta no se guarda, tampoco queda encolada; si se guarda, queda
encolada seguro. No existe el caso de una venta que nunca se entere de que tenía
que subir.

El envío usa la **API REST** de Firebase con `urllib` de la biblioteca estándar, no
el SDK. Es a propósito: el SDK arrastra `grpc`, que es código C y no se puede
compilar para Android con python-for-android. Así el mismo `nube.py` sirve en la
computadora y en el teléfono, y no suma dependencias al proyecto.

## Preparar el proyecto en Firebase

1. Entre a <https://console.firebase.google.com> y cree un proyecto.
2. En **Compilación → Firestore Database**, cree la base en **modo producción**.
3. En **Compilación → Authentication**, habilite el proveedor **Correo electrónico
   y contraseña**.
4. En esa misma pantalla, pestaña **Users**, agregue un usuario. Va a ser la cuenta
   con la que el sistema escribe: conviene que sea una sola, de uso exclusivo, por
   ejemplo `caja@sunegocio.com`. Anote la contraseña.
5. En **Configuración del proyecto → General**, copie el **ID del proyecto** y la
   **clave de API web**.

### Reglas de seguridad

En **Firestore Database → Reglas**, pegue esto y publique:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Solo la cuenta del sistema escribe. Cambie el UID por el de su usuario:
    // está en Authentication → Users, columna «Identificador de usuario».
    function esLaCaja() {
      return request.auth != null
          && request.auth.uid == 'PEGUE-ACA-EL-UID-DE-LA-CUENTA';
    }

    match /ventas/{factura}      { allow read, write: if esLaCaja(); }
    match /arqueos/{turno}       { allow read, write: if esLaCaja(); }
    match /diagnostico/{doc}     { allow read, write: if esLaCaja(); }
    match /{documento=**}        { allow read, write: if false; }
  }
}
```

Sin estas reglas, Firestore en modo producción rechaza todo y el sistema va a
avisar «Firebase respondió 403».

## Encenderla en el sistema

Entre como administrador y abra el menú de usuario (arriba a la derecha) →
**Sincronización con la nube**.

1. Marque **Mantener este negocio sincronizado con Firebase**.
2. Llene el ID del proyecto, la clave de API web, el correo de la cuenta y su
   contraseña.
3. Pulse **Probar conexión**. Si todo está bien, escribe un documento en la
   colección `diagnostico` y lo dice.
4. **Guardar**.
5. Si quiere que la nube arranque con lo que ya está vendido, pulse **Subir el
   historial**: encola todas las facturas y los arqueos existentes.

De ahí en adelante no hay que hacer nada: lo que se venda se encola solo y el hilo
de fondo lo sube.

## Qué pasa cuando no hay internet

Nada que se note. La venta se cobra, la factura se imprime y el documento queda en
la cola. Cuando vuelve la conexión, la siguiente ronda lo sube. En la pantalla de
sincronización se ve cuántos documentos están esperando.

Si Firebase rechaza un documento en particular (por ejemplo, por las reglas), ese
se queda en la cola con el motivo anotado y los demás siguen subiendo.

## Sobre la contraseña

La contraseña de la cuenta se guarda en la tabla `configuracion`, en texto plano,
igual que el resto de los ajustes del negocio. Para un proyecto de clase está bien,
pero conviene saberlo:

- La **clave de API web no es un secreto**: Firebase la publica en cualquier
  aplicación web. Lo que protege los datos son las reglas de seguridad.
- La **contraseña de la cuenta sí lo es**. Use una cuenta creada solo para esto,
  sin acceso a nada más, y una contraseña que no use en otro lado.
- Quien tenga el archivo `database.db` puede leerla. Si eso importa, habría que
  guardarla en el almacén de credenciales del sistema operativo (`keyring` en
  Windows) en vez de la base. No está hecho.

## Dónde está el código

| Archivo | Qué hace |
|---|---|
| `nube.py` | Cola, cliente REST, reintentos y el hilo de fondo. Sin interfaz |
| `nube_pantalla.py` | La ventana de configuración |
| `schema.sql` | La tabla `cola_nube` (esquema versión 6) |
| `cobro.py`, `turnos.py`, `ventas.py` | Los cuatro puntos donde se encola |
| `tests/prueba_nube.py` | 42 pruebas contra un Firebase simulado en local |

Las pruebas no tocan Firebase de verdad: levantan un servidor HTTP que imita los
dos puntos de la API que se usan. Así se verifica el camino completo —encolar,
subir, reintentar, sobrescribir, qué pasa sin internet— sin credenciales y sin
gastar cuota:

```powershell
py tests/prueba_nube.py
```
