import os
import csv
import uuid
import shutil
import asyncio
import logging
import traceback
import threading
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

import requests
import time
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables from .env
load_dotenv()

# ── Constants ────────────────────────────────────────────────────────────────
POLLINATIONS_API_URL = os.getenv("POLLINATIONS_API_URL", "https://gen.pollinations.ai")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")
if not POLLINATIONS_API_KEY:
    raise RuntimeError("POLLINATIONS_API_KEY is not set. Please add it to your .env file.")

BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / "temp_processing"
TEMP_DIR.mkdir(exist_ok=True)

VIDEOS_DIR = BASE_DIR / "static" / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp4"}
API_TIMEOUT_SECONDS = 120  # Pollinations can be slow for long text

# ── Hook Generation Log (CSV) ───────────────────────────────────────────
LOG_FILE   = BASE_DIR / "hook_logs.csv"
LOG_LOCK   = threading.Lock()  # thread-safe writes
LOG_HEADER = ["no", "time", "platform", "variation", "input_product", "output_script", "log_id"]

def _ensure_log_header():
    """Create log file with header if it does not exist."""
    if not LOG_FILE.exists():
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(LOG_HEADER)

_ensure_log_header()


def append_hook_log(platform: str, variation: str, product: str, script: str) -> str:
    """Append one row to hook_logs.csv and return generated log_id."""
    log_id = str(uuid.uuid4())
    try:
        with LOG_LOCK:
            # count existing rows to get the next sequential number
            try:
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    row_count = sum(1 for _ in csv.reader(f)) - 1  # subtract header
            except Exception:
                row_count = 0

            row = [
                row_count + 1,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                platform,
                variation,
                product,
                script,
                log_id,
            ]
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(row)
        logger.info("Hook log appended: row #%d | %s | %s", row_count + 1, platform, product)
    except Exception as e:
        logger.error("Failed to append hook log (possibly file locked): %s", e)
    return log_id
    
