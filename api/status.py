from http.server import BaseHTTPRequestHandler

from api_common import CLIENT, JsonApiHandler, send_json


class handler(JsonApiHandler, BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            send_json(self, CLIENT.status())
        except Exception as exc:
            self.send_error_json(exc)
