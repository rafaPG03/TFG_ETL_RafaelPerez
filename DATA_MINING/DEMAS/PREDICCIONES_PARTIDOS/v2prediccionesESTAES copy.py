from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

RUTA_BASE = Path(__file__).resolve().parents[2]
RUTA_DSA = RUTA_BASE / "ETL" / "DSA"

ARCHIVO_PARTIDOS = RUTA_DSA / "dim_partidos2.csv"
ARCHIVO_TEMPORADA = RUTA_DSA / "h_equipo_temporada.csv"
ARCHIVO_EQUIPOS = RUTA_DSA / "dim_equipos.csv"
ARCHIVO_SALIDA = Path(__file__).resolve().parent / "predicciones_partidos_incompletos.csv"


#CARGA DE DATOS
def cargar_datos() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Lee las tablas base necesarias para entrenar y predecir.
    partidos = pd.read_csv(ARCHIVO_PARTIDOS, sep=";")
    temporada = pd.read_csv(ARCHIVO_TEMPORADA, sep=";")
    equipos = pd.read_csv(ARCHIVO_EQUIPOS, sep=";")

    # Normaliza tipos para asegurar cálculos correctos y descarta filas inválidas.
    partidos["fecha"] = pd.to_datetime(partidos["id_tiempo"].astype(str), format="%Y%m%d", errors="coerce")
    partidos["goles_local"] = pd.to_numeric(partidos["goles_local"], errors="coerce")
    partidos["goles_visitante"] = pd.to_numeric(partidos["goles_visitante"], errors="coerce")
    partidos = partidos.dropna(subset=["fecha", "id_local", "id_visitante"]).copy()

    # Convierte a numéricas las métricas de rendimiento por temporada.
    for col in [
        "posicion",
        "puntos",
        "dg",
        "victorias",
        "empates",
        "derrotas",
        "gf",
        "gc",
        "victorias_local",
        "empates_local",
        "derrotas_local",
        "victorias_visitante",
        "empates_visitante",
        "derrotas_visitante",
    ]:
        temporada[col] = pd.to_numeric(temporada[col], errors="coerce")

    return partidos, temporada, equipos


def construir_historial_equipo(partidos_completados: pd.DataFrame) -> pd.DataFrame:
    # Crea la vista de cada partido desde el punto de vista del equipo local.
    local = partidos_completados[["fecha", "id_partido", "id_local", "goles_local", "goles_visitante"]].rename(
        columns={
            "id_local": "id_equipo",
            "goles_local": "goles_favor",
            "goles_visitante": "goles_contra",
        }
    )
    local["is_home"] = 1

    # Crea la misma vista desde el punto de vista del equipo visitante.
    visitante = partidos_completados[["fecha", "id_partido", "id_visitante", "goles_visitante", "goles_local"]].rename(
        columns={
            "id_visitante": "id_equipo",
            "goles_visitante": "goles_favor",
            "goles_local": "goles_contra",
        }
    )
    visitante["is_home"] = 0

    # Une ambas vistas y calcula puntos por partido (3/1/0).
    historial = pd.concat([local, visitante], ignore_index=True)
    historial["puntos"] = np.select(
        [
            historial["goles_favor"] > historial["goles_contra"],
            historial["goles_favor"] == historial["goles_contra"],
        ],
        [3, 1],
        default=0,
    )
    historial = historial.sort_values(["fecha", "id_partido"]).reset_index(drop=True)
    return historial


def media_ultimos_registros(df: pd.DataFrame, col: str, n: int) -> float:
    # Devuelve la media de los ultimos n registros; si no hay datos, devuelve NaN.
    if df.empty:
        return np.nan
    return float(df[col].tail(n).mean())


def calcular_caracteristicas_recientes(
    historial: pd.DataFrame,
    id_equipo: int,
    fecha: pd.Timestamp,
    es_partido_local: bool,
) -> dict[str, float]:
    # Filtra solo el historial anterior al partido a predecir para evitar fuga de informacion.
    historial_equipo = historial[(historial["id_equipo"] == id_equipo) & (historial["fecha"] < fecha)]
    # Separa tambien por condicion local/visitante para rasgos especificos del contexto.
    historial_lado = historial_equipo[historial_equipo["is_home"] == (1 if es_partido_local else 0)]

    # Genera promedios recientes y volumen de experiencia previa del equipo.
    return {
        "avg_puntos_last_5": media_ultimos_registros(historial_equipo, "puntos", 5),
        "avg_puntos_last_10": media_ultimos_registros(historial_equipo, "puntos", 10),
        "avg_goles_favor_last_5": media_ultimos_registros(historial_equipo, "goles_favor", 5),
        "avg_goles_favor_last_10": media_ultimos_registros(historial_equipo, "goles_favor", 10),
        "avg_goles_contra_last_5": media_ultimos_registros(historial_equipo, "goles_contra", 5),
        "avg_goles_contra_last_10": media_ultimos_registros(historial_equipo, "goles_contra", 10),
        "avg_puntos_side_last_5": media_ultimos_registros(historial_lado, "puntos", 5),
        "avg_puntos_side_last_10": media_ultimos_registros(historial_lado, "puntos", 10),
        "avg_goles_favor_side_last_5": media_ultimos_registros(historial_lado, "goles_favor", 5),
        "avg_goles_favor_side_last_10": media_ultimos_registros(historial_lado, "goles_favor", 10),
        "avg_goles_contra_side_last_5": media_ultimos_registros(historial_lado, "goles_contra", 5),
        "avg_goles_contra_side_last_10": media_ultimos_registros(historial_lado, "goles_contra", 10),
        "partidos_previos_total": float(len(historial_equipo)),
        "partidos_previos_side": float(len(historial_lado)),
    }


