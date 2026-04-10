import csv
import os
from pathlib import Path

BASE_DIR = Path("backend")
LOG_FILE = BASE_DIR / "hook_logs.csv"
VIDEOS_DIR = BASE_DIR / "static" / "videos"
AUDIOS_DIR = BASE_DIR / "static" / "audios"

def test_read_logs():
    print(f"🔍 Mencoba membaca: {LOG_FILE.absolute()}")
    if not LOG_FILE.exists():
        print("❌ File tidak ditemukan!")
        return

    rows = []
    try:
        # Simulate main.py logic
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                rows.append(row)
                if i < 3:
                    print(f"✅ Row {i+1} found: {row.get('input_product')} | log_id: {row.get('log_id')}")
        
        print(f"📊 Total baris terbaca: {len(rows)}")
    except Exception as e:
        print(f"❌ Error saat membaca: {e}")

if __name__ == "__main__":
    test_read_logs()
