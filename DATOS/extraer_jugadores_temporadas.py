import requests
import json
import os
import time

RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
CARPETA_INPUT = os.path.join(RUTA_BASE, "jugadores_partido")
CARPETA_OUTPUT = os.path.join(RUTA_BASE, "jugadores_temporada")

API_KEY = "9a1f5c647c9c3460a5febd199a79e30a"
HEADERS = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': API_KEY}
DELAY = 60/400 

def extraer_perfiles_anuales():
    if not os.path.exists(CARPETA_OUTPUT):
        os.makedirs(CARPETA_OUTPUT)

    archivos = [f for f in os.listdir(CARPETA_INPUT) if f.endswith('.json')]
    
    for archivo in archivos:
        year = archivo.split('_')[-1].split('.')[0]
        print(f"\n👤 Obteniendo IDs únicos de la temporada {year}...")
        
        with open(os.path.join(CARPETA_INPUT, archivo), 'r', encoding='utf-8') as f:
            data_partidos = json.load(f)
        
        # Evita repetir consultas para un jugador dentro de la misma temporada.
        ids_unicos = set()
        for partido in data_partidos:
            for p_entry in partido.get('players', []):
                for player in p_entry.get('players', []):
                    ids_unicos.add(player['player']['id'])
        
        print(f"🎯 Detectados {len(ids_unicos)} jugadores únicos. Iniciando descarga...")
        
        perfiles_temporada = []
        for i, p_id in enumerate(ids_unicos):
            url = f"https://v3.football.api-sports.io/players?id={p_id}&league=140&season={year}"
            
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                res_data = response.json().get('response', [])
                
                if res_data:
                    perfiles_temporada.append(res_data[0])
                
                if i % 50 == 0:
                    print(f"   > Progreso {year}: {i}/{len(ids_unicos)} perfiles descargados...")
                
                time.sleep(DELAY)
                
            except Exception as e:
                print(f"❌ Error en jugador {p_id}: {e}")
                continue

        output_file = os.path.join(CARPETA_OUTPUT, f"perfiles_completos_{year}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(perfiles_temporada, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Temporada {year} finalizada con {len(perfiles_temporada)} perfiles.")

if __name__ == "__main__":
    extraer_perfiles_anuales()
