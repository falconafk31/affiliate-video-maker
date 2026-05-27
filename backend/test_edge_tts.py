import asyncio
from pathlib import Path
import edge_tts

async def test_tts():
    text = "Halo! Ini adalah uji coba suara alami perempuan Indonesia dari Edge TTS. Sangat natural, kan?"
    voice = "id-ID-GadisNeural"
    output_path = Path("test_edge_tts_gadis.mp3")
    
    print(f"Mengirim teks ke Edge-TTS menggunakan suara: {voice}...")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))
    
    if output_path.exists():
        size = output_path.stat().st_size
        print(f"SUCCESS! File audio tersimpan di '{output_path}' ({size} bytes).")
    else:
        print("ERROR: File tidak berhasil dibuat.")

if __name__ == "__main__":
    asyncio.run(test_tts())
