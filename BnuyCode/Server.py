import os
import json
import hmac
import logging
import requests
import flask.cli
from . import BnuuyCrypt
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
    
    msg_crypt = ui.main_obj.msg_crypt
    @app.route("/friend_handshake", methods=["GET"])
    def data_sender():
        try: pub_key = int(request.args.get("pub_key"))
        except (ValueError, TypeError):
            return jsonify({"status": "failure",
                            "reason": "Received a non int public key"}), 404
        try:
            hashes = json.loads(request.args.get("hashes"))
        except (ValueError, TypeError, UnicodeDecodeError):
            return jsonify({"status": "failure",
                            "reason": "Received malformed hashes"}), 404
        uuid = request.args.get("uuid")
        name = request.args.get("name")
        ip = request.args.get("ip")

        # note: im not sure how this even works
        selected_authkey = None
        found_hash = False
        def compare_digests(key, auth_key, pub_key, hash):
            expected_digest = msg_crypt.msg_fingerprint(
                    msg_crypt.get_byte(request.args.get(key)),
                    msg_crypt.get_byte(10),
                    None,
                    special_key=auth_key,
                    salt=msg_crypt.get_byte(pub_key))
            return hmac.compare_digest(expected_digest, hash)

        try:
            for key, hash in hashes.items():
                found_hash = False
                key = key.get_text()[0]

                if selected_authkey is not None:
                    if compare_digests(key, auth_key, pub_key, hash):
                        found_hash = True

                else:
                    for auth_key in ui.key_list:
                        if compare_digests(key, auth_key, pub_key, hash):
                            found_hash = True
                            selected_authkey = auth_key
                            break

                if found_hash: continue
                else: break
        except (KeyError, TypeError, BnuuyCrypt.BadParameter):
            return jsonify({"status": "failure",
                            "reason": "A key is missing from the handshake's internals, try updating InvisiChat"}), 404
        except AttributeError:
            # someone may be lingering is just a troll btw :3c
            return jsonify({"status": "failure",
                            "reason": "Invalid data type was sent to the contact, someone may be lingering."}), 404

        if found_hash is False:
            return jsonify({"status": "failure",
                            "reason": "Wrong auth key, or the handshake was modified in transit!"}), 404
        data = {"remove_authkey": selected_authkey}
        os.write(ui.write_fd, json.dumps(data).encode())


        if uuid not in ui.messages.keys():
            try: 
                msg_crypt.simple_contact_signature(uuid, pub_key)
                contact_init = {"save_new_contact": [ip, uuid, name]}
                os.write(ui.write_fd, json.dumps(contact_init).encode())
            except BnuuyCrypt.WeakEncryptor:
                return jsonify({"status": "failure", 
                                "reason": "Received a unsecure public key"}), 404 
            except BnuuyCrypt.AlreadySavedUUID:
                return jsonify({"status": "failure",
                                "reason": "This user is already saved!"}), 404

        data = {"pub_key": msg_crypt.public_key,
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
    msg_crypt = interface.main_obj.msg_crypt
    status_map = info.get("status_map")
    status = info.get("status")
    contact_ip = info.get("link")
    auth_key = info.get("authkey")

    status.set_text("Attempting connection!...")
    status_map.set_attr_map({None: "lgrey_txt"})
    link = contact_ip.get_edit_text()
    auth_key = auth_key.get_edit_text()
    params = {"pub_key": msg_crypt.public_key,
              "uuid": interface.main_obj.data["uuid"],
              "name": interface.main_obj.data["sender"],
              "port": interface.main_obj.data["port"],
              "ip": interface.main_obj.data["receiver"],
              "hashes": {}
              }
    for key, data in params.items():
        if key == "hashes": continue
        params["hashes"][key] = msg_crypt.msg_fingerprint(msg_crypt.get_byte(data),
                                                          msg_crypt.get_byte(10),
                                                          None,
                                                          special_key=auth_key,
                                                          salt=msg_crypt.public_key,)
    try:
        params["hashes"] = json.dumps(params.get("hashes"))
        resp = requests.get(f"http://{link}:8009/friend_handshake",
                    params=params,
                    timeout=5,)
        if resp.status_code == 200:
            resp = resp.json()
            resp = resp.get("data")
            name = resp.get("name")
            page_class.upd_status(f"Success! You may begin chatting with {name}.", "success")

            if resp.get("uuid") not in interface.messages.keys():
                try:
                    msg_crypt.simple_contact_signature(resp.get("uuid"), resp.get("pub_key"))
                except BnuuyCrypt.WeakEncryptor:
                    page_class.upd_status("404. This user returned a unsecure public key! cancelling..", "err")
                    return None
                except BnuuyCrypt.AlreadySavedUUID:
                    page_class.upd_status("This user is already in your contact list!", "err")
                    return None
                contact_init = {"save_new_contact": [resp.get("ip"),
                                                     resp.get("uuid"),
                                                     resp.get("name")
                                                     ]}
                os.write(ui.write_fd, json.dumps(contact_init).encode())

        elif resp.status_code == 404:
            resp = resp.json()
            reason = resp.get("reason")
            if reason is not None:
                page_class.upd_status(f"404, Unable to connect! Contacted peer's reason: {reason}", "err")
            else:
                page_class.upd_status("404, Unable to connect!", "err")
        else:
            page_class.upd_status(f"Unknown error! Response code: {resp.status_code}", "err")

    except requests.Timeout:
        page_class.upd_status("Failure! Connection timed out :(", "err")

    except requests.ConnectionError:
        page_class.upd_status("Failure! Connection refused, user is offline, or the network is unreachable.", "err")

    except requests.exceptions.JSONDecodeError:
        if interface.debug_mode:
            page_class.upd_status(f"Failure! Received broken stuff: {resp}", "err")
        else:
            page_class.upd_status("Failure! Received broken stuff", "err")

    except (requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema):
        page_class.upd_status("Invalid URL, please exclude https://, http://, or a port from the link!", "err")
