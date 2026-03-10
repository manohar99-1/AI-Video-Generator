"""
Supabase Client - Tracks video generation status
Reuses your existing Supabase project from autonomous-book-publisher
"""

import json
import os
import uuid
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://itrbhknfusfacxlwcmbq.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

# SQL to create table (run once in Supabase dashboard):
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    niche TEXT,
    topic TEXT,
    status TEXT DEFAULT 'pending',
    script JSONB,
    video_path TEXT,
    youtube_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""


class SupabaseClient:
    def __init__(self):
        self.client = None
        self.local_log = []  # Fallback if Supabase not available

        if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
                print("   ✅ Supabase connected")
            except Exception as e:
                print(f"   ⚠️ Supabase failed: {e}, using local log")

    def create_video_record(self, niche: str, topic: str, status: str) -> str:
        """Create a new video record and return its ID"""
        video_id = str(uuid.uuid4())[:8]

        record = {
            "id": video_id,
            "niche": niche,
            "topic": topic,
            "status": status,
            "created_at": datetime.utcnow().isoformat(),
        }

        if self.client:
            try:
                self.client.table("videos").insert(record).execute()
            except Exception as e:
                print(f"   ⚠️ DB insert failed: {e}")

        self.local_log.append(record)
        return video_id

    def update_video(self, video_id: str, **kwargs) -> None:
        """Update video record fields"""
        kwargs["updated_at"] = datetime.utcnow().isoformat()

        if self.client:
            try:
                self.client.table("videos").update(kwargs).eq("id", video_id).execute()
            except Exception as e:
                print(f"   ⚠️ DB update failed: {e}")

        # Update local log
        for record in self.local_log:
            if record["id"] == video_id:
                record.update(kwargs)

    def get_video(self, video_id: str) -> dict:
        """Get video record by ID"""
        if self.client:
            try:
                result = (
                    self.client.table("videos")
                    .select("*")
                    .eq("id", video_id)
                    .single()
                    .execute()
                )
                return result.data
            except Exception:
                pass

        # Fallback to local
        for record in self.local_log:
            if record["id"] == video_id:
                return record
        return {}
