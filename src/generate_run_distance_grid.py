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
    "#1c2720",
    "#08713a",
    "#15964a",
    "#55d45f",
    "#bde64b",
    "#f2dc3f",
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
    if ratio <= 0.20:
        return 1
    if ratio <= 0.40:
        return 2
    if ratio <= 0.60:
        return 3
    if ratio <= 0.80:
        return 4
    return 5


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
    <h2>{summary.year}</h2>
    <dl class="year-summary">
      <div><dt>Distance</dt><dd>{summary.total_miles:.1f} <span>mi</span></dd></div>
      <div><dt>Run days</dt><dd>{summary.run_days}</dd></div>
    </dl>
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

    if years:
        body = "\n".join(render_year_grid(year, daily_miles) for year in years)
    else:
        body = '<p class="empty-state">No archived running activities found.</p>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Running Grid</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0f1511;
      --text: #eef4ef;
      --muted: #9baaa0;
      --label: #b7c2ba;
      --line: #303a33;
      --accent: #8ee05d;
      --level-0: {LEVEL_COLORS[0]};
      --level-1: {LEVEL_COLORS[1]};
      --level-2: {LEVEL_COLORS[2]};
      --level-3: {LEVEL_COLORS[3]};
      --level-4: {LEVEL_COLORS[4]};
      --level-5: {LEVEL_COLORS[5]};
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      min-width: 320px;
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

    .hero {{
      margin-bottom: 36px;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(3.25rem, 7vw, 5.25rem);
      font-weight: 800;
      letter-spacing: -0.055em;
      line-height: 0.94;
    }}

    h1 span {{
      color: var(--accent);
      font-style: italic;
    }}

    .year-card {{
      overflow-x: auto;
      margin-top: 18px;
    }}

    .year-card + .year-card {{
      margin-top: 64px;
    }}

    .year-header {{
      display: flex;
      justify-content: space-between;
      gap: 28px;
      align-items: end;
      margin-bottom: 18px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--accent);
    }}

    h2 {{
      margin: 0;
      font-size: 2.25rem;
      font-weight: 800;
      line-height: 1;
      letter-spacing: -0.035em;
    }}

    .year-summary {{
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: minmax(84px, auto);
      gap: 28px;
      margin: 0;
    }}

    .year-summary dt {{
      margin: 0 0 2px;
      color: var(--label);
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.07em;
      line-height: 1.2;
      text-transform: uppercase;
    }}

    .year-summary dd {{
      margin: 0;
      color: var(--text);
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.015em;
      white-space: nowrap;
    }}

    .year-summary dd span {{
      color: var(--muted);
      font-size: 0.76em;
      font-weight: 600;
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
      border-radius: 2px;
      border: 1px solid rgba(238, 244, 239, 0.04);
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
    .level-5 {{ background: var(--level-5); }}

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
      border-radius: 2px;
      border: 1px solid rgba(238, 244, 239, 0.04);
    }}

    .empty-state {{
      padding: 24px;
      border-top: 1px solid var(--accent);
      color: var(--muted);
    }}

    @media (max-width: 720px) {{
      main {{
        padding: 22px 12px 36px;
      }}

      .year-header {{
        display: block;
      }}

      .year-summary {{
        grid-auto-flow: row;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
        margin-top: 16px;
      }}

      h1 {{
        font-size: 3rem;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header class="hero">
      <h1>Running <span>Grid</span></h1>
      <div class="legend" aria-hidden="true">
        <span>Less</span>
        <span class="legend-swatch level-0"></span>
        <span class="legend-swatch level-1"></span>
        <span class="legend-swatch level-2"></span>
        <span class="legend-swatch level-3"></span>
        <span class="legend-swatch level-4"></span>
        <span class="legend-swatch level-5"></span>
        <span>More</span>
      </div>
    </header>
    {body}
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
