"""Conexión MySQL compartida; las consultas pertenecen al repository."""
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from pymysql.cursors import DictCursor

# La configuración del proceso prevalece sobre el archivo local.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def connect():
    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError("Faltan variables de entorno: " + ", ".join(missing))
    try:
        port = int(os.environ["DB_PORT"])
        connect_timeout = int(os.environ.get("DB_CONNECT_TIMEOUT", "5"))
    except ValueError as exc:
        raise RuntimeError("DB_PORT y DB_CONNECT_TIMEOUT deben ser números enteros") from exc
    if not 1 <= port <= 65535 or not 1 <= connect_timeout <= 60:
        raise RuntimeError("DB_PORT o DB_CONNECT_TIMEOUT fuera del rango permitido")
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=port,
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=connect_timeout,
        read_timeout=15,
        write_timeout=15,
    )
