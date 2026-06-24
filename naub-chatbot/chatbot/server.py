"""
NAUB Chatbot — Main Web Application Server
Pure Python stdlib HTTP server. No external framework dependencies.
"""

import http.server
import json
import os
import uuid
import urllib.parse
from chatbot.engine import get_engine
from chatbot.database import (
    init_db, log_conversation, get_session_history,
    get_or_create_session, get_analytics, verify_admin
)
from chatbot.validators import validate_query

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Admin session tokens (in-memory; good enough for single-server deployment)
ADMIN_SESSIONS: set[str] = set()

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}


class NAUBHandler(http.server.BaseHTTPRequestHandler):
    log_message = lambda self, *a: None  # suppress default access log

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _get_cookie(self, name: str) -> str | None:
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith(name + "="):
                return part[len(name) + 1:]
        return None

    def _get_session_id(self) -> str:
        sid = self._get_cookie("naub_session")
        if sid:
            return sid
        return str(uuid.uuid4())

    def _render_template(self, filename: str, context: dict = {}) -> str:
        path = os.path.join(TEMPLATES_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        for key, value in context.items():
            html = html.replace("{{ " + key + " }}", str(value))
        return html

    # ── Routing ───────────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        # Static files
        if path.startswith("/static/"):
            self._serve_static(path)
            return

        routes = {
            "/": self._index,
            "/admin": self._admin_login_page,
            "/admin/dashboard": self._admin_dashboard,
            "/admin/logout": self._admin_logout,
            "/api/history": self._api_history,
            "/api/admin/analytics": self._api_analytics,
            "/health": lambda: self._send_json({"status": "ok", "service": "NAUB Chatbot"}),
        }

        handler = routes.get(path)
        if handler:
            handler()
        else:
            self._send_html(self._render_template("404.html"), 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        routes = {
            "/api/chat": self._api_chat,
            "/api/suggest": self._api_suggest,
            "/admin/login": self._admin_login,
        }

        handler = routes.get(path)
        if handler:
            handler()
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── Page Handlers ──────────────────────────────────────────────────────────

    def _index(self):
        html = self._render_template("index.html")
        session_id = self._get_session_id()
        get_or_create_session(session_id)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Set-Cookie", f"naub_session={session_id}; Path=/; SameSite=Lax")
        body = html.encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _admin_login_page(self):
        # Redirect if already logged in
        token = self._get_cookie("naub_admin")
        if token and token in ADMIN_SESSIONS:
            self._redirect("/admin/dashboard")
            return
        html = self._render_template("admin_login.html")
        self._send_html(html)

    def _admin_dashboard(self):
        token = self._get_cookie("naub_admin")
        if not token or token not in ADMIN_SESSIONS:
            self._redirect("/admin")
            return
        analytics = get_analytics()
        html = self._render_template("admin_dashboard.html", {
            "total_messages": analytics["total_messages"],
            "total_sessions": analytics["total_sessions"],
            "accuracy": analytics["accuracy"],
            "fallback_count": analytics["fallback_count"],
        })
        self._send_html(html)

    def _admin_logout(self):
        token = self._get_cookie("naub_admin")
        if token:
            ADMIN_SESSIONS.discard(token)
        self.send_response(302)
        self.send_header("Location", "/admin")
        self.send_header("Set-Cookie", "naub_admin=; Path=/; Max-Age=0")
        self.end_headers()

    def _redirect(self, location: str):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    # ── API Handlers ───────────────────────────────────────────────────────────

    def _api_chat(self):
        body = self._read_body()
        user_message = (body.get("message") or "").strip()
        session_id = self._get_session_id()

        if not user_message:
            self._send_json({"error": "Empty message"}, 400)
            return

        if len(user_message) > 500:
            self._send_json({"error": "Message too long (max 500 chars)"}, 400)
            return

        # ── Gibberish / invalid-input guard ──────────────────────────────
        # Validate BEFORE calling the engine or writing to the database.
        # Gibberish messages are returned with a helpful prompt but are
        # never stored in conversation_logs.
        validation = validate_query(user_message)
        if not validation:
            self._send_json({
                "response": validation.message,
                "intent":   "invalid_input",
                "matched":  False,
                "logged":   False,
                "session_id": session_id,
            })
            return
        # ─────────────────────────────────────────────────────────────────

        engine = get_engine()
        result = engine.get_response(user_message)

        log_conversation(
            session_id=session_id,
            user_message=user_message,
            bot_response=result["response"],
            intent=result["intent"],
            category=result["category"],
            score=result["score"],
            matched=result["matched"],
        )

        self._send_json({
            "response": result["response"],
            "intent": result["intent"],
            "matched": result["matched"],
            "logged":  True,
            "session_id": session_id,
        })

    def _api_suggest(self):
        body = self._read_body()
        partial = (body.get("partial") or "").strip()
        if not partial:
            self._send_json({"suggestions": []})
            return
        engine = get_engine()
        suggestions = engine.get_suggestions(partial)
        self._send_json({"suggestions": suggestions})

    def _api_history(self):
        session_id = self._get_session_id()
        history = get_session_history(session_id)
        self._send_json({"history": history, "session_id": session_id})

    def _api_analytics(self):
        token = self._get_cookie("naub_admin")
        if not token or token not in ADMIN_SESSIONS:
            self._send_json({"error": "Unauthorized"}, 401)
            return
        analytics = get_analytics()
        self._send_json(analytics)

    def _admin_login(self):
        body = self._read_body()
        username = (body.get("username") or "").strip()
        password = (body.get("password") or "").strip()

        if verify_admin(username, password):
            token = str(uuid.uuid4())
            ADMIN_SESSIONS.add(token)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", f"naub_admin={token}; Path=/; SameSite=Lax; HttpOnly")
            body_bytes = json.dumps({"success": True, "redirect": "/admin/dashboard"}).encode()
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            self.wfile.write(body_bytes)
        else:
            self._send_json({"success": False, "error": "Invalid credentials"}, 401)

    # ── Static File Server ─────────────────────────────────────────────────────

    def _serve_static(self, path: str):
        # Security: prevent path traversal
        clean = os.path.normpath(path.lstrip("/"))
        full_path = os.path.join(BASE_DIR, clean)
        if not full_path.startswith(STATIC_DIR):
            self._send_json({"error": "Forbidden"}, 403)
            return

        if not os.path.isfile(full_path):
            self._send_json({"error": "Not found"}, 404)
            return

        ext = os.path.splitext(full_path)[1].lower()
        mime = MIME_TYPES.get(ext, "application/octet-stream")

        with open(full_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(content)
