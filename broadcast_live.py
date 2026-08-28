"""
1-Click Live Microphone Broadcaster for Windows PC
Captures microphone with FFmpeg and streams directly to https://onlineradio.onrender.com/live
"""

import subprocess
import urllib.request
import base64
import sys

URL = "https://onlineradio.onrender.com/live"
PASSWORD = "myradiopassword"

# Audio devices on PC:
# 1. "Microphone (Sirus.Headset)"
# 2. "Microphone (C922 Pro Stream Webcam)"
MIC_NAME = "Microphone (Sirus.Headset)"

auth = base64.b64encode(f"source:{PASSWORD}".encode()).decode("ascii")

print("="*60)
print("🎙️ STARTING LIVE BROADCAST TO YOUR RADIO STATION...")
print(f"Station URL: https://onlineradio.onrender.com")
print(f"Microphone: {MIC_NAME}")
print("Press Ctrl+C to STOP broadcasting and return to Recorded Playlist.")
print("="*60 + "\n")

cmd = [
    r"D:\VideoTools\ffmpeg.EXE",
    "-fflags", "nobuffer",
    "-flags", "low_delay",
    "-f", "dshow",
    "-i", f"audio={MIC_NAME}",
    "-af", "volume=10dB",
    "-c:a", "libmp3lame",
    "-b:a", "128k",
    "-ar", "44100",
    "-ac", "2",
    "-id3v2_version", "0",
    "-write_xing", "0",
    "-f", "mp3",
    "pipe:1"
]

proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

def audio_generator(pipe):
    while True:
        chunk = pipe.read(2048)
        if not chunk:
            break
        yield chunk

req = urllib.request.Request(URL, data=audio_generator(proc.stdout), method="PUT", headers={
    "Authorization": f"Basic {auth}",
    "Content-Type": "audio/mpeg",
    "User-Agent": "AgyLiveBroadcaster/1.0"
})

try:
    print("[🔴 LIVE NOW] You are on the air! Speak into your microphone...")
    with urllib.request.urlopen(req, timeout=86400) as resp:
        pass
except KeyboardInterrupt:
    print("\n[⏹ OFF AIR] Stopping broadcast... Returning station to Recorded Playlist.")
except Exception as e:
    print(f"\nBroadcast ended: {e}")
finally:
    proc.terminate()
