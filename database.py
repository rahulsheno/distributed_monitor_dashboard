import sqlite3
import time
import config

conn = sqlite3.connect("metrics.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS metrics(
    node TEXT,
    ip TEXT,
    cpu REAL,
    memory REAL,
    disk REAL,
    timestamp REAL
)
""")

conn.commit()

def insert_metric(node, ip, cpu, memory, disk, ts):
    cursor.execute(
        "INSERT INTO metrics VALUES (?,?,?,?,?,?)",
        (node, ip, cpu, memory, disk, ts)
    )
    conn.commit()

def get_metrics():
    now = time.time()

    cursor.execute("""
    SELECT m.node, m.ip, m.cpu, m.memory, m.disk, m.timestamp
    FROM metrics m
    JOIN (
        SELECT node, MAX(timestamp) AS latest
        FROM metrics
        GROUP BY node
    ) latest
    ON m.node = latest.node AND m.timestamp = latest.latest
    """)

    rows = cursor.fetchall()

    return [
        {"node":r[0],"ip":r[1],"cpu":r[2],"memory":r[3],"disk":r[4]}
        for r in rows if now - r[5] <= config.NODE_TIMEOUT
    ]

def get_latest_records():
    cursor.execute("""
    SELECT cpu, memory, disk, timestamp
    FROM metrics
    ORDER BY timestamp DESC
    LIMIT 10
    """)
    return cursor.fetchall()