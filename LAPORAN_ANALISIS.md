# 📋 Laporan Analisis Kode & Alur Penggunaan — Affiliate Video Maker

> **Tanggal analisis:** 22 September 2026
> **Cakupan:** seluruh backend (`main.py`, `mcp_server.py`), frontend (4 komponen + router), konfigurasi Docker/Nginx/Vite, dan dokumentasi.
> **Status:** Dokumen analisis saja — tidak ada perubahan kode, tidak ada commit/push/PR.

---

## 1. Ringkasan Eksekutif

Aplikasi ini adalah generator video affiliate bertenaga AI (hook generator → TTS → merge FFmpeg) dengan stack **FastAPI + Vue 3 + FFmpeg + Pollinations AI**. Secara keseluruhan fiturnya sudah lengkap untuk use-case single-admin, dan banyak keputusan bagus sudah diambil (FFmpeg native menggantikan MoviePy, SSE progress bar, video library, anti-bruteforce, lazy-loaded routes).

Namun ditemukan **beberapa bug nyata yang memengaruhi alur inti** (video bisa "hilang" saat user menulis skrip manual, mode `trim_audio` salah perilaku, deployment Docker tidak konsisten port sehingga proxy bisa rusak), **lubang keamanan** (endpoint debug membocorkan sebagian API key, media statis tanpa auth, JWT secret fallback), serta **inkonsistensi konfigurasi port (8000/8080/9000)** di README, Dockerfile, docker-compose, dan nginx.conf.

**Prioritas utama (P0):** 5 bug fungsional + 3 isu keamanan yang ada di bagian §3 dan §4.

---

## 2. Arsitektur & Alur Penggunaan (Current State)

### 2.1 Arsitektur

```
┌────────────────────────────┐        ┌───────────────────────────────┐
│  Frontend (Vue 3 + Vite)   │  HTTP  │  Backend (FastAPI + Uvicorn)  │
│  - VideoEditor.vue         │───────▶│  - /api/generate-hook (LLM)   │
│  - VideoLibrary.vue        │        │  - /api/jobs/submit (SSE job) │
│  - LogViewer.vue           │        │  - /api/generate-audio (TTS)  │
│  - Login.vue               │        │  - /api/library/* (CRUD)      │
│  - Chart.js analytics      │        │  - FFmpeg subprocess merge    │
└────────────────────────────┘        │  - CSV + JSON file "DB"       │
                                      └──────────┬────────────────────┘
                                                 │ HTTPS
                                      ┌──────────▼────────────────────┐
                                      │  Pollinations AI              │
                                      │  - chat/completions (hook)    │
                                      │  - openai-audio (TTS)         │
                                      │  + Edge-TTS (id-ID-Gadis)     │
                                      └───────────────────────────────┘
```

### 2.2 Alur penggunaan utama

1. **Login** → `POST /api/login` (bcrypt + JWT 24 jam, lockout 5x gagal / 15 menit).
2. **Step 1 — Generate Hook**: ketik nama produk → pilih platform (TikTok/Shopee) → pilih 1 dari 9 variasi → `POST /api/generate-hook` → hasil masuk textarea Script Editor + tersimpan di `hook_logs.csv` (dapat `log_id`).
3. **Step 2 — Proses**: mode *Video+Audio* (upload / pilih dari Library) atau *Hanya Audio*; pilih voice model (Edge-TTS Gadis / 6 suara GPT-Audio); pilih mode sinkronisasi durasi (auto / loop_video / trim_audio); user boleh mengedit skrip.
4. **Render (SSE)**: `POST /api/jobs/submit` → `EventSource /api/jobs/{id}/stream` → tahap `generating_voice` (10%) → `merging_video` (45%) → `saving` (85%) → `done` (100%). Hasil disimpan ke `static/videos/{log_id}.mp4`.
5. **Hasil**: preview video (opt-in untuk hemat bandwidth) + download + tombol "Buat Lagi".
6. **Library**: upload raw video sekali → dipakai berulang via modal picker (handoff via `sessionStorage`).
7. **Logs**: tabel riwayat + CSV export + analytics Chart.js + security logs; video/audio yang masih ada (retention 7 hari) bisa diunduh per baris.

