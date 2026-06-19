import argparse
import json
import os
from pathlib import Path

import pandas as pd
import psycopg2


mapeo_eventos = {
    "Argument": "Discusion / protesta",
    "Card": "Tarjeta",
    "Card reviewed": "Tarjeta revisada",
    "Card upgrade": "Tarjeta aumentada",
    "Dangerous play": "Juego peligroso",
    "Delay of game": "Perdida de tiempo",
    "Diving": "Simulacion",
    "Elbowing": "Codazo",
    "Foul": "Falta",
    "Goal": "Gol",
    "Goal cancelled": "Gol anulado",
    "Goal confirmed": "Gol confirmado",
    "Handball": "Mano",
    "Handling": "Mano",
    "Holding": "Sujecion",
    "Missed Penalty": "Penalti fallado",
    "Normal Goal": "Gol en jugada",
    "Not on pitch": "Fuera del campo",
    "Off the ball foul": "Falta sin balon",
    "Own Goal": "Gol en propia",
    "Penalty": "Penalti",
    "Penalty awarded": "Penalti senalado",
    "Penalty cancelled": "Penalti anulado",
    "Penalty confirmed": "Penalti confirmado",
    "Persistent fouling": "Faltas reiteradas",
    "Professional foul last man": "Falta como ultimo hombre",
    "Professional handball": "Mano profesional",
    "Red Card": "Tarjeta roja",
    "Red card cancelled": "Roja anulada",
    "Rescinded Card": "Tarjeta retirada",
    "Roughing": "Juego brusco",
    "Simulation": "Simulacion",
    "Substitution 1": "Sustitucion 1",
    "Substitution 2": "Sustitucion 2",
    "Substitution 3": "Sustitucion 3",
    "Substitution 4": "Sustitucion 4",
    "Substitution 5": "Sustitucion 5",
    "Substitution 6": "Sustitucion 6",
    "Time wasting": "Perdida de tiempo",
    "Tripping": "Zancadilla",
    "Unallowed field entering": "Entrada ilegal al campo",
    "Unsportsmanlike conduct": "Conducta antideportiva",
    "Var": "VAR",
    "Violent conduct": "Conducta violenta",
    "Yellow Card": "Tarjeta amarilla",
    "subst": "Sustitucion",
}


def traducir_eventos(evento):
    if evento is None:
        return None
    return mapeo_eventos.get(evento, evento)


def construir_parser():
    parser = argparse.ArgumentParser(
        description="Transforma partidos_eventos_full.json a CSV y carga en public.h_partido_eventos"
    )
    parser.add_argument(
        "--json-path",
        default=r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS\TIEMPO_REAL\partidos_eventos_full.json",
        help="Ruta al JSON de eventos de tiempo real",
    )
    parser.add_argument(
        "--csv-out",
        default=r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\h_partidos_eventos_tiempo_real.csv",
        help="Ruta del CSV de salida",
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


def transformar_eventos(data):
    todos_los_eventos = []

    for partido in data:
        f_id = partido.get("fixture_id")
        eventos = partido.get("data", [])

        for e in eventos:
            fila = {
                "id_partido": f_id,
                "minuto": e.get("time", {}).get("elapsed"),
                "extra": e.get("time", {}).get("extra"),
                "id_equipo": e.get("team", {}).get("id"),
                "id_jugador": e.get("player", {}).get("id"),
                "id_asistente_o_sale": e.get("assist", {}).get("id"),
                "tipo": traducir_eventos(e.get("type")),
                "detalle": traducir_eventos(e.get("detail")),
                "comentarios": traducir_eventos(e.get("comments")),
            }
            todos_los_eventos.append(fila)

    if not todos_los_eventos:
        return pd.DataFrame(
            columns=[
                "id_partido",
                "minuto",
                "extra",
                "id_equipo",
                "id_jugador",
                "id_asistente_o_sale",
                "tipo",
                "detalle",
                "comentarios",
            ]
        )

    df = pd.DataFrame(todos_los_eventos)

    # id_partido viene informado en este JSON; si faltase, se descarta el registro.
    df["id_partido"] = pd.to_numeric(df["id_partido"], errors="coerce")
    df = df[df["id_partido"].notna()].copy()
    df["id_partido"] = df["id_partido"].astype(int)

    # Estos IDs pueden venir nulos (por ejemplo, eventos sin jugador/asistente).
    # Se guardan como NULL para no violar claves foraneas con valor 0.
    cols_ids_nullable = ["id_equipo", "id_jugador", "id_asistente_o_sale"]
    for col in cols_ids_nullable:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    df["minuto"] = pd.to_numeric(df["minuto"], errors="coerce").fillna(0).astype(int)
    df["extra"] = pd.to_numeric(df["extra"], errors="coerce").fillna(0).astype(int)

    df = df.sort_values(by=["id_partido", "minuto"])
    return df


def conectar_postgres(args):
    return psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
    )


