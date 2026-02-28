import time
import sys
import sqlite3
import os

# ---------------- ENCODING ----------------
sys.stdout.reconfigure(encoding='utf-8')

# ---------------- CONFIG ----------------
RAW_THRESHOLD = 2049        # ~0.5 bar equivalent
READ_INTERVAL = 0.5         # seconds

# ---------------- DATABASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "new_db.db")

# ---------------- DATABASE CONNECTION ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# ---------------- TABLE SETUP ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS brake_pressure_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT,
    BP_raw INTEGER,
    FP_raw INTEGER,
    CR_raw INTEGER,
    BC_raw INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    uploaded INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------------- GET DEVICE ID ----------------
cursor.execute("SELECT device_id FROM device_config LIMIT 1")
result = cursor.fetchone()
if result:
    DEVICE_ID = result[0]
    print(f" Device ID found: {DEVICE_ID}", flush=True)
else:
    DEVICE_ID = "MISSING"
    print(" Device ID missing or not found!", flush=True)

# ---------------- ADS1115 SENSOR SETUP ----------------
ADS_AVAILABLE = True
try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    ads.gain = 1

    bp_channel = AnalogIn(ads, 0)
    fp_channel = AnalogIn(ads, 1)
    cr_channel = AnalogIn(ads, 2)
    bc_channel = AnalogIn(ads, 3)

except Exception as e:
    ADS_AVAILABLE = False
    print(f"ADS1115 not available: {e}", flush=True)

# ---------------- SENSOR READ FUNCTION ----------------
def read_raw_values():
    if ADS_AVAILABLE:
        return (
            bp_channel.value,
            fp_channel.value,
            cr_channel.value,
            bc_channel.value
        )
    return (0, 0, 0, 0)

# ---------------- MAIN LOOP ----------------
print("\n Capture system started...\n", flush=True)
print("Device_id, BP_raw, FP_raw, CR_raw, BC_raw, timestamp", flush=True)

last_raw = None

while True:
    current_raw = read_raw_values()
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    # Print CSV-style output
    print(
        f"{DEVICE_ID}, {current_raw[0]}, {current_raw[1]}, {current_raw[2]}, {current_raw[3]}, {timestamp}",
        flush=True
    )

    upload = False
    if last_raw is None:
        upload = True
    else:
        diffs = [abs(current_raw[i] - last_raw[i]) for i in range(4)]
        if any(diff >= RAW_THRESHOLD for diff in diffs):
            upload = True

    if upload:
        cursor.execute("""
            INSERT INTO brake_pressure_log
            (device_id, BP_raw, FP_raw, CR_raw, BC_raw, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (DEVICE_ID, *current_raw, timestamp))
        conn.commit()
        last_raw = current_raw
        print(f" Data inserted into DB at {timestamp}", flush=True)
    else:
        print(" No significant change → Skipped insert", flush=True)

    print("---------------------------------------------\n", flush=True)
    time.sleep(READ_INTERVAL)