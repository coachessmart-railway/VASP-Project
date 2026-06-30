import serial
import sqlite3
import json
import os
import time
import threading
from datetime import datetime

from awscrt import mqtt
from awsiot import mqtt_connection_builder
from RPLCD.i2c import CharLCD

# ================= SERIAL / LORA =================
SERIAL_PORT = "/dev/serial0"
BAUD_RATE = 9600

# ================= PROJECT PATHS =================
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

# ================= LCD1602 I2C =================
# i2cdetect: 0x27 = LCD, 0x48 = ADS1115
lcd = CharLCD(
    i2c_expander="PCF8574",
    address=0x27,
    port=1,
    cols=16,
    rows=2,
    charmap="A00",
    auto_linebreaks=True
)


def lcd_print(line1="", line2=""):
    try:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string(str(line1)[:16])
        lcd.cursor_pos = (1, 0)
        lcd.write_string(str(line2)[:16])
    except Exception as e:
        print("LCD error:", e)


def display_lora_data(data):
    # LCD shows only Device ID, Temperature, Timestamp
    line1 = f"{data['device_id']} T:{data['temperature']:.1f}C"
    # received_timestamp example: 2026-06-30 14:28:44 -> 06-30 14:28
    line2 = data["received_timestamp"][5:16]
    lcd_print(line1, line2)


# ================= DATABASE =================
def get_db_connection():
    # timeout helps if main thread and AWS thread access DB together
    return sqlite3.connect(DB_FILE, timeout=10, check_same_thread=False)


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)

    con = get_db_connection()
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
        generation_no INTEGER,
        sequence_no INTEGER,
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

    cur.execute("PRAGMA table_info(hams_data)")
    columns = [col[1] for col in cur.fetchall()]

    add_cols = {
        "master_id": "TEXT",
        "device_id": "TEXT",
        "generation_no": "INTEGER",
        "sequence_no": "INTEGER",
        "received_timestamp": "TEXT",
        "device_time": "TEXT",
        "temperature": "REAL",
        "status": "TEXT",
        "temp_state": "TEXT",
        "resistance": "REAL",
        "pt1000_voltage": "REAL",
        "pt1000_adc": "INTEGER",
        "battery_ads_voltage": "REAL",
        "battery_voltage": "REAL",
        "battery_adc": "INTEGER",
        "message": "TEXT",
        "raw_data": "TEXT",
        "aws_publish_status": "TEXT"
    }

    for col, col_type in add_cols.items():
        if col not in columns:
            cur.execute(f"ALTER TABLE hams_data ADD COLUMN {col} {col_type}")

    con.commit()
    con.close()


def get_master_id():
    con = get_db_connection()
    cur = con.cursor()
    cur.execute("SELECT device_id FROM device_config WHERE id = 1")
    row = cur.fetchone()
    con.close()

    if row and row[0].strip():
        return row[0].strip()

    print("No ID given in device_config table")
    return None


def save_to_db(data):
    con = get_db_connection()
    cur = con.cursor()

    cur.execute("""
    INSERT INTO hams_data (
        master_id, device_id, generation_no, sequence_no,
        received_timestamp, device_time,
        temperature, status, temp_state,
        resistance, pt1000_voltage, pt1000_adc,
        battery_ads_voltage, battery_voltage, battery_adc,
        message, raw_data, aws_publish_status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["master_id"],
        data["device_id"],
        data["generation_no"],
        data["sequence_no"],
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
    con = get_db_connection()
    cur = con.cursor()
    cur.execute("UPDATE hams_data SET aws_publish_status = ? WHERE id = ?", (status, row_id))
    con.commit()
    con.close()


def get_pending_aws_rows(limit=20):
    con = get_db_connection()
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("""
        SELECT * FROM hams_data
        WHERE aws_publish_status IN ('pending', 'failed')
        ORDER BY id ASC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    con.close()
    return rows


def row_to_aws_data(row):
    return {
        "db_id": row["id"],
        "master_id": row["master_id"],
        "device_id": row["device_id"],
        "generation_no": row["generation_no"],
        "sequence_no": row["sequence_no"],
        "received_timestamp": row["received_timestamp"],
        "device_time": row["device_time"],
        "temperature": row["temperature"],
        "status": row["status"],
        "temp_state": row["temp_state"],
        "resistance": row["resistance"],
        "pt1000_voltage": row["pt1000_voltage"],
        "pt1000_adc": row["pt1000_adc"],
        "battery_ads_voltage": row["battery_ads_voltage"],
        "battery_voltage": row["battery_voltage"],
        "battery_adc": row["battery_adc"],
        "message": row["message"]
    }


# ================= PACKET PARSING =================
def parse_compact_packet(line, master_id):
    parts = line.strip().split(",")

    # Packet format:
    # HAMS002,11,3,7,32.42,Moderate,Normal,1126.10,0.3340,2672,0.5540,3.32,4432
    if len(parts) != 13:
        print("Invalid packet length:", len(parts))
        return None

    try:
        received_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "master_id": master_id if master_id else "NO_ID_GIVEN",
            "device_id": parts[0],
            "generation_no": int(parts[1]),
            "sequence_no": int(parts[2]),
            "received_timestamp": received_timestamp,
            "device_time": parts[3] + " sec",
            "temperature": float(parts[4]),
            "status": parts[5],
            "temp_state": parts[6],
            "resistance": float(parts[7]),
            "pt1000_voltage": float(parts[8]),
            "pt1000_adc": int(parts[9]),
            "battery_ads_voltage": float(parts[10]),
            "battery_voltage": float(parts[11]),
            "battery_adc": int(parts[12]),
            "message": "LoRa data received successfully",
            "raw_data": line,
            "aws_publish_status": "pending"
        }

    except Exception as e:
        print("Packet parsing error:", e)
        return None


