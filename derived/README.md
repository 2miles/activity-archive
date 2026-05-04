# Derived Outputs

This directory contains recomputable outputs built from the JSON archive.

The source of truth is:

```text
archive/
  activities/
  streams/
```

Generated outputs currently include:

```text
derived/
  activities.csv
  all_routes_map.html
  heatmaps/
    *.html
    running_distance_grid.html
  maps/
    <activity_id>.png
  reports/
    activity_log.txt
    runs_log.txt
    runs_log.md
  thumbnails/
    <activity_id>.png
```

These files should be treated as disposable build artifacts. Rebuild them from the archive with:

```bash
python src/generate_csv.py
python src/generate_run_log.py
python src/generate_run_log_md.py
python src/generate_activity_log.py
python src/generate_route_thumbnails.py --size 400
python src/generate_route_maps.py --sleep 0.2
python src/generate_heatmaps.py
python src/generate_run_distance_grid.py
```

Or run the normal pipeline:

```bash
python src/sync.py
```
