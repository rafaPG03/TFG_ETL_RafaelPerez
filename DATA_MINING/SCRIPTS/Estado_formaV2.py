import argparse
import os
import pandas as pd
import numpy as np
from pathlib import Path
import importlib

# ============================================================================
# MODELO MEJORADO DE ESTADO DE FORMA - TEMPORADA 2025
# ============================================================================
# Cambios clave:
# 1. Ponderación temporal exponencial (partidos recientes pesan más)
# 2. Bonus aditivo por rivales en lugar de multiplicativo
# 3. Análisis xG mejorado con métricas de "suerte"
# 4. Arquitectura modular con funciones
# 5. Validación de datos y manejo de errores
# 6. Métricas adicionales (tendencia, variabilidad)
# ============================================================================

# CONFIGURACIÓN
TEMPORADA_TARGET = 2025
NUM_PARTIDOS = 5
BONUS_TOP6 = 0.5  # Bonus más generoso por rival difícil
PONDERACION_TEMPORAL = 0.85  # Decay exponencial para partidos antiguos

# Umbrales de clasificación (más permisivos)
UMBRAL_POSITIVO = 5.5  # Antes era 7
UMBRAL_CRITICO = 3.2  # Antes era 4
FACTOR_NORMALIZACION = 3.0  # Antes era 4.3 (permite puntuaciones más altas)

BASE_DIR = Path(r'C:\Users\rafa-\OneDrive\Escritorio\ESI\TFG\DATA_MINING\DSA_DM')
OUTPUT_FILE = BASE_DIR / "ESTADO_FORMA_EQUIPOS_2025.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calcula estado de forma leyendo datos desde PostgreSQL"
    )
    parser.add_argument("--db-host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--db-port", default=os.getenv("PGPORT", "5432"))
    parser.add_argument("--db-name", default=os.getenv("PGDATABASE", "TFG_BDLaLiga"))
    parser.add_argument("--db-user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("PGPASSWORD", "betico18"))
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    return parser.parse_args()


def read_table(conn, query: str) -> pd.DataFrame:
    return pd.read_sql_query(query, conn)


def cargar_datos(args: argparse.Namespace):
    """Carga y limpia los datos necesarios desde PostgreSQL."""
    print("📥 Cargando datos...")
    try:
        psycopg2 = importlib.import_module("psycopg2")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Falta psycopg2 en el entorno actual. Instala: pip install psycopg2-binary"
        ) from exc

    conn = psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password,
    )

    try:
        df_partidos = read_table(
            conn,
            """
            SELECT
                id_partido,
                temporada,
                id_local,
                id_visitante,
                goles_local,
                goles_visitante,
                status
            FROM public.dim_partidos
            """,
        )

        df_stats = read_table(
            conn,
            """
            SELECT
                id_partido,
                id_equipo,
                goles_esperados
            FROM public.h_equipo_partido
            """,
        )

        df_clasificacion = read_table(
            conn,
            """
            SELECT
                t.id_equipo,
                e.nombre_equipo,
                t.temporada,
                t.jornada,
                t.posicion
            FROM public.h_equipo_temporada t
            LEFT JOIN public.dim_equipo e ON e.id_equipo = t.id_equipo
            """,
        )
    finally:
        conn.close()

    # Limpieza de espacios en nombres
    for df in [df_partidos, df_stats, df_clasificacion]:
        df.columns = df.columns.str.strip()

    return df_partidos, df_stats, df_clasificacion

def obtener_info_equipos_temporada(df_clasificacion, temporada):
    """Obtiene equipos y ranking de una temporada."""
    df_temp = df_clasificacion[df_clasificacion['temporada'] == temporada].copy()

    if not df_temp.empty and 'jornada' in df_temp.columns:
        idx = df_temp.groupby('id_equipo')['jornada'].idxmax()
        df_temp = df_temp.loc[idx].copy()
    
    if df_temp.empty:
        print(f"⚠️  Advertencia: No hay datos para la temporada {temporada}")
        return pd.DataFrame(), []
    
    equipos_top6 = df_temp.nsmallest(6, 'posicion')['id_equipo'].tolist()
    return df_temp, equipos_top6

def calcular_puntos_base(goles_favor, goles_contra):
    """Calcula puntos base por resultado (0, 1 o 3)."""
    if goles_favor > goles_contra:
        return 3
    elif goles_favor == goles_contra:
        return 1
    else:
        return 0

def aplicar_ajustes_xg(puntos, goles_favor, goles_contra, xg_propio, xg_rival):
    """
    Ajusta puntos basado en xG para capturar "suerte" (fortuna/desgracia).
    Lógica más permisiva: menos penalizaciones, más bonos.
    """
    ajuste = 0
    
    # Si perdiste pero merecías mucho más
    if puntos == 0 and xg_propio > (xg_rival + 0.5):
        ajuste = 0.6  # Bono robusto por mala suerte
    
    # Si ganaste pero apenas tuviste oportunidades (suerte extrema)
    elif puntos == 3 and xg_propio < xg_rival - 0.7:
        ajuste = -0.1  # Penalización muy suave
    
    # Si empataste siendo defensivamente sólido
    elif puntos == 1 and xg_propio < (xg_rival - 0.3):
        ajuste = 0.2  # Bono defensivo
    
    return puntos + ajuste

def calcular_bonus_rival(id_rival, equipos_top6):
    """Bonus por enfrentar rival difícil (top 6)."""
    return BONUS_TOP6 if id_rival in equipos_top6 else 0

