import pandas as pd
import numpy as np
import pickle
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

# 1. CARGA DE DATOS
df_partidos = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\dim_partidos2.csv', sep=';')
df_hechos = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\h_equipo_partido.csv', sep=';')
df_equipos = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\dim_equipos.csv', sep=';')

# Convertir id_tiempo a fecha real (YYYYMMDD)
df_partidos['date'] = pd.to_datetime(df_partidos['id_tiempo'].astype(str), format='%Y%m%d')

# 2. PREPARACIÓN: Unir hechos con nombres de equipos y datos de partido
# Necesitamos una fila por equipo por partido (similar a team_stats_per_match)
df_merged = pd.merge(df_hechos, df_partidos, on='id_partido')
df_merged = pd.merge(df_merged, df_equipos[['id_equipo', 'nombre_equipo']], on='id_equipo')

# Determinar si el equipo fue Local o Visitante en ese partido
df_merged['is_home'] = np.where(df_merged['id_equipo'] == df_merged['id_local'], 'Home', 'Away')

# Crear columna de goles anotados y recibidos para ese equipo específico
df_merged['goals_scored'] = np.where(df_merged['is_home'] == 'Home', df_merged['goles_local'], df_merged['goles_visitante'])
df_merged['goals_conceded'] = np.where(df_merged['is_home'] == 'Home', df_merged['goles_visitante'], df_merged['goles_local'])

# 3. CÁLCULO DE PROMEDIOS (ENGINEERING)
# Ordenamos por fecha para que el rolling average sea correcto
df_merged = df_merged.sort_values(['id_equipo', 'date'])

def get_rolling_stats(df, window=10):
    stats_cols = ['tiros_a_puerta', 'tiros_totales', 'corners', 'posesion', 'goles_esperados']
    # Calculamos el promedio de los N partidos anteriores (sin incluir el actual)
    for col in stats_cols:
        df[f'avg_{col}_last_{window}'] = df.groupby('id_equipo')[col].transform(lambda x: x.shift().rolling(window, min_periods=1).mean())
    return df

df_final = get_rolling_stats(df_merged)

# 4. SEPARACIÓN: ENTRENAMIENTO VS PREDICCIÓN
# Partidos con resultado (Completados)
train_set = df_final[df_final['status'] == 'Completado'].dropna()

# Partidos por jugar (Incompletos)
upcoming_matches = df_final[df_final['status'] == 'Incompleto']

# 5. ENTRENAMIENTO (Ejemplo simplificado)
features = [col for col in df_final.columns if 'avg_' in col]
X = train_set[features]
y = train_set['goals_scored']

model = RandomForestRegressor(n_estimators=100).fit(X, y)

# 6. PREDICCIÓN
upcoming_matches['prediccion_goles'] = model.predict(upcoming_matches[features])

# Mostrar resultados
print(upcoming_matches[['date', 'nombre_equipo', 'is_home', 'prediccion_goles']])