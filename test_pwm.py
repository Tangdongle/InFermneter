import wiringpi

OUTPUT = 1

wiringpi.wiringPiSetup()
channel = 17
wiringpi.pinMode(channel, OUTPUT)
wiringpi.softPwmCreate(channel, 0, 100)

wiringpi.softPwmWrite(channel, 100)
print("Starting loop")
while True:
    pass
