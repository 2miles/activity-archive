# Activity JSON Sync

This document describes how this project downloads, maintains, and updates a local archive of Strava activities using a JSON-first approach.

## Purpose

The sync system is designed to:

- Maintain a complete local archive of Strava activities
- Avoid re-downloading data unnecessarily
- Respect Strava API rate limits
- Be safe to interrupt and resume
- Treat local JSON as the source of truth for derived outputs

Strava is treated as an upstream data source, not a database.

## Archive Model

```text
archive/
  activities/
    <activity_id>.json
  streams/
    <activity_id>.json
  index/
    activity_index.json
```

- `archive/activities/*.json` contains one detailed activity per file.
- `archive/streams/*.json` contains optional per-activity stream payloads.
- `archive/index/activity_index.json` is a helper index for backfill and refresh tracking, not the canonical dataset.
- Activity files are written atomically through a temporary file and rename.
- Existing `_local` metadata is preserved when activity files are refreshed or overwritten.

## Source Of Truth

The JSON archive is the canonical dataset.

All of the following should be generated from local JSON, not live API calls:

- CSV exports
- Human-readable logs
- Markdown reports
- Route thumbnails and maps
- Heatmaps and other visualizations

Live Strava API calls should be limited to sync/export scripts.

## API Behavior

Strava read limits:

- 100 read requests per 15 minutes
- 1,000 read requests per day

Calls such as `client.get_activity(activity_id)` and stream downloads consume read requests. The exporters are designed to use filesystem checks before making detail or stream requests.

## Activity Exporter

Main entry point:

```bash
python src/export_activities_json.py
```

Current modes:

- Default sync: fetch activities after the newest archived activity.
- `--backfill`: fill missing historical activity files using `activity_index.json`, oldest first.
- `--refresh`: gradually re-fetch already archived activities and mark each file with `_local.recently_refreshed`.

### Default Sync

```bash
python src/export_activities_json.py --limit 25 --sleep 0.2
```

Behavior:

- If the archive is empty, fetches the newest activities first.
- If the archive has data, finds the newest archived `start_date`.
- Lists only activities after that date.
- Writes up to `--limit` detailed activity JSON files.
- Updates `activity_index.json` as files are written.

This is the normal ongoing sync mode once the archive exists.

### Backfill

```bash
python src/export_activities_json.py --backfill --limit 50 --sleep 0.2
```

Behavior:

- Uses `archive/index/activity_index.json` to find missing activity files.
- If the index is missing, builds it from the Strava activity list first.
- Walks the index from oldest to newest.
- Skips activity files that already exist.
- Writes up to `--limit` missing detailed activity JSON files.

Repeat this command until all historical activities are archived.

### Refresh

```bash
python src/export_activities_json.py --refresh --limit 98 --sleep 0.2
```

Behavior:

- Scans archived activity files.
- Refreshes files that do not have `_local.recently_refreshed = true`.
- Preserves existing `_local` metadata.
- Marks each refreshed file with `_local.recently_refreshed = true`.
- Resets all refresh flags after the full archive has been refreshed, so a new cycle can start later.

Use this when you want to pick up changed Strava metadata for existing archived activities, such as renamed activities.

## Stream Exporter

Main entry point:

```bash
python src/export_streams_json.py --limit 95 --sleep 0.2
```

Behavior:

- Reads activity IDs from `archive/activities/*.json`.
- Skips activities that already have `archive/streams/<activity_id>.json`.
- Downloads high-resolution streams for missing stream files.
- Writes stream files atomically.

Stream export depends on the activity archive, not on `activity_index.json`.

## Full Pipeline

Main entry point:

```bash
python src/sync.py
```

The pipeline runs these steps in order:

1. Export new activities
2. Export missing streams
3. Generate `derived/activities.csv`
4. Generate `derived/reports/runs_log.txt`
5. Generate `derived/reports/runs_log.md`
6. Generate `derived/reports/activity_log.txt`
7. Generate missing route thumbnails
8. Generate missing route maps
9. Generate heatmaps
10. Generate the running distance grid

## Typical Workflows

### First-Time Archive

Backfill activities in batches:

```bash
python src/export_activities_json.py --backfill --limit 50 --sleep 0.2
```

Then export streams in batches:

```bash
python src/export_streams_json.py --limit 95 --sleep 0.2
```

### Ongoing Sync

```bash
python src/sync.py
```

This picks up new activities, fills missing streams, and rebuilds derived outputs.

### Metadata Refresh

```bash
python src/export_activities_json.py --refresh --limit 98 --sleep 0.2
```

Run this occasionally if you want existing archived activities to pick up upstream metadata changes.

## Interruptions And Failures

The exporters are safe to interrupt.

If you hit a rate limit or press Ctrl-C:

- Completed writes remain valid.
- Atomic writes avoid partial JSON files.
- Re-running the same command resumes from filesystem state.

If you see a short-term API rate limit error, stop the script, wait about 15 to 20 minutes, then re-run the same command with the same or a lower `--limit`.

## Guarantees

The sync system aims to preserve:

- Idempotency: repeated runs do not duplicate archived data.
- Atomicity: files are not left partially written.
- Resumability: interrupted runs can continue later.
- Filesystem-first checks: existing local files prevent unnecessary API calls.

## Design Philosophy

- JSON files are long-term archive artifacts.
- Derived outputs are disposable and rebuildable.
- Strava API usage is minimized and controlled.
- The archive should remain useful even if derived outputs are deleted and rebuilt.
