import argparse
import os
from pathlib import Path

import pandas as pd
import psycopg2


UMBRAL_PCT = 0.1

RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_SALIDAS = RUTA_RAIZ / "DATA_MINING" / "DSA_DM"
RUTA_SALIDA = RUTA_SALIDAS / "NECESIDADES_REFUERZO_EQUIPO.csv"
COLUMNAS_CSV = ["id_equipo", "temporada", "necesidad", "motivo"]


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera NECESIDADES_REFUERZO_EQUIPO.csv leyendo desde PostgreSQL"
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


def cargar_datos(argumentos: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    conexion = psycopg2.connect(
        host=argumentos.db_host,
        port=argumentos.db_port,
        dbname=argumentos.db_name,
        user=argumentos.db_user,
        password=argumentos.db_password,
    )

    try:
        jugadores_temporada = leer_tabla(
            conexion,
            """
            SELECT
                id_jugador,
                id_equipo,
                temporada,
                posicion,
                minutos,
                asistencias,
                pases_totales,
                pases_clave,
                precision_pases,
                regates_intentados,
                regates_exito,
                regateado,
                faltas_cometidas,
                intercepciones,
                entradas,
                bloqueos,
                paradas,
                goles_concedidos
            FROM public.h_jugador_temporada
            """,
        )
        equipos_jornada = leer_tabla(
            conexion,
            """
            SELECT
                id_equipo,
                temporada,
                jornada,
                gf,
                gc
            FROM public.h_equipo_temporada
            """,
        )
    finally:
        conexion.close()

    jugadores_temporada.columns = jugadores_temporada.columns.str.strip()
    equipos_jornada.columns = equipos_jornada.columns.str.strip()
    return jugadores_temporada, equipos_jornada


def validar_columnas(datos: pd.DataFrame, columnas_obligatorias: set[str], nombre: str) -> None:
    columnas_faltantes = columnas_obligatorias - set(datos.columns)
    if columnas_faltantes:
        raise ValueError(f"Faltan columnas en {nombre}: {sorted(columnas_faltantes)}")


def calcular_por_90(valor: float, minutos: float) -> float:
    return valor / minutos * 90.0 if minutos > 0 else 0.0


def es_bajo(valor: float, media: float, pct: float) -> bool:
    return valor <= (1 - pct) * media


def es_alto(valor: float, media: float, pct: float) -> bool:
    return valor >= (1 + pct) * media


def preparar_metricas_posicion(jugadores_temporada: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    columnas_numericas = [
        "minutos",
        "asistencias",
        "pases_totales",
        "pases_clave",
        "regates_intentados",
        "regates_exito",
        "regateado",
        "faltas_cometidas",
        "intercepciones",
        "entradas",
        "bloqueos",
        "paradas",
        "goles_concedidos",
    ]

    posicion_agregada = (
        jugadores_temporada.groupby(["temporada", "id_equipo", "posicion"], as_index=False)[columnas_numericas]
        .sum()
    )

    filas = []
    for _, fila in posicion_agregada.iterrows():
        minutos = fila["minutos"]
        pases_totales = fila["pases_totales"]
        regates_intentados = fila["regates_intentados"]
        regates_exito = fila["regates_exito"]

        filas.append(
            {
                "temporada": fila["temporada"],
                "id_equipo": fila["id_equipo"],
                "posicion": fila["posicion"],
                "minutos": minutos,
                "asistencias_p90": calcular_por_90(fila["asistencias"], minutos),
                "pases_totales_p90": calcular_por_90(pases_totales, minutos),
                "pases_clave_p90": calcular_por_90(fila["pases_clave"], minutos),
                "faltas_cometidas_p90": calcular_por_90(fila["faltas_cometidas"], minutos),
                "intercepciones_p90": calcular_por_90(fila["intercepciones"], minutos),
                "entradas_p90": calcular_por_90(fila["entradas"], minutos),
                "bloqueos_p90": calcular_por_90(fila["bloqueos"], minutos),
                "regateado_p90": calcular_por_90(fila["regateado"], minutos),
                "paradas_p90": calcular_por_90(fila["paradas"], minutos),
                "goles_concedidos_p90": calcular_por_90(fila["goles_concedidos"], minutos),
                "regates_exito_rate": (regates_exito / regates_intentados) if regates_intentados > 0 else 0.0,
            }
        )

    metricas_posicion = pd.DataFrame(filas)

    precision_ponderada = (
        jugadores_temporada.assign(
            pases_x_precision=lambda datos: datos["pases_totales"] * datos["precision_pases"]
        )
        .groupby(["temporada", "id_equipo", "posicion"], as_index=False)
        .agg(pases_totales=("pases_totales", "sum"), pases_x_precision=("pases_x_precision", "sum"))
    )
    precision_ponderada["precision_pases"] = precision_ponderada.apply(
        lambda fila: fila["pases_x_precision"] / fila["pases_totales"]
        if fila["pases_totales"] > 0
        else 0.0,
        axis=1,
    )

    metricas_posicion = metricas_posicion.merge(
        precision_ponderada[["temporada", "id_equipo", "posicion", "precision_pases"]],
        on=["temporada", "id_equipo", "posicion"],
        how="left",
    )

    referencia_liga = (
        metricas_posicion.groupby(["temporada", "posicion"], as_index=False)
        .agg(
            asistencias_p90_media=("asistencias_p90", "mean"),
            pases_totales_p90_media=("pases_totales_p90", "mean"),
            pases_clave_p90_media=("pases_clave_p90", "mean"),
            precision_pases_media=("precision_pases", "mean"),
            faltas_cometidas_p90_media=("faltas_cometidas_p90", "mean"),
            intercepciones_p90_media=("intercepciones_p90", "mean"),
            entradas_p90_media=("entradas_p90", "mean"),
            bloqueos_p90_media=("bloqueos_p90", "mean"),
            regateado_p90_media=("regateado_p90", "mean"),
            paradas_p90_media=("paradas_p90", "mean"),
            goles_concedidos_p90_media=("goles_concedidos_p90", "mean"),
            regates_exito_rate_media=("regates_exito_rate", "mean"),
        )
    )

    return metricas_posicion, referencia_liga


def obtener_equipos_temporada(equipos_jornada: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    equipos_jornada = equipos_jornada.sort_values(["temporada", "id_equipo", "jornada"])
    equipos_temporada = (
        equipos_jornada.groupby(["temporada", "id_equipo"], as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )
    referencia_goles = (
        equipos_temporada.groupby("temporada", as_index=False)
        .agg(gf_media=("gf", "mean"), gc_media=("gc", "mean"))
    )
    return equipos_temporada, referencia_goles


def buscar_referencia_goles(referencia_goles: pd.DataFrame, temporada: int) -> tuple[float, float]:
    referencia_temporada = referencia_goles[referencia_goles["temporada"] == temporada]
    return (
        referencia_temporada["gf_media"].iloc[0],
        referencia_temporada["gc_media"].iloc[0],
    )


def obtener_primera_fila(datos: pd.DataFrame, temporada: int, posicion: str) -> pd.Series | None:
    filas = datos[(datos["temporada"] == temporada) & (datos["posicion"] == posicion)]
    if filas.empty:
        return None
    return filas.iloc[0]


def generar_necesidades(
    jugadores_temporada: pd.DataFrame, equipos_jornada: pd.DataFrame
) -> pd.DataFrame:
    validar_columnas(
        jugadores_temporada,
        {
            "id_jugador",
            "id_equipo",
            "temporada",
            "posicion",
            "minutos",
            "asistencias",
            "pases_totales",
            "pases_clave",
            "precision_pases",
            "regates_intentados",
            "regates_exito",
            "regateado",
            "faltas_cometidas",
            "intercepciones",
            "entradas",
            "bloqueos",
            "paradas",
            "goles_concedidos",
        },
        "h_jugador_temporada",
    )
    validar_columnas(
        equipos_jornada,
        {"id_equipo", "temporada", "jornada", "gf", "gc"},
        "h_equipo_temporada",
    )

    equipos_temporada, referencia_goles = obtener_equipos_temporada(equipos_jornada)
    metricas_posicion, referencia_liga = preparar_metricas_posicion(jugadores_temporada)

    resultados = []

    for _, equipo in equipos_temporada.iterrows():
        temporada = equipo["temporada"]
        id_equipo = equipo["id_equipo"]
        gf = equipo["gf"]
        gc = equipo["gc"]
        gf_media, gc_media = buscar_referencia_goles(referencia_goles, temporada)

        datos_posicion = metricas_posicion[
            (metricas_posicion["temporada"] == temporada)
            & (metricas_posicion["id_equipo"] == id_equipo)
        ]

        necesidades = []

        if es_bajo(gf, gf_media, UMBRAL_PCT):
            necesidades.append(("Delantero", "Pocos goles respecto a la media de la liga"))

        delanteros = datos_posicion[datos_posicion["posicion"] == "Delantero"]
        if not delanteros.empty:
            delantero = delanteros.iloc[0]
            referencia = obtener_primera_fila(referencia_liga, temporada, "Delantero")
            if (
                referencia is not None
                and es_bajo(delantero["regates_exito_rate"], referencia["regates_exito_rate_media"], UMBRAL_PCT)
                and es_bajo(delantero["asistencias_p90"], referencia["asistencias_p90_media"], UMBRAL_PCT)
            ):
                necesidades.append(
                    ("Extremo", "Delanteros con regate y asistencias por debajo de la media")
                )

        mediocentros = datos_posicion[datos_posicion["posicion"] == "Mediocentro"]
        if not mediocentros.empty:
            mediocentro = mediocentros.iloc[0]
            referencia = obtener_primera_fila(referencia_liga, temporada, "Mediocentro")
            if referencia is not None:
                if (
                    es_bajo(mediocentro["precision_pases"], referencia["precision_pases_media"], UMBRAL_PCT)
                    and es_bajo(mediocentro["pases_clave_p90"], referencia["pases_clave_p90_media"], UMBRAL_PCT)
                    and es_bajo(mediocentro["asistencias_p90"], referencia["asistencias_p90_media"], UMBRAL_PCT)
                ):
                    necesidades.append(
                        ("Medio ofensivo", "Mediocentros con pases clave y asistencias bajas")
                    )

                if (
                    es_alto(mediocentro["faltas_cometidas_p90"], referencia["faltas_cometidas_p90_media"], UMBRAL_PCT)
                    and es_bajo(mediocentro["precision_pases"], referencia["precision_pases_media"], UMBRAL_PCT)
                    and es_bajo(mediocentro["intercepciones_p90"], referencia["intercepciones_p90_media"], UMBRAL_PCT)
                ):
                    necesidades.append(
                        ("Pivote defensivo", "Mediocentros con muchas faltas y baja recuperacion")
                    )

        defensas = datos_posicion[datos_posicion["posicion"] == "Defensa"]
        if not defensas.empty:
            defensa = defensas.iloc[0]
            referencia = obtener_primera_fila(referencia_liga, temporada, "Defensa")
            if referencia is not None:
                if (
                    es_bajo(defensa["asistencias_p90"], referencia["asistencias_p90_media"], UMBRAL_PCT)
                    and es_alto(defensa["regateado_p90"], referencia["regateado_p90_media"], UMBRAL_PCT)
                ):
                    necesidades.append(
                        ("Laterales", "Defensas con pocas asistencias y muchos regateados")
                    )

                if (
                    es_alto(gc, gc_media, UMBRAL_PCT)
                    and es_bajo(defensa["entradas_p90"], referencia["entradas_p90_media"], UMBRAL_PCT)
                    and es_bajo(defensa["bloqueos_p90"], referencia["bloqueos_p90_media"], UMBRAL_PCT)
                    and es_bajo(defensa["intercepciones_p90"], referencia["intercepciones_p90_media"], UMBRAL_PCT)
                ):
                    necesidades.append(
                        ("Central", "Defensas con bajos aportes defensivos y muchos goles encajados")
                    )

        porteros = datos_posicion[datos_posicion["posicion"] == "Portero"]
        if not porteros.empty:
            portero = porteros.iloc[0]
            referencia = obtener_primera_fila(referencia_liga, temporada, "Portero")
            if (
                referencia is not None
                and es_bajo(portero["paradas_p90"], referencia["paradas_p90_media"], UMBRAL_PCT)
                and es_alto(portero["goles_concedidos_p90"], referencia["goles_concedidos_p90_media"], UMBRAL_PCT)
            ):
                necesidades.append(("Portero", "Porteros con pocas paradas y muchos goles encajados"))

        if not necesidades:
            necesidades.append(("Sin necesidad clara", "Sin senales negativas relevantes"))

        for necesidad, motivo in necesidades:
            resultados.append(
                {
                    "id_equipo": id_equipo,
                    "temporada": temporada,
                    "necesidad": necesidad,
                    "motivo": motivo,
                }
            )

    return pd.DataFrame(resultados, columns=COLUMNAS_CSV)


def main() -> None:
    argumentos = leer_argumentos()
    jugadores_temporada, equipos_jornada = cargar_datos(argumentos)
    resultados = generar_necesidades(jugadores_temporada, equipos_jornada)

    archivo_salida = Path(argumentos.output)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    resultados.to_csv(archivo_salida, index=False, sep=";", encoding="utf-8-sig")

    print(f"Archivo generado: {archivo_salida}")


if __name__ == "__main__":
    main()
