# Local Server

This repo includes:

- A FastAPI backend in `server/`
- A React/Vite frontend in `web/`

The backend serves generated files from `derived/`, exposes sync endpoints, and
can serve the built frontend at `/`.

## Modes

Use one of these workflows:

1. Frontend development mode
   Run FastAPI and Vite separately. Open the Vite URL.
2. Built frontend mode
   Build the React app once, then let FastAPI serve it at `/`.

For active UI work, use frontend development mode.

For local personal use, NAS use, or Tailscale use, built frontend mode is usually
simpler.

If the difference between these two modes is new to you, see
[docs/frontend-modes.md](frontend-modes.md).

If you want to run the app on your NAS in containers, see [docs/docker.md](docker.md).

## Backend Server

Start the FastAPI server from the repo root:

```bash
.venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8765
```

For local-only use, `127.0.0.1` is safest because it only listens on the same
machine.

## Frontend Development Mode

Install frontend dependencies once:

```bash
cd web
npm install
```

Start the Vite dev server:

```bash
npm run dev
```

By default Vite runs on:

```text
http://127.0.0.1:5173
```

The Vite config proxies `/api` and `/derived` to FastAPI on port `8765`, so local
frontend development normally uses two terminals:

```bash
# terminal 1, from repo root
.venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8765

# terminal 2
cd web
npm run dev
```

Then open:

```text
http://127.0.0.1:5173
```

If port `5173` is already in use:

```bash
npm run dev -- --port 5174
```

## Built Frontend Mode

Build the React frontend:

```bash
cd web
npm run build
```

This creates `web/dist/`.

If `web/dist/index.html` exists, FastAPI serves it at:

```text
http://127.0.0.1:8765/
```

Typical built-frontend workflow:

```bash
# after frontend changes
cd web
npm run build

# serve from FastAPI
cd ..
.venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765/
```

## Recommended Workflow

For active frontend development:

1. Start FastAPI on `127.0.0.1:8765`.
2. Start Vite on `127.0.0.1:5173` or another local port.
3. Open the Vite URL, not the FastAPI root URL.

For normal personal use after building:

1. Run `npm run build` in `web/`.
2. Start FastAPI.
3. Open `http://127.0.0.1:8765/`.

## Verify It Works

Useful URLs:

```text
http://127.0.0.1:8765/
http://127.0.0.1:8765/api/health
http://127.0.0.1:8765/api/artifacts
http://127.0.0.1:8765/api/sync/status
http://127.0.0.1:8765/derived/heatmaps/running_distance_grid.html
```

Expected behavior:

- `/` serves the built React frontend if `web/dist/` exists.
- `/api/health` returns `{"status":"ok"}`.
- `/api/artifacts` returns a JSON list of generated non-image artifacts.
- `/api/sync/status` returns the current sync state and last run timestamps.
- `/derived/heatmaps/running_distance_grid.html` serves the generated running distance grid.

To include maps and thumbnails in the artifact list:

```text
http://127.0.0.1:8765/api/artifacts?include_images=true
```

## Current Endpoints

```text
GET /api/health
GET /api/artifacts
GET /api/artifacts?include_images=true
GET /api/sync/status
POST /api/sync
GET /derived/<path>
```

`/derived/<path>` serves files from the local `derived/` directory. The private
archive data in `archive/`, `.env`, and `token.json` are not served by this
server.

## Trigger A Sync

Start the server first, then trigger sync with:

```bash
curl -X POST http://127.0.0.1:8765/api/sync
```

Check status with:

```bash
curl http://127.0.0.1:8765/api/sync/status
```

Behavior notes:

- The sync runs in the background.
- Only one sync can run at a time.
- If a sync is already running, `POST /api/sync` returns HTTP `409`.
- Status values currently include `idle`, `running`, `success`, and `error`.

## Stop The Servers

If FastAPI or Vite is running in the foreground, press:

```text
Ctrl+C
```

To find the FastAPI process by port:

```bash
lsof -i :8765
```

Then stop it by PID:

```bash
kill <PID>
```

## Tailscale / NAS Use

For access from another device over Tailscale, FastAPI needs to listen on an
address reachable from the tailnet:

```bash
.venv/bin/python -m uvicorn server.app:app --host 0.0.0.0 --port 8765
```

Then visit the NAS Tailscale name or IP:

```text
http://<nas-tailnet-name>:8765
```

Do not expose this server directly to the public internet. The sync endpoint can
trigger Strava API calls and mutate local archive files, so it should be protected
before wider exposure.

## Troubleshooting

- Dashboard says `Backend unavailable`:
  Make sure FastAPI is running on `127.0.0.1:8765`, then verify:

  ```bash
  curl http://127.0.0.1:8765/api/health
  curl http://127.0.0.1:8765/api/sync/status
  ```

- Vite dev server port is already in use:

  ```bash
  npm run dev -- --port 5174
  ```

- FastAPI root `/` does not show the dashboard:
  Build the frontend first:

  ```bash
  cd web
  npm run build
  ```

## Future Work

- Improve dashboard copy and UI states.
- Add a simple sync history view.
- Add auth or other protection before exposing sync control beyond localhost/private tailnet use.
