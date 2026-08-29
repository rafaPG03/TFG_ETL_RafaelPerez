import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd


RUTA_SCRIPTS = Path(__file__).resolve().parent
RUTA_DATA_MINING = RUTA_SCRIPTS.parent
RUTA_ENTRADA = RUTA_DATA_MINING / "DSA_DM" / "perfil_estadistico_jugadores.csv"
RUTA_JUGADOR_TEMPORADA = RUTA_DATA_MINING.parent / "ETL" / "DSA" / "h_jugador_temporada.csv"
RUTA_SALIDA = RUTA_DATA_MINING / "DSA_DM" / "jugadores_similares_top5_por_temporada.csv"

FEATURES = ["ataque", "creacion", "defensa", "porteros", "duelos", "regates"]
TOP_K = 5
N_INIT = 5


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera jugadores similares para cada temporada a partir del perfil estadistico"
    )
    parser.add_argument("--input", default=str(RUTA_ENTRADA), help="CSV de perfiles por jugador y temporada")
    parser.add_argument(
        "--player-season-file",
        default=str(RUTA_JUGADOR_TEMPORADA),
        help="CSV h_jugador_temporada para obtener la posicion principal de cada campana",
    )
    parser.add_argument("--output", default=str(RUTA_SALIDA))
    return parser.parse_args()


def validar_entrada(df: pd.DataFrame) -> None:
    required = ["id_jugador", "temporada", "nombre", *FEATURES]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en el fichero de entrada: {missing}")


def normalizar_posicion(position: str) -> str:
    """Unifica las pocas etiquetas equivalentes presentes en el historico."""
    value = str(position).strip()
    return {"Forward": "Delantero", "Goalkeeper": "Portero"}.get(value, value)


