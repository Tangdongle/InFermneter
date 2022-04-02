"""
Primary pump manager code

Manages major pumps and degassing sequence
"""

import argparse
import asyncio
import configparser
import requests
from collections import namedtuple

try:
    import RPi.GPIO as IO
except ImportError:
    print(
        "No GPIO lib detected. Is this running on the PI and has this library been installed?"
    )
    quit(1)

# If custom config file is defined, use the supplied config file instead
parser = argparse.ArgumentParser(description="Pump manager")
parser.add_argument(
    "--config",
    dest="config_fname",
    default="config.ini",
    required=False,
    type=str,
    help="Custom config file to use",
)
args = parser.parse_args()

CONFIGFILE = args.config_fname

HEADERS = {"Content-type": "application/json"}

# A couple of definitions
PumpConfig = namedtuple(
    "PumpConfig", ["gpio", "flowrate", "cycle_time", "enabled", "frequency"]
)
MixerPumpConfig = namedtuple(
    "MixerPumpConfig",
    [
        "on",
        "cycle_time",
        "cycle_enabled",
        "enabled",
    ],
)

LevelSensorConfig = namedtuple(
    "LevelSensorConfig",
    [
        "gpio",
    ],
)

DrainPumpConfig = namedtuple(
    "DrainPumpConfig",
    ["gpio_dir", "gpio_pul", "gpio_en", "delay", "dir", "drain_duration"],
)

# Don't alert us about stupid shit
IO.setwarnings(False)


config = configparser.ConfigParser()
config.read(CONFIGFILE)

# Lowest flowrate before cycling begins
FLOW_LOW = float(config["GENERAL"]["FLOW_LOW"])

# Read our pump config data
PUMP_IDS = {
    pid: PumpConfig(
        int(config[f"PUMP{pid}"]["GPIO"]),
        float(config[f"PUMP{pid}"]["MLPM"]),
        int(config[f"PUMP{pid}"]["CYCLE_TIME"]),
        bool(int(config[f"PUMP{pid}"]["ENABLED"])),
        int(config[f"PUMP{pid}"]["FREQUENCY"]),
    )
    for pid in range(1, int(config["GENERAL"]["NUM_PUMPS"]) + 1)
}

# Get our mixer GPIO pin number from config
MIXER = int(config["MIXER"]["MIXER_GPIO"])


def calc_off_period(on, cycle_time):
    """
    Calculate how long a cycle should be off for
    """
    return cycle_time - on


def calc_power(flowrate: float):
    """
    Calculate the required Duty Cycle for a given flowrate
    """
    return (
        (0.001153 * pow(flowrate, 3))
        - (0.154667 * pow(flowrate, 2))
        + (7.611175 * flowrate)
        - 100.318949
    )


async def cycle_mixer_pump(mpump):
    """
    Operate the mixing pumps

    Degassing is for slowly equalizing the pressure that the mixxing pumps
    generate as they turn on (as they excite the CO2 too fast at 100%
    If degassing is required, we run through that process first and then begin normal mixing cycles
    """

    on = True  # Is cycle on?

    on_time = mpump.on  # Normal mixing pump ON time per cycle

    if mpump.cycle_enabled:
        print("[MIXER] Cycling Enabled")
        # Alternate between turning the mixing pumps on and off
        while True:
            IO.output(MIXER, IO.HIGH if on else IO.LOW)
            to_stop = on_time if on else calc_off_period(on_time, mpump.cycle_time)
            on = not on
            await asyncio.sleep(to_stop)
    else:
        print("[MIXER] Constant operation")
        # If cycling is not enabled, switch the pumps on and leave it
        IO.output(MIXER, IO.HIGH)
        while True:
            await asyncio.sleep(1000)


async def cycle_pump(idx: int, pwm, on: bool):
    """
    Cycle logic for main pumps
    """
    print(f"Cycling pump {idx}")

    global HEADERS

    # Which pump are we looking at?
    pconfig = PUMP_IDS[idx + 1]

    # Fetch the flowrate for this pump
    flowrate = pconfig.flowrate

    # Fetch the cycle time for this pump
    cycle_time = pconfig.cycle_time
    if flowrate <= FLOW_LOW:
        print(f"Pump {idx}: Set for dynamic power cycling")
        while True:

            def on_cycle():
                """
                Calculate how long the pump should be on for each cycle
                """
                return flowrate / FLOW_LOW * cycle_time

            def off_cycle():
                """
                Calculate how long the pump should be off for each cycle
                """
                return (1 - flowrate / FLOW_LOW) * cycle_time

            power = calc_power(FLOW_LOW)
            to_stop = on_cycle() if on else off_cycle()

            # Set the PWM duty cycle to the required power level
            pwm.ChangeDutyCycle(power if on else 0)
            requests.post(
                "https://beer.tanger.dev/notification",
                json={
                    "message": f"Pump {idx + 1} is {'enabled' if on else 'disabled'}",
                    "level": "info",
                },
                headers=HEADERS,
            )
            await asyncio.sleep(to_stop)
            on = not on
            await asyncio.sleep(0.5)
    else:
        print("Set for static power cycling")
        pwm.ChangeDutyCycle(calc_power(flowrate) if on else 0)
        while True:
            await asyncio.sleep(1000)


