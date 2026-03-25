from pathlib import Path
import json
from datetime import datetime

OLD_DIR = Path("archive/activities")
OUT_PATH = Path("archive/index/activity_index.json")


def parse_iso(dt_str):
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def main():
    items = []

    for path in OLD_DIR.glob("*.json"):
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
    items.sort(key=lambda x: x["start_date"] or "")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_PATH, "w") as f:
        json.dump(items, f, indent=2)

    print(f"Wrote {len(items)} activities to {OUT_PATH}")


if __name__ == "__main__":
    main()
