import requests
import json
import os
import time

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
CARPETA_STANDINGS = os.path.join(RUTA_BASE, "clasificaciones") # Donde guardas la clasificación
CARPETA_OUTPUT = os.path.join(RUTA_BASE, "equipo_stats_temporada")

# --- CONFIGURACIÓN API ---
API_KEY = "9a1f5c647c9c3460a5febd199a79e30a"
HEADERS = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': API_KEY}
DELAY = 60/400 

def extraer_stats_desde_standings():
    if not os.path.exists(CARPETA_OUTPUT):
        os.makedirs(CARPETA_OUTPUT)

    # Listamos los archivos de clasificación (ej: standings_2024.json)
    archivos_std = [f for f in os.listdir(CARPETA_STANDINGS) if f.endswith('.json')]
    
    for archivo in archivos_std:
        year = archivo.split('_')[1].split('.')[0]
        print(f"\n🏆 Procesando equipos de la clasificación {year}...")
        
        # 1. Leer los IDs directamente de la clasificación
        with open(os.path.join(CARPETA_STANDINGS, archivo), 'r', encoding='utf-8') as f:
            data = json.load(f)
            # La estructura de la API es: response -> league -> standings -> [lista de equipos]
            try:
                lista_equipos = data[0]['league']['standings'][0]
            except (KeyError, IndexError):
                print(f"⚠️ Estructura de archivo incorrecta en {archivo}")
                continue
        
        stats_acumuladas = []
        
        # 2. Bucle corto: solo 20 equipos por temporada
        for equipo in lista_equipos:
            team_id = equipo['team']['id']
            team_name = equipo['team']['name']
            
            print(f"   > Solicitando: {team_name}...", end="\r")
            
            url = f"https://v3.football.api-sports.io/teams/statistics?league=140&season={year}&team={team_id}"
            
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                res_data = response.json().get('response', {})
                
                if res_data:
                    stats_acumuladas.append(res_data)
                
                time.sleep(DELAY)
                
            except Exception as e:
                print(f"\n❌ Error en {team_name}: {e}")
                continue

        # 3. Guardar el resultado final de la temporada
        output_file = os.path.join(CARPETA_OUTPUT, f"stats_globales_equipos_{year}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats_acumuladas, f, ensure_ascii=False, indent=4)
            
        print(f"\n✅ Temporada {year} completada.")

if __name__ == "__main__":
    extraer_stats_desde_standings()