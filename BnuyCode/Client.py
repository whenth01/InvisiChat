import os
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
                "content": None,
                "id": None
                }

        self.messages = []
        self.sending_post = False

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def send_message(self):
        while True:
            if self.data["receiver"] is None:
                signup_details = self.ui.signup()
                self.data["receiver"] = f"http://{signup_details.get('ip')}:8008/message"
                self.data["sender"] = signup_details.get("name")

            self.data["id"] = str(uuid.uuid4())
            self.data["content"] = self.ui.chat_menu(self.data.get("sender"))
            try:
                self.clear_terminal()
                print("Sending message...")
                self.sending_post = True
                resp = requests.post(self.data["receiver"], json=self.data)
                self.clear_terminal()
                self.sending_post = False

            except requests.ConnectionError: 
                self.sending_post = False
                pass
