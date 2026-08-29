import argparse
import json
import os
from pathlib import Path

import pandas as pd
import psycopg2


MAPEO_STATS = {
    "Shots on Goal": "tiros_a_puerta",
    "Total Shots": "tiros_totales",
    "Shots insidebox": "tiros_en_area",
    "Shots outsidebox": "tiros_fuera_area",
    "Fouls": "faltas_cometidas",
    "Corner Kicks": "corners",
    "Offsides": "fueras_de_juego",
    "Ball Possession": "posesion",
    "Yellow Cards": "tarjetas_amarillas",
    "Red Cards": "tarjetas_rojas",
    "Goalkeeper Saves": "paradas",
    "Total passes": "pases_totales",
    "Passes accurate": "pases_acertados",
    "Passes %": "pct_pases_acertados",
    "expected_goals": "goles_esperados",
    "goals_prevented": "df_goles_esperados",
}

COLUMNAS_SALIDA = [
    "id_partido",
    "id_equipo",
    "tiros_a_puerta",
    "tiros_totales",
    "tiros_en_area",
    "tiros_fuera_area",
    "faltas_cometidas",
    "corners",
    "fueras_de_juego",
    "posesion",
    "tarjetas_amarillas",
    "tarjetas_rojas",
    "paradas",
    "pases_totales",
    "pases_acertados",
    "pct_pases_acertados",
    "goles_esperados",
    "df_goles_esperados",
]


def construir_parser():
    parser = argparse.ArgumentParser(
        description="Transforma partidos_stats_full.json a CSV y carga en public.h_equipo_partido"
    )
    parser.add_argument(
        "--json-path",
        default=r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS\TIEMPO_REAL\partidos_stats_full.json",
        help="Ruta al JSON de estadisticas de equipos en tiempo real",
    )
    parser.add_argument(
        "--csv-out",
        default=r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS\TIEMPO_REAL\h_equipo_partido.csv",
        help="Ruta del CSV de salida",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Genera el CSV sin cargar datos en PostgreSQL",
    )
    parser.add_argument("--db-host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("PGPORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("PGDATABASE", "TFG_Prueba"))
    parser.add_argument("--db-user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("PGPASSWORD", "betico18"))
    return parser


def cargar_json(ruta_json):
    with open(ruta_json, "r", encoding="utf-8") as f:
        return json.load(f)


def limpiar_valor(valor):
    if isinstance(valor, str):
        valor = valor.replace("%", "").strip()
    return 0 if valor is None else valor


def transformar_stats_equipos(data_json):
    rows = []

    for partido in data_json:
        fixture_id = partido.get("fixture_id")
        equipos = partido.get("data", partido.get("statistics", []))

        for team_data in equipos:
            fila = {
                "id_partido": fixture_id,
                "id_equipo": team_data.get("team", {}).get("id"),
            }

            for col in MAPEO_STATS.values():
                fila[col] = 0

            for stat in team_data.get("statistics", []):
                tipo = stat.get("type")
                if tipo in MAPEO_STATS:
                    fila[MAPEO_STATS[tipo]] = limpiar_valor(stat.get("value"))

            rows.append(fila)

    if not rows:
        return pd.DataFrame(columns=COLUMNAS_SALIDA)

    df = pd.DataFrame(rows, columns=COLUMNAS_SALIDA)

    df["id_partido"] = pd.to_numeric(df["id_partido"], errors="coerce")
    df["id_equipo"] = pd.to_numeric(df["id_equipo"], errors="coerce")
    df = df[df["id_partido"].notna() & df["id_equipo"].notna()].copy()
    df["id_partido"] = df["id_partido"].astype(int)
    df["id_equipo"] = df["id_equipo"].astype(int)

    cols_decimal = ["pct_pases_acertados", "goles_esperados", "df_goles_esperados"]
    cols_enteros = [
        c
        for c in COLUMNAS_SALIDA
        if c not in ["id_partido", "id_equipo"] + cols_decimal
    ]

    for col in cols_enteros:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    for col in cols_decimal:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)

    df = df.sort_values(by=["id_partido", "id_equipo"])
    return df


def conectar_postgres(args):
    return psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
    )


def insertar_h_equipo_partido(conn, csv_path):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TEMP TABLE tmp_h_equipo_partido (
                id_partido integer NOT NULL,
                id_equipo integer NOT NULL,
                tiros_a_puerta integer,
                tiros_totales integer,
                tiros_en_area integer,
                tiros_fuera_area integer,
                faltas_cometidas integer,
                corners integer,
                fueras_de_juego integer,
                posesion integer,
                tarjetas_amarillas integer,
                tarjetas_rojas integer,
                paradas integer,
                pases_totales integer,
                pases_acertados integer,
                pct_pases_acertados numeric(5,2),
                goles_esperados numeric(5,2),
                df_goles_esperados numeric(5,2)
            ) ON COMMIT DROP;
            """
        )

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            cur.copy_expert(
                """
                COPY tmp_h_equipo_partido (
                    id_partido, id_equipo, tiros_a_puerta, tiros_totales, tiros_en_area,
                    tiros_fuera_area, faltas_cometidas, corners, fueras_de_juego, posesion,
                    tarjetas_amarillas, tarjetas_rojas, paradas, pases_totales, pases_acertados,
                    pct_pases_acertados, goles_esperados, df_goles_esperados
                )
                FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ';', NULL '');
                """,
                f,
            )

        cur.execute(
            """
            INSERT INTO public.h_equipo_partido (
                id_partido, id_equipo, tiros_a_puerta, tiros_totales, tiros_en_area,
                tiros_fuera_area, faltas_cometidas, corners, fueras_de_juego, posesion,
                tarjetas_amarillas, tarjetas_rojas, paradas, pases_totales, pases_acertados,
                pct_pases_acertados, goles_esperados, df_goles_esperados
            )
            SELECT
                t.id_partido, t.id_equipo, t.tiros_a_puerta, t.tiros_totales, t.tiros_en_area,
                t.tiros_fuera_area, t.faltas_cometidas, t.corners, t.fueras_de_juego, t.posesion,
                t.tarjetas_amarillas, t.tarjetas_rojas, t.paradas, t.pases_totales, t.pases_acertados,
                t.pct_pases_acertados, t.goles_esperados, t.df_goles_esperados
            FROM tmp_h_equipo_partido t
            WHERE NOT EXISTS (
                SELECT 1
                FROM public.h_equipo_partido h
                WHERE h.id_partido = t.id_partido
                  AND h.id_equipo = t.id_equipo
            );
            """
        )

    conn.commit()


def main():
    args = construir_parser().parse_args()
    json_path = Path(args.json_path)
    csv_out = Path(args.csv_out)
    csv_out.parent.mkdir(parents=True, exist_ok=True)

    data_json = cargar_json(json_path)
    df = transformar_stats_equipos(data_json)
    df.to_csv(csv_out, index=False, sep=";", encoding="utf-8-sig")

    if not args.skip_db:
        conn = conectar_postgres(args)
        try:
            if not df.empty:
                insertar_h_equipo_partido(conn, csv_out)
        finally:
            conn.close()

    print(f"CSV generado: {csv_out}")
    print(f"Registros transformados para h_equipo_partido: {len(df)}")


if __name__ == "__main__":
    main()
