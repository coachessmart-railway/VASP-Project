import os
import time
import sqlite3
import json
import ssl
import paho.mqtt.client as mqtt

# ---------------- BASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "new_db.db")

# ---------------- CERT PATHS ----------------
CA_PATH = os.path.join(BASE_DIR, "certs", "AmazonRootCA1.pem")
CERT_PATH = os.path.join(BASE_DIR, "certs", "certificate.pem.crt")
KEY_PATH = os.path.join(BASE_DIR, "certs", "private.pem.key")

# ---------------- MQTT CONFIG ----------------
MQTT_ENDPOINT = "a1vddjuckiz90j-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "Raspberrypi_4A"
TOPIC = f"{CLIENT_ID}/data"  # Topic matches Thing name for AWS Test client

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- MQTT CONNECTION FLAG ----------------
mqtt_connected = False

# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print("✅ Connected to AWS IoT Core")
    else:
        mqtt_connected = False
        print(f"❌ MQTT connection failed with code {rc}")

def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    print("⚠️ MQTT disconnected. Will reconnect automatically...")

# ---------------- MQTT CLIENT ----------------
mqtt_client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
mqtt_client.tls_set(ca_certs=CA_PATH,
                    certfile=CERT_PATH,
                    keyfile=KEY_PATH,
                    tls_version=ssl.PROTOCOL_TLSv1_2)
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.loop_start()

# ---------------- INITIAL CONNECT ----------------
while not mqtt_connected:
    try:
        mqtt_client.connect(MQTT_ENDPOINT, port=8883)
    except Exception as e:
        print(f"❌ MQTT connect failed: {e}, retrying in 2 sec...")
        time.sleep(2)
    time.sleep(1)

print("🚀 Uploader started...\n")

# ---------------- MAIN LOOP ----------------
while True:
    # Fetch all unuploaded rows
    cursor.execute("SELECT * FROM brake_pressure_log WHERE uploaded=0 ORDER BY timestamp ASC")
    rows = cursor.fetchall()

    if not rows:
        time.sleep(0.3)
        continue

    for row in rows:
        payload = {
            "device_id": row["device_id"],
            "timestamp": row["timestamp"],
            "BP_raw": row["BP_raw"],
            "FP_raw": row["FP_raw"],
            "CR_raw": row["CR_raw"],
            "BC_raw": row["BC_raw"]
        }

        # Print local DB row
        print(f"📥 Local DB row: device_id={row['device_id']}, timestamp={row['timestamp']}, "
              f"BP_raw={row['BP_raw']}, FP_raw={row['FP_raw']}, CR_raw={row['CR_raw']}, BC_raw={row['BC_raw']}")

        # Wait until MQTT is connected
        while not mqtt_connected:
            print("⚠️ Waiting for MQTT connection before upload...")
            try:
                mqtt_client.reconnect()
            except Exception as e:
                print(f"❌ MQTT reconnect failed: {e}, retrying in 1 sec...")
            time.sleep(1)

        # Publish to AWS IoT
        try:
            mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
            print(f"📤 Sent to AWS IoT: {json.dumps(payload)}\n")
            # Mark row as uploaded
            cursor.execute("UPDATE brake_pressure_log SET uploaded=1 WHERE id=?", (row["id"],))
            conn.commit()
        except Exception as e:
            print(f"❌ Failed to publish row id={row['id']}: {e}")
            time.sleep(0.2)

    time.sleep(0)