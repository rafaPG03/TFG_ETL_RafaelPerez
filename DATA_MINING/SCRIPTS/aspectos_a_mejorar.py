import pandas as pd
from pathlib import Path

# 0) CONFIGURACION GENERAL
# Porcentaje de corte: 0.25 = 25% por debajo/encima de la media
THRESHOLD_PCT = 0.1

ROOT_DIR = Path(__file__).resolve().parents[2]
INPUT_DIR = ROOT_DIR / "ETL" / "DSA"
OUTPUT_DIR = Path(r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATA_MINING\DSA_DM")
OUTPUT_FILE = OUTPUT_DIR / "NECESIDADES_REFUERZO_EQUIPO.csv"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PATH_JUGADOR_TEMP = INPUT_DIR / "h_jugador_temporada_agrupado.csv"
PATH_EQUIPO_JORNADA = INPUT_DIR / "h_equipo_jornada.csv"

# 1) CARGA DE DATOS (CSV)
df_jugador_temp = pd.read_csv(PATH_JUGADOR_TEMP, sep=";", low_memory=False)
df_equipo_jornada = pd.read_csv(PATH_EQUIPO_JORNADA, sep=";", low_memory=False)

# Limpieza basica
df_jugador_temp.columns = df_jugador_temp.columns.str.strip()
df_equipo_jornada.columns = df_equipo_jornada.columns.str.strip()

required_jugador_cols = {
    "id_jugador",
    "id_equipo",
    "temporada",
    "posicion",
    "minutos",
    "asistencias",
    "pases_totales",
    "pases_clave",
    "precision_pases",
    "regates_intentados",
    "regates_exito",
    "regateado",
    "faltas_cometidas",
    "intercepciones",
    "entradas",
    "bloqueos",
    "paradas",
    "goles_concedidos",
}
missing_jugador_cols = required_jugador_cols - set(df_jugador_temp.columns)
if missing_jugador_cols:
    raise ValueError(f"Faltan columnas en h_jugador_temporada_agrupado.csv: {sorted(missing_jugador_cols)}")

required_equipo_cols = {
    "id_equipo",
    "temporada",
    "jornada",
    "nombre_equipo",
    "gf",
    "gc",
}
missing_equipo_cols = required_equipo_cols - set(df_equipo_jornada.columns)
if missing_equipo_cols:
    raise ValueError(f"Faltan columnas en h_equipo_jornada.csv: {sorted(missing_equipo_cols)}")

# 2) TOTALES DE EQUIPO POR TEMPORADA
# Tomamos la ultima jornada para obtener acumulados de gf y gc
df_equipo_jornada = df_equipo_jornada.sort_values(["temporada", "id_equipo", "jornada"])
df_equipo_temp = (
    df_equipo_jornada
    .groupby(["temporada", "id_equipo"], as_index=False)
    .tail(1)
    .reset_index(drop=True)
)

# Promedios de liga por temporada
liga_gf_gc = (
    df_equipo_temp
    .groupby("temporada", as_index=False)
    .agg(gf_media=("gf", "mean"), gc_media=("gc", "mean"))
)

# 3) AGREGADOS POR POSICION (equipo-temporada)
numeric_cols = [
    "minutos",
    "asistencias",
    "pases_totales",
    "pases_clave",
    "regates_intentados",
    "regates_exito",
    "regateado",
    "faltas_cometidas",
    "intercepciones",
    "entradas",
    "bloqueos",
    "paradas",
    "goles_concedidos",
]

df_pos = (
    df_jugador_temp
    .groupby(["temporada", "id_equipo", "posicion"], as_index=False)[numeric_cols]
    .sum()
)

# Metricas derivadas por 90 minutos
def per90(series, minutes):
    return series / minutes * 90.0 if minutes > 0 else 0.0

rows = []
for _, row in df_pos.iterrows():
    minutes = row["minutos"]
    pases_totales = row["pases_totales"]
    reg_int = row["regates_intentados"]
    reg_ex = row["regates_exito"]

    rows.append({
        "temporada": row["temporada"],
        "id_equipo": row["id_equipo"],
        "posicion": row["posicion"],
        "minutos": minutes,
        "asistencias_p90": per90(row["asistencias"], minutes),
        "pases_totales_p90": per90(pases_totales, minutes),
        "pases_clave_p90": per90(row["pases_clave"], minutes),
        "faltas_cometidas_p90": per90(row["faltas_cometidas"], minutes),
        "intercepciones_p90": per90(row["intercepciones"], minutes),
        "entradas_p90": per90(row["entradas"], minutes),
        "bloqueos_p90": per90(row["bloqueos"], minutes),
        "regateado_p90": per90(row["regateado"], minutes),
        "paradas_p90": per90(row["paradas"], minutes),
        "goles_concedidos_p90": per90(row["goles_concedidos"], minutes),
        "regates_exito_rate": (reg_ex / reg_int) if reg_int > 0 else 0.0,
    })

df_pos_metrics = pd.DataFrame(rows)

# Calculo de precision de pases ponderada por equipo-temporada-posicion
passes_weighted = (
    df_jugador_temp
    .assign(pases_x_precision=lambda x: x["pases_totales"] * x["precision_pases"])
    .groupby(["temporada", "id_equipo", "posicion"], as_index=False)
    .agg(pases_totales=("pases_totales", "sum"), pases_x_precision=("pases_x_precision", "sum"))
)
passes_weighted["precision_pases"] = passes_weighted.apply(
    lambda r: r["pases_x_precision"] / r["pases_totales"] if r["pases_totales"] > 0 else 0.0,
    axis=1,
)

df_pos_metrics = df_pos_metrics.merge(
    passes_weighted[["temporada", "id_equipo", "posicion", "precision_pases"]],
    on=["temporada", "id_equipo", "posicion"],
    how="left",
)

# Benchmarks de liga por temporada y posicion
bench = (
    df_pos_metrics
    .groupby(["temporada", "posicion"], as_index=False)
    .agg(
        asistencias_p90_media=("asistencias_p90", "mean"),
        pases_totales_p90_media=("pases_totales_p90", "mean"),
        pases_clave_p90_media=("pases_clave_p90", "mean"),
        precision_pases_media=("precision_pases", "mean"),
        faltas_cometidas_p90_media=("faltas_cometidas_p90", "mean"),
        intercepciones_p90_media=("intercepciones_p90", "mean"),
        entradas_p90_media=("entradas_p90", "mean"),
        bloqueos_p90_media=("bloqueos_p90", "mean"),
        regateado_p90_media=("regateado_p90", "mean"),
        paradas_p90_media=("paradas_p90", "mean"),
        goles_concedidos_p90_media=("goles_concedidos_p90", "mean"),
        regates_exito_rate_media=("regates_exito_rate", "mean"),
    )
)

def is_low(value, mean, pct):
    return value <= (1 - pct) * mean

def is_high(value, mean, pct):
    return value >= (1 + pct) * mean

# 4) REGLAS DE NECESIDAD POR EQUIPO Y TEMPORADA
resultados = []

for _, eq in df_equipo_temp.iterrows():
    temporada = eq["temporada"]
    id_equipo = eq["id_equipo"]
    nombre_equipo = eq["nombre_equipo"]

    gf = eq["gf"]
    gc = eq["gc"]

    gf_media = liga_gf_gc[liga_gf_gc["temporada"] == temporada]["gf_media"].iloc[0]
    gc_media = liga_gf_gc[liga_gf_gc["temporada"] == temporada]["gc_media"].iloc[0]

    # Datos por posicion
    pos_data = df_pos_metrics[
        (df_pos_metrics["temporada"] == temporada) &
        (df_pos_metrics["id_equipo"] == id_equipo)
    ]

    needs = []

    # 1) Pocos goles vs media -> Delanteros
    if is_low(gf, gf_media, THRESHOLD_PCT):
        needs.append((
            "Delantero",
            "Pocos goles respecto a la media de la liga"
        ))

    # 2) Delanteros con regate y asistencias bajos -> Extremo
    fw = pos_data[pos_data["posicion"] == "Delantero"]
    if not fw.empty:
        fw = fw.iloc[0]
        fw_bench = bench[(bench["temporada"] == temporada) & (bench["posicion"] == "Delantero")].iloc[0]
        if (
            is_low(fw["regates_exito_rate"], fw_bench["regates_exito_rate_media"], THRESHOLD_PCT)
            and is_low(fw["asistencias_p90"], fw_bench["asistencias_p90_media"], THRESHOLD_PCT)
        ):
            needs.append((
                "Extremo",
                "Delanteros con regate y asistencias por debajo de la media"
            ))

    # 3) Mediocentros con malos pases, pases clave y asistencias -> Medio ofensivo
    mid = pos_data[pos_data["posicion"] == "Mediocentro"]
    if not mid.empty:
        mid = mid.iloc[0]
        mid_bench = bench[(bench["temporada"] == temporada) & (bench["posicion"] == "Mediocentro")].iloc[0]
        if (
            is_low(mid["precision_pases"], mid_bench["precision_pases_media"], THRESHOLD_PCT)
            and is_low(mid["pases_clave_p90"], mid_bench["pases_clave_p90_media"], THRESHOLD_PCT)
            and is_low(mid["asistencias_p90"], mid_bench["asistencias_p90_media"], THRESHOLD_PCT)
        ):
            needs.append((
                "Medio ofensivo",
                "Mediocentros con pases clave y asistencias bajas"
            ))

        # 4) Mediocentros con muchas faltas, malos pases y pocas intercepciones -> Pivote defensivo
        if (
            is_high(mid["faltas_cometidas_p90"], mid_bench["faltas_cometidas_p90_media"], THRESHOLD_PCT)
            and is_low(mid["precision_pases"], mid_bench["precision_pases_media"], THRESHOLD_PCT)
            and is_low(mid["intercepciones_p90"], mid_bench["intercepciones_p90_media"], THRESHOLD_PCT)
        ):
            needs.append((
                "Pivote defensivo",
                "Mediocentros con muchas faltas y baja recuperacion"
            ))

    # 5) Defensas con pocas asistencias y muchos regateados -> Laterales
    dfc = pos_data[pos_data["posicion"] == "Defensa"]
    if not dfc.empty:
        dfc = dfc.iloc[0]
        dfc_bench = bench[(bench["temporada"] == temporada) & (bench["posicion"] == "Defensa")].iloc[0]
        if (
            is_low(dfc["asistencias_p90"], dfc_bench["asistencias_p90_media"], THRESHOLD_PCT)
            and is_high(dfc["regateado_p90"], dfc_bench["regateado_p90_media"], THRESHOLD_PCT)
        ):
            needs.append((
                "Laterales",
                "Defensas con pocas asistencias y muchos regateados"
            ))

        # 6) Defensas con malos datos defensivos y muchos goles encajados -> Central
        if (
            is_high(gc, gc_media, THRESHOLD_PCT)
            and is_low(dfc["entradas_p90"], dfc_bench["entradas_p90_media"], THRESHOLD_PCT)
            and is_low(dfc["bloqueos_p90"], dfc_bench["bloqueos_p90_media"], THRESHOLD_PCT)
            and is_low(dfc["intercepciones_p90"], dfc_bench["intercepciones_p90_media"], THRESHOLD_PCT)
        ):
            needs.append((
                "Central",
                "Defensas con bajos aportes defensivos y muchos goles encajados"
            ))

    # 7) Porteros con pocas paradas y muchos goles concedidos -> Portero
    gk = pos_data[pos_data["posicion"] == "Portero"]
    if not gk.empty:
        gk = gk.iloc[0]
        gk_bench = bench[(bench["temporada"] == temporada) & (bench["posicion"] == "Portero")].iloc[0]
        if (
            is_low(gk["paradas_p90"], gk_bench["paradas_p90_media"], THRESHOLD_PCT)
            and is_high(gk["goles_concedidos_p90"], gk_bench["goles_concedidos_p90_media"], THRESHOLD_PCT)
        ):
            needs.append((
                "Portero",
                "Porteros con pocas paradas y muchos goles encajados"
            ))

    if not needs:
        needs.append(("Sin necesidad clara", "Sin senales negativas relevantes"))

    for necesidad, motivo in needs:
        resultados.append({
            "id_equipo": id_equipo,
            "nombre_equipo": nombre_equipo,
            "temporada": temporada,
            "necesidad": necesidad,
            "motivo": motivo,
            "umbral_pct": THRESHOLD_PCT,
        })

# 5) EXPORTACION
df_resultados = pd.DataFrame(resultados)
df_resultados.to_csv(OUTPUT_FILE, index=False, sep=";", encoding="utf-8-sig")

print(f"CSV generado en: {OUTPUT_FILE}")