import pandas as pd
import os

# --- CONFIGURACIÓN DE RUTAS ---
RUTA_BASE = r"C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA"
ARCHIVO_PARTIDOS = os.path.join(RUTA_BASE, "dim_partidos.csv")
ARCHIVO_TIEMPO = os.path.join(RUTA_BASE, "dim_tiempo.csv")


def limpiar_dim_tiempo():
    """Elimina duplicados por día y mantiene solo atributos del día"""
    
    df_tiempo = pd.read_csv(ARCHIVO_TIEMPO, sep=';')
    
    # Pillar solo ids sin duplicar
    df_unico = df_tiempo.drop_duplicates(subset=['id_tiempo'], keep='first')
    
    # Seleccionar solo las columnas deseadas
    columnas_deseadas = ['id_tiempo', 'anio', 'mes', 'nombre_mes', 'dia', 'nombre_dia', 'jornada']
    df_final = df_unico[columnas_deseadas]
    
    # Guardar en CSV
    df_final.to_csv(ARCHIVO_TIEMPO, index=False, sep=';', encoding='utf-8-sig')
    
    print(f"✅ dim_tiempo limpiada. Registros únicos: {len(df_final)}") 


def preparar_dim_partidos():
    """Extrae hora en columna separada y vincula con id_tiempo"""
    
    # Leer CSV
    df_partidos = pd.read_csv(ARCHIVO_PARTIDOS, sep=';')
    
    # Procesamos fecha: extraer id_tiempo (YYYYMMDD) y hora (HH:MM)
    df_partidos['fecha'] = pd.to_datetime(df_partidos['fecha'], errors='coerce')
    df_partidos['id_tiempo'] = pd.to_numeric(
        df_partidos['fecha'].dt.strftime('%Y%m%d'), errors='coerce'
    ).astype('Int64')
    df_partidos['hora'] = df_partidos['fecha'].dt.strftime('%H:%M')

    # Aseguramos que los goles se mantengan como enteros nullable al reescribir el CSV.
    for col in ['goles_local', 'goles_visitante']:
        if col in df_partidos.columns:
            df_partidos[col] = pd.to_numeric(df_partidos[col], errors='coerce').astype('Int64')
    
    # Eliminamos columna fecha original
    df_partidos = df_partidos.drop(columns=['fecha','jornada'])
    
    # Reordenamos columnas: id_partido, id_tiempo, hora, resto
    otras_columnas = [col for col in df_partidos.columns if col not in ['id_partido', 'id_tiempo', 'hora']]
    columnas_finales = ['id_partido', 'id_tiempo', 'hora'] + otras_columnas
    df_final = df_partidos[columnas_finales]
    
    # Guardar 
    df_final.to_csv(ARCHIVO_PARTIDOS, index=False, sep=';', encoding='utf-8-sig')
    
    print(f"✅ dim_partidos actualizada. Registros: {len(df_final)}")


if __name__ == "__main__":
    limpiar_dim_tiempo()
    preparar_dim_partidos()
    print("\n✅ Proceso completado exitosamente")
