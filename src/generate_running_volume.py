#!/usr/bin/env python3
"""
Generate a standalone running volume chart from archived activity JSON.

Input:
  archive/activities/*.json

Output:
  derived/reports/running_volume.html

Daily bars show total run distance by local date.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
from math import ceil
from pathlib import Path

from activity_archive.activity import activity_start_local, is_run
from activity_archive.archive import iter_activity_dicts
from activity_archive.paths import ACTIVITIES_DIR, RUNNING_VOLUME_HTML_PATH
from activity_archive.units import meters_to_miles, safe_float


@dataclass(frozen=True)
class VolumeDay:
    day: date
    miles: float
    is_padding: bool = False


@dataclass(frozen=True)
class YearRunStats:
    run_count: int
    total_miles: float
    longest_miles: float

    @property
    def average_miles(self) -> float:
        return self.total_miles / self.run_count if self.run_count else 0.0


def load_daily_run_miles(activities_dir: Path) -> dict[date, float]:
    if not activities_dir.exists():
        raise FileNotFoundError(f"Missing activities archive dir: {activities_dir}")

    daily_miles: dict[date, float] = defaultdict(float)

    for activity in iter_activity_dicts(activities_dir):
        if not is_run(activity):
            continue

        dt_local = activity_start_local(activity)
        if dt_local is None:
            continue

        miles = meters_to_miles(safe_float(activity.get("distance")))
        if miles <= 0:
            continue

        daily_miles[dt_local.date()] += miles

    return dict(daily_miles)


def load_yearly_run_stats(activities_dir: Path) -> dict[int, YearRunStats]:
    if not activities_dir.exists():
        raise FileNotFoundError(f"Missing activities archive dir: {activities_dir}")

    yearly_runs: dict[int, list[float]] = defaultdict(list)

    for activity in iter_activity_dicts(activities_dir):
        if not is_run(activity):
            continue

        dt_local = activity_start_local(activity)
        if dt_local is None:
            continue

        miles = meters_to_miles(safe_float(activity.get("distance")))
        if miles <= 0:
            continue

        yearly_runs[dt_local.year].append(miles)

    return {
        year: YearRunStats(
            run_count=len(run_miles),
            total_miles=sum(run_miles),
            longest_miles=max(run_miles),
        )
        for year, run_miles in yearly_runs.items()
    }


def build_volume_days(daily_miles: dict[date, float]) -> list[VolumeDay]:
    if not daily_miles:
        return []

    current = min(daily_miles)
    end = max(daily_miles)
    days: list[VolumeDay] = []

    while current <= end:
        miles = daily_miles.get(current, 0.0)
        days.append(
            VolumeDay(
                day=current,
                miles=miles,
            )
        )
        current += timedelta(days=1)

    return days


def chart_x(index: int, day_width: int, left_pad: int) -> float:
    return left_pad + index * day_width + day_width / 2


def chart_y(value: float, max_value: float, top_pad: int, plot_height: int) -> float:
    if max_value <= 0:
        return top_pad + plot_height
    return top_pad + plot_height - (value / max_value) * plot_height


def linear_axis(max_value: float) -> tuple[float, list[float]]:
    """Return an integer-mile chart maximum and one-mile tick marks."""
    if max_value <= 0:
        return 1.0, [0.0, 1.0]

    axis_max = float(ceil(max_value))
    ticks = [float(miles) for miles in range(int(axis_max) + 1)]
    return axis_max, ticks


def build_calendar_years(days: list[VolumeDay]) -> list[list[VolumeDay]]:
    if not days:
        return []

    by_day = {volume_day.day: volume_day for volume_day in days}
    first_day = days[0].day
    last_day = days[-1].day
    year_panels: list[list[VolumeDay]] = []

    for year in range(last_day.year, first_day.year - 1, -1):
        current = date(year, 1, 1)
        end = date(year, 12, 31)
        year_days: list[VolumeDay] = []

        while current <= end:
            volume_day = by_day.get(current)
            if volume_day is not None:
                year_days.append(volume_day)
            else:
                year_days.append(
                    VolumeDay(
                        day=current,
                        miles=0.0,
                        is_padding=current < first_day or current > last_day,
                    )
                )
            current += timedelta(days=1)

        year_panels.append(year_days)

    return year_panels


def render_svg(
    days: list[VolumeDay],
    chart_index: int,
    axis_max: float,
    y_tick_values: list[float],
) -> str:
    if not days:
        return """
        <div class="empty-state">
          No archived runs with distance were found.
        </div>"""

    day_width = 3
    left_pad = 58
    right_pad = 28
    top_pad = 28
    bottom_pad = 54
    plot_height = 360
    width = left_pad + right_pad + len(days) * day_width
    height = top_pad + plot_height + bottom_pad
    chart_bottom = top_pad + plot_height
    grid_lines = []
    for daily_value in y_tick_values:
        y = chart_y(daily_value, axis_max, top_pad, plot_height)
        grid_lines.append(
            f"""
            <g>
              <line class="grid-line" x1="{left_pad}" y1="{y:.2f}" x2="{width - right_pad}" y2="{y:.2f}" />
              <text class="axis-label" x="{left_pad - 10}" y="{y + 4:.2f}" text-anchor="end">{daily_value:.0f}</text>
            </g>"""
        )

    month_ticks = []
    seen_months: set[tuple[int, int]] = set()
    for index, volume_day in enumerate(days):
        month_key = (volume_day.day.year, volume_day.day.month)
        if month_key in seen_months:
            continue
        seen_months.add(month_key)
        x = chart_x(index, day_width, left_pad)
        month_ticks.append(
            f"""
            <g>
              <line class="month-line" x1="{x:.2f}" y1="{top_pad}" x2="{x:.2f}" y2="{chart_bottom}" />
              <text class="month-label" x="{x:.2f}" y="{height - 18}" text-anchor="middle">{escape(volume_day.day.strftime("%b"))}</text>
            </g>"""
        )

    bars = []
    for index, volume_day in enumerate(days):
        if volume_day.miles <= 0:
            continue

        x = left_pad + index * day_width - 0.5
        y = chart_y(volume_day.miles, axis_max, top_pad, plot_height)
        bar_height = max(1.0, chart_bottom - y)
        label = f"{volume_day.day.isoformat()}: {volume_day.miles:.2f} mi"
        bars.append(
            f"""
            <rect class="daily-bar" x="{x:.2f}" y="{y:.2f}" width="3" height="{bar_height:.2f}" fill="url(#bar-gradient-{chart_index})">
              <title>{escape(label)}</title>
            </rect>"""
        )

    return f"""
      <div class="chart-scroll">
        <svg class="volume-chart" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="chart-title-{chart_index} chart-desc-{chart_index}">
          <title id="chart-title-{chart_index}">Daily running distance</title>
          <desc id="chart-desc-{chart_index}">Each bar is one day of running distance.</desc>
          <defs>
            <linearGradient id="bar-gradient-{chart_index}" x1="0" y1="{chart_bottom}" x2="0" y2="{top_pad}" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stop-color="#08713a" />
              <stop offset="28%" stop-color="#15964a" />
              <stop offset="50%" stop-color="#55d45f" />
              <stop offset="78%" stop-color="#bde64b" />
              <stop offset="100%" stop-color="#f2dc3f" />
            </linearGradient>
          </defs>
          <rect class="chart-bg" x="0" y="0" width="{width}" height="{height}" rx="10" />
          {''.join(grid_lines)}
          {''.join(month_ticks)}
          <line class="axis-line" x1="{left_pad}" y1="{chart_bottom}" x2="{width - right_pad}" y2="{chart_bottom}" />
          <text class="axis-unit" x="{left_pad - 10}" y="{top_pad - 10}" text-anchor="end">mi</text>
          {''.join(bars)}
        </svg>
      </div>"""


def render_chart_panel(
    days: list[VolumeDay],
    chart_index: int,
    axis_max: float,
    y_tick_values: list[float],
    run_stats: YearRunStats | None = None,
) -> str:
    real_days = [day for day in days if not day.is_padding]
    panel_run_days = [day for day in real_days if day.miles > 0]
    panel_miles = sum(day.miles for day in real_days)
    start = days[0].day
    if run_stats is None:
        run_stats = YearRunStats(
            run_count=len(panel_run_days),
            total_miles=panel_miles,
            longest_miles=max((day.miles for day in panel_run_days), default=0.0),
        )

    return f"""
    <section class="chart-panel">
      <div class="chart-heading">
        <h2>{escape(start.strftime("%Y"))}</h2>
        <dl class="chart-summary">
          <div><dt>Distance</dt><dd>{run_stats.total_miles:.1f} <span>mi</span></dd></div>
          <div><dt>Runs</dt><dd>{run_stats.run_count}</dd></div>
          <div><dt>Average</dt><dd>{run_stats.average_miles:.1f} <span>mi</span></dd></div>
          <div><dt>Longest</dt><dd>{run_stats.longest_miles:.1f} <span>mi</span></dd></div>
        </dl>
      </div>
      {render_svg(days, chart_index, axis_max, y_tick_values)}
    </section>"""


def render_html(
    days: list[VolumeDay],
    yearly_run_stats: dict[int, YearRunStats] | None = None,
) -> str:
    max_daily_value = max((day.miles for day in days), default=1.0)
    axis_max, y_tick_values = linear_axis(max_daily_value)
    year_panels = build_calendar_years(days)
    yearly_run_stats = yearly_run_stats or {}
    chart_panels = [
        render_chart_panel(
            chart_days,
            index,
            axis_max,
            y_tick_values,
            yearly_run_stats.get(chart_days[0].day.year),
        )
        for index, chart_days in enumerate(year_panels, start=1)
    ]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Running Graph</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0f1511;
      --panel: #19201b;
      --text: #eef4ef;
      --muted: #9baaa0;
      --line: #303a33;
      --bar: #55d45f;
      --bar-strong: #8ee05d;
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

    h1 {{
      margin: 0;
      font-size: clamp(3.25rem, 7vw, 5.25rem);
      font-weight: 800;
      line-height: 0.94;
      letter-spacing: -0.055em;
    }}

    h1 span {{
      color: var(--bar-strong);
      font-style: italic;
    }}

    .chart-panel {{
      margin-top: 18px;
    }}

    .chart-panel + .chart-panel {{
      margin-top: 64px;
    }}

    .chart-heading {{
      display: flex;
      justify-content: space-between;
      gap: 28px;
      align-items: end;
      margin-bottom: 18px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--bar-strong);
    }}

    h2 {{
      margin: 0;
      font-size: 2.25rem;
      font-weight: 800;
      line-height: 1;
      letter-spacing: -0.035em;
    }}

    .chart-summary {{
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: minmax(76px, auto);
      gap: 28px;
      margin: 0;
    }}

    .chart-summary div {{
      min-width: 0;
    }}

    .chart-summary dt {{
      margin: 0 0 2px;
      color: #b7c2ba;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.07em;
      line-height: 1.2;
      text-transform: uppercase;
    }}

    .chart-summary dd {{
      margin: 0;
      color: var(--text);
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: -0.015em;
      white-space: nowrap;
    }}

    .chart-summary dd span {{
      color: var(--muted);
      font-size: 0.76em;
      font-weight: 600;
    }}

    .chart-scroll {{
      overflow-x: auto;
    }}

    .volume-chart {{
      display: block;
      width: auto;
      height: auto;
    }}

    .chart-bg {{
      fill: transparent;
    }}

    .grid-line {{
      stroke: #354139;
      stroke-width: 1;
      opacity: 0.9;
    }}

    .month-line {{
      stroke: #59665e;
      stroke-width: 1.25;
      opacity: 0.82;
    }}

    .axis-line {{
      stroke: #647168;
      stroke-width: 1;
    }}

    .axis-label,
    .month-label {{
      fill: var(--muted);
      font-size: 12px;
    }}

    .axis-unit {{
      fill: var(--muted);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.04em;
    }}

    .daily-bar {{
      opacity: 0.92;
      transition: filter 120ms ease, opacity 120ms ease;
    }}

    .daily-bar:hover {{
      filter: saturate(1.15) brightness(0.92);
      opacity: 1;
    }}

    .empty-state {{
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      padding: 28px;
      color: var(--muted);
    }}

    @media (max-width: 640px) {{
      main {{
        padding: 22px 12px 36px;
      }}

      h1 {{
        font-size: 3rem;
      }}

      .chart-heading {{
        display: block;
      }}

      .chart-summary {{
        grid-auto-flow: row;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin-top: 16px;
      }}
    }}

    @media (max-width: 420px) {{
      .chart-summary {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px 24px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Running <span>Graph</span></h1>
    </header>

    {''.join(chart_panels) if chart_panels else render_svg(days, 1, axis_max, y_tick_values)}
  </main>
</body>
</html>
"""


def write_html(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def main() -> None:
    daily_miles = load_daily_run_miles(ACTIVITIES_DIR)
    yearly_run_stats = load_yearly_run_stats(ACTIVITIES_DIR)
    days = build_volume_days(daily_miles)
    write_html(RUNNING_VOLUME_HTML_PATH, render_html(days, yearly_run_stats))
    print(f"Wrote {RUNNING_VOLUME_HTML_PATH}")


if __name__ == "__main__":
    main()
