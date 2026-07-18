#!/usr/bin/env python3

import time
import serial
import pynmea2

from RPLCD.i2c import CharLCD


# ---------------- LCD CONFIG ----------------

lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,        # Change to 0x3F if required
    port=1,
    cols=20,
    rows=4,
    charmap='A00'
)


def lcd_write(lines):

    lcd.clear()

    for row, text in enumerate(lines):
        lcd.cursor_pos = (row, 0)
        lcd.write_string(text[:20])


# ---------------- GPS CONFIG ----------------

GPS_PORT = "/dev/ttyAMA3"
GPS_BAUD = 38400


gps = serial.Serial(
    GPS_PORT,
    GPS_BAUD,
    timeout=1
)


# ---------------- STARTUP SCREEN ----------------

lcd_write([
    "HAMS BB DEVICE",
    "System Starting...",
    "Raspberry Pi 4",
    "LCD OK"
])

print("LCD Started")

time.sleep(5)


# ---------------- SYSTEM STATUS ----------------

lcd_write([
    "HAMS BB STATUS",
    "Power: ON",
    "Network: OFFLINE",
    "System Running"
])

print("System Running")

time.sleep(5)


# ---------------- GPS START ----------------

print("GPS Monitoring Started")


while True:

    try:

        data = gps.readline().decode(
            "ascii",
            errors="ignore"
        ).strip()


        if not data.startswith("$"):
            continue


        try:
            msg = pynmea2.parse(data)

        except:
            continue


        if msg.sentence_type == "GGA":

            fix = int(msg.gps_qual or 0)
            satellites = int(msg.num_sats or 0)


            if fix == 0:

                lcd_write([
                    "HAMS BB GPS",
                    "Waiting For Fix",
                    f"SAT:{satellites}",
                    "Searching..."
                ])

                print(
                    "Waiting GPS Fix | Satellites:",
                    satellites
                )


            else:

                latitude = msg.latitude
                longitude = msg.longitude
                altitude = msg.altitude


                print("------------------------")
                print("GPS FIX OK")
                print("Latitude :", latitude)
                print("Longitude:", longitude)
                print("Altitude :", altitude)
                print("Satellites:", satellites)
                print("------------------------")


                lcd_write([
                    "HAMS BB GPS",
                    f"FIX:YES SAT:{satellites}",
                    f"LAT:{latitude:.6f}",
                    f"LON:{longitude:.6f}"
                ])


        time.sleep(1)


    except KeyboardInterrupt:

        lcd.clear()
        gps.close()
        print("Stopped")
        break


    except Exception as error:

        print("Error:", error)
        time.sleep(1)