### 2.3 Penilaian alur

Alur 2-step (hook → render) sudah tepat untuk produk ini: user bisa mengoreksi skrip AI sebelum TTS — ini keunggulan UX. Handoff Library→Editor via sessionStorage cukup elegan. Progress SSE real-time juga nilai plus besar dibanding spinner buta.

---

## 3. 🐛 Bug & Masalah Fungsional

### P0 — Merusak hasil / alur inti

| # | Temuan | Lokasi | Detail |
|---|--------|--------|--------|
| B1 | **Video hasil render HILANG jika user menulis skrip manual (tanpa generate hook)** | `backend/main.py:1183-1196` (`_run_video_job`), `main.py:596-603` (`process_video`), `frontend/src/components/VideoEditor.vue:790` | File final hanya dipersist jika `log_id` ada. Tanpa `log_id`, `job_dir` dihapus → video lenyap, `video_url=null`. Frontend lalu membangun URL rusak `API_BASE + null + "?t=..."` → player & download 404. **Ini bug paling serius**: alur "tulis skrip sendiri" (yang justru diiklankan di placeholder textarea) menghasilkan video yang tidak bisa diakses. **Fix:** selalu persist ke `VIDEOS_DIR / f"{log_id or job_id}.mp4"` dan selalu kembalikan `video_url`. |
| B2 | **Mode `trim_audio` salah saat audio lebih pendek dari video** | `backend/main.py:480-530` (`merge_video_audio`) | Perintah selalu memakai `-shortest`, sehingga output = durasi stream terpendek. Jika audio < video, video ikut terpotong — padahal UI menjanjikan *"Audio dipotong sesuai panjang video asli"* (output = durasi video). **Fix:** untuk `trim_audio`, pakai `-t {vid_dur}` (dan/atau `apad`+`atrim`), jangan `-shortest`. |
| B3 | **In-memory `jobs` & `LOGIN_ATTEMPTS` rusak dengan `--workers 2`** | `backend/Dockerfile:28`, `main.py:112-114`, `main.py:1145` | Uvicorn menjalankan 2 worker proses terpisah. Job yang di-submit ke worker A bisa menghasilkan **404 "Job tidak ditemukan"** saat SSE stream jatuh ke worker B. Brute-force lockout juga terbagi per-worker (efektif hanya 5×2=10 percobaan, dan cache tidak sinkron). **Fix:** jalankan `--workers 1` (render CPU-bound sudah di `asyncio.to_thread`), atau pindahkan state ke Redis/DB. |
| B4 | **Proxy Nginx Docker mengarah ke port yang salah** | `frontend/nginx.conf:23` vs `backend/Dockerfile:28` & `docker-compose.yml` | nginx `proxy_pass http://backend:8080/api/` tapi backend listen di **9000**. Seluruh trafik `/api/` lewat nginx (termasuk skenario `VITE_API_BASE_URL=/api`) akan **502**. Ditambah `docker-compose.yml:28` set `VITE_API_BASE_URL: ""` (falsy) → frontend fallback ke `http://hostname:9000` (by-pass nginx, CORS mentah). **Fix:** samakan ke satu port (mis. 8000), set `VITE_API_BASE_URL=/api` di build Docker, dan fallback frontend ke path relatif `/api` (bukan hardcode `:9000`). |
| B5 | **`POST /api/jobs/submit` crash 500 jika tidak ada file & tidak ada `library_video_id`** | `backend/main.py:1210-1245` | `video: UploadFile = File(None)` lalu `Path(video.filename)` → `AttributeError` saat `video=None`. Frontend mengirim dummy empty blob untuk library, jadi lolos — tapi API publik tetap rapuh. **Fix:** validasi `video or library_video_id`, return 400. |

### P1 — Bug nyata, dampak lebih terbatas

