import math
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "perfil_estadistico_jugadores_v2.csv"
OUTPUT_FILE = BASE_DIR / "jugadores_similares_top5_v2.csv"
PLAYER_MATCH_FILE = BASE_DIR.parents[1] / "ETL" / "DSA" / "h_jugador_partido.csv"

FEATURES = ["ataque", "creacion", "defensa", "porteros", "duelos", "regates"]
TOP_K = 5
HYBRID_ALPHA = 0.7
N_INIT = 10
MAX_K = 12


def validate_input(df: pd.DataFrame) -> None:
    required = ["id_jugador", "nombre", *FEATURES]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en el fichero de entrada: {missing}")


def normalize_position(pos: str) -> str:
    p = str(pos).strip().lower()
    if p in {"p", "por", "gk"} or "port" in p or "goalkeep" in p:
        return "Portero"
    if p in {"df", "def"} or "def" in p or "lateral" in p or "back" in p:
        return "Defensa"
    if p in {"m", "mc", "mcd", "mco"} or "medio" in p or "centrocamp" in p:
        return "Mediocentro"
    if p in {"dl", "dc", "st", "cf"} or "del" in p or "extremo" in p or "wing" in p:
        return "Delantero"
    return "Desconocida"


def load_main_positions() -> pd.DataFrame:
    hist = pd.read_csv(PLAYER_MATCH_FILE, sep=";")
    required = ["id_jugador", "posicion", "minutos"]
    missing = [c for c in required if c not in hist.columns]
    if missing:
        raise ValueError(f"No se puede obtener posicion desde h_jugador_partido: {missing}")

    hist = hist[required].copy()
    hist["minutos"] = pd.to_numeric(hist["minutos"], errors="coerce").fillna(0)
    hist["posicion"] = hist["posicion"].fillna("Desconocida").astype(str).str.strip()
    hist["posicion_norm"] = hist["posicion"].apply(normalize_position)

    pos_minutes = (
        hist.groupby(["id_jugador", "posicion_norm"], as_index=False)["minutos"]
        .sum()
        .sort_values(["id_jugador", "minutos", "posicion_norm"], ascending=[True, False, True])
    )
    main_pos = pos_minutes.drop_duplicates(subset=["id_jugador"], keep="first")
    return main_pos[["id_jugador", "posicion_norm"]].rename(columns={"posicion_norm": "posicion"})


def zscore_scale(X: np.ndarray) -> np.ndarray:
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0
    return (X - mean) / std


def init_kmeans_pp(X: np.ndarray, n_clusters: int, rng: np.random.Generator) -> np.ndarray:
    n_samples = X.shape[0]
    centroids = [X[rng.integers(0, n_samples)]]

    for _ in range(1, n_clusters):
        distances = np.min(
            np.linalg.norm(X[:, None, :] - np.array(centroids)[None, :, :], axis=2) ** 2,
            axis=1,
        )
        total = distances.sum()
        if total == 0:
            centroids.append(X[rng.integers(0, n_samples)])
            continue
        probs = distances / total
        next_idx = rng.choice(n_samples, p=probs)
        centroids.append(X[next_idx])

    return np.array(centroids)


def run_kmeans_once(
    X: np.ndarray,
    n_clusters: int,
    rng: np.random.Generator,
    max_iter: int = 200,
) -> tuple[np.ndarray, np.ndarray, float]:
    n_samples = X.shape[0]
    centroids = init_kmeans_pp(X, n_clusters, rng)
    labels = np.full(n_samples, -1, dtype=int)

    for _ in range(max_iter):
        distances = np.linalg.norm(X[:, None, :] - centroids[None, :, :], axis=2)
        new_labels = np.argmin(distances, axis=1)

        if np.array_equal(labels, new_labels):
            break
        labels = new_labels

        for k in range(n_clusters):
            members = X[labels == k]
            if len(members) == 0:
                centroids[k] = X[rng.integers(0, n_samples)]
            else:
                centroids[k] = members.mean(axis=0)

    inertia = float(np.sum((X - centroids[labels]) ** 2))
    return labels, centroids, inertia


def run_kmeans(
    X: np.ndarray,
    n_clusters: int,
    random_state: int = 42,
    n_init: int = N_INIT,
) -> np.ndarray:
    best_labels = None
    best_inertia = math.inf

    for seed in range(n_init):
        rng = np.random.default_rng(random_state + seed)
        labels, _, inertia = run_kmeans_once(X, n_clusters, rng)
        if inertia < best_inertia:
            best_inertia = inertia
            best_labels = labels

    if best_labels is None:
        raise RuntimeError("No se pudo ajustar KMeans")

    return best_labels


