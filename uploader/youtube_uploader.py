"""
YouTube Uploader - Uploads video to YouTube using Data API v3
FREE - 10,000 units/day quota
Setup: Create OAuth2 credentials in Google Cloud Console
"""

import json
import os
import pickle
from pathlib import Path

# Google API client
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = "config/youtube_token.pickle"
CREDENTIALS_PATH = "config/youtube_credentials.json"


class YouTubeUploader:
    def __init__(self):
        self.service = None
        if GOOGLE_AVAILABLE:
            self._init_service()

    def _init_service(self):
        """Initialize YouTube API service with OAuth2"""
        creds = None

        # Load saved token
        if os.path.exists(TOKEN_PATH):
            with open(TOKEN_PATH, "rb") as token:
                creds = pickle.load(token)

        # Refresh or re-authenticate
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif not creds or not creds.valid:
            if not os.path.exists(CREDENTIALS_PATH):
                print("   ⚠️ YouTube credentials not found. Skipping upload.")
                print(f"   📋 Add credentials to: {CREDENTIALS_PATH}")
                return

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            # For GitHub Actions: use service account or pre-authorized token
            creds = flow.run_local_server(port=0)

        # Save token
        Path(TOKEN_PATH).parent.mkdir(exist_ok=True)
        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)

        self.service = build("youtube", "v3", credentials=creds)

    def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list,
    ) -> str:
        """Upload video to YouTube as a Short"""

        if not self.service:
            print("   ⚠️ YouTube service not initialized. Saving metadata only.")
            return self._save_metadata(video_path, title, description, tags)

        print(f"   📤 Uploading: {title}")

        # Add #Shorts to make it a YouTube Short
        title = f"{title} #Shorts"[:100]
        description = f"{description}\n\n#Shorts #Facts #Viral"

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags + ["Shorts", "Facts", "Viral"],
                "categoryId": "22",  # People & Blogs
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": "private",  # Saved as draft — publish manually
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024,  # 1MB chunks
        )

        request = self.service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        # Resumable upload
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"   📊 Upload progress: {int(status.progress() * 100)}%")

        video_id = response["id"]
        youtube_url = f"https://youtu.be/{video_id}"
        print(f"   ✅ Saved as draft: {youtube_url} (go to YouTube Studio to review & publish)")
        return youtube_url

    def _save_metadata(
        self, video_path: Path, title: str, description: str, tags: list
    ) -> str:
        """Save video metadata when upload is not possible"""
        metadata = {
            "title": title,
            "description": description,
            "tags": tags,
            "video_path": str(video_path),
            "status": "ready_to_upload",
        }
        meta_path = Path("outputs") / f"{video_path.stem}_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"   💾 Metadata saved: {meta_path}")
        return f"local://{video_path}"
