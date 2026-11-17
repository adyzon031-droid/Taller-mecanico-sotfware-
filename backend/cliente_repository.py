"""SQL parametrizado de clientes con aislamiento de empresa/taller."""
from pathlib import Path
import os
from db import connect
from pagination import parse_page

SORT_COLUMNS={"nombre":"c.nombre_completo","taller":"t.nombre","estado":"e.valor","fecha":"c.created_at"}

class ClienteRepository:
    @staticmethod
    def _run(sql,args=(),fetch="all"):
        c=connect()
        try:
            with c.cursor() as x:
                x.execute(sql,args);result=x.fetchone() if fetch=="one" else x.fetchall() if fetch=="all" else x.rowcount
            c.commit()
            return result
        except Exception:c.rollback();raise
        finally:c.close()

    def taller_de_empresa(self,target,session_taller):
        return self._run("SELECT id FROM talleres WHERE id=%s AND empresa_id=(SELECT empresa_id FROM talleres WHERE id=%s) AND activo=1",(target,session_taller),"one")

    @staticmethod
    def _scope(user):
        if user['rol']=='administrador':return "t.empresa_id=(SELECT empresa_id FROM talleres WHERE id=%s)",[user['taller_id']]
        return "c.taller_id=%s",[user['taller_id']]

    def crear(self,v,photo_context=None):
        fields=("taller_id","nombre_completo","nombres","apellido_paterno","apellido_materno","datos_por_completar","curp","rfc","contacto_alterno","edad","fecha_nacimiento","celular","celular_prefijo","celular_pais","telefono_fijo","telefono_fijo_prefijo","telefono_fijo_pais","telefono_personal","telefono_trabajo","telefono_trabajo_prefijo","telefono_trabajo_pais","email","email_trabajo","foto_ruta","calle","numero_interior","colonia","colonia_manual","municipio","estado","codigo_postal","estatus_id","creado_por")
        contact=v.get("contacto") or {}
        sql=f"INSERT INTO clientes ({','.join(fields)}) VALUES ({','.join('%('+f+')s' for f in fields)})"
        c=connect()
        try:
            with c.cursor() as x:
                x.execute("SELECT id FROM estatus WHERE valor='activo'");v["estatus_id"]=x.fetchone()["id"]
                x.execute(sql,v);new_id=x.lastrowid
                self._save_contact(x,new_id,contact)
            if photo_context:os.replace(*photo_context)
            c.commit();return new_id
        except Exception:c.rollback();self._delete_dest(photo_context);raise
        finally:self._delete_temp(photo_context);c.close()

    def listar(self,user,filters=None,page=1,page_size=10,sort='fecha',direction='desc',status='activo'):
        filters=filters or {}; parsed=parse_page({'page':page,'page_size':page_size,'sort':sort,'direction':direction},SORT_COLUMNS,'fecha')
        page,page_size,direction=parsed.page,parsed.page_size,parsed.direction;col=SORT_COLUMNS[parsed.sort]
        scope,args=self._scope(user);where=[scope,"e.valor<>'eliminado'"];args=list(args)
        if status in ('activo','suspendido'):where.append('e.valor=%s');args.append(status)
        elif status!='todos':raise ValueError('estado')
        if user['rol']=='administrador' and filters.get('taller_id') not in (None,'','todos'):
            where.append('c.taller_id=%s');args.append(int(filters['taller_id']))
        q=str(filters.get('q') or '').strip()
        if q:
            pattern='%'+q+'%';where.append('(c.nombre_completo LIKE %s OR c.curp LIKE %s OR c.email LIKE %s OR c.celular LIKE %s)');args.extend([pattern]*4)
        clause=' AND '.join('('+x+')' for x in where)
        total=self._run(f"SELECT COUNT(*) AS n FROM clientes c JOIN talleres t ON t.id=c.taller_id JOIN estatus e ON e.id=c.estatus_id WHERE {clause}",args,'one')['n']
        rows=self._run(f"SELECT c.*,e.valor estatus,t.nombre AS taller_nombre FROM clientes c JOIN talleres t ON t.id=c.taller_id JOIN estatus e ON e.id=c.estatus_id WHERE {clause} ORDER BY {col} {direction.upper()},c.id ASC LIMIT %s OFFSET %s",args+[page_size,(page-1)*page_size])
        return {'clientes':rows,'items':rows,'page':page,'page_size':page_size,'per_page':page_size,'total':total,'pages':(total+page_size-1)//page_size,'total_pages':(total+page_size-1)//page_size}

    def obtener(self,user,client_id):
        scope,args=self._scope(user)
        return self._run(f"SELECT c.*,e.valor estatus,t.nombre AS taller_nombre,cc.nombre AS contacto_nombre,cc.telefono_personal AS contacto_telefono_personal,cc.telefono_personal_prefijo AS contacto_telefono_personal_prefijo,cc.telefono_personal_pais AS contacto_telefono_personal_pais,cc.email AS contacto_email,cc.telefono_trabajo AS contacto_telefono_trabajo,cc.telefono_trabajo_prefijo AS contacto_telefono_trabajo_prefijo,cc.telefono_trabajo_pais AS contacto_telefono_trabajo_pais,cc.email_trabajo AS contacto_email_trabajo FROM clientes c JOIN talleres t ON t.id=c.taller_id JOIN estatus e ON e.id=c.estatus_id LEFT JOIN cliente_contactos cc ON cc.cliente_id=c.id WHERE c.id=%s AND {scope} AND e.valor<>'eliminado'",[client_id,*args],'one')

    def actualizar(self,session_user,client_id,v,photo_context=None):
        fields=("taller_id","nombre_completo","nombres","apellido_paterno","apellido_materno","datos_por_completar","curp","rfc","contacto_alterno","edad","fecha_nacimiento","celular","celular_prefijo","celular_pais","telefono_fijo","telefono_fijo_prefijo","telefono_fijo_pais","telefono_personal","telefono_trabajo","telefono_trabajo_prefijo","telefono_trabajo_pais","email","email_trabajo","foto_ruta","calle","numero_interior","colonia","colonia_manual","municipio","estado","codigo_postal")
        contact=v.get("contacto") or {}
        scope,scope_args=self._scope(session_user)
        sql='UPDATE clientes c JOIN talleres t ON t.id=c.taller_id JOIN estatus e ON e.id=c.estatus_id SET '+','.join(f'c.{f}=%({f})s' for f in fields)+' WHERE c.id=%(id)s AND e.valor=\'activo\' AND '+scope
        c=connect()
        try:
            with c.cursor() as x:
                values=dict(v,id=client_id)
                x.execute("SELECT c.id,e.valor FROM clientes c JOIN talleres t ON t.id=c.taller_id JOIN estatus e ON e.id=c.estatus_id WHERE c.id=%s AND "+scope+" FOR UPDATE",[client_id,*scope_args])
                locked=x.fetchone()
                if not locked or locked['valor']!='activo':c.rollback();return False
                x.execute(sql,values)
                self._save_contact(x,client_id,contact)
            if photo_context:os.replace(*photo_context)
            c.commit();return True
        except Exception:c.rollback();self._delete_dest(photo_context);raise
        finally:self._delete_temp(photo_context);c.close()

    def duplicado(self,workshop_id,v,exclude_id=None):
        checks=[];args=[workshop_id]
        for key in ('curp','rfc','email'):
            if v.get(key):checks.append(f'{key}=%s');args.append(v[key])
        phone=v.get('telefono_personal') or v.get('celular')
        prefix=v.get('telefono_personal_prefijo') or v.get('celular_prefijo','52')
        if phone:checks.append('(telefono_personal_prefijo=%s AND telefono_personal=%s)');args.extend((prefix,phone))
        if v.get('nombre_completo') and v.get('fecha_nacimiento'):
            checks.append('(nombre_completo=%s AND fecha_nacimiento=%s)');args.extend((v['nombre_completo'],v['fecha_nacimiento']))
        if not checks:return False
        sql="SELECT c.id FROM clientes c JOIN estatus e ON e.id=c.estatus_id WHERE c.taller_id=%s AND e.valor<>'eliminado' AND ("+' OR '.join(checks)+')'
        # Las columnas heredadas de estado/baja se conservan para compatibilidad,
        # pero el catálogo estatus es la fuente de verdad.
        if exclude_id: sql+=' AND c.id<>%s';args.append(exclude_id)
        return bool(self._run(sql+' LIMIT 1',args,'one'))

    def guardar_foto_y_actualizar(self,user,client_id,path):
        scope,args=self._scope(user)
        return bool(self._run("UPDATE clientes c JOIN talleres t ON t.id=c.taller_id JOIN estatus e ON e.id=c.estatus_id SET c.foto_ruta=%s WHERE "+scope+" AND c.id=%s AND e.valor='activo'",[path,*args,client_id],"count"))

    def estado(self,user,client_id,status,user_id,reason=None):
        scope,args=self._scope(user)
        c=connect()
        try:
            with c.cursor() as x:
                x.execute("SELECT c.estatus_id,e.valor FROM clientes c JOIN talleres t ON t.id=c.taller_id JOIN estatus e ON e.id=c.estatus_id WHERE c.id=%s AND "+scope+" FOR UPDATE",[client_id,*args]); row=x.fetchone()
                if not row:return False
                if status=='suspendido' and row['valor'] in ('suspendido','eliminado'):raise ValueError('El cliente ya está suspendido o eliminado.')
                if status=='activo' and row['valor']!='suspendido':raise ValueError('Solo se puede reactivar un cliente suspendido.')
                x.execute("SELECT id FROM estatus WHERE valor=%s",(status,));status_id=x.fetchone()['id']
                if status=='suspendido':x.execute("UPDATE clientes SET estatus_id=%s,suspendido_at=CURRENT_TIMESTAMP,suspendido_por=%s,motivo_suspension=%s WHERE id=%s",(status_id,user_id,reason,client_id))
                else:x.execute("UPDATE clientes SET estatus_id=%s WHERE id=%s",(status_id,client_id))
            c.commit();return True
        except ValueError as error:c.rollback();raise __import__('cliente_facade').ClienteError(str(error),409)
        except Exception:c.rollback();raise
        finally:c.close()

    def eliminar(self,user,client_id):
        scope,args=self._scope(user)
        c=connect()
        try:
            with c.cursor() as x:
                x.execute("SELECT c.id,e.valor FROM clientes c JOIN talleres t ON t.id=c.taller_id JOIN estatus e ON e.id=c.estatus_id WHERE "+scope+" AND c.id=%s FOR UPDATE",args+[client_id]);row=x.fetchone()
                if not row:return False
                x.execute("SELECT id FROM estatus WHERE valor='eliminado'");status_id=x.fetchone()['id']
                x.execute("UPDATE clientes SET estatus_id=%s WHERE id=%s",(status_id,client_id))
            c.commit();return True
        except Exception:c.rollback();raise
        finally:c.close()

    def talleres_empresa(self,user,active=True):
        return self._run("SELECT id,nombre FROM talleres WHERE empresa_id=(SELECT empresa_id FROM talleres WHERE id=%s) AND activo=%s ORDER BY nombre",(user['taller_id'],int(active)))

    @staticmethod
    def _save_contact(cursor,client_id,contact):
        cursor.execute("""INSERT INTO cliente_contactos
            (cliente_id,nombre,telefono_personal_prefijo,telefono_personal_pais,telefono_personal,email,
             telefono_trabajo_prefijo,telefono_trabajo_pais,telefono_trabajo,email_trabajo)
            VALUES (%(cliente_id)s,%(nombre)s,%(telefono_personal_prefijo)s,%(telefono_personal_pais)s,
             %(telefono_personal)s,%(email)s,%(telefono_trabajo_prefijo)s,%(telefono_trabajo_pais)s,
             %(telefono_trabajo)s,%(email_trabajo)s)
            ON DUPLICATE KEY UPDATE nombre=VALUES(nombre),telefono_personal_prefijo=VALUES(telefono_personal_prefijo),
             telefono_personal_pais=VALUES(telefono_personal_pais),telefono_personal=VALUES(telefono_personal),
             email=VALUES(email),telefono_trabajo_prefijo=VALUES(telefono_trabajo_prefijo),
             telefono_trabajo_pais=VALUES(telefono_trabajo_pais),telefono_trabajo=VALUES(telefono_trabajo),
             email_trabajo=VALUES(email_trabajo)""",dict(contact,cliente_id=client_id))

    @staticmethod
    def _delete_dest(ctx):
        if ctx:Path(ctx[1]).unlink(missing_ok=True)
    @staticmethod
    def _delete_temp(ctx):
        if ctx:Path(ctx[0]).unlink(missing_ok=True)
