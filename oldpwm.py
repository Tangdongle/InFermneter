import asyncio
import time
import configparser
from collections import namedtuple
try:
    import RPi.GPIO as IO
except ImportError:
    print("No GPIO lib detected. Is this running on the PI and has this library been installed?")
    quit(1)

PumpConfig = namedtuple("PumpConfig", ["gpio", "flowrate"])


IO.setwarnings(False)

CONFIGFILE = "config.ini"

config = configparser.ConfigParser()
config.read(CONFIGFILE)


FLOW_MAX = 78.0
FLOW_LOW = 20.0
CYCLE_TIME = 100


PUMP_IDS = {
    pid: PumpConfig(config[f"PUMP{pid}"]["GPIO"], config[f"PUMP{pid}"]["FLOWRATE"])
    for pid in range(1)
}

MIN_FLOWRATE = min((p.flowrate for p in PUMP_IDS.values()))


async def cycle_pump(idx: int, pwm: object, on: bool):
    pconfig = PUMP_IDS[idx]
    flowrate = pconfig.flowrate
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
        await asyncio.sleep(to_stop)
        on = not on


def calc_power(flowrate: float):
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


def calc_cycle_power(pwms: tuple(object)):
    on = True

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[
        cycle_pump(idx, pwm, on)
        for idx, pwm in enumerate(pwms)
    ]))


frequency = 100

IO.setmode(IO.BCM)

def setuppump(config):
    pin = config.gpio
    IO.setup(pin, IO.OUT)
    p = IO.PWM(pin, frequency)
    p.start(0)
    return p

pumps = (
    setuppump(config)
    for config in PUMP_IDS.values()
)

try:
    dc = 0

    while True:
        val = float(input("Flow Rate: "))
        if val <= FLOW_LOW:
            calc_cycle_power(pumps)

        dc = calc_power(val)
        # Change the duty cycle on all pumps
        [pump.ChangeDutyCycle(dc) for pump in pumps]
        time.sleep(0.1)
except KeyboardInterrupt:
    pass


for pump in pumps:
    pump.ChangeDutyCycle(0)
    pump.stop()
IO.cleanup()
