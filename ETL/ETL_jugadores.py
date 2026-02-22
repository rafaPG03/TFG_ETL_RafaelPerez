import json
import pandas as pd
import os

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
DSA = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA" 
CARPETA_JUGADORES = os.path.join(RUTA_BASE, "jugadores_temporada") # Ajusta el nombre de tu carpeta
ARCHIVO_SALIDA = os.path.join(DSA, "dim_jugadores.csv")

paises_traduccion = {
    "Albania": "Albania",
    "Algeria": "Argelia",
    "Andorra": "Andorra",
    "Angola": "Angola",
    "Argentina": "Argentina",
    "Armenia": "Armenia",
    "Australia": "Australia",
    "Austria": "Austria",
    "Azerbaijan": "Azerbaiyán",
    "Belarus": "Bielorrusia",
    "Belgium": "Bélgica",
    "Bosnia and Herzegovina": "Bosnia y Herzegovina",
    "Brazil": "Brasil",
    "Bulgaria": "Bulgaria",
    "Burkina Faso": "Burkina Faso",
    "Cameroon": "Camerún",
    "Canada": "Canadá",
    "Cape Verde": "Cabo Verde",
    "Central African Republic": "República Centroafricana",
    "Chile": "Chile",
    "China PR": "RP China",
    "Colombia": "Colombia",
    "Congo": "Congo",
    "Congo DR": "República Democrática del Congo",
    "Costa Rica": "Costa Rica",
    "Croatia": "Croacia",
    "Cuba": "Cuba",
    "Cyprus": "Chipre",
    "Czech Republic": "República Checa",
    "Czechia": "Chequia",
    "Côte d'Ivoire": "Costa de Marfil",
    "Denmark": "Dinamarca",
    "Dominican Republic": "República Dominicana",
    "Ecuador": "Ecuador",
    "England": "Inglaterra",
    "Equatorial Guinea": "Guinea Ecuatorial",
    "Eritrea": "Eritrea",
    "Estonia": "Estonia",
    "Finland": "Finlandia",
    "France": "Francia",
    "French Guiana": "Guayana Francesa",
    "Gabon": "Gabón",
    "Gambia": "Gambia",
    "Georgia": "Georgia",
    "Germany": "Alemania",
    "Ghana": "Ghana",
    "Greece": "Grecia",
    "Guadeloupe": "Guadalupe",
    "Guinea": "Guinea",
    "Guinea-Bissau": "Guinea-Bisáu",
    "Honduras": "Honduras",
    "Hungary": "Hungría",
    "Iceland": "Islandia",
    "Indonesia": "Indonesia",
    "Israel": "Israel",
    "Italy": "Italia",
    "Japan": "Japón",
    "Kenya": "Kenia",
    "Korea Republic": "Corea del Sur",
    "Kosovo": "Kosovo",
    "Liberia": "Liberia",
    "Lithuania": "Lituania",
    "Mali": "Mali",
    "Martinique": "Martinica",
    "Mauritania": "Mauritania",
    "Mexico": "México",
    "Montenegro": "Montenegro",
    "Morocco": "Marruecos",
    "Mozambique": "Mozambique",
    "Netherlands": "Países Bajos",
    "New Caledonia": "Nueva Caledonia",
    "Nicaragua": "Nicaragua",
    "Niger": "Níger",
    "Nigeria": "Nigeria",
    "North Macedonia": "Macedonia del Norte",
    "Norway": "Noruega",
    "Panama": "Panamá",
    "Paraguay": "Paraguay",
    "Peru": "Perú",
    "Poland": "Polonia",
    "Portugal": "Portugal",
    "Puerto Rico": "Puerto Rico",
    "Qatar": "Catar",
    "Republic of Ireland": "Irlanda",
    "Romania": "Rumanía",
    "Russia": "Rusia",
    "Saudi Arabia": "Arabia Saudita",
    "Scotland": "Escocia",
    "Senegal": "Senegal",
    "Serbia": "Serbia",
    "Sierra Leone": "Sierra Leona",
    "Slovakia": "Eslovaquia",
    "Slovenia": "Eslovenia",
    "Spain": "España",
    "Suriname": "Surinam",
    "Sweden": "Suecia",
    "Switzerland": "Suiza",
    "Togo": "Togo",
    "Tunisia": "Túnez",
    "Turkey": "Turquía",
    "Türkiye": "Turquía",
    "USA": "Estados Unidos",
    "Uganda": "Uganda",
    "Ukraine": "Ucrania",
    "Uruguay": "Uruguay",
    "Venezuela": "Venezuela",
    "Wales": "Gales",
    "Yugoslavia": "Yugoslavia",
    "Zambia": "Zambia",
    "Zimbabwe": "Zimbabue"
}

