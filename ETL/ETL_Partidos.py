import json
import pandas as pd
import os

RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
DSA = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA" 
CARPETA_PARTIDOS = os.path.join(RUTA_BASE, "partidos_base")
ARCHIVO_SALIDA = os.path.join(DSA, "dim_partidos.csv")

def es_partido_acabado(p):
    """Verifica si un partido está completado."""
    try:
        if not p.get('fixture') or not p.get('teams') or not p.get('goals'):
            return False
        
        if not p['fixture'].get('id') or not p['fixture'].get('date'):
            return False
        
        if (not p['teams'].get('home') or not p['teams'].get('away') or
            not p['teams']['home'].get('id') or not p['teams']['away'].get('id')):
            return False
        
        # El cero es un resultado válido; solo se descartan goles nulos.
        if p['goals'].get('home') is None or p['goals'].get('away') is None:
            return False
        
        return True
    except (KeyError, TypeError):
        return False

def determinar_ganador(p, acabado):
    """Determina el ganador. Retorna None si el partido no está acabado."""
    if not acabado:
        return None
    
    home_win = p['teams']['home']['winner']
    away_win = p['teams']['away']['winner']

    if home_win is True:
        return p['teams']['home']['name']
    elif away_win is True:
        return p['teams']['away']['name']
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
                acabado = es_partido_acabado(p)
                
                if acabado:
                    id_partido = p['fixture']['id']
                    arbitro = p['fixture']['referee']
                    fecha = p['fixture']['date']
                    estadio = p['fixture']['venue']['name']
                    jornada = p['league']['round']
                    temporada = p['league']['season']
                    id_local = p['teams']['home']['id']
                    id_visitante = p['teams']['away']['id']
                    ganador = determinar_ganador(p, acabado)
                    goles_local = p['goals']['home']
                    goles_visitante = p['goals']['away']
                else:
                    # Conserva los campos disponibles de los partidos pendientes.
                    id_partido = p.get('fixture', {}).get('id')
                    arbitro = p.get('fixture', {}).get('referee')
                    fecha = p.get('fixture', {}).get('date')
                    estadio = p.get('fixture', {}).get('venue', {}).get('name')
                    jornada = p.get('league', {}).get('round')
                    temporada = p.get('league', {}).get('season')
                    id_local = p.get('teams', {}).get('home', {}).get('id')
                    id_visitante = p.get('teams', {}).get('away', {}).get('id')
                    ganador = None
                    goles_local = None
                    goles_visitante = None
                
                fila = {
                    "id_partido": id_partido,
                    "arbitro": arbitro,
                    "fecha": fecha,
                    "estadio": estadio,
                    "jornada": jornada,
                    "temporada": temporada,
                    "id_local": id_local,
                    "id_visitante": id_visitante,
                    "ganador": ganador,
                    "goles_local": goles_local,
                    "goles_visitante": goles_visitante,
                    "status": "Completado" if acabado else "Incompleto"
                }
                all_data.append(fila)

    df = pd.DataFrame(all_data)
    df = df.sort_values(by=['fecha'], ascending=[True])
    
    # Elimina el país añadido al nombre del árbitro por la API.
    df['arbitro'] = df['arbitro'].str.replace(", Spain", "", case=False, regex=False)

    # La jornada se almacena como número entero.
    df['jornada'] = df['jornada'].str.extract('(\d+)', expand=False).astype('Int64')

    # Los goles usan enteros anulables para los partidos pendientes.
    df['goles_local'] = pd.to_numeric(df['goles_local'], errors='coerce').astype('Int64')
    df['goles_visitante'] = pd.to_numeric(df['goles_visitante'], errors='coerce').astype('Int64')

    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')

    df.to_csv(ARCHIVO_SALIDA, index=False, sep=';', encoding='utf-8-sig')
    
    completados = (df['status'] == 'Completado').sum()
    incompletos = (df['status'] == 'Incompleto').sum()
    
    print(f"✅ ETL Completado. Se han procesado {len(df)} registros de partidos.")
    print(f"   - Partidos Completados: {completados}")
    print(f"   - Partidos Incompletos: {incompletos}")
    print(f"📂 Archivo guardado en: {ARCHIVO_SALIDA}")

if __name__=="__main__":
    procesar_partidos()