| # | Temuan | Lokasi | Detail |
|---|--------|--------|--------|
| B6 | **Memory leak `jobs` dict** — `_cleanup_old_jobs()` didefinisikan tapi **tidak pernah dipanggil** | `main.py:1148` | Jika user menutup tab saat render berjalan, tidak ada listener SSE yang menjadwalkan `_delayed_job_cleanup` → entry job menumpuk selamanya. **Fix:** panggil `_cleanup_old_jobs()` secara periodik (scheduler) atau di setiap `submit_job`. |
| B7 | **JWT `exp` salah hitung di server non-UTC** | `main.py:56` | `datetime.utcnow().timestamp()` — `utcnow()` naive dianggap *local time* oleh `.timestamp()`. Di server UTC+7, token bisa expired 7 jam lebih cepat. **Fix:** `datetime.now(timezone.utc)`. |
| B8 | **Nomor urut log (`no`) tidak sinkron setelah Reset Log** | `main.py:1005-1010` vs `main.py:125-140` | `clear_logs` tidak me-reset `global_row_count`; penomoran lanjut dari angka lama sampai request `/api/logs` berikutnya me-recount. **Fix:** reset counter di `clear_logs` (atau hitung dari file saat append). |
| B9 | **`keep-alive` tanpa `onActivated` → data basi saat pindah halaman** | `frontend/src/App.vue:42-44`, semua komponen pakai `onMounted` | Kunjungan kedua ke Logs/Library tidak me-refresh data (log/video baru tidak muncul sampai klik Refresh). **Fix:** tambah `onActivated(refresh...)` atau pasang `:include` eksplisit + tombol auto-refresh. |
| B10 | **Parsing error response axios salah untuk JSON** | `VideoEditor.vue:830` | `err.response.data.text()` hanya works jika data berupa Blob; untuk error JSON (400/501/5xx dari FastAPI) `.text` tidak ada → pesan detail (`detail: "..."`) tidak pernah tampil, user dapat "Server error (xxx)" generik. **Fix:** cek `typeof err.response.data === 'object'` → ambil `.detail`. |
| B11 | **Validasi file tidak konsisten antar layer** | `VideoEditor.vue:213` vs `backend/main.py` & `VideoLibrary.vue:35` | Editor hanya menerima `.mp4`, Library menerima `.mp4/.mov/.avi`, backend menerima 3 ekstensi itu (dan *diam-diam rename* ekstensi lain ke `.mp4` yang akan membuat FFmpeg gagal/aneh). **Fix:** satu daftar `ALLOWED_EXTENSIONS` yang dipakai semua layer; tolak dengan pesan jelas, jangan rename. |
| B12 | **Crop portrait bisa menghasilkan dimensi ganjil → FFmpeg error** | `backend/main.py:505` (`crop=ih*(9/16):ih`) | Untuk input di luar rasio 16:9/9:16 persis (mis. 4:5, 1:1, atau tinggi ganjil), lebar hasil crop bisa desimal/ganjil → `libx264` menolak (harus genap). Juga selalu re-encode walaupun input sudah 9:16. **Fix:** `scale='trunc(ih*9/16/2)*2':ih` / `crop='min(iw\,trunc(ih*9/16/2)*2)':ih`, dan skip filter (pakai `-c:v copy`) jika rasio sudah 9:16. |
| B13 | **Nomor 2 (regenerate) menimpa skrip yang sudah diedit user tanpa konfirmasi** | `VideoEditor.vue` `generateHook()` | `prompt.value = response.data.script` menimpa editan user di textarea. **Fix:** confirm dialog jika `prompt` berubah sejak hasil generate terakhir. |
| B14 | **Toast "Video dipilih!" tidak terlihat** | `VideoLibrary.vue` `useVideo()` | `router.push('/')` langsung unmount komponen → toast hilang sebelum tampil. **Fix:** pindahkan toast ke store/global, atau tampilkan di halaman tujuan. |
| B15 | **Atribut `download` pada link cross-origin diabaikan browser** | `LogViewer.vue` (link download video/audio) | `:href="apiBase + log.video_url"` dengan `apiBase` beda origin → tombol "Download" bisa membuka tab baru alih-alih mengunduh. **Fix:** fetch blob + `createObjectURL` (seperti `downloadCsv`), atau lewat endpoint proxy same-origin. |

---

## 4. 🔐 Keamanan

