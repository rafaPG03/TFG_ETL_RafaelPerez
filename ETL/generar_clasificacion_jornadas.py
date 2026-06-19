import pandas as pd
import numpy as np
from collections import defaultdict

# Leer los archivos necesarios
dim_partidos = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\dim_partidos2.csv', sep=';')
dim_tiempo = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\dim_tiempo.csv', sep=';')
dim_equipos = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\dim_equipos.csv', sep=';')
h_equipo_temporada = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\h_equipo_temporada.csv', sep=';')

# Merge para obtener jornada en dim_partidos
dim_partidos['id_tiempo'] = dim_partidos['id_tiempo'].astype(str)
dim_tiempo['id_tiempo'] = dim_tiempo['id_tiempo'].astype(str)

partidos = dim_partidos.merge(dim_tiempo[['id_tiempo', 'jornada']], on='id_tiempo', how='left')

# Filtrar solo partidos completados
partidos = partidos[partidos['status'] == 'Completado']

# Normalizar tipos numéricos para evitar floats en cálculos y salida.
columnas_int_partidos = ['temporada', 'jornada', 'id_local', 'id_visitante', 'goles_local', 'goles_visitante']
for col in columnas_int_partidos:
    partidos[col] = pd.to_numeric(partidos[col], errors='coerce').astype('Int64')

partidos = partidos.dropna(subset=columnas_int_partidos)

# Crear mapeo de id_equipo a nombre_equipo
equipo_id_a_nombre = dict(zip(dim_equipos['id_equipo'], dim_equipos['nombre_equipo']))

# Ordenar partidos por temporada y jornada
partidos = partidos.sort_values(['temporada', 'jornada'], ascending=True)

# Estructura para guardar clasificación por jornada
clasificacion_jornadas = []

