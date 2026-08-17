from flask import Flask, request, jsonify
import flask.cli
import os
import logging

# Receive port: 8008 
## hehe funy number
# Send port: 0426
## BnuuyPlayer was made on 04/26 !:3


def message_receive():
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    app = Flask(__name__)

    @app.route("/message", methods=["POST"])
    def get_msg():
        data = request.get_json()
        print(f"""
Got data:
{data}
""")
        return jsonify({"status": "recieved"}), 200
    flask.cli.show_server_banner = lambda *a, **k: None
    app.run(host="0.0.0.0", port=8008)

