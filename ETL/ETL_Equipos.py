import json
import pandas as pd
import os

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
DSA = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA" 
CARPETA_EQUIPOS = os.path.join(RUTA_BASE, "equipos_base")
ARCHIVO_SALIDA = os.path.join(DSA, "dim_equipos.csv")

def procesar_equipos():
    all_data = []

    archivos = [f for f in os.listdir(CARPETA_EQUIPOS) if f.endswith('.json')]

    for archivo in archivos:
        ruta_completa = os.path.join(CARPETA_EQUIPOS, archivo)

        with open(ruta_completa, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for p in data:
                fila = {
                    "id_equipo": p['team']['id'],
                    "nombre_equipo": p['team']['name'],
                    "codigo": p['team']['code'],
                    "pais": p['team']['country'],
                    "fundado_en": p['team']['founded'],
                    "logo": p['team']['logo'],
                    "estadio": p['venue']['name'],
                    "direccion": p['venue']['address'],
                    "ciudad": p['venue']['city'],
                    "capacidad": p['venue']['capacity'],
                }
                all_data.append(fila)

    df = pd.DataFrame(all_data)

    # Guardar en CSV
    df.to_csv(ARCHIVO_SALIDA, index=False, sep=';', encoding='utf-8-sig')
    
    print(f"✅ ETL Completado. Se han procesado {len(df)} registros de equipos.")
    print(f"📂 Archivo guardado en: {ARCHIVO_SALIDA}")

if __name__=="__main__":
    procesar_equipos()