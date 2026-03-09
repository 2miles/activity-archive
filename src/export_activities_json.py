"""
Export Strava activities to a JSON archive (one file per activity).

Design goals:
- JSON-first archival: one file per activity id
- Default behavior is incremental sync:
    download activities AFTER newest archived
- --refresh re-fetches already archived activities in refresh-cycle batches
- --limit means:
    - sync mode    : write up to N new JSON files
    - refresh mode : refresh up to N archived JSON files in the current cycle
- Always uses client.get_activity(id) for downloads (DetailedActivity)
- Skips existing files in sync mode
- Atomic writes to avoid partial JSON files
- Avoid burning API calls on "checking" (checks are filesystem-only)

Refresh-cycle behavior:
- Each archived JSON may contain:
    "_local": {
      "recently_refreshed": true|false
    }
- Missing flag counts as false
- --refresh only processes files where recently_refreshed != true
- After all files have been refreshed in the cycle, all flags are reset to false

Usage:
  # incremental sync: write up to 25 new activities since last sync
  python3 src/export_activities_json.py --limit 25 --sleep 0.2

  # first run (no archive yet): just pull the most recent N
  python3 src/export_activities_json.py --limit 50 --sleep 0.6

  # refresh up to 98 already-archived activities in the current refresh cycle
  python3 src/export_activities_json.py --refresh --limit 98 --sleep 0.2
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple

from client import get_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "archive" / "activities"


def parse_iso(dt_str: str) -> Optional[datetime]:
    """Parse ISO datetime string to datetime. Returns None if invalid."""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def get_archive_bounds() -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Return (oldest_start_date_utc, newest_start_date_utc) from archived JSON.
    Uses 'start_date' (UTC) field written in the archive.
    """
    oldest: Optional[datetime] = None
    newest: Optional[datetime] = None

    for path in OUT_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        d = data.get("start_date")
        if not isinstance(d, str):
            continue

        dt = parse_iso(d)
        if dt is None:
            continue

        if oldest is None or dt < oldest:
            oldest = dt
        if newest is None or dt > newest:
            newest = dt

    return oldest, newest


