import pandas as pd
import numpy as np
from pathlib import Path


BASE_DIR = Path(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATA_MINING\DSA_DM')
OUTPUT_FILE = BASE_DIR / "PROBABLES_GOLEADORES.csv"


# 1. CARGA DE DATOS
df_partidos = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\dim_partidos2.csv', sep=';')
df_h_jugador_partido = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\h_jugador_partido.csv', sep=';')
df_h_jugador_temporada = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\h_jugador_temporada.csv', sep=';')
df_dim_jugadores = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\dim_jugadores.csv', sep=';')

for df in [df_partidos, df_h_jugador_partido, df_h_jugador_temporada, df_dim_jugadores]:
    df.columns = df.columns.str.strip()

print("Sincronizando plantillas de la temporada 2025...")

# --- FILTRO CRUCIAL: Solo jugadores activos en su club actual en 2025 ---
df_plantillas_2025 = df_h_jugador_temporada[df_h_jugador_temporada['temporada'] == 2025]
dict_nombres = df_dim_jugadores.set_index('id_jugador')['nombre'].to_dict()

# 2. PRE-CÁLCULOS (Misma lógica optimizada)
df_relacion = df_h_jugador_partido.merge(df_partidos[['id_partido', 'id_local', 'id_visitante']], on='id_partido')
df_relacion['id_rival'] = np.where(df_relacion['id_equipo'] == df_relacion['id_local'], 
                                   df_relacion['id_visitante'], 
                                   df_relacion['id_local'])

mapa_goles_rival = df_relacion.groupby(['id_jugador', 'id_rival'])['goles'].sum().to_dict()

# Racha (solo últimos 7)
df_h_jugador_partido = df_h_jugador_partido.sort_values(['id_jugador', 'id_partido'])
dict_racha = df_h_jugador_partido.groupby('id_jugador')['goles'].rolling(window=7, min_periods=1).mean().groupby(level=0).last().to_dict()

# 3. PROCESAMIENTO
partidos_pendientes = df_partidos[df_partidos['status'] == 'Incompleto']
resultados_probabilidad = []

for _, partido in partidos_pendientes.iterrows():
    id_partido = partido['id_partido']
    
    for id_equipo, id_rival in [(partido['id_local'], partido['id_visitante']), (partido['id_visitante'], partido['id_local'])]:
        
        # AQUÍ ESTÁ EL CAMBIO: Solo jugadores que ESTÁN en este equipo en 2025
        jugadores_reales = df_plantillas_2025[df_plantillas_2025['id_equipo'] == id_equipo]
        scores_jugadores = []
        
        for _, jug in jugadores_reales.iterrows():
            id_jugador = jug['id_jugador']
            
            forma_score = dict_racha.get(id_jugador, 0)
            # Goles en la temporada actual / partidos temporada actual
            promedio_2025 = jug['goles'] / max(jug['partidos'], 1)
            goles_vs_rival = mapa_goles_rival.get((id_jugador, id_rival), 0)

            # MODELO RE-CALIBRADO
            # Bajamos los pesos para que la probabilidad sea más realista (entre 0.10 y 0.45 normalmente)
            logit_score = (forma_score * 0.35) + (promedio_2025 * 0.45) + (min(goles_vs_rival, 3) * 0.05)
            
            # Sigmoide con factor de escala suavizado (0.8 en lugar de 4)
            # Esto evita que los cracks salten directamente al 99%
            probabilidad = 1 / (1 + np.exp(-(logit_score - 0.5) * 2))
            
            # Ajuste final: La probabilidad de marcar un gol en un partido real rara vez supera el 60% 
            # para jugadores de élite (exceptuando casos históricos muy raros).
            probabilidad = min(probabilidad, 0.75) 

            scores_jugadores.append((id_jugador, dict_nombres.get(id_jugador, "N/A"), round(probabilidad, 3)))

        # Top 3 (sin duplicados)
        top_3 = sorted(scores_jugadores, key=lambda x: x[2], reverse=True)[:3]
        
        for id_j, nom, prob in top_3:
            resultados_probabilidad.append({
                'id_partido': id_partido,
                'id_equipo': id_equipo,
                'id_jugador': id_j,
                'nombre_jugador': nom,
                'probabilidad': prob
            })

# 4. EXPORTAR
df_final = pd.DataFrame(resultados_probabilidad)
df_final.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')