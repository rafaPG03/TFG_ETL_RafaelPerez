import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity as similitud_coseno
from sklearn.preprocessing import MinMaxScaler as EscaladorMinMax
from sklearn.preprocessing import StandardScaler as EscaladorEstandar


RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_DSA = RUTA_RAIZ / "ETL" / "DSA"
RUTA_DM = RUTA_RAIZ / "DATA_MINING" / "DSA_DM"

ARCHIVO_NECESIDADES = RUTA_DM / "NECESIDADES_REFUERZO_EQUIPO.csv"
ARCHIVO_PERFILES = RUTA_DM / "perfil_estadistico_jugadores.csv"
ARCHIVO_GRUPOS_KMEANS = RUTA_DM / "jugadores_similares_top5_por_temporada.csv"
ARCHIVO_JUGADOR_TEMPORADA = RUTA_DSA / "h_jugador_temporada.csv"
ARCHIVO_EQUIPO_TEMPORADA = RUTA_DSA / "h_equipo_temporada.csv"
ARCHIVO_JUGADORES = RUTA_DSA / "dim_jugadores.csv"
ARCHIVO_SALIDA = RUTA_DM / "fichajes_recomendados_refuerzos.csv"

ATRIBUTOS_PERFIL = ["ataque", "creacion", "defensa", "porteros", "duelos", "regates"]
COLUMNAS_SALIDA = [
    "id_equipo",
    "nombre_equipo",
    "necesidad",
    "id_jugador",
    "nombre_jugador",
    "id_equipo_actual",
    "equipo_actual",
    "score_recomendacion",
    "motivo",
]

PESOS_SCORE = {
    "similitud": 0.40,
    "nota_media": 0.25,
    "estado_forma": 0.15,
    "edad": 0.10,
    "experiencia": 0.10,
}

MIN_MINUTOS = 600
MAX_RECOMENDACIONES = 3
EDAD_IDEAL_MIN = 20
EDAD_IDEAL_MAX = 27
EDAD_MAX_PROMESA = 23
NOTA_MIN_PROMESA = 6.70

TRAMOS_MERCADO = [
    (1, 3),
    (4, 7),
    (8, 14),
    (15, 20),
]

PAREJAS_FICHAJE_BLOQUEADAS = {
    frozenset({529, 541}),  # Barcelona - Real Madrid
    frozenset({541, 530}),  # Real Madrid - Atletico Madrid
    frozenset({548, 531}),  # Real Sociedad - Athletic Club
    frozenset({536, 543}),  # Sevilla - Real Betis
}

MAPA_NECESIDAD_POSICION = {
    "Delantero": "Delantero",
    "Extremo": "Delantero",
    "Medio ofensivo": "Mediocentro",
    "Pivote defensivo": "Mediocentro",
    "Laterales": "Defensa",
    "Central": "Defensa",
    "Portero": "Portero",
}

ETIQUETAS_POSICION = {
    "Delantero": "Delantero",
    "Mediocentro": "Mediocentro",
    "Defensa": "Defensa",
    "Portero": "Portero",
}

PESOS_ATRIBUTOS_POR_NECESIDAD = {
    "Delantero": {"ataque": 0.60, "creacion": 0.15, "regates": 0.15, "duelos": 0.10},
    "Extremo": {"regates": 0.45, "creacion": 0.30, "ataque": 0.25},
    "Medio ofensivo": {"creacion": 0.55, "regates": 0.20, "ataque": 0.15, "duelos": 0.10},
    "Pivote defensivo": {"defensa": 0.45, "duelos": 0.35, "creacion": 0.20},
    "Laterales": {"defensa": 0.35, "creacion": 0.25, "regates": 0.20, "duelos": 0.20},
    "Central": {"defensa": 0.55, "duelos": 0.35, "creacion": 0.10},
    "Portero": {"porteros": 0.80, "duelos": 0.20},
}


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera recomendaciones deterministas de fichajes por necesidad de plantilla"
    )
    parser.add_argument("--temporada", type=int, default=None, help="Temporada a procesar")
    parser.add_argument("--archivo-necesidades", default=str(ARCHIVO_NECESIDADES))
    parser.add_argument("--archivo-perfiles", default=str(ARCHIVO_PERFILES))
    parser.add_argument("--archivo-grupos-kmeans", default=str(ARCHIVO_GRUPOS_KMEANS))
    parser.add_argument(
        "--archivo-jugador-temporada",
        default=str(ARCHIVO_JUGADOR_TEMPORADA),
    )
    parser.add_argument(
        "--archivo-equipo-temporada",
        default=str(ARCHIVO_EQUIPO_TEMPORADA),
    )
    parser.add_argument("--archivo-jugadores", default=str(ARCHIVO_JUGADORES))
    parser.add_argument("--salida", default=str(ARCHIVO_SALIDA))
    return parser.parse_args()


