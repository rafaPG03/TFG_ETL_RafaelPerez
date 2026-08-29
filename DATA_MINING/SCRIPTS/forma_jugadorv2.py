import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2


RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_SALIDAS = RUTA_RAIZ / "DATA_MINING" / "DSA_DM"
RUTA_SALIDA = RUTA_SALIDAS / "ESTADO_FORMA_JUGADORES_2025.csv"


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera ESTADO_FORMA_JUGADORES_2025.csv leyendo desde PostgreSQL"
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


def calcular_score_unico(row):
    pos = str(row.get("posicion", "")).upper()
    nota_base = row.get("nota", 0)

    score_acciones = 0
    score_acciones += row.get("goles", 0) * 1.5
    score_acciones += row.get("asistencias", 0) * 1.0

    if "P" not in pos:
        score_acciones += row.get("duelos_ganados", 0) * 0.2

    if "DF" in pos or "D" in pos:
        score_acciones += row.get("intercepciones", 0) * 0.4
        score_acciones += row.get("entradas", 0) * 0.3
        score_acciones -= row.get("regateado", 0) * 0.5
        score_acciones -= row.get("goles_concedidos", 0) * 0.4
    elif "M" in pos:
        score_acciones += row.get("pases_clave", 0) * 0.5
        score_acciones += row.get("regates", 0) * 0.3
        score_acciones += row.get("precision_pases", 0) / 100
    elif "D" in pos or "A" in pos:
        score_acciones += row.get("tiros_a_puerta", 0) * 0.5
        score_acciones += row.get("regates", 0) * 0.4
    elif "P" in pos:
        score_acciones += row.get("paradas", 0) * 0.6
        score_acciones += row.get("penaltis_parados", 0) * 2.0
        score_acciones -= row.get("goles_concedidos", 0) * 0.8

    return round((nota_base * 0.6) + (score_acciones * 0.4), 2)


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
        df_h_partidos_raw = leer_tabla(
            conexion,
            """
            SELECT
                id_partido,
                id_jugador,
                id_equipo,
                posicion,
                minutos,
                nota,
                capitan,
                sustituto,
                goles,
                penaltis_marcados,
                asistencias,
                paradas,
                goles_concedidos,
                tiros_totales,
                tiros_a_puerta,
                pases_totales,
                pases_clave,
                precision_pases,
                regates_intentados,
                regates,
                regateado,
                duelos_totales,
                duelos_ganados,
                faltas_cometidas,
                faltas_recibidas,
                entradas,
                bloqueos,
                intercepciones,
                amarilla,
                roja,
                penaltis_parados
            FROM public.h_jugador_partido
            """,
        )
        df_dim_partidos = leer_tabla(
            conexion,
            """
            SELECT id_partido, temporada
            FROM public.dim_partidos
            """,
        )
        df_dim_jug = leer_tabla(
            conexion,
            """
            SELECT id_jugador, nombre
            FROM public.dim_jugador
            """,
        )
    finally:
        conexion.close()

    for df in [df_h_partidos_raw, df_dim_partidos, df_dim_jug]:
        df.columns = df.columns.str.strip()

    df_merge = df_h_partidos_raw.merge(df_dim_partidos[["id_partido", "temporada"]], on="id_partido")
    df_2025 = df_merge[df_merge["temporada"] == 2025].copy()

    dict_nombres = df_dim_jug.set_index("id_jugador")["nombre"].to_dict()

    df_2025["score_calculado"] = df_2025.apply(calcular_score_unico, axis=1)

    resultados = []
    jugadores_unicos = df_2025["id_jugador"].unique()

    print("Analizando momentum con metricas unificadas...")

    for id_j in jugadores_unicos:
        df_jugador = df_2025[df_2025["id_jugador"] == id_j].sort_values("id_partido", ascending=False)

        partidos_validos_temp = df_jugador[df_jugador["minutos"] >= 15]
        if len(partidos_validos_temp) == 0:
            continue

        media_temporada = partidos_validos_temp["score_calculado"].mean()

        df_reciente = df_jugador.head(7)
        partidos_validos_rec = df_reciente[df_reciente["minutos"] >= 20]

        if len(partidos_validos_rec) < 3:
            estado = "Pocos minutos"
            media_reciente = 0
            evolucion = 0
        else:
            media_reciente = partidos_validos_rec["score_calculado"].mean()
            evolucion = media_reciente - media_temporada

            if evolucion > 0.3:
                estado = "Rendimiento Alto"
            elif evolucion < -0.3:
                estado = "Rendimiento Bajo"
            else:
                estado = "Estable"

        resultados.append(
            {
                "id_jugador": id_j,
                "nombre_jugador": dict_nombres.get(id_j, "N/A"),
                "id_equipo": df_jugador.iloc[0]["id_equipo"],
                "estado": estado,
                "score_temporada": round(media_temporada, 2),
                "score_reciente": round(media_reciente, 2),
                "evolucion": round(evolucion, 2),
            }
        )

    df_momentum_final = pd.DataFrame(resultados)
    archivo_salida = Path(argumentos.output)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    df_momentum_final.to_csv(archivo_salida, index=False, sep=";", encoding="utf-8-sig")

    print(f"Completado. Se han analizado {len(df_momentum_final)} jugadores bajo el nuevo criterio unico.")


if __name__ == "__main__":
    main()
