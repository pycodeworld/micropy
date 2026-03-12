from pcwlib import Servo
from time import sleep_ms

servo = Servo(2, 180)
angles = [0, 90, 180, 90, 0]
for angle in angles:
    servo.angle(angle)
    sleep_ms(3000)
