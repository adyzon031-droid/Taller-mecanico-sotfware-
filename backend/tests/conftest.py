import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Los tests de API usan clientes/repositorios simulados; las verificaciones con
# MariaDB real se ejecutan aparte con el cliente de pruebas y la BD local.
from app import app
app.config["TESTING"] = True
