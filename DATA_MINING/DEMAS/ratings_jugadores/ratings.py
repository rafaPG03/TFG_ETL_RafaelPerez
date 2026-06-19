import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2


BASE_DIR = Path(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATA_MINING\DSA_DM')
OUTPUT_FILE = BASE_DIR / "perfil_estadistico_jugadores.csv"
TEMPORADA_ACTUAL = 2025
C = 5


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera perfil_estadistico_jugadores.csv leyendo desde PostgreSQL"
    )
    parser.add_argument("--db-host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("PGPORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("PGDATABASE", "TFG_BDLaLiga"))
    parser.add_argument("--db-user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("PGPASSWORD", "betico18"))
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    return parser.parse_args()


def read_table(conn, query):
    return pd.read_sql_query(query, conn)


def calcular_peso_temporal(anio):
    delta = TEMPORADA_ACTUAL - anio
    return 0.7 ** delta if delta >= 0 else 0


def calcular_indices(row):
    partidos = max(row["partidos"], 1)
    minutos = max(row["minutos"], 1)

    factor_experiencia = min(1.0, partidos / 10)

    score_ataque = (row["goles"] * 3 + row["tiros_a_puerta"] * 1.5) / partidos
    ataque = min(10, score_ataque * 1.2) * factor_experiencia

    pases_volumen = row["pases_totales"] / minutos
    factor_peligro = (row["pases_clave"] * 3 + row["asistencias"] * 5) / partidos
    factor_eficiencia = (row["precision_pases"] / 100) * pases_volumen * 10
    score_creacion = (factor_peligro * 1.3) + (factor_eficiencia * 0.7)
    creacion = min(10, score_creacion) * factor_experiencia

    defensivo = (row["entradas"] + row["intercepciones"] + row["bloqueos"]) / partidos
    penalizacion_def = (
        row.get("rojas", 0) * 0.8
        + row["amarillas"] * 0.5
        + row.get("regateado", 0) * 0.3
    ) / partidos
    defensa = max(0, min(10, (defensivo - penalizacion_def) * 1.5)) * factor_experiencia

    es_portero = str(row["posicion"]).strip().upper() in {"PORTERO", "P", "G"}
    if es_portero:
        ratio_paradas = row["paradas"] / (row["goles_concedidos"] + 1)
        goles_pp = row["goles_concedidos"] / partidos
        factor_muro = max(0, 5 - (goles_pp * 2))
        score_portero = (ratio_paradas * 1.5) + factor_muro + (row["penaltis_parados"] * 2)
        portero = min(10, score_portero) * factor_experiencia
    else:
        portero = 0

    ratio_duelos = row["duelos_ganados"] / (row["duelos_totales"] + C)
    volumen_duelos = row["duelos_totales"] / partidos
    duelos = min(10, (ratio_duelos * 7) + (volumen_duelos * 0.3)) * factor_experiencia

    ratio_regates = row["regates_exito"] / (row["regates_intentados"] + C)
    regates_por_partido = row["regates_exito"] / partidos
    faltas_sufridas = row["faltas_sufridas"] / partidos
    regates = min(
        10,
        (ratio_regates * 6) + (regates_por_partido * 1.5) + (faltas_sufridas * 0.5),
    ) * factor_experiencia

    return pd.Series([ataque, creacion, defensa, portero, duelos, regates])


def normalizar_rango_0_10(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    df_out = df.copy()
    for col in columnas:
        serie = pd.to_numeric(df_out[col], errors="coerce")
        maximo = serie.max()

        if pd.isna(maximo) or maximo <= 0:
            df_out[col] = 0.0
        else:
            # El valor máximo de la columna se convierte en 10.
            df_out[col] = (serie / maximo) * 10

        df_out[col] = df_out[col].clip(0, 10).round(2)

    return df_out


def anadir_percentiles(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    df_out = df.copy()
    for col in columnas:
        serie = pd.to_numeric(df_out[col], errors="coerce")
        # Percentil relativo del jugador en la stat (0-100, mayor es mejor).
        df_out[f"percentil_{col}"] = (serie.rank(method="average", pct=True) * 100).round(2)

    return df_out


def main():
    args = parse_args()
    conn = psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
    )

    try:
        df = read_table(conn, "SELECT * FROM public.h_jugador_temporada")
        df_dim_jug = read_table(conn, "SELECT id_jugador, nombre FROM public.dim_jugador")
    finally:
        conn.close()

    df.columns = df.columns.str.strip()
    df_dim_jug.columns = df_dim_jug.columns.str.strip()

    df["peso_temp"] = pd.to_numeric(df["temporada"], errors="coerce").fillna(0).apply(calcular_peso_temporal)

    columnas_notas = ["ataque", "creacion", "defensa", "porteros", "duelos", "regates"]
    df[columnas_notas] = df.apply(calcular_indices, axis=1)

    for col in columnas_notas:
        df[col] = df[col] * df["peso_temp"]

    perfil_jugador = df.groupby("id_jugador").agg(
        {
            "ataque": "sum",
            "creacion": "sum",
            "defensa": "sum",
            "porteros": "sum",
            "duelos": "sum",
            "regates": "sum",
            "peso_temp": "sum",
        }
    )

    perfil_jugador = perfil_jugador[perfil_jugador["peso_temp"] > 0].copy()
    for col in columnas_notas:
        perfil_jugador[col] = (perfil_jugador[col] / perfil_jugador["peso_temp"]).round(2)

    perfil_jugador = perfil_jugador.drop(columns=["peso_temp"]).reset_index()

    perfil_final = pd.merge(perfil_jugador, df_dim_jug[["id_jugador", "nombre"]], on="id_jugador", how="left")
    columnas_ordenadas = [
        "id_jugador",
        "nombre",
        "ataque",
        "creacion",
        "defensa",
        "porteros",
        "duelos",
        "regates",
    ]
    perfil_final = perfil_final[columnas_ordenadas]

    # Normalizamos cada rating al rango [0, 10].
    perfil_final = normalizar_rango_0_10(perfil_final, columnas_notas)

    # Añadimos percentiles por cada stat calculada.
    perfil_final = anadir_percentiles(perfil_final, columnas_notas)

    columnas_percentiles = [f"percentil_{col}" for col in columnas_notas]
    perfil_final = perfil_final[columnas_ordenadas + columnas_percentiles]

    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    perfil_final.to_csv(output_file, index=False, sep=";", encoding="utf-8-sig")
    print(f"CSV sacado: {output_file}")


if __name__ == "__main__":
    main()