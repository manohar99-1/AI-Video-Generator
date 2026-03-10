"""
Image Agent - Generates cartoon images using Pollinations.AI
100% FREE - No API key required!
https://pollinations.ai
"""

import asyncio
import hashlib
import urllib.parse
from pathlib import Path
import aiohttp
import aiofiles


OUTPUT_DIR = Path("outputs")
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"

# Image settings for YouTube Shorts (9:16 vertical)
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920

# Style suffix added to every prompt for consistent cartoon look
STYLE_SUFFIX = (
    ", 3D render, Pixar animation style, cinematic lighting, "
    "vibrant colors, sharp details, 8K resolution, "
    "professional studio lighting, clean background"
)

# Negative aspects to avoid (encoded in prompt)
NEGATIVE_SUFFIX = " white background, realistic photography, blurry, watermark"


class ImageAgent:
    def __init__(self):
        self.cache_dir = OUTPUT_DIR / "image_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def generate_images(
        self, scenes: list, character_style: str, video_id: str
    ) -> list:
        """Generate one image per scene concurrently"""

        tasks = [
            self._generate_single(
                scene=scene,
                character_style=character_style,
                video_id=video_id,
            )
            for scene in scenes
        ]

        # Run all image generations concurrently
        images = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failures
        valid_images = []
        for i, img in enumerate(images):
            if isinstance(img, Exception):
                print(f"   ⚠️ Scene {i+1} image failed: {img}")
                # Use placeholder
                valid_images.append(self._get_placeholder_path(i))
            else:
                valid_images.append(img)

        return valid_images

    async def _generate_single(
        self, scene: dict, character_style: str, video_id: str
    ) -> Path:
        """Generate image for a single scene"""

        # Build full prompt
        base_prompt = scene.get("image_prompt", "cute cartoon character")
        full_prompt = f"{character_style}, {base_prompt}{STYLE_SUFFIX}"

        # Check cache first
        cache_key = hashlib.md5(full_prompt.encode()).hexdigest()[:12]
        cache_path = self.cache_dir / f"{cache_key}.jpg"

        if cache_path.exists():
            print(f"   📦 Scene {scene['id']}: Using cached image")
            return cache_path

        # Build Pollinations URL
        encoded_prompt = urllib.parse.quote(full_prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={IMAGE_WIDTH}&height={IMAGE_HEIGHT}"
            f"&model=flux&enhance=true&nologo=true"
            f"&seed={scene['id'] * 42}"
        )

        print(f"   🎨 Scene {scene['id']}: Generating image...")

        # Download with retries
        for attempt in range(3):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            async with aiofiles.open(cache_path, "wb") as f:
                                await f.write(content)
                            print(f"   ✅ Scene {scene['id']}: Image saved ({len(content)//1024}KB)")
                            return cache_path
                        else:
                            print(f"   ⚠️ Scene {scene['id']}: HTTP {resp.status}, retry {attempt+1}")
            except Exception as e:
                print(f"   ⚠️ Scene {scene['id']}: Error {e}, retry {attempt+1}")
                await asyncio.sleep(2 ** attempt)  # exponential backoff

        # All retries failed
        raise Exception(f"Failed to generate image for scene {scene['id']}")

    def _get_placeholder_path(self, index: int) -> Path:
        """Return a solid color placeholder if image generation fails"""
        placeholder = self.cache_dir / f"placeholder_{index}.jpg"
        if not placeholder.exists():
            # Create a minimal valid JPEG placeholder
            try:
                from PIL import Image, ImageDraw
                colors = ["#2d7a2d", "#6a0dad", "#0a74da", "#d4380d", "#c77c00"]
                color = colors[index % len(colors)]
                img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), color)
                draw = ImageDraw.Draw(img)
                draw.text(
                    (IMAGE_WIDTH // 2, IMAGE_HEIGHT // 2),
                    f"Scene {index + 1}",
                    fill="white",
                )
                img.save(placeholder, "JPEG")
            except Exception:
                pass
        return placeholder
