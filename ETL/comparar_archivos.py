import pandas as pd

# 1. Cargar los archivos CSV
# Usamos sep=';' porque es el delimitador que indicaste en tus ejemplos
df_eventos = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\h_partidos_eventos.csv', sep=';')
df_maestro = pd.read_csv(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\ETL\DSA\dim_jugadoresNew.csv', sep=';')

# 2. Obtener los IDs únicos de cada archivo
# Extraemos la columna id_jugador de eventos (eliminando duplicados y nulos)
ids_en_eventos = set(df_eventos['id_jugador'].dropna().unique())

# Extraemos la columna id_jugador del maestro de jugadores
ids_en_maestro = set(df_maestro['id_jugador'].unique())

# 3. Encontrar los que están en eventos pero NO en el maestro (Diferencia de conjuntos)
jugadores_faltantes = ids_en_eventos - ids_en_maestro

# 4. Mostrar resultados
if jugadores_faltantes:
    print(f"⚠️ Se han encontrado {len(jugadores_faltantes)} IDs de jugadores que faltan en dim_jugadores2.csv:")
    print(list(jugadores_faltantes))
    
    # Opcional: Guardarlos en un nuevo CSV para revisarlos
    # pd.DataFrame(list(jugadores_faltantes), columns=['id_jugador']).to_csv('ids_faltantes.csv', index=False)
else:
    print("✅ ¡Todo correcto! Todos los jugadores de los eventos existen en el maestro.")