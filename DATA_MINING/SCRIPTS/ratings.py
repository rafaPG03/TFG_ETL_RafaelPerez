import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2


RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_SALIDAS = RUTA_RAIZ / "DATA_MINING" / "DSA_DM"
RUTA_SALIDA = RUTA_SALIDAS / "perfil_estadistico_jugadores.csv"
TEMPORADA_ACTUAL = 2025
C = 5


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera perfil_estadistico_jugadores.csv leyendo desde PostgreSQL"
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


def normalizar_rango_0_10_por_grupo(
    df: pd.DataFrame, columnas: list[str], columna_grupo: str
) -> pd.DataFrame:
    # Normaliza cada estadística al rango [0, 10] dentro de su grupo.
    df_out = df.copy()
    for col in columnas:
        serie = pd.to_numeric(df_out[col], errors="coerce")
        maximo_grupo = serie.groupby(df_out[columna_grupo]).transform("max")
        numerador = np.where(maximo_grupo > 0, serie / maximo_grupo, 0.0)
        df_out[col] = (pd.Series(numerador, index=df_out.index) * 10).clip(0, 10).round(2)

    return df_out


def anadir_percentiles(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    df_out = df.copy()
    for col in columnas:
        serie = pd.to_numeric(df_out[col], errors="coerce")
        # Percentil relativo del jugador en la estadística.
        df_out[f"percentil_{col}"] = (serie.rank(method="average", pct=True) * 100).round(2)

    return df_out


def anadir_percentiles_por_grupo(
    df: pd.DataFrame, columnas: list[str], columna_grupo: str
) -> pd.DataFrame:
    df_out = df.copy()
    for col in columnas:
        serie = pd.to_numeric(df_out[col], errors="coerce")
        # Percentil relativo del jugador dentro de su grupo.
        df_out[f"percentil_{col}"] = (
            df_out.groupby(columna_grupo)[col]
            .rank(method="average", pct=True)
            .mul(100)
            .round(2)
        )

    return df_out


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
        df = leer_tabla(conexion, "SELECT * FROM public.h_jugador_temporada")
        df_dim_jug = leer_tabla(conexion, "SELECT id_jugador, nombre FROM public.dim_jugador")
    finally:
        conexion.close()

    df.columns = df.columns.str.strip()
    df_dim_jug.columns = df_dim_jug.columns.str.strip()
    df["temporada"] = pd.to_numeric(df["temporada"], errors="coerce")
    df = df[df["temporada"].notna()].copy()
    df["temporada"] = df["temporada"].astype(int)

    columnas_notas = ["ataque", "creacion", "defensa", "porteros", "duelos", "regates"]
    df[columnas_notas] = df.apply(calcular_indices, axis=1)

    # Mantiene un perfil independiente por jugador y temporada.
    perfil_jugador = (
        df.groupby(["id_jugador", "temporada"], as_index=False)[columnas_notas]
        .mean()
        .round(2)
    )

    perfil_final = pd.merge(
        perfil_jugador,
        df_dim_jug[["id_jugador", "nombre"]],
        on="id_jugador",
        how="left",
    )
    columnas_ordenadas = [
        "id_jugador",
        "temporada",
        "nombre",
        "ataque",
        "creacion",
        "defensa",
        "porteros",
        "duelos",
        "regates",
    ]
    perfil_final = perfil_final[columnas_ordenadas]

    # Normaliza cada valoración al rango [0, 10] dentro de la temporada.
    perfil_final = normalizar_rango_0_10_por_grupo(perfil_final, columnas_notas, "temporada")

    # Calcula los percentiles de cada estadística dentro de la temporada.
    perfil_final = anadir_percentiles_por_grupo(perfil_final, columnas_notas, "temporada")

    columnas_percentiles = [f"percentil_{col}" for col in columnas_notas]
    perfil_final = perfil_final[columnas_ordenadas + columnas_percentiles]

    archivo_salida = Path(argumentos.output)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    perfil_final.to_csv(archivo_salida, index=False, sep=";", encoding="utf-8-sig")
    print(f"Archivo generado: {archivo_salida}")


if __name__ == "__main__":
    main()
