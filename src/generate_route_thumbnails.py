from __future__ import annotations

import argparse
import time
from pathlib import Path

from generate_route_thumbnail import (
    ACTIVITIES_DIR,
    OUT_DIR,
    decode_points,
    draw_thumbnail,
    get_encoded_polyline,
    load_json,
    normalize_points,
)


def run(size: int, padding: float, limit: int | None, sleep_seconds: float) -> None:
    activity_paths = sorted(ACTIVITIES_DIR.glob("*.json"), key=lambda p: p.name)

    print("Mode: generate route thumbnails")
    print(f"Archived activities found: {len(activity_paths)}")

    if not activity_paths:
        print("No archived activities found. Nothing to do.")
        print(f"Expected activity archive dir: {ACTIVITIES_DIR}")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)

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

            out_path = OUT_DIR / f"{activity_id}.png"

            if out_path.exists():
                n_skipped += 1
                continue

            if not first_target_printed:
                print(f"First target activity id: {activity_id}")
                first_target_printed = True

            try:
                activity = load_json(activity_path)
                encoded = get_encoded_polyline(activity)
                latlon_points = decode_points(encoded)
                image_points = normalize_points(latlon_points, size, padding)
                img = draw_thumbnail(image_points, size=size)

                img.save(out_path)
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
    print(f"Output: {OUT_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate route thumbnail PNGs for all archived activities."
    )
    parser.add_argument(
        "--size",
        type=int,
        default=400,
        help="Image size in pixels (default: 400)",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0.12,
        help="Padding ratio around route, between 0 and <0.5 (default: 0.12)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of missing thumbnails to write (default: no limit)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep after each successful write",
    )

    args = parser.parse_args()

    run(
        size=args.size,
        padding=args.padding,
        limit=args.limit,
        sleep_seconds=args.sleep,
    )


if __name__ == "__main__":
    main()
