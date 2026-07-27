#!/usr/bin/env python3


# =====================================================
#                    IMPORTS
# =====================================================

import time
import os
import sys
import sqlite3
import serial
import pynmea2




# =====================================================
#                 CONFIGURATION
# =====================================================


# ---------------- GPS Configuration -----------------

GPS_PORT = "/dev/ttyAMA3"

GPS_BAUD = 38400



# ---------------- LCD Configuration -----------------

LCD_ADDRESS = 0x27



# ---------------- RAW Change Threshold -------------

RAW_THRESHOLD = 345



# ---------------- ADS1115 Status -------------------

ADS048_STATUS = "Disconnected"

ADS049_STATUS = "Disconnected"




# =====================================================
#                 DATABASE SETUP
# =====================================================


# Current Python file location

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)



# Database folder

DB_FOLDER = os.path.join(
    BASE_DIR,
    "db"
)



# Create database folder if not available

if not os.path.exists(DB_FOLDER):

    os.makedirs(DB_FOLDER)




# Database file path

DB_PATH = os.path.join(
    DB_FOLDER,
    "test_db.db"
)




# SQLite Database Connection

try:

    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )


    cursor = conn.cursor()


    print(
        "Database Connected"
    )


except Exception as e:


    print(
        "Database Connection Error:",
        e
    )


    sys.exit(1)




# =====================================================
#             CREATE TABLE IF NOT EXISTS
# =====================================================


try:


    cursor.execute(
    """

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


        GPS_status TEXT,

        SAT INTEGER,


        LAT REAL,

        LONG REAL,

        ALT REAL,


        timestamp TEXT,


        uploaded INTEGER DEFAULT 0


    )

    """
    )


    conn.commit()


    print(
        "Database Table Ready"
    )



except Exception as e:


    print(
        "Database Table Error:",
        e
    )# =====================================================
#                 DEVICE ID READING
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

        DEVICE_ID = row[0]


    else:

        DEVICE_ID = "Raspberry4_8"



except Exception as e:


    print(
        "Device ID Read Error:",
        e
    )


    DEVICE_ID = "Raspberry4_8"



print(
    "Device ID:",
    DEVICE_ID
)# =====================================================
#                  ADS1115 SETUP
# =====================================================


# Default variables

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




    # Raspberry Pi I2C Bus

    i2c = busio.I2C(

        board.SCL,

        board.SDA

    )




    # =================================================
    #              ADS1115 - ADDRESS 0x48
    # =================================================


    ads1 = ADS.ADS1115(

        i2c,

        address=0x48

    )


    ads1.gain = 1




    # Channel Mapping

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



    ADS048_STATUS = "Connected"





    # =================================================
    #              ADS1115 - ADDRESS 0x49
    # =================================================


    ads2 = ADS.ADS1115(

        i2c,

        address=0x49

    )


    ads2.gain = 1





    # Channel Mapping

    MR = AnalogIn(

        ads2,

        ADS.P0

    )



    BAT = AnalogIn(

        ads2,

        ADS.P1

    )



    ADS049_STATUS = "Connected"




    print(
        "ADS1115 0x48 Connected"
    )


    print(
        "ADS1115 0x49 Connected"
    )



except Exception as e:


    print(
        "ADS1115 Error:",
        e
    )

    ADS048_STATUS = "Disconnected"

    ADS049_STATUS = "Disconnected"
    # =====================================================
#              ADS1115 RAW READ FUNCTION
# =====================================================


