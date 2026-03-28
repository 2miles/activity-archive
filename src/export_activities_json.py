"""
Export Strava activities to a normalized JSON archive (one file per activity).

Design goals:
- JSON-first archival: one file per activity id
- Uses client.get_activity(id) for all writes (DetailedActivity)
- Uses model_dump(mode="json") so nested objects like map become real JSON
- Default behavior is incremental sync:
    download activities AFTER newest archived
- --refresh re-fetches already archived activities in refresh-cycle batches
- --backfill uses activity_index.json as an index and populates missing files
  from oldest to newest
- If activity_index.json is missing during --backfill, build it from the
  Strava activity list first
- Atomic writes to avoid partial JSON files
- Preserves _local metadata across overwrites
- Keeps activity_index.json updated as activities are written

Recommended workflow:
  # backfill archive from activity_index.json, oldest first
  python src/export_activities_json.py --backfill --limit 50 --sleep 0.2

  # normal day-to-day sync for newly created activities
  python src/export_activities_json.py --limit 25 --sleep 0.2

  # gradually re-fetch already archived activities to refresh names/metadata
  python src/export_activities_json.py --refresh --limit 98 --sleep 0.2
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from client import get_client
from activity_archive.paths import ACTIVITIES_DIR, ACTIVITY_INDEX_PATH


def parse_iso(dt_str: str) -> Optional[datetime]:
    """Parse an ISO datetime string. Returns None if invalid."""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def get_archive_bounds(
    dir_path: Path = ACTIVITIES_DIR,
) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    Return (oldest_start_date_utc, newest_start_date_utc) from archived JSON.
    Uses the 'start_date' (UTC) field written in the archive.
    """
    oldest: Optional[datetime] = None
    newest: Optional[datetime] = None

    for path in dir_path.glob("*.json"):
        data = load_json(path)
        if data is None:
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


def activity_to_dict(activity: Any) -> dict[str, Any]:
    """
    Convert a stravalib activity model into clean JSON-serializable data.

    Preferred path:
      - Pydantic model_dump(mode="json")

    Fallbacks are kept only so the script fails less abruptly if the model
    implementation changes.
    """
    if hasattr(activity, "model_dump"):
        try:
            data = activity.model_dump(mode="json")
            if not isinstance(data, dict):
                raise TypeError("model_dump(mode='json') did not return a dict")
            data.pop("bound_client", None)
            return data
        except TypeError:
            data = activity.model_dump()
            if isinstance(data, dict):
                data.pop("bound_client", None)
                return data

    data = dict(getattr(activity, "__dict__", {}))
    data.pop("bound_client", None)
    return data


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically via a temporary file then rename."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp_path.replace(path)


def load_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def load_activity_index_items() -> list[dict[str, Any]]:
    try:
        with ACTIVITY_INDEX_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def load_activity_index_map() -> dict[int, dict[str, Any]]:
    by_id: dict[int, dict[str, Any]] = {}

    for item in load_activity_index_items():
        raw_id = item.get("id")
        if isinstance(raw_id, int):
            by_id[raw_id] = item

    return by_id


def write_activity_index_map(index_map: dict[int, dict[str, Any]]) -> None:
    items = list(index_map.values())
    items.sort(key=lambda x: parse_iso(x.get("start_date")) or datetime.min)

    ACTIVITY_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ACTIVITY_INDEX_PATH.open("w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
        f.write("\n")


def update_activity_index_map(
    index_map: dict[int, dict[str, Any]],
    activity_id: int,
    start_date: str | None,
) -> None:
    index_map[activity_id] = {
        "id": activity_id,
        "start_date": start_date,
    }


def build_activity_index_from_api(client: Any) -> dict[int, dict[str, Any]]:
    print("Building activity index from Strava activity list...")

    index_map: dict[int, dict[str, Any]] = {}
    n_listed = 0

    try:
        for act in client.get_activities():
            n_listed += 1

            activity_id = getattr(act, "id", None)
            start_date = getattr(act, "start_date", None)

            if activity_id is None:
                continue

            if hasattr(start_date, "isoformat"):
                start_date_str = start_date.isoformat()
            elif isinstance(start_date, str):
                start_date_str = start_date
            else:
                start_date_str = None

            index_map[int(activity_id)] = {
                "id": int(activity_id),
                "start_date": start_date_str,
            }

            if n_listed % 100 == 0:
                print(f"Indexed {n_listed} activities")

    except KeyboardInterrupt:
        print("\nInterrupted while building activity index.")

    write_activity_index_map(index_map)
    print(f"Wrote {len(index_map)} activities to {ACTIVITY_INDEX_PATH}")
    return index_map


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
    """Preserve _local metadata across overwrites."""
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

    for path in sorted(ACTIVITIES_DIR.glob("*.json"), key=lambda p: p.name):
        data = load_json(path)
        if data is None:
            continue
        if not is_recently_refreshed(data):
            candidates.append(path)

    return candidates


def count_refresh_remaining() -> int:
    return len(get_refresh_candidates())


def reset_all_refresh_flags() -> int:
    """Set recently_refreshed = false for all archived JSON files."""
    n_reset = 0

    for path in sorted(ACTIVITIES_DIR.glob("*.json"), key=lambda p: p.name):
        data = load_json(path)
        if data is None:
            continue
        set_recently_refreshed(data, False)
        atomic_write_json(path, data)
        n_reset += 1

    return n_reset


def run_backfill_mode(client: Any, limit: Optional[int], sleep_seconds: float) -> None:
    print("Mode: backfill-from-index")

    if not ACTIVITY_INDEX_PATH.exists():
        index_map = build_activity_index_from_api(client)
    else:
        index_map = load_activity_index_map()

    if not index_map:
        print("Activity index is empty.")
        return

    items = list(index_map.values())
    items.sort(key=lambda x: parse_iso(x.get("start_date")) or datetime.min)

    existing_ids = {path.stem for path in ACTIVITIES_DIR.glob("*.json")}

    print(f"Index size: {len(items)}")
    print(f"Already archived: {len(existing_ids)}")

    n_checked = 0
    n_written = 0
    n_skipped_existing = 0
    n_errors = 0
    index_changed = False

    try:
        for item in items:
            if limit is not None and n_written >= limit:
                break

            raw_id = item.get("id")
            if raw_id is None:
                continue

            activity_id = str(raw_id)
            n_checked += 1

            if activity_id in existing_ids:
                n_skipped_existing += 1
                continue

            try:
                detailed = client.get_activity(int(activity_id))
                data = activity_to_dict(detailed)

                out_path = ACTIVITIES_DIR / f"{activity_id}.json"
                atomic_write_json(out_path, data)

                start_date = data.get("start_date")
                update_activity_index_map(
                    index_map,
                    int(activity_id),
                    start_date if isinstance(start_date, str) else None,
                )
                index_changed = True

                existing_ids.add(activity_id)
                n_written += 1

                print(f"Wrote {activity_id}")

                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)

            except Exception as e:
                n_errors += 1
                print(f"{activity_id}: ERROR: {e}")

    except KeyboardInterrupt:
        print("\nInterrupted (Ctrl-C). Already-written files are safe.")

    if index_changed:
        write_activity_index_map(index_map)

    print(
        f"Done. Checked {n_checked} | skipped existing {n_skipped_existing} | wrote {n_written} | errors {n_errors}"
    )


