"""
authorize.py — one-time local helper: run the YouTube OAuth flow in a browser
and write a fresh token.json.

Run it whenever the refresh token dies (invalid_grant in CI):

    python authorize.py

Then copy the ENTIRE contents of the new token.json into the YOUTUBE_TOKEN
repository secret (GitHub repo -> Settings -> Secrets and variables -> Actions).

To stop refresh tokens expiring every 7 days, open the Google Cloud Console ->
APIs & Services -> OAuth consent screen and set Publishing status to
"In production" (an unverified app just shows a warning on YOUR one-time
sign-in; uploads are unaffected).
"""

import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

from upload import CLIENT_SECRETS, SCOPES, TOKEN_FILE


def main():
    if not os.path.exists(CLIENT_SECRETS):
        print(f"❌ {CLIENT_SECRETS} not found. Download an OAuth *desktop* client "
              "JSON from Google Cloud Console (YouTube Data API v3 enabled) and "
              "save it here first.")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    print(f"✅ Wrote {TOKEN_FILE}.")
    print("Next: update the YOUTUBE_TOKEN GitHub secret with this file's full "
          "contents so the daily workflow can upload.")


if __name__ == "__main__":
    main()
