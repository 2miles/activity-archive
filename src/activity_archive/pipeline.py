from __future__ import annotations

from dataclasses import dataclass
import subprocess
import sys
from typing import Sequence

from activity_archive.paths import PROJECT_ROOT


@dataclass(frozen=True)
class PipelineStep:
    label: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class PipelineResult:
    label: str
    command: tuple[str, ...]
    returncode: int


class PipelineError(RuntimeError):
    def __init__(self, result: PipelineResult):
        self.result = result
        super().__init__(f"Pipeline step failed: {result.label}")


def sync_steps(python_executable: str | None = None) -> list[PipelineStep]:
    python = python_executable or sys.executable

    return [
        PipelineStep(
            "Export new activities",
            (python, "src/export_activities_json.py", "--limit", "98", "--sleep", "0.2"),
        ),
        PipelineStep(
            "Export missing streams",
            (python, "src/export_streams_json.py", "--limit", "98", "--sleep", "0.2"),
        ),
        PipelineStep("Generate derived CSV", (python, "src/generate_csv.py")),
        PipelineStep("Generate run log", (python, "src/generate_run_log.py")),
        PipelineStep("Generate markdown run log", (python, "src/generate_run_log_md.py")),
        PipelineStep("Generate activity log", (python, "src/generate_activity_log.py")),
        PipelineStep(
            "Generate route thumbnails",
            (python, "src/generate_route_thumbnails.py", "--size", "400"),
        ),
        PipelineStep(
            "Generate route maps",
            (python, "src/generate_route_maps.py", "--sleep", "0.2"),
        ),
        PipelineStep("Generate heatmaps", (python, "src/generate_heatmaps.py")),
        PipelineStep(
            "Generate running distance grid",
            (python, "src/generate_run_distance_grid.py"),
        ),
    ]


def run_step(step: PipelineStep) -> PipelineResult:
    print(f"\n>>> {step.label}", flush=True)
    completed = subprocess.run(step.command, cwd=PROJECT_ROOT)
    result = PipelineResult(step.label, step.command, completed.returncode)

    if result.returncode != 0:
        raise PipelineError(result)

    return result


def run_pipeline(steps: Sequence[PipelineStep]) -> list[PipelineResult]:
    results: list[PipelineResult] = []

    for step in steps:
        results.append(run_step(step))

    return results


def run_sync(python_executable: str | None = None) -> list[PipelineResult]:
    results = run_pipeline(sync_steps(python_executable))
    print("\n✓ Update complete")
    return results
