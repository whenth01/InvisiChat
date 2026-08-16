import http.server
import socket
import socketserver


def start_server():
    PORT = 8008
    Handler = http.server.SimpleHTTPRequestHandler

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", PORT), Handler)

    try:
        with httpd as req:
            req.serve_forever()

    finally:
        httpd.shutdown(socket.SHUT_RDWR)
        httpd.close()

