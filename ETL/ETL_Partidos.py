import json
import pandas as pd
import os

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
DSA = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA" 
CARPETA_PARTIDOS = os.path.join(RUTA_BASE, "partidos_base")
ARCHIVO_SALIDA = os.path.join(DSA, "dim_partidos.csv")

def determinar_ganador(p):
    home_name = p['teams']['home']['name']
    away_name = p['teams']['away']['name']
    home_win = p['teams']['home']['winner']
    away_win = p['teams']['away']['winner']

    if home_win is True:
        return home_name
    elif away_win is True:
        return away_name
    else:
        return "Empate"

def procesar_partidos():
    all_data = []

    archivos = [f for f in os.listdir(CARPETA_PARTIDOS) if f.endswith('.json')]

    for archivo in archivos:
        ruta_completa = os.path.join(CARPETA_PARTIDOS, archivo)

        with open(ruta_completa, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for p in data:
                fila = {
                    "id_partido": p['fixture']['id'],
                    "arbitro": p['fixture']['referee'],
                    "fecha": p['fixture']['date'],
                    "estadio": p['fixture']['venue']['name'],
                    "jornada": p['league']['round'],
                    "temporada": p['league']['season'],
                    "id_local": p['teams']['home']['id'],
                    "id_visitante": p['teams']['away']['id'],
                    "ganador": determinar_ganador(p),
                    "goles_local": p['goals']['home'],
                    "goles_visitante": p['goals']['away']
                }
                all_data.append(fila)

    df = pd.DataFrame(all_data)
        # Ordenamos por fecha
    df = df.sort_values(by=['fecha'], ascending=[True])
    
    # Quitamos ", Spain" del árbitro (si existe)
    df['arbitro'] = df['arbitro'].str.replace(", Spain", "", case=False, regex=False)

    # Dejamos solo el número en Jornada (Extrae los dígitos al final del texto)
    df['jornada'] = df['jornada'].str.extract('(\d+)').astype(int)

    # ConvertiMOS goles a Entero (rellenando nulos con 0 por si acaso)
    df['goles_local'] = df['goles_local'].fillna(0).astype(int)
    df['goles_visitante'] = df['goles_visitante'].fillna(0).astype(int)

    # Formateamos Fecha
    df['fecha'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m-%d %H:%M')

    # Guardar en CSV
    df.to_csv(ARCHIVO_SALIDA, index=False, sep=';', encoding='utf-8-sig')
    
    print(f"✅ ETL Completado. Se han procesado {len(df)} registros de equipos.")
    print(f"📂 Archivo guardado en: {ARCHIVO_SALIDA}")

if __name__=="__main__":
    procesar_partidos()


