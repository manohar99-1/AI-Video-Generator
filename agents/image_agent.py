"""
Image Agent - Fetches high quality real images using Pexels API
Uses narration text + topic keywords for accurate image matching
"""

import asyncio
import hashlib
import io
import os
from pathlib import Path

import aiohttp
from PIL import Image

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
OUTPUT_DIR = Path("outputs")

TARGET_W = 1080
TARGET_H = 1920

# Topic-specific keyword maps for better image matching
TOPIC_KEYWORDS = {
    # Health/Food
    "garlic": "garlic cloves food",
    "turmeric": "turmeric spice golden",
    "ginger": "ginger root spice",
    "spinach": "spinach leaves green",
    "broccoli": "broccoli vegetable healthy",
    "lemon": "lemon citrus fruit",
    "avocado": "avocado fruit healthy",
    "banana": "banana fruit yellow",
    "blood sugar": "blood sugar test diabetes",
    "heart": "heart health cardiology",
    "artery": "heart artery health",
    "brain": "human brain neuroscience",
    "cancer": "cancer research medicine",
    "gut": "gut health digestion",
    "liver": "liver health organ",
    "kidney": "kidney health organ",
    "immune": "immune system health",
    "inflammation": "inflammation health medical",
    "cholesterol": "cholesterol heart health",
    "fat": "belly fat weight loss",
    "sleep": "sleep rest healthy",
    "stress": "stress anxiety mental health",
    "exercise": "exercise workout fitness",
    "water": "drinking water hydration",
    "vitamin": "vitamins supplements health",
    # Psychology
    "psychology": "psychology mind thinking",
    "manipulation": "psychology influence people",
    "jealous": "jealousy envy emotion",
    "lying": "lie deception body language",
    "confidence": "confidence success mindset",
    "procrastinat": "procrastination lazy thinking",
    "habit": "habits routine daily life",
    "memory": "memory brain recall",
    # Tech/AI
    "ai": "artificial intelligence technology",
    "robot": "robot technology future",
    "chatgpt": "AI chatbot computer",
    "job": "job career work automation",
    "technology": "technology digital innovation",
    "data": "data technology digital",
    "computer": "computer technology coding",
}

# Scene type to visual concept mapping
SCENE_TYPE_VISUALS = {
    "intro": "dramatic reveal spotlight",
    "outro": "success celebration achievement",
    "fact": "discovery research science",
}


