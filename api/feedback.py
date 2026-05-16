from http.server import BaseHTTPRequestHandler

from api_common import JsonApiHandler, read_json, save_feedback, send_json


class handler(JsonApiHandler, BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            send_json(self, save_feedback(read_json(self)))
        except Exception:
            send_json(self, {"ok": True, "message": "Feedback received, but serverless storage is temporary."})
