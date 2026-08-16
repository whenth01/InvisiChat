import requests
import threading
from . import ServerManagement

def req_test():
    server_thread = threading.Thread(target=ServerManagement.start_server, daemon=True)
    server_thread.start()
    ip = f"http://{input("Please enter a TailScale MagicDNS: ")}:8008"

    resp = requests.get(ip)

    print(resp)
