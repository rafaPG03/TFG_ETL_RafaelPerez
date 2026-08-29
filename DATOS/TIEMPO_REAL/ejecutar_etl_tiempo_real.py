import subprocess
import sys
from pathlib import Path


SCRIPTS_ETL = [
    "ETL_Partido_Equipo_Tiempo_Real.py",
    "ETL_Jugador_Partido_Tiempo_Real.py",
    "ETL_Eventos_Tiempo_Real.py",
]


def ejecutar_script(ruta_script):
    print(f"\nEjecutando: {ruta_script.name}")
    resultado = subprocess.run(
        [sys.executable, str(ruta_script)],
        cwd=ruta_script.parent,
        check=False,
    )

    if resultado.returncode != 0:
        raise RuntimeError(
            f"El script {ruta_script.name} termino con codigo {resultado.returncode}"
        )


def main():
    carpeta_actual = Path(__file__).resolve().parent

    for nombre_script in SCRIPTS_ETL:
        ruta_script = carpeta_actual / nombre_script
        if not ruta_script.exists():
            raise FileNotFoundError(f"No se encontro el script: {ruta_script}")

        ejecutar_script(ruta_script)

    print("\nETL de tiempo real finalizado correctamente.")


if __name__ == "__main__":
    main()
