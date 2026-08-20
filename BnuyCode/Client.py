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
                }

        self.messages = []
        self.sending_post = False

    def send_message(self):
        while True:
            if self.data["receiver"] is None:
                signup_details = self.ui.signup()
                self.data["receiver"] = f"http://{signup_details.get('ip')}:8008/message"
                self.data["sender"] = signup_details.get("name")

            self.data["content"] = self.ui.chat_menu(self.data.get("sender"))
            try:
                self.sending_post = True
                resp = requests.post(self.data["receiver"], json=self.data)
                self.sending_post = False
                self.messages.append(dict(self.data))

            except requests.ConnectionError: 
                self.sending_post = False
                pass
