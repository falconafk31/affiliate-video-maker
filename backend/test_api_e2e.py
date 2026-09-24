"""
E2E offline untuk pipeline job video + Auto Subtitle Burn-in (termasuk custom
font & style). TTS di-stub (audio sine) — seluruh sisanya ASLI: endpoint HTTP,
job store SSE, FFmpeg merge, burn subtitle, upload font TTF/OTF/TTC.

Jalankan:  cd backend && ../.venv/bin/python test_api_e2e.py
"""
import asyncio
import json
import re
import subprocess
import sys
import tempfile
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


def make_test_font(path: Path, family: str = "TestSubtitleFont") -> None:
    """Bangun TTF minimal tapi valid via fontTools (offline, tanpa file eksternal)."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder([".notdef", "A"])
    fb.setupCharacterMap({65: "A"})
    pen = TTGlyphPen(None)
    pen.moveTo((100, 0))
    pen.lineTo((500, 0))
    pen.lineTo((500, 700))
    pen.lineTo((100, 700))
    pen.closePath()
    glyph_a = pen.glyph()
    notdef = TTGlyphPen(None).glyph()
    fb.setupGlyf({".notdef": notdef, "A": glyph_a})
    fb.setupHorizontalMetrics({".notdef": (600, 0), "A": (600, 100)})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": family, "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    fb.save(str(path))


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


async def wait_job(client, auth, data: dict, files: dict) -> dict:
    r = await client.post("/api/jobs/submit", data=data, files=files, headers=auth)
    if r.status_code != 200:
        return {"status": f"submit-fail:{r.status_code}", "raw": r.text[:120]}
    job_id = r.json()["job_id"]
    done = {}
    async with client.stream("GET", f"/api/jobs/{job_id}/stream") as resp:
        async for line in resp.aiter_lines():
            m = re.match(r"data: (\{.*\})", line)
            if m:
                done = json.loads(m.group(1))
                if done.get("status") in ("done", "error"):
                    break
    return done


async def run() -> None:
    main.generate_voice_from_pollinations = fake_generate_voice

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        # ── Login (mode dev) ─────────────────────────────────────────────────
        r = await client.post("/api/login", json={"password": "dev"})
        check("POST /api/login → 200 + token", r.status_code == 200 and "access_token" in r.json())
        auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

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

            # ── Job 1: burn_subtitles=true default style, tanpa log_id ───────
            with open(raw, "rb") as f:
                done = await wait_job(client, auth,
                    {"prompt_text": script, "voice_model": "id-ID-GadisNeural",
                     "duration_mode": "auto", "burn_subtitles": "true"},
                    {"video": ("raw.mp4", f, "video/mp4")})
            check("Job 1 (subtitle AKTIF) → done", done.get("status") == "done",
                  str(done.get("error") or done.get("status")))
            check("Job 1 → video_url & subtitle_url terisi",
                  bool(done.get("video_url")) and bool(done.get("subtitle_url")))
            vid1 = Path(done["video_url"]).stem
            check("Job 1 → video & srt terpersist",
                  (main.VIDEOS_DIR / f"{vid1}.mp4").exists()
                  and (main.SUBS_DIR / f"{vid1}.srt").exists())
            ass1 = main.SUBS_DIR / f"{vid1}.ass"
            check("Job 1 → sidecar .ass terpersist (gaya default DejaVu)",
                  ass1.exists() and "DejaVu Sans" in ass1.read_text(encoding="utf-8"))

            # ── Job 2: burn_subtitles=false ──────────────────────────────────
            with open(raw, "rb") as f:
                done2 = await wait_job(client, auth,
                    {"prompt_text": script, "voice_model": "id-ID-GadisNeural",
                     "duration_mode": "auto", "burn_subtitles": "false"},
                    {"video": ("raw.mp4", f, "video/mp4")})
            check("Job 2 (NONAKTIF) → done tanpa subtitle_url",
                  done2.get("status") == "done" and not done2.get("subtitle_url"))
            vid2 = Path(done2.get("video_url", "/x")).stem
            check("Job 2 → video tetap terpersist",
                  (main.VIDEOS_DIR / f"{vid2}.mp4").exists() if done2.get("video_url") else False)

            # ── Custom font: tolak format non-standar, upload TTF valid ───────
            bad = td / "x.woff2"
            bad.write_bytes(b"woff-not-supported")
            with open(bad, "rb") as f:
                r = await client.post("/api/fonts/upload",
                                      files={"font": ("x.woff2", f, "font/woff2")}, headers=auth)
            check("upload .woff2 ditolak 400 (format tidak standar utk libass)",
                  r.status_code == 400, f"{r.status_code}")

            ttf = td / "TestFont.ttf"
            make_test_font(ttf)
            with open(ttf, "rb") as f:
                r = await client.post("/api/fonts/upload",
                                      files={"font": ("TestFont.ttf", f, "font/ttf")}, headers=auth)
            check("upload .ttf → 200 + family terbaca dari file",
                  r.status_code == 200
                  and r.json().get("font", {}).get("family") == "TestSubtitleFont",
                  r.text[:150])
            font_id = r.json()["font"]["id"]

            r = await client.get("/api/fonts", headers=auth)
            check("GET /api/fonts → font terdaftar",
                  any(x["id"] == font_id for x in r.json().get("fonts", [])))

            # ── Job 3: custom font + style penuh (kuning, tebal, bawah, caps) ─
            with open(raw, "rb") as f:
                done3 = await wait_job(client, auth,
                    {"prompt_text": script, "voice_model": "id-ID-GadisNeural",
                     "duration_mode": "auto", "burn_subtitles": "true",
                     "subtitle_font_id": font_id, "subtitle_size": "lg",
                     "subtitle_color": "yellow", "subtitle_outline_color": "black",
                     "subtitle_outline": "thick", "subtitle_position": "bottom",
                     "subtitle_caps": "true"},
                    {"video": ("raw.mp4", f, "video/mp4")})
            check("Job 3 (custom font+style) → done", done3.get("status") == "done",
                  str(done3.get("error") or done3.get("status")))
            vid3 = Path(done3.get("video_url", "/x")).stem
            ass3 = main.SUBS_DIR / f"{vid3}.ass"
            if ass3.exists():
                a = ass3.read_text(encoding="utf-8")
                check("ASS job 3: font family custom", "TestSubtitleFont" in a)
                check("ASS job 3: warna kuning + posisi bawah",
                      "&H0000FFFF" in a and "{\\pos(360,1024)}" in a)
                check("ASS job 3: teks kapital", "SERIUS DEH" in a)
            else:
                check("ASS job 3 tersedia untuk diperiksa", False, "file .ass tidak ada")

            check("file font tersimpan di static/fonts/",
                  any(main.FONTS_DIR.glob("*.ttf")))

            # ── Hapus font ──────────────────────────────────────────────────
            r = await client.delete(f"/api/fonts/{font_id}", headers=auth)
            check("DELETE /api/fonts/{id} → ok", r.status_code == 200)
            r = await client.get("/api/fonts", headers=auth)
            check("font terhapus dari daftar",
                  not any(x["id"] == font_id for x in r.json().get("fonts", [])))

            # bersihkan artefak test
            for p in list(main.VIDEOS_DIR.glob("*.mp4")) + list(main.SUBS_DIR.glob("*")):
                p.unlink(missing_ok=True)


print("═" * 60)
print("E2E offline — job pipeline + Auto Subtitle + Custom Font/Style")
print("═" * 60)
asyncio.run(run())
print("═" * 60)
print(f"HASIL: {PASS} lulus, {FAIL} gagal")
sys.exit(1 if FAIL else 0)