# Por cada temporada
for temporada in sorted(partidos['temporada'].unique()):
    partidos_temp = partidos[partidos['temporada'] == temporada]
    
    # Estructura para acumular stats por equipo
    stats_por_equipo = defaultdict(lambda: {
        'posicion': 0,
        'nombre_equipo': '',
        'puntos': 0,
        'dg': 0,
        'forma': '',
        'partidos_jugados': 0,
        'victorias': 0,
        'empates': 0,
        'derrotas': 0,
        'gf': 0,
        'gc': 0,
        'partidos_jugados_local': 0,
        'victorias_local': 0,
        'empates_local': 0,
        'derrotas_local': 0,
        'gf_local': 0,
        'gc_local': 0,
        'partidos_jugados_visitante': 0,
        'victorias_visitante': 0,
        'empates_visitante': 0,
        'derrotas_visitante': 0,
        'gf_visitante': 0,
        'gc_visitante': 0,
        'resultados': []
    })
    
    # Obtener todos los equipos de esa temporada
    equipos_temp = h_equipo_temporada[h_equipo_temporada['temporada'] == temporada]['id_equipo'].unique()
    for equipo_id in equipos_temp:
        stats_por_equipo[equipo_id]['nombre_equipo'] = equipo_id_a_nombre.get(equipo_id, f'Equipo {equipo_id}')
    
    # Procesar jornadas
    for jornada in sorted(partidos_temp['jornada'].dropna().unique()):
        partidos_jornada = partidos_temp[partidos_temp['jornada'] == jornada]
        
        # Procesar cada partido de la jornada
        for idx, partido in partidos_jornada.iterrows():
            id_local = int(partido['id_local'])
            id_visitante = int(partido['id_visitante'])
            goles_local = int(partido['goles_local'])
            goles_visitante = int(partido['goles_visitante'])
            
            # Actualizar estadísticas del equipo local
            stats_por_equipo[id_local]['partidos_jugados'] += 1
            stats_por_equipo[id_local]['partidos_jugados_local'] += 1
            stats_por_equipo[id_local]['gf'] += goles_local
            stats_por_equipo[id_local]['gf_local'] += goles_local
            stats_por_equipo[id_local]['gc'] += goles_visitante
            stats_por_equipo[id_local]['gc_local'] += goles_visitante
            
            # Actualizar estadísticas del equipo visitante
            stats_por_equipo[id_visitante]['partidos_jugados'] += 1
            stats_por_equipo[id_visitante]['partidos_jugados_visitante'] += 1
            stats_por_equipo[id_visitante]['gf'] += goles_visitante
            stats_por_equipo[id_visitante]['gf_visitante'] += goles_visitante
            stats_por_equipo[id_visitante]['gc'] += goles_local
            stats_por_equipo[id_visitante]['gc_visitante'] += goles_local
            
            # Determinar resultado y actualizar puntos
            if goles_local > goles_visitante:
                # Gana local
                stats_por_equipo[id_local]['victorias'] += 1
                stats_por_equipo[id_local]['victorias_local'] += 1
                stats_por_equipo[id_local]['puntos'] += 3
                stats_por_equipo[id_local]['resultados'].append('W')
                
                stats_por_equipo[id_visitante]['derrotas'] += 1
                stats_por_equipo[id_visitante]['derrotas_visitante'] += 1
                stats_por_equipo[id_visitante]['resultados'].append('L')
            elif goles_local < goles_visitante:
                # Gana visitante
                stats_por_equipo[id_visitante]['victorias'] += 1
                stats_por_equipo[id_visitante]['victorias_visitante'] += 1
                stats_por_equipo[id_visitante]['puntos'] += 3
                stats_por_equipo[id_visitante]['resultados'].append('W')
                
                stats_por_equipo[id_local]['derrotas'] += 1
                stats_por_equipo[id_local]['derrotas_local'] += 1
                stats_por_equipo[id_local]['resultados'].append('L')
            else:
                # Empate
                stats_por_equipo[id_local]['empates'] += 1
                stats_por_equipo[id_local]['empates_local'] += 1
                stats_por_equipo[id_local]['puntos'] += 1
                stats_por_equipo[id_local]['resultados'].append('D')
                
                stats_por_equipo[id_visitante]['empates'] += 1
                stats_por_equipo[id_visitante]['empates_visitante'] += 1
                stats_por_equipo[id_visitante]['puntos'] += 1
                stats_por_equipo[id_visitante]['resultados'].append('D')
        
        # Calcular posiciones y forma al final de la jornada
        # Ordenar por puntos, diferencia de goles y goles a favor
        equipos_ordenados = sorted(
            stats_por_equipo.items(),
            key=lambda x: (-x[1]['puntos'], -(x[1]['gf'] - x[1]['gc']), -x[1]['gf'])
        )
        
        # Actualizar posiciones y generar registros para esta jornada
        for posicion, (id_equipo, stats) in enumerate(equipos_ordenados, 1):
            stats['posicion'] = posicion
            stats['dg'] = stats['gf'] - stats['gc']
            
            # Forma (últimos 5 resultados)
            forma_list = stats['resultados'][-5:] if stats['resultados'] else []
            stats['forma'] = ''.join(forma_list) if forma_list else ''
            
            # Añadir fila a clasificacion_jornadas
            clasificacion_jornadas.append({
                'id_equipo': id_equipo,
                'temporada': temporada,
                'jornada': jornada,
                'posicion': stats['posicion'],
                'nombre_equipo': stats['nombre_equipo'],
                'puntos': stats['puntos'],
                'dg': stats['dg'],
                'forma': stats['forma'],
                'partidos_jugados': stats['partidos_jugados'],
                'victorias': stats['victorias'],
                'empates': stats['empates'],
                'derrotas': stats['derrotas'],
                'gf': stats['gf'],
                'gc': stats['gc'],
                'partidos_jugados_local': stats['partidos_jugados_local'],
                'victorias_local': stats['victorias_local'],
                'empates_local': stats['empates_local'],
                'derrotas_local': stats['derrotas_local'],
                'gf_local': stats['gf_local'],
                'gc_local': stats['gc_local'],
                'partidos_jugados_visitante': stats['partidos_jugados_visitante'],
                'victorias_visitante': stats['victorias_visitante'],
                'empates_visitante': stats['empates_visitante'],
                'derrotas_visitante': stats['derrotas_visitante'],
                'gf_visitante': stats['gf_visitante'],
                'gc_visitante': stats['gc_visitante']
            })

# Crear DataFrame y guardar a CSV
df_resultado = pd.DataFrame(clasificacion_jornadas)

# Ordenar por temporada, jornada y posición
df_resultado = df_resultado.sort_values(['temporada', 'jornada', 'posicion'])

# Forzar columnas numéricas finales a enteros en el CSV.
columnas_int_salida = [
    'id_equipo', 'temporada', 'jornada', 'posicion', 'puntos', 'dg',
    'partidos_jugados', 'victorias', 'empates', 'derrotas', 'gf', 'gc',
    'partidos_jugados_local', 'victorias_local', 'empates_local', 'derrotas_local', 'gf_local', 'gc_local',
    'partidos_jugados_visitante', 'victorias_visitante', 'empates_visitante', 'derrotas_visitante', 'gf_visitante',
    'gc_visitante'
]
df_resultado[columnas_int_salida] = df_resultado[columnas_int_salida].apply(pd.to_numeric, errors='raise').astype('int64')

# Guardar a CSV con delimitador punto y coma
df_resultado.to_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\h_equipo_jornada.csv', index=False, sep=';')

print("✓ Archivo h_equipo_jornada.csv creado exitosamente")
print(f"  Total de registros: {len(df_resultado)}")
print(f"\nPrimeras filas:")
print(df_resultado.head(20))
print(f"\nÚltimas filas:")
print(df_resultado.tail(20))