def clean_old_videos():
    """Delete videos older than 7 days to conserve disk space."""
    now = time.time()
    for f in VIDEOS_DIR.glob("*.mp4"):
        try:
            if os.path.exists(f) and os.path.getmtime(f) < now - 7 * 86400:
                os.remove(f)
                logger.info("Auto-deleted old video (7+ days): %s", f.name)
        except Exception as e:
            logger.error("Error deleting old video %s: %s", f, e)


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure temp directory exists on startup."""
    TEMP_DIR.mkdir(exist_ok=True)
    yield


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Affiliate Video Maker API",
    description="Generates AI voiceover and merges it with your uploaded video.",
    version="1.0.0",
    lifespan=lifespan,
)

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


# ── Helpers ───────────────────────────────────────────────────────────────────
def cleanup_files(*paths: Path) -> None:
    """Remove files and directories silently."""
    for p in paths:
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                p.unlink()
        except Exception:
            pass


def generate_voice_from_pollinations(prompt: str, voice: str, output_path: Path) -> None:
    """
    Call POST /v1/audio/speech or GET /audio/... depending on voice model,
    and save the audio response to output_path. Raises HTTPException on failure.
    """
    logger.info("Preparing Pollinations request for voice: %s", voice)

    try:
        if voice.lower() == "whisper":
            import urllib.parse
            # Replace slashes and newlines which can cause 404s in Nginx URIs
            safe_prompt = prompt.replace("/", " ").replace("\n", " ")
            encoded_prompt = urllib.parse.quote(safe_prompt)
            endpoint = f"{POLLINATIONS_API_URL.rstrip('/')}/audio/{encoded_prompt}?model={voice}"
            headers = {"Authorization": f"Bearer {POLLINATIONS_API_KEY}"}
            response = requests.get(endpoint, headers=headers, timeout=API_TIMEOUT_SECONDS, stream=True)
        else:
            endpoint = f"{POLLINATIONS_API_URL.rstrip('/')}/v1/audio/speech"
            headers  = {
                "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {"input": prompt, "voice": voice, "response_format": "mp3"}
            response = requests.post(
                endpoint, headers=headers, json=payload,
                timeout=API_TIMEOUT_SECONDS, stream=True,
            )
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Pollinations AI API timed out.")
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Error calling Pollinations AI: {exc}")

    ct = response.headers.get("content-type", "")
    logger.info("Pollinations response: status=%s content-type=%s content-length=%s",
                response.status_code, ct, response.headers.get("content-length", "?"))

    if response.status_code == 401:
        raise HTTPException(status_code=401,
            detail="Invalid Pollinations API key (401). Check POLLINATIONS_API_KEY in .env.")
    if response.status_code == 402:
        raise HTTPException(status_code=402,
            detail="Insufficient Pollinations credits (402). Top up at enter.pollinations.ai.")
    if response.status_code == 404:
        raise HTTPException(status_code=502,
            detail=f"Pollinations audio endpoint not found (404). URL: {endpoint}")
    if not response.ok:
        preview = response.text[:300]
        raise HTTPException(status_code=502,
            detail=f"Pollinations returned HTTP {response.status_code}: {preview}")

    # Block obviously wrong responses (HTML/JSON error pages)
    if any(t in ct for t in ("text/html", "text/plain", "application/json")):
        body = response.text[:500]
        logger.error("Pollinations returned non-audio body: %s", body)
        raise HTTPException(status_code=502,
            detail=f"Pollinations returned non-audio content ({ct}): {body}")

    # Stream save
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    saved = output_path.stat().st_size
    logger.info("Audio saved: %s (%d bytes)", output_path.name, saved)
    if saved < 512:
        raise HTTPException(status_code=502,
            detail=f"Pollinations returned empty audio ({saved} bytes). "
                   "Check your API key credit balance or try a shorter prompt.")


def crop_to_portrait(clip):
    """
    Center-crop a video clip to 9:16 portrait aspect ratio.
    - Landscape (16:9) → crop left/right, keep center column
    - Already portrait but wrong ratio → crop top/bottom
    - Already 9:16 → no change
    """
    w, h = clip.size
    target_ratio = 9 / 16  # 0.5625
    current_ratio = w / h

    if abs(current_ratio - target_ratio) < 0.01:
        return clip  # already 9:16, skip

    if current_ratio > target_ratio:
        # Too wide → crop width (keep full height)
        new_w = int(h * 9 / 16)
        # Ensure even number (required by libx264)
        new_w = new_w if new_w % 2 == 0 else new_w - 1
        x_center = w / 2
        logger.info("Cropping portrait: %dx%d → %dx%d (center crop width)", w, h, new_w, h)
        return clip.crop(x_center=x_center, width=new_w, height=h)
    else:
        # Too tall → crop height (keep full width, center)
        new_h = int(w * 16 / 9)
        new_h = new_h if new_h % 2 == 0 else new_h - 1
        y_center = h / 2
        logger.info("Cropping portrait: %dx%d → %dx%d (center crop height)", w, h, w, new_h)
        return clip.crop(width=w, height=new_h, y_center=y_center)


def merge_video_audio(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    duration_mode: str = "auto",
    force_portrait: bool = True,
) -> None:
    """
    Strip audio from video, attach AI voice, then match durations.

    duration_mode:
      'auto'       – smart: if audio > video → loop video; if video > audio → trim video.
      'loop_video' – always loop video to fill audio length (audio drives duration).
      'trim_audio' – old behavior: trim audio to video length (video drives duration).
    """
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

        logger.info("Loading video: %s", video_path.name)
        video = VideoFileClip(str(video_path))
        video_no_audio = video.without_audio()

        # ── Force 9:16 portrait aspect ratio ─────────────────────────────────
        if force_portrait:
            original_size = video_no_audio.size
            video_no_audio = crop_to_portrait(video_no_audio)
            if video_no_audio.size != original_size:
                logger.info("Portrait crop applied: %s → %s", original_size, video_no_audio.size)

        audio = AudioFileClip(str(audio_path))

        vid_dur = round(video_no_audio.duration, 3)
        aud_dur = round(audio.duration, 3)
        logger.info("Durations — video: %.2fs  audio: %.2fs  mode: %s", vid_dur, aud_dur, duration_mode)

        if duration_mode == "trim_audio":
            if aud_dur > vid_dur:
                audio = audio.subclip(0, vid_dur)
            final_video = video_no_audio.set_audio(audio)

        elif duration_mode == "loop_video" or (duration_mode == "auto" and aud_dur > vid_dur):
            loops_needed = int(aud_dur / vid_dur) + 1
            logger.info("Looping video x%d to cover %.2fs", loops_needed, aud_dur)
            looped_video = concatenate_videoclips([video_no_audio] * loops_needed)
            looped_video = looped_video.subclip(0, aud_dur)
            final_video = looped_video.set_audio(audio)

        else:
            logger.info("Trimming video to audio length (%.2fs)", aud_dur)
            trimmed_video = video_no_audio.subclip(0, aud_dur)
            final_video = trimmed_video.set_audio(audio)

        logger.info("Rendering final video…")
        final_video.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(output_path.parent / "temp_audio.m4a"),
            remove_temp=True,
            logger=None,
            threads=4,
            preset="ultrafast"
        )
        logger.info("Render complete: %s", output_path.name)

        video.close()
        audio.close()
        final_video.close()

    except Exception as e:
        logger.error("merge_video_audio failed:\n%s", traceback.format_exc())
        raise RuntimeError(f"Video merge error: {e}") from e


# ── Endpoint ──────────────────────────────────────────────────────────────────
@app.post("/api/process-video")
def process_video(
    prompt_text: str = Form(..., description="Teks hook untuk di-voiceover"),
    voice_model: str = Form("nova", description="Voice preset: nova, shimmer, alloy, dst"),
    video: UploadFile = File(..., description="Video sumber"),
    duration_mode: str = Form(
        "auto",
        description="auto | loop_video | trim_audio",
    ),
    log_id: str = Form(None, description="Opsional UUID log untuk melampirkan video ini"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    force_portrait: str = Form(
        "true",
        description="Force output to 9:16 portrait aspect ratio (true/false)",
    ),
):
    # ── Validate file type ────────────────────────────────────────────────────
    suffix = Path(video.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Only .mp4 files are accepted. Got: '{suffix}'")

    if not prompt_text.strip():
        raise HTTPException(status_code=400, detail="prompt_text cannot be empty.")

    # ── Per-request working directory ─────────────────────────────────────────
    job_id = uuid.uuid4().hex
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    raw_video_path = job_dir / f"raw_video{suffix}"
    voice_path = job_dir / "temp_voice.mp3"
    output_path = job_dir / "final_output.mp4"

    try:
        # a) Save uploaded video — seek to 0 first to avoid "moov atom not found"
        video.file.seek(0)
        with open(raw_video_path, "wb") as buffer:
            while chunk := video.file.read(1024 * 1024):  # read 1 MB at a time
                buffer.write(chunk)
            buffer.flush()
            os.fsync(buffer.fileno())

        # Validate the saved file is a real, non-empty MP4
        saved_size = raw_video_path.stat().st_size
        if saved_size < 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File video terlalu kecil ({saved_size} bytes). Pastikan file .mp4 valid dan tidak kosong.",
            )

        # b) Generate AI voiceover
        generate_voice_from_pollinations(prompt_text, voice_model, voice_path)

        if duration_mode not in ("auto", "loop_video", "trim_audio"):
            duration_mode = "auto"
        portrait = force_portrait.lower() not in ("false", "0", "no")

        # c + d + e) Merge video & audio (synchronous call directly inside thread pool)
        merge_video_audio(raw_video_path, voice_path, output_path, duration_mode, portrait)

        # g) Schedule cleanup and persistence
        final_video_path = output_path
        if log_id:
            final_video_path = VIDEOS_DIR / f"{log_id}.mp4"
            shutil.copy(output_path, final_video_path)
            logger.info("Persisted video to static/videos for log_id: %s", log_id)

        background_tasks.add_task(clean_old_videos)
        background_tasks.add_task(cleanup_files, job_dir)

        # f) Return final video
        return FileResponse(
            path=str(final_video_path),
            media_type="video/mp4",
            filename="affiliate_video.mp4",
            background=None,  # FileResponse handles streaming; cleanup via background_tasks
        )

    except HTTPException as he:
        cleanup_files(job_dir)
        logger.error("HTTPException in /api/process-video: %s %s", he.status_code, he.detail)
        raise
    except Exception as e:
        cleanup_files(job_dir)
        logger.error("Unhandled exception in /api/process-video:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}")



# ── AI Hook Generator ─────────────────────────────────────────────────────────
# Text API uses the same gen.pollinations.ai base URL as the audio API
TEXT_API_URL = POLLINATIONS_API_URL  # https://gen.pollinations.ai

HOOK_SYSTEM_PROMPT = """Kamu adalah copywriter expert affiliate marketing Indonesia. 
Tugasmu adalah menulis skrip voiceover untuk video affiliate TikTok/Shopee yang viral dan menarik.
Aturan penulisan:
- Gunakan Bahasa Indonesia gaul yang natural dan relatable
- Tulis angka dalam kata (misal: 'seratus ribu', bukan '100.000')
- Tambahkan jeda alami dengan koma dan titik
- Tidak lebih dari 120 kata
- Jangan gunakan emoji, hashtag, atau tanda bintang
- Langsung mulai skrip tanpa intro/penjelasan tambahan
- Akhiri dengan call-to-action yang kuat"""

HOOK_STYLE_PROMPTS = {
    "tiktok": {
        "viral":   "Buat hook viral impulsif dengan pembuka yang mengejutkan (bukan 'hei stop scrolling'), social proof dengan angka spesifik, dan FOMO yang kuat.",
        "shock":   "Buat hook shock & reveal — mulai dari pengakuan jujur skeptis, twist mengejutkan saat mencoba, dan rasa penasaran yang mendorong klik.",
        "story":   "Buat hook cerita personal — ceritakan penyesalan tidak menemukan produk ini lebih awal, perjalanan mencoba banyak produk gagal, lalu penemuan yang mengubah segalanya.",
        "fomo":    "Buat hook FOMO urgency ekstrem — data stok menipis yang spesifik, keputusan mahal jika menunda, dan urgensi waktu nyata.",
    },
    "shopee": {
        "flash":   "Buat hook flash sale Shopee — angka diskon yang mengejutkan, bukti laku keras (angka pcs terjual), dan kombinasi voucher yang bikin deal makin gila.",
        "review":  "Buat hook review jujur Shopee — ekspektasi rendah di awal, detail unboxing yang memuaskan, dan rekomendasi organik ke orang terdekat.",
        "bundle":  "Buat hook bundle deal — kalkulasi hemat dalam rupiah yang konkret, bonus item yang mengejutkan, dan eksklusivitas promo.",
        "premium": "Buat hook premium value — kontras kualitas vs harga yang tidak masuk akal, bukti keaslian produk, dan akses yang biasanya hanya untuk kalangan tertentu.",
    },
}

@app.post("/api/generate-hook")
def generate_hook(
    product_name: str = Form(..., description="Nama produk affiliate"),
    hook_type: str    = Form("tiktok", description="Platform: tiktok atau shopee"),
    variation: str    = Form("viral",  description="Variasi hook style"),
):
    """
    Generate an AI-powered affiliate hook script using Pollinations text API
    with gemini-flash model. No video processing — returns JSON with the script.
    """
    if not product_name.strip():
        raise HTTPException(status_code=400, detail="product_name tidak boleh kosong.")

    hook_type = hook_type.lower().strip()
    variation = variation.lower().strip()

    styles = HOOK_STYLE_PROMPTS.get(hook_type, HOOK_STYLE_PROMPTS["tiktok"])
    style_instruction = styles.get(variation, list(styles.values())[0])

    platform_label = "TikTok" if hook_type == "tiktok" else "Shopee"
    user_prompt = (
        f"Produk: {product_name}\n"
        f"Platform: {platform_label}\n"
        f"Instruksi gaya: {style_instruction}\n\n"
        f"Tulis skrip voiceover affiliatenya sekarang:"
    )

    logger.info("Generating hook via Pollinations text API | product=%s platform=%s variation=%s",
                product_name, hook_type, variation)

    try:
        response = requests.post(
            f"{TEXT_API_URL.rstrip('/')}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gemini-fast",
                "messages": [
                    {"role": "system", "content": HOOK_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                "temperature": 0.85,
                "max_tokens": 300,
                "private": True,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        # Extract text from OpenAI-compatible response
        script = data["choices"][0]["message"]["content"].strip()
        logger.info("Hook generated: %d chars", len(script))

        # ── Write to CSV log ──────────────────────────────────────────
        log_id = append_hook_log(hook_type, variation, product_name, script)

        return {"script": script, "product": product_name, "platform": hook_type, "variation": variation, "log_id": log_id}

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Pollinations text API timeout. Coba lagi.")
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Error calling Pollinations text API: {exc}")
    except (KeyError, IndexError) as exc:
        logger.error("Unexpected text API response structure: %s", traceback.format_exc())
        raise HTTPException(status_code=502, detail=f"Unexpected API response format: {exc}")


# ── Log Viewer Endpoints ───────────────────────────────────────────────────────
@app.get("/api/logs")
def get_logs():
    """Return all hook generation logs as JSON array with dynamic video mapping."""
    _ensure_log_header()
    rows = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Add video URL statelessly if the file currently exists
                log_id = row.get("log_id")
                if log_id and (VIDEOS_DIR / f"{log_id}.mp4").exists():
                    row["video_url"] = f"/api/videos/{log_id}.mp4"
                rows.append(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {e}")
    return {"total": len(rows), "logs": rows}


@app.get("/api/logs/download")
def download_logs():
    """Download hook_logs.csv file."""
    _ensure_log_header()
    if not LOG_FILE.exists():
        raise HTTPException(status_code=404, detail="Log file not found.")
    return FileResponse(
        path=str(LOG_FILE),
        media_type="text/csv",
        filename="hook_logs.csv",
    )


@app.delete("/api/logs/clear")
def clear_logs():
    """Reset log file (keep header only)."""
    with LOG_LOCK:
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(LOG_HEADER)
    logger.info("Hook logs cleared.")
    return {"status": "ok", "message": "Log file has been cleared."}


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "pollinations_url": POLLINATIONS_API_URL,
        "api_key_set": bool(POLLINATIONS_API_KEY),
        "api_key_prefix": POLLINATIONS_API_KEY[:8] + "..." if POLLINATIONS_API_KEY else None,
    }


# ── Debug / connectivity test ─────────────────────────────────────────────────
@app.get("/api/debug")
def debug():
    """Quick connectivity test — call this to diagnose 500 errors without uploading a file."""
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

    # Check MoviePy / FFmpeg
    try:
        from moviepy.editor import VideoFileClip  # noqa: F401
        result["moviepy_available"] = True
        import subprocess
        out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        result["ffmpeg_available"] = out.returncode == 0
    except Exception as e:
        result["moviepy_error"] = str(e)

    # Ping Pollinations API (HEAD request, no credits used)
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
