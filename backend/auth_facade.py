"""Autenticación y validación de credenciales de aplicación."""
import bcrypt


class AuthFacade:
    def __init__(self, repository):
        self.repository = repository

    def autenticar(self, correo, password):
        if not isinstance(correo, str) or not isinstance(password, str) or not correo or not password:
            return None
        usuario = self.repository.buscar_por_correo(correo)
        if not usuario or not usuario["activo"]:
            return None
        try:
            valid = bcrypt.checkpw(password.encode("utf-8"), usuario["password_hash"].encode("ascii"))
        except (ValueError, TypeError):
            return None
        if not valid:
            return None
        return {"usuario_id": usuario["id"], "nombre": usuario["nombre"], "rol": usuario["rol"], "taller_id": usuario["taller_id"], "empresa_id": usuario["empresa_id"]}
