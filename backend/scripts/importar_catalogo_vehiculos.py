"""Importa de forma idempotente el catálogo versionado de marcas y modelos."""
import csv
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import connect

CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "catalogo_vehiculos.csv"
ACRONYMS = {"BMW", "GMC", "RAM", "SEAT"}


def title_name(value):
    words = re.sub(r"\s+", " ", value).strip().split(" ")
    normalized = []
    for word in words:
        parts = word.split("-")
        fixed = []
        for part in parts:
            if part.upper() in ACRONYMS:
                fixed.append(part.upper())
            else:
                fixed.append(part[:1].upper() + part[1:].lower())
        normalized.append("-".join(fixed))
    return " ".join(normalized)


def main():
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as source:
        rows = [(title_name(row["marca"]), title_name(row["modelo"])) for row in csv.DictReader(source)]
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM estatus WHERE valor=%s", ("activo",))
            active_id = cursor.fetchone()["id"]
            for brand in sorted({name for name, _ in rows}):
                cursor.execute(
                    "INSERT INTO marcas (nombre,estatus_id) VALUES (%s,%s) ON DUPLICATE KEY UPDATE nombre=VALUES(nombre)",
                    (brand, active_id),
                )
            cursor.execute("SELECT id,nombre FROM marcas")
            brand_ids = {row["nombre"]: row["id"] for row in cursor.fetchall()}
            for brand, model in rows:
                cursor.execute(
                    "INSERT INTO modelos (marca_id,nombre,estatus_id) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE nombre=VALUES(nombre)",
                    (brand_ids[brand], model, active_id),
                )
        connection.commit()
        print(f"Marcas: {len({brand for brand, _ in rows})}; modelos: {len(rows)}")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
