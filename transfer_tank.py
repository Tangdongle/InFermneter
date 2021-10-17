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
import argparse
import requests
from datetime import timedelta, datetime, timezone

from utilities import get_last_timestamp, update_timestamp_file

parser = argparse.ArgumentParser(description="Pump manager")
parser.add_argument(
    "--config",
    dest="config_fname",
    default="config.ini",
    required=False,
    type=str,
    help="Custom config file to use",
)

parser.add_argument(
    "--drain-lock-file",
    dest="drain_fname",
    default="draining.lock",
    required=False,
    type=str,
    help="File to lock draining",
)
args = parser.parse_args()

CONFIGFILE = args.config_fname
DRAIN_FILELOCK = args.drain_fname
LAST_DRAINED = None
HAS_PRIMED = False


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
PRIMING_GPIO = int(config["TRANSFER"]["PRIMING_GPIO"])


IO.setmode(IO.BCM)
IO.setup(TANK_BOTTOM_GPIO_IN, IO.IN, pull_up_down=IO.PUD_DOWN)
IO.setup(TANK_TOP_GPIO_IN, IO.IN, pull_up_down=IO.PUD_DOWN)
IO.setup(PUMP_GPIO_OUT, IO.OUT)
IO.setup(PRIMING_GPIO, IO.OUT)

IO.output(PUMP_GPIO_OUT, IO.HIGH)
IO.output(PRIMING_GPIO, IO.HIGH)

print("Starting ttank")
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
              update_timestamp_file(DRAIN_FILELOCK)
            # If we have been draining and the bottom sensor turns on
            # we have finished draining and can disable the pump
            if DRAINING and bot_val:
              print(f"Draining complete in {DRAIN_DELAY} seconds.")
              time.sleep(DRAIN_DELAY)

              DRAINING = False
              IO.output(PUMP_GPIO_OUT, IO.HIGH)
            elif DRAINING:
              LAST_DRAINED = get_last_timestamp(DRAIN_FILELOCK, minutes=2)
              two_plus_mins_in = datetime.now(timezone.utc) >= LAST_DRAINED + timedelta(minutes=2)
              one_min_in = datetime.now(timezone.utc) >= LAST_DRAINED + timedelta(minutes=1) 
          
              if one_min_in and not two_plus_mins_in and not HAS_PRIMED:
                # If the system has been draining for more than 1 minute,
                # we want to turn the priming valve on for 1 second
                # Now the System has been draining for more than 1 minute
                DRAINING = True
                HAS_PRIMED = True
                # Set priming tank on
                IO.output(PRIMING_GPIO, IO.LOW)
                time.sleep(1)
                # Set priming tank back off
                IO.output(PRIMING_GPIO, IO.HIGH)
              # If more than one min and the priming has run
              elif two_plus_mins_in:
                # If the system has been draining for more than 2 minutes,
                # we want to forcefully switch it off and send an alert!
                # System has been draining for more than 2 minures
                DRAINING = False
                IO.output(PUMP_GPIO_OUT, IO.HIGH)
                data = {
                    "last_drained": LAST_DRAINED,
                    "emsg": "Transfer tank pump running for > 2 mins"
                }
                requests.post("https://beer.tanger.dev/ttankmon", headers={"Content-Type": "application/json"}, data=data)
                print("Shutting down transfer tank code")
                quit(1)

                time.sleep(0.5)
finally:
  IO.cleanup()
