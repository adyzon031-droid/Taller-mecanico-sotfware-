"""API REST JSON para Fase 02. La sesión debe ser establecida por el login."""
import os
import uuid
import json
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, request, session
from dotenv import load_dotenv
from pymysql.err import IntegrityError

from auth_facade import AuthFacade
from auth_repository import AuthRepository
from cliente_facade import ClienteError, ClienteFacade
from cliente_repository import ClienteRepository

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "")
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.config["PERMANENT_SESSION_LIFETIME"] = 28800
facade = ClienteFacade(ClienteRepository())
auth_facade = AuthFacade(AuthRepository())
ROLES = {"admin", "administrador", "secretaria", "recepcionista"}
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
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,OPTIONS"
        response.headers["Vary"] = "Origin"
    return response


@app.route("/api/clientes", methods=["OPTIONS"])
@app.route("/api/clientes/<path:_path>", methods=["OPTIONS"])
@app.route("/api/auth/<path:_path>", methods=["OPTIONS"])
def preflight(_path=""):
    return "", 204


def requiere_rol(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = g.usuario
        if not user:
            return jsonify(error="Sesión requerida"), 401
        if str(user.get("rol", "")).lower() not in ROLES:
            return jsonify(error="Permiso insuficiente"), 403
        if not user.get("usuario_id") or not user.get("taller_id"):
            return jsonify(error="La sesión no contiene usuario y taller activos"), 403
        return view(*args, **kwargs)
    return wrapped


def payload_cliente(row):
    for key, value in row.items():
        if isinstance(value, (date, datetime)):
            row[key] = value.isoformat()
    return row


@app.errorhandler(ClienteError)
def error_cliente(error):
    return jsonify(error=str(error)), error.status


@app.errorhandler(IntegrityError)
def error_integridad(_error):
    return jsonify(error="Registro duplicado o restricción de integridad"), 409


@app.errorhandler(413)
def foto_grande(_error):
    return jsonify(error="La fotografía supera el máximo de 15 MB"), 422


def _validar_foto(foto):
    if not foto or not foto.filename or "." not in foto.filename:
        raise ClienteError("Selecciona una fotografía")
    ext = foto.filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED:
        raise ClienteError("Formato no permitido; usa JPG, JPEG, PNG o WEBP")
    header = foto.stream.read(12)
    foto.stream.seek(0)
    signatures = {
        "jpg": header.startswith(b"\xff\xd8\xff"),
        "jpeg": header.startswith(b"\xff\xd8\xff"),
        "png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        "webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
    }
    if not signatures.get(ext, False):
        raise ClienteError("El contenido no coincide con el formato de la fotografía")
    return ext


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
    foto = None
    if request.is_json:
        datos = request.get_json(silent=True)
    elif request.mimetype == "multipart/form-data":
        try:
            datos = json.loads(request.form.get("cliente", ""))
        except json.JSONDecodeError:
            return jsonify(error="El campo cliente debe contener JSON válido"), 422
        foto = request.files.get("foto")
    else:
        return jsonify(error="Se requiere JSON o multipart/form-data"), 422
    if not isinstance(datos, dict):
        return jsonify(error="Se requiere un objeto JSON cliente"), 422
    contexto = None
    foto_ruta = None
    try:
        if foto and foto.filename:
            ext = _validar_foto(foto)
            PHOTO_DIR.mkdir(parents=True, exist_ok=True)
            nombre = f"{uuid.uuid4().hex}.{ext}"
            temporal, destino = PHOTO_DIR / f".{nombre}.upload", PHOTO_DIR / nombre
            foto.save(temporal)
            contexto, foto_ruta = (temporal, destino), f"storage/clientes/{nombre}"
        cliente_id = facade.crear(datos, g.usuario, contexto, foto_ruta)
    except Exception:
        if contexto:
            contexto[0].unlink(missing_ok=True)
        raise
    return jsonify(id=cliente_id, mensaje="Cliente registrado correctamente"), 201


@app.get("/api/clientes")
@requiere_rol
def listar_clientes():
    filtros = {key: request.args.get(key, "") for key in ("nombre_completo", "email", "telefono_personal")}
    return jsonify(clientes=[payload_cliente(row) for row in facade.listar(g.usuario, filtros)])


@app.get("/api/clientes/verificar-duplicado")
@requiere_rol
def verificar_duplicado():
    datos = request.args.to_dict()
    datos.setdefault("fecha_nacimiento", "1900-01-01")
    datos.setdefault("nombre_completo", "")
    datos.setdefault("telefono_personal", "")
    datos.setdefault("email", "")
    from cliente_repository import ClienteRepository
    duplicado = ClienteRepository().duplicado(g.usuario["taller_id"], datos)
    return jsonify(duplicado=duplicado)


@app.get("/api/clientes/<int:cliente_id>")
@requiere_rol
def consultar_cliente(cliente_id):
    row = facade.obtener(g.usuario, cliente_id)
    return (jsonify(cliente=payload_cliente(row)), 200) if row else (jsonify(error="Cliente no encontrado"), 404)


@app.put("/api/clientes/<int:cliente_id>")
@requiere_rol
def actualizar_cliente(cliente_id):
    if not request.is_json:
        return jsonify(error="Se requiere JSON"), 422
    if not facade.actualizar(g.usuario, cliente_id, request.get_json()):
        return jsonify(error="Cliente no encontrado"), 404
    return jsonify(mensaje="Cliente actualizado correctamente")


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
