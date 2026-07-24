#!/usr/bin/env python3

import time
import board
import busio

import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


# -------------------------------
# I2C Initialization
# -------------------------------

i2c = busio.I2C(board.SCL, board.SDA)


# -------------------------------
# ADS1115-1 Address 0x48
# BP FP CR BC
# -------------------------------

ads1 = ADS.ADS1115(
    i2c,
    address=0x48
)

ads1.gain = 1


BP = AnalogIn(ads1, 0)
FP = AnalogIn(ads1, 1)
CR = AnalogIn(ads1, 2)
BC = AnalogIn(ads1, 3)


# -------------------------------
# ADS1115-2 Address 0x49
# MR Battery
# -------------------------------

ads2 = ADS.ADS1115(
    i2c,
    address=0x49
)

ads2.gain = 1


Battery = AnalogIn(ads2, 2)
MR = AnalogIn(ads2, 3)



print("--------------------------------")
print(" ADS1115 RAW VALUE TEST")
print("--------------------------------")


while True:

    print("\nTime :", time.strftime("%Y-%m-%d %H:%M:%S"))

    print("--------------------------------")

    print("ADS1115-1 (0x48)")

    print("BP Raw :", BP.value)
    print("FP Raw :", FP.value)
    print("CR Raw :", CR.value)
    print("BC Raw :", BC.value)


    print("--------------------------------")

    print("ADS1115-2 (0x49)")

    print("MR Raw      :", MR.value)
    print("Battery Raw :", Battery.value)


    print("--------------------------------")


    time.sleep(1)