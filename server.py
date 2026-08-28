"""
Hybrid Internet Radio Server (Live Broadcast + Recorded Audio AutoDJ)
Features:
- Non-blocking read1() Live Stream Ingestion from BUTT / Mixxx / Mobile Apps.
- Deterministic 128kbps MP3 Audio Clock: Zero stutter, uninterrupted 24/7 stream.
- Auto-Switch: Smoothly transitions between DJ and AutoDJ background playlist.
- Native HTML5 Web Player & Direct /radio.mp3 Stream for Choyong LC90 / VLC.
"""

import os
import glob
import threading
import queue
import time
import socket
import base64
import json
import collections
import http.client
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))
SOURCE_PASSWORD = os.environ.get("SOURCE_PASSWORD", "myradiopassword")
STATION_NAME = os.environ.get("STATION_NAME", "My Online Radio")

ZENO_SERVER = "link.zeno.fm"
ZENO_PORT = 80
ZENO_MOUNT = "/yz9ttrydrc9uv/source"
ZENO_USER = "source"
ZENO_PASS = "Wg8Lut3x"

AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

is_live = False
current_track = "welcome_jingle.mp3"
state_lock = threading.Lock()

listener_queues = []
listeners_lock = threading.Lock()
buffer_lock = threading.Lock()
# A rolling buffer of 32KB (approx 2 seconds of 128kbps audio) allows listeners to connect quickly without huge delay.
rolling_buffer = collections.deque(maxlen=1024 * 32)
zeno_queue = queue.Queue(maxsize=100)

def broadcast_audio(chunk):
    """Pushes audio chunk to all connected listeners."""
    with buffer_lock:
        for byte in chunk:
            rolling_buffer.append(byte)

    with listeners_lock:
        for q in list(listener_queues):
            try:
                q.put_nowait(chunk)
            except queue.Full:
                try:
                    q.get_nowait()
                    q.put_nowait(chunk)
                except Exception:
                    pass
                    
    try:
        zeno_queue.put_nowait(chunk)
    except queue.Full:
        try:
            zeno_queue.get_nowait()
            zeno_queue.put_nowait(chunk)
        except Exception:
            pass

# Load Jingle and strip ID3 tags once to prevent mid-stream decoder crashes
jingle_bytes = b""
try:
    with open(os.path.join(AUDIO_DIR, "welcome_jingle.mp3"), "rb") as f:
        data = f.read()
        
        # Skip ID3v2 tag at the start
        if data.startswith(b"ID3"):
            size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
            data = data[size + 10:]
            
        # Skip ID3v1 tag at the end
        if data[-128:].startswith(b"TAG"):
            data = data[:-128]
            
        jingle_bytes = data
except Exception as e:
    print(f"Error loading Jingle: {e}", flush=True)

live_mode_type = None

def autodj_worker():
    global current_track, is_live, live_mode_type, last_studio_ping
    jingle_pos = 0
    
    while True:
        if is_live:
            if live_mode_type == "STUDIO" and 'last_studio_ping' in globals() and time.time() - last_studio_ping > 5:
                with state_lock:
                    is_live = False
                    current_track = "welcome_jingle.mp3"
            else:
                time.sleep(1)
                continue

        if not jingle_bytes:
            time.sleep(1)
            continue
            
        try:
            while not is_live:
                chunk = jingle_bytes[jingle_pos:jingle_pos+2048]
                jingle_pos += 2048
                
                if not chunk:
                    # End of jingle, loop back to start
                    jingle_pos = 0
                    continue
                
                broadcast_audio(chunk)
                
                # Sleep to emulate 128kbps (16KB/s). 2048 bytes = 0.125s
                time.sleep(0.125)
        except Exception:
            time.sleep(1)

def zeno_broadcaster_worker():
    auth = base64.b64encode(f"{ZENO_USER}:{ZENO_PASS}".encode()).decode("ascii")
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "audio/mpeg",
        "Ice-Name": STATION_NAME,
        "Ice-Public": "1"
    }
    
    while True:
        try:
            conn = http.client.HTTPConnection(ZENO_SERVER, ZENO_PORT, timeout=10)
            conn.putrequest("PUT", ZENO_MOUNT)
            for header, value in headers.items():
                conn.putheader(header, value)
            conn.endheaders()
            
            print(f"[Zeno] Connected to Zeno.fm successfully! ({ZENO_MOUNT})", flush=True)
            
            # Clear any stale data in the queue
            while not zeno_queue.empty():
                try:
                    zeno_queue.get_nowait()
                except queue.Empty:
                    break
            
            while True:
                chunk = zeno_queue.get()
                conn.send(chunk)
        except Exception as e:
            print(f"[Zeno] Connection lost: {e}. Reconnecting in 5s...", flush=True)
            time.sleep(5)


def get_index_html():
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("""<title>""" + STATION_NAME + """ - Live Radio</title>""", f"<title>{STATION_NAME} - Live Radio</title>")
    html = html.replace("""<h1 class="station-title">""" + STATION_NAME + """</h1>""", f"<h1 class=\"station-title\">{STATION_NAME}</h1>")
    return html

def get_studio_html():
    with open("studio.html", "r", encoding="utf-8") as f:
        return f.read()

