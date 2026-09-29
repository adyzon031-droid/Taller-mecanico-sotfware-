"""Consultas de autenticación y alta administrativa de cuentas."""
from db import connect


class AuthRepository:
    def buscar_por_correo(self, correo):
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id,nombre,email,password_hash,rol,taller_id,activo FROM usuarios WHERE email=%s LIMIT 1",
                    (correo.lower().strip(),),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    def crear_usuario(self, nombre, correo, password_hash, rol, taller_id):
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO usuarios (nombre,email,password_hash,rol,taller_id,activo) VALUES (%s,%s,%s,%s,%s,1)",
                    (nombre.strip(), correo.lower().strip(), password_hash, rol, taller_id),
                )
                user_id = cursor.lastrowid
            connection.commit()
            return user_id
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
