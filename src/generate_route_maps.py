"""
Generate static route map PNGs for all archived Strava activities.

Behavior:
- Scans archive/activities/*.json
- Skips maps that already exist
- Generates missing maps
- Writes PNGs to derived/maps/

Usage:
    python src/generate_route_maps.py
    python src/generate_route_maps.py --limit 10
    python src/generate_route_maps.py --sleep 0.2
"""

from __future__ import annotations

import argparse
import time

from generate_route_map import (
    ACTIVITIES_DIR,
    MAPS_DIR,
    build_output_path,
    generate_map,
)


def run(
    width: int,
    height: int,
    line_width: int,
    line_color: str,
    limit: int | None,
    sleep_seconds: float,
) -> None:
    activity_paths = sorted(ACTIVITIES_DIR.glob("*.json"), key=lambda p: p.name)

    print("Mode: generate route map")
    print(f"Archived activities found: {len(activity_paths)}")

    if not activity_paths:
        print("No archived activities found. Nothing to do.")
        print(f"Expected activity archive dir: {ACTIVITIES_DIR}")
        return

    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    n_scanned = 0
    n_written = 0
    n_skipped = 0
    n_errors = 0
    first_target_printed = False

    try:
        for activity_path in activity_paths:
            if limit is not None and n_written >= limit:
                break

            n_scanned += 1

            try:
                activity_id = int(activity_path.stem)
            except ValueError:
                print(f"Skipping non-numeric activity filename: {activity_path.name}")
                n_skipped += 1
                continue

            out_path = build_output_path(activity_id)

            if out_path.exists():
                n_skipped += 1
                continue

            if not first_target_printed:
                print(f"First target activity id: {activity_id}")
                first_target_printed = True

            try:
                generate_map(
                    activity_path=activity_path,
                    out_path=out_path,
                    width=width,
                    height=height,
                    line_width=line_width,
                    line_color=line_color,
                )
                n_written += 1

                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)

                if n_written % 25 == 0:
                    print(f"Scanned {n_scanned} | wrote {n_written} | skipped {n_skipped}")

            except Exception as e:
                n_errors += 1
                print(f"{activity_id}: ERROR: {e}")

    except KeyboardInterrupt:
        print("\nInterrupted (Ctrl-C). Already-written files are safe.")

    print(
        f"Done. Scanned {n_scanned} | wrote {n_written} | skipped {n_skipped} | errors {n_errors}"
    )
    print(f"Output: {MAPS_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate static route maps for all archived activities."
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1200,
        help="Output width in pixels (default: 1200)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1200,
        help="Output height in pixels (default: 1200)",
    )
    parser.add_argument(
        "--line-width",
        type=int,
        default=5,
        help="Route line width in pixels (default: 5)",
    )
    parser.add_argument(
        "--line-color",
        default="#000000",
        help="Route line color (default: #000000)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of missing maps to write (default: no limit)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep after each successful write",
    )

    args = parser.parse_args()

    run(
        width=args.width,
        height=args.height,
        line_width=args.line_width,
        line_color=args.line_color,
        limit=args.limit,
        sleep_seconds=args.sleep,
    )


if __name__ == "__main__":
    main()
