from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

ROOT_RE = re.compile(r"root='([^']+)'")

RUN_TYPES = {"Run", "TrailRun", "VirtualRun"}


def is_run(activity: dict) -> bool:
    return activity_type(activity) in RUN_TYPES


def normalize_root_string(v: Any) -> str:
    """
    Normalize activity type strings.

    Examples:
      "root='Walk'" -> "Walk"
      "Run"         -> "Run"
      None          -> ""
    """
    if v is None:
        return ""
    s = str(v)
    m = ROOT_RE.search(s)
    return m.group(1) if m else s.strip()


def activity_type(activity: dict) -> str:
    """
    Prefer 'type', fall back to 'sport_type'.
    Returns normalized string (e.g., 'Run', 'Walk').
    """
    t = normalize_root_string(activity.get("type"))
    if t:
        return t
    return normalize_root_string(activity.get("sport_type"))


def parse_isoish_datetime(dt_str: Any) -> Optional[datetime]:
    """
    Parse ISO-ish datetime strings.
    Supports:
      - 2026-01-18T13:50:17
      - 2026-01-18 13:50:17
      - 2026-01-18T21:50:17+00:00
      - ...Z
    """
    if not isinstance(dt_str, str) or not dt_str.strip():
        return None
    s = dt_str.strip().replace("Z", "+00:00")
    if "T" not in s and " " in s:
        s = s.replace(" ", "T", 1)
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def activity_start_local(activity: dict) -> Optional[datetime]:
    """Prefer start_date_local, fall back to start_date."""
    return parse_isoish_datetime(activity.get("start_date_local")) or parse_isoish_datetime(
        activity.get("start_date")
    )
