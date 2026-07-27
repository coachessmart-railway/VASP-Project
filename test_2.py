#!/usr/bin/env python3

import os
import sys
import time
import sqlite3
import serial
import pynmea2

# =====================================================
# CONFIGURATION
# =====================================================

RAW_THRESHOLD = 326
READ_INTERVAL = 0.1

GPS_PORT = "/dev/ttyAMA3"
GPS_BAUD = 38400

LCD_ADDRESS = 0x27
LCD_COLS = 20
LCD_ROWS = 4

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================
# DATABASE
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FOLDER = os.path.join(BASE_DIR, "db")
os.makedirs(DB_FOLDER, exist_ok=True)

DB_PATH = os.path.join(DB_FOLDER, "test_db.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS brake_pressure_log
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    device_id TEXT,

    BP_raw INTEGER,
    FP_raw INTEGER,
    CR_raw INTEGER,
    BC_raw INTEGER,

    MR_raw INTEGER,

    Battery_raw INTEGER,
    Battery_voltage REAL,

    timestamp TEXT,

    uploaded INTEGER DEFAULT 0
)
""")

conn.commit()

print("✅ Database Connected")

# =====================================================
# DEVICE ID
# =====================================================

try:

    cursor.execute(
        "SELECT device_id FROM device_config LIMIT 1"
    )

    row = cursor.fetchone()

    if row:
        DEVICE_ID = row[0]
    else:
        DEVICE_ID = "UNKNOWN"

except Exception:

    DEVICE_ID = "UNKNOWN"

print("Device ID =", DEVICE_ID)

# =====================================================
# ADS1115
# =====================================================

ADS048_STATUS = "Disconnected"
ADS049_STATUS = "Disconnected"

BP = None
FP = None
CR = None
BC = None

MR = None
BAT = None

try:

    import board
    import busio

    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c = busio.I2C(board.SCL, board.SDA)

    ads1 = ADS.ADS1115(i2c, address=0x48)
    ads2 = ADS.ADS1115(i2c, address=0x49)

    ads1.gain = 1
    ads2.gain = 1

    BP = AnalogIn(ads1, 0)
    FP = AnalogIn(ads1, 1)
    CR = AnalogIn(ads1, 2)
    BC = AnalogIn(ads1, 3)

    MR = AnalogIn(ads2, 0)
    BAT = AnalogIn(ads2, 1)

    ADS048_STATUS = "Connected"
    ADS049_STATUS = "Connected"

    print("✅ ADS1115 0x48 Connected")
    print("✅ ADS1115 0x49 Connected")

except Exception as e:

    print("❌ ADS1115 Error:", e)

# =====================================================
# GPS
# =====================================================

gps = None

try:

    gps = serial.Serial(
        GPS_PORT,
        GPS_BAUD,
        timeout=1
    )

    print("✅ GPS Connected")

except Exception as e:

    print("❌ GPS Error:", e)

# =====================================================
# LCD
# =====================================================

lcd = None

try:

    from RPLCD.i2c import CharLCD

    lcd = CharLCD(
        "PCF8574",
        LCD_ADDRESS,
        cols=LCD_COLS,
        rows=LCD_ROWS
    )

    lcd.clear()

    print("✅ LCD Connected")

except Exception as e:

    print("❌ LCD Error:", e)

lcd_page = 0
lcd_last_time = 0
LCD_DELAY = 10                                                                                                                                                                                                      
# =====================================================
# READ ADS1115 RAW VALUES
# =====================================================

def read_raw_values():

    data = {

        "BP_raw": 0,
        "FP_raw": 0,
        "CR_raw": 0,
        "BC_raw": 0,

        "MR_raw": 0,

        "Battery_raw": 0,
        "Battery_voltage": 0.0

    }

    try:

        if BP is not None:

            data["BP_raw"] = BP.value
            data["FP_raw"] = FP.value
            data["CR_raw"] = CR.value
            data["BC_raw"] = BC.value

        if MR is not None:

            data["MR_raw"] = MR.value

        if BAT is not None:

            data["Battery_raw"] = BAT.value
            data["Battery_voltage"] = round(
                BAT.voltage,
                2
            )

    except Exception as e:

        print("RAW Read Error:", e)

    return data


# =====================================================
# GPS READ
# =====================================================

def read_gps():

    gps_data = {

        "status": "NO FIX",
        "SAT": 0,
        "LAT": 0.0,
        "LON": 0.0,
        "ALT": 0.0

    }

    if gps is None:

        return gps_data

    try:

        timeout = time.time() + 2

        while time.time() < timeout:

            line = gps.readline().decode(
                "ascii",
                errors="ignore"
            ).strip()

            if line.startswith("$GNGGA") or line.startswith("$GPGGA"):

                msg = pynmea2.parse(line)

                gps_data["status"] = "FIX"

                gps_data["SAT"] = int(msg.num_sats)

                gps_data["LAT"] = float(msg.latitude)

                gps_data["LON"] = float(msg.longitude)

                try:
                    gps_data["ALT"] = float(msg.altitude)
                except:
                    gps_data["ALT"] = 0.0

                break

    except Exception as e:

        print("GPS Read Error:", e)

    return gps_data


# =====================================================
# LCD DISPLAY
# =====================================================

def update_lcd(data, gps_data):

    global lcd_page
    global lcd_last_time

    if lcd is None:
        return

    now = time.time()

    if now - lcd_last_time < LCD_DELAY:
        return

    lcd_last_time = now

    lcd.clear()

    # ---------------------------------------
    # PAGE 1
    # ---------------------------------------

    if lcd_page == 0:

        lcd.cursor_pos = (0, 0)
        lcd.write_string(DEVICE_ID[:20])

        lcd.cursor_pos = (1, 0)
        lcd.write_string(
            f"BP:{data['BP_raw']}"
        )

        lcd.cursor_pos = (1, 10)
        lcd.write_string(
            f"FP:{data['FP_raw']}"
        )

        lcd.cursor_pos = (2, 0)
        lcd.write_string(
            f"CR:{data['CR_raw']}"
        )

        lcd.cursor_pos = (2, 10)
        lcd.write_string(
            f"BC:{data['BC_raw']}"
        )

        lcd.cursor_pos = (3, 0)
        lcd.write_string("PRESSURE RAW")

    # ---------------------------------------
    # PAGE 2
    # ---------------------------------------

    elif lcd_page == 1:

        lcd.cursor_pos = (0, 0)
        lcd.write_string(DEVICE_ID[:20])

        lcd.cursor_pos = (1, 0)
        lcd.write_string(
            f"MR:{data['MR_raw']}"
        )

        lcd.cursor_pos = (2, 0)
        lcd.write_string(
            f"BAT:{data['Battery_voltage']:.2f}V"
        )

        lcd.cursor_pos = (3, 0)

        if ADS048_STATUS == "Connected" and ADS049_STATUS == "Connected":

            lcd.write_string("ADS: OK")

        else:

            lcd.write_string("ADS: FAIL")

    # ---------------------------------------
    # PAGE 3
    # ---------------------------------------

    elif lcd_page == 2:

        lcd.cursor_pos = (0, 0)
        lcd.write_string(DEVICE_ID[:20])

        lcd.cursor_pos = (1, 0)
        lcd.write_string(
            f"SAT:{gps_data['SAT']}"
        )

        lcd.cursor_pos = (1, 10)
        lcd.write_string(
            gps_data["status"]
        )

        lcd.cursor_pos = (2, 0)
        lcd.write_string(
            f"LAT:{gps_data['LAT']:.4f}"
        )

        lcd.cursor_pos = (3, 0)
        lcd.write_string(
            f"LON:{gps_data['LON']:.4f}"
        )

    # ---------------------------------------
    # PAGE 4
    # ---------------------------------------

    elif lcd_page == 3:

        lcd.cursor_pos = (0, 0)
        lcd.write_string("GPS ALTITUDE")

        lcd.cursor_pos = (1, 0)
        lcd.write_string(
            f"ALT:{gps_data['ALT']:.1f}m"
        )

        lcd.cursor_pos = (2, 0)
        lcd.write_string(
            time.strftime("%d-%m-%Y")
        )

        lcd.cursor_pos = (3, 0)
        lcd.write_string(
            time.strftime("%H:%M:%S")
        )

    lcd_page += 1

    if lcd_page > 3:

        lcd_page = 0
        # =====================================================
# DATABASE INSERT
# =====================================================

def insert_database(data, gps_data, timestamp):

    try:

        cursor.execute("""

        INSERT INTO brake_pressure_log
        (

            device_id,

            BP_raw,
            FP_raw,
            CR_raw,
            BC_raw,

            MR_raw,

            Battery_raw,
            Battery_voltage,

            timestamp,

            uploaded

        )

        VALUES
        (
            ?,?,?,?,?,?,?,?,?,
            0
        )

        """,

        (

            DEVICE_ID,

            data["BP_raw"],
            data["FP_raw"],
            data["CR_raw"],
            data["BC_raw"],

            data["MR_raw"],

            data["Battery_raw"],
            data["Battery_voltage"],

            timestamp

        ))

        conn.commit()

        print("✅ Data inserted into SQLite")

    except Exception as e:

        print("Database Insert Error :", e)


# =====================================================
# RAW CHANGE DETECTION
# =====================================================

last_raw = None


def check_raw_change(data):

    global last_raw

    current = [

        data["BP_raw"],
        data["FP_raw"],
        data["CR_raw"],
        data["BC_raw"],
        data["MR_raw"]

    ]

    if last_raw is None:

        last_raw = current

        return True

    diff = [

        abs(current[i] - last_raw[i])

        for i in range(5)

    ]

    print("RAW Difference :", diff)

    if any(

        value >= RAW_THRESHOLD

        for value in diff

    ):

        last_raw = current

        return True

    return False


# =====================================================
# DISPLAY CONSOLE
# =====================================================

def print_console(data, gps_data, timestamp):

    print()

    print("=" * 70)

    print(f"Device ID : {DEVICE_ID}")

    print()

    print(

        f"BP : {data['BP_raw']}    "
        f"FP : {data['FP_raw']}"

    )

    print(

        f"CR : {data['CR_raw']}    "
        f"BC : {data['BC_raw']}"

    )

    print(

        f"MR : {data['MR_raw']}"

    )

    print()

    print(

        f"Battery RAW : {data['Battery_raw']}"

    )

    print(

        f"Battery Voltage : {data['Battery_voltage']:.2f} V"

    )

    print()

    print(

        f"GPS Status : {gps_data['status']}"

    )

    print(

        f"SAT : {gps_data['SAT']}"

    )

    print(

        f"LAT : {gps_data['LAT']:.6f}"

    )

    print(

        f"LON : {gps_data['LON']:.6f}"

    )

    print(

        f"ALT : {gps_data['ALT']:.2f} m"

    )

    print()

    print(

        f"ADS1115 0x48 : {ADS048_STATUS}"

    )

    print(

        f"ADS1115 0x49 : {ADS049_STATUS}"

    )

    print()

    print(

        f"Timestamp : {timestamp}"

    )

    print("=" * 70)
    # =====================================================
# MAIN PROGRAM
# =====================================================

print()
print("============================================================")
print("   BRAKE BINDING MONITORING SYSTEM")
print("============================================================")
print("Device ID :", DEVICE_ID)
print("System Started Successfully...")
print("Press CTRL+C to Stop")
print("============================================================")
print()


try:

    while True:

        # -----------------------------------------
        # Read ADS1115 Sensors
        # -----------------------------------------

        data = read_raw_values()

        # -----------------------------------------
        # Read GPS
        # -----------------------------------------

        gps_data = read_gps()

        # -----------------------------------------
        # Current Timestamp
        # -----------------------------------------

        timestamp = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # -----------------------------------------
        # Print Console
        # -----------------------------------------

        print_console(
            data,
            gps_data,
            timestamp
        )

        # -----------------------------------------
        # Update LCD
        # -----------------------------------------

        update_lcd(
            data,
            gps_data
        )

        # -----------------------------------------
        # RAW Change Detection
        # -----------------------------------------

        if check_raw_change(data):

            insert_database(
                data,
                gps_data,
                timestamp
            )

            print()
            print("✅ RAW Changed")
            print("✅ Data Stored Successfully")
            print()

        else:

            print()
            print("⏭ No Significant RAW Change")
            print("SQLite Insert Skipped")
            print()

        # -----------------------------------------
        # Delay
        # -----------------------------------------

        time.sleep(
            READ_INTERVAL
        )


except KeyboardInterrupt:

    print()
    print("====================================================")
    print("Stopping Brake Binding Monitoring System...")
    print("====================================================")

finally:

    try:

        if lcd is not None:

            lcd.clear()

            lcd.write_string(
                "System Stopped"
            )

    except:
        pass

    try:

        if gps is not None:

            gps.close()

    except:
        pass

    conn.close()

    print("SQLite Database Closed")

    print("Program Terminated Successfully")