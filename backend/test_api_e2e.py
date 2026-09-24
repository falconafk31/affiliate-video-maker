"""
E2E offline untuk pipeline job video + Auto Subtitle + Custom Font/Style +
Custom AI Provider (OpenAI-compatible teks & suara, termasuk endpoint
chat-completions audio modalities + test koneksi + model bawaan configurable).

TTS bawaan di-stub (audio sine) — jalur custom & uji koneksi memakai fake
OpenAI server sungguhan di localhost.

Jalankan:  cd backend && ../.venv/bin/python test_api_e2e.py
"""
import asyncio
import base64
import json
import re
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


# ── Fake OpenAI-compatible server (chat/completions + audio/speech) ───────────
FAKE_STATE = {"chat_model": None, "chat_auth": None, "chat_audio": None,
              "speech": None, "speech_auth": None}
FAKE_MP3: Path | None = None


class FakeAIHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # senyap
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            body = {}
        path = self.path.rstrip("/")
        if path.endswith("/chat/completions"):
            if body.get("modalities"):
                # Jalur chat-audio (modalities) → balas dengan audio base64
                audio_part = (body.get("audio") or {})
                FAKE_STATE["chat_audio"] = {"model": body.get("model"), "voice": audio_part.get("voice"),
                                            "auth": self.headers.get("Authorization", "")}
                out = json.dumps({
                    "choices": [{"message": {
                        "role": "assistant",
                        "audio": {"data": base64.b64encode(FAKE_MP3.read_bytes()).decode()},
                    }}]
                }).encode()
            else:
                model = body.get("model") or ""
                FAKE_STATE["chat_model"] = model
                FAKE_STATE["chat_auth"] = self.headers.get("Authorization", "")
                if model == "null-content-model":
                    # Simulasi respons OpenRouter model reasoning: content null
                    out = json.dumps({"choices": [{"message": {"role": "assistant", "content": None}}]}).encode()
                elif model == "list-content-model":
                    # Simulasi provider yang mengirim content berupa list of parts
                    out = json.dumps({"choices": [{"message": {"role": "assistant",
                        "content": [{"type": "text", "text": "Cek kipas mini ini, dari konten list!"}]}}]}).encode()
                else:
                    out = json.dumps({
                        "choices": [{"message": {"content": "Cek kipas mini ini, baterainya awet dua hari penuh!"}}]
                    }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        elif path.endswith("/audio/speech"):
            FAKE_STATE["speech"] = {"model": body.get("model"), "voice": body.get("voice"),
                                    "input_len": len(body.get("input", ""))}
            FAKE_STATE["speech_auth"] = self.headers.get("Authorization", "")
            data = FAKE_MP3.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()


async def fake_generate_voice(prompt, voice_model, output_path):
    """Stub TTS bawaan; jalur custom & openai-audio: diteruskan ke fungsi ASLI."""
    vm = str(voice_model)
    if vm.startswith("custom:") or vm.startswith("openai-audio"):
        return await real_generate_voice(prompt, voice_model, output_path)
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


real_generate_voice = main.generate_voice_from_pollinations


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
    done["job_id"] = job_id
    return done


async def run() -> None:
    global FAKE_MP3
    main.generate_voice_from_pollinations = fake_generate_voice

    logs_csv = Path(main.__file__).parent / "logs" / "hook_logs.csv"
    csv_backup = logs_csv.read_bytes() if logs_csv.exists() else b""

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

            # ── 6) Custom AI Provider (OpenAI-compatible) ────────────────────
            FAKE_MP3 = td / "fake_tts.mp3"
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=44100",
                            "-t", "2", "-b:a", "128k", str(FAKE_MP3)],
                           capture_output=True, check=True)
            server = ThreadingHTTPServer(("127.0.0.1", 0), FakeAIHandler)
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base_url = f"http://127.0.0.1:{port}/v1"

            old_poll_url, old_poll_key = main.POLLINATIONS_API_URL, main.POLLINATIONS_API_KEY
            try:
                # ── Test koneksi (tombol 🧪) ─────────────────────────────────
                r = await client.post("/api/ai-config/test", headers=auth, json={
                    "kind": "text", "base_url": base_url,
                    "api_key": "sk-test-secret-123456", "model": "fake-gpt"})
                check("test koneksi text → ok", r.status_code == 200 and r.json().get("ok") is True,
                      r.text[:150])
                r = await client.post("/api/ai-config/test", headers=auth, json={
                    "kind": "voice_speech", "base_url": base_url,
                    "api_key": "sk-voice-key-999", "model": "fake-tts", "voice": "mini-voice"})
                check("test koneksi voice_speech → ok", r.json().get("ok") is True, r.text[:150])
                r = await client.post("/api/ai-config/test", headers=auth, json={
                    "kind": "voice_chat_audio", "base_url": base_url,
                    "api_key": "sk-audio-key-1", "model": "fake-audio", "voice": "mini-voice"})
                check("test koneksi voice_chat_audio → ok", r.json().get("ok") is True, r.text[:150])
                r = await client.post("/api/ai-config/test", headers=auth, json={
                    "kind": "text", "base_url": "http://127.0.0.1:1/v1", "api_key": "x", "model": "m"})
                check("test koneksi gagal → ok:false (bukan exception)", r.json().get("ok") is False,
                      r.text[:150])

                # Model teks custom
                r = await client.post("/api/ai-config/text-models", headers=auth, json={
                    "label": "Fake LLM", "base_url": base_url,
                    "api_key": "sk-test-secret-123456", "model": "fake-gpt"})
                check("POST text-models → 200 + id", r.status_code == 200
                      and r.json().get("model", {}).get("id"), r.text[:150])
                tid = r.json()["model"]["id"]
                check("respons POST: api_key ter-mask", "…" in r.json()["model"]["api_key"]
                      and r.json()["model"]["has_key"] is True)

                r = await client.get("/api/ai-config", headers=auth)
                check("GET ai-config: key ter-mask di daftar",
                      all(m["api_key"] != "sk-test-secret-123456" for m in r.json()["text_models"]))

                r = await client.post("/api/ai-config/active-text-model",
                                      headers=auth, json={"id": tid})
                check("aktifkan model teks custom", r.status_code == 200
                      and r.json()["active_text_model"] == tid)

                r = await client.post("/api/generate-hook", headers=auth, data={
                    "product_name": "Kipas Mini 2000", "hook_type": "tiktok", "variation": "viral"})
                check("generate-hook via custom LLM → 200", r.status_code == 200, r.text[:150])
                check("hook pakai model custom + key terkirim",
                      FAKE_STATE["chat_model"] == "fake-gpt"
                      and FAKE_STATE["chat_auth"] == "Bearer sk-test-secret-123456",
                      str(FAKE_STATE))
                check("isi hook dari fake LLM masuk", "kipas mini" in r.json().get("script", "").lower())

                # Edit dengan key kosong → key lama dipertahankan
                r = await client.post("/api/ai-config/text-models", headers=auth, json={
                    "id": tid, "label": "Fake LLM v2", "base_url": base_url,
                    "api_key": "", "model": "fake-gpt-v2"})
                r = await client.get("/api/ai-config", headers=auth)
                check("edit tanpa key → key lama tetap (has_key)",
                      any(m["id"] == tid and m["has_key"] for m in r.json()["text_models"]))

                # ── Regresi bug OpenRouter: content null / content list ──────
                r = await client.post("/api/ai-config/text-models", headers=auth, json={
                    "label": "Null Content", "base_url": base_url,
                    "api_key": "sk-null", "model": "null-content-model"})
                tid_null = r.json()["model"]["id"]
                await client.post("/api/ai-config/active-text-model", headers=auth, json={"id": tid_null})
                r = await client.post("/api/generate-hook", headers=auth, data={
                    "product_name": "Kipas Mini", "hook_type": "tiktok", "variation": "viral"})
                check("content null → 502 pesan jelas (bukan 500 NoneType)",
                      r.status_code == 502 and "content" in r.json().get("detail", "").lower(),
                      f"{r.status_code} {r.text[:120]}")
                r = await client.post("/api/ai-config/test", headers=auth, json={
                    "kind": "text", "base_url": base_url, "api_key": "sk-null",
                    "model": "null-content-model"})
                check("test koneksi deteksi content kosong → ok:false",
                      r.json().get("ok") is False, r.text[:120])

                r = await client.post("/api/ai-config/text-models", headers=auth, json={
                    "label": "List Content", "base_url": base_url,
                    "api_key": "sk-list", "model": "list-content-model"})
                tid_list = r.json()["model"]["id"]
                await client.post("/api/ai-config/active-text-model", headers=auth, json={"id": tid_list})
                r = await client.post("/api/generate-hook", headers=auth, data={
                    "product_name": "Kipas Mini", "hook_type": "tiktok", "variation": "viral"})
                check("content format list [{type:text}] → hook tetap jadi",
                      r.status_code == 200 and "kipas mini" in r.json().get("script", "").lower(),
                      r.text[:120])
                await client.post("/api/ai-config/active-text-model", headers=auth, json={"id": tid})
                await client.delete(f"/api/ai-config/text-models/{tid_null}", headers=auth)
                await client.delete(f"/api/ai-config/text-models/{tid_list}", headers=auth)

                # Model suara custom — endpoint standar /audio/speech
                r = await client.post("/api/ai-config/voice-models", headers=auth, json={
                    "label": "Fake TTS", "base_url": base_url,
                    "api_key": "sk-voice-key-999", "model": "fake-tts",
                    "voice": "mini-voice", "speed": 1.0, "endpoint_type": "speech"})
                check("POST voice-models → 200 + id", r.status_code == 200
                      and r.json().get("model", {}).get("id"), r.text[:150])
                vid_custom = r.json()["model"]["id"]

                # ── Penyimpanan di DATABASE (SQLite) ─────────────────────────
                import sqlite3
                check("DB SQLite ada di backend/data/app.db", Path(main.DB_PATH).exists(),
                      str(main.DB_PATH))
                conn = sqlite3.connect(str(main.DB_PATH))
                n_text = conn.execute("SELECT COUNT(*) FROM ai_models WHERE id=? AND kind='text'",
                                      (tid,)).fetchone()[0]
                n_voice = conn.execute("SELECT COUNT(*) FROM ai_models WHERE id=? AND kind='voice'",
                                       (vid_custom,)).fetchone()[0]
                conn.close()
                check("model teks & suara tersimpan di tabel ai_models (SQLite)",
                      n_text == 1 and n_voice == 1, f"text={n_text} voice={n_voice}")

                # Job 4: voice custom OpenAI-compatible (/audio/speech)
                with open(raw, "rb") as f:
                    done4 = await wait_job(client, auth,
                        {"prompt_text": script, "voice_model": f"custom:{vid_custom}",
                         "duration_mode": "auto", "burn_subtitles": "false"},
                        {"video": ("raw.mp4", f, "video/mp4")})
                check("Job 4 (custom voice speech) → done", done4.get("status") == "done",
                      str(done4.get("error") or done4.get("status")))
                check("TTS /audio/speech: model+voice sesuai konfigurasi + auth",
                      FAKE_STATE["speech"] and FAKE_STATE["speech"]["model"] == "fake-tts"
                      and FAKE_STATE["speech"]["voice"] == "mini-voice"
                      and FAKE_STATE["speech_auth"] == "Bearer sk-voice-key-999",
                      str(FAKE_STATE["speech"]))

                # Job 5: voice id tidak valid → error terkendali
                with open(raw, "rb") as f:
                    done5 = await wait_job(client, auth,
                        {"prompt_text": script, "voice_model": "custom:doesnotexist",
                         "duration_mode": "auto", "burn_subtitles": "false"},
                        {"video": ("raw.mp4", f, "video/mp4")})
                check("Job 5 (custom voice id salah) → error jelas",
                      done5.get("status") == "error"
                      and "tidak ditemukan" in (done5.get("error") or ""),
                      str(done5.get("error")))

                # Model suara custom — endpoint chat_audio (modalities)
                r = await client.post("/api/ai-config/voice-models", headers=auth, json={
                    "label": "Fake Audio-Chat TTS", "base_url": base_url,
                    "api_key": "sk-audio-key-222", "model": "fake-audio-model",
                    "voice": "chat-voice", "endpoint_type": "chat_audio"})
                vid_chat = r.json()["model"]["id"]
                with open(raw, "rb") as f:
                    done6 = await wait_job(client, auth,
                        {"prompt_text": script, "voice_model": f"custom:{vid_chat}",
                         "duration_mode": "auto", "burn_subtitles": "false"},
                        {"video": ("raw.mp4", f, "video/mp4")})
                check("Job 6 (custom voice chat_audio) → done", done6.get("status") == "done",
                      str(done6.get("error") or done6.get("status")))
                check("TTS chat/completions+audio: model+voice+auth benar",
                      FAKE_STATE["chat_audio"] and FAKE_STATE["chat_audio"]["model"] == "fake-audio-model"
                      and FAKE_STATE["chat_audio"]["voice"] == "chat-voice"
                      and FAKE_STATE["chat_audio"]["auth"] == "Bearer sk-audio-key-222",
                      str(FAKE_STATE["chat_audio"]))

                # ── Model bawaan tidak hardcode (Pollinations teks & audio) ──
                main.POLLINATIONS_API_URL = base_url  # patch → fake server
                main.POLLINATIONS_API_KEY = "sk-poll-test"
                r = await client.post("/api/ai-config/defaults", headers=auth, json={
                    "pollinations_text_model": "my-text-model",
                    "pollinations_audio_model": "my-audio-model",
                    "edge_tts_voice": "id-ID-ArdiNeural"})
                check("POST defaults → 200", r.status_code == 200, r.text[:120])
                r = await client.get("/api/ai-config", headers=auth)
                d = r.json().get("defaults", {})
                check("GET defaults: model bawaan tersimpan",
                      d.get("pollinations_text_model") == "my-text-model"
                      and d.get("pollinations_audio_model") == "my-audio-model"
                      and d.get("edge_tts_voice") == "id-ID-ArdiNeural", str(d))

                # hook bawaan memakai model yang dikonfigurasi (bukan "openai" hardcoded)
                r = await client.post("/api/ai-config/active-text-model",
                                      headers=auth, json={"id": ""})
                r = await client.post("/api/generate-hook", headers=auth, data={
                    "product_name": "Kipas Mini 2000", "hook_type": "tiktok", "variation": "viral"})
                check("hook bawaan memakai pollinations_text_model config",
                      r.status_code == 200 and FAKE_STATE["chat_model"] == "my-text-model",
                      str(FAKE_STATE["chat_model"]))

                r = await client.post("/api/ai-config/test", headers=auth, json={
                    "kind": "pollinations_text", "model": "my-text-model"})
                check("test koneksi pollinations_text → ok", r.json().get("ok") is True, r.text[:120])
                r = await client.post("/api/ai-config/test", headers=auth, json={
                    "kind": "pollinations_audio", "model": "my-audio-model", "voice": "nova"})
                check("test koneksi pollinations_audio → ok", r.json().get("ok") is True, r.text[:120])

                # GPT-Audio bawaan memakai pollinations_audio_model config
                FAKE_STATE["chat_audio"] = None
                with open(raw, "rb") as f:
                    done7 = await wait_job(client, auth,
                        {"prompt_text": script, "voice_model": "openai-audio:nova",
                         "duration_mode": "auto", "burn_subtitles": "false"},
                        {"video": ("raw.mp4", f, "video/mp4")})
                check("Job 7 (GPT-Audio bawaan) → done", done7.get("status") == "done",
                      str(done7.get("error") or done7.get("status")))
                check("GPT-Audio memakai pollinations_audio_model config (bukan hardcoded)",
                      FAKE_STATE["chat_audio"] and FAKE_STATE["chat_audio"]["model"] == "my-audio-model"
                      and FAKE_STATE["chat_audio"]["voice"] == "nova", str(FAKE_STATE["chat_audio"]))

                main.POLLINATIONS_API_URL, main.POLLINATIONS_API_KEY = old_poll_url, old_poll_key

                # ── timeout_s per provider (P1) ────────────────────────────
                r = await client.post("/api/ai-config/text-models", headers=auth, json={
                    "id": tid, "label": "Fake LLM v2", "base_url": base_url,
                    "api_key": "", "model": "fake-gpt-v2", "timeout_s": 25})
                r = await client.get("/api/ai-config", headers=auth)
                check("timeout_s provider tersimpan (GET → 25)",
                      any(m["id"] == tid and float(m.get("timeout_s") or 0) == 25
                          for m in r.json()["text_models"]), r.text[:200])

                # ── Rate-limit generate-hook (anti boros kuota) ──────────────
                main._RATE_HITS.clear()
                statuses = []
                for i in range(31):
                    rr = await client.post("/api/generate-hook", headers=auth, data={
                        "product_name": f"Produk Rate {i}", "hook_type": "tiktok",
                        "variation": "viral"})
                    statuses.append(rr.status_code)
                check("rate-limit hook: 31 call cepat → call ke-31 ditekan 429",
                      statuses[-1] == 429 and statuses.count(429) == 1,
                      str(statuses[-6:]))
                main._RATE_HITS.clear()

                # ── Voice preview (🔊 Contoh Suara) ─────────────────────────
                r = await client.post("/api/voice-preview", headers=auth,
                                      json={"voice_model": "id-ID-GadisNeural"})
                check("voice-preview → audio_url /api/audios/preview_*.mp3",
                      r.status_code == 200
                      and "/api/audios/preview_" in r.json().get("audio_url", ""),
                      r.text[:150])
                prev_file = Path(main.AUDIOS_DIR) / Path(r.json().get("audio_url", "")).name
                check("file preview audio dibuat di AUDIOS_DIR",
                      prev_file.exists() and prev_file.stat().st_size > 500)
                prev_file.unlink(missing_ok=True)

                # ── Job 5: rasio 1:1 + kualitas HD + persistensi kolom jobs ─
                with open(raw, "rb") as f:
                    done5 = await wait_job(client, auth,
                        {"prompt_text": script, "voice_model": "id-ID-GadisNeural",
                         "duration_mode": "auto", "burn_subtitles": "false",
                         "output_ratio": "1:1", "quality": "hd"},
                        {"video": ("raw.mp4", f, "video/mp4")})
                check("Job 5 (rasio 1:1 + HD) → done", done5.get("status") == "done",
                      str(done5.get("error") or done5.get("status")))
                out5 = Path(main.VIDEOS_DIR) / f"{done5['job_id']}.mp4"
                w5, h5 = main.get_media_dimensions(str(out5))
                check("output 1:1 → 720x720 (crop kotak dari 720x1280)", (w5, h5) == (720, 720),
                      f"{w5}x{h5}")
                _conn = sqlite3.connect(str(main.DB_PATH))
                row5 = _conn.execute("SELECT status FROM jobs WHERE id=?",
                                     (done5["job_id"],)).fetchone()
                _conn.close()
                check("row jobs tersimpan di SQLite (write-through _set_job)",
                      row5 is not None and row5[0] == "done", str(row5))

                # Kembalikan ke default + bersihkan konfigurasi
                r = await client.post("/api/ai-config/defaults", headers=auth, json={
                    "pollinations_text_model": "openai",
                    "pollinations_audio_model": "openai-audio",
                    "edge_tts_voice": "id-ID-GadisNeural"})
                check("reset defaults → ok", r.status_code == 200)
                r = await client.delete(f"/api/ai-config/text-models/{tid}", headers=auth)
                check("DELETE text-models → ok", r.status_code == 200)
                r = await client.delete(f"/api/ai-config/voice-models/{vid_custom}", headers=auth)
                check("DELETE voice-models (speech) → ok", r.status_code == 200)
                r = await client.delete(f"/api/ai-config/voice-models/{vid_chat}", headers=auth)
                check("DELETE voice-models (chat_audio) → ok", r.status_code == 200)
                r = await client.get("/api/ai-config", headers=auth)
                # ── Migrasi json lama → SQLite ───────────────────────────────
                legacy = Path(main.__file__).parent / "logs" / "ai_config.json"
                legacy.write_text(json.dumps({
                    "text_models": [{"id": "legacy123", "label": "Legacy LLM",
                                     "base_url": base_url, "api_key": "sk-legacy-key",
                                     "model": "legacy-model"}],
                    "active_text_model": "",
                }), encoding="utf-8")
                main._migrate_legacy_ai_json()
                r = await client.get("/api/ai-config", headers=auth)
                check("migrasi json lama → SQLite (entry legacy masuk DB)",
                      any(m["id"] == "legacy123" for m in r.json()["text_models"]))
                check("file json lama DIHAPUS permanen (API key tidak tersisa)",
                      not legacy.exists() and not legacy.with_suffix(".json.migrated").exists())
                await client.delete("/api/ai-config/text-models/legacy123", headers=auth)
                for pth in (legacy, legacy.with_suffix(".json.migrated")):
                    pth.unlink(missing_ok=True)

                r = await client.get("/api/ai-config", headers=auth)
                check("konfigurasi bersih setelah dihapus",
                      not r.json()["text_models"] and not r.json()["voice_models"])
            finally:
                main.POLLINATIONS_API_URL, main.POLLINATIONS_API_KEY = old_poll_url, old_poll_key
                server.shutdown()

            # bersihkan artefak test
            for p in list(main.VIDEOS_DIR.glob("*.mp4")) + list(main.SUBS_DIR.glob("*")):
                p.unlink(missing_ok=True)

    if logs_csv.exists():
        logs_csv.write_bytes(csv_backup)


print("═" * 60)
print("E2E offline — job pipeline + Auto Subtitle + Custom Font/Style + Custom AI Provider")
print("═" * 60)
asyncio.run(run())
print("═" * 60)
print(f"HASIL: {PASS} lulus, {FAIL} gagal")
sys.exit(1 if FAIL else 0)
