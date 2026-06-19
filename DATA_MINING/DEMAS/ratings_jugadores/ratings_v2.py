from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DSA_DIR = BASE_DIR.parents[1] / "ETL" / "DSA"

INPUT_SEASON_FILE = DSA_DIR / "h_jugador_temporada.csv"
INPUT_PLAYERS_FILE = DSA_DIR / "dim_jugadores.csv"
OUTPUT_FILE = BASE_DIR / "perfil_estadistico_jugadores_v2.csv"

CURRENT_SEASON = 2025
HALF_LIFE_YEARS = 2.0
RATIO_SMOOTH = 5.0
MIN_MATCHES_FULL_CONF = 10.0
MIN_MINUTES_FULL_CONF = 900.0

FEATURES = ["ataque", "creacion", "defensa", "porteros", "duelos", "regates"]

REQUIRED_SEASON_COLUMNS = [
    "id_jugador",
    "temporada",
    "posicion",
    "partidos",
    "minutos",
    "goles",
    "tiros_a_puerta",
    "pases_totales",
    "pases_clave",
    "asistencias",
    "precision_pases",
    "entradas",
    "intercepciones",
    "bloqueos",
    "amarillas",
    "paradas",
    "penaltis_parados",
    "duelos_ganados",
    "duelos_totales",
    "regates_exito",
    "regates_intentados",
    "faltas_sufridas",
]

OPTIONAL_SEASON_COLUMNS_WITH_DEFAULT = {
    "goles_concedidos": 0.0,
    "regateado": 0.0,
}


