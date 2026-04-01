#!/usr/bin/env python3
"""Nextflow weblog receiver — captures workflow events as NDJSON.

Starts an HTTP server on a random localhost port, writes the port to
/tmp/weblog_port_{ppid} so the parent shell can discover it.
Receives POST requests from Nextflow's -with-weblog flag and appends
each event as a JSON line to the EVENTS_FILE.
"""

import json
import os
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer

EVENTS_FILE = os.environ.get("EVENTS_FILE", "events.ndjson")


class WeblogHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)
        try:
            event = json.loads(data.decode())
            with open(EVENTS_FILE, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as ex:
            print("Error processing event:", ex)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("localhost", 0))
port = sock.getsockname()[1]
sock.close()

with open("/tmp/weblog_port_" + str(os.getppid()), "w") as f:
    f.write(str(port))

print("Weblog receiver starting on port", port, "writing to", EVENTS_FILE)
HTTPServer(("localhost", port), WeblogHandler).serve_forever()
