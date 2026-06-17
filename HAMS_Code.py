import serial
import sqlite3
import json
import os
import time
from datetime import datetime
from awscrt import mqtt
from awsiot import mqtt_connection_builder

SERIAL_PORT = "/dev/serial0"
BAUD_RATE = 9600

BASE_DIR = "/home/pi_1234/data/src/pressure_project/VASP-Project"

DB_DIR = os.path.join(BASE_DIR, "db", "HAMS_DB")
DB_FILE = os.path.join(DB_DIR, "hams_data.db")

CERT_DIR = os.path.join(BASE_DIR, "HAMS_certs")
CA_PATH = os.path.join(CERT_DIR, "AmazonRootCA1.pem")
CERT_PATH = os.path.join(CERT_DIR, "certificate.pem.crt")
KEY_PATH = os.path.join(CERT_DIR, "private.pem.key")

AWS_ENDPOINT = "a1vddjuckiz90j-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "HAMS_Data"
TOPIC = "hams/device/data"


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)

    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS device_config (
        id INTEGER PRIMARY KEY,
        device_id TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS hams_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        master_id TEXT,
        device_id TEXT,
        received_timestamp TEXT,
        device_time TEXT,
        temperature REAL,
        status TEXT,
        temp_state TEXT,
        resistance REAL,
        pt1000_voltage REAL,
        pt1000_adc INTEGER,
        battery_ads_voltage REAL,
        battery_voltage REAL,
        battery_adc INTEGER,
        message TEXT,
        raw_data TEXT,
        aws_publish_status TEXT
    )
    """)

    con.commit()
    con.close()


def get_master_id():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    cur.execute("SELECT device_id FROM device_config WHERE id = 1")
    row = cur.fetchone()

    con.close()

    if row and row[0].strip():
        return row[0].strip()

    print("No ID given in device_config table")
    return None


def parse_compact_packet(line, master_id):
    parts = line.strip().split(",")

    if len(parts) != 11:
        print("Invalid packet length:", len(parts))
        return None

    try:
        received_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        device_id = parts[0]
        device_time = parts[1] + " sec"
        temperature = float(parts[2])
        status = parts[3]
        temp_state = parts[4]
        resistance = float(parts[5])
        pt1000_voltage = float(parts[6])
        pt1000_adc = int(parts[7])
        battery_ads_voltage = float(parts[8])
        battery_voltage = float(parts[9])
        battery_adc = int(parts[10])

        db_data = {
            "master_id": master_id if master_id else "NO_ID_GIVEN",
            "device_id": device_id,
            "received_timestamp": received_timestamp,
            "device_time": device_time,
            "temperature": temperature,
            "status": status,
            "temp_state": temp_state,
            "resistance": resistance,
            "pt1000_voltage": pt1000_voltage,
            "pt1000_adc": pt1000_adc,
            "battery_ads_voltage": battery_ads_voltage,
            "battery_voltage": battery_voltage,
            "battery_adc": battery_adc,
            "message": "LoRa data received successfully",
            "raw_data": line,
            "aws_publish_status": "pending"
        }

        aws_data = {
            "master_id": master_id,
            "device_id": device_id,
            "received_timestamp": received_timestamp,
            "device_time": device_time,
            "temperature": temperature,
            "status": status,
            "temp_state": temp_state,
            "resistance": resistance,
            "pt1000_voltage": pt1000_voltage,
            "pt1000_adc": pt1000_adc,
            "battery_ads_voltage": battery_ads_voltage,
            "battery_voltage": battery_voltage,
            "battery_adc": battery_adc,
            "message": "LoRa data received successfully"
        }

        return db_data, aws_data

    except Exception as e:
        print("Packet parsing error:", e)
        return None


def save_to_db(data):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    cur.execute("""
    INSERT INTO hams_data (
        master_id, device_id, received_timestamp, device_time,
        temperature, status, temp_state,
        resistance, pt1000_voltage, pt1000_adc,
        battery_ads_voltage, battery_voltage, battery_adc,
        message, raw_data, aws_publish_status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["master_id"],
        data["device_id"],
        data["received_timestamp"],
        data["device_time"],
        data["temperature"],
        data["status"],
        data["temp_state"],
        data["resistance"],
        data["pt1000_voltage"],
        data["pt1000_adc"],
        data["battery_ads_voltage"],
        data["battery_voltage"],
        data["battery_adc"],
        data["message"],
        data["raw_data"],
        data["aws_publish_status"]
    ))

    row_id = cur.lastrowid
    con.commit()
    con.close()
    return row_id


