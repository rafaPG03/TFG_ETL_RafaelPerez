import requests
import json
import os
import time

# --- CONFIGURACIÓN DE RUTAS ---
# Usamos r"" para que Windows acepte las barras invertidas sin problemas
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
CARPETA_PARTIDOS = os.path.join(RUTA_BASE, "clasificaciones")

# --- CONFIGURACIÓN API ---
API_KEY = "9a1f5c647c9c3460a5febd199a79e30a" # Pon aquí tu clave real
HEADERS = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': API_KEY}
TEMPORADAS = range(2015, 2026) 
ID_LIGA = 140 
RATE = 60/400

def extraer_partidos_base():
    # Crear la carpeta si no existe
    if not os.path.exists(CARPETA_PARTIDOS):
        os.makedirs(CARPETA_PARTIDOS)
        print(f"📁 Carpeta creada en: {CARPETA_PARTIDOS}")
    
    print(f"🚀 Iniciando extracción en {RUTA_BASE}")

    for year in TEMPORADAS:
        print(f"📅 Descargando clasificacion {year}...", end=" ", flush=True)
        
        url = f"https://v3.football.api-sports.io/teams?league=140&season={year}"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            data = response.json().get('response', [])
            
            if data:
                filename = os.path.join(CARPETA_PARTIDOS, f"clasificacion_{year}.json")
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                print(f"✅ OK ({len(data)} partidos)")
            else:
                print(f"⚠️ Vacío")
            
            # Con 450/min podemos ir rápido, 0.2s es muy seguro
            time.sleep(RATE)
            
        except Exception as e:
            print(f"❌ Error: {e}")

    print(f"\n✨ ¡Listo! Revisa tu escritorio en la carpeta ESI/TFG/DATOS/partidos_base")

if __name__ == "__main__":
    extraer_partidos_base()