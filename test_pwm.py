import wiringpi

OUTPUT = 1

wiringpi.wiringPiSetup()
channels = [17, 18, 19, 20, 21, 22, 23, 24, 25]
for channel in channels:
    wiringpi.pinMode(channel, OUTPUT)
    wiringpi.softPwmCreate(channel, 0, 100)

for time in range(0, 4):
    for channel in channels:
        wiringpi.softPwmWrite(channel, 100)
    wiringpi.delay(10)
    for channel in channels:
        wiringpi.softPwmWrite(channel, 0)
