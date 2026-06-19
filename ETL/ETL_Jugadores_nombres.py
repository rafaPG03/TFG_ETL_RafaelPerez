import json
import pandas as pd
import os

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
DSA = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA" 
CARPETA_JUGADORES = os.path.join(RUTA_BASE, "jugadores_temporada") 
# NUEVA RUTA: Ajusta el nombre de la carpeta donde están los JSON de los partidos/fixtures
CARPETA_PARTIDOS = os.path.join(RUTA_BASE, "jugadores_partido") 

ARCHIVO_SALIDA = os.path.join(DSA, "dim_jugadoresNew.csv")

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
    if pais is None: return None
    return paises_traduccion.get(pais, pais)

def cargar_nombres_cortos():
    """
    Escanea la carpeta de partidos para crear un mapa de {id_jugador: nombre_corto}
    """
    nombres_map = {}
    if not os.path.exists(CARPETA_PARTIDOS):
        print(f"⚠️ Carpeta de partidos {CARPETA_PARTIDOS} no encontrada. Se usarán nombres por defecto.")
        return nombres_map

    archivos = [f for f in os.listdir(CARPETA_PARTIDOS) if f.endswith('.json')]
    
    for archivo in archivos:
        ruta = os.path.join(CARPETA_PARTIDOS, archivo)
        with open(ruta, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # La estructura según tu ejemplo es una lista de fixtures
                for fixture in data:
                    # 'players' es una lista de equipos (local/visitante)
                    for team_data in fixture.get('players', []):
                        # Dentro de cada equipo hay otra lista 'players' con los jugadores
                        for p_entry in team_data.get('players', []):
                            p_info = p_entry.get('player', {})
                            id_j = p_info.get('id')
                            nombre_corto = p_info.get('name')
                            if id_j and nombre_corto:
                                nombres_map[id_j] = nombre_corto
            except Exception as e:
                print(f"Error leyendo {archivo}: {e}")
    
    print(f"🔗 Mapeo de nombres completado. {len(nombres_map)} nombres cortos encontrados.")
    return nombres_map

def procesar_jugadores_unicos():
    # 1. Cargar primero el mapeo de nombres conocidos
    nombres_cortos_dict = cargar_nombres_cortos()
    
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
                    # --- LÓGICA DE NOMBRE ---
                    # Si el ID existe en nuestro mapa de nombres cortos, lo usamos.
                    # Si no, usamos el nombre que viene en el JSON de la temporada.
                    nombre_a_usar = nombres_cortos_dict.get(id_jugador, p.get('name'))
                    p_firstname = p.get('firstname') or ""
                    p_lastname = p.get('lastname') or ""

                    # 2. Creamos la variable única de nombre completo (limpiando espacios extra)
                    nombre_completo = f"{p_firstname} {p_lastname}".strip()
                    
                    altura = str(p.get('height')).replace(' cm', '').strip()
                    peso = str(p.get('weight')).replace(' kg', '').strip()
                    
                    if altura == 'None' or altura == '': altura = None
                    if peso == 'None' or peso == '': peso = None
                    
                    jugadores_dict[id_jugador] = {
                        "id_jugador": id_jugador,
                        "nombre": nombre_a_usar, # <--- Nombre actualizado
                        "nombre_completo": nombre_completo,
                        "edad": p.get('age'),
                        "fecha_nacimiento": p.get('birth', {}).get('date'),
                        "lugar_nacimiento": p.get('birth', {}).get('place'),
                        "pais_nacimiento": traducir_pais(p.get('birth', {}).get('country')),
                        "nacionalidad": traducir_pais(p.get('nationality')),
                        "altura": altura,
                        "peso": peso,
                        "foto": p.get('photo')
                    }

    df = pd.DataFrame(list(jugadores_dict.values()))

    # Limpieza
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df['edad'] = pd.to_numeric(df['edad'], errors='coerce')
    df['altura'] = pd.to_numeric(df['altura'], errors='coerce')
    df['peso'] = pd.to_numeric(df['peso'], errors='coerce')
    df = df.sort_values(by="nombre")

    # Guardar CSV
    df.to_csv(
        ARCHIVO_SALIDA, 
        index=False, 
        sep=';', 
        encoding='utf-8-sig', 
        na_rep='', 
        float_format='%.0f'
    )
    
    print(f"✅ ETL de Jugadores completado.")
    print(f"👤 Total de jugadores únicos: {len(df)}")

if __name__ == "__main__":
    procesar_jugadores_unicos()