import os
import time
import uuid
import requests
import threading
from . import Server
from . import UI

class ClientSide():
    def __init__(self):
        self.ui = UI.Interface(self)
        self.msg_receiver = threading.Thread(target=Server.message_receive, 
                                    args=(self.ui,), 
                                    daemon=True)

        self.background_receiver = threading.Thread(target=Server.handshake,
                                    args=(self.ui,),
                                    daemon=True)

        self.data = {
                "receiver": None,
                "sender": None,
                "port": 8008,
                "uuid": None,
                "id": None,
                }

        self.messages = []
        self.sending_post = False

        self.signup()
        self.msg_receiver.start()
        self.ui.main_menu()

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    #### SIGNUP
    def signup_collect(self, data): 
        self.data["receiver"] = f"http://{data.get('ip')}:8008/message"
        self.data["sender"] = data.get("name")
        self.data["uuid"] = str(uuid.uuid4())
        self.background_receiver.start()

    def signup(self):
        if self.data["receiver"] is None:
            self.ui.signup(callback_method=self.signup_collect)


    #### SEND MESSAGEZ
    def send_msg_callback(self, message_dict, pos):
        try:
            self.sending_post = True
            self.ui.loop.draw_screen()
            resp = requests.post(self.data["receiver"], json=message_dict, timeout=5)
            self.ui.currently_sending_msg[pos].set_attr_map({None: "default"})
            self.sending_post = False

        except requests.ConnectionError: 
            self.ui.currently_sending_msg[pos].set_attr_map({None: "err"})
        except requests.Timeout:
            self.ui.currently_sending_msg[pos].set_attr_map({None: "err"})

        finally: 
            self.ui.currently_sending_msg.pop(pos)
            self.sending_post = False

    def send_msg(self, button):
        self.ui.chat_menu(callback_method=self.send_msg_callback)