def leer_csv(ruta: Path) -> pd.DataFrame:
    datos = pd.read_csv(ruta, sep=";", encoding="utf-8-sig")
    datos.columns = datos.columns.str.strip()
    return datos


def normalizar_posicion(posicion: str) -> str:
    valor = str(posicion).strip()
    return {"Forward": "Delantero", "Goalkeeper": "Portero"}.get(valor, valor)


def validar_columnas(datos: pd.DataFrame, columnas_obligatorias: list[str], nombre: str) -> None:
    columnas_faltantes = [columna for columna in columnas_obligatorias if columna not in datos.columns]
    if columnas_faltantes:
        raise ValueError(f"Faltan columnas en {nombre}: {columnas_faltantes}")


def obtener_temporada_comun_mas_reciente(*tablas: pd.DataFrame) -> int:
    temporadas_comunes = None
    for tabla in tablas:
        temporadas_tabla = set(
            pd.to_numeric(tabla["temporada"], errors="coerce").dropna().astype(int)
        )
        temporadas_comunes = (
            temporadas_tabla
            if temporadas_comunes is None
            else temporadas_comunes & temporadas_tabla
        )
    if not temporadas_comunes:
        raise ValueError("No existe una temporada comun entre las tablas de entrada")
    return max(temporadas_comunes)


def cargar_estado_forma(temporada: int) -> pd.DataFrame:
    archivos_candidatos = [
        RUTA_DM / f"ESTADO_FORMA_JUGADORES_{temporada}.csv",
        RUTA_DM / "ESTADO_FORMA_JUGADORES_2025.csv",
    ]
    for ruta in archivos_candidatos:
        if ruta.exists():
            estado_forma = leer_csv(ruta)
            validar_columnas(estado_forma, ["id_jugador", "score_reciente"], ruta.name)
            return estado_forma[["id_jugador", "score_reciente"]].copy()
    return pd.DataFrame(columns=["id_jugador", "score_reciente"])


def obtener_filas_principales_por_jugador(jugadores_temporada: pd.DataFrame) -> pd.DataFrame:
    jugadores_temporada = jugadores_temporada.copy()
    jugadores_temporada["minutos"] = pd.to_numeric(
        jugadores_temporada["minutos"], errors="coerce"
    ).fillna(0)
    jugadores_temporada["posicion"] = jugadores_temporada["posicion"].apply(normalizar_posicion)
    return (
        jugadores_temporada.sort_values(
            ["temporada", "id_jugador", "minutos", "id_equipo"],
            ascending=[True, True, False, True],
        )
        .drop_duplicates(["temporada", "id_jugador"])
        .reset_index(drop=True)
    )


