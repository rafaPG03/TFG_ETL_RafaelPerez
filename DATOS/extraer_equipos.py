import requests
import json
import os
import time

RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
CARPETA_EQUIPOS = os.path.join(RUTA_BASE, "equipos_base")

API_KEY = "9a1f5c647c9c3460a5febd199a79e30a"
HEADERS = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': API_KEY}
TEMPORADAS = range(2015, 2026) 
ID_LIGA = 140 
RATE = 60/400

def extraer_equipos_unicos():
    if not os.path.exists(CARPETA_EQUIPOS):
        os.makedirs(CARPETA_EQUIPOS)
        print(f"📁 Carpeta creada en: {CARPETA_EQUIPOS}")
    
    # Conserva una única versión de cada equipo en todo el histórico.
    equipos_maestros = {}

    print(f"🚀 Iniciando extracción de equipos únicos en {RUTA_BASE}")

    for year in TEMPORADAS:
        print(f"📅 Consultando temporada {year}...", end=" ", flush=True)
        
        url = f"https://v3.football.api-sports.io/teams?league={ID_LIGA}&season={year}"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            data = response.json().get('response', [])
            
            if data:
                nuevos_en_esta_temporada = 0
                for item in data:
                    id_equipo = item['team']['id']
                    
                    if id_equipo not in equipos_maestros:
                        equipos_maestros[id_equipo] = item
                        nuevos_en_esta_temporada += 1
                
                print(f"✅ OK (+{nuevos_en_esta_temporada} nuevos)")
            else:
                print(f"⚠️ Sin datos")
            
            time.sleep(RATE)
            
        except Exception as e:
            print(f"❌ Error: {e}")

    if equipos_maestros:
        filename = os.path.join(CARPETA_EQUIPOS, "equipos_unicos_historico.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(list(equipos_maestros.values()), f, ensure_ascii=False, indent=4)
        
        print(f"\n✨ ¡Extracción finalizada!")
        print(f"📊 Total de equipos únicos encontrados (2015-2025): {len(equipos_maestros)}")
        print(f"📂 Archivo maestro guardado en: {filename}")
    else:
        print("\n❌ No se obtuvieron datos para guardar.")

if __name__ == "__main__":
    extraer_equipos_unicos()
