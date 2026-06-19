import argparse
import json
import os
from pathlib import Path

import pandas as pd
import psycopg2


mapeo_posiciones = {
    "G": "P",
    "D": "DF",
    "F": "DL",
}


def traducir_posicion(posicion):
    if posicion is None:
        return None
    return mapeo_posiciones.get(posicion, posicion)


def conectar_postgres(args):
    return psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
    )


def cargar_json(ruta_json):
    with open(ruta_json, "r", encoding="utf-8") as f:
        return json.load(f)


def extraer_jugadores_para_dim(data_json):
    jugadores = {}
    for game in data_json:
        for team_entry in game.get("data", []):
            for p_data in team_entry.get("players", []):
                p_info = p_data.get("player", {})
                player_id = p_info.get("id")
                if player_id is None:
                    continue

                try:
                    player_id = int(player_id)
                except (TypeError, ValueError):
                    continue

                nombre = p_info.get("name")
                foto = p_info.get("photo")

                if player_id not in jugadores:
                    jugadores[player_id] = {
                        "id_jugador": player_id,
                        "nombre": nombre,
                        "foto": foto,
                    }
                else:
                    if (not jugadores[player_id].get("nombre")) and nombre:
                        jugadores[player_id]["nombre"] = nombre
                    if (not jugadores[player_id].get("foto")) and foto:
                        jugadores[player_id]["foto"] = foto

    return pd.DataFrame(jugadores.values(), columns=["id_jugador", "nombre", "foto"])


