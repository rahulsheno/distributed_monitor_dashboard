# Distributed Node Monitor

> Real-time infrastructure monitoring system built with Python, Flask, Socket.IO, ECharts, and SQLite.

---

## Overview

Distributed Node Monitor collects CPU, memory, and disk usage from multiple machines and streams them live to a central web dashboard. Each monitored machine runs a lightweight client that sends UDP packets to a central server, which persists the data and pushes it to connected browsers in real time.

**Data flow:**

```
metrics.py → client.py → [UDP] → server.py → database.py → dashboard.py → Browser
```

---

## Architecture

| Layer        | Component                  | Responsibility                                              |
|--------------|----------------------------|-------------------------------------------------------------|
| Collection   | `client.py` + `metrics.py` | Gather system stats; transmit via UDP every N seconds       |
| Ingestion    | `server.py`                | Receive UDP packets; persist readings to SQLite             |
| Storage      | `database.py` + `metrics.db` | Store historical metrics; expose query helpers            |
| Presentation | `dashboard.py`             | Serve the web UI; push live updates via Socket.IO           |

---

## File Reference

### `config.py`

Central configuration. Edit this file to change deployment settings without touching any other source file.

| Constant        | Default     | Description                                                           |
|-----------------|-------------|-----------------------------------------------------------------------|
| `SERVER_IP`     | `127.0.0.1` | IP address the client sends UDP packets to                            |
| `SERVER_PORT`   | `9999`      | UDP port the server listens on                                        |
| `SEND_INTERVAL` | `5`         | Seconds between metric transmissions from a client node               |
| `NODE_TIMEOUT`  | `5`         | Seconds of silence before a node is hidden from the dashboard         |

---

### `metrics.py`

Handles metric collection on the client machine. Supports two modes:

- **Real mode** — reads live CPU, memory, and disk values via `psutil`.
- **Force mode** — injects randomised high-load values to simulate a stressed node. Toggle with `Ctrl+Q` at runtime.

| Function            | Purpose                                                          |
|---------------------|------------------------------------------------------------------|
| `get_real_metrics()`  | Returns live `psutil` readings plus hostname, IP, and timestamp |
| `get_force_metrics()` | Returns randomised high-load values (CPU 82–96%, MEM 85–97%, Disk 88–98%) |
| `collect_metrics()`   | Entry point — delegates to whichever mode is active             |
| `toggle_mode()`       | Called by the `Ctrl+Q` hotkey to flip the `force_mode` flag     |

---

### `client.py`

Runs on each monitored node. Creates a UDP socket, resolves the machine's network-reachable IP, and sends a JSON payload on every `SEND_INTERVAL` tick.

**Node naming** — the hostname is used by default. Pass a suffix as a CLI argument to run multiple simulated nodes on the same host:

```bash
python client.py        # node id = hostname
python client.py A      # node id = hostname_A
python client.py B      # node id = hostname_B
```

**Payload shape:**

```json
{
  "node_id": "my-host_A",
  "system_ip": "192.168.1.10",
  "cpu": 42.3,
  "memory": 67.1,
  "disk": 55.0,
  "timestamp": 1712345678.123
}
```

---

### `server.py`

UDP listener and ingestion service. Binds on all interfaces (`0.0.0.0`) on `SERVER_PORT`. For every incoming datagram it:

1. Decodes the JSON payload.
2. Calls `insert_metric()` to persist the reading.
3. Emits a Socket.IO `update` event.

Also spins up a minimal Flask + Socket.IO app on port `9998`. The primary user-facing interface is the dashboard on port `5000`.

---

### `database.py`

SQLite data access layer. Creates the `metrics` table on first run if it does not exist.

**Schema:**

```sql
CREATE TABLE metrics (
    node       TEXT,
    ip         TEXT,
    cpu        REAL,
    memory     REAL,
    disk       REAL,
    timestamp  REAL
);
```

**Exposed helpers:**

