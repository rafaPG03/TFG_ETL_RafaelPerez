import requests
import json
import os
import time

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS\TIEMPO_REAL"


# --- CONFIGURACIÓN API ---
API_KEY = "9a1f5c647c9c3460a5febd199a79e30a"
HEADERS = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': API_KEY}
ID_LIGA = 140 
TEMPORADA = 2025 # La que me pediste

def extraer_clasificacion():
    
    print(f"🚀 Iniciando extracción de clasificación (Standings) para la Liga {ID_LIGA}")

    # Endpoint específico de standings
    url = f"https://v3.football.api-sports.io/standings?league={ID_LIGA}&season={TEMPORADA}"
    
    print(f"📅 Consultando temporada {TEMPORADA}...", end=" ", flush=True)
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        # Comprobamos que la respuesta sea exitosa
        if response.status_code == 200:
            data = response.json()
            
            # Verificamos si hay datos en la respuesta
            if data.get('response'):
                filename = os.path.join(RUTA_BASE, f"CLASIFICACION_{TEMPORADA}.json")
                
                with open(filename, "w", encoding="utf-8") as f:
                    # Guardamos el JSON completo tal cual viene de la API
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                print(f"✅ OK")
                print(f"\n✨ ¡Extracción finalizada!")
                print(f"📂 Archivo guardado en: {filename}")
            else:
                print(f"⚠️ Sin datos en la respuesta")
        else:
            print(f"❌ Error API: Código {response.status_code}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    extraer_clasificacion()