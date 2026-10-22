# Local review server: serves the review page + audio (with HTTP Range, needed for seeking)
# and autosaves corrections. Binds to 127.0.0.1 only, and answers only requests addressed to it
# (Host check against DNS rebinding) and saves only from its own page (Origin check).
# usage: python3 review_server.py <workdir> [port]   (page from this folder; data, audio, corrections from <workdir>)
import json, os, sys, time, shutil, re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

W = os.path.abspath(sys.argv[1])
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
CORR = os.path.join(W, "corrections.json")
BACKUP_DIR = os.path.join(W, "corrections-backups")
os.makedirs(BACKUP_DIR, exist_ok=True)
PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "review.html")
FILES = {"/": (PAGE, "text/html; charset=utf-8"),
         "/review.html": (PAGE, "text/html; charset=utf-8"),
         "/data.json": (os.path.join(W, "data.json"), "application/json; charset=utf-8"),
         "/orig.flac": (os.path.join(W, "audio", "orig.flac"), "audio/flac"),
         "/clean.flac": (os.path.join(W, "audio", "clean.flac"), "audio/flac")}
last_backup = [0.0]
HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
ORIGINS = {"http://" + h for h in HOSTS}


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body=b"", ctype="text/plain; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if self.headers.get("Host") not in HOSTS:
            return self._send(403, b"forbidden")
        path = self.path.split("?")[0]
        if path == "/api/state":
            body = open(CORR, "rb").read() if os.path.exists(CORR) else b"{}"
            return self._send(200, body, "application/json; charset=utf-8")
        if path not in FILES:
            return self._send(404, b"not found")
        fp, ctype = FILES[path]
        if not os.path.exists(fp): return self._send(404, b"not found")
        size = os.path.getsize(fp)
        rng = self.headers.get("Range")
        if rng and ctype.startswith("audio"):
            m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip())
            if not m or not (m.group(1) or m.group(2)):
                return self._send(416, b"bad range", extra={"Content-Range": f"bytes */{size}"})
            if m.group(1):
                a = int(m.group(1)); b = min(int(m.group(2)) if m.group(2) else size - 1, size - 1)
            else:   # "bytes=-N" = the last N bytes
                a = max(0, size - int(m.group(2))); b = size - 1
            if a >= size or a > b:
                return self._send(416, b"bad range", extra={"Content-Range": f"bytes */{size}"})
            with open(fp, "rb") as f:
                f.seek(a); body = f.read(b - a + 1)
            return self._send(206, body, ctype, {"Content-Range": f"bytes {a}-{b}/{size}", "Accept-Ranges": "bytes"})
        with open(fp, "rb") as f:
            body = f.read()
        return self._send(200, body, ctype, {"Accept-Ranges": "bytes"} if ctype.startswith("audio") else None)

    def do_POST(self):
        # another website open in the same browser must not be able to overwrite the corrections
        if self.headers.get("Host") not in HOSTS or self.headers.get("Origin", next(iter(ORIGINS))) not in ORIGINS:
            return self._send(403, b"forbidden")
        if self.path != "/api/save":
            return self._send(404, b"not found")
        n = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(n)
        try:
            state = json.loads(raw)
        except Exception:
            return self._send(400, b"bad json")
        # once the new page (version 2) has saved, refuse saves from an old open tab of the first page
        if state.get("version") != 2 and os.path.exists(CORR):
            try:
                if json.load(open(CORR)).get("version") == 2:
                    return self._send(409, b'{"ok": false, "error": "old page - reload"}', "application/json")
            except Exception:
                pass
        state["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        tmp = CORR + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        os.replace(tmp, CORR)
        if time.time() - last_backup[0] > 300:  # timestamped copy at most every 5 minutes
            shutil.copy(CORR, os.path.join(BACKUP_DIR, time.strftime("corrections-%Y%m%d-%H%M%S.json")))
            last_backup[0] = time.time()
        return self._send(200, json.dumps({"ok": True, "saved_at": state["saved_at"]}).encode(), "application/json")


print(f"review server on http://127.0.0.1:{PORT}/  (workdir {W})", flush=True)
ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
