"""API REST JSON para Fase 02. La sesión debe ser establecida por el login."""
import os
import uuid
import json
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, request, send_file, session
from dotenv import load_dotenv
from pymysql.err import IntegrityError

from auth_facade import AuthFacade
from auth_repository import AuthRepository
from cliente_facade import ClienteError, ClienteFacade
from cliente_repository import ClienteRepository

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "")
# Reserva margen para el multipart; _validar_foto limita el archivo en 15 MiB.
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.config["PERMANENT_SESSION_LIFETIME"] = 28800
facade = ClienteFacade(ClienteRepository())
auth_facade = AuthFacade(AuthRepository())
ROLES = {"administrador", "recepcionista"}
PHOTO_DIR = Path(__file__).resolve().parent.parent / "storage" / "clientes"
ALLOWED = {"jpg", "jpeg", "png", "webp"}


@app.before_request
def cargar_sesion():
    """Obtiene identidad y taller de la sesión firmada establecida por el login."""
    g.usuario = session.get("usuario")


@app.after_request
def cors(response):
    origin = os.environ.get("CORS_ORIGIN", "")
    if origin and request.headers.get("Origin") == origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        response.headers["Vary"] = "Origin"
    return response


@app.route("/api/clientes", methods=["OPTIONS"])
@app.route("/api/clientes/<path:_path>", methods=["OPTIONS"])
@app.route("/api/auth/<path:_path>", methods=["OPTIONS"])
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
            return fn(*args, **kwargs)
        return wrapped
    return decorate(view) if view else decorate


def payload_cliente(row):
    for key, value in row.items():
        if isinstance(value, (date, datetime)):
            row[key] = value.isoformat()
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
    return jsonify(usuario=usuario), 200


@app.post("/api/auth/logout")
def cerrar_sesion():
    session.clear()
    return jsonify(mensaje="Sesión cerrada")


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
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(10, max(1, int(request.args.get("per_page", 10))))
    except ValueError:
        raise ClienteError("La página debe ser un número entero.", errors={"page": "Usa un número entero."})
    result = facade.listar(g.usuario, {"q": request.args.get("q", "")}, page, per_page)
    result["clientes"] = [payload_cliente(row) for row in result["clientes"]]
    return jsonify(result)


@app.get("/api/clientes/verificar-duplicado")
@requiere_rol
def verificar_duplicado():
    datos = {key: request.args.get(key, "") for key in ("email", "telefono_personal", "nombre_completo", "fecha_nacimiento")}
    excluir_id = request.args.get("excluir_id", type=int)
    duplicado = ClienteRepository().duplicado(g.usuario["taller_id"], datos, excluir_id)
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
        from cliente_repository import ClienteRepository
        if not ClienteRepository().guardar_foto_y_actualizar(g.usuario["taller_id"], cliente_id, ruta_relativa):
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