def jsonable(v: Any) -> Any:
    """Make values JSON-serializable with minimal distortion."""
    try:
        if hasattr(v, "isoformat"):
            return v.isoformat()
    except Exception:
        pass

    try:
        if hasattr(v, "magnitude") and hasattr(v, "units"):
            return str(v)
    except Exception:
        pass

    if isinstance(v, dict):
        return {str(k): jsonable(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [jsonable(val) for val in v]

    try:
        json.dumps(v)
        return v
    except TypeError:
        return str(v)


def activity_to_dict(a: Any) -> dict[str, Any]:
    """
    Convert stravalib DetailedActivity to a JSON-friendly dict.
    Uses __dict__ (what stravalib populated) and removes client reference.
    """
    data = dict(getattr(a, "__dict__", {}))
    data.pop("bound_client", None)
    return {k: jsonable(v) for k, v in data.items()}


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


def ensure_local_block(data: dict[str, Any]) -> dict[str, Any]:
    local_block = data.get("_local")
    if not isinstance(local_block, dict):
        local_block = {}
        data["_local"] = local_block
    return local_block


def is_recently_refreshed(data: dict[str, Any]) -> bool:
    local_block = data.get("_local")
    if not isinstance(local_block, dict):
        return False
    return local_block.get("recently_refreshed") is True


def set_recently_refreshed(data: dict[str, Any], value: bool) -> None:
    local_block = ensure_local_block(data)
    local_block["recently_refreshed"] = value


def merge_local_fields(
    new_data: dict[str, Any], old_data: Optional[dict[str, Any]]
) -> dict[str, Any]:
    """
    Preserve _local metadata across overwrites.
    """
    if isinstance(old_data, dict):
        old_local = old_data.get("_local")
        if isinstance(old_local, dict):
            new_data["_local"] = dict(old_local)
    return new_data


def get_refresh_candidates() -> list[Path]:
    """
    Return archived files that still need refresh in the current cycle.
    Missing recently_refreshed counts as false.
    """
    candidates: list[Path] = []

    for path in sorted(OUT_DIR.glob("*.json"), key=lambda p: p.name):
        data = load_json(path)
        if data is None:
            continue

        if not is_recently_refreshed(data):
            candidates.append(path)

    return candidates


def count_refresh_remaining() -> int:
    return len(get_refresh_candidates())


def reset_all_refresh_flags() -> int:
    """
    Set recently_refreshed = false for all archived JSON files.
    Returns number of files updated.
    """
    n_reset = 0

    for path in sorted(OUT_DIR.glob("*.json"), key=lambda p: p.name):
        data = load_json(path)
        if data is None:
            continue

        set_recently_refreshed(data, False)
        atomic_write_json(path, data)
        n_reset += 1

    return n_reset


def run_refresh_mode(client: Any, limit: Optional[int], sleep_seconds: float) -> None:
    candidates = get_refresh_candidates()
    remaining_before = len(candidates)
    total_archived = len(list(OUT_DIR.glob("*.json")))

    print("Mode: refresh")
    print(f"Archive size: {total_archived}")
    print(f"Remaining in current refresh cycle: {remaining_before}")

    if total_archived == 0:
        print("Archive is empty. Nothing to refresh.")
        return

    if remaining_before == 0:
        print("All activities are already marked recently_refreshed=true.")
        print("Resetting all refresh flags to false for a new cycle...")
        n_reset = reset_all_refresh_flags()
        print(f"Reset {n_reset} files.")
        candidates = get_refresh_candidates()
        remaining_before = len(candidates)
        print(f"Remaining in new cycle: {remaining_before}")

    if limit is not None:
        candidates = candidates[:limit]

    print(f"Refreshing {len(candidates)} activities...")

    n_processed = 0
    n_written = 0
    n_errors = 0

    try:
        for path in candidates:
            activity_id = int(path.stem)
            old_data = load_json(path)

            try:
                detailed = client.get_activity(activity_id)
                new_data = activity_to_dict(detailed)
                new_data = merge_local_fields(new_data, old_data)
                set_recently_refreshed(new_data, True)
                atomic_write_json(path, new_data)

                n_processed += 1
                n_written += 1

                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)

                if n_written % 25 == 0:
                    print(f"Refreshed {n_written}")

            except Exception as e:
                n_processed += 1
                n_errors += 1
                print(f"{activity_id}: ERROR: {e}")

    except KeyboardInterrupt:
        print("\nInterrupted (Ctrl-C). Already-written files are safe.")

    remaining_after = count_refresh_remaining()

    print(f"Done refresh. Processed {n_processed} | wrote {n_written} | errors {n_errors}")
    print(f"Remaining in current refresh cycle: {remaining_after}")

    if remaining_after == 0:
        print("Refresh cycle complete. Resetting all recently_refreshed flags to false...")
        n_reset = reset_all_refresh_flags()
        print(f"Reset {n_reset} files for the next cycle.")


def run_sync_mode(client: Any, limit: Optional[int], sleep_seconds: float) -> None:
    _, newest = get_archive_bounds()

    list_kwargs: dict[str, Any] = {}

    if newest is None:
        print("Mode: sync")
        print("Archive is empty; fetching newest activities first.")
    else:
        list_kwargs["after"] = newest
        print("Mode: sync")
        print("Listing activities after newest archived:", newest.isoformat())

    activities_iter = client.get_activities(**list_kwargs)

    n_listed = 0
    n_written = 0
    first = True

    try:
        for act in activities_iter:
            if limit is not None and n_written >= limit:
                break

            n_listed += 1
            activity_id = act.id
            out_path = OUT_DIR / f"{activity_id}.json"

            if first:
                print("First listed activity id:", activity_id)
                first = False

            old_data = load_json(out_path) if out_path.exists() else None

            detailed = client.get_activity(activity_id)
            data = activity_to_dict(detailed)
            data = merge_local_fields(data, old_data)

            atomic_write_json(out_path, data)
            n_written += 1

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

            if n_written % 25 == 0:
                print(f"Listed {n_listed} | wrote {n_written}")

    except KeyboardInterrupt:
        print("\nInterrupted (Ctrl-C). Already-written files are safe.")

    print(f"Done. Listed {n_listed} | wrote {n_written}")
    print(f"Output: {OUT_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Strava DetailedActivity JSON files.")

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of activity JSON files to write in the selected mode (default: no limit)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep after each successful write",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh already-archived activities that are not yet refreshed in the current cycle",
    )

    args = parser.parse_args()

    client = get_client()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.refresh:
        run_refresh_mode(client, args.limit, args.sleep)
    else:
        run_sync_mode(client, args.limit, args.sleep)


if __name__ == "__main__":
    main()
