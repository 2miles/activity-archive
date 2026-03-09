"""
Export Strava activity streams to a JSON archive (one file per activity).

Design goals:
- JSON-first archival: one file per activity id
- Default behavior is incremental stream sync:
    download streams only for archived activities missing stream JSON
- --force re-fetches streams even if stream JSON already exists
- Reads activity ids from archive/activities (filesystem is source of truth)
- Requests all known stream types at high resolution
- Atomic writes to avoid partial JSON files
- Avoid burning API calls on "checking" (checks are filesystem-only)

Behavior:
- Default mode:
    scan archived activity JSON files in archive/activities
    skip activities that already have archive/streams/{id}.json
    download streams for missing ones until --limit is reached
- --force:
    re-download streams for archived activities even if stream JSON exists

Usage:
  # download streams for up to 50 missing activities
  python3 src/export_streams_json.py --limit 50 --sleep 0.2

  # continue until all archived activities have streams
  python3 src/export_streams_json.py --sleep 0.2
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Optional

from client import get_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES_DIR = PROJECT_ROOT / "archive" / "activities"
STREAMS_DIR = PROJECT_ROOT / "archive" / "streams"

ALL_STREAM_TYPES = [
    "time",
    "distance",
    "latlng",
    "altitude",
    "velocity_smooth",
    "grade_smooth",
    "heartrate",
    "cadence",
    "watts",
    "temp",
    "moving",
]


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """
    Write JSON to path atomically: write to .tmp then rename.
    Prevents partial files on Ctrl-C / crashes.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    tmp_path.replace(path)


def load_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def get_archived_activity_paths() -> list[Path]:
    """
    Return archived activity JSON paths sorted by filename.
    Assumes filenames are activity ids like 123456.json.
    """
    return sorted(ACTIVITIES_DIR.glob("*.json"), key=lambda p: p.name)


def stream_file_exists(activity_id: int) -> bool:
    return (STREAMS_DIR / f"{activity_id}.json").exists()


def stream_to_data(stream_obj: Any) -> Any:
    """
    Extract just the stream data payload from a stravalib stream object.

    Typical objects have a .data attribute. If not, fall back conservatively.
    """
    data = getattr(stream_obj, "data", None)
    if data is not None:
        return data

    # Fallback: try dict-like object
    if isinstance(stream_obj, dict) and "data" in stream_obj:
        return stream_obj["data"]

    # Last resort: return string representation so we don't crash silently
    return str(stream_obj)


def build_streams_payload(activity_id: int, streams: dict[str, Any]) -> dict[str, Any]:
    """
    Build a clean JSON structure for archived stream data.
    """
    stream_data: dict[str, Any] = {}

    for stream_type, stream_obj in streams.items():
        stream_data[str(stream_type)] = stream_to_data(stream_obj)

    return {
        "activity_id": activity_id,
        "resolution": "high",
        "requested_stream_types": ALL_STREAM_TYPES,
        "stream_types": sorted(stream_data.keys()),
        "streams": stream_data,
    }


def fetch_activity_streams(client: Any, activity_id: int) -> dict[str, Any]:
    """
    Fetch all known stream types for one activity at high resolution.
    Returns a dict keyed by stream type.
    """
    streams = client.get_activity_streams(
        activity_id,
        types=ALL_STREAM_TYPES,
        resolution="high",
    )

    # stravalib usually returns a dict-like object keyed by stream type.
    # Normalize to plain dict for predictable downstream handling.
    return dict(streams)


def run_sync_mode(client: Any, limit: Optional[int], sleep_seconds: float) -> None:
    activity_paths = get_archived_activity_paths()

    print("Mode: sync streams")
    print(f"Archived activities found: {len(activity_paths)}")

    if not activity_paths:
        print("No archived activities found. Nothing to do.")
        print(f"Expected activity archive dir: {ACTIVITIES_DIR}")
        return

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

            out_path = STREAMS_DIR / f"{activity_id}.json"

            if out_path.exists():
                n_skipped += 1
                continue

            if not first_target_printed:
                print(f"First target activity id: {activity_id}")
                first_target_printed = True

            try:
                streams = fetch_activity_streams(client, activity_id)
                payload = build_streams_payload(activity_id, streams)
                atomic_write_json(out_path, payload)
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
    print(f"Output: {STREAMS_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Strava activity streams to JSON files.")

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of stream JSON files to write (default: no limit)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep after each successful write",
    )

    args = parser.parse_args()

    client = get_client()
    STREAMS_DIR.mkdir(parents=True, exist_ok=True)

    run_sync_mode(client, args.limit, args.sleep)


if __name__ == "__main__":
    main()
