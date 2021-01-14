"""
Air pump needs to run for one minute a day
"""

import RPi.GPIO as IO
import configparser
from datetime import datetime, timedelta, timezone
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
    return

# File to write timestamp of last run to
TS_FILE = config["AIRPUMP"]["TS_FILE"]
FREQUENCY = int(config["AIRPUMP"]["FREQUENCY"])
TS_STR_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
# Strip the last characters from isoformat string to get rid of the pesky timezone
TS_STR_REPLACE_TZ_OFFSET = -6

IO.setmode(IO.BCM)
IO.setup(PUMP_GPIO_OUT, IO.OUT, initial=IO.HIGH)
NOFILE = False
try:
    with open(TS_FILE, "rb") as ts:
        last_run = datetime.strptime(ts.read()[:TS_STR_REPLACE_TZ_OFFSET], TS_STR_FORMAT)
        if last_run >= datetime.now(timezone.utc) - timedelta(days=FREQUENCY):
            print("Time's not up, keep waiting")
            IO.output(IO.HIGH)  # make sure the UV is off
        else:
            # Switch the UV on and let cron do it's job of checking every X minutes
            IO.output(IO.LOW)
except FileNotFoundError:
    NOFILE = True

# If we have no timestamp, run anyway
if NOFILE:
    IO.output(IO.LOW)

# Write the timestamp
with open(TS_FILE, "wb") as ts:
    timestamp = datetime.now(timezone.utc).isoformat()
    ts.write(timestamp)

# No Cleanup
