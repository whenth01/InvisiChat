import os
import json
import hmac
import logging
import requests
import flask.cli
from . import BnuuyCrypt
from time import sleep as wait
from flask import Flask, request, jsonify

# Messaging port: 8008 
## hehe funy number
# Handshake port: 8009

"""IMPORTANT NOTE 
1: Before full release, MOVE THE DAMN PUB KEY EXCHANGE TO BEFORE ALL DATA IS SHARED

Plan:
    1: Sender sends pub key + hash 
    2: Receiver verifies hash against it's authkeys
      2.1: If it's good, it saves the pub key to a tmp dict
      2.1.1: Then it returns encrypted handshake + unencrypted pub key
    3: Sender takes pub key, saves to same tmp dict, then decrypts..
    3.1: Then sends over it's own encrypted handshake data
I hope this doesnt mean i rework everything QwQ...

    completed on 22 sept (commit hash c6d1346)

2: The open internet is a hellscape, and the current servers have no whitelist/rate limit

Plan for rate limit:
    1: If the same IP sends too POST/GET requests in a row, auto-refuse
    2: If after the minute the same IP continues doing that, block them and warn the user
    (completed, I changed the design so the more the limit is abused
     the worse it is for the attacker)

Plan for white list:
    1: If the IP sent isnt in the user made whitelist, auto refuse
    (this'll pair with the rate linit plan)

Plan for anti-replay
    1: Make a dict specifically to store message orderes
    2: The dict stores message ids ordered by when they were appended
    3: If a message ID reappears, reject it
    (completed, step 1 was unnecessary, step 3 was the only place i needed to write code)
    (so yay:3, sep 29 completed)
"""

def verify_url(url, port):
    try:
        resp = requests.post(f"http://{url}:{port}/message", 
                             json="check_alive", 
                             timeout=4,
                             allow_redirects=False,)
        resp_dict = resp.json()
        uuid = resp_dict.get("uuid")
        return (resp.status_code == 200, uuid)
    except requests.exceptions.RequestException:
        return False

def get_request(link, params, timeout=5):
    resp = requests.get(f"http://{link}:8009/friend_handshake",
                 params={"parameters": json.dumps(params)},
                 timeout=timeout,)
    return resp

def tmp_hasher(data, auth_key, msg_crypt, iv=10):
    tmp = str(msg_crypt.msg_fingerprint(msg_crypt.get_byte(
                                                    json.dumps(data)
                                                    ),
                                                    msg_crypt.get_byte(iv),
                                                    None,
                                                    special_key=auth_key,
                                                    salt=msg_crypt.public_key,))
    return tmp