# ================= AWS MQTT =================
def connect_aws_once():
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
    return mqtt_connection


def disconnect_aws(mqtt_connection):
    try:
        if mqtt_connection:
            mqtt_connection.disconnect().result()
    except Exception:
        pass


def publish_to_aws(mqtt_connection, data):
    payload = json.dumps(data)
    publish_future, packet_id = mqtt_connection.publish(
        topic=TOPIC,
        payload=payload,
        qos=mqtt.QoS.AT_LEAST_ONCE
    )
    publish_future.result()


def aws_publish_worker(master_id):
    """
    Background AWS thread:
    - Connects to AWS continuously.
    - Publishes all pending/failed rows from SQLite.
    - If AWS disconnects, marks row failed and reconnects.
    - Main LoRa receiving never stops because of AWS issue.
    """
    if master_id is None:
        print("AWS worker stopped: No master ID.")
        return

    mqtt_connection = None

    while True:
        try:
            if mqtt_connection is None:
                print("Connecting to AWS IoT Core...")
                lcd_print("AWS Connecting", "Please wait")
                mqtt_connection = connect_aws_once()
                print("Connected to AWS IoT Core")
                lcd_print("AWS Connected", "Waiting LoRa")

            rows = get_pending_aws_rows(limit=20)

            if not rows:
                time.sleep(1)
                continue

            for row in rows:
                aws_data = row_to_aws_data(row)
                publish_to_aws(mqtt_connection, aws_data)
                update_aws_status(row["id"], "published")
                print(f"Published to AWS IoT Core. Row ID: {row['id']}")

        except Exception as e:
            print("AWS disconnected / publish failed:", e)

            # Mark oldest pending row failed, so it retries later
            try:
                rows = get_pending_aws_rows(limit=1)
                if rows:
                    update_aws_status(rows[0]["id"], "failed")
            except Exception:
                pass

            lcd_print("AWS Failed", "Retrying...")
            disconnect_aws(mqtt_connection)
            mqtt_connection = None
            time.sleep(5)


# ================= SERIAL =================
def open_serial():
    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print("Serial opened:", SERIAL_PORT)
            return ser
        except Exception as e:
            print("Serial open failed:", e)
            lcd_print("Serial Failed", "Retry 2 sec")
            time.sleep(2)


# ================= PRINT DATA =================
def print_parsed_data(data):
    print("Parsed Data:")
    print("Master ID      :", data["master_id"])
    print("Device ID      :", data["device_id"])
    print("Generation No  :", data["generation_no"])
    print("Sequence No    :", data["sequence_no"])
    print("Device Time    :", data["device_time"])
    print("Temperature    :", data["temperature"])
    print("Status         :", data["status"])
    print("Temp State     :", data["temp_state"])
    print("Resistance     :", data["resistance"])
    print("PT1000 Voltage :", data["pt1000_voltage"])
    print("PT1000 ADC     :", data["pt1000_adc"])
    print("Battery ADS V  :", data["battery_ads_voltage"])
    print("Battery V      :", data["battery_voltage"])
    print("Battery ADC    :", data["battery_adc"])


# ================= MAIN =================
def main():
    init_db()
    master_id = get_master_id()

    if master_id:
        print(f'Master ID = "{master_id}"')
        lcd_print("HAMS Receiver", master_id[:16])
    else:
        print("No ID given. Data will be saved but not published to AWS.")
        lcd_print("No Master ID", "AWS Skipped")

    # Start AWS publisher in background.
    # It will also publish old pending/failed DB rows after reconnect.
    aws_thread = threading.Thread(target=aws_publish_worker, args=(master_id,), daemon=True)
    aws_thread.start()

    ser = open_serial()

    print("HAMS Raspberry Pi Master Receiver Started")
    print("Waiting for LoRa data...")
    lcd_print("HAMS Receiver", "Waiting LoRa")

    while True:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()

            if not line:
                continue

            print("RX:", line)

            if line.startswith("SLEEP"):
                continue

            if "ADS_ERROR" in line:
                print("ADS1115 error received:", line)
                lcd_print("ADS Error", line[:16])
                continue

            if "ID_ERROR" in line:
                print("Device ID error received:", line)
                lcd_print("ID Error", line[:16])
                continue

            db_data = parse_compact_packet(line, master_id)

            if db_data is None:
                print("Invalid packet. Not saved.")
                lcd_print("Invalid Packet", line[:16])
                print("-----------------------------------")
                continue

            print_parsed_data(db_data)
            display_lora_data(db_data)

            row_id = save_to_db(db_data)
            print("Saved offline DB. Row ID:", row_id)
            print("AWS publish status: pending")
            print("-----------------------------------")

        except KeyboardInterrupt:
            print("Stopped by user")
            try:
                lcd.clear()
            except Exception:
                pass
            break

        except serial.SerialException as e:
            print("Serial port error:", e)
            lcd_print("Serial Error", "Reopen...")
            try:
                ser.close()
            except Exception:
                pass
            time.sleep(2)
            ser = open_serial()

        except Exception as e:
            print("Main loop error:", e)
            lcd_print("Main Error", str(e)[:16])
            time.sleep(0.5)

    try:
        ser.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()
