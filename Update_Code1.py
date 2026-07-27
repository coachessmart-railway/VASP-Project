#!/usr/bin/env python3

import time
import os
import serial
import sqlite3


# ================= CONFIG =================

READ_INTERVAL = 1

RAW_THRESHOLD = 348

ADS1_ADDRESS = 0x48
ADS2_ADDRESS = 0x49

GPS_PORT = "/dev/ttyAMA3"
GPS_BAUD = 38400

LCD_ADDRESS = 0x27


# ================= DATABASE =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(
    BASE_DIR,
    "db",
    "hams_data.db"
)


os.makedirs(
    os.path.dirname(DB_PATH),
    exist_ok=True
)


conn = sqlite3.connect(
    DB_PATH,
    check_same_thread=False
)

cursor = conn.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS brake_pressure_log
(
id INTEGER PRIMARY KEY AUTOINCREMENT,

BP_raw INTEGER,
FP_raw INTEGER,
CR_raw INTEGER,
BC_raw INTEGER,

MR_raw INTEGER,
Battery_raw INTEGER,

GPS TEXT,

timestamp DATETIME,

uploaded INTEGER DEFAULT 0

)
""")


conn.commit()



# ================= ADS1115 =================

ADS_AVAILABLE = True


try:

    import board
    import busio

    import adafruit_ads1x15.ads1115 as ADS

    from adafruit_ads1x15.analog_in import AnalogIn


    i2c = busio.I2C(
        board.SCL,
        board.SDA
    )


    ads1 = ADS.ADS1115(
        i2c,
        address=ADS1_ADDRESS
    )


    ads2 = ADS.ADS1115(
        i2c,
        address=ADS2_ADDRESS
    )


    ads1.gain = 1
    ads2.gain = 1


    BP = AnalogIn(
        ads1,
        ADS.P0
    )

    FP = AnalogIn(
        ads1,
        ADS.P1
    )

    CR = AnalogIn(
        ads1,
        ADS.P2
    )

    BC = AnalogIn(
        ads1,
        ADS.P3
    )


    MR = AnalogIn(
        ads2,
        ADS.P0
    )


    BATTERY = AnalogIn(
        ads2,
        ADS.P1
    )


    print("ADS1115 Connected")


except Exception as e:

    ADS_AVAILABLE = False

    print(
        "ADS1115 Error:",
        e
    )




# ================= LCD =================


LCD_AVAILABLE = True


try:

    from RPLCD.i2c import CharLCD


    lcd = CharLCD(
        "PCF8574",
        LCD_ADDRESS,
        cols=20,
        rows=4
    )


    lcd.clear()

    print("LCD Connected")


except Exception as e:

    LCD_AVAILABLE = False

    print(
        "LCD Error:",
        e
    )




# ================= GPS =================


GPS_AVAILABLE = True


try:

    gps = serial.Serial(
        GPS_PORT,
        GPS_BAUD,
        timeout=1
    )


    print("GPS Connected")


except Exception as e:

    GPS_AVAILABLE = False

    print(
        "GPS Error:",
        e
    )




# ================= FUNCTIONS =================


def read_ads1115():


    if ADS_AVAILABLE:


        return (

            BP.value,

            FP.value,

            CR.value,

            BC.value,

            MR.value,

            BATTERY.value

        )


    return (

        0,
        0,
        0,
        0,
        0,
        0

    )





def read_gps():


    if GPS_AVAILABLE:

        try:

            data = gps.readline()

            return data.decode(
                errors="ignore"
            ).strip()


        except:

            return "GPS ERROR"


    return "GPS NOT CONNECTED"





def lcd_print(values):


    if LCD_AVAILABLE:


        lcd.clear()


        lcd.write_string(

            f"BP:{values[0]} FP:{values[1]}"

        )


        lcd.cursor_pos=(1,0)


        lcd.write_string(

            f"CR:{values[2]} BC:{values[3]}"

        )


        lcd.cursor_pos=(2,0)


        lcd.write_string(

            f"MR:{values[4]} BAT:{values[5]}"

        )


        lcd.cursor_pos=(3,0)


        lcd.write_string(

            "RAW DATA"

        )





# ================= MAIN =================


print("\nHAMS RAW CAPTURE STARTED\n")


last_raw = None



while True:


    current_raw = read_ads1115()


    gps_data = read_gps()


    timestamp = time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )



    print("--------------------------------")

    print(
        "Time:",
        timestamp
    )


    print(
        "ADS1115-1 (0x48)"
    )


    print(
        "BP Raw:",
        current_raw[0]
    )

    print(
        "FP Raw:",
        current_raw[1]
    )

    print(
        "CR Raw:",
        current_raw[2]
    )

    print(
        "BC Raw:",
        current_raw[3]
    )


    print("----------------")


    print(
        "ADS1115-2 (0x49)"
    )


    print(
        "MR Raw:",
        current_raw[4]
    )


    print(
        "Battery Raw:",
        current_raw[5]
    )


    print(
        "GPS:",
        gps_data
    )


    print("--------------------------------")



    lcd_print(
        current_raw
    )



    # ========= CHANGE CHECK =========


    store_data = False



    if last_raw is None:

        store_data = True



    else:


        pressure_diff = [

            abs(
                current_raw[i]
                -
                last_raw[i]
            )

            for i in range(4)

        ]


        if any(

            diff >= RAW_THRESHOLD

            for diff in pressure_diff

        ):

            store_data = True




    # ========= DATABASE INSERT =========


    if store_data:


        cursor.execute("""

        INSERT INTO brake_pressure_log

        (
        BP_raw,
        FP_raw,
        CR_raw,
        BC_raw,

        MR_raw,
        Battery_raw,

        GPS,
        timestamp

        )

        VALUES(?,?,?,?,?,?,?,?)

        """,

        (

        current_raw[0],
        current_raw[1],
        current_raw[2],
        current_raw[3],

        current_raw[4],
        current_raw[5],

        gps_data,
        timestamp

        ))



        conn.commit()



        last_raw = current_raw



        print(
            "✅ Stored in DB"
        )



    else:


        print(
            "⏭ No change >348"
        )



    time.sleep(
        READ_INTERVAL
    )