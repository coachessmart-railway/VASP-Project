#!/usr/bin/env python3

import time
import serial
import pynmea2

from RPLCD.i2c import CharLCD


# ---------------- LCD I2C-6 ----------------

lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,       # Change to 0x3F if required
    port=6,
    cols=20,
    rows=4,
    charmap='A00'
)


def lcd_show(line1, line2, line3, line4):

    lcd.clear()

    lcd.cursor_pos = (0, 0)
    lcd.write_string(line1[:20])

    lcd.cursor_pos = (1, 0)
    lcd.write_string(line2[:20])

    lcd.cursor_pos = (2, 0)
    lcd.write_string(line3[:20])

    lcd.cursor_pos = (3, 0)
    lcd.write_string(line4[:20])


# ---------------- GPS UART ----------------

GPS_PORT = "/dev/ttyAMA3"
GPS_BAUD = 38400


gps = serial.Serial(
    GPS_PORT,
    GPS_BAUD,
    timeout=1
)


# ---------------- START SCREEN ----------------

lcd_show(
    "HAMS BB DEVICE",
    "GPS Starting...",
    "UART3 Connected",
    "Waiting Data"
)

print("GPS Started")
time.sleep(3)


# ---------------- MAIN LOOP ----------------

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


        # GGA gives location

        if msg.sentence_type == "GGA":

            fix = int(msg.gps_qual or 0)
            satellites = int(msg.num_sats or 0)


            if fix == 0:

                print(
                    f"Waiting GPS Fix | Satellites: {satellites}"
                )

                lcd_show(
                    "HAMS BB GPS",
                    "Waiting For Fix",
                    f"SAT:{satellites}",
                    "Searching..."
                )


            else:

                latitude = msg.latitude
                longitude = msg.longitude
                altitude = msg.altitude


                # Terminal Output

                print("--------------------------------")
                print("GPS FIX OK")
                print("Latitude :", latitude)
                print("Longitude:", longitude)
                print("Altitude :", altitude, "m")
                print("Satellites:", satellites)

                print(
                    "Map:",
                    f"https://maps.google.com/?q={latitude},{longitude}"
                )

                print("--------------------------------")


                # LCD Output

                lcd_show(
                    "HAMS BB GPS",
                    f"SAT:{satellites} ALT:{altitude}m",
                    f"LAT:{latitude:.6f}",
                    f"LON:{longitude:.6f}"
                )


        # RMC gives speed

        elif msg.sentence_type == "RMC":

            if msg.status == "A":

                speed = float(
                    msg.spd_over_grnd or 0
                ) * 1.852

                print(
                    f"Speed: {speed:.2f} km/h"
                )


        time.sleep(0.2)


    except KeyboardInterrupt:

        print("GPS stopped")
        lcd.clear()
        gps.close()
        break


    except Exception as e:

        print("Error:", e)
        time.sleep(1)