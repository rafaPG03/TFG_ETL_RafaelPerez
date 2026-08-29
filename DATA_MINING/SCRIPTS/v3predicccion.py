import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_SALIDA = RUTA_RAIZ / "DATA_MINING" / "DSA_DM" / "predicciones_partidos_incompletos2.csv"
RUTA_METRICAS = RUTA_RAIZ / "DATA_MINING" / "DSA_DM" / "metricas_prediccion_partidos.csv"


def parsear_argumentos() -> argparse.Namespace:
    """Configura los argumentos de linea de comandos para la ejecucion del script."""
    parser = argparse.ArgumentParser(
        description="Predice partidos incompletos leyendo datos desde PostgreSQL"
    )
    parser.add_argument("--db-host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("PGPORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("PGDATABASE", "TFG_BDLaLiga"))
    parser.add_argument("--db-user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("PGPASSWORD", "betico18"))
    parser.add_argument("--output", default=str(RUTA_SALIDA))
    parser.add_argument("--metrics-output", default=str(RUTA_METRICAS))
    return parser.parse_args()


def leer_tabla(conexion: psycopg2.extensions.connection, consulta: str) -> pd.DataFrame:
    """Ejecuta una consulta SQL y devuelve los resultados en un DataFrame de Pandas."""
    return pd.read_sql_query(consulta, conexion)


def cargar_datos(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Se conecta a la base de datos y extrae las tablas necesarias."""
    conexion = psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
    )

    try:
        # 1. Extraer el historico de partidos
        partidos = leer_tabla(
            conexion,
            """
            SELECT
                id_partido,
                id_tiempo,
                temporada,
                id_local,
                id_visitante,
                goles_local,
                goles_visitante,
                status
            FROM public.dim_partidos
            """,
        )

        # 2. Extraer metricas acumuladas de la temporada de la ultima jornada registrada
        datos_temporada = leer_tabla(
            conexion,
            """
            WITH ult_jornada AS (
                SELECT
                    id_equipo,
                    temporada,
                    posicion,
                    puntos,
                    dg,
                    victorias,
                    empates,
                    derrotas,
                    gf,
                    gc,
                    victorias_local,
                    empates_local,
                    derrotas_local,
                    victorias_visitante,
                    empates_visitante,
                    derrotas_visitante,
                    ROW_NUMBER() OVER (
                        PARTITION BY id_equipo, temporada
                        ORDER BY jornada DESC
                    ) AS rn
                FROM public.h_equipo_temporada
            )
            SELECT
                id_equipo,
                temporada,
                posicion,
                puntos,
                dg,
                victorias,
                empates,
                derrotas,
                gf,
                gc,
                victorias_local,
                empates_local,
                derrotas_local,
                victorias_visitante,
                empates_visitante,
                derrotas_visitante
            FROM ult_jornada
            WHERE rn = 1
            """,
        )

        # 3. Extraer el diccionario de equipos
        equipos = leer_tabla(
            conexion,
            """
            SELECT id_equipo, nombre_equipo
            FROM public.dim_equipo
            """,
        )
    finally:
        conexion.close()

    # Preprocesamiento y limpieza inicial de tipos de datos
    partidos["fecha"] = pd.to_datetime(partidos["id_tiempo"].astype(str), format="%Y%m%d", errors="coerce")
    partidos["goles_local"] = pd.to_numeric(partidos["goles_local"], errors="coerce")
    partidos["goles_visitante"] = pd.to_numeric(partidos["goles_visitante"], errors="coerce")
    partidos = partidos.dropna(subset=["fecha", "id_local", "id_visitante"]).copy()

    # Asegurar que las columnas estadisticas de la temporada sean numericas
    columnas_numericas_temp = [
        "posicion", "puntos", "dg", "victorias", "empates", "derrotas", "gf", "gc",
        "victorias_local", "empates_local", "derrotas_local",
        "victorias_visitante", "empates_visitante", "derrotas_visitante"
    ]
    for col in columnas_numericas_temp:
        datos_temporada[col] = pd.to_numeric(datos_temporada[col], errors="coerce")

    return partidos, datos_temporada, equipos


def construir_historial_equipos(partidos_completados: pd.DataFrame) -> pd.DataFrame:
    """Desglosa los partidos para crear una linea de tiempo cronologica por cada equipo."""
    # Perspectiva cuando el equipo jugo en casa
    local = partidos_completados[["fecha", "id_partido", "id_local", "goles_local", "goles_visitante"]].rename(
        columns={
            "id_local": "id_equipo",
            "goles_local": "goles_a_favor",
            "goles_visitante": "goles_en_contra",
        }
    )
    local["es_local"] = 1

    # Perspectiva cuando el equipo jugo fuera
    visitante = partidos_completados[["fecha", "id_partido", "id_visitante", "goles_visitante", "goles_local"]].rename(
        columns={
            "id_visitante": "id_equipo",
            "goles_visitante": "goles_a_favor",
            "goles_local": "goles_en_contra",
        }
    )
    visitante["es_local"] = 0

    # Unificar ambas perspectivas y calcular los puntos obtenidos
    historial = pd.concat([local, visitante], ignore_index=True)
    historial["puntos"] = np.select(
        [
            historial["goles_a_favor"] > historial["goles_en_contra"],
            historial["goles_a_favor"] == historial["goles_en_contra"],
        ],
        [3, 1],
        default=0,
    )
    
    # Ordenar cronologicamente para que las ventanas moviles sean correctas
    historial = historial.sort_values(["fecha", "id_partido"]).reset_index(drop=True)
    return historial


def calcular_media_segura(df: pd.DataFrame, columna: str, n: int) -> float:
    """Calcula la media de los ultimos N registros evitando errores si el DataFrame esta vacio."""
    if df.empty:
        return np.nan
    return float(df[columna].tail(n).mean())


def calcular_caracteristicas_recientes(
    historial: pd.DataFrame,
    id_equipo: int,
    fecha: pd.Timestamp,
    es_partido_local: bool,
) -> dict[str, float]:
    """Calcula el estado de forma reciente (ultimos 5 y 10 partidos) de un equipo antes de una fecha."""
    # Filtrar partidos anteriores del equipo
    hist_equipo = historial[(historial["id_equipo"] == id_equipo) & (historial["fecha"] < fecha)]
    # Filtrar partidos anteriores del equipo en la misma condicion (casa o fuera)
    hist_condicion = hist_equipo[hist_equipo["es_local"] == (1 if es_partido_local else 0)]

    return {
        "media_puntos_ultimos_5": calcular_media_segura(hist_equipo, "puntos", 5),
        "media_puntos_ultimos_10": calcular_media_segura(hist_equipo, "puntos", 10),
        "media_goles_favor_ultimos_5": calcular_media_segura(hist_equipo, "goles_a_favor", 5),
        "media_goles_favor_ultimos_10": calcular_media_segura(hist_equipo, "goles_a_favor", 10),
        "media_goles_contra_ultimos_5": calcular_media_segura(hist_equipo, "goles_en_contra", 5),
        "media_goles_contra_ultimos_10": calcular_media_segura(hist_equipo, "goles_en_contra", 10),
        
        "media_puntos_condicion_ultimos_5": calcular_media_segura(hist_condicion, "puntos", 5),
        "media_puntos_condicion_ultimos_10": calcular_media_segura(hist_condicion, "puntos", 10),
        "media_goles_favor_condicion_ultimos_5": calcular_media_segura(hist_condicion, "goles_a_favor", 5),
        "media_goles_favor_condicion_ultimos_10": calcular_media_segura(hist_condicion, "goles_a_favor", 10),
        "media_goles_contra_condicion_ultimos_5": calcular_media_segura(hist_condicion, "goles_en_contra", 5),
        "media_goles_contra_condicion_ultimos_10": calcular_media_segura(hist_condicion, "goles_en_contra", 10),
        
        "partidos_previos_totales": float(len(hist_equipo)),
        "partidos_previos_condicion": float(len(hist_condicion)),
    }


def anadir_caracteristicas_temporada(partidos_base: pd.DataFrame, datos_temporada: pd.DataFrame) -> pd.DataFrame:
    """Cruza los datos de los partidos con las estadisticas acumuladas de la temporada de cada equipo."""
    columnas_temporada = [
        "id_equipo", "temporada", "posicion", "puntos", "dg", "victorias", "empates", "derrotas",
        "gf", "gc", "victorias_local", "empates_local", "derrotas_local",
        "victorias_visitante", "empates_visitante", "derrotas_visitante",
    ]
    base_temporada = datos_temporada[columnas_temporada].copy()

    # Renombrar columnas para diferenciar las estadisticas del local y del visitante
    local_temporada = base_temporada.rename(columns={c: f"local_temp_{c}" for c in base_temporada.columns if c not in ["id_equipo", "temporada"]})
    visitante_temporada = base_temporada.rename(columns={c: f"visitante_temp_{c}" for c in base_temporada.columns if c not in ["id_equipo", "temporada"]})

    # Cruzar datos del equipo local
    resultado = partidos_base.merge(
        local_temporada,
        left_on=["id_local", "temporada"],
        right_on=["id_equipo", "temporada"],
        how="left",
    ).drop(columns=["id_equipo"])

    # Cruzar datos del equipo visitante
    resultado = resultado.merge(
        visitante_temporada,
        left_on=["id_visitante", "temporada"],
        right_on=["id_equipo", "temporada"],
        how="left",
    ).drop(columns=["id_equipo"])

    return resultado


def construir_tabla_caracteristicas(partidos: pd.DataFrame, historial: pd.DataFrame, datos_temporada: pd.DataFrame) -> pd.DataFrame:
    """Construye el dataset final calculando las variables predictoras para cada partido."""
    partidos_ordenados = partidos.sort_values(["fecha", "id_partido"]).reset_index(drop=True)
    filas_caracteristicas: list[dict] = []

    for _, partido in partidos_ordenados.iterrows():
        # Calcular forma reciente para ambos equipos
        local_reciente = calcular_caracteristicas_recientes(historial, int(partid_local := partido["id_local"]), partido["fecha"], True)
        visitante_reciente = calcular_caracteristicas_recientes(historial, int(partid_visitante := partido["id_visitante"]), partido["fecha"], False)

        fila = {
            "id_partido": partido["id_partido"],
            "fecha": partido["fecha"],
            "temporada": partido["temporada"],
            "id_local": int(partid_local),
            "id_visitante": int(partid_visitante),
            "status": partido.get("status", np.nan),
            "goles_local": partido["goles_local"],
            "goles_visitante": partido["goles_visitante"],
        }
        # Agregar prefijos para identificar que variable pertenece a cada equipo
        fila.update({f"local_{k}": v for k, v in local_reciente.items()})
        fila.update({f"visitante_{k}": v for k, v in visitante_reciente.items()})
        filas_caracteristicas.append(fila)

    df_caracteristicas = pd.DataFrame(filas_caracteristicas)
    df_caracteristicas = anadir_caracteristicas_temporada(df_caracteristicas, datos_temporada)
    return df_caracteristicas


def definir_objetivo_1x2(df: pd.DataFrame) -> pd.Series:
    """Define la variable objetivo en el formato tradicional: L (Local), E (Empate), V (Visitante)."""
    return np.select(
        [
            df["goles_local"] > df["goles_visitante"],
            df["goles_local"] == df["goles_visitante"],
        ],
        ["L", "E"],
        default="V",
    )


def crear_modelos() -> dict[str, object]:
    """Define los modelos que se entrenan y comparan sobre el mismo dataset."""
    return {
        "RandomForest": RandomForestClassifier(
            n_estimators=500,
            max_depth=12,
            min_samples_leaf=3,
            random_state=42,
            class_weight="balanced_subsample",
            n_jobs=-1,
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=250,
            learning_rate=0.04,
            max_depth=3,
            random_state=42,
        ),
        "SVM": Pipeline(
            steps=[
                ("imputador", SimpleImputer(strategy="median")),
                ("escalado", StandardScaler()),
                (
                    "modelo",
                    SVC(
                        kernel="rbf",
                        C=1.5,
                        gamma="scale",
                        class_weight="balanced",
                        probability=True,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }


def dividir_validacion_temporal(df_entrenamiento: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reserva la parte final del historico para evaluar sin mezclar futuro con pasado."""
    df_ordenado = df_entrenamiento.sort_values(["fecha", "id_partido"]).reset_index(drop=True)
    corte = int(len(df_ordenado) * 0.8)

    if corte <= 0 or corte >= len(df_ordenado):
        raise ValueError("No hay suficientes partidos completados para validar los modelos.")

    return df_ordenado.iloc[:corte].copy(), df_ordenado.iloc[corte:].copy()


def calcular_metricas_modelo(nombre: str, y_real: pd.Series, y_pred: np.ndarray) -> dict:
    """Calcula metricas pensadas para comparar modelos multiclase 1X2."""
    return {
        "modelo": nombre,
        "accuracy": round(float(accuracy_score(y_real, y_pred)), 4),
        "precision_macro": round(float(precision_score(y_real, y_pred, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(y_real, y_pred, average="macro", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y_real, y_pred, average="macro", zero_division=0)), 4),
        "partidos_validacion": int(len(y_real)),
    }


def evaluar_modelos(
    df_entrenamiento: pd.DataFrame,
    columnas_caracteristicas: list[str],
    medianas: pd.Series,
    metrics_output: Path,
) -> pd.DataFrame:
    """Entrena los modelos en el 80% inicial y los valida en el 20% final del historico."""
    df_train, df_test = dividir_validacion_temporal(df_entrenamiento)
    X_train = df_train[columnas_caracteristicas].fillna(medianas)
    y_train = df_train["target"]
    X_test = df_test[columnas_caracteristicas].fillna(medianas)
    y_test = df_test["target"]

    metricas = []
    for nombre, modelo in crear_modelos().items():
        modelo.fit(X_train, y_train)
        predicciones = modelo.predict(X_test)
        metricas.append(calcular_metricas_modelo(nombre, y_test, predicciones))

    df_metricas = pd.DataFrame(metricas).sort_values(
        ["f1_macro", "accuracy", "modelo"],
        ascending=[False, False, True],
    )
    df_metricas["usado_para_prediccion"] = df_metricas["modelo"].eq("RandomForest")

    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    df_metricas.to_csv(metrics_output, index=False)
    return df_metricas


def main() -> None:
    args = parsear_argumentos()
    partidos, datos_temporada, equipos = cargar_datos(args)

    # Mascara para identificar partidos que ya se han jugado completamente
    mascara_completados = (
        partidos["status"].fillna("").str.lower().eq("completado")
        & partidos["goles_local"].notna()
        & partidos["goles_visitante"].notna()
    )
    partidos_completados = partidos.loc[mascara_completados].copy()

    if partidos_completados.empty:
        raise ValueError("No hay partidos completados para entrenar el modelo.")

    # Generacion de variables del sistema
    historial = construir_historial_equipos(partidos_completados)
    df_caracteristicas = construir_tabla_caracteristicas(partidos, historial, datos_temporada)

    # Separar los datos en conjunto de entrenamiento (jugados) y de prediccion (pendientes)
    mascara_entrenamiento = (
        df_caracteristicas["status"].fillna("").str.lower().eq("completado")
        & df_caracteristicas["goles_local"].notna()
        & df_caracteristicas["goles_visitante"].notna()
    )
    mascara_prediccion = ~mascara_entrenamiento

    df_entrenamiento = df_caracteristicas.loc[mascara_entrenamiento].copy()
    df_prediccion = df_caracteristicas.loc[mascara_prediccion].copy()

    # Asignar la variable objetivo de entrenamiento
    df_entrenamiento["target"] = definir_objetivo_1x2(df_entrenamiento)

    # Filtrar solo las columnas predictoras calculadas (que empiezan por local_ o visitante_)
    columnas_caracteristicas = [
        c for c in df_caracteristicas.columns if c.startswith("local_") or c.startswith("visitante_")
    ]

    X_entrenamiento = df_entrenamiento[columnas_caracteristicas].copy()
    y_entrenamiento = df_entrenamiento["target"]

    # Imputacion de valores faltantes usando la mediana del conjunto de entrenamiento
    medianas = X_entrenamiento.median(numeric_only=True)
    X_entrenamiento = X_entrenamiento.fillna(medianas)

    metricas = evaluar_modelos(
        df_entrenamiento,
        columnas_caracteristicas,
        medianas,
        Path(args.metrics_output),
    )

    # Si no hay partidos por predecir, generar un CSV vacio con la estructura requerida.
    if df_prediccion.empty:
        vacio = pd.DataFrame(
            columns=[
                "fecha", "id_partido", "id_local", "nombre_local", "id_visitante", "nombre_visitante",
                "prob_victoria_local", "prob_empate", "prob_victoria_visitante", "prediccion",
            ]
        )
        vacio.to_csv(Path(args.output), index=False)
        return

    # Entrenar el modelo principal con todo el historico antes de predecir partidos pendientes.
    modelo = crear_modelos()["SVM"]
    modelo.fit(X_entrenamiento, y_entrenamiento)

    # Preparar datos de prediccion e imputar nulos con las mismas medianas de entrenamiento
    X_prediccion = df_prediccion[columnas_caracteristicas].fillna(medianas)
    probabilidades_crudas = modelo.predict_proba(X_prediccion)

    # Asegurar el orden correcto de las columnas de probabilidad independientemente de las clases vistas
    clases_esperadas = ["L", "E", "V"]
    probabilidades_alineadas = np.zeros((len(df_prediccion), 3), dtype=float)
    clase_a_posicion = {c: i for i, c in enumerate(clases_esperadas)}
    for i, cls in enumerate(modelo.classes_):
        probabilidades_alineadas[:, clase_a_posicion[cls]] = probabilidades_crudas[:, i]

    # Re-normalizar filas para evitar cualquier problema matematico menor (division por cero o sumas != 1)
    suma_filas = probabilidades_alineadas.sum(axis=1)
    suma_filas[suma_filas == 0] = 1.0
    probabilidades_alineadas = probabilidades_alineadas / suma_filas[:, None]

    # Construir el dataframe de resultados finales en base a porcentajes
    resultados = df_prediccion[["fecha", "id_partido", "id_local", "id_visitante"]].copy()
    resultados["prob_victoria_local"] = np.round(probabilidades_alineadas[:, 0] * 100, 2)
    resultados["prob_empate"] = np.round(probabilidades_alineadas[:, 1] * 100, 2)
    resultados["prob_victoria_visitante"] = np.round(probabilidades_alineadas[:, 2] * 100, 2)

    # Obtener la prediccion final basada en la clase con mayor probabilidad
    etiquetas_predichas = modelo.predict(X_prediccion)
    mapa_etiquetas = {"L": "Victoria local", "E": "Empate", "V": "Victoria visitante"}
    resultados["prediccion"] = pd.Series(etiquetas_predichas).map(mapa_etiquetas).values

    # Anadir los nombres legibles de los equipos cruzando con la tabla de equipos
    nombres_equipos = equipos[["id_equipo", "nombre_equipo"]].drop_duplicates()
    resultados = resultados.merge(
        nombres_equipos.rename(columns={"id_equipo": "id_local", "nombre_equipo": "nombre_local"}),
        on="id_local",
        how="left",
    )
    resultados = resultados.merge(
        nombres_equipos.rename(columns={"id_equipo": "id_visitante", "nombre_equipo": "nombre_visitante"}),
        on="id_visitante",
        how="left",
    )

    # Reordenar las columnas para el entregable final en formato scannable
    resultados = resultados[
        [
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
    ].sort_values(["id_partido"]).reset_index(drop=True)

    # Asegurar que el directorio de destino exista y guardar como archivo CSV
    archivo_salida = Path(args.output)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    resultados.to_csv(archivo_salida, index=False)
    print(f"Archivo generado: {archivo_salida}")
    print(f"Metricas generadas: {Path(args.metrics_output)}")
    print(f"Modelo usado para prediccion: RandomForest")


if __name__ == "__main__":
    main()
