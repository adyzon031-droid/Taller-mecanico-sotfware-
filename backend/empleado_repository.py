"""Acceso parametrizado y transaccional a empleados y cuentas."""
from db import connect

SORTS = {"nombre":"COALESCE(e.nombres,u.nombre)","puesto":"e.puesto","taller":"t.nombre","estado":"e.activo","fecha_ingreso":"e.fecha_ingreso"}

class EmpleadoRepository:
    def _scope(self, cursor, user):
        cursor.execute("SELECT empresa_id FROM talleres WHERE id=%s", (user["taller_id"],))
        row=cursor.fetchone()
        return row["empresa_id"] if row else None

    def listar(self,user,filters,page,size,sort,direction):
        c=connect()
        try:
            with c.cursor() as x:
                empresa=self._scope(x,user)
                if not empresa:return {"empleados":[],"total":0,"page":page,"pages":0}
                where=["t.empresa_id=%s"];args=[empresa]
                if filters.get("q"):
                    q="%"+filters["q"].strip()+"%";where.append("(u.nombre LIKE %s OR u.email LIKE %s OR e.telefono_personal LIKE %s)");args += [q,q,q]
                if filters.get("taller_id"):
                    where.append("e.taller_id=%s");args.append(filters["taller_id"])
                if filters.get("estado") in ("activo","baja"):
                    where.append("e.activo=%s");args.append(int(filters["estado"]=="activo"))
                if filters.get("rol"):
                    where.append("u.rol=%s");args.append(filters["rol"])
                if filters.get("puesto"):
                    where.append("e.puesto=%s");args.append(filters["puesto"])
                clause=" AND ".join(where)
                x.execute("SELECT COUNT(*) total FROM empleados e JOIN usuarios u ON u.id=e.usuario_id JOIN talleres t ON t.id=e.taller_id WHERE "+clause,args);total=x.fetchone()["total"]
                x.execute("SELECT e.*,u.nombre,u.email,u.rol,u.activo usuario_activo,t.nombre taller_nombre FROM empleados e JOIN usuarios u ON u.id=e.usuario_id JOIN talleres t ON t.id=e.taller_id WHERE "+clause+" ORDER BY "+SORTS[sort]+" "+direction.upper()+" LIMIT %s OFFSET %s",args+[size,(page-1)*size]);rows=x.fetchall()
                return {"empleados":rows,"total":total,"page":page,"pages":(total+size-1)//size}
        finally:c.close()

    def obtener(self,user,employee_id):
        c=connect()
        try:
            with c.cursor() as x:
                empresa=self._scope(x,user)
                x.execute("SELECT e.*,u.nombre,u.email,u.rol,u.activo usuario_activo,t.nombre taller_nombre FROM empleados e JOIN usuarios u ON u.id=e.usuario_id JOIN talleres t ON t.id=e.taller_id WHERE e.id=%s AND t.empresa_id=%s",(employee_id,empresa))
                return x.fetchone()
        finally:c.close()

    def talleres(self,user):
        c=connect()
        try:
            with c.cursor() as x:
                empresa=self._scope(x,user);x.execute("SELECT id,nombre FROM talleres WHERE empresa_id=%s AND activo=1 ORDER BY nombre",(empresa,));return x.fetchall()
        finally:c.close()

    def duplicado(self,user,field,value,exclude_id=None):
        columns={"curp":"curp","rfc":"rfc","email":"email","telefono_personal":"telefono_personal"}
        column=columns.get(field)
        if not column:return False
        c=connect()
        try:
            with c.cursor() as x:
                empresa=self._scope(x,user)
                sql="SELECT 1 FROM empleados WHERE empresa_id=%s AND "+column+"=%s"
                args=[empresa,value]
                if exclude_id:sql+=" AND id<>%s";args.append(exclude_id)
                sql+=" LIMIT 1";x.execute(sql,args);return bool(x.fetchone())
        finally:c.close()

    def crear(self,user,data,password_hash):
        c=connect()
        try:
            with c.cursor() as x:
                empresa=self._scope(x,user);x.execute("SELECT id FROM talleres WHERE id=%s AND empresa_id=%s AND activo=1",(data["taller_id"],empresa))
                if not x.fetchone():return None
                x.execute("INSERT INTO usuarios(nombre,email,password_hash,rol,taller_id,activo) VALUES(%s,%s,%s,%s,%s,1)",(data["nombre"],data["email"],password_hash,data["rol"],data["taller_id"]))
                uid=x.lastrowid
                columns=[k for k in data if k in EMPLOYEE_FIELDS]
                x.execute("INSERT INTO empleados(empresa_id,taller_id,usuario_id,"+",".join(columns)+") VALUES(%s,%s,%s,"+",".join(["%s"]*len(columns))+")",[empresa,data["taller_id"],uid]+[data[k] for k in columns]);eid=x.lastrowid
            c.commit();return eid
        except Exception:c.rollback();raise
        finally:c.close()

    def actualizar(self,user,employee_id,data,password_hash=None):
        c=connect()
        try:
            with c.cursor() as x:
                empresa=self._scope(x,user);x.execute("SELECT e.usuario_id,e.activo FROM empleados e JOIN talleres t ON t.id=e.taller_id WHERE e.id=%s AND t.empresa_id=%s FOR UPDATE",(employee_id,empresa));old=x.fetchone()
                if not old:return False
                x.execute("SELECT id FROM empresas WHERE id=%s FOR UPDATE",(empresa,))
                if not old["activo"]:return "inactive"
                if data["rol"] not in ("administrador","recepcionista","mecanico"):return "invalid"
                if old["usuario_id"]==user["usuario_id"] and data["rol"]!="administrador":return "self"
                if old["usuario_id"]==user["usuario_id"] and not data.get("activo",True):return "self"
                x.execute("SELECT rol FROM usuarios WHERE id=%s",(old["usuario_id"],));old_role=x.fetchone()["rol"]
                if old_role=="administrador" and data["rol"]!="administrador":
                    x.execute("SELECT COUNT(*) n FROM empleados e JOIN usuarios u ON u.id=e.usuario_id WHERE e.empresa_id=%s AND e.activo=1 AND u.activo=1 AND u.rol='administrador'",(empresa,))
                    if x.fetchone()["n"]<=1:return "last_admin"
                if data.get("taller_id"):
                    x.execute("SELECT id FROM talleres WHERE id=%s AND empresa_id=%s AND activo=1",(data["taller_id"],empresa))
                    if not x.fetchone():return False
                columns=[k for k in data if k in EMPLOYEE_FIELDS and k not in ("id","usuario_id","activo")]
                if columns:x.execute("UPDATE empleados SET "+",".join(k+"=%s" for k in columns)+",taller_id=%s WHERE id=%s",[data[k] for k in columns]+[data["taller_id"],employee_id])
                sql="UPDATE usuarios SET nombre=%s,email=%s,rol=%s,taller_id=%s";args=[data["nombre"],data["email"],data["rol"],data["taller_id"]]
                if password_hash:sql+=",password_hash=%s";args.append(password_hash)
                x.execute(sql+" WHERE id=%s",args+[old["usuario_id"]])
            c.commit();return True
        except Exception:c.rollback();raise
        finally:c.close()

    def estado(self,user,employee_id,active,reason=None):
        c=connect()
        try:
            with c.cursor() as x:
                empresa=self._scope(x,user);x.execute("SELECT id FROM empresas WHERE id=%s FOR UPDATE",(empresa,));x.execute("SELECT e.usuario_id,e.activo,u.rol FROM empleados e JOIN usuarios u ON u.id=e.usuario_id JOIN talleres t ON t.id=e.taller_id WHERE e.id=%s AND t.empresa_id=%s FOR UPDATE",(employee_id,empresa));row=x.fetchone()
                if not row:return None
                if not active and row["usuario_id"]==user["usuario_id"]:return "self"
                if not active and row["rol"]=="administrador" and row["activo"]:
                    x.execute("SELECT COUNT(*) n FROM empleados e JOIN usuarios u ON u.id=e.usuario_id JOIN talleres t ON t.id=e.taller_id WHERE t.empresa_id=%s AND e.activo=1 AND u.activo=1 AND u.rol='administrador'",(empresa,))
                    if x.fetchone()["n"]<=1:return "last_admin"
                x.execute("UPDATE empleados SET activo=%s,fecha_baja=%s,motivo_baja=%s,baja_por=%s WHERE id=%s",(int(active),None if active else __import__('datetime').datetime.now(),None if active else (reason or None),None if active else user["usuario_id"],employee_id))
                x.execute("UPDATE usuarios SET activo=%s WHERE id=%s",(int(active),row["usuario_id"]))
            c.commit();return True
        except Exception:c.rollback();raise
        finally:c.close()

EMPLOYEE_FIELDS={"nombres","apellido_paterno","apellido_materno","curp","rfc","fecha_nacimiento","telefono_personal","telefono_personal_prefijo","telefono_personal_pais","email","telefono_trabajo","telefono_trabajo_prefijo","telefono_trabajo_pais","email_trabajo","calle","numero_interior","codigo_postal","estado","municipio","colonia","colonia_manual","contacto_emergencia_nombre","contacto_emergencia_parentesco","contacto_emergencia_telefono","contacto_emergencia_prefijo","contacto_emergencia_pais","puesto","fecha_ingreso","foto_ruta"}
