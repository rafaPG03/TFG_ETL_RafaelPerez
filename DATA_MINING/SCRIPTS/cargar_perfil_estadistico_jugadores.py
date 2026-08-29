from pathlib import Path

import psycopg2
from psycopg2 import sql


RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_CSV = RUTA_RAIZ / "DATA_MINING" / "DSA_DM" / "perfil_estadistico_jugadores.csv"
ESQUEMA = "public"
TABLA = "h_jugadores_ratings"

CONFIGURACION_BD = {
    "host": "localhost",
    "port": 5432,
    "dbname": "TFG_Prueba",
    "user": "postgres",
    "password": "betico18",
}

COLUMNAS = [
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


def asegurar_tabla(cursor) -> None:
    consulta_creacion = sql.SQL(
        """
        CREATE TABLE IF NOT EXISTS {esquema}.{tabla} (
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
    ).format(esquema=sql.Identifier(ESQUEMA), tabla=sql.Identifier(TABLA))
    cursor.execute(consulta_creacion)


def cargar_csv_con_upsert(cursor, ruta_csv: Path) -> None:
    tabla_temporal = f"tmp_{TABLA}"
    consulta_temporal = sql.SQL(
        "CREATE TEMP TABLE {temporal} (LIKE {esquema}.{tabla} INCLUDING ALL EXCLUDING CONSTRAINTS)"
    ).format(
        temporal=sql.Identifier(tabla_temporal),
        esquema=sql.Identifier(ESQUEMA),
        tabla=sql.Identifier(TABLA),
    )
    cursor.execute(consulta_temporal)

    consulta_copia = sql.SQL(
        "COPY {temporal} ({columnas}) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER ';', NULL '')"
    ).format(
        temporal=sql.Identifier(tabla_temporal),
        columnas=sql.SQL(", ").join(sql.Identifier(columna) for columna in COLUMNAS),
    )
    with ruta_csv.open("r", encoding="utf-8", newline="") as archivo_csv:
        cursor.copy_expert(consulta_copia.as_string(cursor), archivo_csv)

    columnas_actualizables = [
        columna for columna in COLUMNAS if columna not in ("id_jugador", "temporada")
    ]
    actualizaciones = sql.SQL(", ").join(
        sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(columna), sql.Identifier(columna))
        for columna in columnas_actualizables
    )
    consulta_insercion = sql.SQL(
        "INSERT INTO {esquema}.{tabla} ({columnas}) "
        "SELECT {columnas} FROM {temporal} "
        "ON CONFLICT (id_jugador, temporada) DO UPDATE SET {actualizaciones}"
    ).format(
        esquema=sql.Identifier(ESQUEMA),
        tabla=sql.Identifier(TABLA),
        columnas=sql.SQL(", ").join(sql.Identifier(columna) for columna in COLUMNAS),
        temporal=sql.Identifier(tabla_temporal),
        actualizaciones=actualizaciones,
    )
    cursor.execute(consulta_insercion)


def main() -> None:
    if not RUTA_CSV.exists():
        raise FileNotFoundError(f"No se encuentra el CSV: {RUTA_CSV}")

    with psycopg2.connect(**CONFIGURACION_BD) as conexion:
        with conexion.cursor() as cursor:
            asegurar_tabla(cursor)
            cargar_csv_con_upsert(cursor, RUTA_CSV)
        conexion.commit()


if __name__ == "__main__":
    main()