def preparar_datos(argumentos: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    necesidades = leer_csv(Path(argumentos.archivo_necesidades))
    perfiles = leer_csv(Path(argumentos.archivo_perfiles))
    grupos_kmeans = leer_csv(Path(argumentos.archivo_grupos_kmeans))
    jugadores_temporada = leer_csv(Path(argumentos.archivo_jugador_temporada))
    equipos_temporada = leer_csv(Path(argumentos.archivo_equipo_temporada))
    jugadores = leer_csv(Path(argumentos.archivo_jugadores))

    validar_columnas(necesidades, ["id_equipo", "temporada", "necesidad"], "necesidades")
    validar_columnas(perfiles, ["id_jugador", "temporada", "nombre", *ATRIBUTOS_PERFIL], "perfiles")
    validar_columnas(grupos_kmeans, ["id_jugador", "temporada", "posicion", "cluster"], "kmeans")
    validar_columnas(
        jugadores_temporada,
        ["id_jugador", "id_equipo", "temporada", "posicion", "partidos", "minutos", "nota_media"],
        "h_jugador_temporada",
    )
    validar_columnas(
        equipos_temporada,
        ["id_equipo", "temporada", "posicion", "nombre_equipo"],
        "h_equipo_temporada",
    )
    validar_columnas(jugadores, ["id_jugador", "edad"], "dim_jugadores")

    for tabla in [necesidades, perfiles, grupos_kmeans, jugadores_temporada, equipos_temporada]:
        tabla["temporada"] = pd.to_numeric(tabla["temporada"], errors="coerce").astype("Int64")

    temporada = argumentos.temporada or obtener_temporada_comun_mas_reciente(
        necesidades, perfiles, grupos_kmeans, jugadores_temporada, equipos_temporada
    )

    necesidades = necesidades[
        (necesidades["temporada"] == temporada)
        & (necesidades["necesidad"] != "Sin necesidad clara")
    ].copy()
    equipos_temporada = equipos_temporada[equipos_temporada["temporada"] == temporada].copy()
    perfiles = perfiles[perfiles["temporada"] == temporada].copy()
    grupos_kmeans = grupos_kmeans[grupos_kmeans["temporada"] == temporada].copy()
    jugadores_temporada = obtener_filas_principales_por_jugador(
        jugadores_temporada[jugadores_temporada["temporada"] == temporada]
    )

    estado_forma = cargar_estado_forma(temporada)
    candidatos = (
        jugadores_temporada.merge(perfiles, on=["id_jugador", "temporada"], how="inner")
        .merge(grupos_kmeans[["id_jugador", "temporada", "cluster"]], on=["id_jugador", "temporada"], how="inner")
        .merge(jugadores[["id_jugador", "edad"]], on="id_jugador", how="left")
        .merge(estado_forma, on="id_jugador", how="left")
        .merge(
            equipos_temporada[["id_equipo", "nombre_equipo", "posicion"]].rename(
                columns={
                    "id_equipo": "id_equipo_actual",
                    "nombre_equipo": "equipo_actual",
                    "posicion": "posicion_equipo_actual",
                }
            ),
            left_on="id_equipo",
            right_on="id_equipo_actual",
            how="left",
        )
    )
    candidatos["nombre_jugador"] = candidatos["nombre"].fillna(
        candidatos["id_jugador"].astype(str)
    )

    columnas_numericas = [
        "partidos",
        "minutos",
        "nota_media",
        "edad",
        "score_reciente",
        "posicion_equipo_actual",
        *ATRIBUTOS_PERFIL,
    ]
    for columna in columnas_numericas:
        candidatos[columna] = pd.to_numeric(candidatos[columna], errors="coerce")
    candidatos["posicion"] = candidatos["posicion"].apply(normalizar_posicion)

    equipos = equipos_temporada[["id_equipo", "nombre_equipo", "posicion"]].copy()
    equipos["posicion"] = pd.to_numeric(equipos["posicion"], errors="coerce")
    necesidades = necesidades.merge(equipos, on="id_equipo", how="left")
    necesidades = consolidar_necesidades_por_posicion(necesidades)
    return necesidades, candidatos, temporada


def consolidar_necesidades_por_posicion(necesidades: pd.DataFrame) -> pd.DataFrame:
    necesidades = necesidades.copy()
    necesidades["posicion_requerida"] = necesidades["necesidad"].map(MAPA_NECESIDAD_POSICION)
    necesidades = necesidades.dropna(subset=["posicion_requerida"])
    if necesidades.empty:
        return necesidades

    necesidades_agrupadas = (
        necesidades.groupby(
            ["id_equipo", "nombre_equipo", "posicion", "posicion_requerida"],
            as_index=False,
            dropna=False,
        )
        .agg(necesidades_origen=("necesidad", lambda valores: sorted(set(valores))))
    )
    necesidades_agrupadas["necesidad"] = necesidades_agrupadas["posicion_requerida"].map(
        ETIQUETAS_POSICION
    )
    return necesidades_agrupadas


def obtener_tramo_mercado(posicion: int) -> int | None:
    for indice, (inicio_tramo, fin_tramo) in enumerate(TRAMOS_MERCADO):
        if inicio_tramo <= posicion <= fin_tramo:
            return indice
    return None


def es_pareja_fichaje_bloqueada(id_equipo: int, id_equipo_candidato: int) -> bool:
    return frozenset({id_equipo, id_equipo_candidato}) in PAREJAS_FICHAJE_BLOQUEADAS


def mercado_permite_fichaje(
    id_equipo: int,
    posicion_equipo: int,
    id_equipo_candidato: int,
    posicion_equipo_candidato: int,
    edad_candidato: float,
    nota_candidato: float,
) -> bool:
    if pd.isna(id_equipo_candidato) or pd.isna(posicion_equipo_candidato):
        return False
    if es_pareja_fichaje_bloqueada(int(id_equipo), int(id_equipo_candidato)):
        return False

    tramo_equipo = obtener_tramo_mercado(int(posicion_equipo))
    tramo_candidato = obtener_tramo_mercado(int(posicion_equipo_candidato))
    if tramo_equipo is None or tramo_candidato is None:
        return False
    return tramo_candidato >= tramo_equipo


def calcular_fuerza_necesidad(datos: pd.DataFrame, necesidades: str | list[str]) -> pd.Series:
    lista_necesidades = [necesidades] if isinstance(necesidades, str) else necesidades
    puntuaciones = []
    for necesidad in lista_necesidades:
        pesos_atributos = PESOS_ATRIBUTOS_POR_NECESIDAD[necesidad]
        puntuacion = pd.Series(0.0, index=datos.index)
        for atributo, peso in pesos_atributos.items():
            puntuacion = puntuacion + datos[atributo].fillna(0) * peso
        puntuaciones.append(puntuacion)
    return pd.concat(puntuaciones, axis=1).mean(axis=1)


def seleccionar_cluster_objetivo(
    candidatos_posicion: pd.DataFrame, necesidades: str | list[str]
) -> int:
    puntuacion_cluster = (
        candidatos_posicion.assign(
            _fuerza_necesidad=calcular_fuerza_necesidad(candidatos_posicion, necesidades)
        )
        .groupby("cluster", as_index=False)
        .agg(puntuacion=("_fuerza_necesidad", "mean"), jugadores=("id_jugador", "count"))
        .sort_values(["puntuacion", "jugadores", "cluster"], ascending=[False, False, True])
    )
    return int(puntuacion_cluster.iloc[0]["cluster"])


def construir_perfil_objetivo(
    candidatos_posicion: pd.DataFrame, necesidades: str | list[str], cluster_objetivo: int
) -> np.ndarray:
    candidatos_cluster = candidatos_posicion[
        candidatos_posicion["cluster"] == cluster_objetivo
    ].copy()
    candidatos_cluster["_fuerza_necesidad"] = calcular_fuerza_necesidad(
        candidatos_cluster, necesidades
    )
    umbral_elite = candidatos_cluster["_fuerza_necesidad"].quantile(0.75)
    candidatos_elite = candidatos_cluster[candidatos_cluster["_fuerza_necesidad"] >= umbral_elite]
    if candidatos_elite.empty:
        candidatos_elite = candidatos_cluster
    return candidatos_elite[ATRIBUTOS_PERFIL].mean(numeric_only=True).fillna(0).to_numpy(dtype=float)


def escalar_entre_cero_y_uno(valores: pd.Series) -> pd.Series:
    valores = pd.to_numeric(valores, errors="coerce").fillna(0).to_numpy(dtype=float).reshape(-1, 1)
    if len(valores) == 0:
        return pd.Series(dtype=float)
    return pd.Series(EscaladorMinMax().fit_transform(valores).ravel())


def calcular_puntuacion_edad(edad: pd.Series) -> pd.Series:
    edad = pd.to_numeric(edad, errors="coerce")
    centro_edad_ideal = (EDAD_IDEAL_MIN + EDAD_IDEAL_MAX) / 2
    puntuacion = 1 - ((edad - centro_edad_ideal).abs() / 12)
    return puntuacion.clip(lower=0, upper=1).fillna(0.5)


def calcular_puntuacion_similitud(
    candidatos: pd.DataFrame, perfil_objetivo: np.ndarray
) -> pd.Series:
    atributos_candidatos = (
        candidatos[ATRIBUTOS_PERFIL].apply(pd.to_numeric, errors="coerce").fillna(0)
    )
    escalador = EscaladorEstandar()
    matriz = np.vstack([perfil_objetivo, atributos_candidatos.to_numpy(dtype=float)])
    matriz_escalada = escalador.fit_transform(matriz)
    similitudes = similitud_coseno(matriz_escalada[1:], matriz_escalada[[0]]).ravel()
    return pd.Series((similitudes + 1) / 2, index=candidatos.index)


def construir_motivo(fila: pd.Series, necesidad: str) -> str:
    if fila["edad"] <= EDAD_MAX_PROMESA and fila["nota_media"] >= NOTA_MIN_PROMESA:
        return "Jugador joven con gran proyeccion."
    if necesidad in {"Delantero", "Extremo"} and fila["ataque"] >= fila[ATRIBUTOS_PERFIL].mean():
        return "Gran capacidad goleadora y alto estado de forma."
    if necesidad in {"Central", "Laterales", "Pivote defensivo", "Defensa"} and fila["defensa"] >= fila[ATRIBUTOS_PERFIL].mean():
        return "Excelente rendimiento defensivo y alta experiencia."
    return f"Perfil muy similar al tipo de {necesidad.lower()} requerido."


def filtrar_por_mercado(
    candidatos: pd.DataFrame, id_equipo: int, posicion_equipo: int
) -> pd.DataFrame:
    return candidatos[
        candidatos.apply(
            lambda candidato: mercado_permite_fichaje(
                id_equipo,
                posicion_equipo,
                candidato["id_equipo_actual"],
                candidato["posicion_equipo_actual"],
                candidato["edad"],
                candidato["nota_media"],
            ),
            axis=1,
        )
    ].copy()


def recomendar_para_necesidad(fila_necesidad: pd.Series, candidatos: pd.DataFrame) -> pd.DataFrame:
    necesidad = fila_necesidad["necesidad"]
    necesidades_origen = fila_necesidad.get("necesidades_origen", [necesidad])
    posicion_requerida = fila_necesidad.get(
        "posicion_requerida", MAPA_NECESIDAD_POSICION.get(necesidad)
    )
    if posicion_requerida is None or pd.isna(fila_necesidad["posicion"]):
        return pd.DataFrame(columns=COLUMNAS_SALIDA)

    candidatos_posicion = candidatos[
        (candidatos["posicion"] == posicion_requerida) & (candidatos["minutos"] >= MIN_MINUTOS)
    ].copy()
    if candidatos_posicion.empty:
        return pd.DataFrame(columns=COLUMNAS_SALIDA)

    cluster_objetivo = seleccionar_cluster_objetivo(candidatos_posicion, necesidades_origen)
    perfil_objetivo = construir_perfil_objetivo(
        candidatos_posicion, necesidades_origen, cluster_objetivo
    )

    posicion_equipo = int(fila_necesidad["posicion"])
    id_equipo = int(fila_necesidad["id_equipo"])
    candidatos_base = candidatos_posicion[candidatos_posicion["id_equipo"] != id_equipo].copy()
    candidatos_cluster = candidatos_base[candidatos_base["cluster"] == cluster_objetivo].copy()
    candidatos_filtrados = filtrar_por_mercado(candidatos_cluster, id_equipo, posicion_equipo)

    # Si el cluster objetivo deja pocos nombres, se completa con jugadores de la
    # misma posicion. La restriccion de mercado nunca se relaja.
    if len(candidatos_filtrados) < MAX_RECOMENDACIONES:
        candidatos_respaldo = filtrar_por_mercado(candidatos_base, id_equipo, posicion_equipo)
        candidatos_respaldo = candidatos_respaldo[
            ~candidatos_respaldo["id_jugador"].isin(candidatos_filtrados["id_jugador"])
        ]
        candidatos_filtrados = pd.concat(
            [candidatos_filtrados, candidatos_respaldo], ignore_index=True
        )

    if candidatos_filtrados.empty:
        return pd.DataFrame(columns=COLUMNAS_SALIDA)

    candidatos_filtrados["_similitud"] = calcular_puntuacion_similitud(
        candidatos_filtrados, perfil_objetivo
    )
    candidatos_filtrados["_nota"] = escalar_entre_cero_y_uno(candidatos_filtrados["nota_media"]).to_numpy()
    candidatos_filtrados["_forma"] = escalar_entre_cero_y_uno(candidatos_filtrados["score_reciente"]).to_numpy()
    candidatos_filtrados["_edad"] = calcular_puntuacion_edad(candidatos_filtrados["edad"]).to_numpy()
    candidatos_filtrados["_experiencia"] = escalar_entre_cero_y_uno(candidatos_filtrados["partidos"]).to_numpy()
    candidatos_filtrados["score_recomendacion"] = (
        candidatos_filtrados["_similitud"] * PESOS_SCORE["similitud"]
        + candidatos_filtrados["_nota"] * PESOS_SCORE["nota_media"]
        + candidatos_filtrados["_forma"] * PESOS_SCORE["estado_forma"]
        + candidatos_filtrados["_edad"] * PESOS_SCORE["edad"]
        + candidatos_filtrados["_experiencia"] * PESOS_SCORE["experiencia"]
    )
    candidatos_filtrados["motivo"] = candidatos_filtrados.apply(
        lambda candidato: construir_motivo(candidato, necesidad), axis=1
    )

    mejores_candidatos = candidatos_filtrados.sort_values(
        ["score_recomendacion", "nota_media", "partidos", "edad", "id_jugador"],
        ascending=[False, False, False, True, True],
    ).head(MAX_RECOMENDACIONES)
    return pd.DataFrame(
        {
            "id_equipo": fila_necesidad["id_equipo"],
            "nombre_equipo": fila_necesidad["nombre_equipo"],
            "necesidad": necesidad,
            "id_jugador": mejores_candidatos["id_jugador"].astype(int),
            "nombre_jugador": mejores_candidatos["nombre_jugador"],
            "id_equipo_actual": mejores_candidatos["id_equipo_actual"].astype("Int64"),
            "equipo_actual": mejores_candidatos["equipo_actual"],
            "score_recomendacion": mejores_candidatos["score_recomendacion"].round(4),
            "motivo": mejores_candidatos["motivo"],
        },
        columns=COLUMNAS_SALIDA,
    )


def generar_recomendaciones(
    necesidades: pd.DataFrame, candidatos: pd.DataFrame
) -> pd.DataFrame:
    recomendaciones = [
        recomendar_para_necesidad(fila_necesidad, candidatos)
        for _, fila_necesidad in necesidades.iterrows()
    ]
    recomendaciones = [tabla for tabla in recomendaciones if not tabla.empty]
    if not recomendaciones:
        return pd.DataFrame(columns=COLUMNAS_SALIDA)
    return pd.concat(recomendaciones, ignore_index=True)[COLUMNAS_SALIDA]


def main() -> None:
    argumentos = leer_argumentos()
    necesidades, candidatos, temporada = preparar_datos(argumentos)
    recomendaciones = generar_recomendaciones(necesidades, candidatos)

    archivo_salida = Path(argumentos.salida)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    recomendaciones.to_csv(archivo_salida, sep=";", index=False, encoding="utf-8-sig")

    print(f"Archivo generado: {archivo_salida}")
    print(f"Temporada procesada: {temporada}")
    print(f"Recomendaciones generadas: {len(recomendaciones)}")


if __name__ == "__main__":
    main()
