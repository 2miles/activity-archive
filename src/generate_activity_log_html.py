#!/usr/bin/env python3
"""
Generate a responsive HTML activity log from archived activity JSON.

Input:
  archive/activities/*.json

Output:
  derived/reports/activity_log.html

Newest -> oldest.
Activities are grouped by month with activity type badges, distance, and minutes.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path

from activity_archive.activity import activity_start_local, activity_type
from activity_archive.archive import iter_activity_dicts
from activity_archive.paths import ACTIVITIES_DIR, ACTIVITY_LOG_HTML_PATH
from activity_archive.units import meters_to_miles, safe_float, safe_int


TYPE_CLASSES = {
    "Run": "type-run",
    "TrailRun": "type-run",
    "VirtualRun": "type-run",
    "Walk": "type-walk",
    "Hike": "type-hike",
    "Ride": "type-ride",
    "VirtualRide": "type-ride",
}

TYPE_LABELS = {
    "Run": ("run", "runs"),
    "TrailRun": ("trail run", "trail runs"),
    "VirtualRun": ("virtual run", "virtual runs"),
    "Walk": ("walk", "walks"),
    "Hike": ("hike", "hikes"),
    "Ride": ("ride", "rides"),
    "VirtualRide": ("virtual ride", "virtual rides"),
}


@dataclass(frozen=True)
class ActivityRow:
    date_str: str
    type_name: str
    dist_mi: float
    moving_minutes: int


def load_activities_by_month(activities_dir: Path) -> dict[tuple[int, int], list[ActivityRow]]:
    if not activities_dir.exists():
        raise FileNotFoundError(f"Missing activities archive dir: {activities_dir}")

    by_month: dict[tuple[int, int], list[ActivityRow]] = defaultdict(list)

    for activity in iter_activity_dicts(activities_dir):
        dt_local = activity_start_local(activity)
        if dt_local is None:
            continue

        meters = safe_float(activity.get("distance"))
        moving_seconds = safe_int(activity.get("moving_time"))
        d = dt_local.date()

        by_month[(d.year, d.month)].append(
            ActivityRow(
                date_str=d.strftime("%Y-%m-%d"),
                type_name=activity_type(activity) or "Activity",
                dist_mi=meters_to_miles(meters),
                moving_minutes=round(moving_seconds / 60),
            )
        )

    return by_month


def type_class(type_name: str) -> str:
    return TYPE_CLASSES.get(type_name, "type-other")


def type_total_label(type_name: str, count: int) -> str:
    singular, plural = TYPE_LABELS.get(
        type_name,
        (type_name.lower(), f"{type_name.lower()}s"),
    )
    return f"{count} {singular if count == 1 else plural}"


def render_type_totals(counter: Counter[str]) -> str:
    return "".join(
        f"""
          <span class="type-total {escape(type_class(type_name))}">
            {escape(type_total_label(type_name, count))}
          </span>"""
        for type_name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    )


def render_month_section(year: int, month: int, activities: list[ActivityRow]) -> str:
    month_name = date(year, month, 1).strftime("%B %Y")
    month_activities = sorted(activities, key=lambda row: row.date_str, reverse=True)

    total_miles = sum(row.dist_mi for row in month_activities)
    total_minutes = sum(row.moving_minutes for row in month_activities)
    type_counts = Counter(row.type_name for row in month_activities)

    rows = []
    for row in month_activities:
        activity_date = date.fromisoformat(row.date_str)
        day = f"{activity_date.strftime('%b')} {activity_date.day}"
        rows.append(
            f"""
            <tr>
              <td>{escape(day)}</td>
              <td>
                <span class="type-badge {escape(type_class(row.type_name))}">
                  {escape(row.type_name)}
                </span>
              </td>
              <td>{row.dist_mi:.2f}</td>
              <td>{row.moving_minutes} min</td>
            </tr>"""
        )

    return f"""
    <section class="month-section">
      <div class="month-heading">
        <div class="month-title">
          <h2>{escape(month_name)}</h2>
          <div class="type-totals">
            {render_type_totals(type_counts)}
          </div>
        </div>
        <dl class="month-summary">
          <div><dt>Activities</dt><dd>{len(month_activities)}</dd></div>
          <div><dt>Distance</dt><dd>{total_miles:.2f} <span>mi</span></dd></div>
          <div><dt>Time</dt><dd>{total_minutes} <span>min</span></dd></div>
        </dl>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Day</th>
              <th>Type</th>
              <th>Miles</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </div>
    </section>"""


def render_html(activities_by_month: dict[tuple[int, int], list[ActivityRow]]) -> str:
    month_keys = sorted(activities_by_month.keys(), reverse=True)

    month_sections = [
        render_month_section(year, month, activities_by_month[(year, month)])
        for year, month in month_keys
    ]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Activity Log</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0f1511;
      --text: #eef4ef;
      --muted: #9baaa0;
      --label: #b7c2ba;
      --line: #303a33;
      --accent: #8ee05d;
      --run: #62b0ff;
      --walk: #72df91;
      --hike: #f2c94c;
      --ride: #ff8b7b;
      --other: #b7c2ba;
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

    .month-summary dd span {{
      color: var(--muted);
      font-size: 0.76em;
      font-weight: 600;
    }}

    .type-totals {{
      display: flex;
      flex-wrap: wrap;
      gap: 5px 12px;
      margin-top: 9px;
    }}

    .type-total,
    .type-badge {{
      display: inline-flex;
      color: var(--other);
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}

    .type-badge {{
      min-width: 72px;
      font-size: 0.8rem;
      letter-spacing: 0.02em;
    }}

    .type-run {{
      color: var(--run);
    }}

    .type-walk {{
      color: var(--walk);
    }}

    .type-hike {{
      color: var(--hike);
    }}

    .type-ride {{
      color: var(--ride);
    }}

    .type-other {{
      color: var(--other);
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
    td:first-child,
    th:nth-child(2),
    td:nth-child(2) {{
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
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin-top: 16px;
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
      <h1>Activity <span>Log</span></h1>
    </header>
    {''.join(month_sections)}
  </main>
</body>
</html>
"""


def main() -> None:
    activities_by_month = load_activities_by_month(ACTIVITIES_DIR)
    month_count = len(activities_by_month)
    content = render_html(activities_by_month)

    ACTIVITY_LOG_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIVITY_LOG_HTML_PATH.write_text(content, encoding="utf-8")

    print(f"Wrote {month_count} month blocks to {ACTIVITY_LOG_HTML_PATH}")


if __name__ == "__main__":
    main()