| # | Temuan | Lokasi | Severity | Detail |
|---|--------|--------|----------|--------|
| S1 | **Endpoint `/api/debug` & `/health` membocorkan prefix API key** | `main.py:1327, 1339` | **Tinggi** | `api_key_prefix: POLLINATIONS_API_KEY[:8] + "..."` — 8 karakter pertama **secret key** (`sk_...`) diekspos **tanpa auth**. Kombinasi dengan brute-force offline memperkecil ruang tebakan, dan memastikan format key. **Fix:** hapus sama sekali dari response, atau protect endpoint dengan auth & hanya tampilkan `api_key_set: true`. |
| S2 | **Media statis tanpa autentikasi** | `main.py:231-233` (mount `/api/videos`, `/api/audios`, `/api/lib-static`) | Sedang | Semua video/audio hasil render & library bisa diunduh siapa pun yang tahu URL (UUID sulit ditebak, tapi URL bocor lewat share/Referer/log). Untuk konten affiliate yang belum rilis ini berisiko. **Fix:** signed URL berjangka waktu, atau endpoint streaming dengan `Depends(get_current_user)`. |
| S3 | **JWT_SECRET fallback default yang lemah** | `main.py:40` | **Tinggi** | `os.getenv("JWT_SECRET", "default_secret_if_not_set")` — jika `.env` lupa di-set, token bisa dipalsukan siapa pun yang baca source (repo publik!). **Fix:** `raise RuntimeError` jika tidak diset (sudah dilakukan untuk API key — konsistenkan). |
| S4 | **CORS `allow_origins=["*"]` + `allow_credentials=True`** | `main.py:241-248` | Sedang | Kombinasi yang secara spesifikasi tidak valid dan membuka API ke semua origin. **Fix:** whitelist origin frontend (env `ALLOWED_ORIGINS`). |
| S5 | **Secret contoh lemah di `.env.example` & README** | `backend/.env.example`, `README.md` | Rendah | `JWT_SECRET=rahasia123456789` dipakai orang apa adanya. **Fix:** placeholder acak + instruksi `openssl rand -hex 32`. |
| S6 | **Login lockout & attempt log tidak tahan multi-worker / restart** | `main.py:36`, `login_logs.csv` | Sedang | In-memory dict hilang saat restart (attacker bisa restart-trigger lewat crash) dan terbagi per-worker (lihat B3). `login_logs.csv` juga tumbuh tanpa batas (rotasi/per-file cap belum ada). |
| S7 | **SSE stream tanpa auth** | `main.py:1272` (by design, EventSource tak bisa kirim header) | Rendah | Status job bisa dibaca siapa pun yang menebak `job_id` (UUID hex — cukup aman), tapi tidak konsisten dengan endpoint lain. **Fix:** pakai `fetch`-based SSE reader yang bisa kirim `Authorization`, atau token query jangka pendek. |
| S8 | **Token disimpan di `localStorage`** | `main.js`, `Login.vue` | Rendah (tradeoff umum) | Rentan XSS. Mitigasi: pastikan tidak ada `v-html`, pertimbangkan cookie `HttpOnly`+`SameSite`. Tambah juga tombol **Logout** + hapus token (saat ini tidak ada logout sama sekali — lihat U3). |

---

## 5. ⚡ Optimasi Performa

### Backend

