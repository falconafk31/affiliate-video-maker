# 🗺️ ROADMAP — Affiliate Video Maker

Rencana pengembangan dan peningkatan proyek. Status setiap butir akan diperbarui seiring pengerjaan.

- 🟢 **Done** — sudah selesai & ter-commit
- 🟡 **In Progress** — sedang dikerjakan
- 🔴 **TODO** — siap dikerjakan (high priority)
- 🔵 **Backlog** — butuh riset / prioritas lebih rendah

Versi rilis dan isinya terdokumentasi di [CHANGELOG.md](./CHANGELOG.md).

---

## ✅ Selesai (riwayat singkat)

- 🟢 **v0.1.x** — Hook Generator (Pollinations), Dual AI Voiceover (Edge-TTS + GPT-Audio), render FFmpeg native, job system async + SSE, Video Library, Video Editor 2 langkah, Log Viewer + Security Logs, Auth single-admin (bcrypt + JWT + anti-bruteforce), Docker Compose, MCP Server, retention media (7 & 30 hari).
- 🟢 **v0.2.0** — **Auto Subtitle Burn-in (AKTIF/NONAKTIF)**: caption gaya TikTok, timing word-boundary Edge-TTS (fallback proporsional), file `.srt` bisa diunduh, preset gaya caption, `backend/requirements.txt` sudah benar (`requirements.txt` bukan `requirement.txt`), seed `hook_logs.csv` agar `/api/logs` aman untuk user baru, perbaikan pipeline & pengembangan lokal (lihat CHANGELOG 0.2.0).
- 🟢 **v0.3.0** — **Custom Subtitle Style** (ukuran/warna/outline/posisi/kapital) + **Custom Font Import** (`.ttf/.otf/.ttc`, family auto-detect, `fontsdir` tanpa instalasi sistem) + balanced line wrap + sidecar `.ass` + test font (E2E/unit) + dokumentasi lengkap.
- 🟢 **v0.4.0** — **Custom AI Provider (OpenAI-compatible)**: model teks (hook) terpisah dari model suara (voiceover) — masing-masing bisa pakai provider sendiri (Base URL + API Key + Model bebas); 1 model teks aktif + daftar voice model custom (`custom:{id}`); panel ⚙️ Kelola AI Model; API key ter-mask; `POLLINATIONS_API_KEY` jadi opsional; E2E fake OpenAI server.
- 🟢 **v0.5.0** — **Test Koneksi provider** (🧪 sebelum simpan, `{ok, message, latency_ms}`) + **dua jenis endpoint voice custom** (`/audio/speech` standar ATAU `/chat/completions` + modalities audio gpt-4o-audio style) + **semua model tidak hardcode** (model teks & suara Pollinations serta voice Edge-TTS configurable via "Model Bawaan").
- 🟢 **v0.6.0** — **Halaman `/setting` (Kelola AI Model)** — nav `[ Setting ]`, modal di home dihapus, panel "Endpoint yang digunakan" + **penyimpanan konfigurasi di database SQLite** (`backend/data/app.db`, tabel `ai_models` + `ai_settings`, migrasi otomatis dari json lama).
- 🟢 **v0.7.0** — **Hook V3 + render audio fix**: registry 13 variasi dengan grounding facts, duration 30–50 detik, validator/repair warning, FFmpeg explicit `-t` + FASTSTART, dan test koneksi model reasoning dengan `max_tokens=128`.

---

## 🎯 0.3.x — Penyempurnaan Subtitle & UX

- 🔴 **Perbanyak style preset caption** — simpan kombinasi style favorit (mis. "TikTok Kuning", "Clean White") dan pakai ulang dalam sekali klik.
- 🔴 **Preview style real-time** — pratinjau caption dengan frame video saat mengubah style di panel Gaya Caption (sekarang hanya mengubah hasil render akhir).
- 🔴 **Upload logo/watermark PNG** — drag & drop logo ke video (posisi & opacity), refresh otomatis berkas asset.
- 🔴 **Auto CTA popup** — generik placeholder harga/toko (mis. "Rp59rb · Keranjang Kuning") otomatis muncul di 3 detik terakhir.
- 🔴 **Kustomisasi gaya CTA & watermark** — warna, ukuran, posisi, durasi tampil.
- 🔴 **Multi-Cta / Text Animation** — beberapa teks pop-up berurutan.
- 🔴 **Auto Thumbnail Cover** — ambil frame terbaik + overlay teks hook untuk sampul video.
- 🔴 **Auto Virtual Avatar / Raw Story** — mode video baru: avatar AI / video cerita dengan TTS.
- 🔴 **Multi-Format Export** — pilihan output: 9:16 / 1:1 / 16:9, kualitas HD / hemat (bitrate & scale).
- 🔴 **Hapus semua media (audio/video) di logs** — tombol bersih-bersih massal.
- 🔴 **Auto Add Music** — soundtrack latar otomatis dengan ducking volume terhadap suara.

## 🔒 0.4.x — Keamanan & UX

- 🔴 Aktifkan `--reload` opsional via env; ganti `loguru` → `logging` (hilangkan 1 dependensi).
- 🔴 Enkripsi/HTTP-only cookie untuk JWT + proteksi CORS yang benar (saat ini `allow_origins=["*"]`).
- 🔴 Rate-limit endpoint publik (`/api/generate-hook`, `/api/login`, `/api/health`).
- 🔴 Snapshot test foto snapshot foto frontend.

## 🧪 0.5.x — Testing & Observability

- 🔴 Cypress E2E login & video processing di CI.
- 🔴 Konversi test manual → pytest + marker `ffmpeg`/`e2e`.
- 🔴 Log terstruktur (JSON) untuk observabilitas di VPS.

## 🔵 Backlog — Riset / Butuh Sumber Daya Eksternal

- 🔵 **Dubbing / translate bahasa asing** — sumber suara & video dari luar (butuh API & biaya).
- 🔵 **Auto Publish / Scheduler** — jadwal upload TikTok & Shopee Video (kredensial & API pihak ketiga).
- 🔵 **Stok video otomatis** — ambil klip dari stok (Pexels/Pixabay API) saat user tidak punya raw video.
- 🔵 **AI Avatar bawaan** — karakter virtual generatif (butuh model/API berbayar).
- 🔵 **Engagement Hot Score** — analitik prediktif performa video (butuh dataset).
- 🔵 **Text-to-Video penuh** — pipeline video 100% dari teks (riset model lokal/berbayar).

---

*Dokumen ini hidup — silakan usulkan perubahan prioritas lewat issue/diskusi.*
