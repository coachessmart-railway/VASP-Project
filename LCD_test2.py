from RPLCD.gpio import CharLCD
from RPi import GPIO
import time

GPIO.setwarnings(False)
GPIO.cleanup()

print("Starting LCD Test...")

lcd = CharLCD(
    numbering_mode=GPIO.BCM,
    pin_rs=26,
    pin_e=19,
    pins_data=[13, 6, 5, 11],
    cols=20,
    rows=4
)

lcd.clear()

lcd.write_string("HELLO")

print("HELLO sent to LCD")

while True:
    time.sleep(1)