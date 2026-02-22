import requests
import json
import os
import time
import pandas as pd  # Añadimos pandas

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
CARPETA_DESTINO = os.path.join(RUTA_BASE, "jugadores_faltantes")

# --- CONFIGURACIÓN API ---
API_KEY = "9a1f5c647c9c3460a5febd199a79e30a"
HEADERS = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': API_KEY}
JUGADORES_FALTANTES = [
    47003, 35834, 104624, 46767, 104867, 
    80891, 80848, 104837, 89886, 107147, 
    156480, 157910, 181868, 195164, 75908, 
    30406, 496425, 352854
]
RATE = 60/400

def extraer_jugadores_faltantes():
    if not os.path.exists(CARPETA_DESTINO):
        os.makedirs(CARPETA_DESTINO)
    
    print(f"🚀 Iniciando extracción de {len(JUGADORES_FALTANTES)} jugadores...")
    todos_los_jugadores = []

    for id_jugador in JUGADORES_FALTANTES:
        print(f"📅 Descargando datos del jugador {id_jugador}...", end=" ", flush=True)
        url = f"https://v3.football.api-sports.io/players/profiles?player={id_jugador}"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                data = response.json().get('response', [])
                if data:
                    todos_los_jugadores.extend(data)
                    print(f"✅ OK")
                else:
                    print(f"⚠️ Sin datos")
            else:
                print(f"❌ Error HTTP {response.status_code}")
            
            time.sleep(RATE)
            
        except Exception as e:
            print(f"❌ Error: {e}")

    # --- PROCESO DE GUARDADO ---
    if todos_los_jugadores:
        # 1. Guardar JSON (Copia de seguridad)
        ruta_json = os.path.join(CARPETA_DESTINO, "jugadores_faltantes.json")
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(todos_los_jugadores, f, ensure_ascii=False, indent=4)

        # 2. Convertir a CSV usando Pandas
        # json_normalize "aplana" los diccionarios (ej: player_id, player_name...)
        df = pd.json_normalize(todos_los_jugadores)
        
        ruta_csv = os.path.join(CARPETA_DESTINO, "jugadores_faltantes.csv")
        df.to_csv(ruta_csv, index=False, sep=';', encoding='utf-8-sig')
        
        print(f"\n✨ ¡Éxito total!")
        print(f"📄 JSON guardado en: {ruta_json}")
        print(f"📊 CSV guardado en: {ruta_csv}")
    else:
        print("\n❌ No se obtuvieron datos para generar los archivos.")

if __name__ == "__main__":
    extraer_jugadores_faltantes()