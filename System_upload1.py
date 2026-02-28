import sqlite3
import time
import json
import ssl
import os
import paho.mqtt.client as mqtt
import signal
import sys

# ---------------- BASE PATH ----------------
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_PATH, "db", "new_db.db")
AWS_PATH = os.path.join(BASE_PATH, "certs")

CA_PATH = os.path.join(AWS_PATH, "AmazonRootCA1.pem")
CERT_PATH = os.path.join(AWS_PATH, "certificate.pem.crt")
KEY_PATH = os.path.join(AWS_PATH, "private.pem.key")

# ---------------- MQTT CONFIG ----------------
ENDPOINT = "a1vddjuckiz90j-ats.iot.ap-south-1.amazonaws.com"
PORT = 8883
CLIENT_ID = "Raspberrypi_4A"
TOPIC = "Raspberrypi_4A/data"

# ---------------- DATABASE ----------------
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- MQTT STATE ----------------
mqtt_connected = False
mqtt_client = None

# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print("✅ Connected to AWS IoT Core", flush=True)
    else:
        mqtt_connected = False
        print(f"⚠️ MQTT connection failed RC={rc}", flush=True)

def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    print("⚠️ MQTT disconnected. Will reconnect automatically...", flush=True)

def on_publish(client, userdata, mid):
    pass  # Optional log

# ---------------- CONNECT MQTT ----------------
def connect_mqtt():
    global mqtt_client
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    client.tls_set(ca_certs=CA_PATH, certfile=CERT_PATH, keyfile=KEY_PATH, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish

    while True:
        try:
            client.connect(ENDPOINT, PORT, keepalive=60)
            client.loop_start()
            break
        except Exception as e:
            print("⚠️ MQTT connect error:", e, "Retrying in 5 sec...", flush=True)
            time.sleep(5)
    return client

mqtt_client = connect_mqtt()

# ---------------- UPLOAD FUNCTION ----------------
def upload_row(row):
    global mqtt_connected
    while not mqtt_connected:
        print("⚠️ Waiting for MQTT connection before upload...", flush=True)
        time.sleep(1)

    payload = {
        "device_id": row["device_id"],
        "timestamp": row["timestamp"],
        "BP_raw": row["BP_raw"],
        "FP_raw": row["FP_raw"],
        "CR_raw": row["CR_raw"],
        "BC_raw": row["BC_raw"]
    }

    result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"📥 Local DB row: device_id={row['device_id']}, timestamp={row['timestamp']}, "
              f"BP_raw={row['BP_raw']}, FP_raw={row['FP_raw']}, CR_raw={row['CR_raw']}, BC_raw={row['BC_raw']}", flush=True)
        print(f"📤 Sent to AWS IoT: {json.dumps(payload)}\n", flush=True)
        return True
    else:
        print(f"❌ Publish failed RC={result.rc}. Will retry...", flush=True)
        return False

# ---------------- MAIN LOOP ----------------
def main_loop():
    while True:
        cursor.execute("SELECT * FROM brake_pressure_log WHERE uploaded=0 ORDER BY id ASC")
        rows = cursor.fetchall()

        if not rows:
            time.sleep(0.5)
            continue

        for row in rows:
            # Upload row and retry until success
            while True:
                success = upload_row(row)
                if success:
                    cursor.execute("UPDATE brake_pressure_log SET uploaded=1 WHERE id=?", (row["id"],))
                    conn.commit()
                    break
                time.sleep(1)  # retry delay

            time.sleep(0.5)  # row processing delay

# ---------------- GRACEFUL SHUTDOWN ----------------
def shutdown(sig, frame):
    print("🛑 Shutting down...", flush=True)
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    conn.close()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# ---------------- RUN ----------------
print("🚀 Uploader started...\n", flush=True)
main_loop()