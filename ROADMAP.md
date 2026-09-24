# Roadmap

Rencana pengembangan **Affiliate Video Maker**. Prioritas diambil dari
[LAPORAN_ANALISIS.md](./LAPORAN_ANALISIS.md) + lanjutan fitur subtitle.
Status terkini lihat [CHANGELOG.md](./CHANGELOG.md).

> ✅ = selesai · 🚧 = berikutnya (next up) · 🗓️ = terencana · 💡 = eksplorasi

---

## ✅ Selesai — v0.2.0 (2026-09-22)

- ✅ **Auto Subtitle Burn-in** dengan pilihan **AKTIF / NONAKTIF** (gaya TikTok, timing
  word-boundary Edge-TTS, SRT bisa diunduh dari Logs)
- ✅ Video hasil render selalu terpersist (skrip manual tanpa `log_id` tidak lagi hilang)
- ✅ Crop 9:16 dimensi genap (aman semua rasio input) + validasi `jobs/submit` (400, bukan crash)
- ✅ Frontend API relatif `/api` + dev-proxy Vite (dev lokal tanpa set env)
- ✅ Perbaikan proxy Nginx Docker (port + header SSE) + font DejaVu di image backend
- ✅ Test offline: `test_subtitles.py` (28 assertions) + `test_api_e2e.py` (13 assertions)

---

## 🚧 Next Up — perbaikan cepat (quick wins)

Keamanan & kebenaran perilaku (prioritas tinggi — lihat §3–4 laporan analisis):

- 🚧 **Hapus `api_key_prefix`** dari `/health` & `/api/debug`, beri auth pada `/api/debug` (S1)
- 🚧 **Fail-fast `JWT_SECRET`** — jangan fallback `"default_secret_if_not_set"` (S3)
- 🚧 **Perbaiki exp JWT** (`datetime.now(timezone.utc)`) — salah hitung di server non-UTC (B7)
- 🚧 **Perilaku `trim_audio`** — `-t durasi_video`, jangan `-shortest` (video tak ikut terpotong
  saat audio lebih pendek) (B2)
- 🚧 **Single worker / shared state** — `--workers 2` vs `jobs` & `LOGIN_ATTEMPTS` in-memory
  memecah SSE & lockout antar-proses (B3)
- 🚧 **Tombol Logout** + redirect ke tujuan awal setelah login (U1, U15)
- 🚧 **Refresh data via `onActivated`** di Logs/Library (keep-alive membuat data basi) (B9)
- 🚧 **Konfirmasi sebelum regenerate hook** bila skrip sudah diedit user (B13)
- 🚧 **Parsing error axios JSON** (`.detail`) — pesan error server sering tidak tampil (B10)
- 🚧 **Konsistensi terima file** `.mp4/.mov/.avi` antara Editor, Library & backend (B11)
- 🚧 **CORS whitelist origin** (ganti `allow_origins=["*"]`) + pertimbangkan auth untuk
  media statis / signed URL (S2, S4)
- 🚧 **`beforeunload` guard** saat render berjalan + recovery `job_id` via `sessionStorage`
  setelah refresh (U4, U5)

---

## 🗓️ Terencana — jangka menengah

- 🗓️ **SQLite untuk `hook_logs` & `login_logs`** (ganti CSV — query terindex, tanpa rewrite
  file penuh) + paginasi server-side `/api/logs`
- 🗓️ **Job queue dengan batas konkurensi** (semaphore 1–2 render FFmpeg serentak) + indikator
  "antrian" di UI
- 🗓️ **`-movflags +faststart`** & **skip re-encode** (`-c:v copy`) bila video sudah 9:16
- 🗓️ **Refactor `main.py`** → `routers/` + `services/` (tts, ffmpeg, pollinations) + `prompts.py`;
  hapus kode mati (`process_video` legacy bila sudah tergantikan jobs, konstanta tak terpakai)
- 🗓️ **CI** (ruff + pytest + `vite build`) & unit test endpoint auth/logs/library
- 🗓️ **Opsi gaya subtitle** — posisi (tengah/atas/bawah), warna preset, ukuran font, mode
  "1 baris besar" vs "2 baris"
- 🗓️ **Preview voice** — dengarkan sampel 1 kalimat sebelum render pilih voice model (U8)
- 🗓️ **Peringatan panjang skrip** vs aturan 500 karakter / ±40 detik di Script Editor (U9)
- 🗓️ **Aksesibilitas** — focus ring keyboard, drop-zone bisa di-tab, focus trap + ESC di modal,
  kontras teks kecil (U10)
- 🗓️ **Nama file download bermakna** `{produk}_{platform}_{tanggal}.mp4` (U7)
- 🗓️ **Pembersihan terjadwal** (`clean_old_videos` periodik, bukan hanya saat ada job) + rotasi
  `login_logs.csv` & log aplikasi

---

## 💡 Eksplorasi — fitur produk (jangka panjang)

Urut berdasarkan nilai untuk affiliate marketer harian:

1. 💡 **Batch generate** — 1 produk → semua variasi hook sekaligus, pilih yang terbaik → render
2. 💡 **Caption highlight per kata (karaoke)** — subtitle berubah warna mengikuti timing
   word-boundary (infrastruktur timing sudah ada di v0.2.0)
3. 💡 **BGM + auto-ducking** — musik latar dari library bebas-royalti (FFmpeg
   `sidechaincompress`), slider volume
4. 💡 **Generate caption posting + hashtag** — draft caption TikTok/Shopee bersamaan video
5. 💡 **Thumbnail otomatis** + play inline di Logs (ganti `<video>` per kartu Library)
6. 💡 **Template/preset produk** — simpan kombinasi voice + mode + variasi hook favorit
7. 💡 **Watermark / CTA sticker** — teks "Cek keranjang kuning!" dengan timing sederhana
8. 💡 **A/B compare view** — 2 hasil generate berdampingan sebelum render
9. 💡 **Multi-user sederhana / share link view-only** untuk review klien
10. 💡 **Redis** untuk job state (multi-instance) + monitoring (health: FFmpeg, disk free)

---

## Cara berkontribusi

1. Pilih item **Next Up** (dampak paling besar, scope kecil).
2. Tambah test untuk setiap perbaikan (`test_subtitles.py` / `test_api_e2e.py` sebagai pola).
3. Catat hasilnya di [CHANGELOG.md](./CHANGELOG.md) bagian `[Unreleased]`.
