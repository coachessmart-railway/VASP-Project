#!/usr/bin/env python3

import time


# =====================================================
# CONFIGURATION
# =====================================================

SHUNT_RESISTOR = 160.0

ADC_MAX = 32767

ADC_VOLTAGE = 4.096


PRESSURE_RANGE = 10.0



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


    ads = ADS.ADS1115(
        i2c,
        address=0x48
    )


    ads.gain = 1



    BP = AnalogIn(
        ads,
        0
    )

    FP = AnalogIn(
        ads,
        1
    )

    CR = AnalogIn(
        ads,
        2
    )

    BC = AnalogIn(
        ads,
        3
    )



    print(
        "✅ ADS1115 0x48 Connected"
    )


except Exception as e:

    print(
        "ADS Error:",
        e
    )

    exit()




# =====================================================
# COMMON CONVERSION FUNCTION
# =====================================================


def convert_pressure(raw_value):


    # Raw ADC to voltage

    voltage = (

        raw_value /

        ADC_MAX

    ) * ADC_VOLTAGE




    # Voltage to current

    current = (

        voltage /

        SHUNT_RESISTOR

    ) * 1000




    # Current to pressure

    pressure = (

        (current - 4)

        /

        16

    ) * PRESSURE_RANGE




    if pressure < 0:

        pressure = 0



    return (

        round(voltage,3),

        round(current,2),

        round(pressure,2)

    )





# =====================================================
# SENSOR PRINT FUNCTION
# =====================================================


def print_sensor(
        name,
        raw_value
):


    voltage,current,pressure = convert_pressure(
        raw_value
    )


    print(
        name,
        "Raw =",
        raw_value
    )


    print(
        name,
        "Voltage =",
        voltage,
        "V"
    )


    print(
        name,
        "Current =",
        current,
        "mA"
    )


    print(
        name,
        "Pressure =",
        pressure,
        "bar"
    )


    print()





# =====================================================
# MAIN LOOP
# =====================================================


print(
    "\n🚀 Pressure Conversion Started\n"
)



while True:


    BP_raw = BP.value

    FP_raw = FP.value

    CR_raw = CR.value

    BC_raw = BC.value



    print("--------------------------------")



    print_sensor(
        "BP",
        BP_raw
    )


    print_sensor(
        "FP",
        FP_raw
    )


    print_sensor(
        "CR",
        CR_raw
    )


    print_sensor(
        "BC",
        BC_raw
    )


    print("--------------------------------\n")



    time.sleep(1)