def traducir_pais(pais):
    """Traduce la posición del inglés al español"""
    if pais is None:
        return None
    return paises_traduccion.get(pais, pais)

def procesar_jugadores_unicos():
    jugadores_dict = {}
    
    if not os.path.exists(CARPETA_JUGADORES):
        print(f"Carpeta {CARPETA_JUGADORES} no encontrada.")
        return

    archivos = [f for f in os.listdir(CARPETA_JUGADORES) if f.endswith('.json')]
    
    for archivo in archivos:
        ruta_completa = os.path.join(CARPETA_JUGADORES, archivo)
        with open(ruta_completa, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            for item in data:
                p = item.get('player', {})
                id_jugador = p.get('id')
                
                if id_jugador and id_jugador not in jugadores_dict:
                    # 1. Limpieza inicial de strings
                    altura = str(p.get('height')).replace(' cm', '').strip()
                    peso = str(p.get('weight')).replace(' kg', '').strip()
                    
                    # Si el valor resultante es 'None' o vacío, lo dejamos como None
                    if altura == 'None' or altura == '': altura = None
                    if peso == 'None' or peso == '': peso = None
                    
                    jugadores_dict[id_jugador] = {
                        "id_jugador": id_jugador,
                        "nombre": p.get('name'),
                        "edad": p.get('age'),
                        "fecha_nacimiento": p.get('birth', {}).get('date'),
                        "lugar_nacimiento": p.get('birth', {}).get('place'),
                        "pais_nacimiento": traducir_pais(p.get('birth', {}).get('country')),
                        "nacionalidad": traducir_pais(p.get('nationality')),
                        "altura": altura,
                        "peso": peso,
                        "foto": p.get('photo')
                    }

    # Convertir a DataFrame
    df = pd.DataFrame(list(jugadores_dict.values()))

    # --- LIMPIEZA FINAL ANTI-ERRORES POSTGRES ---
    
    # 1. Quitar espacios en blanco de cualquier columna de texto
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # 2. Convertir columnas numéricas de forma segura
    # errors='coerce' convierte lo que no sea número (espacios, basura) en NaN (Nulo)
    df['edad'] = pd.to_numeric(df['edad'], errors='coerce')
    df['altura'] = pd.to_numeric(df['altura'], errors='coerce')
    df['peso'] = pd.to_numeric(df['peso'], errors='coerce')

    # 3. Manejo de Nulos: 
    # En Postgres, un integer no puede ser '', debe ser un número o NULL.
    # Llenamos los NaN con 0 o los dejamos como vacíos para que el CSV los marque como NULL.
    # Para tu TFG, lo más limpio es que si no hay altura, sea NULL (vacío en el CSV)
    
    # Ordenar por nombre
    df = df.sort_values(by="nombre")

    # Guardar CSV - Usamos quoting para evitar que espacios accidentales rompan la carga
    # na_rep='' asegura que los nulos se guarden como celdas vacías (Postgres lo entiende como NULL)
# ... (todo lo anterior igual hasta llegar al to_csv) ...

    # Guardar CSV 
    # Añadimos float_format='%.0f' para que los .0 desaparezcan al guardar
    df.to_csv(
        ARCHIVO_SALIDA, 
        index=False, 
        sep=';', 
        encoding='utf-8-sig', 
        na_rep='', 
        float_format='%.0f'  # <--- ESTO QUITA LOS DECIMALES
    )
        
    print(f"✅ ETL de Jugadores completado.")
    print(f"👤 Total de jugadores únicos: {len(df)}")
    print(f"📂 Archivo guardado: {ARCHIVO_SALIDA}")

if __name__ == "__main__":
    procesar_jugadores_unicos()