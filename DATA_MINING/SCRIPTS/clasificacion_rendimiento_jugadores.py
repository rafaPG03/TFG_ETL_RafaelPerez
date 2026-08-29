from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC


RUTA_SCRIPTS = Path(__file__).resolve().parent
RUTA_DATA_MINING = RUTA_SCRIPTS.parent
RUTA_RAIZ = RUTA_DATA_MINING.parent
RUTA_H_JUGADOR_TEMPORADA = RUTA_RAIZ / "ETL" / "DSA" / "h_jugador_temporada.csv"
RUTA_PERFIL = RUTA_DATA_MINING / "DSA_DM" / "perfil_estadistico_jugadores.csv"
RUTA_SALIDA = RUTA_DATA_MINING / "DSA_DM" / "clasificacion_rendimiento_jugadores.csv"
RUTA_METRICAS = RUTA_DATA_MINING / "DSA_DM" / "metricas_clasificacion_rendimiento.csv"

CLASES_RENDIMIENTO = ["BAJO", "MEDIO", "ALTO"]
MIN_MINUTOS_TEMPORADA = 450
RANDOM_STATE = 42

COLUMNAS_NUMERICAS_BASE = [
    "partidos",
    "minutos",
    "titular",
    "nota_media",
    "goles",
    "asistencias",
    "tiros_totales",
    "tiros_a_puerta",
    "pases_totales",
    "pases_clave",
    "precision_pases",
    "entradas",
    "bloqueos",
    "intercepciones",
    "duelos_totales",
    "duelos_ganados",
    "faltas_sufridas",
    "faltas_cometidas",
    "regates_intentados",
    "regates_exito",
    "regateado",
    "amarillas",
    "rojas",
    "penaltis_marcados",
    "goles_concedidos",
    "paradas",
    "penaltis_parados",
]

COLUMNAS_PERFIL = [
    "ataque",
    "creacion",
    "defensa",
    "porteros",
    "duelos",
    "regates",
    "percentil_ataque",
    "percentil_creacion",
    "percentil_defensa",
    "percentil_porteros",
    "percentil_duelos",
    "percentil_regates",
]

COLUMNAS_MODELO = COLUMNAS_NUMERICAS_BASE + COLUMNAS_PERFIL


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Clasifica el rendimiento de la siguiente temporada de cada jugador "
            "con Random Forest, SVM y una red neuronal MLP"
        )
    )
    parser.add_argument("--player-season-file", default=str(RUTA_H_JUGADOR_TEMPORADA))
    parser.add_argument("--profile-file", default=str(RUTA_PERFIL))
    parser.add_argument("--output", default=str(RUTA_SALIDA))
    parser.add_argument("--metrics-output", default=str(RUTA_METRICAS))
    parser.add_argument(
        "--min-minutes",
        type=int,
        default=MIN_MINUTOS_TEMPORADA,
        help="Minutos minimos en la temporada objetivo para etiquetar el rendimiento",
    )
    return parser.parse_args()


def crear_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def normalizar_posicion(posicion: str) -> str:
    valor = str(posicion).strip()
    equivalencias = {
        "Forward": "Delantero",
        "Goalkeeper": "Portero",
        "Defender": "Defensa",
        "Midfielder": "Mediocentro",
    }
    return equivalencias.get(valor, valor if valor else "Desconocida")


def validar_columnas(df: pd.DataFrame, columnas: list[str], nombre_fichero: str) -> None:
    faltantes = [col for col in columnas if col not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en {nombre_fichero}: {faltantes}")


def leer_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    return df


def cargar_temporadas_jugador(path: Path) -> pd.DataFrame:
    df = leer_csv(path)
    columnas_requeridas = ["id_jugador", "id_equipo", "temporada", "posicion", *COLUMNAS_NUMERICAS_BASE]
    validar_columnas(df, columnas_requeridas, path.name)

    for col in ["id_jugador", "id_equipo", "temporada", *COLUMNAS_NUMERICAS_BASE]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["id_jugador", "temporada"]).copy()
    df["id_jugador"] = df["id_jugador"].astype(int)
    df["temporada"] = df["temporada"].astype(int)
    df["posicion"] = df["posicion"].fillna("Desconocida").apply(normalizar_posicion)

    # Un jugador puede aparecer en varios equipos durante una temporada.
    # Se suman volumenes y se pondera la nota media por minutos.
    df["minutos_para_ponderar"] = df["minutos"].fillna(0).clip(lower=0)
    df["nota_x_minutos"] = df["nota_media"].fillna(0) * df["minutos_para_ponderar"]

    acumulables = [col for col in COLUMNAS_NUMERICAS_BASE if col not in {"nota_media", "precision_pases"}]
    agregaciones = {col: "sum" for col in acumulables}
    agregaciones.update(
        {
            "nota_x_minutos": "sum",
            "minutos_para_ponderar": "sum",
            "precision_pases": "mean",
        }
    )

    base = df.groupby(["id_jugador", "temporada"], as_index=False).agg(agregaciones)

    posicion_principal = (
        df.sort_values(["id_jugador", "temporada", "minutos_para_ponderar"], ascending=[True, True, False])
        .drop_duplicates(["id_jugador", "temporada"])[["id_jugador", "temporada", "posicion", "id_equipo"]]
    )

    base = base.merge(posicion_principal, on=["id_jugador", "temporada"], how="left")
    base["nota_media"] = np.where(
        base["minutos_para_ponderar"] > 0,
        base["nota_x_minutos"] / base["minutos_para_ponderar"],
        np.nan,
    )
    base.drop(columns=["nota_x_minutos", "minutos_para_ponderar"], inplace=True)
    return base


