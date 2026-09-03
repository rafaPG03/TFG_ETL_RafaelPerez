import pandas as pd
import os

DSA = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA"
ARCHIVO_PARTIDOS = os.path.join(DSA, "dim_partidos.csv")
ARCHIVO_TIEMPO = os.path.join(DSA, "dim_tiempo.csv")

def crear_dimension_tiempo_con_jornada():
    if not os.path.exists(ARCHIVO_PARTIDOS):
        print(f"No se encuentra el archivo: {ARCHIVO_PARTIDOS}")
        return
        
    df_partidos = pd.read_csv(ARCHIVO_PARTIDOS, sep=';')
    
    # La jornada depende de la temporada y no solo de la fecha.
    df_tiempo = df_partidos[['fecha', 'jornada', 'temporada']].drop_duplicates()
    
    df_tiempo['fecha_dt'] = pd.to_datetime(df_tiempo['fecha'])
    
    df_tiempo['id_tiempo'] = df_tiempo['fecha_dt'].dt.strftime('%Y%m%d').astype(int)
    df_tiempo['anio'] = df_tiempo['fecha_dt'].dt.year
    df_tiempo['mes'] = df_tiempo['fecha_dt'].dt.month
    df_tiempo['nombre_mes'] = df_tiempo['fecha_dt'].dt.month_name(locale='es_ES')
    df_tiempo['dia'] = df_tiempo['fecha_dt'].dt.day
    df_tiempo['nombre_dia'] = df_tiempo['fecha_dt'].dt.day_name(locale='es_ES')

    columnas_finales = [
        'id_tiempo', 'fecha', 'temporada', 'jornada', 
        'anio', 'mes', 'nombre_mes', 'dia', 'nombre_dia'
    ]
    df_tiempo = df_tiempo[columnas_finales].sort_values(by='id_tiempo')

    df_tiempo.to_csv(ARCHIVO_TIEMPO, index=False, sep=';', encoding='utf-8-sig')
    print(f"✅ Dimensión Tiempo (con Jornadas) creada: {len(df_tiempo)} registros.")

if __name__ == "__main__":
    crear_dimension_tiempo_con_jornada()
