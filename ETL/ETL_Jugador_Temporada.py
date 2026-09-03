import json
import pandas as pd
import os

RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
DSA = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA" 
CARPETA_JUGADORES = os.path.join(RUTA_BASE, "jugadores_temporada")
ARCHIVO_SALIDA = os.path.join(DSA, "h_jugador_temporada.csv")

TRADUCCIONES_POSICIONES = {
    'Goalkeeper': 'Portero',
    'Defender': 'Defensa',
    'Midfielder': 'Mediocentro',
    'Attacker': 'Delantero'
}

def traducir_posicion(posicion):
    """Traduce la posición del inglés al español"""
    if posicion is None:
        return None
    return TRADUCCIONES_POSICIONES.get(posicion, posicion)

def procesar_stats_jugadores():
    rows = []
    
    if not os.path.exists(CARPETA_JUGADORES):
        print("Carpeta no encontrada.")
        return

    archivos = [f for f in os.listdir(CARPETA_JUGADORES) if f.endswith('.json')]
    
    for archivo in archivos:
        ruta_completa = os.path.join(CARPETA_JUGADORES, archivo)
        with open(ruta_completa, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            for item in data:
                id_jugador = item.get('player', {}).get('id')
                
                # Conserva una fila por cada equipo en el que participó el jugador.
                for stat in item.get('statistics', []):
                    fila = {
                        "id_jugador": id_jugador,
                        "id_equipo": stat.get('team', {}).get('id'),
                        "temporada": stat.get('league', {}).get('season'),
                        "posicion": traducir_posicion(stat.get('games', {}).get('position')),
                        # Participación.
                        "partidos": stat.get('games', {}).get('appearences'),
                        "minutos": stat.get('games', {}).get('minutes'),
                        "titular": stat.get('games', {}).get('lineups'),
                        "nota_media": stat.get('games', {}).get('rating'),
                        # Ataque.
                        "goles": stat.get('goals', {}).get('total'),
                        "asistencias": stat.get('goals', {}).get('assists'),
                        "tiros_totales": stat.get('shots', {}).get('total'),
                        "tiros_a_puerta": stat.get('shots', {}).get('on'),
                        # Distribución.
                        "pases_totales": stat.get('passes', {}).get('total'),
                        "pases_clave": stat.get('passes', {}).get('key'),
                        "precision_pases": stat.get('passes', {}).get('accuracy'),
                        # Defensa y disciplina.
                        "entradas": stat.get('tackles', {}).get('total'),
                        "bloqueos": stat.get('tackles', {}).get('blocks'),
                        "intercepciones": stat.get('tackles', {}).get('interceptions'),
                        "duelos_totales": stat.get('duels', {}).get('total'),
                        "duelos_ganados": stat.get('duels', {}).get('won'),
                        "faltas_sufridas": stat.get('fouls', {}).get('drawn'),
                        "faltas_cometidas": stat.get('fouls', {}).get('commited'),
                        "regates_intentados": stat.get('dribbles', {}).get('attempts'),
                        "regates_exito": stat.get('dribbles', {}).get('success'),
                        "regateado": stat.get('dribbles', {}).get('past'),
                        "amarillas": stat.get('cards', {}).get('yellow'),
                        "rojas": stat.get('cards', {}).get('red'),
                        "penaltis_marcados": stat.get('penalty', {}).get('scored'),
                        # Portería.
                        "goles_concedidos": stat.get('goals', {}).get('conceded'),
                        "paradas": stat.get('goals', {}).get('saves'),
                        "penaltis_parados": stat.get('penalty', {}).get('saved') 
                    }
                    rows.append(fila)

    df = pd.DataFrame(rows)

    df = df.sort_values(by=['temporada', 'id_equipo'], ascending=[True, True])

    # La nota admite decimales; el resto de estadísticas son recuentos enteros.
    df['nota_media'] = pd.to_numeric(df['nota_media'], errors='coerce').fillna(0.0)

    cols_no_enteras = ['posicion', 'nota_media']
    cols_para_enteros = [c for c in df.columns if c not in cols_no_enteras]

    for col in cols_para_enteros:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    df.to_csv(ARCHIVO_SALIDA, index=False, sep=';', encoding='utf-8-sig')
    
    print(f"✅ ETL de Estadísticas de Jugador completado.")
    print(f"📊 Total de registros (Jugador-Equipo-Temporada): {len(df)}")

if __name__ == "__main__":
    procesar_stats_jugadores()
