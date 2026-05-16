from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from api_common import CLIENT, JsonApiHandler, send_json


class handler(JsonApiHandler, BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        keyword = (params.get("q") or [""])[0]
        city = (params.get("city") or [""])[0]
        try:
            send_json(self, {"items": CLIENT.search_pois(keyword, city=city)})
        except ValueError as exc:
            self.send_error_json(exc, 400)
        except Exception as exc:
            self.send_error_json(exc)
