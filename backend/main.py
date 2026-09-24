import os
import csv
import uuid
import json
import shutil
import asyncio
import logging
import traceback
import threading
import re
import subprocess
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

import requests
import httpx
import time
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, BackgroundTasks, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import bcrypt
import jwt

load_dotenv()

# ── Security & Auth ───────────────────────────────────────────────────────────
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
JWT_SECRET = os.getenv("JWT_SECRET", "default_secret_if_not_set")
ALGORITHM = "HS256"
security = OAuth2PasswordBearer(tokenUrl="/api/docs-login")

LOGIN_ATTEMPTS = {}  # { "ip_address": {"attempts": int, "locked_until": float} }
LOCKOUT_TIME = 900   # 15 minutes
MAX_FAILED_ATTEMPTS = 5

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow().timestamp() + (24 * 3600)}) # 24 hours
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(security)):
    if not ADMIN_PASSWORD_HASH:
        return "admin" # Skip auth if not configured for dev (fallback)
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# ── Auth Logs (CSV) ───────────────────────────────────────────────────────────
AUTH_LOG_FILE = Path(__file__).parent / "logs" / "login_logs.csv"
def _ensure_auth_log():
    if not AUTH_LOG_FILE.exists():
        AUTH_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(AUTH_LOG_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["timestamp", "ip_address", "status"])

_ensure_auth_log()

def log_auth_attempt(ip_address: str, status: str):
    try:
        with open(AUTH_LOG_FILE, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ip_address, status])
    except Exception as e:
        logger.error(f"Failed to write auth log: {e}")

class LoginRequest(BaseModel):
    password: str

# ── Constants ─────────────────────────────────────────────────────────────────
POLLINATIONS_API_URL = os.getenv("POLLINATIONS_API_URL", "https://gen.pollinations.ai")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")
if not POLLINATIONS_API_KEY:
    raise RuntimeError("POLLINATIONS_API_KEY is not set. Please add it to your .env file.")

BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / "temp_processing"
TEMP_DIR.mkdir(exist_ok=True)

VIDEOS_DIR = BASE_DIR / "static" / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

AUDIOS_DIR = BASE_DIR / "static" / "audios"
AUDIOS_DIR.mkdir(parents=True, exist_ok=True)

SUBS_DIR = BASE_DIR / "static" / "subs"
SUBS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi"}
API_TIMEOUT_SECONDS = 120

# ── Video Library ─────────────────────────────────────────────────────────────
LIBRARY_DIR       = BASE_DIR / "static" / "library"
LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
LIBRARY_META_FILE = BASE_DIR / "logs" / "video_library.json"
LIBRARY_LOCK      = threading.Lock()
VIDEO_LIBRARY_RETENTION_DAYS = int(os.getenv("VIDEO_LIBRARY_RETENTION_DAYS", "30"))

# ── SSE Job Store (in-memory) ─────────────────────────────────────────────────
# Keys: job_id (str)  Values: dict with status/progress/message/video_url/audio_url/error
jobs: dict = {}
JOBS_LOCK = threading.Lock()

# ── Hook Generation Log (CSV) ─────────────────────────────────────────────────
LOGS_DIR   = BASE_DIR / "logs"
LOG_FILE   = LOGS_DIR / "hook_logs.csv"
LOG_LOCK   = threading.Lock()
LOG_HEADER = ["no", "time", "platform", "variation", "input_product", "output_script", "log_id"]
global_row_count = 0

def _ensure_log_header():
    global global_row_count
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(LOG_HEADER)
        global_row_count = 0
    else:
        try:
            with open(LOG_FILE, "r", encoding="utf-8-sig") as f:
                global_row_count = sum(1 for _ in csv.reader(f)) - 1
        except Exception:
            global_row_count = 0

_ensure_log_header()


def append_hook_log(platform: str, variation: str, product: str, script: str) -> str:
    global global_row_count
    log_id = str(uuid.uuid4())
    try:
        with LOG_LOCK:
            global_row_count += 1
            row = [
                global_row_count,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                platform, variation, product, script, log_id,
            ]
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(row)
        logger.info("Hook log appended: #%d | %s | %s", global_row_count, platform, product)
    except Exception as e:
        logger.error("Failed to append hook log: %s", e)
    return log_id


def update_hook_log_script(log_id: str, new_script: str):
    if not log_id:
        return
    try:
        with LOG_LOCK:
            rows = []
            updated = False
            if LOG_FILE.exists():
                with open(LOG_FILE, "r", encoding="utf-8-sig") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if header:
                        rows.append(header)
                        try:
                            log_id_idx = header.index("log_id")
                            script_idx = header.index("output_script")
                        except ValueError:
                            return
                        for row in reader:
                            if len(row) > log_id_idx and row[log_id_idx] == log_id:
                                if len(row) > script_idx:
                                    row[script_idx] = new_script
                                    updated = True
                            rows.append(row)
                
                if updated:
                    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
                        csv.writer(f).writerows(rows)
                    logger.info("Hook log updated for log_id: %s with edited script", log_id)
    except Exception as e:
        logger.error("Failed to update hook log script: %s", e)



def clean_old_videos():
    now = time.time()
    for f in VIDEOS_DIR.glob("*.mp4"):
        try:
            if os.path.exists(f) and os.path.getmtime(f) < now - 7 * 86400:
                os.remove(f)
                logger.info("Auto-deleted old video: %s", f.name)
        except Exception as e:
            logger.error("Error deleting old video %s: %s", f, e)
    for f in AUDIOS_DIR.glob("*.mp3"):
        try:
            if os.path.exists(f) and os.path.getmtime(f) < now - 7 * 86400:
                os.remove(f)
                logger.info("Auto-deleted old audio: %s", f.name)
        except Exception as e:
            logger.error("Error deleting old audio %s: %s", f, e)
    for f in SUBS_DIR.glob("*.srt"):
        try:
            if os.path.exists(f) and os.path.getmtime(f) < now - 7 * 86400:
                os.remove(f)
                logger.info("Auto-deleted old subtitle: %s", f.name)
        except Exception as e:
            logger.error("Error deleting old subtitle %s: %s", f, e)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    TEMP_DIR.mkdir(exist_ok=True)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIOS_DIR.mkdir(parents=True, exist_ok=True)
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    # Bersihkan orphaned temp job dirs yang lebih dari 2 jam (dari crash sebelumnya)
    now = time.time()
    for d in TEMP_DIR.iterdir():
        try:
            if d.is_dir() and (now - d.stat().st_mtime) > 7200:
                shutil.rmtree(d, ignore_errors=True)
                logger.info("Startup cleanup: removed orphaned temp dir %s", d.name)
        except Exception:
            pass
    yield


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(title="Affiliate Video Maker API", lifespan=lifespan)

# Add GZIP Middleware to compress responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "time": datetime.now().isoformat()}

app.mount("/api/videos", StaticFiles(directory=VIDEOS_DIR), name="videos")
app.mount("/api/audios", StaticFiles(directory=AUDIOS_DIR), name="audios")
app.mount("/api/lib-static", StaticFiles(directory=LIBRARY_DIR), name="library_videos")
app.mount("/api/subs", StaticFiles(directory=SUBS_DIR), name="subtitles")


# ── Auth Endpoints ────────────────────────────────────────────────────────────
@app.post("/api/login")
def login(request: Request, payload: LoginRequest):
    ip = request.client.host
    now = time.time()
    
    # Check bruteforce lockout
    if ip in LOGIN_ATTEMPTS:
        if LOGIN_ATTEMPTS[ip]["locked_until"] > now:
            log_auth_attempt(ip, "BLOCKED")
            raise HTTPException(status_code=429, detail="Terlalu banyak percobaan gagal. Coba lagi dalam 15 menit.")
        elif LOGIN_ATTEMPTS[ip]["locked_until"] != 0 and LOGIN_ATTEMPTS[ip]["locked_until"] <= now:
            # Reset after lockout expires
            LOGIN_ATTEMPTS[ip] = {"attempts": 0, "locked_until": 0}
    else:
        LOGIN_ATTEMPTS[ip] = {"attempts": 0, "locked_until": 0}
        
    if not ADMIN_PASSWORD_HASH:
        # Dev mode fallback
        log_auth_attempt(ip, "SUCCESS_DEV")
        return {"access_token": create_access_token({"sub": "admin"}), "token_type": "bearer"}

    if verify_password(payload.password, ADMIN_PASSWORD_HASH):
        LOGIN_ATTEMPTS[ip] = {"attempts": 0, "locked_until": 0}
        log_auth_attempt(ip, "SUCCESS")
        token = create_access_token({"sub": "admin"})
        return {"access_token": token, "token_type": "bearer"}
    else:
        LOGIN_ATTEMPTS[ip]["attempts"] += 1
        if LOGIN_ATTEMPTS[ip]["attempts"] >= MAX_FAILED_ATTEMPTS:
            LOGIN_ATTEMPTS[ip]["locked_until"] = now + LOCKOUT_TIME
            log_auth_attempt(ip, "BLOCKED")
            raise HTTPException(status_code=429, detail="Akun terkunci karena terlalu banyak percobaan gagal.")
        
        log_auth_attempt(ip, "FAILED")
        raise HTTPException(status_code=401, detail="Password salah")

@app.post("/api/docs-login")
def docs_login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    # Re-use the existing logic but map OAuth2 form data
    login_req = LoginRequest(password=form_data.password)
    return login(request, login_req)

