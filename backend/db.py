"""Conexión MySQL compartida; las consultas pertenecen al repository."""
import os
import pymysql
from pymysql.cursors import DictCursor


def connect():
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError("Faltan variables de entorno: " + ", ".join(missing))
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )
