# 🎬 Affiliate Video Maker (Retro 8-Bit Edition)

> **Automated AI-powered affiliate marketing video generator** — AI generates an Indonesian voiceover from your hook script and merges it with your raw video clip in one click. Features a lightning-fast native FFmpeg backend and a highly optimized **Modern 8-Bit Retro UI (Cyan/Magenta)** theme.

![Tech Stack](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)
![Vue.js](https://img.shields.io/badge/Frontend-Vue.js%203-4FC08D?logo=vue.js)
![AI](https://img.shields.io/badge/AI-Pollinations%20AI-FF6B35)
![License](https://img.shields.io/badge/License-MIT-blue)

📖 **Dokumentasi lain:** [CHANGELOG.md](./CHANGELOG.md) · [ROADMAP.md](./ROADMAP.md) · [LAPORAN_ANALISIS.md](./LAPORAN_ANALISIS.md) · [DEPLOYMENT.md](./DEPLOYMENT.md) · [DOCKER_INSTRUCTIONS.md](./DOCKER_INSTRUCTIONS.md)

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
| 🔥 **Auto Subtitle Burn-in** | Caption gaya TikTok otomatis dari skrip — bisa **AKTIF / NONAKTIF** per render; timing mengikuti voiceover (akurat via word-boundary Edge-TTS); file `.srt` bisa diunduh dari Logs |
| 🎨 **Custom Subtitle Style** | Atur ukuran font, warna teks, warna & tebal outline, posisi (atas/tengah/bawah), dan HURUF KAPITAL — langsung dari editor |
| 🔤 **Custom Font Import** | Upload font format standar **TTF / OTF / TTC** (maks 5 MB) untuk dipakai di subtitle — tanpa instalasi ke sistem |
| 🎙️ **Dual AI Voiceover** | **Edge-TTS** (natural Indonesian female Gadis voice) + **Pollinations GPT-Audio** (`openai-audio` model with optimized indonesian affiliate narrator prompt) |
| 🎬 **Native FFmpeg Merge** | 10x faster and RAM-efficient raw FFmpeg backend rendering (completely replaced heavy MoviePy) |
| ⚡ **Extreme Performance** | Lazy-loaded Vue Router, Mobile-optimized touch UI, and GZIP payload compression |
| 🎨 **Retro 8-Bit UI** | Beautiful, lightweight Cyberpunk/Retro pixel UI without heavy CSS blur filters (60 FPS scrolling) |
| 🔄 **Cache-Busting** | Timestamps appended to URLs to prevent browser from playing cached/old voice files when regenerating |
| 🕒 **7-Day Media Retention** | Rendered videos/audios/subtitles disimpan & bisa diakses dari UI selama 7 hari (auto-delete); Video Library 30 hari; Font custom sampai dihapus manual |
| 📊 **Log Prompt UI** | View generation history, play/download rendered videos + SRT, and see exact edited scripts |
| 🔁 **Smart Duration Sync** | 3 modes: Auto (smart loop), Loop Video, Trim Audio |
| 🛠️ **MCP Server** | Exposes `generate_ai_voice` & `merge_video_and_voice` as MCP tools |

---

## 🚀 Tech Stack

### Backend
- **FastAPI** — REST API server (with GZipMiddleware)
- **FFmpeg (Subprocess)** — Raw native video processing + libass subtitle burn-in (Ultra-fast & RAM-efficient)
- **Pollinations AI** — AI voiceover generation (no API cost for basic use; API key for credits)
- **Edge-TTS** — Voiceover Indonesia gratis dengan word-boundary timing (untuk subtitle akurat)
- **FontTools** — Pembaca nama family file font standar (TTF/OTF/TTC)
- **Security** — PyJWT for Token Auth & bcrypt for Hash checking
- **Python-dotenv** — Environment configuration

### Frontend
- **Vue.js 3** (Composition API)
- **Vite** — Build tool (+ dev proxy `/api` → backend)
- **Vue Router** — Routing with Keep-Alive state persistence
- **Tailwind CSS** — Styling
- **Axios** — HTTP client (with global interceptors)

---

## 📁 Project Structure

```
affiliate-video-maker/
├── .gitignore
├── README.md
├── CHANGELOG.md                 ← Riwayat perubahan
├── ROADMAP.md                   ← Rencana pengembangan
├── LAPORAN_ANALISIS.md          ← Analisis kode & saran perbaikan
├── docker-compose.yml           ← Docker deployment orchestration
├── DOCKER_INSTRUCTIONS.md       ← Docker deployment guide
├── backend/
│   ├── .env                     ← GITIGNORED — Holds JWT Secret & Password Hash
│   ├── .env.example
│   ├── main.py                  ← FastAPI app, Auth, Render, Subtitle & Font
│   ├── mcp_server.py            ← MCP tools (generate_ai_voice & merge_video_and_voice)
│   ├── generate_hash.py         ← Script to generate bcrypt password hash
│   ├── requirements.txt
│   ├── test_subtitles.py        ← Unit test pipeline subtitle burn-in
│   ├── test_api_e2e.py          ← E2E offline job pipeline (TTS di-stub)
│   ├── logs/
│   │   ├── hook_logs.csv        ← CSV database for generated hooks
│   │   ├── login_logs.csv       ← CSV database for authentication attempts
│   │   ├── video_library.json   ← Metadata Video Library
│   │   └── fonts.json           ← Metadata Custom Font
│   ├── static/
│   │   ├── videos/              ← Hasil render (retensi 7 hari, auto-delete)
│   │   ├── audios/              ← Voiceover MP3 (retensi 7 hari)
│   │   ├── subs/                ← File subtitle .srt/.ass hasil generate (retensi 7 hari)
│   │   ├── fonts/               ← Custom font upload TTF/OTF/TTC (sampai dihapus manual)
│   │   └── library/             ← Video raw library (retensi 30 hari)
│   └── temp_processing/         ← Auto-created runtime temp folder
└── frontend/
    ├── .env                     ← OPSIONAL — VITE_API_BASE_URL bila backend beda origin
    ├── index.html
    ├── package.json
    ├── tailwind.config.js
    ├── vite.config.js           ← Dev server + proxy /api → backend
    └── src/
        ├── main.js              ← Axios interceptors (JWT) + bootstrap
        ├── style.css
        ├── App.vue
        ├── router/
        │   └── index.js         ← Route definitions & Auth guards
        └── components/
            ├── Login.vue        ← 8-bit retro login page
            ├── VideoEditor.vue  ← Main UI (Editor + Subtitle toggle/style/font)
            ├── VideoLibrary.vue ← Video Library component
            └── LogViewer.vue    ← Logs, Analytics & Security Logs
```

---

## ⚙️ Local Development Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- **FFmpeg** installed and available in PATH (build dengan libass untuk fitur subtitle) → [Download](https://ffmpeg.org/download.html)
- Pollinations AI API key → [Get key](https://enter.pollinations.ai)

### 1. Backend Setup

```bash
cd affiliate-video-maker/backend

# Copy environment file
cp .env.example .env

# Edit backend/.env — add your API key, Hash, and JWT Secret
# See "Environment Variables" section below for details

# Install dependencies
pip install -r requirements.txt

# Start development server (port 9000 — sama dengan VITE_API_PROXY_TARGET default)
python -m uvicorn main:app --reload --port 9000
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

> **Catatan lokal:**
> - Frontend memanggil API secara relatif (`/api/...`) dan Vite otomatis me-*proxy* ke
>   `http://127.0.0.1:9000` (atur env `VITE_API_PROXY_TARGET` bila port backend beda).
>   Bila backend berada di origin lain, set `VITE_API_BASE_URL` di `frontend/.env`.
> - **Mode dev login:** jika `ADMIN_PASSWORD_HASH` dikosongkan, password tidak diperiksa —
>   ketik **apa saja** di halaman login (khusus localhost). Untuk password sungguhan,
>   isi `ADMIN_PASSWORD_HASH` (lihat bawah).

### 3. Menjalankan Test

```bash
cd affiliate-video-maker/backend

# Unit test pipeline subtitle burn-in (offline, butuh FFmpeg)
python test_subtitles.py

# E2E offline job pipeline + custom font/style (TTS di-stub, FFmpeg asli)
python test_api_e2e.py
```

---

## 🔐 Environment Variables (.env)

Buat file `.env` di dalam folder `backend/` dengan format berikut:

```env
POLLINATIONS_API_URL=https://gen.pollinations.ai
POLLINATIONS_API_KEY=sk_xxxxxxxxxxxxxxxx

# Security Configuration
ADMIN_PASSWORD_HASH=$2b$12$......dari-generate_hash.py......
JWT_SECRET=<acak-panjang, mis. hasil openssl rand -hex 32>
```

> **Cara membuat `ADMIN_PASSWORD_HASH`:**
> Jalankan perintah `python backend/generate_hash.py` di terminal lokalmu. Script akan memintamu memasukkan password, lalu mencetak kode hash (seperti `$2b$12$...`) yang bisa langsung kamu *copy-paste* ke file `.env`.
>
> **`ADMIN_PASSWORD_HASH` kosong = mode dev** (login tanpa verifikasi password — hanya untuk localhost).
> **`JWT_SECRET`** jangan pakai nilai contoh di produksi — buat acak: `openssl rand -hex 32`.

### Frontend (`frontend/.env` — opsional)

```env
# Hanya perlu jika backend ada di origin lain (mis. https://api.domain.com)
# Kosongkan/default = same-origin "/api/..." (di-proxy Vite/Nginx)
VITE_API_BASE_URL=
# Target proxy Vite saat dev (default http://127.0.0.1:9000)
VITE_API_PROXY_TARGET=http://127.0.0.1:9000
```

---

## 🔒 Security & Authentication

Aplikasi ini dilengkapi sistem keamanan Single-Admin yang kuat:
1. **Bcrypt Hash**: Password disimpan dalam `.env` (sebagai `ADMIN_PASSWORD_HASH`), jadi password asli tidak pernah bocor. Gunakan `python backend/generate_hash.py` untuk membuat Hash baru.
2. **JWT Guard**: Seluruh API krusial dilindungi oleh *JSON Web Token* middleware.
3. **Anti-Bruteforce**: IP Address akan otomatis diblokir selama 15 menit jika gagal login 5 kali berturut-turut.
4. **Security Logs**: Halaman `LogViewer` mencatat semua aktivitas login (SUKSES/GAGAL/BLOKIR).
5. **Mode Dev**: `ADMIN_PASSWORD_HASH` kosong menonaktifkan verifikasi password — **hanya untuk localhost**, jangan dipakai di produksi.

---

## 🐳 Docker Deployment

Deployment ke VPS kini sangat mudah menggunakan Docker Compose. Sistem ini menjalankan Nginx (untuk frontend) dan Uvicorn (untuk backend) secara terisolasi.

Baca panduan lengkapnya di 👉 **[DOCKER_INSTRUCTIONS.md](./DOCKER_INSTRUCTIONS.md)**

---

## 🕒 Retention Policy

| Media | Lokasi | Retensi |
|---|---|---|
| Video hasil render | `backend/static/videos/` | **7 hari** |
| Audio voiceover | `backend/static/audios/` | **7 hari** |
| Subtitle `.srt` / `.ass` | `backend/static/subs/` | **7 hari** |
| Video Library | `backend/static/library/` | **30 hari** (env `VIDEO_LIBRARY_RETENTION_DAYS`) |
| Custom Font | `backend/static/fonts/` | **Selamanya** (sampai dihapus manual) |

Tugas latar `clean_old_videos` menghapus file yang lewat batas secara otomatis. Entri log yang file medianya sudah dihapus akan menampilkan placeholder `-` di UI.

---

## 🌐 API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | — | Health check + API status |
| `POST` | `/api/login` | — | Login (body: `{password}`) → JWT |
| `POST` | `/api/docs-login` | — | Login OAuth2 untuk Swagger docs |
| `GET` | `/api/auth-logs` | ✅ | Riwayat 100 aktivitas login terakhir |
| `POST` | `/api/generate-hook` | ✅ | Generate AI script + save to CSV log |
| `POST` | `/api/generate-audio` | ✅ | Generate voiceover MP3 saja |
| `POST` | `/api/process-video` | ✅ | Render video sinkron (satu langkah) |
| `POST` | `/api/jobs/submit` | ✅ | Submit render job (async, progress via SSE) |
| `GET` | `/api/jobs/{job_id}/stream` | —* | SSE progress job (status/progress/video_url) |
| `GET` | `/api/logs` | ✅ | Riwayat generate + URL media yang masih ada |
| `GET` | `/api/logs/download` | ✅ | Download `hook_logs.csv` |
| `DELETE` | `/api/logs/clear` | ✅ | Reset semua log |
| `GET` | `/api/library` | ✅ | Daftar video library |
| `POST` | `/api/library/upload` | ✅ | Upload video ke library |
| `DELETE` | `/api/library/{video_id}` | ✅ | Hapus video library |
| `GET` | `/api/fonts` | ✅ | Daftar custom font (subtitle) |
| `POST` | `/api/fonts/upload` | ✅ | Upload custom font (.ttf/.otf/.ttc, maks 5 MB) |
| `DELETE` | `/api/fonts/{font_id}` | ✅ | Hapus custom font |
| `GET` | `/api/videos/{file}` | — | Static: hasil render |
| `GET` | `/api/audios/{file}` | — | Static: voiceover |
| `GET` | `/api/subs/{file}` | — | Static: subtitle `.srt`/`.ass` |
| `GET` | `/api/lib-static/{file}` | — | Static: video library |

\* Stream SSE tidak mengirim header `Authorization` (keterbatasan `EventSource`) — cukup aman karena `job_id` berupa UUID acak.

### POST `/api/process-video` & `/api/jobs/submit`

**Form Data:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `video` | File (.mp4/.mov/.avi) | ✅* | — | Raw video clip |
| `prompt_text` | string | ✅ | — | Voiceover script |
| `log_id` | string | ❌ | — | UUID from generation log (links video to history and updates edited scripts) |
| `voice_model` | string | ❌ | `id-ID-GadisNeural` | `id-ID-GadisNeural` (Edge-TTS) or `openai-audio:shimmer`/`nova`/`alloy`/`onyx`/`echo`/`fable` (GPT Audio via Pollinations) |
| `duration_mode` | string | ❌ | `auto` | `auto` / `loop_video` / `trim_audio` |
| `force_portrait` | string | ❌ | `true` | Crop video ke 9:16 |
| `burn_subtitles` | string | ❌ | `false` | `true` / `false` — burn caption auto-subtitle ke video |
| `subtitle_font_id` | string | ❌ | *(bawaan)* | ID custom font dari `POST /api/fonts/upload`; kosongkan = DejaVu Sans |
| `subtitle_size` | string | ❌ | `md` | `sm` / `md` / `lg` |
| `subtitle_color` | string | ❌ | `white` | `white` `yellow` `cyan` `magenta` `green` `red` `blue` `orange` `black` |
| `subtitle_outline_color` | string | ❌ | `black` | Warna outline (sama seperti di atas) + `none` |
| `subtitle_outline` | string | ❌ | `md` | `thin` / `md` / `thick` |
| `subtitle_position` | string | ❌ | `center` | `top` / `center` / `bottom` |
| `subtitle_caps` | string | ❌ | `false` | `true` = caption HURUF KAPITAL semua |
| `library_video_id` | string | ❌ | — | *(jobs/submit saja)* Pakai video dari Library, tanpa upload |

\* `video` wajib diisi **kecuali** `library_video_id` dipakai (jobs/submit).

**Response:** `{ "status": "success", "video_url": "/api/videos/{id}.mp4", "subtitle_url": "/api/subs/{id}.srt", "log_id": ... }`

---

## 🔥 Auto Subtitle Burn-in & Custom Style

Caption bisa di-burn permanen ke video — **pilihan AKTIF / NONAKTIF** di Step 2 Editor.
Saat AKTIF, panel **🎨 Gaya Caption** terbuka untuk kustomisasi penuh.

| Aspek | Opsi |
|---|---|
| **Font** | DejaVu Sans (bawaan) atau **custom font** hasil upload **`.ttf` / `.otf` / `.ttc`** (maks 5 MB) — nama family dibaca otomatis dari file; dimuat via `fontsdir` FFmpeg, **tanpa instalasi ke sistem**. `.woff/.woff2` (web font) tidak didukung. |
| **Ukuran** | Kecil (4%) / Sedang (5.2%) / Besar (7%) dari tinggi video |
| **Warna teks** | Putih, Kuning, Cyan, Magenta, Hijau, Merah, Biru, Oranye, Hitam |
| **Outline** | Warna (Hitam/Putih/Tanpa) + tebal (Tipis/Sedang/Tebal) |
| **Posisi** | Atas / Tengah (TikTok) / Bawah |
| **Kapital** | Semua huruf besar (gaya caption TikTok) |
| **Timing** | Word-boundary Edge-TTS (akurat per kata) · fallback proporsional untuk GPT-Audio |
| **Resolusi** | Ukuran font/outline/posisi proporsional terhadap dimensi output render |
| **File** | `.srt` (unduh dari Logs) + `.ass` (sidecar ber-style) di `static/subs/` |

> Catatan: file `.srt` standar tidak menyimpan gaya (hanya teks + timing) — gaya penuh
> tersimpan di sidecar `.ass`. Burn-in selalu mengikuti gaya yang dipilih saat render.

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

### TikTok Hooks
- 🔥 **Viral Impulsif** — High energy, FOMO-driven
- 😱 **Shock & Reveal** — Curiosity/surprise angle
- 💬 **Cerita Personal** — Authentic testimonial style
- ⚡ **FOMO Urgency** — Scarcity + time pressure

### Shopee Hooks
- 🛒 **Flash Sale** — Discount-focused
- ⭐ **Review Jujur** — Honest review with voucher CTA
- 🎁 **Bundle Deal** — Buy-more-save-more angle
- 💎 **Premium Value** — Quality justification

### V2 Hooks (universal — untuk kedua platform)
- 🚀 **V2: Problem** — Problem-based, "itu gue banget" dalam 2 detik
- 🚀 **V2: Personal** — Personal experience, terasa cerita teman
- 🚀 **V2: Edukasi** — Insight gratis, bukan terasa diiklani
- 🚀 **V2: Pro-Kontra** — Contra opinion yang bikin berhenti scroll
- 🚀 **V2: Visual Shock** — Reaksi spontan menyaksikan sesuatu

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

## 📈 Roadmap & Changelog

- Rencana pengembangan (fitur berikutnya, perbaikan keamanan, dll.) → **[ROADMAP.md](./ROADMAP.md)**
- Riwayat perubahan rilis → **[CHANGELOG.md](./CHANGELOG.md)**
- Hasil analisis kode lengkap (temuan bug/UX/performa) → **[LAPORAN_ANALISIS.md](./LAPORAN_ANALISIS.md)**

---

## 📝 License

MIT — free to use and modify.
