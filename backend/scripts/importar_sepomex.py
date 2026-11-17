"""Carga completa y transaccional del catálogo SEPOMEX local."""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import connect

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "data" / "sepomex" / "CPdescarga.txt"
REQUIRED = ("d_codigo", "d_asenta", "d_tipo_asenta", "D_mnpio", "d_estado")


def norm(value):
    return re.sub(r"\s+", " ", value or "").strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    path = parser.parse_args().file
    if not path.is_file():
        raise SystemExit("No existe data/sepomex/CPdescarga.txt; coloca ahí el archivo oficial SEPOMEX en codificación Latin-1.")

    with path.open("r", encoding="latin-1", newline="") as source:
        reader = csv.reader(source, delimiter="|")
        next(reader, None)  # Leyenda
        headers = [norm(value).lstrip("\ufeff") for value in next(reader, [])]
        missing = [name for name in REQUIRED if name not in headers]
        if missing:
            raise SystemExit("El encabezado SEPOMEX no contiene las columnas requeridas.")
        indexes = [headers.index(name) for name in REQUIRED]
        rows = []
        unique_rows = set()
        cps, states, municipalities = set(), set(), set()
        for raw in reader:
            if not raw or max(indexes) >= len(raw):
                continue
            cp_raw, colonia, tipo, municipio, estado = (norm(raw[index]) for index in indexes)
            if not cp_raw.isdigit() or not colonia or not tipo or not municipio or not estado:
                continue
            cp = cp_raw.zfill(5)
            if len(cp) != 5:
                continue
            row = (cp, estado, municipio, colonia, tipo)
            if row in unique_rows:
                continue
            unique_rows.add(row)
            rows.append(row)
            cps.add(cp)
            states.add(estado)
            municipalities.add((estado, municipio))

    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM codigos_postales")
            batch_size = 2000
            sql = ("INSERT INTO codigos_postales (cp,estado,municipio,colonia,tipo_asentamiento) "
                   "VALUES (%s,%s,%s,%s,%s)")
            for start in range(0, len(rows), batch_size):
                cursor.executemany(sql.replace("INSERT INTO", "INSERT IGNORE INTO"), rows[start:start + batch_size])
            cursor.execute("SELECT COUNT(*) AS rows_loaded, COUNT(DISTINCT cp) AS cps, COUNT(DISTINCT estado) AS states FROM codigos_postales")
            totals = cursor.fetchone()
            cursor.execute("SELECT COUNT(*) AS municipalities FROM (SELECT DISTINCT estado,municipio FROM codigos_postales) AS m")
            totals["municipalities"] = cursor.fetchone()["municipalities"]
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print(f"Filas cargadas: {totals['rows_loaded']}")
    print(f"CP distintos: {totals['cps']}")
    print(f"Estados: {totals['states']}")
    print(f"Municipios: {totals['municipalities']}")


if __name__ == "__main__":
    main()
