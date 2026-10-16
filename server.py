from flask import Flask, request, jsonify, send_from_directory, abort
import pathlib, re, os, uuid
import yt_dlp

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB

BASE = pathlib.Path(__file__).parent.resolve()
UPLOAD_DIR = BASE / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
(BASE / "assets").mkdir(exist_ok=True)

last_sync = {"action": "init"}

def clean_yt_url(url: str):
    m = re.search(r'(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})', url or "")
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    return (url or "").strip()

def safe_filename(name: str) -> str:
    name = re.sub(r'[^A-Za-z0-9._-]+', '_', name or "audio.m4a").strip("._")
    stem, suffix = os.path.splitext(name)
    return f"{stem[:50]}_{uuid.uuid4().hex[:6]}{suffix or '.m4a'}"

@app.route("/")
def index():
    return send_from_directory(str(BASE), "index.html")

@app.route("/assets/<path:p>")
def assets(p):
    return send_from_directory(str(BASE / "assets"), p)

@app.route("/uploads/<path:p>")
def uploads(p):
    # block traversal
    if ".." in p or p.startswith("/"):
        abort(400)
    return send_from_directory(str(UPLOAD_DIR), p)

@app.route("/api/sync", methods=["GET","POST"])
@app.route("/api/portal/sync", methods=["GET","POST"])
def sync():
    return jsonify(last_sync)

@app.route("/api/files")
def files():
    fs = [{"name": fp.name, "url": f"/uploads/{fp.name}", "size": fp.stat().st_size}
          for fp in UPLOAD_DIR.glob("*") if fp.is_file()]
    return jsonify(sorted(fs, key=lambda x: x["name"]))

@app.route("/api/delete", methods=["POST"])
def delete_file():
    name = pathlib.Path((request.get_json() or {}).get("file") or "").name
    if not name:
        return jsonify({"ok": False}), 400
    try:
        (UPLOAD_DIR / name).unlink(missing_ok=True)
    except Exception as e:
        print(f"[DELETE ERROR] {e}")
    return jsonify({"ok": True})

@app.route("/api/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "no file"}), 400
    fn = safe_filename(f.filename)
    f.save(UPLOAD_DIR / fn)
    return jsonify({"ok": True, "file": fn})

@app.route("/api/youtube", methods=["POST"])
def youtube():
    data = request.get_json() or {}
    url = clean_yt_url(data.get("url") or "")
    if not url:
        return jsonify({"ok": False, "error": "no url"}), 400

    cookie = next((str(p) for p in [BASE / "cookies.txt", BASE / "www.youtube.com_cookies.txt"] if p.exists()), None)
    
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': str(UPLOAD_DIR / '%(title).100s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'restrictfilenames': True,
    }
    if cookie:
        ydl_opts['cookiefile'] = cookie

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return jsonify({"ok": True, "title": info.get('title')})
    except Exception as e:
        print(f"[YT ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)[:500]}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)