@app.get("/api/auth-logs")
def get_auth_logs(current_user: str = Depends(get_current_user)):
    logs = []
    if AUTH_LOG_FILE.exists():
        try:
            with open(AUTH_LOG_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                logs = [row for row in reader]
                logs.reverse() # newest first
        except Exception as e:
            logger.error(f"Error reading auth logs: {e}")
    return {"logs": logs[:100]} # return last 100



# ── Helpers ───────────────────────────────────────────────────────────────────
def cleanup_files(*paths: Path) -> None:
    for p in paths:
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                p.unlink()
        except Exception:
            pass


async def generate_voice_from_pollinations(prompt: str, voice_model: str, output_path: Path) -> list[dict] | None:
    """
    ASYNC: Calls Edge-TTS or Pollinations TTS API.

    Mengembalikan word-boundary timing [{"start": dtk, "end": dtk, "text": str}, ...]
    bila provider menyediakannya (Edge-TTS), selain itu None — dipakai untuk
    penyelarasan timing subtitle.
    """
    if voice_model in ("id-ID-GadisNeural", "whisper"):
        import edge_tts
        actual_voice = "id-ID-GadisNeural"
        logger.info("Generating voice via Edge-TTS | voice: %s (requested: %s), prompt: %s...", actual_voice, voice_model, prompt[:30])
        try:
            communicate = edge_tts.Communicate(prompt, actual_voice)
            word_boundaries: list[dict] = []
            audio_buf = bytearray()
            async for chunk in communicate.stream():
                ctype = chunk.get("type")
                if ctype == "audio":
                    audio_buf.extend(chunk.get("data", b""))
                elif ctype == "WordBoundary":
                    # offset & duration dalam unit 100 nanodetik (seperti TimeSpan ticks)
                    word_boundaries.append({
                        "start": chunk["offset"] / 1e7,
                        "end": (chunk["offset"] + chunk["duration"]) / 1e7,
                        "text": chunk.get("text", ""),
                    })
            with open(output_path, "wb") as f:
                f.write(audio_buf)
            saved = output_path.stat().st_size
            logger.info("Edge-TTS Audio saved: %s (%d bytes, %d word boundaries)",
                        output_path.name, saved, len(word_boundaries))
            if saved < 512:
                raise HTTPException(status_code=502, detail="Edge-TTS returned empty audio.")
            return word_boundaries or None
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Edge-TTS Error: %s", e)
            raise HTTPException(status_code=500, detail=f"Gagal generate suara Edge-TTS: {str(e)}")

    if voice_model.startswith("openai-audio"):
        voice_part = "shimmer"
        if ":" in voice_model:
            voice_part = voice_model.split(":")[1]

        logger.info("Generating voice via Pollinations openai-audio | voice: %s, prompt: %s...", voice_part, prompt[:30])
        headers = {
            "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
            "Content-Type": "application/json",
        }
        
        system_prompt = (
            "Tugas utama Anda adalah membaca ulang teks dari user kata-demi-kata dengan PERSIS, LENGKAP, dan VERBATIM. "
            "JANGAN menjawab pertanyaan, JANGAN merespon secara percakapan, JANGAN menambahkan, mengubah, atau mengurangi kata apa pun. "
            "Bacakan dengan nada suara yang natural, ramah, dan santai seperti narator profesional Indonesia yang berbicara ke teman dekat. "
            "Cukup suarakan teks input tersebut secara persis."
        )

        payload = {
            "model": "openai-audio",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "modalities": ["text", "audio"],
            "audio": {
                "voice": voice_part,
                "format": "mp3"
            }
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{POLLINATIONS_API_URL.rstrip('/')}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=90.0
                )
                response.raise_for_status()
                data = response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    message = data["choices"][0]["message"]
                    if "audio" in message and "data" in message["audio"]:
                        import base64
                        audio_bytes = base64.b64decode(message["audio"]["data"])
                        with open(output_path, "wb") as f:
                            f.write(audio_bytes)
                        
                        saved = output_path.stat().st_size
                        logger.info("openai-audio saved: %s (%d bytes)", output_path.name, saved)
                        if saved < 512:
                            raise HTTPException(status_code=502, detail="API returned empty audio file.")
                        return None
                    else:
                        raise HTTPException(status_code=502, detail="No audio data returned in API response.")
                else:
                    raise HTTPException(status_code=502, detail="No choices returned in API response.")
            except httpx.TimeoutException:
                logger.error("Pollinations openai-audio API timeout (90s)")
                raise HTTPException(status_code=504, detail="AI Voice sedang sibuk (Timeout 90s). Coba lagi.")
            except httpx.HTTPStatusError as e:
                logger.error("Pollinations openai-audio HTTP Error: %s", e)
                raise HTTPException(status_code=e.response.status_code, detail=f"API Voice Error: {e.response.text}")
            except Exception as e:
                logger.error("Unexpected openai-audio Error: %s", e)
                raise HTTPException(status_code=500, detail=f"Gagal generate suara: {str(e)}")

    logger.info("Calling Pollinations TTS (ASYNC) | prompt: %s...", prompt[:30])

    params = {
        "voice": voice_model,
        "private": "true",
        "timestamp": str(int(time.time())),
        "prompt": prompt
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                POLLINATIONS_API_URL + "/voice",
                params=params,
                timeout=60.0,
                headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"}
            )
            response.raise_for_status()

            # Check if it's actual audio
            ct = response.headers.get("Content-Type", "").lower()
            if "audio" not in ct:
                body = response.text[:200]
                raise HTTPException(status_code=502, detail=f"Pollinations returned non-audio ({ct}): {body}")

            with open(output_path, "wb") as f:
                f.write(response.content)

            saved = output_path.stat().st_size
            logger.info("Audio saved: %s (%d bytes)", output_path.name, saved)
            if saved < 512:
                raise HTTPException(status_code=502, detail="Pollinations returned empty audio. Check API key.")

        except httpx.TimeoutException:
            logger.error("Pollinations TTS side timeout (60s)")
            raise HTTPException(status_code=504, detail="AI Voice sedang sibuk (Timeout 60s). Coba lagi.")
        except httpx.HTTPStatusError as e:
            logger.error("Pollinations TTS HTTP Error: %s", e)
            raise HTTPException(status_code=e.response.status_code, detail=f"API Voice Error: {e.response.text}")
        except Exception as e:
            logger.error("Unexpected TTS Error: %s", e)
            raise HTTPException(status_code=500, detail=f"Gagal generate suara: {str(e)}")

    return None




def get_media_duration(file_path: str) -> float:
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of",
            "default=noprint_wrappers=1:nokey=1", file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        logger.warning("ffprobe tidak tersedia/gagal untuk %s (%s) — fallback parse via ffmpeg", file_path, e)
        try:
            out = subprocess.run(["ffmpeg", "-i", file_path], capture_output=True, text=True)
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", out.stderr or "")
            if m:
                h, mnt, sec = int(m.group(1)), int(m.group(2)), float(m.group(3))
                return h * 3600 + mnt * 60 + sec
        except Exception as e2:
            logger.error("Fallback duration parse gagal untuk %s: %s", file_path, e2)
        return 0.0


def get_media_dimensions(file_path: str) -> tuple[int, int]:
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        w_str, h_str = result.stdout.strip().split("x")[:2]
        return int(float(w_str)), int(float(h_str))
    except Exception:
        try:
            out = subprocess.run(["ffmpeg", "-i", file_path], capture_output=True, text=True)
            m = re.search(r"Stream .*Video:.*?(\d{2,5})x(\d{2,5})", out.stderr or "")
            if m:
                return int(m.group(1)), int(m.group(2))
        except Exception as e2:
            logger.error("Fallback dimensi video gagal untuk %s: %s", file_path, e2)
        return 0, 0


# ══════════════════════════════════════════════════════════════════════════════
# AUTO SUBTITLE (burn-in) — pecah skrip → caption → timing → SRT/ASS → filter FFmpeg
# ══════════════════════════════════════════════════════════════════════════════

# Gaya TikTok: putih tebal + outline hitam, blok 1–2 baris di tengah layar.
# Ukuran font/outline dihitung per-resolusi di generate_ass() (satuan piksel,
# karena PlayRes file ASS diset = dimensi output render).

_FFMPEG_HAS_SUBTITLES: bool | None = None


def ffmpeg_supports_subtitles() -> bool:
    """Cek sekali apakah build FFmpeg punya filter 'ass'/'subtitles' (libass)."""
    global _FFMPEG_HAS_SUBTITLES
    if _FFMPEG_HAS_SUBTITLES is None:
        try:
            out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                                 capture_output=True, text=True, timeout=10)
            _FFMPEG_HAS_SUBTITLES = re.search(
                r"^\s*\S+\s+(?:ass|subtitles)\s", out.stdout or "", re.MULTILINE
            ) is not None
        except Exception as e:
            logger.error("Gagal mendeteksi filter subtitles FFmpeg: %s", e)
            _FFMPEG_HAS_SUBTITLES = False
        logger.info("FFmpeg filter subtitles (libass): %s",
                    "TERSEDIA" if _FFMPEG_HAS_SUBTITLES else "TIDAK ADA")
    return bool(_FFMPEG_HAS_SUBTITLES)


# ── Preset gaya caption (burn-in) — dipetakan ke style ASS ─────────────────────
# Warna disimpan dalam notasi BGR libass (&H00BBGGRR).
SUBTITLE_COLOR_PRESETS = {
    "white":   "FFFFFF",
    "yellow":  "00FFFF",   # #FFD400-ish → BGR
    "cyan":    "FFFF00",
    "magenta": "FF00FF",
    "green":   "00FF00",
    "red":     "0000FF",
    "blue":    "FF0000",
    "orange":  "00A5FF",
    "black":   "000000",
}
SUBTITLE_SIZE_PRESETS    = {"sm": 0.040, "md": 0.052, "lg": 0.070}   # fraksi tinggi video
SUBTITLE_OUTLINE_PRESETS = {"thin": 0.005, "md": 0.008, "thick": 0.013}
SUBTITLE_POSITION_PRESETS = {"top": 0.22, "center": 0.46, "bottom": 0.80}
SUBTITLE_DEFAULT_FONT = "DejaVu Sans"