def silhouette_score_simple(X: np.ndarray, labels: np.ndarray) -> float:
    unique_labels = np.unique(labels)
    if len(unique_labels) <= 1:
        return -1.0

    dist = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
    sil_values = []

    for i in range(X.shape[0]):
        same_mask = labels == labels[i]
        same_mask[i] = False

        if np.any(same_mask):
            a = float(dist[i, same_mask].mean())
        else:
            a = 0.0

        b = math.inf
        for c in unique_labels:
            if c == labels[i]:
                continue
            other_mask = labels == c
            if np.any(other_mask):
                b = min(b, float(dist[i, other_mask].mean()))

        denom = max(a, b) if math.isfinite(b) else a
        s = 0.0 if denom == 0 else (b - a) / denom
        sil_values.append(s)

    return float(np.mean(sil_values))


def choose_k_by_silhouette(X: np.ndarray) -> int:
    n_players = len(X)
    if n_players <= 6:
        return max(2, n_players - 1)

    k_min = 2
    k_max = min(MAX_K, n_players - 1)

    best_k = 2
    best_score = -1.0
    for k in range(k_min, k_max + 1):
        labels = run_kmeans(X, n_clusters=k, random_state=42, n_init=5)
        score = silhouette_score_simple(X, labels)
        if score > best_score:
            best_score = score
            best_k = k

    return best_k


def cosine_similarity_matrix(X: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X_norm = X / norms
    return X_norm @ X_norm.T


def euclidean_similarity_matrix(X: np.ndarray) -> np.ndarray:
    distances = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
    max_dist = float(distances.max())
    if max_dist == 0:
        return np.ones_like(distances)
    return 1.0 - (distances / max_dist)


def hybrid_similarity_matrix(X: np.ndarray, alpha: float = HYBRID_ALPHA) -> np.ndarray:
    cos = cosine_similarity_matrix(X)
    euc = euclidean_similarity_matrix(X)
    return (alpha * cos) + ((1.0 - alpha) * euc)


def get_top_similar_ids(
    idx: int,
    clusters: np.ndarray,
    positions: np.ndarray,
    sim_matrix: np.ndarray,
    top_k: int,
) -> list[int]:
    my_pos = positions[idx]
    candidate_idx = [i for i in range(len(positions)) if i != idx and positions[i] == my_pos]

    same_cluster = [i for i in candidate_idx if clusters[i] == clusters[idx]]
    same_cluster = sorted(same_cluster, key=lambda j: sim_matrix[idx, j], reverse=True)

    selected = same_cluster[:top_k]

    if len(selected) < top_k:
        global_pool = [j for j in candidate_idx if j not in selected]
        global_pool = sorted(global_pool, key=lambda j: sim_matrix[idx, j], reverse=True)
        selected.extend(global_pool[: top_k - len(selected)])

    return selected


def main() -> None:
    df = pd.read_csv(INPUT_FILE, sep=";")
    validate_input(df)

    df = df.drop_duplicates(subset=["id_jugador"]).copy()

    pos_df = load_main_positions()
    df = df.merge(pos_df, on="id_jugador", how="left")
    df["posicion"] = df["posicion"].fillna("Desconocida")

    feature_df = df[FEATURES].apply(pd.to_numeric, errors="coerce")
    feature_df = feature_df.fillna(feature_df.median(numeric_only=True))

    X = zscore_scale(feature_df.values.astype(float))

    n_clusters = choose_k_by_silhouette(X)
    clusters = run_kmeans(X, n_clusters=n_clusters, random_state=42, n_init=N_INIT)

    sim_matrix = hybrid_similarity_matrix(X, alpha=HYBRID_ALPHA)
    positions = df["posicion"].values

    result_rows = []
    for idx, row in df.reset_index(drop=True).iterrows():
        top_indices = get_top_similar_ids(idx, clusters, positions, sim_matrix, TOP_K)

        out = {
            "id_jugador": int(row["id_jugador"]),
            "nombre": row["nombre"],
            "posicion": row["posicion"],
            "cluster": int(clusters[idx]),
        }

        if "confianza_datos" in row:
            out["confianza_datos"] = round(float(row["confianza_datos"]), 3)

        for rank in range(1, TOP_K + 1):
            if rank <= len(top_indices):
                j = top_indices[rank - 1]
                out[f"id_similar{rank}"] = int(df.iloc[j]["id_jugador"])
                out[f"nombre_similar{rank}"] = df.iloc[j]["nombre"]
                out[f"similitud{rank}"] = round(float(sim_matrix[idx, j]), 4)
            else:
                out[f"id_similar{rank}"] = np.nan
                out[f"nombre_similar{rank}"] = np.nan
                out[f"similitud{rank}"] = np.nan

        result_rows.append(out)

    result = pd.DataFrame(result_rows)
    result.to_csv(OUTPUT_FILE, sep=";", index=False, encoding="utf-8-sig")

    print(f"Archivo generado: {OUTPUT_FILE}")
    print(f"Clusters seleccionados (silhouette): {n_clusters}")


if __name__ == "__main__":
    main()
