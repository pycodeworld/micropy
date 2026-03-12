
from machine import I2C, Pin
from time import sleep_ms
from pcwlib import *
from pca9685 import *
from pcwi2c import I2CDev


i2c = I2C(0, scl=Pin(16), sda=Pin(15), freq=400000)
controller = PCA9685(i2c, address=0x40)

servo1 = Servo360(I2CDev(controller, 0))
servo1.calibrate(25)
for speed in [-50, 50, 0]:
    servo1.speed(speed)
    sleep_ms(500)

servo2 = Servo(I2CDev(controller, 1))
for angle in range(0, 181, 20):
    servo2.angle(angle)
    sleep_ms(1000)

led = PWMDev(I2CDev(controller, 2))
for percent in range(0, 101, 1):
    led.percent(percent)
    sleep_ms(10)
 
controller.deinit()
