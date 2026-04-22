from __future__ import annotations

from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from activity_archive.paths import DERIVED_DIR, PROJECT_ROOT


class Artifact(BaseModel):
    label: str
    path: str
    url: str
    kind: str
    bytes: int


app = FastAPI(title="Activity Archive")


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


app.mount("/derived", StaticFiles(directory=DERIVED_DIR, check_dir=False), name="derived")
