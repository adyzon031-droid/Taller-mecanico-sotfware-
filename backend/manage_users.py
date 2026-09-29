"""Crea cuentas de aplicación de forma interactiva, sin guardar claves en texto claro."""
import getpass
import re
from pathlib import Path
import bcrypt
from dotenv import load_dotenv

from auth_repository import AuthRepository

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def main():
    print("Alta local de usuario del taller")
    nombre = input("Nombre: ").strip()
    correo = input("Correo: ").strip().lower()
    rol = input("Rol (administrador/recepcionista): ").strip().lower()
    taller_id = input("ID del taller: ").strip()
    if not nombre or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", correo):
        raise SystemExit("Nombre o correo inválido")
    if rol not in {"administrador", "recepcionista"}:
        raise SystemExit("Rol no permitido")
    if not taller_id.isdigit():
        raise SystemExit("El taller debe ser un ID numérico")
    password = getpass.getpass("Contraseña nueva (mínimo 12 caracteres): ")
    confirm = getpass.getpass("Confirma la contraseña: ")
    if len(password) < 12 or password != confirm:
        raise SystemExit("La contraseña no cumple longitud o confirmación")
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")
    user_id = AuthRepository().crear_usuario(nombre, correo, hashed, rol, int(taller_id))
    print(f"Cuenta creada: id={user_id}, correo={correo}, rol={rol}, taller_id={taller_id}")
    print("La contraseña no se almacena en texto claro ni se muestra de nuevo.")


if __name__ == "__main__":
    main()
