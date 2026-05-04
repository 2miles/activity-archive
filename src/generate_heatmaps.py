from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import folium
import polyline

from activity_archive.paths import ACTIVITIES_DIR, HEATMAPS_DIR

PORTLAND_CENTER = [45.5231, -122.6765]
DEFAULT_ZOOM = 10
TILES = "CartoDB positron"


ENABLED_HEATMAPS = [
    "original",
    "pink_purple",
]


HEATMAP_STYLES = [
    {
        "name": "original",
        "output": "all_routes_original.html",
        "layers": [
            {"weight": 1.5, "opacity": 100, "color": "#FF006E"},
        ],
    },
    {
        "name": "pink_purple",
        "output": "all_routes_pink_purple.html",
        "layers": [
            {"weight": 1.5, "opacity": 0.66, "color": "#FF006E"},
            {"weight": 6, "opacity": 0.10, "color": "#33006E"},
        ],
    },
    {
        "name": "glow",
        "output": "all_routes_glow.html",
        "layers": [
            {"weight": 10, "opacity": 0.05, "color": "#33006E"},
            {"weight": 2, "opacity": 0.35, "color": "#FF006E"},
        ],
    },
    {
        "name": "dark",
        "output": "all_routes_dark.html",
        "layers": [
            {"weight": 2, "opacity": 0.12, "color": "#111111"},
        ],
    },
]


def iter_activity_files() -> list[Path]:
    return sorted(ACTIVITIES_DIR.glob("*.json"))


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def extract_polyline(data: dict[str, Any]) -> str | None:
    map_data = data.get("map")
    if not isinstance(map_data, dict):
        return None

    return map_data.get("polyline") or map_data.get("summary_polyline")


def load_coords_from_file(path: Path) -> list[tuple[float, float]] | None:
    data = load_json(path)
    if not data:
        print(f"Skipping {path.name}: unreadable or non-dict JSON")
        return None

    encoded = extract_polyline(data)
    if not encoded:
        print(f"Skipping {path.name}: no polyline found")
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


def load_all_routes() -> tuple[list[list[tuple[float, float]]], int]:
    total_files = 0
    routes: list[list[tuple[float, float]]] = []

    for path in iter_activity_files():
        total_files += 1
        coords = load_coords_from_file(path)
        if coords:
            routes.append(coords)

    return routes, total_files


def build_map() -> folium.Map:
    return folium.Map(
        location=PORTLAND_CENTER,
        zoom_start=DEFAULT_ZOOM,
        tiles=TILES,
    )


def add_styled_route(
    m: folium.Map,
    coords: list[tuple[float, float]],
    layer: dict[str, Any],
) -> None:
    folium.PolyLine(
        locations=coords,
        weight=layer["weight"],
        opacity=layer["opacity"],
        color=layer["color"],
    ).add_to(m)


def render_style(style: dict[str, Any], routes: list[list[tuple[float, float]]]) -> Path:
    m = build_map()

    for coords in routes:
        for layer in style["layers"]:
            add_styled_route(m, coords, layer)

    HEATMAPS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = HEATMAPS_DIR / style["output"]
    m.save(str(out_path))
    return out_path


def get_enabled_styles() -> list[dict[str, Any]]:
    styles_by_name = {style["name"]: style for style in HEATMAP_STYLES}
    unknown_names = [name for name in ENABLED_HEATMAPS if name not in styles_by_name]

    if unknown_names:
        raise ValueError(f"Unknown enabled heatmap style(s): {', '.join(unknown_names)}")

    return [styles_by_name[name] for name in ENABLED_HEATMAPS]


def main() -> None:
    if not ACTIVITIES_DIR.exists():
        raise FileNotFoundError(f"Activities directory not found: {ACTIVITIES_DIR}")

    routes, total_files = load_all_routes()

    print(f"Scanned files: {total_files}")
    print(f"Routes loaded: {len(routes)}")

    for style in get_enabled_styles():
        out_path = render_style(style, routes)
        print(f"Saved {style['name']}: {out_path}")


if __name__ == "__main__":
    main()
