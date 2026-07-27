#!/usr/bin/env python3

import time
import sys
import sqlite3
import os


# =====================================================
# ENCODING
# =====================================================

sys.stdout.reconfigure(
    encoding='utf-8'
)



# =====================================================
# CONFIGURATION
# =====================================================


RAW_THRESHOLD = 326

READ_INTERVAL = 0.1



# =====================================================
# DATABASE PATH
# =====================================================


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


DB_FOLDER = os.path.join(
    BASE_DIR,
    "db"
)


if not os.path.exists(DB_FOLDER):

    os.makedirs(DB_FOLDER)



DB_PATH = os.path.join(
    DB_FOLDER,
    "test_db.db"
)




# =====================================================
# DATABASE CONNECTION
# =====================================================


conn = sqlite3.connect(

    DB_PATH,

    check_same_thread=False

)


conn.row_factory = sqlite3.Row


cursor = conn.cursor()



# =====================================================
# CREATE TABLE
# =====================================================


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


timestamp DATETIME,


uploaded INTEGER DEFAULT 0


)

""")


conn.commit()



print(
    "✅ Database Connected"
)



# =====================================================
# DEVICE ID
# =====================================================


try:


    cursor.execute(

        """
        SELECT device_id
        FROM device_config
        LIMIT 1
        """

    )


    row = cursor.fetchone()



    if row:

        DEVICE_ID = row["device_id"]

    else:

        DEVICE_ID = "UNKNOWN"



except:


    DEVICE_ID = "Raspberry4_8"



print(

    "Device ID =",

    DEVICE_ID

)



# =====================================================
# ADS1115 SETUP
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




    i2c = busio.I2C(

        board.SCL,

        board.SDA

    )



    # ==============================================
    # ADS1115 ADDRESS 0x48
    # ==============================================


    ads1 = ADS.ADS1115(

        i2c,

        address=0x48

    )


    ads1.gain = 1



    BP = AnalogIn(

        ads1,

        0

    )


    FP = AnalogIn(

        ads1,

        1

    )


    CR = AnalogIn(

        ads1,

        2

    )


    BC = AnalogIn(

        ads1,

        3

    )



    ADS048_STATUS = "Connected"




    # ==============================================
    # ADS1115 ADDRESS 0x49
    # ==============================================


    ads2 = ADS.ADS1115(

        i2c,

        address=0x49

    )


    ads2.gain = 1




    MR = AnalogIn(

        ads2,

        0

    )


    BAT = AnalogIn(

        ads2,

        1

    )



    ADS049_STATUS = "Connected"




    print(

        "✅ ADS1115 0x48 Connected"

    )


    print(

        "✅ ADS1115 0x49 Connected"

    )



except Exception as e:


    print(

        "ADS1115 Error:",

        e

    )





# =====================================================
# READ ADS1115 RAW VALUES
# =====================================================


def read_raw_values():



    data = {


        "BP_raw":0,

        "FP_raw":0,

        "CR_raw":0,

        "BC_raw":0,


        "MR_raw":0,


        "Battery_raw":0,

        "Battery_voltage":0.0


    }



    try:


        data["BP_raw"] = BP.value

        data["FP_raw"] = FP.value

        data["CR_raw"] = CR.value

        data["BC_raw"] = BC.value



        data["MR_raw"] = MR.value


        data["Battery_raw"] = BAT.value


        data["Battery_voltage"] = round(

            BAT.voltage,

            2

        )



    except Exception as e:


        print(

            "RAW Read Error:",

            e

        )



    return data




# =====================================================
# INSERT DATABASE
# =====================================================


def insert_database(data,timestamp):


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

    (?,?,?,?,?,?,?,?,?,0)

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





# =====================================================
# RAW CHANGE LOGIC
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

        abs(

            current[i]

            -

            last_raw[i]

        )

        for i in range(5)

    ]



    print(

        "RAW Difference =",

        diff

    )



    if any(

        x >= RAW_THRESHOLD

        for x in diff

    ):


        last_raw=current

        return True



    return False




# =====================================================
# MAIN LOOP
# =====================================================


print(

    "\n🚀 HAMS ADS1115 Capture Started\n"

)



while True:



    data = read_raw_values()



    timestamp=time.strftime(

        "%Y-%m-%d %H:%M:%S"

    )




    print("--------------------------------")


    print(

        "device_id =",

        DEVICE_ID

    )


    print()


    print(

        "BP_raw =",

        data["BP_raw"]

    )


    print(

        "FP_raw =",

        data["FP_raw"]

    )


    print(

        "CR_raw =",

        data["CR_raw"]

    )


    print(

        "BC_raw =",

        data["BC_raw"]

    )


    print()


    print(

        "MR_raw =",

        data["MR_raw"]

    )


    print()


    print(

        "Battery_raw =",

        data["Battery_raw"]

    )


    print(

        "Battery_voltage =",

        data["Battery_voltage"],

        "V"

    )


    print()


    print(

        "ADS1115-1 (0x48) =",

        ADS048_STATUS

    )


    print(

        "ADS1115-2 (0x49) =",

        ADS049_STATUS

    )


    print()


    print(

        "timestamp =",

        timestamp

    )


    print("--------------------------------")




    if check_raw_change(data):


        insert_database(

            data,

            timestamp

        )


        print(

            "✅ Data inserted uploaded=0"

        )


    else:


        print(

            "⏭ No significant RAW change"

        )



    print()



    time.sleep(READ_INTERVAL)