def update_aws_status(row_id, status):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    cur.execute("""
    UPDATE hams_data
    SET aws_publish_status = ?
    WHERE id = ?
    """, (status, row_id))

    con.commit()
    con.close()


def connect_aws():
    while True:
        try:
            print("Connecting to AWS IoT Core...")

            mqtt_connection = mqtt_connection_builder.mtls_from_path(
                endpoint=AWS_ENDPOINT,
                cert_filepath=CERT_PATH,
                pri_key_filepath=KEY_PATH,
                ca_filepath=CA_PATH,
                client_id=CLIENT_ID,
                clean_session=False,
                keep_alive_secs=30
            )

            mqtt_connection.connect().result()
            print("Connected to AWS IoT Core")
            return mqtt_connection

        except Exception as e:
            print("AWS connection failed:", e)
            print("Reconnect after 5 seconds...")
            time.sleep(5)


def reconnect_aws(old_connection=None):
    try:
        if old_connection:
            old_connection.disconnect().result()
    except Exception:
        pass

    return connect_aws()


def publish_to_aws(mqtt_connection, data):
    payload = json.dumps(data)

    publish_future, packet_id = mqtt_connection.publish(
        topic=TOPIC,
        payload=payload,
        qos=mqtt.QoS.AT_LEAST_ONCE
    )

    publish_future.result()


def publish_with_reconnect(mqtt_connection, aws_data, row_id):
    while True:
        try:
            publish_to_aws(mqtt_connection, aws_data)
            update_aws_status(row_id, "published")
            print("Published to AWS IoT Core")
            return mqtt_connection

        except Exception as e:
            print("AWS disconnected / publish failed:", e)
            update_aws_status(row_id, "failed")

            print("Reconnect after 5 seconds...")
            time.sleep(5)

            mqtt_connection = reconnect_aws(mqtt_connection)

            time.sleep(0.1)


def main():
    init_db()

    master_id = get_master_id()

    if master_id:
        print(f'Master ID = "{master_id}"')
        mqtt_connection = connect_aws()
    else:
        print("No ID given. Data will be received and saved, but not published to AWS.")
        mqtt_connection = None

    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

    print("HAMS Raspberry Pi Master Receiver Started")
    print("Waiting for LoRa data...")

    while True:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()

            if not line:
                time.sleep(0.1)
                continue

            print("RX:", line)

            if line.startswith("SLEEP"):
                continue

            if "ADS_ERROR" in line:
                print("ADS1115 error received:", line)
                continue

            parsed = parse_compact_packet(line, master_id)

            if parsed is None:
                print("Invalid packet. Not saved.")
                print("-----------------------------------")
                continue

            db_data, aws_data = parsed

            row_id = save_to_db(db_data)
            print("Saved offline DB. Row ID:", row_id)

            if master_id is None:
                update_aws_status(row_id, "not_published_no_master_id")
                print("No ID given. AWS publish skipped.")
                print("-----------------------------------")
                continue

            aws_data["db_id"] = row_id

            mqtt_connection = publish_with_reconnect(
                mqtt_connection,
                aws_data,
                row_id
            )

            print("-----------------------------------")

        except KeyboardInterrupt:
            print("Stopped by user")
            break

        except Exception as e:
            print("Main loop error:", e)
            time.sleep(0.1)

    ser.close()

    try:
        if mqtt_connection:
            mqtt_connection.disconnect().result()
            print("AWS MQTT disconnected safely")
    except Exception:
        pass


if __name__ == "__main__":
    main()