# 🚀 VPS Deployment Guide — Affiliate Video Maker

> Panduan deploy ke VPS Ubuntu/Debian menggunakan **PM2** sebagai process manager dan **Nginx** sebagai reverse proxy.

---

## 📋 Requirements VPS

- Ubuntu 20.04+ / Debian 11+
- Minimum 2 CPU, 2GB RAM (video processing membutuhkan resource)
- Domain atau IP publik

---

## 1️⃣ Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
sudo apt install -y python3.10 python3.10-venv python3-pip

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install FFmpeg (REQUIRED for MoviePy)
sudo apt install -y ffmpeg

# Verify installs
python3 --version     # 3.10+
node --version        # 18+
ffmpeg -version       # 7.x

# Install PM2 globally
sudo npm install -g pm2

# Install 'serve' for serving frontend static files
sudo npm install -g serve
```

---

## 2️⃣ Clone Repository

```bash
# Clone ke /var/www/
cd /var/www
git clone https://github.com/YOUR_USERNAME/affiliate-video-maker.git
cd affiliate-video-maker
```

---

## 3️⃣ Setup Backend

```bash
cd /var/www/affiliate-video-maker/backend

# Buat virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy dan edit .env
cp .env.example .env
nano .env
```

Isi `.env`:
```env
POLLINATIONS_API_URL=https://gen.pollinations.ai
POLLINATIONS_API_KEY=sk_xxxxxxxxxxxxxxxx
```

---

## 4️⃣ Build Frontend

```bash
cd /var/www/affiliate-video-maker/frontend

# Install dependencies
npm install

# Edit .env untuk production
nano .env
```

Isi `frontend/.env`:
```env
VITE_API_BASE_URL=https://api.your-domain.com
```

```bash
# Build production bundle
npm run build
# Output: frontend/dist/
```

---

## 5️⃣ Update PM2 Ecosystem Config

Edit `ecosystem.config.js` di root project — sesuaikan path Python virtualenv:

```javascript
// Ubah args backend agar pakai venv
args: "-m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2",
// Tambahkan interpreter path virtualenv:
interpreter: "/var/www/affiliate-video-maker/backend/venv/bin/python",
```

> **Note**: Edit `ecosystem.config.js`, ubah field `interpreter` dari `"none"` menjadi path venv Python.

---

## 6️⃣ Start dengan PM2

```bash
cd /var/www/affiliate-video-maker

# Start semua services
pm2 start ecosystem.config.js

# Simpan config PM2 agar auto-start setelah reboot
pm2 save
pm2 startup
# Jalankan perintah yang ditampilkan oleh pm2 startup

# Cek status
pm2 status
pm2 logs
```

---

## 7️⃣ Setup Nginx Reverse Proxy

```bash
sudo apt install -y nginx

# Buat config Nginx
sudo nano /etc/nginx/sites-available/affiliate-video-maker
```

Paste config berikut (ganti `your-domain.com`):

```nginx
# Frontend
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Backend API
server {
    listen 80;
    server_name api.your-domain.com;

    # Increase upload limit for video files (default 1MB is too small)
    client_max_body_size 500M;
    client_body_timeout 300s;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# Enable config
sudo ln -s /etc/nginx/sites-available/affiliate-video-maker /etc/nginx/sites-enabled/

# Test dan reload Nginx
sudo nginx -t
sudo systemctl reload nginx
```

---

## 8️⃣ SSL dengan Let's Encrypt (HTTPS)

```bash
sudo apt install -y certbot python3-certbot-nginx

# Generate SSL certificates
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
sudo certbot --nginx -d api.your-domain.com

# Auto-renewal sudah otomatis via systemd timer
```

---

## 🔧 PM2 Commands Cheatsheet

```bash
pm2 status                        # Lihat semua process
pm2 logs                          # Lihat semua logs
pm2 logs affiliate-backend        # Logs backend saja
pm2 logs affiliate-frontend       # Logs frontend saja
pm2 restart affiliate-backend     # Restart backend
pm2 restart all                   # Restart semua
pm2 reload ecosystem.config.js    # Reload dengan zero-downtime
pm2 stop all                      # Stop semua
pm2 delete all                    # Hapus semua dari PM2
pm2 monit                         # Real-time monitoring dashboard
```

---

## 🔄 Update / Deploy Terbaru

```bash
cd /var/www/affiliate-video-maker

# Pull terbaru dari GitHub
git pull origin main

# Update backend dependencies (jika ada perubahan requirements.txt)
cd backend && source venv/bin/activate && pip install -r requirements.txt && cd ..

# Rebuild frontend (jika ada perubahan frontend)
cd frontend && npm install && npm run build && cd ..

# Restart PM2
pm2 reload ecosystem.config.js
```

---

## 🔍 Troubleshooting

### Backend tidak bisa start
```bash
pm2 logs affiliate-backend --lines 50
# Cek apakah .env sudah terisi
cat /var/www/affiliate-video-maker/backend/.env
```

### FFmpeg not found
```bash
which ffmpeg
sudo apt install -y ffmpeg
```

### Video upload gagal (413 Request Entity Too Large)
```bash
# Edit Nginx config, pastikan ada:
client_max_body_size 500M;
sudo systemctl reload nginx
```

### Temp files menumpuk
```bash
# Temp files harusnya auto-cleanup setelah setiap request
# Jika perlu manual cleanup:
rm -rf /var/www/affiliate-video-maker/backend/temp_processing/*/
```

---

## 📊 Monitoring

```bash
# Real-time dashboard
pm2 monit

# Lihat penggunaan resource
pm2 status

# Cek logs error saja
pm2 logs --err
```
