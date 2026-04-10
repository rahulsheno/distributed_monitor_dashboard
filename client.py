import socket
import json
import time
import sys
from metrics import collect_metrics
import config

def get_network_ip():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)

        if ip.startswith("127."):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
            finally:
                s.close()
    except:
        ip = "127.0.0.1"

    return ip

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

base_name = socket.gethostname()

if len(sys.argv) > 1:
    node_id = f"{base_name}_{sys.argv[1]}"
else:
    node_id = base_name

while True:
    metrics = collect_metrics()

    metrics["node_id"] = node_id
    metrics["system_ip"] = get_network_ip()

    message = json.dumps(metrics)

    sock.sendto(
        message.encode(),
        (config.SERVER_IP, config.SERVER_PORT)
    )

    time.sleep(config.SEND_INTERVAL)