def validate_columns(df: pd.DataFrame, required: list[str], source_name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {source_name}: {missing}")


def temporal_weight(season: float) -> float:
    delta = CURRENT_SEASON - season
    if delta < 0:
        return 0.0
    return float(0.5 ** (delta / HALF_LIFE_YEARS))


def to_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def normalize_position(pos: str) -> str:
    p = str(pos).strip().lower()
    if "port" in p or p == "gk":
        return "Portero"
    if "def" in p or "lateral" in p or "back" in p:
        return "Defensa"
    if "medio" in p or "centrocamp" in p or p in {"mc", "mcd", "mco"}:
        return "Mediocentro"
    if "del" in p or "extremo" in p or "wing" in p or p in {"dc", "st", "cf"}:
        return "Delantero"
    return "Desconocida"


def build_scores(df: pd.DataFrame) -> pd.DataFrame:
    partidos = df["partidos"].clip(lower=1.0)
    minutos = df["minutos"].clip(lower=1.0)

    exp_matches = (partidos / MIN_MATCHES_FULL_CONF).clip(upper=1.0)
    exp_minutes = (minutos / MIN_MINUTES_FULL_CONF).clip(upper=1.0)
    factor_experiencia = np.minimum(exp_matches, exp_minutes)

    score_ataque = (df["goles"] * 3.0 + df["tiros_a_puerta"] * 1.5) / partidos
    ataque = np.minimum(10.0, score_ataque * 1.2) * factor_experiencia

    pases_volumen = df["pases_totales"] / minutos
    factor_peligro = (df["pases_clave"] * 3.0 + df["asistencias"] * 5.0) / partidos
    factor_eficiencia = (df["precision_pases"] / 100.0) * pases_volumen * 10.0
    score_creacion = (factor_peligro * 1.3) + (factor_eficiencia * 0.7)
    creacion = np.minimum(10.0, score_creacion) * factor_experiencia

    defensivo = (df["entradas"] + df["intercepciones"] + df["bloqueos"]) / partidos
    penalizacion_def = (
        (df["goles_concedidos"] * 0.8) + (df["amarillas"] * 0.5) + (df["regateado"] * 0.3)
    ) / partidos
    defensa = np.maximum(0.0, np.minimum(10.0, (defensivo - penalizacion_def) * 1.5)) * factor_experiencia

    ratio_paradas = df["paradas"] / (df["goles_concedidos"] + 1.0)
    goles_pp = df["goles_concedidos"] / partidos
    factor_muro = np.maximum(0.0, 5.0 - (goles_pp * 2.0))
    score_portero = (ratio_paradas * 1.5) + factor_muro + (df["penaltis_parados"] * 2.0)
    portero_bruto = np.minimum(10.0, score_portero) * factor_experiencia
    porteros = np.where(df["posicion_norm"] == "Portero", portero_bruto, 0.0)

    ratio_duelos = df["duelos_ganados"] / (df["duelos_totales"] + RATIO_SMOOTH)
    volumen_duelos = df["duelos_totales"] / partidos
    duelos = np.minimum(10.0, (ratio_duelos * 7.0) + (volumen_duelos * 0.3)) * factor_experiencia

    ratio_regates = df["regates_exito"] / (df["regates_intentados"] + RATIO_SMOOTH)
    regates_partido = df["regates_exito"] / partidos
    faltas_sufridas = df["faltas_sufridas"] / partidos
    regates = (
        np.minimum(10.0, (ratio_regates * 6.0) + (regates_partido * 1.5) + (faltas_sufridas * 0.5))
        * factor_experiencia
    )

    out = df.copy()
    out["ataque"] = ataque
    out["creacion"] = creacion
    out["defensa"] = defensa
    out["porteros"] = porteros
    out["duelos"] = duelos
    out["regates"] = regates
    out["factor_experiencia"] = factor_experiencia
    return out


def main() -> None:
    df = pd.read_csv(INPUT_SEASON_FILE, sep=";")
    df_names = pd.read_csv(INPUT_PLAYERS_FILE, sep=";")

    df.columns = df.columns.str.strip()
    df_names.columns = df_names.columns.str.strip()

    validate_columns(df, REQUIRED_SEASON_COLUMNS, "h_jugador_temporada.csv")
    validate_columns(df_names, ["id_jugador", "nombre"], "dim_jugadores.csv")

    for col, default in OPTIONAL_SEASON_COLUMNS_WITH_DEFAULT.items():
        if col not in df.columns:
            df[col] = default

    numeric_cols = list(dict.fromkeys(REQUIRED_SEASON_COLUMNS + list(OPTIONAL_SEASON_COLUMNS_WITH_DEFAULT.keys())))
    numeric_cols.remove("id_jugador")
    numeric_cols.remove("posicion")
    df = to_numeric(df, numeric_cols)

    df["id_jugador"] = pd.to_numeric(df["id_jugador"], errors="coerce")
    df = df.dropna(subset=["id_jugador", "temporada"]).copy()
    df["id_jugador"] = df["id_jugador"].astype(int)

    fill_zero_cols = [c for c in numeric_cols if c != "precision_pases"]
    df[fill_zero_cols] = df[fill_zero_cols].fillna(0.0)
    df["precision_pases"] = df["precision_pases"].fillna(df["precision_pases"].median())

    df["posicion_norm"] = df["posicion"].apply(normalize_position)
    df["peso_temp"] = df["temporada"].apply(temporal_weight)

    scored = build_scores(df)

    for col in FEATURES:
        scored[col] = scored[col] * scored["peso_temp"]

    grouped = scored.groupby("id_jugador", as_index=False).agg(
        ataque=("ataque", "sum"),
        creacion=("creacion", "sum"),
        defensa=("defensa", "sum"),
        porteros=("porteros", "sum"),
        duelos=("duelos", "sum"),
        regates=("regates", "sum"),
        peso_temp=("peso_temp", "sum"),
        partidos_totales=("partidos", "sum"),
        minutos_totales=("minutos", "sum"),
    )

    grouped["peso_temp"] = grouped["peso_temp"].replace(0, np.nan)
    for col in FEATURES:
        grouped[col] = (grouped[col] / grouped["peso_temp"]).fillna(0.0).round(2)

    conf_partidos = (grouped["partidos_totales"] / 25.0).clip(upper=1.0)
    conf_minutos = (grouped["minutos_totales"] / 1800.0).clip(upper=1.0)
    grouped["confianza_datos"] = np.minimum(conf_partidos, conf_minutos).round(3)

    grouped = grouped.drop(columns=["peso_temp"]) 

    result = grouped.merge(df_names[["id_jugador", "nombre"]], on="id_jugador", how="left")

    ordered_cols = [
        "id_jugador",
        "nombre",
        "ataque",
        "creacion",
        "defensa",
        "porteros",
        "duelos",
        "regates",
        "confianza_datos",
        "partidos_totales",
        "minutos_totales",
    ]
    result = result[ordered_cols].sort_values(["confianza_datos", "ataque"], ascending=[False, False])

    result.to_csv(OUTPUT_FILE, index=False, sep=";", encoding="utf-8-sig")

    print(f"Archivo generado: {OUTPUT_FILE}")
    print(f"Jugadores procesados: {len(result)}")


if __name__ == "__main__":
    main()
