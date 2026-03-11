"""
Image Agent - Generates cartoon images using Hugging Face FLUX.1
Best free quality available - requires free HF_TOKEN
Model: black-forest-labs/FLUX.1-schnell (fast, free, high quality)
Get free token at: https://huggingface.co/settings/tokens
"""

import asyncio
import hashlib
import io
import os
from pathlib import Path

import aiohttp
from PIL import Image

HF_TOKEN = os.getenv("HF_TOKEN")
OUTPUT_DIR = Path("outputs")

# Best free models on HuggingFace (in order of quality)
MODELS = [
    "black-forest-labs/FLUX.1-schnell",   # Best quality, fast
    "stabilityai/stable-diffusion-xl-base-1.0",  # Fallback
]

# YouTube Shorts dimensions (9:16)
IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1024  # HF generates square, we'll crop/pad to 9:16

STYLE_SUFFIX = (
    ", 3D render, Pixar animation style, cinematic lighting, "
    "vibrant colors, sharp details, professional studio lighting, "
    "clean colorful background, high quality, 8K"
)

NEGATIVE_PROMPT = (
    "realistic photo, blurry, watermark, text, ugly, "
    "deformed, noisy, low quality, dark, gloomy"
)


class ImageAgent:
    def __init__(self):
        self.cache_dir = OUTPUT_DIR / "image_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not HF_TOKEN:
            print("   ⚠️ HF_TOKEN not set! Add it to GitHub Secrets.")
            print("   Get free token at: https://huggingface.co/settings/tokens")

    async def generate_images(
        self, scenes: list, character_style: str, video_id: str
    ) -> list:
        """Generate one image per scene sequentially"""

        images = []
        for i, scene in enumerate(scenes):
            print(f"   🎨 Scene {scene['id']}: Generating image ({i+1}/{len(scenes)})...")
            try:
                img_path = await self._generate_single(
                    scene=scene,
                    character_style=character_style,
                    video_id=video_id,
                )
                images.append(img_path)
                print(f"   ✅ Scene {scene['id']}: Image saved!")
            except Exception as e:
                print(f"   ⚠️ Scene {scene['id']} failed: {e}")
                images.append(self._get_placeholder_path(i))

            # Wait between requests to avoid rate limiting
            if i < len(scenes) - 1:
                await asyncio.sleep(5)

        return images

    async def _generate_single(
        self, scene: dict, character_style: str, video_id: str
    ) -> Path:
        """Generate image for a single scene using HF API"""

        base_prompt = scene.get("image_prompt", "cute cartoon character")
        full_prompt = f"{character_style}, {base_prompt}{STYLE_SUFFIX}"

        # Check cache first
        cache_key = hashlib.md5(full_prompt.encode()).hexdigest()[:12]
        cache_path = self.cache_dir / f"{cache_key}.jpg"

        if cache_path.exists():
            print(f"   📦 Scene {scene['id']}: Using cached image")
            return cache_path

        # Try each model
        for model in MODELS:
            try:
                image_bytes = await self._call_hf_api(full_prompt, model)
                if image_bytes:
                    # Process and save image
                    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                    # Resize to 9:16 by padding
                    img = self._resize_to_vertical(img)
                    img.save(cache_path, "JPEG", quality=95)
                    return cache_path
            except Exception as e:
                print(f"   ⚠️ Model {model} failed: {e}")
                await asyncio.sleep(3)
                continue

        raise Exception(f"All models failed for scene {scene['id']}")

    async def _call_hf_api(self, prompt: str, model: str) -> bytes:
        """Call Hugging Face Inference API"""

        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": NEGATIVE_PROMPT,
                "width": IMAGE_WIDTH,
                "height": IMAGE_HEIGHT,
                "num_inference_steps": 4,   # FLUX.1-schnell works great at 4 steps
                "guidance_scale": 0.0,       # FLUX.1-schnell doesn't use guidance
            },
            "options": {
                "wait_for_model": True,       # Wait if model is loading
                "use_cache": False,
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
                elif resp.status == 503:
                    # Model loading, wait and retry
                    print(f"   ⏳ Model loading, waiting 20s...")
                    await asyncio.sleep(20)
                    raise Exception("Model loading")
                else:
                    text = await resp.text()
                    raise Exception(f"HTTP {resp.status}: {text[:100]}")

    def _resize_to_vertical(self, img: Image.Image) -> Image.Image:
        """Resize square image to 1080x1920 vertical format"""
        target_w, target_h = 1080, 1920

        # Scale image to fit width
        scale = target_w / img.width
        new_h = int(img.height * scale)
        img = img.resize((target_w, new_h), Image.LANCZOS)

        # Pad top and bottom to reach target height
        result = Image.new("RGB", (target_w, target_h), (20, 20, 20))
        paste_y = (target_h - new_h) // 2
        result.paste(img, (0, paste_y))
        return result

    def _get_placeholder_path(self, index: int) -> Path:
        """Return colored placeholder if generation fails"""
        placeholder = self.cache_dir / f"placeholder_{index}.jpg"
        if not placeholder.exists():
            try:
                colors = [(45, 122, 45), (106, 13, 173), (10, 116, 218), (212, 56, 13), (199, 124, 0)]
                color = colors[index % len(colors)]
                img = Image.new("RGB", (1080, 1920), color)
                img.save(placeholder, "JPEG")
            except Exception:
                pass
        return placeholder
