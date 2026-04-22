# Local Server

This repo includes a small FastAPI server for viewing generated artifacts from
`derived/`. It is intended for local or private-network use, such as running on a
NAS and accessing it over Tailscale.

The server is currently read-only. It can list and serve generated files, but it
does not yet trigger `sync`.

## Start The Server

From the repo root, use the project virtual environment:

```bash
.venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8765
```

For local-only use, `127.0.0.1` is the safest host because it only listens on the
same machine.

## Verify It Works

Open these URLs in a browser:

```text
http://127.0.0.1:8765/api/health
http://127.0.0.1:8765/api/artifacts
http://127.0.0.1:8765/derived/heatmaps/running_distance_grid.html
```

Expected behavior:

- `/api/health` returns `{"status":"ok"}`.
- `/api/artifacts` returns a JSON list of generated non-image artifacts.
- `/derived/heatmaps/running_distance_grid.html` serves the generated running distance grid.

To include maps and thumbnails in the artifact list:

```text
http://127.0.0.1:8765/api/artifacts?include_images=true
```

## Stop The Server

If the server is running in the foreground, press:

```text
Ctrl+C
```

If you started it in another terminal and need to find it:

```bash
lsof -i :8765
```

Then stop the process by PID:

```bash
kill <PID>
```

## Tailscale / NAS Use

For access from another device over Tailscale, the server needs to listen on an
address reachable from the tailnet. A simple private-network command is:

```bash
.venv/bin/python -m uvicorn server.app:app --host 0.0.0.0 --port 8765
```

Then visit the NAS Tailscale name or IP from another device:

```text
http://<nas-tailnet-name>:8765
```

Do not expose this server directly to the public internet. Future sync endpoints
will trigger Strava API calls and mutate local archive files, so they should be
protected before remote use.

## Current Endpoints

```text
GET /api/health
GET /api/artifacts
GET /api/artifacts?include_images=true
GET /derived/<path>
```

`/derived/<path>` serves files from the local `derived/` directory. The private
archive data in `archive/`, `.env`, and `token.json` are not served by this
server.

## Future Work

Planned dashboard-oriented endpoints:

- `POST /api/sync` to trigger the existing sync pipeline.
- `GET /api/sync/status` to report whether sync is running, last success time, and last error.
- A React/Vite frontend that calls these endpoints and links to generated artifacts.
