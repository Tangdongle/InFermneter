#!/usr/bin/python3

import argparse
import requests
import os
import time
import configparser

headers = {"Content-type": "application/json"}

try:
    import RPi.GPIO as IO
except ImportError:
    print(
        "No GPIO lib detected. Is this running on the PI and has this library been installed?"
    )
    quit(1)

# If custom config file is defined, use the supplied config file instead
parser = argparse.ArgumentParser(description="Pump manager")
parser.add_argument(
    "--config_section",
    dest="config_section",
    default="temp",
    required=True,
    type=str,
    help="Type of temp config",
)
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
CONFIG_SECTION = args.config_section

config = configparser.ConfigParser()
config.read(CONFIGFILE)

# To be put in config path, or enumerate all 28-* devices
ONEWIRE_PATH = config[CONFIG_SECTION]["PATH"]
URL = config[CONFIG_SECTION]["URL"]


def read_temp_raw():
    f = open(ONEWIRE_PATH, "r")
    lines = f.readlines()
    f.close()
    return lines


def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != "YES":
        time.sleep(0.2)
        lines = read_temp_raw()
    equal_pos = lines[1].find("t=")
    if equal_pos != -1:
        temp_string = lines[1][equal_pos + 2:]
        temp_in_c = float(temp_string) / 1000.0
        temp_in_f = temp_in_c * 9.0 / 5.0 + 32.0
        return temp_in_c, temp_in_f


if __name__ == "__main__":
    if not os.path.exists(ONEWIRE_PATH):
        print(f"Bad config, recheck where the onewire file is located: {ONEWIRE_PATH}")
        quit(1)

    while True:
        temp_c, temp_f = read_temp()
        try:
            response = requests.post(
                URL,
                json={"temp": temp_c, "data": CONFIG_SECTION},
                headers=headers,
            )
            if response.status_code == 200:
                print(f"Templog request sent with data: {temp_c}")
            else:
              print(
                  f"Templog request NOT sent successfully with data: {temp_c} and response code: {response.status_code}: {response.content}"
              )
        except requests.ConnectionError:
            print(
                f"Templog request NOT sent successfully with data: {temp_c} and response code: {response.status_code}: {response.content}"
            )

        time.sleep(60 * 5)

    quit(1)
