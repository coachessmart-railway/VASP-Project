import serial
import sqlite3
import json
import os
import re
import time
from datetime import datetime
from awscrt import mqtt
from awsiot import mqtt_connection_builder

# =========================
# LoRa UART
# =========================
SERIAL_PORT = "/dev/serial0"
BAUD_RATE = 9600

# =========================
# Project Paths
# =========================
BASE_PATH = "/home/pi_1234/data/src/pressure_project/VASP-Project"

DB_DIR = BASE_PATH + "/db/HAMS_DB"
DB_FILE = DB_DIR + "/hams_data.db"

CERT_DIR = BASE_PATH + "/HAMS_certs"
CERT_FILE = CERT_DIR + "/device_certificate.pem.crt"
KEY_FILE = CERT_DIR + "/private_key.pem.key"
ROOT_CA_FILE = CERT_DIR + "/root_ca.pem"

# =========================
# AWS IoT Core
# =========================
AWS_ENDPOINT = "a1vddjuckiz90j-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "HAMS_Data"
TOPIC = "hams/device/data"


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)

    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS hams_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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


def get_float(text):
    match = re.search(r"-?\d+\.?\d*", text)
    return float(match.group()) if match else None


def get_int(text):
    match = re.search(r"-?\d+", text)
    return int(match.group()) if match else None


def parse_hams_packet(raw_data):
    data = {
        "received_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "raw_data": raw_data,
        "aws_publish_status": "pending"
    }

    for line in raw_data.splitlines():
        line = line.strip()

        if line.startswith("ID"):
            data["device_id"] = line.split(":", 1)[1].strip()

        elif line.startswith("Time"):
            data["device_time"] = line.split(":", 1)[1].strip()

        elif line.startswith("Temperature"):
            data["temperature"] = get_float(line)

            status_match = re.search(r'Status\s*=\s*"([^"]+)"', line)
            state_match = re.search(r'Temp_State\s*=\s*"([^"]+)"', line)

            if status_match:
                data["status"] = status_match.group(1)

            if state_match:
                data["temp_state"] = state_match.group(1)

        elif line.startswith("Resistance"):
            data["resistance"] = get_float(line)

        elif line.startswith("PT1000 Voltage"):
            data["pt1000_voltage"] = get_float(line)

        elif line.startswith("PT1000 ADC"):
            data["pt1000_adc"] = get_int(line)

        elif line.startswith("Battery ADS Vtg"):
            data["battery_ads_voltage"] = get_float(line)

        elif line.startswith("Battery Voltage"):
            data["battery_voltage"] = get_float(line)

        elif line.startswith("Battery ADC"):
            data["battery_adc"] = get_int(line)

        elif line.startswith("Message"):
            data["message"] = line

    return data


def save_to_db(data):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    cur.execute("""
    INSERT INTO hams_data (
        device_id,
        received_timestamp,
        device_time,
        temperature,
        status,
        temp_state,
        resistance,
        pt1000_voltage,
        pt1000_adc,
        battery_ads_voltage,
        battery_voltage,
        battery_adc,
        message,
        raw_data,
        aws_publish_status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("device_id"),
        data.get("received_timestamp"),
        data.get("device_time"),
        data.get("temperature"),
        data.get("status"),
        data.get("temp_state"),
        data.get("resistance"),
        data.get("pt1000_voltage"),
        data.get("pt1000_adc"),
        data.get("battery_ads_voltage"),
        data.get("battery_voltage"),
        data.get("battery_adc"),
        data.get("message"),
        data.get("raw_data"),
        data.get("aws_publish_status")
    ))

    row_id = cur.lastrowid
    con.commit()
    con.close()

    return row_id


def update_aws_status(row_id, status):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    cur.execute(
        "UPDATE hams_data SET aws_publish_status=? WHERE id=?",
        (status, row_id)
    )

    con.commit()
    con.close()


def connect_aws():
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=AWS_ENDPOINT,
        cert_filepath=CERT_FILE,
        pri_key_filepath=KEY_FILE,
        ca_filepath=ROOT_CA_FILE,
        client_id=CLIENT_ID,
        clean_session=False,
        keep_alive_secs=30
    )

    print("Connecting to AWS IoT Core...")
    mqtt_connection.connect().result()
    print("Connected to AWS IoT Core")

    return mqtt_connection


def publish_to_aws(mqtt_connection, data):
    payload = json.dumps(data)

    mqtt_connection.publish(
        topic=TOPIC,
        payload=payload,
        qos=mqtt.QoS.AT_LEAST_ONCE
    )


def main():
    init_db()

    mqtt_connection = connect_aws()

    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)

    print("HAMS Raspberry Pi Master Receiver Started")
    print("Waiting for LoRa data from HAMS001 to HAMS008...")

    buffer = ""

    while True:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()

            if line:
                print("RX:", line)
                buffer += line + "\n"

                if "LoRa data sent successfully" in line:
                    data = parse_hams_packet(buffer)

                    if not data.get("device_id"):
                        print("Invalid packet: Device ID missing")
                        buffer = ""
                        continue

                    row_id = save_to_db(data)
                    print("Saved offline DB. Row ID:", row_id)

                    data["db_id"] = row_id

                    try:
                        publish_to_aws(mqtt_connection, data)
                        update_aws_status(row_id, "published")
                        print("Published to AWS IoT Core")
                    except Exception as e:
                        update_aws_status(row_id, "failed")
                        print("AWS publish failed:", e)

                    print("-----------------------------------")
                    buffer = ""

        except KeyboardInterrupt:
            print("Stopped by user")
            break

        except Exception as e:
            print("Error:", e)
            time.sleep(2)

    ser.close()
    mqtt_connection.disconnect().result()


if __name__ == "__main__":
    main()