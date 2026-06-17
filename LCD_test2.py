from RPLCD.gpio import CharLCD
from RPi import GPIO
import time

GPIO.setwarnings(False)
GPIO.cleanup()

lcd = CharLCD(
    numbering_mode=GPIO.BCM,
    cols=20,
    rows=4,
    pin_rs=26,
    pin_e=19,
    pins_data=[13, 6, 5, 11],
    compat_mode=True
)

lcd.clear()
lcd.write_string("HELLO SANIYA")

while True:
    time.sleep(1)