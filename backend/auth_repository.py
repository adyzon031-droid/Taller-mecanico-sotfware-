"""Consultas de autenticación y alta administrativa de cuentas."""
from db import connect


class AuthRepository:
    def buscar_por_correo(self, correo):
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT u.id,u.nombre,u.email,u.password_hash,u.rol,u.taller_id,u.activo,t.empresa_id FROM usuarios u JOIN talleres t ON t.id=u.taller_id WHERE u.email=%s AND t.activo=1 LIMIT 1",
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
                cursor.execute(
                    "INSERT INTO empleados (empresa_id,taller_id,usuario_id,nombres,email,activo) "
                    "SELECT t.empresa_id,t.id,%s,%s,%s,1 FROM talleres t WHERE t.id=%s",
                    (user_id, nombre.strip(), correo.lower().strip(), taller_id),
                )
            connection.commit()
            return user_id
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
