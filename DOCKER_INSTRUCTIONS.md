# Panduan Deployment dengan Docker 🐳

Aplikasi Affiliate Video Maker sekarang sudah mendukung deployment menggunakan **Docker** dan **Docker Compose**. Ini adalah cara paling mudah dan bersih untuk menjalankan aplikasi di VPS atau Local tanpa pusing mengatur versi Python, Node.js, atau menginstal FFmpeg secara manual.

## Persiapan
Pastikan kamu sudah menginstal:
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Struktur File Docker
1. `docker-compose.yml` (Root) — Orkestrasi untuk menjalankan backend dan frontend secara bersamaan.
2. `backend/Dockerfile` — Image Python 3.10 dengan pre-installed `ffmpeg`.
3. `frontend/Dockerfile` — Multi-stage build menggunakan Node.js untuk build Vue dan Nginx untuk serving.
4. `frontend/nginx.conf` — Konfigurasi reverse proxy Nginx di dalam container frontend untuk meneruskan request `/api/` ke container backend.

## Cara Menjalankan (Local / VPS)

### 1. Set Environment Variables
Buat file `.env` di **root directory** (sejajar dengan `docker-compose.yml`) yang berisi API key Pollinations kamu:
```env
POLLINATIONS_API_KEY=sk_12345abcdef
```
*(Opsional: kamu bisa langsung set variabel environment ini di shell server kamu).*

### 2. Jalankan Build & Start
Di terminal (root directory proyek), jalankan perintah berikut:

```bash
# Build image dan jalankan container di background (detached mode)
docker-compose up -d --build
```

### 3. Akses Aplikasi
Setelah perintah di atas selesai, aplikasi akan langsung berjalan:
- **Frontend (Web UI)**: `http://localhost:80` (atau `http://IP_VPS`)
- **Backend (API)**: `http://localhost:8080` (hanya terekspos jika butuh diakses langsung, biasanya frontend sudah reverse proxy `/api/`)

### 4. Melihat Log
Untuk melihat log dari aplikasi (misal untuk debug proses render video):
```bash
# Log seluruh aplikasi
docker-compose logs -f

# Hanya log backend
docker-compose logs -f backend

# Hanya log frontend (Nginx)
docker-compose logs -f frontend
```

### 5. Menghentikan Aplikasi
```bash
docker-compose down
```

---

## Catatan GitHub
Semua konfigurasi Docker (`Dockerfile`, `docker-compose.yml`, `.dockerignore`) sudah siap di-push ke GitHub. Ketika kamu pull di VPS baru, kamu hanya perlu membuat ulang file `.env` dan menjalankan `docker-compose up -d --build`.

File log prompt (`hook_logs.csv`) telah di-mounting keluar dari container, sehingga jika container di-restart log tidak akan hilang. Data video sementara yang sedang diproses tidak disimpan persisten agar ukuran storage tetap ringan.