1. **Hindari re-encode saat tidak perlu** (`main.py` `merge_video_audio`): jika input sudah 9:16 dan `duration_mode` mengizinkan, pakai `-c:v copy` (saat ini selalu `libx264` karena `force_portrait` default `true`). Ini 5–10× lebih cepat dan menghemat CPU.
2. **Tambahkan `-movflags +faststart`** pada output MP4 agar `moov` di depan → playback web (progressive download) jauh lebih responsif.
3. **Batasasi konkurensi render**: `asyncio.create_task(_run_video_job(...))` tanpa batas — 5 upload serentak = 5 FFmpeg sekaligus → CPU/RAM meledak (apalagi dengan 2 workers = 10 proses ffmpeg). Tambah semaphore/queue (mis. max 1–2 render bersamaan) + indikator "antrian" di UI.
4. **Simpan referensi task** `_run_video_job` (task yang tidak direferensikan bisa di-GC oleh event loop) — kumpulkan di set, buang saat selesai.
5. **CSV sebagai database**: `update_hook_log_script` membaca & menulis **seluruh file** setiap edit; `get_logs` membaca seluruh file + `_ensure_log_header()` me-recount setiap request. Untuk ribuan log ini O(n) terus-menerus. **Saran:** SQLite (sudah pasti tersedia di Python) untuk `hook_logs` & `login_logs` — migration mudah, query terindex, tidak ada masalah encoding BOM/lock.
6. **`clean_old_videos()` dipanggil blocking** dari coroutine (`_run_video_job`) — pindahkan ke `asyncio.to_thread` atau scheduler terpisah yang jalan harian (saat ini cleanup hanya terpicu saat ada job baru — file bisa menumpuk jika aplikasi sepi).
7. **Jangan salin video library ke `job_dir`** (`shutil.copy`, bisa ratusan MB per job) — FFmpeg cukup baca path aslinya (read-only); hemat I/O & disk temp.
8. **`requirements.txt` masih memuat `moviepy==1.0.3`** padahal README menyatakan sudah "completely replaced" — moviepy hanya dipakai `mcp_server.py`. Hapus dari core deps (atau pindahkan ke extras) → image Docker jauh lebih ramping. `mcp_server.py` juga sebaiknya memakai FFmpeg path yang sama (konsistensi + 10× lebih cepat).
9. **Hapus kode mati**: `API_TIMEOUT_SECONDS` (tak dipakai), `last_status` di SSE generator (tak dipakai), fallback TTS `GET /voice` legacy (tak pernah dipanggil frontend), `process_video` sync (sudah digantikan SSE jobs — hapus atau tandai deprecated agar tak dirawat dua kali), `add_auth.py` & file `test_*.py` scratch di root/backend.
10. **Paginasi server-side `/api/logs`** saat log sudah besar (saat ini semua baris dikirim, frontend yang mem-paginate).

### Frontend

1. **Satu modul API bersama** — `API_BASE`/`API_BASE_URL` di-hardcode identik di 4 komponen dengan fallback `${protocol}//${hostname}:9000` yang salah untuk deployment di balik reverse proxy/HTTPS standar (port 9000 tak terekspos). Buat `src/api.js` dengan base **relatif `/api`** sebagai default (nginx sudah proxy), override via `VITE_API_BASE_URL` hanya jika perlu.
2. **Chart.js**: sudah lazy-load via route — baik. Pertimbangkan `await import('chart.js')` di dalam `renderCharts()` agar chunk analytics benar-benar terpisah.
3. **Self-host font** (JetBrains Mono + VT323 dari Google Fonts di `index.html`) — menghemat 1 RTT dan menghindari ketergantungan eksternal/privacy; atau `font-display: swap` sudah ada (cukup baik).
4. **Video preview library** memuat `preload="metadata"` untuk semua kartu — untuk puluhan video, pertimbangkan thumbnail statis (generate via FFmpeg `thumbnail.jpg` saat upload) alih-alih `<video>` element per kartu.

---

## 6. 🏗️ Arsitektur & Kualitas Kode

1. **Konsistensi port — bereskan sekali untuk semua** (ini sumber bug B4 & kebingungan onboarding):
   - README dev: `uvicorn --port 8000`, lalu tulis "Backend must be running on port 9000";
   - Dockerfile: `9000`; docker-compose: `9000:9000`; nginx.conf: `backend:8080`; DOCKER_INSTRUCTIONS.md: `8080`; DEPLOYMENT.md (PM2): `8000`.
   **Keputusan:** pilih **satu** (mis. 8000 internal), frontend selalu memanggil `/api` relatif.
