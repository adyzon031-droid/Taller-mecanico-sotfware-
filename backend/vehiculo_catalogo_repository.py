"""Acceso a datos del catálogo de vehículos."""
import re
from db import connect
from vehiculo_catalogo_facade import CatalogError, comparar_nombre


class VehicleCatalogRepository:
    def _status_id(self, cursor, name):
        cursor.execute("SELECT id FROM estatus WHERE valor=%s", (name,))
        row = cursor.fetchone()
        if not row:
            raise RuntimeError("Falta aplicar la migración del catálogo de vehículos")
        return row["id"]

    @staticmethod
    def _safe_prefix(value):
        # Los comodines ingresados por el usuario se tratan como texto literal.
        return re.sub(r"([\\%_])", r"\\\1", str(value or "").strip())

    @staticmethod
    def _like_clause(value):
        return f"{value}%"

    @staticmethod
    def _vehicle_count(cursor, column, record_id):
        cursor.execute("SELECT COUNT(*) total FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='vehiculos' AND COLUMN_NAME=%s", (column,))
        if not cursor.fetchone()["total"]:
            return 0
        cursor.execute(f"SELECT COUNT(*) total FROM vehiculos WHERE `{column}`=%s", (record_id,))
        return int(cursor.fetchone()["total"])

    def options(self, q=""):
        conn = connect()
        try:
            with conn.cursor() as cur:
                args = []
                where = "e.valor IN ('activo','en espera')"
                if q:
                    where += " AND m.nombre LIKE %s"
                    args.append(self._like_clause(self._safe_prefix(q)))
                cur.execute(f"SELECT m.id,m.nombre,e.valor estatus,(e.valor='en espera') pendiente FROM marcas m JOIN estatus e ON e.id=m.estatus_id WHERE {where} ORDER BY (m.nombre=%s) DESC,m.nombre" if q else f"SELECT m.id,m.nombre,e.valor estatus,(e.valor='en espera') pendiente FROM marcas m JOIN estatus e ON e.id=m.estatus_id WHERE {where} ORDER BY m.nombre", args + ([q] if q else []))
                return cur.fetchall()
        finally:
            conn.close()

    def model_options(self, brand_id, q=""):
        conn = connect()
        try:
            with conn.cursor() as cur:
                args = [brand_id]
                where = "mo.marca_id=%s AND e.valor IN ('activo','en espera')"
                if q:
                    where += " AND mo.nombre LIKE %s"
                    args.append(self._like_clause(self._safe_prefix(q)))
                if q:
                    cur.execute(f"SELECT mo.id,mo.marca_id,mo.nombre,e.valor estatus,(e.valor='en espera') pendiente FROM modelos mo JOIN estatus e ON e.id=mo.estatus_id WHERE {where} ORDER BY (mo.nombre=%s) DESC,mo.nombre", args+[q])
                else:
                    cur.execute(f"SELECT mo.id,mo.marca_id,mo.nombre,e.valor estatus,(e.valor='en espera') pendiente FROM modelos mo JOIN estatus e ON e.id=mo.estatus_id WHERE {where} ORDER BY mo.nombre", args)
                return cur.fetchall()
        finally:
            conn.close()

    def search(self, q, brand_id=None):
        if not q or not str(q).strip():
            return []
        prefix = self._like_clause(self._safe_prefix(q))
        conn = connect()
        try:
            with conn.cursor() as cur:
                if brand_id:
                    cur.execute("SELECT mo.id,mo.marca_id,mo.nombre modelo,m.nombre marca,e.valor estatus FROM modelos mo JOIN marcas m ON m.id=mo.marca_id JOIN estatus e ON e.id=mo.estatus_id WHERE mo.marca_id=%s AND e.valor='activo' AND mo.nombre LIKE %s ORDER BY (mo.nombre=%s) DESC,mo.nombre LIMIT 10", (brand_id,prefix,q))
                    return [{"tipo":"modelo", **r, "etiqueta": f"{r['modelo']}"} for r in cur.fetchall()]
                cur.execute("SELECT m.id marca_id,m.nombre marca,NULL modelo,e.valor estatus FROM marcas m JOIN estatus e ON e.id=m.estatus_id WHERE e.valor='activo' AND m.nombre LIKE %s ORDER BY (m.nombre=%s) DESC,m.nombre LIMIT 10", (prefix,q))
                brands=[{"tipo":"marca", **r, "etiqueta":r["marca"]} for r in cur.fetchall()]
                cur.execute("SELECT mo.id modelo_id,mo.marca_id,m.nombre marca,mo.nombre modelo,e.valor estatus FROM modelos mo JOIN marcas m ON m.id=mo.marca_id JOIN estatus e ON e.id=mo.estatus_id WHERE e.valor='activo' AND (m.nombre LIKE %s OR mo.nombre LIKE %s) ORDER BY (mo.nombre=%s OR m.nombre=%s) DESC,m.nombre,mo.nombre LIMIT 10", (prefix,prefix,q,q))
                models=[{"tipo":"combinacion", **r, "etiqueta":f"{r['marca']} · {r['modelo']}"} for r in cur.fetchall()]
                combined=brands+models
                combined.sort(key=lambda x:(0 if comparar_nombre(x.get("modelo") or x["marca"])==comparar_nombre(q) else 1, comparar_nombre(x["marca"]), comparar_nombre(x.get("modelo") or "")))
                return combined[:10]
        finally:
            conn.close()

    def list(self, table, q="", page=1, page_size=10, sort="nombre", direction="asc", brand_id=None):
        if table not in {"marcas","modelos"}:
            raise ValueError("tabla no permitida")
        conn=connect()
        try:
            with conn.cursor() as cur:
                params=[]; where=[]
                if q:
                    where.append("x.nombre LIKE %s"); params.append(self._like_clause(self._safe_prefix(q)))
                if brand_id and table=="modelos":
                    where.append("x.marca_id=%s"); params.append(brand_id)
                where_sql=" WHERE "+" AND ".join(where) if where else ""
                sort_col={"nombre":"x.nombre","estatus":"e.valor","created_at":"x.created_at"}[sort]
                joins="JOIN estatus e ON e.id=x.estatus_id"
                if table=="modelos": joins+=" JOIN marcas m ON m.id=x.marca_id"
                cur.execute(f"SELECT COUNT(*) total FROM {table} x {joins}{where_sql}",params);total=cur.fetchone()["total"]
                select="x.id,x.nombre,x.estatus_id,e.valor estatus,x.created_at,x.updated_at"
                if table=="modelos": select+=" ,x.marca_id,m.nombre marca"
                cur.execute(f"SELECT {select} FROM {table} x {joins}{where_sql} ORDER BY {sort_col} {direction.upper()},x.id LIMIT %s OFFSET %s",params+[page_size,(page-1)*page_size])
                return {"items":cur.fetchall(),"total":int(total),"page":page,"page_size":page_size,"pages":(int(total)+page_size-1)//page_size}
        finally:
            conn.close()

    def get(self, table, record_id):
        conn=connect()
        try:
            with conn.cursor() as cur:
                joins="JOIN estatus e ON e.id=x.estatus_id"
                select="x.id,x.nombre,x.estatus_id,e.valor estatus,x.created_at,x.updated_at"
                if table=="modelos": joins+=" JOIN marcas m ON m.id=x.marca_id";select+=",x.marca_id,m.nombre marca"
                cur.execute(f"SELECT {select} FROM {table} x {joins} WHERE x.id=%s",(record_id,))
                return cur.fetchone()
        finally: conn.close()

    def create(self, table, name, brand_id=None, status="activo"):
        conn=connect()
        try:
            with conn.cursor() as cur:
                status_id=self._status_id(cur,status)
                if table=="marcas": cur.execute("INSERT INTO marcas(nombre,estatus_id) VALUES(%s,%s)",(name,status_id))
                else:
                    if not self.get_brand_exists(cur,brand_id): raise CatalogError("La marca no existe.",404)
                    cur.execute("INSERT INTO modelos(marca_id,nombre,estatus_id) VALUES(%s,%s,%s)",(brand_id,name,status_id))
                record_id=cur.lastrowid
            conn.commit()
            return self.get(table,record_id)
        except Exception:
            conn.rollback();raise
        finally: conn.close()

    @staticmethod
    def get_brand_exists(cursor, brand_id):
        cursor.execute("SELECT id FROM marcas WHERE id=%s",(brand_id,));return bool(cursor.fetchone())

    def update(self, table, record_id, name, brand_id=None):
        conn=connect()
        try:
            with conn.cursor() as cur:
                if not self.get_exists(cur,table,record_id): return None
                if table=="marcas": cur.execute("UPDATE marcas SET nombre=%s WHERE id=%s",(name,record_id))
                else:
                    if not self.get_brand_exists(cur,brand_id): raise CatalogError("La marca no existe.",404)
                    cur.execute("UPDATE modelos SET nombre=%s,marca_id=%s WHERE id=%s",(name,brand_id,record_id))
            conn.commit();return self.get(table,record_id)
        except Exception:
            conn.rollback();raise
        finally:conn.close()

    @staticmethod
    def get_exists(cursor,table,record_id):
        cursor.execute(f"SELECT id FROM {table} WHERE id=%s",(record_id,));return bool(cursor.fetchone())

    def change_status(self, table, record_id, active):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT id,estatus_id FROM {table} WHERE id=%s",(record_id,));row=cur.fetchone()
                if not row:return None
                if not active:
                    count=self._vehicle_count(cur,"marca_id" if table=="marcas" else "modelo_id",record_id)
                    if count:raise CatalogError("No se puede desactivar: hay vehículos vinculados.",409,{"vehiculos":count})
                status_id=self._status_id(cur,"activo" if active else "inactivo")
                cur.execute(f"UPDATE {table} SET estatus_id=%s WHERE id=%s",(status_id,record_id))
            conn.commit();return self.get(table,record_id)
        except Exception:
            conn.rollback();raise
        finally:conn.close()

    def resolve_pending(self, brand_id, brand_name, model_name):
        conn=connect()
        try:
            with conn.cursor() as cur:
                pending=self._status_id(cur,"en espera")
                active=self._status_id(cur,"activo")
                if brand_id:
                    cur.execute("SELECT m.id,m.nombre,e.valor estatus FROM marcas m JOIN estatus e ON e.id=m.estatus_id WHERE m.id=%s",(brand_id,));brand=cur.fetchone()
                    if not brand:raise CatalogError("La marca no existe.",404)
                    if brand_name and comparar_nombre(brand["nombre"])!=comparar_nombre(brand_name):raise CatalogError("La marca seleccionada no coincide.",422,{"marca":"La marca seleccionada no coincide."})
                    resolved_brand_id=brand["id"]; resolved_brand=brand["nombre"]
                else:
                    cur.execute("SELECT m.id,m.nombre,e.valor estatus FROM marcas m JOIN estatus e ON e.id=m.estatus_id WHERE m.nombre=%s LIMIT 1",(brand_name,));brand=cur.fetchone()
                    if brand: resolved_brand_id=brand["id"];resolved_brand=brand["nombre"]
                    else:
                        cur.execute("INSERT INTO marcas(nombre,estatus_id) VALUES(%s,%s)",(brand_name,pending));resolved_brand_id=cur.lastrowid;resolved_brand=brand_name
                result={"marca_id":resolved_brand_id,"marca":resolved_brand,"marca_estatus":brand["estatus"] if brand else "en espera","modelo_id":None,"modelo":None,"modelo_estatus":None}
                if model_name:
                    cur.execute("SELECT mo.id,mo.nombre,e.valor estatus FROM modelos mo JOIN estatus e ON e.id=mo.estatus_id WHERE mo.marca_id=%s AND mo.nombre=%s LIMIT 1",(resolved_brand_id,model_name));model=cur.fetchone()
                    if model:result.update(modelo_id=model["id"],modelo=model["nombre"],modelo_estatus=model["estatus"])
                    else:
                        cur.execute("INSERT INTO modelos(marca_id,nombre,estatus_id) VALUES(%s,%s,%s)",(resolved_brand_id,model_name,pending));result.update(modelo_id=cur.lastrowid,modelo=model_name,modelo_estatus="en espera")
            conn.commit();return result
        except Exception:
            conn.rollback();raise
        finally:conn.close()