def read_ads1115():


    sensor_data = {


        "BP_raw": 0,

        "FP_raw": 0,

        "CR_raw": 0,

        "BC_raw": 0,


        "MR_raw": 0,


        "Battery_raw": 0,


        "Battery_voltage": 0.0


    }




    try:


        # =============================================
        # ADS1115 0x48 Reading
        # =============================================


        if BP is not None:


            sensor_data["BP_raw"] = BP.value


            sensor_data["FP_raw"] = FP.value


            sensor_data["CR_raw"] = CR.value


            sensor_data["BC_raw"] = BC.value





        # =============================================
        # ADS1115 0x49 Reading
        # =============================================


        if MR is not None:


            sensor_data["MR_raw"] = MR.value



            sensor_data["Battery_raw"] = BAT.value



            sensor_data["Battery_voltage"] = round(

                BAT.voltage,

                2

            )




    except Exception as e:


        print(

            "ADS1115 Reading Error:",

            e

        )



    return sensor_data
# =====================================================
#                    GPS SETUP
# =====================================================


gps = None



try:


    gps = serial.Serial(

        GPS_PORT,

        GPS_BAUD,

        timeout=1

    )


    print(
        "GPS Connected"
    )



except Exception as e:


    print(

        "GPS Connection Error:",

        e

    )


    gps = None
    # =====================================================
#                  GPS READ FUNCTION
# =====================================================


def read_gps():


    gps_data = {


        "GPS_status": "NO FIX",

        "SAT": 0,

        "LAT": 0.0,

        "LONG": 0.0,

        "ALT": 0.0


    }



    # If GPS not connected

    if gps is None:


        return gps_data




    try:


        # Read multiple NMEA lines

        for i in range(20):


            line = gps.readline().decode(

                "ascii",

                errors="ignore"

            ).strip()



            if not line:


                continue




            # Only GGA sentence required

            if (

                line.startswith("$GNGGA")

                or

                line.startswith("$GPGGA")

            ):



                try:


                    msg = pynmea2.parse(line)




                    # Satellite count

                    if msg.num_sats:


                        gps_data["SAT"] = int(

                            msg.num_sats

                        )





                    # GPS Fix Check

                    if msg.gps_qual > 0:



                        gps_data["GPS_status"] = "FIX"



                        gps_data["LAT"] = round(

                            msg.latitude,

                            6

                        )



                        gps_data["LONG"] = round(

                            msg.longitude,

                            6

                        )



                        gps_data["ALT"] = round(

                            float(msg.altitude),

                            2

                        )



                    else:


                        gps_data["GPS_status"] = "NO FIX"



                except Exception as e:


                    print(

                        "GPS Parse Error:",

                        e

                    )



                break




    except Exception as e:


        print(

            "GPS Reading Error:",

            e

        )



    return gps_data
    # =====================================================
#              COMPLETE DATA FUNCTION
# =====================================================


def read_all_data():


    # Read ADS1115

    sensor = read_ads1115()



    # Read GPS

    gps_data = read_gps()



    # Current timestamp

    timestamp = time.strftime(

        "%Y-%m-%d %H:%M:%S"

    )




    # Create complete data packet

    data = {


        # -----------------------------
        # Device Information
        # -----------------------------

        "device_id": DEVICE_ID,



        # -----------------------------
        # ADS1115 RAW VALUES
        # -----------------------------

        "BP_raw":

            sensor["BP_raw"],



        "FP_raw":

            sensor["FP_raw"],



        "CR_raw":

            sensor["CR_raw"],



        "BC_raw":

            sensor["BC_raw"],



        "MR_raw":

            sensor["MR_raw"],




        # -----------------------------
        # Battery
        # -----------------------------

        "Battery_raw":

            sensor["Battery_raw"],



        "Battery_voltage":

            sensor["Battery_voltage"],




        # -----------------------------
        # GPS
        # -----------------------------

        "GPS_status":

            gps_data["GPS_status"],



        "SAT":

            gps_data["SAT"],



        "LAT":

            gps_data["LAT"],



        "LONG":

            gps_data["LONG"],



        "ALT":

            gps_data["ALT"],




        # -----------------------------
        # Time
        # -----------------------------

        "timestamp":

            timestamp


    }



    return data
data = read_all_data()

print(data)# =====================================================
#                    LCD SETUP
# =====================================================


lcd = None



