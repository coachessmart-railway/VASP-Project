import sqlite3
import time
import json
import ssl
import os
import signal
import sys
import paho.mqtt.client as mqtt

# ---------------- BASE PATH ----------------
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_PATH, "db", "new_db.db")
AWS_PATH = os.path.join(BASE_PATH, "certs")

CA_PATH   = os.path.join(AWS_PATH, "AmazonRootCA1.pem")
CERT_PATH = os.path.join(AWS_PATH, "certificate.pem.crt")
KEY_PATH  = os.path.join(AWS_PATH, "private.pem.key")

# ---------------- CHECK FILES ----------------
for f in [DB_PATH, CA_PATH, CERT_PATH, KEY_PATH]:
    if not os.path.exists(f):
        print(f"❌ Missing file: {f}", flush=True)
        sys.exit(1)

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "a1vddjuckiz90j-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberrypi_4A"
TOPIC     = "brake/pressure"

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- MQTT FLAGS ----------------
mqtt_client = None
mqtt_connected = False

# ---------------- MQTT CALLBACKS ----------------
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
    print("⚠️ MQTT disconnected. Will reconnect automatically.", flush=True)

def on_publish(client, userdata, mid):
    print("📤 Data published successfully", flush=True)

# ---------------- CONNECT MQTT ----------------
def connect_mqtt():
    global mqtt_client, mqtt_connected
    mqtt_client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    mqtt_client.tls_set(
        ca_certs=CA_PATH,
        certfile=CERT_PATH,
        keyfile=KEY_PATH,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_publish = on_publish

    mqtt_client.loop_start()  # background network loop

    while not mqtt_connected:
        try:
            mqtt_client.connect(ENDPOINT, PORT, keepalive=60)
        except Exception as e:
            print("⚠️ MQTT connect error:", e, "Retrying in 5 sec...", flush=True)
            time.sleep(5)
        time.sleep(1)

connect_mqtt()

# ---------------- UPLOAD FUNCTION ----------------
def upload_row(row):
    global mqtt_connected
    while not mqtt_connected:
        print("⚠️ Waiting for MQTT connection before upload...", flush=True)
        time.sleep(2)

    payload = {
        "device_id": row["device_id"],
        "BP_raw": row["BP_raw"],
        "FP_raw": row["FP_raw"],
        "CR_raw": row["CR_raw"],
        "BC_raw": row["BC_raw"],
        "timestamp": row["timestamp"]
    }

    result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"📤 Uploaded: {json.dumps(payload, indent=2)}", flush=True)
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
            time.sleep(5)
            continue

        for row in rows:
            if upload_row(row):
                cursor.execute(
                    "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                    (row["id"],)
                )
                conn.commit()
            else:
                print("⚠️ Upload failed. Will retry in next loop.", flush=True)
                time.sleep(5)  # wait before retrying
            time.sleep(1)

# ---------------- GRACEFUL SHUTDOWN ----------------
def shutdown(sig, frame):
    print("🛑 Shutting down...", flush=True)
    mqtt_client.loop_stop()
    conn.close()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# ---------------- RUN ----------------
print("🚀 Uploader started...\n", flush=True)
main_loop()