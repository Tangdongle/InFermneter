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
