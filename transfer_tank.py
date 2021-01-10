"""
Transfer tank sensors are active (1) when down (liquid lifts them up)

Pump relay defaults to NC (Not connected) side
so booleans for pump output are inverted

Pump needs to be activated when both sensors are 0
Pump stays active until bottom sensor is back on
"""

import RPi.GPIO as IO
import time
import configparser

CONFIGFILE = "config.ini"

config = configparser.ConfigParser()
config.read(CONFIGFILE)

if not bool(config["TRANSFER"]["ENABLED"]):
    print("Transfer tank disabled, exiting")
    quit(0)

ENABLE_CONSTANT_ON = bool(int(config["TRANSFER"]["ALWAYS_ON"]))

TANK_BOTTOM_GPIO_IN = int(config["TRANSFER"]["BOTTOM_GPIO"])
TANK_TOP_GPIO_IN = int(config["TRANSFER"]["TOP_GPIO"])
PUMP_GPIO_OUT = int(config["TRANSFER"]["PUMP_GPIO_OUT"])

# While this is TRUE (1), the pump relay will be active
DRAINING = True if config["TRANSFER"]["START_DRAINING"] == "True" else False

# Offset to continue draining after the bottom transfer sensor has been activated
DRAIN_DELAY = int(config["TRANSFER"]["DRAIN_DELAY"])

IO.setmode(IO.BCM)
IO.setup(TANK_BOTTOM_GPIO_IN, IO.IN, pull_up_down=IO.PUD_DOWN)
IO.setup(TANK_TOP_GPIO_IN, IO.IN, pull_up_down=IO.PUD_DOWN)
IO.setup(PUMP_GPIO_OUT, IO.OUT)

IO.output(PUMP_GPIO_OUT, IO.HIGH)

try:
    if ENABLE_CONSTANT_ON:
        IO.output(PUMP_GPIO_OUT, IO.HIGH)
    else:
        while True:
            top_val = IO.input(TANK_TOP_GPIO_IN)
            bot_val = IO.input(TANK_BOTTOM_GPIO_IN)

            # If both the top and bottom sensors are off (0)
            # we need to start the draining cycle
            if not top_val and not bot_val and not DRAINING:
                print("Draining enabled...")
                DRAINING = True
                IO.output(PUMP_GPIO_OUT, IO.LOW)

            # If we have been draining and the bottom sensor turns on
            # we have finished draining and can disable the pump
            if DRAINING and bot_val:
                print(f"Draining complete in {DRAIN_DELAY} seconds.")
                time.sleep(DRAIN_DELAY)

                DRAINING = False
                IO.output(PUMP_GPIO_OUT, IO.HIGH)

            time.sleep(0.5)
finally:
    IO.cleanup()
