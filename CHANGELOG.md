# Changelog

Semua perubahan penting proyek **Affiliate Video Maker** dicatat di file ini.

Format mengacu pada [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

*(Belum ada perubahan — ruang untuk rilis berikutnya, lihat [ROADMAP.md](./ROADMAP.md))*

---

## [0.5.0] - 2026-09-24

**Test koneksi provider, endpoint chat-audio (modalities), dan semua model tidak hardcode.**

### Added
- **🧪 Test Koneksi** (`POST /api/ai-config/test`) — uji provider **sebelum disimpan**:
  kirim permintaan mini sungguhan (chat 1 kata / TTS "Halo.") ke teks, voice `/audio/speech`,
  voice chat-audio, maupun Pollinations — respons `{ok, message, latency_ms}`. Saat edit dengan
  API key kosong, test otomatis memakai key tersimpan. Tombol 🧪 ada di setiap form + form bawaan.
- **Jenis endpoint model suara custom** — pilih per provider:
  - `speech` → `POST {base_url}/audio/speech` (standar OpenAI TTS)
  - `chat_audio` → `POST {base_url}/chat/completions` + `modalities: ["text","audio"]`
    (gpt-4o-audio style, untuk provider yang belum punya endpoint TTS standar)
- **🔧 Model Bawaan tidak hardcode** (`POST /api/ai-config/defaults`) — nama model &
  voice berikut bisa diganti dari panel ⚙️:
  - `pollinations_text_model` — model hook bawaan (default `openai`, sebelumnya hardcoded)
  - `pollinations_audio_model` — model GPT-Audio bawaan (default `openai-audio`, sebelumnya hardcoded)
  - `edge_tts_voice` — voice Edge-TTS (default `id-ID-GadisNeural`, mis. ganti ke
    `id-ID-ArdiNeural` untuk suara laki-laki)
- E2E diperluas (45 checks): fake OpenAI server kini membalas **modalities audio** —
  uji test koneksi (4 jenis), render `chat_audio`, model bawaan terkonfigurasi dipakai
  hook & GPT-Audio (bukan nilai hardcoded).

### Changed
- Prompt "bacakan verbatim" untuk jalur TTS chat-audio diunggah jadi `TTS_VERBATIM_SYSTEM_PROMPT`
  (dipakai bersama GPT-Audio Pollinations & voice custom `chat_audio`).
- README: dokumentasi jenis endpoint, test koneksi, dan model bawaan.

---

## [0.4.0] - 2026-09-24

**Custom AI Provider (OpenAI-compatible) — model teks & model suara terpisah.**

### Added
- **🧠 Model Teks Custom (untuk hook)** — 1 model teks aktif, bisa diganti ke provider
  **OpenAI-compatible** mana pun (`POST {base_url}/chat/completions`): GPT-4o-mini,
  DeepSeek, Ollama/LM Studio, OpenRouter, dll. — *Label, Base URL, API Key, Model* bebas.
- **🎙️ Model Suara Custom (untuk voiceover)** — daftar voice model **OpenAI-compatible**
  (`POST {base_url}/audio/speech`, `response_format: mp3`): OpenAI TTS, ElevenLabs,
  MiniMax, LocalAI, dll. — *Label, Base URL, API Key, Model, Voice, Speed*. Otomatis muncul
  di dropdown **Voice Model** sebagai `custom:{id}` (bisa banyak provider sekaligus).
- **Panel ⚙️ Kelola AI Model** di editor — CRUD model teks & suara, pilih model teks aktif
  ("" = Pollinations bawaan), API key selalu tampil **ter-mask**; edit dengan key kosong =
  pertahankan key lama.
- Endpoint baru: `GET /api/ai-config`, `POST/DELETE /api/ai-config/text-models`,
  `POST/DELETE /api/ai-config/voice-models`, `POST /api/ai-config/active-text-model` (ber-Auth).
  Konfigurasi disimpan di `backend/logs/ai_config.json` (tidak ikut Git).
- Test E2E: fake OpenAI server lokal — uji generate-hook via custom LLM (model+API key
  terkirim benar), render job dengan custom voice (`custom:{id}`), key masking, keep-key
  saat edit kosong, error terkendali untuk id tak dikenal.

### Changed
- `POLLINATIONS_API_KEY` kini **opsional** — hanya wajib saat provider Pollinations dipakai;
  tanpa key, tersedia Edge-TTS + provider custom.
- `generate_voice_from_pollinations()` mendukung `custom:{id}` (TTS OpenAI-compatible);
  `POST /api/generate-hook` memakai model teks aktif (custom / Pollinations).
- README: dokumentasi konfigurasi AI provider + endpoint & param baru.

---

## [0.3.0] - 2026-09-24

**Custom Subtitle Style & Custom Font Import.**

### Added
- **🎨 Custom Subtitle Style** — panel **Gaya Caption** di editor (saat subtitle AKTIF):
  - **Ukuran font**: Kecil (4%) / Sedang (5.2%) / Besar (7%) dari tinggi video
  - **Warna teks**: 9 preset (Putih, Kuning, Cyan, Magenta, Hijau, Merah, Biru, Oranye, Hitam)
  - **Outline**: warna (Hitam/Putih/**Tanpa outline**) + tebal (Tipis/Sedang/Tebal)
  - **Posisi**: Atas / Tengah (gaya TikTok) / Bawah
  - **HURUF KAPITAL**: toggle caption semua huruf besar (gaya TikTok)
  - Parameter API: `subtitle_size`, `subtitle_color`, `subtitle_outline_color`,
    `subtitle_outline`, `subtitle_position`, `subtitle_caps`
- **🔤 Custom Font Import** — upload font format standar **`.ttf` / `.otf` / `.ttc`**
  (maks 5 MB) lewat panel yang sama:
  - Nama family dibaca otomatis dari file (fontTools) — tanpa input manual
  - Dimuat via opsi `fontsdir` FFmpeg (font disalin ke folder kerja render) —
    **tanpa instalasi font ke sistem**
  - Endpoint baru: `GET /api/fonts`, `POST /api/fonts/upload`,
    `DELETE /api/fonts/{font_id}` (semua ber-Auth) + metadata `logs/fonts.json`
  - Format `.woff`/`.woff2` (web font) ditolak dengan pesan jelas
  - Font custom disimpan permanen sampai dihapus manual
- **Balanced line wrap** — caption dipecah jadi 1–3 baris seimbang (meminimalkan
  lebar baris terpanjang) sehingga pas untuk semua ukuran font; lebar baris
  dihitung otomatis dari ukuran font & dimensi video
- Sidecar `.ass` (ber-style) ikut disimpan di `static/subs/` bersama `.srt`
- Test: asersi style ASS (ukuran/warna/outline/posisi/kapital), balanced wrap,
  pembuatan TTF uji via fontTools FontBuilder, E2E upload/daftar/hapus font,
  render dengan custom font, dan penolakan `.woff2`

### Changed
- `generate_ass()` & `build_subtitles()` mendukung `style` + `font_id` opsional
  (default tetap gaya lama: putih tebal + outline hitam di tengah)
- README: dokumentasi lengkap custom style/font, tabel param & endpoint baru

---

## [0.2.0] - 2026-09-22

Rilis fitur **Auto Subtitle Burn-in** + perbaikan pipeline render & pengembangan lokal.

### Added
- **🔥 Auto Subtitle Burn-in (AKTIF/NONAKTIF)** — caption gaya TikTok (putih tebal + outline
  hitam, blok 1–2 baris, di tengah layar) di-burn permanen ke video via filter `ass` FFmpeg
  (libass). Pilihan aktif/mati per render di Step 2 Editor, default AKTIF.
  - Skrip dipecah otomatis jadi caption (frasa utuh, hard-cap 42 karakter/2 baris).
  - Timing mengikuti voiceover: **word-boundary Edge-TTS** (akurat per kata) dengan fallback
    proporsional panjang teks (GPT-Audio / bila jumlah token tidak cocok).
  - File ASS dibangun dengan `PlayRes` = dimensi output render + posisi `\pos()` absolut —
    ukuran font/outline proporsional di semua resolusi.
- **File `.srt` untuk diunduh** — disimpan di `static/subs/{id}.srt`, tombol **SRT** baru di
  kolom Media halaman Logs.
- Parameter form `burn_subtitles` (`true`/`false`) pada `POST /api/process-video` dan
  `POST /api/jobs/submit`; respons menyertakan `subtitle_url` saat aktif.
- **Test suite**: `backend/test_subtitles.py` dan `backend/test_api_e2e.py`.
- Helper pipeline subtitle: `split_script_into_captions`, `build_caption_timings`,
  `generate_srt`, `generate_ass`, `build_subtitles`, `ffmpeg_supports_subtitles`,
  `get_media_dimensions`, `compute_output_dimensions`.

### Changed
- **Frontend memakai URL API relatif (`/api/...`)** — di-proxy Vite saat dev
  (`vite.config.js` + env `VITE_API_PROXY_TARGET`) dan Nginx saat production.
- Vite dev server: `host: true` + `allowedHosts: true` agar bisa diakses via preview/LAN.
- Edge-TTS kini memakai `Communicate.stream()` untuk menangkap **word-boundary** (timing
  subtitle) — output audio tetap sama.
- `get_media_duration` punya fallback parsing `ffmpeg -i` bila `ffprobe` tidak tersedia.
- Dokumentasi: README disegarkan; ditambah `CHANGELOG.md`, `ROADMAP.md`, `LAPORAN_ANALISIS.md`.
- `merge_video_audio` menerima `subtitle_ass` opsional.

### Fixed
- **Video hasil render tidak lagi hilang** saat user menulis skrip manual tanpa generate hook
  (tanpa `log_id`) — hasil selalu dipersist (id = `log_id` atau `job_id`) dan `video_url`
  tidak pernah `null`.
- `POST /api/jobs/submit` tanpa file video & tanpa `library_video_id` kini mengembalikan
  **400** dengan pesan jelas (sebelumnya crash `AttributeError` → 500).
- **Crop 9:16 selalu menghasilkan dimensi genap** — aman untuk libx264 pada semua rasio input
  (4:5, 1:1, 9:20, tinggi ganjil) sekaligus menjaga rasio.
- `frontend/nginx.conf`: `proxy_pass` salah port (`backend:8080` → `backend:9000`) + header SSE.
- `frontend/Dockerfile`: default `ARG VITE_API_BASE_URL` konsisten kosong (same-origin).
- `backend/Dockerfile`: menambahkan `fonts-dejavu-core` (font untuk burn subtitle).
- Penomoran `no` log CSV: `clear_logs` kini ikut me-reset counter penomoran.
- `HTTPException` di jalur Edge-TTS tidak lagi ter-wrap menjadi error 500 generik.

### Security
- Catatan mode dev di README: `ADMIN_PASSWORD_HASH` kosong = login tanpa verifikasi password
  (hanya localhost); anjuran `JWT_SECRET` acak (`openssl rand -hex 32`) untuk produksi.
- `.gitignore`: `backend/static/subs/*` tidak ikut ter-commit (media hasil generate).

---

## [0.1.0] - *(historis)*

Versi awal aplikasi — detail perubahan lihat `git log`:
- AI Hook Generator (TikTok/Shopee + variasi V2) berbasis Pollinations.
- Dual AI Voiceover (Edge-TTS Gadis + GPT-Audio Pollinations).
- Render video native FFmpeg (crop 9:16, mode sinkronisasi durasi auto/loop/trim).
- Job system async + progress SSE (`/api/jobs/submit` + `/api/jobs/{id}/stream`).
- Video Library (upload sekali, pakai berulang) + Video Editor 2 langkah.
- Log Viewer: tabel riwayat, CSV export, analytics Chart.js, security logs.
- Auth single-admin: bcrypt + JWT + anti-bruteforce 5×/15 menit.
- Video Library retention 30 hari, media render retention 7 hari.
- MCP Server (`generate_ai_voice`, `merge_video_and_voice`).
- Deployment Docker Compose (Nginx + Uvicorn) & dokumentasi VPS/PM2.

[Unreleased]: https://github.com/falconafk31/affiliate-video-maker/compare/HEAD
[0.3.0]: https://github.com/falconafk31/affiliate-video-maker/compare/8022e13...HEAD
[0.2.0]: https://github.com/falconafk31/affiliate-video-maker/compare/554f142...8022e13
[0.1.0]: https://github.com/falconafk31/affiliate-video-maker/commits/554f142
