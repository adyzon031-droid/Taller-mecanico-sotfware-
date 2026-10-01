"""Consultas MySQL del módulo de clientes; cada query queda acotada al taller."""
from pathlib import Path
import os

from db import connect


class ClienteRepository:
    def crear(self, valores, foto_contexto=None):
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
            if foto_contexto:
                os.replace(*foto_contexto)
            connection.commit()
            return cliente_id
        except Exception:
            connection.rollback()
            self._borrar_destino(foto_contexto)
            raise
        finally:
            self._borrar_temporal(foto_contexto)
            connection.close()

    def listar(self, taller_id, filtros=None, page=1, per_page=10):
        filtros = filtros or {}
        page = max(1, int(page))
        per_page = min(10, max(1, int(per_page)))
        where = ["taller_id=%s", "activo=1", "deleted_at IS NULL"]
        args = [taller_id]
        q = str(filtros.get("q", "")).strip()
        if q:
            pattern = f"%{q}%"
            where.append("(nombre_completo LIKE %s OR email LIKE %s OR telefono_personal LIKE %s)")
            args.extend((pattern, pattern, pattern))
        clause = " AND ".join(where)
        total = self._one(f"SELECT COUNT(*) AS total FROM clientes WHERE {clause}", args)["total"]
        rows = self._many(
            f"SELECT * FROM clientes WHERE {clause} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            [*args, per_page, (page - 1) * per_page],
        )
        return {
            "clientes": rows,
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        }

    def obtener(self, taller_id, cliente_id):
        return self._one(
            "SELECT * FROM clientes WHERE taller_id=%s AND id=%s AND activo=1 AND deleted_at IS NULL",
            (taller_id, cliente_id),
        )

    def actualizar(self, taller_id, cliente_id, valores, foto_contexto=None):
        sql = """UPDATE clientes SET nombre_completo=%(nombre_completo)s,
          contacto_alterno=%(contacto_alterno)s,edad=%(edad)s,
          fecha_nacimiento=%(fecha_nacimiento)s,telefono_personal=%(telefono_personal)s,
          telefono_trabajo=%(telefono_trabajo)s,email=%(email)s,
          email_trabajo=%(email_trabajo)s,foto_ruta=%(foto_ruta)s,
          calle=%(calle)s,colonia=%(colonia)s,municipio=%(municipio)s,
          estado=%(estado)s,codigo_postal=%(codigo_postal)s
          WHERE taller_id=%(taller_id)s AND id=%(id)s AND activo=1 AND deleted_at IS NULL"""
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM clientes WHERE taller_id=%s AND id=%s AND activo=1 AND deleted_at IS NULL FOR UPDATE",
                    (taller_id, cliente_id),
                )
                if not cursor.fetchone():
                    connection.rollback()
                    return False
                values = dict(valores, taller_id=taller_id, id=cliente_id)
                cursor.execute(sql, values)
            if foto_contexto:
                os.replace(*foto_contexto)
            connection.commit()
            return True
        except Exception:
            connection.rollback()
            self._borrar_destino(foto_contexto)
            raise
        finally:
            self._borrar_temporal(foto_contexto)
            connection.close()

    def eliminar(self, taller_id, cliente_id):
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE clientes SET activo=0,deleted_at=CURRENT_TIMESTAMP "
                    "WHERE taller_id=%s AND id=%s AND activo=1 AND deleted_at IS NULL",
                    (taller_id, cliente_id),
                )
                deleted = cursor.rowcount > 0
            connection.commit()
            return deleted
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def duplicado(self, taller_id, valores, excluir_id=None):
        matches, args = [], [taller_id]
        if valores.get("email"):
            matches.append("email=%s")
            args.append(str(valores["email"]).strip().lower())
        if valores.get("telefono_personal"):
            matches.append("telefono_personal=%s")
            args.append(str(valores["telefono_personal"]).strip())
        if valores.get("nombre_completo") and valores.get("fecha_nacimiento"):
            matches.append("(nombre_completo=%s AND fecha_nacimiento=%s)")
            args.extend((valores["nombre_completo"], valores["fecha_nacimiento"]))
        if not matches:
            return False
        sql = """SELECT id FROM clientes WHERE taller_id=%s AND activo=1 AND deleted_at IS NULL
          AND (""" + " OR ".join(matches) + ")"
        if excluir_id is not None:
            sql += " AND id<>%s"
            args.append(excluir_id)
        sql += " LIMIT 1"
        return self._one(sql, args) is not None

    def guardar_foto_y_actualizar(self, taller_id, cliente_id, ruta):
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE clientes SET foto_ruta=%s WHERE taller_id=%s AND id=%s AND activo=1 AND deleted_at IS NULL",
                    (ruta, taller_id, cliente_id),
                )
                changed = cursor.rowcount
            connection.commit()
            return changed > 0
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _borrar_destino(contexto):
        if contexto:
            Path(contexto[1]).unlink(missing_ok=True)

    @staticmethod
    def _borrar_temporal(contexto):
        if contexto:
            Path(contexto[0]).unlink(missing_ok=True)

    @staticmethod
    def _many(sql, args):
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, args)
                return cursor.fetchall()
        finally:
            connection.close()

    @staticmethod
    def _one(sql, args):
        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, args)
                return cursor.fetchone()
        finally:
            connection.close()
