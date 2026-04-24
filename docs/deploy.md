# Deploy / Update Workflow

This is the short version of how to update the NAS copy safely.

## Source Of Truth

The NAS copy is the source of truth for:

- `archive/`
- `derived/`
- `.env`
- `token.json`

Do not treat your laptop copy of those files as canonical.

Do not run real sync from your laptop if the NAS is now the canonical host.

## Normal Update Flow

1. Develop on your laptop
2. Commit working changes
3. Push to GitHub
4. SSH into the NAS
5. Pull the latest code
6. Rebuild and restart the container
7. Verify the app

## Commands On The NAS

From the NAS repo root:

```bash
cd /volume1/docker/activity-archive
git pull
docker compose up -d --build
docker compose ps
```

Then verify:

```bash
curl http://127.0.0.1:8765/api/health
curl http://127.0.0.1:8765/api/sync/status
```

Open:

```text
http://<nas-tailnet-name>:8765/
```

## When You Need To Rebuild

Run `docker compose up -d --build` after:

- backend code changes
- frontend code changes
- `requirements.txt` changes
- Docker-related changes

## When You Probably Do Not Need To Rebuild

You usually do not need a rebuild just because:

- `archive/` changed
- `derived/` changed
- `.env` changed
- `token.json` changed

Those are mounted from the NAS host and are not baked into the image.

## If Something Goes Wrong

Check container status:

```bash
docker compose ps
docker compose logs --tail=200
```

If needed, restart cleanly:

```bash
docker compose down
docker compose up -d --build
```

## Canonical Rule

Use this rule to avoid drift:

- laptop is for code
- NAS is for real data and real sync
