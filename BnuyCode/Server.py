import os
import json
import time
import logging
import flask.cli
from . import UI
from flask import Flask, request, jsonify

# Messaging port: 8008 
## hehe funy number


def message_receive(ui):
    cached_msg = []

    def send_cached_msgs(cached_msg, ui):
        os.write(ui.write_fd, json.dumps(cached_msg).encode())

    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    app = Flask(__name__)

    @app.route("/message", methods=["POST"])
    def get_msg():
        data = request.get_json(silent=True, force=True)
        if data is None:
            return jsonify({"status": "unknown POST request"}), 404
        elif not isinstance(data, dict):
            return jsonify({"status": f"unknown/garbled data: {data}, expected dict"})

        if ui.write_fd is None:
            cached_msg.append(data)
        else:

            if len(cached_msg) > 0:
                cached_msg.append(data)
                send_cached_msgs(cached_msg, ui)
                cached_msg.clear()

            else:
                os.write(ui.write_fd, json.dumps(data).encode())

        return jsonify({"status": "received"}), 200
    flask.cli.show_server_banner = lambda *a, **k: None
    app.run(host="0.0.0.0", port=8008, threaded=True)

