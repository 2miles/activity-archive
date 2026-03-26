from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# --- Archive (source of truth) ---
ARCHIVE_DIR = PROJECT_ROOT / "archive"
ACTIVITIES_DIR = ARCHIVE_DIR / "activities"
STREAMS_DIR = ARCHIVE_DIR / "streams"
INDEX_DIR = ARCHIVE_DIR / "index"

ACTIVITY_INDEX_PATH = INDEX_DIR / "activity_index.json"

# --- Generated outputs ---
DERIVED_DIR = PROJECT_ROOT / "derived"
REPORTS_DIR = DERIVED_DIR / "reports"
MAPS_DIR = DERIVED_DIR / "maps"
THUMBNAILS_DIR = DERIVED_DIR / "thumbnails"

ACTIVITIES_CSV_PATH = DERIVED_DIR / "activities.csv"
ACTIVITY_LOG_PATH = REPORTS_DIR / "activity_log.txt"
RUNS_LOG_PATH = REPORTS_DIR / "runs_log.txt"
ALL_ROUTES_PATH = DERIVED_DIR / "all_routes_map.html"
