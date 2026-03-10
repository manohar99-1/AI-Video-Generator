"""
Video Assembler - Combines images + audio into final YouTube Shorts video
Uses MoviePy (free) with Ken Burns zoom/pan animations
Output: 1080x1920 vertical video (9:16 for Shorts/Reels)
"""

import os
from pathlib import Path

import numpy as np
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)
from PIL import Image, ImageFilter


OUTPUT_DIR = Path("outputs")
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30
FONT = "DejaVu-Sans-Bold"  # Available on Ubuntu (GitHub Actions)


class VideoAssembler:
    def __init__(self):
        self.video_dir = OUTPUT_DIR / "videos"
        self.video_dir.mkdir(parents=True, exist_ok=True)

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

            clip = self._build_scene_clip(
                scene=scene,
                image_path=images[i],
                audio_path=audio_files[i],
                color_theme=color_theme,
                scene_index=i,
            )
            clips.append(clip)
            print(f"   🎞️ Scene {scene['id']}: Built ({clip.duration:.1f}s)")

        # Concatenate all scenes
        final_video = concatenate_videoclips(clips, method="compose")

        # Add background music (optional - silent track if no music)
        # final_video = self._add_background_music(final_video)

        # Export
        output_path = self.video_dir / f"{video_id}_final.mp4"
        final_video.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="fast",
            threads=4,
            logger=None,  # Suppress verbose output
        )

        # Cleanup clips
        for clip in clips:
            clip.close()
        final_video.close()

        return output_path

    def _build_scene_clip(
        self,
        scene: dict,
        image_path: Path,
        audio_path: Path,
        color_theme: str,
        scene_index: int,
    ) -> CompositeVideoClip:
        """Build a single scene clip with Ken Burns animation"""

        # Load audio to get duration
        audio_clip = AudioFileClip(str(audio_path))
        duration = audio_clip.duration + 0.3  # small buffer

        # Load and prepare image
        img_clip = self._create_animated_image(
            image_path=image_path,
            duration=duration,
            animation_type=scene_index % 3,  # rotate between zoom types
        )

        # Add overlay elements
        layers = [img_clip]

        # Fact number badge (for fact scenes)
        if scene.get("type") == "fact":
            badge = self._create_fact_badge(
                number=scene.get("fact_number", 1),
                color_theme=color_theme,
                duration=duration,
            )
            layers.append(badge)

        # Subtitle text
        subtitle = self._create_subtitle(
            text=scene.get("narration", ""),
            duration=duration,
            color_theme=color_theme,
        )
        layers.append(subtitle)

        # Compose all layers
        composite = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
        composite = composite.set_audio(audio_clip)
        composite = composite.set_duration(duration)

        return composite

    def _create_animated_image(
        self, image_path: Path, duration: float, animation_type: int
    ) -> ImageClip:
        """Create Ken Burns zoom/pan effect on image"""

        # Load and resize image to fill frame
        img = Image.open(str(image_path)).convert("RGB")
        img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
        img_array = np.array(img)

        base_clip = ImageClip(img_array).set_duration(duration)

        # Apply zoom animation based on type
        zoom_factor = 1.05  # 5% zoom

        if animation_type == 0:
            # Slow zoom in
            def zoom_in(t):
                scale = 1 + (zoom_factor - 1) * (t / duration)
                return scale
            clip = base_clip.resize(zoom_in)

        elif animation_type == 1:
            # Slow zoom out
            def zoom_out(t):
                scale = zoom_factor - (zoom_factor - 1) * (t / duration)
                return scale
            clip = base_clip.resize(zoom_out)

        else:
            # Pan right
            clip = base_clip

        return clip.set_position("center")

    def _create_fact_badge(
        self, number: int, color_theme: str, duration: float
    ) -> TextClip:
        """Create a numbered badge (top-left corner)"""

        badge = TextClip(
            txt=f"#{number}",
            fontsize=90,
            color="white",
            font=FONT,
            stroke_color=color_theme,
            stroke_width=4,
            method="label",
        )
        badge = badge.set_position((60, 120)).set_duration(duration)
        return badge

    def _create_subtitle(
        self, text: str, duration: float, color_theme: str
    ) -> CompositeVideoClip:
        """Create subtitle bar at bottom of video"""

        # Background bar
        bar_height = 280
        bar = ColorClip(
            size=(VIDEO_WIDTH, bar_height),
            color=(0, 0, 0),
        ).set_opacity(0.72).set_duration(duration)
        bar = bar.set_position(("center", VIDEO_HEIGHT - bar_height))

        # Wrap text
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > 30:
                lines.append(" ".join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
        wrapped_text = "\n".join(lines[:3])  # max 3 lines

        # Text
        txt_clip = TextClip(
            txt=wrapped_text,
            fontsize=52,
            color="white",
            font=FONT,
            stroke_color="black",
            stroke_width=2,
            method="caption",
            size=(VIDEO_WIDTH - 80, None),
            align="center",
        )
        txt_y = VIDEO_HEIGHT - bar_height + 20
        txt_clip = txt_clip.set_position(("center", txt_y)).set_duration(duration)

        return CompositeVideoClip([bar, txt_clip], size=(VIDEO_WIDTH, VIDEO_HEIGHT))