def _normalize_subtitle_style(
    subtitle_size: str = "md",
    subtitle_color: str = "white",
    subtitle_outline_color: str = "black",
    subtitle_outline: str = "md",
    subtitle_position: str = "center",
    subtitle_caps: str = "false",
) -> dict:
    """Validasi & petakan parameter gaya caption dari form menjadi preset tereksekusi."""
    return {
        "font_name": SUBTITLE_DEFAULT_FONT,
        "size_frac": SUBTITLE_SIZE_PRESETS.get(subtitle_size, 0.052),
        "color": SUBTITLE_COLOR_PRESETS.get(subtitle_color, "FFFFFF"),
        "outline_color": (None if subtitle_outline_color == "none"
                          else SUBTITLE_COLOR_PRESETS.get(subtitle_outline_color, "000000")),
        "outline_frac": SUBTITLE_OUTLINE_PRESETS.get(subtitle_outline, 0.008),
        "pos_frac": SUBTITLE_POSITION_PRESETS.get(subtitle_position, 0.46),
        "caps": str(subtitle_caps).lower() not in ("false", "0", "no", ""),
    }


def split_script_into_captions(script: str, max_chars: int = 42) -> list[str]:
    """Pecah skrip voiceover menjadi potongan caption 1–2 baris untuk burn-in."""
    text = re.sub(r"\s+", " ", script or "").strip()
    if not text:
        return []

    # 1) Pecah per kalimat di tanda baca akhir
    sentences = [s.strip() for s in re.split(r"(?<=[.!?;])\s+", text) if s.strip()]

    # 2) Pecah kalimat panjang di koma, lalu di batas kata bila masih panjang
    captions: list[str] = []
    for sentence in sentences:
        parts = [p.strip() for p in re.split(r"(?<=[,])\s+", sentence) if p.strip()]
        buf = ""
        for part in parts:
            candidate = f"{buf} {part}".strip()
            if len(candidate) <= max_chars:
                buf = candidate
                continue
            if buf:
                captions.append(buf)
                buf = ""
            while len(part) > max_chars:
                # Pilih titik potong (spasi) yang mendekati 68% max_chars —
                # potongan lebih seimbang & frase ("lima belas persen") tidak terbelah.
                target = int(max_chars * 0.68)
                best = -1
                for m in re.finditer(r"\s", part[: max_chars + 1]):
                    pos = m.start()
                    if best < 0 or abs(pos - target) < abs(best - target):
                        best = pos
                cut = best if best > 0 else max_chars
                captions.append(part[:cut].strip())
                part = part[cut:].strip()
            buf = part
        if buf:
            captions.append(buf)

    # 3) Gabungkan potongan yang terlalu pendek agar enak dibaca (hard-cap max_chars
    #    supaya selalu muat 2 baris saat burn-in): gabung ke kiri dulu, lalu ke kanan.
    merged: list[str] = []
    for cap in captions:
        if merged and (len(cap) < 14 or len(merged[-1]) < 14) \
                and len(merged[-1]) + 1 + len(cap) <= max_chars:
            merged[-1] = f"{merged[-1]} {cap}"
        else:
            merged.append(cap)
    final: list[str] = []
    i = 0
    while i < len(merged):
        cur = merged[i]
        if len(cur) < 14 and i + 1 < len(merged) \
                and len(cur) + 1 + len(merged[i + 1]) <= max_chars:
            final.append(f"{cur} {merged[i + 1]}")
            i += 2
        else:
            final.append(cur)
            i += 1
    return final


def build_caption_timings(
    captions: list[str],
    audio_duration: float,
    word_boundaries: list[dict] | None = None,
) -> list[tuple[float, float, str]]:
    """
    Susun timing (start, end, teks) per caption.
    - Bila word_boundaries tersedia & jumlah token cocok → timing nyata per kata (akurat).
    - Selain itu → distribusi proporsional berdasarkan panjang karakter ke durasi audio.
    """
    if not captions:
        return []

    token_counts = [len(re.findall(r"\S+", cap)) for cap in captions]
    timings: list[list] = []

    if word_boundaries and sum(token_counts) == len(word_boundaries):
        logger.info("Subtitle timing: memakai word-boundary %d kata", len(word_boundaries))
        idx = 0
        for cap, n in zip(captions, token_counts):
            words = word_boundaries[idx: idx + n]
            idx += n
            timings.append([float(words[0]["start"]), float(words[-1]["end"]), cap])
    else:
        if word_boundaries:
            logger.warning("Subtitle timing: jumlah token (%d) != boundary (%d) — fallback proporsional",
                           sum(token_counts), len(word_boundaries))
        else:
            logger.info("Subtitle timing: fallback proporsional (tanpa word-boundary)")
        weights = [max(len(cap), 8) for cap in captions]
        total_weight = sum(weights)
        lead = min(0.15, max(audio_duration * 0.02, 0.0))
        usable = max(audio_duration - lead - 0.05, 0.5)
        cursor = lead
        for cap, w in zip(captions, weights):
            dur = usable * w / total_weight
            timings.append([cursor, cursor + dur, cap])
            cursor += dur

    # Rapikan: tanpa tumpang-tindih, durasi minimal, caption terakhir tahan sampai akhir audio
    for i, item in enumerate(timings):
        if i + 1 < len(timings):
            nxt = timings[i + 1][0]
            item[1] = max(min(item[1] + 0.1, nxt), item[0] + 0.3)
            if item[1] > nxt:
                timings[i + 1][0] = item[1]
        else:
            # Caption terakhir selalu tahan sampai akhir audio (tanpa melewati)
            item[1] = max(item[1], audio_duration)

    return [(round(a, 3), round(b, 3), c) for a, b, c in timings]


