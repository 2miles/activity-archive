from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import sys
import threading
from typing import Callable

from activity_archive.pipeline import PipelineError, run_sync


def utc_now() -> datetime:
    return datetime.now().astimezone()


def iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


@dataclass
class SyncStatusSnapshot:
    state: str
    running: bool
    last_started_at: str | None
    last_finished_at: str | None
    last_error: str | None
    last_success_at: str | None


class SyncManager:
    def __init__(self, runner: Callable[[], object] | None = None):
        self._runner = runner or self._default_runner
        self._lock = threading.Lock()
        self._state = "idle"
        self._last_started_at: datetime | None = None
        self._last_finished_at: datetime | None = None
        self._last_success_at: datetime | None = None
        self._last_error: str | None = None

    def _default_runner(self) -> object:
        return run_sync(python_executable=sys.executable)

    def start(self) -> bool:
        with self._lock:
            if self._state == "running":
                return False

            self._state = "running"
            self._last_started_at = utc_now()
            self._last_error = None

            thread = threading.Thread(target=self._run_background, daemon=True)
            thread.start()
            return True

    def _run_background(self) -> None:
        try:
            self._runner()
        except PipelineError as exc:
            with self._lock:
                self._state = "error"
                self._last_finished_at = utc_now()
                self._last_error = (
                    f"{exc.result.label} failed with exit code {exc.result.returncode}"
                )
        except Exception as exc:
            with self._lock:
                self._state = "error"
                self._last_finished_at = utc_now()
                self._last_error = str(exc)
        else:
            with self._lock:
                finished_at = utc_now()
                self._state = "success"
                self._last_finished_at = finished_at
                self._last_success_at = finished_at
                self._last_error = None

    def snapshot(self) -> SyncStatusSnapshot:
        with self._lock:
            return SyncStatusSnapshot(
                state=self._state,
                running=self._state == "running",
                last_started_at=iso_or_none(self._last_started_at),
                last_finished_at=iso_or_none(self._last_finished_at),
                last_error=self._last_error,
                last_success_at=iso_or_none(self._last_success_at),
            )