def agregar_caracteristicas_temporada(partidos: pd.DataFrame, temporada: pd.DataFrame) -> pd.DataFrame:
    # Selecciona columnas de clasificacion/forma acumulada para enriquecer el modelo.
    columnas_temporada = [
        "id_equipo",
        "temporada",
        "posicion",
        "puntos",
        "dg",
        "victorias",
        "empates",
        "derrotas",
        "gf",
        "gc",
        "victorias_local",
        "empates_local",
        "derrotas_local",
        "victorias_visitante",
        "empates_visitante",
        "derrotas_visitante",
    ]
    base_temporada = temporada[columnas_temporada].copy()

    # Duplica columnas de temporada para asociarlas por separado a local y visitante.
    temporada_local = base_temporada.rename(columns={c: f"home_season_{c}" for c in base_temporada.columns if c not in ["id_equipo", "temporada"]})
    temporada_visitante = base_temporada.rename(columns={c: f"away_season_{c}" for c in base_temporada.columns if c not in ["id_equipo", "temporada"]})

    # Cruza estadisticas de temporada del equipo local.
    salida = partidos.merge(
        temporada_local,
        left_on=["id_local", "temporada"],
        right_on=["id_equipo", "temporada"],
        how="left",
    ).drop(columns=["id_equipo"])

    # Cruza estadisticas de temporada del equipo visitante.
    salida = salida.merge(
        temporada_visitante,
        left_on=["id_visitante", "temporada"],
        right_on=["id_equipo", "temporada"],
        how="left",
    ).drop(columns=["id_equipo"])

    return salida


def construir_tabla_caracteristicas(partidos: pd.DataFrame, historial: pd.DataFrame, temporada: pd.DataFrame) -> pd.DataFrame:
    # Procesa partidos por orden temporal para construir rasgos consistentes.
    partidos_ordenados = partidos.sort_values(["fecha", "id_partido"]).reset_index(drop=True)
    filas: list[dict] = []

    for _, partido in partidos_ordenados.iterrows():
        # Calcula rasgos recientes para ambos equipos antes de este encuentro.
        recientes_local = calcular_caracteristicas_recientes(historial, int(partido["id_local"]), partido["fecha"], True)
        recientes_visitante = calcular_caracteristicas_recientes(historial, int(partido["id_visitante"]), partido["fecha"], False)

        # Crea una fila base con datos del partido y su estado.
        fila = {
            "id_partido": partido["id_partido"],
            "fecha": partido["fecha"],
            "temporada": partido["temporada"],
            "id_local": int(partido["id_local"]),
            "id_visitante": int(partido["id_visitante"]),
            "status": partido.get("status", np.nan),
            "goles_local": partido["goles_local"],
            "goles_visitante": partido["goles_visitante"],
        }
        # Adjunta rasgos prefijados para diferenciar local y visitante.
        fila.update({f"home_{k}": v for k, v in recientes_local.items()})
        fila.update({f"away_{k}": v for k, v in recientes_visitante.items()})
        filas.append(fila)

    # Convierte a DataFrame y completa con datos de temporada.
    salida = pd.DataFrame(filas)
    salida = agregar_caracteristicas_temporada(salida, temporada)
    return salida


def objetivo_1x2(df: pd.DataFrame) -> pd.Series:
    # Traduce goles finales al objetivo de clasificacion: H (local), D (empate), A (visitante).
    return np.select(
        [
            df["goles_local"] > df["goles_visitante"],
            df["goles_local"] == df["goles_visitante"],
        ],
        ["H", "D"],
        default="A",
    )


