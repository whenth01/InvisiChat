import requests
import threading
import json
from . import Server

class ClientSide():
    def __init__(self):
        self.msg = threading.Thread(target=Server.message_receive, daemon=True)
        self.msg.start()

    def send_message(self):
        ip = f"http://{input("Please enter a TailScale MagicDNS: ")}8008:/message"
        sender = input("Please enter a sender name: ")
        receiver = input("Please enter a receiver name: ")
        message = input("Please enter youe message: ")

        data = {
            "receiver": receiver,
            "sender": sender,
            "content": message
            }

        resp = requests.post(ip, json=data)

        if resp.status_code == 200:
            print("Successfully sent!")

