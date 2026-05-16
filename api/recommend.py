from http.server import BaseHTTPRequestHandler

from api_common import CLIENT, JsonApiHandler, read_json, send_json


class handler(JsonApiHandler, BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            send_json(self, CLIENT.recommend(read_json(self)))
        except ValueError as exc:
            self.send_error_json(exc, 400)
        except Exception as exc:
            self.send_error_json(exc)
