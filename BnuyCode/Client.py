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

        self.msg_receiver.start()
        self.data = {
                "receiver": None,
                "sender": None,
                "uuid": None,
                "id": None,
                }

        self.messages = []
        self.sending_post = False

        self.signup()
        self.ui.main_menu()

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    #### SIGNUP
    def signup_collect(self, data): 
        self.data["receiver"] = f"http://{data.get('ip')}:8008/message"
        self.data["sender"] = data.get("name")
        self.data["uuid"] = str(uuid.uuid4())

    def signup(self):
        if self.data["receiver"] is None:
            self.ui.signup(callback_method=self.signup_collect)


    #### SEND MESSAGEZ
    def send_msg_callback(self, message_dict):
        try:
            self.sending_post = True
            resp = requests.post(self.data["receiver"], json=message_dict, timeout=5)
            self.sending_post = False

        except requests.ConnectionError: 
            pass
        except requests.Timeout:
            self.clear_terminal()
            pass
        finally: self.sending_post = False

    def send_msg(self, button):
        self.ui.chat_menu(callback_method=self.send_msg_callback)
