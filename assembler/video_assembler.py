"""
Video Assembler - Combines images + audio into final YouTube Shorts video
Uses MoviePy (free) - Static images with subtitles
Output: 1080x1920 vertical video (9:16 for Shorts/Reels)
"""

import os
import subprocess
from pathlib import Path

import numpy as np
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    concatenate_videoclips,
)
from PIL import Image


OUTPUT_DIR = Path("outputs")
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 24
FONT = "DejaVu-Sans-Bold"


class VideoAssembler:
    def __init__(self):
        self.video_dir = OUTPUT_DIR / "videos"
        self.video_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = OUTPUT_DIR / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def assemble(
        self,
        script: dict,
        images: list,
        audio_files: list,
        color_theme: str,
        video_id: str,
    ) -> Path:
        """Assemble all scenes into final video"""

        clips = []

        for i, scene in enumerate(script["scenes"]):
            if i >= len(images) or i >= len(audio_files):
                break

            # Convert MP3 to WAV for better MoviePy compatibility
            audio_path = self._convert_to_wav(audio_files[i], video_id, i)

            clip = self._build_scene_clip(
                scene=scene,
                image_path=images[i],
                audio_path=audio_path,
                color_theme=color_theme,
                scene_index=i,
            )
            clips.append(clip)
            print(f"   🎞️ Scene {scene['id']}: Built ({clip.duration:.1f}s)")

        # Concatenate all scenes
        final_video = concatenate_videoclips(clips, method="compose")

        # Export
        output_path = self.video_dir / f"{video_id}_final.mp4"
        final_video.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="fast",
            threads=2,
            logger=None,
        )

        for clip in clips:
            clip.close()
        final_video.close()

        return output_path

    def _convert_to_wav(self, mp3_path: Path, video_id: str, index: int) -> Path:
        """Convert MP3 to WAV using ffmpeg for better compatibility"""
        wav_path = self.temp_dir / f"{video_id}_scene_{index}.wav"
        if not wav_path.exists():
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(mp3_path),
                    "-ar", "44100", "-ac", "2",
                    str(wav_path)
                ], capture_output=True, check=True)
            except Exception as e:
                print(f"   ⚠️ WAV conversion failed: {e}, using MP3 directly")
                return mp3_path
        return wav_path

    def _build_scene_clip(
        self,
        scene: dict,
        image_path: Path,
        audio_path: Path,
        color_theme: str,
        scene_index: int,
    ) -> CompositeVideoClip:
        """Build a single scene clip"""

        # Load audio to get duration
        audio_clip = AudioFileClip(str(audio_path))
        duration = audio_clip.duration

        # Load image
        img_clip = self._create_image_clip(image_path=image_path, duration=duration)

        layers = [img_clip]

        # Fact number badge
        if scene.get("type") == "fact":
            try:
                badge = self._create_fact_badge(
                    number=scene.get("fact_number", 1),
                    color_theme=color_theme,
                    duration=duration,
                )
                layers.append(badge)
            except Exception as e:
                print(f"   ⚠️ Badge failed: {e}")

        # Subtitle
        try:
            subtitle = self._create_subtitle(
                text=scene.get("narration", ""),
                duration=duration,
                color_theme=color_theme,
            )
            layers.append(subtitle)
        except Exception as e:
            print(f"   ⚠️ Subtitle failed: {e}")

        composite = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
        composite = composite.set_audio(audio_clip)
        composite = composite.set_duration(duration)

        return composite

    def _create_image_clip(self, image_path: Path, duration: float) -> ImageClip:
        """Create static image clip"""
        img = Image.open(str(image_path)).convert("RGB")
        img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
        img_array = np.array(img)
        return ImageClip(img_array).set_duration(duration).set_position("center")

    def _create_fact_badge(self, number: int, color_theme: str, duration: float) -> TextClip:
        """Create a numbered badge"""
        badge = TextClip(
            txt=f"#{number}",
            fontsize=90,
            color="white",
            font=FONT,
            stroke_color="black",
            stroke_width=3,
            method="label",
        )
        return badge.set_position((60, 120)).set_duration(duration)

    def _create_subtitle(self, text: str, duration: float, color_theme: str) -> CompositeVideoClip:
        """Create subtitle bar at bottom"""

        bar_height = 260
        bar = ColorClip(
            size=(VIDEO_WIDTH, bar_height),
            color=(0, 0, 0),
        ).set_opacity(0.70).set_duration(duration)
        bar = bar.set_position(("center", VIDEO_HEIGHT - bar_height))

        # Wrap text
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > 32:
                lines.append(" ".join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
        wrapped_text = "\n".join(lines[:3])

        txt_clip = TextClip(
            txt=wrapped_text,
            fontsize=50,
            color="white",
            font=FONT,
            stroke_color="black",
            stroke_width=2,
            method="caption",
            size=(VIDEO_WIDTH - 80, None),
            align="center",
        )
        txt_y = VIDEO_HEIGHT - bar_height + 15
        txt_clip = txt_clip.set_position(("center", txt_y)).set_duration(duration)

        return CompositeVideoClip([bar, txt_clip], size=(VIDEO_WIDTH, VIDEO_HEIGHT))
