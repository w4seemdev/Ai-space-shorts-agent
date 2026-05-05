import os
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_youtube_client():
    token_data = os.getenv("YOUTUBE_TOKEN")
    if not token_data:
        raise Exception("❌ YOUTUBE_TOKEN not found!")
    
    token_info = json.loads(token_data)
    creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
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
                "categoryId": "28"
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

if __name__ == "__main__":
    upload_video("Amazing Space Facts! #shorts #space")