class ImageAgent:
    def __init__(self):
        self.cache_dir = OUTPUT_DIR / "image_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not PEXELS_API_KEY:
            print("   ⚠️ PEXELS_API_KEY not set!")

    async def generate_images(
        self, scenes: list, character_style: str, video_id: str
    ) -> list:
        """Fetch one perfectly matched image per scene"""

        niche = self._detect_niche(character_style)
        images = []
        used_ids = set()

        for i, scene in enumerate(scenes):
            print(f"   🖼️ Scene {scene['id']}: Fetching image ({i+1}/{len(scenes)})...")
            try:
                img_path = await self._fetch_best_image(
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

            await asyncio.sleep(0.5)

        return images

    async def _fetch_best_image(
        self, scene: dict, niche: str, used_ids: set, index: int
    ) -> Path:
        """Generate smart query and fetch best matching image"""

        # Build multiple queries from most to least specific
        queries = self._build_queries(scene, niche)

        cache_key = hashlib.md5(f"{queries[0]}_{index}".encode()).hexdigest()[:12]
        cache_path = self.cache_dir / f"{cache_key}.jpg"

        if cache_path.exists():
            print(f"   📦 Scene {scene['id']}: Using cached image")
            return cache_path

        for query in queries:
            print(f"   🔍 Searching: '{query}'")
            photo_url = await self._search_pexels(query, used_ids)
            if photo_url:
                success = await self._download_and_process(photo_url, cache_path)
                if success:
                    return cache_path

        raise Exception(f"No image found for scene {scene['id']}")

    def _build_queries(self, scene: dict, niche: str) -> list:
        """Build ordered list of search queries from most to least specific"""

        narration = scene.get("narration", "").lower()
        scene_type = scene.get("type", "fact")
        queries = []

        # Query 1: Extract key topic from narration text
        topic_query = self._extract_topic_from_narration(narration, niche)
        if topic_query:
            queries.append(topic_query)

        # Query 2: Niche + scene type
        niche_queries = {
            "health_food": {
                "intro": "healthy food nutrition colorful",
                "fact": "health food medicine science",
                "outro": "healthy lifestyle wellness",
            },
            "psychology": {
                "intro": "human mind psychology thinking",
                "fact": "brain psychology behavior",
                "outro": "mental clarity success mindset",
            },
            "tech_ai": {
                "intro": "artificial intelligence future technology",
                "fact": "technology innovation digital",
                "outro": "technology success future",
            },
        }
        fallback = niche_queries.get(niche, {}).get(scene_type, "")
        if fallback:
            queries.append(fallback)

        # Query 3: Generic niche fallback
        generic = {
            "health_food": "healthy food vegetables nutrition",
            "psychology": "human psychology mind",
            "tech_ai": "technology artificial intelligence",
        }
        queries.append(generic.get(niche, "knowledge facts education"))

        return queries

    def _extract_topic_from_narration(self, narration: str, niche: str) -> str:
        """Extract the most relevant search query from narration text"""

        # Check topic keyword map
        for keyword, search_query in TOPIC_KEYWORDS.items():
            if keyword in narration:
                return search_query

        # Extract meaningful nouns from narration
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "are", "was", "were",
            "this", "that", "these", "those", "you", "your", "our", "will",
            "can", "number", "one", "two", "three", "fact", "here", "last",
            "first", "second", "third", "completely", "recently", "amazing",
            "shocking", "scientists", "confirmed", "change", "see", "know",
            "follow", "more", "every", "day", "like", "share", "dont",
        }

        words = narration.lower().split()
        meaningful = [
            w.strip(".,!?") for w in words
            if w.strip(".,!?") not in stop_words
            and len(w.strip(".,!?")) > 3
        ]

        if len(meaningful) >= 2:
            return " ".join(meaningful[:3])

        return ""

    async def _search_pexels(self, query: str, used_ids: set) -> str | None:
        """Search Pexels API"""
        if not PEXELS_API_KEY:
            return None

        headers = {"Authorization": PEXELS_API_KEY}
        params = {
            "query": query,
            "orientation": "portrait",
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
                    for photo in photos:
                        if photo["id"] not in used_ids:
                            used_ids.add(photo["id"])
                            return photo["src"].get("large2x") or photo["src"]["large"]
        except Exception as e:
            print(f"   ⚠️ Pexels error: {e}")

        return None

    async def _download_and_process(self, url: str, save_path: Path) -> bool:
        """Download and crop image to 9:16"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status != 200:
                        return False
                    content = await resp.read()

            img = Image.open(io.BytesIO(content)).convert("RGB")
            img = self._crop_to_vertical(img)
            img.save(save_path, "JPEG", quality=95)
            return True
        except Exception as e:
            print(f"   ⚠️ Download failed: {e}")
            return False

    def _crop_to_vertical(self, img: Image.Image) -> Image.Image:
        """Smart crop to 1080x1920"""
        target_ratio = TARGET_W / TARGET_H
        img_ratio = img.width / img.height

        if img_ratio > target_ratio:
            new_w = int(img.height * target_ratio)
            left = (img.width - new_w) // 2
            img = img.crop((left, 0, left + new_w, img.height))
        else:
            new_h = int(img.width / target_ratio)
            top = (img.height - new_h) // 3
            img = img.crop((0, top, img.width, top + new_h))

        return img.resize((TARGET_W, TARGET_H), Image.LANCZOS)

    def _detect_niche(self, character_style: str) -> str:
        style = character_style.lower()
        if "brain" in style:
            return "psychology"
        elif "robot" in style:
            return "tech_ai"
        return "health_food"

    def _get_placeholder_path(self, index: int) -> Path:
        placeholder = self.cache_dir / f"placeholder_{index}.jpg"
        if not placeholder.exists():
            try:
                colors = [(45, 122, 45), (106, 13, 173), (10, 116, 218), (212, 56, 13), (199, 124, 0)]
                img = Image.new("RGB", (TARGET_W, TARGET_H), colors[index % len(colors)])
                img.save(placeholder, "JPEG")
            except Exception:
                pass
        return placeholder