def cargar_perfiles(path: Path) -> pd.DataFrame:
    df = leer_csv(path)
    columnas_requeridas = ["id_jugador", "temporada", "nombre", *COLUMNAS_PERFIL]
    validar_columnas(df, columnas_requeridas, path.name)

    for col in ["id_jugador", "temporada", *COLUMNAS_PERFIL]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["id_jugador", "temporada"]).copy()
    df["id_jugador"] = df["id_jugador"].astype(int)
    df["temporada"] = df["temporada"].astype(int)
    df["nombre"] = df["nombre"].fillna("N/A").astype(str)
    return df[["id_jugador", "temporada", "nombre", *COLUMNAS_PERFIL]]


def calcular_score_rendimiento(df: pd.DataFrame) -> pd.Series:
    percentil_general = df[
        [
            "percentil_ataque",
            "percentil_creacion",
            "percentil_defensa",
            "percentil_porteros",
            "percentil_duelos",
            "percentil_regates",
        ]
    ].mean(axis=1)

    nota_percentil = (
        df.groupby(["temporada", "posicion"])["nota_media"]
        .rank(method="average", pct=True)
        .mul(100)
    )
    return (percentil_general * 0.65 + nota_percentil.fillna(percentil_general) * 0.35).round(2)


def etiquetar_rendimiento(df: pd.DataFrame, min_minutos: int) -> pd.DataFrame:
    df = df.copy()
    df["score_rendimiento"] = calcular_score_rendimiento(df)
    df["clase_rendimiento"] = pd.NA

    jugadores_validos = df["minutos"].fillna(0) >= min_minutos
    for _, indices in df[jugadores_validos].groupby(["temporada", "posicion"]).groups.items():
        scores = df.loc[indices, "score_rendimiento"]
        if len(scores) < 3:
            df.loc[indices, "clase_rendimiento"] = "MEDIO"
            continue

        q35 = scores.quantile(0.35)
        q75 = scores.quantile(0.75)
        df.loc[indices, "clase_rendimiento"] = np.select(
            [scores < q35, scores >= q75],
            ["BAJO", "ALTO"],
            default="MEDIO",
        )

    return df


def construir_dataset(base: pd.DataFrame) -> pd.DataFrame:
    actual = base.copy()
    objetivo = base[
        [
            "id_jugador",
            "temporada",
            "score_rendimiento",
            "clase_rendimiento",
        ]
    ].rename(
        columns={
            "temporada": "temporada_objetivo",
            "score_rendimiento": "score_real_temporada_siguiente",
            "clase_rendimiento": "clase_real_temporada_siguiente",
        }
    )
    actual["temporada_objetivo"] = actual["temporada"] + 1
    dataset = actual.merge(objetivo, on=["id_jugador", "temporada_objetivo"], how="left")
    return dataset


def dividir_train_test(dataset: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    etiquetado = dataset.dropna(subset=["clase_real_temporada_siguiente"]).copy()
    if etiquetado["temporada_objetivo"].nunique() < 2:
        raise ValueError("No hay suficientes temporadas enlazadas para entrenar y validar.")

    ultima_temporada = etiquetado["temporada_objetivo"].max()
    train = etiquetado[etiquetado["temporada_objetivo"] < ultima_temporada].copy()
    test = etiquetado[etiquetado["temporada_objetivo"] == ultima_temporada].copy()

    if len(train) < 10 or len(test) < 3 or train["clase_real_temporada_siguiente"].nunique() < 2:
        corte = int(len(etiquetado) * 0.8)
        train = etiquetado.iloc[:corte].copy()
        test = etiquetado.iloc[corte:].copy()

    if train.empty or test.empty:
        raise ValueError("No hay suficientes datos para separar entrenamiento y validacion.")

    return train, test


def crear_preprocesador() -> ColumnTransformer:
    numericas = Pipeline(
        steps=[
            ("imputador", SimpleImputer(strategy="median")),
            ("escalado", StandardScaler()),
        ]
    )
    categoricas = Pipeline(
        steps=[
            ("imputador", SimpleImputer(strategy="most_frequent")),
            ("onehot", crear_one_hot_encoder()),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numericas, COLUMNAS_MODELO),
            ("cat", categoricas, ["posicion"]),
        ]
    )


