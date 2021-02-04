import wiringpi

OUTPUT = 1

wiringpi.wiringPiSetupGpio()
channels = [17, 18, 19, 20, 21, 22, 23, 24, 25]

for channel in channels:
    pwm_success = wiringpi.softPwmCreate(channel, 0, 100)
    print(pwm_success)

    wiringpi.softPwmWrite(channel, 75)

try:
    while True:
        wiringpi.delay(1000)
finally:
    wiringpi.softPwmWrite(channel, 0)
    print("cleaning up")
