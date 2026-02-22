import requests
import json
import os
import time

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
CARPETA_PARTIDOS = os.path.join(RUTA_BASE, "partidos_base")
CARPETA_STATS = os.path.join(RUTA_BASE, "partidos_stats")

# --- CONFIGURACIÓN API ---
API_KEY = "9a1f5c647c9c3460a5febd199a79e30a"
HEADERS = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': API_KEY}
# Ajuste de velocidad para 400 req/min
DELAY = 60/400 

def extraer_estadisticas_equipos():
    if not os.path.exists(CARPETA_STATS):
        os.makedirs(CARPETA_STATS)

    # Listar los archivos JSON que descargaste en la Fase 1
    archivos_partidos = [f for f in os.listdir(CARPETA_PARTIDOS) if f.endswith('.json')]
    
    for archivo in archivos_partidos:
        year = archivo.split('_')[1].split('.')[0]
        print(f"\n📊 Procesando estadísticas de la temporada {year}...")
        
        # 1. Leer los partidos guardados para obtener los IDs
        with open(os.path.join(CARPETA_PARTIDOS, archivo), 'r', encoding='utf-8') as f:
            partidos = json.load(f)
        
        stats_temporada = []
        
        # 2. Bucle para pedir stats de cada partido
        for i, p in enumerate(partidos):
            f_id = p['fixture']['id']
            
            url = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}"
            
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                res_data = response.json().get('response', [])
                
                # Guardamos el ID del partido junto con sus estadísticas
                stats_temporada.append({
                    "fixture_id": f_id,
                    "statistics": res_data
                })
                
                if i % 20 == 0:
                    print(f"   > Progreso {year}: {i}/{len(partidos)} partidos...")
                
                # CONTROL DE VELOCIDAD CRÍTICO
                time.sleep(DELAY)
                
            except Exception as e:
                print(f"❌ Error en fixture {f_id}: {e}")
                continue

        # 3. Guardar el archivo de estadísticas de la temporada
        output_file = os.path.join(CARPETA_STATS, f"stats_equipos_{year}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats_temporada, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Temporada {year} finalizada y guardada.")

if __name__ == "__main__":
    extraer_estadisticas_equipos()