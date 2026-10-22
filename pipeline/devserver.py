"""Local preview: serves app/ with single-page-app fallback and data/ at /data/.
Usage: python3 pipeline/devserver.py [port]   (run from the repository root)
"""
import sys, os, http.server, socketserver
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path == "/config.js":
            return str(ROOT / "pipeline" / "dev-config.js")
        if path.startswith("/data/"):
            return str(ROOT / path.lstrip("/"))
        p = ROOT / "app" / path.lstrip("/")
        if path == "/" or not p.exists() or p.is_dir():
            return str(ROOT / "app" / "index.html")
        return str(p)

    def log_message(self, *a):
        pass


(ROOT / "pipeline" / "dev-config.js").write_text(
    'window.MLG_CONFIG = {dataBase: "/data/", fallbackBase: "", ref: "local"};\n')
socketserver.TCPServer.allow_reuse_address = True
with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as s:
    print("serving on", PORT)
    s.serve_forever()
