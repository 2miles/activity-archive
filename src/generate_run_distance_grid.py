#!/usr/bin/env python3
"""
Generate a GitHub-style yearly running distance grid from archived JSON.

Input:
  archive/activities/*.json

Output:
  derived/heatmaps/running_distance_grid.html

The archive remains the source of truth. No Strava API calls are made.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
from pathlib import Path

from activity_archive.activity import activity_start_local, is_run
from activity_archive.archive import iter_activity_dicts
from activity_archive.paths import ACTIVITIES_DIR, RUN_DISTANCE_GRID_PATH
from activity_archive.units import meters_to_miles, safe_float


LEVEL_COLORS = [
    "#ebedf0",
    "#9be9a8",
    "#40c463",
    "#30a14e",
    "#216e39",
]


@dataclass(frozen=True)
class YearSummary:
    year: int
    total_miles: float
    run_days: int
    max_day_miles: float


def load_daily_run_miles(activities_dir: Path) -> dict[date, float]:
    if not activities_dir.exists():
        raise FileNotFoundError(f"Missing activities archive dir: {activities_dir}")

    daily_miles: dict[date, float] = defaultdict(float)

    for activity in iter_activity_dicts(activities_dir):
        if not is_run(activity):
            continue

        dt = activity_start_local(activity)
        if dt is None:
            continue

        miles = meters_to_miles(safe_float(activity.get("distance")))
        if miles <= 0:
            continue

        daily_miles[dt.date()] += miles

    return dict(daily_miles)


def iter_year_days(year: int) -> list[date]:
    current = date(year, 1, 1)
    end = date(year, 12, 31)
    days: list[date] = []

    while current <= end:
        days.append(current)
        current += timedelta(days=1)

    return days


def level_for_miles(miles: float, max_day_miles: float) -> int:
    if miles <= 0 or max_day_miles <= 0:
        return 0

    ratio = miles / max_day_miles
    if ratio <= 0.25:
        return 1
    if ratio <= 0.50:
        return 2
    if ratio <= 0.75:
        return 3
    return 4


def summarize_year(year: int, daily_miles: dict[date, float]) -> YearSummary:
    year_days = iter_year_days(year)
    values = [daily_miles.get(day, 0.0) for day in year_days]

    return YearSummary(
        year=year,
        total_miles=sum(values),
        run_days=sum(1 for miles in values if miles > 0),
        max_day_miles=max(values, default=0.0),
    )


def build_weeks(year: int) -> list[list[date | None]]:
    days = iter_year_days(year)
    weeks: list[list[date | None]] = []
    week: list[date | None] = [None] * 7

    for day in days:
        weekday = (day.weekday() + 1) % 7  # Sunday-first to match GitHub's grid.
        week[weekday] = day

        if weekday == 6:
            weeks.append(week)
            week = [None] * 7

    if any(day is not None for day in week):
        weeks.append(week)

    return weeks


def render_day_cell(day: date | None, daily_miles: dict[date, float], max_day_miles: float) -> str:
    if day is None:
        return '<span class="day empty" aria-hidden="true"></span>'

    miles = daily_miles.get(day, 0.0)
    level = level_for_miles(miles, max_day_miles)
    title = f"{day.isoformat()}: {miles:.2f} miles"

    return (
        f'<span class="day level-{level}" '
        f'title="{escape(title)}" '
        f'aria-label="{escape(title)}"></span>'
    )


def render_year_grid(year: int, daily_miles: dict[date, float]) -> str:
    summary = summarize_year(year, daily_miles)
    weeks = build_weeks(year)

    week_html = []
    for week in weeks:
        cells = "\n".join(
            render_day_cell(day, daily_miles, summary.max_day_miles) for day in week
        )
        week_html.append(f'<div class="week">\n{cells}\n</div>')

    return f"""
<section class="year-card">
  <header class="year-header">
    <div>
      <h2>{summary.year}</h2>
      <p>{summary.total_miles:.1f} miles across {summary.run_days} run days</p>
    </div>
    <div class="max-day">Longest day: {summary.max_day_miles:.1f} mi</div>
  </header>
  <div class="grid-wrap">
    <div class="weekday-labels" aria-hidden="true">
      <span>Sun</span>
      <span>Mon</span>
      <span>Tue</span>
      <span>Wed</span>
      <span>Thu</span>
      <span>Fri</span>
      <span>Sat</span>
    </div>
    <div class="year-grid" role="img" aria-label="Daily running mileage for {summary.year}">
      {"".join(week_html)}
    </div>
  </div>
