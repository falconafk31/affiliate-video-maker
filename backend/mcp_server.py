"""
MCP Server for Affiliate Video Maker.
Exposes two tools:
  1. generate_ai_voice  – fetch AI audio from Pollinations and save as MP3
  2. merge_video_and_voice – merge a video file with an audio file via MoviePy
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env relative to this file's location
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

POLLINATIONS_API_URL = os.getenv("POLLINATIONS_API_URL", "https://gen.pollinations.ai")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")
if not POLLINATIONS_API_KEY:
    raise RuntimeError("POLLINATIONS_API_KEY is not set. Please configure your .env file.")

TEMP_DIR = Path(__file__).parent / "temp_processing"
TEMP_DIR.mkdir(exist_ok=True)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("affiliate-video-maker")


# ── Tool 1 ────────────────────────────────────────────────────────────────────
@mcp.tool()
def generate_ai_voice(prompt: str, voice: str = "nova") -> str:
    """
    Generate an AI voiceover from the Pollinations API.

    Args:
        prompt: The text script to convert to speech.
        voice:  The Pollinations voice model to use (default: 'nova').

    Returns:
        Absolute path to the saved MP3 file.

    Raises:
        RuntimeError: On API errors or empty responses.
    """
    import requests
    import uuid

    if not prompt.strip():
        raise ValueError("prompt cannot be empty.")

    output_path = TEMP_DIR / f"voice_{uuid.uuid4().hex}.mp3"
    endpoint = f"{POLLINATIONS_API_URL.rstrip('/')}/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"input": prompt, "voice": voice, "response_format": "mp3"}

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=120,
            stream=True,
        )
        if response.status_code == 401:
            raise RuntimeError("Invalid Pollinations API key (401). Check POLLINATIONS_API_KEY in .env.")
        if response.status_code == 402:
            raise RuntimeError("Insufficient Pollinations AI credits (402). Top up at enter.pollinations.ai.")
        response.raise_for_status()
    except RuntimeError:
        raise
    except requests.exceptions.Timeout:
        raise RuntimeError("Pollinations AI API timed out. Try a shorter prompt or retry later.")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Pollinations API request failed: {e}")

    content_type = response.headers.get("content-type", "")
    if "audio" not in content_type and "octet-stream" not in content_type:
        raise RuntimeError(f"Unexpected response content-type: {content_type}. Expected audio.")

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    if output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("Pollinations API returned an empty audio file.")

    return str(output_path)


# ── Tool 2 ────────────────────────────────────────────────────────────────────
@mcp.tool()
def merge_video_and_voice(video_path: str, audio_path: str) -> str:
    """
    Strip original audio from a video, attach AI voiceover, and render a new MP4.

    Args:
        video_path: Absolute path to the source .mp4 video.
        audio_path: Absolute path to the AI-generated .mp3 audio.

    Returns:
        Absolute path to the rendered output .mp4 file.

    Raises:
        FileNotFoundError: If either input file does not exist.
        RuntimeError: On MoviePy rendering errors.
    """
    import uuid
    from moviepy.editor import VideoFileClip, AudioFileClip

    video_path_obj = Path(video_path)
    audio_path_obj = Path(audio_path)

    if not video_path_obj.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not audio_path_obj.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    output_path = TEMP_DIR / f"merged_{uuid.uuid4().hex}.mp4"

    try:
        video = VideoFileClip(str(video_path_obj))
        video_no_audio = video.without_audio()

        audio = AudioFileClip(str(audio_path_obj))

        # Trim audio if it exceeds video length
        if audio.duration > video_no_audio.duration:
            audio = audio.subclip(0, video_no_audio.duration)

        final_video = video_no_audio.set_audio(audio)
        final_video.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(TEMP_DIR / f"temp_audio_{uuid.uuid4().hex}.m4a"),
            remove_temp=True,
            logger=None,
        )

        video.close()
        audio.close()
        final_video.close()

    except Exception as e:
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        raise RuntimeError(f"Video rendering failed: {e}")

    return str(output_path)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
