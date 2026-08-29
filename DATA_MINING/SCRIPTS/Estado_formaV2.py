import argparse
import importlib
import os
from pathlib import Path

import numpy as np
import pandas as pd


TEMPORADA_TARGET = 2025
NUM_PARTIDOS = 5
BONUS_TOP6 = 0.5
PONDERACION_TEMPORAL = 0.85

UMBRAL_POSITIVO = 5.5
UMBRAL_CRITICO = 3.2
FACTOR_NORMALIZACION = 3.0

RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_SALIDAS = RUTA_RAIZ / "DATA_MINING" / "DSA_DM"
RUTA_SALIDA = RUTA_SALIDAS / "ESTADO_FORMA_EQUIPOS_2025.csv"
RUTA_SALIDA_TODAS = RUTA_SALIDAS / "ESTADO_FORMA_EQUIPOS_TODAS_TEMPORADAS.csv"


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calcula estado de forma leyendo datos desde PostgreSQL"
    )
    parser.add_argument("--db-host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("PGPORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("PGDATABASE", "TFG_BDLaLiga"))
    parser.add_argument("--db-user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("PGPASSWORD", "betico18"))
    parser.add_argument("--output", default=str(RUTA_SALIDA))
    parser.add_argument("--output-todas", default=str(RUTA_SALIDA_TODAS))
    return parser.parse_args()


def leer_tabla(conexion, consulta: str) -> pd.DataFrame:
    return pd.read_sql_query(consulta, conexion)


def cargar_datos(argumentos: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    print("Cargando datos...")
    try:
        psycopg2 = importlib.import_module("psycopg2")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Falta psycopg2 en el entorno actual. Instala: pip install psycopg2-binary"
        ) from exc

    conexion = psycopg2.connect(
        host=argumentos.db_host,
        port=argumentos.db_port,
        dbname=argumentos.db_name,
        user=argumentos.db_user,
        password=argumentos.db_password,
    )

    try:
        partidos = leer_tabla(
            conexion,
            """
            SELECT
                id_partido,
                temporada,
                id_local,
                id_visitante,
                goles_local,
                goles_visitante,
                status
            FROM public.dim_partidos
            """,
        )
        estadisticas = leer_tabla(
            conexion,
            """
            SELECT
                id_partido,
                id_equipo,
                goles_esperados
            FROM public.h_equipo_partido
            """,
        )
        clasificacion = leer_tabla(
            conexion,
            """
            SELECT
                t.id_equipo,
                e.nombre_equipo,
                t.temporada,
                t.jornada,
                t.posicion
            FROM public.h_equipo_temporada t
            LEFT JOIN public.dim_equipo e ON e.id_equipo = t.id_equipo
            """,
        )
    finally:
        conexion.close()

    for datos in [partidos, estadisticas, clasificacion]:
        datos.columns = datos.columns.str.strip()

    return partidos, estadisticas, clasificacion


def obtener_info_equipos_temporada(
    clasificacion: pd.DataFrame, temporada: int
) -> tuple[pd.DataFrame, list[int]]:
    datos_temporada = clasificacion[clasificacion["temporada"] == temporada].copy()

    if not datos_temporada.empty and "jornada" in datos_temporada.columns:
        indices = datos_temporada.groupby("id_equipo")["jornada"].idxmax()
        datos_temporada = datos_temporada.loc[indices].copy()

    if datos_temporada.empty:
        print(f"Advertencia: no hay datos para la temporada {temporada}")
        return pd.DataFrame(), []

    equipos_top6 = datos_temporada.nsmallest(6, "posicion")["id_equipo"].tolist()
    return datos_temporada, equipos_top6


def calcular_puntos_base(goles_favor: float, goles_contra: float) -> int:
    if goles_favor > goles_contra:
        return 3
    if goles_favor == goles_contra:
        return 1
    return 0


def aplicar_ajustes_xg(
    puntos: float,
    goles_favor: float,
    goles_contra: float,
    xg_propio: float,
    xg_rival: float,
) -> float:
    ajuste = 0

    if puntos == 0 and xg_propio > (xg_rival + 0.5):
        ajuste = 0.6
    elif puntos == 3 and xg_propio < xg_rival - 0.7:
        ajuste = -0.1
    elif puntos == 1 and xg_propio < (xg_rival - 0.3):
        ajuste = 0.2

    return puntos + ajuste


def calcular_bonus_rival(id_rival: int, equipos_top6: list[int]) -> float:
    return BONUS_TOP6 if id_rival in equipos_top6 else 0


def procesar_partido(
    partido: pd.Series,
    id_equipo: int,
    id_rival: int,
    estadisticas_rival: pd.DataFrame,
    equipos_top6: list[int],
) -> float:
    es_local = partido["id_local"] == id_equipo

    goles_favor = partido["goles_local"] if es_local else partido["goles_visitante"]
    goles_contra = partido["goles_visitante"] if es_local else partido["goles_local"]

    puntos = calcular_puntos_base(goles_favor, goles_contra)

    if "goles_esperados" in partido and not estadisticas_rival.empty:
        try:
            xg_propio = float(partido["goles_esperados"])
            xg_rival = float(estadisticas_rival.iloc[0]["goles_esperados"])
            puntos = aplicar_ajustes_xg(puntos, goles_favor, goles_contra, xg_propio, xg_rival)
        except (ValueError, KeyError):
            pass

    return puntos + calcular_bonus_rival(id_rival, equipos_top6)


def calcular_forma_equipo(
    id_equipo: int,
    equipos_temporada: pd.DataFrame,
    estadisticas: pd.DataFrame,
    partidos: pd.DataFrame,
    equipos_top6: list[int],
    temporada: int = TEMPORADA_TARGET,
) -> dict | None:
    equipo_info = equipos_temporada[equipos_temporada["id_equipo"] == id_equipo]
    if equipo_info.empty:
        return None

    nombre_equipo = equipo_info["nombre_equipo"].iloc[0]
    partidos_temporada = partidos[partidos["temporada"] == temporada].copy()
    ids_partidos_temporada = set(partidos_temporada["id_partido"])
    estadisticas_temporada = estadisticas[
        estadisticas["id_partido"].isin(ids_partidos_temporada)
    ].copy()
    estadisticas_equipo = estadisticas_temporada[estadisticas_temporada["id_equipo"] == id_equipo]
    partidos_equipo = estadisticas_equipo.merge(
        partidos_temporada,
        on="id_partido",
        how="inner",
    )

    if partidos_equipo.empty:
        print(f"{nombre_equipo}: sin partidos en {temporada}")
        return None

    ultimos_n = partidos_equipo.sort_values(by="id_partido", ascending=False).head(NUM_PARTIDOS)
    ultimos_n = ultimos_n.sort_values(by="id_partido", ascending=True)

    puntos_ponderados = []
    pesos = []

    for indice, (_, partido) in enumerate(ultimos_n.iterrows()):
        peso = PONDERACION_TEMPORAL ** (NUM_PARTIDOS - indice - 1)
        pesos.append(peso)

        id_rival = partido["id_visitante"] if partido["id_local"] == id_equipo else partido["id_local"]
        estadisticas_rival = estadisticas_temporada[
            (estadisticas_temporada["id_partido"] == partido["id_partido"])
            & (estadisticas_temporada["id_equipo"] != id_equipo)
        ]

        puntos = procesar_partido(partido, id_equipo, id_rival, estadisticas_rival, equipos_top6)
        puntos_ponderados.append(puntos * peso)

    nota_media = np.sum(puntos_ponderados) / np.sum(pesos)
    variabilidad = np.std(puntos_ponderados)
    nota_final = min(10, (nota_media / FACTOR_NORMALIZACION) * 10)

    if nota_final >= UMBRAL_POSITIVO:
        estado = "Positivo"
    elif nota_final >= UMBRAL_CRITICO:
        estado = "Estable"
    else:
        estado = "Critico"

    return {
        "id_equipo": id_equipo,
        "nombre_equipo": nombre_equipo,
        "puntuacion_forma": round(nota_final, 2),
        "estado": estado,
        "tendencia": round(nota_media, 2),
        "variabilidad": round(variabilidad, 2),
    }


def calcular_forma_temporada(
    temporada: int,
    partidos: pd.DataFrame,
    estadisticas: pd.DataFrame,
    clasificacion: pd.DataFrame,
    incluir_temporada: bool = False,
) -> pd.DataFrame:
    equipos_temporada, equipos_top6 = obtener_info_equipos_temporada(clasificacion, temporada)
    if equipos_temporada.empty:
        return pd.DataFrame()

    resultados = []
    for id_equipo in equipos_temporada["id_equipo"].unique():
        resultado = calcular_forma_equipo(
            id_equipo,
            equipos_temporada,
            estadisticas,
            partidos,
            equipos_top6,
            temporada,
        )
        if resultado:
            if incluir_temporada:
                resultado = {"temporada": temporada, **resultado}
            resultados.append(resultado)

    if not resultados:
        return pd.DataFrame()

    columnas_orden = ["puntuacion_forma"]
    ascending = [False]
    if incluir_temporada:
        columnas_orden = ["temporada", "puntuacion_forma"]
        ascending = [True, False]

    return pd.DataFrame(resultados).sort_values(columnas_orden, ascending=ascending)


def obtener_temporadas_disponibles(clasificacion: pd.DataFrame) -> list[int]:
    temporadas = pd.to_numeric(clasificacion["temporada"], errors="coerce").dropna()
    return sorted(temporadas.astype(int).unique().tolist())


def main() -> None:
    argumentos = leer_argumentos()
    partidos, estadisticas, clasificacion = cargar_datos(argumentos)

    salida = calcular_forma_temporada(
        TEMPORADA_TARGET,
        partidos,
        estadisticas,
        clasificacion,
    )
    if salida.empty:
        raise ValueError(f"No hay datos disponibles para la temporada {TEMPORADA_TARGET}")

    archivo_salida = Path(argumentos.output)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(archivo_salida, index=False, sep=";")

    print(f"Analisis completado. Equipos procesados: {len(salida)}")
    print(f"Archivo generado: {archivo_salida}")
    print(salida.to_string(index=False))

    temporadas = obtener_temporadas_disponibles(clasificacion)
    resultados_temporadas = [
        calcular_forma_temporada(
            temporada,
            partidos,
            estadisticas,
            clasificacion,
            incluir_temporada=True,
        )
        for temporada in temporadas
    ]
    resultados_temporadas = [
        resultado for resultado in resultados_temporadas if not resultado.empty
    ]

    if resultados_temporadas:
        salida_todas = pd.concat(resultados_temporadas, ignore_index=True)
    else:
        salida_todas = pd.DataFrame(
            columns=[
                "temporada",
                "id_equipo",
                "nombre_equipo",
                "puntuacion_forma",
                "estado",
                "tendencia",
                "variabilidad",
            ]
        )

    archivo_salida_todas = Path(argumentos.output_todas)
    archivo_salida_todas.parent.mkdir(parents=True, exist_ok=True)
    salida_todas.to_csv(archivo_salida_todas, index=False, sep=";")
    print(f"Archivo historico generado: {archivo_salida_todas}")


if __name__ == "__main__":
    main()
