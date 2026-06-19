import requests
import json
import os
import time

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS\TIEMPO_REAL"


# --- CONFIGURACIÓN API ---
API_KEY = "9a1f5c647c9c3460a5febd199a79e30a"
HEADERS = {'x-rapidapi-host': "v3.football.api-sports.io", 'x-rapidapi-key': API_KEY}
RATE = 60/400 

# --- LISTA DE IDS ---
IDS_PARTIDOS = [
    1391032, 1391038, 1391036, 1391034, 1391031, 1391037, 1391030, 1391033, 1391029, 
    1391035, 1391043, 1391044, 1391042, 1391046, 1391045, 1391039, 1391040, 1391041, 
    1391047, 1391048, 1391049, 1391050, 1391055, 1391058, 1391056, 1391057, 1391051, 
    1391053, 1391054, 1391052, 1390974, 1391067, 1391065, 1391066, 1391063, 1391059, 
    1391064, 1391068, 1391060, 1391061, 1391062
]

def extraer_todo_acumulado():
    if not os.path.exists(RUTA_BASE):
        os.makedirs(RUTA_BASE)

    # Listas para acumular las respuestas de cada endpoint
    acumulado_stats = []
    acumulado_players = []
    acumulado_events = []

    total = len(IDS_PARTIDOS)
    print(f"🚀 Iniciando extracción de {total} partidos...")

    for i, f_id in enumerate(IDS_PARTIDOS, 1):
        print(f"🔄 [{i}/{total}] Procesando ID: {f_id}...", end="\r")
        
        # 1. Llamada a Statistics
        try:
            res_stats = requests.get(f"https://v3.football.api-sports.io/fixtures/statistics?fixture={f_id}", headers=HEADERS)
            data_s = res_stats.json().get('response', [])
            if data_s: acumulado_stats.append({"fixture_id": f_id, "data": data_s})
            time.sleep(RATE)

            # 2. Llamada a Players
            res_players = requests.get(f"https://v3.football.api-sports.io/fixtures/players?fixture={f_id}", headers=HEADERS)
            data_p = res_players.json().get('response', [])
            if data_p: acumulado_players.append({"fixture_id": f_id, "data": data_p})
            time.sleep(RATE)

            # 3. Llamada a Events
            res_events = requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={f_id}", headers=HEADERS)
            data_e = res_events.json().get('response', [])
            if data_e: acumulado_events.append({"fixture_id": f_id, "data": data_e})
            time.sleep(RATE)

        except Exception as e:
            print(f"\n❌ Error en ID {f_id}: {e}")

    # --- GUARDADO DE LOS 3 ARCHIVOS MAESTROS ---
    print("\n\n💾 Guardando archivos maestros...")
    
    archivos = {
        "partidos_stats_full.json": acumulado_stats,
        "partidos_jugadores_full.json": acumulado_players,
        "partidos_eventos_full.json": acumulado_events
    }

    for nombre, lista in archivos.items():
        ruta = os.path.join(RUTA_BASE, nombre)
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(lista, f, ensure_ascii=False, indent=4)
        print(f"✅ Generado: {nombre}")

    print(f"\n✨ Proceso finalizado. Todo guardado en: {RUTA_BASE}")

if __name__ == "__main__":
    extraer_todo_acumulado()