def main() -> None:
    # 1) Carga y prepara los datos de entrada.
    partidos, temporada, equipos = cargar_datos()

    # 2) Selecciona partidos completados para construir entrenamiento fiable.
    mascara_completados = (
        partidos["status"].fillna("").str.lower().eq("completado")
        & partidos["goles_local"].notna()
        & partidos["goles_visitante"].notna()
    )
    partidos_completados = partidos.loc[mascara_completados].copy()

    if partidos_completados.empty:
        raise ValueError("No hay partidos completados para entrenar el modelo.")

    # 3) Construye historial y tabla final de caracteristicas para todos los partidos.
    historial = construir_historial_equipo(partidos_completados)
    tabla_caracteristicas = construir_tabla_caracteristicas(partidos, historial, temporada)

    # 4) Separa filas para entrenar (partidos cerrados) y para predecir (resto).
    mascara_entrenamiento = (
        tabla_caracteristicas["status"].fillna("").str.lower().eq("completado")
        & tabla_caracteristicas["goles_local"].notna()
        & tabla_caracteristicas["goles_visitante"].notna()
    )
    mascara_prediccion = ~mascara_entrenamiento

    datos_entrenamiento = tabla_caracteristicas.loc[mascara_entrenamiento].copy()
    datos_prediccion = tabla_caracteristicas.loc[mascara_prediccion].copy()

    # Si no hay pendientes, genera el CSV de salida vacio con el esquema esperado.
    if datos_prediccion.empty:
        vacio = pd.DataFrame(
            columns=[
                "fecha",
                "id_partido",
                "id_local",
                "nombre_local",
                "id_visitante",
                "nombre_visitante",
                "prob_victoria_local",
                "prob_empate",
                "prob_victoria_visitante",
                "prediccion",
            ]
        )
        vacio.to_csv(ARCHIVO_SALIDA, index=False)
        return

    datos_entrenamiento["objetivo"] = objetivo_1x2(datos_entrenamiento)

    columnas_caracteristicas = [
        c
        for c in tabla_caracteristicas.columns
        if c.startswith("home_") or c.startswith("away_")
    ]

    X_entrenamiento = datos_entrenamiento[columnas_caracteristicas].copy()
    y_entrenamiento = datos_entrenamiento["objetivo"]
    medianas = X_entrenamiento.median(numeric_only=True)
    X_entrenamiento = X_entrenamiento.fillna(medianas)

    modelo = RandomForestClassifier(
        n_estimators=500,
        max_depth=12,
        min_samples_leaf=3,
        random_state=42,
        class_weight="balanced_subsample",
        n_jobs=-1,
    )
    modelo.fit(X_entrenamiento, y_entrenamiento)

    # 6) Predice probabilidades sobre partidos no completados.
    X_prediccion = datos_prediccion[columnas_caracteristicas].fillna(medianas)
    probabilidades_crudas = modelo.predict_proba(X_prediccion)

    # Alinea probabilidades al orden fijo H, D, A aunque falte alguna clase en entrenamiento.
    todas_clases = ["H", "D", "A"]
    probabilidades_alineadas = np.zeros((len(datos_prediccion), 3), dtype=float)
    clase_a_posicion = {c: i for i, c in enumerate(todas_clases)}
    for i, clase in enumerate(modelo.classes_):
        probabilidades_alineadas[:, clase_a_posicion[clase]] = probabilidades_crudas[:, i]

    # Normaliza por seguridad para que cada fila sume 100%.
    suma_fila = probabilidades_alineadas.sum(axis=1)
    suma_fila[suma_fila == 0] = 1.0
    probabilidades_alineadas = probabilidades_alineadas / suma_fila[:, None]

    # 7) Construye salida final con probabilidades y etiqueta de prediccion.
    resultado = datos_prediccion[["fecha", "id_partido", "id_local", "id_visitante"]].copy()
    resultado["prob_victoria_local"] = np.round(probabilidades_alineadas[:, 0] * 100, 2)
    resultado["prob_empate"] = np.round(probabilidades_alineadas[:, 1] * 100, 2)
    resultado["prob_victoria_visitante"] = np.round(probabilidades_alineadas[:, 2] * 100, 2)

    etiqueta_predicha = modelo.predict(X_prediccion)
    mapa_etiquetas = {"H": "Victoria local", "D": "Empate", "A": "Victoria visitante"}
    resultado["prediccion"] = pd.Series(etiqueta_predicha).map(mapa_etiquetas).values

    # Añade nombres de equipos para una salida legible.
    nombres = equipos[["id_equipo", "nombre_equipo"]].drop_duplicates()
    resultado = resultado.merge(
        nombres.rename(columns={"id_equipo": "id_local", "nombre_equipo": "nombre_local"}),
        on="id_local",
        how="left",
    )
    resultado = resultado.merge(
        nombres.rename(columns={"id_equipo": "id_visitante", "nombre_equipo": "nombre_visitante"}),
        on="id_visitante",
        how="left",
    )

    resultado = resultado[
        [
            "fecha",
            "id_partido",
            "id_local",
            "nombre_local",
            "id_visitante",
            "nombre_visitante",
            "prob_victoria_local",
            "prob_empate",
            "prob_victoria_visitante",
            "prediccion",
        ]
    ].sort_values(["fecha", "id_partido"]).reset_index(drop=True)

    # 8) Exporta el resultado final en CSV.
    resultado.to_csv(ARCHIVO_SALIDA, index=False)


if __name__ == "__main__":
    main()
