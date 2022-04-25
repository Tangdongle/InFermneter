"""
Primary pump manager code

Manages major pumps and degassing sequence
"""

import argparse
import asyncio
import configparser
import requests
import datetime
from collections import namedtuple
import logging
formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG) # process everything, even if everything isn't printe

ch = logging.StreamHandler()
ch.setLevel(logging.INFO) # or any other level
ch.setFormatter(formatter)
logger.addHandler(ch)

fh = logging.FileHandler('pmplog.log')
fh.setLevel(logging.DEBUG) # or any level you want
fh.setFormatter(formatter)
logger.addHandler(fh)


try:
    import RPi.GPIO as IO
except ImportError:
    logger.info(
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
    [
        "gpio_dir",
        "gpio_pul",
        "gpio_en",
        "drain_sen",
        "drain_boost",
        "drain_cycle_time",
        "motor_steps",
        "step_set",
        "dir",
        "enabled",
    ],
)

# Don't alert us about stupid shit
IO.setwarnings(False)


config = configparser.ConfigParser()
config.read(CONFIGFILE)

# Lowest flowrate before cycling begins
FLOW_LOW = float(config["GENERAL"]["FLOW_LOW"])
PPD = float(config["AUTO"]["PPD"])
REAC_RECYC = float(config["AUTO"]["REACTOR_RECYLE"])
CLAR_RECYC = float(config["AUTO"]["CLARIFIER_RECYLE"])
SLOPS_RATE = float(config["AUTO"]["SLOPS_RATE"])
TEMP_STOP = float(config["DRAIN"]["TEMP_STOP"])

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
SAFETY_RELAY = 18


def feed_rate(ppd):
    return 0.395 * ppd


def calc_drain_pump_transfer_rate(feed_rate, drain_sensitivity, level_sensor_active):
    if level_sensor_active:
        return feed_rate * (1 + drain_sensitivity)
    else:
        return feed_rate * (1 - drain_sensitivity)


def calc_insantaneous_rate(transfer_rate, drain_boost):
    return transfer_rate * drain_boost


def calc_off_period(on, cycle_time):
    """
    Calculate how long a cycle should be off for
    """
    return cycle_time - on


def calc_power(flowrate):
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
        logger.info("[MIXER] Cycling Enabled")
        # Alternate between turning the mixing pumps on and off
        while True:
            IO.output(MIXER, IO.HIGH if on else IO.LOW)
            to_stop = on_time if on else calc_off_period(on_time, mpump.cycle_time)
            on = not on
            await asyncio.sleep(to_stop)
    else:
        logger.info("[MIXER] Constant operation")
        # If cycling is not enabled, switch the pumps on and leave it
        IO.output(MIXER, IO.HIGH)
        while True:
            await asyncio.sleep(1000)


async def cycle_pump(idx: int, pwm, on: bool):
    """
    Cycle logic for main pumps
    """
    logger.info(f"Cycling pump {idx + 1}")

    global HEADERS

    # Which pump are we looking at?
    pconfig = PUMP_IDS[idx + 1]

    if idx + 1 == 2:
        flowrate = feed_rate(PPD) * REAC_RECYC

    elif idx + 1 == 3:
        flowrate = feed_rate(PPD) * CLAR_RECYC
    elif idx + 1 == 4:
        flowrate = feed_rate(PPD) * SLOPS_RATE
    else:
        # Fetch the flowrate for this pump
        flowrate = pconfig.flowrate

    # Fetch the cycle time for this pump
    cycle_time = pconfig.cycle_time
    if flowrate <= FLOW_LOW:
        logger.info(f"Pump {idx + 1}: Set for dynamic power cycling")
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
            #requests.post(
            #    "https://beer.tanger.dev/notification",
            #    json={
            #        "message": f"Pump {idx + 1} is {'enabled' if on else 'disabled'}",
            #        "level": "info",
            #    },
            #    headers=HEADERS,
            #)
            await asyncio.sleep(to_stop)
            on = not on
            await asyncio.sleep(0.5)
    else:
        logger.info("Set for static power cycling")
        pwm.ChangeDutyCycle(calc_power(flowrate) if on else 0)
        while True:
            await asyncio.sleep(1000)


