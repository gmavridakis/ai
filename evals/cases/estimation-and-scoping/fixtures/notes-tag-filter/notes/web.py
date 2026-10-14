"""Minimal HTTP handler used by the internal notes page (no framework)."""
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from notes.store import NoteStore

STORE = NoteStore()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path != "/search":
            self.send_response(404); self.end_headers(); return
        q = parse_qs(url.query).get("q", [""])[0]
        rows = STORE.search(q)
        body = "\n".join(f'{n["id"]}\t{n["title"]}' for n in rows).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body)