def obtener_ids_dim_en_bd(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id_jugador FROM public.dim_jugador;")
        rows = cur.fetchall()
    return {int(r[0]) for r in rows}


def generar_csv_dim_faltantes(df_dim_json, ids_bd, ruta_csv_salida):
    df_faltantes = df_dim_json[~df_dim_json["id_jugador"].isin(ids_bd)].copy()
    df_faltantes = df_faltantes.sort_values(by="id_jugador")
    df_faltantes.to_csv(ruta_csv_salida, index=False, sep=";", encoding="utf-8-sig")
    return df_faltantes


def cargar_dim_faltantes_desde_csv(conn, ruta_csv):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TEMP TABLE tmp_dim_jugador_nuevos (
                id_jugador integer NOT NULL,
                nombre character varying(100),
                foto text
            ) ON COMMIT DROP;
            """
        )

        with open(ruta_csv, "r", encoding="utf-8-sig") as f:
            cur.copy_expert(
                """
                COPY tmp_dim_jugador_nuevos (id_jugador, nombre, foto)
                FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ';', NULL '');
                """,
                f,
            )

        cur.execute(
            """
            INSERT INTO public.dim_jugador (id_jugador, nombre, foto)
            SELECT t.id_jugador, t.nombre, t.foto
            FROM tmp_dim_jugador_nuevos t
            LEFT JOIN public.dim_jugador d
                ON d.id_jugador = t.id_jugador
            WHERE d.id_jugador IS NULL;
            """
        )

    conn.commit()


def transformar_json_a_h_jugador_partido(data_json):
    rows = []

    for game in data_json:
        fixture_id = game.get("fixture_id")

        for team_entry in game.get("data", []):
            id_equipo = team_entry.get("team", {}).get("id")

            for p_data in team_entry.get("players", []):
                p_info = p_data.get("player", {})

                for stat in p_data.get("statistics", []):
                    fila = {
                        "id_partido": fixture_id,
                        "id_jugador": p_info.get("id"),
                        "id_equipo": id_equipo,
                        "posicion": traducir_posicion(stat.get("games", {}).get("position")),
                        "minutos": stat.get("games", {}).get("minutes"),
                        "nota": stat.get("games", {}).get("rating"),
                        "capitan": stat.get("games", {}).get("captain"),
                        "sustituto": stat.get("games", {}).get("substitute"),
                        "goles": stat.get("goals", {}).get("total"),
                        "penaltis_marcados": stat.get("penalty", {}).get("scored"),
                        "asistencias": stat.get("goals", {}).get("assists"),
                        "paradas": stat.get("goals", {}).get("saves"),
                        "goles_concedidos": stat.get("goals", {}).get("conceded"),
                        "tiros_totales": stat.get("shots", {}).get("total"),
                        "tiros_a_puerta": stat.get("shots", {}).get("on"),
                        "pases_totales": stat.get("passes", {}).get("total"),
                        "pases_clave": stat.get("passes", {}).get("key"),
                        "precision_pases": str(stat.get("passes", {}).get("accuracy", "0")).replace("%", ""),
                        "regates_intentados": stat.get("dribbles", {}).get("attempts"),
                        "regates": stat.get("dribbles", {}).get("success"),
                        "regateado": stat.get("dribbles", {}).get("past"),
                        "duelos_totales": stat.get("duels", {}).get("total"),
                        "duelos_ganados": stat.get("duels", {}).get("won"),
                        "faltas_cometidas": stat.get("fouls", {}).get("committed"),
                        "faltas_recibidas": stat.get("fouls", {}).get("drawn"),
                        "entradas": stat.get("tackles", {}).get("total"),
                        "bloqueos": stat.get("tackles", {}).get("blocks"),
                        "intercepciones": stat.get("tackles", {}).get("interceptions"),
                        "amarilla": stat.get("cards", {}).get("yellow"),
                        "roja": stat.get("cards", {}).get("red"),
                        "penaltis_parados": stat.get("penalty", {}).get("saved"),
                    }
                    rows.append(fila)

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df = df.sort_values(by=["id_partido", "id_equipo"], ascending=[True, True])

    df["nota"] = pd.to_numeric(df["nota"], errors="coerce").fillna(0.0)

    cols_enteros = [
        "id_partido",
        "id_jugador",
        "id_equipo",
        "minutos",
        "goles",
        "asistencias",
        "paradas",
        "tiros_totales",
        "tiros_a_puerta",
        "pases_totales",
        "pases_clave",
        "precision_pases",
        "faltas_cometidas",
        "faltas_recibidas",
        "amarilla",
        "roja",
        "penaltis_parados",
        "intercepciones",
        "bloqueos",
        "entradas",
        "regates_intentados",
        "regates",
        "goles_concedidos",
        "duelos_totales",
        "duelos_ganados",
        "regateado",
        "penaltis_marcados",
    ]

    for col in cols_enteros:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


def cargar_h_jugador_partido_desde_csv(conn, ruta_csv):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TEMP TABLE tmp_h_jugador_partido (
                id_partido integer NOT NULL,
                id_jugador integer NOT NULL,
                id_equipo integer,
                posicion character varying(10),
                minutos integer,
                nota numeric(4,2),
                capitan boolean,
                sustituto boolean,
                goles integer,
                penaltis_marcados integer,
                asistencias integer,
                paradas integer,
                goles_concedidos integer,
                tiros_totales integer,
                tiros_a_puerta integer,
                pases_totales integer,
                pases_clave integer,
                precision_pases integer,
                regates_intentados integer,
                regates integer,
                regateado integer,
                duelos_totales integer,
                duelos_ganados integer,
                faltas_cometidas integer,
                faltas_recibidas integer,
                entradas integer,
                bloqueos integer,
                intercepciones integer,
                amarilla integer,
                roja integer,
                penaltis_parados integer
            ) ON COMMIT DROP;
            """
        )

        with open(ruta_csv, "r", encoding="utf-8-sig") as f:
            cur.copy_expert(
                """
                COPY tmp_h_jugador_partido (
                    id_partido, id_jugador, id_equipo, posicion, minutos, nota, capitan, sustituto,
                    goles, penaltis_marcados, asistencias, paradas, goles_concedidos, tiros_totales,
                    tiros_a_puerta, pases_totales, pases_clave, precision_pases, regates_intentados,
                    regates, regateado, duelos_totales, duelos_ganados, faltas_cometidas,
                    faltas_recibidas, entradas, bloqueos, intercepciones, amarilla, roja, penaltis_parados
                )
                FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ';', NULL '');
                """,
                f,
            )

        cur.execute(
            """
            INSERT INTO public.h_jugador_partido (
                id_partido, id_jugador, id_equipo, posicion, minutos, nota, capitan, sustituto,
                goles, penaltis_marcados, asistencias, paradas, goles_concedidos, tiros_totales,
                tiros_a_puerta, pases_totales, pases_clave, precision_pases, regates_intentados,
                regates, regateado, duelos_totales, duelos_ganados, faltas_cometidas,
                faltas_recibidas, entradas, bloqueos, intercepciones, amarilla, roja, penaltis_parados
            )
            SELECT
                t.id_partido, t.id_jugador, t.id_equipo, t.posicion, t.minutos, t.nota, t.capitan, t.sustituto,
                t.goles, t.penaltis_marcados, t.asistencias, t.paradas, t.goles_concedidos, t.tiros_totales,
                t.tiros_a_puerta, t.pases_totales, t.pases_clave, t.precision_pases, t.regates_intentados,
                t.regates, t.regateado, t.duelos_totales, t.duelos_ganados, t.faltas_cometidas,
                t.faltas_recibidas, t.entradas, t.bloqueos, t.intercepciones, t.amarilla, t.roja, t.penaltis_parados
            FROM tmp_h_jugador_partido t
            WHERE NOT EXISTS (
                SELECT 1
                FROM public.h_jugador_partido h
                WHERE h.id_partido = t.id_partido
                  AND h.id_jugador = t.id_jugador
            );
            """
        )

    conn.commit()


