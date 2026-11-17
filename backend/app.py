"""API REST JSON para Fase 02. La sesión debe ser establecida por el login."""
import os
import uuid
import json
import re
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, request, send_file, send_from_directory, session
from dotenv import load_dotenv
from pymysql.err import IntegrityError

from auth_facade import AuthFacade
from auth_repository import AuthRepository
from cliente_facade import ClienteError, ClienteFacade
from cliente_repository import ClienteRepository
from taller_facade import TallerFacade
from taller_repository import TallerRepository
from ubicacion_facade import UbicacionFacade
from ubicacion_repository import UbicacionRepository
from empleado_facade import EmpleadoFacade
from empleado_repository import EmpleadoRepository
from vehiculo_catalogo_facade import CatalogError, VehicleCatalogFacade
from vehiculo_catalogo_repository import VehicleCatalogRepository
from estatus_facade import StatusError, EstatusFacade
from estatus_repository import EstatusRepository
from vehiculo_facade import VehiculoFacade, VehicleError
from vehiculo_repository import VehiculoRepository
from pagination import PaginationError, parse_page
import bcrypt
import phonenumbers

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
app = Flask(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"


@app.get("/health")
def health():
    """Comprueba que Flask y la base de datos estén disponibles."""
    from db import connect

    conexion = None
    try:
        conexion = connect()
        with conexion.cursor() as cursor:
            cursor.execute("SELECT 1")

        return jsonify(status="ok", database="ok"), 200

    except Exception:
        app.logger.exception("Falló la comprobación de salud")
        return jsonify(status="unavailable"), 503

    finally:
        if conexion is not None:
            conexion.close()


@app.get("/")
def inicio():
    """Entrega la aplicación web."""
    return send_from_directory(PROJECT_ROOT, "index.html")


@app.get("/frontend/<path:filename>")
def archivos_frontend(filename):
    """Entrega únicamente los archivos públicos del frontend."""
    return send_from_directory(FRONTEND_DIR, filename)


app.secret_key = os.environ.get("APP_SECRET_KEY", "")
if not app.secret_key:
    raise RuntimeError("La variable APP_SECRET_KEY es obligatoria.")
# Reserva margen para el multipart; _validar_foto limita el archivo en 15 MiB.
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.config["PERMANENT_SESSION_LIFETIME"] = 28800
taller_repository = TallerRepository()
facade = ClienteFacade(ClienteRepository(), taller_repository=None)
ubicacion_repository = UbicacionRepository()
ubicacion_facade = UbicacionFacade(ubicacion_repository)
facade.ubicacion_service = ubicacion_facade
facade.taller_repository = taller_repository
taller_facade = TallerFacade(taller_repository, ubicacion_facade)
auth_facade = AuthFacade(AuthRepository())
empleado_repository = EmpleadoRepository()
empleado_facade = EmpleadoFacade(empleado_repository)
vehiculo_catalogo_repository = VehicleCatalogRepository()
vehiculo_catalogo_facade = VehicleCatalogFacade(vehiculo_catalogo_repository)
estatus_repository = EstatusRepository()
estatus_facade = EstatusFacade(estatus_repository)
vehiculo_repository = VehiculoRepository()
vehiculo_facade = VehiculoFacade(vehiculo_repository, vehiculo_catalogo_repository)
ROLES = {"administrador", "recepcionista"}
PHOTO_DIR = Path(__file__).resolve().parent.parent / "storage" / "clientes"
TALLER_PHOTO_DIR = Path(__file__).resolve().parent.parent / "storage" / "talleres"
EMPLOYEE_PHOTO_DIR = Path(__file__).resolve().parent.parent / "storage" / "empleados"
ALLOWED = {"jpg", "jpeg", "png", "webp"}


@app.before_request
def cargar_sesion():
    """Obtiene identidad y taller de la sesión firmada establecida por el login."""
    g.usuario = session.get("usuario")


@app.after_request
def cors(response):
    origin = request.headers.get("Origin", "")
    allowed_origins = {
        value.strip()
        for value in os.environ.get("CORS_ORIGINS", "").split(",")
        if value.strip()
    }
    legacy_origin = os.environ.get("CORS_ORIGIN", "").strip()
    if legacy_origin:
        allowed_origins.add(legacy_origin)
    if origin and origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
        response.headers["Vary"] = "Origin"
    return response


@app.route("/api/talleres", methods=["OPTIONS"])
@app.route("/api/talleres/<path:_path>", methods=["OPTIONS"])
@app.route("/api/clientes", methods=["OPTIONS"])
@app.route("/api/clientes/<path:_path>", methods=["OPTIONS"])
@app.route("/api/auth/<path:_path>", methods=["OPTIONS"])
@app.route("/api/ubicacion/<path:_path>", methods=["OPTIONS"])
@app.route("/api/paises/<path:_path>", methods=["OPTIONS"])
@app.route("/api/marcas", methods=["OPTIONS"])
@app.route("/api/marcas/<path:_path>", methods=["OPTIONS"])
@app.route("/api/modelos", methods=["OPTIONS"])
@app.route("/api/modelos/<path:_path>", methods=["OPTIONS"])
@app.route("/api/catalogo-vehiculos/<path:_path>", methods=["OPTIONS"])
@app.route("/api/estatus", methods=["OPTIONS"])
@app.route("/api/estatus/<path:_path>", methods=["OPTIONS"])
@app.route("/api/vehiculos", methods=["OPTIONS"])
@app.route("/api/vehiculos/<path:_path>", methods=["OPTIONS"])
def preflight(_path=""):
    return "", 204


def requiere_rol(view=None, roles=None):
    allowed = set(roles or ROLES)
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = g.usuario
            if not user:
                return jsonify(error="Sesión requerida"), 401
            if str(user.get("rol", "")).lower() not in allowed:
                return jsonify(error="Permiso insuficiente"), 403
            if not user.get("usuario_id") or not user.get("taller_id"):
                return jsonify(error="La sesión no contiene usuario y taller activos"), 403
            if app.testing:
                return fn(*args, **kwargs)
            from db import connect
            connection=connect()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT u.activo,u.rol,u.taller_id,e.activo empleado_activo FROM usuarios u LEFT JOIN empleados e ON e.usuario_id=u.id WHERE u.id=%s",(user["usuario_id"],))
                    current=cursor.fetchone()
            finally:connection.close()
            if not current or not current["activo"] or current["empleado_activo"] == 0:
                session.clear();return jsonify(error="La cuenta está inactiva; inicia sesión con una cuenta activa"),401
            user["rol"]=current["rol"];user["taller_id"]=current["taller_id"];g.usuario=user;session["usuario"]=user
            return fn(*args, **kwargs)
        return wrapped
    return decorate(view) if view else decorate


def payload_cliente(row):
    if row.get("estatus"):
        row["estado_cliente"] = row["estatus"]
    for key, value in row.items():
        if isinstance(value, (date, datetime)):
            row[key] = value.isoformat()
    for field in ("celular", "telefono_fijo", "telefono_personal", "telefono_trabajo"):
        number = str(row.get(field) or "")
        prefix = str(row.get(f"{field}_prefijo") or "52")
        try:
            parsed = phonenumbers.parse(f"+{prefix}{number}", None)
            row[f"{field}_formateado"] = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        except phonenumbers.NumberParseException:
            row[f"{field}_formateado"] = ""
    if row.get("celular"):
        row["telefono_personal"] = row["celular"]
        row["telefono_personal_prefijo"] = row.get("celular_prefijo") or "52"
        row["telefono_personal_pais"] = row.get("celular_pais") or "MX"
        row["telefono_personal_formateado"] = row.get("celular_formateado", "")
    row["contacto"]={
        "nombre":row.pop("contacto_nombre",None),
        "telefono_personal":row.pop("contacto_telefono_personal",None),
        "telefono_personal_prefijo":row.pop("contacto_telefono_personal_prefijo",None),
        "telefono_personal_pais":row.pop("contacto_telefono_personal_pais",None),
        "email":row.pop("contacto_email",None),
        "telefono_trabajo":row.pop("contacto_telefono_trabajo",None),
        "telefono_trabajo_prefijo":row.pop("contacto_telefono_trabajo_prefijo",None),
        "telefono_trabajo_pais":row.pop("contacto_telefono_trabajo_pais",None),
        "email_trabajo":row.pop("contacto_email_trabajo",None),
    }
    return row


@app.errorhandler(ClienteError)
def error_cliente(error):
    body = {"error": str(error)}
    if error.errors:
        body["errors"] = error.errors
    return jsonify(body), error.status


@app.errorhandler(IntegrityError)
def error_integridad(_error):
    return jsonify(error="Registro duplicado o restricción de integridad"), 409


@app.errorhandler(413)
def foto_grande(_error):
    return jsonify(error="Revisa el archivo seleccionado.", errors={"foto": "La fotografía supera el máximo de 15 MB."}), 422


def _validar_foto(foto):
    if not foto or not foto.filename or "." not in foto.filename:
        raise ClienteError("Selecciona una fotografía.", errors={"foto": "Selecciona una fotografía."})
    ext = foto.filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED:
        raise ClienteError("Formato de fotografía inválido.", errors={"foto": "Usa JPG, JPEG, PNG o WEBP."})
    position = foto.stream.tell()
    foto.stream.seek(0, os.SEEK_END)
    size = foto.stream.tell()
    foto.stream.seek(position)
    if size > 15 * 1024 * 1024:
        raise ClienteError("La fotografía supera el máximo de 15 MB.", errors={"foto": "La fotografía supera el máximo de 15 MB."})
    header = foto.stream.read(12)
    foto.stream.seek(0)
    expected_mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    signatures = {
        "jpg": header.startswith(b"\xff\xd8\xff"),
        "jpeg": header.startswith(b"\xff\xd8\xff"),
        "png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        "webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
    }
    if not signatures.get(ext, False) or foto.mimetype != expected_mime[ext]:
        raise ClienteError("El contenido no coincide con el formato de la fotografía.", errors={"foto": "El archivo debe tener MIME y firma válidos para su extensión."})
    return ext


def _guardar_temporal(foto):
    ext = _validar_foto(foto)
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    nombre = f"{uuid.uuid4().hex}.{ext}"
    temporal, destino = PHOTO_DIR / f".{nombre}.upload", PHOTO_DIR / nombre
    try:
        foto.save(temporal)
    except Exception:
        temporal.unlink(missing_ok=True)
        raise
    return (temporal, destino), f"storage/clientes/{nombre}"


def _datos_y_foto():
    foto = None
    if request.is_json:
        datos = request.get_json(silent=True)
    elif request.mimetype == "multipart/form-data":
        try:
            datos = json.loads(request.form.get("cliente", ""))
        except json.JSONDecodeError:
            raise ClienteError("El campo cliente debe contener JSON válido.", errors={"_global": "El cuerpo no es válido."})
        foto = request.files.get("foto")
    else:
        raise ClienteError("Se requiere JSON o multipart/form-data.", errors={"_global": "Formato de envío no válido."})
    if not isinstance(datos, dict):
        raise ClienteError("Se requiere un objeto JSON cliente.", errors={"_global": "Se requiere un objeto JSON."})
    return datos, foto


@app.post("/api/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    usuario = auth_facade.autenticar(body.get("email"), body.get("password"))
    if not usuario:
        return jsonify(error="Correo o contraseña incorrectos"), 401
    session.clear()
    session["usuario"] = usuario
    session.permanent = True
    return jsonify(usuario=usuario), 200


@app.post("/api/auth/sesion")
def consultar_sesion():
    usuario = session.get("usuario")
    if not usuario:
        return jsonify(error="Sesión no iniciada"), 401
    from db import connect
    c=connect()
    try:
        with c.cursor() as x:
            x.execute("SELECT u.activo,u.rol,u.taller_id,e.activo empleado_activo FROM usuarios u LEFT JOIN empleados e ON e.usuario_id=u.id WHERE u.id=%s",(usuario.get("usuario_id"),));current=x.fetchone()
    finally:c.close()
    if not current or not current["activo"] or current["empleado_activo"]==0:
        session.clear();return jsonify(error="La cuenta está inactiva"),401
    usuario["rol"]=current["rol"];usuario["taller_id"]=current["taller_id"];session["usuario"]=usuario
    return jsonify(usuario=usuario), 200


@app.post("/api/auth/logout")
def cerrar_sesion():
    session.clear()
    return jsonify(mensaje="Sesión cerrada")


@app.get("/api/paises")
def listar_paises():
    return jsonify(paises=ubicacion_facade.paises())


@app.get("/api/paises/validar-numero")
@requiere_rol
def validar_numero_pais():
    region = request.args.get("region", "").upper()
    prefijo = request.args.get("prefijo", "")
    numero = request.args.get("numero", "")
    if not re.fullmatch(r"[A-Z]{2}", region) or not re.fullmatch(r"\d{1,3}", prefijo) or not re.fullmatch(r"\d{1,15}", numero):
        return jsonify(valido=False, error="Ingresa un número válido para el país seleccionado."), 200
    try:
        if phonenumbers.country_code_for_region(region) != int(prefijo):
            raise ValueError
        parsed = phonenumbers.parse(f"+{prefijo}{numero}", region)
        valid = phonenumbers.is_valid_number_for_region(parsed, region)
        if prefijo == "52":
            valid = valid and len(numero) == 10
    except (ValueError, phonenumbers.NumberParseException):
        valid = False
    return jsonify(valido=bool(valid), error=None if valid else "Ingresa un número válido para el país seleccionado.")


@app.get("/api/ubicacion/cp/<cp>")
@requiere_rol
def ubicacion_cp(cp):
    if not re.fullmatch(r"\d{5}", cp):
        raise ClienteError("Usa cinco dígitos para el código postal.", errors={"codigo_postal": "Usa cinco dígitos."})
    return jsonify(ubicacion_facade.cp(cp))


@app.get("/api/ubicacion/estados")
@requiere_rol
def ubicacion_estados():
    return jsonify(estados=ubicacion_facade.estados())


@app.get("/api/ubicacion/municipios")
@requiere_rol
def ubicacion_municipios():
    return jsonify(municipios=ubicacion_facade.municipios(request.args.get("estado", "")))


@app.get("/api/ubicacion/colonias")
@requiere_rol
def ubicacion_colonias():
    return jsonify(colonias=ubicacion_facade.colonias(
        request.args.get("estado", ""), request.args.get("municipio", ""), request.args.get("q", "")[:100]))


@app.get("/api/ubicacion/buscar")
@requiere_rol
def ubicacion_buscar():
    return jsonify(codigos_postales=ubicacion_facade.buscar(
        request.args.get("estado", ""), request.args.get("municipio", ""), request.args.get("colonia", "")))


@app.get("/api/talleres")
@requiere_rol
def listar_talleres():
    active=request.args.get("activo")
    if active not in (None,"0","1"):return jsonify(error="Filtro activo inválido"),400
    rows=taller_facade.listar(g.usuario)
    if active is not None:rows=[r for r in rows if int(r.get("activo",1))==int(active)]
    for row in rows:
        for key,value in row.items():
            if isinstance(value,(date,datetime)):row[key]=value.isoformat()
    return jsonify(talleres=rows)

@app.post("/api/talleres")
@requiere_rol(roles={"administrador"})
def crear_taller():
    data=request.get_json(silent=True)
    if not isinstance(data,dict):raise ClienteError("Se requiere JSON.",errors={"_global":"Formato JSON requerido."})
    return jsonify(id=taller_facade.crear(g.usuario,data)),201

@app.get("/api/talleres/<int:taller_id>")
@requiere_rol
def consultar_taller(taller_id):
    row=taller_facade.obtener(g.usuario,taller_id)
    if not row:return jsonify(error="Taller no encontrado"),404
    for key,value in row.items():
        if isinstance(value,(date,datetime)):row[key]=value.isoformat()
    return jsonify(taller=row)

@app.put("/api/talleres/<int:taller_id>")
@requiere_rol(roles={"administrador"})
def actualizar_taller(taller_id):
    data=request.get_json(silent=True)
    if not isinstance(data,dict):raise ClienteError("Se requiere JSON.",errors={"_global":"Formato JSON requerido."})
    if not taller_facade.actualizar(g.usuario,taller_id,data):return jsonify(error="Taller no encontrado"),404
    return jsonify(mensaje="Taller actualizado")

@app.patch("/api/talleres/<int:taller_id>/estado")
@requiere_rol(roles={"administrador"})
def estado_taller(taller_id):
    body=request.get_json(silent=True) or {}
    if not isinstance(body.get("activo"),bool):return jsonify(error="activo debe ser booleano",errors={"activo":"Selecciona activo o suspendido."}),422
    if not taller_facade.set_estado(g.usuario,taller_id,body["activo"],g.usuario["usuario_id"],body.get("motivo")):
        return jsonify(error="Taller no encontrado"),404
    return jsonify(mensaje="Estado actualizado")

@app.post("/api/talleres/<int:taller_id>/foto")
@requiere_rol(roles={"administrador"})
def cargar_foto_taller(taller_id):
    if not taller_facade.obtener(g.usuario,taller_id):return jsonify(error="Taller no encontrado"),404
    foto=request.files.get("foto");ext=_validar_foto(foto);TALLER_PHOTO_DIR.mkdir(parents=True,exist_ok=True)
    filename=uuid.uuid4().hex+'.'+ext;dest=TALLER_PHOTO_DIR/filename
    foto.save(dest);relative='storage/talleres/'+filename
    try:
        if not taller_repository.actualizar_foto(g.usuario,taller_id,relative):dest.unlink(missing_ok=True);return jsonify(error="Taller no encontrado"),404
    except Exception:dest.unlink(missing_ok=True);raise
    return jsonify(foto_ruta=relative),201

@app.get("/api/talleres/<int:taller_id>/foto")
@requiere_rol
def foto_taller(taller_id):
    row=taller_facade.obtener(g.usuario,taller_id)
    if not row or not row.get('foto_ruta'):return jsonify(error="Fotografía no encontrada"),404
    route=(TALLER_PHOTO_DIR/Path(row['foto_ruta']).name).resolve()
    if route.parent!=TALLER_PHOTO_DIR.resolve() or not route.is_file():return jsonify(error="Fotografía no encontrada"),404
    mime={"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","webp":"image/webp"}.get(route.suffix.lower().lstrip('.'))
    if not mime:return jsonify(error="Fotografía no encontrada"),404
    response=send_file(route,mimetype=mime,conditional=True);response.headers['Cache-Control']='private, no-store';return response

@app.get("/api/clientes/talleres")
@requiere_rol
def talleres_clientes():
    return jsonify(talleres=facade.repository.talleres_empresa(g.usuario))

@app.patch("/api/clientes/<int:cliente_id>/estado")
@requiere_rol(roles={"administrador", "recepcionista"})
def cambiar_estado_cliente(cliente_id):
    body=request.get_json(silent=True) or {};status=body.get('estado')
    if status not in ('activo','suspendido'):return jsonify(error="Estado inválido",errors={"estado":"Usa activo o suspendido."}),422
    if status=='suspendido':ok=facade.suspender(g.usuario,cliente_id,g.usuario['usuario_id'],body.get('motivo'))
    else:ok=facade.reactivar(g.usuario,cliente_id,g.usuario['usuario_id'])
    return (jsonify(mensaje="Estado actualizado"),200) if ok else (jsonify(error="Cliente no encontrado"),404)

@app.post("/api/clientes")
@requiere_rol
def crear_cliente():
    datos, foto = _datos_y_foto()
    contexto = None
    foto_ruta = None
    if foto and foto.filename:
        contexto, foto_ruta = _guardar_temporal(foto)
    try:
        cliente_id = facade.crear(datos, g.usuario, contexto, foto_ruta)
    except Exception:
        if contexto:
            Path(contexto[0]).unlink(missing_ok=True)
        raise
    return jsonify(id=cliente_id, mensaje="Cliente registrado correctamente"), 201


@app.get("/api/clientes")
@requiere_rol
def listar_clientes():
    try:
        page=parse_page(request.args,{"nombre":"c.nombre_completo","taller":"t.nombre","estado":"e.valor","fecha":"c.created_at"},"fecha",reject_oversized=True)
    except PaginationError as error:
        return jsonify(error=str(error), errors={error.field: str(error)}),400
    except ValueError as error:return jsonify(error=str(error)),400
    filters={"q":request.args.get("q",""),"taller_id":request.args.get("taller_id")}
    try:
        result=facade.listar(g.usuario,filters,page.page,page.page_size,page.sort,page.direction,request.args.get("estado","todos"))
    except ValueError:
        return jsonify(error="Filtro de estado o taller no válido"),400
    result["clientes"] = [payload_cliente(row) for row in result["clientes"]]
    return jsonify(result)


@app.get("/api/clientes/verificar-duplicado")
@requiere_rol
def verificar_duplicado():
    datos = {key: request.args.get(key, "") for key in ("email","celular","celular_prefijo","curp","rfc","nombre_completo","nombres","apellido_paterno","apellido_materno","fecha_nacimiento")}
    if not datos.get("celular"):
        datos["celular"]=request.args.get("telefono_personal","")
        datos["celular_prefijo"]=request.args.get("telefono_personal_prefijo","52")
    excluir_id = request.args.get("excluir_id", type=int)
    target=g.usuario["taller_id"] if g.usuario["rol"]=="recepcionista" else request.args.get("taller_id") or g.usuario["taller_id"]
    try:target=int(target)
    except (ValueError,TypeError):return jsonify(error="Taller inválido"),400
    if not facade.repository.taller_de_empresa(target,g.usuario["taller_id"]):return jsonify(error="Taller no encontrado"),404
    if datos.get("nombres") and datos.get("apellido_paterno"):
        datos["nombre_completo"]=" ".join(x for x in (datos.get("nombres"),datos.get("apellido_paterno"),datos.get("apellido_materno")) if x)
    duplicado = facade.repository.duplicado(target, datos, excluir_id)
    return jsonify(duplicado=duplicado)


@app.get("/api/clientes/<int:cliente_id>")
@requiere_rol
def consultar_cliente(cliente_id):
    row = facade.obtener(g.usuario, cliente_id)
    return (jsonify(cliente=payload_cliente(row)), 200) if row else (jsonify(error="Cliente no encontrado"), 404)


@app.put("/api/clientes/<int:cliente_id>")
@requiere_rol
def actualizar_cliente(cliente_id):
    datos, foto = _datos_y_foto()
    contexto = foto_ruta = None
    if foto and foto.filename:
        contexto, foto_ruta = _guardar_temporal(foto)
    try:
        if g.usuario["rol"]=="administrador" and datos.get("taller_id"):
            try:target=int(datos["taller_id"])
            except (ValueError,TypeError):return jsonify(error="Taller inválido"),400
            if not facade.repository.taller_de_empresa(target,g.usuario["taller_id"]):return jsonify(error="Taller no encontrado"),404
        actualizado = facade.actualizar(g.usuario, cliente_id, datos, contexto, foto_ruta)
    except Exception:
        if contexto:
            Path(contexto[0]).unlink(missing_ok=True)
        raise
    if not actualizado:
        return jsonify(error="Cliente no encontrado"), 404
    return jsonify(mensaje="Cliente actualizado correctamente"), 200


@app.delete("/api/clientes/<int:cliente_id>")
@requiere_rol(roles={"administrador"})
def eliminar_cliente(cliente_id):
    if not facade.eliminar(g.usuario, cliente_id):
        return jsonify(error="Cliente no encontrado"), 404
    return jsonify(mensaje="Cliente eliminado correctamente"), 200


@app.get("/api/clientes/<int:cliente_id>/foto")
@requiere_rol
def foto_cliente(cliente_id):
    cliente = facade.obtener(g.usuario, cliente_id)
    if not cliente or not cliente.get("foto_ruta"):
        return jsonify(error="Fotografía no encontrada"), 404
    filename = Path(cliente["foto_ruta"]).name
    if not filename or not filename.split(".", 1)[0].isalnum():
        return jsonify(error="Fotografía no encontrada"), 404
    ruta = (PHOTO_DIR / filename).resolve()
    if ruta.parent != PHOTO_DIR.resolve() or not ruta.is_file():
        return jsonify(error="Fotografía no encontrada"), 404
    mimetype = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ruta.suffix.lower().lstrip("."))
    if not mimetype:
        return jsonify(error="Fotografía no encontrada"), 404
    response = send_file(ruta, mimetype=mimetype, conditional=True)
    response.headers["Cache-Control"] = "private, no-store"
    return response




@app.errorhandler(CatalogError)
def error_catalogo(error):
    body={"error":str(error)}
    if error.errors:body["errors"]=error.errors
    return jsonify(body),error.status


@app.errorhandler(StatusError)
def error_estatus(error):
    return jsonify(error=str(error), errors=error.errors), error.status


@app.errorhandler(VehicleError)
def error_vehiculo(error):
    body={"error":str(error),"errors":error.errors}
    if error.code:body["code"]=error.code
    return jsonify(body), error.status


@app.get("/api/estatus/opciones")
@requiere_rol
def opciones_estatus():
    return jsonify(estatus=estatus_repository.options())


@app.route("/api/estatus", methods=["GET", "POST"])
@requiere_rol
def administrar_estatus():
    if request.method == "POST":
        if g.usuario.get("rol") != "administrador": return jsonify(error="Permiso insuficiente"),403
        value, description = estatus_facade.validate(request.get_json(silent=True))
        return jsonify(item=estatus_repository.save(value,description)),201
    try:return jsonify(estatus_repository.list(request.args))
    except ValueError as error:return jsonify(error=str(error)),400


@app.route("/api/estatus/<int:status_id>", methods=["GET", "PUT"])
@requiere_rol
def estatus_por_id(status_id):
    if request.method == "GET":
        row=estatus_repository.get(status_id)
        return (jsonify(item=row),200) if row else (jsonify(error="Estatus no encontrado"),404)
    if g.usuario.get("rol") != "administrador": return jsonify(error="Permiso insuficiente"),403
    value, description=estatus_facade.validate(request.get_json(silent=True));row=estatus_repository.save(value,description,status_id)
    return (jsonify(item=row),200) if row else (jsonify(error="Estatus no encontrado"),404)


@app.patch("/api/estatus/<int:status_id>/desactivar")
@app.patch("/api/estatus/<int:status_id>/reactivar")
@requiere_rol
def estatus_cambiar_estado(status_id):
    if g.usuario.get("rol") != "administrador": return jsonify(error="Permiso insuficiente"),403
    active=request.path.endswith("reactivar")
    row=estatus_repository.activate(status_id,active)
    return (jsonify(item=row),200) if row else (jsonify(error="Estatus no encontrado"),404)


@app.route("/api/vehiculos", methods=["GET", "POST"])
@requiere_rol(roles={"administrador", "recepcionista"})
def administrar_vehiculos():
    if request.method == "GET":
        include_deleted=request.args.get("eliminados") == "1" and g.usuario.get("rol")=="administrador"
        return jsonify(vehiculo_repository.list(g.usuario,request.args,include_deleted))
    body=request.get_json(silent=True) or {}
    data=vehiculo_facade.validate(body)
    result=vehiculo_repository.create(g.usuario,data)
    return jsonify(result),201


@app.get("/api/vehiculos/verificar-placa")
@requiere_rol(roles={"administrador", "recepcionista"})
def verificar_placa_vehiculo():
    plate=__import__('re').sub(r"[-\\s]", "", request.args.get("placa", "")).upper()
    if not __import__('re').fullmatch(r"[A-Z0-9]{5,8}",plate): return jsonify(error="Placa inválida",errors={"placa":"Usa de 5 a 8 letras o números."}),422
    exclude=request.args.get("excluir_id")
    return jsonify(registrada=vehiculo_repository.verify_plate(g.usuario,plate,int(exclude) if exclude and exclude.isdigit() else None))


@app.get("/api/clientes/<int:cliente_id>/vehiculos")
@requiere_rol(roles={"administrador", "recepcionista"})
def vehiculos_de_cliente(cliente_id):
    try: result=vehiculo_repository.by_client(g.usuario,cliente_id,request.args)
    except ValueError as error:return jsonify(error=str(error)),400
    if result is None:return jsonify(error="Cliente no encontrado"),404
    return jsonify(vehiculos=result['items'],page=result['page'],page_size=result['page_size'],total=result['total'],pages=result['total_pages'])


@app.route("/api/vehiculos/<int:vehicle_id>/relaciones", methods=["GET", "POST"])
@requiere_rol(roles={"administrador", "recepcionista"})
def relaciones_vehiculo(vehicle_id):
    if request.method=="GET":
        rows=vehiculo_repository.relaciones(g.usuario,vehicle_id,request.args.get("incluir_historicos")=="1")
        return (jsonify(relaciones=rows),200) if rows is not None else (jsonify(error="Vehículo no encontrado"),404)
    data=vehiculo_facade.validar_relacion(request.get_json(silent=True) or {})
    relation_id=vehiculo_repository.asociar(g.usuario,vehicle_id,data)
    return (jsonify(id=relation_id),201) if relation_id is not None else (jsonify(error="Vehículo no encontrado"),404)


@app.post("/api/vehiculos/<int:vehicle_id>/cambiar-propietario")
@requiere_rol(roles={"administrador", "recepcionista"})
def cambiar_propietario_vehiculo(vehicle_id):
    data=vehiculo_facade.validar_relacion(request.get_json(silent=True) or {},cambio_propietario=True)
    relation_id=vehiculo_repository.cambiar_propietario(g.usuario,vehicle_id,data)
    return (jsonify(id=relation_id),200) if relation_id is not None else (jsonify(error="Vehículo no encontrado"),404)


@app.route("/api/vehiculos/<int:vehicle_id>", methods=["GET", "PUT"])
@requiere_rol(roles={"administrador", "recepcionista"})
def consultar_vehiculo(vehicle_id):
    if request.method == "PUT":
        data=vehiculo_facade.validate(request.get_json(silent=True) or {})
        result=vehiculo_repository.update(g.usuario,vehicle_id,data)
        return (jsonify(result),200) if result else (jsonify(error="Vehículo no encontrado"),404)
    row=vehiculo_repository.get(g.usuario,vehicle_id)
    return (jsonify(vehiculo=row),200) if row else (jsonify(error="Vehículo no encontrado"),404)


@app.patch("/api/vehiculos/<int:vehicle_id>/activar")
@requiere_rol(roles={"administrador", "recepcionista"})
def activar_vehiculo(vehicle_id):
    data=vehiculo_facade.validar_activacion(request.get_json(silent=True) or {})
    result=vehiculo_repository.activate(g.usuario,vehicle_id,data)
    return (jsonify(result),200) if result else (jsonify(error="Vehículo no encontrado"),404)


@app.patch("/api/vehiculos/<int:vehicle_id>/desactivar")
@requiere_rol(roles={"administrador", "recepcionista"})
def desactivar_vehiculo(vehicle_id):
    data=vehiculo_facade.validar_desactivacion(request.get_json(silent=True) or {})
    row=vehiculo_repository.deactivate(g.usuario,vehicle_id,data["motivo"])
    return (jsonify(vehiculo=row),200) if row else (jsonify(error="Vehículo no encontrado"),404)


@app.patch("/api/vehiculos/<int:vehicle_id>/eliminar")
@app.patch("/api/vehiculos/<int:vehicle_id>/restaurar")
@requiere_rol(roles={"administrador", "recepcionista"})
def cambiar_estado_vehiculo(vehicle_id):
    restore=request.path.endswith("restaurar")
    if restore and g.usuario.get("rol")!="administrador":return jsonify(error="Permiso insuficiente"),403
    row=vehiculo_repository.change_deleted(g.usuario,vehicle_id,restore)
    return (jsonify(vehiculo=row),200) if row else (jsonify(error="Vehículo no encontrado"),404)


def _catalogo_result(repository, table, record_id, active):
    row=repository.change_status(table,record_id,active)
    if not row:return jsonify(error="Registro no encontrado"),404
    return jsonify(item=row)


@app.route("/api/marcas/opciones", methods=["GET"])
@requiere_rol
def marcas_opciones():
    q=request.args.get("q","").strip()
    return jsonify(marcas=vehiculo_catalogo_repository.options(q))


@app.route("/api/marcas/<int:brand_id>/modelos/opciones", methods=["GET"])
@requiere_rol
def modelos_opciones(brand_id):
    q=request.args.get("q","").strip()
    return jsonify(modelos=vehiculo_catalogo_repository.model_options(brand_id,q))


@app.route("/api/catalogo-vehiculos/buscar", methods=["GET"])
@requiere_rol
def buscar_catalogo_vehiculos():
    q=request.args.get("q","").strip()
    if not q:return jsonify(resultados=[])
    if len(q)>80:return jsonify(error="La búsqueda admite hasta 80 caracteres"),422
    brand_id=request.args.get("marca_id")
    if brand_id:
        try:brand_id=int(brand_id)
        except ValueError:return jsonify(error="Marca inválida",errors={"marca_id":"Selecciona una marca válida."}),422
    return jsonify(resultados=vehiculo_catalogo_repository.search(q,brand_id))


@app.route("/api/catalogo-vehiculos/pendiente", methods=["POST"])
@requiere_rol
def crear_catalogo_pendiente():
    result=vehiculo_catalogo_facade.resolve_pending(request.get_json(silent=True))
    return jsonify(item=result),201


@app.route("/api/marcas", methods=["GET","POST"])
@requiere_rol(roles={"administrador"})
def administrar_marcas():
    if request.method=="POST":
        name=vehiculo_catalogo_facade.marca(request.get_json(silent=True))
        return jsonify(item=vehiculo_catalogo_repository.create("marcas",name)),201
    page,page_size,sort,direction=vehiculo_catalogo_facade.pagination(request.args)
    return jsonify(vehiculo_catalogo_repository.list("marcas",request.args.get("q","").strip(),page,page_size,sort,direction))


@app.route("/api/marcas/<int:brand_id>", methods=["GET","PUT"])
@requiere_rol(roles={"administrador"})
def administrar_marca(brand_id):
    if request.method=="GET":
        row=vehiculo_catalogo_repository.get("marcas",brand_id)
        return (jsonify(item=row),200) if row else (jsonify(error="Marca no encontrada"),404)
    name=vehiculo_catalogo_facade.marca(request.get_json(silent=True))
    row=vehiculo_catalogo_repository.update("marcas",brand_id,name)
    return (jsonify(item=row),200) if row else (jsonify(error="Marca no encontrada"),404)


@app.route("/api/marcas/<int:brand_id>/desactivar", methods=["PATCH"])
@requiere_rol(roles={"administrador"})
def desactivar_marca(brand_id):return _catalogo_result(vehiculo_catalogo_repository,"marcas",brand_id,False)


@app.route("/api/marcas/<int:brand_id>/reactivar", methods=["PATCH"])
@requiere_rol(roles={"administrador"})
def reactivar_marca(brand_id):return _catalogo_result(vehiculo_catalogo_repository,"marcas",brand_id,True)


@app.route("/api/modelos", methods=["GET","POST"])
@requiere_rol(roles={"administrador"})
def administrar_modelos():
    if request.method=="POST":
        brand_id,name=vehiculo_catalogo_facade.modelo(request.get_json(silent=True))
        return jsonify(item=vehiculo_catalogo_repository.create("modelos",name,brand_id)),201
    page,page_size,sort,direction=vehiculo_catalogo_facade.pagination(request.args)
    brand_id=request.args.get("marca_id")
    if brand_id:
        try:brand_id=int(brand_id)
        except ValueError:raise CatalogError("Selecciona una marca válida.",errors={"marca_id":"Selecciona una marca válida."})
    return jsonify(vehiculo_catalogo_repository.list("modelos",request.args.get("q","").strip(),page,page_size,sort,direction,brand_id))


@app.route("/api/modelos/<int:model_id>", methods=["GET","PUT"])
@requiere_rol(roles={"administrador"})
def administrar_modelo(model_id):
    if request.method=="GET":
        row=vehiculo_catalogo_repository.get("modelos",model_id)
        return (jsonify(item=row),200) if row else (jsonify(error="Modelo no encontrado"),404)
    brand_id,name=vehiculo_catalogo_facade.modelo(request.get_json(silent=True))
    row=vehiculo_catalogo_repository.update("modelos",model_id,name,brand_id)
    return (jsonify(item=row),200) if row else (jsonify(error="Modelo no encontrado"),404)


@app.route("/api/modelos/<int:model_id>/desactivar", methods=["PATCH"])
@requiere_rol(roles={"administrador"})
def desactivar_modelo(model_id):return _catalogo_result(vehiculo_catalogo_repository,"modelos",model_id,False)


@app.route("/api/modelos/<int:model_id>/reactivar", methods=["PATCH"])
@requiere_rol(roles={"administrador"})
def reactivar_modelo(model_id):return _catalogo_result(vehiculo_catalogo_repository,"modelos",model_id,True)


# Administración de personal: todas las consultas filtran por la empresa de sesión.
def _empleado_body():
    foto=None
    if request.is_json:body=request.get_json(silent=True)
    elif request.mimetype=="multipart/form-data":
        try:body=json.loads(request.form.get("empleado",""))
        except json.JSONDecodeError:raise ClienteError("Formato inválido",errors={"_global":"El formulario no contiene JSON válido."})
        foto=request.files.get("foto")
    else:body=None
    if not isinstance(body,dict):raise ClienteError("Se requiere JSON",errors={"_global":"Envía los datos del empleado."})
    return body,foto

def _employee_payload(row):
    safe={k:(v.isoformat() if isinstance(v,(date,datetime)) else v) for k,v in row.items() if k!="password_hash"}
    return safe

def _validate_employee_address(data,errors):
    if not any(data.get(k) for k in ("estado","municipio","colonia","codigo_postal")) or data.get("colonia_manual"):
        return
    if not ubicacion_facade.direccion_valida(data.get("estado"),data.get("municipio"),data.get("colonia"),data.get("codigo_postal"),False):
        errors["codigo_postal"]="La dirección no coincide con el catálogo SEPOMEX."

@app.get("/api/empleados")
@requiere_rol(roles={"administrador"})
def listar_empleados():
    try:page=parse_page(request.args,empleado_repository.SORTS,"nombre")
    except ValueError as error:return jsonify(error=str(error)),400
    try:
        result=empleado_repository.listar(g.usuario,{k:request.args.get(k,"") for k in ("q","taller_id","estado","rol","puesto")},page.page,page.page_size,page.sort,page.direction)
    except (ValueError,TypeError):return jsonify(error="Filtro inválido"),400
    result["empleados"]=[_employee_payload(row) for row in result["empleados"]]
    result["page_size"]=page.page_size;result["total_pages"]=result.get("pages",0);result["items"]=result["empleados"]
    return jsonify(result)

@app.get("/api/empleados/talleres")
@requiere_rol(roles={"administrador"})
def talleres_empleados():return jsonify(talleres=empleado_repository.talleres(g.usuario))

@app.get("/api/empleados/verificar-duplicado")
@requiere_rol(roles={"administrador"})
def verificar_duplicado_empleado():
    field=request.args.get("campo","");value=request.args.get("valor","").strip()
    if field not in {"curp","rfc","email","telefono_personal"} or not value:return jsonify(error="Consulta inválida"),400
    value=value.upper() if field in {"curp","rfc"} else value.lower() if field=="email" else re.sub(r"\D","",value)
    return jsonify(duplicado=empleado_repository.duplicado(g.usuario,field,value,request.args.get("excluir_id",type=int)))

@app.post("/api/empleados")
@requiere_rol(roles={"administrador"})
def crear_empleado():
    raw,foto=_empleado_body();data,errors=empleado_facade.validar(raw,True)
    _validate_employee_address(data,errors)
    password=raw.get("password","");confirm=raw.get("password_confirm","")
    if not isinstance(password,str) or len(password)<12:errors["password"]="La contraseña debe tener al menos 12 caracteres."
    elif password!=confirm:errors["password_confirm"]="Las contraseñas no coinciden."
    if errors:return jsonify(error="Revisa los campos",errors=errors),422
    if foto and foto.filename:
        ext=_validar_foto(foto);EMPLOYEE_PHOTO_DIR.mkdir(parents=True,exist_ok=True);filename=uuid.uuid4().hex+"."+ext;dest=EMPLOYEE_PHOTO_DIR/filename;foto.save(dest);data["foto_ruta"]="storage/empleados/"+filename
    else:dest=None
    try:eid=empleado_repository.crear(g.usuario,data,bcrypt.hashpw(password.encode("utf-8"),bcrypt.gensalt(rounds=12)).decode("ascii"))
    except Exception:
        if dest:dest.unlink(missing_ok=True)
        raise
    if eid is None:
        if dest:dest.unlink(missing_ok=True)
        return jsonify(error="Taller no encontrado en la empresa actual"),404
    return jsonify(id=eid,mensaje="Empleado registrado"),201

@app.get("/api/empleados/<int:employee_id>")
@requiere_rol(roles={"administrador"})
def consultar_empleado(employee_id):
    row=empleado_repository.obtener(g.usuario,employee_id)
    return (jsonify(empleado=_employee_payload(row)),200) if row else (jsonify(error="Empleado no encontrado"),404)

@app.put("/api/empleados/<int:employee_id>")
@requiere_rol(roles={"administrador"})
def actualizar_empleado(employee_id):
    raw,foto=_empleado_body();data,errors=empleado_facade.validar(raw,False)
    _validate_employee_address(data,errors)
    password=raw.get("password","")
    if password and (not isinstance(password,str) or len(password)<12):errors["password"]="La contraseña debe tener al menos 12 caracteres."
    if password and password!=raw.get("password_confirm",""):errors["password_confirm"]="Las contraseñas no coinciden."
    if errors:return jsonify(error="Revisa los campos",errors=errors),422
    new_file=None
    if foto and foto.filename:
        ext=_validar_foto(foto);EMPLOYEE_PHOTO_DIR.mkdir(parents=True,exist_ok=True);filename=uuid.uuid4().hex+"."+ext;new_file=EMPLOYEE_PHOTO_DIR/filename;foto.save(new_file);data["foto_ruta"]="storage/empleados/"+filename
    hashed=bcrypt.hashpw(password.encode("utf-8"),bcrypt.gensalt(rounds=12)).decode("ascii") if password else None
    try:result=empleado_repository.actualizar(g.usuario,employee_id,data,hashed)
    except Exception:
        if new_file:new_file.unlink(missing_ok=True)
        raise
    if new_file and result is not True:new_file.unlink(missing_ok=True)
    if result is False:return jsonify(error="Empleado no encontrado"),404
    if result=="inactive":return jsonify(error="Reactive al empleado antes de editar"),409
    if result=="self":return jsonify(error="No puede quitarse su propio rol de administrador"),422
    if result=="last_admin":return jsonify(error="Debe permanecer al menos un administrador activo",errors={"rol":"No puede quitarse el rol al último administrador activo de la empresa."}),422
    if result=="invalid":return jsonify(error="Rol inválido",errors={"rol":"Selecciona un rol permitido."}),422
    return jsonify(mensaje="Empleado actualizado")

@app.post("/api/empleados/<int:employee_id>/foto")
@requiere_rol(roles={"administrador"})
def foto_empleado(employee_id):
    foto=request.files.get("foto");ext=_validar_foto(foto)
    if not empleado_repository.obtener(g.usuario,employee_id):return jsonify(error="Empleado no encontrado"),404
    EMPLOYEE_PHOTO_DIR.mkdir(parents=True,exist_ok=True);filename=uuid.uuid4().hex+"."+ext;dest=EMPLOYEE_PHOTO_DIR/filename;foto.save(dest)
    raw=empleado_repository.obtener(g.usuario,employee_id);data={k:raw.get(k) for k in ()}
    # La ruta exclusiva evita aceptar nombres de archivo del cliente.
    c=__import__('db').connect()
    try:
        with c.cursor() as x:x.execute("UPDATE empleados SET foto_ruta=%s WHERE id=%s",("storage/empleados/"+filename,employee_id))
        c.commit()
    except Exception:c.rollback();dest.unlink(missing_ok=True);raise
    finally:c.close()
    return jsonify(mensaje="Fotografía guardada"),201

@app.patch("/api/empleados/<int:employee_id>/baja")
@requiere_rol(roles={"administrador"})
def baja_empleado(employee_id):
    result=empleado_repository.estado(g.usuario,employee_id,False,(request.get_json(silent=True) or {}).get("motivo"))
    if result is None:return jsonify(error="Empleado no encontrado"),404
    if result in ("self","last_admin"):return jsonify(error="No se puede dar de baja al último administrador activo ni a sí mismo",errors={"activo":"Debe permanecer al menos un administrador activo y no puede darse de baja a sí mismo."}),422
    return jsonify(mensaje="Empleado dado de baja")

@app.patch("/api/empleados/<int:employee_id>/reactivar")
@requiere_rol(roles={"administrador"})
def reactivar_empleado(employee_id):
    result=empleado_repository.estado(g.usuario,employee_id,True)
    return (jsonify(error="Empleado no encontrado"),404) if result is None else (jsonify(mensaje="Empleado reactivado"),200)

@app.get("/api/empleados/<int:employee_id>/foto")
@requiere_rol(roles={"administrador"})
def mostrar_foto_empleado(employee_id):
    row=empleado_repository.obtener(g.usuario,employee_id)
    if not row or not row.get("foto_ruta"):return jsonify(error="Fotografía no encontrada"),404
    path=(EMPLOYEE_PHOTO_DIR/Path(row["foto_ruta"]).name).resolve()
    if path.parent!=EMPLOYEE_PHOTO_DIR.resolve() or not path.is_file():return jsonify(error="Fotografía no encontrada"),404
    mime={"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","webp":"image/webp"}.get(path.suffix.lower().lstrip('.'))
    if not mime:return jsonify(error="Fotografía no encontrada"),404
    response=send_file(path,mimetype=mime);response.headers["Cache-Control"]="private, no-store";return response


@app.post("/api/clientes/<int:cliente_id>/foto")
@requiere_rol
def subir_foto(cliente_id):
    foto = request.files.get("foto")
    ext = _validar_foto(foto)
    # Comprueba que el cliente pertenezca al taller activo antes de escribir.
    if not facade.obtener(g.usuario, cliente_id):
        return jsonify(error="Cliente no encontrado"), 404
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    nombre = f"{uuid.uuid4().hex}.{ext}"
    destino = PHOTO_DIR / nombre
    foto.save(destino)
    ruta_relativa = f"storage/clientes/{nombre}"
    try:
        if not facade.repository.guardar_foto_y_actualizar(g.usuario, cliente_id, ruta_relativa):
            destino.unlink(missing_ok=True)
            return jsonify(error="Cliente no encontrado"), 404
    except Exception:
        destino.unlink(missing_ok=True)
        raise
    return jsonify(foto_ruta=ruta_relativa), 201


if not app.secret_key:
    raise RuntimeError("Configura APP_SECRET_KEY en el entorno antes de iniciar la API")

if __name__ == "__main__":
    app.run(host=os.environ.get("APP_HOST", "127.0.0.1"), port=int(os.environ.get("APP_PORT", "5000")), debug=False)
