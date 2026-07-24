#!/usr/bin/env python3

import time
import board
import busio

import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


# -------------------------------
# Constants
# -------------------------------

SHUNT = 160.0
ADC_FULL = 32767.0
ADC_VOLTAGE = 4.096


# Pressure ranges
BP_RANGE = 5.0
FP_RANGE = 6.0
CR_RANGE = 5.0
BC_RANGE = 3.8
MR_RANGE = 10.0



# -------------------------------
# I2C
# -------------------------------

i2c = busio.I2C(board.SCL, board.SDA)


# ADS1115-1
ads1 = ADS.ADS1115(i2c,address=0x48)
ads1.gain = 1


BP = AnalogIn(ads1,0)
FP = AnalogIn(ads1,1)
CR = AnalogIn(ads1,2)
BC = AnalogIn(ads1,3)


# ADS1115-2

ads2 = ADS.ADS1115(i2c,address=0x49)
ads2.gain = 1


Battery = AnalogIn(ads2,2)
MR = AnalogIn(ads2,3)



# -------------------------------
# Conversion Function
# -------------------------------

def convert_pressure(sensor, pressure_range):

    raw = sensor.value

    voltage = (raw / ADC_FULL) * ADC_VOLTAGE

    current = (voltage / SHUNT) * 1000


    pressure = ((current - 4.0) / 16.0) * pressure_range


    if pressure < 0:
        pressure = 0


    return raw, voltage, current, pressure



# -------------------------------
# Main Loop
# -------------------------------


while True:


    bp = convert_pressure(BP,BP_RANGE)
    fp = convert_pressure(FP,FP_RANGE)
    cr = convert_pressure(CR,CR_RANGE)
    bc = convert_pressure(BC,BC_RANGE)

    mr = convert_pressure(MR,MR_RANGE)



    print("\n--------------------------------")
    print(time.strftime("%Y-%m-%d %H:%M:%S"))
    print("--------------------------------")


    print(
    f"BP Raw:{bp[0]}  "
    f"V:{bp[1]:.3f}V "
    f"I:{bp[2]:.2f}mA "
    f"P:{bp[3]:.2f} kg/cm2"
    )


    print(
    f"FP Raw:{fp[0]}  "
    f"V:{fp[1]:.3f}V "
    f"I:{fp[2]:.2f}mA "
    f"P:{fp[3]:.2f} kg/cm2"
    )


    print(
    f"CR Raw:{cr[0]}  "
    f"V:{cr[1]:.3f}V "
    f"I:{cr[2]:.2f}mA "
    f"P:{cr[3]:.2f} kg/cm2"
    )


    print(
    f"BC Raw:{bc[0]}  "
    f"V:{bc[1]:.3f}V "
    f"I:{bc[2]:.2f}mA "
    f"P:{bc[3]:.2f} kg/cm2"
    )


    print(
    f"MR Raw:{mr[0]}  "
    f"V:{mr[1]:.3f}V "
    f"I:{mr[2]:.2f}mA "
    f"P:{mr[3]:.2f} kg/cm2"
    )


    print("--------------------------------")


    time.sleep(1)