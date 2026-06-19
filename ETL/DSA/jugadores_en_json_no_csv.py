from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def leer_jugadores_json(ruta_json: Path) -> dict[int, str]:
    """Extrae jugadores del JSON de partidos en formato {id: nombre}."""
    with ruta_json.open("r", encoding="utf-8") as f:
        datos = json.load(f)

    jugadores: dict[int, str] = {}
    for partido in datos:
        for entrada_equipo in partido.get("data", []):
            for entrada_jugador in entrada_equipo.get("players", []):
                jugador = entrada_jugador.get("player", {})
                jugador_id = jugador.get("id")
                nombre = (jugador.get("name") or "").strip()
                if jugador_id is None:
                    continue
                try:
                    jugador_id_int = int(jugador_id)
                    # Conserva el primer nombre no vacio encontrado para cada ID.
                    if jugador_id_int not in jugadores or not jugadores[jugador_id_int]:
                        jugadores[jugador_id_int] = nombre
                except (TypeError, ValueError):
                    continue
    return jugadores


def leer_ids_csv(ruta_csv: Path) -> set[int]:
    """Extrae IDs de jugador de dim_jugadoresNew.csv (columna id_jugador)."""
    ids: set[int] = set()
    with ruta_csv.open("r", encoding="utf-8-sig", newline="") as f:
        muestra = f.read(4096)
        f.seek(0)
        dialecto = csv.Sniffer().sniff(muestra, delimiters=",;")
        reader = csv.DictReader(f, dialect=dialecto)
        for fila in reader:
            jugador_id = fila.get("id_jugador") or fila.get("\ufeffid_jugador")
            if not jugador_id:
                continue
            try:
                ids.add(int(jugador_id))
            except ValueError:
                continue
    return ids


def construir_parser() -> argparse.ArgumentParser:
    script_path = Path(__file__).resolve()
    raiz_proyecto = script_path.parents[2]

    parser = argparse.ArgumentParser(
        description="Muestra IDs de jugadores presentes en JSON y ausentes en CSV."
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=raiz_proyecto / "DATOS" / "TIEMPO_REAL" / "partidos_jugadores_full.json",
        help="Ruta al JSON de partidos_jugadores_full.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=raiz_proyecto / "ETL" / "DSA" / "dim_jugadoresNew.csv",
        help="Ruta al CSV dim_jugadoresNew.",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=None,
        help="Opcional: guarda los faltantes en un TXT con formato id;nombre.",
    )
    return parser


def main() -> None:
    parser = construir_parser()
    args = parser.parse_args()

    ruta_json: Path = args.json
    ruta_csv: Path = args.csv
    ruta_salida: Path | None = args.salida

    if not ruta_json.exists():
        raise FileNotFoundError(f"No existe el JSON: {ruta_json}")
    if not ruta_csv.exists():
        raise FileNotFoundError(f"No existe el CSV: {ruta_csv}")

    jugadores_json = leer_jugadores_json(ruta_json)
    ids_csv = leer_ids_csv(ruta_csv)
    faltan_en_csv = sorted(set(jugadores_json) - ids_csv)

    print(f"IDs unicos en JSON: {len(jugadores_json)}")
    print(f"IDs unicos en CSV: {len(ids_csv)}")
    print(f"IDs en JSON y no en CSV: {len(faltan_en_csv)}")

    if faltan_en_csv:
        print("\nListado de jugadores faltantes (id;nombre):")
        for jugador_id in faltan_en_csv:
            nombre = jugadores_json.get(jugador_id, "")
            print(f"{jugador_id};{nombre}")

    if ruta_salida is not None:
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        with ruta_salida.open("w", encoding="utf-8", newline="") as f:
            f.write("id_jugador;nombre\n")
            for jugador_id in faltan_en_csv:
                nombre = jugadores_json.get(jugador_id, "")
                f.write(f"{jugador_id};{nombre}\n")
        print(f"\nIDs guardados en: {ruta_salida}")


if __name__ == "__main__":
    main()