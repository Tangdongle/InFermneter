"""
UV needs to run once every three days
Run this with a cronjob that checks every x minutes, where x is the duration
that the UV light should run for. It will be switched off on next run
"""

import RPi.GPIO as IO
from datetime import datetime, timedelta, timezone
import configparser
import argparse
import time

from utilities import get_last_timestamp, update_timestamp_file

parser = argparse.ArgumentParser(description="UV Manager")
parser.add_argument(
    "--config",
    dest="config_fname",
    default="config.ini",
    required=False,
    type=str,
    help="Custom config file to use",
)
args = parser.parse_args()

CONFIGFILE = args.config_fname

config = configparser.ConfigParser()
config.read(CONFIGFILE)

AIR_PUMP_GPIO_OUT = int(config["AIRPUMP"]["PUMP_GPIO_OUT"])
if AIR_PUMP_GPIO_OUT == -1:
    print("No GPIO set")
    quit(1)

# File to write timestamp of last run to
AIR_TS_FILE = config["AIRPUMP"]["TS_FILE"]
AIR_FREQUENCY = float(config["AIRPUMP"]["FREQUENCY"])
CYCLE_TIME = int(config["AIRPUMP"]["CYCLE_TIME"])
TS_STR_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
# Strip the last characters from isoformat string to get rid of the pesky timezone
TS_STR_REPLACE_TZ_OFFSET = -6

PUMP_GPIO_OUT = int(config["UV"]["PUMP_GPIO_OUT"])
if PUMP_GPIO_OUT == -1:
    print("No GPIO set")
    quit(1)

# File to write timestamp of last run to
UV_TS_FILE = config["UV"]["TS_FILE"]
FREQUENCY = int(config["UV"]["FREQUENCY"])

IO.setmode(IO.BCM)
IO.setup(PUMP_GPIO_OUT, IO.OUT, initial=IO.HIGH)
IO.setup(AIR_PUMP_GPIO_OUT, IO.OUT, initial=IO.HIGH)

SECONDS_TO_WAIT_FOR_FOAM = 60 * 60 # One hour
SECONDS_UV_ON = 20


def cycle_air_pump(seconds):
    print(f"Turning air pump on for {seconds} seconds")
    IO.output(AIR_PUMP_GPIO_OUT, IO.LOW)
    time.sleep(seconds)
    print("Turning air pump off")
    IO.output(AIR_PUMP_GPIO_OUT, IO.HIGH)


if __name__ == '__main__':
    cycle_air_pump(CYCLE_TIME)
    time.sleep(SECONDS_TO_WAIT_FOR_FOAM)
    IO.output(PUMP_GPIO_OUT, IO.LOW)
    time.sleep(SECONDS_UV_ON)
    IO.output(PUMP_GPIO_OUT, IO.HIGH)
    IO.cleanup()
    with open("/home/pi/uv_log.log", "a+") as fd:
         fd.write(f"UV triggered at {datetime.now()}")
