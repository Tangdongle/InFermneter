import RPi.GPIO as IO
from .server import app

import os
import signal
import subprocess
import sys
import threading

from queue import Queue
from math import exp
import time
IO.setwarnings(False)

FLOW_MAX = 1090.0
FLOW_LOW = 450.0
CYCLE_TIME = 30

power = 0

def calc_power(flowrate):
  if flowrate < FLOW_LOW:
    flowrate = FLOW_LOW
  if flowrate > FLOW_MAX:
    flowrate = FLOW_MAX
  return (4.76e-5 * pow(flowrate, 2)) + (3.85e-2 * flowrate) + 1.14
  #return 0.0911 * flowrate - 6.21

def calc_cycle_power(pwm, flowrate):
  on = True
  print(f"Starting cycle for flowrate: {flowrate}")

  def on_cycle():
    return flowrate / FLOW_LOW * CYCLE_TIME

  def off_cycle():
    return (1 - flowrate / FLOW_LOW) * CYCLE_TIME

  while True:
    print(f"Cycle is {on}")
    to_stop = on_cycle() if on else off_cycle()
    print(f"Waitinf for  {to_stop}")
    pwm.ChangeDutyCycle(calc_power(FLOW_LOW) if on else 0)
    print(f"Setting duty cycle to {calc_power(FLOW_LOW)}")
    time.sleep(to_stop)
    on = not on

# GPIO Pins
clk = 17
dt = 18

dt_val = 0
clk_val = 0
fq = 100

last_gpio = None

INCREMENT = 5

IO.setmode(IO.BCM)

IO.setup(12,IO.OUT)
p = IO.PWM(12,fq)
p.start(0)

counter = 0

def loop():
    try:
        dc = 0
        while True:
          val = float(input("Flow Rate: "))
          if val <= FLOW_LOW:
            calc_cycle_power(p, val)

          dc = calc_power(val)
          print(dc)
          p.ChangeDutyCycle(dc)
          #event.wait(1200)
          #consume_queue()
          #event.clear()
          time.sleep(0.1)
    except KeyboardInterrupt:
      pass


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
    p.ChangeDutyCycle(0)
    p.stop()
    IO.cleanup()
