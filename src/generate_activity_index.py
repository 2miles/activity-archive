import json
from datetime import datetime

from activity_archive.paths import ACTIVITIES_DIR, ACTIVITY_INDEX_PATH


def parse_iso(dt_str):
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def main():
    items = []

    for path in ACTIVITIES_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue

        activity_id = int(path.stem)
        start_date = data.get("start_date")

        if isinstance(start_date, str):
            items.append({"id": activity_id, "start_date": start_date})
        else:
            items.append({"id": activity_id, "start_date": None})

    # sort oldest → newest
    items.sort(key=lambda x: parse_iso(x["start_date"]) or datetime.min)

    ACTIVITY_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(ACTIVITY_INDEX_PATH, "w") as f:
        json.dump(items, f, indent=2)

    print(f"Wrote {len(items)} activities to {ACTIVITY_INDEX_PATH}")


if __name__ == "__main__":
    main()
