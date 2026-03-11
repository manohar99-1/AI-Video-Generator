"""
Voice Agent - Generates voiceover using gTTS (Google Text-to-Speech)
100% FREE - Works on GitHub Actions
pip install gtts
"""

import asyncio
from pathlib import Path
from gtts import gTTS


OUTPUT_DIR = Path("outputs")

VOICE_CONFIG = {
    "en-IN-NeerjaNeural": {"lang": "en", "tld": "co.in"},   # Indian English
    "en-US-AriaNeural":   {"lang": "en", "tld": "com"},      # US English
    "en-US-GuyNeural":    {"lang": "en", "tld": "com"},      # US English
    "en-GB-SoniaNeural":  {"lang": "en", "tld": "co.uk"},    # British English
    "en-AU-NatashaNeural":{"lang": "en", "tld": "com.au"},   # Australian English
}


class VoiceAgent:
    def __init__(self):
        self.audio_dir = OUTPUT_DIR / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    async def generate_audio(self, scenes: list, voice: str, video_id: str) -> list:
        """Generate audio for each scene"""
        audio_files = []
        config = VOICE_CONFIG.get(voice, {"lang": "en", "tld": "com"})

        for scene in scenes:
            audio_path = await self._generate_scene_audio(
                scene=scene,
                config=config,
                video_id=video_id,
            )
            audio_files.append(audio_path)
            await asyncio.sleep(1)  # small delay between requests

        return audio_files

    async def _generate_scene_audio(self, scene: dict, config: dict, video_id: str) -> Path:
        """Generate audio for a single scene using gTTS"""

        text = scene.get("narration", "")
        scene_id = scene.get("id", 0)
        audio_path = self.audio_dir / f"{video_id}_scene_{scene_id}.mp3"

        if audio_path.exists():
            return audio_path

        # Run gTTS in thread pool (it's synchronous)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._save_audio,
            text,
            config,
            audio_path,
        )

        print(f"   🎙️ Scene {scene_id}: Audio generated")
        return audio_path

    def _save_audio(self, text: str, config: dict, path: Path):
        """Synchronous gTTS save"""
        tts = gTTS(
            text=text,
            lang=config["lang"],
            tld=config["tld"],
            slow=False,
        )
        tts.save(str(path))

    async def get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file"""
        try:
            import mutagen.mp3
            audio = mutagen.mp3.MP3(str(audio_path))
            return audio.info.length
        except Exception:
            return 8.0
