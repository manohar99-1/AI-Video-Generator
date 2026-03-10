"""
Script Agent - Writes full video script with scenes for each fact
Uses OpenRouter free models
"""

import json
import os
import aiohttp


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
FREE_MODEL = "meta-llama/llama-3.1-8b-instruct:free"


class ScriptAgent:
    async def write_script(self, topic: str, hook: str, niche: str) -> dict:
        """Write a full 5-scene video script"""

        if OPENROUTER_API_KEY:
            try:
                script = await self._fetch_from_ai(topic, hook, niche)
                if script and self._validate_script(script):
                    return script
            except Exception as e:
                print(f"   ⚠️ Script AI failed: {e}, using template")

        return self._template_script(topic, hook, niche)

    async def _fetch_from_ai(self, topic: str, hook: str, niche: str) -> dict:
        prompt = f"""Write a YouTube Shorts video script for: "{topic}"
Opening hook: "{hook}"

Rules:
- Exactly 5 scenes (intro + 3 facts + outro)
- Each scene: 1-2 short punchy sentences (max 20 words each)
- Total duration: 45-55 seconds
- Energetic, surprising tone
- End with call to action: "Follow for more!"

Respond ONLY with valid JSON (no markdown):
{{
  "title": "video title for YouTube (max 60 chars)",
  "description": "YouTube description (2-3 sentences + hashtags)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "estimated_duration": 50,
  "scenes": [
    {{
      "id": 1,
      "type": "intro",
      "narration": "Hook text spoken by narrator",
      "image_prompt": "detailed prompt for AI image generation",
      "duration": 8
    }},
    {{
      "id": 2,
      "type": "fact",
      "fact_number": 1,
      "narration": "Fact 1 narration text",
      "image_prompt": "detailed prompt for this fact's image",
      "duration": 10
    }},
    {{
      "id": 3,
      "type": "fact",
      "fact_number": 2,
      "narration": "Fact 2 narration text",
      "image_prompt": "detailed prompt for this fact's image",
      "duration": 10
    }},
    {{
      "id": 4,
      "type": "fact",
      "fact_number": 3,
      "narration": "Fact 3 narration text",
      "image_prompt": "detailed prompt for this fact's image",
      "duration": 10
    }},
    {{
      "id": 5,
      "type": "outro",
      "narration": "Follow for more amazing facts!",
      "image_prompt": "celebratory cartoon character waving goodbye, Pixar style",
      "duration": 7
    }}
  ]
}}"""

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ai-video-generator",
        }

        payload = {
            "model": FREE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1200,
            "temperature": 0.8,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(OPENROUTER_URL, headers=headers, json=payload) as resp:
                data = await resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                content = content.replace("```json", "").replace("```", "").strip()
                # Find JSON boundaries
                start = content.find("{")
                end = content.rfind("}") + 1
                return json.loads(content[start:end])

    def _validate_script(self, script: dict) -> bool:
        required = ["title", "scenes", "estimated_duration"]
        return all(k in script for k in required) and len(script["scenes"]) >= 4

    def _template_script(self, topic: str, hook: str, niche: str) -> dict:
        """Fallback template when AI is unavailable"""
        # Extract subject from topic for image prompts
        subject_map = {
            "health_food": "cute 3D cartoon vegetable character with big expressive eyes, Pixar style, kitchen background",
            "psychology": "cute 3D cartoon brain character with big eyes, thinking pose, Pixar style",
            "tech_ai": "cute 3D cartoon robot character with glowing eyes, futuristic lab background, Pixar style",
        }
        char = subject_map.get(niche, subject_map["health_food"])

        return {
            "title": topic[:60],
            "description": f"{topic}. Watch till the end for the most shocking fact! #Shorts #Facts #{niche.replace('_', '').title()}",
            "tags": ["shorts", "facts", "health", "viral", "trending"],
            "estimated_duration": 50,
            "scenes": [
                {
                    "id": 1,
                    "type": "intro",
                    "narration": hook,
                    "image_prompt": f"{char}, surprised expression, holding up hands, dramatic lighting, 8K",
                    "duration": 8,
                },
                {
                    "id": 2,
                    "type": "fact",
                    "fact_number": 1,
                    "narration": f"Number one! This is the first shocking fact about {topic.lower()}. You will not believe this!",
                    "image_prompt": f"{char}, pointing finger, excited expression, number 1 floating text, golden background",
                    "duration": 10,
                },
                {
                    "id": 3,
                    "type": "fact",
                    "fact_number": 2,
                    "narration": f"Number two! Here is the second amazing fact. Scientists confirmed this recently!",
                    "image_prompt": f"{char}, wide eyes, jaw dropped, number 2 floating, science lab background",
                    "duration": 10,
                },
                {
                    "id": 4,
                    "type": "fact",
                    "fact_number": 3,
                    "narration": f"Number three! This last fact will completely change how you see {topic.lower()}!",
                    "image_prompt": f"{char}, mind blown expression, explosion effect behind, number 3 floating, dramatic lighting",
                    "duration": 10,
                },
                {
                    "id": 5,
                    "type": "outro",
                    "narration": "Follow for more amazing facts every day! Don't forget to like and share!",
                    "image_prompt": f"{char}, waving happily, thumbs up, colorful confetti background, cheerful expression",
                    "duration": 7,
                },
            ],
        }
