# server.py V9.6 - RETRY MULTI-CLIENT - FIX DEFINITIF
from flask import Flask, request, jsonify, send_from_directory
import pathlib, re, os
import yt_dlp

app = Flask(__name__)
BASE = pathlib.Path(__file__).parent
UPLOAD_DIR = BASE / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
(BASE / "assets").mkdir(exist_ok=True)

def get_cookie_file():
    for name in ["cookies.txt", "www.youtube.com_cookies.txt"]:
        p = BASE / name
        if p.exists(): return str(p)
        if os.path.exists(name): return name
    return None

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
    try: (UPLOAD_DIR / name).unlink(missing_ok=True)
    except: pass
    return jsonify({"ok":True})

@app.route("/api/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f: return jsonify({"ok":False,"error":"no file"}),400
    filename = re.sub(r'[^A-Za-z0-9._-]', '_', f.filename or "") or "iphone.m4a"
    path = UPLOAD_DIR / filename
    f.save(path)
    return jsonify({"ok":True,"file":filename,"url":f"/uploads/{filename}"})

@app.route("/api/youtube", methods=["POST"])
def youtube():
    url = clean_yt_url((request.get_json() or {}).get("url") or "")
    cookie_file = get_cookie_file()
    
    # On va essayer 3 configurations différentes
    configs = []
    if cookie_file:
        configs.append(['web', 'tv'])
        configs.append(['web'])
        configs.append(['ios', 'web'])
    else:
        configs.append(['android', 'ios'])
        configs.append(['web', 'android'])
        configs.append(['tv'])

    last_error = ""
    for clients in configs:
        print(f"[YT TRY] clients={clients} cookie={bool(cookie_file)}")
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/bestvideo*+bestaudio/best',
            'outtmpl': str(UPLOAD_DIR / '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': False,
            'nocheckcertificate': True,
            'extractor_args': {'youtube': {'player_client': clients}},
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        }
        if cookie_file:
            ydl_opts['cookiefile'] = cookie_file
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return jsonify({"ok":True,"title":info.get('title','audio')})
        except Exception as e:
            last_error = str(e)
            print(f"[YT FAIL {clients}] {last_error[:200]}")
            continue

    return jsonify({"ok":False,"error":last_error[:500]}), 500

if __name__=="__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
