"""Read-only HTTP server for the seven-day view.

Standard library only: ``http.server`` plus :mod:`heizungslogger.web`. The
server never writes and never touches the serial port, so it can run with a much
stricter sandbox than the logger itself.
"""

import argparse
import datetime
import http.server
import os

import dateutil.tz

from heizungslogger import web


class App:
    """Render the page, reusing the last result while the files are unchanged."""

    def __init__(self, log_directory: str, tz=None, refresh_seconds: float = 60.0) -> None:
        self.log_directory = log_directory
        self.tz = tz or dateutil.tz.tzlocal()
        self.refresh_seconds = refresh_seconds
        self._signature: tuple | None = None
        self._built_at: datetime.datetime | None = None
        self._body = b""

    @staticmethod
    def _signature_now(paths: list[str]) -> tuple:
        signature = []
        for path in paths:
            try:
                info = os.stat(path)
            except OSError:
                signature.append((path, None, None))
            else:
                signature.append((path, info.st_mtime_ns, info.st_size))
        return tuple(signature)

    def page(self, now: datetime.datetime | None = None) -> tuple[int, bytes]:
        """Return ``(status, body)`` for ``GET /``."""
        now = now or datetime.datetime.utcnow()
        if not os.path.isdir(self.log_directory):
            body = (
                "<!doctype html><meta charset='utf-8'><h1>Unavailable</h1>"
                f"<p>log directory not found: {self.log_directory}</p>"
            )
            return 503, body.encode("utf-8")

        start = web.window_start(now)
        paths = web.window_paths(self.log_directory, start)
        signature = self._signature_now(paths)
        stale = self._built_at is None or (
            now - self._built_at
        ).total_seconds() >= self.refresh_seconds
        if self._body and signature == self._signature and not stale:
            return 200, self._body

        samples = web.load_samples(paths)
        buckets = web.bucketize(samples, start)
        body = web.render_page(buckets, samples, start, now, self.tz)
        self._signature = signature
        self._built_at = now
        self._body = body.encode("utf-8")
        return 200, self._body


class Handler(http.server.BaseHTTPRequestHandler):
    """Serve exactly one page."""

    server_version = "heizungslogger-web"
    protocol_version = "HTTP/1.0"

    def do_GET(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        if self.path.split("?", 1)[0] not in ("/", "/index.html"):
            self.send_error(404)
            return
        status, body = self.server.app.page()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


class Server(http.server.ThreadingHTTPServer):
    """Threading server carrying the page builder."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], app: App) -> None:
        self.app = app
        super().__init__(address, Handler)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only seven-day view of the day files")
    parser.add_argument("--log_directory", help="Directory holding the LOG files", type=str)
    parser.add_argument("--bind", help="Address to listen on", type=str, default="0.0.0.0")
    parser.add_argument("--port", help="Port to listen on", type=int, default=80)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the server. Returns the process exit status."""
    args = build_parser().parse_args(argv)
    log_directory = args.log_directory if args.log_directory is not None else "./"
    app = App(log_directory)

    try:
        server = Server((args.bind, args.port), app)
    except PermissionError:
        print(f"cannot bind {args.bind}:{args.port}: permission denied")
        print("port 80 needs CAP_NET_BIND_SERVICE on the unit (see docs/OPERATIONS.md)")
        return 1
    except OSError as exc:
        print(f"cannot bind {args.bind}:{args.port}: {exc}")
        return 1

    print(f"serving {log_directory} on http://{args.bind}:{args.port}/ (read-only)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
