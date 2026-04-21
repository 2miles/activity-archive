import subprocess
import sys


PYTHON = sys.executable


def run(label, cmd):
    print(f"\n>>> {label}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"\nERROR during step -> {label}")
        sys.exit(result.returncode)


def main():

    # 1. Pull new Strava activities (default sync mode)
    run(
        "Export new activities",
        [PYTHON, "src/export_activities_json.py", "--limit", "98", "--sleep", "0.2"],
    )

    # 2. Download streams for activities missing them
    run(
        "Export missing streams",
        [PYTHON, "src/export_streams_json.py", "--limit", "98", "--sleep", "0.2"],
    )

    # 3. Generate derived CSV
    run("Generate derived CSV", [PYTHON, "src/generate_csv.py"])

    # 4. Generate run log
    run("Generate run log", [PYTHON, "src/generate_run_log.py"])

    # 5. Generate markdown run log
    run("Generate markdown run log", [PYTHON, "src/generate_run_log_md.py"])

    # 6. Generate activity log
    run("Generate activity log", [PYTHON, "src/generate_activity_log.py"])

    # 7. Generate transparent route thumbnails
    run(
        "Generate route thumbnails",
        [PYTHON, "src/generate_route_thumbnails.py", "--size", "400"],
    )

    # 8. Generate route maps
    run(
        "Generate route maps",
        [PYTHON, "src/generate_route_maps.py", "--sleep", "0.2"],
    )

    # 9. Generate heatmaps
    run(
        "Generate_heatmaps",
        [PYTHON, "src/generate_heatmaps.py"],
    )

    # 10. Generate running distance grid
    run(
        "Generate running distance grid",
        [PYTHON, "src/generate_run_distance_grid.py"],
    )

    print("\n✓ Update complete")


if __name__ == "__main__":
    main()
