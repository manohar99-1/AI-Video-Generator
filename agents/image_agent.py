"""
Image Agent - Fetches high quality real images using Pexels API
100% FREE - Get free API key at https://www.pexels.com/api/
Professional HD stock photos - much better than AI generation
"""

import asyncio
import hashlib
import os
from pathlib import Path

import aiohttp
import aiofiles
from PIL import Image
import io

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
OUTPUT_DIR = Path("outputs")

# YouTube Shorts dimensions (9:16 vertical)
TARGET_W = 1080
TARGET_H = 1920

# Fallback search terms if scene-specific search fails
NICHE_FALLBACKS = {
    "health_food": ["healthy food", "vegetables", "nutrition", "wellness", "organic food"],
    "psychology":  ["human brain", "mind psychology", "thinking person", "mental health", "neuroscience"],
    "tech_ai":     ["artificial intelligence", "technology", "computer", "robot", "digital future"],
}


class ImageAgent:
    def __init__(self):
        self.cache_dir = OUTPUT_DIR / "image_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not PEXELS_API_KEY:
            print("   ⚠️ PEXELS_API_KEY not set! Add it to GitHub Secrets.")
            print("   Get free key at: https://www.pexels.com/api/")

    async def generate_images(
        self, scenes: list, character_style: str, video_id: str
    ) -> list:
        """Fetch one real image per scene"""

        # Extract niche from character_style for fallback
        niche = "health_food"
        if "brain" in character_style.lower():
            niche = "psychology"
        elif "robot" in character_style.lower():
            niche = "tech_ai"

        images = []
        used_ids = set()  # avoid duplicate images across scenes

        for i, scene in enumerate(scenes):
            print(f"   🖼️ Scene {scene['id']}: Fetching image ({i+1}/{len(scenes)})...")
            try:
                img_path = await self._fetch_image(
                    scene=scene,
                    niche=niche,
                    used_ids=used_ids,
                    index=i,
                )
                images.append(img_path)
                print(f"   ✅ Scene {scene['id']}: Image ready!")
            except Exception as e:
                print(f"   ⚠️ Scene {scene['id']} failed: {e}")
                images.append(self._get_placeholder_path(i))

            await asyncio.sleep(0.5)  # small polite delay

        return images

    async def _fetch_image(
        self, scene: dict, niche: str, used_ids: set, index: int
    ) -> Path:
        """Search Pexels and download best matching image"""

        # Build search query from scene's image prompt
        raw_prompt = scene.get("image_prompt", "")
        query = self._prompt_to_search_query(raw_prompt, niche)

        # Cache key based on query + index to avoid reuse
        cache_key = hashlib.md5(f"{query}_{index}".encode()).hexdigest()[:12]
        cache_path = self.cache_dir / f"{cache_key}.jpg"

        if cache_path.exists():
            print(f"   📦 Scene {scene['id']}: Using cached image")
            return cache_path

        # Try main query, then fallbacks
        queries_to_try = [query] + NICHE_FALLBACKS.get(niche, ["nature"])

        for q in queries_to_try:
            photo_url = await self._search_pexels(q, used_ids)
            if photo_url:
                success = await self._download_and_process(photo_url, cache_path)
                if success:
                    return cache_path

        raise Exception(f"No image found for scene {scene['id']}")

    async def _search_pexels(self, query: str, used_ids: set) -> str | None:
        """Search Pexels API and return best photo URL"""

        if not PEXELS_API_KEY:
            return None

        headers = {"Authorization": PEXELS_API_KEY}
        params = {
            "query": query,
            "orientation": "portrait",   # vertical for Shorts
            "size": "large",
            "per_page": 15,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.pexels.com/v1/search",
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        return None

                    data = await resp.json()
                    photos = data.get("photos", [])

                    # Pick first photo not already used
                    for photo in photos:
                        if photo["id"] not in used_ids:
                            used_ids.add(photo["id"])
                            # Use large2x for best quality
                            return photo["src"].get("large2x") or photo["src"]["large"]

        except Exception as e:
            print(f"   ⚠️ Pexels search failed for '{query}': {e}")

        return None

    async def _download_and_process(self, url: str, save_path: Path) -> bool:
        """Download image and resize to 9:16 vertical format"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        return False
                    content = await resp.read()

            # Process image
            img = Image.open(io.BytesIO(content)).convert("RGB")
            img = self._crop_to_vertical(img)
            img.save(save_path, "JPEG", quality=95)
            return True

        except Exception as e:
            print(f"   ⚠️ Download failed: {e}")
            return False

    def _crop_to_vertical(self, img: Image.Image) -> Image.Image:
        """Smart crop image to 1080x1920 (9:16) vertical format"""
        target_ratio = TARGET_W / TARGET_H  # 0.5625
        img_ratio = img.width / img.height

        if img_ratio > target_ratio:
            # Image is wider — crop sides
            new_w = int(img.height * target_ratio)
            left = (img.width - new_w) // 2
            img = img.crop((left, 0, left + new_w, img.height))
        else:
            # Image is taller — crop top/bottom (keep center)
            new_h = int(img.width / target_ratio)
            top = (img.height - new_h) // 3  # slightly above center looks better
            img = img.crop((0, top, img.width, top + new_h))

        return img.resize((TARGET_W, TARGET_H), Image.LANCZOS)

    def _prompt_to_search_query(self, prompt: str, niche: str) -> str:
        """Convert AI image prompt to a clean Pexels search query"""

        # Remove style words that don't help with stock photo search
        remove_words = [
            "3d", "render", "pixar", "cartoon", "animation", "cinematic",
            "lighting", "vibrant", "sharp", "8k", "studio", "background",
            "cute", "character", "big eyes", "expressive", "dramatic",
            "floating", "explosion", "effect", "pose", "style", "number",
            "golden", "colorful", "confetti", "cheerful", "waving", "thumbs"
        ]

        words = prompt.lower().split()
        clean_words = [w for w in words if w not in remove_words and len(w) > 2]

        # Take first 4 meaningful words
        query = " ".join(clean_words[:4]).strip()

        # Fallback if query is too short
        if len(query) < 5:
            fallbacks = NICHE_FALLBACKS.get(niche, ["nature health"])
            query = fallbacks[0]

        return query

    def _get_placeholder_path(self, index: int) -> Path:
        """Colored placeholder as last resort"""
        placeholder = self.cache_dir / f"placeholder_{index}.jpg"
        if not placeholder.exists():
            try:
                colors = [(45, 122, 45), (106, 13, 173), (10, 116, 218), (212, 56, 13), (199, 124, 0)]
                img = Image.new("RGB", (TARGET_W, TARGET_H), colors[index % len(colors)])
                img.save(placeholder, "JPEG")
            except Exception:
                pass
        return placeholder
