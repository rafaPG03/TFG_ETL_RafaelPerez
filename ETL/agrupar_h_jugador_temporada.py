import argparse
from pathlib import Path

import pandas as pd


COLUMNAS = [
    "id_jugador",
    "id_equipo",
    "temporada",
    "posicion",
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

COLUMNAS_NUMERICAS = [
    "minutos",
    "nota",
    "goles",
    "penaltis_marcados",
    "asistencias",
    "paradas",
    "goles_concedidos",
    "tiros_totales",
    "tiros_a_puerta",
    "pases_totales",
    "pases_clave",
    "precision_pases",
    "regates_intentados",
    "regates",
    "regateado",
    "duelos_totales",
    "duelos_ganados",
    "faltas_cometidas",
    "faltas_recibidas",
    "entradas",
    "bloqueos",
    "intercepciones",
    "amarilla",
    "roja",
    "penaltis_parados",
]

COLUMNAS_SUMA_SALIDA = [
    "minutos",
    "titular",
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

COLUMNAS_ENTERAS_SALIDA = [
    "id_jugador",
    "id_equipo",
    "temporada",
    "partidos",
    "minutos",
    "titular",
    "goles",
    "asistencias",
    "tiros_totales",
    "tiros_a_puerta",
    "pases_totales",
    "pases_clave",
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

POSICION_MAP = {
    "P": "Portero",
    "DF": "Defensa",
    "M": "Mediocentro",
    "DL": "Delantero",
}


def parse_args() -> argparse.Namespace:
    script_path = Path(__file__).resolve()
    raiz = script_path.parents[1]
    default_input = raiz / "ETL" / "DSA" / "h_jugador_partido.csv"
    dim_partidos_2 = raiz / "ETL" / "DSA" / "dim_partidos2.csv"
    dim_partidos_1 = raiz / "ETL" / "DSA" / "dim_partidos.csv"
    default_dim_partidos = dim_partidos_2 if dim_partidos_2.exists() else dim_partidos_1
    default_output = raiz / "ETL" / "DSA" / "h_jugador_temporada_agrupado.csv"

    parser = argparse.ArgumentParser(
        description=(
            "Construye h_jugador_temporada desde h_jugador_partido y dim_partidos "
            "(para obtener temporada), y lo exporta con el mismo esquema."
        )
    )
    parser.add_argument("--input", type=Path, default=default_input, help="CSV h_jugador_partido")
    parser.add_argument(
        "--dim-partidos",
        type=Path,
        default=default_dim_partidos,
        help="CSV dim_partidos con id_partido y temporada",
    )
    parser.add_argument("--output", type=Path, default=default_output, help="CSV de salida")
    return parser.parse_args()


def validar_columnas(df: pd.DataFrame, requeridas: list[str], nombre_df: str) -> None:
    faltantes = [c for c in requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en {nombre_df}: {faltantes}")


def preparar_h_jugador_partido(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for c in COLUMNAS_NUMERICAS:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["id_partido"] = pd.to_numeric(df["id_partido"], errors="coerce")
    df["id_jugador"] = pd.to_numeric(df["id_jugador"], errors="coerce")
    df["id_equipo"] = pd.to_numeric(df["id_equipo"], errors="coerce")
    df = df.dropna(subset=["id_partido", "id_jugador", "id_equipo"]) 

    df["id_partido"] = df["id_partido"].astype(int)
    df["id_jugador"] = df["id_jugador"].astype(int)
    df["id_equipo"] = df["id_equipo"].astype(int)

    df["posicion"] = (
        df["posicion"]
        .fillna("Desconocida")
        .astype(str)
        .str.strip()
        .replace(POSICION_MAP)
    )

    # Titular = no entró como sustituto.
    df["sustituto"] = (
        df["sustituto"]
        .fillna(False)
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "si", "sí"])
    )
    df["titular"] = (~df["sustituto"]).astype(int)

    return df


def preparar_dim_partidos(df_partidos: pd.DataFrame) -> pd.DataFrame:
    df = df_partidos.copy()
    df["id_partido"] = pd.to_numeric(df["id_partido"], errors="coerce")
    df["temporada"] = pd.to_numeric(df["temporada"], errors="coerce")
    df = df.dropna(subset=["id_partido", "temporada"])
    df["id_partido"] = df["id_partido"].astype(int)
    df["temporada"] = df["temporada"].astype(int)
    return df[["id_partido", "temporada"]].drop_duplicates(subset=["id_partido"])


def construir_h_jugador_temporada(df_partidos_jugador: pd.DataFrame, df_dim_partidos: pd.DataFrame) -> pd.DataFrame:
    df = df_partidos_jugador.merge(df_dim_partidos, on="id_partido", how="inner")

    claves_base = ["id_jugador", "id_equipo", "temporada"]

    agregaciones = {c: "sum" for c in COLUMNAS_SUMA_SALIDA}
    agregaciones.update({"id_partido": "nunique"})

    # Nota media ponderada por minutos para reproducir bien el comportamiento de temporada.
    df["_peso_nota"] = df["minutos"].clip(lower=0)
    df["_nota_x_peso"] = df["nota"] * df["_peso_nota"]

    # Ajuste de nombres al formato final.
    df = df.rename(
        columns={
            "regates": "regates_exito",
            "faltas_recibidas": "faltas_sufridas",
            "amarilla": "amarillas",
            "roja": "rojas",
        }
    )

    # Posicion final: la que acumula mas minutos por jugador-equipo-temporada.
    minutos_pos = (
        df.groupby(claves_base + ["posicion"], as_index=False)["minutos"]
        .sum()
        .sort_values(claves_base + ["minutos", "posicion"], ascending=[True, True, True, False, True])
    )
    posicion_dominante = (
        minutos_pos.drop_duplicates(subset=claves_base, keep="first")
        .loc[:, claves_base + ["posicion"]]
    )

    agg = df.groupby(claves_base, as_index=False).agg(
        {
            **agregaciones,
            "_nota_x_peso": "sum",
            "_peso_nota": "sum",
        }
    )

    agg["nota_media"] = 0.0
    mask = agg["_peso_nota"] > 0
    agg.loc[mask, "nota_media"] = agg.loc[mask, "_nota_x_peso"] / agg.loc[mask, "_peso_nota"]
    agg["nota_media"] = agg["nota_media"].round(6)

    mask_partidos = agg["id_partido"] > 0
    agg.loc[mask_partidos, "precision_pases"] = (
        agg.loc[mask_partidos, "precision_pases"] / agg.loc[mask_partidos, "id_partido"]
    )
    agg.loc[~mask_partidos, "precision_pases"] = 0
    agg["precision_pases"] = agg["precision_pases"].round(2)

    agg = agg.rename(columns={"id_partido": "partidos"})

    agg = agg.drop(columns=["_nota_x_peso", "_peso_nota"])
    agg = agg.merge(posicion_dominante, on=claves_base, how="left")
    agg["posicion"] = agg["posicion"].fillna("Desconocida")

    for c in COLUMNAS_ENTERAS_SALIDA:
        agg[c] = pd.to_numeric(agg[c], errors="coerce").fillna(0).astype(int)

    agg = agg[COLUMNAS].sort_values(["temporada", "id_equipo", "id_jugador", "posicion"])
    return agg


def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"No existe el fichero de entrada: {args.input}")
    if not args.dim_partidos.exists():
        raise FileNotFoundError(f"No existe el fichero dim_partidos: {args.dim_partidos}")

    df_h_jugador_partido = pd.read_csv(args.input, sep=";", encoding="utf-8-sig")
    df_dim_partidos = pd.read_csv(args.dim_partidos, sep=";", encoding="utf-8-sig")

    validar_columnas(
        df_h_jugador_partido,
        [
            "id_partido",
            "id_jugador",
            "id_equipo",
            "posicion",
            "minutos",
            "nota",
            "sustituto",
            "goles",
            "penaltis_marcados",
            "asistencias",
            "paradas",
            "goles_concedidos",
            "tiros_totales",
            "tiros_a_puerta",
            "pases_totales",
            "pases_clave",
            "precision_pases",
            "regates_intentados",
            "regates",
            "regateado",
            "duelos_totales",
            "duelos_ganados",
            "faltas_cometidas",
            "faltas_recibidas",
            "entradas",
            "bloqueos",
            "intercepciones",
            "amarilla",
            "roja",
            "penaltis_parados",
        ],
        "h_jugador_partido",
    )
    validar_columnas(df_dim_partidos, ["id_partido", "temporada"], "dim_partidos")

    df_h_jugador_partido = preparar_h_jugador_partido(df_h_jugador_partido)
    df_dim_partidos = preparar_dim_partidos(df_dim_partidos)

    df_out = construir_h_jugador_temporada(df_h_jugador_partido, df_dim_partidos)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(args.output, sep=";", index=False, encoding="utf-8-sig")

    print(f"CSV agrupado generado en: {args.output}")
    print(f"Registros h_jugador_partido (entrada): {len(df_h_jugador_partido)}")
    print(f"Partidos con temporada disponible: {len(df_dim_partidos)}")
    print(f"Registros salida: {len(df_out)}")


if __name__ == "__main__":
    main()
