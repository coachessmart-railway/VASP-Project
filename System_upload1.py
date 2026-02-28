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

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "a1vddjuckiz90j-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberrypi_4A"  # unique client ID
TOPIC     = "brake/pressure"

# ---------------- DATABASE ----------------
if not os.path.exists(DB_PATH):
    print(f"❌ Database not found: {DB_PATH}", flush=True)
    sys.exit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- FETCH DEVICE ID ----------------
"""cursor.execute("SELECT device_id FROM device_config LIMIT 1")
row = cursor.fetchone()
DEVICE_ID = row["device_id"] if row else None

if DEVICE_ID is None:
    print("⚠️ Device ID missing in device_config table. Exiting...", flush=True)
    sys.exit(1)
else:
    print(f"✅ Device ID: {DEVICE_ID}", flush=True)"""

# ---------------- MQTT FLAGS ----------------
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
    print("⚠️ MQTT disconnected. Retrying in 5 sec...", flush=True)
    time.sleep(5)
    try:
        client.reconnect()
    except Exception as e:
        print("❌ MQTT reconnect failed:", e, flush=True)

def on_publish(client, userdata, mid):
    print("📤 Data published to AWS IoT", flush=True)

# ---------------- CONNECT MQTT ----------------
def connect_mqtt():
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    client.tls_set(
        ca_certs=CA_PATH,
        certfile=CERT_PATH,
        keyfile=KEY_PATH,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish

    client.loop_start()

    while not mqtt_connected:
        try:
            client.connect(ENDPOINT, PORT, keepalive=60)
            print("Connecting to MQTT...", flush=True)
        except Exception as e:
            print("⚠️ MQTT connect error:", e, "Retrying in 5 sec...", flush=True)
        time.sleep(0.5)
    return client

mqtt_client = connect_mqtt()

# ---------------- UPLOAD FUNCTION ----------------
def upload_row(row):
    global mqtt_connected
    while not mqtt_connected:
        print("⚠️ Waiting for MQTT connection...", flush=True)
        time.sleep(0.5)

    payload = {
        "device_id": DEVICE_ID,
        "timestamp": row["timestamp"],
        "bp_raw": row["BP_raw"],
        "fp_raw": row["FP_raw"],
        "cr_raw": row["CR_raw"],
        "bc_raw": row["BC_raw"]
    }

    result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(
            f"📤 Uploaded: device_id={DEVICE_ID}, BP={row['BP_raw']}, FP={row['FP_raw']}, "
            f"CR={row['CR_raw']}, BC={row['BC_raw']}, timestamp={row['timestamp']}", flush=True
        )
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
            print("No new data to upload. Waiting...", flush=True)
            time.sleep(0.5)
            continue

        for row in rows:
            success = upload_row(row)
            if success:
                cursor.execute(
                    "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                    (row["id"],)
                )
                conn.commit()
                print(f"✅ Marked uploaded | id={row['id']}\n", flush=True)
            else:
                print("Retrying upload later...", flush=True)
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
print("🚀 Uploader started...\n", flush=True)
main_loop()