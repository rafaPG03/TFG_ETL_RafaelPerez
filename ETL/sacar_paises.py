import json
import os
import pandas as pd

# --- CONFIGURACIÓN DE RUTAS ---
CARPETA_JUGADORES = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS\jugadores_temporada"
ARCHIVO_SALIDA = "mapeo_paises_traduccion.csv"

def extraer_paises_json_api():
    paises_unicos = set()
    
    # Comprobar si la carpeta existe
    if not os.path.exists(CARPETA_JUGADORES):
        print(f"❌ La ruta no existe: {CARPETA_JUGADORES}")
        return

    archivos = [f for f in os.listdir(CARPETA_JUGADORES) if f.endswith('.json')]
    print(f"🔍 Procesando {len(archivos)} archivos de jugadores...")

    for archivo in archivos:
        ruta = os.path.join(CARPETA_JUGADORES, archivo)
        with open(ruta, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                
                for item in data:
                    player_info = item.get('player', {})
                    
                    # Extraer Nacionalidad
                    nacionalidad = player_info.get('nationality')
                    if nacionalidad:
                        paises_unicos.add(nacionalidad.strip())
                    
                    # Extraer País de Nacimiento (dentro de 'birth')
                    birth_info = player_info.get('birth', {})
                    pais_nac = birth_info.get('country')
                    if pais_nac:
                        paises_unicos.add(pais_nac.strip())
                        
            except Exception as e:
                print(f"⚠️ Error procesando {archivo}: {e}")

    # Convertir a DataFrame, ordenar y preparar para traducción
    lista_final = sorted(list(paises_unicos))
    df = pd.DataFrame(lista_final, columns=['Nombre_Original_API'])
    
    # Añadimos columnas para ayudarte en la traducción
    df['Traduccion_ES'] = "" 
    df['Gentilicio_ES'] = "" # Útil si quieres poner "Nacionalidad: Española"

    # Guardar CSV
    df.to_csv(ARCHIVO_SALIDA, index=False, sep=';', encoding='utf-8-sig')
    
    print("-" * 30)
    print(f"✅ ¡Hecho! Se han encontrado {len(lista_final)} países/nacionalidades únicos.")
    print(f"📁 Archivo listo para traducir en: {ARCHIVO_SALIDA}")

if __name__ == "__main__":
    extraer_paises_json_api()