import requests

url = "https://gen.pollinations.ai/audio/halo%20dunia%20ini%20tes?model=whisper"
print(f"Testing {url}")
r = requests.get(url)
print(f"Status: {r.status_code}")
if r.status_code != 200:
    print(r.text)
else:
    print(f"Success! Downloaded {len(r.content)} bytes of audio.")
