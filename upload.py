"""
upload.py — upload a finished Short to YouTube via the Data API v3.

OAuth is file-based: `client_secrets.json` (downloaded from Google Cloud) plus a
`token.json` generated on first sign-in (run `python authorize.py`). Both are
gitignored — never commit them. In CI they are written from GitHub Secrets.
"""

import http.client
import logging
import os
import random
import ssl
import sys
import time

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

log = logging.getLogger("upload")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.json"
CLIENT_SECRETS = "client_secrets.json"
DEFAULT_TAGS = ["space", "facts", "shorts", "science", "nasa"]

# Chunked resumable upload: a mid-upload network blip resumes instead of
# failing the whole run.
CHUNK_SIZE = 8 * 1024 * 1024
MAX_RETRIES = 8
RETRIABLE_STATUS = {500, 502, 503, 504}
RETRIABLE_EXCEPTIONS = (ssl.SSLError, http.client.IncompleteRead,
                        ConnectionError, OSError)

# YouTube limits: title 100 chars; description 5000 BYTES of UTF-8 (not chars).
TITLE_MAX_BYTES = 100
DESCRIPTION_MAX_BYTES = 4900


def _headless():
    """True when there is no human to click through a browser OAuth flow."""
    return bool(os.getenv("CI") or os.getenv("GITHUB_ACTIONS")) \
        or not sys.stdin.isatty()


def _clean_metadata(text, max_bytes):
    """Strip characters YouTube rejects and enforce its byte limits."""
    text = text.replace("<", "").replace(">", "")
    return text.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore").strip()


def get_youtube_client():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as e:
                raise RuntimeError(
                    "YouTube refresh token was rejected (invalid_grant). "
                    "Re-run `python authorize.py` locally and update the "
                    "YOUTUBE_TOKEN repo secret with the new token.json. If this "
                    "recurs every ~7 days, set the Google Cloud OAuth consent "
                    "screen to 'In production' — Testing-mode refresh tokens "
                    "expire weekly."
                ) from e
        else:
            if _headless():
                raise RuntimeError(
                    "token.json is missing or unusable and interactive OAuth is "
                    "impossible here. Run `python authorize.py` locally, then "
                    "update the YOUTUBE_TOKEN secret with the new token.json."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(title, description="Auto-generated space facts Short!",
                 video_path="output.mp4", tags=None):
    """Upload `video_path` to YouTube and return the new video id."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video to upload not found: {video_path}")

    title = _clean_metadata(title, TITLE_MAX_BYTES)
    description = _clean_metadata(description, DESCRIPTION_MAX_BYTES)

    log.info("📤 Uploading %s to YouTube...", video_path)
    youtube = get_youtube_client()

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags or DEFAULT_TAGS,
                "categoryId": "28",  # Science & Technology
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(video_path, chunksize=CHUNK_SIZE,
                                   resumable=True),
    )

    response = None
    retries = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                log.info("   upload %d%%...", int(status.progress() * 100))
        except (HttpError, *RETRIABLE_EXCEPTIONS) as e:
            if isinstance(e, HttpError) and e.resp.status not in RETRIABLE_STATUS:
                raise
            retries += 1
            if retries > MAX_RETRIES:
                raise RuntimeError(
                    f"Upload failed after {MAX_RETRIES} retries") from e
            delay = min(2 ** retries, 60) * (0.5 + random.random() / 2)
            log.warning("Transient upload error (%d/%d), retrying in %.1fs: %s",
                        retries, MAX_RETRIES, delay, e)
            time.sleep(delay)

    video_id = response["id"]
    log.info("✅ Uploaded! https://youtube.com/shorts/%s", video_id)
    return video_id


if __name__ == "__main__":
    # Manual upload helper: pass a file path to upload it. Without an argument it
    # only prints usage — it never silently uploads a stale/hardcoded file.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s",
                        datefmt="%H:%M:%S")

    if len(sys.argv) < 2:
        print("Usage: python upload.py <video_path> [title]")
        print("Note: agent.py already uploads automatically; this is for manual reruns.")
        sys.exit(0)

    path = sys.argv[1]
    manual_title = sys.argv[2] if len(sys.argv) > 2 else "Amazing Space Facts! #shorts"
    upload_video(manual_title, video_path=path)
