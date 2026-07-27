#!/usr/bin/env python3

import time
import os
import sqlite3
import serial
import pynmea2


# ================= CONFIG =================

DEVICE_ID = "Raspberry4_8"

RAW_THRESHOLD = 348

READ_INTERVAL = 1


# ADS1115 ADDRESS

ADS1_ADDRESS = 0x48
ADS2_ADDRESS = 0x49


# LCD

LCD_ADDRESS = 0x27


# GPS

GPS_PORT = "/dev/ttyAMA3"
GPS_BAUD = 38400



# ================= DATABASE =================


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


DB_PATH = os.path.join(
    BASE_DIR,
    "db",
    "test_db.db"
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

device_id TEXT,

BP_raw INTEGER,
FP_raw INTEGER,
CR_raw INTEGER,
BC_raw INTEGER,

MR_raw INTEGER,

Battery_raw INTEGER,


GPS_status TEXT,

SAT INTEGER,

LAT REAL,

LONG REAL,

ALT REAL,


timestamp TEXT,


uploaded INTEGER DEFAULT 0

)
""")


conn.commit()



# ================= ADS1115 =================


ADS048_STATUS = "Disconnected"
ADS049_STATUS = "Disconnected"


try:

    import board
    import busio

    import adafruit_ads1x15.ads1115 as ADS

    from adafruit_ads1x15.analog_in import AnalogIn


    i2c = busio.I2C(
        board.SCL,
        board.SDA
    )


    ads048 = ADS.ADS1115(
        i2c,
        address=ADS1_ADDRESS
    )


    ads049 = ADS.ADS1115(
        i2c,
        address=ADS2_ADDRESS
    )


    ads048.gain = 1
    ads049.gain = 1



    # ADS1115 0x48

    BP = AnalogIn(
        ads048,
        0
    )

    FP = AnalogIn(
        ads048,
        1
    )

    CR = AnalogIn(
        ads048,
        2
    )

    BC = AnalogIn(
        ads048,
        3
    )


    ADS048_STATUS = "Connected"



    # ADS1115 0x49

    MR = AnalogIn(
        ads049,
        0
    )


    BATTERY = AnalogIn(
        ads049,
        1
    )


    ADS049_STATUS = "Connected"



    print(
        "✅ ADS1115 sensor detected and initialized."
    )



except Exception as e:

    print(
        "ADS1115 Error:",
        e
    )



# ================= LCD =================


LCD_STATUS = "Disconnected"


try:

    from RPLCD.i2c import CharLCD


    lcd = CharLCD(
        "PCF8574",
        LCD_ADDRESS,
        cols=20,
        rows=4
    )


    lcd.clear()


    LCD_STATUS = "Connected"


    print(
        "LCD Connected"
    )


except Exception as e:

    lcd = None

    print(
        "LCD Error:",
        e
    )



# ================= GPS =================


GPS_STATUS = "Disconnected"


try:

    gps = serial.Serial(
        GPS_PORT,
        GPS_BAUD,
        timeout=1
    )


    GPS_STATUS = "Connected"


    print(
        "GPS Connected"
    )


except Exception as e:

    gps = None

    print(
        "GPS Error:",
        e
    )




# ================= FUNCTIONS =================


def read_adc():


    try:

        return (

            BP.value,

            FP.value,

            CR.value,

            BC.value,

            MR.value,

            BATTERY.value

        )


    except:

        return (

            0,
            0,
            0,
            0,
            0,
            0

        )





def read_gps():


    data = {

        "status":"NO FIX",

        "sat":0,

        "lat":0,

        "long":0,

        "alt":0

    }



    if gps is None:

        return data



    try:


        while gps.in_waiting:


            line = gps.readline().decode(
                errors="ignore"
            )


            if line.startswith("$GNGGA"):


                msg = pynmea2.parse(
                    line
                )


                data["status"] = "OK"


                data["sat"] = int(
                    msg.num_sats
                )


                data["lat"] = msg.latitude


                data["long"] = msg.longitude


                data["alt"] = float(
                    msg.altitude
                )


                break



    except:

        pass



    return data





def lcd_display(values,gps_data):


    if lcd is None:

        return



    pages = [

        [
        f"BP:{values[0]} FP:{values[1]}",
        f"CR:{values[2]} BC:{values[3]}",
        "RAW PRESSURE",
        DEVICE_ID
        ],


        [
        f"MR:{values[4]}",
        f"BAT:{values[5]}",
        f"SAT:{gps_data['sat']}",
        "GPS OK"
        ],


        [
        f"LAT:{gps_data['lat']}",
        f"LON:{gps_data['long']}",
        f"ALT:{gps_data['alt']}",
        "GPS DATA"
        ]

    ]



    for page in pages:


        lcd.clear()


        for row,text in enumerate(page):


            lcd.cursor_pos = (
                row,
                0
            )


            lcd.write_string(
                str(text)[:20]
            )


        time.sleep(2)




# ================= MAIN =================


print()
print("🚀 Capture system started...")
print()



last_raw = None



while True:



    adc = read_adc()


    gps_data = read_gps()


    timestamp = time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )



    print("--------------------------------")

    print(
        "device_id =",
        DEVICE_ID
    )


    print(
        "BP_raw =",
        adc[0],
        "FP_raw =",
        adc[1],
        "CR_raw =",
        adc[2],
        "BC_raw =",
        adc[3]
    )


    print(
        "MR_raw =",
        adc[4],
        "Battery_raw =",
        adc[5]
    )


    print(
        "GPS_connection =",
        gps_data["status"]
    )


    print(
        "SAT =",
        gps_data["sat"]
    )


    print(
        "LAT =",
        gps_data["lat"]
    )


    print(
        "LONG =",
        gps_data["long"]
    )


    print(
        "ALT =",
        gps_data["alt"]
    )


    print(
        "timestamp =",
        timestamp
    )


    print(
        "ADS1115_status =",
        ADS048_STATUS
    )


    print(
        "ADS_049_status =",
        ADS049_STATUS
    )



    # LCD

    lcd_display(
        adc,
        gps_data
    )



    # ============== CHANGE LOGIC ==============


    save = False



    if last_raw is None:


        save = True



    else:


        difference = [

            abs(
                adc[i]-last_raw[i]
            )

            for i in range(4)

        ]


        if any(
            x >= RAW_THRESHOLD
            for x in difference
        ):

            save = True




    # ============== DATABASE INSERT ==============


    if save:


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

        GPS_status,

        SAT,

        LAT,

        LONG,

        ALT,

        timestamp,

        uploaded

        )

        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0)

        """,

        (

        DEVICE_ID,

        adc[0],
        adc[1],
        adc[2],
        adc[3],

        adc[4],

        adc[5],

        gps_data["status"],

        gps_data["sat"],

        gps_data["lat"],

        gps_data["long"],

        gps_data["alt"],

        timestamp

        ))



        conn.commit()



        last_raw = adc



        print(
            "✅ Data inserted into DB at",
            timestamp
        )



    else:


        print(
            "⏭ No significant change >348"
        )



    print("--------------------------------")


    time.sleep(
        READ_INTERVAL
    )