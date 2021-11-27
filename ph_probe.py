#!/usr/bin/env python3
import time
from smbus import SMBus
import requests
print("Starting PH Probe")
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

url = "https://beer.tanger.dev/ph"
headers = {'Content-type': 'application/json'}
while(True):
  print('channel 1 is:')
  print(readChannel(1))
  print('check AOUT, should be about 2.5v')
  print(analogOut(127))
  val = readChannel(1)
  val = (val / 10.0)
  try:
      response = requests.post(url, json={"ph": (val / 10.0), "data": "Test"}, headers=headers)
      if response.status_code == 200:
          print(f"PH request sent with data: {val}")
      print(
          f"PH request NOT sent successfully with data: {val} and response code: {response.status_code}: {response.content}"
      )
  except requests.ConnectionError:
      print(
          f"PH request NOT sent successfully with data: {val} and response code: {response.status_code}: {response.content}"
      )
  time.sleep(3)
