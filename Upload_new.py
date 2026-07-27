#!/usr/bin/env python3


# =====================================================
# IMPORTS
# =====================================================

import os
import time
import sqlite3
import json
import ssl
import paho.mqtt.client as mqtt




# =====================================================
# PATH CONFIGURATION
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
# AWS CERTIFICATE PATH
# =====================================================


CA_PATH = os.path.join(
    BASE_DIR,
    "certs",
    "AmazonRootCA1.pem"
)


CERT_PATH = os.path.join(
    BASE_DIR,
    "certs",
    "certificate.pem.crt"
)


KEY_PATH = os.path.join(
    BASE_DIR,
    "certs",
    "private.pem.key"
)





# =====================================================
# AWS MQTT CONFIGURATION
# =====================================================


MQTT_ENDPOINT = (
    "a1vddjuckiz90j-ats.iot.ap-south-1.amazonaws.com"
)


CLIENT_ID = (
    "Raspberrypi_4A"
)


TOPIC = (
    CLIENT_ID + "/data"
)





# =====================================================
# DATABASE CONNECTION
# =====================================================


try:


    conn = sqlite3.connect(

        DB_PATH,

        check_same_thread=False

    )


    conn.row_factory = sqlite3.Row


    cursor = conn.cursor()



    print(
        "✅ Database Connected"
    )



except Exception as e:


    print(
        "❌ Database Error:",
        e
    )


    exit()





# =====================================================
# MQTT STATUS
# =====================================================


mqtt_connected = False






# =====================================================
# MQTT CALLBACK FUNCTIONS
# =====================================================


def on_connect(
        client,
        userdata,
        flags,
        rc
):


    global mqtt_connected



    if rc == 0:


        mqtt_connected = True


        print(
            "✅ AWS IoT MQTT Connected"
        )



    else:


        mqtt_connected = False


        print(
            "❌ MQTT Connection Failed:",
            rc
        )






def on_disconnect(
        client,
        userdata,
        rc
):


    global mqtt_connected


    mqtt_connected = False


    print(
        "⚠ MQTT Disconnected"
    )







# =====================================================
# MQTT CLIENT SETUP
# =====================================================


mqtt_client = mqtt.Client(

    client_id=CLIENT_ID,

    protocol=mqtt.MQTTv311

)



mqtt_client.tls_set(

    ca_certs=CA_PATH,

    certfile=CERT_PATH,

    keyfile=KEY_PATH,

    tls_version=ssl.PROTOCOL_TLSv1_2

)



mqtt_client.on_connect = on_connect

mqtt_client.on_disconnect = on_disconnect



mqtt_client.loop_start()






# =====================================================
# MQTT CONNECT
# =====================================================


while not mqtt_connected:


    try:


        print(
            "Connecting AWS IoT..."
        )


        mqtt_client.connect(

            MQTT_ENDPOINT,

            port=8883

        )


    except Exception as e:


        print(

            "MQTT Error:",

            e

        )


        time.sleep(2)



    time.sleep(1)






print(

    "\n🚀 HAMS AWS Upload Started\n"

)






# =====================================================
# MAIN UPLOAD LOOP
# =====================================================


while True:



    try:



        cursor.execute(

            """

            SELECT *

            FROM brake_pressure_log

            WHERE uploaded=0

            ORDER BY id ASC

            """

        )



        rows = cursor.fetchall()





        if not rows:


            time.sleep(1)

            continue






        print(

            "Pending Upload Records =",

            len(rows)

        )






        for row in rows:




            payload = {


                "device_id":
                    row["device_id"],



                "timestamp":
                    row["timestamp"],




                "BP_raw":
                    row["BP_raw"],



                "FP_raw":
                    row["FP_raw"],



                "CR_raw":
                    row["CR_raw"],



                "BC_raw":
                    row["BC_raw"],




                "MR_raw":
                    row["MR_raw"],




                "Battery_raw":
                    row["Battery_raw"],



                "Battery_voltage":
                    row["Battery_voltage"],




                "GPS_status":
                    row["GPS_status"],



                "SAT":
                    row["SAT"],



                "LAT":
                    row["LAT"],



                "LONG":
                    row["LONG"],



                "ALT":
                    row["ALT"]

            }





            print("--------------------------------")


            print(
                "Uploading ID =",
                row["id"]
            )


            print(
                json.dumps(payload)
            )





            while not mqtt_connected:


                print(
                    "Waiting AWS connection..."
                )


                time.sleep(1)







            try:



                result = mqtt_client.publish(

                    TOPIC,

                    json.dumps(payload),

                    qos=1

                )





                if result.rc == 0:



                    cursor.execute(

                        """

                        UPDATE brake_pressure_log

                        SET uploaded=1

                        WHERE id=?

                        """,

                        (

                        row["id"],

                        )

                    )



                    conn.commit()



                    print(

                        "✅ Uploaded Successfully"

                    )



                else:



                    print(

                        "❌ MQTT Publish Failed"

                    )





            except Exception as e:



                print(

                    "Upload Error:",

                    e

                )





            print("--------------------------------\n")







    except Exception as e:



        print(

            "Main Loop Error:",

            e

        )





    time.sleep(1)