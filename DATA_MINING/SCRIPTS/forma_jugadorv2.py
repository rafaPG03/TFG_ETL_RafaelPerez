import pandas as pd
import numpy as np
from pathlib import Path

# 1. CARGA DE DATOS
ruta_base = r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA'


BASE_DIR = Path(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATA_MINING\DSA_DM')
OUTPUT_FILE = BASE_DIR / "ESTADO_FORMA_JUGADORES_2025.csv"



df_h_partidos_raw = pd.read_csv(f'{ruta_base}\h_jugador_partido.csv', sep=';')
df_dim_partidos = pd.read_csv(f'{ruta_base}\dim_partidos2.csv', sep=';')
df_dim_jug = pd.read_csv(f'{ruta_base}\dim_jugadores.csv', sep=';')

# Limpieza de columnas
for df in [df_h_partidos_raw, df_dim_partidos, df_dim_jug]:
    df.columns = df.columns.str.strip()

# 2. FILTRADO TEMPORADA 2025
# Unimos para saber la temporada de cada partido
df_merge = df_h_partidos_raw.merge(df_dim_partidos[['id_partido', 'temporada']], on='id_partido')
df_2025 = df_merge[df_merge['temporada'] == 2025].copy()

# Diccionarios auxiliares
dict_nombres = df_dim_jug.set_index('id_jugador')['nombre'].to_dict()

# 3. FUNCIÓN DE SCORE ÚNICA (Homogénea para todos los cálculos)
def calcular_score_unico(row):
    pos = str(row.get('posicion', '')).upper()
    nota_base = row.get('nota', 0)
    
    # Pesos de acciones (Nuevos atributos añadidos)
    score_acciones = 0
    
    # Goles y Asistencias (Impacto alto en todos)
    score_acciones += (row.get('goles', 0) * 1.5)
    score_acciones += (row.get('asistencias', 0) * 1.0)
    
    # Duelos (Todos menos porteros)
    if 'P' not in pos:
        # Ponderación neta de duelos: ganados suman, la diferencia aporta valor
        score_acciones += (row.get('duelos_ganados', 0) * 0.2)
        
    # Lógica por posición específica
    if 'DF' in pos or 'D' in pos: # Defensas
        score_acciones += (row.get('intercepciones', 0) * 0.4)
        score_acciones += (row.get('entradas', 0) * 0.3)
        score_acciones -= (row.get('regateado', 0) * 0.5) # Penalización por ser regateado
        score_acciones -= (row.get('goles_concedidos', 0) * 0.4)
        
    elif 'M' in pos: # Mediocentros
        score_acciones += (row.get('pases_clave', 0) * 0.5)
        score_acciones += (row.get('regates', 0) * 0.3)
        score_acciones += (row.get('precision_pases', 0) / 100) # Un pequeño extra por precisión
        
    elif 'D' in pos or 'A' in pos: # Delanteros / Atacantes
        score_acciones += (row.get('tiros_a_puerta', 0) * 0.5)
        score_acciones += (row.get('regates', 0) * 0.4)
        
    elif 'P' in pos: # Porteros
        score_acciones += (row.get('paradas', 0) * 0.6)
        score_acciones += (row.get('penaltis_parados', 0) * 2.0)
        score_acciones -= (row.get('goles_concedidos', 0) * 0.8)

    # El score final es una combinación de la nota (subjetiva) y las stats (objetivas)
    return round((nota_base * 0.6) + (score_acciones * 0.4), 2)

# 4. PROCESAMIENTO POR JUGADOR
# Calculamos el score para cada fila de la tabla
df_2025['score_calculado'] = df_2025.apply(calcular_score_unico, axis=1)

resultados = []
jugadores_unicos = df_2025['id_jugador'].unique()

print("Analizando momentum con métricas unificadas...")

for id_j in jugadores_unicos:
    # Historial del jugador en 2025
    df_jugador = df_2025[df_2025['id_jugador'] == id_j].sort_values('id_partido', ascending=False)
    
    # A. Media de la Temporada (Benchmark)
    # Solo contamos partidos donde jugó minutos significativos para la media
    partidos_validos_temp = df_jugador[df_jugador['minutos'] >= 15]
    if len(partidos_validos_temp) == 0: continue
    
    media_temporada = partidos_validos_temp['score_calculado'].mean()
    
    # B. Media Reciente (Últimos 7)
    df_reciente = df_jugador.head(7)
    partidos_validos_rec = df_reciente[df_reciente['minutos'] >= 20]
    
    # Determinación de estado
    if len(partidos_validos_rec) < 3:
        estado = "Pocos minutos"
        media_reciente = 0
        evolucion = 0
    else:
        media_reciente = partidos_validos_rec['score_calculado'].mean()
        evolucion = media_reciente - media_temporada
        
        if evolucion > 0.3:
            estado = "Rendimiento Alto"
        elif evolucion < -0.3:
            estado = "Rendimiento Bajo"
        else:
            estado = "Estable"

    resultados.append({
        'id_jugador': id_j,
        'nombre_jugador': dict_nombres.get(id_j, "N/A"),
        'id_equipo': df_jugador.iloc[0]['id_equipo'],
        'estado': estado,
        'score_temporada': round(media_temporada, 2),
        'score_reciente': round(media_reciente, 2),
        'evolucion': round(evolucion, 2)
    })

# 5. EXPORTAR
df_momentum_final = pd.DataFrame(resultados)
df_momentum_final.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')

print(f"Completado. Se han analizado {len(df_momentum_final)} jugadores bajo el nuevo criterio único.")