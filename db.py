"""Acceso a la base de datos.

Toda la aplicación se conecta con conectar(): la conexión se cierra siempre,
se confirma (commit) si todo sale bien y se deshace (rollback) si hay un error.
Así ningún error deja la base bloqueada ni una operación a medias."""
import sqlite3
from contextlib import contextmanager

DB_NAME = "database.db"


@contextmanager
def conectar():
    conn = sqlite3.connect(DB_NAME, timeout=5)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def consultar(sql, parametros=()):
    """Devuelve todas las filas de una consulta."""
    with conectar() as conn:
        return conn.execute(sql, parametros).fetchall()


def uno(sql, parametros=()):
    """Devuelve la primera fila de una consulta (o None)."""
    with conectar() as conn:
        return conn.execute(sql, parametros).fetchone()


def ejecutar(sql, parametros=()):
    with conectar() as conn:
        conn.execute(sql, parametros)
