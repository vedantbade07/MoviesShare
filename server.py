#!/usr/bin/env python3
"""
MovieShare: a small password-protected movie/file browser.
Python 3.9+; standard library only.
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, quote, urlsplit
import argparse
import base64
import html
import mimetypes
import os
import re
import secrets
import sys

CHUNK_SIZE = 256 * 1024

PAGE_STYLE = """
:root{color-scheme:dark;--bg:#10131a;--panel:#191e28;--text:#f3f5f7;--muted:#aab3c2;--accent:#7c9cff;--line:#2a3240}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:28px max(20px,calc((100% - 1050px)/2));background:linear-gradient(120deg,#202b43,#171a24);border-bottom:1px solid var(--line)}
h1{margin:0;font-size:clamp(1.5rem,4vw,2.2rem)}header p{margin:6px 0 0;color:var(--muted)}
main{max-width:1050px;margin:24px auto;padding:0 18px}
.breadcrumb{color:var(--muted);margin-bottom:18px;overflow-wrap:anywhere}.breadcrumb a,a{color:var(--accent);text-decoration:none}.breadcrumb a:hover,a:hover{text-decoration:underline}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.card{display:flex;gap:12px;align-items:center;min-height:76px;padding:14px;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.icon{font-size:1.7rem;flex:0 0 36px;text-align:center}.name{font-weight:600;overflow-wrap:anywhere}.meta{font-size:.85rem;color:var(--muted)}
.player{width:100%;max-height:72vh;background:#000;border-radius:12px}.actions{margin:14px 0 22px;display:flex;gap:12px;flex-wrap:wrap}
.button{display:inline-block;background:#28344e;border:1px solid #435578;border-radius:9px;padding:9px 13px;color:var(--text)}
footer{max-width:1050px;margin:35px auto;padding:0 18px 25px;color:var(--muted);font-size:.85rem}
.empty{color:var(--muted);padding:22px;background:var(--panel);border-radius:12px}
"""

def human_size(size):
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024

def safe_join(root: Path, url_path: str) -> Path:
    decoded = unquote(url_path)
    # Treat URL paths as POSIX paths, regardless of Windows host.
    parts = [p for p in decoded.replace("\\", "/").split("/") if p not in ("", ".", "..")]
    candidate = root.joinpath(*parts).resolve()
    if candidate != root and root not in candidate.parents:
        raise PermissionError("Path is outside the shared folder")
    return candidate

class MovieShareHandler(BaseHTTPRequestHandler):
    server_version = "MovieShare/1.0"

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {self.client_address[0]} - {fmt % args}")

    def _authorized(self):
        header = self.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                raw = base64.b64decode(header[6:], validate=True).decode("utf-8")
                username, sep, password = raw.partition(":")
                if sep and secrets.compare_digest(username, self.server.share_user) and secrets.compare_digest(password, self.server.share_password):
                    return True
            except (ValueError, UnicodeDecodeError):
                pass
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="MovieShare", charset="UTF-8"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return False

    def _send_html(self, title, body, status=200):
        page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · MovieShare</title>
<style>{PAGE_STYLE}</style></head><body><header><h1>🎬 MovieShare</h1>
<p>Your personal movie and file library</p></header><main>{body}</main>
<footer>MovieShare · Private folder browser · Only share access with people you trust.</footer></body></html>"""
        data = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _url_for(self, rel, directory=False):
        encoded = "/".join(quote(part, safe="") for part in rel.parts)
        url = "/" + encoded
        if directory and not url.endswith("/"):
            url += "/"
        return url or "/"

    def _directory(self, path, rel):
        if not self.path.endswith("/") and self.path.split("?", 1)[0] != "/":
            self.send_response(301)
            self.send_header("Location", self._url_for(rel, True))
            self.end_headers()
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))
        except PermissionError:
            self.send_error(403, "Folder access denied")
            return

        crumbs = ['<a href="/">Home</a>']
        current = Path()
        for part in rel.parts:
            current = current / part
            crumbs.append(f'<a href="{self._url_for(current, True)}">{html.escape(part)}</a>')
        cards = []
        if rel.parts:
            parent = rel.parent
            cards.append(f'<a class="card" href="{self._url_for(parent, True)}"><span class="icon">↩️</span><span><div class="name">Parent folder</div><div class="meta">Go up one level</div></span></a>')
        for item in entries:
            # Do not follow symlinks; this prevents sharing files outside the configured folder.
            if item.is_symlink():
                continue
            item_rel = rel / item.name
            is_dir = item.is_dir()
            href = self._url_for(item_rel, is_dir)
            icon = "📁" if is_dir else ("🎞️" if item.suffix.lower() in {".mp4",".mkv",".webm",".mov",".m4v",".ogv"} else "📄")
            meta = "Folder" if is_dir else human_size(item.stat().st_size)
            cards.append(f'<a class="card" href="{href}"><span class="icon">{icon}</span><span><div class="name">{html.escape(item.name)}</div><div class="meta">{meta}</div></span></a>')
        body = f'<div class="breadcrumb">{" / ".join(crumbs)}</div>'
        body += '<div class="grid">' + "".join(cards) + '</div>' if cards else '<div class="empty">This folder is empty.</div>'
        self._send_html(" / ".join(rel.parts) or "Home", body)

    def _file(self, path, rel):
        if not path.is_file():
            self.send_error(404, "File not found")
            return
        size = path.stat().st_size
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        encoded_name = quote(path.name, safe="")
        streamable = mime.startswith("video/") or mime.startswith("audio/")
        body = f'<div class="breadcrumb"><a href="/">Home</a> / <a href="{self._url_for(rel.parent, True)}">{html.escape(str(rel.parent) if str(rel.parent) != "." else "Home")}</a> / {html.escape(path.name)}</div>'
        if streamable:
            body += f'<video class="player" controls preload="metadata" src="{self._url_for(rel)}"></video>'
        body += f'<h2>{html.escape(path.name)}</h2><p class="meta">{human_size(size)} · {html.escape(mime)}</p><div class="actions"><a class="button" href="{self._url_for(rel)}?download=1">⬇ Download file</a><a class="button" href="{self._url_for(rel.parent, True)}">← Back to folder</a></div>'
        self._send_html(path.name, body)

    def _serve_file(self, path, download=False):
        try:
            size = path.stat().st_size
            start, end = 0, size - 1
            range_header = self.headers.get("Range")
            status = 200
            if range_header:
                match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
                if not match or (not match.group(1) and not match.group(2)):
                    self.send_error(416, "Invalid byte range")
                    return
                if match.group(1):
                    start = int(match.group(1))
                    if match.group(2):
                        end = int(match.group(2))
                else:
                    suffix = int(match.group(2))
                    start = max(0, size - suffix)
                if start >= size or start > end:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                end = min(end, size - 1)
                status = 206
            length = max(0, end - start + 1)
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            if download:
                self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(path.name)}")
            self.end_headers()
            if self.command != "HEAD":
                with path.open("rb") as f:
                    f.seek(start)
                    remaining = length
                    while remaining:
                        chunk = f.read(min(CHUNK_SIZE, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        self._handle_request()

    def do_HEAD(self):
        self._handle_request()

    def _handle_request(self):
        if not self._authorized():
            return
        parsed = urlsplit(self.path)
        try:
            path = safe_join(self.server.root, parsed.path)
        except PermissionError:
            self.send_error(403, "Path outside shared folder")
            return
        if not path.exists():
            self.send_error(404, "Not found")
            return
        if path.is_symlink():
            self.send_error(403, "Symbolic links are not shared")
            return
        rel = path.relative_to(self.server.root)
        if path.is_dir():
            self._directory(path, rel)
        else:
            query = dict(part.split("=", 1) if "=" in part else (part, "") for part in parsed.query.split("&") if part)
            if query.get("download") == "1":
                self._serve_file(path, download=True)
            elif self.command == "HEAD" or self.headers.get("Range"):
                self._serve_file(path)
            else:
                self._file(path, rel)

def main():
    parser = argparse.ArgumentParser(description="Password-protected browser-based file and movie server.")
    parser.add_argument("--directory", default=r"D:\Movies", help="Folder to share (default: D:\\Movies)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address; use 0.0.0.0 for LAN/tunnel access")
    parser.add_argument("--port", type=int, default=6789)
    parser.add_argument("--user", default=os.environ.get("MOVIESHARE_USER", "viewer"))
    parser.add_argument("--password", default=os.environ.get("MOVIESHARE_PASSWORD"))
    args = parser.parse_args()

    root = Path(args.directory).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"Shared folder does not exist: {root}")
    password = args.password or secrets.token_urlsafe(12)
    if len(password) < 12:
        parser.error("Password must be at least 12 characters long.")

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    httpd = Server((args.host, args.port), MovieShareHandler)
    httpd.root = root
    httpd.share_user = args.user
    httpd.share_password = password

    print("\nMovieShare is running.")
    print(f"Folder:   {root}")
    print(f"Local URL: http://127.0.0.1:{args.port}")
    print(f"Username: {args.user}")
    print(f"Password: {password}")
    print("\nKeep this window open. Press Ctrl+C to stop.")
    print("For remote access, use a private VPN such as Tailscale or an HTTPS tunnel.")
    print("Do not expose this plain-HTTP server directly to the public internet.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping MovieShare...")
    finally:
        httpd.server_close()

if __name__ == "__main__":
    main()
