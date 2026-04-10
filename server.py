import socket
import json
import config
from database import insert_metric
from flask_socketio import SocketIO
from flask import Flask

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

HOST = "0.0.0.0"
PORT = config.SERVER_PORT

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))

def receive_data():
    while True:
        data, addr = sock.recvfrom(4096)
        metrics = json.loads(data.decode())

        node = metrics["node_id"]
        ip = metrics.get("system_ip", addr[0])
        cpu = metrics["cpu"]
        memory = metrics["memory"]
        disk = metrics["disk"]
        ts = metrics["timestamp"]

        insert_metric(node, ip, cpu, memory, disk, ts)

        socketio.emit("update", {
            "node": node,
            "ip": ip,
            "cpu": cpu,
            "memory": memory,
            "disk": disk
        })

if __name__ == "__main__":
    socketio.start_background_task(receive_data)
    socketio.run(app, host="0.0.0.0", port=9998)