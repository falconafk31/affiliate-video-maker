# 🎬 Affiliate Video Maker (Retro 8-Bit Edition)

> **Automated AI-powered affiliate marketing video generator** — AI generates an Indonesian voiceover from your hook script and merges it with your raw video clip in one click. Features a lightning-fast native FFmpeg backend and a highly optimized **Modern 8-Bit Retro UI (Cyan/Magenta)** theme.

![Tech Stack](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)
![Vue.js](https://img.shields.io/badge/Frontend-Vue.js%203-4FC08D?logo=vue.js)
![AI](https://img.shields.io/badge/AI-Pollinations%20AI-FF6B35)
![License](https://img.shields.io/badge/License-MIT-blue)

---
## ✨ Screenshoot
1. https://plain-apac-prod-public.komododecks.com/202606/03/8rScV1onp4G5E4TcbNSo/image.png
2. https://plain-apac-prod-public.komododecks.com/202606/03/Mnhsace7aVaV4rbbXaFn/image.png
3. https://plain-apac-prod-public.komododecks.com/202606/03/KBmWJouY4w80l58adWsB/image.png
---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI Hook Generator** | Auto-generate Indonesian TikTok & Shopee affiliate hooks from a product name |
| 🎙️ **Dual AI Voiceover** | **Edge-TTS** (natural Indonesian female Gadis voice) + **Pollinations GPT-Audio** (`openai-audio` model with optimized indonesian affiliate narrator prompt) |
| 🎬 **Native FFmpeg Merge** | 10x faster and RAM-efficient raw FFmpeg backend rendering (completely replaced heavy MoviePy) |
| ⚡ **Extreme Performance** | Lazy-loaded Vue Router, Mobile-optimized touch UI, and GZIP payload compression |
| 🎨 **Retro 8-Bit UI** | Beautiful, lightweight Cyberpunk/Retro pixel UI without heavy CSS blur filters (60 FPS scrolling) |
| 🔄 **Cache-Busting** | Timestamps appended to URLs to prevent browser from playing cached/old voice files when regenerating |
| 🕒 **7-Day Video Log** | Rendered videos are saved and accessible via the UI for 7 days (auto-delete) |
| 📊 **Log Prompt UI** | View generation history, play/download rendered videos, and see exact edited scripts |
| 🔁 **Smart Duration Sync** | 3 modes: Auto (smart loop), Loop Video, Trim Audio |
| 🛠️ **MCP Server** | Exposes `generate_ai_voice` & `merge_video_and_voice` as MCP tools |

---

## 🚀 Tech Stack

### Backend
- **FastAPI** — REST API server (with GZipMiddleware)
- **FFmpeg (Subprocess)** — Raw native video processing (Ultra-fast & RAM-efficient)
- **Pollinations AI** — AI voiceover generation (no API cost for basic use; API key for credits)
- **Python-dotenv** — Environment configuration

### Frontend
- **Vue.js 3** (Composition API)
- **Vite** — Build tool
- **Tailwind CSS** — Styling
- **Axios** — HTTP client

---

## 📁 Project Structure

```
affiliate-video-maker/
├── .gitignore
├── README.md
├── ecosystem.config.js          ← PM2 deployment config
├── backend/
│   ├── .env                     ← GITIGNORED — copy from .env.example
│   ├── .env.example
│   ├── main.py                  ← FastAPI app (POST /api/process-video)
│   ├── mcp_server.py            ← MCP tools server
│   ├── requirements.txt
│   └── temp_processing/         ← GITIGNORED — auto-created at runtime
└── frontend/
    ├── .env                     ← VITE_API_BASE_URL config
    ├── index.html
    ├── package.json
    ├── tailwind.config.js
    ├── vite.config.js
    └── src/
        ├── main.js
        ├── style.css
        ├── App.vue
        └── components/
            └── VideoEditor.vue  ← Main UI component
```

---

## ⚙️ Local Development Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- **FFmpeg** installed and available in PATH → [Download](https://ffmpeg.org/download.html)
- Pollinations AI API key → [Get key](https://enter.pollinations.ai)

### 1. Backend Setup

```bash
cd affiliate-video-maker/backend

# Copy environment file
cp .env.example .env

# Edit .env — add your API key
# POLLINATIONS_API_URL=https://gen.pollinations.ai
# POLLINATIONS_API_KEY=sk_xxxxxxxxxxxxxxxx

# Install dependencies
pip install -r requirements.txt

# Start development server
python -m uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd affiliate-video-maker/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Open **http://localhost:5173** in your browser. (Note: Backend must be running on port 8000).

---

## 🕒 Video Retention Policy

Rendered videos are saved in `backend/static/videos/`. To keep the server storage clean:
*   Videos are kept for **7 days**.
*   A background task `clean_old_videos` automatically deletes files older than 7 days.
*   Log entries in the UI will show a "-" placeholder if the physical video file has been deleted.

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check + API status |
| `GET` | `/api/logs` | Fetch hook generation history with video URLs |
| `POST` | `/api/generate-hook` | Generate AI script + save to CSV log |
| `POST` | `/api/process-video` | Render video + attach to existing log ID |

### POST `/api/process-video`

**Form Data:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `video` | File (.mp4) | ✅ | — | Raw video clip |
| `prompt_text` | string | ✅ | — | Voiceover script |
| `log_id` | string | ❌ | — | UUID from generation log (links video to history and updates edited scripts) |
| `voice_model` | string | ❌ | `id-ID-GadisNeural` | `id-ID-GadisNeural` (Edge-TTS) or `openai-audio:shimmer`/`nova`/`alloy`/`onyx`/`echo`/`fable` (GPT Audio via Pollinations) |
| `duration_mode` | string | ❌ | `auto` | `auto` / `loop_video` / `trim_audio` |

**Response:** JSON format `{ "status": "success", "video_url": "/api/videos/{log_id}.mp4", "log_id": log_id }` or binary based on mode.

---

## 🛠️ MCP Server

Exposes two tools for AI agent integration:

```python
# Tool 1: Generate AI voice
generate_ai_voice(prompt: str, voice: str = "nova") -> str  # returns MP3 path

# Tool 2: Merge video and voice
merge_video_and_voice(video_path: str, audio_path: str) -> str  # returns MP4 path
```

Run the MCP server:
```bash
cd backend
python mcp_server.py
```

---

## 🤖 Auto Hook Generator

The frontend includes a built-in hook script generator. Just type a **product name** and select a platform:

### TikTok Hooks (4 variations)
- 🔥 **Viral Impulsif** — High energy, FOMO-driven
- 😱 **Shock & Reveal** — Curiosity/surprise angle
- 💬 **Cerita Personal** — Authentic testimonial style
- ⚡ **FOMO Urgency** — Scarcity + time pressure

### Shopee Hooks (4 variations)
- 🛒 **Flash Sale** — Discount-focused
- ⭐ **Review Jujur** — Honest review with voucher CTA
- 🎁 **Bundle Deal** — Buy-more-save-more angle
- 💎 **Premium Value** — Quality justification

---

## 🔄 Duration Sync Modes

| Mode | Behavior | Best For |
|---|---|---|
| 🧠 **Auto (Smart)** | Loop video if audio > video; trim video if video > audio | General use |
| 🔁 **Loop Video** | Always loop video to fill full audio duration | Short clips + long script |
| ✂️ **Trim Audio** | Clip audio to video length | Fixed-length video content |

---

## 🚀 VPS Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for full VPS + PM2 setup guide.

---

## 🔐 Environment Variables

### Backend (`backend/.env`)

```env
POLLINATIONS_API_URL=https://gen.pollinations.ai
POLLINATIONS_API_KEY=sk_xxxxxxxxxxxxxxxx
```

### Frontend (`frontend/.env`)

```env
VITE_API_BASE_URL=https://your-domain.com
```

---

## 📝 License

MIT — free to use and modify.
