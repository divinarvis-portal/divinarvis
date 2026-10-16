from flask import Flask, request, jsonify, send_from_directory
import pathlib, re, os
import yt_dlp

app = Flask(__name__)
BASE = pathlib.Path(__file__).parent
UPLOAD_DIR = BASE / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
(BASE / "assets").mkdir(exist_ok=True)

last_sync = {"action":"init"}

def clean_yt_url(url):
    m = re.search(r'(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})', url or "")
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    return url

@app.route("/")
def index():
    return send_from_directory(str(BASE), "index.html")

@app.route("/assets/<path:p>")
def assets(p):
    return send_from_directory(str(BASE / "assets"), p)

@app.route("/uploads/<path:p>")
def uploads(p):
    return send_from_directory(str(UPLOAD_DIR), p)

@app.route("/api/sync", methods=["GET","POST"])
@app.route("/api/portal/sync", methods=["GET","POST"])
def sync():
    return jsonify(last_sync)

@app.route("/api/files")
def files():
    fs = []
    for fp in UPLOAD_DIR.glob("*"):
        if fp.is_file():
            fs.append({"name": fp.name, "url": f"/uploads/{fp.name}"})
    return jsonify(fs)

@app.route("/api/delete", methods=["POST"])
def delete_file():
    name = (request.get_json() or {}).get("file")
    try:
        (UPLOAD_DIR / name).unlink(missing_ok=True)
    except:
        pass
    return jsonify({"ok": True})

@app.route("/api/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    fn = re.sub(r'[^A-Za-z0-9._-]', '_', f.filename or "audio.m4a")
    f.save(UPLOAD_DIR / fn)
    return jsonify({"ok": True})

@app.route("/api/youtube", methods=["POST"])
def youtube():
    data = request.get_json() or {}
    url = clean_yt_url(data.get("url") or "")
    cookie = None
    for n in ["cookies.txt", "www.youtube.com_cookies.txt"]:
        p = BASE / n
        if p.exists():
            cookie = str(p)
    
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': str(UPLOAD_DIR / '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': False,
    }
    if cookie:
        ydl_opts['cookiefile'] = cookie

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return jsonify({"ok": True, "title": info.get('title')})
    except Exception as e:
        print(f"[YT ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)[:800]}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
