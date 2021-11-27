"""
Primary pump manager code

Manages major pumps and degassing sequence
"""

import argparse
import asyncio
import configparser
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
        "degas_enabled",
        "degas_on",
        "degas_limit",
        "degas_cycle_time",
    ],
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
    icounter = 0  # Degassing iteration counter

    if mpump.degas_enabled:
        print("Beginning degassing sequence")
        d_on = mpump.degas_on  # Degas phase on time per cycle
        while True:
            # If the degas cycle is on, turn it off and vice versa
            IO.output(MIXER, IO.HIGH if on else IO.LOW)
            # Calculate how long between the next cycle
            to_stop = d_on if on else calc_off_period(d_on, mpump.degas_cycle_time)

            on = not on
            await asyncio.sleep(to_stop)
            if icounter >= mpump.degas_limit:
                # We're done degassing, move on to normal mixing procedures
                break
            if not on:
                icounter += 1
            await asyncio.sleep(0.5)

        print("Ending degassing sequence")
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
            await asyncio.sleep(to_stop)
            on = not on
            await asyncio.sleep(0.5)
    else:
        print("Set for static power cycling")
        pwm.ChangeDutyCycle(calc_power(flowrate) if on else 0)
        while True:
             await asyncio.sleep(1000)


def start_pumps(pwms):
    """
    Begin each enabled pump running in async
    """
    # Access our config declared in the global scope
    global config

    # Default to on
    on = True

    print("Starting pump loop")
    # Set up our mixer
    mixer = MixerPumpConfig(
        int(config["MIXER"]["ON"]),
        int(config["MIXER"]["CYCLE_TIME"]),
        bool(int(config["MIXER"]["ENABLE_CYCLING"])),
        bool(int(config["MIXER"]["ENABLED"])),
        bool(int(config["DEGAS"]["ENABLED"])),
        int(config["DEGAS"]["DEGAS_ON"]),
        int(config["DEGAS"]["DEGAS_CYCLE_LIMIT"]),
        int(config["DEGAS"]["DEGAS_CYCLE_TIME"]),
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
            + [cycle_mixer_pump(mixer)]
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