class RadioServerHandler(BaseHTTPRequestHandler):
    def do_AUTH(self):
        auth_header = self.headers.get("Authorization", "")
        ice_pwd = self.headers.get("ice-password", "")
        
        if ice_pwd == SOURCE_PASSWORD or auth_header == SOURCE_PASSWORD:
            return True
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                pwd = decoded.split(":")[-1]
                if pwd == SOURCE_PASSWORD:
                    return True
            except Exception:
                pass
        return False

    def handle_live_source(self):
        """Non-blocking live audio ingestion via rfile.read1()."""
        global is_live, current_track
        if not self.do_AUTH():
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Live Broadcast Source"')
            self.end_headers()
            self.wfile.write(b"Unauthorized: Invalid Source Password\n")
            return

        print(f"\n[🎙️ LIVE] Broadcaster CONNECTED from {self.client_address[0]}!", flush=True)
        print(f"[DEBUG] Request Line: {self.requestline}", flush=True)
        print(f"[DEBUG] Headers:\n{self.headers}", flush=True)

        with state_lock:
            is_live = True
            live_mode_type = "SCRIPT"
            current_track = "🔴 LIVE BROADCAST"

        # Set a timeout so we don't hang if the broadcaster drops ungracefully
        self.connection.settimeout(15.0)

        is_chunked = self.headers.get("Transfer-Encoding", "").lower() == "chunked"
        
        try:
            last_keepalive = time.time()
            while True:
                if is_chunked:
                    # Read chunk size line
                    line = self.rfile.readline()
                    if not line:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        chunk_size = int(line, 16)
                    except ValueError:
                        break
                    
                    if chunk_size == 0:
                        break # End of stream
                        
                    # Read exactly chunk_size bytes
                    chunk = self.rfile.read(chunk_size)
                    if not chunk:
                        break
                        
                    # Read the trailing \r\n
                    self.rfile.read(2)
                else:
                    # read1() returns immediately as audio bytes arrive (for non-chunked streams)
                    chunk = self.rfile.read1(2048)
                    if not chunk:
                        print("[!] Broadcaster disconnected.", flush=True)
                        break

                broadcast_audio(chunk)

                # Render proxy enforces a 100-second idle timeout on HTTP requests.
                # Writing a dummy space byte every 30s prevents the connection from being dropped.
                if time.time() - last_keepalive > 30:
                    try:
                        self.wfile.write(b" ")
                        self.wfile.flush()
                        last_keepalive = time.time()
                    except Exception:
                        pass
        except Exception as e:
            print(f"[!] Live stream ended: {e}", flush=True)
        finally:
            print(f"[🎙️ LIVE] Broadcaster DISCONNECTED: {self.client_address[0]}.", flush=True)
            with state_lock:
                is_live = False
                current_track = "welcome_jingle.mp3"
                
            try:
                self.send_response(200)
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(b"Live stream ended.\n")
            except Exception:
                pass

    def do_SOURCE(self):
        self.handle_live_source()

    def do_PUT(self):
        self.handle_live_source()

    def do_POST(self):
        global is_live, current_track, last_studio_ping, live_mode_type
        
        if self.path == "/api/stop":
            if not self.do_AUTH():
                self.send_response(401)
                self.end_headers()
                return
            with state_lock:
                is_live = False
                current_track = "welcome_jingle.mp3"
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return

        if self.path == "/api/stream":
            if not self.do_AUTH():
                self.send_response(401)
                self.end_headers()
                return
            
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                chunk = self.rfile.read(content_length)
                
                with state_lock:
                    is_live = True
                    live_mode_type = "STUDIO"
                    current_track = "🔴 LIVE FROM STUDIO"
                    last_studio_ping = time.time()
                
                broadcast_audio(chunk)
                
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return
            
        self.handle_live_source()

    def do_GET(self):
        if self.path == "/studio":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(get_studio_html().encode("utf-8"))
            return

        if self.path in ("/healthz", "/health"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if self.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with state_lock:
                data = {
                    "station": STATION_NAME,
                    "is_live": is_live,
                    "track": current_track,
                    "listeners": len(listener_queues)
                }
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(get_index_html().encode("utf-8"))
            return

        if self.path.startswith("/radio.mp3") or self.path.startswith("/stream") or self.path.startswith("/live.mp3"):
            print(f"[+] Listener connected from {self.client_address[0]}", flush=True)
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.send_header("Connection", "keep-alive")
            self.send_header("icy-name", STATION_NAME)
            self.send_header("icy-br", "128")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            client_q = queue.Queue(maxsize=100)

            with buffer_lock:
                if rolling_buffer:
                    client_q.put(bytes(rolling_buffer))

            with listeners_lock:
                listener_queues.append(client_q)

            try:
                while True:
                    try:
                        chunk = client_q.get(timeout=10)
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    except queue.Empty:
                        pass
            except (BrokenPipeError, ConnectionResetError, socket.error):
                pass
            finally:
                with listeners_lock:
                    if client_q in listener_queues:
                        listener_queues.remove(client_q)
                print(f"[-] Listener disconnected: {self.client_address[0]}", flush=True)
            return

        self.send_error(404)

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    t = threading.Thread(target=autodj_worker, daemon=True)
    t.start()
    
    t_zeno = threading.Thread(target=zeno_broadcaster_worker, daemon=True)
    t_zeno.start()

    print(f"\n" + "="*60, flush=True)
    print(f"[*] {STATION_NAME} is ONLINE on Port {PORT}!", flush=True)
    print(f"[*] Public Stream: http://0.0.0.0:{PORT}/radio.mp3", flush=True)
    print(f"[*] Live Source Ingest: http://0.0.0.0:{PORT}/live", flush=True)
    print(f"[*] Source Password: {SOURCE_PASSWORD}", flush=True)
    print("="*60 + "\n", flush=True)

    server = ThreadingHTTPServer(("0.0.0.0", PORT), RadioServerHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