def cargar_posiciones_temporada(path: Path) -> pd.DataFrame:
    """Obtiene la posicion con mas minutos de cada jugador en cada temporada."""
    hist = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    required = ["id_jugador", "temporada", "posicion", "minutos"]
    missing = [col for col in required if col not in hist.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {path.name}: {missing}")

    hist = hist[required].copy()
    hist["temporada"] = pd.to_numeric(hist["temporada"], errors="coerce")
    hist["minutos"] = pd.to_numeric(hist["minutos"], errors="coerce").fillna(0)
    hist = hist.dropna(subset=["id_jugador", "temporada"])
    hist["temporada"] = hist["temporada"].astype(int)
    hist["posicion"] = hist["posicion"].fillna("Desconocida").apply(normalizar_posicion)

    # Un jugador puede aparecer en varios equipos: se conserva su posicion con mas minutos.
    pos_minutes = (
        hist.groupby(["id_jugador", "temporada", "posicion"], as_index=False)["minutos"]
        .sum()
        .sort_values(
            ["id_jugador", "temporada", "minutos", "posicion"],
            ascending=[True, True, False, True],
        )
    )
    return pos_minutes.drop_duplicates(["id_jugador", "temporada"])[
        ["id_jugador", "temporada", "posicion"]
    ]


def elegir_numero_clusters(n_players: int) -> int:
    if n_players < 3:
        return 1
    proposed = int(math.sqrt(n_players / 2))
    return max(2, min(proposed, 20, n_players - 1))


def zscore_scale(X: np.ndarray) -> np.ndarray:
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0
    return (X - mean) / std


def run_kmeans_once(
    X: np.ndarray, n_clusters: int, rng: np.random.Generator, max_iter: int = 100
) -> tuple[np.ndarray, float]:
    n_samples = X.shape[0]
    centroids = X[rng.choice(n_samples, size=n_clusters, replace=False)].copy()
    labels = np.full(n_samples, -1, dtype=int)

    for _ in range(max_iter):
        distances = np.linalg.norm(X[:, None, :] - centroids[None, :, :], axis=2)
        new_labels = np.argmin(distances, axis=1)
        if np.array_equal(labels, new_labels):
            break
        labels = new_labels

        for cluster in range(n_clusters):
            members = X[labels == cluster]
            centroids[cluster] = (
                members.mean(axis=0) if len(members) else X[rng.integers(n_samples)]
            )

    inertia = float(np.sum((X - centroids[labels]) ** 2))
    return labels, inertia


def run_kmeans(X: np.ndarray, n_clusters: int, random_state: int = 42) -> np.ndarray:
    """Conserva K-means, con varias inicializaciones para evitar un mal arranque puntual."""
    if n_clusters == 1:
        return np.zeros(len(X), dtype=int)

    best_labels = None
    best_inertia = math.inf
    for seed in range(N_INIT):
        labels, inertia = run_kmeans_once(X, n_clusters, np.random.default_rng(random_state + seed))
        if inertia < best_inertia:
            best_labels, best_inertia = labels, inertia

    return best_labels


def cosine_similarity_matrix(X: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X_norm = X / norms
    return X_norm @ X_norm.T


def get_top_similar_ids(
    idx: int, clusters: np.ndarray, positions: np.ndarray, sim_matrix: np.ndarray
) -> list[int]:
    same_position = [i for i in range(len(positions)) if i != idx and positions[i] == positions[idx]]
    same_cluster = sorted(
        (i for i in same_position if clusters[i] == clusters[idx]),
        key=lambda j: sim_matrix[idx, j],
        reverse=True,
    )
    selected = same_cluster[:TOP_K]

    if len(selected) < TOP_K:
        remaining = sorted(
            (i for i in same_position if i not in selected),
            key=lambda j: sim_matrix[idx, j],
            reverse=True,
        )
        selected.extend(remaining[: TOP_K - len(selected)])
    return selected


def procesar_temporada(season_df: pd.DataFrame) -> list[dict]:
    feature_df = season_df[FEATURES].apply(pd.to_numeric, errors="coerce")
    feature_df = feature_df.fillna(feature_df.median(numeric_only=True)).fillna(0)
    X = zscore_scale(feature_df.to_numpy(dtype=float))
    clusters = run_kmeans(X, elegir_numero_clusters(len(season_df)))
    similarities = cosine_similarity_matrix(X)
    positions = season_df["posicion"].to_numpy()

    rows = []
    for idx, row in season_df.reset_index(drop=True).iterrows():
        similar_indices = get_top_similar_ids(idx, clusters, positions, similarities)
        result = {
            "id_jugador": int(row["id_jugador"]),
            "temporada": int(row["temporada"]),
            "nombre": row["nombre"],
            "posicion": row["posicion"],
            "cluster": int(clusters[idx]),
        }
        for rank in range(1, TOP_K + 1):
            if rank <= len(similar_indices):
                similar = similar_indices[rank - 1]
                result[f"id_similar{rank}"] = int(season_df.iloc[similar]["id_jugador"])
                result[f"nombre_similar{rank}"] = season_df.iloc[similar]["nombre"]
                result[f"similitud{rank}"] = round(float(similarities[idx, similar]), 4)
            else:
                result[f"id_similar{rank}"] = pd.NA
                result[f"nombre_similar{rank}"] = np.nan
                result[f"similitud{rank}"] = np.nan
        rows.append(result)
    return rows


def main() -> None:
    args = leer_argumentos()
    input_file = Path(args.input)
    df = pd.read_csv(input_file, sep=";", encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    validar_entrada(df)

    df["temporada"] = pd.to_numeric(df["temporada"], errors="coerce")
    df = df.dropna(subset=["id_jugador", "temporada"]).copy()
    df["temporada"] = df["temporada"].astype(int)
    df = df.drop_duplicates(["id_jugador", "temporada"])

    positions = cargar_posiciones_temporada(Path(args.player_season_file))
    df = df.merge(positions, on=["id_jugador", "temporada"], how="left")
    df["posicion"] = df["posicion"].fillna("Desconocida")

    result_rows = []
    for _, season_df in df.sort_values(["temporada", "id_jugador"]).groupby("temporada", sort=True):
        result_rows.extend(procesar_temporada(season_df.reset_index(drop=True)))

    result = pd.DataFrame(result_rows)
    for rank in range(1, TOP_K + 1):
        result[f"id_similar{rank}"] = result[f"id_similar{rank}"].astype("Int64")
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_file, sep=";", index=False, encoding="utf-8-sig")

    print(f"Archivo generado: {output_file}")
    print(f"Temporadas procesadas: {df['temporada'].nunique()}")


if __name__ == "__main__":
    main()
