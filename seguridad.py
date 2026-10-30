"""Contraseñas con hash (PBKDF2-SHA256 con sal aleatoria).

En la base nunca se guarda la contraseña, solo su hash: aunque alguien abra
database.db, no puede leer las contraseñas."""
import hashlib
import hmac
import os

ITERACIONES = 120_000


def hash_password(password):
    sal = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${sal.hex()}${h.hex()}"


def verificar_password(password, guardado):
    try:
        _, iteraciones, sal, h = guardado.split("$")
    except ValueError:
        return False
    calculado = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(sal), int(iteraciones))
    return hmac.compare_digest(calculado.hex(), h)
