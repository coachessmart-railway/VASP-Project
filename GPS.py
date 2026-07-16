#!/usr/bin/env python3

import time

import pynmea2
import serial


GPS_PORT = "/dev/ttyAMA3"
GPS_BAUD_RATE = 38400


def main():
    gps = None

    try:
        gps = serial.Serial(
            port=GPS_PORT,
            baudrate=GPS_BAUD_RATE,
            timeout=2
        )

        print("=" * 55)
        print("NEO-M9N Live GPS Monitoring")
        print(f"Port      : {GPS_PORT}")
        print(f"Baud rate : {GPS_BAUD_RATE}")
        print("=" * 55)
        print("Waiting for a valid GPS fix...")
        print("Keep the antenna outdoors with a clear sky view.\n")

        while True:
            raw_data = gps.readline()

            if not raw_data:
                continue

            line = raw_data.decode(
                "ascii",
                errors="ignore"
            ).strip()

            if not line.startswith("$"):
                continue

            try:
                message = pynmea2.parse(line)

            except pynmea2.ParseError:
                continue

            # GGA gives fix quality, satellites, altitude and position.
            if message.sentence_type == "GGA":
                fix_quality = int(message.gps_qual or 0)
                satellites = int(message.num_sats or 0)

                if fix_quality == 0:
                    print(
                        f"Waiting for GPS fix... "
                        f"Satellites used: {satellites}",
                        end="\r"
                    )
                    continue

                latitude = message.latitude
                longitude = message.longitude
                altitude = message.altitude or "N/A"
                hdop = message.horizontal_dil or "N/A"

                google_maps_url = (
                    f"https://maps.google.com/?q="
                    f"{latitude},{longitude}"
                )

                print("\n" + "=" * 55)
                print("VALID GPS LOCATION")
                print("=" * 55)
                print(f"Latitude        : {latitude:.7f}")
                print(f"Longitude       : {longitude:.7f}")
                print(f"Altitude        : {altitude} m")
                print(f"Satellites used : {satellites}")
                print(f"Fix quality     : {fix_quality}")
                print(f"HDOP            : {hdop}")
                print(f"Google Maps     : {google_maps_url}")
                print("=" * 55)

            # RMC gives speed, course, date and valid/invalid status.
            elif message.sentence_type == "RMC":
                if message.status != "A":
                    continue

                latitude = message.latitude
                longitude = message.longitude

                speed_knots = float(
                    message.spd_over_grnd or 0
                )

                speed_kmph = speed_knots * 1.852

                course = message.true_course or "N/A"
                gps_date = message.datestamp or "N/A"
                gps_time = message.timestamp or "N/A"

                print(f"Speed           : {speed_kmph:.2f} km/h")
                print(f"Direction       : {course}°")
                print(f"GPS date        : {gps_date}")
                print(f"GPS UTC time    : {gps_time}")
                print(
                    f"Current location: "
                    f"{latitude:.7f}, {longitude:.7f}"
                )
                print("-" * 55)

            time.sleep(0.05)

    except serial.SerialException as error:
        print(f"\nSerial-port error: {error}")
        print(f"Check whether {GPS_PORT} is used by another program.")

    except PermissionError:
        print(f"\nPermission denied for {GPS_PORT}.")
        print("Add the user to the dialout group:")
        print("sudo usermod -aG dialout pi_1234")
        print("sudo reboot")

    except KeyboardInterrupt:
        print("\nGPS monitoring stopped by user.")

    finally:
        if gps is not None and gps.is_open:
            gps.close()


if __name__ == "__main__":
    main()