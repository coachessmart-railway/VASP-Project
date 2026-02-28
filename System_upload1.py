import sqlite3
import time
import json
import ssl
import os
import paho.mqtt.client as mqtt
import signal
import sys

# ---------------- BASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "new_db.db")
CERTS_PATH = os.path.join(BASE_DIR, "certs")

CA_PATH = os.path.join(CERTS_PATH, "AmazonRootCA1.pem")
CERT_PATH = os.path.join(CERTS_PATH, "certificate.pem.crt")
KEY_PATH = os.path.join(CERTS_PATH, "private.pem.key")

# ---------------- MQTT CONFIG ----------------
ENDPOINT = "a1vddjuckiz90j-ats.iot.ap-south-1.amazonaws.com"
PORT = 8883
CLIENT_ID = "Raspberrypi_4A"  # unique client ID
TOPIC = "brake/pressure"

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- MQTT CALLBACKS ----------------
mqtt_connected = False

def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print("✅ Connected to AWS IoT Core", flush=True)
    else:
        mqtt_connected = False
        print("⚠️ MQTT connection failed, RC =", rc, flush=True)

def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    print("⚠️ MQTT disconnected. Will reconnect automatically...", flush=True)

def on_publish(client, userdata, mid):
    pass

# ---------------- CONNECT MQTT ----------------
def connect_mqtt():
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    client.tls_set(ca_certs=CA_PATH, certfile=CERT_PATH, keyfile=KEY_PATH, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish

    while True:
        try:
            client.connect(ENDPOINT, PORT, keepalive=60)
            client.loop_start()
            wait = 0
            while not mqtt_connected and wait < 10:
                time.sleep(1)
                wait += 1
            if mqtt_connected:
                return client
        except Exception as e:
            print("⚠️ MQTT connect error:", e, "Retrying in 5 sec...", flush=True)
            time.sleep(5)

mqtt_client = connect_mqtt()

# ---------------- UPLOAD FUNCTION ----------------
def upload_row(row):
    global mqtt_connected
    if not mqtt_connected:
        print("⚠️ MQTT not connected. Skipping upload...", flush=True)
        return False

    # Payload for AWS
    payload = {
        "device_id": row["device_id"],
        "timestamp": row["timestamp"],
        "BP_raw": row["BP_raw"],
        "FP_raw": row["FP_raw"],
        "CR_raw": row["CR_raw"],
        "BC_raw": row["BC_raw"]
    }

    # Terminal print: local DB row
    print(
        f"📥 Local DB row: device_id={row['device_id']}, "
        f"timestamp={row['timestamp']}, BP_raw={row['BP_raw']}, "
        f"FP_raw={row['FP_raw']}, CR_raw={row['CR_raw']}, BC_raw={row['BC_raw']}",
        flush=True
    )

    # Publish to AWS
    result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"📤 Sent to AWS IoT: {json.dumps(payload, ensure_ascii=False)}\n", flush=True)
        return True
    else:
        print("❌ Publish failed with RC:", result.rc, flush=True)
        return False

# ---------------- MAIN LOOP ----------------
def main_loop():
    while True:
        cursor.execute("""
            SELECT * FROM brake_pressure_log
            WHERE uploaded = 0
            ORDER BY timestamp ASC
        """)
        rows = cursor.fetchall()
        if not rows:
            time.sleep(1)
            continue

        for row in rows:
            success = upload_row(row)
            if success:
                cursor.execute("UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?", (row["id"],))
                conn.commit()
            else:
                # Retry in next iteration
                time.sleep(0.5)
                break

        time.sleep(0.5)

# ---------------- GRACEFUL SHUTDOWN ----------------
def shutdown(sig, frame):
    print("🛑 Shutting down...", flush=True)
    mqtt_client.loop_stop()
    conn.close()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# ---------------- RUN ----------------
print("🚀 AWS Uploader started...\n", flush=True)
main_loop()