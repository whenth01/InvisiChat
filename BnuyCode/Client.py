import os
import uuid
import requests
import threading
from . import GoBack
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
                "content": None,
                "uuid": None,
                "id": None,
                }

        self.messages = []
        self.sending_post = False

        self.signup()
        self.ui.main_menu()

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def signup(self):
        if self.data["receiver"] is None:
            signup_details = self.ui.signup()
            self.data["receiver"] = f"http://{signup_details.get('ip')}:8008/message"
            self.data["sender"] = signup_details.get("name")
            self.data["uuid"] = str(uuid.uuid4())

    def send_msg(self, button):
        while True:
            self.data["id"] = str(uuid.uuid4())

            self.data["content"] = self.ui.chat_menu(self.data.get("sender"))
            if self.data["content"] == self.data["id"]: return

            try:
                self.clear_terminal()
                print("Sending message...")
                self.sending_post = True
                resp = requests.post(self.data["receiver"], json=self.data, timeout=5)
                self.clear_terminal()
                self.sending_post = False

            except requests.ConnectionError: 
                self.sending_post = False
                pass
            except requests.Timeout:
                self.sending_post = False
                self.clear_terminal()
                pass
