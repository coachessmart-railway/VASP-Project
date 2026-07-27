#!/usr/bin/env python3

import time
import os
import sqlite3
import serial
import pynmea2


# ================= CONFIG =================

GPS_PORT = "/dev/ttyAMA3"
GPS_BAUD = 38400

LCD_ADDRESS = 0x27

RAW_THRESHOLD = 345

ADS048_STATUS = "Disconnected"
ADS049_STATUS = "Disconnected"


# ================= DATABASE =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(
    BASE_DIR,
    "db",
    "test_db.db"
)


conn = sqlite3.connect(
    DB_PATH,
    check_same_thread=False
)

cursor = conn.cursor()



# ================= DEVICE ID =================

cursor.execute(
    "SELECT device_id FROM device_config LIMIT 1"
)

row = cursor.fetchone()

if row:
    DEVICE_ID = row[0]
else:
    DEVICE_ID = "UNKNOWN"



# ================= ADS1115 =================

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
        address=0x48
    )

    ads2 = ADS.ADS1115(
        i2c,
        address=0x49
    )


    ads1.gain = 1
    ads2.gain = 1


    BP = AnalogIn(ads1,0)
    FP = AnalogIn(ads1,1)
    CR = AnalogIn(ads1,2)
    BC = AnalogIn(ads1,3)


    MR = AnalogIn(ads2,0)
    BAT = AnalogIn(ads2,1)


    ADS048_STATUS="Connected"
    ADS049_STATUS="Connected"


except Exception as e:

    print("ADS Error:",e)



# ================= GPS =================


try:

    gps = serial.Serial(
        GPS_PORT,
        GPS_BAUD,
        timeout=1
    )

except Exception as e:

    gps=None
    print("GPS Error:",e)




# ================= READ SENSOR =================


def read_sensor():

    try:

        return {

            "BP_raw":BP.value,
            "FP_raw":FP.value,
            "CR_raw":CR.value,
            "BC_raw":BC.value,

            "MR_raw":MR.value,

            "Battery_raw":BAT.value,

            "Battery_voltage":
                round(BAT.voltage,2)

        }


    except Exception as e:

        print(e)

        return {

            "BP_raw":0,
            "FP_raw":0,
            "CR_raw":0,
            "BC_raw":0,
            "MR_raw":0,
            "Battery_raw":0,
            "Battery_voltage":0

        }



# ================= GPS READ =================


def read_gps():

    gps_data={
        "status":"NO FIX",
        "sat":0,
        "lat":0,
        "long":0,
        "alt":0
    }


    if gps is None:
        return gps_data


    try:

        line = gps.readline().decode(
            errors="ignore"
        )


        if "$GNGGA" in line:

            msg=pynmea2.parse(line)


            if int(msg.num_sats)>0:

                gps_data["status"]="FIX"
                gps_data["sat"]=int(msg.num_sats)
                gps_data["lat"]=msg.latitude
                gps_data["long"]=msg.longitude
                gps_data["alt"]=msg.altitude


    except Exception as e:
        print("GPS Error:",e)


    return gps_data




# ================= MAIN =================


print("\n🚀 HAMS Capture Started\n")


last_data=None



while True:


    sensor=read_sensor()

    gps_data=read_gps()


    timestamp=time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    print("--------------------------------")

    print("device_id =",DEVICE_ID)


    print()

    print("BP_raw =",sensor["BP_raw"])

    print("FP_raw =",sensor["FP_raw"])

    print("CR_raw =",sensor["CR_raw"])

    print("BC_raw =",sensor["BC_raw"])


    print()

    print("MR_raw =",sensor["MR_raw"])


    print()

    print(
        "Battery_raw =",
        sensor["Battery_raw"]
    )


    print(
        "Battery_voltage =",
        sensor["Battery_voltage"],
        "V"
    )


    print()

    print(
        "GPS_status =",
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


    print()

    print(
        "timestamp =",
        timestamp
    )


    print()

    print(
        "ADS1115-1 =",
        ADS048_STATUS
    )

    print(
        "ADS1115-2 =",
        ADS049_STATUS
    )



    upload=False


    current_compare=[

        sensor["BP_raw"],
        sensor["FP_raw"],
        sensor["CR_raw"],
        sensor["BC_raw"],
        sensor["MR_raw"]

    ]



    if last_data is None:

        upload=True


    else:

        diff=[

        abs(
        current_compare[i]-last_data[i]
        )

        for i in range(5)

        ]


        if any(
            d>=RAW_THRESHOLD
            for d in diff
        ):

            upload=True




    if upload:


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

        GPS_status,

        SAT,

        LAT,

        LONG,

        ALT,

        timestamp,

        uploaded

        )

        VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)

        """,

        (

        DEVICE_ID,

        sensor["BP_raw"],
        sensor["FP_raw"],
        sensor["CR_raw"],
        sensor["BC_raw"],

        sensor["MR_raw"],

        sensor["Battery_raw"],

        sensor["Battery_voltage"],

        gps_data["status"],

        gps_data["sat"],

        gps_data["lat"],

        gps_data["long"],

        gps_data["alt"],

        timestamp

        ))


        conn.commit()


        last_data=current_compare


        print(
            "\n✅ Data inserted into DB uploaded=0"
        )


    else:

        print(
            "\n⏭ No significant change"
        )


    print("--------------------------------\n")


    time.sleep(1)