from __future__ import annotations

import hmac
import json
import os
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from d8_runtime import MAX_BODY_BYTES, D8Runtime, DeterministicMockAcquisition, config_from_env

PORT = int(os.environ.get("D8_INTERNAL_PORT", "8080"))


def build_runtime() -> D8Runtime:
    config = config_from_env()
    provider_mode = os.environ.get("D8_PROVIDER_MODE", "canonical")
    if provider_mode == "mock":
        if config.profile not in {"development", "test"}:
            raise RuntimeError("mock provider mode is forbidden for VPS_SHADOW")
        core = DeterministicMockAcquisition()
    elif provider_mode == "canonical":
        from acquisition_core import CanonicalAcquisitionCore
        core = CanonicalAcquisitionCore()
    else:
        raise RuntimeError("unsupported D8_PROVIDER_MODE")
    return D8Runtime(config, core)


class Handler(BaseHTTPRequestHandler):
    server_version = "eth-macro-d8/1.0"
    protocol_version = "HTTP/1.1"

    @property
    def runtime(self) -> D8Runtime:
        return self.server.runtime  # type: ignore[attr-defined]

    def _auth(self) -> bool:
        profile = self.runtime.config.profile
        token = os.environ.get("D8_RUNTIME_TOKEN")
        if profile == "VPS_SHADOW" and not token:
            self._json(503, {"status": "FAIL", "error_class": "AUTH_FAILED", "message": "required internal token is not configured"}); return False
        if token:
            auth = self.headers.get("Authorization", "")
            supplied = auth[7:] if auth.startswith("Bearer ") else ""
            if not hmac.compare_digest(supplied, token):
                self._json(401, {"status": "FAIL", "error_class": "AUTH_FAILED"}); return False
        return True

    def do_GET(self) -> None:
        if self.path not in {"/v1/health", "/v1/readiness"}:
            self._json(404, {"status": "FAIL", "error_class": "REQUEST_INVALID"}); return
        if not self._auth(): return
        if self.path == "/v1/health": self._json(200, self.runtime.health()); return
        code, body = self.runtime.readiness(); self._json(code, body)

    def do_POST(self) -> None:
        if self.path != "/v1/collect-cycle":
            self._json(404, {"status": "FAIL", "error_class": "REQUEST_INVALID"}); return
        if not self._auth(): return
        length = self.headers.get("Content-Length")
        if length is None:
            self._json(411, {"status": "FAIL", "error_class": "REQUEST_INVALID"}); return
        try: size = int(length)
        except ValueError:
            self._json(400, {"status": "FAIL", "error_class": "REQUEST_INVALID"}); return
        if size < 0 or size > MAX_BODY_BYTES:
            self._json(413, {"status": "FAIL", "error_class": "REQUEST_INVALID"}); return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json":
            self._json(415, {"status": "FAIL", "error_class": "REQUEST_INVALID"}); return
        try: body = json.loads(self.rfile.read(size))
        except Exception:
            self._json(400, {"status": "FAIL", "error_class": "REQUEST_INVALID"}); return
        code, response = self.runtime.collect_cycle(body); self._json(code, response)

    def do_PUT(self) -> None: self._json(405, {"status": "FAIL", "error_class": "REQUEST_INVALID"})
    def do_DELETE(self) -> None: self._json(405, {"status": "FAIL", "error_class": "REQUEST_INVALID"})
    def log_message(self, fmt: str, *args: Any) -> None:
        # Never log headers or request bodies/tokens.
        print("d8-http " + (fmt % args))

    def _json(self, code: int, value: dict[str, Any]) -> None:
        data = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.send_header("Connection", "close"); self.end_headers(); self.wfile.write(data)


class Server(ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True
    def __init__(self, address, handler, runtime):
        super().__init__(address, handler); self.runtime = runtime


def main() -> None:
    runtime = build_runtime()
    server = Server(("0.0.0.0", PORT), Handler, runtime)
    stop_once = threading.Event()
    def stop(_signum, _frame):
        if stop_once.is_set(): return
        stop_once.set(); runtime.begin_shutdown(); threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
    try: server.serve_forever(poll_interval=0.2)
    finally:
        runtime.begin_shutdown(); server.server_close()

if __name__ == "__main__": main()