def insertar_h_partido_eventos(conn, csv_path):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TEMP TABLE tmp_h_partido_eventos (
                id_partido integer,
                minuto integer,
                extra integer,
                id_equipo integer,
                id_jugador integer,
                id_asistente_o_sale integer,
                tipo character varying(50),
                detalle character varying(100),
                comentarios text
            ) ON COMMIT DROP;
            """
        )

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            cur.copy_expert(
                """
                COPY tmp_h_partido_eventos (
                    id_partido, minuto, extra, id_equipo, id_jugador, id_asistente_o_sale,
                    tipo, detalle, comentarios
                )
                FROM STDIN WITH (FORMAT CSV, HEADER TRUE, DELIMITER ';', NULL '');
                """,
                f,
            )

        cur.execute(
            """
            WITH base AS (
                SELECT COALESCE(MAX(id_evento), 0) AS max_id
                FROM public.h_partido_eventos
            ),
            nuevos AS (
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY
                            t.id_partido,
                            t.minuto,
                            t.extra,
                            t.id_equipo,
                            t.id_jugador,
                            t.tipo,
                            t.detalle,
                            t.comentarios
                    ) AS rn,
                    t.*
                FROM tmp_h_partido_eventos t
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM public.h_partido_eventos h
                    WHERE h.id_partido = t.id_partido
                      AND h.minuto = t.minuto
                      AND COALESCE(h.extra, 0) = COALESCE(t.extra, 0)
                      AND COALESCE(h.id_equipo, 0) = COALESCE(t.id_equipo, 0)
                      AND COALESCE(h.id_jugador, 0) = COALESCE(t.id_jugador, 0)
                      AND COALESCE(h.id_asistente_o_sale, 0) = COALESCE(t.id_asistente_o_sale, 0)
                      AND COALESCE(h.tipo, '') = COALESCE(t.tipo, '')
                      AND COALESCE(h.detalle, '') = COALESCE(t.detalle, '')
                      AND COALESCE(h.comentarios, '') = COALESCE(t.comentarios, '')
                )
            )
            INSERT INTO public.h_partido_eventos (
                id_evento,
                id_partido,
                minuto,
                extra,
                id_equipo,
                id_jugador,
                id_asistente_o_sale,
                tipo,
                detalle,
                comentarios
            )
            SELECT
                b.max_id + n.rn,
                n.id_partido,
                n.minuto,
                n.extra,
                n.id_equipo,
                n.id_jugador,
                n.id_asistente_o_sale,
                n.tipo,
                n.detalle,
                n.comentarios
            FROM nuevos n
            CROSS JOIN base b;
            """
        )

    conn.commit()


def main():
    args = construir_parser().parse_args()
    json_path = Path(args.json_path)
    csv_out = Path(args.csv_out)
    csv_out.parent.mkdir(parents=True, exist_ok=True)

    data = cargar_json(json_path)
    df = transformar_eventos(data)
    df.to_csv(csv_out, index=False, sep=";", encoding="utf-8-sig")

    conn = conectar_postgres(args)
    try:
        if not df.empty:
            insertar_h_partido_eventos(conn, csv_out)
    finally:
        conn.close()

    print(f"CSV generado: {csv_out}")
    print(f"Eventos transformados: {len(df)}")


if __name__ == "__main__":
    main()
