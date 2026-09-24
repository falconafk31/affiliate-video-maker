"""
E2E offline untuk pipeline job video + Auto Subtitle Burn-in.
TTS di-stub (audio sine) karena test tidak boleh bergantung jaringan —
seluruh sisanya ASLI: endpoint HTTP, job store SSE, FFmpeg merge, burn subtitle.

Jalankan:  cd backend && ../.venv/bin/python test_api_e2e.py
"""
import asyncio
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
import main  # noqa: E402

PASS, FAIL = 0, 0


def check(name: str, cond: bool, extra: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {extra}")


async def fake_generate_voice(prompt, voice_model, output_path):
    """Stub TTS: audio sine sepanjang ± prompt words, + word-boundary tiruan."""
    words = re.findall(r"\S+", prompt)
    dur = max(2.0, 0.32 * len(words))
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
         "-t", f"{dur:.2f}", "-b:a", "128k", str(output_path)],
        capture_output=True, check=True,
    )
    step = dur / max(len(words), 1)
    return [
        {"start": round(i * step, 3), "end": round(i * step + step * 0.9, 3), "text": w}
        for i, w in enumerate(words)
    ]


async def run() -> None:
    global PASS, FAIL
    main.generate_voice_from_pollinations = fake_generate_voice

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        # ── Login (mode dev: ADMIN_PASSWORD_HASH kosong) ──────────────────────
        r = await client.post("/api/login", json={"password": "dev"})
        check("POST /api/login → 200 + token", r.status_code == 200 and "access_token" in r.json())
        auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # ── Submit tanpa file & tanpa library_video_id harus ditolak (B5) ────
        r = await client.post("/api/jobs/submit", data={"prompt_text": "tes"}, headers=auth)
        check("submit tanpa video → 400 terkendali (bukan crash)",
              r.status_code == 400, f"status={r.status_code}")

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            raw = td / "raw.mp4"
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=size=720x1280:rate=30",
                            "-t", "3", "-pix_fmt", "yuv420p", str(raw)],
                           capture_output=True, check=True)
            script = ("Serius deh, kipas mini ini awet banget baterainya. "
                      "Dua hari pemakaian masih penuh. Cocok buat kamu yang kerja outdoor!")

            # ── Job 1: burn_subtitles=true, tanpa log_id (uji persist + SRT) ─
            with open(raw, "rb") as f:
                r = await client.post(
                    "/api/jobs/submit",
                    data={"prompt_text": script, "voice_model": "id-ID-GadisNeural",
                          "duration_mode": "auto", "burn_subtitles": "true"},
                    files={"video": ("raw.mp4", f, "video/mp4")},
                    headers=auth,
                )
            check("POST /api/jobs/submit (subtitle AKTIF) → queued",
                  r.status_code == 200 and r.json().get("status") == "queued",
                  f"{r.status_code} {r.text[:120]}")
            job_id = r.json()["job_id"]

            done_job = {}
            async with client.stream("GET", f"/api/jobs/{job_id}/stream") as resp:
                async for line in resp.aiter_lines():
                    m = re.match(r"data: (\{.*\})", line)
                    if m:
                        import json
                        done_job = json.loads(m.group(1))
                        if done_job.get("status") in ("done", "error"):
                            break
            check("SSE stream → status done", done_job.get("status") == "done",
                  str(done_job.get("error") or done_job.get("status")))
            check("response membawa video_url (tanpa log_id pun tidak null)",
                  bool(done_job.get("video_url")))
            check("response membawa subtitle_url saat AKTIF",
                  bool(done_job.get("subtitle_url")))

            vid_id = Path(done_job["video_url"]).stem
            check("video terpersist di static/videos/",
                  (main.VIDEOS_DIR / f"{vid_id}.mp4").exists())
            srt = main.SUBS_DIR / f"{vid_id}.srt"
            check("file .srt terpersist di static/subs/ untuk diunduh", srt.exists())
            if srt.exists():
                content = srt.read_text(encoding="utf-8")
                check("isi .srt berisi caption dari skrip", "-->" in content and "kipas mini" in content)

            # ── Job 2: burn_subtitles=false → tanpa subtitle ─────────────────
            with open(raw, "rb") as f:
                r = await client.post(
                    "/api/jobs/submit",
                    data={"prompt_text": script, "voice_model": "id-ID-GadisNeural",
                          "duration_mode": "auto", "burn_subtitles": "false"},
                    files={"video": ("raw.mp4", f, "video/mp4")},
                    headers=auth,
                )
            job2 = r.json()["job_id"]
            done2 = {}
            async with client.stream("GET", f"/api/jobs/{job2}/stream") as resp:
                async for line in resp.aiter_lines():
                    m = re.match(r"data: (\{.*\})", line)
                    if m:
                        import json
                        done2 = json.loads(m.group(1))
                        if done2.get("status") in ("done", "error"):
                            break
            check("job subtitle NONAKTIF → done", done2.get("status") == "done",
                  str(done2.get("error") or done2.get("status")))
            check("NONAKTIF → tidak ada subtitle_url", not done2.get("subtitle_url"))
            check("NONAKTIF → video tetap dirender & terpersist",
                  (main.VIDEOS_DIR / f"{Path(done2['video_url']).stem}.mp4").exists()
                  if done2.get("video_url") else False)

            # ── /api/logs menyertakan srt_url bila file ada ──────────────────
            r = await client.get("/api/logs", headers=auth)
            check("GET /api/logs → 200", r.status_code == 200)

            # bersihkan artefak test
            for p in [main.VIDEOS_DIR / f"{vid_id}.mp4",
                      main.SUBS_DIR / f"{vid_id}.srt"]:
                p.unlink(missing_ok=True)
            if done2.get("video_url"):
                (main.VIDEOS_DIR / f"{Path(done2['video_url']).stem}.mp4").unlink(missing_ok=True)


print("═" * 60)
print("E2E offline — job pipeline + Auto Subtitle Burn-in")
print("═" * 60)
asyncio.run(run())
print("═" * 60)
print(f"HASIL: {PASS} lulus, {FAIL} gagal")
sys.exit(1 if FAIL else 0)
