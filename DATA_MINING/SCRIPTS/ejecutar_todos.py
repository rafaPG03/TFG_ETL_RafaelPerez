from __future__ import annotations

import subprocess
import sys
from pathlib import Path


RUTA_SCRIPTS = Path(__file__).resolve().parent
RUTA_SALIDAS = RUTA_SCRIPTS.parent / "DSA_DM"

SCRIPTS_A_EJECUTAR = [
    ("ratings.py", []),
    ("cargar_perfil_estadistico_jugadores.py", []),
    ("clasificacion_rendimiento_jugadores.py", []),
    ("similitud_jugadores.py", []),
    ("Estado_formaV2.py", []),
    ("forma_jugadorv2.py", []),
    ("prob_goleadores.py", []),
    ("aspectos_a_mejorar.py", []),
    ("recomendacion_fichajes_refuerzo.py", []),
    (
        "v3predicccion.py",
        ["--output", str(RUTA_SALIDAS / "predicciones_partidos_incompletos.csv")],
    ),
    ("prediccion_goles_partidos.py", []),
    ("simulacion_montecarlo_laliga.py", []),
]


def ejecutar_script(nombre_script: str, argumentos: list[str]) -> int:
    ruta_script = RUTA_SCRIPTS / nombre_script
    if not ruta_script.exists():
        print(f"[SKIP] No existe: {nombre_script}")
        return 0

    comando = [sys.executable, str(ruta_script), *argumentos]
    print(f"\n=== Ejecutando {nombre_script} ===")
    proceso = subprocess.run(comando, cwd=RUTA_SCRIPTS)

    if proceso.returncode == 0:
        print(f"[OK] {nombre_script}")
    else:
        print(f"[FAIL] {nombre_script} -> codigo {proceso.returncode}")

    return proceso.returncode


def main() -> int:
    errores = []

    for nombre_script, argumentos in SCRIPTS_A_EJECUTAR:
        codigo = ejecutar_script(nombre_script, argumentos)
        if codigo != 0:
            errores.append((nombre_script, codigo))

    print("\n=== Resumen ===")
    if not errores:
        print("Todos los scripts se ejecutaron correctamente.")
        return 0

    for nombre_script, codigo in errores:
        print(f"- {nombre_script}: codigo {codigo}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
