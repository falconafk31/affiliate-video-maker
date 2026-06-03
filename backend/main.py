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
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

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


async def generate_voice_from_pollinations(prompt: str, voice_model: str, output_path: Path):
    """
    ASYNC: Calls Edge-TTS or Pollinations TTS API.
    """
    if voice_model in ("id-ID-GadisNeural", "whisper"):
        import edge_tts
        actual_voice = "id-ID-GadisNeural"
        logger.info("Generating voice via Edge-TTS | voice: %s (requested: %s), prompt: %s...", actual_voice, voice_model, prompt[:30])
        try:
            communicate = edge_tts.Communicate(prompt, actual_voice)
            await communicate.save(str(output_path))
            saved = output_path.stat().st_size
            logger.info("Edge-TTS Audio saved: %s (%d bytes)", output_path.name, saved)
            if saved < 512:
                raise HTTPException(status_code=502, detail="Edge-TTS returned empty audio.")
            return
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
                        return
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
        logger.error("Failed to get duration for %s: %s", file_path, e)
        return 0.0

def merge_video_audio(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    duration_mode: str = "auto",
    force_portrait: bool = True,
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
            vf.append("crop=ih*(9/16):ih")
            
        if vf:
            cmd.extend(["-vf", ",".join(vf)])
        
        cmd.extend([
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest"
        ])
        
        if not vf:
            cmd.extend(["-c:v", "copy"])
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23"])

        cmd.append(str(output_path))
        
        logger.info("Running FFmpeg command...")
        
        # Hide window on Windows to prevent popups
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        process = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
        
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
    log_id: str = Form(None),
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

        # CALL ASYNC VOICE GEN
        await generate_voice_from_pollinations(prompt_text, voice_model, voice_path)

        if duration_mode not in ("auto", "loop_video", "trim_audio"):
            duration_mode = "auto"
        portrait = force_portrait.lower() not in ("false", "0", "no")

        # MoviePy operations are heavy - run in thread pool
        await asyncio.to_thread(merge_video_audio, raw_video_path, voice_path, output_path, duration_mode, portrait)

        if log_id:
            update_hook_log_script(log_id, prompt_text)
            shutil.copy(output_path, VIDEOS_DIR / f"{log_id}.mp4")
            logger.info("Persisted video for log_id: %s", log_id)

        background_tasks.add_task(clean_old_videos)
        background_tasks.add_task(cleanup_files, job_dir)

        return {
            "status": "success",
            "video_url": f"/api/videos/{log_id}.mp4" if log_id else None,
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
def get_logs():
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
                rows.append(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {e}")
    return {"total": len(rows), "logs": rows}


@app.get("/api/logs/download")
def download_logs():
    _ensure_log_header()
    if not LOG_FILE.exists():
        raise HTTPException(status_code=404, detail="Log file not found.")
    return FileResponse(path=str(LOG_FILE), media_type="text/csv", filename="hook_logs.csv")


@app.delete("/api/logs/clear")
def clear_logs():
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
def library_list():
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
def library_delete(video_id: str):
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
    log_id: str | None,
):
    """Background coroutine that executes the full render pipeline with SSE status updates."""
    try:
        # Stage 1: Generate voice
        _set_job(job_id, status="generating_voice", progress=10, message="🎙️ Membuat AI voiceover...")
        await generate_voice_from_pollinations(prompt_text, voice_model, voice_path)

        # Stage 2: Merge video
        _set_job(job_id, status="merging_video", progress=45, message="🎬 Menggabungkan video + audio...")
        await asyncio.to_thread(merge_video_audio, raw_video_path, voice_path, output_path, duration_mode, portrait)

        # Stage 3: Persist
        _set_job(job_id, status="saving", progress=85, message="💾 Menyimpan hasil render...")
        video_url = None
        if log_id:
            update_hook_log_script(log_id, prompt_text)
            shutil.copy(output_path, VIDEOS_DIR / f"{log_id}.mp4")
            video_url = f"/api/videos/{log_id}.mp4"
            logger.info("SSE job persisted video for log_id: %s", log_id)

        _set_job(
            job_id,
            status="done",
            progress=100,
            message="✅ Selesai!",
            video_url=video_url,
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
    video: UploadFile = File(...),
    prompt_text: str = Form(...),
    voice_model: str = Form("id-ID-GadisNeural"),
    duration_mode: str = Form("auto"),
    force_portrait: str = Form("true"),
    log_id: str = Form(None),
    library_video_id: str = Form(None),
):
    """
    Submit a video render job. Returns job_id immediately.
    Client should then poll GET /api/jobs/{job_id}/stream for SSE progress.
    """
    job_id = uuid.uuid4().hex
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Determine video source: upload or library
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
        job_dir, prompt_text, voice_model, duration_mode, portrait, log_id,
    ))

    logger.info("SSE job submitted: %s | voice=%s | mode=%s", job_id, voice_model, duration_mode)
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
