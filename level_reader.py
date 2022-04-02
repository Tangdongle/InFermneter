import time
try:
    import RPi.GPIO as IO
except ImportError:
    print(
        "No GPIO lib detected. Is this running on the PI and has this library been installed?"
    )
    quit(1)

GPIO_SENSE = 10
IO.setmode(IO.BCM)

# Don't alert us about stupid shit
IO.setwarnings(False)

# Set our GPIO modes
IO.setup(GPIO_SENSE, IO.OUT)

try:
    while True:
        val = not IO.input(GPIO_SENSE)  # Read from sensor
        if val:
            print("Sensing some liquid!")
        else:
            print("No Liquid to sense this time")
        time.sleep(2)

finally:
    IO.cleanup()
