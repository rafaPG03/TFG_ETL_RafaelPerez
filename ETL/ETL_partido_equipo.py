import json
import pandas as pd
import os

RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
DSA = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA" 
CARPETA_STATS = os.path.join(RUTA_BASE, "partidos_stats")
ARCHIVO_SALIDA = os.path.join(DSA, "h_equipo_partido.csv")

MAPEO_STATS = {
    "Shots on Goal": "tiros_a_puerta",
    "Total Shots": "tiros_totales",
    "Shots insidebox": "tiros_en_area",
    "Shots outsidebox": "tiros_fuera_area",
    "Fouls": "faltas_cometidas",
    "Corner Kicks": "corners",
    "Offsides": "fueras_de_juego",
    "Ball Possession": "posesion",
    "Yellow Cards": "tarjetas_amarillas",
    "Red Cards": "tarjetas_rojas",
    "Goalkeeper Saves": "paradas",
    "Total passes": "pases_totales",
    "Passes accurate": "pases_acertados",
    "Passes %": "pct_pases_acertados",
    "expected_goals": "goles_esperados",
    "goals_prevented": "df_goles_esperados" 
}

def procesar_stats_equipos():
    rows = []
    
    if not os.path.exists(CARPETA_STATS):
        print("Carpeta no encontrada.")
        return

    for archivo in os.listdir(CARPETA_STATS):
        if archivo.endswith('.json'):
            with open(os.path.join(CARPETA_STATS, archivo), 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for game in data:
                    fixture_id = game.get("fixture_id")
                    
                    for team_data in game.get("statistics", []):
                        fila = {
                            "id_partido": fixture_id,
                            "id_equipo": team_data["team"]["id"],
                        }

                        # Inicializa todas las estadísticas para mantener un esquema estable.
                        for col in MAPEO_STATS.values():
                            fila[col] = 0
                        
                        stats_list = team_data.get("statistics", [])
                        for s in stats_list:
                            tipo = s.get("type")
                            valor = s.get("value")
                            if tipo in MAPEO_STATS:
                                if isinstance(valor, str) and "%" in valor:
                                    valor = valor.replace("%", "")
                                fila[MAPEO_STATS[tipo]] = valor if valor is not None else 0
                        rows.append(fila)

    df = pd.DataFrame(rows)

    # Las métricas de goles esperados conservan decimales.
    cols_decimal = ["goles_esperados"]
    
    # El resto de estadísticas son recuentos enteros.
    cols_para_enteros = [c for c in df.columns if c not in ["nombre", "id_partido", "id_equipo"] + cols_decimal]

    for col in cols_para_enteros:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    for col in cols_decimal:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0).astype(float)

    df.to_csv(ARCHIVO_SALIDA, index=False, sep=';', encoding='utf-8-sig')
    print(f"✅ ETL de Estadísticas finalizado. {len(df)} filas generadas.")

if __name__ == "__main__":
    procesar_stats_equipos()
