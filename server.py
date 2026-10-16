# server.py V10.0 - DIVINARVIS SYNC & UPLOAD
from flask import Flask, request, jsonify, send_from_directory
import pathlib
import re
import os
import yt_dlp

BASE = pathlib.Path(__file__).parent
UPLOAD_DIR = BASE / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

def clean_yt_url(u):
    m = re.search(r'(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})', u or "")
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    return u

@app.route('/')
def index():
    return send_from_directory(str(BASE), "index.html")

@app.route('/assets/<path:p>')
def assets(p):
    return send_from_directory(str(BASE / "assets"), p)

@app.route('/uploads/<path:p>')
def uploads(p):
    return send_from_directory(str(UPLOAD_DIR), p)

@app.route('/api/sync', methods=['GET', 'POST'])
def sync():
    if request.method == 'POST':
        data = request.json or {}
        return jsonify(data)
    return jsonify({"action": "init"})

@app.route('/api/portal/sync', methods=['GET', 'POST'])
def portal_sync():
    return sync()

@app.route('/api/files', methods=['GET'])
def files():
    files_list = [{"name": f.name, "url": f"/uploads/{f.name}"} for f in UPLOAD_DIR.glob("*") if f.is_file()]
    return jsonify(files_list)

@app.route('/api/delete', methods=['POST'])
def delete_file():
    try:
        data = request.get_json() or {}
        filename = data.get("file", "")
        if filename:
            file_path = UPLOAD_DIR / filename
            file_path.unlink(missing_ok=True)
    except Exception:
        pass
    return jsonify({"ok": True})

@app.route('/api/upload', methods=['POST'])
def upload():
    f = request.files.get("file")
    if f and f.filename:
        fn = re.sub(r'[^A-Za-z0-9_.-]', '_', f.filename)
        f.save(UPLOAD_DIR / fn)
        return jsonify({"ok": True, "file": fn})
    return jsonify({"ok": False}), 400

@app.route('/api/youtube', methods=['POST'])
def youtube():
    data = request.get_json() or {}
    url = clean_yt_url(data.get("url", ""))
    if not url:
        return jsonify({"ok": False, "error": "URL manquante"}), 400
    
    cookie = None
    for n in ["cookies.txt", "www.youtube.com_cookies.txt"]:
        p = BASE / n
        if p.exists():
            cookie = str(p)
            break
            
    opts = {
        'format': 'bestaudio/ext=m4a/bestaudio/best',
        'outtmpl': str(UPLOAD_DIR / '%(title)s.%(ext)s'),
        'noplaylist': True,
        'nocheckcertificate': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }
    if cookie:
        opts['cookiefile'] = cookie
        
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return jsonify({"ok": True, "title": info.get('title', 'audio')})
    except Exception as e:
        print(e)
        return jsonify({"ok": False, "error": str(e)[:800]}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))