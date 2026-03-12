from pcwlib import *
from time import sleep_ms

"""
摇杆传感器测试
通过摇杆控制三色LED灯，X、Y控制红、绿颜色，开关控制蓝色
"""
led = LedRgb(38, 37, 36)
def sw_handler(pin):
    led.color(bule=255-led.blue.percent()*255/100)

ts = ToyStick(21, 20, 19, sw=sw_handler)
while True:
    r, g = ts.percent()
    led.color(r, g)
    sleep_ms(100)
