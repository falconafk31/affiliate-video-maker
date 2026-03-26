# 🎬 Affiliate Video Maker

> **Automated AI-powered affiliate marketing video generator** — AI generates an Indonesian voiceover from your hook script and merges it with your raw video clip in one click.

![Tech Stack](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)
![Vue.js](https://img.shields.io/badge/Frontend-Vue.js%203-4FC08D?logo=vue.js)
![AI](https://img.shields.io/badge/AI-Pollinations%20AI-FF6B35)
![License](https://img.shields.io/badge/License-MIT-blue)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI Hook Generator** | Auto-generate Indonesian TikTok & Shopee affiliate hooks from a product name |
| 🎙️ **AI Voiceover** | Powered by Pollinations AI — no additional TTS service needed |
| 🎬 **Video Merge** | MoviePy + FFmpeg: strips original audio, adds AI voice, renders MP4 |
| 🔁 **Smart Duration Sync** | 3 modes: Auto (smart), Loop Video, Trim Audio |
| 📥 **Drag & Drop Upload** | Simple .mp4 upload with file validation |
| 🌙 **Dark UI** | Modern glassmorphism design with Tailwind CSS |
| 🛠️ **MCP Server** | Exposes `generate_ai_voice` & `merge_video_and_voice` as MCP tools |

---

## 🚀 Tech Stack

### Backend
- **FastAPI** — REST API server
- **MoviePy** — Video processing (FFmpeg backend)
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

Open **http://localhost:5173** in your browser.

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check + API key status |
| `GET` | `/api/debug` | Full diagnostics (FFmpeg, MoviePy, Pollinations connectivity) |
| `POST` | `/api/process-video` | Main endpoint — processes video + generates voiceover |

### POST `/api/process-video`

**Form Data:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `video` | File (.mp4) | ✅ | — | Raw video clip |
| `prompt_text` | string | ✅ | — | Voiceover script (Indonesian recommended) |
| `voice_model` | string | ❌ | `nova` | Pollinations voice: `nova`, `shimmer`, `alloy`, `echo`, `fable`, `onyx` |
| `duration_mode` | string | ❌ | `auto` | `auto` / `loop_video` / `trim_audio` |

**Response:** Binary MP4 file (`video/mp4`)

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
