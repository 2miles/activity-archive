"""
Generate a static route map thumbnail PNG from one archived Strava activity JSON file.

Behavior:
- Reads archive/activities/{activity_id}.json
- Extracts summary_polyline (or polyline fallback)
- Decodes the polyline
- Renders a static map with route overlay
- Adds simple start / end markers
- Saves a PNG to derived/maps/{activity_id}.png

Install:
    pip install staticmap polyline pillow

Usage:
    python src/generate_route_map.py 5799697041
    python src/generate_route_map.py 5799697041 --width 600 --height 400
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import polyline
from staticmap import CircleMarker, Line, StaticMap


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES_DIR = PROJECT_ROOT / "archive" / "activities"
OUT_DIR = PROJECT_ROOT / "derived" / "maps"

START_MARKER_COLOR = "#00FF00"
END_MARKER_COLOR = "#FF0000"
START_END_MARKER_SIZE = 12


def load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def get_encoded_polyline(activity: dict[str, Any]) -> str:
    map_obj = activity.get("map")
    if not isinstance(map_obj, dict):
        raise ValueError("Activity JSON is missing a valid 'map' object")

    encoded = map_obj.get("polyline") or map_obj.get("summary_polyline")
    if not isinstance(encoded, str) or not encoded.strip():
        raise ValueError("Activity JSON is missing a usable polyline in 'map'")

    return encoded


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """
    Returns [(lat, lon), ...]
    """
    points = polyline.decode(encoded)
    if len(points) < 2:
        raise ValueError("Decoded polyline has fewer than 2 points")
    return points


def latlon_to_lonlat(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """
    staticmap expects (lon, lat), not (lat, lon).
    """
    return [(lon, lat) for lat, lon in points]


def build_output_path(activity_id: int) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUT_DIR / f"{activity_id}.png"


def generate_map(
    activity_path: Path,
    out_path: Path,
    width: int,
    height: int,
    line_width: int,
    line_color: str,
) -> None:
    """
    Generate and save one static mapPNG for a single activity JSON file.
    """
    activity = load_json(activity_path)
    encoded = get_encoded_polyline(activity)
    latlon_points = decode_polyline(encoded)
    lonlat_points = latlon_to_lonlat(latlon_points)

    m = StaticMap(width, height)
    m.add_line(Line(lonlat_points, line_color, line_width))

    start_lonlat = lonlat_points[0]
    end_lonlat = lonlat_points[-1]

    m.add_marker(CircleMarker(start_lonlat, START_MARKER_COLOR, START_END_MARKER_SIZE))
    m.add_marker(CircleMarker(end_lonlat, END_MARKER_COLOR, START_END_MARKER_SIZE))

    image = m.render()
    image.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a static route map from one archived activity."
    )
    parser.add_argument("activity_id", type=int, help="Strava activity id")
    parser.add_argument("--width", type=int, default=1200, help="Output width in pixels")
    parser.add_argument("--height", type=int, default=1200, help="Output height in pixels")
    parser.add_argument(
        "--line-width",
        type=int,
        default=5,
        help="Route line width in pixels",
    )
    parser.add_argument(
        "--line-color",
        default="#000000",
        help="Route line color (default: #000000)",
    )

    args = parser.parse_args()

    activity_path = ACTIVITIES_DIR / f"{args.activity_id}.json"
    if not activity_path.exists():
        raise FileNotFoundError(f"Activity file not found: {activity_path}")

    out_path = build_output_path(args.activity_id)

    generate_map(
        activity_path=activity_path,
        out_path=out_path,
        width=args.width,
        height=args.height,
        line_width=args.line_width,
        line_color=args.line_color,
    )

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
