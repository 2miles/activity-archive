"""
Create an authenticated Strava API client with automatic token refresh.

This module provides a single helper function that returns a ready-to-use
`stravalib.Client` instance using tokens stored in `token.json`.

Responsibilities:
- Load OAuth tokens from disk.
- Refresh the access token if it has expired.
- Persist refreshed tokens back to `token.json`.

Usage:
    from client import get_client

    client = get_client()
    activities = client.get_activities()

Notes:
- Assumes `token.json` exists in the project root.
- Requires STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET to be set via environment.
- This module contains no OAuth authorization logic.
"""

from pathlib import Path
import json
import os
import time
from dotenv import load_dotenv
from stravalib import Client

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOKEN_PATH = PROJECT_ROOT / "token.json"


def get_client() -> Client:
    with open(TOKEN_PATH) as f:
        tok = json.load(f)

    client = Client(
        access_token=tok["access_token"],
        refresh_token=tok["refresh_token"],
        token_expires=tok["expires_at"],
    )

    if client.token_expires and client.token_expires < time.time():
        refreshed = client.refresh_access_token(
            client_id=int(os.environ["STRAVA_CLIENT_ID"]),
            client_secret=os.environ["STRAVA_CLIENT_SECRET"],
            refresh_token=tok["refresh_token"],
        )
        with open(TOKEN_PATH, "w") as f:
            json.dump(refreshed, f, indent=2)

        client.access_token = refreshed["access_token"]
        client.refresh_token = refreshed["refresh_token"]
        client.token_expires = refreshed["expires_at"]

    return client
