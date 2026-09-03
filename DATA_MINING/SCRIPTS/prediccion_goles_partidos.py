from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.multioutput import MultiOutputRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from predicciones_partidos import cargar_datos, construir_historial_equipos, construir_tabla_caracteristicas


RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_SALIDA = RUTA_RAIZ / "DATA_MINING" / "DSA_DM" / "prediccion_goles_partidos.csv"
RUTA_METRICAS = RUTA_RAIZ / "DATA_MINING" / "METRICAS" / "metricas_regresion_goles_partidos.csv"

OBJETIVOS = ["goles_local", "goles_visitante"]


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predice los goles esperados de partidos pendientes mediante regresion"
    )
    parser.add_argument("--db-host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("PGPORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("PGDATABASE", "TFG_BDLaLiga"))
    parser.add_argument("--db-user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("PGPASSWORD", "betico18"))
    parser.add_argument("--output", default=str(RUTA_SALIDA))
    parser.add_argument("--metrics-output", default=str(RUTA_METRICAS))
    return parser.parse_args()


def crear_modelos() -> dict[str, object]:
    return {
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=500,
            max_depth=12,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        ),
        "GradientBoostingRegressor": MultiOutputRegressor(
            GradientBoostingRegressor(
                n_estimators=250,
                learning_rate=0.04,
                max_depth=3,
                random_state=42,
            )
        ),
        "SVR": MultiOutputRegressor(
            Pipeline(
                steps=[
                    ("imputador", SimpleImputer(strategy="median")),
                    ("escalado", StandardScaler()),
                    ("modelo", SVR(kernel="rbf", C=2.0, epsilon=0.15, gamma="scale")),
                ]
            )
        ),
        "MLPRegressor": Pipeline(
            steps=[
                ("imputador", SimpleImputer(strategy="median")),
                ("escalado", StandardScaler()),
                (
                    "modelo",
                    MLPRegressor(
                        hidden_layer_sizes=(48, 24),
                        activation="relu",
                        max_iter=1200,
                        random_state=42,
                        early_stopping=True,
                    ),
                ),
            ]
        ),
    }


