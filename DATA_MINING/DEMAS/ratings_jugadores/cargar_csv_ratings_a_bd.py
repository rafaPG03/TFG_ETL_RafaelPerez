import argparse
import os
from pathlib import Path

import psycopg2


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PERFIL_CSV = BASE_DIR / "perfil_estadistico_jugadores.csv"
DEFAULT_SIMILARES_CSV = BASE_DIR / "jugadores_similares_top5.csv"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Carga CSVs de ratings_jugadores en PostgreSQL"
    )
    parser.add_argument("--db-host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("PGPORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("PGDATABASE", "TFG_Prueba"))
    parser.add_argument("--db-user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("PGPASSWORD", ""))

    parser.add_argument("--perfil-csv", default=str(DEFAULT_PERFIL_CSV))
    parser.add_argument("--similares-csv", default=str(DEFAULT_SIMILARES_CSV))

    parser.add_argument(
        "--perfil-table",
        default="public.dm_perfil_estadistico_jugadores",
        help="Tabla destino para perfil_estadistico_jugadores.csv",
    )
    parser.add_argument(
        "--similares-table",
        default="public.dm_jugadores_similares_top5",
        help="Tabla destino para jugadores_similares_top5.csv",
    )
    parser.add_argument(
        "--skip-perfil",
        action="store_true",
        help="No cargar perfil_estadistico_jugadores.csv",
    )
    parser.add_argument(
        "--skip-similares",
        action="store_true",
        help="No cargar jugadores_similares_top5.csv",
    )
    return parser.parse_args()


def crear_tabla_perfil(cur, perfil_table: str):
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {perfil_table} (
            id_jugador integer PRIMARY KEY,
            nombre character varying(100),
            ataque numeric(6,2),
            creacion numeric(6,2),
            defensa numeric(6,2),
            porteros numeric(6,2),
            duelos numeric(6,2),
            regates numeric(6,2)
        );
        """
    )


def crear_tabla_similares(cur, similares_table: str):
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {similares_table} (
            id_jugador integer PRIMARY KEY,
            nombre character varying(100),
            cluster integer,
            id_similar1 integer,
            nombre_similar1 character varying(100),
            similitud1 numeric(8,4),
            id_similar2 integer,
            nombre_similar2 character varying(100),
            similitud2 numeric(8,4),
            id_similar3 integer,
            nombre_similar3 character varying(100),
            similitud3 numeric(8,4),
            id_similar4 integer,
            nombre_similar4 character varying(100),
            similitud4 numeric(8,4),
            id_similar5 integer,
            nombre_similar5 character varying(100),
            similitud5 numeric(8,4)
        );
        """
    )


def cargar_perfil(cur, perfil_csv: Path, perfil_table: str):
    cur.execute(
        """
        CREATE TEMP TABLE tmp_perfil (
            id_jugador integer,
            nombre character varying(100),
            ataque numeric(6,2),
            creacion numeric(6,2),
            defensa numeric(6,2),
            porteros numeric(6,2),
            duelos numeric(6,2),
            regates numeric(6,2)
        ) ON COMMIT DROP;
        """
    )

    with perfil_csv.open("r", encoding="utf-8-sig") as f:
        cur.copy_expert(
            """
            COPY tmp_perfil (id_jugador, nombre, ataque, creacion, defensa, porteros, duelos, regates)
            FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ';', NULL '');
            """,
            f,
        )

    cur.execute(
        f"""
        INSERT INTO {perfil_table} (
            id_jugador, nombre, ataque, creacion, defensa, porteros, duelos, regates
        )
        SELECT
            t.id_jugador, t.nombre, t.ataque, t.creacion, t.defensa, t.porteros, t.duelos, t.regates
        FROM tmp_perfil t
        ON CONFLICT (id_jugador)
        DO UPDATE SET
            nombre = EXCLUDED.nombre,
            ataque = EXCLUDED.ataque,
            creacion = EXCLUDED.creacion,
            defensa = EXCLUDED.defensa,
            porteros = EXCLUDED.porteros,
            duelos = EXCLUDED.duelos,
            regates = EXCLUDED.regates;
        """
    )


