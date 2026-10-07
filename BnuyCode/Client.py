import os
import time
import uuid
import requests
import threading
from . import UI
from . import Server
from . import BnuuyCrypt

class NoContactOpen(Exception): pass

class ClientSide():
    def __init__(self):
        self.ui = UI.Interface(self)
        self.msg_receiver = threading.Thread(target=Server.message_receive, 
                                            args=(self.ui,), 
                                            daemon=True)

        self.background_receiver = threading.Thread(target=Server.handshake,
                                                    args=(self.ui,),
                                                    daemon=True)

        self.ratelimit_thread = threading.Thread(target=self.ratelimit_drainer, 
                                                 daemon=True)

        self.thread_lock = threading.Lock()


        self.msg_crypt = BnuuyCrypt.MessageCrypt()
        self.rand_gen = BnuuyCrypt.RandGenerators()

        self.data = {
                "receiver": None,
                "sender": None,
                "port": 8008,
                "uuid": None,
                "id": None,
                }

        # this is used for ratelimiting
        self.contacted_ips = {}
        self.sending_post = False

    def ratelimit_drainer(self):
        while True:
            try:
                ips_to_purge = []
                self.thread_lock.acquire()

                for key in self.contacted_ips:
                    times_sent = self.contacted_ips.get(key)
                    if times_sent == 0:
                        ips_to_purge.append(key)
                        continue
                    self.contacted_ips[key] -= 1

                for ip in ips_to_purge:
                    del self.contacted_ips[ip]

                self.thread_lock.release()

            except RuntimeError:
                self.thread_lock.release()
                continue

            time.sleep(3)
            continue

    def add_to_ratelimit(self, ip):
        with self.thread_lock:

            if ip not in self.contacted_ips:
                self.contacted_ips[ip] = 1
            else:
                self.contacted_ips[ip] += 1

            if self.contacted_ips[ip] > 20: return "ratelimit_activate"
            else: return "success"


    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def startup(self):
        self.signup()
        self.ratelimit_thread.start()
        self.msg_receiver.start()
        self.ui.main_menu()

    #### SIGNUP
    def signup_collect(self, data): 
        self.data["receiver"] = data.get('ip')
        self.data["sender"] = data.get("name")
        self.data["uuid"] = str(uuid.uuid4())
        self.background_receiver.start()

    def signup(self):
        if self.data["receiver"] is None:
            self.ui.signup(callback_method=self.signup_collect)


    #### SEND MESSAGEZ
    def send_msg_callback(self, message_dict, pos):
        def find_message_pos():
            pos = len(self.ui.messages[self.ui.currently_opened_chat])-1
            while True: 
                if self.ui.messages[self.ui.currently_opened_chat][pos] != message_dict:
                    pos -= 1
                elif pos == 0:
                    return 0
                else: break
            return pos
        msg_pos = find_message_pos()
        curr_chat = self.ui.currently_opened_chat
        err = False
        try:
            self.sending_post = True
            self.ui.loop.draw_screen()

            if self.ui.currently_opened_chat != self.data["uuid"]:
                self.ui.messages[curr_chat][msg_pos][self.data["uuid"]]["failed_send"] = False
                peer = self.ui.contact_ips[self.ui.currently_opened_chat]
                message_dict = self.msg_crypt.simple_encrypt_msg(message_dict,
                                                                curr_chat,
                                                                self.data["uuid"]
                                                            )
                resp = requests.post(f"http://{peer}:{self.data['port']}/message", 
                                     json=message_dict, 
                                     timeout=5)
            else: raise NoContactOpen

            self.ui.currently_sending_msg[pos].set_attr_map({None: "default"})
            self.sending_post = False

        except (BnuuyCrypt.BadParameter,
                requests.exceptions.RequestException,
                NoContactOpen,):
            self.ui.currently_sending_msg[pos].set_attr_map({None: "err"})
            err = True
        except BnuuyCrypt.BadCallOrder:
            self.ui.currently_sending_msg[pos].set_attr_map({None: "err"})
            err = True
        except KeyError:
            self.ui.currently_sending_msg[pos].set_attr_map({None: "err"})
            err = True

        finally:
            try:
                if resp is not None and resp.status_code != 200:
                    self.ui.currently_sending_msg[pos].set_attr_map({None: "err"})
                    self.ui.messages[curr_chat][msg_pos][self.data["uuid"]]["failed_send"]=True
            except UnboundLocalError: pass
            if err:
                self.ui.messages[curr_chat][msg_pos][self.data["uuid"]]["failed_send"] = True

            self.ui.currently_sending_msg.pop(pos)
            self.sending_post = False

    def send_msg(self, button):
        self.ui.chat_menu(callback_method=self.send_msg_callback)
