"""
Quick test script for Pollinations AI audio-generation API.
Uses POST /v1/audio/speech with Bearer token + Indonesian TikTok Affiliate Hook.
Run: python test_pollinations.py
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

API_BASE  = os.getenv("POLLINATIONS_API_URL", "https://gen.pollinations.ai")
API_KEY   = os.getenv("POLLINATIONS_API_KEY", "")
ENDPOINT  = f"{API_BASE.rstrip('/')}/v1/audio/speech"
OUTPUT    = "test_voice_output.mp3"

# ── Indonesian TikTok Affiliate Hook (optimized) ──────────────────────────────
# Tips: Tulis teks persis seperti yang ingin diucapkan, dalam Bahasa Indonesia.
# Gunakan tanda koma (,) untuk jeda pendek, titik (.) untuk jeda panjang.
# Hindari emoji atau karakter khusus.
PROMPT = (
    "Hei, tunggu dulu. Kamu tau nggak produk ini? "
    "Ini yang bikin ribuan orang akhirnya bisa tidur nyenyak tanpa obat. "
    "Udah terbukti, udah ribuan yang merasakan manfaatnya. "
    "Dan sekarang lagi ada diskon gila-gilaan, tapi stoknya terbatas banget. "
    "Jangan sampai nyesel. Link ada di bio, buruan sebelum kehabisan!"
)

VOICE  = "nova"   # Coba juga: shimmer, alloy, echo, fable, onyx

print("=" * 60)
print("  Pollinations AI — Indonesian TikTok Affiliate Hook Test")
print("=" * 60)
print(f"  Endpoint : {ENDPOINT}")
print(f"  Voice    : {VOICE}")
print(f"  API Key  : {'✅ Set (' + API_KEY[:8] + '...)' if API_KEY else '❌ NOT SET'}")
print(f"  Prompt   :\n  {PROMPT[:120]}...")
print()

if not API_KEY:
    print("❌ ERROR: POLLINATIONS_API_KEY belum diset di file .env")
    print("   Isi: POLLINATIONS_API_KEY=sk_xxxxxxxxxxxxxxxx")
    exit(1)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
payload = {
    "input": PROMPT,
    "voice": VOICE,
    "response_format": "mp3",
}

try:
    print("Mengirim request ke Pollinations AI...")
    response = requests.post(ENDPOINT, headers=headers, json=payload, timeout=60, stream=True)

    print(f"  Status Code   : {response.status_code}")
    print(f"  Content-Type  : {response.headers.get('content-type', 'N/A')}")
    print(f"  Content-Length: {response.headers.get('content-length', 'unknown')} bytes")

    if response.status_code == 401:
        print("\n❌ 401 Unauthorized — API key salah atau tidak valid.")
        exit(1)
    elif response.status_code == 402:
        print("\n❌ 402 Payment Required — Kredit Pollinations habis.")
        print("   Top up di: https://enter.pollinations.ai")
        exit(1)

    response.raise_for_status()

    with open(OUTPUT, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    size = Path(OUTPUT).stat().st_size
    if size == 0:
        print("\n❌ File MP3 kosong (0 bytes). Coba lagi atau ganti voice model.")
        exit(1)

    print(f"\n✅ SUKSES! Audio tersimpan di '{OUTPUT}' ({size:,} bytes)")
    print("   Putar file MP3 tersebut untuk cek kualitas suaranya.\n")

    # ── Voice recommendations ─────────────────────────────────────────────────
    print("  💡 Tips voice model untuk Bahasa Indonesia:")
    print("     nova    → Perempuan, energik ✅ (direkomendasikan)")
    print("     shimmer → Perempuan, lembut")
    print("     alloy   → Netral, smooth")
    print("     echo    → Laki-laki, dalam")
    print("     fable   → Laki-laki, naratif")
    print("     onyx    → Laki-laki, tegas")

except requests.exceptions.Timeout:
    print("\n❌ TIMEOUT — API tidak merespons dalam 60 detik.")
except requests.exceptions.HTTPError as e:
    print(f"\n❌ HTTP ERROR: {e}")
    try:
        print(f"   Response: {response.text[:300]}")
    except Exception:
        pass
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
