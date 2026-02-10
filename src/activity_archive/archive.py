from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def iter_activity_dicts(archive_dir: Path) -> Iterator[dict[str, Any]]:
    """
    Yield activity JSON dicts from archive_dir/*.json.
    Skips unreadable files and non-dict JSON.
    """
    if not archive_dir.exists():
        return

    for p in sorted(archive_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            yield data


def count_json_files(archive_dir: Path) -> int:
    if not archive_dir.exists():
        return 0
    return sum(1 for _ in archive_dir.glob("*.json"))
