from __future__ import annotations

import math
from typing import Any

M_PER_MI = 1609.344
FT_PER_M = 3.280839895
MPS_TO_MPH = 2.2369362920544


def safe_float(v: Any, default: float = 0.0) -> float:
    """
    Convert value to float safely.
    - None → default
    - nan → default
    - invalid strings → default
    """
    if v is None:
        return default
    if isinstance(v, (int, float)):
        if isinstance(v, float) and math.isnan(v):
            return default
        return float(v)
    try:
        return float(v)
    except Exception:
        return default


def safe_int(v: Any, default: int = 0) -> int:
    """
    Convert a value to int safely.
    - None / bool / invalid → default
    - int → unchanged
    - float or numeric string → int(float(v))
    """
    if v is None:
        return default
    if isinstance(v, bool):
        return default
    if isinstance(v, int):
        return v
    try:
        return int(float(v))
    except Exception:
        return default


def meters_to_miles(meters: float) -> float:
    return meters / M_PER_MI if meters else 0.0


def meters_to_feet(meters: float) -> float:
    return meters * FT_PER_M if meters else 0.0


def mps_to_mph(mps: float) -> float:
    return mps * MPS_TO_MPH if mps else 0.0


def seconds_to_mmss(seconds: int) -> str:
    if seconds <= 0:
        return ""
    mm = seconds // 60
    ss = seconds % 60
    return f"{mm}:{ss:02d}"


def seconds_to_hhmmss(seconds: int) -> str:
    if seconds <= 0:
        return "00:00:00"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def pace_mmss(distance_mi: float, moving_seconds: int) -> str:
    if distance_mi <= 0 or moving_seconds <= 0:
        return ""
    sec_per_mi = int(round(moving_seconds / distance_mi))
    return seconds_to_mmss(sec_per_mi)
