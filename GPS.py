from RPLCD.i2c import CharLCD

lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,
    port=6,
    cols=20,
    rows=4,
    charmap='A00'
)

lcd.clear()
lcd.write_string("HAMS BB LCD OK")