#!/usr/bin/env python3

import time
import board
import busio

import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# -----------------------------------
# Initialize I2C
# -----------------------------------
i2c = busio.I2C(board.SCL, board.SDA)

# -----------------------------------
# ADS1115 #1 (0x48)
# -----------------------------------
ads1 = ADS.ADS1115(i2c, address=0x48)
ads1.gain = 1

bp = AnalogIn(ads1, ADS.P0)
fp = AnalogIn(ads1, ADS.P1)
cr = AnalogIn(ads1, ADS.P2)
bc = AnalogIn(ads1, ADS.P3)

# -----------------------------------
# ADS1115 #2 (0x49)
# -----------------------------------
ads2 = ADS.ADS1115(i2c, address=0x49)
ads2.gain = 1

battery = AnalogIn(ads2, ADS.P2)
mr = AnalogIn(ads2, ADS.P3)

print("==============================================")
print("      ADS1115 RAW VALUE TEST")
print("==============================================")

while True:

    print("\n--------------------------------------------")
    print(time.strftime("%Y-%m-%d %H:%M:%S"))
    print("--------------------------------------------")

    print(f"BP Raw       : {bp.value}")
    print(f"FP Raw       : {fp.value}")
    print(f"CR Raw       : {cr.value}")
    print(f"BC Raw       : {bc.value}")

    print("--------------------------------------------")

    print(f"MR Raw       : {mr.value}")
    print(f"Battery Raw  : {battery.value}")

    time.sleep(1)