def obtener_mascaras(partidos: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    mascara_entrenamiento = (
        partidos["status"].fillna("").str.lower().eq("completado")
        & partidos["goles_local"].notna()
        & partidos["goles_visitante"].notna()
    )
    return mascara_entrenamiento, ~mascara_entrenamiento


def obtener_columnas_caracteristicas(df_caracteristicas: pd.DataFrame) -> list[str]:
    return [
        columna
        for columna in df_caracteristicas.columns
        if columna.startswith("local_") or columna.startswith("visitante_")
    ]


def dividir_validacion_temporal(df_entrenamiento: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_ordenado = df_entrenamiento.sort_values(["fecha", "id_partido"]).reset_index(drop=True)
    corte = int(len(df_ordenado) * 0.8)

    if corte <= 0 or corte >= len(df_ordenado):
        raise ValueError("No hay suficientes partidos completados para validar la regresion.")

    return df_ordenado.iloc[:corte].copy(), df_ordenado.iloc[corte:].copy()


def calcular_metricas_objetivo(
    nombre_modelo: str,
    objetivo: str,
    y_real: np.ndarray,
    y_pred: np.ndarray,
    usado_para_prediccion: bool,
) -> dict:
    return {
        "modelo": nombre_modelo,
        "objetivo": objetivo,
        "mae": round(float(mean_absolute_error(y_real, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_real, y_pred))), 4),
        "r2": round(float(r2_score(y_real, y_pred)), 4),
        "partidos_validacion": int(len(y_real)),
        "usado_para_prediccion": usado_para_prediccion,
    }


def evaluar_modelos(
    df_entrenamiento: pd.DataFrame,
    columnas_caracteristicas: list[str],
    metrics_output: Path,
) -> pd.DataFrame:
    df_train, df_test = dividir_validacion_temporal(df_entrenamiento)

    X_train = df_train[columnas_caracteristicas].copy()
    X_test = df_test[columnas_caracteristicas].copy()
    medianas = X_train.median(numeric_only=True)
    X_train = X_train.fillna(medianas)
    X_test = X_test.fillna(medianas)

    y_train = df_train[OBJETIVOS]
    y_test = df_test[OBJETIVOS]

    filas_metricas = []
    for nombre_modelo, modelo in crear_modelos().items():
        modelo.fit(X_train, y_train)
        predicciones = np.clip(modelo.predict(X_test), 0, None)
        usado = nombre_modelo == "RandomForestRegressor"

        for indice, objetivo in enumerate(OBJETIVOS):
            filas_metricas.append(
                calcular_metricas_objetivo(
                    nombre_modelo,
                    objetivo,
                    y_test[objetivo].to_numpy(),
                    predicciones[:, indice],
                    usado,
                )
            )

        filas_metricas.append(
            calcular_metricas_objetivo(
                nombre_modelo,
                "promedio",
                y_test[OBJETIVOS].to_numpy().ravel(),
                predicciones.ravel(),
                usado,
            )
        )

    metricas = pd.DataFrame(filas_metricas).sort_values(
        ["objetivo", "mae", "rmse", "modelo"],
        ascending=[True, True, True, True],
    )
    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    metricas.to_csv(metrics_output, index=False)
    return metricas


def resultado_desde_goles(goles_local: float, goles_visitante: float) -> str:
    diferencia = goles_local - goles_visitante
    if diferencia > 0.25:
        return "Victoria local"
    if diferencia < -0.25:
        return "Victoria visitante"
    return "Empate"


def construir_salida(
    df_prediccion: pd.DataFrame,
    equipos: pd.DataFrame,
    predicciones: np.ndarray,
) -> pd.DataFrame:
    resultados = df_prediccion[["fecha", "id_partido", "id_local", "id_visitante"]].copy()
    resultados["goles_local_esperados"] = np.round(predicciones[:, 0], 2)
    resultados["goles_visitante_esperados"] = np.round(predicciones[:, 1], 2)
    resultados["diferencia_goles_esperada"] = (
        resultados["goles_local_esperados"] - resultados["goles_visitante_esperados"]
    ).round(2)
    resultados["resultado_estimado"] = [
        resultado_desde_goles(local, visitante)
        for local, visitante in zip(
            resultados["goles_local_esperados"],
            resultados["goles_visitante_esperados"],
        )
    ]
    resultados["marcador_estimado"] = (
        resultados["goles_local_esperados"].round().astype(int).astype(str)
        + "-"
        + resultados["goles_visitante_esperados"].round().astype(int).astype(str)
    )
    resultados["modelo"] = "RandomForestRegressor"

    nombres_equipos = equipos[["id_equipo", "nombre_equipo"]].drop_duplicates()
    resultados = resultados.merge(
        nombres_equipos.rename(columns={"id_equipo": "id_local", "nombre_equipo": "nombre_local"}),
        on="id_local",
        how="left",
    )
    resultados = resultados.merge(
        nombres_equipos.rename(
            columns={"id_equipo": "id_visitante", "nombre_equipo": "nombre_visitante"}
        ),
        on="id_visitante",
        how="left",
    )

    return resultados[
        [
            "id_partido",
            "id_local",
            "nombre_local",
            "id_visitante",
            "nombre_visitante",
            "goles_local_esperados",
            "goles_visitante_esperados",
            "diferencia_goles_esperada",
            "resultado_estimado",
            "marcador_estimado",
        ]
    ].sort_values(["id_partido"]).reset_index(drop=True)


def main() -> None:
    args = leer_argumentos()
    partidos, datos_temporada, equipos = cargar_datos(args)

    mascara_completados = (
        partidos["status"].fillna("").str.lower().eq("completado")
        & partidos["goles_local"].notna()
        & partidos["goles_visitante"].notna()
    )
    partidos_completados = partidos.loc[mascara_completados].copy()
    if partidos_completados.empty:
        raise ValueError("No hay partidos completados para entrenar la regresion.")

    historial = construir_historial_equipos(partidos_completados)
    df_caracteristicas = construir_tabla_caracteristicas(partidos, historial, datos_temporada)
    mascara_entrenamiento, mascara_prediccion = obtener_mascaras(df_caracteristicas)

    df_entrenamiento = df_caracteristicas.loc[mascara_entrenamiento].copy()
    df_prediccion = df_caracteristicas.loc[mascara_prediccion].copy()
    columnas_caracteristicas = obtener_columnas_caracteristicas(df_caracteristicas)

    evaluar_modelos(df_entrenamiento, columnas_caracteristicas, Path(args.metrics_output))

    columnas_salida = [
        "id_partido",
        "id_local",
        "nombre_local",
        "id_visitante",
        "nombre_visitante",
        "goles_local_esperados",
        "goles_visitante_esperados",
        "diferencia_goles_esperada",
        "resultado_estimado",
        "marcador_estimado",
    ]

    archivo_salida = Path(args.output)
    archivo_salida.parent.mkdir(parents=True, exist_ok=True)

    if df_prediccion.empty:
        pd.DataFrame(columns=columnas_salida).to_csv(archivo_salida, index=False)
        print(f"Archivo generado: {archivo_salida}")
        print(f"Metricas generadas: {Path(args.metrics_output)}")
        return

    X_entrenamiento = df_entrenamiento[columnas_caracteristicas].copy()
    y_entrenamiento = df_entrenamiento[OBJETIVOS].copy()
    medianas = X_entrenamiento.median(numeric_only=True)
    X_entrenamiento = X_entrenamiento.fillna(medianas)

    modelo = crear_modelos()["RandomForestRegressor"]
    modelo.fit(X_entrenamiento, y_entrenamiento)

    X_prediccion = df_prediccion[columnas_caracteristicas].fillna(medianas)
    predicciones = np.clip(modelo.predict(X_prediccion), 0, None)
    resultados = construir_salida(df_prediccion, equipos, predicciones)
    resultados.to_csv(archivo_salida, index=False)

    print(f"Archivo generado: {archivo_salida}")
    print(f"Metricas generadas: {Path(args.metrics_output)}")
    print("Modelo usado para prediccion: RandomForestRegressor")


if __name__ == "__main__":
    main()
