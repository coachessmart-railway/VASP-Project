import time
import sys
import sqlite3
import os

# ---------------- ENCODING ----------------
sys.stdout.reconfigure(encoding='utf-8')

# ---------------- CONFIG ----------------
RAW_THRESHOLD = 326  # ~0.5 bar equivalent
READ_INTERVAL = 0.1  # seconds

# ---------------- DATABASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "new_db.db")

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row  # allows column name access
cursor = conn.cursor()

# Ensure brake_pressure_log table exists
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

# ---------------- FETCH DEVICE ID ----------------
cursor.execute("SELECT device_id FROM device_config LIMIT 1")
DEVICE_ROW = cursor.fetchone()
if DEVICE_ROW and DEVICE_ROW["device_id"]:
    DEVICE_ID = DEVICE_ROW["device_id"]
    print(f"✅ Device ID = {DEVICE_ID}\n", flush=True)
else:
    DEVICE_ID = "UNKNOWN"
    print("⚠️ Device ID missing!", flush=True)

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

    print("✅ ADS1115 sensor detected and initialized.", flush=True)

except Exception as e:
    ADS_AVAILABLE = False
    print(f"⚠️ ADS1115 sensor not detected! ({e})", flush=True)

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

last_raw = None

while True:
    if ADS_AVAILABLE:
        current_raw = read_raw_values()
        ads_status = "Connected"
    else:
        current_raw = (0, 0, 0, 0)
        ads_status = "Not connected"

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    # Print output format including ADS1115 status
    print(
        f"device_id = {DEVICE_ID}, "
        f"BP_raw = {current_raw[0]}, FP_raw = {current_raw[1]}, "
        f"CR_raw = {current_raw[2]}, BC_raw = {current_raw[3]}, "
        f"timestamp = {timestamp}, "
        f"ADS1115_status = {ads_status}",
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
        print(f"✅ Data inserted into DB at {timestamp}\n", flush=True)
    else:
        print("⏭ No significant change → Skipped insert\n", flush=True)

    time.sleep(READ_INTERVAL)