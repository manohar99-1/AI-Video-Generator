"""
AI Video Generator - Main Orchestrator
Generates cartoon-style YouTube Shorts / Instagram Reels
100% Free Tools: Pollinations.AI + Edge-TTS + MoviePy + YouTube API
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from agents.topic_agent import TopicAgent
from agents.script_agent import ScriptAgent
from agents.image_agent import ImageAgent
from agents.voice_agent import VoiceAgent
from assembler.video_assembler import VideoAssembler
from uploader.youtube_uploader import YouTubeUploader
from database.supabase_client import SupabaseClient

# ── Config ────────────────────────────────────────────────────────────────────
NICHES = ["health_food", "psychology", "tech_ai"]

NICHE_CONFIG = {
    "health_food": {
        "topics_prompt": "viral health food facts YouTube Shorts",
        "character_style": "cute 3D cartoon food character with big eyes, Pixar style",
        "voice": "en-IN-NeerjaNeural",
        "color_theme": "#2d7a2d",
    },
    "psychology": {
        "topics_prompt": "mind-blowing psychology facts YouTube Shorts",
        "character_style": "cute 3D cartoon brain character with big eyes, Pixar style",
        "voice": "en-US-AriaNeural",
        "color_theme": "#6a0dad",
    },
    "tech_ai": {
        "topics_prompt": "shocking AI technology facts YouTube Shorts",
        "character_style": "cute 3D cartoon robot character with big eyes, Pixar style",
        "voice": "en-US-GuyNeural",
        "color_theme": "#0a74da",
    },
}

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


async def generate_video(niche: str = None, topic: str = None):
    """Full pipeline: topic → script → images → voice → video → upload"""

    db = SupabaseClient()
    niche = niche or NICHES[0]
    config = NICHE_CONFIG[niche]

    print(f"\n{'='*60}")
    print(f"🎬 AI VIDEO GENERATOR")
    print(f"Niche: {niche} | Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    # ── Step 1: Pick Topic ─────────────────────────────────────────────────
    print("📌 Step 1/6: Picking trending topic...")
    topic_agent = TopicAgent()
    if not topic:
        topic_data = await topic_agent.get_trending_topic(config["topics_prompt"])
        topic = topic_data["title"]
        hook = topic_data["hook"]
    else:
        hook = f"Did you know? {topic}"

    print(f"   Topic: {topic}")

    # Save to DB
    video_id = db.create_video_record(niche=niche, topic=topic, status="scripting")

    # ── Step 2: Write Script ───────────────────────────────────────────────
    print("\n📝 Step 2/6: Writing script...")
    script_agent = ScriptAgent()
    script = await script_agent.write_script(topic=topic, hook=hook, niche=niche)
    db.update_video(video_id, status="imaging", script=script)
    print(f"   Scenes: {len(script['scenes'])} | Duration: ~{script['estimated_duration']}s")

    # ── Step 3: Generate Images ────────────────────────────────────────────
    print("\n🎨 Step 3/6: Generating AI images (Pollinations.AI)...")
    image_agent = ImageAgent()
    images = await image_agent.generate_images(
        scenes=script["scenes"],
        character_style=config["character_style"],
        video_id=video_id,
    )
    db.update_video(video_id, status="voicing")
    print(f"   Generated: {len(images)} images")

    # ── Step 4: Generate Voiceover ─────────────────────────────────────────
    print("\n🎙️ Step 4/6: Generating voiceover (Edge-TTS)...")
    voice_agent = VoiceAgent()
    audio_files = await voice_agent.generate_audio(
        scenes=script["scenes"],
        voice=config["voice"],
        video_id=video_id,
    )
    print(f"   Generated: {len(audio_files)} audio clips")

    # ── Step 5: Assemble Video ─────────────────────────────────────────────
    print("\n🎬 Step 5/6: Assembling video (MoviePy)...")
    assembler = VideoAssembler()
    video_path = assembler.assemble(
        script=script,
        images=images,
        audio_files=audio_files,
        color_theme=config["color_theme"],
        video_id=video_id,
    )
    db.update_video(video_id, status="uploading", video_path=str(video_path))
    print(f"   Video saved: {video_path}")

    # ── Step 6: Upload to YouTube ──────────────────────────────────────────
    print("\n📤 Step 6/6: Uploading to YouTube...")
    uploader = YouTubeUploader()
    youtube_url = uploader.upload(
        video_path=video_path,
        title=script["title"],
        description=script["description"],
        tags=script["tags"],
    )
    db.update_video(video_id, status="published", youtube_url=youtube_url)

    print(f"\n✅ DONE! Video published: {youtube_url}")
    print(f"{'='*60}\n")

    return {"video_id": video_id, "youtube_url": youtube_url, "topic": topic}


if __name__ == "__main__":
    niche = sys.argv[1] if len(sys.argv) > 1 else "health_food"
    asyncio.run(generate_video(niche=niche))
