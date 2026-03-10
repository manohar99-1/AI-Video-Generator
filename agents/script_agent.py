"""
Topic Agent - Finds trending topics using OpenRouter (free models)
"""

import json
import os
import random
import aiohttp


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
FREE_MODEL = "meta-llama/llama-3.1-8b-instruct:free"

# Fallback topic pools if API fails
FALLBACK_TOPICS = {
    "health_food": [
        {"title": "5 Vegetables That Destroy Belly Fat", "hook": "These 5 vegetables are literally fat destroyers!"},
        {"title": "What Happens If You Eat Garlic Every Day", "hook": "Doctors don't want you to know this about garlic!"},
        {"title": "5 Foods That Clean Your Arteries Naturally", "hook": "Your arteries are getting clogged right now — unless you eat these!"},
        {"title": "The Fruit That Kills Cancer Cells", "hook": "Scientists discovered this fruit fights cancer — and it's in your kitchen!"},
        {"title": "5 Seeds That Control Blood Sugar", "hook": "Diabetics swear by these 5 tiny seeds!"},
    ],
    "psychology": [
        {"title": "5 Dark Psychology Tricks Used On You Daily", "hook": "You are being manipulated right now and you don't even know it!"},
        {"title": "Why Your Brain Lies To You", "hook": "Your own brain is your biggest enemy — here's proof!"},
        {"title": "5 Signs Someone Is Secretly Jealous Of You", "hook": "That 'friend' might secretly hate your success!"},
        {"title": "The Science Of Why You Procrastinate", "hook": "You're not lazy — your brain is broken in this specific way!"},
        {"title": "5 Body Language Signs Someone Is Lying", "hook": "Spot a liar in 10 seconds using these body language tricks!"},
    ],
    "tech_ai": [
        {"title": "5 AI Tools That Are Replacing Human Jobs", "hook": "Millions of jobs are disappearing because of these 5 AI tools!"},
        {"title": "What GPT-5 Can Actually Do", "hook": "GPT-5 just broke every record — here's what it can REALLY do!"},
        {"title": "5 Free AI Tools You Don't Know About", "hook": "These 5 free AI tools will make you 10x more productive!"},
        {"title": "How AI Is Reading Your Emotions Right Now", "hook": "AI can tell you're scared before YOU even know it!"},
        {"title": "5 Things AI Still Cannot Do", "hook": "AI is taking over — but here are 5 things it will NEVER replace!"},
    ],
}


class TopicAgent:
    async def get_trending_topic(self, niche_prompt: str) -> dict:
        """Get a trending topic using AI or fallback to curated list"""

        # Try OpenRouter first
        if OPENROUTER_API_KEY:
            try:
                topic = await self._fetch_from_ai(niche_prompt)
                if topic:
                    return topic
            except Exception as e:
                print(f"   ⚠️ OpenRouter failed: {e}, using fallback topics")

        # Fallback: pick from curated list
        niche_key = self._detect_niche(niche_prompt)
        topics = FALLBACK_TOPICS.get(niche_key, FALLBACK_TOPICS["health_food"])
        return random.choice(topics)

    async def _fetch_from_ai(self, niche_prompt: str) -> dict:
        prompt = f"""Generate 1 viral YouTube Shorts topic about: {niche_prompt}

Rules:
- Title must be clickbait but truthful (max 60 chars)
- Hook must grab attention in first 3 seconds
- Format must work for 45-60 second short video
- Must be about facts/tips (numbered list format like "5 things...")

Respond ONLY with valid JSON, no markdown, no explanation:
{{"title": "5 Foods That Destroy Belly Fat", "hook": "These 5 foods are literally fat killers!"}}"""

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ai-video-generator",
        }

        payload = {
            "model": FREE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": 0.9,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(OPENROUTER_URL, headers=headers, json=payload) as resp:
                data = await resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                # Clean JSON
                content = content.replace("```json", "").replace("```", "").strip()
                return json.loads(content)

    def _detect_niche(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["food", "health", "vegetable", "diet"]):
            return "health_food"
        elif any(w in prompt_lower for w in ["psychology", "mind", "brain"]):
            return "psychology"
        elif any(w in prompt_lower for w in ["tech", "ai", "technology"]):
            return "tech_ai"
        return "health_food"
