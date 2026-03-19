"""
Generate a route thumbnail PNG from one archived Strava activity JSON file.

Behavior:
- Reads an activity JSON file from archive/activities/{id}.json
- Uses map.summary_polyline first, then map.polyline as fallback
- Decodes the polyline
- Normalizes route coordinates to fit inside a square image
- Draws the route line on a solid background
- Saves a PNG thumbnail

Install:
    pip install polyline pillow

Usage:
    python src/generate_route_thumbnail.py 123456789
    python src/generate_route_thumbnail.py 123456789 --size 400 --padding 0.12
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

import polyline
from PIL import Image, ImageDraw

import ast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES_DIR = PROJECT_ROOT / "archive" / "activities"
OUT_DIR = PROJECT_ROOT / "derived" / "thumbnails"


def load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def extract_repr_field(text: str, field_name: str) -> str | None:
    match = re.search(rf"{field_name}=('(?:[^'\\\\]|\\\\.)*')", text)
    if not match:
        return None
    return ast.literal_eval(match.group(1))


def get_encoded_polyline(activity: dict[str, Any]) -> str:
    map_obj = activity.get("map")

    if isinstance(map_obj, dict):
        encoded = map_obj.get("summary_polyline") or map_obj.get("polyline")
        if isinstance(encoded, str) and encoded.strip():
            return encoded

    if isinstance(map_obj, str):
        encoded = extract_repr_field(map_obj, "summary_polyline")
        if encoded:
            return encoded

        encoded = extract_repr_field(map_obj, "polyline")
        if encoded:
            return encoded

    raise ValueError("Activity JSON is missing a usable polyline in 'map'")


def decode_points(encoded: str) -> list[tuple[float, float]]:
    """
    Returns points as (lat, lon).
    """
    points = polyline.decode(encoded)
    if len(points) < 2:
        raise ValueError("Decoded polyline has fewer than 2 points")
    return points


def normalize_points(
    latlon_points: list[tuple[float, float]],
    size: int,
    padding_ratio: float,
) -> list[tuple[float, float]]:
    """
    Convert (lat, lon) points into image-space (x, y) points.

    Notes:
    - x uses longitude
    - y uses latitude, flipped so north is up
    - preserves aspect ratio
    - centers the route in the square canvas
    """
    if not (0 <= padding_ratio < 0.5):
        raise ValueError("padding_ratio must be >= 0 and < 0.5")

    lats = [lat for lat, _ in latlon_points]
    lons = [lon for _, lon in latlon_points]

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    width_geo = max_lon - min_lon
    height_geo = max_lat - min_lat

    # Handle extremely thin or degenerate routes
    if width_geo == 0:
        width_geo = 1e-12
    if height_geo == 0:
        height_geo = 1e-12

    padding_px = size * padding_ratio
    drawable = size - 2 * padding_px

    scale = min(drawable / width_geo, drawable / height_geo)

    drawn_width = width_geo * scale
    drawn_height = height_geo * scale

    x_offset = (size - drawn_width) / 2
    y_offset = (size - drawn_height) / 2

    image_points: list[tuple[float, float]] = []

    for lat, lon in latlon_points:
        x = x_offset + (lon - min_lon) * scale
        y = y_offset + (max_lat - lat) * scale
        image_points.append((x, y))

    return image_points


def stroke_width_for_size(size: int) -> int:
    """
    Simple heuristic for a clean thumbnail stroke.
    """
    # return max(2, round(size * 0.012))
    return max(3, round(size * 0.015))


def draw_thumbnail(
    points: list[tuple[float, float]],
    size: int,
) -> Image.Image:

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    width = stroke_width_for_size(size)

    route_color = (255, 0, 110, 255)
    draw.line(points, fill=route_color, width=width, joint="curve")

    # marker size relative to image
    marker_radius = max(3, width * 1.5)

    start_x, start_y = points[0]
    end_x, end_y = points[-1]

    dist = ((start_x - end_x) ** 2 + (start_y - end_y) ** 2) ** 0.5

    if dist < marker_radius * 2:
        start_x -= marker_radius
        end_x += marker_radius

    # start marker (white)
    draw.ellipse(
        (
            start_x - marker_radius,
            start_y - marker_radius,
            start_x + marker_radius,
            start_y + marker_radius,
        ),
        outline=(255, 255, 255, 255),
        fill=(0, 150, 0, 255),
    )

    # end marker (black)
    draw.ellipse(
        (
            end_x - marker_radius,
            end_y - marker_radius,
            end_x + marker_radius,
            end_y + marker_radius,
        ),
        outline=(255, 255, 255, 255),
        fill=(150, 0, 0, 255),
    )

    return img


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a route thumbnail PNG from one activity."
    )
    parser.add_argument("activity_id", type=int, help="Strava activity id")
    parser.add_argument("--size", type=int, default=400, help="Image size in pixels (default: 400)")
    parser.add_argument(
        "--padding",
        type=float,
        default=0.12,
        help="Padding ratio around route, between 0 and <0.5 (default: 0.12)",
    )
    args = parser.parse_args()

    activity_path = ACTIVITIES_DIR / f"{args.activity_id}.json"
    if not activity_path.exists():
        raise FileNotFoundError(f"Activity file not found: {activity_path}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    activity = load_json(activity_path)
    encoded = get_encoded_polyline(activity)
    latlon_points = decode_points(encoded)
    image_points = normalize_points(latlon_points, args.size, args.padding)
    img = draw_thumbnail(
        image_points,
        size=args.size,
    )

    out_path = OUT_DIR / f"{args.activity_id}.png"
    img.save(out_path)

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
