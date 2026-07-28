#!/usr/bin/env python3

import os
import time
import sqlite3
import json
import ssl
import paho.mqtt.client as mqtt


# =====================================================
# BASE PATH
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# =====================================================
# DATABASE PATH
# =====================================================

# ---------------- DATABASE PATH ----------------

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
    "certs_2",
    "AmazonRootCA1.pem"
)

CERT_PATH = os.path.join(
    BASE_DIR,
    "certs_2",
    "certificate.pem.crt"
)

KEY_PATH = os.path.join(
    BASE_DIR,
    "certs_2",
    "private.pem.key"
)


# =====================================================
# AWS MQTT CONFIGURATION
# =====================================================

MQTT_ENDPOINT = (
    "a1vddjuckiz90j-ats.iot.ap-south-1.amazonaws.com"
)


CLIENT_ID = (
    "Raspberrypi4"
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

    print("✅ Database Connected")


except Exception as e:

    print(
        "❌ Database Connection Error:",
        e
    )

    exit()


# =====================================================
# MQTT STATUS
# =====================================================

mqtt_connected = False


# =====================================================
# MQTT CALLBACKS
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
            "✅ AWS IoT Connected"
        )

    else:

        mqtt_connected = False

        print(
            "❌ AWS Connection Failed:",
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
        "⚠ AWS MQTT Disconnected"
    )



def on_publish(
        client,
        userdata,
        mid
):

    print(
        "✅ Message Published ID:",
        mid
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


mqtt_client.reconnect_delay_set(
    min_delay=1,
    max_delay=60
)


mqtt_client.on_connect = on_connect

mqtt_client.on_disconnect = on_disconnect

mqtt_client.on_publish = on_publish


mqtt_client.loop_start()


# =====================================================
# AWS CONNECT FUNCTION
# =====================================================

def connect_aws():

    global mqtt_connected


    while not mqtt_connected:

        try:

            print(
                "Connecting AWS IoT..."
            )


            mqtt_client.connect(
                MQTT_ENDPOINT,
                port=8883,
                keepalive=60
            )


        except Exception as e:

            print(
                "❌ AWS Connect Error:",
                e
            )


            time.sleep(5)


        time.sleep(2)



connect_aws()


print(
    "\n🚀 AWS Upload Service Started\n"
)# =====================================================
# MAIN UPLOAD LOOP
# =====================================================

while True:

    try:

        # Check AWS connection
        if not mqtt_connected:

            print(
                "⚠ Waiting for AWS MQTT connection..."
            )

            connect_aws()


        # Fetch pending records

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
            "Pending Records:",
            len(rows)
        )



        for row in rows:


            try:


                # =====================================================
                # CREATE PAYLOAD
                # =====================================================

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
                        row["ALT"],


                    "ADS1115_48":
                        row["ADS1115_48"],


                    "ADS1115_49":
                        row["ADS1115_49"]

                }



                message = json.dumps(payload)



                print("--------------------------------")

                print(
                    "Uploading ID:",
                    row["id"]
                )



                # =====================================================
                # PUBLISH TO AWS
                # =====================================================


                if not mqtt_connected:

                    print(
                        "AWS disconnected, reconnecting..."
                    )

                    connect_aws()



                result = mqtt_client.publish(

                    TOPIC,

                    message,

                    qos=1

                )



                # Wait for AWS acknowledgement

                result.wait_for_publish()



                if result.rc == mqtt.MQTT_ERR_SUCCESS:



                    print(
                        "✅ Upload Successful"
                    )


                    # Mark uploaded only after success

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



                else:


                    print(
                        "❌ MQTT Publish Failed"
                    )



            except Exception as e:


                print(
                    "❌ Upload Error:",
                    e
                )


                time.sleep(2)



            print("--------------------------------\n")



    except sqlite3.Error as e:


        print(
            "Database Error:",
            e
        )


        time.sleep(5)



    except Exception as e:


        print(
            "Main Loop Error:",
            e
        )


        time.sleep(5)



    time.sleep(1)