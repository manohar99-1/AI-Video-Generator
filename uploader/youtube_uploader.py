"""
YouTube Uploader - Uploads video to YouTube using Data API v3
FREE - 10,000 units/day quota
Setup: Create OAuth2 credentials in Google Cloud Console
"""

import json
import os
import pickle
import aiohttp
import asyncio
from pathlib import Path

# Google API client
try:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = "config/youtube_token.pickle"
CREDENTIALS_PATH = "config/youtube_credentials.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


class YouTubeUploader:
    def __init__(self):
        self.service = None
        if GOOGLE_AVAILABLE:
            self._init_service()

    def _init_service(self):
        creds = None
        if os.path.exists(TOKEN_PATH):
            with open(TOKEN_PATH, "rb") as token:
                creds = pickle.load(token)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif not creds or not creds.valid:
            if not os.path.exists(CREDENTIALS_PATH):
                print("   ⚠️ YouTube credentials not found. Skipping upload.")
                return
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        Path(TOKEN_PATH).parent.mkdir(exist_ok=True)
        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)

        self.service = build("youtube", "v3", credentials=creds)

    def upload(self, video_path: Path, title: str, description: str, tags: list) -> str:
        """Upload video to YouTube as a private draft"""

        if not self.service:
            print("   ⚠️ YouTube service not initialized. Saving metadata only.")
            return self._save_metadata(video_path, title, description, tags)

        print(f"   📤 Uploading: {title}")

        title = f"{title} #Shorts"[:100]
        description = f"{description}\n\n#Shorts #Facts #Viral"

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags + ["Shorts", "Facts", "Viral"],
                "categoryId": "22",
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": "private",  # Saved as draft — publish manually
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True, chunksize=1024*1024)
        request = self.service.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"   📊 Upload progress: {int(status.progress() * 100)}%")

        video_id = response["id"]
        youtube_url = f"https://youtu.be/{video_id}"
        studio_url = f"https://studio.youtube.com/video/{video_id}/edit"

        print(f"   ✅ Saved as draft: {youtube_url}")

        # Send Telegram notification
        import nest_asyncio; nest_asyncio.apply(); asyncio.get_event_loop().run_until_complete(self._notify_telegram(title=title, youtube_url=youtube_url, studio_url=studio_url))

        return youtube_url

    async def _notify_telegram(self, title: str, youtube_url: str, studio_url: str):
        """Send Telegram message with buttons when draft is ready"""

        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("   ⚠️ Telegram not configured, skipping notification")
            return

        message = (
            f"🎬 *New Video Draft Ready!*\n\n"
            f"📌 *Title:* {title}\n\n"
            f"👀 *Preview:* {youtube_url}\n\n"
            f"✏️ *Edit & Publish:*\n{studio_url}\n\n"
            f"_Open YouTube Studio app → tap Content → find your draft → publish when ready!_"
        )

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "✏️ Edit in Studio", "url": studio_url},
                    {"text": "👀 Preview", "url": youtube_url},
                ]]
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        print("   📱 Telegram notification sent!")
                    else:
                        print(f"   ⚠️ Telegram failed: HTTP {resp.status}")
        except Exception as e:
            print(f"   ⚠️ Telegram error: {e}")

    def _save_metadata(self, video_path: Path, title: str, description: str, tags: list) -> str:
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