def crear_modelos() -> dict[str, Pipeline]:
    return {
        "RandomForest": Pipeline(
            steps=[
                ("preprocesador", crear_preprocesador()),
                (
                    "modelo",
                    RandomForestClassifier(
                        n_estimators=250,
                        max_depth=8,
                        min_samples_leaf=3,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "SVM": Pipeline(
            steps=[
                ("preprocesador", crear_preprocesador()),
                (
                    "modelo",
                    SVC(
                        kernel="rbf",
                        C=1.5,
                        gamma="scale",
                        probability=True,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "MLP": Pipeline(
            steps=[
                ("preprocesador", crear_preprocesador()),
                (
                    "modelo",
                    MLPClassifier(
                        hidden_layer_sizes=(32, 16),
                        activation="relu",
                        max_iter=700,
                        early_stopping=True,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
    }


def calcular_metricas(nombre: str, y_real: pd.Series, y_pred: np.ndarray) -> dict:
    return {
        "modelo": nombre,
        "accuracy": round(float(accuracy_score(y_real, y_pred)), 4),
        "precision_macro": round(float(precision_score(y_real, y_pred, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(y_real, y_pred, average="macro", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y_real, y_pred, average="macro", zero_division=0)), 4),
    }


def entrenar_y_evaluar(
    modelos: dict[str, Pipeline], train: pd.DataFrame, test: pd.DataFrame
) -> tuple[dict[str, Pipeline], pd.DataFrame, str]:
    X_train = train[COLUMNAS_MODELO + ["posicion"]]
    y_train = train["clase_real_temporada_siguiente"]
    X_test = test[COLUMNAS_MODELO + ["posicion"]]
    y_test = test["clase_real_temporada_siguiente"]

    metricas = []
    modelos_entrenados = {}
    for nombre, modelo in modelos.items():
        modelo.fit(X_train, y_train)
        pred = modelo.predict(X_test)
        modelos_entrenados[nombre] = modelo
        metricas.append(calcular_metricas(nombre, y_test, pred))

    df_metricas = pd.DataFrame(metricas).sort_values(
        ["f1_macro", "accuracy", "modelo"], ascending=[False, False, True]
    )
    mejor_modelo = str(df_metricas.iloc[0]["modelo"])
    return modelos_entrenados, df_metricas, mejor_modelo


def anadir_predicciones(
    dataset: pd.DataFrame, modelos: dict[str, Pipeline], mejor_modelo: str
) -> pd.DataFrame:
    salida = dataset[
        [
            "id_jugador",
            "nombre",
            "id_equipo",
            "posicion",
            "temporada",
            "temporada_objetivo",
            "minutos",
            "nota_media",
            "score_rendimiento",
            "score_real_temporada_siguiente",
            "clase_real_temporada_siguiente",
        ]
    ].copy()
    salida.rename(
        columns={
            "temporada": "temporada_base",
            "score_rendimiento": "score_temporada_base",
        },
        inplace=True,
    )

    X = dataset[COLUMNAS_MODELO + ["posicion"]]
    for nombre, modelo in modelos.items():
        salida[f"prediccion_{nombre.lower()}"] = modelo.predict(X)

    modelo_principal = modelos[mejor_modelo]
    probabilidades = modelo_principal.predict_proba(X)
    clases_modelo = list(modelo_principal.classes_)
    for clase in CLASES_RENDIMIENTO:
        if clase in clases_modelo:
            salida[f"probabilidad_{clase.lower()}"] = np.round(
                probabilidades[:, clases_modelo.index(clase)], 4
            )
        else:
            salida[f"probabilidad_{clase.lower()}"] = 0.0

    salida["modelo_recomendado"] = mejor_modelo
    return salida.sort_values(["temporada_base", "posicion", "id_jugador"])


def main() -> None:
    args = leer_argumentos()
    temporadas = cargar_temporadas_jugador(Path(args.player_season_file))
    perfiles = cargar_perfiles(Path(args.profile_file))

    base = temporadas.merge(perfiles, on=["id_jugador", "temporada"], how="inner")
    if base.empty:
        raise ValueError("No hay datos comunes entre h_jugador_temporada y perfil_estadistico_jugadores.")

    base = etiquetar_rendimiento(base, args.min_minutes)
    dataset = construir_dataset(base)
    train, test = dividir_train_test(dataset)

    modelos, metricas, mejor_modelo = entrenar_y_evaluar(crear_modelos(), train, test)
    salida = anadir_predicciones(dataset, modelos, mejor_modelo)

    output_path = Path(args.output)
    metrics_path = Path(args.metrics_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(output_path, sep=";", index=False, encoding="utf-8-sig")
    metricas.to_csv(metrics_path, sep=";", index=False, encoding="utf-8-sig")

    print(f"Archivo generado: {output_path}")
    print(f"Metricas generadas: {metrics_path}")
    print(f"Filas entrenadas: {len(train)}")
    print(f"Filas validadas: {len(test)}")
    print(f"Modelo recomendado: {mejor_modelo}")


if __name__ == "__main__":
    main()
