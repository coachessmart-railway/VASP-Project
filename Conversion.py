#!/usr/bin/env python3

import time


# =====================================================
# CONFIGURATION
# =====================================================

SHUNT_RESISTOR = 160.0

ADC_RANGE = 4.096

MAX_ADC = 32767


# 4-20mA pressure sensor
PRESSURE_RANGE_BAR = 10.0



# =====================================================
# ADS1115 SETUP
# =====================================================

try:

    import board
    import busio

    import adafruit_ads1x15.ads1115 as ADS

    from adafruit_ads1x15.analog_in import AnalogIn



    i2c = busio.I2C(
        board.SCL,
        board.SDA
    )



    ads1 = ADS.ADS1115(
        i2c,
        address=0x48
    )


    ads1.gain = 1



    BP = AnalogIn(
        ads1,
        0
    )

    FP = AnalogIn(
        ads1,
        1
    )

    CR = AnalogIn(
        ads1,
        2
    )

    BC = AnalogIn(
        ads1,
        3
    )



    print("✅ ADS1115 0x48 Connected")



except Exception as e:

    print(
        "ADS Error:",
        e
    )

    exit()



# =====================================================
# CONVERSION FUNCTION
# =====================================================


def calculate_pressure(raw):


    # Raw to voltage

    voltage = (

        raw / MAX_ADC

    ) * ADC_RANGE



    # Voltage to current

    current_A = (

        voltage /

        SHUNT_RESISTOR

    )


    current_mA = (

        current_A * 1000

    )



    # Current to pressure

    pressure = (

        (current_mA - 4)

        /

        16

    ) * PRESSURE_RANGE_BAR



    if pressure < 0:

        pressure = 0



    return (

        round(voltage,3),

        round(current_mA,2),

        round(pressure,2)

    )




# =====================================================
# MAIN LOOP
# =====================================================


print("\n🚀 ADS1115 Pressure Test Started\n")



while True:


    BP_raw = BP.value

    FP_raw = FP.value

    CR_raw = CR.value

    BC_raw = BC.value



    print("--------------------------------")



    print(
        "BP Raw =",
        BP_raw
    )


    v,i,p = calculate_pressure(
        BP_raw
    )


    print(
        "BP Voltage =",
        v,
        "V"
    )


    print(
        "BP Current =",
        i,
        "mA"
    )


    print(
        "BP Pressure =",
        p,
        "bar"
    )



    print()



    print(
        "FP Raw =",
        FP_raw
    )


    print(
        "CR Raw =",
        CR_raw
    )


    print(
        "BC Raw =",
        BC_raw
    )



    print("--------------------------------\n")



    time.sleep(1)