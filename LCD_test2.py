from RPLCD.i2c import CharLCD
import time

try:
    lcd = CharLCD(
        i2c_expander='PCF8574',
        address=0x27,
        port=1,
        cols=20,
        rows=4,
        auto_linebreaks=False,
        charmap='A00'
    )

    lcd.clear()
    lcd.write_string("Hello Saniya!")
    print("LCD OK")

    time.sleep(10)

except Exception as e:
    print("Error:", e)