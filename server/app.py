from __future__ import annotations

from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from activity_archive.paths import DERIVED_DIR, PROJECT_ROOT
from server.sync_manager import SyncManager

WEB_DIR = PROJECT_ROOT / "web"
WEB_DIST_DIR = WEB_DIR / "dist"
WEB_INDEX_PATH = WEB_DIST_DIR / "index.html"
WEB_ASSETS_DIR = WEB_DIST_DIR / "assets"


class Artifact(BaseModel):
    label: str
    path: str
    url: str
    kind: str
    bytes: int


class SyncStatus(BaseModel):
    state: str
    running: bool
    last_started_at: str | None
    last_finished_at: str | None
    last_error: str | None
    last_success_at: str | None


class SyncStartResponse(BaseModel):
    started: bool
    message: str
    status: SyncStatus


app = FastAPI(title="Activity Archive")
sync_manager = SyncManager()


def artifact_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix == ".csv":
        return "csv"
    if suffix == ".txt":
        return "text"
    if suffix == ".md":
        return "markdown"
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return "image"
    return "file"


def artifact_label(path: Path) -> str:
    name = path.stem.replace("_", " ").replace("-", " ").strip()
    return name.title() if name else path.name


def iter_artifacts(include_images: bool = False) -> list[Artifact]:
    if not DERIVED_DIR.exists():
        return []

    artifacts: list[Artifact] = []

    for path in sorted(DERIVED_DIR.rglob("*")):
        if not path.is_file() or path.name == ".DS_Store":
            continue

        kind = artifact_kind(path)
        if kind == "image" and not include_images:
            continue

        relative = path.relative_to(DERIVED_DIR)
        relative_url = "/".join(relative.parts)
        artifacts.append(
            Artifact(
                label=artifact_label(path),
                path=str(relative),
                url=f"/derived/{relative_url}",
                kind=kind,
                bytes=path.stat().st_size,
            )
        )

    return artifacts


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/artifacts")
def artifacts(include_images: bool = False) -> list[Artifact]:
    return iter_artifacts(include_images=include_images)


@app.get("/api/sync/status")
def sync_status() -> SyncStatus:
    return SyncStatus.model_validate(sync_manager.snapshot().__dict__)


@app.post("/api/sync", status_code=status.HTTP_202_ACCEPTED)
def start_sync() -> SyncStartResponse:
    started = sync_manager.start()
    current_status = SyncStatus.model_validate(sync_manager.snapshot().__dict__)

    if not started:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "started": False,
                "message": "Sync is already running",
                "status": current_status.model_dump(),
            },
        )

    return SyncStartResponse(
        started=True,
        message="Sync started",
        status=current_status,
    )


@app.get("/", include_in_schema=False)
def dashboard_root():
    if WEB_INDEX_PATH.exists():
        return FileResponse(WEB_INDEX_PATH)

    return JSONResponse(
        {
            "message": "Frontend build not found.",
            "next_step": "Run `npm install` and `npm run build` inside `web/`.",
        },
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


app.mount("/assets", StaticFiles(directory=WEB_ASSETS_DIR, check_dir=False), name="assets")
app.mount("/derived", StaticFiles(directory=DERIVED_DIR, check_dir=False), name="derived")
