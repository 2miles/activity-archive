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


def render_summary_card(label: str, value: str) -> str:
    return f"""
      <div class="summary-card">
        <span>{escape(label)}</span>
        <strong>{escape(value)}</strong>
      </div>"""


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
              <td>{escape(pace)}</td>
              <td>{escape(seconds_to_hhmmss(rr.moving_seconds))}</td>
            </tr>"""
        )

    return f"""
    <section class="month-section">
      <div class="month-heading">
        <h2>{escape(month_name)}</h2>
        <div class="month-summary">
          <span>{len(month_runs)} runs</span>
          <span>{total_miles:.2f} miles</span>
          <span>{escape(avg_pace)}</span>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Day</th>
              <th>Miles</th>
              <th>Pace</th>
              <th>Time</th>
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
    total_runs = sum(len(runs) for runs in runs_by_month.values())
    total_miles = sum(rr.dist_mi for runs in runs_by_month.values() for rr in runs)
    total_seconds = sum(rr.moving_seconds for runs in runs_by_month.values() for rr in runs)

    avg_pace = "N/A"
    if total_miles > 0 and total_seconds > 0:
        avg_pace_seconds = int(round(total_seconds / total_miles))
        avg_pace = f"{seconds_to_mmss(avg_pace_seconds)}/mi"

    month_sections = [
        render_month_section(year, month, runs_by_month[(year, month)])
        for year, month in month_keys
    ]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Run Log</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f4ef;
      --panel: #ffffff;
      --text: #1d2520;
      --muted: #647067;
      --line: #ddd6cc;
      --accent: #0f766e;
      --accent-soft: #d9f0ec;
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
      width: min(100%, 980px);
      margin: 0 auto;
      padding: 28px 18px 48px;
    }}

    header {{
      margin-bottom: 24px;
    }}

    h1, h2 {{
      margin: 0;
      line-height: 1.1;
      letter-spacing: 0;
    }}

    h1 {{
      font-size: 3.5rem;
    }}

    h2 {{
      font-size: 1.35rem;
    }}

    .lede {{
      max-width: 680px;
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 1rem;
    }}

    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 10px;
      margin-top: 22px;
    }}

    .summary-card {{
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 14px;
    }}

    .summary-card span {{
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .summary-card strong {{
      display: block;
      margin-top: 6px;
      font-size: 1.35rem;
      line-height: 1.1;
    }}

    .month-section {{
      margin-top: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      overflow: hidden;
    }}

    .month-heading {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      padding: 16px;
      border-bottom: 1px solid var(--line);
    }}

    .month-summary {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
      color: var(--muted);
      font-size: 0.9rem;
    }}

    .month-summary span {{
      border-radius: 999px;
      background: var(--accent-soft);
      color: #164e47;
      padding: 4px 9px;
    }}

    .table-wrap {{
      overflow-x: auto;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-variant-numeric: tabular-nums;
    }}

    th, td {{
      padding: 11px 16px;
      border-bottom: 1px solid var(--line);
      text-align: right;
      white-space: nowrap;
    }}

    th:first-child,
    td:first-child {{
      text-align: left;
    }}

    th {{
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    tr:last-child td {{
      border-bottom: 0;
    }}

    @media (max-width: 720px) {{
      main {{
        padding: 22px 12px 36px;
      }}

      h1 {{
        font-size: 2.2rem;
      }}

      .month-heading {{
        align-items: flex-start;
        flex-direction: column;
      }}

      .month-summary {{
        justify-content: flex-start;
      }}

      th, td {{
        padding: 10px 12px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Run Log</h1>
      <p class="lede">A responsive monthly view of archived runs, generated from local Activity Archive JSON.</p>
      <div class="summary-grid">
        {render_summary_card("Months", str(len(month_keys)))}
        {render_summary_card("Runs", str(total_runs))}
        {render_summary_card("Miles", f"{total_miles:.2f}")}
        {render_summary_card("Time", seconds_to_hhmmss(total_seconds))}
        {render_summary_card("Avg Pace", avg_pace)}
      </div>
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
