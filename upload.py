"""
upload.py — upload a finished Short to YouTube via the Data API v3.

OAuth is file-based: `client_secrets.json` (downloaded from Google Cloud) plus a
`token.json` generated on first sign-in. Both are gitignored — never commit them.
In CI they are written from GitHub Secrets.
"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.json"
CLIENT_SECRETS = "client_secrets.json"
DEFAULT_TAGS = ["space", "facts", "shorts", "science", "nasa"]


def get_youtube_client():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
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

    print(f"📤 Uploading {video_path} to YouTube...")
    youtube = get_youtube_client()

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title[:100],
                "description": description[:4900],
                "tags": tags or DEFAULT_TAGS,
                "categoryId": "28",  # Science & Technology
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True),
    )

    response = request.execute()
    video_id = response["id"]
    print(f"✅ Uploaded! https://youtube.com/shorts/{video_id}")
    return video_id


if __name__ == "__main__":
    # Manual upload helper: pass a file path to upload it. Without an argument it
    # only prints usage — it never silently uploads a stale/hardcoded file.
    import sys

    if len(sys.argv) < 2:
        print("Usage: python upload.py <video_path> [title]")
        print("Note: agent.py already uploads automatically; this is for manual reruns.")
        sys.exit(0)

    path = sys.argv[1]
    manual_title = sys.argv[2] if len(sys.argv) > 2 else "Amazing Space Facts! #shorts #space"
    upload_video(manual_title, video_path=path)
