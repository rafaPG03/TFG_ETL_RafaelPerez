import pandas as pd
import numpy as np

# 1. CARGA DE DATOS
ruta_base = r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA'

df_h_partido_raw = pd.read_csv(f'{ruta_base}\h_jugador_partido.csv', sep=';')
df_h_temporada = pd.read_csv(f'{ruta_base}\h_jugador_temporada.csv', sep=';')
df_dim_jug = pd.read_csv(f'{ruta_base}\dim_jugadores.csv', sep=';')
df_dim_partidos = pd.read_csv(f'{ruta_base}\dim_partidos2.csv', sep=';') # Necesario para filtrar la fecha

# Limpieza de columnas
for df in [df_h_partido_raw, df_h_temporada, df_dim_jug, df_dim_partidos]:
    df.columns = df.columns.str.strip()

print("Sincronizando plantillas y filtrando partidos de la temporada 2025...")

# --- FILTRO MAESTRO DE TEMPORADA 2025 ---

# A. Filtramos la tabla de partidos para quedarnos solo con los de 2025
partidos_2025 = df_dim_partidos[df_dim_partidos['temporada'] == 2025]['id_partido'].unique()

# B. Filtramos h_jugador_partido para que SOLO tenga datos de 2025 (Solución al error de Yeremy Pino)
df_h_partido = df_h_partido_raw[df_h_partido_raw['id_partido'].isin(partidos_2025)].copy()

# C. Jugadores que están en la base de datos para la temporada 2025
jugadores_2025 = df_h_temporada[df_h_temporada['temporada'] == 2025]

# Mapeos rápidos
dict_nombres = df_dim_jug.set_index('id_jugador')['nombre'].to_dict()

# 2. LÓGICA DE SCORE ORIGINAL (PONDERADA)
metricas_pos = {
    'Portero': {'pos': ['paradas', 'penaltis_parados'], 'neg': ['goles_concedidos']},
    'Defensa': {'pos': ['intercepciones', 'entradas', 'bloqueos', 'duelos_ganados'], 'neg': ['amarillas', 'goles_concedidos']},
    'Mediocentro': {'pos': ['asistencias', 'pases_clave', 'regates_exito', 'precision_pases'], 'neg': ['faltas_cometidas']},
    'Delantero': {'pos': ['goles', 'tiros_a_puerta', 'regates_exito', 'pases_clave'], 'neg': []}
}

def calcular_custom_score(row, pos):
    if pos not in metricas_pos: return row.get('nota', 0)
    config = metricas_pos[pos]
    
    # Restauramos pesos originales: Nota (50%) + Acciones (50%)
    score = row.get('nota', 0) * 0.5 
    for m in config['pos']:
        mult = 2.0 if m in ['goles', 'asistencias'] else 1.0
        score += (row.get(m, 0) * mult)
    for m in config['neg']:
        score -= (row.get(m, 0) * 1.2)
    return score

# 3. PROCESAMIENTO
resultados = []

for _, row_t in jugadores_2025.iterrows():
    id_j = row_t['id_jugador']
    pos = row_t['posicion']
    
    # Benchmark de temporada (basado solo en 2025 por la carga de datos)
    score_medio_temp = calcular_custom_score(row_t, pos) / max(row_t['partidos'], 1)
    
    # Últimos 7 partidos del jugador SOLO en 2025
    ultimos_partidos_all = df_h_partido[df_h_partido['id_jugador'] == id_j].sort_values('id_partido', ascending=False).head(7)
    
    # Filtrar por minutos para veracidad estadística
    partidos_validos = ultimos_partidos_all[ultimos_partidos_all['minutos'] >= 20]
    
    if len(partidos_validos) < 3:
        estado = "Pocos minutos"
        media_reciente = 0
        diff = 0
    else:
        scores_recientes = []
        for _, row_p in partidos_validos.iterrows():
            row_p_map = row_p.rename({'regates': 'regates_exito', 'amarilla': 'amarillas'})
            scores_recientes.append(calcular_custom_score(row_p_map, pos))
        
        media_reciente = np.mean(scores_recientes)
        diff = media_reciente - score_medio_temp
        
        if diff > 3:
            estado = "Rendimiento Alto"
        elif diff < -0.7:
            estado = "Rendimiento Bajo"
        else:
            estado = "Estable"

    resultados.append({
        'id_jugador': id_j,
        'nombre_jugador': dict_nombres.get(id_j, "N/A"),
        'id_equipo': row_t['id_equipo'],
        'posicion': pos,
        'estado': estado,
        'score_temporada': round(score_medio_temp, 2),
        'score_reciente': round(media_reciente, 2),
        'evolucion': round(diff, 2)
    })

# 4. EXPORTACIÓN
df_final = pd.DataFrame(resultados)
df_final.to_csv('ESTADO_FORMA_JUGADORES_2025.csv', index=False, sep=';', encoding='utf-8-sig')

print(f"Análisis blindado completado. Se han procesado {len(df_final)} jugadores de la temporada actual.")