try:


    from RPLCD.i2c import CharLCD



    lcd = CharLCD(

        'PCF8574',

        LCD_ADDRESS,

        cols=20,

        rows=4,

        charmap='A02'

    )



    lcd.clear()



    lcd.write_string(

        "HAMS Starting..."

    )



    print(

        "LCD Connected"

    )



except Exception as e:


    print(

        "LCD Error:",

        e

    )


    lcd = None
    # =====================================================
#              LCD DISPLAY FUNCTION
# =====================================================


def lcd_display(data):


    if lcd is None:


        return




    try:



        lcd.clear()



        # -------------------------------
        # Line 1 : Device ID
        # -------------------------------

        lcd.cursor_pos = (

            0,

            0

        )


        lcd.write_string(

            "HAMS "

            + str(data["device_id"])[:15]

        )




        # -------------------------------
        # Line 2 : BP FP
        # -------------------------------

        lcd.cursor_pos = (

            1,

            0

        )


        lcd.write_string(

            "BP:{} FP:{}".format(

                data["BP_raw"],

                data["FP_raw"]

            )

        )




        # -------------------------------
        # Line 3 : CR BC
        # -------------------------------

        lcd.cursor_pos = (

            2,

            0

        )


        lcd.write_string(

            "CR:{} BC:{}".format(

                data["CR_raw"],

                data["BC_raw"]

            )

        )




        # -------------------------------
        # Line 4 : Battery GPS
        # -------------------------------

        lcd.cursor_pos = (

            3,

            0

        )


        lcd.write_string(

            "BAT:{} GPS:{}".format(

                data["Battery_raw"],

                data["SAT"]

            )

        )



    except Exception as e:


        print(

            "LCD Display Error:",

            e

        )# =====================================================
#                  PRINT DATA FUNCTION
# =====================================================


def print_data(data):


    print("\n--------------------------------")


    print(
        "device_id =",
        data["device_id"]
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
        "GPS_status =",
        data["GPS_status"]
    )


    print(
        "SAT =",
        data["SAT"]
    )


    print(
        "LAT =",
        data["LAT"]
    )


    print(
        "LONG =",
        data["LONG"]
    )


    print(
        "ALT =",
        data["ALT"]
    )



    print()



    print(
        "timestamp =",
        data["timestamp"]
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


    print("--------------------------------")
    # =====================================================
#              DATABASE INSERT FUNCTION
# =====================================================


def insert_database(data):


    try:


        cursor.execute(

        """

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

        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)


        """,


        (

        data["device_id"],


        data["BP_raw"],

        data["FP_raw"],

        data["CR_raw"],

        data["BC_raw"],



        data["MR_raw"],



        data["Battery_raw"],


        data["Battery_voltage"],



        data["GPS_status"],


        data["SAT"],



        data["LAT"],


        data["LONG"],


        data["ALT"],



        data["timestamp"],



        0

        )


        )



        conn.commit()



        print(

            "✅ Data inserted into database uploaded=0"

        )



    except Exception as e:



        print(

            "Database Insert Error:",

            e

        )
        # =====================================================
#              RAW CHANGE DETECTION
# =====================================================


last_raw_data = None





def check_raw_change(data):


    global last_raw_data



    # Values to compare

    current_raw = [


        data["BP_raw"],


        data["FP_raw"],


        data["CR_raw"],


        data["BC_raw"],


        data["MR_raw"]


    ]




    # =============================================
    # First Reading
    # =============================================


    if last_raw_data is None:


        last_raw_data = current_raw


        return True




    # =============================================
    # Calculate Difference
    # =============================================


    difference = [


        abs(

            current_raw[i]

            -

            last_raw_data[i]

        )


        for i in range(5)


    ]



    print(

        "RAW Difference =",

        difference

    )





    # =============================================
    # Check Threshold
    # =============================================


    if any(

        value >= RAW_THRESHOLD

        for value in difference

    ):



        last_raw_data = current_raw


        return True




    else:


        return False
