# server.py V9.3 - FIX COOKIES + IPHONE UPLOAD - DIVINARVIS
from flask import Flask, request, jsonify, send_from_directory
import pathlib, datetime, re, os
import yt_dlp

app = Flask(__name__)
BASE = pathlib.Path(__file__).parent
UPLOAD_DIR = BASE / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
(BASE / "assets").mkdir(exist_ok=True)

# --- COOKIES AUTO-DETECT ---
def get_cookie_file():
    for name in ["cookies.txt", "www.youtube.com_cookies.txt", "youtube.com_cookies.txt"]:
        p = BASE / name
        if p.exists():
            print(f"✅ Found cookie file: {p}")
            return str(p)
        if os.path.exists(name):
            print(f"✅ Found cookie file: {name}")
            return name
    print("⚠️ No cookie file found")
    return None

print(f"[INIT] Upload folder = {UPLOAD_DIR.resolve()}")
RADIOS = [
    {"name": "Capital London", "url": "https://media-ice.musicradio.com/CapitalMP3"},
    {"name": "Capital XTRA", "url": "https://media-ice.musicradio.com/CapitalXTRANationalMP3"},
]

last_sync = {"action":"init","ts":0}

def clean_yt_url(url: str) -> str:
    url = url.strip()
    url = re.sub(r'\?si=.*$', '', url)
    m = re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})', url)
    if m: return f"https://www.youtube.com/watch?v={m.group(1)}"
    return url

@app.route("/")
def index(): return send_from_directory(str(BASE), "index.html")
@app.route("/assets/<path:p>")
def assets(p): return send_from_directory(str(BASE / "assets"), p)
@app.route("/uploads/<path:p>")
def uploads(p): return send_from_directory(str(UPLOAD_DIR), p)

@app.route("/api/sync", methods=["GET","POST"])
@app.route("/api/portal/sync", methods=["GET","POST"])
def sync():
    global last_sync
    if request.method=="POST":
        last_sync=request.get_json(force=True) or {}
        return jsonify({"ok":True})
    return jsonify(last_sync)

@app.route("/api/files")
def files():
    fs=[]
    for fp in UPLOAD_DIR.glob("*"):
        if fp.is_file():
            fs.append({"name": fp.name, "url": f"/uploads/{fp.name}", "size": fp.stat().st_size})
    return jsonify(fs)

@app.route("/api/delete", methods=["POST"])
def delete_file():
    name=(request.get_json() or {}).get("file")
    try: 
        (UPLOAD_DIR / name).unlink(missing_ok=True)
    except Exception as e: print(f"[DELETE ERR] {e}")
    return jsonify({"ok":True})

@app.route("/api/upload", methods=["POST"])
def upload():
    print(f"[UPLOAD] files={list(request.files.keys())}")
    f = request.files.get("file")
    if not f:
        return jsonify({"ok":False,"error":"no file field"}),400
    filename = f.filename
    filename = re.sub(r'[^A-Za-z0-9._-]', '_', filename)
    if not filename: filename = f"iphone_{datetime.datetime.now().strftime('%H%M%S')}.m4a"
    path = UPLOAD_DIR / filename
    try:
        f.save(path)
        print(f"[UPLOAD OK] {path} - {path.stat().st_size} bytes")
        return jsonify({"ok":True,"file":filename,"url":f"/uploads/{filename}"})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}),500

@app.route("/api/youtube", methods=["POST"])
def youtube():
    data = request.get_json() or {}
    raw_url = data.get("url") or ""
    url = clean_yt_url(raw_url)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(UPLOAD_DIR / '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': False,
        'extractor_args': {'youtube': {'player_client': ['android', 'web', 'ios']}},
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
    }
    
    cookie_file = get_cookie_file()
    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title','audio')
            return jsonify({"ok":True,"title":title})
    except Exception as e:
        print(f"[YT ERROR] {e}")
        return jsonify({"ok":False,"error":str(e)[:400]}), 500

if __name__=="__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