2. **State in-memory (`jobs`, `LOGIN_ATTEMPTS`) vs multi-worker** — sudah dibahas di B3; arsitektur jangka panjang: Redis untuk job state & rate-limit, atau single-worker + external queue (Celery/RQ) untuk render.
3. **Struktur modul `main.py` 1365 baris** — pisah jadi `routers/` (`auth.py`, `hooks.py`, `jobs.py`, `library.py`, `logs.py`), `services/` (`tts.py`, `ffmpeg.py`, `pollinations.py`), `models/`. Prompt hook (±300 baris string) pindah ke `prompts.py` atau file `.md` — jauh lebih mudah di-tune tanpa menyentuh logika.
4. **Side-effect di computed** (`LogViewer.vue:454-465`): `filteredLogs` melakukan `currentPage.value = 1`. Bekerja tapi anti-pattern (re-entrancy, confusing). Pindahkan ke `watch([search, filterPlatform])`.
5. **Tidak ada test otomatis** yang berarti — `test_log_reader*.py`, `test_get_whisper.py` hanya print-based scratch. Tambah `pytest` + `httpx.ASGITransport` untuk unit test endpoint (auth, log CRUD, validasi upload) dan test `merge_video_audio` dengan fixture FFmpeg kecil. Minimal: CI `ruff` + `pytest` + `vite build`.
6. **Type hints & validasi**: `log_id: str = Form(None)` → `str | None`; response model Pydantic untuk konsistensi kontrak API (juga otomatis dokumentasi OpenAPI yang rapi).
7. **Error handling TTS**: tiga jalur kode TTS berbeda (Edge-TTS, chat-completions audio, GET `/voice`) + `mcp_server` keempat (`/v1/audio/speech`) — ekstrak satu `TTSProvider` interface dengan strategi, plus retry sederhana (1×) untuk error transient.
8. **Naming**: `voice_model: "whisper"` yang sebenarnya alias `id-ID-GadisNeural` membingungkan (`main.py` default `"whisper"` vs `submit_job` default `id-ID-GadisNeural`) — hapus alias legacy.
9. **Repo hygiene**: file `backend/static/library/3a9fc7db....mp4` **(7.9 MB) ter-commit ke Git** — `.gitignore` meng-ignore `static/videos` & `static/audios` tapi lupa `static/library`. Tambah `backend/static/library/*` ke `.gitignore` + `git rm --cached`, dan jangan commit artefak media. File scratch `add_auth.py`, `test_*.py` di root/backend juga sebaiknya dihapus atau dipindah ke `scripts/`.
10. **README** menyebut `ecosystem.config.js` dalam struktur proyek tapi file tersebut tidak ada di repo — sinkronkan dokumentasi.

---

## 7. 🎨 UI/UX

### Yang sudah bagus
- Alur 2 langkah ber-nomor (Step 1 / Step 2) sangat jelas, CTA besar bertema retro konsisten.
- Progress bar SSE dengan label tahap + persen menurunkan kecemasan menunggu render.
- "Preview dinonaktifkan untuk hemat bandwidth" — keputusan yang thoughtful untuk VPS kecil.
- Estimasi durasi detik + char counter real-time di Script Editor.
- Empty state yang ramah (Library kosong, Log kosong) dan modal konfirmasi destructive action.
- Handoff Library→Editor smooth (sekali pakai, auto-clear).

### Perbaikan yang disarankan

