"""
Generate a Strava OAuth authorization URL.

This script prints a one-time authorization URL that must be opened in a web
browser to grant this application read access to Strava activity data.

Usage:
    python auth/auth_url.py

Steps:
1. Run this script to print the authorization URL.
2. Open the URL in a browser and approve access.
3. After approval, Strava will redirect to a localhost URL that will not load.
4. Copy the `code` parameter from the browser address bar.
5. Paste that code into `auth/exchange_code.py`.

Notes:
- This script does NOT perform authentication itself.
- It does NOT create or modify token.json.
- It is only needed when initially authorizing or re-authorizing the app.
- The redirect URI does not need to exist; the code is copied manually.
"""

from stravalib import Client
from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID = int(os.environ["STRAVA_CLIENT_ID"])

client = Client()
url = client.authorization_url(
    client_id=CLIENT_ID,
    redirect_uri="http://localhost:8765/authorization",
    scope=["activity:read_all"],  # minimal + sufficient for exporting everything
    approval_prompt="force",  # guarantees you get a fresh code
)
print(url)
