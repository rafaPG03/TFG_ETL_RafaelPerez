import json
import pandas as pd
import os

RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
DSA = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA" 
CARPETA_STANDINGS = os.path.join(RUTA_BASE, "clasificaciones")
ARCHIVO_SALIDA = os.path.join(DSA, "h_equipo_temporada.csv")

def procesar_clasificaciones():
    all_data = []
    
    archivos = [f for f in os.listdir(CARPETA_STANDINGS) if f.endswith('.json')]
    
    for archivo in archivos:
        ruta_completa = os.path.join(CARPETA_STANDINGS, archivo)
        
        with open(ruta_completa, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
            league_info = data[0]['league']
            id_liga = league_info['id']
            temporada = league_info['season']
            
            standings_list = league_info['standings'][0]
            
            for team_data in standings_list:
                fila = {
                    "id_equipo": team_data['team']['id'],
                    "temporada": temporada,
                    "posicion": team_data['rank'],
                    "nombre_equipo": team_data['team']['name'],
                    "puntos": team_data['points'],
                    "dg": team_data['goalsDiff'],
                    "forma": team_data['form'],
                    
                    # Estadísticas totales.
                    "partidos_jugados": team_data['all']['played'],
                    "victorias": team_data['all']['win'],
                    "empates": team_data['all']['draw'],
                    "derrotas": team_data['all']['lose'],
                    "gf": team_data['all']['goals']['for'],
                    "gc": team_data['all']['goals']['against'],
                    
                    # Estadísticas como local.
                    "partidos_jugados_local": team_data['home']['played'],
                    "victorias_local": team_data['home']['win'],
                    "empates_local": team_data['home']['draw'],
                    "derrotas_local": team_data['home']['lose'],
                    "gf_local": team_data['home']['goals']['for'],
                    "gc_local": team_data['home']['goals']['against'],
                    
                    # Estadísticas como visitante.
                    "partidos_jugados_visitante": team_data['away']['played'],
                    "victorias_visitante": team_data['away']['win'],
                    "empates_visitante": team_data['away']['draw'],
                    "derrotas_visitante": team_data['away']['lose'],
                    "gf_visitante": team_data['away']['goals']['for'],
                    "gc_visitante": team_data['away']['goals']['against']
                }
                all_data.append(fila)

    df = pd.DataFrame(all_data)
    
    df = df.sort_values(by=['temporada', 'posicion'], ascending=[False, True])
    
    df.to_csv(ARCHIVO_SALIDA, index=False, sep=';', encoding='utf-8-sig')
    
    print(f"✅ ETL Completado. Se han procesado {len(df)} registros de equipos.")
    print(f"📂 Archivo guardado en: {ARCHIVO_SALIDA}")

if __name__ == "__main__":
    procesar_clasificaciones()
