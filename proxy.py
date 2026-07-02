"""
서울시 버스도착정보 API 로컬 CORS 프록시.

사용법:
    python proxy.py            # 기본 포트 8787
    python proxy.py 9000       # 다른 포트 지정

위젯 설정에서:
    데이터 모드: "로컬 프록시"
    프록시 URL: http://localhost:8787

호출 규격:
    GET /proxy?url=<URL-encoded target URL>
    허용 도메인: ws.bus.go.kr (안전을 위해 화이트리스트로 제한)
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
import re
import sys

ALLOWED_HOSTS = {"ws.bus.go.kr"}
DEFAULT_PORT = 8787


class _NoRedirect(HTTPRedirectHandler):
    """3xx 응답을 따라가지 않는다 — 리다이렉트로 화이트리스트를 우회하지 못하게."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = build_opener(_NoRedirect())


class ProxyHandler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/proxy":
            self.send_response(404)
            self._cors()
            self.end_headers()
            self.wfile.write(b'{"error":"use /proxy?url=..."}')
            return

        qs = parse_qs(parsed.query)
        target = qs.get("url", [""])[0]
        if not target:
            self.send_response(400)
            self._cors()
            self.end_headers()
            self.wfile.write(b'{"error":"missing url"}')
            return

        target_host = urlparse(target).hostname or ""
        if target_host not in ALLOWED_HOSTS:
            self.send_response(403)
            self._cors()
            self.end_headers()
            self.wfile.write(
                f'{{"error":"host not allowed: {target_host}"}}'.encode("utf-8")
            )
            return

        try:
            req = Request(target, headers={"User-Agent": "bus-widget-proxy/1.0"})
            with _OPENER.open(req, timeout=10) as res:
                body = res.read()
                content_type = res.headers.get("Content-Type", "application/json")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self._cors()
            self.end_headers()
            self.wfile.write(body)
        except HTTPError as e:
            self.send_response(e.code)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"error":"upstream {e.code}"}}'.encode("utf-8"))
        except URLError as e:
            self.send_response(502)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"error":"{e.reason}"}}'.encode("utf-8"))

    def log_message(self, fmt, *args):
        # 쿼리스트링(serviceKey 포함)은 로그에 남기지 않는다
        msg = re.sub(r"\?[^\s\"]*", "?[redacted]", fmt % args)
        sys.stderr.write("[proxy] " + msg + "\n")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    httpd = ThreadingHTTPServer(("127.0.0.1", port), ProxyHandler)
    print(f"bus-widget proxy running at http://localhost:{port}")
    print(f"allowed hosts: {', '.join(sorted(ALLOWED_HOSTS))}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
        httpd.server_close()


if __name__ == "__main__":
    main()
