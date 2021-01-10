```
_____       ______                             _
|_   _|     |  ____|                           | |
  | |  _ __ | |__ ___ _ __ _ __ ___   ___ _ __ | |_ ___ _ __
  | | | '_ \|  __/ _ \ '__| '_ ` _ \ / _ \ '_ \| __/ _ \ '__|
 _| |_| | | | | |  __/ |  | | | | | |  __/ | | | ||  __/ |
|_____|_| |_|_|  \___|_|  |_| |_| |_|\___|_| |_|\__\___|_|
```

# InFermenter Pump Manager

This module contains pump manager logic for the InFermenter (Infinite-Fermenter) system

All config is specified in config.ini, review the file and read the comments to get an idea of what does what

## Components

The InFermenter is comprised of 3 main components:
  * Pumpman
  * Transfer Tank
  * Temperature Sensor

A device may use between 1 and 3 components simultaneously

### Pumpman
The pumpman module is a generic way to handle pumps with cycle timers and associated mixing pump

### Transfer Tank
The transfer tank module manages the logic for emptying transfer tanks, given certain conditions

### Temperature Sensor
The temperature sensor module is responsible for reading and broadcasting data taken from a one-wire-connected digital temperature sensor

## Installation

The required libraries can be installed by running the `install` make target

## Temperature Sensore Setup

The OneWire protocol directly writes to a file. The filename should be located at `/sys/bus/w1/devices/<device_id>/w1_slave`

Make sure the correct modules are loaded
```sh
sudo modprobe w1-gpio pullup=1
sudo modprobe w1-therm
```

Symlink the `temp_sensor_log.py` file to somewhere available in the system PATH.

Then, chmod +x the script to enable it to be run.

Finally, configure the crontab to run every 5 minutes to get the temperature changes.


