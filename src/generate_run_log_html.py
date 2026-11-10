#!/usr/bin/env python3
"""
Generate a responsive HTML runs log from archived activity JSON.

Input:
  archive/activities/*.json

Output:
  derived/reports/runs_log.html

Newest -> oldest.
Runs are grouped by month with monthly summaries and mobile-friendly tables.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path

from activity_archive.activity import is_run, parse_iso_datetime
from activity_archive.archive import iter_activity_dicts
from activity_archive.paths import ACTIVITIES_DIR, RUNS_LOG_HTML_PATH
from activity_archive.units import (
    meters_to_miles,
    pace_mmss,
    safe_float,
    safe_int,
    seconds_to_hhmmss,
    seconds_to_mmss,
)


@dataclass(frozen=True)
class RunRow:
    date_str: str
    dist_mi: float
    pace_mmss: str
    moving_seconds: int


def load_runs_by_month(activities_dir: Path) -> dict[tuple[int, int], list[RunRow]]:
    if not activities_dir.exists():
        raise FileNotFoundError(f"Missing activities archive dir: {activities_dir}")

    by_month: dict[tuple[int, int], list[RunRow]] = defaultdict(list)

    for activity in iter_activity_dicts(activities_dir):
        if not is_run(activity):
            continue

        dt_local = parse_iso_datetime(activity.get("start_date_local")) or parse_iso_datetime(
            activity.get("start_date")
        )
        if dt_local is None:
            continue

        meters = safe_float(activity.get("distance"))
        dist_mi = meters_to_miles(meters)
        moving_seconds = safe_int(activity.get("moving_time"))

        d = dt_local.date()
        by_month[(d.year, d.month)].append(
            RunRow(
                date_str=d.strftime("%Y-%m-%d"),
                dist_mi=dist_mi,
                pace_mmss=pace_mmss(dist_mi, moving_seconds),
                moving_seconds=moving_seconds,
            )
        )

    return by_month


def render_month_section(year: int, month: int, runs: list[RunRow]) -> str:
    month_name = date(year, month, 1).strftime("%B %Y")
    month_runs = sorted(runs, key=lambda rr: rr.date_str, reverse=True)

    total_miles = sum(rr.dist_mi for rr in month_runs)
    total_seconds = sum(rr.moving_seconds for rr in month_runs)
    avg_pace = "N/A"
    if total_miles > 0 and total_seconds > 0:
        avg_pace_seconds = int(round(total_seconds / total_miles))
        avg_pace = f"{seconds_to_mmss(avg_pace_seconds)}/mi"

    rows = []
    for rr in month_runs:
        run_date = date.fromisoformat(rr.date_str)
        day = f"{run_date.strftime('%b')} {run_date.day}"
        pace = rr.pace_mmss if rr.pace_mmss else "N/A"
        rows.append(
            f"""
            <tr>
              <td>{escape(day)}</td>
              <td>{rr.dist_mi:.2f}</td>
              <td>{escape(seconds_to_hhmmss(rr.moving_seconds))}</td>
              <td>{escape(pace)}</td>
            </tr>"""
        )

    return f"""
    <section class="month-section">
      <div class="month-heading">
        <h2>{escape(month_name)}</h2>
        <dl class="month-summary">
          <div><dt>Runs</dt><dd>{len(month_runs)}</dd></div>
          <div><dt>Distance</dt><dd>{total_miles:.2f} <span>mi</span></dd></div>
          <div><dt>Time</dt><dd>{escape(seconds_to_hhmmss(total_seconds))}</dd></div>
          <div><dt>Average pace</dt><dd>{escape(avg_pace)}</dd></div>
        </dl>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Day</th>
              <th>Miles</th>
              <th>Time</th>
              <th>Pace</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </div>
    </section>"""


def render_html(runs_by_month: dict[tuple[int, int], list[RunRow]]) -> str:
    month_keys = sorted(runs_by_month.keys(), reverse=True)

    month_sections = [
        render_month_section(year, month, runs_by_month[(year, month)])
        for year, month in month_keys
    ]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Running Log</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0f1511;
      --text: #eef4ef;
      --muted: #9baaa0;
      --label: #b7c2ba;
      --line: #303a33;
      --accent: #8ee05d;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}

    main {{
      width: min(100%, 1180px);
      margin: 0 auto;
      padding: 28px 18px 48px;
    }}

    header {{
      margin-bottom: 36px;
    }}

    h1,
    h2 {{
      margin: 0;
    }}

    h1 {{
      font-size: clamp(3.25rem, 7vw, 5.25rem);
      font-weight: 800;
      line-height: 0.94;
      letter-spacing: -0.055em;
    }}

    h1 span {{
      color: var(--accent);
      font-style: italic;
    }}

    h2 {{
      font-size: 2.25rem;
      font-weight: 800;
      line-height: 1;
      letter-spacing: -0.035em;
    }}

    .month-summary div {{
      min-width: 0;
    }}

    .month-summary dt {{
      margin: 0 0 2px;
      color: var(--label);
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      line-height: 1.2;
    }}

    .month-summary dd {{
      margin: 0;
      color: var(--text);
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.015em;
      white-space: nowrap;
    }}

    .month-section {{
      margin-top: 18px;
    }}

    .month-section + .month-section {{
      margin-top: 64px;
    }}

    .month-heading {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 28px;
      margin-bottom: 16px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--accent);
    }}

    .month-summary {{
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: minmax(84px, auto);
      gap: 28px;
      margin: 0;
    }}

    .month-summary dd span {{
      color: var(--muted);
      font-size: 0.76em;
      font-weight: 600;
    }}

    .table-wrap {{
      overflow-x: auto;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-variant-numeric: tabular-nums;
    }}

    th,
    td {{
      padding: 13px 12px;
      border-bottom: 1px solid var(--line);
      text-align: right;
      white-space: nowrap;
    }}

    th:first-child,
    td:first-child {{
      text-align: left;
    }}

    th {{
      color: var(--label);
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    tr:last-child td {{
      border-bottom-color: transparent;
    }}

    tbody tr:hover {{
      background: rgba(142, 224, 93, 0.045);
    }}

    @media (max-width: 720px) {{
      main {{
        padding: 22px 12px 36px;
      }}

      h1 {{
        font-size: 3rem;
      }}

      .month-heading {{
        display: block;
      }}

      .month-summary {{
        grid-auto-flow: row;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin-top: 16px;
      }}

      th, td {{
        padding: 10px 12px;
      }}
    }}

    @media (max-width: 420px) {{
      .month-summary {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Running <span>Log</span></h1>
    </header>
    {''.join(month_sections)}
  </main>
</body>
</html>
"""


def main() -> None:
    runs_by_month = load_runs_by_month(ACTIVITIES_DIR)
    month_count = len(runs_by_month)
    content = render_html(runs_by_month)

    RUNS_LOG_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNS_LOG_HTML_PATH.write_text(content, encoding="utf-8")

    print(f"Wrote {month_count} month blocks to {RUNS_LOG_HTML_PATH}")


if __name__ == "__main__":
    main()
