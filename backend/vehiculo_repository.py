"""Persistencia de vehículos con aislamiento del taller de la sesión."""
import json
from pymysql.err import IntegrityError
from db import connect
from pagination import parse_page,page_result
from estatus_facade import StatusError
from vehiculo_facade import VehicleError


class VehiculoRepository:
    SORT={"placa":"v.placa","marca":"v.marca_texto","modelo":"v.modelo_texto","anio":"v.anio","fecha_ingreso":"v.fecha_ingreso","cliente":"c.nombre_completo","created_at":"v.created_at"}

    def _status(self,cur,value):
        cur.execute("SELECT id FROM estatus WHERE valor=%s",(value,));r=cur.fetchone()
        if not r: raise RuntimeError("Falta el catálogo de estatus actualizado")
        return r['id']

    def _scope(self,user): return user['taller_id']

    @staticmethod
    def _audit(cur,user,entity,entity_id,action,motivo=None,before=None,after=None):
        cur.execute('''INSERT INTO auditoria(taller_id,usuario_id,entidad,entidad_id,accion,motivo,datos_antes,datos_despues)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (user['taller_id'],user['usuario_id'],entity,entity_id,action,motivo,
                     json.dumps(before, default=str) if before else None,json.dumps(after, default=str) if after else None))

    @staticmethod
    def _snapshot(row):
        fields=("cliente_id","taller_id","placa","placa_vigente","marca_id","modelo_id","marca_texto","modelo_texto","anio","version","numero_serie","serie_vigente","kilometraje","fecha_ingreso","estatus_id","estatus")
        return {field: row.get(field) for field in fields}

    @staticmethod
    def _duplicate_error(error):
        detail=str(error)
        if "uq_vehiculos_taller_placa_vigente" in detail:
            return VehicleError("Ya existe una placa activa en este taller.",409,{"placa":"La placa ya pertenece a un vehículo activo del taller."},"PLACA_DUPLICADA")
        if "uq_vehiculos_taller_vin_activo" in detail:
            return VehicleError("Ya existe un VIN activo en este taller.",409,{"numero_serie":"El VIN ya pertenece a un vehículo activo del taller."},"VIN_DUPLICADO")
        return None

    @staticmethod
    def _possible_duplicates(cur,taller_id,d,exclude=None):
        clauses=[];args=[taller_id]
        if d.get('placa'): clauses.append('v.placa=%s');args.append(d['placa'])
        if d.get('marca') and d.get('modelo') and d.get('anio'):
            clauses.append('(v.marca_texto=%s AND v.modelo_texto=%s AND v.anio=%s)');args.extend((d['marca'],d['modelo'],d['anio']))
        if not clauses:return []
        sql='''SELECT v.id,v.placa,v.marca_texto marca,v.modelo_texto modelo,v.anio,e.valor estatus
               FROM vehiculos v JOIN estatus e ON e.id=v.estatus_id
               WHERE v.taller_id=%s AND v.deleted_at IS NULL AND ('''+ ' OR '.join(clauses)+')'
        if exclude: sql+=' AND v.id<>%s';args.append(exclude)
        cur.execute(sql,args);return cur.fetchall()

    @staticmethod
    def _vin_conflict(cur,taller_id,vin,exclude=None):
        if not vin:return None
        sql='''SELECT id FROM vehiculos WHERE taller_id=%s AND numero_serie=%s
               AND deleted_at IS NULL AND excepcion_auditada=0''';args=[taller_id,vin]
        if exclude:sql+=' AND id<>%s';args.append(exclude)
        cur.execute(sql+' LIMIT 1',args);return cur.fetchone()

    def list(self,user,args,include_deleted=False):
        p=parse_page(args,self.SORT,'created_at'); q=str(args.get('q','')).strip(); params=[self._scope(user)]; where=['v.taller_id=%s']
        if not include_deleted: where.append('v.deleted_at IS NULL')
        if args.get('marca_id'):
            where.append('v.marca_id=%s'); params.append(args['marca_id'])
        if args.get('estatus_id'):
            where.append('v.estatus_id=%s'); params.append(args['estatus_id'])
        if q:
            where.append('(v.placa LIKE %s OR v.numero_serie LIKE %s OR v.marca_texto LIKE %s OR v.modelo_texto LIKE %s OR c.nombre_completo LIKE %s)')
            params.extend([q+'%']*5)
        clause=' WHERE '+' AND '.join(where); conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f'SELECT COUNT(*) total FROM vehiculos v JOIN clientes c ON c.id=v.cliente_id{clause}',params);total=cur.fetchone()['total']
                sql=f'''SELECT v.id,v.cliente_id,v.taller_id,v.placa,v.marca_id,v.modelo_id,v.marca_texto,v.modelo_texto,v.anio,v.version,v.numero_serie,v.kilometraje,v.fecha_ingreso,v.estatus_id,e.valor estatus,c.nombre_completo cliente_nombre,v.created_at,v.updated_at,v.deleted_at
                FROM vehiculos v JOIN clientes c ON c.id=v.cliente_id JOIN estatus e ON e.id=v.estatus_id{clause} ORDER BY {self.SORT[p.sort]} {p.direction.upper()},v.id LIMIT %s OFFSET %s'''
                cur.execute(sql,params+[p.page_size,(p.page-1)*p.page_size]);return page_result(cur.fetchall(),total,p.page,p.page_size)
        finally:conn.close()

    def get(self,user,record_id):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute('''SELECT v.*,e.valor estatus FROM vehiculos v JOIN estatus e ON e.id=v.estatus_id WHERE v.id=%s AND v.taller_id=%s AND v.deleted_at IS NULL''',(record_id,self._scope(user)));return cur.fetchone()
        finally:conn.close()

    def verify_plate(self,user,plate,exclude=None):
        conn=connect()
        try:
            with conn.cursor() as cur:
                sql='SELECT 1 FROM vehiculos WHERE placa=%s AND taller_id=%s AND deleted_at IS NULL'; args=[plate,self._scope(user)]
                if exclude: sql+=' AND id<>%s';args.append(exclude)
                cur.execute(sql+' LIMIT 1',args);return bool(cur.fetchone())
        finally:conn.close()

    def create(self,user,d):
        conn=connect(); warnings=d['_warnings']; status=None
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT c.estatus_id,e.valor FROM clientes c JOIN estatus e ON e.id=c.estatus_id WHERE c.id=%s AND c.taller_id=%s FOR UPDATE',(d.get('cliente_id'),self._scope(user))); client=cur.fetchone()
                if not client: raise StatusError('Cliente no encontrado en el taller.',404)
                client_status=client['valor']
                if client_status!='activo': raise StatusError('El cliente debe estar activo para recibir vehículos.',409)
                conflict=self._vin_conflict(cur,self._scope(user),d.get('numero_serie'))
                if conflict and not d.get('permitir_excepcion'):
                    raise VehicleError('Ya existe un VIN activo en este taller.',409,{'numero_serie':'VIN duplicado.'},'VIN_DUPLICADO')
                status=self._status(cur,'activo')
                brand_id=d.get('marca_id'); model_id=d.get('modelo_id')
                pending=self._status(cur,'en espera')
                if model_id:
                    cur.execute("SELECT mo.marca_id,mo.nombre,e.valor FROM modelos mo JOIN estatus e ON e.id=mo.estatus_id WHERE mo.id=%s AND e.valor IN ('activo','en espera')",(model_id,)); model=cur.fetchone()
                    if not model or (brand_id and int(model['marca_id'])!=int(brand_id)): raise StatusError('El modelo no pertenece a la marca elegida.',422,{'modelo_id':'El modelo no pertenece a la marca.'})
                # Cuando llega texto manual, se enlaza a un resultado exacto; si no existe se deja sin FK.
                if not brand_id:
                    from vehiculo_catalogo_facade import comparar_nombre
                    cur.execute('SELECT id,nombre FROM marcas'); candidates=cur.fetchall()
                    r=next((x for x in candidates if comparar_nombre(x['nombre'])==comparar_nombre(d['marca'])),None)
                    if r:brand_id=r['id']
                    else:
                        cur.execute('INSERT INTO marcas(nombre,estatus_id) VALUES(%s,%s)',(d['marca'],pending));brand_id=cur.lastrowid
                if not model_id and d.get('modelo'):
                    from vehiculo_catalogo_facade import comparar_nombre
                    cur.execute('SELECT id,nombre FROM modelos WHERE marca_id=%s',(brand_id,)); candidates=cur.fetchall()
                    r=next((x for x in candidates if comparar_nombre(x['nombre'])==comparar_nombre(d['modelo'])),None)
                    if r:model_id=r['id']
                    else:
                        cur.execute('INSERT INTO modelos(marca_id,nombre,estatus_id) VALUES(%s,%s,%s)',(brand_id,d['modelo'],pending));model_id=cur.lastrowid
                exception=bool(conflict and d.get('permitir_excepcion'))
                cur.execute('''INSERT INTO vehiculos(cliente_id,taller_id,placa,placa_vigente,marca_id,modelo_id,marca_texto,modelo_texto,anio,version,numero_serie,serie_vigente,kilometraje,fecha_ingreso,estatus_id,created_by,excepcion_auditada)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',(d['cliente_id'],self._scope(user),d['placa'],d['placa'],brand_id,model_id,d['marca'],d.get('modelo'),d['anio'],d.get('version'),d.get('numero_serie'),None if exception else d.get('numero_serie'),d.get('kilometraje'),d['fecha_ingreso'],status,user['usuario_id'],int(exception)))
                new_id=cur.lastrowid
                cur.execute("INSERT INTO cliente_vehiculo(cliente_id,vehiculo_id,taller_id,tipo_relacion,es_principal,fecha_inicio,created_by,principal_vigente_valor,relacion_vigente_valor) VALUES(%s,%s,%s,'propietario',1,%s,%s,%s,%s)",(d['cliente_id'],new_id,self._scope(user),d['fecha_ingreso'],user['usuario_id'],new_id,f'{d["cliente_id"]}:{new_id}:propietario'))
                possible=self._possible_duplicates(cur,self._scope(user),d,new_id)
                if conflict:self._audit(cur,user,'vehiculo',new_id,'vin_excepcion',d.get('motivo_excepcion'),{'vehiculo_conflicto_id':conflict['id']},{'excepcion_auditada':True})
                self._audit(cur,user,'cliente_vehiculo',new_id,'asociar_propietario',None,None,{'cliente_id':d['cliente_id']})
            conn.commit();return {'vehiculo':self.get(user,new_id),'warnings':warnings,'posibles_duplicados':possible}
        except IntegrityError as error:
            conn.rollback()
            translated=self._duplicate_error(error)
            if translated:raise translated
            raise
        except Exception:conn.rollback();raise
        finally:conn.close()

    def update(self,user,record_id,d,activate=False):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute('''SELECT v.*,e.valor estatus FROM vehiculos v JOIN estatus e ON e.id=v.estatus_id
                               WHERE v.id=%s AND v.taller_id=%s FOR UPDATE''',(record_id,self._scope(user)));row=cur.fetchone()
                if not row:return None
                if row['deleted_at']:raise StatusError('El vehículo eliminado no se puede editar.',409)
                if activate and row['estatus']!='inactivo':
                    raise VehicleError('Solo se puede activar un vehículo con estatus inactivo.',409,code='ESTATUS_NO_ACTIVABLE')
                before=self._snapshot(row) if activate else None
                cur.execute('SELECT kilometraje FROM vehiculos WHERE id=%s',(record_id,));previous=cur.fetchone()['kilometraje']
                if d.get('kilometraje') is not None and previous is not None and d['kilometraje']<previous:d['_warnings'].append({'campo':'kilometraje','mensaje':'El kilometraje es menor al último registro de este vehículo.'})
                cur.execute('SELECT c.estatus_id,e.valor FROM clientes c JOIN estatus e ON e.id=c.estatus_id WHERE c.id=%s AND c.taller_id=%s',(d.get('cliente_id') or row['cliente_id'],self._scope(user)));client=cur.fetchone()
                if not client:raise StatusError('Cliente no encontrado en el taller.',404)
                if client['valor']!='activo':raise StatusError('El cliente debe estar activo para recibir vehículos.',409)
                brand_id=d.get('marca_id');model_id=d.get('modelo_id');pending=self._status(cur,'en espera')
                if model_id:
                    cur.execute('SELECT marca_id FROM modelos WHERE id=%s',(model_id,));model=cur.fetchone()
                    if not model or not brand_id or int(model['marca_id'])!=int(brand_id):raise StatusError('El modelo no pertenece a la marca elegida.',422,{'modelo_id':'El modelo no pertenece a la marca.'})
                if not brand_id:
                    from vehiculo_catalogo_facade import comparar_nombre
                    cur.execute('SELECT id,nombre FROM marcas'); brand=next((r for r in cur.fetchall() if comparar_nombre(r['nombre'])==comparar_nombre(d['marca'])),None)
                    if brand:brand_id=brand['id']
                    else:cur.execute('INSERT INTO marcas(nombre,estatus_id) VALUES(%s,%s)',(d['marca'],pending));brand_id=cur.lastrowid
                if not model_id and d.get('modelo'):
                    from vehiculo_catalogo_facade import comparar_nombre
                    cur.execute('SELECT id,nombre FROM modelos WHERE marca_id=%s',(brand_id,)); model=next((r for r in cur.fetchall() if comparar_nombre(r['nombre'])==comparar_nombre(d['modelo'])),None)
                    if model:model_id=model['id']
                    else:cur.execute('INSERT INTO modelos(marca_id,nombre,estatus_id) VALUES(%s,%s,%s)',(brand_id,d['modelo'],pending));model_id=cur.lastrowid
                next_status='activo' if activate else row['estatus']
                status_id=self._status(cur,next_status)
                active_values=next_status=='activo'
                cur.execute('''UPDATE vehiculos SET cliente_id=%s,placa=%s,placa_vigente=%s,marca_id=%s,modelo_id=%s,
                               marca_texto=%s,modelo_texto=%s,anio=%s,version=%s,numero_serie=%s,serie_vigente=%s,
                               kilometraje=%s,fecha_ingreso=%s,estatus_id=%s WHERE id=%s''',
                            (d.get('cliente_id') or row['cliente_id'],d['placa'],d['placa'] if active_values else None,
                             brand_id,model_id,d['marca'],d.get('modelo'),d['anio'],d.get('version'),d.get('numero_serie'),
                             d.get('numero_serie') if active_values else None,d.get('kilometraje'),d['fecha_ingreso'],status_id,record_id))
                if activate:
                    after={**before,"cliente_id":d.get('cliente_id') or row['cliente_id'],"placa":d['placa'],"placa_vigente":d['placa'],"marca_id":brand_id,"modelo_id":model_id,"marca_texto":d['marca'],"modelo_texto":d.get('modelo'),"anio":d['anio'],"version":d.get('version'),"numero_serie":d.get('numero_serie'),"serie_vigente":d.get('numero_serie'),"kilometraje":d.get('kilometraje'),"fecha_ingreso":d['fecha_ingreso'],"estatus_id":status_id,"estatus":"activo"}
                    self._audit(cur,user,'vehiculo',record_id,'activar',None,before,after)
            conn.commit();return {'vehiculo':self.get(user,record_id),'warnings':d['_warnings']}
        except IntegrityError as error:
            conn.rollback()
            translated=self._duplicate_error(error)
            if translated:raise translated
            raise
        except Exception:conn.rollback();raise
        finally:conn.close()

    def activate(self,user,record_id,data):
        return self.update(user,record_id,data,activate=True)

    def deactivate(self,user,record_id,motivo):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute('''SELECT v.*,e.valor estatus FROM vehiculos v JOIN estatus e ON e.id=v.estatus_id
                               WHERE v.id=%s AND v.taller_id=%s AND v.deleted_at IS NULL FOR UPDATE''',(record_id,self._scope(user)))
                row=cur.fetchone()
                if not row:return None
                if row['estatus']!='activo':
                    raise VehicleError('Solo se puede desactivar un vehículo con estatus activo.',409,code='ESTATUS_NO_DESACTIVABLE')
                before=self._snapshot(row)
                status_id=self._status(cur,'inactivo')
                cur.execute('UPDATE vehiculos SET estatus_id=%s,placa_vigente=NULL,serie_vigente=NULL WHERE id=%s',(status_id,record_id))
                after={**before,"estatus_id":status_id,"estatus":"inactivo","placa_vigente":None,"serie_vigente":None}
                self._audit(cur,user,'vehiculo',record_id,'desactivar',motivo,before,after)
            conn.commit();return self.get(user,record_id)
        except Exception:
            conn.rollback();raise
        finally:conn.close()

    def change_deleted(self,user,record_id,restore=False):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id,placa,deleted_at,estatus_id FROM vehiculos WHERE id=%s AND taller_id=%s FOR UPDATE',(record_id,self._scope(user)));row=cur.fetchone()
                if not row:return None
                if not restore and row['deleted_at']:raise StatusError('El vehículo ya está eliminado.',409)
                if restore and not row['deleted_at']:raise StatusError('El vehículo ya está activo.',409)
                if restore:
                    cur.execute('SELECT 1 FROM vehiculos WHERE placa=%s AND deleted_at IS NULL AND id<>%s',(row['placa'],record_id))
                    if cur.fetchone():raise StatusError('La placa ya está registrada.',409)
                    cur.execute('SELECT placa,numero_serie FROM vehiculos WHERE id=%s',(record_id,)); keys=cur.fetchone()
                    st=self._status(cur,'activo');cur.execute('UPDATE vehiculos SET deleted_at=NULL,deleted_by=NULL,estatus_id=%s,placa_vigente=%s,serie_vigente=%s WHERE id=%s',(st,keys['placa'],keys['numero_serie'],record_id))
                else:
                    st=self._status(cur,'eliminado');cur.execute('UPDATE vehiculos SET deleted_at=CURRENT_TIMESTAMP,deleted_by=%s,estatus_id=%s,placa_vigente=NULL,serie_vigente=NULL WHERE id=%s',(user['usuario_id'],st,record_id))
            conn.commit();return self.get(user,record_id) if restore else {'id':record_id,'estatus':'eliminado'}
        except IntegrityError as error:
            conn.rollback()
            translated=self._duplicate_error(error)
            if translated:raise translated
            raise
        except Exception:conn.rollback();raise
        finally:conn.close()

    def relaciones(self,user,vehicle_id,include_history=False):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM vehiculos WHERE id=%s AND taller_id=%s AND deleted_at IS NULL',(vehicle_id,self._scope(user)))
                if not cur.fetchone():return None
                where='' if include_history else ' AND cv.fecha_fin IS NULL'
                cur.execute('''SELECT cv.id,cv.cliente_id,cv.tipo_relacion,cv.es_principal,cv.fecha_inicio,cv.fecha_fin,cv.motivo,cv.created_at,cv.cerrada_en
                               FROM cliente_vehiculo cv WHERE cv.vehiculo_id=%s AND cv.taller_id=%s'''+where+' ORDER BY cv.fecha_inicio DESC,cv.id DESC',(vehicle_id,self._scope(user)))
                return cur.fetchall()
        finally:conn.close()

    def asociar(self,user,vehicle_id,data):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM vehiculos WHERE id=%s AND taller_id=%s AND deleted_at IS NULL FOR UPDATE',(vehicle_id,self._scope(user)))
                if not cur.fetchone():return None
                cur.execute("SELECT c.id,e.valor FROM clientes c JOIN estatus e ON e.id=c.estatus_id WHERE c.id=%s AND c.taller_id=%s FOR UPDATE",(data['cliente_id'],self._scope(user))); client=cur.fetchone()
                if not client:raise StatusError('Cliente no encontrado en el taller.',404)
                if client['valor']!='activo':raise StatusError('El cliente debe estar activo.',409)
                principal=int(bool(data.get('es_principal')))
                relation_key=f"{data['cliente_id']}:{vehicle_id}:{data['tipo_relacion']}"
                cur.execute('''INSERT INTO cliente_vehiculo(cliente_id,vehiculo_id,taller_id,tipo_relacion,es_principal,fecha_inicio,motivo,created_by,principal_vigente_valor,relacion_vigente_valor)
                               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',(data['cliente_id'],vehicle_id,self._scope(user),data['tipo_relacion'],principal,data['fecha_inicio'],data.get('motivo') or None,user['usuario_id'],vehicle_id if principal else None,relation_key))
                relation_id=cur.lastrowid;self._audit(cur,user,'cliente_vehiculo',relation_id,'asociar',data.get('motivo'),None,{'vehiculo_id':vehicle_id,'cliente_id':data['cliente_id'],'tipo_relacion':data['tipo_relacion']})
            conn.commit();return relation_id
        except IntegrityError as error:
            conn.rollback();raise StatusError('La relación vigente ya existe o ya hay un propietario principal.',409) from error
        except Exception:conn.rollback();raise
        finally:conn.close()

    def cambiar_propietario(self,user,vehicle_id,data):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id,cliente_id FROM vehiculos WHERE id=%s AND taller_id=%s AND deleted_at IS NULL FOR UPDATE',(vehicle_id,self._scope(user))); vehicle=cur.fetchone()
                if not vehicle:return None
                cur.execute("SELECT * FROM cliente_vehiculo WHERE vehiculo_id=%s AND taller_id=%s AND es_principal=1 AND fecha_fin IS NULL FOR UPDATE",(vehicle_id,self._scope(user))); current=cur.fetchone()
                if not current:raise StatusError('El vehículo no tiene propietario principal vigente.',409)
                if current['cliente_id']==data['cliente_id']:raise VehicleError('El cliente nuevo debe ser distinto del actual.',422,{'cliente_nuevo_id':'Selecciona otro cliente.'})
                if data['fecha_efectiva']<current['fecha_inicio']:raise VehicleError('La fecha no puede ser anterior a la relación vigente.',422,{'fecha_efectiva':'La fecha no puede ser anterior al inicio vigente.'})
                cur.execute("SELECT c.id,e.valor FROM clientes c JOIN estatus e ON e.id=c.estatus_id WHERE c.id=%s AND c.taller_id=%s FOR UPDATE",(data['cliente_id'],self._scope(user))); target=cur.fetchone()
                if not target:raise StatusError('Cliente no encontrado en el taller.',404)
                if target['valor']!='activo':raise StatusError('El cliente debe estar activo.',409)
                cur.execute('UPDATE cliente_vehiculo SET fecha_fin=%s,motivo=%s,cerrada_por=%s,cerrada_en=CURRENT_TIMESTAMP,principal_vigente_valor=NULL,relacion_vigente_valor=NULL WHERE id=%s',(data['fecha_efectiva'],data['motivo'],user['usuario_id'],current['id']))
                cur.execute("INSERT INTO cliente_vehiculo(cliente_id,vehiculo_id,taller_id,tipo_relacion,es_principal,fecha_inicio,motivo,created_by,principal_vigente_valor,relacion_vigente_valor) VALUES(%s,%s,%s,'propietario',1,%s,%s,%s,%s,%s)",(data['cliente_id'],vehicle_id,self._scope(user),data['fecha_efectiva'],data['motivo'],user['usuario_id'],vehicle_id,f'{data["cliente_id"]}:{vehicle_id}:propietario'))
                relation_id=cur.lastrowid;cur.execute('UPDATE vehiculos SET cliente_id=%s WHERE id=%s',(data['cliente_id'],vehicle_id))
                self._audit(cur,user,'vehiculo',vehicle_id,'cambiar_propietario',data['motivo'],{'cliente_id':current['cliente_id']},{'cliente_id':data['cliente_id'],'relacion_id':relation_id})
            conn.commit();return relation_id
        except Exception:conn.rollback();raise
        finally:conn.close()

    def by_client(self,user,client_id,args=None):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT c.id,e.valor FROM clientes c JOIN estatus e ON e.id=c.estatus_id WHERE c.id=%s AND c.taller_id=%s AND e.valor<>'eliminado'",(client_id,self._scope(user)))
                if not cur.fetchone():return None
                p=parse_page(args or {},{'placa':'v.placa','fecha':'cv.fecha_inicio'},'placa'); historical=(args or {}).get('incluir_historicos')=='1'
                where="cv.cliente_id=%s AND cv.taller_id=%s"+("" if historical else " AND cv.fecha_fin IS NULL")
                cur.execute('SELECT COUNT(*) total FROM cliente_vehiculo cv WHERE '+where,(client_id,self._scope(user))); total=cur.fetchone()['total']
                order='v.placa' if p.sort=='placa' else 'cv.fecha_inicio'
                cur.execute('''SELECT v.id,v.placa,v.marca_texto marca,v.modelo_texto modelo,v.anio,cv.tipo_relacion,cv.es_principal,cv.fecha_inicio desde,cv.fecha_fin hasta
                               FROM cliente_vehiculo cv JOIN vehiculos v ON v.id=cv.vehiculo_id WHERE '''+where+f' ORDER BY {order} {p.direction.upper()},cv.id ASC LIMIT %s OFFSET %s',(client_id,self._scope(user),p.page_size,(p.page-1)*p.page_size))
                return page_result(cur.fetchall(),total,p.page,p.page_size)
        finally:conn.close()
