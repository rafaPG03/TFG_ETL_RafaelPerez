from pathlib import Path

import psycopg2
from psycopg2 import sql


CSV_PATH = Path(r"c:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATA_MINING\DSA_DM\perfil_estadistico_jugadores.csv")
SCHEMA = "public"
TABLE = "h_jugadores_ratings"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "TFG_Prueba",
    "user": "postgres",
    "password": "betico18",
}

COLUMNS = [
    "id_jugador",
    "temporada",
    "nombre",
    "ataque",
    "creacion",
    "defensa",
    "porteros",
    "duelos",
    "regates",
    "percentil_ataque",
    "percentil_creacion",
    "percentil_defensa",
    "percentil_porteros",
    "percentil_duelos",
    "percentil_regates",
]


def ensure_table(cur):
    create_table = sql.SQL(
        """
        CREATE TABLE IF NOT EXISTS {schema}.{table} (
            id_jugador INTEGER NOT NULL,
            temporada INTEGER NOT NULL,
            nombre TEXT,
            ataque DOUBLE PRECISION,
            creacion DOUBLE PRECISION,
            defensa DOUBLE PRECISION,
            porteros DOUBLE PRECISION,
            duelos DOUBLE PRECISION,
            regates DOUBLE PRECISION,
            percentil_ataque DOUBLE PRECISION,
            percentil_creacion DOUBLE PRECISION,
            percentil_defensa DOUBLE PRECISION,
            percentil_porteros DOUBLE PRECISION,
            percentil_duelos DOUBLE PRECISION,
            percentil_regates DOUBLE PRECISION,
            PRIMARY KEY (id_jugador, temporada)
        )
        """
    ).format(schema=sql.Identifier(SCHEMA), table=sql.Identifier(TABLE))
    cur.execute(create_table)


def copy_upsert_from_csv(cur, csv_path):
    temp_table = f"tmp_{TABLE}"
    create_temp = sql.SQL(
        "CREATE TEMP TABLE {temp} (LIKE {schema}.{table} INCLUDING ALL EXCLUDING CONSTRAINTS)"
    ).format(
        temp=sql.Identifier(temp_table),
        schema=sql.Identifier(SCHEMA),
        table=sql.Identifier(TABLE),
    )
    cur.execute(create_temp)

    copy_sql = sql.SQL(
        "COPY {temp} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER ';', NULL '')"
    ).format(
        temp=sql.Identifier(temp_table),
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in COLUMNS),
    )
    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        cur.copy_expert(copy_sql.as_string(cur), csv_file)

    update_cols = [
        c for c in COLUMNS if c not in ("id_jugador", "temporada")
    ]
    updates = sql.SQL(", ").join(
        sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c))
        for c in update_cols
    )
    insert_sql = sql.SQL(
        "INSERT INTO {schema}.{table} ({cols}) "
        "SELECT {cols} FROM {temp} "
        "ON CONFLICT (id_jugador, temporada) DO UPDATE SET {updates}"
    ).format(
        schema=sql.Identifier(SCHEMA),
        table=sql.Identifier(TABLE),
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in COLUMNS),
        temp=sql.Identifier(temp_table),
        updates=updates,
    )
    cur.execute(insert_sql)


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"No se encuentra el CSV: {CSV_PATH}")

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            ensure_table(cur)
            copy_upsert_from_csv(cur, CSV_PATH)
        conn.commit()


if __name__ == "__main__":
    main()
