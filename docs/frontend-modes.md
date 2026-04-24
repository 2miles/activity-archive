# Frontend Modes

This project has two normal ways to run the frontend:

1. Development mode
2. Built mode

They exist because building the UI and using the app are different tasks.

## Development Mode

In development mode, the React frontend is served by Vite.

Commands:

```bash
# terminal 1, repo root
.venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8765

# terminal 2
cd web
npm run dev
```

Then open:

```text
http://127.0.0.1:5173
```

What is happening:

- FastAPI runs the backend on port `8765`
- Vite runs the frontend dev server on port `5173`
- Vite proxies `/api` and `/derived` requests to FastAPI

Why this mode exists:

- Fast rebuilds while editing React files
- Hot reload in the browser
- Better frontend development workflow

Use development mode when:

- you are editing the React UI
- you want fast feedback while coding
- you are changing CSS/layout/components

Tradeoffs:

- requires two running processes
- you open the Vite URL, not the FastAPI root URL

## Built Mode

In built mode, the React app is compiled into static files first, and then
FastAPI serves those built files.

Commands:

```bash
cd web
npm run build
cd ..
.venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765/
```

What is happening:

- `npm run build` creates production frontend files in `web/dist/`
- FastAPI serves those files at `/`
- FastAPI also serves the API and derived files

Why this mode exists:

- simpler runtime
- only one process to run
- better for normal personal use
- better for NAS/Tailscale use
- better for Docker deployment

Use built mode when:

- you are not actively editing the frontend
- you want to just use the app
- you want to run it on your NAS
- you want to containerize it

Tradeoffs:

- no hot reload
- after frontend changes, you must rebuild with `npm run build`

## Simple Mental Model

Development mode:

```text
Vite serves the frontend
FastAPI serves the backend
```

Built mode:

```text
FastAPI serves both the built frontend and the backend
```

## Which One Should You Use?

Use development mode if you are actively building the UI.

Use built mode if you are just running the app for yourself.

For Docker and NAS deployment, built mode is usually the correct choice.
