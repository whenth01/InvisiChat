import requests
import threading
import json
from . import Server

class ClientSide():
    def __init__(self):
        self.msg = threading.Thread(target=Server.message_receive, daemon=True)
        self.msg.start()
        self.data = {
                "receiver": None,
                "sender": None,
                "content": None,
                }

    def send_message(self):
        while True:
            if self.data["receiver"] is None:
                ip = f"http://{input("Please enter a TailScale MagicDNS: ")}:8008/message"
                sender = input("Please enter a sender name: ")
                self.data["receiver"] = ip 
                self.data["sender"] = sender

            msg = input("Enter what youd like to send: ")
            self.data["content"] = msg

            resp = requests.post(ip, json=data)

            if resp.status_code == 200:
                print(f"Successfully sent!")

