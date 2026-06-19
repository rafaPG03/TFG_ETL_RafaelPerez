import requests
import json
import os
import time

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
CARPETA_STANDINGS = os.path.join(RUTA_BASE, "clasificaciones")
CARPETA_OUTPUT = os.path.join(RUTA_BASE, "equipo_stats_temporada")

# --- CONFIGURACIÓN API ---
API_KEY = "9a1f5c647c9c3460a5febd199a79e30a"
HEADERS = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': API_KEY}
ID_LIGA = 140
TEMPORADAS = range(2015, 2026) # 2015 hasta 2025 inclusive
RATE = 60/400 

def extraer_stats_por_temporada():
    if not os.path.exists(CARPETA_OUTPUT):
        os.makedirs(CARPETA_OUTPUT)

    for year in TEMPORADAS:
        print(f"\n📅 --- INICIANDO TEMPORADA {year} ---")
        ruta_std = os.path.join(CARPETA_STANDINGS, f"clasificacion_{year}.json")
        
        if not os.path.exists(ruta_std):
            print(f"⚠️ Saltando {year}: No existe el archivo")
            continue

        with open(ruta_std, 'r', encoding='utf-8') as f:
            data_std = json.load(f)
            try:
                # Acceso corregido según tu fragmento
                equipos_ids = [
                    team['team']['id'] 
                    for team in data_std[0]['league']['standings'][0]
                ]
            except Exception as e:
                print(f"❌ Error procesando IDs: {e}")
                continue

        stats_esta_temporada = []
        for i, team_id in enumerate(equipos_ids, 1):
            print(f"   🔄 [{i}/20] ID {team_id}...", end="\r")
            url = f"https://v3.football.api-sports.io/teams/statistics?league={ID_LIGA}&season={year}&team={team_id}"
            
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                res_json = response.json()
                # API Football devuelve { "response": { ...stats... } }
                res_data = res_json.get('response', {})
                
                if res_data:
                    stats_esta_temporada.append(res_data)
                
                time.sleep(RATE)
            except Exception as e:
                print(f"\n❌ Error en equipo {team_id}: {e}")

        # Guardado por temporada
        archivo_year = os.path.join(CARPETA_OUTPUT, f"stats_equipos_{year}.json")
        with open(archivo_year, 'w', encoding='utf-8') as f:
            json.dump(stats_esta_temporada, f, ensure_ascii=False, indent=4)
            
        print(f"\n✅ Archivo {year} generado con éxito.")

if __name__ == "__main__":
    extraer_stats_por_temporada()