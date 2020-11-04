import RPi.GPIO as IO

import asyncio

import time

IO.setwarnings(False)

FLOW_MAX = 78.0
FLOW_LOW = 20.0
CYCLE_TIME = 100

power = 0


async def cycle_pump(idx, pwm, flowrate, on):
    print(f"Starting cycle for flowrate: {flowrate} for pump {idx}")
    while True:

        def on_cycle():
            return flowrate / FLOW_LOW * CYCLE_TIME

        def off_cycle():
            return (1 - flowrate / FLOW_LOW) * CYCLE_TIME

        print(f"Cycle is {on} for pump {idx}")
        to_stop = on_cycle() if on else off_cycle()
        print(f"Waiting for  {to_stop}")
        pwm.ChangeDutyCycle(calc_power(FLOW_LOW) if on else 0)
        print(f"Setting duty cycle to {calc_power(FLOW_LOW)}")
        asyncio.sleep(to_stop)
        on = not on


def calc_power(flowrate):
    if flowrate < FLOW_LOW:
        flowrate = FLOW_LOW
    if flowrate > FLOW_MAX:
        flowrate = FLOW_MAX
    return (
        (0.000562 * pow(flowrate, 3))
        - (0.053428 * pow(flowrate, 2))
        + (2.039215 * flowrate)
        - 2.385384
    )
    # return 0.0911 * flowrate - 6.21


def calc_cycle_power(pwms, flowrate):
    on = True

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(
        cycle_pump(idx, pwm, flowrate, on)
        for idx, pwm in enumerate(pwms)
    ))


# GPIO Pins
clk = 17
dt = 18

dt_val = 0
clk_val = 0
fq = 100

last_gpio = None

INCREMENT = 5

IO.setmode(IO.BCM)
# IO.setup(clk,IO.IN, pull_up_down=IO.PUD_DOWN)
# IO.setup(dt,IO.IN, pull_up_down=IO.PUD_DOWN)

IO.setup(12, IO.OUT)
p = IO.PWM(12, fq)
p.start(0)


IO.setup(13, IO.OUT)
p2 = IO.PWM(13, fq)
p2.start(0)

# clkLastState = IO.input(clk)
counter = 0


def callback(channel):
    global last_gpio
    global clk_val
    global dt_val

    level = IO.input(channel)
    # if channel == clk:
    #  clk_val = level
    # elif channel == dt:
    #  dt_val = level

    if level != 1:
        return

    # if (channel != last_gpio):  # (debounce)
    #  last_gpio = channel
    #  if channel == dt and clk_val == 1:
    #    change_callback(1)
    #  elif channel == clk and dt_val == 1:
    #    change_callback(-1)


# IO.add_event_detect(dt, IO.BOTH, callback)
# IO.add_event_detect(clk, IO.BOTH, callback)

try:

    # queue = Queue()
    # event = threading.Event()

    ## Runs in the main thread to handle the work assigned to us by the
    ## callbacks.
    # def consume_queue():
    #  global power
    #  # If we fall behind and have to process many queue entries at once,
    #  # we can catch up by only calling `amixer` once at the end.
    #  while not queue.empty():
    #    delta = queue.get()
    #    if delta == 1:
    #      power += INCREMENT
    #    elif delta == -1:
    #      power -= INCREMENT
    #    if power > 100:
    #      power = 100
    #    elif power < 0:
    #      power = 0
    #    print(power)

    dc = 0
    ## on_turn and on_press run in the background thread. We want them to do
    ## as little work as possible, so all they do is enqueue the volume delta.
    # def change_callback(delta):
    #  queue.put(delta)
    #  event.set()

    while True:
        val = float(input("Flow Rate: "))
        if val <= FLOW_LOW:
            calc_cycle_power((p, p2), val)

        dc = calc_power(val)
        print(dc)
        p.ChangeDutyCycle(dc)
        p2.ChangeDutyCycle(dc)
        # event.wait(1200)
        # consume_queue()
        # event.clear()
        time.sleep(0.1)
except KeyboardInterrupt:
    pass


# IO.remove_event_detect(dt)
# IO.remove_event_detect(clk)
p.ChangeDutyCycle(0)
p.stop()
p2.ChangeDutyCycle(0)
p2.stop()
IO.cleanup()