def _format_srt_time(seconds: float) -> str:
    ms = int(round(max(seconds, 0.0) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_ass_time(seconds: float) -> str:
    cs = int(round(max(seconds, 0.0) * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _wrap_caption_text(text: str, wrap_at: int = 20) -> list[str]:
    """
    Pecah caption jadi 1–3 baris SEIMBANG untuk burn-in (meminimalkan lebar
    baris terpanjang, tanpa mengubah/menghilangkan kata).
    """
    text = text.strip()
    if len(text) <= wrap_at:
        return [text]
    words = text.split()
    n = len(words)
    if n < 2:
        return [text]

    def width(i: int, j: int) -> int:
        return sum(len(w) for w in words[i:j]) + (j - i - 1)

    max_lines = min(3, max(1, -(-max(width(0, n), 1) // max(wrap_at, 1))))
    INF = 10 ** 9

    from functools import lru_cache

    @lru_cache(maxsize=None)
    def best(i: int, k: int):
        """(biaya_maksimum_baris, titik_pemotongan) untuk words[i:] menjadi k baris."""
        if k <= 1 or n - i <= 1:
            return width(i, n), (n,)
        best_cost, best_cuts = INF, None
        for j in range(i + 1, n - k + 2):
            w = width(i, j)
            sub_cost, cuts = best(j, k - 1)
            cost = max(w, sub_cost)
            if cost < best_cost:
                best_cost, best_cuts = cost, (j,) + cuts
        return best_cost, best_cuts

    best_cost, best_cuts = best(0, 1)
    for k in range(2, max_lines + 1):
        cost, cuts = best(0, k)
        if cost < best_cost:
            best_cost, best_cuts = cost, cuts

    lines, prev = [], 0
    for cut in best_cuts:
        lines.append(" ".join(words[prev:cut]))
        prev = cut
    return [l for l in lines if l]


def _sanitize_ass_text(text: str) -> str:
    # Hilangkan karakter yang punya arti khusus di ASS ({}, \)
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def generate_srt(timings: list[tuple[float, float, str]]) -> str:
    """Susun file SRT standar (untuk diunduh user) dari daftar timing caption."""
    blocks = []
    for i, (start, end, text) in enumerate(timings, 1):
        body = "\n".join(_wrap_caption_text(_sanitize_ass_text(text)))
        blocks.append(f"{i}\n{_format_srt_time(start)} --> {_format_srt_time(end)}\n{body}\n")
    return "\n".join(blocks)


def generate_ass(
    timings: list[tuple[float, float, str]],
    play_w: int,
    play_h: int,
    style: dict | None = None,
) -> str:
    """
    Susun file ASS untuk burn-in. PlayRes = dimensi output render sehingga
    ukuran font/outline eksak dalam piksel dan posisi dijamin via \\pos().
    Gaya bisa dikustomisasi (font/ukuran/warna/outline/posisi/kapital) via `style`.
    """
    play_w = max(int(play_w), 320)
    play_h = max(int(play_h), 320)
    st = style or _normalize_subtitle_style()

    font_size = max(round(play_h * st["size_frac"]), 16)
    outline_col = st["outline_color"]
    outline = max(round(play_h * st["outline_frac"]), 2) if outline_col else 0
    margin = max(round(play_w * 0.035), 16)
    center_x = play_w // 2
    center_y = round(play_h * st["pos_frac"])
    wrap_at = max(10, int((play_w - 2 * margin) / (0.50 * font_size)))

    header = (
        "[Script Info]\n"
        "; Generated by Affiliate Video Maker (auto subtitle burn-in)\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {play_w}\n"
        f"PlayResY: {play_h}\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: TikTok,{st['font_name']},{font_size},&H00{st['color']},&H000000FF,"
        f"&H00{outline_col or '000000'},&H80000000,-1,0,0,0,100,100,0,0,1,{outline},0,5,"
        f"{margin},{margin},0,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    events = []
    for start, end, text in timings:
        body_text = _sanitize_ass_text(text)
        if st["caps"]:
            body_text = body_text.upper()
        lines = _wrap_caption_text(body_text, wrap_at)
        body = "\\N".join(lines)
        events.append(
            f"Dialogue: 0,{_format_ass_time(start)},{_format_ass_time(end)},"
            f"TikTok,,0,0,0,,{{\\pos({center_x},{center_y})}}{body}"
        )
    return header + "\n".join(events) + "\n"


def build_subtitles(
    script: str,
    audio_path: Path,
    work_dir: Path,
    word_boundaries: list[dict] | None = None,
    play_w: int = 720,
    play_h: int = 1280,
    style: dict | None = None,
    font_id: str = "",
) -> tuple[Path, Path] | None:
    """
    Bangun file subtitle dari skrip voiceover.
    Mengembalikan (path_srt, path_ass) — SRT untuk diunduh user, ASS untuk burn-in.
    `font_id` opsional: custom font (TTF/OTF/TTC) yang di-upload user — disalin ke
    work_dir agar bisa dimuat FFmpeg via fontsdir tanpa instalasi sistem.
    None bila skrip kosong.
    """
    st = dict(style) if style else _normalize_subtitle_style()

    custom = resolve_custom_font(font_id, work_dir) if font_id else None
    if custom:
        st["font_name"] = custom[0]

    captions = split_script_into_captions(script)
    if not captions:
        return None
    audio_dur = get_media_duration(str(audio_path))
    if audio_dur <= 0:
        logger.warning("Durasi audio tidak terdeteksi — timing subtitle memakai estimasi 1.5 dtk/caption")
        audio_dur = max(1.5 * len(captions), 3.0)
    timings = build_caption_timings(captions, audio_dur, word_boundaries)

    srt_path = work_dir / "captions.srt"
    ass_path = work_dir / "captions.ass"
    srt_path.write_text(generate_srt(timings), encoding="utf-8")
    ass_path.write_text(generate_ass(timings, play_w, play_h, st), encoding="utf-8")
    logger.info("Subtitle dibuat: %s + %s (%d caption, audio %.2fs, %dx%d, font=%s)",
                srt_path.name, ass_path.name, len(captions), audio_dur, play_w, play_h,
                st["font_name"])
    return srt_path, ass_path


def compute_output_dimensions(vw: int, vh: int, portrait: bool) -> tuple[int, int]:
    """Dimensi output SETELAH crop 9:16 — harus sama persis dengan rumus crop di FFmpeg."""
    if not vw or not vh:
        return (720, 1280) if portrait else (1280, 720)
    if portrait:
        out_w = min(vw, int(vh * 9 / 32) * 2)   # = trunc(ih*9/16/2)*2
        out_h = min(vh, int(vw * 8 / 9) * 2)    # = trunc(iw*16/9/2)*2
        return out_w, out_h
    return vw, vh


def merge_video_audio(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    duration_mode: str = "auto",
    force_portrait: bool = True,
    subtitle_ass: Path | None = None,
) -> None:
    try:
        logger.info("Merging video with FFmpeg: %s", video_path.name)
        
        vid_dur = get_media_duration(str(video_path))
        aud_dur = get_media_duration(str(audio_path))
        logger.info("Durations - video: %.2fs  audio: %.2fs  mode: %s", vid_dur, aud_dur, duration_mode)

        cmd = ["ffmpeg", "-y"]
        
        if duration_mode == "loop_video" or (duration_mode == "auto" and aud_dur > vid_dur):
            cmd.extend(["-stream_loop", "-1"])
            
        cmd.extend(["-i", str(video_path), "-i", str(audio_path)])

        vf = []
        if force_portrait:
            # Crop ke 9:16 dengan dimensi GENAP (libx264 menolak ganjil) dan aman
            # untuk semua rasio input: landscape, 1:1, 4:5, 9:16, sampai 9:20.
            vf.append("crop='min(iw,trunc(ih*9/16/2)*2)':'min(ih,trunc(iw*16/9/2)*2)'")
        if subtitle_ass is not None:
            ass_filter = f"ass={subtitle_ass.name}"
            # Font custom (hasil upload) disalin ke folder kerja — muat via fontsdir
            # relatif (bebas masalah escaping path di Windows/karakter khusus).
            if any(subtitle_ass.parent.glob("*.tt[fc]")) or any(subtitle_ass.parent.glob("*.otf")):
                ass_filter += ":fontsdir=."
            vf.append(ass_filter)

        if vf:
            cmd.extend(["-vf", ",".join(vf)])
        
        cmd.extend([
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest"
        ])
        
        if not vf:
            cmd.extend(["-c:v", "copy"])
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "28"])

        cmd.append(str(output_path))
        
        logger.info("Running FFmpeg command...")
        
        # Hide window on Windows to prevent popups
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            # cwd ke folder subtitle supaya filter ass tidak butuh path absolut
            # (aman untuk Windows & karakter khusus pada path)
            cwd=str(subtitle_ass.parent) if subtitle_ass is not None else None,
        )
        
        if process.returncode != 0:
            logger.error("FFmpeg error output:\n%s", process.stderr)
            raise RuntimeError(f"FFmpeg returned code {process.returncode}")

        logger.info("Render complete: %s", output_path.name)

    except Exception as e:
        logger.error("merge_video_audio failed:\n%s", traceback.format_exc())
        raise RuntimeError(f"Video merge error: {e}") from e


# ── Endpoint: Generate Video ──────────────────────────────────────────────────
@app.post("/api/process-video")
async def process_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    prompt_text: str = Form(...),
    voice_model: str = Form("whisper"),
    duration_mode: str = Form("auto"),
    force_portrait: str = Form("true"),
    burn_subtitles: str = Form("false"),
    subtitle_font_id: str = Form(""),
    subtitle_size: str = Form("md"),
    subtitle_color: str = Form("white"),
    subtitle_outline_color: str = Form("black"),
    subtitle_outline: str = Form("md"),
    subtitle_position: str = Form("center"),
    subtitle_caps: str = Form("false"),
    log_id: str = Form(None),
    current_user: str = Depends(get_current_user),
):
    suffix = Path(video.filename).suffix.lower()
    if suffix not in (".mp4", ".mov", ".avi"):
        suffix = ".mp4"
    
    job_id = uuid.uuid4().hex
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    raw_video_path = job_dir / f"raw_video{suffix}"
    voice_path = job_dir / "temp_voice.mp3"
    output_path = job_dir / "final_output.mp4"

    try:
        # Save uploaded video
        with open(raw_video_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)

        if raw_video_path.stat().st_size < 1024:
            raise HTTPException(status_code=400, detail="File video terlalu kecil.")

        # CALL ASYNC VOICE GEN (kembalikan word-boundary bila ada, utk timing subtitle)
        word_boundaries = await generate_voice_from_pollinations(prompt_text, voice_model, voice_path)

        if duration_mode not in ("auto", "loop_video", "trim_audio"):
            duration_mode = "auto"
        portrait = force_portrait.lower() not in ("false", "0", "no")
        burn_subs = burn_subtitles.lower() not in ("false", "0", "no")
        subtitle_style = _normalize_subtitle_style(
            subtitle_size, subtitle_color, subtitle_outline_color,
            subtitle_outline, subtitle_position, subtitle_caps,
        )

        # Auto subtitle burn-in (opsional)
        srt_path = ass_path = None
        if burn_subs:
            if not ffmpeg_supports_subtitles():
                raise HTTPException(
                    status_code=500,
                    detail="FFmpeg di server tidak mendukung filter 'ass/subtitles' (libass). "
                           "Matikan Auto Subtitle atau instal FFmpeg build lengkap.",
                )
            vw, vh = get_media_dimensions(str(raw_video_path))
            play_w, play_h = compute_output_dimensions(vw, vh, portrait)
            built = build_subtitles(prompt_text, voice_path, job_dir, word_boundaries,
                                    play_w, play_h, subtitle_style, subtitle_font_id)
            if built:
                srt_path, ass_path = built

        # FFmpeg merge (blocking) - run in thread pool
        await asyncio.to_thread(
            merge_video_audio, raw_video_path, voice_path, output_path,
            duration_mode, portrait, ass_path,
        )

        # Selalu persist hasil (pakai job_id bila tidak ada log_id) agar video tidak hilang
        target_id = log_id or job_id
        if log_id:
            update_hook_log_script(log_id, prompt_text)
        shutil.copy(output_path, VIDEOS_DIR / f"{target_id}.mp4")
        if srt_path is not None:
            shutil.copy(srt_path, SUBS_DIR / f"{target_id}.srt")
        if ass_path is not None:
            shutil.copy(ass_path, SUBS_DIR / f"{target_id}.ass")
        logger.info("Persisted video for id: %s (subtitle: %s)", target_id, bool(srt_path))

        background_tasks.add_task(clean_old_videos)
        background_tasks.add_task(cleanup_files, job_dir)

        return {
            "status": "success",
            "video_url": f"/api/videos/{target_id}.mp4",
            "subtitle_url": f"/api/subs/{target_id}.srt" if srt_path is not None else None,
            "log_id": log_id
        }

    except HTTPException:
        cleanup_files(job_dir)
        raise
    except Exception as e:
        cleanup_files(job_dir)
        logger.error("Unhandled exception in process_video: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# AI HOOK GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
TEXT_API_URL = POLLINATIONS_API_URL

# ── Blacklist kata pembuka statis — dipakai di prompt & post-processing ───────
_BANNED_OPENERS = (
    "Duh", "Eh", "Wah", "Wih", "Aduh", "Astaga", "Wow",
    "Guys", "Bestie", "Gaes", "Bro", "Sis",
    "Jujur", "Jujur nih", "Jujur banget",
    "Serius", "Serius deh", "Serius nih",
    "Beneran", "Beneran deh", "No cap",
    "Oke", "Oke jadi", "Oke guys",
    "Nah", "Nah jadi", "Nah guys",
    "Jadi", "Jadi gini", "Jadi begini",
    "So", "So guys", "Btw",
    "Hei", "Halo", "Hi",
    "Pernah", "Pernah gak", "Pernah nggak", "Pernahkah",
    "Tau gak", "Tau gak sih", "Tahu nggak",
    "Percaya gak", "Percaya nggak",
    "Kalian", "Kalian wajib", "Kalian harus",
    "Stop", "Stop scrolling", "Berhenti",
    "Lagi nyari", "Lagi cari",
    "Capek sama", "Capek dengan",
    "Ini dia", "Ini dia rahasianya",
    "Gak disangka", "Nggak disangka",
    "Sering gak sih", "Sering nggak sih",
    "Aku mau", "Aku mau cerita", "Aku mau share",
    "Mau cerita", "Mau share",
    "Ternyata oh ternyata",
)
_BANNED_OPENERS_STR = ", ".join(_BANNED_OPENERS)  # tanpa quote agar tidak break URI encoding Pollinations

# ── FIX #1 #2 #3 #4: HOOK_SYSTEM_PROMPT ─────────────────────────────────────
HOOK_SYSTEM_PROMPT = f"""Kamu adalah kreator konten TikTok dan Shopee yang sudah sering viral di niche produk rumah tangga dan parenting.
Kamu bicara natural seperti orang biasa yang excited nemuin produk bagus — bukan copywriter yang nulis skrip iklan.

Aturan penulisan:
- DILARANG menulis lebih dari 500 karakter (termasuk spasi).
- Gunakan Bahasa Indonesia gaul yang natural dan relatable
- Tulis angka dalam kata (misal: seratus ribu, bukan 100.000)
- Tulis persentase dalam kata (misal: lima belas persen, bukan 15%) — DILARANG menggunakan simbol %
- Bicara ke satu orang pakai kata "kamu" — bukan ke kerumunan pakai "kalian" atau "guys"
- Langsung mulai tanpa basa-basi atau salam pembuka
- Akhiri dengan kalimat yang mendorong rasa penasaran atau action
- DILARANG KERAS memulai dengan kata-kata berikut karena terdengar bot: {_BANNED_OPENERS_STR}
- DILARANG menggunakan "..." sebagai jeda artifisial lebih dari satu kali"""

# ── FIX #5 #6 #7: HOOK_V2_SYSTEM_PROMPT ─────────────────────────────────────
HOOK_V2_SYSTEM_PROMPT = f"""Kamu adalah kreator video yang sudah viral puluhan kali di TikTok.
Kamu BUKAN copywriter kaku — kamu ORANG SUNGGUHAN yang bicara jujur dan natural.

SIAPA KAMU
Kamu bicara seperti teman yang baru nemuin sesuatu yang bikin kaget, atau pelanggan yang genuinely excited, atau orang yang mau berbagi pengalaman jujur. Nadamu hangat, santai, manusiawi — sama sekali tidak terasa iklan.

ATURAN KERAS — WAJIB DIIKUTI
- DILARANG menulis lebih dari 500 karakter (termasuk spasi).
- DILARANG memulai dengan kata-kata berikut karena terdengar bot: {_BANNED_OPENERS_STR}
- DILARANG menggunakan pola kalimat template apapun
- DILARANG menggunakan emoji atau tanda bintang
- DILARANG menggunakan simbol % — tulis dalam kata (misal: dua puluh persen, bukan 20%)
- DILARANG menulis label seperti VISUAL:, TEKS:, FORMAT:, NARASI:, ANGLE:, atau simbol |
- DILARANG bicara ke kerumunan — gunakan "kamu", bukan "kalian", "guys", "bestie", "gaes"
- DILARANG menggunakan "..." sebagai jeda artifisial lebih dari satu kali
- Output HANYA kalimat yang diucapkan — murni voiceover, tidak ada deskripsi teknis
- Maksimal 5 kalimat — singkat, padat, langsung menghantam

TUJUAN EMOSI (pilih satu sesuai instruksi):
- PROBLEM: Audiens merasa "itu gue banget" dalam 2 detik pertama
- PERSONAL: Audiens percaya karena kamu terasa seperti orang biasa yang sudah nyoba
- EDUCATION: Audiens merasa dapat insight gratis yang berguna, bukan dijuali
- CONTRA: Audiens terpancing karena kamu bilang sesuatu yang melawan asumsi mereka
- VISUAL: Audiens berhenti scroll karena kalimat pertama terasa seperti sedang menyaksikan sesuatu yang mengejutkan

TUGAS: Tulis SATU hook voiceover yang sangat natural berdasarkan produk di bawah."""

# ── HOOK_STYLE_PROMPTS ───────────────────────────────────────────────────────
# Keterangan panjang output per variasi:
#   SINGKAT (5-6 kalimat, ~15-20 detik) : viral, fomo, flash, bundle  → impulsif, energi tinggi
#   PANJANG (8-10 kalimat, ~25-40 detik): shock, story, review, premium, semua v2 → butuh arc & build-up
HOOK_STYLE_PROMPTS = {
    "tiktok": {
        "viral": (
            "Buat NARASI VOICEOVER viral impulsif — 5 sampai 6 kalimat, audio 15 sampai 20 detik. "
            "Struktur: "
            "(1) Hook pembuka yang mengejutkan — langsung sebut angka, fakta, atau situasi konkret, "
            "(2) perkuat dengan satu social proof spesifik yang membuat audiens percaya, "
            "(3) sampaikan satu keunggulan utama produk yang paling bikin penasaran, "
            "(4) ciptakan urgensi atau FOMO yang terasa real, "
            "(5) tutup dengan CTA singkat yang mendorong action sekarang. "
            "Energi harus tinggi dari awal sampai akhir — tidak boleh ada kalimat yang flat."
        ),
        "shock": (
            "Buat NARASI VOICEOVER PENUH dengan format shock & reveal — 8 sampai 10 kalimat, audio maximal 25 detik. "
            "Struktur: "
            "(1) Buka dari titik di mana kamu sudah memegang produknya dan baru sadar sesuatu yang mengejutkan, "
            "(2) bangun rasa penasaran dengan detail spesifik yang tidak terduga, "
            "(3) ungkap twist utama yang membuat audiens tidak menyangka, "
            "(4) perkuat dengan satu bukti konkret atau pengalaman nyata, "
            "(5) tutup dengan CTA yang terasa natural. "
            "JANGAN mulai dengan kata jujur, serius, atau beneran."
        ),
        "story": (
            "Buat NARASI VOICEOVER PENUH dengan format cerita personal — 8 sampai 10 kalimat, audio minimal 25 detik. "
            "Struktur: "
            "(1) Mulai dari momen spesifik yang sedang terjadi — bukan dari penyesalan atau pertanyaan, "
            "(2) gambarkan situasi sebelum menemukan produk ini dengan detail yang relatable, "
            "(3) ceritakan momen penemuan yang mengubah segalanya, "
            "(4) tunjukkan perubahan konkret yang dirasakan setelah pakai produk, "
            "(5) tutup dengan rekomendasi natural ke satu orang yang mungkin mengalami hal sama. "
            "JANGAN mulai dengan pernah, dulu, atau pertanyaan ke audiens."
        ),
        "fomo": (
            "Buat NARASI VOICEOVER FOMO urgency — 5 sampai 6 kalimat, audio 15 sampai 20 detik maximal 30 detik. "
            "Struktur: "
            "(1) Hook pembuka dengan angka stok atau waktu yang spesifik — langsung ke fakta mendesak, "
            "(2) tunjukkan apa yang didapat jika action sekarang — nilai konkret dalam rupiah, "
            "(3) gambarkan kerugian nyata jika menunda — spesifik dan terasa real, "
            "(4) perkuat dengan social proof singkat bahwa orang lain sudah ambil keputusan, "
            "(5) tutup dengan CTA yang menciptakan urgensi tanpa terkesan memaksa. "
            "Setiap kalimat harus terasa mendesak — tidak ada ruang untuk kalimat santai."
        ),
    },
    "shopee": {
        "flash": (
            "Buat NARASI VOICEOVER flash sale Shopee — 5 sampai 6 kalimat, audio 15 sampai 20 detik maximal 30 detik. "
            "Struktur: "
            "(1) Hook pembuka dengan harga final atau angka diskon yang mengejutkan — langsung ke angka, "
            "(2) breakdown kenapa harga ini gila — bandingkan harga normal vs harga sekarang, "
            "(3) tunjukkan bukti laku keras: angka terjual atau rating toko, "
            "(4) sebut kombinasi voucher atau bonus yang membuat deal makin tidak masuk akal, "
            "(5) tutup dengan CTA yang menekan urgensi flash sale — stok atau waktu terbatas. "
            "Nada harus excited dan cepat — seperti teman yang baru nemuin deal gila."
        ),
        "review": (
            "Buat NARASI VOICEOVER PENUH dengan format review jujur Shopee — 8 sampai 10 kalimat, audio minimal 25 detik. "
            "Struktur: "
            "(1) Mulai dari detail spesifik saat unboxing atau pertama kali pakai — bukan dari ekspektasi awal, "
            "(2) ceritakan kesan pertama yang konkret dan spesifik, "
            "(3) tunjukkan satu atau dua keunggulan yang paling mengejutkan setelah dipakai, "
            "(4) bandingkan dengan produk lain yang pernah dicoba secara jujur, "
            "(5) tutup dengan rekomendasi organik ke satu orang — bukan ke semua orang. "
            "JANGAN mulai dengan kata jujur, serius, atau beneran."
        ),
        "bundle": (
            "Buat NARASI VOICEOVER bundle deal Shopee — 5 sampai 6 kalimat, audio 15 sampai 20 detik maximal 30 detik. "
            "Struktur: "
            "(1) Hook pembuka dengan total hemat dalam rupiah yang langsung mengejutkan, "
            "(2) sebutkan isi bundle satu per satu dengan nilai masing-masing agar terasa tidak masuk akal, "
            "(3) ungkap bonus item paling mengejutkan yang tidak terduga, "
            "(4) perkuat dengan eksklusivitas — kenapa deal ini tidak akan ada lagi, "
            "(5) tutup dengan CTA yang mendorong klik sebelum kehabisan. "
            "Nada harus excited — seperti teman yang excited kasih info deal rahasia."
        ),
        "premium": (
            "Buat NARASI VOICEOVER PENUH dengan format premium value — 8 sampai 10 kalimat, audio maximal 30 detik. "
            "Struktur: "
            "(1) Buka dengan kontras harga vs kualitas yang terasa tidak masuk akal — langsung ke angka, "
            "(2) perkuat dengan satu detail spesifik yang membuktikan kualitas premium, "
            "(3) bandingkan secara jujur dengan produk sejenis yang lebih mahal, "
            "(4) ceritakan satu pengalaman atau momen konkret saat kualitasnya terasa, "
            "(5) tutup dengan CTA yang memperkuat rasa eksklusif tanpa terkesan memaksa."
        ),
    },
}

# ── FIX #8 #9: v2_map — hapus notasi panah, perkaya education ────────────────
_V2_MAP = {
    "v2_problem": (
        "Angle: PROBLEM-BASED — tulis NARASI VOICEOVER PENUH, bukan sekadar hook pendek. "
        "Struktur: "
        "(1) Buka dengan satu masalah sangat spesifik yang dirasakan orang tua — bukan masalah umum, "
        "(2) agitasi masalah itu: gambarkan dampaknya yang bikin frustrasi atau rugi, "
        "(3) hadirkan produk sebagai solusi secara natural tanpa terasa jualan, "
        "(4) tunjukkan satu bukti konkret bahwa produk ini benar-benar menyelesaikan masalah tadi, "
        "(5) tutup dengan CTA yang mendorong action tanpa terkesan memaksa. "
        "Target panjang: 5 sampai 8 kalimat agar audio minimal 20 detik maximal 30 detik."
    ),
    "v2_personal": (
        "Angle: PERSONAL EXPERIENCE — tulis NARASI VOICEOVER PENUH, bukan sekadar hook pendek. "
        "Struktur: "
        "(1) Buka dari momen spesifik setelah memakai produk — langsung ke reaksi atau kejadian konkretnya, "
        "(2) ceritakan detail pengalaman yang paling mengejutkan atau berbeda dari ekspektasi, "
        "(3) hubungkan ke situasi sebelum pakai produk ini — kontrasnya harus terasa nyata, "
        "(4) perkuat dengan satu detail spesifik yang membuat pengalaman ini credible, "
        "(5) tutup dengan rekomendasi yang terasa natural seperti cerita ke teman, bukan ke kamera. "
        "Target panjang: 5 sampai 8 kalimat agar audio minimal 20 detik maximal 30 detik."
    ),
    "v2_education": (
        "Angle: EDUCATION — tulis NARASI VOICEOVER PENUH, bukan sekadar hook pendek. "
        "Struktur: (1) Buka dengan satu fakta atau insight mengejutkan yang jarang orang tau, "
        "(2) jelaskan kenapa ini penting atau relevan untuk produk ini, "
        "(3) hubungkan ke pengalaman nyata yang relatable, "
        "(4) tutup dengan CTA yang mendorong rasa ingin tau atau action. "
        "Target panjang: 5 sampai 8 kalimat agar audio minimal 20 detik maximal 30 detik. "
        "Audiens harus merasa dapat ilmu gratis, bukan sedang ditonton iklan. "
        "DILARANG menggunakan simbol persen — tulis dalam kata."
    ),
    "v2_contra": (
        "Angle: CONTRA OPINION — tulis NARASI VOICEOVER PENUH, bukan sekadar hook pendek. "
        "Struktur: "
        "(1) Buka dengan pernyataan berani yang melawan asumsi umum soal produk atau mainan ini, "
        "(2) akui kenapa banyak orang percaya asumsi itu — tunjukkan kamu mengerti sudut pandang mereka, "
        "(3) sajikan argumen balik dengan logika yang kuat dan fakta konkret, "
        "(4) perkuat dengan satu bukti nyata atau pengalaman yang mendukung pendapatmu, "
        "(5) tutup dengan CTA yang mengajak audiens untuk buktikan sendiri. "
        "Target panjang: 5 sampai 8 kalimat agar audio minimal 20 detik maximal 30 detik. "
        "Harus terasa berani tapi masuk akal — bukan sensasional."
    ),
    "v2_visual": (
        "Angle: VISUAL SHOCK — tulis NARASI VOICEOVER PENUH yang diucapkan sepanjang video, bukan cuma hook. "
        "Struktur: (1) Kalimat pertama adalah reaksi spontan menyaksikan sesuatu yang mengejutkan, "
        "(2) lanjutkan dengan voiceover yang menggambarkan apa yang terjadi seolah kamu sedang melihatnya, "
        "(3) sampaikan fakta atau keunggulan produk yang terungkap dari adegan itu, "
        "(4) tutup dengan CTA singkat yang natural. "
        "Target panjang: 5 sampai 8 kalimat agar audio minimal 20 detik maximal 30 detik. "
        "DILARANG menulis VISUAL:, TEKS:, FORMAT:, NARASI:, atau simbol | dalam output. "
        "Output HANYA kata-kata yang diucapkan — bukan deskripsi teknis atau stage direction."
    ),
}

def _clean_hook_output(text: str, variation: str) -> str:
    if variation == "v2_visual":
        teks_parts = re.findall(r'TEKS:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if teks_parts:
            text = " ".join(t.strip() for t in teks_parts)
            logger.info("v2_visual: extracted %d TEKS: part(s)", len(teks_parts))
        else:
            text = re.sub(r'(VISUAL|TEKS|FORMAT|NARASI|ANGLE)\s*:\s*', '', text, flags=re.IGNORECASE)
            text = text.replace('|', ' ').strip()
            text = re.sub(r'\s{2,}', ' ', text)

    banned_pattern = '|'.join(re.escape(w) for w in _BANNED_OPENERS)
    cleaned = re.sub(rf'^({banned_pattern})[,!\s]+', '', text, flags=re.IGNORECASE)
    if cleaned != text:
        logger.info("Opener statis dibersihkan: '%s...' -> '%s...'", text[:30], cleaned[:30])
        text = cleaned[0].upper() + cleaned[1:] if cleaned else text

    if '%' in text:
        text = re.sub(r'(\d+)\s*%', lambda m: m.group(1) + ' persen', text)
        text = text.replace('%', ' persen')
        logger.info("Simbol persen dibersihkan dari output hook")

    return text.strip()

@app.post("/api/generate-hook")
async def generate_hook(
    product_name: str = Form(..., description="Nama produk affiliate"),
    hook_type: str    = Form("tiktok", description="Platform: tiktok atau shopee"),
    variation: str    = Form("viral",  description="Variasi hook style"),
    current_user: str = Depends(get_current_user),
):
    if not product_name.strip():
        raise HTTPException(status_code=400, detail="product_name tidak boleh kosong.")

    hook_type = hook_type.lower().strip()
    variation = variation.lower().strip()

    if variation in _V2_MAP:
        current_system_prompt = HOOK_V2_SYSTEM_PROMPT
        style_instruction = _V2_MAP[variation]
    else:
        current_system_prompt = HOOK_SYSTEM_PROMPT
        styles = HOOK_STYLE_PROMPTS.get(hook_type, HOOK_STYLE_PROMPTS["tiktok"])
        style_instruction = styles.get(variation, list(styles.values())[0])

    platform_label = "TikTok" if hook_type == "tiktok" else "Shopee"
    user_prompt = (
        f"Produk: {product_name}\n"
        f"Platform: {platform_label}\n"
        f"Instruksi: {style_instruction}\n\n"
        f"Tulis hooknya sekarang, langsung mulai tanpa penjelasan:"
    )

    logger.info("Generating hook (ASYNC) | product=%s platform=%s variation=%s",
                product_name, hook_type, variation)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{TEXT_API_URL.rstrip('/')}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "openai",
                    "messages": [
                        {"role": "system", "content": current_system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 600 if variation in (
                        "v2_education", "v2_visual", "v2_problem", "v2_personal", "v2_contra",
                        "shock", "story", "review", "premium"
                    ) else 400,
                    "private": True,
                },
                timeout=45.0,
            )
            response.raise_for_status()
            data = response.json()
            script = data["choices"][0]["message"]["content"].strip()
            script = _clean_hook_output(script, variation)

            log_id = append_hook_log(hook_type, variation, product_name, script)
            
            return {
                "script": script,
                "product": product_name,
                "platform": hook_type,
                "variation": variation,
                "log_id": log_id,
                "is_visual_only": variation == "v2_visual",
                "status": "success"
            }

        except httpx.TimeoutException:
            logger.error("Pollinations text API timeout (45s)")
            raise HTTPException(status_code=504, detail="AI sedang sibuk (Timeout 45s). Coba lagi.")
        except httpx.HTTPStatusError as e:
            logger.error("Pollinations API HTTP Error: %s", e)
            raise HTTPException(status_code=e.response.status_code, detail=f"API AI Error: {e.response.text}")
        except Exception as e:
            logger.error("Error generating hook: %s", str(e))
            raise HTTPException(status_code=500, detail=f"Gagal generate hook: {str(e)}")


# ── Endpoint: Generate Audio Only ─────────────────────────────────────────────
@app.post("/api/generate-audio")
async def generate_audio_only(
    background_tasks: BackgroundTasks,
    prompt_text: str = Form(...),
    voice_model: str = Form("whisper"),
    log_id: str      = Form(None),
    current_user: str = Depends(get_current_user),
):
    job_id = str(uuid.uuid4())
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    try:
        voice_path = job_dir / "voice.mp3"
        await generate_voice_from_pollinations(prompt_text, voice_model, voice_path)

        target_id = log_id if log_id else job_id
        if log_id:
            update_hook_log_script(log_id, prompt_text)
        shutil.copy(voice_path, AUDIOS_DIR / f"{target_id}.mp3")
        logger.info("Persisted audio for id: %s", target_id)

        background_tasks.add_task(clean_old_videos)
        background_tasks.add_task(cleanup_files, job_dir)

        return {"status": "success", "audio_url": f"/api/audios/{target_id}.mp3", "log_id": target_id}

    except HTTPException:
        cleanup_files(job_dir)
        raise
    except Exception as e:
        cleanup_files(job_dir)
        logger.error("Error in /api/generate-audio: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ── Log Viewer Endpoints ───────────────────────────────────────────────────────
@app.get("/api/logs")
def get_logs(current_user: str = Depends(get_current_user)):
    _ensure_log_header()
    rows = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                log_id = row.get("log_id")
                if log_id:
                    if (VIDEOS_DIR / f"{log_id}.mp4").exists():
                        row["video_url"] = f"/api/videos/{log_id}.mp4"
                    if (AUDIOS_DIR / f"{log_id}.mp3").exists():
                        row["audio_url"] = f"/api/audios/{log_id}.mp3"
                    if (SUBS_DIR / f"{log_id}.srt").exists():
                        row["srt_url"] = f"/api/subs/{log_id}.srt"
                rows.append(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {e}")
    return {"total": len(rows), "logs": rows}


@app.get("/api/logs/download")
def download_logs(current_user: str = Depends(get_current_user)):
    _ensure_log_header()
    if not LOG_FILE.exists():
        raise HTTPException(status_code=404, detail="Log file not found.")
    return FileResponse(path=str(LOG_FILE), media_type="text/csv", filename="hook_logs.csv")


@app.delete("/api/logs/clear")
def clear_logs(current_user: str = Depends(get_current_user)):
    with LOG_LOCK:
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(LOG_HEADER)
    logger.info("Hook logs cleared.")
    return {"status": "ok", "message": "Log file has been cleared."}


# ══════════════════════════════════════════════════════════════════════════════
# VIDEO LIBRARY
# ══════════════════════════════════════════════════════════════════════════════

def _read_library_meta() -> list:
    if not LIBRARY_META_FILE.exists():
        return []
    try:
        with open(LIBRARY_META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_library_meta(entries: list) -> None:
    LIBRARY_META_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LIBRARY_META_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def _clean_library_old_files():
    """Remove library entries and files older than VIDEO_LIBRARY_RETENTION_DAYS."""
    cutoff = time.time() - VIDEO_LIBRARY_RETENTION_DAYS * 86400
    with LIBRARY_LOCK:
        entries = _read_library_meta()
        kept = []
        for entry in entries:
            vid_path = LIBRARY_DIR / entry["filename"]
            if entry.get("uploaded_at", 0) < cutoff:
                try:
                    vid_path.unlink(missing_ok=True)
                    logger.info("Library auto-deleted: %s", entry["filename"])
                except Exception:
                    pass
            else:
                kept.append(entry)
        if len(kept) != len(entries):
            _write_library_meta(kept)


@app.post("/api/library/upload")
async def library_upload(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    display_name: str = Form(""),
    current_user: str = Depends(get_current_user),
):
    """Upload a video to the persistent library for re-use."""
    suffix = Path(video.filename).suffix.lower()
    if suffix not in {".mp4", ".mov", ".avi"}:
        suffix = ".mp4"

    lib_id = uuid.uuid4().hex
    filename = f"{lib_id}{suffix}"
    dest_path = LIBRARY_DIR / filename

    try:
        with open(dest_path, "wb") as buf:
            shutil.copyfileobj(video.file, buf)
        size = dest_path.stat().st_size
        if size < 1024:
            dest_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="File video terlalu kecil.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan video: {e}")

    original_name = display_name.strip() or video.filename or filename
    entry = {
        "id": lib_id,
        "filename": filename,
        "original_name": original_name,
        "size": size,
        "uploaded_at": time.time(),
        "video_url": f"/api/lib-static/{filename}",
    }

    with LIBRARY_LOCK:
        entries = _read_library_meta()
        entries.append(entry)
        _write_library_meta(entries)

    background_tasks.add_task(_clean_library_old_files)
    logger.info("Library upload: %s (%d bytes)", original_name, size)
    return {"status": "success", "video": entry}


@app.get("/api/library")
def library_list(current_user: str = Depends(get_current_user)):
    """Return all library videos that still exist on disk."""
    with LIBRARY_LOCK:
        entries = _read_library_meta()
    result = []
    for entry in entries:
        vid_path = LIBRARY_DIR / entry["filename"]
        if vid_path.exists():
            result.append(entry)
    # Newest first
    result.sort(key=lambda e: e.get("uploaded_at", 0), reverse=True)
    return {"total": len(result), "videos": result}


@app.delete("/api/library/{video_id}")
def library_delete(video_id: str,
    current_user: str = Depends(get_current_user)
):
    """Delete a video from the library."""
    with LIBRARY_LOCK:
        entries = _read_library_meta()
        new_entries = [e for e in entries if e["id"] != video_id]
        deleted = [e for e in entries if e["id"] == video_id]
        if not deleted:
            raise HTTPException(status_code=404, detail="Video tidak ditemukan di library.")
        for e in deleted:
            try:
                (LIBRARY_DIR / e["filename"]).unlink(missing_ok=True)
            except Exception:
                pass
        _write_library_meta(new_entries)
    logger.info("Library deleted: %s", video_id)
    return {"status": "ok", "deleted_id": video_id}


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM FONTS — untuk subtitle burn-in (format standar: TTF / OTF / TTC)
# ══════════════════════════════════════════════════════════════════════════════
FONTS_DIR       = BASE_DIR / "static" / "fonts"
FONTS_DIR.mkdir(parents=True, exist_ok=True)
FONTS_META_FILE = BASE_DIR / "logs" / "fonts.json"
FONTS_LOCK      = threading.Lock()
ALLOWED_FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}
MAX_FONT_BYTES  = 5 * 1024 * 1024  # 5 MB


def _read_fonts_meta() -> list:
    if not FONTS_META_FILE.exists():
        return []
    try:
        with open(FONTS_META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_fonts_meta(entries: list) -> None:
    FONTS_META_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FONTS_META_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def _extract_font_family(path: Path) -> str | None:
    """Baca nama family asli dari file font standar (TTF/OTF/TTC) via fontTools."""
    try:
        from fontTools.ttLib import TTFont, TTCollection
        if path.suffix.lower() == ".ttc":
            coll = TTCollection(str(path), lazy=True)
            if not coll.fonts:
                return None
            name = coll.fonts[0]["name"]
        else:
            name = TTFont(str(path), lazy=True)["name"]
        family = name.getDebugName(16) or name.getDebugName(1)  # typographic family → family
        return family.strip() if family else None
    except Exception as e:
        logger.error("Gagal membaca nama family font %s: %s", path, e)
        return None


def resolve_custom_font(font_id: str, work_dir: Path) -> tuple[str, Path] | None:
    """
    Salin file font custom ke folder kerja (untuk opsi fontsdir FFmpeg) dan
    kembalikan (nama_family, path_file). None bila font_id kosong/tidak ditemukan.
    """
    if not font_id:
        return None
    entry = next((e for e in _read_fonts_meta() if e.get("id") == font_id), None)
    if not entry:
        return None
    src = FONTS_DIR / entry["filename"]
    if not src.exists():
        return None
    dest = work_dir / entry["filename"]
    shutil.copy(src, dest)
    logger.info("Custom font disiapkan: %s (%s)", entry["family"], entry["filename"])
    return entry["family"], dest


@app.post("/api/fonts/upload")
async def fonts_upload(
    font: UploadFile = File(...),
    display_name: str = Form(""),
    current_user: str = Depends(get_current_user),
):
    """Upload custom font (TTF/OTF/TTC) untuk subtitle burn-in."""
    suffix = Path(font.filename or "").suffix.lower()
    if suffix not in ALLOWED_FONT_EXTENSIONS:
        raise HTTPException(status_code=400,
                            detail="Format font tidak didukung. Gunakan .ttf, .otf, atau .ttc "
                                   "(format standar TrueType/OpenType).")

    font_id = uuid.uuid4().hex
    dest_path = FONTS_DIR / f"{font_id}{suffix}"
    try:
        with open(dest_path, "wb") as buf:
            shutil.copyfileobj(font.file, buf)
        size = dest_path.stat().st_size
        if size < 64:
            dest_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="File font terlalu kecil / kosong.")
        if size > MAX_FONT_BYTES:
            dest_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Ukuran font maksimal 5 MB.")
        family = _extract_font_family(dest_path)
        if not family:
            dest_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400,
                                detail="File font tidak valid atau tidak punya nama family.")
    except HTTPException:
        raise
    except Exception as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan font: {e}")

    entry = {
        "id": font_id,
        "filename": dest_path.name,
        "family": family,
        "display_name": display_name.strip() or family,
        "size": size,
        "uploaded_at": time.time(),
    }
    with FONTS_LOCK:
        entries = _read_fonts_meta()
        entries.append(entry)
        _write_fonts_meta(entries)
    logger.info("Font upload: %s (%s, %d bytes)", entry["display_name"], family, size)
    return {"status": "success", "font": entry}


@app.get("/api/fonts")
def fonts_list(current_user: str = Depends(get_current_user)):
    """Daftar custom font yang tersedia untuk subtitle."""
    with FONTS_LOCK:
        entries = _read_fonts_meta()
    result = [e for e in entries if (FONTS_DIR / e["filename"]).exists()]
    result.sort(key=lambda e: e.get("uploaded_at", 0), reverse=True)
    return {"total": len(result), "fonts": result}


@app.delete("/api/fonts/{font_id}")
def fonts_delete(font_id: str, current_user: str = Depends(get_current_user)):
    """Hapus custom font."""
    with FONTS_LOCK:
        entries = _read_fonts_meta()
        deleted = [e for e in entries if e["id"] == font_id]
        if not deleted:
            raise HTTPException(status_code=404, detail="Font tidak ditemukan.")
        for e in deleted:
            try:
                (FONTS_DIR / e["filename"]).unlink(missing_ok=True)
            except Exception:
                pass
        _write_fonts_meta([e for e in entries if e["id"] != font_id])
    logger.info("Font deleted: %s", font_id)
    return {"status": "ok", "deleted_id": font_id}


# ══════════════════════════════════════════════════════════════════════════════
# SSE JOB SYSTEM — Non-blocking video render with real-time progress
# ══════════════════════════════════════════════════════════════════════════════

def _set_job(job_id: str, **kwargs):
    with JOBS_LOCK:
        if job_id not in jobs:
            jobs[job_id] = {}
        jobs[job_id].update(kwargs)


def _cleanup_old_jobs():
    """Remove job entries older than 1 hour."""
    cutoff = time.time() - 3600
    with JOBS_LOCK:
        stale = [jid for jid, j in jobs.items() if j.get("created_at", 0) < cutoff]
        for jid in stale:
            del jobs[jid]
    if stale:
        logger.info("Cleaned up %d stale job(s)", len(stale))


async def _run_video_job(
    job_id: str,
    raw_video_path: Path,
    voice_path: Path,
    output_path: Path,
    job_dir: Path,
    prompt_text: str,
    voice_model: str,
    duration_mode: str,
    portrait: bool,
    burn_subtitles: bool,
    subtitle_style: dict | None,
    subtitle_font_id: str,
    log_id: str | None,
):
    """Background coroutine that executes the full render pipeline with SSE status updates."""
    try:
        # Stage 1: Generate voice
        _set_job(job_id, status="generating_voice", progress=10, message="🎙️ Membuat AI voiceover...")
        word_boundaries = await generate_voice_from_pollinations(prompt_text, voice_model, voice_path)

        # Stage 2: Auto subtitle (opsional)
        srt_path = ass_path = None
        if burn_subtitles:
            _set_job(job_id, status="generating_subtitles", progress=30, message="📝 Menyusun subtitle otomatis...")
            if not ffmpeg_supports_subtitles():
                raise HTTPException(
                    status_code=500,
                    detail="FFmpeg di server tidak mendukung filter 'ass/subtitles' (libass). "
                           "Matikan Auto Subtitle atau instal FFmpeg build lengkap.",
                )
            vw, vh = get_media_dimensions(str(raw_video_path))
            play_w, play_h = compute_output_dimensions(vw, vh, portrait)
            built = build_subtitles(prompt_text, voice_path, job_dir, word_boundaries,
                                    play_w, play_h, subtitle_style, subtitle_font_id)
            if built:
                srt_path, ass_path = built

        # Stage 3: Merge video
        _set_job(job_id, status="merging_video", progress=45, message="🎬 Menggabungkan video + audio...")
        await asyncio.to_thread(
            merge_video_audio, raw_video_path, voice_path, output_path,
            duration_mode, portrait, ass_path,
        )

        # Stage 4: Persist — selalu simpan (pakai job_id bila tidak ada log_id)
        _set_job(job_id, status="saving", progress=85, message="💾 Menyimpan hasil render...")
        target_id = log_id or job_id
        if log_id:
            update_hook_log_script(log_id, prompt_text)
        shutil.copy(output_path, VIDEOS_DIR / f"{target_id}.mp4")
        if srt_path is not None:
            shutil.copy(srt_path, SUBS_DIR / f"{target_id}.srt")
        if ass_path is not None:
            shutil.copy(ass_path, SUBS_DIR / f"{target_id}.ass")
        video_url = f"/api/videos/{target_id}.mp4"
        logger.info("SSE job persisted video for id: %s (subtitle: %s)", target_id, bool(srt_path))

        _set_job(
            job_id,
            status="done",
            progress=100,
            message="✅ Selesai!",
            video_url=video_url,
            subtitle_url=f"/api/subs/{target_id}.srt" if srt_path is not None else None,
        )
        cleanup_files(job_dir)
        clean_old_videos()

    except HTTPException as e:
        _set_job(job_id, status="error", progress=0, message="❌ Gagal", error=e.detail)
        cleanup_files(job_dir)
    except Exception as e:
        logger.error("SSE job %s failed: %s", job_id, traceback.format_exc())
        _set_job(job_id, status="error", progress=0, message="❌ Gagal", error=str(e))
        cleanup_files(job_dir)


@app.post("/api/jobs/submit")
async def submit_job(
    video: UploadFile = File(None),
    prompt_text: str = Form(...),
    voice_model: str = Form("id-ID-GadisNeural"),
    duration_mode: str = Form("auto"),
    force_portrait: str = Form("true"),
    burn_subtitles: str = Form("false"),
    subtitle_font_id: str = Form(""),
    subtitle_size: str = Form("md"),
    subtitle_color: str = Form("white"),
    subtitle_outline_color: str = Form("black"),
    subtitle_outline: str = Form("md"),
    subtitle_position: str = Form("center"),
    subtitle_caps: str = Form("false"),
    log_id: str = Form(None),
    library_video_id: str = Form(None),
    current_user: str = Depends(get_current_user),
):
    """
    Submit a video render job. Returns job_id immediately.
    Client should then poll GET /api/jobs/{job_id}/stream for SSE progress.
    """
    job_id = uuid.uuid4().hex
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Tentukan sumber video: upload atau library (validasi sebelum diproses)
    if library_video_id:
        # Use video from library
        with LIBRARY_LOCK:
            entries = _read_library_meta()
        lib_entry = next((e for e in entries if e["id"] == library_video_id), None)
        if not lib_entry:
            raise HTTPException(status_code=404, detail="Video library tidak ditemukan.")
        lib_path = LIBRARY_DIR / lib_entry["filename"]
        if not lib_path.exists():
            raise HTTPException(status_code=404, detail="File video library sudah dihapus.")
        raw_video_path = job_dir / lib_path.name
        shutil.copy(lib_path, raw_video_path)
    else:
        if video is None or not video.filename:
            cleanup_files(job_dir)
            raise HTTPException(status_code=400,
                                detail="Wajib upload video atau pilih video dari library.")
        suffix = Path(video.filename).suffix.lower()
        if suffix not in {".mp4", ".mov", ".avi"}:
            suffix = ".mp4"
        raw_video_path = job_dir / f"raw_video{suffix}"
        with open(raw_video_path, "wb") as buf:
            shutil.copyfileobj(video.file, buf)
        if raw_video_path.stat().st_size < 1024:
            cleanup_files(job_dir)
            raise HTTPException(status_code=400, detail="File video terlalu kecil.")

    voice_path  = job_dir / "temp_voice.mp3"
    output_path = job_dir / "final_output.mp4"

    if duration_mode not in ("auto", "loop_video", "trim_audio"):
        duration_mode = "auto"
    portrait = force_portrait.lower() not in ("false", "0", "no")
    burn_subs = burn_subtitles.lower() not in ("false", "0", "no")
    subtitle_style = _normalize_subtitle_style(
        subtitle_size, subtitle_color, subtitle_outline_color,
        subtitle_outline, subtitle_position, subtitle_caps,
    )

    _set_job(job_id,
        status="queued",
        progress=5,
        message="⏳ Job diterima, mempersiapkan...",
        video_url=None,
        audio_url=None,
        error=None,
        created_at=time.time(),
    )

    # Fire-and-forget background task
    asyncio.create_task(_run_video_job(
        job_id, raw_video_path, voice_path, output_path,
        job_dir, prompt_text, voice_model, duration_mode, portrait, burn_subs,
        subtitle_style, subtitle_font_id, log_id,
    ))

    logger.info("SSE job submitted: %s | voice=%s | mode=%s | subtitle=%s",
                job_id, voice_model, duration_mode, burn_subs)
    return {"status": "queued", "job_id": job_id}


@app.get("/api/jobs/{job_id}/stream")
async def stream_job_status(job_id: str):
    """
    SSE endpoint. Streams job status updates until done or error.
    Client: const es = new EventSource('/api/jobs/{job_id}/stream')
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan.")

    async def event_generator():
        last_status = None
        while True:
            with JOBS_LOCK:
                job = dict(jobs.get(job_id, {}))

            payload = json.dumps(job)
            yield f"data: {payload}\n\n"

            if job.get("status") in ("done", "error"):
                # Schedule cleanup after a short delay to allow last event delivery
                asyncio.create_task(_delayed_job_cleanup(job_id, delay=30))
                break

            await asyncio.sleep(0.8)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


async def _delayed_job_cleanup(job_id: str, delay: int = 30):
    await asyncio.sleep(delay)
    with JOBS_LOCK:
        jobs.pop(job_id, None)


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "pollinations_url": POLLINATIONS_API_URL,
        "api_key_set": bool(POLLINATIONS_API_KEY),
        "api_key_prefix": POLLINATIONS_API_KEY[:8] + "..." if POLLINATIONS_API_KEY else None,
    }


# ── Debug ─────────────────────────────────────────────────────────────────────
@app.get("/api/debug")
def debug():
    import sys
    result = {
        "python_version": sys.version,
        "pollinations_url": POLLINATIONS_API_URL,
        "api_key_set": bool(POLLINATIONS_API_KEY),
        "api_key_prefix": POLLINATIONS_API_KEY[:8] + "..." if POLLINATIONS_API_KEY else None,
        "temp_dir_exists": TEMP_DIR.exists(),
        "moviepy_available": False,
        "ffmpeg_available": False,
        "pollinations_reachable": False,
        "pollinations_error": None,
    }
    try:
        from moviepy.editor import VideoFileClip  # noqa: F401
        result["moviepy_available"] = True
        import subprocess
        out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        result["ffmpeg_available"] = out.returncode == 0
    except Exception as e:
        result["moviepy_error"] = str(e)
    try:
        resp = requests.head(
            f"{POLLINATIONS_API_URL.rstrip('/')}/v1/audio/speech",
            headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"},
            timeout=10,
        )
        result["pollinations_reachable"] = True
        result["pollinations_status"] = resp.status_code
    except Exception as e:
        result["pollinations_error"] = str(e)
    return result
