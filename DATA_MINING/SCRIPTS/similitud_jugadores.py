import math
import os
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "perfil_estadistico_jugadores.csv"
OUTPUT_FILE = BASE_DIR / "jugadores_similares_top5.csv"

FEATURES = ["ataque", "creacion", "defensa", "porteros", "duelos", "regates"]
TOP_K = 5


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera jugadores_similares_top5.csv leyendo desde PostgreSQL"
    )
    parser.add_argument("--db-host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("PGPORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("PGDATABASE", "TFG_Prueba"))
    parser.add_argument("--db-user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("PGPASSWORD", ""))
    parser.add_argument(
        "--perfil-table",
        default="public.dm_perfil_estadistico_jugadores",
        help="Tabla de la BD que contiene id_jugador,nombre y features de perfil",
    )
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    return parser.parse_args()


def validate_input(df: pd.DataFrame) -> None:
    required = ["id_jugador", "nombre", *FEATURES]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en el fichero de entrada: {missing}")


def load_main_positions(conn) -> pd.DataFrame:
    hist = pd.read_sql_query(
        "SELECT id_jugador, posicion, minutos FROM public.h_jugador_temporada",
        conn,
    )
    required = ["id_jugador", "posicion", "minutos"]
    missing = [c for c in required if c not in hist.columns]
    if missing:
        raise ValueError(f"No se puede obtener posicion desde h_jugador_temporada: {missing}")

    hist = hist[required].copy()
    hist["minutos"] = pd.to_numeric(hist["minutos"], errors="coerce").fillna(0)
    hist["posicion"] = hist["posicion"].fillna("Desconocida").astype(str).str.strip()

    pos_minutes = (
        hist.groupby(["id_jugador", "posicion"], as_index=False)["minutos"]
        .sum()
        .sort_values(["id_jugador", "minutos", "posicion"], ascending=[True, False, True])
    )
    main_pos = pos_minutes.drop_duplicates(subset=["id_jugador"], keep="first")
    return main_pos[["id_jugador", "posicion"]]


def load_profiles(conn, perfil_table: str) -> pd.DataFrame:
    query = (
        f"SELECT id_jugador, nombre, ataque, creacion, defensa, porteros, duelos, regates "
        f"FROM {perfil_table}"
    )
    return pd.read_sql_query(query, conn)


def choose_n_clusters(n_players: int) -> int:
    # Regla sencilla y robusta para no sobredimensionar clusters.
    if n_players <= 10:
        return max(2, n_players // 2)
    proposed = int(math.sqrt(n_players / 2))
    return max(3, min(proposed, 20, n_players - 1))


def zscore_scale(X: np.ndarray) -> np.ndarray:
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0
    return (X - mean) / std


def run_kmeans(
    X: np.ndarray,
    n_clusters: int,
    random_state: int = 42,
    max_iter: int = 100,
) -> np.ndarray:
    rng = np.random.default_rng(random_state)
    n_samples = X.shape[0]

    initial_idx = rng.choice(n_samples, size=n_clusters, replace=False)
    centroids = X[initial_idx].copy()
    labels = np.zeros(n_samples, dtype=int)

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

    return labels


def cosine_similarity_matrix(X: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X_norm = X / norms
    return X_norm @ X_norm.T


def get_top_similar_ids(
    idx: int,
    clusters: np.ndarray,
    positions: np.ndarray,
    sim_matrix: np.ndarray,
    top_k: int,
) -> list[int]:
    same_position = np.where(positions == positions[idx])[0].tolist()
    same_position = [i for i in same_position if i != idx]

    same_cluster = [i for i in same_position if clusters[i] == clusters[idx]]

    same_cluster_sorted = sorted(
        same_cluster,
        key=lambda j: sim_matrix[idx, j],
        reverse=True,
    )

    selected = same_cluster_sorted[:top_k]

    if len(selected) < top_k:
        same_position_global = sorted(
            [j for j in same_position if j not in selected],
            key=lambda j: sim_matrix[idx, j],
            reverse=True,
        )
        needed = top_k - len(selected)
        selected.extend(same_position_global[:needed])

    return selected


def main() -> None:
    args = parse_args()
    conn = psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
    )

    try:
        df = load_profiles(conn, args.perfil_table)
        pos_df = load_main_positions(conn)
    finally:
        conn.close()

    df.columns = df.columns.str.strip()
    validate_input(df)

    df = df.drop_duplicates(subset=["id_jugador"]).copy()
    df = df.merge(pos_df, on="id_jugador", how="left")
    df["posicion"] = df["posicion"].fillna("Desconocida")

    feature_df = df[FEATURES].apply(pd.to_numeric, errors="coerce")
    feature_df = feature_df.fillna(feature_df.median(numeric_only=True))

    X = zscore_scale(feature_df.values.astype(float))

    n_clusters = choose_n_clusters(len(df))
    clusters = run_kmeans(X, n_clusters=n_clusters, random_state=42)

    sim_matrix = cosine_similarity_matrix(X)
    positions = df["posicion"].values

    result_rows = []
    for idx, row in df.reset_index(drop=True).iterrows():
        top_indices = get_top_similar_ids(idx, clusters, positions, sim_matrix, TOP_K)

        out = {
            "id_jugador": int(row["id_jugador"]),
            "nombre": row["nombre"],
            "cluster": int(clusters[idx]),
        }

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
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_file, sep=";", index=False, encoding="utf-8-sig")

    print(f"Archivo generado: {output_file}")


if __name__ == "__main__":
    main()
