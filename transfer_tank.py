###
### Transfer tank sensors are active (1) when down (liquid lifts them up)
###
### Pump relay defaults to NC (Not connected) side
### so booleans for pump output are inverted
###
### Pump needs to be activated when both sensors are 0
### Pump stays active until bottom sensor is back on
###

import RPi.GPIO as IO
import time

# While this is TRUE (1), the pump relay will be active
DRAINING = False

TANK_BOTTOM_GPIO_IN = 15
TANK_TOP_GPIO_IN = 14
PUMP_GPIO_OUT = 2

IO.setmode(IO.BCM)
IO.setup(TANK_BOTTOM_GPIO_IN, IO.IN)
IO.setup(TANK_TOP_GPIO_IN, IO.IN)
IO.setup(PUMP_GPIO_OUT, IO.OUT)

IO.output(PUMP_GPIO_OUT, IO.HIGH)

try:
  while True:
    top_val = IO.input(TANK_TOP_GPIO_IN)
    bot_val = IO.input(TANK_BOTTOM_GPIO_IN)

    # If both the top and bottom sensors are off (0)
    # we need to start the draining cycle
    if (top_val == False and bot_val == False and not DRAINING):
      print("Draining enabled...")
      DRAINING = True
      IO.output(PUMP_GPIO_OUT, IO.LOW)

    # If we have been draining and the bottom sensor turns on
    # we have finished draining and can disable the pump
    if (DRAINING and bot_val == True):
      print("Draining complete.")
      DRAINING = False
      IO.output(PUMP_GPIO_OUT, IO.HIGH)

    time.sleep(0.5)
finally:
  IO.cleanup()
