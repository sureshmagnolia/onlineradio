import subprocess
import sys

# ==========================================
# Zeno.fm Broadcast Settings
# ==========================================
ZENO_SERVER = "link.zeno.fm"
ZENO_PORT = "80"
ZENO_MOUNT = "yz9ttrydrc9uv/source" 
ZENO_USER = "source"
ZENO_PASS = "Wg8Lut3x"

# Audio devices on PC:
MIC_NAME = "Microphone (Sirus.Headset)"

# FFmpeg natively supports streaming to Icecast servers using the icecast:// protocol
# Format: icecast://[username:password@]server:port/mountpoint
icecast_url = f"icecast://{ZENO_USER}:{ZENO_PASS}@{ZENO_SERVER}:{ZENO_PORT}/{ZENO_MOUNT}"

print("="*60)
print("🎙️ STARTING LIVE BROADCAST TO ZENO.FM...")
print(f"Microphone: {MIC_NAME}")
print("Press Ctrl+C to STOP broadcasting.")
print("="*60 + "\n")

cmd = [
    r"D:\VideoTools\ffmpeg.EXE",
    "-fflags", "nobuffer",
    "-flags", "low_delay",
    "-f", "dshow",
    "-i", f"audio={MIC_NAME}",
    "-af", "volume=10dB",       # Boost microphone volume if needed
    "-c:a", "libmp3lame",
    "-b:a", "128k",
    "-ar", "44100",
    "-ac", "2",
    "-content_type", "audio/mpeg", # Required for icecast protocol
    "-f", "mp3",
    icecast_url
]

try:
    print("[🔴 LIVE NOW] You are on the air! Speak into your microphone...")
    print("Streaming directly to Zeno.fm...")
    
    # We use subprocess.run to let FFmpeg handle the network transmission entirely!
    subprocess.run(cmd)
    
except KeyboardInterrupt:
    print("\n[⏹ OFF AIR] Stopping broadcast...")
except Exception as e:
    print(f"\nBroadcast ended: {e}")
