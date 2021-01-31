#!/usr/bin/python3
import argparse
import requests
import os
import time

headers = {'Content-type': 'application/json'}

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
    "--url",
    dest="url",
    default="https://beer.tanger.dev/temp",
    required=False,
    type=str,
    help="Endpoint to send  data to",
)

args = parser.parse_args()

# To be put in config path, or enumerate all 28-* devices
ONEWIRE_PATH = "/sys/bus/w1/devices/28-01192fb03527/w1_slave"

def read_temp_raw():
    f = open(ONEWIRE_PATH, "r")
    lines = f.readlines()
    f.close()
    return lines

def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equal_pos = lines[1].find('t=')
    if equal_pos != -1:
        temp_string = lines[1][equal_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f

if __name__ == "__main__":
    if not os.path.exists(ONEWIRE_PATH):
        print(f"Bad config, recheck where the onewire file is located")
        quit(1)

    while True:
        temp_c, temp_f = read_temp()
        try:
            response = requests.post(args.url, json={"temp": temp_c, "data": "Test"}, headers=headers)
            print({"temp": temp_c, "data": ""})
            if response.status_code == 200:
                print(f"Templog request sent with data: {temp_c}")
            print(
                f"Templog request NOT sent successfully with data: {temp_c} and response code: {response.status_code}: {response.content}"
            )
        except requests.ConnectionError:
            print(
                f"Templog request NOT sent successfully with data: {temp_c} and response code: {response.status_code}: {response.content}"
            )

        time.sleep(60 * 5)

    quit(1)
