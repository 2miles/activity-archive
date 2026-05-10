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


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    word = singular if count == 1 else plural or f"{singular}s"
    return f"{count} {word}"


def render_summary_card(label: str, value: str) -> str:
    return f"""
      <div class="summary-card">
        <span>{escape(label)}</span>
        <strong>{escape(value)}</strong>
      </div>"""


def render_type_totals(counter: Counter[str]) -> str:
    return "".join(
        f"""
          <span class="type-chip {escape(type_class(type_name))}">
            {escape(type_name)} {count}
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
              <td>{row.moving_minutes}</td>
            </tr>"""
        )

    return f"""
    <section class="month-section">
      <div class="month-heading">
        <div>
          <h2>{escape(month_name)}</h2>
          <div class="type-totals">
            {render_type_totals(type_counts)}
          </div>
        </div>
        <div class="month-summary">
          <span>{pluralize(len(month_activities), "activity", "activities")}</span>
          <span>{total_miles:.2f} miles</span>
          <span>{total_minutes} min</span>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Day</th>
              <th>Type</th>
              <th>Miles</th>
              <th>Minutes</th>
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
    all_rows = [row for rows in activities_by_month.values() for row in rows]
    type_counts = Counter(row.type_name for row in all_rows)
    total_miles = sum(row.dist_mi for row in all_rows)
    total_minutes = sum(row.moving_minutes for row in all_rows)

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
      color-scheme: light;
      --bg: #f7f4ef;
      --panel: #ffffff;
      --text: #1d2520;
      --muted: #647067;
      --line: #ddd6cc;
      --accent-soft: #d9f0ec;
      --run-bg: #dbeafe;
      --run-text: #1d4ed8;
      --walk-bg: #dcfce7;
      --walk-text: #166534;
      --hike-bg: #fef3c7;
      --hike-text: #92400e;
      --ride-bg: #fee2e2;
      --ride-text: #b91c1c;
      --other-bg: #e5e7eb;
      --other-text: #374151;
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

    .month-summary,
    .type-totals {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      font-size: 0.9rem;
    }}

    .month-summary {{
      justify-content: flex-end;
      color: var(--muted);
    }}

    .type-totals {{
      margin-top: 10px;
    }}

    .month-summary span,
    .type-chip,
    .type-badge {{
      border-radius: 999px;
      padding: 4px 9px;
      font-weight: 700;
    }}

    .month-summary span {{
      background: var(--accent-soft);
      color: #164e47;
      font-weight: 500;
    }}

    .type-badge {{
      display: inline-flex;
      min-width: 66px;
      justify-content: center;
      font-size: 0.84rem;
    }}

    .type-chip {{
      font-size: 0.78rem;
    }}

    .type-run {{
      background: var(--run-bg);
      color: var(--run-text);
    }}

    .type-walk {{
      background: var(--walk-bg);
      color: var(--walk-text);
    }}

    .type-hike {{
      background: var(--hike-bg);
      color: var(--hike-text);
    }}

    .type-ride {{
      background: var(--ride-bg);
      color: var(--ride-text);
    }}

    .type-other {{
      background: var(--other-bg);
      color: var(--other-text);
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
    td:first-child,
    th:nth-child(2),
    td:nth-child(2) {{
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
      <h1>Activity Log</h1>
      <p class="lede">A monthly view of archived activities, generated from local Activity Archive JSON.</p>
      <div class="summary-grid">
        {render_summary_card("Months", str(len(month_keys)))}
        {render_summary_card("Activities", str(len(all_rows)))}
        {render_summary_card("Miles", f"{total_miles:.2f}")}
        {render_summary_card("Minutes", str(total_minutes))}
        {render_summary_card("Types", str(len(type_counts)))}
      </div>
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
