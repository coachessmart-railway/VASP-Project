from RPLCD.gpio import CharLCD
from RPi import GPIO
import time

lcd = CharLCD(
    numbering_mode=GPIO.BCM,
    cols=20,
    rows=4,
    pin_rs=26,
    pin_e=19,
    pins_data=[13, 6, 5, 11]
)

try:
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string("Hello Saniya")
    lcd.cursor_pos = (1, 0)
    lcd.write_string("Good Morning")
    lcd.cursor_pos = (2, 0)
    lcd.write_string("RTABMS Display")
    lcd.cursor_pos = (3, 0)
    lcd.write_string("Raspberry Pi")

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    lcd.clear()
    GPIO.cleanup()