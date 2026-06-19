import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import numpy as np

# 1. CARGA Y PREPARACIÓN
CARPETA_CLASIFICACION = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\h_equipo_jornada.csv"
full_data = pd.read_csv(CARPETA_CLASIFICACION, sep=';')

# Nos quedamos con la ultima jornada disponible por equipo y temporada
full_data = (
    full_data.sort_values(["temporada", "id_equipo", "jornada"])
    .groupby(["temporada", "id_equipo"], as_index=False)
    .tail(1)
)

# Ingeniería de atributos (Tus fórmulas originales)
full_data["partidos_restantes"] = 38 - full_data["partidos_jugados"]
full_data["pts/pj"] = (full_data["puntos"] / full_data["partidos_jugados"])
full_data["ptos_proyectados"] = full_data["puntos"] + full_data["partidos_restantes"] * full_data["pts/pj"]

# --- NUEVA LÓGICA: Definición de etiquetas multiclase ---
def asignar_objetivo(pos):
    if pos == 1: return "1. Campeon"
    elif 2 <= pos <= 4: return "2. Champions"
    elif 5 <= pos <= 6: return "3. Europa League"
    elif pos == 7: return "4. Conference"
    elif 8 <= pos <= 17: return "5. Media Tabla"
    elif 18 <= pos <= 20: return "6. Descenso"
    return "Otros"

full_data["objetivo"] = full_data["posicion"].apply(asignar_objetivo)

# 2. SEPARACIÓN DE DATOS
medidas = ["pts/pj", "dg", "victorias", "derrotas", "ptos_proyectados"]

df_train = full_data[full_data["temporada"] < 2025].copy()
df_test = full_data[full_data["temporada"] == 2025].copy()

X_train = df_train[medidas]
y_train = df_train["objetivo"]
X_test = df_test[medidas]

# 3. ENTRENAMIENTO DEL MODELO MULTICLASE
model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X_train, y_train)

# 4. EVALUACIÓN (Datos Históricos)
train_preds = model.predict(X_train)
print(f"\n--- Modelo Multiclase (Datos Históricos) ---")
print(f"Precision Global: {accuracy_score(y_train, train_preds):.3f}")
print("\nClassification Report:")
print(classification_report(y_train, train_preds))

# 5. PREDICCIÓN 2025
# Obtenemos las probabilidades para cada clase
probs = model.predict_proba(X_test)
clases = model.classes_ # El orden de las columnas en 'probs'

# Añadimos cada probabilidad al dataframe de test
for i, nombre_clase in enumerate(clases):
    df_test[nombre_clase] = (probs[:, i] * 100).round(2)

# Calculamos la probabilidad total de Europa (1 al 7) sumando las columnas correspondientes
# Esto es muy útil para tu TFG
columnas_europa = ["1. Campeon", "2. Champions", "3. Europa League", "4. Conference"]
df_test["Prob_Europa_Total (%)"] = df_test[columnas_europa].sum(axis=1).round(2)

# 6. RESULTADOS FINALES
df_test = df_test.sort_values(["jornada", "ptos_proyectados"], ascending=[False, False])

print("\n--- Probabilidades por Objetivo Temporada 2025 ---")
columnas_print = ["nombre_equipo", "jornada", "ptos_proyectados", "1. Campeon", "2. Champions", 
                  "3. Europa League", "4. Conference", "Prob_Europa_Total (%)", 
                  "5. Media Tabla", "6. Descenso"]

print(df_test[columnas_print].to_string(index=False))