async def drain_cycle(level_sensor, drain_pump):
    global HEADERS
    print("Starting drain cycle")
    # Set direction
    IO.output(drain_pump.gpio_dir, IO.HIGH if drain_pump.dir == "CCW" else IO.LOW)
    # Disable  draining pump
    IO.output(drain_pump.gpio_en, IO.LOW)
    while True:
        val = not IO.input(level_sensor.gpio)  # Read from sensor
        if val:
            print("Sensing some liquid!")
            requests.post(
                "https://beer.tanger.dev/notification",
                json={"message": f"Level Sensor Triggered", "level": "info"},
                headers=HEADERS,
            )

            print(f"Drain  Pump dir is {drain_pump.dir}")
            requests.post(
                "https://beer.tanger.dev/notification",
                json={"message": f"Drain pump is now running", "level": "info"},
                headers=HEADERS,
            )
            IO.output(
                drain_pump.gpio_dir, IO.HIGH if drain_pump.dir == "CCW" else IO.LOW
            )
            print("Starting new cycle")
            IO.output(drain_pump.gpio_en, IO.HIGH)
            iters = 0
            while True:
                IO.output(drain_pump.gpio_pul, IO.HIGH)
                await asyncio.sleep(drain_pump.delay)
                IO.output(drain_pump.gpio_pul, IO.LOW)
                await asyncio.sleep(drain_pump.delay)
                iters += 1
                # Check it's been running for long enough
                if iters * drain_pump.delay >= drain_pump.drain_duration:
                    break
            requests.post(
                "https://beer.tanger.dev/notification",
                json={"message": f"Drain pump has finished running", "level": "info"},
                headers=HEADERS,
            )
            IO.output(drain_pump.gpio_en, IO.LOW)
        await asyncio.sleep(2)


def start_pumps(pwms):
    """
    Begin each enabled pump running in async
    """
    # Access our config declared in the global scope
    global config
    global HEADERS

    # Default to on
    on = True

    print("Starting pump loop")
    # Set up our mixer
    mixer = MixerPumpConfig(
        int(config["MIXER"]["ON"]),
        int(config["MIXER"]["CYCLE_TIME"]),
        bool(int(config["MIXER"]["ENABLE_CYCLING"])),
        bool(int(config["MIXER"]["ENABLED"])),
    )

    level_sensor_enabled = bool(config["LEVEL"]["ENABLED"])
    drain_pump_enabled = bool(config["DRAIN"]["ENABLED"])
    level_sensor = LevelSensorConfig(int(config["LEVEL"]["GPIO"]))
    drain_pump = DrainPumpConfig(
        int(config["DRAIN"]["GPIO_DIR"]),
        int(config["DRAIN"]["GPIO_PUL"]),
        int(config["DRAIN"]["GPIO_EN"]),
        float(config["DRAIN"]["DELAY"]),
        config["DRAIN"]["DELAY"],
        float(config["DRAIN"]["DRAIN_DURATION"]),
    )

    if level_sensor_enabled:
        print("Level Sensor Enabled")
        # Set up level sensor GPIO
        IO.setup(level_sensor.gpio, IO.OUT)
        requests.post(
            "https://beer.tanger.dev/notification",
            json={"message": "Level Sensor setup", "level": "info"},
            headers=HEADERS,
        )

    if drain_pump_enabled:
        print("Drain Pump Enabled")
        # Set up drain pump GPIOs
        IO.setup(drain_pump.gpio_dir, IO.OUT)
        IO.setup(drain_pump.gpio_pul, IO.OUT)
        IO.setup(drain_pump.gpio_en, IO.OUT)

        requests.post(
            "https://beer.tanger.dev/notification",
            json={"message": "Drain Pump setup", "level": "info"},
            headers=HEADERS,
        )
    # Get the loop that will run our pump tasks asynchronously
    # Think of this as a while True loop with no breaking condition
    loop = asyncio.get_event_loop()

    print(pwms)
    # As our async tasks never complete, this runs indefinitely
    loop.run_until_complete(
        asyncio.gather(
            *[
                cycle_pump(idx, pwm, on)
                for (idx, pwm, enabled) in pwms
                if enabled  # Only activate pump if enabled
            ]
            + [drain_cycle(level_sensor, drain_pump)]
            if level_sensor_enabled and drain_pump_enabled
            else [] + [cycle_mixer_pump(mixer)]
            if mixer.enabled
            else []
        )
    )


# ========================================
# Initialisation and main pump dispatch

try:
    # Set our GPIO modes
    IO.setmode(IO.BCM)
    IO.setup(MIXER, IO.OUT)

    def setuppump(config: PumpConfig):
        """
        Set our pump GPIO and initialise the PWM connection
        """
        # If not enabled, don't just start it up
        if config.enabled:
            pin = config.gpio
            IO.setup(int(pin), IO.OUT)
            p = IO.PWM(int(pin), config.frequency)
            p.start(0)
            print(f"Setting up pump {pin} with PWM frequency {config.frequency}")
            return p

    # Set up our pumps, ignoring any disabled ones
    pumps = [
        (idx, setuppump(config), config.enabled)
        for idx, config in enumerate(PUMP_IDS.values())
        if config.enabled
    ]
    print(pumps)
    try:
        start_pumps(pumps)
    except Exception as e:
        print(f"Quitting/Error: Cleaning up: {e}")
except Exception as e:
    print(e)
    pass
finally:
    print("Cleaning up")
    try:
        # cleanup our pins
        for pump in pumps:
            pump.ChangeDutyCycle(0)
            pump.stop()
    except:
        pass
    finally:
        IO.cleanup()
