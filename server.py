# server.py V9.2 SYNC FIX - DIVINARVIS + CAPITAL + YT + UPLOAD IPHONE
from flask import Flask, request, jsonify, send_from_directory
import pathlib, datetime, re, os

app = Flask(__name__)
BASE = pathlib.Path(__file__).parent
UPLOAD_DIR = BASE / "uploads"import os
from flask import Flask, request, jsonify, send_from_directory
import yt_dlp
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- COOKIES AUTO-DETECT ---
def get_cookie_file():
    for name in ["cookies.txt", "www.youtube.com_cookies.txt", "youtube.com_cookies.txt"]:
        if os.path.exists(name):
            print(f"✅ Found cookie file: {name}")
            return name
    print("⚠️ No cookie file found")
    return None

COOKIE_FILE = get_cookie_file()

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def serve_static(path):
    if os.path.exists(path):
        return send_from_directory(".", path)
    return send_from_directory(".", "index.html")

@app.route("/api/files")
def list_files():
    files = []
    if os.path.exists(UPLOAD_FOLDER):
        for f in os.listdir(UPLOAD_FOLDER):
            if f.endswith(".mp3"):
                files.append(f)
    return jsonify(files)

@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files["file"]
    filename = secure_filename(file.filename)
    dest = os.path.join(UPLOAD_FOLDER, filename)
    file.save(dest)
    print(f"[UPLOAD OK] {filename}")
    return jsonify({"ok": True, "file": filename})

@app.route("/api/youtube", methods=["POST"])
def youtube_dl():
    data = request.get_json() or {}
    url = data.get("url") or request.form.get("url")
    if not url:
        return jsonify({"error": "No url"}), 400

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(UPLOAD_FOLDER, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web', 'ios']
            }
        },
        'noplaylist': True,
        'quiet': False,
    }

    cookie_file = get_cookie_file()
    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base = os.path.splitext(os.path.basename(ydl.prepare_filename(info)))[0]
            mp3_name = base + ".mp3"
            return jsonify({"ok": True, "file": mp3_name})
    except Exception as e:
        print(f"[YT ERROR] {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
UPLOAD_DIR.mkdir(exist_ok=True)
( BASE / "assets").mkdir(exist_ok=True)

print(f"[INIT] Upload folder = {UPLOAD_DIR.resolve()}")
print(f"[INIT] Content = {list(UPLOAD_DIR.glob('*'))}")

RADIOS = [
    {"name": "Capital London", "url": "https://media-ice.musicradio.com/CapitalMP3"},
    {"name": "Capital XTRA", "url": "https://media-ice.musicradio.com/CapitalXTRANationalMP3"},
]

last_sync = {"action":"init","ts":0}

def clean_yt_url(url: str) -> str:
    url = url.strip()
    url = re.sub(r'\?si=.*$', '', url)
    url = re.sub(r'\?is=.*$', '', url)
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
        # print(f"[SYNC] {last_sync}")
        return jsonify({"ok":True})
    return jsonify(last_sync)

@app.route("/api/files")
def files():
    fs=[]
    for fp in UPLOAD_DIR.glob("*"):
        if fp.is_file():
            fs.append({"name": fp.name, "url": f"/uploads/{fp.name}", "size": fp.stat().st_size})
    print(f"[FILES] {len(fs)} fichiers")
    return jsonify(fs)

@app.route("/api/delete", methods=["POST"])
def delete_file():
    name=(request.get_json() or {}).get("file")
    try: 
        (UPLOAD_DIR / name).unlink(missing_ok=True)
        print(f"[DELETE] {name}")
    except Exception as e: print(f"[DELETE ERR] {e}")
    return jsonify({"ok":True})

# --- C'EST ICI QUE CA BLOQUAIT ---
@app.route("/api/upload", methods=["POST"])
def upload():
    print(f"[UPLOAD] Requête reçue de {request.remote_addr}")
    print(f"[UPLOAD] files={list(request.files.keys())} form={list(request.form.keys())}")
    f = request.files.get("file")
    if not f:
        print("[UPLOAD] ERREUR: pas de fichier 'file' dans la requête")
        return jsonify({"ok":False,"error":"no file field"}),400
    filename = f.filename
    # sécurise nom iPhone qui a des espaces / accents
    filename = re.sub(r'[^A-Za-z0-9._-]', '_', filename)
    if not filename: filename = f"iphone_{datetime.datetime.now().strftime('%H%M%S')}.m4a"
    path = UPLOAD_DIR / filename
    try:
        f.save(path)
        print(f"[UPLOAD OK] {path} - {path.stat().st_size} bytes")
        return jsonify({"ok":True,"file":filename,"url":f"/uploads/{filename}"})
    except Exception as e:
        print(f"[UPLOAD FAIL] {e}")
        return jsonify({"ok":False,"error":str(e)}),500

@app.route("/api/youtube", methods=["POST"])
def youtube():
    raw_url=(request.get_json() or {}).get("url","")
    url=clean_yt_url(raw_url)
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(UPLOAD_DIR / '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'extractor_args': {'youtube': {'player_client': ['android','web']}},
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info=ydl.extract_info(url, download=True)
            title=info.get('title','audio')
            return jsonify({"ok":True,"title":title,"file":title+".mp3"})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)[:300]})

if __name__=="__main__":
    print("DIVINARVIS V9.2 SYNC FIX sur http://0.0.0.0:8000")
    print(f"Uploads folder: {UPLOAD_DIR.resolve()}")
    app.run(host="0.0.0.0", port=8000, debug=True)
