# server.py V9.9 - POT TOKEN BYPASS
from flask import Flask, request, jsonify, send_from_directory
import pathlib, re, os
import yt_dlp

app = Flask(__name__)
BASE = pathlib.Path(__file__).parent
UPLOAD_DIR = BASE / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
last_sync = {"action":"init"}

def get_cookie():
    for n in ["cookies.txt","www.youtube.com_cookies.txt"]:
        p=BASE/n
        if p.exists(): return str(p)
    return None

def clean_yt_url(url):
    m=re.search(r'(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})', url or "")
    if m: return f"https://www.youtube.com/watch?v={m.group(1)}"
    return url

@app.route("/")
def index(): return send_from_directory(str(BASE),"index.html")
@app.route("/assets/<path:p>")
def assets(p): return send_from_directory(str(BASE/"assets"),p)
@app.route("/uploads/<path:p>")
def uploads(p): return send_from_directory(str(UPLOAD_DIR),p)
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
    return jsonify([{"name":f.name,"url":f"/uploads/{f.name}"} for f in UPLOAD_DIR.glob("*") if f.is_file()])
@app.route("/api/delete", methods=["POST"])
def delete_file():
    try: (UPLOAD_DIR/(request.get_json() or {}).get("file","")).unlink(missing_ok=True)
    except: pass
    return jsonify({"ok":True})
@app.route("/api/upload", methods=["POST"])
def upload():
    f=request.files.get("file")
    fn=re.sub(r'[^A-Za-z0-9._-]','_',f.filename or "a.m4a")
    f.save(UPLOAD_DIR/fn)
    return jsonify({"ok":True})

@app.route("/api/youtube", methods=["POST"])
def youtube():
    url=clean_yt_url((request.get_json() or {}).get("url") or "")
    cookie=get_cookie()
    print(f"[YT] URL={url} cookie={bool(cookie)}")
    
    # On essaye 2 configs
    configs = [
        {'clients':['web','android'], 'use_cookie': True},
        {'clients':['android','ios'], 'use_cookie': False},
    ]
    
    last_err=""
    for cfg in configs:
        opts={
            'format':'bestaudio/best',
            'outtmpl':str(UPLOAD_DIR/'%(title)s.%(ext)s'),
            'noplaylist':True,
            'quiet':False,
            'extractor_args':{
                'youtube':{
                    'player_client': cfg['clients'],
                    'po_token': ['web+android+ios+'],
                }
            },
            'postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}],
        }
        if cfg['use_cookie'] and cookie:
            opts['cookiefile']=cookie
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info=ydl.extract_info(url, download=True)
                return jsonify({"ok":True,"title":info.get('title')})
        except Exception as e:
            last_err=str(e)
            print(f"[FAIL {cfg['clients']}] {last_err[:300]}")
            continue
            
    return jsonify({"ok":False,"error":last_err[:600]}),500

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8000)))
