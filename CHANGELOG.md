# Changelog

Semua perubahan penting proyek **Affiliate Video Maker** dicatat di file ini.

Format mengacu pada [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

*(Belum ada perubahan — ruang untuk rilis berikutnya, lihat [ROADMAP.md](./ROADMAP.md))*

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
- **Test suite**: `backend/test_subtitles.py` (28 assertions — chunking, timing, SRT/ASS,
  burn-in FFmpeg nyata, rasio 9:16/4:5/landscape) dan `backend/test_api_e2e.py`
  (13 assertions E2E offline: login → submit job → SSE → persist; TTS di-stub, FFmpeg asli).
- Helper pipeline subtitle: `split_script_into_captions`, `build_caption_timings`,
  `generate_srt`, `generate_ass`, `build_subtitles`, `ffmpeg_supports_subtitles`,
  `get_media_dimensions`, `compute_output_dimensions`.

### Changed
- **Frontend memakai URL API relatif (`/api/...`)** — di-proxy Vite saat dev
  (`vite.config.js` + env `VITE_API_PROXY_TARGET`) dan Nginx saat production.
  `VITE_API_BASE_URL` hanya di-set bila backend berada di origin lain. Menghapus fallback
  hardcode `:9000` yang merusak deployment di balik reverse proxy.
- Vite dev server: `host: true` + `allowedHosts: true` agar bisa diakses via preview/LAN.
- Edge-TTS kini memakai `Communicate.stream()` untuk menangkap **word-boundary** (timing
  subtitle) — output audio tetap sama.
- `get_media_duration` punya fallback parsing `ffmpeg -i` bila `ffprobe` tidak tersedia.
- Dokumentasi: README disegarkan (struktur proyek, tabel endpoint lengkap, retention policy,
  mode dev login, cara menjalankan test); ditambah `CHANGELOG.md`, `ROADMAP.md`.
- `merge_video_audio` menerima `subtitle_ass` opsional; proses `HTTPException` di jalur
  Edge-TTS tidak lagi ter-wrap menjadi error 500 generik.

### Fixed
- **Video hasil render tidak lagi hilang** saat user menulis skrip manual tanpa generate hook
  (tanpa `log_id`) — hasil selalu dipersist (id = `log_id` atau `job_id`) dan `video_url`
  tidak pernah `null`.
- `POST /api/jobs/submit` tanpa file video & tanpa `library_video_id` kini mengembalikan
  **400** dengan pesan jelas (sebelumnya crash `AttributeError` → 500).
- **Crop 9:16 selalu menghasilkan dimensi genap** (`trunc(min(iw,ih*9/16)/2)*2`) — aman untuk
  libx264 pada semua rasio input (4:5, 1:1, 9:20, tinggi ganjil) sekaligus menjaga rasio.
- `frontend/nginx.conf`: `proxy_pass` salah port (`backend:8080` → `backend:9000`, sesuai
  Dockerfile) yang menyebabkan 502 pada deployment Docker; ditambah header SSE
  (`proxy_http_version 1.1`, `proxy_buffering off`).
- `frontend/Dockerfile`: default `ARG VITE_API_BASE_URL` konsisten kosong (same-origin),
  tidak lagi menghasilkan path `/api/api/...`.
- `backend/Dockerfile`: menambahkan `fonts-dejavu-core` (font untuk burn subtitle).
- Penomoran `no` log CSV: `clear_logs` kini ikut me-reset counter penomoran.

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
[0.2.0]: https://github.com/falconafk31/affiliate-video-maker/compare/554f142...HEAD
[0.1.0]: https://github.com/falconafk31/affiliate-video-maker/commits/554f142
