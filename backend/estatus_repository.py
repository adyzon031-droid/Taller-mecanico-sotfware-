"""Consultas del catálogo de estados."""
from db import connect
from pagination import parse_page, page_result
from estatus_facade import StatusError, SYSTEM


class EstatusRepository:
    SORT = {"id": "e.id", "valor": "e.valor", "descripcion": "e.descripcion", "updated_at": "e.updated_at", "activo": "e.activo"}

    def list(self, args, active_only=False):
        page = parse_page(args, self.SORT, "valor")
        query = str(args.get("q", "")).strip()
        where = ["e.activo=1"] if active_only else []
        params = []
        if query:
            where.append("e.valor LIKE %s OR e.descripcion LIKE %s")
            params.extend([f"%{query}%", f"%{query}%"])
        clause = " WHERE " + " AND ".join(f"({x})" for x in where) if where else ""
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) total FROM estatus e{clause}", params)
                total = cur.fetchone()["total"]
                order = self.SORT[page.sort]
                cur.execute(f"SELECT e.id,e.valor,e.descripcion,e.es_sistema,e.activo,e.created_at,e.updated_at FROM estatus e{clause} ORDER BY {order} {page.direction.upper()},e.id LIMIT %s OFFSET %s", params + [page.page_size, (page.page-1)*page.page_size])
                return page_result(cur.fetchall(), total, page.page, page.page_size)
        finally:
            conn.close()

    def options(self):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id,valor,descripcion,es_sistema,activo FROM estatus WHERE activo=1 ORDER BY valor")
                return cur.fetchall()
        finally:conn.close()

    def get(self, record_id):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id,valor,descripcion,es_sistema,activo,created_at,updated_at FROM estatus WHERE id=%s",(record_id,))
                return cur.fetchone()
        finally: conn.close()

    def save(self, value, description, record_id=None):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM estatus WHERE valor=%s AND id<>%s",(value,record_id or 0))
                if cur.fetchone(): raise StatusError("Ese valor ya existe.",409,{"valor":"El valor ya está registrado."})
                if record_id:
                    cur.execute("SELECT es_sistema FROM estatus WHERE id=%s FOR UPDATE",(record_id,)); old=cur.fetchone()
                    if not old:return None
                    if old["es_sistema"]:
                        cur.execute("SELECT valor FROM estatus WHERE id=%s",(record_id,));current=cur.fetchone()["valor"]
                        if current != value: raise StatusError("Los estatus de sistema no se pueden renombrar.",409)
                    cur.execute("UPDATE estatus SET valor=%s,descripcion=%s WHERE id=%s",(value,description,record_id)); rid=record_id
                else:
                    cur.execute("INSERT INTO estatus(valor,descripcion,es_sistema,activo) VALUES(%s,%s,0,1)",(value,description));rid=cur.lastrowid
            conn.commit();return self.get(rid)
        except Exception: conn.rollback();raise
        finally: conn.close()

    def activate(self, record_id, active):
        conn=connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id,valor,es_sistema FROM estatus WHERE id=%s FOR UPDATE",(record_id,)); row=cur.fetchone()
                if not row:return None
                if not active:
                    if row["es_sistema"]: raise StatusError("Un estatus de sistema no se puede desactivar.",409)
                    # Revisa en todas las entidades que consumen el catálogo.
                    refs={"clientes":"estatus_id","vehiculos":"estatus_id","marcas":"estatus_id","modelos":"estatus_id"}
                    counts={}
                    for table,col in refs.items():
                        cur.execute(f"SELECT COUNT(*) n FROM `{table}` WHERE `{col}`=%s",(record_id,));counts[table]=cur.fetchone()["n"]
                    total=sum(counts.values())
                    if total: raise StatusError(f"En uso por {total} registros.",409,{"uso":counts})
                cur.execute("UPDATE estatus SET activo=%s WHERE id=%s",(int(active),record_id))
            conn.commit();return self.get(record_id)
        except Exception:conn.rollback();raise
        finally:conn.close()
