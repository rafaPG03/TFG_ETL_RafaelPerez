import requests
import json
import os
import time

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
CARPETA_PARTIDOS = os.path.join(RUTA_BASE, "partidos_base")
CARPETA_STATS = os.path.join(RUTA_BASE, "jugadores_partido")

# --- CONFIGURACIÓN API ---
API_KEY = "9a1f5c647c9c3460a5febd199a79e30a"
HEADERS = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': API_KEY}
# Ajuste de velocidad para 400 req/min
DELAY = 60/400 

# Filtro de años específicos
ANOS_A_PROCESAR = ["2019", "2020", "2021", "2022", "2023", "2024"]

def extraer_eventos_partidos():
    if not os.path.exists(CARPETA_STATS):
        os.makedirs(CARPETA_STATS)

    archivos_partidos = [f for f in os.listdir(CARPETA_PARTIDOS) if f.endswith('.json')]
    
    for archivo in archivos_partidos:
        year = archivo.split('_')[1].split('.')[0]
        
        # Solo procesar si el año está en nuestra lista de faltantes
        if year not in ANOS_A_PROCESAR:
            continue
            
        print(f"\n📊 Procesando jugadores de la temporada {year}...")
        
        with open(os.path.join(CARPETA_PARTIDOS, archivo), 'r', encoding='utf-8') as f:
            partidos = json.load(f)
        
        jugador_partido = []
        
        for i, p in enumerate(partidos):
            f_id = p['fixture']['id']
            url = f"https://v3.football.api-sports.io/fixtures/players?fixture={f_id}"
            
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                res_data = response.json().get('response', [])
                
                jugador_partido.append({
                    "fixture_id": f_id,
                    "players": res_data
                })
                
                if i % 20 == 0:
                    print(f"   > Progreso {year}: {i}/{len(partidos)} partidos...")
                
                time.sleep(DELAY)
                
            except Exception as e:
                print(f"❌ Error en fixture {f_id}: {e}")
                continue

        output_file = os.path.join(CARPETA_STATS, f"jugadores_partidos_{year}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(jugador_partido, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Temporada {year} finalizada y guardada.")

if __name__ == "__main__":
    extraer_eventos_partidos()