import pandas as pd
import numpy as np

# ------------------------------
# Configuracion del usuario
# ------------------------------
# Ruta al CSV de probabilidades (elige el que corresponda a tu flujo)
PRED_PATH = r"c:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATA_MINING\DSA_DM\predicciones_partidos_incompletos.csv"
# PRED_PATH = r"c:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATA_MINING\DEMAS\PREDICCIONES_PARTIDOS\predicciones_partidos_incompletos.csv"

# Ruta a la clasificacion actual por jornada
TABLE_PATH = r"c:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\h_equipo_jornada.csv"

# Temporada a usar de la tabla (ajusta si no coincide con tus predicciones)
TEMPORADA_ACTUAL = 2025

# Opciones de desempate
DESEMPATE_DG = True  # usa una diferencia de goles minima simulada para desempatar
DESEMPATE_ALEATORIO = False  # si True, desempata con ruido aleatorio en cada simulacion

# Numero de simulaciones
N_SIMULACIONES = 10000
RNG_SEED = 42

# ------------------------------
# Carga de datos
# ------------------------------
pred = pd.read_csv(PRED_PATH)

# Normalizar columnas de probabilidades (por si llegan en %)
prob_cols = ["prob_victoria_local", "prob_empate", "prob_victoria_visitante"]
if pred[prob_cols].max().max() > 1.0:
    pred[prob_cols] = pred[prob_cols] / 100.0

# Asegurar que suman 1 (corrige posibles desviaciones)
pred[prob_cols] = pred[prob_cols].div(pred[prob_cols].sum(axis=1), axis=0)

# Tabla de clasificacion actual
h = pd.read_csv(TABLE_PATH, sep=";")

# Filtrar temporada y ultima jornada disponible
h_temporada = h[h["temporada"] == TEMPORADA_ACTUAL].copy()
if h_temporada.empty:
    raise ValueError("No hay datos en h_equipo_jornada.csv para la temporada indicada.")

ultima_jornada = h_temporada["jornada"].max()
tabla_actual = h_temporada[h_temporada["jornada"] == ultima_jornada].copy()

equipos = tabla_actual[["id_equipo", "nombre_equipo", "puntos", "dg"]].drop_duplicates("id_equipo")
equipos = equipos.sort_values("id_equipo").reset_index(drop=True)

equipo_ids = equipos["id_equipo"].to_numpy()
equipo_nombres = equipos["nombre_equipo"].to_numpy()
puntos_base = equipos["puntos"].to_numpy(dtype=float)
dg_base = equipos["dg"].to_numpy(dtype=float)

# Filtrar partidos a equipos presentes en la tabla
pred = pred[pred["id_local"].isin(equipo_ids) & pred["id_visitante"].isin(equipo_ids)].copy()

# Indices para actualizaciones rapidas
id_to_idx = {tid: i for i, tid in enumerate(equipo_ids)}
local_idx = pred["id_local"].map(id_to_idx).to_numpy()
visit_idx = pred["id_visitante"].map(id_to_idx).to_numpy()

p_local = pred["prob_victoria_local"].to_numpy()
p_empate = pred["prob_empate"].to_numpy()

n_partidos = len(pred)
if n_partidos == 0:
    raise ValueError("No hay partidos pendientes tras filtrar por equipos.")

# ------------------------------
# Simulacion Montecarlo
# ------------------------------
rng = np.random.default_rng(RNG_SEED)

# Contadores por rango
n_equipos = len(equipo_ids)
cont_campeon = np.zeros(n_equipos, dtype=int)
cont_champions = np.zeros(n_equipos, dtype=int)
cont_europa = np.zeros(n_equipos, dtype=int)
cont_mediatabla = np.zeros(n_equipos, dtype=int)
cont_desc = np.zeros(n_equipos, dtype=int)

for _ in range(N_SIMULACIONES):
    puntos = puntos_base.copy()
    dg = dg_base.copy()

    r = rng.random(n_partidos)
    victoria_local = r < p_local
    empate = (r >= p_local) & (r < (p_local + p_empate))
    visitante_victoria = ~victoria_local & ~empate

    # Puntos
    np.add.at(puntos, local_idx[victoria_local], 3)
    np.add.at(puntos, visit_idx[visitante_victoria], 3)
    np.add.at(puntos, local_idx[empate], 1)
    np.add.at(puntos, visit_idx[empate], 1)

    # Diferencia de goles simple para desempate
    if DESEMPATE_DG:
        np.add.at(dg, local_idx[victoria_local], 1)
        np.add.at(dg, visit_idx[victoria_local], -1)
        np.add.at(dg, visit_idx[visitante_victoria], 1)
        np.add.at(dg, local_idx[visitante_victoria], -1)

    # Orden final (puntos desc, dg desc, nombre asc o ruido aleatorio)
    if DESEMPATE_ALEATORIO:
        empate_key = rng.random(n_equipos)
    else:
        empate_key = equipo_nombres

    order = np.lexsort((empate_key, -dg, -puntos))
    posiciones = np.empty(n_equipos, dtype=int)
    posiciones[order] = np.arange(1, n_equipos + 1)

    cont_campeon += (posiciones == 1)
    cont_champions += (posiciones <= 4)
    cont_europa += (posiciones >= 5) & (posiciones <= 7)
    cont_mediatabla += (posiciones >= 8) & (posiciones <= 17)
    cont_desc += (posiciones >= 18)

# ------------------------------
# Resultados
# ------------------------------
result = pd.DataFrame({
    "id_equipo": equipo_ids,
    "equipo": equipo_nombres,
    "campeon_%": 100 * cont_campeon / N_SIMULACIONES,
    "champions_%": 100 * cont_champions / N_SIMULACIONES,
    "europa_%": 100 * cont_europa / N_SIMULACIONES,
    "media_tabla_%": 100 * cont_mediatabla / N_SIMULACIONES,
    "descenso_%": 100 * cont_desc / N_SIMULACIONES,
}).sort_values(["campeon_%", "champions_%", "europa_%"], ascending=False)

print(result.to_string(index=False))

# Guardar resultados en CSV
output_path = r"c:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATA_MINING\DSA_DM\simulacion_montecarlo_laliga_resultados.csv"
result.to_csv(output_path, index=False)