</section>
"""


def render_html(daily_miles: dict[date, float]) -> str:
    years = sorted({day.year for day in daily_miles}, reverse=True)
    total_miles = sum(daily_miles.values())
    total_run_days = sum(1 for miles in daily_miles.values() if miles > 0)

    if years:
        body = "\n".join(render_year_grid(year, daily_miles) for year in years)
    else:
        body = '<p class="empty-state">No archived running activities found.</p>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Running Distance Grid</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f8f2;
      --card: #ffffff;
      --ink: #172312;
      --muted: #65705f;
      --border: #dfe7d8;
      --shadow: 0 18px 50px rgba(28, 58, 27, 0.10);
      --level-0: {LEVEL_COLORS[0]};
      --level-1: {LEVEL_COLORS[1]};
      --level-2: {LEVEL_COLORS[2]};
      --level-3: {LEVEL_COLORS[3]};
      --level-4: {LEVEL_COLORS[4]};
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      min-width: 320px;
      background:
        radial-gradient(circle at top left, rgba(155, 233, 168, 0.48), transparent 32rem),
        linear-gradient(135deg, #f9fbf6 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: Avenir Next, Avenir, Helvetica, Arial, sans-serif;
    }}

    main {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 42px 0 56px;
    }}

    .hero {{
      margin-bottom: 28px;
    }}

    h1 {{
      margin: 0 0 8px;
      font-size: clamp(2rem, 5vw, 4.2rem);
      letter-spacing: -0.06em;
      line-height: 0.95;
    }}

    .hero p {{
      margin: 0;
      color: var(--muted);
      font-size: 1.05rem;
    }}

    .summary {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 22px 0 0;
    }}

    .pill {{
      border: 1px solid var(--border);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.74);
      padding: 8px 12px;
      font-size: 0.94rem;
    }}

    .year-card {{
      overflow-x: auto;
      margin-top: 20px;
      padding: 22px;
      border: 1px solid var(--border);
      border-radius: 24px;
      background: rgba(255, 255, 255, 0.88);
      box-shadow: var(--shadow);
    }}

    .year-header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
      margin-bottom: 18px;
    }}

    h2 {{
      margin: 0;
      font-size: 1.55rem;
      letter-spacing: -0.04em;
    }}

    .year-header p,
    .max-day {{
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 0.94rem;
    }}

    .grid-wrap {{
      display: grid;
      grid-template-columns: 34px max-content;
      gap: 8px;
      align-items: start;
      min-width: max-content;
    }}

    .weekday-labels {{
      display: grid;
      grid-template-rows: repeat(7, 13px);
      gap: 4px;
      color: var(--muted);
      font-size: 0.68rem;
      line-height: 13px;
      text-align: right;
    }}

    .year-grid {{
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: 13px;
      gap: 4px;
    }}

    .week {{
      display: grid;
      grid-template-rows: repeat(7, 13px);
      gap: 4px;
    }}

    .day {{
      width: 13px;
      height: 13px;
      border-radius: 3px;
      border: 1px solid rgba(23, 35, 18, 0.06);
      background: var(--level-0);
    }}

    .empty {{
      visibility: hidden;
    }}

    .level-0 {{ background: var(--level-0); }}
    .level-1 {{ background: var(--level-1); }}
    .level-2 {{ background: var(--level-2); }}
    .level-3 {{ background: var(--level-3); }}
    .level-4 {{ background: var(--level-4); }}

    .legend {{
      display: flex;
      align-items: center;
      gap: 6px;
      margin-top: 22px;
      color: var(--muted);
      font-size: 0.82rem;
    }}

    .legend-swatch {{
      width: 13px;
      height: 13px;
      border-radius: 3px;
      border: 1px solid rgba(23, 35, 18, 0.06);
    }}

    .empty-state {{
      padding: 24px;
      border: 1px solid var(--border);
      border-radius: 18px;
      background: var(--card);
    }}

    @media (max-width: 720px) {{
      main {{
        width: min(100vw - 20px, 1180px);
        padding-top: 28px;
      }}

      .year-card {{
        padding: 16px;
        border-radius: 18px;
      }}

      .year-header {{
        display: block;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header class="hero">
      <h1>Running Distance Grid</h1>
      <p>Daily running mileage from the local Strava archive. Brighter greens mean more miles that day.</p>
      <div class="summary">
        <span class="pill">{len(years)} years</span>
        <span class="pill">{total_miles:.1f} total miles</span>
        <span class="pill">{total_run_days} run days</span>
      </div>
    </header>
    {body}
    <div class="legend" aria-hidden="true">
      <span>Less</span>
      <span class="legend-swatch level-0"></span>
      <span class="legend-swatch level-1"></span>
      <span class="legend-swatch level-2"></span>
      <span class="legend-swatch level-3"></span>
      <span class="legend-swatch level-4"></span>
      <span>More</span>
    </div>
  </main>
</body>
</html>
"""


def main() -> None:
    daily_miles = load_daily_run_miles(ACTIVITIES_DIR)
    content = render_html(daily_miles)

    RUN_DISTANCE_GRID_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUN_DISTANCE_GRID_PATH.write_text(content, encoding="utf-8")

    print(
        f"Wrote {len(daily_miles)} run days to {RUN_DISTANCE_GRID_PATH}"
    )


if __name__ == "__main__":
    main()