| Function               | Behaviour                                                                                     |
|------------------------|-----------------------------------------------------------------------------------------------|
| `insert_metric(...)`   | Inserts a single reading and commits.                                                         |
| `get_metrics()`        | Returns the latest reading per node, filtered to those seen within `NODE_TIMEOUT` seconds.    |
| `get_latest_records()` | Returns the 10 most recent rows across all nodes (used for the aggregate history chart).      |

---

### `dashboard.py`

Flask web application and Socket.IO server. Serves the monitoring UI on port `5000`.

#### Authentication

Session-based login. Two accounts are hard-coded in the `users` dict:

| Username | Password   | Role  |
|----------|------------|-------|
| `admin`  | `admin123` | admin |
| `user`   | `user123`  | user  |

> ⚠️ Credentials are plain text in source. Replace with hashed passwords before any networked deployment.

#### Routes

| Route               | Method     | Description                                                        |
|---------------------|------------|--------------------------------------------------------------------|
| `/login`            | GET / POST | Renders login form; validates credentials and sets session cookie. |
| `/logout`           | GET        | Clears the session and redirects to `/login`.                      |
| `/`                 | GET        | Main dashboard (login required). Streams all-node aggregate data.  |
| `/node_page/<node>` | GET        | Per-node detail view with 10-point history chart and data table.   |

#### Real-Time Updates

A background task (`push_updates`) runs every **3 seconds** and emits two Socket.IO events:

- **`update`** — broadcast to all clients: current per-node readings plus averaged CPU/memory/disk history arrays for the aggregate chart.
- **`node_update`** — per-node event with the last 10 readings, rolling averages, and timestamps; consumed by `/node_page/<node>`.

#### Alert Thresholds

| Metric | Warning | Critical | Visual                       |
|--------|---------|----------|------------------------------|
| CPU    | ≥ 70%   | ≥ 90%    | Orange / Red text + banner   |
| Memory | ≥ 75%   | ≥ 90%    | Orange / Red text + banner   |
| Disk   | ≥ 80%   | ≥ 95%    | Orange / Red text + banner   |

---

## Setup & Running

### 1. Install dependencies

```bash
pip install flask flask-socketio psutil keyboard
```

### 2. Start the ingestion server

```bash
python server.py
```

Listens on UDP `:9999` and HTTP `:9998`.

### 3. Start the dashboard

```bash
python dashboard.py
```

Web UI available at **http://localhost:5000**. Log in with `admin` / `admin123`.

### 4. Start one or more client nodes

```bash
# On each machine you want to monitor:
python client.py

# To simulate multiple nodes on the same machine:
python client.py A
python client.py B
```

### 5. Simulate high load (optional)

With a client running in the foreground, press **`Ctrl+Q`** to toggle force mode. The terminal prints `FORCE MODE: ON` and metrics immediately spike into warning/critical ranges on the dashboard. Press `Ctrl+Q` again to return to real values.

---

## Known Limitations & Security Notes

- **Plain-text credentials** — `admin123` / `user123` are hardcoded. Use hashed passwords and a real user store before any production use.
- **Hardcoded secret key** — `app.secret_key = "secret123"`. Replace with a securely generated random value.
- **UDP is fire-and-forget** — packet loss is not detected or retried.
- **SQLite threading** — the connection is shared across threads without a pool; may cause issues under high concurrency.
- **`keyboard` library** — requires root/admin privileges on some Linux systems.
- **Short `NODE_TIMEOUT`** — 5 s default means nodes on slow or lossy networks may flicker offline. Increase in `config.py` if needed.

---

## Quick Reference

| What                | Command / URL              | Notes                          |
|---------------------|----------------------------|--------------------------------|
| Ingestion server    | `python server.py`         | UDP `:9999`, HTTP `:9998`      |
| Dashboard           | `python dashboard.py`      | http://localhost:5000          |
| Client node         | `python client.py [suffix]`| Run on each monitored host     |
| Toggle stress mode  | `Ctrl+Q` in client terminal| Simulates critical load        |
| Admin login         | `admin` / `admin123`       | Change before production use!  |
