import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2


RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_SALIDAS = RUTA_RAIZ / "DATA_MINING" / "DSA_DM"
RUTA_SALIDA = RUTA_SALIDAS / "PROBABLES_GOLEADORES.csv"


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera PROBABLES_GOLEADORES.csv leyendo desde PostgreSQL"
    )
    parser.add_argument("--db-host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("PGPORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("PGDATABASE", "TFG_BDLaLiga"))
    parser.add_argument("--db-user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("PGPASSWORD", "betico18"))
    parser.add_argument("--output", default=str(RUTA_SALIDA))
    return parser.parse_args()


def leer_tabla(conexion, consulta: str) -> pd.DataFrame:
    return pd.read_sql_query(consulta, conexion)


def main() -> None:
    argumentos = leer_argumentos()
    conexion = psycopg2.connect(
        host=argumentos.db_host,
        port=argumentos.db_port,
        dbname=argumentos.db_name,
        user=argumentos.db_user,
        password=argumentos.db_password,
    )

    try:
        df_partidos = leer_tabla(
            conexion,
            """
            SELECT id_partido, temporada, id_local, id_visitante, status
            FROM public.dim_partidos
            """,
        )
        df_h_jugador_partido = leer_tabla(
            conexion,
            """
            SELECT id_partido, id_jugador, id_equipo, goles
            FROM public.h_jugador_partido
            """,
        )
        df_h_jugador_temporada = leer_tabla(
            conexion,
            """
            SELECT id_jugador, id_equipo, temporada, partidos, goles
            FROM public.h_jugador_temporada
            """,
        )
        df_dim_jugadores = leer_tabla(
            conexion,
            """
            SELECT id_jugador, nombre
            FROM public.dim_jugador
            """,
        )
    finally:
        conexion.close()

    for df in [df_partidos, df_h_jugador_partido, df_h_jugador_temporada, df_dim_jugadores]:
        df.columns = df.columns.str.strip()

    print("Sincronizando plantillas de la temporada 2025...")

    df_plantillas_2025 = df_h_jugador_temporada[df_h_jugador_temporada["temporada"] == 2025]
    dict_nombres = df_dim_jugadores.set_index("id_jugador")["nombre"].to_dict()

    df_relacion = df_h_jugador_partido.merge(df_partidos[["id_partido", "id_local", "id_visitante"]], on="id_partido")
    df_relacion["id_rival"] = np.where(
        df_relacion["id_equipo"] == df_relacion["id_local"],
        df_relacion["id_visitante"],
        df_relacion["id_local"],
    )

    mapa_goles_rival = df_relacion.groupby(["id_jugador", "id_rival"])["goles"].sum().to_dict()

    df_h_jugador_partido = df_h_jugador_partido.sort_values(["id_jugador", "id_partido"])
    dict_racha = (
        df_h_jugador_partido.groupby("id_jugador")["goles"]
        .rolling(window=7, min_periods=1)
        .mean()
        .groupby(level=0)
        .last()
        .to_dict()
    )

    partidos_pendientes = df_partidos[df_partidos["status"] == "Incompleto"]
    resultados_probabilidad = []

    for _, partido in partidos_pendientes.iterrows():
        id_partido = partido["id_partido"]

        for id_equipo, id_rival in [
            (partido["id_local"], partido["id_visitante"]),
            (partido["id_visitante"], partido["id_local"]),
        ]:
            jugadores_reales = df_plantillas_2025[df_plantillas_2025["id_equipo"] == id_equipo]
            scores_jugadores = []

            for _, jug in jugadores_reales.iterrows():
                id_jugador = jug["id_jugador"]

                forma_score = dict_racha.get(id_jugador, 0)
                promedio_2025 = jug["goles"] / max(jug["partidos"], 1)
                goles_vs_rival = mapa_goles_rival.get((id_jugador, id_rival), 0)

                logit_score = (forma_score * 0.35) + (promedio_2025 * 0.45) + (min(goles_vs_rival, 3) * 0.05)
                probabilidad = 1 / (1 + np.exp(-(logit_score - 0.5) * 2))
                probabilidad = min(probabilidad, 0.75)

                scores_jugadores.append(
                    (id_jugador, dict_nombres.get(id_jugador, "N/A"), round(probabilidad, 3))
                )

            top_3 = sorted(scores_jugadores, key=lambda x: x[2], reverse=True)[:3]

            for id_j, nom, prob in top_3:
                resultados_probabilidad.append(
                    {
                        "id_partido": id_partido,
                        "id_equipo": id_equipo,
                        "id_jugador": id_j,
                        "nombre_jugador": nom,
                        "probabilidad": prob,
                    }
                )

    df_final = pd.DataFrame(resultados_probabilidad)
    archivo_salida = Path(argumentos.output)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(archivo_salida, index=False, sep=";", encoding="utf-8-sig")


if __name__ == "__main__":
    main()
