"""
Air pump needs to run for one minute a day
"""

import RPi.GPIO as IO
import configparser
from datetime import datetime, timedelta, timezone
import time
import argparse

parser = argparse.ArgumentParser(description="Air Pump Manager")
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
PUMP_GPIO_OUT = int(config["AIRPUMP"]["PUMP_GPIO_OUT"])
if PUMP_GPIO_OUT == -1:
    print("No GPIO set")
    quit(1)

# File to write timestamp of last run to
TS_FILE = config["AIRPUMP"]["TS_FILE"]
FREQUENCY = float(config["AIRPUMP"]["FREQUENCY"])
CYCLE_TIME = int(config["AIRPUMP"]["CYCLE_TIME"])
TS_STR_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
# Strip the last characters from isoformat string to get rid of the pesky timezone
TS_STR_REPLACE_TZ_OFFSET = -6

IO.setmode(IO.BCM)
IO.setup(PUMP_GPIO_OUT, IO.OUT, initial=IO.HIGH)
NOFILE = False

def get_last_timestamp():
    last_run = datetime.now(timezone.utc) - timedelta(days=FREQUENCY)

    try:
        with open(TS_FILE, "r") as ts:
            last_run = datetime.strptime(ts.read()[:TS_STR_REPLACE_TZ_OFFSET], TS_STR_FORMAT)
            last_run = last_run.replace(tzinfo=timezone.utc)
    except FileNotFoundError:
        pass

    return last_run

def update_timestamp_file():
    print("Updating timestamp file with new timestamp")
    with open(TS_FILE, "w") as ts:
        timestamp = datetime.now(timezone.utc).isoformat()
        ts.write(timestamp)

def cycle(seconds):
    print(f"Turning air pump on for {seconds} seconds")
    IO.output(PUMP_GPIO_OUT, IO.LOW)
    time.sleep(seconds)
    print("Turning air pump off")
    IO.output(PUMP_GPIO_OUT, IO.HIGH)


while True:
    last_cycle = get_last_timestamp()
    next_run = last_cycle + timedelta(days=FREQUENCY)

    if datetime.now(timezone.utc) >= next_run:
        update_timestamp_file()
        cycle(CYCLE_TIME)

    # sleeping for 3 hours after each successive cycle
    # pump will never be turned on more than each 3 hours
    # and will mostly be used in increments of 3 hours
    time.sleep(60 * 60 * 3)

# No Cleanup
