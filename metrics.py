import time
import socket
import psutil
import keyboard
import random

force_mode = False

def toggle_mode():
    global force_mode
    force_mode = not force_mode
    print("FORCE MODE:", "ON" if force_mode else "OFF")

keyboard.add_hotkey("ctrl+q", toggle_mode)

def get_system_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def get_real_metrics():
    return {
        "node_id": socket.gethostname(),
        "system_ip": get_system_ip(),
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent,
        "timestamp": time.time()
    }

def get_force_metrics():
    
    cpu = round(random.uniform(82.0, 96.5), 1)
    memory = round(random.uniform(85.0, 97.5), 1)
    disk = round(random.uniform(88.0, 98.8), 1)

    return {
        "cpu": cpu,
        "memory": memory,
        "disk": disk
    }

def collect_metrics():

    if force_mode:
        data = get_force_metrics()
        data["timestamp"] = time.time()
        return data

    return get_real_metrics()