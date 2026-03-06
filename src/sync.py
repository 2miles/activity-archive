import subprocess
import sys


def run(cmd):
    print(f"\n>>> Running: {cmd}")
    result = subprocess.run(cmd, shell=True)

    if result.returncode != 0:
        print(f"\nERROR: command failed -> {cmd}")
        sys.exit(result.returncode)


def main():

    # 1. Pull new Strava activities
    run("python src/export_activities_json.py --new --limit 98 --sleep 0.2")

    # 2. Generate derived CSV
    run("python src/generate_csv.py")

    # 3. Generate run log
    run("python src/generate_run_log.py")

    # 4. Generate activity log
    run("python src/generate_activity_log.py")

    print("\n✓ Update complete")


if __name__ == "__main__":
    main()
