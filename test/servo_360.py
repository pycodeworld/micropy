from pcwlib import Servo360
from time import sleep

servo = Servo360(12)
servo.forward(100)
sleep(2)
servo.forward(50)
sleep(2)
servo.stop()
sleep(1)
servo.backward(75)
sleep(2)
servo.stop()
servo.deinit()
