"""
Test pipeline Auto Subtitle Burn-in (termasuk custom style & wrap balanced):
  1. split_script_into_captions  — pemecahan skrip jadi caption
  2. build_caption_timings       — timing proporsional & word-boundary
  3. generate_srt / generate_ass — format SRT & ASS (default + custom style)
  4. merge_video_audio           — burn-in nyata via FFmpeg (libass)
  5. rasio video tidak lazim     — dimensi genap (libx264 aman)

Jalankan:  cd backend && ../.venv/bin/python test_subtitles.py
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from main import (
    split_script_into_captions,
    build_caption_timings,
    generate_srt,
    generate_ass,
    build_subtitles,
    merge_video_audio,
    ffmpeg_supports_subtitles,
    compute_output_dimensions,
    _wrap_caption_text,
    _normalize_subtitle_style,
)

PASS, FAIL = 0, 0


def check(name: str, cond: bool, extra: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {extra}")


print("═" * 60)
print("1) split_script_into_captions")
script = (
    "Tau gak sih, masker aloe vera ini lagi diskon lima belas persen di Shopee! "
    "Teksturnya ringan banget, langsung meresap ke kulit. "
    "Aku udah pakai dua minggu dan jerawatku kempes. "
    "Cek keranjang kuning sekarang sebelum kehabisan!"
)
caps = split_script_into_captions(script)
print(f"     → {len(caps)} caption:")
for c in caps:
    print(f"       [{len(c):2d}] {c}")
check("menghasilkan beberapa caption", len(caps) >= 3)
check("semua caption ≤ 42 karakter (maks 2 baris)", all(len(c) <= 42 for c in caps),
      str([len(c) for c in caps]))
check("teks tidak hilang (total kata sama)",
      len(re.findall(r"\S+", " ".join(caps))) == len(re.findall(r"\S+", script)))
check("skrip kosong → []", split_script_into_captions("   ") == [])

print("═" * 60)
print("2) build_caption_timings")
t_prop = build_caption_timings(caps, audio_duration=12.0, word_boundaries=None)
check("proporsional: jumlah timing == jumlah caption", len(t_prop) == len(caps))
check("proporsional: mulai dari awal", t_prop[0][0] <= 0.2)
check("proporsional: berakhir ± di akhir audio", abs(t_prop[-1][1] - 12.0) < 0.6,
      f"end={t_prop[-1][1]}")
check("proporsional: monoton tanpa tumpang-tindih",
      all(t_prop[i][1] <= t_prop[i + 1][0] + 1e-6 for i in range(len(t_prop) - 1)))

words = re.findall(r"\S+", script)
wb, t = [], 0.0
for w in words:
    dur = 12.0 / len(words)
    wb.append({"start": round(t, 3), "end": round(t + dur * 0.9, 3), "text": w})
    t += dur
t_word = build_caption_timings(caps, audio_duration=12.0, word_boundaries=wb)
check("word-boundary: jumlah timing == jumlah caption", len(t_word) == len(caps))
check("word-boundary: caption pertama mulai ≈ awal audio", t_word[0][0] < 0.2)
check("word-boundary: caption terakhir tahan sampai akhir audio",
      abs(t_word[-1][1] - 12.0) < 0.01, f"end={t_word[-1][1]}")
check("word-boundary: monoton tanpa tumpang-tindih",
      all(t_word[i][1] <= t_word[i + 1][0] + 1e-6 for i in range(len(t_word) - 1)))

t_fall = build_caption_timings(caps, 12.0, wb[:3])
check("fallback saat token ≠ boundary", len(t_fall) == len(caps) and abs(t_fall[-1][1] - 12.0) < 0.6)

print("═" * 60)
print("3) _wrap_caption_text (balanced wrap)")
long_cap = "Aku udah pakai dua minggu dan jerawatku kempes."
lines = _wrap_caption_text(long_cap, wrap_at=14)
check("wrap: 2–3 baris untuk teks 47ch @wrap14", 2 <= len(lines) <= 3, str(lines))
check("wrap: kata tidak hilang/berubah", " ".join(lines).split() == long_cap.split())
check("wrap: lebar baris terkendali (≤ wrap_at + kata terpanjang)",
      all(len(l) <= 14 + max(len(w) for w in long_cap.split()) for l in lines), str(lines))
check("wrap: pendek → 1 baris", _wrap_caption_text("Keren banget!", 20) == ["Keren banget!"])

print("═" * 60)
print("4) generate_srt & generate_ass (default & custom style)")
srt = generate_srt(t_prop)
check("format SRT: blok bernomor 1..N", srt.startswith("1\n") and f"\n{len(caps)}\n" in srt)
check("format SRT: panah timing standar",
      re.search(r"\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d", srt) is not None)

ass = generate_ass(t_prop, play_w=720, play_h=1280)
check("ASS default: PlayResX/Y = dimensi output", "PlayResX: 720" in ass and "PlayResY: 1280" in ass)
check("ASS default: Dialogue dengan \\pos() absolut", "{\\pos(360,589)}" in ass)
check("ASS default: jumlah Dialogue == jumlah caption", ass.count("Dialogue: ") == len(caps))
check("ASS default: font size skala 5.2% (67px @1280)", "DejaVu Sans,67," in ass)

style = _normalize_subtitle_style(
    subtitle_size="lg", subtitle_color="yellow",
    subtitle_outline_color="black", subtitle_outline="thick",
    subtitle_position="bottom", subtitle_caps="true",
)
check("normalize: preset size lg → 0.070", abs(style["size_frac"] - 0.070) < 1e-9)
check("normalize: warna yellow → BGR 00FFFF", style["color"] == "00FFFF")
check("normalize: caps aktif", style["caps"] is True)
style["font_name"] = "TestSubtitleFont"

ass2 = generate_ass(t_prop, play_w=720, play_h=1280, style=style)
check("ASS custom: font family custom dipakai", "TestSubtitleFont,90," in ass2)
check("ASS custom: ukuran lg (90px @1280)", "TestSubtitleFont,90," in ass2)
check("ASS custom: warna kuning (&H0000FFFF)", "&H0000FFFF" in ass2)
check("ASS custom: outline tebal (17px)", ",1,17,0,5," in ass2)
check("ASS custom: posisi bawah \\pos(360,1024)", "{\\pos(360,1024)}" in ass2)
check("ASS custom: teks HURUF KAPITAL", "TEKSTUR" in ass2 and "Teksturnya" not in ass2)

style_none = _normalize_subtitle_style(subtitle_outline_color="none")
check("normalize: outline none → outline_color None", style_none["outline_color"] is None)
ass3 = generate_ass(t_prop, 720, 1280, {**style_none, "font_name": "DejaVu Sans"})
check("ASS tanpa outline → Outline=0", re.search(r"DejaVu Sans,\d+,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,0,0,5,", ass3) is not None)

check("compute_output_dimensions 9:16 pas → no-op",
      compute_output_dimensions(720, 1280, True) == (720, 1280))
check("compute_output_dimensions 4:5 → crop genap 758x1350",
      compute_output_dimensions(1080, 1350, True) == (758, 1350),
      str(compute_output_dimensions(1080, 1350, True)))

print("═" * 60)
print("5) Burn-in nyata via FFmpeg")
check("FFmpeg punya filter ass/subtitles (libass)", ffmpeg_supports_subtitles())

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    raw = td / "raw.mp4"
    aud = td / "voice.mp3"
    out = td / "final.mp4"

    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=size=720x1280:rate=30",
                    "-t", "6", "-pix_fmt", "yuv420p", str(raw)],
                   capture_output=True, check=True)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
                    "-t", "5", "-b:a", "128k", str(aud)],
                   capture_output=True, check=True)

    built = build_subtitles(script, aud, td, word_boundaries=None, play_w=720, play_h=1280,
                            style=style)
    check("build_subtitles membuat (srt, ass) dengan style", built is not None
          and built[0].exists() and built[1].exists())
    srt_path, ass_path = built

    merge_video_audio(raw, aud, out, duration_mode="auto", force_portrait=True,
                      subtitle_ass=ass_path)
    check("output render ada & > 50 KB", out.exists() and out.stat().st_size > 50_000,
          f"size={out.stat().st_size if out.exists() else 0}")

    dur_out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
                             capture_output=True, text=True).stdout.strip()
    check("durasi output ≈ 5 detik (auto: video dipotong ke audio)",
          abs(float(dur_out) - 5.0) < 0.3, f"dur={dur_out}")

    frame = td / "frame_check.png"
    subprocess.run(["ffmpeg", "-y", "-ss", "2.0", "-i", str(out), "-frames:v", "1", str(frame)],
                   capture_output=True, check=True)
    frame_dest = Path(__file__).parent / "static" / "subs" / "_test_frame.png"
    frame_dest.parent.mkdir(parents=True, exist_ok=True)
    frame_dest.write_bytes(frame.read_bytes())
    print(f"     🖼  Frame verifikasi disimpan: {frame_dest}")

    raw2, out2 = td / "raw_45.mp4", td / "final_45.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=size=720x900:rate=30",
                    "-t", "3", "-pix_fmt", "yuv420p", str(raw2)],
                   capture_output=True, check=True)
    ok_45 = True
    aud2 = td / "voice2.mp3"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=330:sample_rate=44100",
                    "-t", "3", "-b:a", "128k", str(aud2)], capture_output=True, check=True)
    try:
        built2 = build_subtitles(script, aud2, td, play_w=758, play_h=1350)
        merge_video_audio(raw2, aud2, out2, duration_mode="auto", force_portrait=True,
                          subtitle_ass=built2[1])
    except Exception as e:
        ok_45 = False
        print("     error:", e)
    check("input 4:5 → render sukses (dimensi crop genap)", ok_45 and out2.exists())

print("═" * 60)
print(f"HASIL: {PASS} lulus, {FAIL} gagal")
sys.exit(1 if FAIL else 0)
