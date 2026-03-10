"""
Voice Agent - Generates voiceover using Edge-TTS
100% FREE - Microsoft Edge Text-to-Speech
pip install edge-tts
"""

import asyncio
from pathlib import Path
import edge_tts


OUTPUT_DIR = Path("outputs")

# Available free voices (Microsoft Edge TTS)
VOICES = {
    "en-IN-NeerjaNeural": "Indian English Female - energetic",
    "en-US-AriaNeural": "US English Female - warm",
    "en-US-GuyNeural": "US English Male - clear",
    "en-GB-SoniaNeural": "British English Female - crisp",
    "en-AU-NatashaNeural": "Australian English Female - friendly",
}


class VoiceAgent:
    def __init__(self):
        self.audio_dir = OUTPUT_DIR / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    async def generate_audio(
        self, scenes: list, voice: str, video_id: str
    ) -> list:
        """Generate audio for each scene"""

        tasks = [
            self._generate_scene_audio(
                scene=scene,
                voice=voice,
                video_id=video_id,
            )
            for scene in scenes
        ]

        audio_files = await asyncio.gather(*tasks)
        return list(audio_files)

    async def _generate_scene_audio(
        self, scene: dict, voice: str, video_id: str
    ) -> Path:
        """Generate audio for a single scene"""

        text = scene.get("narration", "")
        scene_id = scene.get("id", 0)

        audio_path = self.audio_dir / f"{video_id}_scene_{scene_id}.mp3"

        if audio_path.exists():
            return audio_path

        # Add SSML-like pauses for natural pacing
        text_with_pauses = self._add_emphasis(text, scene.get("type", "fact"))

        communicate = edge_tts.Communicate(
            text=text_with_pauses,
            voice=voice,
            rate="+15%",   # Slightly faster for Shorts energy
            pitch="+0Hz",
            volume="+0%",
        )

        await communicate.save(str(audio_path))
        print(f"   🎙️ Scene {scene_id}: Audio generated")
        return audio_path

    def _add_emphasis(self, text: str, scene_type: str) -> str:
        """Add pacing and emphasis to narration"""

        if scene_type == "intro":
            # Slower, dramatic opening
            return text

        elif scene_type == "outro":
            return text

        elif scene_type == "fact":
            # Add slight pause before the fact number
            text = text.replace("Number one!", "Number one!...")
            text = text.replace("Number two!", "Number two!...")
            text = text.replace("Number three!", "Number three!...")

        return text

    async def get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds"""
        try:
            import mutagen.mp3
            audio = mutagen.mp3.MP3(str(audio_path))
            return audio.info.length
        except Exception:
            # Estimate: ~150 words per minute
            return 8.0
