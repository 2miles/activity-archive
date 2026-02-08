# Activity JSON Sync

This document describes how this project downloads, maintains, and updates a local archive of Strava activities using a JSON-first approach.

## Purpose

The goal of the sync system is to:

- Maintain a complete local archive of all Strava activities
- Avoid re-downloading data unnecessarily
- Respect Strava API rate limits
- Be safe to interrupt and resume at any time
- Serve as the source of truth for all derived outputs (CSV, logs, stats, maps)

Strava is treated as an upstream data source, not a database.

## Archive model

```
archive/
  activities/
    <activity_id>.json
```

- One file per activity
- Filename is the Strava activity ID
- File contents are a JSON-serialized DetailedActivity
- Files are written atomically (.tmp → rename)

Once written, files are never modified unless explicitly forced.

## Source of truth

The JSON archive is the canonical dataset.

All of the following should be generated from local JSON, not live API calls:

- CSV exports
- Human-readable logs
- Statistics
- Visualizations / heatmaps
- Future frontend features

Live Strava API calls are only used for syncing.

## API behavior

Strava read limits:

- 100 read requests / 15 minutes
- 1,000 read requests / day

Each call to:

```
client.get_activity(activity_id)
```

consumes 1 read request

The sync script is designed so that:

- API calls are only made when a file will actually be written
- Checking for existing data is done via the filesystem (zero API cost)

## Sync script

Main entry point:

```
python3 src/export_activities_json.py
```

### What the script does

1. Lists activities via `client.get_activities()`
2. Applies a time window (`--new` or `--older`)
3. For each listed activity:
   - checks if `<id>.json` already exists
   - fetches DetailedActivity only if needed
   - writes JSON atomically
4. Stops when `--limit` files have been written (or listing is exhausted)

## Flags and behavior

### --limit

```
--limit N
```

Means "Write up to N new JSON files"

### --new

```
python3 src/export_activities_json.py --new --limit 25 --sleep 0.2
```

Behavior:

- Finds the newest archived activity
- Fetches only activities after that date
- Writes up to N new files
- Ideal for ongoing, regular syncs

**This is the command you’ll use once the archive is complete.**

### --older

```
python3 src/export_activities_json.py --40 --limit 40 --sleep 0.6
```

Behavior:

- Finds the oldest archived activity
- Fetches activities before that date
- Walks backward through history
- Used to build the archive initially

Repeat until no older activities remain.

### Default behavior

```
python3 src/export_activities_json.py --limit 50
```

- If the archive is empty → fetch newest activities
- If the archive exists → behaves like --new

This matches the most common expectation: “sync forward”.

### --force

- Overwrites existing JSON files
- Forces re-downloads
- Rarely needed

Use only if:

- schema changed
- corrupted files
- intentional reprocessing

### --sleep

```
--seep 0.6
```

- Sleeps after each successful write
- Helps stay under short-term rate limits

## Typical workflows

### First-time archive (empty directory)

```
python3 src/export_activities_json.py --limit 50 --sleep 0.6
```

Seeds the archive with the most recent activities.

### Backfill older history

```
python3 src/export_activities_json.py --older --limit 40 --sleep 0.6
```

Repeat until:

- no activities are listed
- or wrote 0

### Ongoing sync (normal use)

```
python3 src/export_activities_json.py --new --limit 25 --sleep 0.2
```

Run occasionally to pick up new activities.

## Interruptions and failures

The sync process is safe to interrupt.

If you hit a rate limit or press Ctrl-C:

- All completed writes are valid
- No partial files are left behind
- Re-running the same command resumes correctly

If you see:

```
Short term API rate limit exceeded
```

Do this:

1. Stop the script
2. Wait ~15–20 minutes
3. Re-run the same command

## Guarantees

The sync system guarantees:

- Idempotency – running the same command twice does not duplicate data
- Atomicity – files are never partially written
- Resumability – safe to stop and restart at any time
- Filesystem-first checks – no wasted API calls

## Design philosophy

- JSON files are long-term, stable artifacts
- Strava API usage is minimized and controlled
- The archive is meant to outlive Strava itself
- Derived formats (CSV, logs) are disposable

This is an archival pipeline, not a scraper.
