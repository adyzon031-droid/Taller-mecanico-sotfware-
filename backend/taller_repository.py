"""SQL del catálogo de talleres, siempre limitado a la empresa de sesión."""
from db import connect

FIELDS = ("nombre", "razon_social", "rfc", "email_contacto", "telefono", "telefono_prefijo", "telefono_pais",
          "calle", "numero_interior", "colonia", "municipio", "estado", "codigo_postal",
          "direccion_temporal_calle", "direccion_temporal_numero_interior", "direccion_temporal_colonia",
          "direccion_temporal_municipio", "direccion_temporal_estado", "direccion_temporal_codigo_postal",
          "colonia_manual", "direccion_temporal_colonia_manual")


class TallerRepository:
    @staticmethod
    def _one(sql, args=()):
        c=connect()
        try:
            with c.cursor() as x:x.execute(sql,args);return x.fetchone()
        finally:c.close()

    @staticmethod
    def _many(sql,args=()):
        c=connect()
        try:
            with c.cursor() as x:x.execute(sql,args);return x.fetchall()
        finally:c.close()

    def empresa_de_taller(self, taller_id):
        row=self._one("SELECT empresa_id FROM talleres WHERE id=%s",(taller_id,))
        return row["empresa_id"] if row else None

    def listar(self, session_user, activos=None):
        if session_user["rol"]=="recepcionista":
            return self._many("SELECT * FROM talleres WHERE id=%s",(session_user["taller_id"],))
        empresa=self.empresa_de_taller(session_user["taller_id"])
        if not empresa:return []
        sql="SELECT * FROM talleres WHERE empresa_id=%s";args=[empresa]
        if activos is not None:sql+=" AND activo=%s";args.append(int(activos))
        return self._many(sql+" ORDER BY nombre",args)

    def obtener(self, session_user, taller_id):
        if session_user["rol"]=="recepcionista":
            return self._one("SELECT * FROM talleres WHERE id=%s AND id=%s",(session_user["taller_id"],taller_id))
        empresa=self.empresa_de_taller(session_user["taller_id"])
        if not empresa:return None
        return self._one("SELECT * FROM talleres WHERE id=%s AND empresa_id=%s",(taller_id,empresa))

    def crear(self, session_user, values):
        empresa=self.empresa_de_taller(session_user["taller_id"])
        columns=("empresa_id",*FIELDS)
        sql="INSERT INTO talleres ("+",".join(columns)+") VALUES ("+",".join(["%s"]*len(columns))+")"
        args=[empresa]+[values.get(f) for f in FIELDS]
        c=connect()
        try:
            with c.cursor() as x:x.execute(sql,args);new_id=x.lastrowid
            c.commit();return new_id
        except Exception:c.rollback();raise
        finally:c.close()

    def actualizar(self, session_user, taller_id, values):
        row=self.obtener(session_user,taller_id)
        if not row:return False
        c=connect()
        try:
            with c.cursor() as x:
                x.execute("UPDATE talleres SET "+",".join(f"{field}=%s" for field in FIELDS)+" WHERE id=%s",[values.get(f) for f in FIELDS]+[taller_id])
            c.commit();return True
        except Exception:c.rollback();raise
        finally:c.close()

    def actualizar_foto(self,session_user,taller_id,path):
        row=self.obtener(session_user,taller_id)
        if not row:return False
        c=connect()
        try:
            with c.cursor() as x:x.execute("UPDATE talleres SET foto_ruta=%s WHERE id=%s",(path,taller_id))
            c.commit();return True
        except Exception:c.rollback();raise
        finally:c.close()

    def estado(self,session_user,taller_id,active,user_id,reason=None):
        row=self.obtener(session_user,taller_id)
        if not row:return False
        c=connect()
        try:
            with c.cursor() as x:
                x.execute("UPDATE talleres SET activo=%s,suspendido_at=%s,suspendido_por=%s,motivo_suspension=%s WHERE id=%s",
                    (int(active),None if active else __import__('datetime').datetime.now(),None if active else user_id,None if active else reason,taller_id))
            c.commit();return True
        except Exception:c.rollback();raise
        finally:c.close()
