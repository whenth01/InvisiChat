import requests
import threading
import json
from . import FlaskTest

msg = threading.Thread(target=FlaskTest.message_receive, daemon=True)
msg.start()

def req_test():
    ip = f"http://{input("Please enter a TailScale MagicDNS: ")}:8008/message"
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

req_test()