def procesamiento_partido(partido, id_equipo, id_rival, stats_rival, equipos_top6):
    """Procesa un partido individual para calcular puntuación."""
    es_local = partido['id_local'] == id_equipo
    
    # Goles
    goles_favor = partido['goles_local'] if es_local else partido['goles_visitante']
    goles_contra = partido['goles_visitante'] if es_local else partido['goles_local']
    
    # Puntos base
    puntos = calcular_puntos_base(goles_favor, goles_contra)
    
    # Ajuste xG
    if 'goles_esperados' in partido and not stats_rival.empty:
        try:
            xg_propio = float(partido['goles_esperados'])
            xg_rival = float(stats_rival.iloc[0]['goles_esperados'])
            puntos = aplicar_ajustes_xg(puntos, goles_favor, goles_contra, xg_propio, xg_rival)
        except (ValueError, KeyError):
            pass  # Si falta xG, solo usamos resultado
    
    # Bonus rival
    puntos += calcular_bonus_rival(id_rival, equipos_top6)
    
    return puntos

def calcular_forma_equipo(eq_id, df_2025, df_stats, df_partidos, equipos_top6):
    """Calcula puntuación de forma para un equipo específico."""
    
    # Obtener nombre
    equipo_info = df_2025[df_2025['id_equipo'] == eq_id]
    if equipo_info.empty:
        return None
    
    nombre_equipo = equipo_info['nombre_equipo'].iloc[0]
    
    # Filtrar partidos de este equipo (SOLO TEMPORADA 2025)
    mis_stats = df_stats[df_stats['id_equipo'] == eq_id]
    mis_partidos = mis_stats.merge(df_partidos[df_partidos['temporada'] == TEMPORADA_TARGET], 
                                    on='id_partido', how='inner')
    
    if mis_partidos.empty:
        print(f"⚠️  {nombre_equipo}: Sin partidos en {TEMPORADA_TARGET}")
        return None
    
    # Últimos N partidos ordenados cronológicamente
    ultimos_n = mis_partidos.sort_values(by='id_partido', ascending=False).head(NUM_PARTIDOS)
    ultimos_n = ultimos_n.sort_values(by='id_partido', ascending=True)  # Cronológico para ponderación
    
    # Calcular puntos con ponderación temporal
    puntos_ponderados = []
    pesos = []
    
    for idx, (_, partido) in enumerate(ultimos_n.iterrows()):
        # Peso exponencial: partidos recientes pesan más
        peso = PONDERACION_TEMPORAL ** (NUM_PARTIDOS - idx - 1)
        pesos.append(peso)
        
        # Identificar rival
        id_rival = partido['id_visitante'] if partido['id_local'] == eq_id else partido['id_local']
        
        # Obtener stats rival
        stats_rival = df_stats[(df_stats['id_partido'] == partido['id_partido']) & 
                               (df_stats['id_equipo'] != eq_id)]
        
        # Calcular puntuación del partido
        puntos = procesamiento_partido(partido, eq_id, id_rival, stats_rival, equipos_top6)
        puntos_ponderados.append(puntos * peso)
    
    # Promedio ponderado
    nota_media = np.sum(puntos_ponderados) / np.sum(pesos)
    
    # Métricas adicionales
    tendencia = ultimos_n['temporada'].iloc[-1] - ultimos_n['temporada'].iloc[0] if len(ultimos_n) > 1 else 0
    variabilidad = np.std(puntos_ponderados)
    
    # Normalización a escala 0-10 (más permisiva)
    nota_final = min(10, (nota_media / FACTOR_NORMALIZACION) * 10)
    
    # Determinar estado (umbrales más permisivos)
    if nota_final >= UMBRAL_POSITIVO:
        estado = "🔥 Positivo"
    elif nota_final >= UMBRAL_CRITICO:
        estado = "📊 Estable"
    else:
        estado = "❌ Crítico"
    
    return {
        'id_equipo': eq_id,
        'nombre_equipo': nombre_equipo,
        'puntuacion_forma': round(nota_final, 2),
        'estado': estado,
        'tendencia': round(nota_media, 2),  # Score bruto sin normalizar
        'variabilidad': round(variabilidad, 2)
    }

def main():
    args = parse_args()

    # Cargar datos
    df_partidos, df_stats, df_clasificacion = cargar_datos(args)
    
    # Obtener equipos de temporada objetivo
    df_2025, equipos_top6 = obtener_info_equipos_temporada(df_clasificacion, TEMPORADA_TARGET)
    
    if df_2025.empty:
        print(f"❌ No hay datos disponibles para la temporada {TEMPORADA_TARGET}")
        exit(1)
    
    lista_equipos_2025 = df_2025['id_equipo'].unique()
    print(f"✅ Procesando {len(lista_equipos_2025)} equipos...")
    
    # Procesar cada equipo
    resultados_forma = []
    
    for eq_id in lista_equipos_2025:
        resultado = calcular_forma_equipo(eq_id, df_2025, df_stats, df_partidos, equipos_top6)
        if resultado:
            resultados_forma.append(resultado)
    
    # Crear DataFrame y exportar
    df_export = pd.DataFrame(resultados_forma)
    df_export = df_export.sort_values('puntuacion_forma', ascending=False)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_export.to_csv(output_path, index=False, sep=';')
    
    print(f"\n✅ ¡Análisis completado! {len(df_export)} equipos procesados")
    print(f"📁 Exportado a: {output_path}\n")
    print(df_export.to_string(index=False))

if __name__ == "__main__":
    main()