"""
Exchange a Strava OAuth authorization code for access and refresh tokens.

This script takes a one-time authorization `code` obtained via `auth_url.py`,
exchanges it with Strava for OAuth tokens, and writes them to `token.json`
in the project root.

Usage:
    1. Obtain a fresh authorization code using `auth/auth_url.py`.
    2. Paste the code into the CODE variable below.
    3. Run:
           python auth/exchange_code.py

Output:
    - Creates or overwrites `token.json` containing:
        - access_token
        - refresh_token
        - expires_at (Unix epoch seconds)

Notes:
- Authorization codes are single-use and expire quickly.
- This script should be run immediately after obtaining a new code.
- This script is typically run once per machine or after revoking access.
- `token.json` must NOT be committed to version control.
"""

import json
from stravalib import Client
from dotenv import load_dotenv
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOKEN_PATH = PROJECT_ROOT / "token.json"

load_dotenv()

CLIENT_ID = int(os.environ["STRAVA_CLIENT_ID"])
CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]

CODE = "PASTE_NEW_CODE_HERE"  # <-- from the browser address bar


client = Client()
token_response = client.exchange_code_for_token(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    code=CODE,
)

with open(TOKEN_PATH, "w") as f:
    json.dump(token_response, f, indent=2)

print(f"Saved {TOKEN_PATH}")
print("expires_at:", token_response.get("expires_at"))