| # | Usulan | Detail |
|---|--------|--------|
| U1 | **Tombol Logout** | Saat ini tidak ada cara logout (token 24 jam di localStorage). Tambah menu user di header: Logout + sisa waktu token. |
| U2 | **Konfirmasi sebelum regenerate hook** | Editan user di textarea bisa hilang seketika (B13). |
| U3 | **Guard `onActivated` / auto-refresh** | Logs & Library basi setelah pindah halaman (B9). |
| U4 | **Recover render setelah refresh** | Jika user refresh saat render berjalan, hasil hilang dari layar (masih ada di Logs jika `log_id` — tapi tidak ada notifikasi). Simpan `job_id` di `sessionStorage`, saat mount tawarkan "Lanjutkan pantau job?" atau minimal banner "Render terakhir kamu ada di Logs". |
| U5 | **`beforeunload` warning** saat render berjalan | Mencegah user kehilangan progress view tanpa sengaja. |
| U6 | **Preview video default ON di desktop, OFF di mobile** | Bandwidth saver saat ini selalu OFF; deteksi `matchMedia` / `navigator.connection.saveData`. |
| U7 | **Nama file download bermakna** | Saat ini selalu `affiliate_video.mp4`. Gunakan `{produk}_{platform}_{tanggal}.mp4`. |
| U8 | **Preview suara sebelum render** | Tombol "Dengarkan contoh" (generate audio 1 kalimat pertama) untuk memilih voice model tanpa render ulang. |
| U9 | **Peringatan panjang skrip vs 500 karakter** | Prompt backend membatasi 500 karakter, tapi editor bebas — user yang menulis manual bisa membuat audio 60 detik. Tambah badge warning di atas ±40 detik, dan validasi soft. |
| U10 | **Aksesibilitas** | Drop-zone adalah `<div @click>` (tidak bisa di-fokus keyboard) — tambah `role="button" tabindex="0" @keydown.enter`; `focus:outline-none` tanpa pengganti menghilangkan focus ring keyboard (ganti `focus-visible:ring`); modal belum punya focus trap & handler ESC; teks `text-[10px] text-slate-500` kontrasnya di batas bawah WCAG. |
| U11 | **Grid variasi hook di mobile** | 9 tombol dalam `grid-cols-3` tetap di layar kecil — label "🚀 V2: Visual Shock" terpotong/wrap aneh. Pakai `grid-cols-2 sm:grid-cols-3`, atau pill scroll horizontal + tooltip deskripsi tiap variasi (saat ini user tidak tahu beda "Viral Impulsif" vs "FOMO Urgency" tanpa menebak). |
| U12 | **Bersihkan kelas CSS bentrok** | Pola `text-black text-slate-100` (dua warna teks sekaligus) muncul berulang di 3 komponen — hasil akhir bergantung urutan CSS, rawan inkonsisten. Pilih satu. |
| U13 | **Route `history` mode** | Router pakai `createWebHashHistory` (URL `/#/logs`) padahal `nginx.conf` sudah menyiapkan `try_files` untuk HTML5 history mode — beralih ke `createWebHistory` untuk URL bersih. |
| U14 | **Error toast terstandar** | Campur `alert()`, inline error, toast hijau. Unifikasi ke komponen toast global (sudah ada di Library/LogViewer — jadikan shared). |
| U15 | **Login: tampilkan alasan lockout sisa waktu** | Saat ini hanya "Coba lagi dalam 15 menit" — tambah hitung mundur, dan setelah sukses redirect ke tujuan awal (saat ini selalu `/`, deep-link `/#/logs` hilang). |

---

## 8. 📦 DevOps & Dokumentasi

1. **docker-compose**: backend tidak punya healthcheck & `depends_on` tanpa condition; tambah `healthcheck` curl `/api/health` + `depends_on: condition: service_healthy`.
2. **SSE via nginx**: tambah `proxy_http_version 1.1; proxy_set_header Connection ''; proxy_buffering off;` pada location `/api/` (saat ini hanya mengandalkan header `X-Accel-Buffering`, yang cukup, tapi kedua opsi lebih aman untuk EventSource jangka panjang). `client_max_body_size 500M` sudah ada di location `/api/` — baik, tapi pastikan juga berlaku untuk upload library.
3. **Volume Docker**: `temp_processing/` tidak di-volume (hilang saat restart container — oke karena ephemeral), tapi pastikan `static/` & `logs/` tetap mounted (sudah — baik).
4. **Kebersihan dokumentasi**:
   - README: port 8000 vs 9000 (kontradiksi internal), `ecosystem.config.js` hilang, "7-Day Video Log" vs `VIDEO_LIBRARY_RETENTION_DAYS=30` untuk library (beda tapi tidak dijelaskan di README bagian retention).
   - `DOCKER_INSTRUCTIONS.md` bilang backend di `8080` — samakan.
   - Screenshots di README memakai URL eksternal komododecks yang bisa kadaluarsa — simpan di `docs/images/`.
5. **Logging**: pakai `RotatingFileHandler` untuk log aplikasi; `login_logs.csv` diberi cap (mis. rotate bulanan).
6. **Monitoring**: `/api/health` sudah ada — tambahkan pengecekan FFmpeg & disk free space (sekarang ada di `/api/debug` yang tak ber-Auth — gabungkan ke health ber-auth).

