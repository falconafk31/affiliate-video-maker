import csv
import os
from pathlib import Path

# Paths relative to project root
BASE_DIR = Path("backend")
LOG_FILE = BASE_DIR / "hook_logs.csv"

def test_read_logs():
    print(f"Reading: {LOG_FILE.absolute()}")
    if not LOG_FILE.exists():
        print("Error: File not found!")
        return

    rows = []
    try:
        # Replicate main.py logic as closely as possible
        # Some windows CSVs use UTF-8-SIG for BOM
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                rows.append(row)
                if i < 3:
                    print(f"Row {i+1}: {row.get('input_product')} (ID: {row.get('log_id')})")
        
        print(f"Total rows read: {len(rows)}")
    except Exception as e:
        print(f"Error during read: {e}")

if __name__ == "__main__":
    test_read_logs()
