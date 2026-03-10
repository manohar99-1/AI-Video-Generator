# 🎬 AI Video Generator

Automatically generates cartoon-style YouTube Shorts & Instagram Reels.
**100% FREE tools** — runs on GitHub Actions.

## 🎯 What It Does

```
Trending Topic → AI Script → Cartoon Images → Voiceover → Video → YouTube Upload
```

**Output:** 45-55 second vertical video (1080x1920) with:
- AI-generated cartoon character images (Pollinations.AI)
- Professional voiceover (Microsoft Edge TTS)
- Animated subtitles
- Ken Burns zoom effects
- Auto-uploaded to YouTube as a Short

---

## 🆓 Free Tools Used

| Tool | What For | Cost |
|------|----------|------|
| Pollinations.AI | AI cartoon images | FREE forever |
| Edge-TTS (Microsoft) | Voiceover | FREE forever |
| MoviePy + FFmpeg | Video assembly | FREE forever |
| OpenRouter | Script writing | FREE (llama-3.1-8b) |
| GitHub Actions | Automation | FREE (2000 min/month) |
| YouTube Data API | Upload | FREE (10k units/day) |

---

## ⚡ Quick Setup (5 Steps)

### Step 1: Fork & Clone
```bash
git clone https://github.com/YOUR_USERNAME/ai-video-generator
cd ai-video-generator
```

### Step 2: Add GitHub Secrets
Go to your repo → **Settings** → **Secrets and variables** → **Actions**

Add these secrets:

| Secret | Where to get | Required? |
|--------|-------------|-----------|
| `OPENROUTER_API_KEY` | https://openrouter.ai (free signup) | Optional |
| `SUPABASE_URL` | Your Supabase project URL | Optional |
| `SUPABASE_ANON_KEY` | Your Supabase anon key | Optional |
| `YOUTUBE_CREDENTIALS` | Google Cloud Console (see below) | For upload |
| `YOUTUBE_TOKEN` | Generated once locally (see below) | For upload |

### Step 3: Setup YouTube API (One Time)

1. Go to https://console.cloud.google.com
2. Create a new project
3. Enable **YouTube Data API v3**
4. Create **OAuth 2.0 credentials** (Desktop app)
5. Download `credentials.json`
6. Run locally once to authorize:

```bash
pip install -r requirements.txt
python setup_youtube_auth.py
```

7. Copy the generated token to GitHub Secrets

### Step 4: Setup Supabase Table
Run this SQL in your Supabase dashboard:

```sql
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    niche TEXT,
    topic TEXT,
    status TEXT DEFAULT 'pending',
    script JSONB,
    video_path TEXT,
    youtube_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Step 5: Run It!

**Manual trigger:**
1. Go to **Actions** tab in your GitHub repo
2. Click **AI Video Generator**
3. Click **Run workflow**
4. Select niche → Click **Run workflow**

**Automatic:** Runs every Monday, Wednesday, Friday at 9AM IST

---

## 📁 Project Structure

```
ai-video-generator/
├── main.py                    # Orchestrator
├── agents/
│   ├── topic_agent.py         # Picks trending topics
│   ├── script_agent.py        # Writes video script
│   ├── image_agent.py         # Generates cartoon images (Pollinations.AI)
│   └── voice_agent.py         # Text-to-speech (Edge-TTS)
├── assembler/
│   └── video_assembler.py     # Combines into final video (MoviePy)
├── uploader/
│   └── youtube_uploader.py    # Uploads to YouTube
├── database/
│   └── supabase_client.py     # Tracks generation status
├── .github/workflows/
│   └── generate_video.yml     # GitHub Actions automation
└── requirements.txt
```

---

## 🎨 Supported Niches

| Niche | Examples | Voice |
|-------|---------|-------|
| `health_food` | "5 Vegetables That Destroy Belly Fat" | Indian English |
| `psychology` | "5 Dark Psychology Tricks" | US English Female |
| `tech_ai` | "5 AI Tools Replacing Jobs" | US English Male |

---

## 📊 Expected Output

- **Video length:** 45-55 seconds
- **Resolution:** 1080x1920 (9:16 vertical)
- **File size:** ~20-40MB
- **Generation time:** ~5-10 minutes on GitHub Actions

---

## 💡 Tips for More Views

1. Post **3x per week** consistently
2. First 3 seconds = most important (hook!)
3. Add trending hashtags in description
4. Reply to every comment in first hour
5. Cross-post to Instagram Reels & TikTok

---

## 🔧 Local Testing

```bash
pip install -r requirements.txt
python main.py health_food
```

Video will be saved to `outputs/videos/`
