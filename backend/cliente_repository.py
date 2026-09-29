"""Persistencia MySQL y acceso a los servicios REST de clientes."""
from db import connect


class ClienteRepository:
    def crear(self, valores):
        sql = """INSERT INTO clientes
          (taller_id,nombre_completo,contacto_alterno,edad,fecha_nacimiento,
           telefono_personal,telefono_trabajo,email,email_trabajo,foto_ruta,
           calle,colonia,municipio,estado,codigo_postal,creado_por)
          VALUES (%(taller_id)s,%(nombre_completo)s,%(contacto_alterno)s,
           %(edad)s,%(fecha_nacimiento)s,%(telefono_personal)s,%(telefono_trabajo)s,
           %(email)s,%(email_trabajo)s,%(foto_ruta)s,%(calle)s,%(colonia)s,
           %(municipio)s,%(estado)s,%(codigo_postal)s,%(creado_por)s)"""
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, valores)
                cliente_id = cursor.lastrowid
            connection.commit()
            return cliente_id
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def listar(self, taller_id, filtros):
        sql = "SELECT * FROM clientes WHERE taller_id=%s"
        args = [taller_id]
        for field in ("nombre_completo", "email", "telefono_personal"):
            if filtros.get(field):
                sql += f" AND {field} LIKE %s"
                args.append("%" + filtros[field] + "%")
        sql += " ORDER BY created_at DESC"
        return self._many(sql, args)

    def obtener(self, taller_id, cliente_id):
        rows = self._many("SELECT * FROM clientes WHERE taller_id=%s AND id=%s", (taller_id, cliente_id))
        return rows[0] if rows else None

    def actualizar(self, taller_id, cliente_id, valores):
        sql = """UPDATE clientes SET nombre_completo=%(nombre_completo)s,
          contacto_alterno=%(contacto_alterno)s,edad=%(edad)s,
          fecha_nacimiento=%(fecha_nacimiento)s,telefono_personal=%(telefono_personal)s,
          telefono_trabajo=%(telefono_trabajo)s,email=%(email)s,
          email_trabajo=%(email_trabajo)s,calle=%(calle)s,colonia=%(colonia)s,
          municipio=%(municipio)s,estado=%(estado)s,codigo_postal=%(codigo_postal)s
          WHERE taller_id=%(taller_id)s AND id=%(id)s"""
        valores.update(taller_id=taller_id, id=cliente_id)
        connection = connect()
        try:
            with connection.cursor() as cursor:
                changed = cursor.execute(sql, valores)
            connection.commit()
            return changed > 0
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def duplicado(self, taller_id, valores, excluir_id=None):
        clauses = ["taller_id=%s"]
        args = [taller_id]
        clauses.append("(email=%s OR telefono_personal=%s OR (nombre_completo=%s AND fecha_nacimiento=%s))")
        args.extend((valores["email"], valores["telefono_personal"], valores["nombre_completo"], valores["fecha_nacimiento"]))
        if excluir_id is not None:
            clauses.append("id<>%s")
            args.append(excluir_id)
        rows = self._many("SELECT id FROM clientes WHERE " + " AND ".join(clauses) + " LIMIT 1", args)
        return bool(rows)

    def guardar_foto_y_actualizar(self, taller_id, cliente_id, ruta):
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE clientes SET foto_ruta=%s WHERE taller_id=%s AND id=%s", (ruta, taller_id, cliente_id))
                changed = cursor.rowcount
            connection.commit()
            return changed > 0
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _many(sql, args):
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, args)
                return cursor.fetchall()
        finally:
            connection.close()
