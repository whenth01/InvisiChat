from flask import Flask, request, jsonify
import logging

def message_receive():
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    app = Flask(__name__)

    @app.route("/message", methods=["POST"])
    def send_msg():
        data = request.get_json()
        print(f"""
Got data:
{data}
""")
        return jsonify({"status": "recieved"}), 200

    app.run(host="0.0.0.0", port=8008)