def cargar_similares(cur, similares_csv: Path, similares_table: str):
    cur.execute(
        """
        CREATE TEMP TABLE tmp_similares (
            id_jugador integer,
            nombre character varying(100),
            cluster integer,
            id_similar1 integer,
            nombre_similar1 character varying(100),
            similitud1 numeric(8,4),
            id_similar2 integer,
            nombre_similar2 character varying(100),
            similitud2 numeric(8,4),
            id_similar3 integer,
            nombre_similar3 character varying(100),
            similitud3 numeric(8,4),
            id_similar4 integer,
            nombre_similar4 character varying(100),
            similitud4 numeric(8,4),
            id_similar5 integer,
            nombre_similar5 character varying(100),
            similitud5 numeric(8,4)
        ) ON COMMIT DROP;
        """
    )

    with similares_csv.open("r", encoding="utf-8-sig") as f:
        cur.copy_expert(
            """
            COPY tmp_similares (
                id_jugador, nombre, cluster,
                id_similar1, nombre_similar1, similitud1,
                id_similar2, nombre_similar2, similitud2,
                id_similar3, nombre_similar3, similitud3,
                id_similar4, nombre_similar4, similitud4,
                id_similar5, nombre_similar5, similitud5
            )
            FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ';', NULL '');
            """,
            f,
        )

    cur.execute(
        f"""
        INSERT INTO {similares_table} (
            id_jugador, nombre, cluster,
            id_similar1, nombre_similar1, similitud1,
            id_similar2, nombre_similar2, similitud2,
            id_similar3, nombre_similar3, similitud3,
            id_similar4, nombre_similar4, similitud4,
            id_similar5, nombre_similar5, similitud5
        )
        SELECT
            t.id_jugador, t.nombre, t.cluster,
            t.id_similar1, t.nombre_similar1, t.similitud1,
            t.id_similar2, t.nombre_similar2, t.similitud2,
            t.id_similar3, t.nombre_similar3, t.similitud3,
            t.id_similar4, t.nombre_similar4, t.similitud4,
            t.id_similar5, t.nombre_similar5, t.similitud5
        FROM tmp_similares t
        ON CONFLICT (id_jugador)
        DO UPDATE SET
            nombre = EXCLUDED.nombre,
            cluster = EXCLUDED.cluster,
            id_similar1 = EXCLUDED.id_similar1,
            nombre_similar1 = EXCLUDED.nombre_similar1,
            similitud1 = EXCLUDED.similitud1,
            id_similar2 = EXCLUDED.id_similar2,
            nombre_similar2 = EXCLUDED.nombre_similar2,
            similitud2 = EXCLUDED.similitud2,
            id_similar3 = EXCLUDED.id_similar3,
            nombre_similar3 = EXCLUDED.nombre_similar3,
            similitud3 = EXCLUDED.similitud3,
            id_similar4 = EXCLUDED.id_similar4,
            nombre_similar4 = EXCLUDED.nombre_similar4,
            similitud4 = EXCLUDED.similitud4,
            id_similar5 = EXCLUDED.id_similar5,
            nombre_similar5 = EXCLUDED.nombre_similar5,
            similitud5 = EXCLUDED.similitud5;
        """
    )


def main():
    args = parse_args()

    perfil_csv = Path(args.perfil_csv)
    similares_csv = Path(args.similares_csv)
    cargar_perfil_csv = (not args.skip_perfil) and perfil_csv.exists()
    cargar_similares_csv = (not args.skip_similares) and similares_csv.exists()

    if not cargar_perfil_csv and not args.skip_perfil and not perfil_csv.exists():
        print(f"Aviso: no existe el CSV de perfil y se omite la carga: {perfil_csv}")
    if not cargar_similares_csv and not args.skip_similares and not similares_csv.exists():
        print(f"Aviso: no existe el CSV de similares y se omite la carga: {similares_csv}")

    if not cargar_perfil_csv and not cargar_similares_csv:
        raise FileNotFoundError(
            "No hay CSVs para cargar. Revisa rutas o usa --skip-perfil/--skip-similares."
        )

    conn = psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
    )

    try:
        with conn.cursor() as cur:
            if cargar_perfil_csv:
                crear_tabla_perfil(cur, args.perfil_table)
                cargar_perfil(cur, perfil_csv, args.perfil_table)
            if cargar_similares_csv:
                crear_tabla_similares(cur, args.similares_table)
                cargar_similares(cur, similares_csv, args.similares_table)
        conn.commit()
    finally:
        conn.close()

    print(f"Carga completada en tablas: {args.perfil_table} y {args.similares_table}")


if __name__ == "__main__":
    main()
