from __future__ import annotations

import sys

from activity_archive.pipeline import PipelineError, run_sync


def main() -> int:
    try:
        run_sync()
    except PipelineError as exc:
        print(f"\nERROR during step -> {exc.result.label}")
        return exc.result.returncode

    return 0


if __name__ == "__main__":
    sys.exit(main())
