"""HTTP request handler: JSON helpers, static files and route dispatch."""
import json
import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler

from services.config import MAX_BODY_BYTES, WEB_DIST
from services.routes_get import GET_ROUTES
from services.routes_risk import POST_ROUTES


class AnalyzerHandler(BaseHTTPRequestHandler):
    def send_json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, file_path):
        data = file_path.read_bytes()
        ctype, _ = mimetypes.guess_type(str(file_path))
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY_BYTES:
            raise ValueError("Invalid request body size")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def log_message(self, format, *args):
        # Keep daemon logs concise
        return

    def serve_frontend(self, url_path):
        if not WEB_DIST.exists():
            self.send_json(503, {"error": "Frontend not built yet. Run npm run build in app/web."})
            return
        candidate = (WEB_DIST / (url_path.lstrip("/") or "index.html")).resolve()
        if not str(candidate).startswith(str(WEB_DIST.resolve())) or not candidate.is_file():
            candidate = WEB_DIST / "index.html"
        self.send_file(candidate)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        try:
            route = GET_ROUTES.get(parsed.path)
            if route is not None:
                code, payload = route(qs)
                self.send_json(code, payload)
            elif parsed.path.startswith("/api/"):
                self.send_json(404, {"error": "Not found"})
            else:
                self.serve_frontend(parsed.path)
        except Exception as exc:
            self.send_json(500, {"error": str(exc)})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            body = self.read_json_body()
            route = POST_ROUTES.get(parsed.path)
            if route is None:
                self.send_json(404, {"error": "Not found"})
                return
            code, payload = route(body)
            self.send_json(code, payload)
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"error": str(exc)})
