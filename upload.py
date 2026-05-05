import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.json"
CLIENT_SECRETS = "client_secrets.json"

def get_youtube_client():
    creds = None

    # Load saved token if exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid token, login
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
        creds = flow.run_local_server(port=0)
        # Save token for next time
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

def upload_video(title, description="Auto-generated space facts Short!"):
    print("📤 Uploading to YouTube...")

    youtube = get_youtube_client()

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["space", "facts", "shorts", "science", "nasa"],
                "categoryId": "28"  # Science & Technology
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        },
        media_body=MediaFileUpload("output.mp4", chunksize=-1, resumable=True)
    )

    response = request.execute()
    video_id = response["id"]
    print(f"✅ Uploaded! Watch at: https://youtube.com/shorts/{video_id}")
    return video_id

# Test it
if __name__ == "__main__":
    upload_video("Amazing Space Facts! #shorts #space")