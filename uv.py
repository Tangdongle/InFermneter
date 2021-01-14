"""
UV needs to run once every three days
Run this with a cronjob that checks every x minutes, where x is the duration
that the UV light should run for. It will be switched off on next run
"""

import RPi.GPIO as IO
from datetime import datetime, timedelta, timezone
import configparser
import argparse

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
PUMP_GPIO_OUT = int(config["UV"]["PUMP_GPIO_OUT"])
if PUMP_GPIO_OUT == -1:
    print("No GPIO set")
    return

# File to write timestamp of last run to
TS_FILE = config["UV"]["TS_FILE"]
TS_STR_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
FREQUENCY = int(config["UV"]["FREQUENCY"])
# Strip the last characters from isoformat string to get rid of the pesky timezone
TS_STR_REPLACE_TZ_OFFSET = -6

IO.setmode(IO.BCM)
IO.setup(PUMP_GPIO_OUT, IO.OUT, initial=IO.LOW)

with open(TS_FILE, "rb") as ts:
    last_run = datetime.strptime(ts.read()[:TS_STR_REPLACE_TZ_OFFSET], TS_STR_FORMAT)
    if last_run >= datetime.now(timezone.utc) - timedelta(days=FREQUENCY):
        print("Time's not up, keep waiting")
        IO.output(IO.LOW)  # make sure the UV is off
    else:
        # Switch the UV on and let cron do it's job of checking every X minutes
        IO.output(IO.HIGH)

# Write the timestamp
with open(TS_FILE, "wb") as ts:
    timestamp = datetime.now(timezone.utc).isoformat()
    ts.write(timestamp)
# No cleanup