async def drain_cycle(level_sensor, drain_pump, ppd):
    global HEADERS
    logger.info("Starting drain cycle")
    # Set direction
    IO.output(drain_pump.gpio_dir, IO.HIGH if drain_pump.dir == "CCW" else IO.LOW)

    def calc_on_cycle(drain_cycle, insta_rate):
        return (drain_cycle / drain_pump.drain_boost) * 60

    def calc_off_cycle(drain_cycle, insta_rate):
        return (drain_cycle) - (drain_cycle / drain_pump.drain_boost) * 60

    def step_delay(motor_steps, step_rate, rp):
        return (motor_steps * step_rate) / (360.0 * 60.0 * rp)

    def rpm(insta):
        return (0.59277675 * insta) - 0.09822848

    ONEWIRE_PATH = config["DRAIN_TEMP"]["PATH"]

    def read_temp_raw():
        f = open(ONEWIRE_PATH, "r")
        lines = f.readlines()
        f.close()
        return lines

    def read_temp():
        lines = read_temp_raw()
        while lines[0].strip()[-3:] != "YES":
            await asyncio.sleep(0.2)
            lines = read_temp_raw()

        equal_pos = lines[1].find("t=")
        if equal_pos != -1:
            temp_string = lines[1][equal_pos + 2:]
            temp_in_c = float(temp_string) / 1000.0
            temp_in_f = temp_in_c * 9.0 / 5.0 + 32.0
            return temp_in_c, temp_in_f

    while True:
        temp_c, temp_f = read_temp()

        current_time = datetime.datetime.now()
        if current_time.hour > 20:
            # Don't run at night
            await asyncio.sleep(60 * 60)
        elif current_time.hour < 6:
            # Don't run at night
            await asyncio.sleep(60 * 60)

        if temp_c > TEMP_STOP:
            # Sleep a minute before checking again
            IO.output(SAFETY_RELAY, IO.HIGH)
            await asyncio.sleep(60)
        else:
            IO.output(SAFETY_RELAY, IO.LOW)

        val = not IO.input(level_sensor.gpio)  # Read from sensor

        transfer_rate = calc_drain_pump_transfer_rate(
            feed_rate(ppd), drain_pump.drain_sen, val
        )
        current_insta_rate = calc_insantaneous_rate(transfer_rate, drain_pump.drain_boost)
        rpm_val = rpm(current_insta_rate)
        d = step_delay(drain_pump.motor_steps, drain_pump.step_set, rpm_val)
        IO.output(drain_pump.gpio_en, IO.HIGH)
        on_cycle = calc_on_cycle(drain_pump.drain_cycle_time, current_insta_rate)
        logger.info(f"On for {on_cycle} seconds")
        logger.info(f"DELAY FOR {d} SECONDS")
        total = 0.0
        while True:
            IO.output(drain_pump.gpio_pul, IO.HIGH)
            await asyncio.sleep(d)
            IO.output(drain_pump.gpio_pul, IO.LOW)
            total += d
            if total * d >= on_cycle:
                break

        logger.info(f"Turning off")
        IO.output(drain_pump.gpio_en, IO.LOW)
        logger.info(f"sleeping for {calc_off_cycle(drain_pump.drain_cycle_time, current_insta_rate)}")
        await asyncio.sleep(
            calc_off_cycle(drain_pump.drain_cycle_time, current_insta_rate)
        )
        requests.post(
            "https://beer.tanger.dev/notification",
            json={"message": f"Drain pump has finished running", "level": "info"},
            headers=HEADERS,
        )


def start_pumps(pwms):
    """
    Begin each enabled pump running in async
    """
    # Access our config declared in the global scope
    global config
    global HEADERS

    # Default to on
    on = True

    logger.info("Starting pump loop")
    # Set up our mixer
    mixer = MixerPumpConfig(
        int(config["MIXER"]["ON"]),
        int(config["MIXER"]["CYCLE_TIME"]),
        bool(int(config["MIXER"]["ENABLE_CYCLING"])),
        bool(int(config["MIXER"]["ENABLED"])),
    )

    level_sensor_enabled = bool(int(config["LEVEL"]["ENABLED"]))
    level_sensor = LevelSensorConfig(int(config["LEVEL"]["GPIO"]))
    drain_pump = DrainPumpConfig(
        int(config["DRAIN"]["GPIO_DIR"]),
        int(config["DRAIN"]["GPIO_PUL"]),
        int(config["DRAIN"]["GPIO_EN"]),
        float(config["DRAIN"]["DRAIN_SEN"]),
        float(config["DRAIN"]["DRAIN_BOOST"]),
        float(config["DRAIN"]["DRAIN_CYCLE_TIME"]),
        int(config["DRAIN"]["MOTOR_STEPS"]),
        float(config["DRAIN"]["STEP_SET"]),
        config["DRAIN"]["DIR"],
        bool(int(config["DRAIN"]["ENABLED"])),
    )

    if level_sensor_enabled:
        logger.info("Level Sensor Enabled")
        # Set up level sensor GPIO
        IO.setup(level_sensor.gpio, IO.OUT)
        requests.post(
            "https://beer.tanger.dev/notification",
            json={"message": "Level Sensor setup", "level": "info"},
            headers=HEADERS,
        )

    if drain_pump.enabled:
        logger.info("Drain Pump Enabled")
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

    # As our async tasks never complete, this runs indefinitely
    loop.run_until_complete(
        asyncio.gather(
            *[
                cycle_pump(idx, pwm, on)
                for (idx, pwm, enabled) in pwms
                if enabled  # Only activate pump if enabled
            ]
            + (
                [drain_cycle(level_sensor, drain_pump, PPD)]
                if level_sensor_enabled and drain_pump.enabled
                else []
            )
            + ([cycle_mixer_pump(mixer)] if mixer.enabled else [])
        )
    )


# ========================================
# Initialisation and main pump dispatch

try:
    # Set our GPIO modes
    IO.setmode(IO.BCM)
    IO.setup(MIXER, IO.OUT)

    def setuppump(idx, config: PumpConfig):
        """
        Set our pump GPIO and initialise the PWM connection
        """
        # If not enabled, don't just start it up
        if config.enabled:
            pin = config.gpio
            IO.setup(int(pin), IO.OUT)
            p = IO.PWM(int(pin), config.frequency)
            p.start(0)
            logger.info(f"SETUP FOR PUMP {idx + 1}: Setting up pump {pin} with PWM frequency {config.frequency}")
            return p

    # Set up our pumps, ignoring any disabled ones
    pumps = [
        (idx, setuppump(idx, config), config.enabled)
        for idx, config in enumerate(PUMP_IDS.values())
        if config.enabled
    ]
    logger.info(pumps)
    try:
        start_pumps(pumps)
    except Exception as e:
        logger.info(f"Quitting/Error: Cleaning up: {e}")
except Exception as e:
    logger.info(e)
    pass
finally:
    logger.info("Cleaning up")
    try:
        # cleanup our pins
        for pump in pumps:
            pump.ChangeDutyCycle(0)
            pump.stop()
    except:
        pass
    finally:
        IO.cleanup()
        raise(IOError)
