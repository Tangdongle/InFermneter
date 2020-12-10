import asyncio
from datetime import datetime

import time
import configparser
from collections import namedtuple
try:
    import RPi.GPIO as IO
except ImportError:
    print("No GPIO lib detected. Is this running on the PI and has this library been installed?")
    quit(1)

PumpConfig = namedtuple("PumpConfig", ["gpio", "flowrate", "cycle_time"])
MixerPumpConfig = namedtuple("MixerPumpConfig", ["degas_on", "degas_cycle_time", "on", "cycle_time", "degas_limit"])


IO.setwarnings(False)

CONFIGFILE = "config.ini"

config = configparser.ConfigParser()
config.read(CONFIGFILE)


FLOW_LOW = 20.0

PUMP_IDS = {
    pid: PumpConfig(int(config[f"PUMP{pid}"]["GPIO"]), float(config[f"PUMP{pid}"]["MLPM"]), int(config[f"PUMP{pid}"]["CYCLE_TIME"]))
    for pid in range(1, 2)
}

MIXER = 23

def calc_off_period(on, cycle_time):
    return cycle_time - on

async def cycle_mixer_pump(mpump):
    on = True
    icounter = 0
    d_on = mpump.degas_on
    while True:
        IO.output(MIXER, IO.HIGH if on else IO.LOW)
        to_stop =  d_on if on else calc_off_period(d_on, mpump.degas_cycle_time)
        on = not on
        await asyncio.sleep(to_stop)
        icounter += 1
        if icounter >= mpump.degas_limit:
            break

    on_time = mpump.on
    while True:
        IO.output(MIXER, IO.HIGH if on else IO.LOW)
        to_stop = on_time if on else calc_off_period(on_time, mpump.cycle_time)
        on = not on
        await asyncio.sleep(to_stop)

async def cycle_pump(idx: int, pwm, on: bool):
    pconfig = PUMP_IDS[idx + 1]
    flowrate = pconfig.flowrate
    cycle_time = pconfig.cycle_time
    if flowrate <= FLOW_LOW:
        print(f"Set for dynamic power cycling")
        while True:

            def on_cycle():
                return flowrate / FLOW_LOW * cycle_time

            def off_cycle():
                return (1 - flowrate / FLOW_LOW) * cycle_time

            power = calc_power(FLOW_LOW)
            print(f"Power is {on}")
            print(f"Current power is {power} for flowrate {flowrate} for PUMP{idx + 1} with config: {pconfig}")
            to_stop = on_cycle() if on else off_cycle()
            print(f"Sleeping for {to_stop}")
            pwm.ChangeDutyCycle(power if on else 0)
            await asyncio.sleep(to_stop)
            on = not on
    else:
        print(f"Set for static power cycling")
        pwm.ChangeDutyCycle(calc_power(flowrate) if on else 0)


def calc_power(flowrate: float):
    return (
        (0.000562 * pow(flowrate, 3))
        - (0.053428 * pow(flowrate, 2))
        + (2.039215 * flowrate)
        - 2.385384
    )


def calc_cycle_power(pwms):
    global config
    on = True
    mixer = MixerPumpConfig(
        int(config[f"MIXER"]["DEGAS_ON"]),
        int(config[f"MIXER"]["DEGAS_CYCLE_TIME"]),
        int(config[f"MIXER"]["ON"]),
        int(config[f"MIXER"]["CYCLE_TIME"]),
        int(config[f"MIXER"]["DEGAS_CYCLE_LIMIT"])
    )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[
        cycle_pump(idx, pwm, on)
        for idx, pwm in pwms.items()
    ] + [cycle_mixer_pump(mixer)]))


frequency = 100

IO.setmode(IO.BCM)
IO.setup(MIXER, IO.OUT)

def setuppump(config: PumpConfig):
    pin = config.gpio
    IO.setup(int(pin), IO.OUT)
    p = IO.PWM(int(pin), frequency)
    p.start(0)
    return p

pumps = {
    idx: setuppump(config)
    for idx, config in enumerate(PUMP_IDS.values())
}
try:
    dc = 0

    calc_cycle_power(pumps)
except KeyboardInterrupt:
    pass


for pump in pumps.values():
    pump.ChangeDutyCycle(0)
    pump.stop()
IO.cleanup()
