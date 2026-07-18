#!/usr/bin/env python3

import serial
import pynmea2
import time

from RPLCD.i2c import CharLCD

# ---------------- LCD ----------------
lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,      # Change to 0x3F if needed
    port=1,
    cols=20,
    rows=4,
    charmap='A00'
)

# ---------------- GPS ----------------
GPS_PORT = "/dev/ttyAMA3"
GPS_BAUD = 38400

gps = serial.Serial(GPS_PORT, GPS_BAUD, timeout=1)

lcd.clear()
lcd.write_string(" HAMS BB DEVICE")
lcd.cursor_pos = (1,0)
lcd.write_string("Starting GPS...")
time.sleep(2)

while True:

    line = gps.readline().decode('ascii', errors='ignore').strip()

    if not line.startswith("$"):
        continue

    try:
        msg = pynmea2.parse(line)
    except:
        continue

    if msg.sentence_type == "GGA":

        fix = int(msg.gps_qual or 0)
        sats = int(msg.num_sats or 0)

        lcd.clear()

        lcd.cursor_pos = (0,0)
        lcd.write_string("HAMS BB GPS STATUS")

        if fix == 0:

            lcd.cursor_pos = (1,0)
            lcd.write_string("Waiting For Fix")

            lcd.cursor_pos = (2,0)
            lcd.write_string(f"Satellites:{sats:02d}")

            lcd.cursor_pos = (3,0)
            lcd.write_string("Searching...")

        else:

            lat = msg.latitude
            lon = msg.longitude
            alt = msg.altitude

            lcd.cursor_pos = (1,0)
            lcd.write_string(f"Fix:YES Sat:{sats}")

            lcd.cursor_pos = (2,0)
            lcd.write_string(f"Lat:{lat:.6f}")

            lcd.cursor_pos = (3,0)
            lcd.write_string(f"Lon:{lon:.6f}")

            print("--------------------------------")
            print("Latitude :", lat)
            print("Longitude:", lon)
            print("Altitude :", alt)
            print("Satellites:", sats)
            print("--------------------------------")

    time.sleep(1)