import sqlite3
import time
import os
import json
import uuid
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# ---------------- PATH CONFIG ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "new_db.db")
CERT_FOLDER = os.path.join(BASE_DIR, "certs")

# ---------------- AWS IOT CONFIG ----------------
ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT = 8883
TOPIC = "brake/data"
CLIENT_ID = "Raspberrypi_4A"

ROOT_CA = os.path.join(CERT_FOLDER, "AmazonRootCA1.pem")
CERTIFICATE = os.path.join(CERT_FOLDER, "certificate.pem.crt")
PRIVATE_KEY = os.path.join(CERT_FOLDER, "private.pem.key")

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("🔎 Verifying certificate files...\n", flush=True)
for f in [ROOT_CA, CERTIFICATE, PRIVATE_KEY]:
    if not os.path.exists(f):
        print(f"❌ Missing file: {f}", flush=True)
        exit()
    else:
        print(f"✅ Found: {f}", flush=True)
print("Certificate verification successful!\n", flush=True)
print("Uploader Started...\n", flush=True)

# ---------------- MQTT CLIENT ----------------
CLIENT_ID = f"client_{uuid.uuid4().hex[:8]}"
mqtt_client = AWSIoTMQTTClient(CLIENT_ID)
mqtt_client.configureEndpoint(ENDPOINT, PORT)
mqtt_client.configureCredentials(ROOT_CA, PRIVATE_KEY, CERTIFICATE)
mqtt_client.configureOfflinePublishQueueing(-1)  # Infinite offline queue
mqtt_client.configureDrainingFrequency(2)        # Draining: 2 Hz
mqtt_client.configureConnectDisconnectTimeout(10)
mqtt_client.configureMQTTOperationTimeout(5)

# ---------------- CONNECT FUNCTION ----------------
def connect_mqtt():
    while True:
        try:
            mqtt_client.connect()
            print("🔌 Connected to AWS IoT Core\n", flush=True)
            break
        except Exception as e:
            print(f"⚠️ MQTT Connection failed: {e}", flush=True)
            time.sleep(2)

connect_mqtt()

# ---------------- MAIN LOOP ----------------
while True:
    try:
        # Fetch one unsent row from DB
        cur.execute("""
            SELECT * FROM brake_pressure_log
            WHERE uploaded = 0 OR uploaded IS NULL
            ORDER BY timestamp ASC
            LIMIT 1
        """)
        row = cur.fetchone()

        if row:
            # Get device_id from DB row (capture.py writes it)
            DEVICE_ID = row["device_id"] if "device_id" in row.keys() else "UNKNOWN"

            payload = {
                "device_id": DEVICE_ID,
                "timestamp": row["timestamp"],
                "BP_raw": row["BP_raw"],
                "FP_raw": row["FP_raw"],
                "CR_raw": row["CR_raw"],
                "BC_raw": row["BC_raw"]
            }

            # Publish payload
            try:
                mqtt_client.publish(TOPIC, json.dumps(payload), 1)

                # Update DB after successful publish
                cur.execute("UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?", (row["id"],))
                conn.commit()

                print("📤 Data Published to AWS IoT Core:", flush=True)
                print(json.dumps(payload, indent=2), flush=True)

            except Exception as e:
                print(f"⚠️ MQTT Publish failed: {e}", flush=True)
                print("Retrying MQTT connection...", flush=True)
                connect_mqtt()  # reconnect if failed

        else:
            print("⏭ No new data to upload", flush=True)

        time.sleep(2)

    except Exception as e:
        print(f"⚠️ Runtime Error: {e}", flush=True)
        time.sleep(1)