#!/usr/bin/env python3
import time
from smbus import SMBus
bus = SMBus(1)

def readChannel(params):
  global bus
  bus.write_byte(0x48, params & 0x03)
  bus.write_byte(0x48, 0)
  return bus.read_byte(0x48)

def analogOut(out):
  global bus
  bus.write_byte(0x48, 0x40)
  bus.write_byte(0x48, out & 0xFF)
  bus.write_byte(0x48, 0x00)

def readAll():
  global bus
  bus.write_byte(0x48, 0x04)
  data = []
  for _ in range(4):
    data.append(bus.read_byte(0x48))
  return data

while(True):
  print('all values are:')
  print(readAll())
  print('channel 1 is:')
  print(readChannel(1))
  print('check AOUT, should be about 2.5v')
  print(analogOut(127))
  time.sleep(3)