def message_receive(ui):
    cached_msg = []

    def send_cached_msgs(cached_msg, interface):
        os.write(interface.write_fd, json.dumps(cached_msg).encode())

    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    app = Flask(__name__)

    @app.route("/message", methods=["POST"])
    def get_msg():
        data = request.get_json(silent=True, force=True)

        status = ui.main_obj.add_to_ratelimit(request.remote_addr)
        if status != "success":
            return jsonify({"status": "failure",
                            "reason": "ratelimit",}), 404

        if data == "check_alive": return jsonify({"status": "success",
                                                  "uuid": ui.main_obj.data["uuid"]}), 200
        if data is None or not isinstance(data, dict):
            return jsonify({"status": "unknown POST request"}), 404
        # I tried using all caps since i heard it means 'do not modify'
        # idk if ill keep using it though
        EXPECTED_KEYS = {"ciphertext", "iv", "uuid", "uuid_hash", "ct_hash",}
        EXPECTED_LEN = len(EXPECTED_KEYS)

        for key in data.keys():
            if key not in EXPECTED_KEYS or not isinstance(data[key], str):
                return jsonify({"status": "failure",
                                "reason": "unknown POST request"}), 404
        if len(data.keys()) != EXPECTED_LEN:
            return jsonify({"status": "failure",
                            "reason": "unknown POST request"}), 404

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
        status = ui.main_obj.add_to_ratelimit(request.remote_addr)
        if status != "success":
            return jsonify({"status": "failure",
                            "reason": "ratelimit",}), 404


        try: param_dict = json.loads(request.args.get("parameters"))
        except (TypeError, json.JSONDecodeError, ValueError):
            return jsonify({"status": "failure",
                            "reason": "Unknown request"}), 404

        try: 
            pub_key = int(param_dict.get("pub_key"))

            if "enc_id" not in param_dict.keys(): 
                decrypt_and_save = False
            else:
                decrypt_and_save = True
        except (ValueError, TypeError, AttributeError, OverflowError):
            return jsonify({"status": "failure",
                            "reason": "Received an invalid or non int public key"}), 404
        try:
            hash = param_dict.pop("hash")
        except KeyError:
            return jsonify({"status": "failure",
                            "reason": "Didnt receive a fingerprint, unable to guarantee no tampering occurred."}), 404


        # note: im not sure how this even works
        pos_in_keylist = 0
        found_hash = False
        def compare_digests(received, auth_key, pub_key, hash):
            expected_digest = msg_crypt.msg_fingerprint(
                    msg_crypt.get_byte(json.dumps(received)),
                    msg_crypt.get_byte(10),
                    None,
                    special_key=auth_key,
                    salt=msg_crypt.get_byte(pub_key))
            return hmac.compare_digest(expected_digest, hash)

        if decrypt_and_save:
            try:
                if compare_digests(param_dict,
                                   ui.authkeys_in_use[pub_key],
                                   pub_key,
                                   hash,):
                    data = msg_crypt.msg_decrypt(param_dict["enc_id"], pub_key)

                    if data.get("uuid") in ui.contact_info and ui.contact_info[data.get("uuid")]["block_status"]:
                            raise ValueError

                    skip = False
                    if data.get("uuid") in ui.messages.keys():
                        try:
                            new_pubkey = msg_crypt.shared_keys[data.get("uuid")]["public_key"]
                            if new_pubkey != pub_key: skip = True
                        except (KeyError, TypeError): pass

                    if data.get("uuid") not in ui.messages.keys() or skip:
                        if len(data) < 4: raise AttributeError
                        if data.get("uuid") == ui.main_obj.data["uuid"]: raise AttributeError
                        for key, info in data.items():
                            if not isinstance(info, str) or key not in ("ip","port","name","uuid"):
                                raise AttributeError
                        status, resp_uuid = verify_url(data.get("ip"), data.get("port"))
                        if not status or resp_uuid is None or resp_uuid != data.get("uuid"):
                            raise AttributeError

                        msg_crypt.simple_contact_signature(data.get("uuid"), pub_key, 
                                                           overwrite=pub_key,
                                                           force_save=skip)
                        contact_init = {"save_new_contact": [data.get("ip"),
                                                             data.get("uuid"),
                                                             data.get("name")
                                                            ]}
                        waited = 0
                        while ui.write_fd is None: 
                            if waited > 15:
                                return jsonify({"status": "failure",
                                                "reason": "Peer's device stopped responding!"}), 404
                            waited += 1
                            wait(0.2)
                        if waited < 15:
                            os.write(ui.write_fd, json.dumps(contact_init).encode())

                        if pub_key in ui.authkeys_in_use: del ui.authkeys_in_use[pub_key]

                    return jsonify({"status": "success"}), 200
                else:
                    return jsonify({"status": "failure",
                                    "reason": "404. Data was modified in transit!"}), 404
            except (BnuuyCrypt.BadParameter, 
                    BnuuyCrypt.BadCallOrder,
                    BnuuyCrypt.AlreadySavedUUID,
                    AttributeError,
                    OverflowError,
                    RecursionError,
                    ValueError,
                    TypeError,
                    KeyError):
                try: 
                    if pub_key in msg_crypt.shared_keys: 
                        del msg_crypt.shared_keys[pub_key]
                except UnboundLocalError: pass
                return jsonify({"status": "failure",
                                "reason": f"Something went wrong during ID decryption!"}), 404


        try:

            for auth_key in ui.key_list:
                auth_key = auth_key.get_text()[0]
                if compare_digests(param_dict, auth_key, pub_key, hash):
                    found_hash = True
                    ui.authkeys_in_use[pub_key] = auth_key
                    ui.key_list.pop(pos_in_keylist)
                    break
                else:
                    pos_in_keylist += 1

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

        data = {
                "uuid": str(ui.main_obj.data["uuid"]),
                "name": str(ui.main_obj.data["sender"]),
                "port": str(ui.main_obj.data["port"]),
                "ip": str(ui.main_obj.data["receiver"]),
            }
        try:
            msg_crypt.simple_contact_signature(pub_key, pub_key, force_save=True)
        except (BnuuyCrypt.WeakEncryptor, BnuuyCrypt.BadParameter):
            if pub_key in msg_crypt.shared_keys: del msg_crypt.shared_keys[pub_key]
            return jsonify({"status": "failure",
                            "reason": "Received public_key had an issue!"}), 404
        encrypted_data = {
                "enc_id": msg_crypt.simple_encrypt_msg(data, pub_key, data["uuid"])
                }
        encrypted_data["pub_key"] = msg_crypt.public_key

        return jsonify({"status": "success", "data": encrypted_data}), 200
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

    status.set_text("Attempting to establish secure connection!...")
    status_map.set_attr_map({None: "lgrey_txt"})
    link = contact_ip.get_edit_text()
    auth_key = auth_key.get_edit_text()
    pubkey_handshake = {"pub_key": str(msg_crypt.public_key)}
    identity_handshake = {"uuid": str(interface.main_obj.data["uuid"]),
              "name": str(interface.main_obj.data["sender"]),
              "port": str(interface.main_obj.data["port"]),
              "ip": str(interface.main_obj.data["receiver"]),
              }
    pubkey_handshake["hash"] = tmp_hasher(pubkey_handshake, auth_key, msg_crypt)
    public_key = None

    try:
        resp = get_request(link, pubkey_handshake)
        if resp.status_code == 200:
            status.set_text("Established secure connection, sharing/receiving data...")
            resp = resp.json()
            resp = resp.get("data")
            public_key = resp.get("pub_key")
            msg_crypt.simple_contact_signature(public_key, public_key, force_save=True)
            resp_id = msg_crypt.msg_decrypt(resp.get("enc_id"), public_key)
            encrypted_id = msg_crypt.simple_encrypt_msg(identity_handshake, 
                                                        public_key,
                                                        identity_handshake["uuid"]
                                                        )
            params = {"enc_id": encrypted_id,
                      "pub_key": msg_crypt.public_key}

            params["hash"] = tmp_hasher(params, ui.authkeys_in_use[public_key], msg_crypt)
            id_resp = get_request(link, params)
            if id_resp.status_code == 200:
                name = resp_id.get("name")
                uuid = resp_id.get("uuid")

            elif id_resp.status_code == 404:
                id_resp = id_resp.json()
                page_class.upd_status(f"404 ERROR: Peer's reason: {id_resp.get('reason')}", "err")
                del msg_crypt.shared_keys[public_key]
                return None
            else:
                page_class.upd_status(f"Unknown ERROR: {id_resp.status_code}", "err")
                del msg_crypt.shared_keys[public_key]
                return None

            if isinstance(uuid, str) and uuid not in interface.messages.keys():
                if len(resp_id) < 4:
                    raise ValueError
                status, resp_uuid = verify_url(resp_id.get("ip"), resp_id.get("port"))
                if not status or resp_uuid is None or resp_uuid != uuid:
                    raise ValueError
                for key, content in resp_id.items():
                    if content == interface.main_obj.data["uuid"]: raise ValueError
                    if not isinstance(content, str) or key not in ("name", "ip", "uuid", "port"):
                        raise ValueError
                try:
                    msg_crypt.simple_contact_signature(uuid, public_key, overwrite=public_key)
                except BnuuyCrypt.AlreadySavedUUID:
                    page_class.upd_status("This user is already in your contact list!", "err")
                    return None

                contact_init = {"save_new_contact": [resp_id.get("ip"),
                                                     resp_id.get("uuid"),
                                                     resp_id.get("name")
                                                     ]}
                page_class.upd_status(f"Success! You may begin chatting with {name}.",
                                      "success")
                os.write(interface.write_fd, json.dumps(contact_init).encode())
            elif not isinstance(uuid, str):
                page_class.upd_status("The peer's client gave an invalid piece of data!","err")
                del msg_crypt.shared_keys[public_key]
            else:
                del msg_crypt.shared_keys[public_key]
                page_class.upd_status("This person is already in your contact list, so nothing was saved!", "err")

        elif resp.status_code == 404:
            resp = resp.json()
            reason = resp.get("reason")
            if reason is not None:
                page_class.upd_status(f"404, Unable to connect! Contacted peer's reason: {reason}", "err")
            else:
                page_class.upd_status("404, Unable to connect!", "err")
        else:
            page_class.upd_status(f"Unknown error! Response code: {resp.status_code}", "err")

        # exception paradise
    except requests.Timeout:
        page_class.upd_status("Failure! Connection timed out :(", "err")

    except requests.ConnectionError:
        page_class.upd_status("Failure! Connection refused, user is offline, or the network is unreachable.", "err")

    except requests.exceptions.TooManyRedirects:
        page_class.upd_status("Failure! The contact's DNS had too many redirects.", "err")

    except requests.exceptions.JSONDecodeError:
        if interface.debug_mode:
            page_class.upd_status(f"Failure! Received broken stuff: {resp}", "err")
        else:
            page_class.upd_status("Failure! Received broken stuff", "err")

    except (requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema):
        page_class.upd_status("Invalid URL, please exclude https://, http://, or a port from the link!", "err")

    except requests.exceptions.ChunkedEncodingError:
        page_class.upd_status("Encoding error occurred! Please try again.", "err")

    except (BnuuyCrypt.BadParameter, AttributeError) as e:
        page_class.upd_status(f"An error occurred! Error: {e}", "err")

    except BnuuyCrypt.AlreadySavedUUID:
        page_class.upd_status("This user is already in your contact list!", "err")

    except BnuuyCrypt.WeakEncryptor:
        if public_key is not None and public_key in msg_crypt.shared_keys:
            del msg_crypt.shared_keys[public_key]
        page_class.upd_status("The contacted peer's public key is unsecure, meaning they likely have a modified client. Aborting!..", "err")

    except ValueError:
        page_class.upd_status("FAIL: The peer gave invalid information!","err")

    except requests.exceptions.RequestException:
        page_class.upd_status("An error occurred during the handshake process!","err")

    finally:
        try: del msg_crypt.shared_keys[public_key]
        except (UnboundLocalError, KeyError, BnuuyCrypt.BadParameter, TypeError): pass
