import json
import pandas as pd
import os

RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
DSA = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA" 
CARPETA_PARTIDOS_JUGADORES = os.path.join(RUTA_BASE, "jugadores_partido")
ARCHIVO_SALIDA = os.path.join(DSA, "h_jugador_partido.csv")

mapeo_posiciones={
    "G":"P",
    "D":"DF",
    "F":"DL"
}

def traducir_posicion(posicion):
    if posicion is None:
        return None
    return mapeo_posiciones.get(posicion, posicion)

def procesar_jugadores_partido():
    rows = []
    
    if not os.path.exists(CARPETA_PARTIDOS_JUGADORES):
        print("Carpeta no encontrada.")
        return

    archivos = [f for f in os.listdir(CARPETA_PARTIDOS_JUGADORES) if f.endswith('.json')]
    
    for archivo in archivos:
        ruta_completa = os.path.join(CARPETA_PARTIDOS_JUGADORES, archivo)
        with open(ruta_completa, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            for game in data:
                fixture_id = game.get("fixture_id")
                
                for team_entry in game.get("players", []):
                    id_equipo = team_entry.get("team", {}).get("id")
                    
                    for p_data in team_entry.get("players", []):
                        p_info = p_data.get("player", {})
                        for stat in p_data.get("statistics", []):
                            
                            fila = {
                                "id_partido": fixture_id,
                                "id_jugador": p_info.get("id"),
                                "id_equipo": id_equipo,
                                
                                # Participación en el partido.
                                "posicion": traducir_posicion(stat.get("games", {}).get("position")),
                                "minutos": stat.get("games", {}).get("minutes"),
                                "nota": stat.get("games", {}).get("rating"),
                                "capitan": stat.get("games", {}).get("captain"),
                                "sustituto": stat.get("games", {}).get("substitute"),
                                
                                # Rendimiento individual.
                                "goles": stat.get("goals", {}).get("total"),
                                "penaltis_marcados": stat.get('penalty', {}).get('scored'),
                                "asistencias": stat.get("goals", {}).get("assists"),
                                "paradas": stat.get("goals", {}).get("saves"),
                                "goles_concedidos": stat.get("goals", {}).get("conceded"),
                                "tiros_totales": stat.get("shots", {}).get("total"),
                                "tiros_a_puerta": stat.get("shots", {}).get("on"),
                                "pases_totales": stat.get("passes", {}).get("total"),
                                "pases_clave": stat.get("passes", {}).get("key"),
                                "precision_pases": str(stat.get("passes", {}).get("accuracy", "0")).replace('%', ''),
                                "regates_intentados": stat.get("dribbles", {}).get("attempts"),
                                "regates": stat.get("dribbles", {}).get("success"),
                                "regateado": stat.get("dribbles", {}).get("past"),
                                "duelos_totales": stat.get("duels", {}).get("total"),
                                "duelos_ganados": stat.get("duels", {}).get("won"),
                                "faltas_cometidas": stat.get("fouls", {}).get("committed"),
                                "faltas_recibidas": stat.get("fouls", {}).get("drawn"),
                                "entradas": stat.get("tackles", {}).get("total"),
                                "bloqueos": stat.get("tackles", {}).get("blocks"), 
                                "intercepciones": stat.get("tackles", {}).get("interceptions"),                                
                                "amarilla": stat.get("cards", {}).get("yellow"),
                                "roja": stat.get("cards", {}).get("red"),
                                "penaltis_parados": stat.get("penalty", {}).get("saved")
                            }
                            rows.append(fila)

    df = pd.DataFrame(rows)

    df = df.sort_values(by=['id_partido', 'id_equipo'], ascending=[True, True])

    # La nota admite decimales; el resto de estadísticas son recuentos enteros.
    df['nota'] = pd.to_numeric(df['nota'], errors='coerce').fillna(0.0)
    
    cols_enteros = [
        "id_partido", "id_jugador", "id_equipo", "minutos", "goles", "asistencias", 
        "paradas", "tiros_totales", "tiros_a_puerta", "pases_totales", "pases_clave", 
        "precision_pases", "faltas_cometidas", "faltas_recibidas", "amarilla", "roja", "penaltis_parados", "intercepciones",
        "bloqueos", "entradas", "regates_intentados", "regates", "goles_concedidos","duelos_totales", "duelos_ganados", "regateado"
    ]
    
    for col in cols_enteros:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    df.to_csv(ARCHIVO_SALIDA, index=False, sep=';', encoding='utf-8-sig')
    print(f"✅ Procesados {len(df)} registros de jugadores por partido.")

if __name__ == "__main__":
    procesar_jugadores_partido()
