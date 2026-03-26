from __future__ import annotations

import json
from pathlib import Path

import folium
import polyline

from activity_archive.paths import ACTIVITIES_DIR, ALL_ROUTES_PATH


PORTLAND_CENTER = [45.5231, -122.6765]
DEFAULT_ZOOM = 10
TILES = "CartoDB positron"


def iter_activity_files() -> list[Path]:
    return sorted(ACTIVITIES_DIR.glob("*.json"))


def extract_polyline(data: dict) -> str | None:
    map_data = data.get("map")
    if not isinstance(map_data, dict):
        return None

    return map_data.get("polyline") or map_data.get("summary_polyline")


def load_coords_from_file(path: Path) -> list[tuple[float, float]] | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Skipping {path.name}: failed to read JSON ({e})")
        return None

    encoded = extract_polyline(data)
    if not encoded:
        print(f"Skipping {path.name}: no summary polyline found")
        return None

    try:
        coords = polyline.decode(encoded)
    except Exception as e:
        print(f"Skipping {path.name}: failed to decode polyline ({e})")
        return None

    if not coords:
        print(f"Skipping {path.name}: decoded polyline was empty")
        return None

    return coords


def build_map() -> folium.Map:
    return folium.Map(
        location=PORTLAND_CENTER,
        zoom_start=DEFAULT_ZOOM,
        tiles=TILES,
    )


def add_routes_to_map(m: folium.Map) -> tuple[int, int]:
    total_files = 0
    added_routes = 0

    for path in iter_activity_files():
        total_files += 1
        coords = load_coords_from_file(path)
        if not coords:
            continue

        folium.PolyLine(
            locations=coords,
            weight=1.5,
            opacity=0.66,
            color="#FF006E",
        ).add_to(m)

        folium.PolyLine(
            locations=coords,
            weight=6,
            opacity=0.1,
            color="#33006E",
        ).add_to(m)

        added_routes += 1

    return total_files, added_routes


def main() -> None:

    if not ACTIVITIES_DIR.exists():
        raise FileNotFoundError(f"Activities directory not found: {ACTIVITIES_DIR}")

    m = build_map()
    total_files, added_routes = add_routes_to_map(m)

    ALL_ROUTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(ALL_ROUTES_PATH))

    print(f"Scanned files:  {total_files}")
    print(f"Routes added:   {added_routes}")
    print(f"Saved map to:   {ALL_ROUTES_PATH}")


if __name__ == "__main__":
    main()
