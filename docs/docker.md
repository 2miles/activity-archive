# Docker Deployment

This project can run as a single container in built-frontend mode.

That means:

- the React frontend is built into the image
- FastAPI serves the built frontend at `/`
- FastAPI also serves the API and `derived/` files

This is the recommended mode for NAS deployment.

## Why Docker Fits This Repo

Docker is a good fit here because:

- the app has a clear runtime shape
- the frontend only needs a build step, not a separate production server
- the archive and derived files can stay on NAS-mounted storage
- your NAS already runs other apps in containers

The container should be disposable.

The data should not be disposable.

## Mounted Data

The compose file mounts:

- `archive/` to `/app/archive`
- `derived/` to `/app/derived`
- `.env` to `/app/.env`
- `token.json` to `/app/token.json`

Important:

- `archive/` must be writable
- `derived/` must be writable
- `token.json` must be writable because Strava token refresh may update it
- `.env` can be read-only

These mounted files/directories are the canonical local state.

## Compose Details

The compose file sets:

- an explicit project name: `activity-archive`
- an explicit container name: `activity-archive`
- a healthcheck against `/api/health`

That makes Docker Desktop and `docker compose ps` easier to read.

## Build And Run

From the repo root:

```bash
docker compose build
docker compose up
```

Or detached:

```bash
docker compose up -d --build
```

Then open:

```text
http://127.0.0.1:8765/
```

## Stop

```bash
docker compose down
```

## Update After Code Changes

If you change backend or frontend code:

```bash
docker compose up -d --build
```

That rebuilds the image and restarts the container.

## NAS Workflow

Recommended deployment flow:

1. Develop on your laptop
2. Commit working changes
3. Push to GitHub
4. Pull on the NAS
5. Run `docker compose up -d --build`

Only run real sync against the NAS copy, not your laptop copy.

For a shorter day-to-day NAS update checklist, see [docs/deploy.md](deploy.md).

## First-Time NAS Setup

Before the NAS becomes canonical:

1. Copy your current good `archive/` to the NAS
2. Copy your current good `derived/` to the NAS
3. Put the real `.env` on the NAS
4. Put the real `token.json` on the NAS
5. Start the container
6. From then on, treat the NAS as the source of truth

## Verify It Works

```bash
curl http://127.0.0.1:8765/api/health
curl http://127.0.0.1:8765/api/sync/status
docker compose ps
```

Expected:

- `/api/health` returns `{"status":"ok"}`
- `/api/sync/status` returns JSON status data
- `http://127.0.0.1:8765/` loads the built dashboard
- `docker compose ps` should eventually show the container as healthy

## Tailscale

If the NAS is on Tailscale, access it by the NAS tailnet hostname or IP:

```text
http://<nas-tailnet-name>:8765/
```

## Notes

- The Docker image contains app code and the built frontend
- The mounted volumes contain the persistent archive and generated outputs
- This setup uses built mode, not Vite dev mode
