# apps/script.py

from http.server import HTTPServer, BaseHTTPRequestHandler


class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Hello from the arbitrary Python script!")


def run(server_class=HTTPServer, handler_class=SimpleHandler, port=9000):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting arbitrary Python script HTTP server on port {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
