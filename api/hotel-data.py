from http.server import BaseHTTPRequestHandler

from api_common import JsonApiHandler, hotel_data_status, read_json, save_hotel_data, send_json


class handler(JsonApiHandler, BaseHTTPRequestHandler):
    def do_GET(self):
        send_json(self, hotel_data_status())

    def do_POST(self):
        try:
            send_json(self, save_hotel_data(read_json(self)))
        except ValueError as exc:
            self.send_error_json(exc, 400)
        except Exception as exc:
            self.send_error_json(exc)