def construir_parser():
    parser = argparse.ArgumentParser(
        description="ETL JSON -> CSV -> PostgreSQL para dim_jugador y h_jugador_partido"
    )
    parser.add_argument(
        "--json-path",
        default=r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS\TIEMPO_REAL\partidos_jugadores_full.json",
        help="Ruta del JSON de entrada",
    )
    parser.add_argument(
        "--out-dir",
        default=r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA",
        help="Carpeta de salida para CSV",
    )

    parser.add_argument("--db-host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("PGPORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("PGDATABASE", "TFG_Prueba"))
    parser.add_argument("--db-user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("PGPASSWORD", "betico18"))

    return parser


def main():
    args = construir_parser().parse_args()

    json_path = Path(args.json_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_dim_faltantes = out_dir / "dim_jugador_nuevos_desde_json.csv"
    csv_h_jugador_partido = out_dir / "h_jugador_partido_desde_json.csv"

    data_json = cargar_json(json_path)

    conn = conectar_postgres(args)
    try:
        df_dim_json = extraer_jugadores_para_dim(data_json)
        ids_bd = obtener_ids_dim_en_bd(conn)
        df_dim_faltantes = generar_csv_dim_faltantes(df_dim_json, ids_bd, csv_dim_faltantes)

        if not df_dim_faltantes.empty:
            cargar_dim_faltantes_desde_csv(conn, csv_dim_faltantes)

        df_h = transformar_json_a_h_jugador_partido(data_json)
        df_h.to_csv(csv_h_jugador_partido, index=False, sep=";", encoding="utf-8-sig")

        if not df_h.empty:
            cargar_h_jugador_partido_desde_csv(conn, csv_h_jugador_partido)

        print(f"CSV nuevos dim_jugador: {csv_dim_faltantes}")
        print(f"CSV h_jugador_partido: {csv_h_jugador_partido}")
        print(f"Jugadores nuevos en dim_jugador: {len(df_dim_faltantes)}")
        print(f"Registros transformados para h_jugador_partido: {len(df_h)}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
