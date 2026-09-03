import requests
import json
import os
import time

RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
CARPETA_PARTIDOS = os.path.join(RUTA_BASE, "partidos_base")
CARPETA_STATS = os.path.join(RUTA_BASE, "partidos_eventos")

API_KEY = "9a1f5c647c9c3460a5febd199a79e30a"
HEADERS = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': API_KEY}
# Intervalo mínimo para respetar el límite de 400 peticiones por minuto.
DELAY = 60/400 

def extraer_eventos_partidos():
    if not os.path.exists(CARPETA_STATS):
        os.makedirs(CARPETA_STATS)

    archivos_partidos = [f for f in os.listdir(CARPETA_PARTIDOS) if f.endswith('.json')]
    
    for archivo in archivos_partidos:
        year = archivo.split('_')[1].split('.')[0]
        print(f"\n📊 Procesando eventos de la temporada {year}...")
        
        with open(os.path.join(CARPETA_PARTIDOS, archivo), 'r', encoding='utf-8') as f:
            partidos = json.load(f)
        
        eventos_partidos = []
        
        for i, p in enumerate(partidos):
            f_id = p['fixture']['id']
            
            url = f"https://v3.football.api-sports.io/fixtures/events?fixture={f_id}"
            
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                res_data = response.json().get('response', [])
                
                eventos_partidos.append({
                    "fixture_id": f_id,
                    "events": res_data
                })
                
                if i % 20 == 0:
                    print(f"   > Progreso {year}: {i}/{len(partidos)} partidos...")
                
                time.sleep(DELAY)
                
            except Exception as e:
                print(f"❌ Error en fixture {f_id}: {e}")
                continue

        output_file = os.path.join(CARPETA_STATS, f"eventos_partidos_{year}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(eventos_partidos, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Temporada {year} finalizada y guardada.")

if __name__ == "__main__":
    extraer_eventos_partidos()