def run_refresh_mode(client: Any, limit: Optional[int], sleep_seconds: float) -> None:
    candidates = get_refresh_candidates()
    remaining_before = len(candidates)
    total_archived = len(list(ACTIVITIES_DIR.glob("*.json")))

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

    index_map = load_activity_index_map()

    n_processed = 0
    n_written = 0
    n_errors = 0
    index_changed = False

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

                start_date = new_data.get("start_date")
                update_activity_index_map(
                    index_map,
                    activity_id,
                    start_date if isinstance(start_date, str) else None,
                )
                index_changed = True

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

    if index_changed:
        write_activity_index_map(index_map)

    remaining_after = count_refresh_remaining()

    print(f"Done refresh. Processed {n_processed} | wrote {n_written} | errors {n_errors}")
    print(f"Remaining in current refresh cycle: {remaining_after}")

    if remaining_after == 0:
        print("Refresh cycle complete. Resetting all recently_refreshed flags to false...")
        n_reset = reset_all_refresh_flags()
        print(f"Reset {n_reset} files for the next cycle.")


def run_sync_mode(client: Any, limit: Optional[int], sleep_seconds: float) -> None:
    """
    Incremental sync for new activities only.

    If the archive is empty, this fetches the most recent activities first.
    Once the archive has data, it only lists activities after the newest
    archived start_date.
    """
    _, newest = get_archive_bounds(ACTIVITIES_DIR)

    list_kwargs: dict[str, Any] = {}

    print("Mode: sync")

    if newest is None:
        print("Archive is empty; fetching newest activities first.")
    else:
        list_kwargs["after"] = newest
        print("Listing activities after newest archived:", newest.isoformat())

    activities_iter = client.get_activities(**list_kwargs)
    index_map = load_activity_index_map()

    n_listed = 0
    n_written = 0
    first = True
    index_changed = False

    try:
        for act in activities_iter:
            if limit is not None and n_written >= limit:
                break

            n_listed += 1
            activity_id = act.id
            out_path = ACTIVITIES_DIR / f"{activity_id}.json"

            if first:
                print("First listed activity id:", activity_id)
                first = False

            old_data = load_json(out_path) if out_path.exists() else None

            detailed = client.get_activity(activity_id)
            data = activity_to_dict(detailed)
            data = merge_local_fields(data, old_data)

            atomic_write_json(out_path, data)

            start_date = data.get("start_date")
            update_activity_index_map(
                index_map,
                activity_id,
                start_date if isinstance(start_date, str) else None,
            )
            index_changed = True

            n_written += 1

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

            if n_written % 25 == 0:
                print(f"Listed {n_listed} | wrote {n_written}")

    except KeyboardInterrupt:
        print("\nInterrupted (Ctrl-C). Already-written files are safe.")

    if index_changed:
        write_activity_index_map(index_map)

    print(f"Done sync. Listed {n_listed} | wrote {n_written}")
    print(f"Output: {ACTIVITIES_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Strava DetailedActivity JSON files into a normalized archive."
    )

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
        help="Refresh already-archived activities not yet refreshed in the current cycle",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Populate missing files using ids from activity_index.json, oldest first",
    )

    args = parser.parse_args()

    if args.refresh and args.backfill:
        raise SystemExit("Choose only one of --refresh or --backfill")

    client = get_client()
    ACTIVITIES_DIR.mkdir(parents=True, exist_ok=True)

    if args.refresh:
        run_refresh_mode(client, args.limit, args.sleep)
    elif args.backfill:
        run_backfill_mode(client, args.limit, args.sleep)
    else:
        run_sync_mode(client, args.limit, args.sleep)


if __name__ == "__main__":
    main()
