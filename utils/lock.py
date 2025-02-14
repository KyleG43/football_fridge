import RPi.GPIO as GPIO

pin = 16
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(pin, GPIO.OUT)

GPIO.output(pin, GPIO.HIGH)
print('Door locked')
