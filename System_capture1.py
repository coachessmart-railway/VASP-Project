# ---------------- IMPORTS ----------------
import time
import sys
import sqlite3
import os

# ---------------- ENCODING ----------------
sys.stdout.reconfigure(encoding='utf-8')

# ---------------- CONFIG ----------------
RAW_THRESHOLD = 1638       # Threshold for significant change (~0.5 bar)
READ_INTERVAL = 0.5        # seconds

# ---------------- DATABASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "db")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "new_db.db")

# ---------------- DEVICE CONFIG ----------------
DEVICE_CONFIG_DIR = os.path.join(DB_DIR, "device_config")
DEVICE_ID_FILE = os.path.join(DEVICE_CONFIG_DIR, "device_id.txt")

DEVICE_ID = None
try:
    with open(DEVICE_ID_FILE, "r") as f:
        DEVICE_ID = f.read().strip()
except FileNotFoundError:
    DEVICE_ID = None

if DEVICE_ID:
    print(f"✅ Device ID is assigned: {DEVICE_ID}\n", flush=True)
else:
    print("⚠️ Device ID missing or not found!\n", flush=True)

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS brake_pressure_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT,
    bp_pressure REAL,
    fp_pressure REAL,
    cr_pressure REAL,
    bc_pressure REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    uploaded INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------------- ADS1115 SENSOR ----------------
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

except Exception:
    ADS_AVAILABLE = False
    print("⚠️ ADS1115 sensor not available. Sensor reads will return 0.", flush=True)

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
print("🚀 Capture system started...\n", flush=True)

# Print CSV header once
print("Device_id, BP_raw, FP_raw, CR_raw, BC_raw, timestamp", flush=True)

last_raw = None

while True:
    current_raw = read_raw_values()
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    # Prepare CSV-style line
    device_id_print = DEVICE_ID if DEVICE_ID else "MISSING"
    csv_line = f"{device_id_print}, {current_raw[0]}, {current_raw[1]}, {current_raw[2]}, {current_raw[3]}, {timestamp}"
    print(csv_line, flush=True)

    # Decide if this reading should be inserted
    upload = False
    if last_raw is None:
        upload = True
    else:
        diffs = [abs(current_raw[i] - last_raw[i]) for i in range(4)]
        if any(diff >= RAW_THRESHOLD for diff in diffs):
            upload = True

    # Insert only if significant change
    if upload:
        cursor.execute("""
            INSERT INTO brake_pressure_log
            (device_id, bp_pressure, fp_pressure, cr_pressure, bc_pressure)
            VALUES (?, ?, ?, ?, ?)
        """, (DEVICE_ID, *current_raw))
        conn.commit()
        last_raw = current_raw
    else:
        print("⏭ No significant change → Skipped insert", flush=True)

    time.sleep(READ_INTERVAL)