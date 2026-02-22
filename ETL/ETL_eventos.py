import json
import pandas as pd
import os

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATOS"
DSA = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA"
CARPETA_EVENTOS = os.path.join(RUTA_BASE, "partidos_eventos")
ARCHIVO_SALIDA = os.path.join(DSA, "h_partidos_eventos.csv")

mapeo_eventos = {
    "Argument": "Discusión / protesta",
    "Card": "Tarjeta",
    "Card reviewed": "Tarjeta revisada",
    "Card upgrade": "Tarjeta aumentada",
    "Dangerous play": "Juego peligroso",
    "Delay of game": "Pérdida de tiempo",
    "Diving": "Simulación",
    "Elbowing": "Codazo",
    "Foul": "Falta",
    "Goal": "Gol",
    "Goal cancelled": "Gol anulado",
    "Goal confirmed": "Gol confirmado",
    "Handball": "Mano",
    "Handling": "Mano",
    "Holding": "Sujeción",
    "Missed Penalty": "Penalti fallado",
    "Normal Goal": "Gol en jugada",
    "Not on pitch": "Fuera del campo",
    "Off the ball foul": "Falta sin balón",
    "Own Goal": "Gol en propia",
    "Penalty": "Penalti",
    "Penalty awarded": "Penalti señalado",
    "Penalty cancelled": "Penalti anulado",
    "Penalty confirmed": "Penalti confirmado",
    "Persistent fouling": "Faltas reiteradas",
    "Professional foul last man": "Falta como último hombre",
    "Professional handball": "Mano profesional",
    "Red Card": "Tarjeta roja",
    "Red card cancelled": "Roja anulada",
    "Rescinded Card": "Tarjeta retirada",
    "Roughing": "Juego brusco",
    "Simulation": "Simulación",
    "Substitution 1": "Sustitución 1",
    "Substitution 2": "Sustitución 2",
    "Substitution 3": "Sustitución 3",
    "Substitution 4": "Sustitución 4",
    "Substitution 5": "Sustitución 5",
    "Substitution 6": "Sustitución 6",
    "Time wasting": "Pérdida de tiempo",
    "Tripping": "Zancadilla",
    "Unallowed field entering": "Entrada ilegal al campo",
    "Unsportsmanlike conduct": "Conducta antideportiva",
    "Var": "VAR",
    "Violent conduct": "Conducta violenta",
    "Yellow Card": "Tarjeta amarilla",
    "subst": "Sustitución"
}

def traducir_eventos(evento):
    """Traduce la posición del inglés al español"""
    if evento is None:
        return None
    return mapeo_eventos.get(evento, evento)

def etl_eventos():
    # Buscamos todos los archivos JSON en la carpeta de eventos
    if not os.path.exists(CARPETA_EVENTOS):
        print(f"No se encuentra la carpeta: {CARPETA_EVENTOS}")
        return

    archivos = [f for f in os.listdir(CARPETA_EVENTOS) if f.endswith('.json')]
    todos_los_eventos = []

    for archivo in archivos:
        ruta_archivo = os.path.join(CARPETA_EVENTOS, archivo)
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except:
                continue

            # Iteramos por cada partido en el JSON
            for partido in data:
                f_id = partido.get("fixture_id")
                eventos = partido.get("events", [])

                for e in eventos:
                    # Extraemos la información de forma plana
                    fila = {
                        "id_partido": f_id,
                        "minuto": e.get("time", {}).get("elapsed"),
                        "extra": e.get("time", {}).get("extra"),
                        "id_equipo": e.get("team", {}).get("id"),
                        "id_jugador": e.get("player", {}).get("id"),
                        "id_asistente_o_sale": e.get("assist", {}).get("id"),
                        "tipo": traducir_eventos(e.get("type")),
                        "detalle": traducir_eventos(e.get("detail")),
                        "comentarios": traducir_eventos(e.get("comments"))
                    }
                    todos_los_eventos.append(fila)

    if not todos_los_eventos:
        print("⚠️ No se encontraron eventos para procesar.")
        return

    # Crear DataFrame
    df = pd.DataFrame(todos_los_eventos)

    # Convertir IDs a enteros 
    cols_ids = ["id_partido", "id_equipo", "id_jugador", "id_asistente_o_sale"]
    for col in cols_ids:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # El minuto también debe ser entero
    df['minuto'] = pd.to_numeric(df['minuto'], errors='coerce').fillna(0).astype(int)
    df['extra'] = pd.to_numeric(df['extra'], errors='coerce').fillna(0).astype(int)


    # Ordenar por partido y minuto para que el CSV sea legible
    df = df.sort_values(by=["id_partido", "minuto"])

    # Guardar CSV
    df.to_csv(ARCHIVO_SALIDA, index=False, sep=';', encoding='utf-8-sig')
    print(f"✅ ETL de Eventos completado. {len(df)} eventos guardados en: {ARCHIVO_SALIDA}")

if __name__ == "__main__":
    etl_eventos()