---

## 9. 💡 Saran Fitur Baru (Product)

Diurutkan berdasarkan nilai untuk use-case affiliate marketer harian:

1. **Subtitle/Caption auto burn-in** — video TikTok/Reels praktis wajib caption besar. Generate SRT dari skrip (timing proporsional dari durasi TTS) → burn dengan `subtitles`/`drawtext` FFmpeg. Ini *game changer* untuk CTR.
2. **Batch generate** — input 1 produk → generate 4–9 variasi hook sekaligus → pilih yang terbaik → render. Menggandakan produktivitas riset hook.
3. **Riwayat "hasil jadi" yang kaya** — thumbnail auto-generate, play inline di Logs, filter "sudah jadi video / belum".
4. **Template & preset produk** — simpan kombinasi (voice favorit + duration mode + variasi hook + CTA tambahan) sebagai preset bernama.
5. **BGM/ducking** — tambah background music dari library bebas-royalti dengan auto-duck (FFmpeg `sidechaincompress`), volume slider.
6. **Watermark / CTA sticker opsional** — teks "Cek keranjang kuning!" atau logo kecil di sudut, position & timing sederhana.
7. **Generate caption posting + hashtag** — sekali klik, selain video dapat draft caption TikTok/Shopee (ekstensi natural dari hook generator).
8. **A/B compare view** — tampilkan 2 hasil generate berdampingan sebelum render.
9. **Multi-user sederhana** (jika kolaborasi tim) — saat ini single-admin; minimal "share link view-only" untuk review klien.
10. **Preview voice instan** — (U8) tombol putar sampel 1 kalimat per voice.

---

## 10. 🗺️ Roadmap Prioritas

### Quick wins (1–2 hari kerja, dampak besar)
- [ ] **B1** persist video tanpa `log_id` + fix URL `null` di frontend
- [ ] **S1/S3** hapus `api_key_prefix`, fail-fast `JWT_SECRET`
- [ ] **B4** samakan port (8000) + `VITE_API_BASE_URL=/api` + fallback relatif
- [ ] **B3** `--workers 1`
- [ ] **B7** fix `datetime.now(timezone.utc)`
- [ ] **B2** perilaku `trim_audio` dengan `-t`
- [ ] **B12** crop aman (dimensi genap) + `-movflags +faststart`
- [ ] **B10** parsing error JSON axios
- [ ] **U1** tombol Logout, **U2** konfirmasi regenerate, **B9/U3** `onActivated`
- [ ] `.gitignore` `static/library/*` + `git rm --cached` file 7.9 MB

### Jangka menengah (1–2 minggu)
- [ ] SQLite untuk logs, hapus moviepy dari core, hapus kode mati & `process_video` sync
- [ ] Job queue dengan batas konkurensi + recovery job via `sessionStorage`
- [ ] Modul `api.js` bersama + `createWebHistory` + perbaikan aksesibilitas dasar
- [ ] pytest + CI (ruff, pytest, vite build)
- [ ] Signed URL / auth untuk media statis (S2), CORS whitelist (S4)

### Jangka panjang
- [ ] Subtitle burn-in (fitur #1), batch generate (#2), BGM ducking (#5)
- [ ] Redis untuk job state (multi-instance), rotasi log, monitoring
- [ ] Split `main.py` ke routers/services, TTS provider abstraction, MCP server FFmpeg

---

## 11. Penutup

Fondasi produk sudah kuat dan visi fiturnya jelas. Titik terlemah ada pada **konsistensi** (port, validasi file, perilaku durasi, persist hasil) dan **kebersihan deployment** (workers vs state in-memory, nginx proxy). Lima perbaikan P0 di §3–4 saja sudah akan menghapus seluruh "video hilang / deploy 502 / token aneh" yang paling mungkin dikeluhkan user nyata. Setelah itu, subtitle burn-in dan batch generate adalah investasi fitur dengan ROI tertinggi untuk target pengguna affiliate marketer.

*Dokumen ini murni analisis — tidak ada kode yang diubah, tidak ada commit/push/PR.*
