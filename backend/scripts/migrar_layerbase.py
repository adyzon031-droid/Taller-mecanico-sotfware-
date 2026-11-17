
from pathlib import Path
from dotenv import dotenv_values
from urllib.parse import urlparse, unquote
import argparse
import pymysql


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "backend" / "migrations"
CREDENTIALS = (
    Path.home() / "Descargas" /
    "taller_mecanico_test-credentials.env"
)


def obtener_migraciones():
    archivos = sorted(MIGRATIONS.glob("*.sql"))

    if len(archivos) != 14:
        raise RuntimeError(
            f"Se esperaban 14 migraciones; encontradas: {len(archivos)}"
        )

    return archivos


def separar_sentencias(archivo):
    delimitador = ";"
    buffer = []

    for linea in archivo.read_text(encoding="utf-8").splitlines():
        texto = linea.strip()

        if not texto:
            continue

        if texto.upper().startswith("DELIMITER "):
            if buffer:
                raise ValueError(
                    f"Buffer pendiente al cambiar delimitador: {archivo.name}"
                )

            delimitador = texto.split(None, 1)[1]
            continue

        if texto.startswith("--") and not buffer:
            continue

        buffer.append(linea)

        if texto.endswith(delimitador):
            sentencia = "\n".join(buffer).rstrip()
            sentencia = sentencia[:-len(delimitador)].strip()

            if sentencia:
                yield sentencia

            buffer = []

    if buffer:
        raise ValueError(
            f"Sentencia incompleta en {archivo.name}: "
            "revisar delimitadores."
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ejecutar las migraciones en la base remota."
    )
    args = parser.parse_args()

    migraciones = obtener_migraciones()

    print("Base objetivo: taller_mecanico_test")
    print("Modo:", "EJECUCIÓN" if args.apply else "PRUEBA")
    print()

    if not args.apply:
        for archivo in migraciones:
            sentencias = list(separar_sentencias(archivo))
            print(f"{archivo.name}: {len(sentencias)} sentencias")

        print()
        print("Prueba terminada. No se modificó la base de datos.")
        print("Revisa los resultados antes de ejecutar con --apply.")
        return

    configuracion = dotenv_values(CREDENTIALS)
    url = configuracion.get("DATABASE_URL")

    if not url:
        raise RuntimeError("No se encontró DATABASE_URL.")

    datos = urlparse(url)
    base = datos.path.lstrip("/")

    if base != "taller_mecanico_test":
        raise RuntimeError(
            "La URL no corresponde a taller_mecanico_test."
        )

    conexion = pymysql.connect(
        host=datos.hostname,
        port=datos.port,
        user=unquote(datos.username or ""),
        password=unquote(datos.password or ""),
        database=base,
        ssl={},
        connect_timeout=30,
        read_timeout=60,
        write_timeout=60,
        autocommit=True
    )

    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
            """)

            for archivo in migraciones:
                nombre = archivo.name

                cursor.execute(
                    "SELECT version FROM schema_migrations "
                    "WHERE version = %s",
                    (nombre,)
                )

                if cursor.fetchone():
                    print(f"YA APLICADA: {nombre}")
                    continue

                print(f"Ejecutando: {nombre}")

                for sentencia in separar_sentencias(archivo):
                    cursor.execute(sentencia)

                cursor.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (nombre,)
                )

                print(f"COMPLETADA: {nombre}")

        print("\nMigraciones finalizadas.")

    except Exception:
        print(
            "\nERROR: se detuvo la ejecución. "
            "Revisa qué migraciones quedaron registradas."
        )
        raise

    finally:
        conexion.close()


if __name__ == "__main__":
    main()
