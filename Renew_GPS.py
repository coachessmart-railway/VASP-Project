#!/usr/bin/env python3


# =====================================================
#                 IMPORTS
# =====================================================

import time
import os
import sys
import sqlite3
import serial
import pynmea2



# =====================================================
#                 GPS CONFIGURATION
# =====================================================


GPS_PORT = "/dev/ttyAMA3"

GPS_BAUD = 38400



# =====================================================
#                 DATABASE CONFIG
# =====================================================


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


DB_PATH = os.path.join(
    BASE_DIR,
    "db",
    "test_db.db"
)



# =====================================================
#                 DATABASE CONNECTION
# =====================================================


try:

    conn = sqlite3.connect(
        DB_PATH
    )

    cursor = conn.cursor()


    print(
        "✅ Database Connected"
    )


except Exception as e:


    print(
        "Database Error:",
        e
    )

    sys.exit(1)




# =====================================================
#                 DEVICE ID
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

        DEVICE_ID = "UNKNOWN"



except Exception as e:


    print(
        "Device ID Error:",
        e
    )


    DEVICE_ID = "Raspberry4_8"



print(
    "Device ID =",
    DEVICE_ID
)




# =====================================================
#                 GPS CONNECTION
# =====================================================


gps = None



try:


    gps = serial.Serial(

        GPS_PORT,

        GPS_BAUD,

        timeout=1

    )


    print(
        "✅ GPS Connected"
    )



except Exception as e:


    print(
        "❌ GPS Connection Error:",
        e
    )


    gps = None




# =====================================================
#                 GPS READ FUNCTION
# =====================================================


def read_gps():


    gps_data = {


        "GPS_status":"NO FIX",

        "SAT":0,

        "LAT":0.0,

        "LONG":0.0,

        "ALT":0.0


    }



    if gps is None:


        return gps_data




    try:


        for i in range(20):


            line = gps.readline().decode(

                "ascii",

                errors="ignore"

            ).strip()



            if not line:


                continue




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



                    # Fix status

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
#                 MAIN LOOP
# =====================================================


print(

    "\n🚀 GPS Capture Started\n"

)



try:


    while True:



        gps_data = read_gps()



        timestamp = time.strftime(

            "%Y-%m-%d %H:%M:%S"

        )



        print("--------------------------------")


        print(

            "device_id =",

            DEVICE_ID

        )


        print()


        print(

            "GPS_status =",

            gps_data["GPS_status"]

        )


        print(

            "SAT =",

            gps_data["SAT"]

        )


        print(

            "LAT =",

            gps_data["LAT"]

        )


        print(

            "LONG =",

            gps_data["LONG"]

        )


        print(

            "ALT =",

            gps_data["ALT"],

            "m"

        )


        print()


        print(

            "timestamp =",

            timestamp

        )


        print("--------------------------------\n")



        time.sleep(1)




except KeyboardInterrupt:


    print(

        "\nStopping GPS Capture"

    )



finally:



    if gps:


        gps.close()



    conn.close()



    print(

        "Closed Successfully"

    )