import time
import sqlite3
import json
import ssl
import os
import paho.mqtt.client as mqtt

# ---------------- CONFIG ----------------
ENDPOINT = "a1vddjuckiz90j-ats.iot.ap-south-1.amazonaws.com"
PORT = 8883
CLIENT_ID = "Raspberrypi_4A"
TOPIC = "Raspberrypi_4A/data"

# Paths to your certificates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CA_PATH = os.path.join(BASE_DIR, "certs", "AmazonRootCA1.pem")
CERT_PATH = os.path.join(BASE_DIR, "certs", "Raspberrypi_4A-certificate.pem.crt")
KEY_PATH = os.path.join(BASE_DIR, "certs", "Raspberrypi_4A-private.pem.key")

DB_PATH = os.path.join(BASE_DIR, "db", "new_db.db")
READ_INTERVAL = 0.5  # seconds

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- MQTT HANDLERS ----------------
mqtt_connected = False

def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print("✅ Connected to AWS IoT Core", flush=True)
    else:
        mqtt_connected = False
        print(f"❌ MQTT connection failed with RC={rc}", flush=True)

def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    print("⚠️ MQTT disconnected. Will reconnect automatically...", flush=True)

mqtt_client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
mqtt_client.tls_set(ca_certs=CA_PATH, certfile=CERT_PATH, keyfile=KEY_PATH, tls_version=ssl.PROTOCOL_TLSv1_2)
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect

def connect_mqtt():
    global mqtt_client
    while not mqtt_connected:
        try:
            mqtt_client.connect(ENDPOINT, PORT, keepalive=120)
            mqtt_client.loop_start()
            wait_sec = 0
            while not mqtt_connected and wait_sec < 10:
                print("⚠️ Waiting for stable MQTT connection...", flush=True)
                time.sleep(1)
                wait_sec += 1
            if not mqtt_connected:
                mqtt_client.loop_stop()
                print("❌ MQTT connect attempt failed. Retrying in 5 sec...", flush=True)
                time.sleep(5)
        except Exception as e:
            print("❌ MQTT connect error:", e, "Retrying in 5 sec...", flush=True)
            time.sleep(5)

# ---------------- UPLOAD FUNCTION ----------------
def upload_row(row):
    payload = {
        "device_id": row["device_id"],
        "timestamp": row["timestamp"],
        "BP_raw": row["BP_raw"],
        "FP_raw": row["FP_raw"],
        "CR_raw": row["CR_raw"],
        "BC_raw": row["BC_raw"]
    }
    while True:
        if mqtt_connected:
            try:
                result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
                result.wait_for_publish()  # ensure delivery
                print(f"📥 Local DB row: device_id={row['device_id']}, timestamp={row['timestamp']}, "
                      f"BP_raw={row['BP_raw']}, FP_raw={row['FP_raw']}, CR_raw={row['CR_raw']}, BC_raw={row['BC_raw']}", flush=True)
                print(f"📤 Sent to AWS IoT: {json.dumps(payload)}\n", flush=True)
                # mark row as uploaded
                cursor.execute("UPDATE brake_pressure_log SET uploaded=1 WHERE id=?", (row["id"],))
                conn.commit()
                return True
            except Exception as e:
                print("❌ Publish failed:", e, "Retrying in 1s...", flush=True)
                time.sleep(1)
        else:
            print("⚠️ Waiting for MQTT connection before upload...", flush=True)
            connect_mqtt()
            time.sleep(1)

# ---------------- MAIN LOOP ----------------
print("🚀 Uploader started...", flush=True)
connect_mqtt()  # ensure MQTT is connected before uploading

try:
    while True:
        # fetch un-uploaded rows
        cursor.execute("SELECT * FROM brake_pressure_log WHERE uploaded=0 ORDER BY timestamp ASC")
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                upload_row(row)
        else:
            # no new data
            time.sleep(READ_INTERVAL)
except KeyboardInterrupt:
    print("🛑 Shutting down...", flush=True)
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    conn.close()