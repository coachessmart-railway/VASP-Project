#!/usr/bin/env python3

import time
import serial
import pynmea2

from RPLCD.i2c import CharLCD

# ---------------- LCD I2C ----------------

lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,
    port=1,                  # Correct I2C bus
    cols=20,
    rows=4,
    charmap='A00',
    auto_linebreaks=False
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


# ---------------- GPS UART3 ----------------

GPS_PORT = "/dev/ttyAMA3"
GPS_BAUD = 38400

gps = serial.Serial(
    port=GPS_PORT,
    baudrate=GPS_BAUD,
    timeout=1
)


# ---------------- START SCREEN ----------------

lcd_show(
    "HAMS BB DEVICE",
    "GPS Starting...",
    "UART3 Connected",
    "Waiting Data"
)

print("GPS Started...")

while True:
    try:
        line = gps.readline().decode("ascii", errors="ignore").strip()

        if line.startswith("$GNGGA") or line.startswith("$GPGGA"):
            msg = pynmea2.parse(line)

            latitude = msg.latitude
            longitude = msg.longitude
            altitude = msg.altitude
            satellites = msg.num_sats

            print("--------------------------------")
            print("Latitude  :", latitude)
            print("Longitude :", longitude)
            print("Altitude  :", altitude, "m")
            print("Satellites:", satellites)
            print("--------------------------------")

            lcd_show(
                f"SAT:{satellites}",
                f"LAT:{latitude:.5f}",
                f"LON:{longitude:.5f}",
                f"ALT:{altitude}m"
            )

    except pynmea2.ParseError:
        pass

    except KeyboardInterrupt:
        lcd.clear()
        print("Program Stopped")
        break

    except Exception as e:
        print("Error:", e)
        time.sleep(1)