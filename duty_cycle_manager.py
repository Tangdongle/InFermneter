import RPi.GPIO as IO

import time
IO.setwarnings(False)

power = 0

FLOW_MAX = 75.0
FLOW_LOW = 15.0
ON = True
OFF = False


class DutyCycleManager():

    def __init__(self):
        IO.setmode(IO.BCM)

        IO.setup(12,IO.OUT)
        self.frequency = 100
        self.pwm_object = IO.PWM(12,self.frequency)
        self.pwm_object.start(0)
        self.duty_cycle = 0

    def set_flowrate(self, flowrate):
        if flowrate < FLOW_LOW:
            flowrate = FLOW_LOW
        if flowrate > FLOW_MAX:
            flowrate = FLOW_MAX

        self.duty_cycle = 0.000562 * pow(flowrate, 3) - (0.053428 * pow(flowrate, 2)) + (2.039215 * flowrate) - 2.385384
        self.pwm_object.ChangeDutyCycle(self.duty_cycle)

    def cleanup(self):
        self.pwm_object.ChangeDutyCycle(0)
        self.pwm_object.stop()
        IO.cleanup()



#class DutyCycleManager():
#    current_output = 0
#    high: float = FLOW_MAX
#    low: float = FLOW_LOW
#    cycle_time: int = 100
#    flowrate: float = 0.0
#    pwm_object = None
#    frequency: int = 100
#
#    def __init__(self, high=FLOW_MAX, low=FLOW_LOW):
#        high = high
#        low = low
#        IO.setmode(IO.BCM)
#
#        IO.setup(12,IO.OUT)
#        self.pwm_object = IO.PWM(12,self.frequency)
#        self.pwm_object.start(0)
#
#
#    def get_cycle(self):
#        return self.current_output
#
#    def set_cycle(self, value):
#        if value < self.low:
#            value = self.low
#        elif value > self.high:
#            value = self.high
#            self.current_output = value
#
#    def calc_power(self, flowrate):
#        if flowrate < self.low:
#            flowrate = self.low
#         if flowrate > self.high:
#             flowrate = self.high
#
#        self.duty_cycle = (4.76e-5 * pow(flowrate, 2)) + (3.85e-2 * flowrate) + 1.14
#        return self.duty_cycle
#
#    def calc_cycle_power(self, flowrate):
#        self.status = ON
#        print(f"Starting cycle for flowrate: {flowrate}")
#
#        def on_cycle(self):
#            return self.flowrate / self.low * self.cycle_time
#
#        def off_cycle(self):
#            return (1 - self.flowrate / self.low) * self.cycle_time
#        print(f"Cycle is {self.status}")
#        to_stop = on_cycle() if self.status else off_cycle()
#        print(f"Waiting for  {to_stop}")
#        self.pwm_object.ChangeDutyCycle(self.calc_power(FLOW_LOW) if self.status else 0)
#        print(f"Setting duty cycle to {self.calc_power(FLOW_LOW)}")
#        time.sleep(to_stop)
#        self.status = not self.status
#
#    def loop(self):
#        try:
#            dc = 0
#            while True:
#                val = float(input("Flow Rate: "))
#                if val <= FLOW_LOW:
#                    self.calc_cycle_power(self.pwm_object, val)
#
#            dc = self.calc_power(val)
#            print(dc)
#            self.pwm_object.ChangeDutyCycle(dc)
#            time.sleep(0.1)
#        except KeyboardInterrupt:
#            pass
#
#    def cleanup(self):
#        self.pwm_object.ChangeDutyCycle(0)
#        self.pwm_object.stop()
#        IO.cleanup()
