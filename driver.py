import time
try:
    import RPi.GPIO as IO
except ImportError:
    print(
        "No GPIO lib detected. Is this running on the PI and has this library been installed?"
    )
    quit(1)

GPIO_DIR = 2
GPIO_PUL = 3
GPIO_EN = 4
IO.setmode(IO.BCM)
DELAY = 0.0001
STEPS = 1768

# Don't alert us about stupid shit
IO.setwarnings(False)

# Set our GPIO modes
IO.setup(GPIO_DIR, IO.OUT)
IO.setup(GPIO_PUL, IO.OUT)
IO.setup(GPIO_EN, IO.OUT)

try:
    IO.output(GPIO_DIR, IO.HIGH)
    # For 48-step motor, 48 iterations is one full cycle 
    # when the stepper is on 1
    #for i in range(0, STEPS):
    print("Starting new cycle")
    while True:
        IO.output(GPIO_PUL, IO.HIGH)
        time.sleep(DELAY)
        IO.output(GPIO_PUL, IO.LOW)
        time.sleep(DELAY)


finally:
    IO.output(GPIO_DIR, IO.LOW)
    IO.cleanup()
