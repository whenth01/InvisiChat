import os
import json
import time
import logging
import requests
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
            return jsonify({"status": f"unknown/garbled data: {data}, expected dict"}), 404

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
    app.run(host="0.0.0.0", port=ui.main_obj.data["port"], threaded=True)

def handshake(ui):
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    app = Flask(__name__)
    @app.route("/friend_handshake", methods=["GET"])
    def data_sender():
        uuid = request.args.get("uuid")
        name = request.args.get("name")
        ip = request.args.get("ip")
        if uuid not in ui.messages.keys():
            ui.contact_ips[uuid] = ip
            ui.message_ids[uuid] = set()
            ui.messages[uuid] = []
            ui.create_contact(uuid, name)
        data = {
                "uuid": ui.main_obj.data["uuid"],
                "name": ui.main_obj.data["sender"],
                "port": ui.main_obj.data["port"],
                "ip": ui.main_obj.data["receiver"],
                }

        return jsonify({"status": "success", "data": data}), 200
    flask.cli.show_server_banner = lambda *a, **k: None
    app.run(host="0.0.0.0", port=8009, threaded=True)

def friend_handshake(info):
    page_class = info.get("page_class")
    interface = info.get("interface")
    status_map = info.get("status_map")
    status = info.get("status")
    contact_ip = info.get("link")

    status.set_text("Attempting connection!...")
    status_map.set_attr_map({None: "lgrey_txt"})
    link = contact_ip.get_edit_text()
    try:
        resp = requests.get(f"http://{link}:8009/friend_handshake",
                        params={"uuid": interface.main_obj.data["uuid"],
                        "name": interface.main_obj.data["sender"],
                        "port": interface.main_obj.data["port"],
                        "ip": interface.main_obj.data["receiver"],
                    },
                    timeout=5,)
        if resp.status_code == 200:
            resp = resp.json()
            resp = resp.get("data")
            name = resp.get("name")
            page_class.upd_status(f"Success! You may begin chatting with {name}.", "success")

            if resp.get("uuid") not in interface.messages.keys():
                interface.message_ids[resp.get("uuid")] = set()
                interface.messages[resp.get("uuid")] = []
                interface.contact_ips[resp.get("uuid")] = resp.get("ip")

                interface.create_contact(resp.get("uuid"), resp.get("name"))
        elif resp.status_code == 404:
            page_class.upd_status("404, Unable to connect!", "err")
        else:
            page_class.upd_status(f"Unknown error! Response code: {resp.status_code}")

    except requests.Timeout:
        page_class.upd_status("Failure! Connection timed out :(", "err")

    except requests.ConnectionError:
        page_class.upd_status("Failure! Connection refused, user is offline, or the network is unreachable.", "err")

    except (requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema):
        page_class.upd_status("Invalid URL, please exclude https://, http://, or a port from the link!", "err")
