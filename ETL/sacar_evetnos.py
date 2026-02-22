import json
import os
import pandas as pd

# --- CONFIGURACIÓN ---
CARPETA_EVENTOS = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS\partidos_eventos"
ARCHIVO_SALIDA = "mapeo_eventos.csv"

def extraer_eventos_json_api():
    eventos_unicos = set()
    
    # Comprobar si la carpeta existe
    if not os.path.exists(CARPETA_EVENTOS):
        print(f"❌ La ruta no existe: {CARPETA_EVENTOS}")
        return

    archivos = [f for f in os.listdir(CARPETA_EVENTOS) if f.endswith('.json')]
    print(f"🔍 Procesando {len(archivos)} archivos de eventos...")

    for archivo in archivos:
        ruta = os.path.join(CARPETA_EVENTOS, archivo)
        with open(ruta, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                
                for item in data:
                    for evento_info in item.get('events', []):

                        tipo = evento_info.get('type')
                        if tipo:
                            eventos_unicos.add(tipo.strip())

                        detail = evento_info.get('detail')
                        if detail:
                            eventos_unicos.add(detail.strip())

                        comments = evento_info.get('comments')
                        if comments:
                            eventos_unicos.add(comments.strip())

                    

                        
            except Exception as e:
                print(f"⚠️ Error procesando {archivo}: {e}")

    # Convertir a DataFrame, ordenar y preparar para traducción
    lista_final = sorted(list(eventos_unicos))
    df = pd.DataFrame(lista_final, columns=['Nombre_Original_API'])

    # Guardar CSV
    df.to_csv(ARCHIVO_SALIDA, index=False, sep=';', encoding='utf-8-sig')
    
    print("-" * 30)
    print(f"✅ ¡Hecho! Se han encontrado {len(lista_final)} eventos únicos.")
    print(f"📁 Archivo listo para traducir en: {ARCHIVO_SALIDA}")

if __name__ == "__main__":
    extraer_eventos_json_api()